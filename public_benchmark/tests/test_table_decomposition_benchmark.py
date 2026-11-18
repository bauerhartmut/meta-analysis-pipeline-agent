"""Tests der Benchmark-Werkzeuge der Table-Decomposition-Engine.

Geprueft werden die reinen Funktionen: Zellabgleich (Precision/Recall-Zaehlweise
des Repos), Kostenzuordnung und Berichtsformatierung. Keine Netzzugriffe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "extended_benchmark" / "table_decomposition"))

import evaluate as bench_evaluate  # noqa: E402
import report as bench_report  # noqa: E402


GOLD = [
    {"field": "intervention_group_size", "arm": "intervention", "value": 30.0},
    {"field": "intervention_mean", "arm": "intervention", "value": 50.6},
    {"field": "comparator_group_size", "arm": "comparator", "value": 30.0},
    {"field": "comparator_mean", "arm": "comparator", "value": -0.7},
]


def test_match_record_counts_exact_wrong_missing_and_without_gold():
    predicted = [
        {"field": "intervention_group_size", "arm": "intervention", "value": 30.0},
        {"field": "intervention_mean", "arm": "intervention", "value": 51.0},
        {"field": "comparator_group_size", "arm": "comparator", "value": 30.0},
        {"field": "intervention_events", "arm": "intervention", "value": 4},
    ]
    result = bench_evaluate.match_record(GOLD, predicted)
    assert result["matched"] == 2          # N und comparator N
    assert result["wrong"] == 1            # Mittelwert daneben
    assert result["missing"] == 1          # comparator_mean fehlt
    assert result["without_gold"] == 1     # events hat kein Gold
    arts = sorted(error["art"] for error in result["errors"])
    assert arts == ["falscher_wert", "fehlend", "ohne_gold"]


def test_match_record_detects_arm_swap():
    predicted = [
        {"field": "intervention_group_size", "arm": "intervention", "value": 30.0},
        {"field": "intervention_mean", "arm": "intervention", "value": -0.7},
        {"field": "comparator_group_size", "arm": "comparator", "value": 30.0},
        {"field": "comparator_mean", "arm": "comparator", "value": 50.6},
    ]
    result = bench_evaluate.match_record(GOLD, predicted)
    assert result["arm_swap"] is True
    assert result["wrong"] == 2


def test_evaluate_computes_precision_recall_and_cost():
    records = {
        "yun2024:1": {"record_id": "yun2024:1", "document": {"split": "test"},
                      "context": {}, "gold": {"cells": GOLD}},
    }
    rows = [
        {
            "record_id": "yun2024:1",
            "strategy": "A",
            "model": "test-model",
            "complexity": "mittel",
            "cells": [
                {"field": "intervention_group_size", "arm": "intervention", "value": 30.0,
                 "quote": "30", "row_label": "Weight"},
                {"field": "intervention_mean", "arm": "intervention", "value": 50.6,
                 "quote": "50.6", "row_label": "Weight"},
                {"field": "comparator_group_size", "arm": "comparator", "value": 30.0,
                 "quote": "30", "row_label": "Weight"},
            ],
            "conflicts": [],
            "telemetry": {"prompt_tokens": 1000, "completion_tokens": 200,
                          "runtime_s": 4.0, "errors": 0},
            "validation": {"status": "strukturell_vollstaendig",
                           "counts": {"error": 0},
                           "findings": [{"code": "zeilenlabel_fehlt"}]},
            "unit_results": [{"error": ""}],
        }
    ]
    result = bench_evaluate.evaluate(rows, records, preis_in=0.5, preis_out=1.5)
    data = result["strategies"]["A"]
    assert data["cells"] == {"gold": 4, "richtig": 3, "falsch": 0,
                             "fehlend": 1, "ohne_gold": 0}
    assert data["precision"] == pytest.approx(1.0)
    assert data["recall"] == pytest.approx(0.75)
    assert data["f1"] == pytest.approx(round(2 * 1.0 * 0.75 / 1.75, 4))
    # 1000/1000*0.5 + 200/1000*1.5 = 0.5 + 0.3 = 0.8; je 3 richtige Zellen -> 26.67
    assert data["kosten"] == pytest.approx(0.8, abs=1e-6)
    assert data["kosten_pro_100_richtige_zellen"] == pytest.approx(
        round(0.8 / 3 * 100, 4))
    assert data["kontext"]["zitat_anteil"] == pytest.approx(1.0)
    assert data["je_komplexitaet"]["mittel"]["recall"] == pytest.approx(0.75)
    assert "outcome_zuordnung" in result["nicht_messbar"]


def test_evaluate_counts_per_record_status_and_code_dicts():
    """Modelllauf-Zeilen tragen Status und Codes als Zaehler je Record."""
    records = {
        "yun2024:1": {"record_id": "yun2024:1", "document": {"split": "test"},
                      "context": {}, "gold": {"cells": GOLD[:1]}},
    }
    rows = [{
        "record_id": "yun2024:1", "strategy": "B", "model": "m", "complexity": "mittel",
        "cells": [{"field": "intervention_group_size", "arm": "intervention",
                   "value": 30.0, "quote": "30", "row_label": "Weight"}],
        "conflicts": [],
        "telemetry": {"prompt_tokens": 10, "completion_tokens": 5, "runtime_s": 1.0},
        "validation": {"status": {"strukturell_vollstaendig": 2},
                       "codes": {"zeilenlabel_fehlt": 3},
                       "tables": []},
        "unit_results": [],
    }]
    result = bench_evaluate.evaluate(rows, records, None, None)
    data = result["strategies"]["B"]
    assert data["validierung"]["status"] == {"strukturell_vollstaendig": 2}
    assert data["validierung"]["codes"] == {"zeilenlabel_fehlt": 3}
    assert data["cells"]["richtig"] == 1


def test_report_states_that_model_metrics_are_missing():
    structure = {
        "strategy_summary": {
            "A": {"strategy_label": "Full-Table Extraction", "records": 2, "tables": 2,
                  "tables_complete": 2, "units": 2, "units_per_record": 1.0,
                  "expected_cells": 4, "prompt_chars": 1000, "prompt_chars_per_record": 500.0,
                  "prompt_chars_per_unit": 500.0, "est_tokens": 250,
                  "gold_reachable": 3, "errors": 0, "warnings": 1},
        },
        "hinweise": [],
    }
    selection = {"role": "test", "n_tables": 2, "n_candidates": 9, "n_records": 2,
                 "n_documents": 1, "gold_reachable_total": 3, "frozen": True,
                 "strata_counts": {"mittel": 2}, "records_sha256": "abc"}
    text = bench_report.build_report(structure, [], selection)
    assert "Kein Modelllauf vorhanden" in text
    assert "nicht gemessen" in text
    assert "| A | Full-Table Extraction | 2 | 2 |" in text
    assert "250" in text

    evaluation = {
        "strategies": {
            "A": {
                "strategy_label": "Full-Table Extraction",
                "records": 2,
                "cells": {"gold": 4, "richtig": 3, "falsch": 1, "fehlend": 0, "ohne_gold": 0},
                "precision": 0.75, "recall": 0.75, "f1": 0.75,
                "records_exakt": 1, "arm_tausch_records": 0, "technische_ausfaelle": 0,
                "tokens": {"prompt": 1000, "completion": 200, "gesamt": 1200},
                "runtime_s": 4.0, "kosten": 0.8, "kosten_pro_100_richtige_zellen": 26.6667,
                "je_komplexitaet": {"mittel": {"records": 2, "richtig": 3, "falsch": 1,
                                               "fehlend": 0, "precision": 0.75, "recall": 0.75}},
                "fehlerklassen": {"falscher_wert": 1},
                "validierung": {"status": {"strukturell_vollstaendig": 2},
                                "codes": {"zeilenlabel_fehlt": 1}},
                "kontext": {"zellen": 3, "mit_zitat": 3, "mit_zeilenlabel": 3,
                            "mit_seite": 0, "zitat_anteil": 1.0, "zeilenlabel_anteil": 1.0},
            }
        },
        "nicht_messbar": {"outcome_zuordnung": "kein Outcome im Gold"},
    }
    text = bench_report.build_report(structure, [evaluation], selection)
    assert "| A | Full-Table Extraction | 2 | 3 | 1 | 0 | 0 |" in text
    assert "Kosten/100 richtige Zellen" in text
    assert "outcome_zuordnung" in text
