"""Tests fuer die zentrale Fehlereinordnung.

Der Datentest in `test_befund_der_lesekopie` prueft die Abnahmebedingung aus
`docs/internal/reliability_analyse.md`: die 104 Ausfallzeilen des GLM-Laufs
muessen als 103 x Budget im Reasoning und 1 x Timeout herauskommen.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import fehlerklassen  # noqa: E402

LESEKOPIE = BENCH / "extended_benchmark" / "runs" / "_lesekopie_20261118" / "predictions.jsonl"


def _antwort(**felder) -> dict:
    basis = {
        "http_status": 200,
        "content": "",
        "finish_reason": "stop",
        "completion_tokens": 900,
        "reasoning_chars": 0,
        "elapsed_s": 1.0,
        "error": "",
    }
    basis.update(felder)
    return basis


def test_erfolg_und_leere_antwort_sind_verschieden() -> None:
    mit_zellen = _antwort(content='{"cells": [1]}', completion_tokens=800)
    ohne_zellen = _antwort(content='{"cells": []}', completion_tokens=800)
    assert fehlerklassen.klassifiziere(mit_zellen, "", 1) == "ok"
    assert fehlerklassen.klassifiziere(ohne_zellen, "keine_zellen", 0) == "leer"
    # Beide sind keine Fehlzeile: nichts ist technisch schiefgegangen.
    assert fehlerklassen.zeilen_klasse("ok") == ""
    assert fehlerklassen.zeilen_klasse("leer") == ""


def test_abgeschnittene_antwort_ist_budget_im_reasoning() -> None:
    # Genau der Fall der 103 Zeilen: 200, finish_reason length, kein Inhalt.
    antwort = _antwort(finish_reason="length", completion_tokens=8000, reasoning_chars=32448)
    assert fehlerklassen.klassifiziere(antwort, "kein_json", 0) == "budget_im_reasoning"
    assert fehlerklassen.ist_temporaer("budget_im_reasoning") is False
    # Kompatibler Zeilenname, damit Auswertung und Nachzug weiter lesen.
    assert fehlerklassen.zeilen_klasse("budget_im_reasoning") == "length_ohne_ergebnis"


def test_abgeschnitten_aber_mit_zellen_gilt_als_erfolg() -> None:
    antwort = _antwort(finish_reason="length", completion_tokens=8000, reasoning_chars=20000)
    assert fehlerklassen.klassifiziere(antwort, "", 3) == "ok"


def test_transportfehler_werden_nicht_mehr_als_json_kaputt_gefuehrt() -> None:
    # Der bisherige Fehlerpfad: Timeout -> leere Antwort -> `kein_json` -> json_kaputt.
    assert fehlerklassen.klassifiziere({"http_status": 0, "error": "kein_json"}, "kein_json", 0) == "verbindungsfehler"
    assert fehlerklassen.klassifiziere({"http_status": 0, "error": "TimeoutError: The read operation timed out"}, "kein_json", 0) == "timeout"
    assert fehlerklassen.ist_temporaer("timeout") is True


def test_http_fehler_bekommen_eigene_klassen() -> None:
    assert fehlerklassen.klassifiziere({"http_status": 429}, "kein_json", 0) == "rate_limit"
    assert fehlerklassen.klassifiziere({"http_status": 503}, "kein_json", 0) == "server_fehler"
    assert fehlerklassen.klassifiziere({"http_status": 401}, "", 0) == "auth"
    assert fehlerklassen.klassifiziere({"http_status": 400}, "", 0) == "anfrage_ungueltig"
    for klasse in ("rate_limit", "server_fehler"):
        assert fehlerklassen.ist_temporaer(klasse) is True
    for klasse in ("auth", "anfrage_ungueltig"):
        assert fehlerklassen.ist_temporaer(klasse) is False


def test_jede_klasse_ist_erreichbar_und_hat_einen_zeilenwert() -> None:
    befunde = {
        fehlerklassen.klassifiziere(_antwort(content='{"cells": [1]}', finish_reason="length"), "", 1),
        fehlerklassen.klassifiziere(_antwort(), "keine_zellen", 0),
        fehlerklassen.klassifiziere({"http_status": 0, "error": "timed out"}, "", 0),
        fehlerklassen.klassifiziere({"http_status": 0, "error": "URLError: reset"}, "", 0),
        fehlerklassen.klassifiziere({"http_status": 429}, "", 0),
        fehlerklassen.klassifiziere({"http_status": 500}, "", 0),
        fehlerklassen.klassifiziere({"http_status": 403}, "", 0),
        fehlerklassen.klassifiziere({"http_status": 422}, "", 0),
        fehlerklassen.klassifiziere(_antwort(finish_reason="length"), "kein_json", 0),
        fehlerklassen.klassifiziere(_antwort(content="nicht json"), "kein_json", 0),
    }
    assert befunde == set(fehlerklassen.KLASSEN)
    for klasse in fehlerklassen.KLASSEN:
        assert isinstance(fehlerklassen.zeilen_klasse(klasse), str)


def test_unbekannte_klasse_wird_nicht_still_akzeptiert() -> None:
    try:
        fehlerklassen.ist_temporaer("gibt_es_nicht")
    except KeyError:
        return
    raise AssertionError("unbekannte Klasse muss abgelehnt werden")


def test_versuch_eintrag_haelt_dauer_tokens_und_klasse() -> None:
    antwort = _antwort(finish_reason="length", completion_tokens=8000, reasoning_chars=32448, elapsed_s=42.0)
    eintrag = fehlerklassen.versuch_eintrag(1, "primaer", antwort, "budget_im_reasoning")
    assert eintrag == {
        "attempt_id": 1,
        "rolle": "primaer",
        "http_status": 200,
        "dauer_s": 42.0,
        "wartete_s": None,
        "finish_reason": "length",
        "completion_tokens": 8000,
        "reasoning_chars": 32448,
        "content_chars": 0,
        "fehlerklasse": "budget_im_reasoning",
        "temporaer": False,
    }


def test_befund_der_lesekopie() -> None:
    """Abnahmebedingung: 103 x Budget im Reasoning, 1 x Timeout."""
    if not LESEKOPIE.exists():
        return  # Sicherung nicht im Arbeitsbaum; der Test ist dann gegenstandslos.
    zaehler: Counter[str] = Counter()
    for zeile in LESEKOPIE.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        row = json.loads(zeile)
        if row.get("model") != "glm" or not row.get("fehlerklasse"):
            continue
        zaehler[
            fehlerklassen.klassifiziere(row, row.get("parse_error") or "", len(row.get("rows") or []))
        ] += 1
    assert zaehler == {"budget_im_reasoning": 103, "timeout": 1}
