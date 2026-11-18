"""Synchroner Retry-Manager fuer einzelne Aufrufe, ohne Netz testbar.

Der Manager beantwortet genau eine Frage: *diesen* Aufruf noch einmal versuchen
oder nicht? Er kennt keine Prompts, keine Dateien und keinen Zustand. Die
Wartezeit kommt aus `Retry-After`, wenn der Anbieter sie mitschickt, sonst aus
einem gedeckelten Backoff mit Jitter.

Bewusst **nicht** enthalten (Begruendung: `docs/internal/reliability_analyse.md`,
Abschnitt 3a und P1): kein Timeout-Faktor, keine getrennten Verbindungs- und
Lesezeitgrenzen, keine eigene Timeout-Behandlung. Ein Timeout ist eine
temporaere Transportstoerung wie jede andere und bekommt denselben Versuch mit
demselben Zeitlimit; in den vorhandenen Laeufen war genau ein Fall betroffen.

Der Manager arbeitet auf Transportebene: eine Antwort mit Inhalt gilt als
gelungen, auch wenn `work` den Inhalt spaeter als kaputtes JSON verwirft. Ob der
Inhalt verwertbar ist, entscheidet nicht der Manager.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import fehlerklassen


@dataclass(frozen=True)
class RetryPolicy:
    """Grenzen eines Aufrufs.

    `max_delay_s` deckelt auch ein `Retry-After`: ein Header mit 3.600 s soll
    einen Lauf nicht blockieren, sondern nach dem Deckel erneut fragen.
    """

    max_versuche: int = 3
    timeout_s: float = 300.0
    basis_s: float = 2.0
    faktor: float = 2.0
    max_delay_s: float = 60.0
    jitter: float = 0.25


STANDARD = RetryPolicy()


def wartezeit(
    versuch: int,
    retry_after: float | None = None,
    policy: RetryPolicy = STANDARD,
    *,
    zufall: Callable[[], float] = random.random,
) -> float:
    """Sekunden bis zum naechsten Versuch nach dem gescheiterten `versuch`.

    `versuch` zaehlt ab 1. `retry_after` hat Vorrang vor dem Backoff; beide
    Wege enden bei `policy.max_delay_s`.
    """
    if versuch < 1:
        raise ValueError("versuch beginnt bei 1")
    if retry_after is not None and retry_after > 0:
        return round(min(float(retry_after), policy.max_delay_s), 3)
    basis = min(policy.basis_s * (policy.faktor ** (versuch - 1)), policy.max_delay_s)
    gestreut = basis * (1 + policy.jitter * (2 * zufall() - 1))
    return round(min(max(gestreut, 0.0), policy.max_delay_s), 3)


def fuehre_aus(
    aufruf: Callable[[float], dict[str, Any]],
    policy: RetryPolicy = STANDARD,
    *,
    schlafe: Callable[[float], None] = time.sleep,
    zufall: Callable[[], float] = random.random,
    melde: Callable[[str, int, float], None] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Ruft `aufruf(timeout_s)` und wiederholt nur temporaere Fehler.

    Gibt `(letzte Antwort, Versuchsspur)` zurueck. Die Spur hat je Versuch einen
    Eintrag aus `fehlerklassen.versuch_eintrag`; `wartete_s` steht an dem
    Versuch, der auf die Wartezeit folgte. Endgueltige Klassen (auth, ungueltige
    Anfrage, Budget im Reasoning) beenden die Schleife sofort.
    """
    versuche: list[dict[str, Any]] = []
    antwort: dict[str, Any] = {}
    # Die Wartezeit gehoert zu dem Versuch, der nach ihr startet; der erste
    # Versuch hat nie gewartet.
    warte: float | None = None
    for nummer in range(1, policy.max_versuche + 1):
        antwort = aufruf(policy.timeout_s)
        klasse = fehlerklassen.klassifiziere(
            antwort,
            "",
            1 if (antwort.get("content") or "").strip() else 0,
        )
        versuche.append(
            fehlerklassen.versuch_eintrag(
                len(versuche) + 1, "http", antwort, klasse, wartete_s=warte
            )
        )
        if not fehlerklassen.ist_temporaer(klasse) or nummer == policy.max_versuche:
            break
        warte = wartezeit(nummer, antwort.get("retry_after"), policy, zufall=zufall)
        if melde is not None:
            melde(klasse, nummer, warte)
        schlafe(warte)
    return antwort, versuche
