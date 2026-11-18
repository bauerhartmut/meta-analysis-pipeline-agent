"""Diagnose: warum sind Goldzellen ueber die Auswahl nicht erreichbar?

Read-only. Klassifiziert jede nicht erreichbare Goldzelle eines Records:

* ``feld_fehlt_im_dokument`` - keine Tabelle des Dokuments hat eine Spalte mit
  dieser Rolle (z. B. Gold nennt SD, die Tabelle nur Mittelwerte).
* ``spalte_nicht_ausgewaehlt`` - eine nicht ausgewaehlte Tabelle des Dokuments
  traegt die Rolle, teils sogar mit passendem Armnamen im Kopf.
* ``arm_nicht_gebunden`` - eine ausgewaehlte Tabelle traegt die Rolle, aber der
  Arm liess sich aus dem Kopf nicht belegen (Spalte ohne Feld).
* ``outcome_zeile_nicht_erkannt`` - keine ausgewaehlte Tabelle hat eine Zeile,
  deren Zeilenlabel-Pfad das Outcome nennt; ohne sie ist kein Zellwert
  erwartbar (die Zelle bleibt trotzdem als nicht erreichbar gezaehlt).

Die Zuordnung ist eine Heuristik auf Header-Text, kein Modellurteil; sie dient
nur der Priorisierung der naechsten Aenderung.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    outcome_rows,
    reachable_cells,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

ROLE_BY_FIELD = (
    ("_group_size", "n"),
    ("_standard_deviation", "sd"),
    ("_mean", "mean"),
    ("_events", "events"),
    ("_p_value", "p"),
)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def field_role(field_name: str) -> str:
    for suffix, role in ROLE_BY_FIELD:
        if field_name.endswith(suffix):
            return role
    return "unbekannt"


def field_arm(field_name: str) -> Optional[str]:
    if field_name.startswith("intervention"):
        return "intervention"
    if field_name.startswith("comparator"):
        return "comparator"
    return None


def context_of(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intervention": record["context"].get("intervention"),
        "comparator": record["context"].get("comparator"),
        "outcome": record["context"].get("outcome"),
        "outcome_type": record["context"].get("outcome_type"),
        "timepoint_target": (record.get("timepoint") or {}).get("target"),
    }


def header_mentions_arm(header: str, arm_name: str) -> bool:
    if not header or not arm_name:
        return False
    head = header.lower()
    tokens = [t for t in arm_name.lower().replace("/", " ").split() if len(t) > 2]
    return bool(tokens) and any(token in head for token in tokens)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--records", required=True)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))
    records = {r["record_id"]: r for r in read_jsonl(Path(args.records))}

    selected: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in selection["tables"]:
        selected[entry["record_ids"][0]].append(entry)

    reasons: Counter = Counter()
    per_role: Counter = Counter()
    cross: Counter = Counter()
    per_arm: Counter = Counter()
    examples: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    document_tables: Dict[str, List[Any]] = {}
    documents: Dict[str, str] = {}

    for record_id, entries in sorted(selected.items()):
        record = records.get(record_id)
        if record is None:
            continue
        doc_id = str(record["document"].get("id"))
        if doc_id not in documents:
            path = REPO / entries[0]["document_path"]
            documents[doc_id] = path.read_text(encoding="utf-8", errors="replace")
            document_tables[doc_id] = parse_document(documents[doc_id], doc_id).tables
        context = context_of(record)

        selected_ids = {entry["table_id"] for entry in entries}
        chosen = [table for table in document_tables[doc_id] if table.table_id in selected_ids]
        others = [table for table in document_tables[doc_id] if table.table_id not in selected_ids]
        for table in document_tables[doc_id]:
            enrich_table(table, context)
        transfer_arms_within_document(document_tables[doc_id], context)
        transfer_arms_from_document(document_tables[doc_id], context, documents[doc_id])

        focus = {table.table_id: outcome_rows(table, str(context.get("outcome") or ""))
                 for table in chosen}
        reachable = {name for table in chosen
                     for _row_id, name in reachable_cells(table, context)}
        for cell in record["gold"]["cells"]:
            if cell["field"] in reachable:
                continue
            role = field_role(cell["field"])
            arm = field_arm(cell["field"])
            per_role[role] += 1
            per_arm[arm or "kein_arm"] += 1
            arm_name = (record["context"].get("intervention") if arm == "intervention"
                        else record["context"].get("comparator") if arm == "comparator" else "")

            matching_chosen = [
                column for table in chosen for column in table.columns
                if column.role == role
            ]
            matching_others = [
                (table.table_id, column) for table in others for column in table.columns
                if column.role == role
            ]
            mentioned_others = [
                (table_id, column) for table_id, column in matching_others
                if header_mentions_arm(column.header, str(arm_name or ""))
            ]
            if not any(focus.values()):
                reason = "outcome_zeile_nicht_erkannt"
            elif matching_chosen:
                reason = "arm_nicht_gebunden"
                if not any(header_mentions_arm(c.header, str(arm_name or ""))
                           for c in matching_chosen):
                    reason = "arm_nicht_gebunden_ohne_namensrest"
            elif mentioned_others:
                reason = "spalte_nicht_ausgewaehlt_mit_arm"
            elif matching_others:
                reason = "spalte_nicht_ausgewaehlt"
            else:
                reason = "feld_fehlt_im_dokument"
            reasons[reason] += 1
            cross[f"{role}/{reason}"] += 1
            if len(examples[reason]) < 3:
                examples[reason].append(
                    {
                        "record_id": record_id,
                        "field": cell["field"],
                        "arm_name": arm_name,
                        "selected": sorted(selected_ids),
                        "candidates": sorted({t for t, _ in matching_others})[:4],
                        "mentioned": sorted({t for t, _ in mentioned_others})[:4],
                    }
                )

    total_unreachable = sum(reasons.values())
    result = {
        "selection": str(args.selection),
        "records": len(selected),
        "unreachable_cells": total_unreachable,
        "reasons": dict(reasons.most_common()),
        "per_role": dict(per_role.most_common()),
        "per_arm": dict(per_arm.most_common()),
        "kreuz_rolle_grund": dict(cross.most_common()),
        "examples": {key: value for key, value in examples.items()},
    }
    print(json.dumps({k: result[k] for k in ("records", "unreachable_cells", "reasons",
                                             "per_role", "per_arm", "kreuz_rolle_grund")},
                     ensure_ascii=False, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
