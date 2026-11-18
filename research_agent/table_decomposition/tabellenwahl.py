"""Tabellenwahl aus dem Dokument - ohne Gold, ohne Armumkehr.

Ein Record verweist auf eine Tabelle. Druckt die eine andere Population als
das Gold (Baseline oder Safety statt analysierter Population), liegt die
passende Zahl oft in einer **anderen Tabelle desselben Dokuments**. Dieses
Modul waehlt sie anhand des Dokuments:

* Traegt eine der aktuellen Tabellen eine Zeile zum Outcome, bleibt es bei
  ihr - auch wenn die Kopfbeschriftung nach Baseline klingt.
* Sonst gewinnt nur dann eine andere Tabelle, wenn die aktuelle eine
  Baseline-Tabelle ist (Kopfbeschriftung nennt "baseline", "demographic" oder
  "characteristics") und die andere die meisten Outcome-Zeilen hat. Traegt
  keine Tabelle eine Outcome-Zeile, zaehlt die gedruckte Caption als Beleg.

Damit wechselt die Wahl nur dort, wo die Auswahl nachweislich eine
Charakteristik-Tabelle ohne Outcome-Zeile als Ergebnisquelle nimmt.

Die Arme werden nicht angefasst: die gewaehlte Tabelle wird mit demselben
``enrich_table`` und denselben Transfers gelesen wie jede andere. Das Modul
extrahiert nichts und liest keinen Goldwert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .semantics import caption_matches_outcome, outcome_rows

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
    """Nennt die Kopfbeschriftung eine Baseline-/Charakteristik-Tabelle?

    Die Beschriftung ist Caption **und** Kopfband. Eine Regel ueber die
    Zeilenlabels (Alter, Geschlecht, MMSE, ...) wurde geprueft und verworfen:
    sie aendert keinen der 9 Tabellenwechsel, weil ``PMC5360580:T1`` seine
    Caption ``Baseline characteristics.`` gedruckt traegt.
    """
    text = beschriftung(table)
    return any(wort in text for wort in BASELINE_WOERTER)


def _rang(table: Any, outcome: str):
    """Rang einer Tabelle: erst Outcome-Zeilen, dann der Caption-Beleg."""
    return (len(outcome_rows(table, outcome)),
            1 if caption_matches_outcome(table, outcome) else 0)


def outcome_tabelle(tabellen: Sequence[Any],
                    outcome: str) -> Optional[Any]:
    """Beste Tabelle ohne Baseline-Beschriftung: Zeilen vor Caption.

    Der Caption-Beleg ist schwaecher als eine Outcome-Zeile und zaehlt deshalb
    nur, wenn keine Tabelle eine solche Zeile traegt (``PMC2430617:T4``:
    ``Occurrence of most common adverse events ...``).
    """
    beste = None
    bester = (0, 0)
    for table in tabellen:
        if ist_baseline(table):
            continue
        rang = _rang(table, outcome)
        if rang > bester:
            beste, bester = table, rang
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
