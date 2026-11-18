"""Offline-Messung Sprint 48: Zahlen aus dem Fliesstext als Fundstelle.

Frage: Werden die fuenf noch offenen `population_mismatch`-Felder erreichbar
und wertgleich, wenn der gedruckte Fliesstext als Fundstelle zaehlt - ohne
Armumkehr und ohne Gold in der Regel?

Gemessen wird derselbe Stand wie in Sprint 47 (Tabellenwahl aus dem Dokument),
einmal ohne und einmal mit den Fliesstext-Fundstellen aus
`research_agent.table_decomposition.fliesstext`. Die Regeln dort lesen nur
gedruckte Formen:

* ``placebo, n = 28`` (Arm direkt an der Zahl),
* ``(283, 289, and 204 patients received ..., respectively)`` mit genannter
  Population,
* ``5.1% (4/79) ... respectively`` (Zaehler = Ereignisse, Nenner = Groesse).

Read-only: Gold und eingefrorene Eingaben werden nur gelesen.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_fliesstext.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition import fliesstext as fl  # noqa: E402
from research_agent.table_decomposition import provenienz as pv  # noqa: E402
from research_agent.table_decomposition import tabellenwahl as tw  # noqa: E402

from diagnose_populationswahl import _dokument, _gold, _lage  # noqa: E402

SPRINT45 = (BENCH / "analysis" / "table_decomposition_20261118"
            / "provenienz_20261118" / "messung.json")


def _kategorien() -> Dict[tuple, str]:
    if not SPRINT45.exists():
        return {}
    alt = json.loads(SPRINT45.read_text(encoding="utf-8"))
    return {(f["record_id"], f["feld"]): f["kategorie"]
            for f in alt.get("nicht_wertgleich") or []}


def _zusammengelegt(*quellen: Dict[str, List[pv.Provenienz]]
                    ) -> Dict[str, List[pv.Provenienz]]:
    out: Dict[str, List[pv.Provenienz]] = {}
    for quelle in quellen:
        for feld, stellen in quelle.items():
            out.setdefault(feld, []).extend(stellen)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--selection", type=Path, default=rb.DEFAULT_SELECTION)
    args = parser.parse_args()

    kategorien = _kategorien()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    ohne_erreichbar = ohne_gleich = 0
    mit_erreichbar = mit_gleich = 0
    ohne_felder: set = set()
    mit_felder: set = set()
    neu_erreichbar: List[str] = []
    verloren: List[str] = []
    arm_wechsel: List[Dict[str, Any]] = []
    konflikte: List[Dict[str, Any]] = []
    regeln: Counter = Counter()
    wert_index: Dict[str, List[float]] = {}
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
        ziel = wahl.tabelle if (wahl and wahl.wechsel) else tables[0]
        gelesen = [ziel] if (wahl and wahl.wechsel) else list(tables)

        tabellen_stellen = pv.feld_stellen(gelesen, context)
        text_stellen = fl.stellen(text, context, gelesen)
        for feld, stellen in text_stellen.items():
            for stelle in stellen:
                regeln[stelle.regel] += 1
            if not tabellen_stellen.get(feld):
                neu_erreichbar.append(f"{record_id}.{feld}")
            tabellen_werte = {stelle.wert for stelle in tabellen_stellen.get(feld, [])
                              if stelle.wert is not None}
            fremd = sorted({stelle.wert for stelle in stellen
                            if stelle.wert is not None} - tabellen_werte)
            if tabellen_werte and fremd:
                konflikte.append({"record_id": record_id, "feld": feld,
                                  "tabelle": sorted(tabellen_werte),
                                  "text": fremd})

        gold = _gold(record)
        alle_stellen = _zusammengelegt(tabellen_stellen, text_stellen)
        vorher = _lage(gold, tabellen_stellen)
        nachher = _lage(gold, alle_stellen)
        for feld, stellen in alle_stellen.items():
            wert_index[f"{record_id}.{feld}"] = sorted({
                round(stelle.wert, 2) for stelle in stellen
                if stelle.wert is not None})

        for feld, lage in vorher.items():
            if not lage["erreichbar"]:
                continue
            ohne_erreichbar += 1
            if lage["wertgleich"]:
                ohne_gleich += 1
                ohne_felder.add(f"{record_id}.{feld}")
            neu = nachher[feld]
            if not neu["erreichbar"]:
                verloren.append(f"{record_id}.{feld}")
                continue
            mit_erreichbar += 1
            if neu["wertgleich"]:
                mit_gleich += 1
                mit_felder.add(f"{record_id}.{feld}")
            if lage["arme"] and neu["arme"] != lage["arme"]:
                arm_wechsel.append({"record_id": record_id, "feld": feld,
                                    "vorher": lage["arme"], "nachher": neu["arme"]})
            kategorie = kategorien.get((record_id, feld))
            if kategorie:
                zaehler = je_kategorie.setdefault(
                    kategorie, {"gesamt": 0, "vorher": 0, "nachher": 0})
                zaehler["gesamt"] += 1
                zaehler["vorher"] += 1 if lage["wertgleich"] else 0
                zaehler["nachher"] += 1 if neu["wertgleich"] else 0

        # Felder, die erst durch den Text erreichbar werden, zaehlen mit.
        for feld in text_stellen:
            if vorher.get(feld, {}).get("erreichbar"):
                continue
            neu = nachher[feld]
            if not neu["erreichbar"]:
                continue
            mit_erreichbar += 1
            if neu["wertgleich"]:
                mit_gleich += 1
                mit_felder.add(f"{record_id}.{feld}")
            kategorie = kategorien.get((record_id, feld))
            if kategorie:
                zaehler = je_kategorie.setdefault(
                    kategorie, {"gesamt": 0, "vorher": 0, "nachher": 0})
                zaehler["gesamt"] += 1
                zaehler["vorher"] += 1 if vorher[feld]["wertgleich"] else 0
                zaehler["nachher"] += 1 if neu["wertgleich"] else 0

        record_berichte.append({
            "record_id": record_id,
            "outcome": context.get("outcome"),
            "tabelle": ziel.table_id,
            "fliesstext": {feld: [stelle.to_dict() for stelle in stellen]
                           for feld, stellen in sorted(text_stellen.items())},
            "fundstellen": {feld: wert_index[f"{record_id}.{feld}"]
                            for feld in alle_stellen},
            "vorher": vorher,
            "nachher": nachher,
        })

    bericht = {
        "selection": {
            "pfad": str(args.selection.relative_to(REPO))
                    if args.selection.is_absolute() else str(args.selection),
            "role": selection.get("role"),
            "n_tables": len(selection.get("tables") or []),
            "n_records": len(selection.get("record_ids") or []),
        },
        "bilanz": {
            "ohne_text": {"erreichbar": ohne_erreichbar,
                          "wertgleich": ohne_gleich},
            "mit_text": {"erreichbar": mit_erreichbar,
                         "wertgleich": mit_gleich},
            "neu_wertgleich": sorted(mit_felder - ohne_felder),
            # Ein Feld mit zwei gedruckten Zahlen ist wertgleich, aber nicht
            # eindeutig - das wird getrennt ausgewiesen.
            "neu_wertgleich_eindeutig": [
                feld for feld in sorted(mit_felder - ohne_felder)
                if len(wert_index.get(feld) or []) == 1],
            "neu_wertgleich_mehrdeutig": [
                feld for feld in sorted(mit_felder - ohne_felder)
                if len(wert_index.get(feld) or []) > 1],
            "verloren": sorted(set(verloren)),
            "arm_wechsel": arm_wechsel,
            "text_fakten": dict(sorted(regeln.items())),
            "konflikte": konflikte,
        },
        "felder_nur_aus_text": sorted(set(neu_erreichbar)),
        "je_kategorie": dict(sorted(je_kategorie.items())),
        "records": record_berichte,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bilanz = bericht["bilanz"]
    print(f"ohne Text {ohne_erreichbar} erreichbar / {ohne_gleich} wertgleich")
    print(f"mit Text  {mit_erreichbar} erreichbar / {mit_gleich} wertgleich")
    print("je Kategorie:", bericht["je_kategorie"])
    print("neu wertgleich:", len(bilanz["neu_wertgleich"]),
          "(eindeutig", len(bilanz["neu_wertgleich_eindeutig"]),
          "/ mehrdeutig", len(bilanz["neu_wertgleich_mehrdeutig"]), ")",
          "| verloren:", len(bilanz["verloren"]),
          "| Armwechsel:", len(arm_wechsel))
    print("Felder nur aus Text:", len(bericht["felder_nur_aus_text"]))
    print("Text-Fakten:", bilanz["text_fakten"])
    print("Konflikte (Textwert weicht von der Tabelle ab):", len(konflikte))
    for eintrag in konflikte[:10]:
        print("  ", eintrag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
