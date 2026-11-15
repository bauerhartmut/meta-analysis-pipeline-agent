"""Tests des Kandidaten-Splits (woertlicher Beleg je Goldzelle)."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import candidate_split as cs  # noqa: E402


def test_findet_deutsche_und_englische_schreibweise() -> None:
    text = "Der Wert lag bei 50,6 gm und in der Tabelle bei 50.6 gm."
    funde = cs.finde(text, 50.6)
    assert {f["variante"] for f in funde} == {"50.6", "50,6"}
    assert text[funde[0]["position"] : funde[0]["position"] + 4] == "50,6"


def test_findet_minus_mit_leerzeichen() -> None:
    text = "the patients fed WA (- 0.7 gm) (p = 0.08)."
    funde = cs.finde(text, -0.7)
    assert funde and funde[0]["variante"] == "- 0.7"


def test_findet_tausendertrennzeichen() -> None:
    text = "940 (34%) were hospitalised in unit A, and 1,831 (66%) in unit B."
    assert cs.finde(text, 1831)
    assert cs.finde(text, 1831)[0]["variante"] == "1,831"


def test_kein_treffer_innerhalb_groesserer_zahlen() -> None:
    text = "Es waren 130 und 30.5 und 1.230 Faelle."
    assert cs.finde(text, 30) == []
    assert cs.finde(text, 230) == []


def test_fenster_zeigt_die_umgebung() -> None:
    text = "xxxxx the mean body weight gain was 50.6 gm in those given WGJ xxxxx"
    fund = cs.finde(text, 50.6)[0]
    assert "50.6 gm" in fund["fenster"]
    assert fund["region"] in ("Kurzfassung", "Hauptteil", "unbestimmt")


def test_gerundet_wird_nur_als_naehe_gemeldet() -> None:
    name, fund = cs.finde_gerundet("Der Wert betrug 7 Punkte.", 6.8)
    assert name == "Ganzzahl"
    assert fund is not None
    assert cs.finde_gerundet("Der Wert betrug 6.8 Punkte.", 6.8)[0] == ""
