#!/usr/bin/env python3
"""Sperrbegriffe für Export und Quellprüfung — eine Quelle für beide Skripte.

`scripts/check_export.py` (Gate im Export-Repository) und
`scripts/build_export.py` (Export-Bau und Scan im Quellbaum) importieren die
Liste von hier, damit sie nicht auseinanderlaufen kann.

Die Muster werden absichtlich zusammengesetzt: so erkennt dieses Modul sich
selbst nicht als Treffer, obwohl die Begriffe darin stehen.
"""

from __future__ import annotations

import re

BANNED_TERMS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Alte Forschungsagenda",
        re.compile(
            r"(?i)\b(?:eu"
            + r"geni\w*|embr"
            + r"yo\w*|herit"
            + r"ab\w*|poly"
            + r"genic|pol"
            + r"derman|pg"
            + r"t-[am])\b"
        ),
    ),
    (
        "Alte Forschungsagenda (Wilson)",
        re.compile(
            r"(?i)wil"
            + r"son[- ]?effekt|wil"
            + r"son effect|wil"
            + r"son_effect"
        ),
    ),
    (
        "Private Infrastruktur",
        re.compile(
            r"(?i)\bngr"
            + r"ok\b|raspberr"
            + r"y|research-agent-fine"
            + r"tune|\b192\.168\.\d+\.\d+\b"
        ),
    ),
]


def finde_sperrbegriffe(text: str) -> list[tuple[str, int, str]]:
    """Liefert (Kategorie, Zeilennummer, Zeilenauszug) für jeden Treffer."""
    treffer: list[tuple[str, int, str]] = []
    for zeilennummer, zeile in enumerate(text.splitlines(), 1):
        for name, pattern in BANNED_TERMS:
            if pattern.search(zeile):
                treffer.append((name, zeilennummer, zeile.strip()[:80]))
    return treffer
