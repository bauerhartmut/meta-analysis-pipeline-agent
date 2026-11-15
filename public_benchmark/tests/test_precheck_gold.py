"""Tests der Gold-Vorpruefung (ohne Modellaufrufe)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import precheck_gold as pg  # noqa: E402

FUELL = "Die Studie beschreibt den Verlauf der Erkrankung ausfuehrlich und ohne Zahlen. " * 20

ABSTRACT = (
    "The mean body weight gain was greater among patients receiving WGJ (+ 50.7 gm) "
    "as compared with the patients in the AJ group (+ 18.3 gm) or the patients fed WA "
    "(- 0.7 gm) (p = 0.08). "
)
ERGEBNIS = (
    "The mean body weight gain was also higher among the juice fed patients; there was "
    "a mean weight gain of 18.3 gm in the AJ fed patients and of 50.6 gm in those given "
    "WGJ, whereas there was a mean loss of body weight (- 7.0 gm) among the WA group "
    "patients (p = 0.08). "
)


def zellen(**werte: float) -> list[dict[str, object]]:
    felder = []
    for name, wert in werte.items():
        feld, arm = name.rsplit("__", 1)
        felder.append({"field": feld, "arm": arm, "value": wert})
    return felder


def test_doppelangabe_wird_in_beiden_richtungen_gefunden() -> None:
    text = ABSTRACT + FUELL + ERGEBNIS
    treffer = pg.zahlpaare(
        text,
        "body weight gain",
        zellen(intervention_mean__intervention=50.6, comparator_mean__comparator=-0.7),
    )
    arten = {(t["gold"], t["wert_b"], t["beziehung"]) for t in treffer}
    assert (50.6, 50.7, "Nachkommastelle") in arten
    assert (-0.7, -7.0, "Faktor 10 (Zehnerstelle)") in arten


def test_tabellenzeilen_zaehlen_nicht_als_doppelangabe() -> None:
    tabelle = (
        "::::table-wrap ::: caption Baseline values :::  A 50.6  B 50.7  C 63.1  D 63.3  "
        "E 20.3  F 20.4  G 12.5  H 12.6 "
    )
    treffer = pg.zahlpaare(tabelle + FUELL, "body weight gain", zellen(intervention_mean__intervention=50.6))
    assert treffer == []


def test_standortzahl_wird_erkannt() -> None:
    text = "Among them, 940 (34%) were hospitalised in unit A, and 1,831 (66%) in unit B."
    treffer = pg.standortzahlen(text, zellen(intervention_group_size__intervention=940.0))
    assert len(treffer) == 1
    assert "unit" in treffer[0]["ortswort"]


def test_tabellenspalte_unit_ist_kein_standort() -> None:
    text = "  Parameter   Lemon verbena   Placebo\n  [unit]   (*N* = 20\n"
    treffer = pg.standortzahlen(text, zellen(intervention_group_size__intervention=20.0))
    assert treffer == []


@pytest.mark.parametrize(
    "wert_a, wert_b, dezimal, erwartet",
    [
        (50.6, 50.7, True, "Nachkommastelle"),
        (-0.7, -7.0, True, "Faktor 10 (Zehnerstelle)"),
        (12.5, 12.6, True, ""),
        (20.0, 2.0, False, ""),
    ],
)
def test_beziehung_grenzen(wert_a: float, wert_b: float, dezimal: bool, erwartet: str) -> None:
    assert pg.beziehung(wert_a, wert_b, dezimal_a=dezimal, dezimal_b=dezimal) == erwartet
