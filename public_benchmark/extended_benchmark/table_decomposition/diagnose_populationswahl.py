"""Offline-Messung Sprint 46: Tabellenwahl aus dem Dokument.

Frage: Werden die 15 `population_mismatch`-Felder wertgleich, wenn die Tabelle
nicht aus der eingefrorenen Auswahl, sondern aus dem Dokument gewaehlt wird -
und bleibt die Armzuordnung dabei unveraendert?

Regel (`research_agent.table_decomposition.tabellenwahl`): traegt die aktuelle
Tabelle eine Zeile zum Outcome, bleibt es bei ihr; sonst gewinnt die Tabelle
mit den meisten Outcome-Zeilen, die keine Baseline-Tabelle ist. Kein Goldwert
steuert die Wahl, kein Arm wird umgehaengt.

Read-only: Gold und eingefrorene Eingaben werden nur gelesen.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_populationswahl.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
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

from research_agent.table_decomposition import provenienz as pv  # noqa: E402
from research_agent.table_decomposition import tabellenwahl as tw  # noqa: E402
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    outcome_rows,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

from diagnose_spaltenzeitpunkte import _zelltreffer  # noqa: E402

SPRINT45 = (BENCH / "analysis" / "table_decomposition_20261118"
            / "provenienz_20261118" / "messung.json")


def _gold(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((record.get("gold") or {}).get("cells") or [])


def _gedruckt(stelle: pv.Provenienz, wert: float) -> bool:
    if stelle.quelle == pv.QUELLE_KOPF:
        return stelle.wert == wert
    return _zelltreffer(stelle.text, wert)


def _dokument(text: str, doc_id: str, context: Dict[str, Any]) -> List[Any]:
    doc = parse_document(text, doc_id)
    for table in doc.tables:
        enrich_table(table, context)
    transfer_arms_within_document(doc.tables, context)
    transfer_arms_from_document(doc.tables, context, text)
    return doc.tables


def _lage(felder: Sequence[Dict[str, Any]], stellen: Dict[str, List[pv.Provenienz]]
          ) -> Dict[str, Any]:
    """Je Goldfeld: erreichbar, wertgleich, Arme der Fundstellen."""
    treffer = {}
    for gold_cell in felder:
        feld = gold_cell["field"]
        orte = stellen.get(feld) or []
        if not orte:
            treffer[feld] = {"erreichbar": False, "wertgleich": False,
                             "arme": [], "art": ""}
            continue
        treffer[feld] = {
            "erreichbar": True,
            "wertgleich": any(_gedruckt(s, gold_cell["value"]) for s in orte),
            "arme": sorted({s.arm for s in orte if s.arm}),
            "art": pv.feld_art(orte),
        }
    return treffer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    kategorien = {}
    if SPRINT45.exists():
        alt = json.loads(SPRINT45.read_text(encoding="utf-8"))
        kategorien = {(f["record_id"], f["feld"]): f["kategorie"]
                      for f in alt.get("nicht_wertgleich") or []}

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    record_berichte: List[Dict[str, Any]] = []
    vorher_erreichbar = vorher_gleich = 0
    nachher_erreichbar = nachher_gleich = 0
    neu_gleich: List[str] = []
    neu_ungleich: List[str] = []
    arm_wechsel: List[Dict[str, Any]] = []
    wechsel = 0
    gruende: Counter = Counter()
    je_kategorie: Dict[str, Dict[str, int]] = {}

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
        nachher_tabellen = [ziel] if wechselt else list(tables)
        if wechselt:
            wechsel += 1

        vorher = pv.feld_stellen(tables, context)
        nachher = pv.feld_stellen(nachher_tabellen, context)
        gold = _gold(record)
        alt = _lage(gold, vorher)
        neu = _lage(gold, nachher)

        for feld, lage in alt.items():
            if not lage["erreichbar"]:
                continue
            vorher_erreichbar += 1
            vorher_gleich += 1 if lage["wertgleich"] else 0
            if not neu[feld]["erreichbar"]:
                continue
            nachher_erreichbar += 1
            nachher_gleich += 1 if neu[feld]["wertgleich"] else 0
            if neu[feld]["wertgleich"] and not lage["wertgleich"]:
                neu_gleich.append(f"{record_id}.{feld}")
            if lage["wertgleich"] and not neu[feld]["wertgleich"]:
                neu_ungleich.append(f"{record_id}.{feld}")
            if lage["arme"] and neu[feld]["arme"] != lage["arme"]:
                arm_wechsel.append({
                    "record_id": record_id, "feld": feld,
                    "vorher": lage["arme"], "nachher": neu[feld]["arme"],
                })
            kategorie = kategorien.get((record_id, feld))
            if kategorie:
                zaehler = je_kategorie.setdefault(
                    kategorie, {"gesamt": 0, "vorher": 0, "nachher": 0})
                zaehler["gesamt"] += 1
                zaehler["vorher"] += 1 if lage["wertgleich"] else 0
                zaehler["nachher"] += 1 if neu[feld]["wertgleich"] else 0

        record_berichte.append({
            "record_id": record_id,
            "outcome": context.get("outcome"),
            "aktuelle_tabellen": [t.table_id for t in tables],
            "gewaehlte_tabelle": ziel.table_id,
            "grund": wahl.grund if wahl else "keine_wahl",
            "wechsel": bool(wahl and wahl.wechsel),
            "outcome_zeilen_gewaehlt": len(outcome_rows(ziel, context.get("outcome") or "")),
            "baseline_gewaehlt": tw.ist_baseline(ziel),
            "felder": {feld: {"vorher": alt[feld], "nachher": neu[feld]}
                       for feld in alt},
        })

    bericht = {
        "bilanz": {
            "vorher": {"erreichbar": vorher_erreichbar, "wertgleich": vorher_gleich},
            "nachher": {"erreichbar": nachher_erreichbar,
                        "wertgleich": nachher_gleich},
            "neu_wertgleich": sorted(neu_gleich),
            "neu_nicht_wertgleich": sorted(neu_ungleich),
            "arm_wechsel": arm_wechsel,
        },
        "tabellenwechsel": wechsel,
        "gruende": dict(sorted(gruende.items())),
        "je_kategorie": dict(sorted(je_kategorie.items())),
        "records": record_berichte,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"vorher {vorher_erreichbar} erreichbar / {vorher_gleich} wertgleich")
    print(f"nachher {nachher_erreichbar} erreichbar / {nachher_gleich} wertgleich")
    print(f"Tabellenwechsel {wechsel}, Gruende {bericht['gruende']}")
    print("je Kategorie:", bericht["je_kategorie"])
    print("neu wertgleich:", len(neu_gleich), "neu nicht wertgleich:", len(neu_ungleich))
    print("Armwechsel:", arm_wechsel)
    for rec in record_berichte:
        if rec["wechsel"]:
            print(f"  {rec['record_id']} {rec['aktuelle_tabellen']} -> "
                  f"{rec['gewaehlte_tabelle']} ({rec['outcome']}) "
                  f"baseline={rec['baseline_gewaehlt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
