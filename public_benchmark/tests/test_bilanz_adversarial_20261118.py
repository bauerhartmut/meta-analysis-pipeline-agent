"""Adversariale Pruefung von `werte_p5_aus.bilanz()` (Sprint 48).

Ergaenzt die Positivkontrolle um Faelle, die dort nicht vorkommen: vertauschte
Arme, unbekannte Felder, Gold-Dubletten, fehlende Zellen, mehrere Vorhersagen
fuer dieselbe Goldzelle, Zeilen ohne numerischen Wert und Reihenfolge.

Orakel statt Nachrechnen: `_orakel()` zaehlt nicht Zelle fuer Zelle wie
`bilanz()`, sondern gruppiert Gold und Vorhersage nach (Schluessel, Wert) und
nimmt je Gruppe das Minimum. Das ist ein anderer Algorithmus mit demselben Soll
und deckt deshalb Zaehlfehler auf, die eine zweite Schleife in gleicher Bauart
verdecken wuerde.

Das Orakel vergleicht Werte exakt. Alle Fixtures nennen Gold- und
Vorhersagewerte deshalb als dieselbe Zahl; die 1e-6-Toleranz von `bilanz()`
wird nur dort geprueft, wo sie ausdruecklich das Thema ist.
"""

from __future__ import annotations

import itertools
import random
import sys
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import werte_p5_aus as p5  # noqa: E402


def _z(feld: str, arm: str, wert, zeitpunkt: str | None = None) -> dict:
    zelle = {"field": feld, "arm": arm, "value": wert}
    if zeitpunkt is not None:
        zelle["timepoint"] = zeitpunkt
    return zelle


def _zahl(wert) -> float | None:
    try:
        return float(str(wert).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _orakel(gold: list[dict], vorhergesagt: list[dict]) -> dict[str, int]:
    """Unabhaengige Rechnung: Minimum je (Schluessel, Wert)-Gruppe."""
    gold_ohne_wert = sum(1 for z in gold if _zahl(z.get("value")) is None)
    gold_gruppen = Counter(
        (p5.schluessel(z), _zahl(z["value"])) for z in gold if _zahl(z.get("value")) is not None
    )
    vor_gruppen = Counter(
        (p5.schluessel(z), _zahl(z["value"])) for z in vorhergesagt if _zahl(z.get("value")) is not None
    )
    tp = sum(min(gold_gruppen[k], vor_gruppen[k]) for k in gold_gruppen)
    fn = sum(gold_gruppen.values()) - tp
    fp = len(vorhergesagt) - tp
    gold_schluessel = {p5.schluessel(z) for z in gold}
    ueberzaehlig = sum(1 for z in vorhergesagt if p5.schluessel(z) in gold_schluessel) - tp
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "ueberzaehlig": ueberzaehlig,
        "fremdschluessel": fp - ueberzaehlig,
        "goldzellen_ohne_wert": gold_ohne_wert,
    }


GOLD_A = [
    _z("intervention_mean", "intervention", 0.77),
    _z("comparator_mean", "comparator", 0.04),
    _z("intervention_group_size", "intervention", 251),
]


# --- 1 bis 2: Einmaligkeit von Treffer und Verbrauch -------------------------


def test_eine_goldzelle_wird_nur_einmal_getroffen() -> None:
    """Drei identische Vorhersagen auf eine Goldzelle: ein TP, zwei FP."""
    b = p5.bilanz([_z("a", "intervention", 1.0)], [_z("a", "intervention", 1.0)] * 3)

    assert (b["tp"], b["fp"], b["fn"]) == (1, 2, 0)
    assert b["ueberzaehlig"] == 2


def test_eine_vorhersagezelle_wird_nur_einmal_verbraucht() -> None:
    """Gold traegt denselben Schluessel zweimal: die eine Vorhersage trifft einmal."""
    gold = [_z("a", "intervention", 1.0), _z("a", "intervention", 1.0)]
    b = p5.bilanz(gold, [_z("a", "intervention", 1.0)])

    assert (b["tp"], b["fp"], b["fn"]) == (1, 0, 1)


# --- 3 bis 5: die drei Fehlerarten -----------------------------------------


def test_falscher_wert_ist_falsch_positiv_und_fn() -> None:
    b = p5.bilanz([_z("a", "intervention", 0.77)], [_z("a", "intervention", 0.70)])

    assert (b["tp"], b["fp"], b["fn"]) == (0, 1, 1)
    assert (b["ueberzaehlig"], b["fremdschluessel"]) == (1, 0)


def test_vertauschter_arm_zaehlt_als_fremdschluessel() -> None:
    b = p5.bilanz([_z("a", "intervention", 0.77)], [_z("a", "comparator", 0.77)])

    assert (b["tp"], b["fp"], b["fn"]) == (0, 1, 1)
    assert (b["ueberzaehlig"], b["fremdschluessel"]) == (0, 1)


def test_unbekanntes_feld_zaehlt_als_fremdschluessel() -> None:
    b = p5.bilanz([_z("a", "intervention", 0.77)], [_z("x", "intervention", 0.77)])

    assert (b["tp"], b["fp"], b["fn"]) == (0, 1, 1)
    assert b["fremdschluessel"] == 1


# --- 6 bis 8: fehlende Zellen, leere Antwort, nicht bewertbar --------------


def test_fehlende_vorhersage_ist_fn_ohne_fp() -> None:
    b = p5.bilanz(GOLD_A, [_z("intervention_mean", "intervention", 0.77)])

    assert (b["tp"], b["fp"], b["fn"]) == (1, 0, 2)


def test_leere_vorhersage_ist_nur_fn() -> None:
    b = p5.bilanz(GOLD_A, [])

    assert (b["tp"], b["fp"], b["fn"]) == (0, 0, 3)
    quote = p5.quote(b["tp"], b["fp"], b["fn"])
    assert quote["precision"] is None
    assert quote["recall"] == 0.0


def test_record_ohne_gold_zaehlt_weder_tp_noch_fp() -> None:
    alt = [{"record_id": "leer", "model": "glm", "fehlerklasse": "length_ohne_ergebnis",
            "failed": True, "completion_tokens": 8000, "predicted": {"cells": []}},
           {"record_id": "a", "model": "glm", "fehlerklasse": "length_ohne_ergebnis",
            "failed": True, "completion_tokens": 8000, "predicted": {"cells": []}}]
    neu = [{"record_id": "leer", "model": "glm", "fehlerklasse": "", "failed": False,
            "completion_tokens": 900, "predicted": {"cells": [_z("a", "intervention", 1.0)] * 4}},
           {"record_id": "a", "model": "glm", "fehlerklasse": "", "failed": False,
            "completion_tokens": 900, "predicted": {"cells": [_z("a", "intervention", 1.0)]}}]
    records = {"leer": {"record_id": "leer", "gold": {"cells": []}},
               "a": {"record_id": "a", "gold": {"cells": [_z("a", "intervention", 1.0)]}}}

    werte = p5.auswerten(alt, neu, records, ids=["leer", "a"])

    assert werte["zellbilanz"]["records"] == 1
    assert (werte["zellbilanz"]["tp"], werte["zellbilanz"]["fp"]) == (1, 0)
    assert werte["zellen_ohne_gold"] == 4
    assert "nicht als FP gezaehlt" in p5.bericht(werte, "x.jsonl", False)


# --- 9 bis 10: Zeitpunkte und Reihenfolge ----------------------------------


def test_mehrere_zeitpunkte_bleiben_grosszuegig_aber_dubletten_fp() -> None:
    gold = [_z("a", "intervention", 0.77)]
    vorhergesagt = [
        _z("a", "intervention", 0.77, "30 days"),
        _z("a", "intervention", 0.80, "60 days"),
        _z("a", "intervention", 0.77, "60 days"),
    ]
    b = p5.bilanz(gold, vorhergesagt)

    # Wertgleichheit entscheidet, nicht der Zeitpunkt: 1 TP, 2 ueberzaehlige FP.
    assert (b["tp"], b["fp"], b["fn"]) == (1, 2, 0)
    assert b["ueberzaehlig"] == 2
    # Die strenge Zaehlung sieht denselben Fall anders: kein eindeutiger Zeitpunkt.
    assert p5.deckung_mit_zeitpunkt(gold, vorhergesagt) == (0, 0)
    assert p5.mehrdeutig(vorhergesagt) == 1


def test_reihenfolge_von_gold_und_vorhersage_aendert_nichts() -> None:
    gold = [_z("a", "intervention", 0.77), _z("a", "intervention", 0.80),
            _z("b", "comparator", 0.04)]
    vorhergesagt = [_z("a", "intervention", 0.77), _z("a", "intervention", 0.77),
                    _z("b", "comparator", 0.05), _z("a", "comparator", 0.77)]

    soll = _orakel(gold, vorhergesagt)
    ergebnisse = set()
    for g in itertools.permutations(gold):
        for v in itertools.permutations(vorhergesagt):
            b = p5.bilanz(list(g), list(v))
            ergebnisse.add(tuple(sorted(b.items())))
    assert len(ergebnisse) == 1
    assert dict(ergebnisse.pop()) == soll


# --- 11 bis 13: Werte ohne Zahl, Schreibweisen, Gross-/Kleinschreibung ------


def test_goldzelle_ohne_zahl_faellt_raus_vorhersage_bleibt_fp() -> None:
    b = p5.bilanz([_z("a", "intervention", None)], [_z("a", "intervention", 1.0)])

    assert b["goldzellen_ohne_wert"] == 1
    assert (b["tp"], b["fn"]) == (0, 0)
    assert b["fp"] == 1


def test_vorhersage_ohne_zahl_ist_fn_und_fp_zugleich() -> None:
    """Bekannter Schluessel, unlesbarer Wert: die Goldzelle bleibt offen, die Zelle ist FP."""
    b = p5.bilanz([_z("a", "intervention", 1.0)], [_z("a", "intervention", "keine Zahl")])

    assert (b["tp"], b["fp"], b["fn"]) == (0, 1, 1)
    assert b["ueberzaehlig"] == 1


def test_komma_und_leerzeichen_werden_gelesen() -> None:
    b = p5.bilanz([_z("a", "intervention", 0.77)],
                  [_z("a", " Intervention ", "0,77")])

    assert b["tp"] == 1
    assert (b["fp"], b["fn"]) == (0, 0)


def test_feld_grossschreibung_ist_ein_eigener_schluessel() -> None:
    """Befund, kein Soll: Felder werden nicht normalisiert, Arme schon."""
    b = p5.bilanz([_z("Intervention_Mean", "intervention", 0.77)],
                  [_z("intervention_mean", "intervention", 0.77)])

    assert (b["tp"], b["fp"], b["fn"]) == (0, 1, 1)
    assert b["fremdschluessel"] == 1


# --- 14: Orakel gegen Zufallsfixtures --------------------------------------


def test_orakel_stimmt_auf_zufallsfixtures() -> None:
    zufall = random.Random(48)
    felder = ["a", "b", "c"]
    arme = ["intervention", "comparator"]
    werte = [0.5, 1.0, 1.5, None, "0,5"]

    for _ in range(200):
        gold = [
            _z(zufall.choice(felder), zufall.choice(arme), zufall.choice(werte))
            for _ in range(zufall.randint(0, 4))
        ]
        vorhergesagt = [
            _z(zufall.choice(felder), zufall.choice(arme), zufall.choice(werte))
            for _ in range(zufall.randint(0, 5))
        ]
        assert p5.bilanz(gold, vorhergesagt) == _orakel(gold, vorhergesagt), (gold, vorhergesagt)


def test_quote_rechnet_aus_der_bilanz() -> None:
    gold = [_z("a", "intervention", 1.0), _z("b", "comparator", 2.0)]
    vorhergesagt = [_z("a", "intervention", 1.0), _z("c", "intervention", 3.0)]

    b = p5.bilanz(gold, vorhergesagt)
    quote = p5.quote(b["tp"], b["fp"], b["fn"])

    assert (b["tp"], b["fp"], b["fn"]) == (1, 1, 1)
    assert quote == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_zellprotokoll_und_bilanz_stimmen_ueberein() -> None:
    zufall = random.Random(49)
    felder = ["a", "b"]
    arme = ["intervention", "comparator"]
    werte = [0.5, 1.0, None, "0,5"]

    for _ in range(100):
        gold = [_z(zufall.choice(felder), zufall.choice(arme), zufall.choice(werte))
                for _ in range(zufall.randint(0, 4))]
        vorhergesagt = [_z(zufall.choice(felder), zufall.choice(arme), zufall.choice(werte))
                        for _ in range(zufall.randint(0, 5))]
        zeilen = p5.bilanzzellen(gold, vorhergesagt)
        assert p5._summen(zeilen) == p5.bilanz(gold, vorhergesagt)
        assert len(zeilen) == len(gold) + len(vorhergesagt)


def test_zellprotokoll_benennt_die_dublette() -> None:
    zeilen = p5.bilanzzellen([_z("a", "intervention", 1.0)],
                             [_z("a", "intervention", 1.0), _z("a", "intervention", 1.0)])

    gold_zeile = [z for z in zeilen if z["seite"] == "gold"][0]
    vor_zeilen = [z for z in zeilen if z["seite"] == "vorhersage"]
    assert gold_zeile["bewertung"] == "TP"
    assert [z["bewertung"] for z in vor_zeilen] == ["TP", "FP"]
    assert [z["grund"] for z in vor_zeilen] == ["", "ueberzaehlig"]
    assert (vor_zeilen[1]["field"], vor_zeilen[1]["arm"], vor_zeilen[1]["value"]) == (
        "a", "intervention", 1.0
    )


def test_zellprotokoll_gold_ohne_wert_ist_ausser_bilanz() -> None:
    zeilen = p5.bilanzzellen([_z("a", "intervention", None)], [])

    assert zeilen[0]["bewertung"] == "ausser_bilanz"
    assert p5._summen(zeilen)["goldzellen_ohne_wert"] == 1


def test_zellprotokoll_traegt_die_vier_nicht_vorhersage_faelle() -> None:
    """Je Fehlerart die erwartete Zelle: falscher Wert, fremder Arm, fremdes Feld, FN."""
    gold = [_z("a", "intervention", 1.0), _z("b", "comparator", 2.0)]
    vorhergesagt = [
        _z("a", "intervention", 1.5),   # falscher Wert -> FP-wert
        _z("a", "comparator", 1.0),     # falscher Arm -> FP-fremd
        _z("x", "intervention", 9.0),   # fremdes Feld -> FP-fremd
    ]
    zeilen = p5.bilanzzellen(gold, vorhergesagt)
    vor = [z for z in zeilen if z["seite"] == "vorhersage"]

    assert [z["bewertung"] for z in vor] == ["FP", "FP", "FP"]
    assert [z["grund"] for z in vor] == ["ueberzaehlig", "fremdschluessel", "fremdschluessel"]
    assert [z["bewertung"] for z in zeilen if z["seite"] == "gold"] == ["FN", "FN"]
