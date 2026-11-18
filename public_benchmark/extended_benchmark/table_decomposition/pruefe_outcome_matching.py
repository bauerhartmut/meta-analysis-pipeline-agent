#!/usr/bin/env python3
"""Prueft den Outcome-Zeilen-Matcher eines Splits - read-only.

Zwei Betriebsarten:

* mit ``--selection``: nur die ausgewaehlten Tabellen je Record (wie der
  Benchmark). Kategorien: ``trifft``, ``auswahl_verfehlt`` (eine andere Tabelle
  des Dokuments waere besser), ``zeile_nicht_erkannt``, ``dokument_ohne_zeile``.
* mit ``--all-records``: alle Records des Splits und alle Tabellen ihrer
  Dokumente. Kategorien: ``trifft``, ``zeile_nicht_erkannt``,
  ``dokument_ohne_zeile``.

Zusaetzlich wird gezaehlt, wie viele Gold-Gruppengroessen aus Kopfangaben
(``n = 434``) erwartbar sind. Das Werkzeug aendert keine Auswahl, keinen Lauf
und keine Goldannotation; es schreibt nur die angeforderte JSON-Datei.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parents[1]
sys.path.insert(0, str(REPO))

from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    reachable_cells,
    reachable_fields,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

DEFAULT_RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def context_of(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intervention": record["context"].get("intervention"),
        "comparator": record["context"].get("comparator"),
        "outcome": record["context"].get("outcome"),
        "outcome_type": record["context"].get("outcome_type"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=None)
    parser.add_argument("--all-records", action="store_true",
                        help="alle Records des Splits pruefen, nicht nur die Auswahl")
    parser.add_argument("--role", choices=("dev", "test"), default=None,
                        help="Split fuer --all-records (sonst Rolle der Auswahl)")
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    records = {record["record_id"]: record for record in read_jsonl(args.records)}
    role: Optional[str] = args.role

    if args.all_records:
        if role is None:
            if args.selection is None:
                parser.error("--all-records braucht --role oder --selection")
            role = json.loads(args.selection.read_text(encoding="utf-8")).get("role")
        selected: Dict[str, Optional[set]] = {}
        for record_id, record in records.items():
            if record["document"].get("split") != role:
                continue
            if not record["gold"]["cells"] or not record["document"].get("path"):
                continue
            selected[record_id] = None      # None = alle Tabellen des Dokuments
        selection_meta: Dict[str, Any] = {"role": role, "tables": None}
    else:
        if args.selection is None:
            parser.error("ohne --all-records ist --selection noetig")
        selection = json.loads(args.selection.read_text(encoding="utf-8"))
        role = role or selection.get("role")
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for entry in selection["tables"]:
            grouped.setdefault(entry["record_ids"][0], []).append(entry)
        selected = {record_id: {entry["table_id"] for entry in entries}
                    for record_id, entries in grouped.items()}
        selection_meta = {
            "role": selection.get("role"),
            "tables": selection.get("n_tables"),
            "records_sha256": selection.get("records_sha256"),
        }

    categories: Counter = Counter()
    per_record: List[Dict[str, Any]] = []
    facts_total = facts_bound = gold_group_via_fact = 0

    for record_id, chosen_ids in sorted(selected.items()):
        record = records[record_id]
        context = context_of(record)
        gold = {cell["field"] for cell in record["gold"]["cells"]}
        gold_group = {field for field in gold if field.endswith("_group_size")}

        path = REPO / record["document"]["path"]
        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_document(text, str(record["document"].get("id") or path.stem))
        for table in parsed.tables:
            enrich_table(table, context)
        transfer_arms_within_document(parsed.tables, context)
        transfer_arms_from_document(parsed.tables, context, text)

        def score(table) -> tuple:
            cells = reachable_cells(table, context)
            rows = {name for row_id, name in cells if row_id >= 0}
            facts = {name for row_id, name in cells if row_id < 0}
            return len(rows & gold), len(reachable_fields(table) & gold), facts

        if chosen_ids is None:
            chosen = list(parsed.tables)
            others: List[Any] = []
        else:
            chosen = [table for table in parsed.tables if table.table_id in chosen_ids]
            others = [table for table in parsed.tables if table.table_id not in chosen_ids]
        chosen_rows = max((score(table)[0] for table in chosen), default=0)
        chosen_any = max((score(table)[1] for table in chosen), default=0)
        other_rows = max((score(table)[0] for table in others), default=0)

        if chosen_rows:
            category = "trifft"
        elif other_rows:
            category = "auswahl_verfehlt"
        elif chosen_any:
            category = "zeile_nicht_erkannt"
        else:
            category = "dokument_ohne_zeile"
        categories[category] += 1

        for table in parsed.tables:
            facts_total += len(table.header_facts)
            facts_bound += len([fact for fact in table.header_facts if fact.get("arm")])
        fact_fields = {name for table in chosen
                       for row_id, name in reachable_cells(table, context) if row_id < 0}
        gold_group_via_fact += len(fact_fields & gold_group)

        per_record.append({
            "record_id": record_id,
            "outcome": context.get("outcome"),
            "category": category,
            "focus_rows": sum(len(table.focus_rows) for table in chosen),
            "gold_cells": len(record["gold"]["cells"]),
            "gold_group_size_cells": len(gold_group),
            "gold_group_size_via_fact": len(fact_fields & gold_group),
            "selected_tables": sorted(chosen_ids) if chosen_ids is not None else "alle",
            "better_tables": sorted(
                table.table_id for table in others if score(table)[0] > chosen_rows
            )[:4],
        })

    payload = {
        "selection": str(args.selection) if args.selection else "(alle Records)",
        "selection_role": selection_meta.get("role"),
        "selection_tables": selection_meta.get("tables"),
        "selection_sha256_records": selection_meta.get("records_sha256"),
        "n_records": len(per_record),
        "categories": dict(categories.most_common()),
        "header_facts_total": facts_total,
        "header_facts_with_arm": facts_bound,
        "gold_group_size_cells_reachable_via_fact": gold_group_via_fact,
        "records": per_record,
        "hinweise": [
            "Read-only: keine Auswahl, kein Lauf und keine Goldannotation geaendert.",
            "Kategorien sind Heuristiken auf Zeilenlabels, kein Modellurteil.",
            "header_facts zaehlen alle Tabellen des Dokuments, nicht nur die Auswahl.",
        ],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(f"geschrieben: {args.out}")
    print(json.dumps({key: payload[key] for key in (
        "selection_role", "selection_tables", "n_records", "categories",
        "header_facts_total", "header_facts_with_arm",
        "gold_group_size_cells_reachable_via_fact")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
