#!/usr/bin/env python3
"""Regelbasierte Pruefung der Vorhersagen.

Die Pruefung markiert Auffaelligkeiten, sie korrigiert nichts: Die Zellen
bleiben unveraendert, damit die Metriken und die Fehleranalyse weiter auf den
Rohantworten beruhen. Aufruf:

    python public_benchmark/extended_benchmark/validate_predictions.py \
        --run public_benchmark/extended_benchmark/runs/<run_id>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "records" / "yun_dev.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pruefe_ereignisse(
    cells: dict[tuple[str, str], float],
) -> dict[str, str]:
    """Markiert Ereigniszellen, die groesser als ihre Gruppengroesse sind."""
    hinweise: dict[str, str] = {}
    for (field, arm), value in cells.items():
        if not field.endswith("_events"):
            continue
        size = cells.get((field.replace("_events", "_group_size"), arm))
        if size is None:
            continue
        if value > size:
            hinweise[f"{field}|{arm}"] = (
                f"Ereignisse {value:g} groesser als Gruppengroesse {size:g}"
            )
            continue
        if value < 0:
            hinweise[f"{field}|{arm}"] = f"negative Ereigniszahl {value:g}"
    return hinweise


def pruefe_lauf(run_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = read_jsonl(run_dir / "predictions.jsonl")
    gold = {
        record["record_id"]: {
            (cell["field"], cell["arm"]): float(cell["value"]) for cell in record["gold"]["cells"]
        }
        for record in records
    }
    markierungen = []
    for row in rows:
        cells = {(cell["field"], cell["arm"]): float(cell["value"]) for cell in row["predicted"]["cells"]}
        for key, hinweis in pruefe_ereignisse(cells).items():
            field, arm = key.split("|")
            gold_value = gold.get(row["record_id"], {}).get((field, arm))
            markierungen.append(
                {
                    "run_id": run_dir.name,
                    "model": row["model"],
                    "record_id": row["record_id"],
                    "field": field,
                    "arm": arm,
                    "value": cells[(field, arm)],
                    "gruppengroesse": cells.get((field.replace("_events", "_group_size"), arm)),
                    "gold": gold_value,
                    "hinweis": hinweis,
                    "gold_ebenfalls_auffaellig": bool(
                        gold_value is not None
                        and (gold_value > (gold.get(row["record_id"], {}).get((field.replace("_events", "_group_size"), arm)) or 0))
                    ),
                }
            )
    return {
        "run_id": run_dir.name,
        "zeilen": len(rows),
        "markierungen": len(markierungen),
        "details": markierungen,
        "regel": "Ereignisse <= Gruppengroesse, negative Ereigniszahlen",
        "korrigiert": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Laufverzeichnis mit predictions.jsonl")
    args = parser.parse_args()

    run_dir = Path(args.run)
    ergebnis = pruefe_lauf(run_dir, read_jsonl(RECORDS))
    out = run_dir / "validation.json"
    out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{ergebnis['zeilen']} Zeilen geprueft, {ergebnis['markierungen']} Markierungen -> {out}")
    for detail in ergebnis["details"]:
        print(f"  {detail['model']} {detail['record_id']} {detail['field']}: {detail['hinweis']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
