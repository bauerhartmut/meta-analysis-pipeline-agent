"""Offline-Messung Sprint 47: Caption, Gruppenkopf-Zeile und Zielwahl.

Frage: Werden die zehn verbliebenen `population_mismatch`-Felder aus Sprint 45
wertgleich, wenn

* die gedruckte Caption einer Tabelle erhalten bleibt (sie stand hinter einer
  Bildzeile beziehungsweise unter einer blossen ``Table N``-Zeile),
* die Tabellenwahl die Caption als Beleg fuer die Outcome-Tabelle zulaesst,
* ein Gruppenkopf in einer Datenzeile als Kopfangabe gelesen wird -

ohne Armumkehr und ohne Gold zur Steuerung?

Read-only: Gold und eingefrorene Eingaben werden nur gelesen. Gemessen werden
zwei Staende mit demselben Code:

* ``ohne_wahl`` - die eingefrorene Tabellenauswahl (Vergleich zu Sprint 45),
* ``mit_wahl`` - die Tabellenwahl aus dem Dokument.

Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_gruppenkoepfe.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition import provenienz as pv  # noqa: E402
from research_agent.table_decomposition import tabellenwahl as tw  # noqa: E402
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import outcome_rows  # noqa: E402

from diagnose_populationswahl import (  # noqa: E402
    SPRINT45,
    _dokument,
    _gedruckt,
    _gold,
    _lage,
)

SPRINT46 = (BENCH / "analysis" / "table_decomposition_20261118"
            / "populationswahl_20261118" / "messung.json")

BLOSSE_BEZEICHNUNG = re.compile(r"^(?:table|tabelle)\s*[a-z]?\d+[a-z]?$",
                                re.IGNORECASE)


def _gleich(stellen: Dict[str, List[pv.Provenienz]],
            felder: List[Dict[str, Any]]) -> List[str]:
    """Felder, deren Goldwert an einer Fundstelle gedruckt steht."""
    treffer = []
    for feld in felder:
        orte = stellen.get(feld["field"]) or []
        if any(_gedruckt(stelle, feld["value"]) for stelle in orte):
            treffer.append(feld["field"])
    return treffer


def _feldsatz(bericht: Optional[Dict[str, Any]]) -> set:
    """Wertgleiche Felder eines frueheren Messberichts als ``record.feld``."""
    if not bericht:
        return set()
    felder = set()
    for record in bericht.get("records") or []:
        for feld, lage in (record.get("felder") or {}).items():
            if (lage.get("nachher") or {}).get("wertgleich"):
                felder.add(f"{record['record_id']}.{feld}")
    return felder


def _kategorien() -> Dict[tuple, str]:
    if not SPRINT45.exists():
        return {}
    alt = json.loads(SPRINT45.read_text(encoding="utf-8"))
    return {(f["record_id"], f["feld"]): f["kategorie"]
            for f in alt.get("nicht_wertgleich") or []}


def _caption_klassen() -> Dict[str, int]:
    """Captions aller Dokumente: leer, nur Bezeichnung, beschreibend."""
    zaehler: Counter = Counter()
    seen = set()
    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    for record_id, entries in rb.group_by_record(selection, None).items():
        record = records.get(record_id)
        if record is None or not entries:
            continue
        doc_id = str(record["document"]["id"])
        if doc_id in seen:
            continue
        seen.add(doc_id)
        tables, text, _redundant = rb.load_tables(entries, record)
        doc = parse_document(text, doc_id)
        for table in doc.tables:
            caption = " ".join((table.caption or "").split())
            if not caption:
                zaehler["leer"] += 1
            elif BLOSSE_BEZEICHNUNG.match(caption):
                zaehler["nur_bezeichnung"] += 1
            else:
                zaehler["beschreibend"] += 1
    return dict(sorted(zaehler.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    kategorien = _kategorien()
    sprint45 = (json.loads(SPRINT45.read_text(encoding="utf-8"))
                if SPRINT45.exists() else None)
    sprint46 = (json.loads(SPRINT46.read_text(encoding="utf-8"))
                if SPRINT46.exists() else None)
    vorher46 = _feldsatz(sprint46)

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    ohne_erreichbar = ohne_gleich = 0
    mit_erreichbar = mit_gleich = 0
    ohne_felder: set = set()
    mit_felder: set = set()
    arm_wechsel: List[Dict[str, Any]] = []
    wechsel: List[Dict[str, Any]] = []
    gruende: Counter = Counter()
    je_kategorie: Dict[str, Dict[str, int]] = {}
    record_berichte: List[Dict[str, Any]] = []

    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        tables, text, _redundant = rb.load_tables(entries, record)
        if not tables:
            continue
        context = rb.context_of(record)
        alle = _dokument(text, str(record["document"]["id"]), context)
        wahl = tw.waehle(tables, alle, context)
        gruende[wahl.grund if wahl else "keine_wahl"] += 1
        wechselt = bool(wahl and wahl.wechsel)
        ziel = wahl.tabelle if wechselt else tables[0]
        nachher = [ziel] if wechselt else list(tables)
        if wechselt:
            wechsel.append({
                "record_id": record_id,
                "von": [table.table_id for table in tables],
                "nach": ziel.table_id,
                "outcome": context.get("outcome"),
                "caption": ziel.caption,
                "outcome_zeilen": len(outcome_rows(ziel,
                                                   context.get("outcome") or "")),
                "baseline": tw.ist_baseline(ziel),
            })

        vorher_lage = _lage(_gold(record), pv.feld_stellen(tables, context))
        nachher_lage = _lage(_gold(record), pv.feld_stellen(nachher, context))

        for feld, lage in vorher_lage.items():
            if not lage["erreichbar"]:
                continue
            ohne_erreichbar += 1
            if lage["wertgleich"]:
                ohne_gleich += 1
                ohne_felder.add(f"{record_id}.{feld}")
            neu = nachher_lage[feld]
            if not neu["erreichbar"]:
                continue
            mit_erreichbar += 1
            if neu["wertgleich"]:
                mit_gleich += 1
                mit_felder.add(f"{record_id}.{feld}")
            if lage["arme"] and neu["arme"] != lage["arme"]:
                arm_wechsel.append({
                    "record_id": record_id, "feld": feld,
                    "vorher": lage["arme"], "nachher": neu["arme"],
                })
            kategorie = kategorien.get((record_id, feld))
            if kategorie:
                zaehler = je_kategorie.setdefault(
                    kategorie, {"gesamt": 0, "vorher": 0, "nachher": 0})
                zaehler["gesamt"] += 1
                zaehler["vorher"] += 1 if lage["wertgleich"] else 0
                zaehler["nachher"] += 1 if neu["wertgleich"] else 0

        record_berichte.append({
            "record_id": record_id,
            "outcome": context.get("outcome"),
            "aktuelle_tabellen": [table.table_id for table in tables],
            "gewaehlte_tabelle": ziel.table_id,
            "caption": ziel.caption,
            "grund": wahl.grund if wahl else "keine_wahl",
            "wechsel": wechselt,
            "vorher": vorher_lage,
            "nachher": nachher_lage,
        })

    bericht = {
        "bilanz": {
            "sprint45": ({"erreichbar": sprint45["bilanz"]
                          ["strukturell_erreichbar"],
                          "wertgleich": sprint45["bilanz"]["wertgleich"]}
                         if sprint45 else None),
            "sprint46": (sprint46 or {}).get("bilanz", {}).get("nachher"),
            "ohne_wahl": {"erreichbar": ohne_erreichbar,
                          "wertgleich": ohne_gleich},
            "mit_wahl": {"erreichbar": mit_erreichbar,
                         "wertgleich": mit_gleich},
            "neu_wertgleich": sorted(mit_felder - ohne_felder),
            "verloren": sorted(ohne_felder - mit_felder),
            "neu_gegen_sprint46": sorted(mit_felder - vorher46),
            "verloren_gegen_sprint46": sorted(vorher46 - mit_felder),
            "arm_wechsel": arm_wechsel,
        },
        "tabellenwechsel": wechsel,
        "gruende": dict(sorted(gruende.items())),
        "je_kategorie": dict(sorted(je_kategorie.items())),
        "captions": _caption_klassen(),
        "records": record_berichte,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    bilanz = bericht["bilanz"]
    print(f"ohne Wahl {ohne_erreichbar} erreichbar / {ohne_gleich} wertgleich")
    print(f"mit Wahl  {mit_erreichbar} erreichbar / {mit_gleich} wertgleich")
    print(f"Tabellenwechsel {len(wechsel)}, Gruende {bericht['gruende']}")
    print("je Kategorie:", bericht["je_kategorie"])
    print("neu wertgleich:", len(bilanz["neu_wertgleich"]),
          "verloren:", len(bilanz["verloren"]))
    print("gegen Sprint 46 neu:", len(bilanz["neu_gegen_sprint46"]),
          "verloren:", len(bilanz["verloren_gegen_sprint46"]))
    print("Armwechsel:", arm_wechsel)
    print("Captions:", bericht["captions"])
    for eintrag in wechsel:
        print(f"  {eintrag['record_id']} {eintrag['von']} -> {eintrag['nach']} "
              f"({eintrag['outcome']}) zeilen={eintrag['outcome_zeilen']} "
              f"baseline={eintrag['baseline']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
