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
