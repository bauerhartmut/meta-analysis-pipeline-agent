"""Offline-Tests fuer die Wiederaufnahme nach temporaerem Anbieterausfall.

Kein Netz, keine echte Wartezeit: geprueft werden nur die Entscheidung und die
Grenzen der Wartezeit. Hintergrund ist der P5-Lauf vom 19.11.2026, der 7 von 7
Records ohne einen Token als Ausfall verbucht hat.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import wiederaufnahme  # noqa: E402


@pytest.mark.parametrize("klasse", ["server_fehler", "rate_limit", "timeout", "verbindungsfehler"])
def test_temporaere_klassen_werden_wiederaufgenommen(klasse: str) -> None:
    assert wiederaufnahme.noetig(klasse, 0, 3) is True


@pytest.mark.parametrize(
    "klasse",
    ["auth", "anfrage_ungueltig", "budget_im_reasoning", "ok", "leer", "length_ohne_ergebnis", ""],
)
def test_endgueltige_klassen_werden_nicht_wiederaufgenommen(klasse: str) -> None:
    assert wiederaufnahme.noetig(klasse, 0, 3) is False


def test_grenzen_der_wiederaufnahme() -> None:
    assert wiederaufnahme.noetig("server_fehler", 2, 3) is True
    assert wiederaufnahme.noetig("server_fehler", 3, 3) is False
    assert wiederaufnahme.noetig("server_fehler", 0, 0) is False
    assert wiederaufnahme.noetig("server_fehler", 0, 3, frist_ok=False) is False


def test_wartezeit_waechst_und_ist_gedeckelt() -> None:
    eins = wiederaufnahme.wartezeit(1, 30.0)
    zwei = wiederaufnahme.wartezeit(2, 30.0)
    assert 20.0 <= eins <= 40.0, eins
    assert zwei > eins, (eins, zwei)
    assert wiederaufnahme.wartezeit(50, 30.0) <= wiederaufnahme.DECKEL_S


def test_nummer_muss_bei_eins_beginnen() -> None:
    with pytest.raises(ValueError):
        wiederaufnahme.wartezeit(0, 30.0)
