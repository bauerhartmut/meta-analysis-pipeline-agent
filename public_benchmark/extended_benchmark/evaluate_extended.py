#!/usr/bin/env python3
"""Bewertet Vorhersagen fuer den erweiterten Benchmark.

Drei Aufgaben, drei Metriksaetze:

* ``numeric_extraction`` (Yun): zellgenaue Treffer (Precision/Recall/F1),
  mittlerer absoluter Fehler (MAE) ueber Feld-Arm-Paare unabhaengig von der
  Toleranz und Armvertauschung.
* ``evidence_direction`` (Evidence Inference): Label-Genauigkeit, Macro-F1 der
  Labels und Spannen-F1 ueber IoU-Matching.
* ``pico_span`` (EBM-NLP): Token-F1 je PICO-Element.

Die Vorhersagedatei ist JSONL nach ``predictions_schema.json``. Nicht
vorhergesagte Records zaehlen als leere Vorhersage; unbekannte Record-IDs
werden gemeldet und nicht bewertet.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATASET_TASKS = {
    "yun": "numeric_extraction",
    "yun2024": "numeric_extraction",
    "evidence_inference": "evidence_direction",
    "evidence_inference_v2": "evidence_direction",
    "ebm_nlp": "pico_span",
}

LABELS = ("no significant difference", "significantly increased", "significantly decreased")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: Zeile {number} ist kein gueltiges JSON: {error}") from error
    return rows


def index_by_id(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        record_id = row.get("record_id")
        if not record_id:
            continue
        result[str(record_id)] = row
    return result


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _base_field(field: str) -> str:
    """Entfernt die ArmvorSilbe, damit intervention_mean und comparator_mean
    als dasselbe Feld mit zwei Armen erkannt werden."""
    for prefix in ("intervention_", "comparator_"):
        if field.startswith(prefix):
            return field[len(prefix) :]
    return field


def _close(predicted: Any, gold: Any, abs_tol: float, rel_tol: float) -> bool:
    try:
        value = float(predicted)
    except (TypeError, ValueError):
        return False
    other = float(gold)
    return abs(value - other) <= max(abs_tol, rel_tol * abs(other))


# --------------------------------------------------------------------------
# Numerische Extraktion
# --------------------------------------------------------------------------


def evaluate_numeric(
    records: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    abs_tol: float = 1e-6,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    gold_cells = 0
    predicted_cells = 0
    matched = 0
    # Fehler werden unabhaengig von der Toleranz ueber Feld-Arm-Paare gesammelt.
    errors: list[float] = []
    per_field: dict[str, dict[str, float]] = defaultdict(
        lambda: {"gold": 0, "predicted": 0, "matched": 0, "errors": 0, "mae_covered": 0}
    )
    field_abs_error: dict[str, list[float]] = defaultdict(list)

    exact_records = 0
    swap_records = 0
    swap_evaluable = 0
    records_without_prediction = 0

    for record in records:
        record_id = str(record["record_id"])
        gold = [(c["field"], c["arm"], float(c["value"])) for c in record["gold"]["cells"]]
        raw_prediction = predictions.get(record_id)
        if raw_prediction is None:
            records_without_prediction += 1
            pred: list[tuple[str, str | None, float]] = []
        else:
            pred = []
            for cell in (raw_prediction.get("predicted") or {}).get("cells", []):
                try:
                    pred.append((str(cell["field"]), cell.get("arm"), float(cell["value"])))
                except (KeyError, TypeError, ValueError):
                    continue

        gold_cells += len(gold)
        predicted_cells += len(pred)
        for field, _arm, _value in gold:
            per_field[field]["gold"] += 1
        for field, _arm, _value in pred:
            per_field[field]["predicted"] += 1

        used_pred: set[int] = set()
        all_matched = True
        for field, arm, value in gold:
            best_index = None
            best_delta = None
            for index, (p_field, p_arm, p_value) in enumerate(pred):
                if index in used_pred or p_field != field or (arm is not None and p_arm != arm):
                    continue
                if not _close(p_value, value, abs_tol, rel_tol):
                    continue
                delta = abs(p_value - value)
                if best_delta is None or delta < best_delta:
                    best_index, best_delta = index, delta
            if best_index is None:
                all_matched = False
                continue
            used_pred.add(best_index)
            matched += 1
            per_field[field]["matched"] += 1

        # MAE unabhaengig von der Toleranz: jedes Gold-Feld-Arm-Paar zaehlt, fuer
        # das eine Vorhersage existiert, auch wenn der Wert ausserhalb liegt.
        paired_pred: set[int] = set()
        for field, arm, value in gold:
            candidates = [
                (abs(p_value - value), index)
                for index, (p_field, p_arm, p_value) in enumerate(pred)
                if index not in paired_pred and p_field == field and (arm is None or p_arm == arm)
            ]
            if not candidates:
                continue
            delta, index = min(candidates)
            paired_pred.add(index)
            errors.append(delta)
            field_abs_error[field].append(delta)
            per_field[field]["mae_covered"] += 1

        extra = len(pred) - len(used_pred)
        if all_matched and extra == 0:
            exact_records += 1

        # Armvertauschung: nur wenn Gold und Vorhersage beide Arme fuehren.
        gold_by_field: dict[str, dict[str, float]] = defaultdict(dict)
        pred_by_field: dict[str, dict[str, float]] = defaultdict(dict)
        for field, arm, value in gold:
            if arm:
                gold_by_field[_base_field(field)][arm] = value
        for field, arm, value in pred:
            if arm:
                pred_by_field[_base_field(field)][arm] = value
        for field, arms in gold_by_field.items():
            if set(arms) != {"intervention", "comparator"}:
                continue
            predicted_arms = pred_by_field.get(field, {})
            if set(predicted_arms) != {"intervention", "comparator"}:
                continue
            swap_evaluable += 1
            correct_orientation = _close(predicted_arms["intervention"], arms["intervention"], abs_tol, rel_tol) and _close(
                predicted_arms["comparator"], arms["comparator"], abs_tol, rel_tol
            )
            swapped = _close(predicted_arms["intervention"], arms["comparator"], abs_tol, rel_tol) and _close(
                predicted_arms["comparator"], arms["intervention"], abs_tol, rel_tol
            )
            if swapped and not correct_orientation:
                swap_records += 1

    precision = _safe_div(matched, predicted_cells)
    recall = _safe_div(matched, gold_cells)
    fields: dict[str, Any] = {}
    for field, counts in sorted(per_field.items()):
        field_values = field_abs_error.get(field, [])
        fields[field] = {
            "gold": counts["gold"],
            "predicted": counts["predicted"],
            "matched": counts["matched"],
            "recall": round(_safe_div(counts["matched"], counts["gold"]), 4),
            "precision": round(_safe_div(counts["matched"], counts["predicted"]), 4),
            "mae": round(sum(field_values) / len(field_values), 4) if field_values else None,
            "mae_covered": counts["mae_covered"],
        }

    return {
        "task": "numeric_extraction",
        "records": len(records),
        "records_without_prediction": records_without_prediction,
        "gold_cells": gold_cells,
        "predicted_cells": predicted_cells,
        "matched_cells": matched,
        "cell_precision": round(precision, 4),
        "cell_recall": round(recall, 4),
        "cell_f1": round(_f1(precision, recall), 4),
        "mae_pairs": round(sum(errors) / len(errors), 4) if errors else None,
        "mae_pairs_max": round(max(errors), 4) if errors else None,
        "mae_pairs_covered": len(errors),
        "mae_coverage": round(_safe_div(len(errors), gold_cells), 4),
        "record_exact": exact_records,
        "record_exact_rate": round(_safe_div(exact_records, len(records)), 4),
        "arm_swap_records": swap_records,
        "arm_swap_evaluable": swap_evaluable,
        "arm_swap_rate": round(_safe_div(swap_records, swap_evaluable), 4),
        "fields": fields,
        "tolerance": {"abs": abs_tol, "rel": rel_tol},
    }


# --------------------------------------------------------------------------
# Evidenzrichtung
# --------------------------------------------------------------------------


def _iou(first: dict[str, Any], second: dict[str, Any]) -> float:
    a_start, a_end = int(first["start"]), int(first["end"])
    b_start, b_end = int(second["start"]), int(second["end"])
    overlap = min(a_end, b_end) - max(a_start, b_start)
    if overlap <= 0:
        return 0.0
    union = max(a_end, b_end) - min(a_start, b_start)
    return overlap / union if union else 0.0


def _span_scores(gold: list[dict[str, Any]], pred: list[dict[str, Any]], iou_threshold: float) -> tuple[int, int, int]:
    """Greedy-Matching ueber IoU; liefert (tp, fp, fn)."""
    used: set[int] = set()
    true_positive = 0
    for gold_span in gold:
        best_index = None
        best_iou = 0.0
        for index, pred_span in enumerate(pred):
            if index in used:
                continue
            value = _iou(gold_span, pred_span)
            if value >= iou_threshold and value > best_iou:
                best_index, best_iou = index, value
        if best_index is not None:
            used.add(best_index)
            true_positive += 1
    return true_positive, len(pred) - true_positive, len(gold) - true_positive


def evaluate_evidence(
    records: list[dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    labelled = 0
    correct = 0
    confusion: Counter[tuple[str, str]] = Counter()
    per_label: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    tp = fp = fn = 0
    span_tp = span_fp = span_fn = 0
    records_without_prediction = 0
    label_span_both = 0

    for record in records:
        record_id = str(record["record_id"])
        gold_label = record["gold"].get("label")
        gold_spans = record["gold"].get("spans") or []
        raw_prediction = predictions.get(record_id)
        if raw_prediction is None:
            records_without_prediction += 1
            predicted = {}
        else:
            predicted = raw_prediction.get("predicted") or {}
        pred_label = predicted.get("label")
        pred_spans = predicted.get("spans") or []

        span_tp_i, span_fp_i, span_fn_i = _span_scores(gold_spans, pred_spans, iou_threshold) if gold_spans else (0, len(pred_spans), 0)
        span_tp += span_tp_i
        span_fp += span_fp_i
        span_fn += span_fn_i

        if gold_label:
            labelled += 1
            confusion[(str(gold_label), str(pred_label))] += 1
            if pred_label == gold_label:
                correct += 1
                per_label[gold_label]["tp"] += 1
                if span_tp_i and span_fn_i == 0:
                    label_span_both += 1
            else:
                if pred_label:
                    per_label[str(pred_label)]["fp"] += 1
                per_label[gold_label]["fn"] += 1

    label_precision = _safe_div(correct, labelled)
    macro_f1_values = []
    labels_report = {}
    for label in sorted({*LABELS, *per_label}):
        counts = per_label.get(label, {"tp": 0, "fp": 0, "fn": 0})
        precision = _safe_div(counts["tp"], counts["tp"] + counts["fp"])
        recall = _safe_div(counts["tp"], counts["tp"] + counts["fn"])
        f1 = _f1(precision, recall)
        labels_report[label] = {
            "tp": counts["tp"],
            "fp": counts["fp"],
            "fn": counts["fn"],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        if counts["tp"] + counts["fn"]:
            macro_f1_values.append(f1)

    span_precision = _safe_div(span_tp, span_tp + span_fp)
    span_recall = _safe_div(span_tp, span_tp + span_fn)
    return {
        "task": "evidence_direction",
        "records": len(records),
        "records_without_prediction": records_without_prediction,
        "records_with_gold_label": labelled,
        "label_accuracy": round(label_precision, 4),
        "label_macro_f1": round(sum(macro_f1_values) / len(macro_f1_values), 4) if macro_f1_values else None,
        "labels": labels_report,
        "label_span_both": label_span_both,
        "span_tp": span_tp,
        "span_fp": span_fp,
        "span_fn": span_fn,
        "span_precision": round(span_precision, 4),
        "span_recall": round(span_recall, 4),
        "span_f1": round(_f1(span_precision, span_recall), 4),
        "iou_threshold": iou_threshold,
        "confusion": {f"{g}->{p}": count for (g, p), count in sorted(confusion.items())},
    }


# --------------------------------------------------------------------------
# PICO-Spannen
# --------------------------------------------------------------------------

ELEMENTS = ("participants", "interventions", "outcomes")


def _token_set(spans: Iterable[dict[str, Any]], element: str) -> set[int]:
    tokens: set[int] = set()
    for span in spans:
        if span.get("element") != element:
            continue
        start, end = int(span["start"]), int(span["end"])
        tokens.update(range(start, max(start, end)))
    return tokens


def evaluate_pico(records: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    per_element: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "gold": 0, "predicted": 0})
    records_without_prediction = 0
    per_record_exact = 0

    for record in records:
        record_id = str(record["record_id"])
        gold_spans = record["gold"].get("spans") or []
        raw_prediction = predictions.get(record_id)
        if raw_prediction is None:
            records_without_prediction += 1
            pred_spans: list[dict[str, Any]] = []
        else:
            pred_spans = (raw_prediction.get("predicted") or {}).get("spans") or []

        exact = True
        for element in ELEMENTS:
            gold_tokens = _token_set(gold_spans, element)
            pred_tokens = _token_set(pred_spans, element)
            true_positive = len(gold_tokens & pred_tokens)
            per_element[element]["gold"] += len(gold_tokens)
            per_element[element]["predicted"] += len(pred_tokens)
            per_element[element]["tp"] += true_positive
            per_element[element]["fp"] += len(pred_tokens) - true_positive
            per_element[element]["fn"] += len(gold_tokens) - true_positive
            if gold_tokens != pred_tokens:
                exact = False
        if exact:
            per_record_exact += 1

    elements: dict[str, Any] = {}
    f1_values = []
    for element in ELEMENTS:
        counts = per_element[element]
        precision = _safe_div(counts["tp"], counts["tp"] + counts["fp"])
        recall = _safe_div(counts["tp"], counts["tp"] + counts["fn"])
        f1 = _f1(precision, recall)
        f1_values.append(f1)
        elements[element] = {
            "gold_tokens": counts["gold"],
            "predicted_tokens": counts["predicted"],
            "tp": counts["tp"],
            "fp": counts["fp"],
            "fn": counts["fn"],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    return {
        "task": "pico_span",
        "records": len(records),
        "records_without_prediction": records_without_prediction,
        "elements": elements,
        "macro_f1": round(sum(f1_values) / len(f1_values), 4),
        "record_exact": per_record_exact,
        "record_exact_rate": round(_safe_div(per_record_exact, len(records)), 4),
    }


EVALUATORS = {
    "numeric_extraction": evaluate_numeric,
    "evidence_direction": evaluate_evidence,
    "pico_span": evaluate_pico,
}


def evaluate(
    dataset: str,
    records: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    abs_tol: float = 1e-6,
    rel_tol: float = 0.0,
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    task = DATASET_TASKS.get(dataset) or (records[0]["task"] if records else None)
    if task not in EVALUATORS:
        raise ValueError(f"Unbekannte Aufgabe fuer Datensatz {dataset!r}: {task!r}")
    prediction_index = index_by_id(predictions)
    record_ids = {str(record["record_id"]) for record in records}
    unknown = sorted(set(prediction_index) - record_ids)
    if task == "numeric_extraction":
        metrics = evaluate_numeric(records, prediction_index, abs_tol, rel_tol)
    elif task == "evidence_direction":
        metrics = evaluate_evidence(records, prediction_index, iou_threshold)
    else:
        metrics = evaluate_pico(records, prediction_index)
    metrics["dataset"] = dataset
    metrics["unknown_prediction_ids"] = unknown[:20]
    metrics["unknown_prediction_count"] = len(unknown)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="yun | evidence_inference | ebm_nlp")
    parser.add_argument("--records", type=Path, required=True, help="JSONL der Gold-Records")
    parser.add_argument("--predictions", type=Path, required=True, help="JSONL im Format predictions_schema.json")
    parser.add_argument("--abs-tol", type=float, default=1e-6)
    parser.add_argument("--rel-tol", type=float, default=0.0)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--out", type=Path, default=None, help="Ziel-JSON; sonst nur stdout")
    args = parser.parse_args()

    records = read_jsonl(args.records)
    predictions = read_jsonl(args.predictions)
    metrics = evaluate(args.dataset, records, predictions, args.abs_tol, args.rel_tol, args.iou)
    payload = json.dumps(metrics, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
