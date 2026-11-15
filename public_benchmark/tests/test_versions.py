"""Tests fuer die kanonischen Prompt-Versionen."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.versions import ALIASE, KANONISCH, normalisiere_version  # noqa: E402


def test_alte_und_neue_schreibweise_werden_gleich() -> None:
    assert normalisiere_version("v2b_cachebuster") == "v2_timepoint"
    assert normalisiere_version("v2_timepoint") == "v2_timepoint"


def test_cache_suffix_wird_entfernt() -> None:
    assert normalisiere_version("v2_timepoint_cb") == "v2_timepoint"
    assert normalisiere_version("v3_abs_count_cb") == "v3_abs_count"


def test_v3_bleibt_getrennt() -> None:
    assert normalisiere_version("v3_abs_count") == "v3_abs_count"
    assert normalisiere_version("v3_abs_count_cb") != normalisiere_version("v2_timepoint")


def test_leere_angabe_bekommt_fallback() -> None:
    assert normalisiere_version("") == "unbekannt"
    assert normalisiere_version(None, fallback="v1") == "v1"


def test_unbekannte_schreibweise_bleibt_erhalten() -> None:
    assert normalisiere_version("v9_experiment") == "v9_experiment"


def test_alle_aliase_zeigen_auf_kanonische_namen() -> None:
    assert set(ALIASE.values()) <= set(KANONISCH)
