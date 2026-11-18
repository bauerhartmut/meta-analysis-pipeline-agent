#!/usr/bin/env python3
"""Geschichtete, eingefrorene Tabellenauswahl fuer den Zerlegungs-Benchmark.

Aus den Yun-699-Records werden Tabellen nach Schwierigkeitsgrad ausgewaehlt:
einfach, mehrere Arme, mehrere Zeitpunkte, mehrstufige Kopfzeilen, Fussnoten und
komplexe PDF-Tabellen. Die Auswahl ist deterministisch (Hash je Tabellen-ID),
wird mit Quelle und SHA-256 eingefroren und aendert keine Goldannotation.

Ohne ``--write`` passiert nichts ausser der Anzeige.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parents[1]
sys.path.insert(0, str(REPO))

from research_agent.table_decomposition.complexity import assess  # noqa: E402
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    reachable_fields,
    transfer_arms_within_document,
)

DEFAULT_RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"
ANALYSIS = BENCH / "analysis"

STRATA_ORDER = (
    "einfach",
    "mittel",
    "komplex",
    "sehr_komplex",
    "mehrarm",
    "mehrzeitpunkt",
    "mehrstufiger_kopf",
    "fussnoten",
    "komplexe_pdf",
    "ohne_armzuordnung",
)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strata_for(table, complexity) -> List[str]:
    features = complexity.features
    strata = {complexity.class_label}
    if features["n_header_levels"] >= 2:
        strata.add("mehrstufiger_kopf")
    if features["n_column_groups"] >= 3:
        strata.add("mehrarm")
    if features["has_timepoints"]:
        strata.add("mehrzeitpunkt")
    if features["n_footnotes"] > 0:
        strata.add("fussnoten")
    if features["n_irregular_rows"] > 0 or features["n_columns"] > 10:
        strata.add("komplexe_pdf")
    if features["n_target_columns"] == 0:
        strata.add("ohne_armzuordnung")
    return [name for name in STRATA_ORDER if name in strata]


def context_of(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intervention": record["context"].get("intervention"),
        "comparator": record["context"].get("comparator"),
        "outcome": record["context"].get("outcome"),
        "outcome_type": record["context"].get("outcome_type"),
        "timepoint_target": (record.get("timepoint") or {}).get("target"),
    }


def build_candidates(records: Sequence[Dict[str, Any]], role: str,
                     require_bound: bool = True,
                     assume_order: bool = False) -> List[Dict[str, Any]]:
    """Kandidaten je (Record, Tabelle) im gewaehlten Split.

    Eine Extraktionsaufgabe ist ein Record auf einer Tabelle: Armbezug und
    Goldzellen gehoeren zum Record, die Struktur zur Tabelle. Die Auswahl
    verwendet keine Goldwerte; nur die Zahl der Spalten mit belegtem Zielfeld
    (aus der Kopfzeile abgeleitet) entscheidet mit.
    """
    candidates: List[Dict[str, Any]] = []
    cache: Dict[str, Any] = {}
    for record in records:
        split = record["document"].get("split")
        if role == "dev" and split != "dev":
            continue
        if role == "test" and split != "test":
            continue
        if not record["gold"]["cells"]:
            continue
        path = record["document"].get("path") or ""
        if not path:
            continue
        full = REPO / path
        if not full.exists():
            print(f"FEHLT: {path}", file=sys.stderr)
            continue
        if path not in cache:
            text = full.read_text(encoding="utf-8", errors="replace")
            doc_id = str(record["document"].get("id") or full.stem)
            cache[path] = (parse_document(text, doc_id), doc_id)
        parsed, doc_id = cache[path]
        context = context_of(record)
        tables = parsed.tables or []
        if not tables:
            candidates.append({
                "candidate_id": f"{record['record_id']}|keine_tabelle",
                "table_id": f"{doc_id}:keine_tabelle",
                "doc_id": doc_id,
                "document_path": path,
                "record_ids": [record["record_id"]],
                "caption": "",
                "parser": "",
                "rows": 0,
                "columns": 0,
                "complexity": {"score": 0.0, "class": "einfach",
                               "features": {}, "drivers": []},
                "strata": ["keine_tabelle"],
                "n_target_columns": 0,
                "gold_cells": len(record["gold"]["cells"]),
                "gold_reachable": 0,
            })
            continue
        for table in tables:
            enrich_table(table, context, assume_order=assume_order)
        transfer_arms_within_document(tables, context)
        for table in tables:
            complexity = assess(table)
            table.complexity = complexity.to_dict()
            fields = reachable_fields(table)
            reachable = sum(1 for cell in record["gold"]["cells"] if cell["field"] in fields)
            if require_bound and reachable == 0:
                continue
            candidates.append({
                "candidate_id": f"{record['record_id']}|{table.table_id}",
                "table_id": table.table_id,
                "doc_id": doc_id,
                "document_path": path,
                "record_ids": [record["record_id"]],
                "caption": table.caption[:200],
                "parser": table.parser,
                "rows": len(table.rows),
                "columns": len(table.columns),
                "complexity": complexity.to_dict(),
                "strata": strata_for(table, complexity),
                "n_target_columns": complexity.features["n_target_columns"],
                "fields": sorted(fields),
                "gold_cells": len(record["gold"]["cells"]),
                "gold_reachable": reachable,
            })
    return candidates


def select(candidates: Sequence[Dict[str, Any]], target: int,
           max_per_document: int = 2, max_per_record: int = 3) -> List[Dict[str, Any]]:
    """Round-Robin ueber die Schichten, deterministisch nach Hash."""
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        for stratum in candidate["strata"]:
            buckets.setdefault(stratum, []).append(candidate)
    for stratum, entries in buckets.items():
        # Erst die Tabellen mit den meisten belegten Zielspalten (Struktur, kein
        # Goldwert), dann deterministisch nach Hash.
        entries.sort(key=lambda item: (
            -int(item.get("n_target_columns") or 0),
            hashlib.sha256(f"{stratum}:{item['candidate_id']}".encode("utf-8")).hexdigest(),
        ))

    chosen: List[Dict[str, Any]] = []
    seen: set = set()
    per_document: Dict[str, int] = {}
    per_record: Dict[str, int] = {}
    covered: Dict[str, set] = {}

    def take(stratum: str) -> bool:
        for entry in buckets.get(stratum, []):
            if entry["candidate_id"] in seen:
                continue
            document = entry["table_id"].split(":")[0]
            record_id = entry["record_ids"][0]
            if max_per_document and per_document.get(document, 0) >= max_per_document:
                continue
            if max_per_record and per_record.get(record_id, 0) >= max_per_record:
                continue
            # Kein Platz fuer eine Tabelle ohne neuen Feldgewinn: die Auswahl
            # soll Felder abdecken, nicht Tabellen sammeln.
            new_fields = set(entry.get("fields") or []) - covered.get(record_id, set())
            if per_record.get(record_id, 0) and not new_fields:
                continue
            seen.add(entry["candidate_id"])
            per_document[document] = per_document.get(document, 0) + 1
            per_record[record_id] = per_record.get(record_id, 0) + 1
            covered.setdefault(record_id, set()).update(entry.get("fields") or [])
            chosen.append(entry)
            return True
        return False

    for stratum in STRATA_ORDER:            # jede Schicht mindestens einmal
        if len(chosen) >= target:
            break
        take(stratum)
    while len(chosen) < target:
        progressed = False
        for stratum in STRATA_ORDER:
            if len(chosen) >= target:
                break
            progressed = take(stratum) or progressed
        if not progressed:
            break
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--role", choices=("dev", "test"), default="test",
                        help="dev fuer Entwicklung, test fuer die eingefrorene Messung")
    parser.add_argument("--target", type=int, default=60,
                        help="Zielzahl Tabellen (Auftrag: 50-100)")
    parser.add_argument("--max-per-document", type=int, default=2,
                        help="hoechstens so viele Tabellen je Dokument (Streuung)")
    parser.add_argument("--max-per-record", type=int, default=6,
                        help="hoechstens so viele Tabellen je Record")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--include-unbound", action="store_true",
                        help="auch Tabellen ohne erreichbare Goldzelle aufnehmen")
    parser.add_argument("--arm-order-fallback", action="store_true",
                        help="Arm aus der Leserichtung annehmen (markiert), wie im Lauf")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    records = read_jsonl(args.records)
    candidates = build_candidates(records, args.role,
                                  require_bound=not args.include_unbound,
                                  assume_order=args.arm_order_fallback)
    chosen = select(candidates, args.target, args.max_per_document, args.max_per_record)

    stratum_counts: Dict[str, int] = {}
    for entry in chosen:
        for stratum in entry["strata"]:
            stratum_counts[stratum] = stratum_counts.get(stratum, 0) + 1

    payload = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "role": args.role,
        "target": args.target,
        "frozen": True,
        "records_file": str(args.records.relative_to(REPO)) if args.records.is_absolute() else str(args.records),
        "records_sha256": sha256_of(args.records),
        "selection_method": (
            "Round-Robin ueber Schwierigkeitsschichten, Reihenfolge je Schicht "
            "durch sha256(Schicht:Tabellen-ID); keine Goldwerte in der Auswahl."
        ),
        "n_candidates": len(candidates),
        "n_tables": len(chosen),
        "require_bound": not args.include_unbound,
        "arm_order_fallback": args.arm_order_fallback,
        "gold_reachable_total": sum(entry.get("gold_reachable", 0) for entry in chosen),
        "strata_order": list(STRATA_ORDER),
        "strata_counts": stratum_counts,
        "record_ids": sorted({rid for entry in chosen for rid in entry["record_ids"]}),
        "n_records": len({rid for entry in chosen for rid in entry["record_ids"]}),
        "n_documents": len({entry["table_id"].split(":")[0] for entry in chosen}),
        "max_per_document": args.max_per_document,
        "max_per_record": args.max_per_record,
        "tables": chosen,
    }
    print(f"{args.role}: {len(chosen)} von {len(candidates)} Tabellenkandidaten")
    for stratum in STRATA_ORDER:
        if stratum in stratum_counts:
            print(f"  {stratum:<20} {stratum_counts[stratum]}")
    if args.out:
        target_path = args.out
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        target_path = ANALYSIS / f"table_decomposition_{stamp}" / f"selection_{args.role}.json"
    if args.write:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"geschrieben: {target_path}")
    else:
        print("(Trockenlauf; mit --write schreiben)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
