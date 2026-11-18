"""Tests der Zeitpunkt-Regel (Sprint 48).

Die Regel bindet nur, wenn der Zielzeitpunkt im Outcome **und** derselbe
Zeitpunkt im Spaltenkopf gedruckt steht. Fehlt eine Seite, entsteht keine
Bindung - kein Rat aus Position, Tabelle oder Goldwert.
"""

from __future__ import annotations

import pytest

from research_agent.table_decomposition import zeitpunkt as zp
from research_agent.table_decomposition.provenienz import Provenienz


def _stelle(zeitpunkt: str, wert: float = 1.2) -> Provenienz:
    return Provenienz(
        feld="intervention_mean", quelle="messzelle", text=str(wert),
        wert=wert, arm="intervention", arm_basis="header_treffer",
        zeitpunkt=zeitpunkt, art="direkt", regel="spaltenfeld",
        sicherheit="hoch", tabelle="T1", zeile=1, spalten=[1],
    )


def test_zielzeitpunkt_wird_aus_dem_outcome_gelesen():
    assert zp.ziele("ocular itching for visit 3B at 7 min") == ["7 min", "visit 3b"]
    assert zp.ziele("FPG") == []


def test_bindung_braucht_den_zeitpunkt_im_spaltenkopf():
    ziel = zp.ziele("change in FPG at week 8")

    gebunden = zp.gebunden([_stelle("week 8"), _stelle("")], ziel)
    assert len(gebunden) == 1
    assert gebunden[0].arm_basis == "zeitpunkt:week 8"


def test_ohne_zielzeitpunkt_keine_bindung():
    assert zp.gebunden([_stelle("week 8")], zp.ziele("FPG")) == []


def test_stellen_ohne_outcome_zeitpunkt_bleiben_leer():
    orte = {"intervention_mean": [_stelle("baseline")]}

    assert zp.stellen(orte, [], {"outcome": "FPG"}) == {}
    assert zp.stellen(orte, [], {"outcome": "FPG at baseline"})
