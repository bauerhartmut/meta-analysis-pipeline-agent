"""Tests fuer Prompt-Versionen im Extraktionsrunner."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import run_extended_extraction as runner  # noqa: E402

RECORD = {"context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "binary"}}


def test_standardversion_ist_v2_timepoint() -> None:
    assert runner.PROMPT_VERSION == "v2_timepoint"
    assert runner.VERSION_ABSOLUTE_COUNTS == "v3_abs_count"


def test_standardprompt_ohne_absolute_counts_zusatz() -> None:
    prompt = runner.build_prompt(RECORD, "Text")
    assert "post-test" in prompt
    assert "never as percentages" not in prompt


def test_flag_schaltet_absolute_counts_zu() -> None:
    prompt = runner.build_prompt(RECORD, "Text", absolute_counts=True)
    assert "never as percentages" in prompt
    assert "post-test" in prompt


def test_letzter_zeitpunkt_ersetzt_die_zeitpunktregel() -> None:
    prompt = runner.build_prompt(RECORD, "Text", last_timepoint=True)
    assert runner.VERSION_LAST_TIMEPOINT == "v4_last_timepoint"
    assert "last time point reported" in prompt
    assert "chosen_timepoint" in prompt and "discarded_timepoints" in prompt
    assert "post-test" not in prompt


def test_zeitpunkt_parser_liest_labels() -> None:
    timepoints, error = runner.parse_timepoints(
        '{"cells": [], "chosen_timepoint": "12 months follow-up", '
        '"discarded_timepoints": ["Baseline", "3 months follow-up"]}'
    )
    assert error == ""
    assert timepoints == {"chosen": "12 months follow-up", "discarded": ["Baseline", "3 months follow-up"]}
    leer, fehler = runner.parse_timepoints('{"cells": []}')
    assert leer["chosen"] == "" and fehler == "kein_zeitpunkt"
    assert runner.parse_timepoints("keine antwort")[1] == "kein_json"
