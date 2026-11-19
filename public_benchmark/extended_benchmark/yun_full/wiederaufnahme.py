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

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Callable, Iterable

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


def abwickeln(
    auftraege: Iterable[tuple[Any, ...]],
    arbeit: Callable[..., dict[str, Any]],
    *,
    threads: int,
    melde: Callable[[str], None] = print,
) -> tuple[int, int]:
    """Arbeitet Auftraege ab und reiht Wiederaufnahmen erneut ein.

    `arbeit` bekommt einen Auftrag als Argumente und gibt ein dict zurueck.
    Traegt es `wiederaufnahme=True`, hat der Auftrag bewusst keine Zeile
    geschrieben und geht erneut in die Schlange, statt die Runde zu beenden.
    Erst der regulaere Rueckgabewert zaehlt als abgeschlossen; eine Ausnahme
    beendet den Lauf nicht, sie wird nur gemeldet.

    Rueckgabe: (abgeschlossene Auftraege, Zahl der Wiederaufnahmen).
    """
    if threads < 1:
        raise ValueError("threads muss mindestens 1 sein")
    fertig = 0
    erneut = 0
    with ThreadPoolExecutor(max_workers=threads) as pool:
        # Die Schlange waechst: ein wiederaufgenommener Auftrag wird erneut
        # eingereiht, statt die Runde zu beenden. `wait` statt `as_completed`,
        # weil nur so neu hinzugefuegte Futures mitlaufen.
        offen = {pool.submit(arbeit, *auftrag): auftrag for auftrag in auftraege}
        while offen:
            erledigt, _ = wait(list(offen), return_when=FIRST_COMPLETED)
            for future in erledigt:
                auftrag = offen.pop(future)
                try:
                    ergebnis = future.result()
                except Exception as fehler:  # noqa: BLE001 - ein Auftrag darf den Lauf nicht beenden
                    melde(f"FEHLER {auftrag}: {fehler}")
                    continue
                if ergebnis.get("wiederaufnahme"):
                    erneut += 1
                    offen[pool.submit(arbeit, *auftrag)] = auftrag
                else:
                    fertig += 1
    return fertig, erneut
