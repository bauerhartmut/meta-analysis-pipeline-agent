"""Tests der Bewertungsmetriken auf synthetischen Vorhersagen."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extended_benchmark.evaluate_extended import (  # noqa: E402
    evaluate,
    evaluate_evidence,
    evaluate_numeric,
    evaluate_pico,
)


def numeric_record(record_id: str, cells: list[tuple[str, str, float]]) -> dict:
    return {
        "record_id": record_id,
        "dataset": "yun2024",
        "task": "numeric_extraction",
        "gold": {"cells": [{"field": f, "arm": a, "value": v, "unit": "x"} for f, a, v in cells]},
    }


def prediction(record_id: str, **predicted) -> dict:
    return {"record_id": record_id, "dataset": "yun2024", "predicted": predicted}


def test_numeric_perfect_prediction_scores_one() -> None:
    records = [numeric_record("r1", [("intervention_group_size", "intervention", 143.0)])]
    metrics = evaluate_numeric(records, {"r1": prediction("r1", cells=[{"field": "intervention_group_size", "arm": "intervention", "value": 143}])})
    assert metrics["cell_precision"] == 1.0
    assert metrics["cell_recall"] == 1.0
    assert metrics["mae_pairs"] == 0.0
    assert metrics["record_exact"] == 1
    assert metrics["arm_swap_evaluable"] == 0


def test_numeric_mae_ignores_cells_without_pair() -> None:
    records = [numeric_record("r1", [("intervention_mean", "intervention", 10.0), ("comparator_mean", "comparator", 20.0)])]
    metrics = evaluate_numeric(records, {"r1": prediction("r1", cells=[{"field": "intervention_mean", "arm": "intervention", "value": 11.0}])})
    assert metrics["mae_pairs"] == 1.0
    assert metrics["mae_pairs_covered"] == 1
    assert metrics["mae_coverage"] == 0.5
    assert metrics["fields"]["comparator_mean"]["mae"] is None


def test_numeric_missing_cell_reduces_recall() -> None:
    records = [numeric_record("r1", [("intervention_mean", "intervention", 25.4), ("comparator_mean", "comparator", 13.5)])]
    metrics = evaluate_numeric(records, {"r1": prediction("r1", cells=[{"field": "intervention_mean", "arm": "intervention", "value": 25.4}])})
    assert metrics["cell_recall"] == 0.5
    assert metrics["cell_precision"] == 1.0
    assert metrics["record_exact"] == 0


def test_numeric_mae_is_positive_at_default_tolerance() -> None:
    """Der MAE muss auch dann messen, wenn die Toleranz den Treffer verhindert."""
    records = [numeric_record("r1", [("intervention_mean", "intervention", 10.0)])]
    metrics = evaluate_numeric(
        records,
        {"r1": prediction("r1", cells=[{"field": "intervention_mean", "arm": "intervention", "value": 14.0}])},
    )
    assert metrics["cell_recall"] == 0.0
    assert metrics["mae_pairs"] == 4.0
    assert metrics["mae_pairs_max"] == 4.0
    assert metrics["mae_pairs_covered"] == 1
    assert metrics["mae_coverage"] == 1.0


def test_numeric_mae_and_recall_differ_under_tolerance() -> None:
    records = [numeric_record("r1", [("intervention_mean", "intervention", 10.0)])]
    predictions = {"r1": prediction("r1", cells=[{"field": "intervention_mean", "arm": "intervention", "value": 12.0}])}
    strict = evaluate_numeric(records, predictions)
    assert strict["cell_recall"] == 0.0
    assert strict["mae_pairs"] == 2.0
    tolerant = evaluate_numeric(records, predictions, abs_tol=3.0)
    assert tolerant["cell_recall"] == 1.0
    # Der MAE bleibt gleich: er haengt nicht von der Toleranz ab.
    assert tolerant["mae_pairs"] == 2.0


def test_numeric_relative_tolerance() -> None:
    records = [numeric_record("r1", [("intervention_mean", "intervention", 100.0)])]
    metrics = evaluate_numeric(
        records,
        {"r1": prediction("r1", cells=[{"field": "intervention_mean", "arm": "intervention", "value": 100.9}])},
        rel_tol=0.01,
    )
    assert metrics["cell_recall"] == 1.0
    assert metrics["mae_pairs"] == pytest.approx(0.9, abs=1e-6)


def test_numeric_detects_swapped_arms() -> None:
    records = [
        numeric_record(
            "r1",
            [("intervention_mean", "intervention", 10.0), ("comparator_mean", "comparator", 20.0)],
        )
    ]
    swapped = prediction(
        "r1",
        cells=[
            {"field": "intervention_mean", "arm": "intervention", "value": 20.0},
            {"field": "comparator_mean", "arm": "comparator", "value": 10.0},
        ],
    )
    metrics = evaluate_numeric(records, {"r1": swapped})
    assert metrics["arm_swap_evaluable"] == 1
    assert metrics["arm_swap_records"] == 1
    assert metrics["arm_swap_rate"] == 1.0


def test_numeric_correct_arms_are_not_reported_as_swap() -> None:
    records = [
        numeric_record(
            "r1",
            [("intervention_mean", "intervention", 10.0), ("comparator_mean", "comparator", 20.0)],
        )
    ]
    correct = prediction(
        "r1",
        cells=[
            {"field": "intervention_mean", "arm": "intervention", "value": 10.0},
            {"field": "comparator_mean", "arm": "comparator", "value": 20.0},
        ],
    )
    metrics = evaluate_numeric(records, {"r1": correct})
    assert metrics["arm_swap_evaluable"] == 1
    assert metrics["arm_swap_records"] == 0


def test_numeric_missing_prediction_counts_as_empty() -> None:
    records = [numeric_record("r1", [("intervention_mean", "intervention", 10.0)])]
    metrics = evaluate_numeric(records, {})
    assert metrics["records_without_prediction"] == 1
    assert metrics["cell_recall"] == 0.0
    assert metrics["record_exact_rate"] == 0.0


def evidence_record(record_id: str, label: str | None, spans: list[tuple[int, int]]) -> dict:
    return {
        "record_id": record_id,
        "dataset": "evidence_inference_v2",
        "task": "evidence_direction",
        "gold": {
            "label": label,
            "spans": [{"kind": "evidence", "element": "result", "start": s, "end": e, "text": "x"} for s, e in spans],
        },
    }


def test_evidence_label_accuracy_and_macro_f1() -> None:
    records = [
        evidence_record("a", "significantly increased", [(0, 10)]),
        evidence_record("b", "no significant difference", [(0, 10)]),
    ]
    predictions = {
        "a": prediction("a", label="significantly increased", spans=[{"start": 0, "end": 10}]),
        "b": prediction("b", label="significantly increased", spans=[{"start": 0, "end": 10}]),
    }
    metrics = evaluate_evidence(records, predictions)
    assert metrics["label_accuracy"] == 0.5
    assert metrics["labels"]["significantly increased"]["tp"] == 1
    assert metrics["labels"]["significantly increased"]["fp"] == 1
    assert metrics["labels"]["no significant difference"]["fn"] == 1


def test_evidence_span_f1_uses_iou_matching() -> None:
    records = [
        evidence_record("a", None, [(0, 10)]),
        evidence_record("b", None, [(0, 10)]),
    ]
    predictions = {
        "a": prediction("a", label=None, spans=[{"start": 2, "end": 12}]),
        "b": prediction("b", label=None, spans=[{"start": 50, "end": 60}]),
    }
    metrics = evaluate_evidence(records, predictions)
    assert metrics["span_tp"] == 1
    assert metrics["span_fp"] == 1
    assert metrics["span_fn"] == 1
    assert metrics["span_precision"] == pytest.approx(0.5)
    assert metrics["span_recall"] == pytest.approx(0.5)
    assert metrics["span_f1"] == pytest.approx(0.5)


def test_evidence_low_iou_does_not_match() -> None:
    records = [evidence_record("a", None, [(0, 10)])]
    predictions = {"a": prediction("a", label=None, spans=[{"start": 9, "end": 30}])}
    metrics = evaluate_evidence(records, predictions)
    assert metrics["span_tp"] == 0
    assert metrics["span_precision"] == 0.0


def pico_record(record_id: str, spans: list[tuple[str, int, int]]) -> dict:
    return {
        "record_id": record_id,
        "dataset": "ebm_nlp",
        "task": "pico_span",
        "gold": {"label": None, "spans": [{"kind": "pico_span", "element": e, "start": s, "end": t, "text": "x"} for e, s, t in spans]},
    }


def test_pico_token_f1_per_element() -> None:
    records = [pico_record("a", [("participants", 0, 5), ("interventions", 10, 12)])]
    predictions = {
        "a": prediction(
            "a",
            spans=[
                {"element": "participants", "start": 0, "end": 3},
                {"element": "interventions", "start": 10, "end": 12},
            ],
        )
    }
    metrics = evaluate_pico(records, predictions)
    participants = metrics["elements"]["participants"]
    assert participants["tp"] == 3
    assert participants["fn"] == 2
    assert participants["precision"] == 1.0
    assert participants["recall"] == pytest.approx(0.6)
    assert participants["f1"] == pytest.approx(0.75)
    assert metrics["elements"]["interventions"]["f1"] == 1.0
    assert metrics["elements"]["outcomes"]["f1"] == 0.0
    assert metrics["record_exact"] == 0


def test_pico_exact_record() -> None:
    records = [pico_record("a", [("outcomes", 4, 8)])]
    predictions = {"a": prediction("a", spans=[{"element": "outcomes", "start": 4, "end": 8}])}
    metrics = evaluate_pico(records, predictions)
    assert metrics["record_exact"] == 1
    assert metrics["macro_f1"] == pytest.approx((0 + 0 + 1) / 3, abs=1e-4)


def test_evaluate_dispatches_and_reports_unknown_ids() -> None:
    records = [numeric_record("r1", [("intervention_mean", "intervention", 10.0)])]
    predictions = [prediction("r1", cells=[]), prediction("unbekannt", cells=[])]
    metrics = evaluate("yun2024", records, predictions)
    assert metrics["task"] == "numeric_extraction"
    assert metrics["unknown_prediction_ids"] == ["unbekannt"]
    assert metrics["unknown_prediction_count"] == 1


def test_evaluate_rejects_unknown_dataset_and_task() -> None:
    record = numeric_record("r1", [])
    record["task"] = "unbekannte_aufgabe"
    with pytest.raises(ValueError):
        evaluate("gibt_es_nicht", [record], [])
