"""Tests der Zeitpunkt-Regel (Sprint 48).

Die Regel bindet nur, wenn der Zielzeitpunkt im Outcome **und** derselbe
Zeitpunkt im Spaltenkopf gedruckt steht. Fehlt eine Seite, entsteht keine
Bindung - kein Rat aus Position, Tabelle oder Goldwert.
"""

from __future__ import annotations

from dataclasses import replace

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


class _Zeile:
    def __init__(self, row_id: int, label: str) -> None:
        self.row_id = row_id
        self.label = label
        self.group_label = ""
        self.label_path = (label,) if label else ()


class _Tabelle:
    table_id = "T1"

    def __init__(self, zeilen) -> None:
        self.rows = zeilen

    def row(self, row_id: int):
        return next(z for z in self.rows if z.row_id == row_id)


def _zeitpunkt_tabelle() -> _Tabelle:
    return _Tabelle([
        _Zeile(0, "Visit 5: 15-min onset of action"),
        _Zeile(1, "7 min"),
        _Zeile(2, "Visit 3B: 16-hour persistence of action"),
        _Zeile(3, "7 min"),
    ])


def test_zeilenlabel_und_gruppe_werden_getrennt_gelesen():
    tabelle = _zeitpunkt_tabelle()

    zeitpunkt, gruppe = zp.zeilen_angaben(tabelle, 1)
    assert zeitpunkt == ["7 min"]
    assert gruppe == ["visit 5"]


def test_gruppe_scheidet_gleiche_zeitpunkte():
    tabelle = _zeitpunkt_tabelle()
    stellen = [_stelle(""), _stelle("")]
    stellen[0] = replace(stellen[0], tabelle="T1", zeile=1, wert=1.0)
    stellen[1] = replace(stellen[1], tabelle="T1", zeile=3, wert=2.0)
    ziel = zp.ziele("itching at visit 3B, 7 min")

    ohne_gruppe = zp.gebunden(stellen, ziel, [tabelle], mit_gruppe=False)
    mit_gruppe = zp.gebunden(stellen, ziel, [tabelle])
    assert [s.wert for s in ohne_gruppe] == [1.0, 2.0]
    assert [s.wert for s in mit_gruppe] == [2.0]


def test_stellen_ohne_outcome_zeitpunkt_bleiben_leer():
    orte = {"intervention_mean": [_stelle("baseline")]}

    assert zp.stellen(orte, {"outcome": "FPG"}) == {}
    assert zp.stellen(orte, {"outcome": "FPG at baseline"})
