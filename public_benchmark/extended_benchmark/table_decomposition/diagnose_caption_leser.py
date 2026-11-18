"""Offline-Pruefung: Was verschiebt die Caption-Korrektur ausserhalb der Wahl?

Die Caption aendert sich fuer 31 der 120 Tabellen. Dieses Skript laesst den
Parser zweimal laufen - mit der alten Caption-Suche (nur Leerzeilen
ueberspringen, keine Beschreibung ueber ``Table N``) und mit der neuen - und
vergleicht alles, was die Caption liest und nicht die Tabellenwahl ist:

* ``strategies._table_header``: die Zeile ``CAPTION (verbatim): ...`` im
  Modell-Prompt,
* ``crops.make_crop``: Zeichenspanne, Laenge und die Zusicherung
  ``includes_caption``,
* ``validation``: die Bedingung ``table.caption in prompt`` (Fehler
  ``caption_fehlt``) und ``crop_ohne_caption``,
* die Strukturzeile der Engine (``caption[:120]``).

Read-only: kein Modelllauf, kein Netz, Gold unberuehrt.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_caption_leser.py \
        --out public_benchmark/extended_benchmark/analysis/.../caption_leser.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

import research_agent.table_decomposition.parser as parser_mod  # noqa: E402
from research_agent.table_decomposition.crops import make_crop  # noqa: E402
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.strategies import (  # noqa: E402
    PlanOptions,
    _table_header,
    plan,
)

STRATEGIEN = ("A", "B", "C", "D", "E")


def _alte_leerzeilen(lines: Sequence[str], index: int) -> int:
    """Alte Suche: nur Leerzeilen ueberspringen, keine Bildzeile."""
    while index >= 0 and not lines[index].strip():
        index -= 1
    return index


def _parse_alt(text: str, doc_id: str):
    """Parser mit der alten Caption-Suche (Bildzeile und ``Table N``)."""
    neu_skip = parser_mod._skip_over
    neu_label = parser_mod._is_label_only
    parser_mod._skip_over = _alte_leerzeilen
    parser_mod._is_label_only = lambda caption: False
    try:
        return parse_document(text, doc_id)
    finally:
        parser_mod._skip_over = neu_skip
        parser_mod._is_label_only = neu_label


def _crop_lage(table: Any, text: str) -> Dict[str, Any]:
    """Zeichenspanne und Text des Tabellen-Crops - wie ``make_crop`` ihn baut."""
    crop = make_crop(
        table,
        [row.row_id for row in table.rows],
        [column.col_id for column in table.columns],
        "probe",
    )
    ausschnitt = text[crop.char_start:crop.char_end] if crop.char_start >= 0 else ""
    return {
        "char_start": crop.char_start,
        "char_end": crop.char_end,
        "laenge": max(0, crop.char_end - crop.char_start),
        "includes_caption": crop.includes_caption,
        "caption_im_ausschnitt": bool(table.caption) and table.caption in ausschnitt,
        "ausschnitt_beginnt": " ".join(ausschnitt[:80].split()),
    }


def _prompt_lage(table: Any, text: str) -> Dict[str, Any]:
    """Einheiten-Prompts aller Verfahren: steht die Caption darin?"""
    einheiten = 0
    ohne_caption = 0
    zeichen = 0
    for strategie in STRATEGIEN:
        for unit in plan(table, strategie, PlanOptions(), text).units:
            einheiten += 1
            prompt = unit.prompt or ""
            zeichen += len(prompt)
            if table.caption and table.caption not in prompt:
                ohne_caption += 1
    return {"einheiten": einheiten, "ohne_caption": ohne_caption,
            "prompt_zeichen": zeichen}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--selection", type=Path, default=rb.DEFAULT_SELECTION)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    gesehen: set = set()
    zeilen: List[Dict[str, Any]] = []
    zaehler: Counter = Counter()
    max_prompt_delta = 0
    max_crop_delta = 0
    kuerzer: List[Dict[str, Any]] = []

    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None or not entries:
            continue
        document = str(record["document"]["id"])
        if document in gesehen:
            continue
        gesehen.add(document)
        text = (REPO / entries[0]["document_path"]).read_text(
            encoding="utf-8", errors="replace")
        alt = {table.table_id: table for table in _parse_alt(text, document).tables}
        neu = {table.table_id: table for table in parse_document(text, document).tables}
        for table_id, table in neu.items():
            vorher = alt.get(table_id)
            if vorher is None:
                zaehler["tabelle_nur_neu"] += 1
                continue
            zaehler["tabellen"] += 1
            if (vorher.caption or "") == (table.caption or ""):
                zaehler["caption_unveraendert"] += 1
                continue
            zaehler["caption_geaendert"] += 1
            alt_crop = _crop_lage(vorher, text)
            neu_crop = _crop_lage(table, text)
            alt_prompt = _table_header(vorher)
            neu_prompt = _table_header(table)
            prompt_delta = len(neu_prompt) - len(alt_prompt)
            crop_delta = neu_crop["laenge"] - alt_crop["laenge"]
            max_prompt_delta = max(max_prompt_delta, abs(prompt_delta))
            max_crop_delta = max(max_crop_delta, abs(crop_delta))
            zaehler["prompt_geaendert"] += 1 if prompt_delta else 0
            zaehler["crop_spanne_geaendert"] += (
                1 if neu_crop["char_start"] != alt_crop["char_start"] else 0)
            zaehler["crop_kuerzer"] += 1 if crop_delta < 0 else 0
            zaehler["caption_neu_im_ausschnitt"] += 1 if neu_crop["caption_im_ausschnitt"] else 0
            zaehler["caption_alt_im_ausschnitt"] += 1 if alt_crop["caption_im_ausschnitt"] else 0
            zaehler["includes_caption_neu"] += 1 if neu_crop["includes_caption"] else 0
            prompt_alt = _prompt_lage(vorher, text)
            prompt_neu = _prompt_lage(table, text)
            zaehler["einheiten_alt"] += prompt_alt["einheiten"]
            zaehler["einheiten_neu"] += prompt_neu["einheiten"]
            zaehler["einheiten_ohne_caption_alt"] += prompt_alt["ohne_caption"]
            zaehler["einheiten_ohne_caption_neu"] += prompt_neu["ohne_caption"]
            max_prompt_delta = max(
                max_prompt_delta,
                abs(prompt_neu["prompt_zeichen"] - prompt_alt["prompt_zeichen"]))
            if crop_delta < 0:
                kuerzer.append({"table_id": table_id, "delta": crop_delta,
                                "aus": alt_crop["laenge"], "an": neu_crop["laenge"]})
            zeilen.append({
                "table_id": table_id,
                "record_id": record_id,
                "caption_alt": vorher.caption,
                "caption_neu": table.caption,
                "prompt_delta": prompt_delta,
                "prompt_zeichen_delta": (prompt_neu["prompt_zeichen"]
                                          - prompt_alt["prompt_zeichen"]),
                "einheiten_ohne_caption_neu": prompt_neu["ohne_caption"],
                "crop_delta": crop_delta,
                "crop_alt": alt_crop,
                "crop_neu": neu_crop,
                "engine_zeile_neu": f"[[table_structure {table.table_id} | {table.caption[:120]}]]",
            })

    bericht = {
        "selection": str(args.selection.relative_to(REPO))
                     if args.selection.is_absolute() else str(args.selection),
        "dokumente": len(gesehen),
        "zaehler": dict(sorted(zaehler.items())),
        "max_prompt_delta": max_prompt_delta,
        "max_crop_delta": max_crop_delta,
        "crop_kuerzer": sorted(kuerzer, key=lambda item: item["delta"]),
        "tabellen": zeilen,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Dokumente:", len(gesehen))
    print("Zaehler:", bericht["zaehler"])
    print("max prompt delta:", max_prompt_delta, "max crop delta:", max_crop_delta)
    print("crop kuerzer:", len(kuerzer))
    for eintrag in kuerzer[:5]:
        print("  ", eintrag)
    fehlt = [z for z in zeilen if not z["crop_neu"]["caption_im_ausschnitt"]]
    print("neue Caption nicht im Ausschnitt:", len(fehlt))
    for eintrag in fehlt[:5]:
        print("  ", eintrag["table_id"], repr(eintrag["caption_neu"])[:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
