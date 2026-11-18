"""Tests fuer die P5-Auswertung: Rettung, Zellgewinn, Golddeckung, 653 getrennt."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import werte_p5_aus as p5  # noqa: E402


def _alt(rid: str) -> dict:
    return {
        "record_id": rid,
        "model": "glm",
        "fehlerklasse": "length_ohne_ergebnis",
        "failed": True,
        "completion_tokens": 8000,
        "predicted": {"cells": []},
    }


def _neu(rid: str, zellen: list[dict], fehler: str = "", tokens: int = 20000) -> dict:
    return {
        "record_id": rid,
        "model": "glm",
        "fehlerklasse": fehler,
        "failed": bool(fehler),
        "completion_tokens": tokens,
        "reasoning_chars": 50000,
        "predicted": {"cells": zellen},
    }


def _record(rid: str, gold: list[tuple[str, str, float | None]]) -> dict:
    return {
        "record_id": rid,
        "gold": {
            "cells": [
                {"field": f, "arm": a, "value": v} for f, a, v in gold
            ]
        },
    }


GOLD_A = [
    ("intervention_mean", "intervention", 0.77),
    ("comparator_mean", "comparator", 0.04),
    ("intervention_group_size", "intervention", 251.0),
    ("comparator_group_size", "comparator", 246.0),
]


def _bestand() -> tuple[list[dict], list[dict], dict[str, dict]]:
    alt = [_alt("a"), _alt("b"), _alt("c"), _alt("d")]
    neu = [
        _neu("a", [
            {"field": "intervention_mean", "arm": "intervention", "value": 0.77},
            {"field": "comparator_mean", "arm": "comparator", "value": 0.05},
        ]),
        _neu("b", [], fehler="length_ohne_ergebnis"),
        _neu("c", [{"field": "intervention_mean", "arm": "intervention", "value": 1.0}]),
        # d fehlt im neuen Lauf
    ]
    records = {
        "a": _record("a", GOLD_A),
        "b": _record("b", [("intervention_mean", "intervention", 1.0),
                           ("comparator_mean", "comparator", 2.0)]),
        "c": _record("c", []),
        "yun2024:653": _record("yun2024:653", []),
    }
    return alt, neu, records


def test_status_und_zellgewinn() -> None:
    alt, neu, records = _bestand()
    werte = p5.auswerten(alt, neu, records)

    assert werte["grundgesamtheit"] == 4
    assert werte["status"] == {"gerettet": 2, "fertig_ohne_zellen": 0, "weiter_ausfall": 1, "fehlt": 1}
    assert werte["zellen_alt"] == 0
    assert werte["zellen_neu"] == 3
    assert werte["zellgewinn"] == 3


def test_golddeckung_auf_den_bewertbaren() -> None:
    alt, neu, records = _bestand()
    werte = p5.auswerten(alt, neu, records)

    assert [e["record_id"] for e in werte["bewertbar"]] == ["a", "b"]
    assert werte["goldzellen_bewertbar"] == 6
    assert werte["adressiert"] == 2  # intervention_mean und comparator_mean aus a
    assert werte["wertgleich"] == 1  # nur 0.77 stimmt, 0.05 gegen 0.04 nicht


def test_653_getrennt_als_nicht_bewertbar() -> None:
    alt = [_alt("yun2024:653")]
    neu = [_neu("yun2024:653", [{"field": "intervention_mean", "arm": "intervention", "value": 5}])]
    werte = p5.auswerten(alt, neu, {"yun2024:653": _record("yun2024:653", [])})

    assert werte["bewertbar"] == []
    assert werte["nicht_bewertbar"][0]["record_id"] == "yun2024:653"
    assert werte["nicht_bewertbar"][0]["status"] == "gerettet"
    assert werte["goldzellen_bewertbar"] == 0
    assert werte["adressiert"] == 0  # zaehlt nicht gegen die Goldzellen der anderen
    assert werte["zellen_neu"] == 1


def test_fertig_ohne_zellen_ist_keine_rettung() -> None:
    alt = [_alt("x")]
    neu = [_neu("x", [])]
    werte = p5.auswerten(alt, neu, {"x": _record("x", [("intervention_mean", "intervention", 1.0)])})
    assert werte["status"]["fertig_ohne_zellen"] == 1
    assert werte["status"]["gerettet"] == 0


def test_ok_ist_kein_ausfall() -> None:
    zeile = {"record_id": "x", "model": "glm", "failed": False, "fehlerklasse": "ok",
             "predicted": {"cells": [{"field": "f", "arm": "intervention", "value": 1.0}]}}
    assert p5.status(zeile) == "gerettet"


def test_mehrdeutiger_zeitpunkt_faellt_aus_der_strengen_zaehlung() -> None:
    gold = [
        {"field": "intervention_mean", "arm": "intervention", "value": 0.77},
        {"field": "comparator_mean", "arm": "comparator", "value": 0.04},
    ]
    vorhergesagt = [
        {"field": "intervention_mean", "arm": "intervention", "value": 0.77, "timepoint": "30 days"},
        # derselbe Feld/Arm-Schluessel zweimal, verschiedene Zeitpunkte
        {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "30 days"},
        {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "60 days"},
    ]
    assert p5.deckung(gold, vorhergesagt) == (2, 2)
    assert p5.deckung_mit_zeitpunkt(gold, vorhergesagt) == (1, 1)
    assert p5.mehrdeutig(vorhergesagt) == 1


def test_schreibweise_gilt_nicht_als_mehrdeutig() -> None:
    gold = [{"field": "f", "arm": "intervention", "value": 1.0}]
    vorhergesagt = [
        {"field": "f", "arm": "intervention", "value": 1.0, "timepoint": " 30 Days "},
        {"field": "f", "arm": "intervention", "value": 1.0, "timepoint": "30 days"},
    ]
    assert p5.mehrdeutig(vorhergesagt) == 0
    assert p5.deckung_mit_zeitpunkt(gold, vorhergesagt) == (1, 1)


def test_fehlender_zeitpunkt_ist_eindeutig() -> None:
    gold = [{"field": "f", "arm": "intervention", "value": 1.0}]
    vorhergesagt = [{"field": "f", "arm": "intervention", "value": 1.0}]
    assert p5.mehrdeutig(vorhergesagt) == 0
    assert p5.deckung_mit_zeitpunkt(gold, vorhergesagt) == (1, 1)


def test_auswertung_weist_beide_varianten_aus() -> None:
    alt = [_alt("a")]
    neu = [_neu("a", [
        {"field": "intervention_mean", "arm": "intervention", "value": 0.77, "timepoint": "30 days"},
        {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "60 days"},
        {"field": "comparator_mean", "arm": "comparator", "value": 0.04, "timepoint": "90 days"},
    ])]
    records = {
        "a": {"record_id": "a", "gold": {"cells": [
            {"field": "intervention_mean", "arm": "intervention", "value": 0.77},
            {"field": "comparator_mean", "arm": "comparator", "value": 0.04},
        ]}}
    }
    werte = p5.auswerten(alt, neu, records)

    assert werte["adressiert"] == 2
    assert werte["adressiert_zeitpunkt"] == 1
    assert werte["wertgleich"] == 2
    assert werte["wertgleich_zeitpunkt"] == 1
    assert werte["zeitpunkt_mehrdeutig"] == 1
    assert werte["goldzellen_mit_zeitpunkt"] == 0
    assert werte["zellen_neu_mit_zeitpunkt"] == 3

    text = p5.bericht(werte, "neu.jsonl", nullprobe=False)
    assert "eindeutiger Zeitpunkt" in text
    assert "Abweichung:" in text
    assert "adressiert +eindeutiger ZP" in text


def test_bericht_nennt_offene_und_gerettete() -> None:
    alt, neu, records = _bestand()
    text = p5.bericht(p5.auswerten(alt, neu, records), "neu.jsonl", nullprobe=False)
    assert "Rettungsquote auf den **2 bewertbaren**" in text
    assert "`a`" in text and "weiter ausgefallen" in text
    assert "Nicht bewertbar" in text
    assert "Beide Zaehlungen stimmen ueberein" in text


def test_aufteilung_nach_ursprungsklasse() -> None:
    alt = [_alt("a"), {**_alt("b"), "fehlerklasse": "json_kaputt"}]
    neu = [
        _neu("a", [{"field": "intervention_mean", "arm": "intervention", "value": 0.77}]),
        _neu("b", [], fehler="json_kaputt"),
    ]
    gold = {"a": _record("a", [("intervention_mean", "intervention", 0.77)])}

    werte = p5.auswerten(alt, neu, gold, ids=["a", "b"])
    klassen = werte["nach_klasse"]

    assert set(klassen) == {"length_ohne_ergebnis", "json_kaputt"}
    gerettet = klassen["length_ohne_ergebnis"]
    assert (gerettet["ids"], gerettet["technisch"], gerettet["auswertbar"]) == (1, 1, 1)
    assert (gerettet["adressiert"], gerettet["wertgleich"]) == (1, 1)
    kaputt = klassen["json_kaputt"]
    assert (kaputt["ids"], kaputt["technisch"], kaputt["weiter_ausfall"]) == (1, 0, 1)


def test_drei_stufen_bleiben_getrennt() -> None:
    alt = [_alt("a"), _alt("b"), _alt("c")]
    neu = [
        _neu("a", [{"field": "intervention_mean", "arm": "intervention", "value": 0.77}]),
        _neu("b", []),
        _neu("c", [], fehler="length_ohne_ergebnis"),
    ]
    gold = {
        "a": _record("a", [("intervention_mean", "intervention", 0.77),
                           ("comparator_mean", "comparator", 0.04)]),
        "b": _record("b", []),
        "c": _record("c", []),
    }

    stufen = p5.auswerten(alt, neu, gold, ids=["a", "b", "c"])["stufen"]

    assert stufen == {
        "ids": 3,
        "technisch": 2,
        "auswertbar": 1,
        "inhaltlich": 1,
        "inhaltlich_zeitpunkt": 1,
    }


def test_ids_ohne_altzeile_werden_gemeldet() -> None:
    werte = p5.auswerten([_alt("a")], [_neu("a", [])], {}, ids=["a", "z"])
    assert werte["ids_ohne_altzeile"] == ["z"]
    assert werte["grundgesamtheit"] == 1


def test_bericht_nennt_stufen_klassen_und_schaetzung() -> None:
    alt = [_alt("a")]
    neu = [_neu("a", [{"field": "intervention_mean", "arm": "intervention", "value": 0.77}])]
    gold = {"a": _record("a", [("intervention_mean", "intervention", 0.77)])}
    text = p5.bericht(p5.auswerten(alt, neu, gold, ids=["a"]), "x/predictions.jsonl", False)

    assert "adressierte IDs" in text
    assert "Drei Stufen der Rettung" in text
    assert "Nach urspruenglicher Fehlerklasse" in text
    assert "kein gemessener Erfolg" in text
    assert "`length_ohne_ergebnis` | 1 |" in text


def _marke_schreiben(pfad: Path, ok: bool = True, alter_s: int = 0, nonce: str = "") -> Path:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps({"ok": ok, "nonce": nonce}), encoding="utf-8")
    zeit = time.time() - alter_s
    os.utime(pfad, (zeit, zeit))
    return pfad


def test_marke_fehlt_gilt_als_nicht_belegt(tmp_path: Path) -> None:
    ok, text = p5.pruefe_marke(tmp_path / "fehlt.json")
    assert not ok
    assert "keine Marke" in text


def test_frische_marke_ist_gueltig(tmp_path: Path) -> None:
    ok, text = p5.pruefe_marke(_marke_schreiben(tmp_path / "ok.json", True, 10), 600)
    assert ok
    assert "gueltig" in text


def test_marke_ohne_erfolg_gilt_als_nicht_belegt(tmp_path: Path) -> None:
    assert not p5.pruefe_marke(_marke_schreiben(tmp_path / "ok.json", False))[0]


def test_alte_marke_gilt_als_nicht_belegt(tmp_path: Path) -> None:
    ok, text = p5.pruefe_marke(_marke_schreiben(tmp_path / "ok.json", True, 1200), 600)
    assert not ok
    assert "alt" in text


def test_kaputte_marke_gilt_als_nicht_belegt(tmp_path: Path) -> None:
    pfad = tmp_path / "ok.json"
    pfad.write_text("{kein json", encoding="utf-8")
    assert not p5.pruefe_marke(pfad)[0]


def test_main_ohne_marke_schreibt_keinen_bericht(tmp_path: Path, monkeypatch) -> None:
    md = tmp_path / "bericht.md"
    js = tmp_path / "bericht.json"
    monkeypatch.setattr(sys, "argv", [
        "werte_p5_aus.py", "--md", str(md), "--json", str(js),
        "--kontrolle-marke", str(tmp_path / "fehlt.json"),
    ])
    assert p5.main() == 3
    assert not md.exists()
    assert not js.exists()


def test_marke_mit_fremdem_nonce_wird_abgelehnt(tmp_path: Path) -> None:
    pfad = _marke_schreiben(tmp_path / "ok.json", True, 5, "fremd")
    ok, text = p5.pruefe_marke(pfad, 600, nonce="meins")
    assert not ok
    assert "Nonce" in text


def test_marke_mit_passendem_nonce_ist_gueltig(tmp_path: Path) -> None:
    pfad = _marke_schreiben(tmp_path / "ok.json", True, 5, "meins")
    assert p5.pruefe_marke(pfad, 600, nonce="meins")[0]


def test_main_ohne_nonce_verweigert_trotz_gueltiger_marke(tmp_path: Path, monkeypatch) -> None:
    marke = _marke_schreiben(tmp_path / "ok.json", True, 5, "gleich")
    md = tmp_path / "bericht.md"
    monkeypatch.setattr(sys, "argv", [
        "werte_p5_aus.py", "--md", str(md), "--kontrolle-marke", str(marke),
    ])
    assert p5.main() == 3
    assert not md.exists()
