"""Tests fuer die regelbasierte Pruefung (validate_predictions.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.validate_predictions import pruefe_ereignisse, pruefe_lauf  # noqa: E402


def test_markiert_ereignisse_ueber_gruppengroesse() -> None:
    hinweise = pruefe_ereignisse(
        {
            ("intervention_events", "intervention"): 130.0,
            ("intervention_group_size", "intervention"): 120.0,
        }
    )
    assert list(hinweise) == ["intervention_events|intervention"]
    assert "groesser als Gruppengroesse" in hinweise["intervention_events|intervention"]


def test_markiert_nichts_bei_plausibler_zelle() -> None:
    hinweise = pruefe_ereignisse(
        {
            ("intervention_events", "intervention"): 48.0,
            ("intervention_group_size", "intervention"): 133.0,
        }
    )
    assert hinweise == {}


def test_markiert_negative_ereigniszahl() -> None:
    hinweise = pruefe_ereignisse(
        {
            ("comparator_events", "comparator"): -3.0,
            ("comparator_group_size", "comparator"): 100.0,
        }
    )
    assert "negative" in hinweise["comparator_events|comparator"]


def test_pruefe_lauf_korrigiert_nichts(tmp_path: Path) -> None:
    predictions = [
        {
            "record_id": "r1",
            "model": "m",
            "predicted": {"cells": [
                {"field": "intervention_events", "arm": "intervention", "value": 130.0},
                {"field": "intervention_group_size", "arm": "intervention", "value": 120.0},
            ]},
        }
    ]
    (tmp_path / "predictions.jsonl").write_text(
        "\n".join(json.dumps(row) for row in predictions) + "\n", encoding="utf-8"
    )
    records = [
        {
            "record_id": "r1",
            "gold": {"cells": [
                {"field": "intervention_events", "arm": "intervention", "value": 12.0},
                {"field": "intervention_group_size", "arm": "intervention", "value": 120.0},
            ]},
        }
    ]
    ergebnis = pruefe_lauf(tmp_path, records)
    assert ergebnis["markierungen"] == 1
    assert ergebnis["korrigiert"] is False
    # Die Vorhersagedatei bleibt unangetastet.
    nachher = (tmp_path / "predictions.jsonl").read_text(encoding="utf-8")
    assert "130.0" in nachher
