"""Tests fuer Versionsetikett und Zellklassen der Rueckfall-Auswertung."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import run_extended_extraction as runner  # noqa: E402
from extended_benchmark.evaluate_fallback import klassifiziere  # noqa: E402


def test_kaputtes_json_wird_wiederholt() -> None:
    """Strukturell unlesbares JSON gilt als Ausfall, eine leere Zellenliste nicht."""
    assert runner.json_kaputt("kein_json")
    assert runner.json_kaputt("kein_objet")
    assert runner.json_kaputt("json_fehler: Expecting ',' delimiter")
    assert not runner.json_kaputt("")
    assert not runner.json_kaputt("keine_zellen")
    assert not runner.json_kaputt("keine_verwertbaren_zellen")


def test_lauf_ohne_annotation_heisst_nicht_v6() -> None:
    ohne = runner.bestimme_version(fallback=True, target="")
    assert ohne == runner.PROMPT_VERSION == "v2_timepoint"
    mit = runner.bestimme_version(fallback=True, target="Post-test")
    assert mit == "v6_target_fallback"


def test_cache_suffix_und_vorrang_der_flags() -> None:
    assert runner.bestimme_version(fallback=True, target="Post-test", cache_buster=True) == "v6_target_fallback_cb"
    assert runner.bestimme_version(absolute_counts=True, target="Post-test") == "v3_abs_count"
    assert runner.bestimme_version(last_timepoint=True, target="Post-test") == "v4_last_timepoint"
    assert runner.bestimme_version(target_timepoint=True, target="") == "v2_timepoint"
    assert runner.bestimme_version(target_timepoint=True, target="Post-test") == "v5_target_timepoint"


def test_zellen_ohne_zeitpunkt_sind_eigene_klasse() -> None:
    assert klassifiziere("post-test", "post-test") == "zieltreu"
    assert klassifiziere("post-test", "") == "ohne_zeitpunkt"
    assert klassifiziere("post-test", "follow up after 4 months") == "rueckfall"
    assert klassifiziere("", "post-test") == "ohne_ziel"
    assert klassifiziere("", "") == "ohne_ziel"
