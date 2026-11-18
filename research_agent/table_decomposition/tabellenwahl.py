"""Tabellenwahl aus dem Dokument - ohne Gold, ohne Armumkehr.

Ein Record verweist auf eine Tabelle. Druckt die eine andere Population als
das Gold (Baseline oder Safety statt analysierter Population), liegt die
passende Zahl oft in einer **anderen Tabelle desselben Dokuments**. Dieses
Modul waehlt sie anhand des Dokuments:

* Traegt eine der aktuellen Tabellen eine Zeile zum Outcome, bleibt es bei
  ihr - auch wenn die Kopfbeschriftung nach Baseline klingt.
* Sonst gewinnt nur dann eine andere Tabelle, wenn die aktuelle eine
  Baseline-Tabelle ist (Kopfbeschriftung nennt "baseline", "demographic" oder
  "characteristics") und die andere die meisten Outcome-Zeilen hat.

Damit wechselt die Wahl nur dort, wo die Auswahl nachweislich eine
Charakteristik-Tabelle ohne Outcome-Zeile als Ergebnisquelle nimmt.

Die Arme werden nicht angefasst: die gewaehlte Tabelle wird mit demselben
``enrich_table`` und denselben Transfers gelesen wie jede andere. Das Modul
extrahiert nichts und liest keinen Goldwert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .semantics import outcome_rows

BASELINE_WOERTER = ("baseline", "demographic", "characteristics",
                    "at study entry", "study entry")


@dataclass(frozen=True)
class Wahl:
    """Ergebnis der Tabellenwahl: gewaehlte Tabelle und Begruendung."""

    tabelle: Any
    grund: str

    @property
    def wechsel(self) -> bool:
        return self.grund == "outcome_tabelle"


def beschriftung(table: Any) -> str:
    """Kopfbeschriftung einer Tabelle: Caption und Kopfbaender."""
    teile = [str(getattr(table, "caption", "") or "")]
    teile.extend(str(band.text or "") for band in table.header_bands)
    return " ".join(teile).lower()


def ist_baseline(table: Any) -> bool:
    """Nennt die Kopfbeschriftung eine Baseline-/Charakteristik-Tabelle?"""
    text = beschriftung(table)
    return any(wort in text for wort in BASELINE_WOERTER)


def outcome_tabelle(tabellen: Sequence[Any],
                    outcome: str) -> Optional[Any]:
    """Tabelle mit den meisten Outcome-Zeilen, Baseline ausgenommen."""
    beste = None
    beste_zahl = 0
    for table in tabellen:
        if ist_baseline(table):
            continue
        zahl = len(outcome_rows(table, outcome))
        if zahl > beste_zahl:
            beste, beste_zahl = table, zahl
    return beste


def waehle(aktuelle: Sequence[Any], alle: Sequence[Any],
           context: dict) -> Optional[Wahl]:
    """Bevorzugt die Outcome-Tabelle, wenn die aktuelle keine Outcome-Zeile hat.

    ``aktuelle`` ist die Auswahl des Records, ``alle`` sind alle Tabellen des
    Dokuments, beide mit dem Kontext des Records angereichert. ``None`` heisst:
    keine begruendete Wahl.
    """
    outcome = str(context.get("outcome") or "").strip()
    if not outcome or not alle or not aktuelle:
        return None
    if any(outcome_rows(table, outcome) for table in aktuelle):
        return Wahl(tabelle=aktuelle[0], grund="aktuelle_tabelle_traegt_outcome")
    if not any(ist_baseline(table) for table in aktuelle):
        return Wahl(tabelle=aktuelle[0], grund="aktuelle_tabelle_ist_nicht_baseline")
    ziel = outcome_tabelle(alle, outcome)
    if ziel is None or any(ziel is table for table in aktuelle):
        return None
    return Wahl(tabelle=ziel, grund="outcome_tabelle")
