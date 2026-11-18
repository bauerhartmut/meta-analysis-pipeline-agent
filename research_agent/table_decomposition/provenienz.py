"""Provenienz je extrahiertem Feld - lesend, ohne eigene Extraktion.

Die Engine weiss, *welches* Feld eine Zelle oder Kopfangabe traegt. Sie sagt
bisher aber nicht, *woher* der Wert stammt. Dieses Modul beschreibt die
Fundstelle: Tabelle, Zeile beziehungsweise Kopfband, Spalten, Originaltext,
gedruckter Wert, Arm, Zeitpunkt, die Regel, ueber die das Feld entstand, und
wie sicher diese Zuordnung ist.

Drei Arten werden strikt getrennt:

* ``direkt`` - an der Stelle steht genau eine Zahl (oder eine Kopfangabe), und
  diese Zahl ist der Wert des Feldes.
* ``abgeleitet`` - der Wert steckt in einer Verbundzelle (``1.2 (0.3)``) und
  entsteht erst durch die Regel (Zweitwert, Rolle aus dem Zeilenlabel, ...).
* ``mehrfach`` - das Feld hat mehrere Fundstellen (etwa zwei Untergruppen mit
  ``n = 17`` und ``n = 16``). Dann gibt es **keine** gedruckte Gruppengroesse;
  eine Summe waere abgeleitet und darf nicht als direkter Wert gelten.

Es wird nichts extrahiert, umgeordnet oder gegen Gold geprueft: das Modul liest
nur die angereicherte Tabelle (``enrich_table``) und ihre Kopfangaben.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence

from .model import ROLE_LABEL, ROLE_N, ROLE_UNKNOWN, field_for
from .semantics import _NUMBER_RE, cell_arm

QUELLE_KOPF = "kopfangabe"
QUELLE_ZELLE = "messzelle"

DIREKT = "direkt"
ABGELEITET = "abgeleitet"
MEHRFACH = "mehrfach"

HOCH = "hoch"
MITTEL = "mittel"
NIEDRIG = "niedrig"

# Zeitangaben in der Kopfbeschriftung einer Spalte. Bewusst eng: nur was als
# Zeitpunkt lesbar ist, wird als Zeitpunkt ausgewiesen.
# Genau eine Zahl, mit Vorzeichen: nur dann ist der Wert direkt gedruckt.
_EINZELZAHL_RE = re.compile(r"^\s*([−–-]?)(\d+(?:[.,]\d+)?)\s*$")

_ZEIT_RE = re.compile(
    r"\b(?:baseline|week|wk|day|month|months|year|years|woche|wochen|monat|"
    r"monate|tag|tage|jahr|jahre|follow-up|endpoint|end\s*of\s*treatment)\b"
    r"|\b\d+\s*(?:h|hr|hrs|hours?|min|minutes?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Provenienz:
    """Eine Fundstelle eines Feldes mit ihrer Herleitung."""

    feld: str
    quelle: str
    text: str
    wert: Optional[float]
    arm: Optional[str]
    arm_basis: str
    zeitpunkt: str
    art: str
    regel: str
    sicherheit: str
    tabelle: str
    zeile: Optional[int]
    spalten: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _zeitpunkt(column: Any) -> str:
    for text in reversed(list(getattr(column, "header_path", []) or [])):
        treffer = _ZEIT_RE.search(text or "")
        if treffer:
            return treffer.group(0)
    return ""


def _kopf(table: Any, feld: str) -> List[Provenienz]:
    stellen: List[Provenienz] = []
    for fact in table.header_facts:
        arm = fact.get("arm") or None
        if field_for(ROLE_N, arm) != feld:
            continue
        stellen.append(Provenienz(
            feld=feld, quelle=QUELLE_KOPF, text=str(fact.get("text") or ""),
            wert=float(fact["value"]), arm=arm,
            arm_basis="kopfangabe" if arm else "",
            zeitpunkt="", art=DIREKT, regel="gruppengroesse_im_kopf",
            sicherheit=HOCH if arm else NIEDRIG, tabelle=table.table_id,
            zeile=None,
            spalten=[int(fact.get("col_start") or 0), int(fact.get("col_end") or 0)],
        ))
    return stellen


def _regel(column: Any, row: Any, feld: str, arm: Optional[str], text: str) -> str:
    """Name der Produktionsregel, die ``feld`` an dieser Zelle traegt.

    Spiegelt die Zweige von ``semantics.row_fields`` und
    ``semantics.reachable_fields``; die Reihenfolge entscheidet nur, welcher
    Name bei mehreren Treffern steht.
    """
    if column.field == feld:
        return "spaltenfeld"
    if column.role == ROLE_UNKNOWN and getattr(row, "value_role", "") \
            and field_for(row.value_role, arm) == feld:
        return "rolle_aus_zeilenlabel"
    if column.is_outcome and column.role != ROLE_UNKNOWN \
            and field_for(column.role, arm) == feld:
        return "arm_als_zeile"
    if column.secondary_role and column.arm \
            and field_for(column.secondary_role, column.arm) == feld:
        return "zweitwert_der_spalte"
    if getattr(row, "secondary_role", "") and arm \
            and len(_NUMBER_RE.findall(text)) >= 2 \
            and field_for(row.secondary_role, arm) == feld:
        return "zweitwert_der_zelle"
    return ""


def _zellen(table: Any, row_id: int, feld: str) -> List[Provenienz]:
    row = table.row(row_id)
    if row is None:
        return []
    stellen: List[Provenienz] = []
    for column in table.columns:
        if column.role == ROLE_LABEL:
            continue
        cell = row.cells.get(column.col_id)
        text = (cell.text or "") if cell is not None else ""
        if not text.strip():
            continue
        arm = cell_arm(column, row)
        regel = _regel(column, row, feld, arm, text)
        if not regel:
            continue
        einzel = _EINZELZAHL_RE.match(text)
        art = DIREKT if einzel else ABGELEITET
        wert = None
        if einzel:
            wert = float(einzel.group(2).replace(",", "."))
            if einzel.group(1):
                wert = -wert
        if art == DIREKT and regel == "spaltenfeld" and arm:
            sicherheit = HOCH
        elif arm:
            sicherheit = MITTEL
        else:
            sicherheit = NIEDRIG
        stellen.append(Provenienz(
            feld=feld, quelle=QUELLE_ZELLE, text=text,
            wert=wert,
            arm=arm, arm_basis=getattr(column, "arm_basis", "") or "",
            zeitpunkt=_zeitpunkt(column), art=art, regel=regel,
            sicherheit=sicherheit, tabelle=table.table_id, zeile=row_id,
            spalten=[column.col_id],
        ))
    return stellen


def stellen(table: Any, row_id: int, feld: str) -> List[Provenienz]:
    """Alle Fundstellen von ``feld`` in dieser Tabelle (Kopf oder Zeile)."""
    if row_id == -1:
        return _kopf(table, feld)
    return _zellen(table, row_id, feld)


def feld_art(stellen: Sequence[Provenienz]) -> str:
    """Art des Feldes ueber alle Fundstellen.

    Mehrere Fundstellen ergeben ``mehrfach`` - auch dann, wenn jede fuer sich
    direkt gedruckt ist. Genau das unterscheidet zwei Untergruppen
    (``n = 17``/``n = 16``) von einer gedruckten Gruppengroesse.
    """
    if not stellen:
        return ""
    if len(stellen) > 1:
        return MEHRFACH
    return stellen[0].art


def feld_sicherheit(stellen: Sequence[Provenienz]) -> str:
    rang = {HOCH: 0, MITTEL: 1, NIEDRIG: 2}
    if not stellen:
        return ""
    return max((s.sicherheit for s in stellen), key=lambda s: rang.get(s, 3))


def feld_arm(stellen: Sequence[Provenienz]) -> str:
    """``eindeutig``, ``mehrdeutig`` oder ``ohne`` - ohne Raten."""
    arme = {s.arm for s in stellen if s.arm}
    if not arme:
        return "ohne"
    return "eindeutig" if len(arme) == 1 else "mehrdeutig"
