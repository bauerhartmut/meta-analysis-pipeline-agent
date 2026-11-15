#!/usr/bin/env python3
"""Getrennte Bewertung der mehrstufigen Ereignisextraktion.

Vergleicht Basislauf und Stufenlauf und weist drei Dinge getrennt aus:

1. Gesamtmetriken beider Laeufe (Zellen-F1, MAE, Abdeckung) auf denselben Records.
2. Metriken nur auf den Ereignisfeldern, also dem Feld, das die Stufe veraendert.
3. Die Zwischenstufe selbst: wie oft Zeilenlabel und Spaltenkopf woertlich im
   Artikel stehen (ohne Modell pruefbar) und wie sich die Ereigniszellen
   einzeln von der Basis zur Stufe verschieben.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from evaluate_extended import _close, evaluate_numeric, read_jsonl  # noqa: E402
from stage_extraction import EVENT_FIELDS, beleg_im_text  # noqa: E402


def load_predictions(run_dir: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(run_dir / "predictions.jsonl")
    return {str(row["record_id"]): row for row in rows}


def only_fields(records: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    trimmed = copy.deepcopy(records)
    for record in trimmed:
        record["gold"]["cells"] = [cell for cell in record["gold"]["cells"] if cell["field"] in fields]
    return trimmed


def only_predicted(predictions: dict[str, dict[str, Any]], fields: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    trimmed: dict[str, dict[str, Any]] = {}
    for record_id, row in predictions.items():
        cells = [cell for cell in (row.get("predicted") or {}).get("cells", []) if cell.get("field") in fields]
        trimmed[record_id] = {**row, "predicted": {"cells": cells}}
    return trimmed


def cell_map(row: dict[str, Any] | None) -> dict[str, float]:
    if not row:
        return {}
    result: dict[str, float] = {}
    for cell in (row.get("predicted") or {}).get("cells", []):
        field = cell.get("field")
        if field in EVENT_FIELDS:
            try:
                result[str(field)] = float(cell["value"])
            except (KeyError, TypeError, ValueError):
                continue
    return result


def progression(
    records: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    staged: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Verschiebung je Ereigniszelle: richtig/falsch vorher und nachher."""
    uebergaenge: Counter[str] = Counter()
    details: list[dict[str, Any]] = []
    for record in records:
        rid = str(record["record_id"])
        gold = {
            cell["field"]: float(cell["value"])
            for cell in record["gold"]["cells"]
            if cell["field"] in EVENT_FIELDS and cell.get("value") is not None
        }
        before = cell_map(baseline.get(rid))
        after = cell_map(staged.get(rid))
        for field, value in gold.items():
            vorher = _close(before[field], value, 1e-6, 0.0) if field in before else None
            nachher = _close(after[field], value, 1e-6, 0.0) if field in after else None
            key = f"{'richtig' if vorher else 'falsch' if vorher is False else 'fehlt'}->"
            key += "richtig" if nachher else "falsch" if nachher is False else "fehlt"
            uebergaenge[key] += 1
            if vorher is not nachher or (vorher is False and nachher is False):
                details.append(
                    {
                        "record_id": rid,
                        "field": field,
                        "gold": value,
                        "baseline": before.get(field),
                        "staged": after.get(field),
                        "uebergang": key,
                    }
                )
    return {"uebergaenge": dict(sorted(uebergaenge.items())), "zellen": details}


def stage1_checks(run_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    texts = {}
    for record in records:
        path = record["document"].get("path") or ""
        candidate = REPO / path if path else None
        texts[str(record["record_id"])] = (
            candidate.read_text(encoding="utf-8", errors="replace") if candidate and candidate.exists() else ""
        )
    rows = read_jsonl(run_dir / "stage1.jsonl")
    arme = Counter()
    beide_belegt = 0
    zeile_belegt = 0
    spalte_belegt = 0
    geprueft = 0
    fehlende_belege: list[dict[str, Any]] = []
    for row in rows:
        text = texts.get(str(row["record_id"]), "")
        for locator in row.get("locators") or []:
            arme[locator["arm"]] += 1
            if not locator.get("found"):
                continue
            geprueft += 1
            zeile = beleg_im_text(locator["row_label"], text)
            spalte = beleg_im_text(locator["column_header"], text)
            zeile_belegt += int(zeile)
            spalte_belegt += int(spalte)
            beide_belegt += int(zeile and spalte)
            if not (zeile and spalte):
                fehlende_belege.append(
                    {
                        "record_id": row["record_id"],
                        "arm": locator["arm"],
                        "row_label": locator["row_label"],
                        "column_header": locator["column_header"],
                        "zeile_belegt": zeile,
                        "spalte_belegt": spalte,
                    }
                )
    return {
        "records_mit_stage1": len(rows),
        "locators_je_arm": dict(arme),
        "geprueft": geprueft,
        "zeile_belegt": zeile_belegt,
        "spalte_belegt": spalte_belegt,
        "beide_belegt": beide_belegt,
        "anteil_beide_belegt": round(beide_belegt / geprueft, 4) if geprueft else None,
        "ohne_beleg": fehlende_belege,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", default="yun_dev_std_20261115")
    parser.add_argument("--stage-run", required=True)
    parser.add_argument("--records", type=Path, default=HERE / "records" / "yun_dev.jsonl")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    records = read_jsonl(args.records)
    baseline_dir = HERE / "runs" / args.baseline_run
    stage_dir = HERE / "runs" / args.stage_run
    baseline = load_predictions(baseline_dir)
    staged = load_predictions(stage_dir)

    ergebnis: dict[str, Any] = {
        "baseline_run": args.baseline_run,
        "stage_run": args.stage_run,
        "records": len(records),
        "gesamt": {
            "baseline": evaluate_numeric(records, baseline),
            "stufe": evaluate_numeric(records, staged),
        },
        "nur_ereignisse": {
            "baseline": evaluate_numeric(only_fields(records, EVENT_FIELDS), only_predicted(baseline, EVENT_FIELDS)),
            "stufe": evaluate_numeric(only_fields(records, EVENT_FIELDS), only_predicted(staged, EVENT_FIELDS)),
        },
        "zwischenstufe": stage1_checks(stage_dir, records),
        "verschiebung": progression(records, baseline, staged),
    }
    merged_rows = read_jsonl(stage_dir / "predictions.jsonl")
    ergebnis["stufenabdeckung"] = {
        "records": len(merged_rows),
        "voll_ersetzt": sum(1 for row in merged_rows if len(row.get("staged_fields") or []) == 2),
        "teilweise": sum(1 for row in merged_rows if len(row.get("staged_fields") or []) == 1),
        "zurueckgefallen": dict(
            Counter(field for row in merged_rows for field in (row.get("fallback_fields") or []))
        ),
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for scope in ("gesamt", "nur_ereignisse"):
        print(f"[{scope}]")
        for label in ("baseline", "stufe"):
            metrics = ergebnis[scope][label]
            print(
                f"  {label:9s} F1 {metrics['cell_f1']:.4f}  recall {metrics['cell_recall']:.4f}  "
                f"precision {metrics['cell_precision']:.4f}  MAE {metrics['mae_pairs']}  "
                f"coverage {metrics['mae_coverage']} ({metrics['mae_pairs_covered']}/{metrics['gold_cells']})  "
                f"exakt {metrics['record_exact']}/{metrics['records']}"
            )
    zwischen = ergebnis["zwischenstufe"]
    print(
        f"[stufe1] locators {zwischen['locators_je_arm']}, woertlich belegt "
        f"{zwischen['beide_belegt']}/{zwischen['geprueft']} ({zwischen['anteil_beide_belegt']})"
    )
    print(f"[verschiebung] {ergebnis['verschiebung']['uebergaenge']}")
    print(f"[abdeckung] {ergebnis['stufenabdeckung']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
