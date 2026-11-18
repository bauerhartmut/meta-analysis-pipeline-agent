"""Gegenprobe-Auswahl: dieselbe Regel auf unbenutzten Records.

Die Tabellenwahl entstand auf der eingefrorenen Test-Auswahl (59 Records,
31 Dokumente). Diese Gegenprobe baut mit demselben deterministischen Verfahren
(`select_tables.build_candidates` + `select`) eine Auswahl aus Records, deren
**Dokument** in der Test-Auswahl nicht vorkommt. Damit begegnet die Regel
Tabellen, die sie beim Bau nicht gesehen hat.

Die Auswahl ist kein Gold-Blick: `require_bound` zaehlt nur, ob ein Feldname
im Kopf erreichbar ist (wie in der eingefrorenen Auswahl), keine Goldwerte.
Das Ergebnis wird nicht in die eingefrorene Test-Auswahl geschrieben.

Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/pruefe_tabellenwahl_gegenprobe.py \
        --out public_benchmark/extended_benchmark/analysis/.../selection_gegenprobe.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
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
from select_tables import STRATA_ORDER, build_candidates, select, sha256_of  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--target", type=int, default=60)
    parser.add_argument("--max-per-document", type=int, default=4,
                        help="Deckel je Dokument; die Test-Auswahl nutzt 2, hier "
                             "bewusst 4 fuer mehr unbenutzte Tabellen")
    parser.add_argument("--exclude-selection", type=Path,
                        default=rb.DEFAULT_SELECTION,
                        help="eingefrorene Auswahl, deren Dokumente aussen bleiben")
    args = parser.parse_args()

    frozen = json.loads(args.exclude_selection.read_text(encoding="utf-8"))
    belegt_dokumente = {entry["table_id"].split(":")[0] for entry in frozen["tables"]}
    belegt_records = {rid for entry in frozen["tables"] for rid in entry["record_ids"]}

    records = rb.load_records(rb.DEFAULT_RECORDS)
    frei: List[Dict[str, Any]] = []
    for record in records.values():
        document = str(record["document"].get("id") or "")
        if document in belegt_dokumente or record["record_id"] in belegt_records:
            continue
        if not (record.get("gold") or {}).get("cells"):
            continue
        pfad = record["document"].get("path") or ""
        if not pfad or not (REPO / pfad).exists():
            continue
        frei.append(record)

    kandidaten = build_candidates(frei, role="", require_bound=True)
    gewaehlt = select(kandidaten, args.target, args.max_per_document, 6)
    dokumente = {entry["table_id"].split(":")[0] for entry in gewaehlt}

    stratum_counts: Dict[str, int] = {}
    for entry in gewaehlt:
        for stratum in entry["strata"]:
            stratum_counts[stratum] = stratum_counts.get(stratum, 0) + 1

    payload = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "role": "gegenprobe",
        "target": args.target,
        "frozen": True,
        "zweck": ("Gegenprobe der Tabellenwahl auf Records, deren Dokumente in "
                  "der Test-Auswahl nicht vorkommen"),
        "records_file": str(rb.DEFAULT_RECORDS.relative_to(REPO)),
        "records_sha256": sha256_of(rb.DEFAULT_RECORDS),
        "exclude_selection": str(args.exclude_selection.relative_to(REPO)),
        "ausgeschlossene_dokumente": len(belegt_dokumente),
        "ausgeschlossene_records": len(belegt_records),
        "n_candidates": len(kandidaten),
        "n_tables": len(gewaehlt),
        "require_bound": True,
        "gold_reachable_total": sum(entry.get("gold_reachable", 0) for entry in gewaehlt),
        "strata_order": list(STRATA_ORDER),
        "strata_counts": stratum_counts,
        "record_ids": sorted({rid for entry in gewaehlt for rid in entry["record_ids"]}),
        "n_records": len({rid for entry in gewaehlt for rid in entry["record_ids"]}),
        "n_documents": len(dokumente),
        "max_per_document": args.max_per_document,
        "max_per_record": 6,
        "tables": gewaehlt,
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"freie Records {len(frei)}, Kandidaten {len(kandidaten)}, "
          f"Tabellen {len(gewaehlt)}, Records {payload['n_records']}, "
          f"Dokumente {payload['n_documents']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
