"""Offline-Tests fuer den Retry-Manager: kein Netz, keine echte Wartezeit.

Alle Szenarien laufen ueber injizierte Aufrufe und eine mitgeschriebene
`schlafe`-Funktion; `zufall` ist festgelegt, damit die Grenzen pruefbar sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import retry_manager  # noqa: E402


def _antwort(klasse: str, **felder) -> dict:
    """Baut eine Antwort, die `klassifiziere` in die gewuenschte Klasse legt."""
    basis = {"http_status": 200, "content": '{"cells": []}', "finish_reason": "stop", "error": ""}
    if klasse == "ok":
        pass
    elif klasse == "budget_im_reasoning":
        basis.update(http_status=200, content="", finish_reason="length", completion_tokens=8000)
    elif klasse == "json_kaputt":
        basis.update(http_status=200, content="kein json")
    elif klasse == "rate_limit":
        basis.update(http_status=429, content="")
    elif klasse == "server_fehler":
        basis.update(http_status=503, content="", error="HTTPError 503")
    elif klasse == "auth":
        basis.update(http_status=401, content="")
    elif klasse == "timeout":
        basis.update(http_status=0, content="", error="TimeoutError: The read operation timed out")
    elif klasse == "verbindungsfehler":
        basis.update(http_status=0, content="", error="URLError: connection reset")
    else:
        raise AssertionError(f"unbekannte Testklasse {klasse}")
    basis.update(felder)
    return basis


class _Protokoll:
    """Merkt sich Aufrufe und Wartezeiten, statt zu schlafen."""

    def __init__(self, antworten: list[dict]) -> None:
        self.antworten = antworten
        self.aufrufe: list[float] = []
        self.gewertet: list[float] = []
        self.meldungen: list[tuple[str, int, float]] = []

    def aufruf(self, timeout: float) -> dict:
        self.aufrufe.append(timeout)
        index = min(len(self.aufrufe) - 1, len(self.antworten) - 1)
        return dict(self.antworten[index])

    def schlafe(self, sekunden: float) -> None:
        self.gewertet.append(sekunden)

    def melde(self, klasse: str, nummer: int, warte: float) -> None:
        self.meldungen.append((klasse, nummer, warte))

    def ausfuehren(self, **policy) -> tuple[dict, list[dict]]:
        return retry_manager.fuehre_aus(
            self.aufruf,
            retry_manager.RetryPolicy(**policy),
            schlafe=self.schlafe,
            zufall=lambda: 0.5,
            melde=self.melde,
        )


def test_erfolg_im_ersten_versuch_ohne_wartezeit() -> None:
    p = _Protokoll([_antwort("ok")])
    antwort, versuche = p.ausfuehren()
    assert len(p.aufrufe) == 1
    assert p.gewertet == []
    assert [v["fehlerklasse"] for v in versuche] == ["ok"]
    assert versuche[0]["temporaer"] is False
    assert antwort["http_status"] == 200


def test_erfolg_im_zweiten_versuch_nach_serverfehler() -> None:
    p = _Protokoll([_antwort("server_fehler"), _antwort("ok")])
    _, versuche = p.ausfuehren()
    assert len(p.aufrufe) == 2
    # Basisbackoff nach Versuch 1 mit Jitter 0,5 ist unveraendert 2,0 s.
    assert p.gewertet == [2.0]
    assert [v["fehlerklasse"] for v in versuche] == ["server_fehler", "ok"]
    # Die Wartezeit traegt der Versuch, der nach ihr startet.
    assert versuche[0]["wartete_s"] is None
    assert versuche[1]["wartete_s"] == 2.0


def test_retry_after_hat_vorrang_vor_backoff() -> None:
    p = _Protokoll([_antwort("rate_limit", retry_after=7.0), _antwort("ok")])
    _, versuche = p.ausfuehren()
    assert p.gewertet == [7.0]
    assert versuche[1]["wartete_s"] == 7.0


def test_retry_after_wird_auf_den_deckel_begrenzt() -> None:
    p = _Protokoll([_antwort("rate_limit", retry_after=3600.0), _antwort("ok")])
    p.ausfuehren(max_delay_s=60.0)
    assert p.gewertet == [60.0]


def test_dauerhafter_serverfehler_endet_nach_dem_letzten_versuch() -> None:
    p = _Protokoll([_antwort("server_fehler")])
    antwort, versuche = p.ausfuehren(max_versuche=3)
    assert len(p.aufrufe) == 3
    assert len(p.gewertet) == 2  # nach dem letzten Versuch wird nicht mehr gewartet
    assert antwort["http_status"] == 503
    assert [v["attempt_id"] for v in versuche] == [1, 2, 3]
    assert versuche[-1]["fehlerklasse"] == "server_fehler"


def test_timeout_wird_wiederholt_ohne_eigene_mechanik() -> None:
    # Kein Timeout-Faktor: jeder Versuch bekommt dasselbe Zeitlimit.
    p = _Protokoll([_antwort("timeout"), _antwort("timeout"), _antwort("ok")])
    _, versuche = p.ausfuehren()
    assert p.aufrufe == [300.0, 300.0, 300.0]
    assert [v["fehlerklasse"] for v in versuche] == ["timeout", "timeout", "ok"]


def test_verbindungsabbruch_wird_wiederholt() -> None:
    p = _Protokoll([_antwort("verbindungsfehler"), _antwort("ok")])
    _, versuche = p.ausfuehren()
    assert len(p.aufrufe) == 2
    assert versuche[0]["temporaer"] is True


def test_endgueltige_klassen_werden_nicht_wiederholt() -> None:
    for klasse in ("auth", "budget_im_reasoning", "ok"):
        p = _Protokoll([_antwort(klasse)])
        _, versuche = p.ausfuehren()
        assert len(p.aufrufe) == 1, klasse
        assert p.gewertet == [], klasse
        assert len(versuche) == 1, klasse


def test_budget_im_reasoning_kostet_keinen_zweiten_aufruf() -> None:
    p = _Protokoll([_antwort("budget_im_reasoning")])
    antwort, versuche = p.ausfuehren()
    assert len(p.aufrufe) == 1
    assert versuche[0]["fehlerklasse"] == "budget_im_reasoning"
    assert versuche[0]["temporaer"] is False
    assert antwort["completion_tokens"] == 8000


def test_backoff_waechst_und_bleibt_unter_dem_deckel() -> None:
    policy = retry_manager.RetryPolicy(basis_s=2.0, faktor=2.0, max_delay_s=10.0, jitter=0.0)
    reihe = [retry_manager.wartezeit(n, None, policy, zufall=lambda: 0.5) for n in (1, 2, 3, 4, 5)]
    assert reihe == [2.0, 4.0, 8.0, 10.0, 10.0]


def test_jitter_bleibt_in_seinen_grenzen() -> None:
    policy = retry_manager.RetryPolicy(basis_s=4.0, max_delay_s=60.0, jitter=0.25)
    assert retry_manager.wartezeit(1, None, policy, zufall=lambda: 0.0) == 3.0
    assert retry_manager.wartezeit(1, None, policy, zufall=lambda: 1.0) == 5.0
    # Oberhalb des Deckels darf auch der Jitter nichts drauflegen.
    assert retry_manager.wartezeit(5, None, policy, zufall=lambda: 1.0) == 60.0


def test_versuchsnummer_muss_ab_eins_zaehlen() -> None:
    try:
        retry_manager.wartezeit(0)
    except ValueError:
        return
    raise AssertionError("versuch 0 muss abgelehnt werden")


def test_meldung_nennt_klasse_versuch_und_wartezeit() -> None:
    p = _Protokoll([_antwort("rate_limit", retry_after=3.0), _antwort("ok")])
    p.ausfuehren()
    assert p.meldungen == [("rate_limit", 1, 3.0)]
