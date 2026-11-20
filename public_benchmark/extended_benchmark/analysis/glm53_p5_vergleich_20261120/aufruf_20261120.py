#!/usr/bin/env python
"""Eine Stelle fuer die Lesezeit der Modellaufrufe.

`run_extended_extraction._call_once` liest mit fester Socket-Lesezeit von 300 s.
Ein Aufruf mit 16.632 Completion-Tokens kann laenger rechnen - gemessen 542,86 s
auf yun2024:421 -, und ein Gateway-Abbruch kann sogar nach acht Minuten kommen
(504). Beide Analyse-Runner setzten dafuer denselben Monkeypatch; er steht jetzt
nur noch hier.

Die Retry-Logik von `rx.call` bleibt unberuehrt: getauscht wird ausschliesslich
die Lesezeit je HTTP-Versuch.

Aufruf im Runner:

    with lesezeit(args.timeout):
        antwort = rx.call(modell, prompt, key, base, attempts=3)
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import run_extended_extraction as rx  # noqa: E402

#: Lesezeit, die `rx._call_once` ohne Eingriff benutzt.
STANDARD_LESEZEIT = 300.0


@contextlib.contextmanager
def lesezeit(sekunden: float) -> Iterator[None]:
    """Setzt die Socket-Lesezeit je HTTP-Versuch fuer die Dauer des Blocks."""
    einmal = rx._call_once
    rx._call_once = lambda m, p, k, b, timeout=sekunden: einmal(m, p, k, b, timeout=timeout)
    try:
        yield
    finally:
        rx._call_once = einmal
