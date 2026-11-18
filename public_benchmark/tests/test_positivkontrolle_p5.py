"""Tests fuer die Positivkontrolle der P5-Auswertung.

Die Sollwerte in `positivkontrolle_p5.ERWARTET` sind von Hand aus dem Fixture
gerechnet. Diese Tests belegen, dass die Auswertung sie trifft und dass die
Kontrolle eine falsche Zahl auch wirklich meldet.
"""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import positivkontrolle_p5 as pk  # noqa: E402


def test_positivkontrolle_trifft_alle_sollwerte() -> None:
    assert pk.pruefe(pk.werte()) == []


def test_kontrolle_hat_jede_kategorie_genau_einmal() -> None:
    werte = pk.werte()
    assert werte["status"] == {
        "gerettet": 5,
        "fertig_ohne_zellen": 1,
        "weiter_ausfall": 1,
        "fehlt": 1,
    }
    assert set(werte["nach_klasse"]) == {"length_ohne_ergebnis", "json_kaputt"}


def test_grosszuegige_und_strenge_zaehlung_gehen_auseinander() -> None:
    werte = pk.werte()
    assert werte["adressiert"] - werte["adressiert_zeitpunkt"] == 1
    assert werte["wertgleich"] - werte["wertgleich_zeitpunkt"] == 1
    assert werte["zeitpunkt_mehrdeutig"] == 1


def test_abweichung_wird_gemeldet() -> None:
    werte = pk.werte()
    werte["adressiert"] = 999
    abweichungen = pk.pruefe(werte)
    assert any("adressiert" in text for text in abweichungen)


def test_bericht_nennt_das_ergebnis() -> None:
    werte = pk.werte()
    text = pk.bericht(werte, [], Path("a/alt.jsonl"), Path("a/neu.jsonl"))
    assert "stimmen" in text
    assert "`zellen_neu_mit_zeitpunkt`" in text
    assert "`wertgleich_zeitpunkt`" in text


def test_zellbilanz_trifft_die_sollwerte() -> None:
    b = pk.werte()["zellbilanz"]
    assert (b["tp"], b["fp"], b["fn"]) == (5, 3, 6)
    assert (b["precision"], b["recall"], b["f1"]) == (0.625, 0.454545, 0.526316)


def test_dublette_zaehlt_als_falsch_positiv_nicht_als_treffer() -> None:
    b = pk.werte()["zellbilanz"]
    # k3 nennt denselben Schluessel zweimal: ein Treffer, eine falsch positive
    # Zelle. Ohne die 1:1-Zuordnung waere fp hier 2 und tp 6.
    assert b["ueberzaehlig"] == 3
    assert b["fremdschluessel"] == 0


def test_record_ohne_gold_bleibt_aussen_vor() -> None:
    werte = pk.werte()
    assert werte["zellen_ohne_gold"] == 1
    assert sum(e["zellen_neu"] for e in werte["nicht_bewertbar"]) == 1


def test_bilanzabweichung_wird_gemeldet() -> None:
    werte = pk.werte()
    werte["zellbilanz"]["fp"] = 99
    assert any("zellbilanz.fp" in text for text in pk.pruefe(werte))
