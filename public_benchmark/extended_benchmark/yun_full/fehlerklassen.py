"""Eine Stelle fuer die Einordnung eines Aufrufs im Extraktionslauf.

Die Klasse beantwortet zwei Fragen, die bisher getrennt und unterschiedlich
beantwortet wurden: *Was* ist schiefgegangen, und *ob* ein weiterer Versuch
ueberhaupt sinnvoll ist. `temporaer=False` heisst: derselbe Aufruf mit denselben
Mitteln scheitert reproduzierbar, ein Retry kostet nur Tokens.

Die Namen der Zeilenklasse bleiben gegenueber dem Bestand kompatibel; die
feinere Diagnose steht in der Versuchsspur. Grund: `done_keys`, die Auswertung
und `nachzug_ausfaelle.sh` lesen `fehlerklasse` direkt.

Kein Netz, kein Zustand: `klassifiziere` ist eine reine Funktion ueber die
Antwortfelder, die `_call_once` und `work` ohnehin erzeugen.
"""

from __future__ import annotations

from typing import Any

#: Klasse -> ist ein weiterer Versuch sinnvoll?
#:
#: `budget_im_reasoning` ist bewusst nicht temporaer: der Anbieter hat mit 200
#: geantwortet und das Budget war im Reasoning aufgebraucht. Derselbe Aufruf mit
#: demselben Budget endet reproduzierbar gleich (395 abgeschnittene Zeilen in den
#: vorhandenen Laeufen, alle genau an der Grenze).
KLASSEN: dict[str, bool] = {
    "ok": False,
    "leer": False,
    "timeout": True,
    "verbindungsfehler": True,
    "rate_limit": True,
    "server_fehler": True,
    "auth": False,
    "anfrage_ungueltig": False,
    "budget_im_reasoning": False,
    "json_kaputt": True,
}

#: Diagnose -> Wert im Feld `fehlerklasse` der Zeile.
#:
#: Nur die beiden Bestandsnamen bleiben stehen; alles andere ist neu und war im
#: bisherigen Datensatz entweder leer oder falsch einsortiert.
ZEILEN_KLASSE: dict[str, str] = {
    "ok": "",
    "leer": "",
    "budget_im_reasoning": "length_ohne_ergebnis",
}

#: Parse-Fehler, die "keine Zellen, aber lesbare Antwort" bedeuten.
_LEER = {"keine_zellen", "keine_verwertbaren_zellen"}


def klassifiziere(response: dict[str, Any], parse_error: str = "", zellen: int = 0) -> str:
    """Ordnet einen Aufruf genau einer Klasse aus `KLASSEN` zu.

    `response` ist das Ergebnis von `_call_once` (oder `call`), `parse_error`
    das, was `parse_cells` zurueckgab, `zellen` die Anzahl verwertbarer Zellen.
    """
    status = response.get("http_status")
    if status == 200:
        return _klassifiziere_antwort(response, parse_error, zellen)
    if status is None or status == 0:
        return _klassifiziere_transport(response.get("error") or "")
    if status == 429:
        return "rate_limit"
    if isinstance(status, int) and 500 <= status <= 599:
        return "server_fehler"
    if status in (401, 403):
        return "auth"
    if isinstance(status, int) and 400 <= status <= 499:
        return "anfrage_ungueltig"
    # Alles Uebrige (3xx, unerwartete Codes) ist ein Transportproblem.
    return "verbindungsfehler"


def klassifiziere_http(antwort: dict[str, Any]) -> str:
    """Transportebene: eine Antwort mit HTTP 200 ist angekommen.

    Fuer die Frage "noch einmal senden?" zaehlt nur, ob eine Antwort kam — was
    im Inhalt steht, entscheidet `work` mit dem Parse-Ergebnis. Ohne diese
    Trennung muesste der Retry-Manager eine Zellenzahl vortaeuschen.
    """
    if antwort.get("http_status") == 200:
        return "ok"
    return klassifiziere(antwort)


def _klassifiziere_antwort(response: dict[str, Any], parse_error: str, zellen: int) -> str:
    if (response.get("finish_reason") or "") == "length":
        # Abgeschnitten. Nur wenn danach noch Zellen lesbar waren, ist die
        # Antwort verwertbar; sonst hat das Budget den Inhalt gefressen.
        if zellen:
            return "ok"
        return "budget_im_reasoning"
    if json_kaputt(parse_error):
        return "json_kaputt"
    if zellen:
        return "ok"
    return "leer"


def _klassifiziere_transport(fehler: str) -> str:
    text = fehler.lower()
    if "timeout" in text or "timed out" in text:
        return "timeout"
    return "verbindungsfehler"


def json_kaputt(parse_error: str) -> bool:
    """Wahr, wenn die Antwort strukturell kein lesbares JSON war."""
    return parse_error in ("kein_json", "kein_objet") or parse_error.startswith("json_fehler")


def ist_temporaer(klasse: str) -> bool:
    """Ob ein weiterer Versuch mit demselben Aufruf sinnvoll ist."""
    if klasse not in KLASSEN:
        raise KeyError(f"unbekannte Fehlerklasse: {klasse}")
    return KLASSEN[klasse]


def zeilen_klasse(klasse: str) -> str:
    """Wert fuer das Feld `fehlerklasse` der Zeile; leer heisst verwertbar."""
    if klasse not in KLASSEN:
        raise KeyError(f"unbekannte Fehlerklasse: {klasse}")
    return ZEILEN_KLASSE.get(klasse, klasse)


def versuch_eintrag(
    attempt_id: int,
    rolle: str,
    response: dict[str, Any],
    klasse: str,
    *,
    wartete_s: float | None = None,
) -> dict[str, Any]:
    """Ein Eintrag der Versuchsspur.

    `rolle` sagt, welcher Aufruf es war (`primaer`, `json`, `repair`), damit die
    Spur auch dann lesbar bleibt, wenn `response` in der Zeile schon die
    Wiederholung ist.
    """
    return {
        "attempt_id": attempt_id,
        "rolle": rolle,
        "http_status": response.get("http_status"),
        "dauer_s": response.get("elapsed_s"),
        "wartete_s": wartete_s,
        "finish_reason": response.get("finish_reason", ""),
        "completion_tokens": response.get("completion_tokens"),
        "reasoning_chars": response.get("reasoning_chars", 0),
        "content_chars": len(response.get("content") or ""),
        "fehlerklasse": klasse,
        "temporaer": ist_temporaer(klasse),
    }
