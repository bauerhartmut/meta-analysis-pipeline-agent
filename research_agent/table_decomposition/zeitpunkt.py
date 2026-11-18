"""Gedruckter Zeitpunkt als Fundstellen-Filter - kein Raten, kein Gold.

Ein Feld kann an mehreren Zeitpunkten gedruckt sein (Baseline gegen Aenderung,
3 min gegen 7 min). Dieses Modul bindet eine Fundstelle nur dann an einen
Zeitpunkt, wenn **beides gedruckt** ist:

1. der Zielzeitpunkt im Text des Outcomes (``ocular itching for visit 3B at
   7 min`` -> ``visit 3b``, ``7 min``),
2. derselbe Zeitpunkt in der Spaltenbeschriftung der Fundstelle
   (``week 8``, ``baseline``, ``day 14``).

Fehlt eine der beiden Seiten, entsteht keine Bindung: ein Zeitpunkt wird nie
aus der Spaltenposition, aus der Tabelle oder aus dem Goldwert abgeleitet. Die
Kennzahl bleibt damit eine Aussage ueber den Text, nicht ueber die Annotation.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .provenienz import Provenienz

# Zeitpunkt, wie er im Outcome steht: ``7 min``, ``week 8``, ``visit 3B``.
_IM_OUTCOME_RE = re.compile(
    r"\b(?:baseline|endpoint|end\s*of\s*treatment)\b"
    r"|\b(?:week|wk|day|month)\s*\d+\b"
    r"|\b\d+\s*(?:min(?:ute)?s?|h|hrs?|hours?|days?|weeks?|wks?|months?)\b"
    r"|\bvisit\s*[0-9]+[A-Za-z]?\b",
    re.IGNORECASE,
)

# Zeitpunkt in einer Spaltenbeschriftung: dieselben Formen plus ``week``/``wk``.
_IM_KOPF_RE = re.compile(
    r"\b(?:baseline|endpoint|end\s*of\s*treatment|follow-up)\b"
    r"|\b(?:week|wk|day|month|month\s*of)\s*\d+\b"
    r"|\b\d+\s*(?:min(?:ute)?s?|h|hrs?|hours?|days?|weeks?|wks?|months?)\b",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def ziele(outcome: str) -> List[str]:
    """Gedruckte Zeitpunkte im Outcome, normiert und entdoppelt."""
    return sorted({_norm(treffer.group(0))
                   for treffer in _IM_OUTCOME_RE.finditer(outcome or "")})


def kopf_zeitpunkte(text: str) -> List[str]:
    """Gedruckte Zeitpunkte in einer Spaltenbeschriftung."""
    return sorted({_norm(treffer.group(0))
                   for treffer in _IM_KOPF_RE.finditer(text or "")})


def gebunden(stellen: Iterable[Provenienz], ziel: Sequence[str]
             ) -> List[Provenienz]:
    """Fundstellen, deren Spaltenkopf einen der Zielzeitpunkte druckt.

    Die Fundstelle traegt den Zeitpunkt danach in ``arm_basis``
    (``zeitpunkt:7 min``), damit die Herkunft an der Stelle steht.
    """
    treffer: List[Provenienz] = []
    gesucht = {_norm(wert) for wert in ziel}
    for stelle in stellen:
        kopf = _norm(getattr(stelle, "zeitpunkt", ""))
        if not kopf or kopf not in gesucht:
            continue
        treffer.append(replace(stelle, arm_basis=f"zeitpunkt:{kopf}"))
    return treffer


def stellen(stellen_je_feld: Dict[str, List[Provenienz]],
            context: Dict[str, Any]) -> Dict[str, List[Provenienz]]:
    """Je Feld die zeitpunktgebundenen Fundstellen eines Dokuments."""
    ziel = ziele(str(context.get("outcome") or ""))
    if not ziel:
        return {}
    out: Dict[str, List[Provenienz]] = {}
    for feld, orte in stellen_je_feld.items():
        orte_gebunden = gebunden(orte, ziel)
        if orte_gebunden:
            out[feld] = orte_gebunden
    return out


def lage(outcome: str, stellen_je_feld: Dict[str, List[Provenienz]],
         feld: str) -> Dict[str, Any]:
    """Kurzbefund fuer ein Feld: Zielzeitpunkt, gedruckte Koepfe, Bindung."""
    ziel = ziele(outcome)
    orte = stellen_je_feld.get(feld) or []
    koepfe = sorted({_norm(stelle.zeitpunkt) for stelle in orte if stelle.zeitpunkt})
    return {
        "ziel": ziel,
        "koepfe": koepfe,
        "gebunden": len(gebunden(orte, ziel)) if ziel else 0,
    }
