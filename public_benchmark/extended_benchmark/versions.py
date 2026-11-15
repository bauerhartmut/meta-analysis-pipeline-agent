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
    "v4_last_timepoint": "v4_last_timepoint",
    "v5_target_timepoint": "v5_target_timepoint",
    "v6_target_fallback": "v6_target_fallback",
}

KANONISCH = (
    "v1",
    "v2_timepoint",
    "v3_abs_count",
    "v4_last_timepoint",
    "v5_target_timepoint",
    "v6_target_fallback",
)

BESCHREIBUNG = {
    "v1": "ohne Zeitpunktangabe",
    "v2_timepoint": "Zeitpunkt im Prompt (vorherige Referenz)",
    "v3_abs_count": "Zeitpunkt plus absolute Ereigniszahlen",
    "v4_last_timepoint": "letzter berichteter Messzeitpunkt, Zeitpunkte mitgeliefert",
    "v5_target_timepoint": "Zielzeitpunkt je Record als Vorgabe",
    "v6_target_fallback": "Zielzeitpunkt mit Rueckfall auf naechsten berichteten Zeitpunkt",
}

# Rolle einer Version in der Auswertung. "verworfen" heisst: im Dev-Lauf
# schlechter als die Referenz, nicht mehr Standard; Zahlen werden getrennt
# ausgewiesen und nicht mit der Referenz summiert.
STATUS = {
    "v1": "historisch",
    # Seit dem 15.11.2026 ist v6 die Referenz (zwei frische Laeufe, F1 0,944 und
    # 0,963); v2 bleibt als vorherige Referenz und als Text fuer Records ohne
    # Zeitpunkt-Annotation erhalten.
    "v2_timepoint": "historisch",
    "v3_abs_count": "verworfen",
    "v4_last_timepoint": "verworfen",
    "v5_target_timepoint": "verworfen",
    "v6_target_fallback": "referenz",
}


def status_von(version: str) -> str:
    return STATUS.get(version, "unbekannt")


def normalisiere_version(raw: str | None, fallback: str = "unbekannt") -> str:
    """Bildet eine Rohbezeichnung auf die kanonische Version ab."""
    if not raw:
        return fallback
    text = raw.strip()
    if text.endswith("_cb"):
        text = text[:-3]
    return ALIASE.get(text, text)
