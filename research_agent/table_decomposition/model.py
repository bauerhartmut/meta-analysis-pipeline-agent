"""Strukturmodell fuer die Table-Decomposition-Engine.

Eine Tabelle wird nicht als Bildbereich, sondern als semantische Struktur
gehalten: Blattspalten mit x-Intervallen, Header-Baender mit Spannen
(zusammengefuehrte Header-Zellen), Datenzeilen mit Zeilenlabels, Fussnoten und
die Zeichenposition im Dokument. Jede Zelle kennt ihre Adresse
(``row_id``/``col_id``) und ihre Fundstelle, damit jedes Teilresultat auf die
Originalstelle zurueckfuehrbar bleibt.

Bewusst schlicht: reine Datentraeger, keine Logik, kein Modellbezug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Felder der numerischen Extraktion (identisch zu run_extended_extraction.FIELDS).
FIELDS: Tuple[str, ...] = (
    "intervention_group_size",
    "intervention_events",
    "intervention_mean",
    "intervention_standard_deviation",
    "comparator_group_size",
    "comparator_events",
    "comparator_mean",
    "comparator_standard_deviation",
)

ARM_INTERVENTION = "intervention"
ARM_COMPARATOR = "comparator"

# Rollen einer Spalte. ``label`` traegt Text, alle anderen tragen Zahlen.
ROLE_LABEL = "label"
ROLE_N = "n"
ROLE_MEAN = "mean"
ROLE_SD = "sd"
ROLE_SE = "se"
ROLE_EVENTS = "events"
ROLE_CI = "ci"
ROLE_PERCENT = "percent"
ROLE_PVALUE = "p_value"
ROLE_UNKNOWN = "unknown"

ROLE_TO_FIELD_SUFFIX = {
    ROLE_N: "group_size",
    ROLE_EVENTS: "events",
    ROLE_MEAN: "mean",
    ROLE_SD: "standard_deviation",
}


def field_for(role: str, arm: Optional[str]) -> Optional[str]:
    """Feldname fuer (Rolle, Arm) oder None, wenn es kein Zielfeld ist.

    ``None`` ist die ehrliche Antwort: SE, CI, p-Werte und Prozentangaben sind
    keine Armfelder des Benchmarks, und ohne Arm gibt es kein Feld.
    """
    suffix = ROLE_TO_FIELD_SUFFIX.get(role)
    if not suffix or arm not in (ARM_INTERVENTION, ARM_COMPARATOR):
        return None
    return f"{arm}_{suffix}"


@dataclass
class HeaderBand:
    """Eine Header-Zeile der Tabelle, mit Spannen je Zelle.

    ``col_start``/``col_end`` sind Blattspalten-Indizes (inklusiv). Eine Zelle
    ueber zwei Blattspalten hat ``col_end - col_start == 1``: das ist die
    zusammengefuehrte Zelle (colspan) der mehrstufigen Ueberschrift.
    """
    level: int
    text: str
    col_start: int
    col_end: int
    anchor: int = -1
    basis: str = ""              # wie die Spanne bestimmt wurde
    start_char: int = -1
    end_char: int = -1
    line: int = -1

    @property
    def span(self) -> int:
        return self.col_end - self.col_start + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "text": self.text,
            "col_start": self.col_start,
            "col_end": self.col_end,
            "span": self.span,
            "anchor": self.anchor,
            "basis": self.basis,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "line": self.line,
        }


@dataclass
class Column:
    """Eine Blattspalte: x-Intervall, Header-Hierarchie und abgeleitete Rolle."""
    col_id: int
    x_start: int
    x_end: int
    header_path: Tuple[str, ...] = ()
    header: str = ""
    role: str = ROLE_UNKNOWN
    arm: Optional[str] = None
    arm_basis: str = ""          # wie der Arm gebunden wurde (Nachvollziehbarkeit)
    unit: str = ""
    field: Optional[str] = None  # Zielfeld, nur bei role+arm gesetzt
    secondary_role: str = ""     # zweite Rolle aus derselben Zelle (z. B. sd in "12.4 (3.1)")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "col_id": self.col_id,
            "x_start": self.x_start,
            "x_end": self.x_end,
            "header_path": list(self.header_path),
            "header": self.header,
            "role": self.role,
            "arm": self.arm,
            "arm_basis": self.arm_basis,
            "unit": self.unit,
            "field": self.field,
            "secondary_role": self.secondary_role,
        }


@dataclass
class Cell:
    """Eine Zelle mit Inhalt und Fundstelle.

    ``text`` ist verbatim, ``value`` die nach den dokumentierten Regeln
    normalisierte Zahl (None, wenn die Zelle keine ist). Beides bleibt
    erhalten: der Originalwert ist der Beleg, der normalisierte Wert die
    Rechnung.
    """
    row_id: int
    col_id: int
    text: str = ""
    value: Optional[float] = None
    line: int = -1
    start_char: int = -1
    end_char: int = -1
    x_start: int = -1
    x_end: int = -1
    inherited_from_row: Optional[int] = None   # leeres Zeilenlabel: gilt weiter
    row_span: int = 1
    col_span: int = 1
    mapping: str = "overlap"                   # overlap | nearest | pipe

    @property
    def address(self) -> Tuple[int, int]:
        return (self.row_id, self.col_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "col_id": self.col_id,
            "text": self.text,
            "value": self.value,
            "line": self.line,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "x_start": self.x_start,
            "x_end": self.x_end,
            "inherited_from_row": self.inherited_from_row,
            "row_span": self.row_span,
            "col_span": self.col_span,
            "mapping": self.mapping,
        }


@dataclass
class Row:
    """Eine Datenzeile. ``label`` ist das Zeilenlabel, wenn eine Spalte es traegt."""
    row_id: int
    index: int
    label: str = ""
    cells: Dict[int, Cell] = field(default_factory=dict)
    line: int = -1
    start_char: int = -1
    end_char: int = -1
    irregular: bool = False       # Zellen fehlen oder doppelt zugeordnet
    # Fette Zeilengruppe (``**Dietary intake**``): Label ohne Werte. Sie gliedert
    # die Zeilen und darf die Tabelle nicht beenden.
    group_label: str = ""
    # Gruppenpfad plus eigenes Zeilenlabel; erst zusammen ist eine Zeile
    # eindeutig (``Dietary intake`` > ``Vegetable intake`` > ``Mean (SD)``).
    label_path: Tuple[str, ...] = ()
    # Rolle aus dem Zeilenlabel, wenn der Spaltenkopf keine traegt:
    # ``Mean (SD)`` -> mean + sd, ``Not complying, n (%)`` -> events.
    value_role: str = ""
    secondary_role: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "index": self.index,
            "label": self.label,
            "group_label": self.group_label,
            "label_path": list(self.label_path),
            "value_role": self.value_role,
            "secondary_role": self.secondary_role,
            "line": self.line,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "irregular": self.irregular,
            "cells": [c.to_dict() for _cid, c in sorted(self.cells.items())],
        }


@dataclass
class Footnote:
    text: str
    marker: str = ""
    line: int = -1

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "marker": self.marker, "line": self.line}


@dataclass
class Table:
    """Eine Tabelle im Dokument, vollstaendig und rueckverfolgbar."""
    table_id: str
    doc_id: str
    index: int
    caption: str = ""
    label: str = ""
    page: Optional[int] = None
    columns: List[Column] = field(default_factory=list)
    header_bands: List[HeaderBand] = field(default_factory=list)
    rows: List[Row] = field(default_factory=list)
    footnotes: List[Footnote] = field(default_factory=list)
    footnote_block: str = ""
    units: List[str] = field(default_factory=list)
    parser: str = "pandoc-rule/1"
    line_start: int = -1
    line_end: int = -1
    char_start: int = -1
    char_end: int = -1
    caption_char_span: Tuple[int, int] = (-1, -1)
    irregularities: List[str] = field(default_factory=list)
    complexity: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    # Feste Angaben aus dem Kopf (``n = 456``): Wert und Arm, woertlich belegt.
    header_facts: List[Dict[str, Any]] = field(default_factory=list)
    # Zeilen, die das Outcome des Records tragen (Zeilenlabel-Pfad, kein Gold).
    focus_rows: List[int] = field(default_factory=list)

    # --- Zugriff ---------------------------------------------------------
    @property
    def n_columns(self) -> int:
        return len(self.columns)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    @property
    def label_columns(self) -> List[int]:
        return [c.col_id for c in self.columns if c.role == ROLE_LABEL]

    @property
    def data_columns(self) -> List[int]:
        return [c.col_id for c in self.columns if c.role != ROLE_LABEL]

    def column(self, col_id: int) -> Optional[Column]:
        for c in self.columns:
            if c.col_id == col_id:
                return c
        return None

    def row(self, row_id: int) -> Optional[Row]:
        for r in self.rows:
            if r.row_id == row_id:
                return r
        return None

    def data_cells(self) -> List[Cell]:
        """Alle Zellen der Datenspalten (die Kandidaten fuer Zahlen)."""
        labels = set(self.label_columns)
        cells: List[Cell] = []
        for row in self.rows:
            for col_id, cell in sorted(row.cells.items()):
                if col_id not in labels and cell.text.strip():
                    cells.append(cell)
        return cells

    def cell(self, row_id: int, col_id: int) -> Optional[Cell]:
        row = self.row(row_id)
        if not row:
            return None
        return row.cells.get(col_id)

    def target_cells(self) -> List[Cell]:
        """Zellen, deren Spalte ein Zielfeld traegt (Rolle + gebundener Arm)."""
        labels = set(self.label_columns)
        return [c for c in self.data_cells() if c.col_id not in labels]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "doc_id": self.doc_id,
            "index": self.index,
            "caption": self.caption,
            "label": self.label,
            "page": self.page,
            "parser": self.parser,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "caption_char_span": list(self.caption_char_span),
            "columns": [c.to_dict() for c in self.columns],
            "header_bands": [b.to_dict() for b in self.header_bands],
            "rows": [r.to_dict() for r in self.rows],
            "footnotes": [f.to_dict() for f in self.footnotes],
            "footnote_block": self.footnote_block,
            "units": list(self.units),
            "irregularities": list(self.irregularities),
            "complexity": dict(self.complexity),
            "context": dict(self.context),
            "header_facts": [dict(fact) for fact in self.header_facts],
            "focus_rows": list(self.focus_rows),
        }


@dataclass
class DocumentTables:
    """Ergebnis eines Dokument-Parsings."""
    doc_id: str
    tables: List[Table] = field(default_factory=list)
    unresolved_blocks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "n_tables": len(self.tables),
            "tables": [t.to_dict() for t in self.tables],
            "unresolved_blocks": self.unresolved_blocks,
        }


def header_path_text(path: Sequence[str]) -> str:
    """Header-Hierarchie als lesbarer Pfad: 'Gruppe > Mean'."""
    return " > ".join(p for p in path if p)
