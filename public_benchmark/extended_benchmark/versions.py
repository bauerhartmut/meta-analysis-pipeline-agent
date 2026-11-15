"""Kanonische Prompt-Versionen fuer Auswertungen.

Die Laeufe tragen historisch unterschiedliche Bezeichnungen fuer dieselbe
Prompt-Fassung (z. B. ``v2b_cachebuster`` und ``v2_timepoint``). Damit
Vergleiche nicht an String-Unterschieden scheitern, bildet dieses Modul jede
Schreibweise auf einen kanonischen Namen ab. Die Rohdaten der Laeufe bleiben
unveraendert; die Zuordnung ist hier fest und getestet.

Der Cache-Zusatz ``_cb`` wird entfernt, weil er nur die Generierung betrifft
und kein eigener Prompt ist. Ob ein Lauf aus dem Cache kam, steht getrennt in
``elapsed_s``/``suspected_cache``.
"""

from __future__ import annotations

# Rohbezeichnung (ohne Cache-Suffix) -> kanonische Version
ALIASE = {
    "v1": "v1",
    "v2_timepoint": "v2_timepoint",
    "v2b_cachebuster": "v2_timepoint",
    "v3_abs_count": "v3_abs_count",
}

KANONISCH = ("v1", "v2_timepoint", "v3_abs_count")

BESCHREIBUNG = {
    "v1": "ohne Zeitpunktangabe",
    "v2_timepoint": "Zeitpunkt im Prompt (Standard)",
    "v3_abs_count": "Zeitpunkt plus absolute Ereigniszahlen",
}


def normalisiere_version(raw: str | None, fallback: str = "unbekannt") -> str:
    """Bildet eine Rohbezeichnung auf die kanonische Version ab."""
    if not raw:
        return fallback
    text = raw.strip()
    if text.endswith("_cb"):
        text = text[:-3]
    return ALIASE.get(text, text)
