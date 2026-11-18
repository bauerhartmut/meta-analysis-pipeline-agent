"""Gedruckter Zeitpunkt als Fundstellen-Filter - kein Raten, kein Gold.

Ein Feld kann an mehreren Zeitpunkten gedruckt sein (Baseline gegen Aenderung,
3 min gegen 7 min). Dieses Modul bindet eine Fundstelle nur dann an einen
Zeitpunkt, wenn **beides gedruckt** ist:

1. der Zielzeitpunkt im Text des Outcomes (``ocular itching for visit 3B at
   7 min`` -> ``visit 3b``, ``7 min``),
2. derselbe Zeitpunkt an der Fundstelle selbst - im Spaltenkopf
   (``week 8``, ``baseline``) oder im Zeilenlabel (``7 min`` unter der
   Gruppenzeile ``Visit 3B: 16-hour persistence of action``).

Das Zeilenlabel gilt nur, wenn es selbst einen Zeitpunkt druckt; sonst tritt
die naechste Gruppenzeile darueber ein (``Visit 3B``). Nennt das Outcome
zusaetzlich die Gruppe, entscheidet sie zwischen gleichen Zeitpunkten in
mehreren Visiten - eine Zeile mit ``7 min`` erbt das ``visit 3b`` ihrer Gruppe
also nicht, sie wird nur danach ausgewaehlt.

Fehlt eine der beiden Seiten, entsteht keine Bindung: ein Zeitpunkt wird nie
aus der Spaltenposition, aus der Tabelle oder aus dem Goldwert abgeleitet.
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

# Zeitpunkt in einer Spaltenbeschriftung oder einem Zeilenlabel.
_IM_KOPF_RE = re.compile(
    r"\b(?:baseline|endpoint|end\s*of\s*treatment|follow-up)\b"
    r"|\b(?:week|wk|day|month|month\s*of)\s*\d+\b"
    r"|\b\d+\s*(?:min(?:ute)?s?|h|hrs?|hours?|days?|weeks?|wks?|months?)\b",
    re.IGNORECASE,
)

# Gruppenzeile ueber den Zeitpunktzeilen: ``Visit 3B``.
_GRUPPE_RE = re.compile(
    r"\b(?:visit|phase|period)\s*[0-9]+[A-Za-z]?\b",
    re.IGNORECASE,
)

# Wie weit ueber einer Zeile nach ihrer Gruppenzeile gesucht wird.
_GRUPPE_MAX = 8


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def ziele(outcome: str) -> List[str]:
    """Gedruckte Zeitpunkte im Outcome, normiert und entdoppelt."""
    return sorted({_norm(treffer.group(0))
                   for treffer in _IM_OUTCOME_RE.finditer(outcome or "")})


def kopf_zeitpunkte(text: str) -> List[str]:
    """Gedruckte Zeitpunkte in einer Spaltenbeschriftung oder einem Label."""
    return sorted({_norm(treffer.group(0))
                   for treffer in _IM_KOPF_RE.finditer(text or "")})


def zeilen_angaben(tabelle: Any, zeile: int) -> tuple:
    """Gedruckte Angaben einer Zeile: ``(zeitpunkte, gruppe)``.

    ``7 min`` im Zeilenlabel ist der genauere Zeitpunkt; die Gruppenzeile
    darueber (``Visit 3B: 16-hour persistence of action``) traegt die groebere
    Angabe. Beide werden getrennt zurueckgegeben: eine Zeile mit ``7 min``
    erbt nicht das ``visit 3b`` ihrer Gruppe, sie traegt es neben sich.
    """
    satz = tabelle.row(zeile) if tabelle is not None else None
    if satz is None:
        return [], []
    eigen = kopf_zeitpunkte(satz.label) or kopf_zeitpunkte(
        " ".join(getattr(satz, "label_path", ()) or ()))
    position = next((i for i, kandidat in enumerate(tabelle.rows)
                     if kandidat.row_id == zeile), None)
    gruppe: List[str] = []
    if position is not None:
        for vor in range(position - 1, max(-1, position - _GRUPPE_MAX) - 1, -1):
            kandidat = tabelle.rows[vor]
            text = kandidat.group_label or kandidat.label
            if not text:
                continue
            if kopf_zeitpunkte(text):
                continue
            treffer = {_norm(t.group(0)) for t in _GRUPPE_RE.finditer(text)}
            if treffer:
                gruppe = sorted(treffer)
                break
    return eigen, gruppe


def zeilen_zeitpunkte(tabelle: Any, zeile: int) -> List[str]:
    """Zeitpunkt einer Zeile: eigenes Label, sonst die Gruppenzeile."""
    eigen, gruppe = zeilen_angaben(tabelle, zeile)
    return eigen or gruppe


def gebunden(stellen: Iterable[Provenienz], ziel: Sequence[str],
             tabellen: Sequence[Any] = (), mit_gruppe: bool = True
             ) -> List[Provenienz]:
    """Fundstellen, deren Spaltenkopf oder Zeilenlabel einen Zielzeitpunkt druckt.

    Nennt das Outcome auch die Gruppe (``visit 3B``) und druckt eine der
    Fundstellen sie, bleiben nur die Fundstellen mit passender Gruppe uebrig -
    noetig, weil ``7 min`` in drei Visiten steht. Ohne Gruppentreffer bleibt der
    Stand der Zeitpunktzeilen. Die Fundstelle traegt den Zeitpunkt danach in
    ``arm_basis`` (``zeitpunkt:7 min``).
    """
    return [stelle for stelle, _gruppentreffer in _kandidaten(stellen, ziel,
                                                             tabellen, mit_gruppe)]


def _kandidaten(stellen: Iterable[Provenienz], ziel: Sequence[str],
                tabellen: Sequence[Any], mit_gruppe: bool
                ) -> List[tuple]:
    gesucht = {_norm(wert) for wert in ziel}
    if not gesucht:
        return []
    index = {getattr(tabelle, "table_id", ""): tabelle for tabelle in tabellen}
    roh: List[tuple] = []
    for stelle in stellen:
        orte = {_norm(stelle.zeitpunkt)} if stelle.zeitpunkt else set()
        gruppe: set = set()
        tabelle = index.get(getattr(stelle, "tabelle", ""))
        if tabelle is not None and getattr(stelle, "zeile", None) is not None:
            eigen, gruppen_labels = zeilen_angaben(tabelle, stelle.zeile)
            orte |= set(eigen) if eigen else set(gruppen_labels)
            gruppe = set(gruppen_labels) & gesucht
        gemeinsam = orte & gesucht
        if not gemeinsam:
            continue
        roh.append((stelle, gemeinsam, gruppe))
    if mit_gruppe and any(gruppe for _stelle, _gemeinsam, gruppe in roh):
        roh = [eintrag for eintrag in roh if eintrag[2]]
    return [(replace(stelle, arm_basis=f"zeitpunkt:{sorted(gemeinsam)[0]}"), gruppe)
            for stelle, gemeinsam, gruppe in roh]


def stellen(stellen_je_feld: Dict[str, List[Provenienz]],
            context: Dict[str, Any],
            tabellen: Sequence[Any] = ()
            ) -> Dict[str, List[Provenienz]]:
    """Je Feld die zeitpunktgebundenen Fundstellen eines Dokuments."""
    ziel = ziele(str(context.get("outcome") or ""))
    if not ziel:
        return {}
    out: Dict[str, List[Provenienz]] = {}
    for feld, orte in stellen_je_feld.items():
        orte_gebunden = gebunden(orte, ziel, tabellen)
        if orte_gebunden:
            out[feld] = orte_gebunden
    return out


def lage(outcome: str, stellen_je_feld: Dict[str, List[Provenienz]],
         feld: str, tabellen: Sequence[Any] = ()) -> Dict[str, Any]:
    """Kurzbefund fuer ein Feld: Zielzeitpunkt, gedruckte Stellen, Bindung."""
    ziel = ziele(outcome)
    orte = stellen_je_feld.get(feld) or []
    index = {getattr(tabelle, "table_id", ""): tabelle for tabelle in tabellen}
    koepfe = sorted({_norm(stelle.zeitpunkt) for stelle in orte if stelle.zeitpunkt})
    zeilen: List[str] = []
    for stelle in orte:
        tabelle = index.get(getattr(stelle, "tabelle", ""))
        if tabelle is None or getattr(stelle, "zeile", None) is None:
            continue
        zeilen.extend(zeilen_zeitpunkte(tabelle, stelle.zeile))
    zeit_allein = gebunden(orte, ziel, tabellen, mit_gruppe=False)
    mit_gruppe = gebunden(orte, ziel, tabellen, mit_gruppe=True)
    return {
        "ziel": ziel,
        "koepfe": koepfe,
        "zeilen": sorted(set(zeilen)),
        "gebunden": len(zeit_allein),
        "gebunden_mit_gruppe": len(mit_gruppe),
        "werte": sorted({stelle.wert for stelle in zeit_allein
                         if stelle.wert is not None}),
        "werte_mit_gruppe": sorted({stelle.wert for stelle in mit_gruppe
                                    if stelle.wert is not None}),
    }
