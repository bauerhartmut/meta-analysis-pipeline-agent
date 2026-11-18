"""Vergleicht Kopfband-Geometrie vor und nach der ordinalen Neuordnung.

Read-only Diagnose fuer eine Auswahl (Standard: eingefrorene Testauswahl).
Je Tabelle werden Originalbaender, Kandidatenbaender, Ueberlappungen, die
Felder vor/nach der Neuordnung und die Goldfelder des Records ausgewiesen.

Aufruf:
    python public_benchmark/extended_benchmark/table_decomposition/diagnose_kopfbaender.py \
        --out <pfad.json> [--table PMC4319071:T2]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BENCH.parents[1]))

from research_agent.table_decomposition import parser as parser_module  # noqa: E402
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    reachable_cells,
    transfer_arms_from_document,
    transfer_arms_within_document,
)
from run_benchmark import ANALYSIS, DEFAULT_RECORDS, context_of, load_records  # noqa: E402

DEFAULT_SELECTION = ANALYSIS / "table_decomposition_20261118" / "selection_test.json"


def _bands(table) -> List[Dict[str, Any]]:
    return [
        {
            "level": band.level,
            "text": band.text,
            "col_start": band.col_start,
            "col_end": band.col_end,
            "basis": band.basis,
        }
        for band in sorted(table.header_bands, key=lambda b: (b.level, b.col_start))
    ]


def _overlaps(table) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for level in sorted({band.level for band in table.header_bands}):
        bands = sorted(
            (band for band in table.header_bands if band.level == level),
            key=lambda band: band.col_start,
        )
        for left, right in zip(bands, bands[1:]):
            if right.col_start <= left.col_end:
                found.append(
                    {
                        "level": level,
                        "links": left.text,
                        "rechts": right.text,
                        "links_spanne": [left.col_start, left.col_end],
                        "rechts_spanne": [right.col_start, right.col_end],
                    }
                )
    return found


def _fields(table, context) -> List[str]:
    return sorted({name for _row_id, name in reachable_cells(table, context)})





def diagnose(selection: Dict[str, Any], records: Dict[str, Dict[str, Any]],
             only: str = "") -> Dict[str, Any]:
    per_table: Dict[str, Any] = {}
    for record_id, entries in sorted(group_records(selection).items()):
        record = records.get(record_id)
        if record is None or not record["gold"]["cells"]:
            continue
        context = context_of(record)
        text = Path(record["document"]["path"]).read_text(encoding="utf-8",
                                                          errors="replace")
        doc_id = str(record["document"]["id"])
        parsed = parse_document(text, doc_id)
        for entry in entries:
            table_id = entry["table_id"]
            if only and table_id != only:
                continue
            base = next((t for t in parsed.tables if t.table_id == table_id), None)
            if base is None:
                continue
            # Der Parser liefert die gedruckte Geometrie; der Kandidat wird
            # hier bewusst ohne Validierung gesetzt, damit die Diagnose zeigt,
            # was die ordinale Zuordnung allein anrichten wuerde.
            alt = copy.deepcopy(base)
            candidates = parser_module._header_band_candidates(alt)
            if candidates:
                alt.apply_header_bands(candidates[0][1])
            for table, ctx in ((base, context), (alt, context)):
                enrich_table(table, ctx)
                transfer_arms_within_document([table], ctx)
                transfer_arms_from_document([table], ctx, text)
            gold = sorted({cell["field"] for cell in record["gold"]["cells"]})
            before = _fields(base, context)
            after = _fields(alt, context)
            per_table[table_id] = {
                "record_ids": list(entry.get("record_ids") or []),
                "gold_felder": gold,
                "baender_original": _bands(base),
                "baender_kandidat": _bands(alt),
                "ueberlappungen_kandidat": _overlaps(alt),
                "felder_original": before,
                "felder_kandidat": after,
                "gold_original": sorted(set(before) & set(gold)),
                "gold_kandidat": sorted(set(after) & set(gold)),
                "verloren": sorted(set(before) - set(after)),
                "gewonnen": sorted(set(after) - set(before)),
                "spalten_original": {
                    str(column.col_id): {
                        "pfad": list(column.header_path),
                        "rolle": column.role,
                        "arm": column.arm,
                        "feld": column.field,
                    }
                    for column in base.columns
                },
                "spalten_kandidat": {
                    str(column.col_id): {
                        "pfad": list(column.header_path),
                        "rolle": column.role,
                        "arm": column.arm,
                        "feld": column.field,
                    }
                    for column in alt.columns
                },
            }
    return {"mode": "diagnose", "selection": str(DEFAULT_SELECTION),
            "tabellen": per_table}


def group_records(selection: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for entry in selection["tables"]:
        for record_id in entry["record_ids"]:
            grouped.setdefault(record_id, []).append(entry)
    return grouped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--table", default="", help="nur diese Tabelle pruefen")
    args = ap.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = load_records(DEFAULT_RECORDS)
    payload = diagnose(selection, records, only=args.table)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    changed = {
        table_id: data
        for table_id, data in payload["tabellen"].items()
        if data["verloren"] or data["gewonnen"] or data["ueberlappungen_kandidat"]
    }
    print(f"Tabellen geprueft: {len(payload['tabellen'])} | abweichend: {len(changed)}")
    for table_id, data in sorted(changed.items()):
        print(f"  {table_id}: verloren={data['verloren']} gewonnen={data['gewonnen']} "
              f"ueberlappungen={len(data['ueberlappungen_kandidat'])}")
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
