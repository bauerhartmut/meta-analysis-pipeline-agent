"""Offline-Messung: Outcome-Zeile aus der Zellform.

Fragt drei Dinge:

1. **Entscheidung**: was ``consider_outcome_row_candidate`` je Tabelle hergibt
   (``original:treffer``, ``original:mehrdeutig``, ``vorschlag:r<id>``,
   ``original:kein_kandidat``) - und ob dadurch erwartbare Zellen entstehen
   (sie entstehen nicht: der Kandidat wird nicht gesetzt).
2. **Zwangslaeufe**: fuer ``PMC3278655:T2`` jede Datenzeile einzeln als
   Outcome-Zeile gesetzt, mit Abgleich gegen das Gold - Feld erreicht, Wert
   woertlich gedruckt.
3. **Gold-Abgleich ohne Zwang**: welche Goldzellen heute erreichbar sind.

Read-only: aendert weder Gold noch eingefrorene Eingaben noch Messartefakte.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_outcome_zeile.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import copy
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

from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.model import ROLE_N  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    _messspalten,
    _zeile_vollstaendig,
    corroborate_outcome_row_from_document,
    enrich_table,
    field_for,
    outcome_rows,
    reachable_cells,
    reachable_fields,
    row_fields,
)

# Werteabgleich wie in der Spaltenzeitpunkt-Messung (Dezimalkomma, Unicode-Minus,
# Verbundzelle, Null nur als Ganzzahl).
from diagnose_spaltenzeitpunkte import _zelltreffer  # noqa: E402

ZWANG = ("PMC3278655:T2",)


def _gold_cells(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    gold = record.get("gold") or {}
    return list(gold.get("cells") or [])


def _wert_zeilen(table, soll: float) -> List[str]:
    """Zeilen, in denen ``soll`` woertlich gedruckt steht."""
    treffer = []
    for row in table.rows:
        for col_id in sorted(row.cells):
            zelle = row.cells[col_id]
            if _zelltreffer((zelle.text or ""), soll):
                treffer.append(
                    f"r{row.row_id} {row.label_path[-1] if row.label_path else row.label}"
                    f"/c{col_id}"
                )
    return treffer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    cache: Dict[str, Any] = {}
    texte: Dict[str, str] = {}
    entscheidungen: Counter = Counter()
    tabellen: List[Dict[str, Any]] = []
    zwang: List[Dict[str, Any]] = []
    for eintrag in selection["tables"]:
        record_id = eintrag["record_ids"][0]
        record = records.get(record_id)
        if record is None:
            continue
        doc_id = str(record["document"].get("id"))
        if doc_id not in cache:
            text = (rb.REPO / eintrag["document_path"]).read_text(
                encoding="utf-8", errors="replace")
            texte[doc_id] = text
            cache[doc_id] = parse_document(text, doc_id)
        parsed = cache[doc_id]
        context = rb.context_of(record)
        table = next((t for t in parsed.tables
                      if t.table_id == eintrag["table_id"]), None)
        if table is None:
            continue
        table = copy.deepcopy(table)
        enrich_table(table, context)
        # p-Wert-Korroboration (setzt die Zeile nur bei genau einem Treffer und
        # bestandenem Wertabgleich).
        corroborate_outcome_row_from_document([table], context, texte[doc_id])
        entscheidungen[table.outcome_row_decision.split(":")[0] + ":"
                       + table.outcome_row_decision.split(":")[1]] += 1
        spalten = _messspalten(table)
        voll = [row.row_id for row in table.rows
                if not row.group_label and _zeile_vollstaendig(table, row, spalten)]
        zellen = {name for _row_id, name in reachable_cells(table, context)}
        gold = _gold_cells(record)
        eintrag_out = {
            "table_id": table.table_id,
            "record_id": record_id,
            "outcome": str(context.get("outcome") or ""),
            "outcome_zeilen": outcome_rows(table, str(context.get("outcome") or "")),
            "entscheidung": table.outcome_row_decision,
            "focus_rows": list(table.focus_rows),
            "messspalten": [f"c{c.col_id}:{c.field}" for c in spalten],
            "vollstaendige_zeilen": voll,
            "erreichbare_felder": sorted(zellen),
            "gold_felder_erreichbar": sum(1 for c in gold if c["field"] in zellen),
            "gold_felder": len(gold),
        }
        tabellen.append(eintrag_out)
        if table.table_id not in ZWANG:
            continue
        # Zwangslaeufe: jede Datenzeile als Outcome-Zeile, Abgleich gegen Gold.
        for row in table.rows:
            probe = copy.deepcopy(table)
            probe.focus_rows = [row.row_id]
            felder = {name for _row_id, name in _zellen_mit_zeile(probe, row)}
            gold_wert = sum(
                1 for c in gold if _zelltreffer_in_zeile(row, c["value"], spalten)
            )
            zwang.append({
                "table_id": table.table_id,
                "record_id": record_id,
                "row_id": row.row_id,
                "label": row.label_path[-1] if row.label_path else row.label,
                "felder": sorted(felder),
                "gold_felder_erreichbar": sum(1 for c in gold if c["field"] in felder),
                "gold_werte_in_zeile": gold_wert,
                "gold_werte_gedruckt": {
                    f"{c['field']}={c['raw']}": _wert_zeilen(table, c["value"])
                    for c in gold if c["field"] in felder
                },
            })

    bericht = {
        "auswahl": len(selection["tables"]),
        "entscheidungen": dict(sorted(entscheidungen.items())),
        "tabellen": tabellen,
        "zwangslaeufe": zwang,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Entscheidungen:", bericht["entscheidungen"])
    for eintrag in tabellen:
        if eintrag["entscheidung"] != "original:kein_kandidat":
            print(f"  {eintrag['table_id']} {eintrag['record_id']}: "
                  f"{eintrag['entscheidung']} vollstaendig={eintrag['vollstaendige_zeilen']} "
                  f"gold {eintrag['gold_felder_erreichbar']}/{eintrag['gold_felder']}")
    for eintrag in zwang:
        if eintrag["row_id"] == 0 or eintrag["gold_werte_in_zeile"]:
            print(f"  Zwang {eintrag['table_id']} {eintrag['record_id']} r{eintrag['row_id']} "
                  f"{eintrag['label'][:38]!r}: felder={eintrag['felder']} "
                  f"gold_felder={eintrag['gold_felder_erreichbar']} "
                  f"gold_werte={eintrag['gold_werte_in_zeile']}")
    return 0


def _zellen_mit_zeile(table, row) -> set:
    """Erwartbare Zellen, wenn genau diese Zeile die Outcome-Zeile waere.

    Spiegelt ``semantics.reachable_cells`` fuer den Zeilenzweig: feste
    Kopfangaben, die Spaltenfelder dieser Zeile und die Felder aus ihrem
    Zeilenlabel.
    """
    cells = set()
    for fact in table.header_facts:
        arm = fact.get("arm")
        field = field_for(ROLE_N, arm if isinstance(arm, str) else None)
        if field:
            cells.add((-1, field))
    cells |= {(row.row_id, name) for name in reachable_fields(table)}
    cells |= {(row.row_id, name) for name in row_fields(table, row)}
    return cells


def _zelltreffer_in_zeile(row, soll: float, spalten) -> bool:
    """Steht der Goldwert in einer Messspalte dieser Zeile?"""
    for column in spalten:
        zelle = row.cells.get(column.col_id)
        if zelle is not None and _zelltreffer((zelle.text or ""), soll):
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
