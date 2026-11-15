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


def test_baseline_gewinnt_nicht_bei_ergebniszellen() -> None:
    from extended_benchmark.annotate_timepoints import zeitpunkt_aus_text

    text = "Baseline values were 4.2 points. " + " Fülltext. " * 40 + "At week 24 the value was 6.5 points."
    gold = text.index("4.2")
    # Ohne Ergebniszellen ist baseline erlaubt (naechste Angabe).
    assert zeitpunkt_aus_text(text, [gold], hat_ergebnis=False)["target"] == "baseline"
    # Mit Ergebniszellen darf baseline nicht gewinnen.
    info = zeitpunkt_aus_text(text, [gold], hat_ergebnis=True)
    assert info["target"] == "week 24"


def test_nur_baseline_und_ergebniszellen_bleibt_leer() -> None:
    from extended_benchmark.annotate_timepoints import zeitpunkt_aus_text

    text = "Baseline characteristics were recorded."
    info = zeitpunkt_aus_text(text, [0], hat_ergebnis=True)
    assert info["target"] == ""
    assert info["status"].startswith("not stated")


def test_satz_der_goldzahl_geht_vor_naehe() -> None:
    from extended_benchmark.annotate_timepoints import zeitpunkt_aus_text

    text = (
        "At month 12 the score was 3.1 points. "
        + " Fülltext. " * 30
        + "The 5.6 value appears here without a timepoint."
    )
    info = zeitpunkt_aus_text(text, [text.index("5.6"), text.index("3.1")], hat_ergebnis=True)
    assert info["target"] == "month 12"
    assert "Satz der Goldzahl" in info["status"]


def test_zeitpunkt_naeher_an_der_goldzahl_gewinnt() -> None:
    from extended_benchmark.annotate_timepoints import zeitpunkt_aus_text

    text = "All variables were measured at baseline." + " Fülltext. " * 60 + "At week 12 the score was 4.2 points."
    gold = text.index("4.2")
    info = zeitpunkt_aus_text(text, [gold])
    assert info["target"] == "week 12"
    assert info["status"].startswith("auto")
    assert "week 12" in info["evidence"]


def test_zeitpunkt_null_wird_baseline() -> None:
    from extended_benchmark.annotate_timepoints import zeitpunkt_aus_text

    text2 = "Week 0 values: 5 points."
    assert zeitpunkt_aus_text(text2, [text2.index("5 points")])["target"] == "baseline"
    text3 = "Week 4 values: 5 points."
    assert zeitpunkt_aus_text(text3, [text3.index("5 points")])["target"] == "week 4"


def test_ohne_zeitpunktangabe_gibt_es_kein_ziel() -> None:
    from extended_benchmark.annotate_timepoints import zeitpunkt_aus_text

    info = zeitpunkt_aus_text("Es wurden 30 Patienten eingeschlossen.", [11])
    assert info["target"] == ""
    assert info["status"] == "not stated"


def test_gerundet_wird_nur_als_naehe_gemeldet() -> None:
    name, fund = cs.finde_gerundet("Der Wert betrug 7 Punkte.", 6.8)
    assert name == "Ganzzahl"
    assert fund is not None
    assert cs.finde_gerundet("Der Wert betrug 6.8 Punkte.", 6.8)[0] == ""
