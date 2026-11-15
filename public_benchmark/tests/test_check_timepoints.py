"""Tests fuer die Offline-Pruefung der Messzeitpunkte."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "extended_benchmark"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from check_timepoints import pruefe_zeitpunkte, rang  # noqa: E402

TEXT = "Measurements at baseline, 3 months follow-up and 12 months follow-up. Total 0-12 months: 64."


def test_rang_ordnet_baseline_monate_und_total() -> None:
    assert rang("baseline") == 0.0
    assert rang("3 months follow-up") == 3.0
    assert rang("12-month follow-up") == 12.0
    assert rang("6 weeks") == 6 * 7 / 30.44
    assert rang("Total 0-12 months") == 999.0
    assert rang("running text") is None


def test_pruefe_zeitpunkte_erkennt_spaeter_verworfenen_zeitpunkt() -> None:
    result = pruefe_zeitpunkte({"chosen": "3 months follow-up", "discarded": ["12 months follow-up"]}, TEXT)
    assert result["chosen_belegt"] is True
    assert result["spaeter_verworfen"] == ["12 months follow-up"]
    assert result["discarded_unbelegt"] == []


def test_pruefe_zeitpunkte_meldet_erfundenes_label() -> None:
    result = pruefe_zeitpunkte({"chosen": "48 weeks follow-up", "discarded": ["baseline"]}, TEXT)
    assert result["chosen_belegt"] is False
    assert result["spaeter_verworfen"] == []


def test_pruefe_zeitpunkte_ohne_discarded_ist_kein_widerspruch() -> None:
    result = pruefe_zeitpunkte({"chosen": "Total 0-12 months", "discarded": []}, TEXT)
    assert result["chosen_belegt"] is True
    assert result["chosen_rang"] == 999.0
    assert result["spaeter_verworfen"] == []
    assert result["discarded_belegt"] == {}
