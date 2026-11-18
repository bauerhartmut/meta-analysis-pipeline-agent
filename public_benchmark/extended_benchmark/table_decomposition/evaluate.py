#!/usr/bin/env python3
"""Bewertung eines Zerlegungs-Benchmarklaufs gegen die Yun-Goldzellen.

Die Zaehlweise folgt dem bestehenden Yun-Benchmark
(``yun_full/auswerte_yun699.py``): exakter Wertvergleich, fehlende Zelle ist
fehlend, eine gemeldete Zelle ohne Goldannotation ist **kein** falsch-positiv,
sondern unbewertbar. Beides wird getrennt ausgewiesen.

Was Yun nicht hergibt, wird auch nicht behauptet: die Goldzellen tragen kein
Outcome- und kein Zeitpunktfeld. Die Zuordnung zu Outcome und Zeitpunkt ist
deshalb **nicht messbar**; gemessen wird stattdessen, ob die Engine den Kontext
(Zitat, Zeilenlabel, Header-Pfad) mitliefert, und wie viele Armvertauschungen
auftreten.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

STRATEGY_LABELS = {
    "A": "Full-Table",
    "B": "Vertical",
    "C": "Horizontal",
    "D": "Bidirectional",
    "E": "Adaptive Recursive",
}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _same(left: Any, right: Any, tolerance: float = 1e-6) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def match_record(gold_cells: Sequence[Dict[str, Any]],
                 predicted: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Zellen eines Records abgleichen; liefert Zaehlungen und Fehlerlisten."""
    used: set = set()
    matched = wrong = missing = 0
    errors: List[Dict[str, Any]] = []
    for gold in gold_cells:
        field_name, arm = gold["field"], gold.get("arm")
        candidates = [
            index for index, cell in enumerate(predicted)
            if index not in used and cell.get("field") == field_name
            and (arm is None or cell.get("arm") == arm)
        ]
        hit = next((i for i in candidates if _same(predicted[i].get("value"), gold.get("value"))), None)
        if hit is not None:
            used.add(hit)
            matched += 1
            continue
        if candidates:
            used.add(candidates[0])
            wrong += 1
            errors.append({
                "art": "falscher_wert",
                "field": field_name,
                "arm": arm,
                "gold": gold.get("value"),
                "modell": predicted[candidates[0]].get("value"),
            })
        else:
            missing += 1
            errors.append({"art": "fehlend", "field": field_name, "arm": arm,
                           "gold": gold.get("value")})

    without_gold = 0
    for index, cell in enumerate(predicted):
        if index in used:
            continue
        same_field = [
            gold for gold in gold_cells
            if gold["field"] == cell.get("field")
            and (gold.get("arm") is None or gold.get("arm") == cell.get("arm"))
        ]
        if same_field:
            continue          # schon als falscher Wert gezaehlt
        without_gold += 1
        errors.append({"art": "ohne_gold", "field": cell.get("field"),
                       "arm": cell.get("arm"), "modell": cell.get("value")})

    gold_by_base: Dict[str, Dict[str, float]] = defaultdict(dict)
    pred_by_base: Dict[str, Dict[str, float]] = defaultdict(dict)
    for gold in gold_cells:
        if gold.get("arm"):
            base = str(gold["field"]).split("_", 1)[1]
            gold_by_base[base][gold["arm"]] = gold.get("value")
    for cell in predicted:
        if cell.get("arm"):
            base = str(cell["field"]).split("_", 1)[1]
            pred_by_base[base][cell["arm"]] = cell.get("value")

    swap = False
    for base, arms in gold_by_base.items():
        if set(arms) != {"intervention", "comparator"}:
            continue
        predicted_arms = pred_by_base.get(base, {})
        if set(predicted_arms) != {"intervention", "comparator"}:
            continue
        correct = (_same(predicted_arms["intervention"], arms["intervention"])
                   and _same(predicted_arms["comparator"], arms["comparator"]))
        swapped = (_same(predicted_arms["intervention"], arms["comparator"])
                   and _same(predicted_arms["comparator"], arms["intervention"]))
        if swapped and not correct:
            swap = True
    return {"matched": matched, "wrong": wrong, "missing": missing,
            "without_gold": without_gold, "errors": errors, "arm_swap": swap}


def _rate(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate(rows: Sequence[Dict[str, Any]], records: Dict[str, Dict[str, Any]],
             preis_in: Optional[float] = None,
             preis_out: Optional[float] = None) -> Dict[str, Any]:
    by_strategy: Dict[str, Dict[str, Any]] = {}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["strategy"]].append(row)

    for strategy, entries in sorted(grouped.items()):
        matched = wrong = missing = without_gold = 0
        exact_records = 0
        swaps = 0
        failures = 0
        conflicts = 0
        prompt_tokens = completion_tokens = 0
        runtime = 0.0
        per_complexity: Dict[str, Counter] = defaultdict(Counter)
        per_field: Dict[str, Counter] = defaultdict(Counter)
        errors_all: List[Dict[str, Any]] = []
        validation_codes: Counter = Counter()
        validation_status: Counter = Counter()
        context = Counter()
        models: Counter = Counter()

        for row in entries:
            record = records.get(row["record_id"])
            if record is None:
                failures += 1
                continue
            result = match_record(record["gold"]["cells"], row.get("cells") or [])
            matched += result["matched"]
            wrong += result["wrong"]
            missing += result["missing"]
            without_gold += result["without_gold"]
            if result["arm_swap"]:
                swaps += 1
            if (result["wrong"] == 0 and result["missing"] == 0
                    and result["without_gold"] == 0 and record["gold"]["cells"]):
                exact_records += 1
            for error in result["errors"]:
                errors_all.append({**error, "record_id": row["record_id"],
                                   "strategy": strategy})
            complexity = row.get("complexity") or "unbekannt"
            per_complexity[complexity]["matched"] += result["matched"]
            per_complexity[complexity]["wrong"] += result["wrong"]
            per_complexity[complexity]["missing"] += result["missing"]
            per_complexity[complexity]["records"] += 1
            for gold in record["gold"]["cells"]:
                per_field[gold["field"]]["gold"] += 1
            for cell in row.get("cells") or []:
                per_field[cell["field"]]["predicted"] += 1

            telemetry = row.get("telemetry") or {}
            prompt_tokens += int(telemetry.get("prompt_tokens") or 0)
            completion_tokens += int(telemetry.get("completion_tokens") or 0)
            runtime += float(telemetry.get("runtime_s") or 0.0)
            failures += len([r for r in (row.get("unit_results") or []) if r.get("error")])
            conflicts += len(row.get("conflicts") or [])
            models[row.get("model") or "?"] += 1
            validation = row.get("validation") or {}
            # Zwei Formen: je Record ein Status-Zaehler (Modelllauf, mehrere
            # Tabellen) oder ein einzelner Status plus Befundliste (aeltere
            # Laeufe). Beide werden gleich gezaehlt.
            status_value = validation.get("status", "ohne")
            if isinstance(status_value, dict):
                for key, count in status_value.items():
                    validation_status[str(key)] += int(count)
            elif isinstance(status_value, str):
                validation_status[status_value] += 1
            codes_value = validation.get("codes")
            if isinstance(codes_value, dict):
                for key, count in codes_value.items():
                    validation_codes[str(key)] += int(count)
            for finding in validation.get("findings") or []:
                if isinstance(finding, dict) and finding.get("code"):
                    validation_codes[finding["code"]] += 1

            for cell in row.get("cells") or []:
                context["zellen"] += 1
                if cell.get("quote"):
                    context["mit_zitat"] += 1
                if cell.get("row_label"):
                    context["mit_zeilenlabel"] += 1
                if cell.get("page") is not None:
                    context["mit_seite"] += 1

        evaluable = matched + wrong
        precision = _rate(matched, evaluable)
        precision_strict = _rate(matched, evaluable + without_gold)
        recall = _rate(matched, matched + wrong + missing)
        f1 = (round(2 * precision * recall / (precision + recall), 4)
              if precision + recall else 0.0)
        cost = None
        if preis_in is not None and preis_out is not None:
            cost = round(prompt_tokens / 1000 * preis_in
                         + completion_tokens / 1000 * preis_out, 4)
        by_strategy[strategy] = {
            "strategy_label": STRATEGY_LABELS.get(strategy, strategy),
            "models": dict(models),
            "records": len(entries),
            "cells": {
                "gold": matched + wrong + missing,
                "richtig": matched,
                "falsch": wrong,
                "fehlend": missing,
                "ohne_gold": without_gold,
            },
            "precision": precision,
            "precision_inkl_ohne_gold": precision_strict,
            "recall": recall,
            "f1": f1,
            "records_exakt": exact_records,
            "records_exakt_anteil": _rate(exact_records, len(entries)),
            "arm_tausch_records": swaps,
            "technische_ausfaelle": failures,
            "konflikte": conflicts,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens,
                       "gesamt": prompt_tokens + completion_tokens},
            "runtime_s": round(runtime, 1),
            "kosten": cost,
            "kosten_pro_100_richtige_zellen": (
                round(cost / matched * 100, 4) if cost is not None and matched else None
            ),
            "kontext": {
                "zellen": context["zellen"],
                "mit_zitat": context["mit_zitat"],
                "mit_zeilenlabel": context["mit_zeilenlabel"],
                "mit_seite": context["mit_seite"],
                "zitat_anteil": _rate(context["mit_zitat"], context["zellen"]),
                "zeilenlabel_anteil": _rate(context["mit_zeilenlabel"], context["zellen"]),
            },
            "je_komplexitaet": {
                name: {
                    "records": counts["records"],
                    "richtig": counts["matched"],
                    "falsch": counts["wrong"],
                    "fehlend": counts["missing"],
                    "precision": _rate(counts["matched"], counts["matched"] + counts["wrong"]),
                    "recall": _rate(
                        counts["matched"],
                        counts["matched"] + counts["wrong"] + counts["missing"]),
                }
                for name, counts in sorted(per_complexity.items())
            },
            "je_feld": {name: dict(counts) for name, counts in sorted(per_field.items())},
            "fehlerklassen": dict(Counter(error["art"] for error in errors_all)),
            "validierung": {
                "status": dict(validation_status),
                "codes": dict(validation_codes.most_common()),
            },
            "fehler_beispiele": errors_all[:40],
        }

    return {
        "strategies": by_strategy,
        "nicht_messbar": {
            "outcome_zuordnung": (
                "Yun-Goldzellen tragen kein Outcome-Feld; die Zuordnung ist mit "
                "diesem Gold nicht messbar."
            ),
            "zeitpunkt_zuordnung": (
                "Yun annotiert keinen Messzeitpunkt; die Zuordnung ist mit diesem "
                "Gold nicht messbar."
            ),
            "hinweis": (
                "Gemessen wird stattdessen die Kontextmitlieferung (Zitat, "
                "Zeilenlabel, Seite) je extrahierter Zelle."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--records", type=Path,
                        default=Path(__file__).resolve().parents[1] / "yun_full" / "records" / "yun699.jsonl")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--preis-in-pro-1k", type=float, default=None)
    parser.add_argument("--preis-out-pro-1k", type=float, default=None)
    args = parser.parse_args()

    predictions = args.run_dir / "predictions.jsonl"
    if not predictions.exists():
        print(f"FEHLT: {predictions}")
        return 2
    rows = read_jsonl(predictions)
    records = {record["record_id"]: record for record in read_jsonl(args.records)}
    result = evaluate(rows, records, args.preis_in_pro_1k, args.preis_out_pro_1k)
    result["run"] = str(args.run_dir)
    result["created"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    target = args.out or (args.run_dir / "evaluation.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for strategy, data in sorted(result["strategies"].items()):
        cells = data["cells"]
        print(f"{strategy} {data['strategy_label']:<22} richtig {cells['richtig']:>4} "
              f"falsch {cells['falsch']:>3} fehlend {cells['fehlend']:>4} | "
              f"P {data['precision']:.4f} R {data['recall']:.4f} F1 {data['f1']:.4f} | "
              f"Ausfaelle {data['technische_ausfaelle']}")
    print(f"geschrieben: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
