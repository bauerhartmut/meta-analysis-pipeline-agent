#!/usr/bin/env python3
"""Gemeinsamer Zahlabgleich fuer Fehleranalyse und Zellvalidierung.

Ein Ort fuer die Frage "steht dieser Wert so im Text". Vorher hatte
`fehlerursachen_20261121.py` eine aeltere, engere Fassung: sie verwarf 14.2 in
"14.20", 48 in "48.0" und 48 in "48." am Satzende und zaehlte damit zu viele
Werte als "nicht im Text". Beide Skripte nutzen jetzt diese Funktion.

Regeln:

* Punkt oder Komma als Dezimaltrenner,
* nachlaufende Nullen erlaubt (14.2 passt auf 14.20),
* ganzzahlige Zelle passt auf 48.0, nicht auf 48.5,
* Ziffern davor und danach duerfen nicht angrenzen (48 passt nicht auf 148),
* Satzpunkt ist kein Zahlbestandteil (48. passt auf die Zahl 48).

Das Vorzeichen wird nicht geprueft: gefragt ist, ob die Zahl im Text steht,
nicht ob sie dort mit demselben Vorzeichen steht.
"""
from __future__ import annotations

import re


def zahl_positionen(wert: float | None, text: str) -> list[int]:
    """Alle Fundstellen der gedruckten Form von `wert`; leer, wenn sie fehlt."""
    if wert is None or not text:
        return []
    kurz = f"{wert:.6f}".rstrip("0").rstrip(".")
    ganz, _, dez = kurz.partition(".")
    if dez:
        muster = rf"(?<![\d.,]){re.escape(ganz)}[.,]{re.escape(dez)}0*(?![\d])"
    else:
        muster = rf"(?<![\d.,]){re.escape(ganz)}(?![.,]\d*[1-9])(?![\d])"
    return [m.start() for m in re.finditer(muster, text)]


def zahl_im_text(wert: float | None, text: str) -> bool:
    return bool(zahl_positionen(wert, text))
