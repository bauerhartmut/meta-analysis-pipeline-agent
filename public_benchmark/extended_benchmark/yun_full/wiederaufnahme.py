"""Wiederaufnahme eines Auftrags nach einem temporaeren Anbieterausfall.

Der HTTP-Retry in `retry_manager` versucht denselben Aufruf dreimal mit
Sekunden-Backoff. Ein echter Anbieterausfall ueberdauert das: Am 19.11.2026 hat
der P5-Lauf 7 von 7 Records endgueltig als Ausfall verbucht, ohne einen einzigen
Token auszugeben (503 "all instances of glm-5.3 are at max capacity", 429,
Timeout). Bei 103 Ausfaellen waere der Lauf leer durchgelaufen und haette einen
Bericht erzeugt, der die Startwache gegen jeden spaeteren Lauf sperrt.

Dieses Modul entscheidet deshalb auf Auftragsebene, ob ein temporaerer Ausfall
erneut versucht wird, und wie lange davor gewartet wird. Es kennt weder Netze
noch Dateien und ist ohne Lauf testbar.

Endgueltige Klassen werden nie wiederaufgenommen: `auth`, `anfrage_ungueltig` und
`budget_im_reasoning` scheitern mit denselben Mitteln reproduzierbar, ein
weiterer Versuch kostet nur Tokens.
"""

from __future__ import annotations

from . import fehlerklassen, retry_manager

#: Obergrenze einer einzelnen Wartezeit. Ein Anbieter, der Stunden braucht, soll
#: den Lauf nicht stundenlang in einem Auftrag festhalten.
DECKEL_S = 600.0


def noetig(
    diagnose: str,
    bisher: int,
    max_versuche: int,
    frist_ok: bool = True,
) -> bool:
    """Soll der Auftrag nach diesem Ausfall erneut laufen?

    `bisher` ist die Zahl der bereits erfolgten Wiederaufnahmen, `frist_ok`
    sagt, ob die Gesamtfrist des Laufs noch nicht abgelaufen ist. Unbekannte
    Klassen gelten als nicht wiederholbar, statt eine Ausnahme zu werfen: die
    Zeilen der alten Retry-Strategie tragen Werte wie `length_ohne_ergebnis`,
    die es in `fehlerklassen.KLASSEN` nicht gibt.
    """
    if max_versuche <= 0 or not frist_ok or bisher >= max_versuche:
        return False
    if diagnose not in fehlerklassen.KLASSEN:
        return False
    return fehlerklassen.ist_temporaer(diagnose)


def wartezeit(nummer: int, basis_s: float, deckel_s: float = DECKEL_S) -> float:
    """Sekunden vor der `nummer`-ten Wiederaufnahme (Zaehlung ab 1).

    Nutzt den vorhandenen Backoff des Retry-Managers, aber ohne `Retry-After`:
    ein `429` mit "Retry after 1 seconds" ist eine Drossel je Aufruf, keine
    Aussage darueber, wann der Anbieter wieder Kapazitaet hat.
    """
    if nummer < 1:
        raise ValueError("nummer beginnt bei 1")
    policy = retry_manager.RetryPolicy(basis_s=basis_s, max_delay_s=deckel_s)
    return retry_manager.wartezeit(nummer, None, policy)
