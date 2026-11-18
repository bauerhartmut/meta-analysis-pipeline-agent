"""Tests fuer die Aufblaehungsmessung an erfolgreichen Zeilen."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import messe_aufblaehung as ma  # noqa: E402


def _zeile(rid: str, zellen: list[dict], fehler: str = "") -> dict:
    return {
        "record_id": rid,
        "model": "glm",
        "fehlerklasse": fehler,
        "failed": False,
        "predicted": {"cells": zellen},
    }


def test_messe_zaehlt_die_aufblaehung() -> None:
    zeilen = [
        # eindeutig: ein Zeitpunkt je Feld/Arm
        _zeile("a", [{"field": "intervention_mean", "arm": "intervention", "value": 0.77,
                      "timepoint": "30 days"}]),
        # mehrdeutig: derselbe Feld/Arm-Schluessel, zwei Zeitpunkte
        _zeile("b", [
            {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "30 days"},
            {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "60 days"},
        ]),
        # ohne Zellen: zaehlt nicht als erfolgreiche Zeile
        _zeile("c", []),
    ]
    records = {
        "a": {"record_id": "a", "gold": {"cells": [
            {"field": "intervention_mean", "arm": "intervention", "value": 0.77}]}},
        "b": {"record_id": "b", "gold": {"cells": [
            {"field": "comparator_mean", "arm": "comparator", "value": 0.04}]}},
        "c": {"record_id": "c", "gold": {"cells": [
            {"field": "x", "arm": "intervention", "value": 1.0}]}},
    }

    werte = ma.messe(zeilen, records)

    assert werte["zeilen"] == 2
    assert werte["goldzellen"] == 2
    assert werte["adressiert"] == 2
    assert werte["adressiert_streng"] == 1
    assert werte["aufblaehung"] == 1
    assert werte["betroffene_zeilen"] == 1
    assert werte["verteilung"] == {"0": 1, "1": 1}
    assert werte["groesste"][0]["record_id"] == "b"
    assert werte["zeitpunkt_mehrdeutig"] == 1


def test_messe_zaehlt_ok_als_erfolg() -> None:
    zeilen = [_zeile("a", [{"field": "f", "arm": "intervention", "value": 1.0}], fehler="ok")]
    records = {"a": {"record_id": "a", "gold": {"cells": [
        {"field": "f", "arm": "intervention", "value": 1.0}]}}}
    assert ma.messe(zeilen, records)["zeilen"] == 1


def test_bericht_nennt_die_grenze() -> None:
    werte = ma.messe(
        [_zeile("a", [{"field": "f", "arm": "intervention", "value": 1.0, "timepoint": "30 days"}])],
        {"a": {"record_id": "a", "gold": {"cells": [
            {"field": "f", "arm": "intervention", "value": 1.0}]}}},
    )
    text = ma.bericht(werte)
    assert "Untergrenze" in text
    assert "Aufblähung" in text
