"""Die fuenf Zerlegungsverfahren (A-E) und ihre Promptform.

* A ``full``          - ganze Tabelle mit Kopf und Fussnoten (Baseline).
* B ``vertical``      - eine Spalte je Einheit, mit voller Header-Hierarchie.
* C ``horizontal``    - eine Zeile je Einheit, mit allen Spaltenkoepfen.
* D ``bidirectional`` - B und C parallel; Abweichungen werden Konflikt.
* E ``adaptive``      - nach Komplexitaet: A, B oder D, plus gezielte
  Zellennachverarbeitung fuer ungeklaerte Zellen.

Jede Einheit traegt ihren vollstaendigen Kontext: Tabellenkopf, Caption,
Header-Hierarchie (alle Eltern-Ebenen), Zeilenlabels, relevante Fussnoten und
die Studienkontext-Angaben. Ein Ausschnitt ohne diese Angaben wird nicht
gebaut - ein Wert ``12.4`` ohne Outcome, Arm und Zeitpunkt ist wertlos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .complexity import MEDIUM, SIMPLE, VERY_COMPLEX, ComplexityScore, assess
from .crops import TableCrop, make_crop, mark_overlaps
from .model import (
    ROLE_LABEL,
    Column,
    Table,
    header_path_text,
)
from .semantics import column_summary, target_columns, unassigned_columns

STRATEGY_FULL = "A"
STRATEGY_VERTICAL = "B"
STRATEGY_HORIZONTAL = "C"
STRATEGY_BIDIRECTIONAL = "D"
STRATEGY_ADAPTIVE = "E"

STRATEGY_LABELS = {
    STRATEGY_FULL: "Full-Table Extraction",
    STRATEGY_VERTICAL: "Vertical Decomposition",
    STRATEGY_HORIZONTAL: "Horizontal Decomposition",
    STRATEGY_BIDIRECTIONAL: "Bidirectional Decomposition",
    STRATEGY_ADAPTIVE: "Adaptive Recursive Decomposition",
}

DIRECTION_FULL = "full"
DIRECTION_COLUMN = "column"
DIRECTION_ROW = "row"
DIRECTION_CELL = "cell"


@dataclass
class PlanOptions:
    """Stellschrauben der Zerlegung (LLM-frei, deterministisch)."""
    max_units_per_table: int = 24
    include_footnotes: bool = True
    include_verbatim: bool = True
    min_columns_for_split: int = 3
    max_refinement_units: int = 8


@dataclass
class ExtractionUnit:
    """Eine Extraktionseinheit: Ausschnitt plus vollstaendiger Kontext.

    ``expected_cells`` sind die Adressen, die in diesem Ausschnitt gelesen
    werden sollen. ``context_row_ids``/``context_col_ids`` laufen nur als
    Kontext mit und werden nicht bewertet.
    """
    unit_id: str
    strategy: str
    direction: str
    table_id: str
    doc_id: str
    row_ids: List[int] = field(default_factory=list)
    col_ids: List[int] = field(default_factory=list)
    context_row_ids: List[int] = field(default_factory=list)
    context_col_ids: List[int] = field(default_factory=list)
    expected_cells: List[Tuple[int, int]] = field(default_factory=list)
    prompt: str = ""
    crop: Optional[TableCrop] = None
    depth: int = 0
    parent_unit_id: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self, with_prompt: bool = True) -> Dict[str, Any]:
        data = {
            "unit_id": self.unit_id,
            "strategy": self.strategy,
            "direction": self.direction,
            "table_id": self.table_id,
            "doc_id": self.doc_id,
            "row_ids": list(self.row_ids),
            "col_ids": list(self.col_ids),
            "context_row_ids": list(self.context_row_ids),
            "context_col_ids": list(self.context_col_ids),
            "expected_cells": [list(c) for c in self.expected_cells],
            "depth": self.depth,
            "parent_unit_id": self.parent_unit_id,
            "notes": list(self.notes),
            "crop": self.crop.to_dict() if self.crop else None,
        }
        if with_prompt:
            data["prompt"] = self.prompt
            data["prompt_chars"] = len(self.prompt)
        return data


@dataclass
class DecompositionPlan:
    table_id: str
    strategy: str
    complexity: ComplexityScore
    units: List[ExtractionUnit] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def expected_calls(self) -> int:
        return len(self.units)

    def to_dict(self, with_prompt: bool = False) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "strategy": self.strategy,
            "strategy_label": STRATEGY_LABELS.get(self.strategy, self.strategy),
            "complexity": self.complexity.to_dict(),
            "expected_calls": self.expected_calls,
            "notes": list(self.notes),
            "units": [u.to_dict(with_prompt=with_prompt) for u in self.units],
        }


# --- Prompt-Bausteine -----------------------------------------------------

def _study_context(table: Table) -> str:
    context = table.context or {}
    outcome_type = context.get("outcome_type") or "unknown"
    lines = [
        "STUDY CONTEXT (binding - use these names, do not invent labels)",
        f"intervention: {context.get('intervention') or 'not stated'}",
        f"comparator: {context.get('comparator') or 'not stated'}",
        f"outcome: {context.get('outcome') or 'not stated'}",
        f"outcome type: {outcome_type}",
    ]
    if context.get("timepoint_target"):
        lines.append(f"target time point: {context['timepoint_target']}")
    return "\n".join(lines)


def _table_header(table: Table) -> str:
    page = table.page if table.page is not None else "not stated in source"
    return "\n".join([
        f"DOCUMENT: {table.doc_id}   TABLE: {table.table_id}   PAGE: {page}",
        f"CAPTION (verbatim): {table.caption or '(none)'}",
    ])


def _column_legend(table: Table) -> str:
    lines = ["COLUMN HEADERS (full hierarchy; column ids are binding)"]
    for column in table.columns:
        if column.role == ROLE_LABEL:
            lines.append(f"col {column.col_id}: row label column")
        else:
            lines.append(f"col {column.col_id}: {column_summary(column)}")
    return "\n".join(lines)


def _group_header_lines(table: Table) -> List[str]:
    lines = ["HEADER HIERARCHY (top level first)"]
    for level in sorted({b.level for b in table.header_bands}):
        bands = [
            f"{b.text} = cols {b.col_start}-{b.col_end}"
            for b in table.header_bands if b.level == level
        ]
        if bands:
            lines.append(f"level {level}: " + " | ".join(bands))
    return lines if len(lines) > 1 else []


def _footnote_block(table: Table, options: PlanOptions) -> List[str]:
    if not options.include_footnotes:
        return []
    if not table.footnote_block.strip() and not table.footnotes:
        return []
    lines = ["FOOTNOTES AND LEGEND (verbatim, they may change the reading)"]
    lines.append(table.footnote_block.strip() or "\n".join(f.text for f in table.footnotes))
    return lines


def _cell_text(cell) -> str:
    return (cell.text or "").strip()


def _rows_block(table: Table, row_ids: Sequence[int], col_ids: Sequence[int]) -> str:
    lines = ["ROWS (verbatim labels; values only for the columns in scope)"]
    for row_id in row_ids:
        row = table.row(row_id)
        if row is None:
            continue
        label = row.label or "(no row label)"
        values = []
        for col_id in col_ids:
            cell = row.cells.get(col_id)
            if cell is not None and _cell_text(cell):
                values.append(f"col {col_id} = {_cell_text(cell)}")
        lines.append(f"row {row_id} | {label}" + (" | " + " | ".join(values) if values else ""))
    return "\n".join(lines)


def _verbatim_block(table: Table, document_text: str) -> List[str]:
    start, end = table.char_start, table.char_end
    if not document_text or start < 0 or end <= start:
        return []
    slice_text = document_text[start:end].strip("\n")
    if not slice_text:
        return []
    return [
        "VERBATIM TABLE (exactly as printed in the source; read numbers from here)",
        slice_text,
    ]


def _scope_text(table: Table, unit: ExtractionUnit) -> str:
    if unit.direction == DIRECTION_FULL:
        return "SCOPE: the whole table (all data columns, all rows)."
    if unit.direction == DIRECTION_CELL:
        return (
            "SCOPE: exactly one cell - "
            f"row {unit.row_ids[0]}, col {unit.col_ids[0]}."
        )
    if unit.direction == DIRECTION_COLUMN:
        cols = ", ".join(str(c) for c in unit.col_ids)
        rows = f"{min(unit.row_ids)}-{max(unit.row_ids)}" if unit.row_ids else "none"
        return f"SCOPE: column(s) {cols}; rows {rows}."
    cols = ", ".join(str(c) for c in unit.col_ids)
    rows = ", ".join(str(r) for r in unit.row_ids)
    return f"SCOPE: row(s) {rows}; columns {cols}."


def _task_block(unit: ExtractionUnit, options: PlanOptions) -> str:
    count = len(unit.expected_cells)
    lines = [
        "TASK",
        f"Read the {count} cell(s) in scope. Return exactly one JSON object:",
        '{"cells": [{"row": <row id>, "column": <column id>, '
        '"raw": "<the number exactly as printed>", "value": <number or null>}]}',
        "- row and column are the ids printed above; never renumber them.",
        "- raw must be copied character for character from the source.",
        "- value is the number without unit, without thousands separators, "
        "decimal point as printed; null if the cell prints no number.",
        "- Omit a cell that is not printed at all. Never estimate, convert or compute.",
        "- Do not assign arms: the arm of every column is already given above.",
        "- No commentary, no markdown, no code fences.",
    ]
    if options.include_footnotes:
        lines.append("- Check the footnotes before you read a value.")
    return "\n".join(lines)


def _build_prompt(table: Table, unit: ExtractionUnit, options: PlanOptions,
                  document_text: str) -> str:
    parts: List[str] = [_table_header(table), _study_context(table)]
    legend = _column_legend(table)
    parts.append(legend)
    groups = _group_header_lines(table)
    if groups:
        parts.append("\n".join(groups))
    if options.include_verbatim and unit.direction == DIRECTION_FULL:
        verbatim = _verbatim_block(table, document_text)
        if verbatim:
            parts.append("\n".join(verbatim))
    if unit.direction == DIRECTION_CELL:
        row_id, col_id = unit.row_ids[0], unit.col_ids[0]
        column = table.column(col_id)
        lines = ["FOCUS CELL CONTEXT"]
        if column is not None:
            lines.append(
                f"column {col_id}: {header_path_text(column.header_path)}"
                + (f" | arm={column.arm}" if column.arm else " | arm=unassigned")
            )
        row = table.row(row_id)
        if row is not None:
            lines.append(f"row {row_id} label: {row.label or '(no row label)'}")
        sibling_rows = [
            r for r in table.rows
            if r.row_id != row_id and col_id in r.cells and _cell_text(r.cells[col_id])
        ][:5]
        if sibling_rows:
            lines.append("other rows of the same column (context only):")
            for r in sibling_rows:
                lines.append(f"  row {r.row_id} | {r.label or '(no label)'} | {_cell_text(r.cells[col_id])}")
        parts.append("\n".join(lines))
        rows_ids = [row_id]
        cols_ids = [col_id]
        parts.append(_rows_block(table, rows_ids, cols_ids))
    else:
        parts.append(_rows_block(table, unit.row_ids, unit.col_ids))
    footnotes = _footnote_block(table, options)
    if footnotes:
        parts.append("\n".join(footnotes))
    parts.append(_scope_text(table, unit))
    parts.append(_task_block(unit, options))
    return "\n\n".join(part for part in parts if part)


# --- Planungshelfer -------------------------------------------------------

def _chunk(items: Sequence[int], limit: int) -> List[List[int]]:
    """Ein Element je Einheit, solange das Budget reicht; sonst Buendel."""
    if not items:
        return []
    limit = max(1, limit)
    if len(items) <= limit:
        return [[item] for item in items]
    size = math.ceil(len(items) / limit)
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def _present_cells(table: Table, row_ids: Sequence[int], col_ids: Sequence[int]) -> List[Tuple[int, int]]:
    cells: List[Tuple[int, int]] = []
    for row_id in row_ids:
        row = table.row(row_id)
        if row is None:
            continue
        for col_id in col_ids:
            cell = row.cells.get(col_id)
            if cell is not None and _cell_text(cell):
                cells.append((row_id, col_id))
    return cells


def _make_unit(table: Table, strategy: str, direction: str, unit_id: str,
               row_ids: Sequence[int], col_ids: Sequence[int],
               options: PlanOptions, document_text: str,
               context_row_ids: Sequence[int] = (),
               context_col_ids: Sequence[int] = (),
               depth: int = 0, parent_unit_id: str = "",
               notes: Sequence[str] = ()) -> ExtractionUnit:
    unit = ExtractionUnit(
        unit_id=unit_id,
        strategy=strategy,
        direction=direction,
        table_id=table.table_id,
        doc_id=table.doc_id,
        row_ids=list(row_ids),
        col_ids=list(col_ids),
        context_row_ids=list(context_row_ids),
        context_col_ids=list(context_col_ids),
        expected_cells=_present_cells(table, row_ids, col_ids),
        depth=depth,
        parent_unit_id=parent_unit_id,
        notes=list(notes),
    )
    unit.crop = make_crop(table, unit.row_ids, unit.col_ids, crop_id=f"crop:{unit_id}",
                          context_row_ids=unit.context_row_ids,
                          context_col_ids=unit.context_col_ids)
    unit.prompt = _build_prompt(table, unit, options, document_text)
    return unit


def _full_units(table: Table, strategy: str, options: PlanOptions,
                document_text: str) -> List[ExtractionUnit]:
    col_ids = table.data_columns
    row_ids = [r.row_id for r in table.rows]
    return [_make_unit(table, strategy, DIRECTION_FULL,
                       unit_id=f"{table.table_id}/{strategy}/full", row_ids=row_ids,
                       col_ids=col_ids, options=options, document_text=document_text)]


def _column_units(table: Table, strategy: str, options: PlanOptions,
                  document_text: str) -> List[ExtractionUnit]:
    columns = [c.col_id for c in target_columns(table)]
    if not columns:
        return []
    row_ids = [r.row_id for r in table.rows]
    chunks = _chunk(columns, options.max_units_per_table)
    units: List[ExtractionUnit] = []
    for position, chunk in enumerate(chunks, start=1):
        suffix = f"c{chunk[0]}" if len(chunk) == 1 else f"c{chunk[0]}-c{chunk[-1]}"
        notes = (
            ["Spalten ohne Zielfeld sind ausgelassen (kein Arm belegt)."]
            if unassigned_columns(table) else []
        )
        units.append(
            _make_unit(
                table, strategy, DIRECTION_COLUMN,
                unit_id=f"{table.table_id}/{strategy}/col/{suffix}",
                row_ids=row_ids, col_ids=chunk, options=options,
                document_text=document_text, context_col_ids=[],
                notes=notes,
            )
        )
    return units


def _row_units(table: Table, strategy: str, options: PlanOptions,
               document_text: str) -> List[ExtractionUnit]:
    col_ids = table.data_columns
    row_ids = [r.row_id for r in table.rows]
    chunks = _chunk(row_ids, options.max_units_per_table)
    units: List[ExtractionUnit] = []
    for chunk in chunks:
        suffix = f"r{chunk[0]}" if len(chunk) == 1 else f"r{chunk[0]}-r{chunk[-1]}"
        units.append(
            _make_unit(
                table, strategy, DIRECTION_ROW,
                unit_id=f"{table.table_id}/{strategy}/row/{suffix}",
                row_ids=chunk, col_ids=col_ids, options=options,
                document_text=document_text,
                context_row_ids=[r for r in row_ids if r not in chunk][:3],
            )
        )
    return units


def plan(table: Table, strategy: str = STRATEGY_FULL,
         options: Optional[PlanOptions] = None,
         document_text: str = "") -> DecompositionPlan:
    """Zerlegungsplan fuer eine Tabelle und ein Verfahren."""
    options = options or PlanOptions()
    strategy = (strategy or STRATEGY_FULL).upper()
    complexity = assess(table)
    notes: List[str] = []

    if strategy == STRATEGY_FULL:
        units = _full_units(table, strategy, options, document_text)
    elif strategy == STRATEGY_VERTICAL:
        units = _column_units(table, strategy, options, document_text)
        if not units:
            notes.append(
                "Keine Spalte mit belegtem Arm: vertikale Zerlegung nicht moeglich, "
                "Full-Table als Ausweichweg."
            )
            units = _full_units(table, STRATEGY_VERTICAL, options, document_text)
    elif strategy == STRATEGY_HORIZONTAL:
        units = _row_units(table, strategy, options, document_text)
    elif strategy == STRATEGY_BIDIRECTIONAL and options.max_units_per_table < 2:
        notes.append(
            "Budget unter zwei Einheiten: beidseitige Zerlegung nicht moeglich, "
            "Full-Table als Ausweichweg."
        )
        units = _full_units(table, strategy, options, document_text)
    elif strategy == STRATEGY_BIDIRECTIONAL:
        row_options = replace(options, max_units_per_table=max(1, options.max_units_per_table // 2))
        col_options = replace(options, max_units_per_table=max(1, options.max_units_per_table // 2))
        units = _row_units(table, strategy, row_options, document_text)
        units += _column_units(table, strategy, col_options, document_text)
        if not any(u.direction == DIRECTION_COLUMN for u in units):
            notes.append("Keine Spalte mit belegtem Arm: nur zeilenweise Zerlegung.")
    elif strategy == STRATEGY_ADAPTIVE:
        units, adaptive_notes = _adaptive_units(table, complexity, options, document_text)
        notes.extend(adaptive_notes)
    else:
        raise ValueError(f"unbekanntes Verfahren: {strategy!r}")

    mark_overlaps([u.crop for u in units if u.crop])
    return DecompositionPlan(table_id=table.table_id, strategy=strategy,
                             complexity=complexity, units=units, notes=notes)


def render_table_view(table: Table, options: Optional[PlanOptions] = None) -> str:
    """Strukturierte Tabellenansicht fuer den Pipeline-Zusatz.

    Dieselben Bausteine wie die Einheiten-Prompts, aber ohne Auftrag: Header-
    Hierarchie, Zeilenlabels und Werte je Spalte, Fussnoten. Die Originaltext-
    laeufe bleiben unangetastet - der Aufrufer haengt diese Ansicht an.
    """
    options = options or PlanOptions()
    parts: List[str] = [_table_header(table), _column_legend(table)]
    groups = _group_header_lines(table)
    if groups:
        parts.append("\n".join(groups))
    parts.append(_rows_block(table, [r.row_id for r in table.rows], table.data_columns))
    footnotes = _footnote_block(table, options)
    if footnotes:
        parts.append("\n".join(footnotes))
    return "\n\n".join(part for part in parts if part)


def _adaptive_units(table: Table, complexity: ComplexityScore,
                    options: PlanOptions,
                    document_text: str) -> Tuple[List[ExtractionUnit], List[str]]:
    """Verfahren E: Aufwand nach gemessener Komplexitaet.

    Einfach -> eine Volltabellen-Einheit. Mittel -> spaltenweise, aber nur wenn
    genug Spalten da sind (sonst waere die Zerlegung reiner Aufwand ohne
    Kontextgewinn). Komplex/sehr komplex -> beidseitig; die Zellennacharbeit
    entscheidet der Lauf (siehe ``refinement_units``).
    """
    notes: List[str] = [f"Komplexitaet {complexity.score:.2f} ({complexity.class_label})."]
    columns = [c.col_id for c in target_columns(table)]
    if complexity.class_label == SIMPLE:
        notes.append("Einfache Tabelle: eine Volltabellen-Einheit.")
        return _full_units(table, STRATEGY_ADAPTIVE, options, document_text), notes
    if complexity.class_label == MEDIUM:
        if len(columns) < options.min_columns_for_split:
            notes.append(
                f"Nur {len(columns)} Zielspalten: Volltabelle ist billiger als Zerlegung."
            )
            return _full_units(table, STRATEGY_ADAPTIVE, options, document_text), notes
        notes.append("Mittlere Komplexitaet: spaltenweise Zerlegung.")
        return _column_units(table, STRATEGY_ADAPTIVE, options, document_text), notes
    if options.max_units_per_table < 2:
        notes.append(
            "Budget unter zwei Einheiten: beidseitige Zerlegung nicht moeglich, "
            "Full-Table als Ausweichweg."
        )
        return _full_units(table, STRATEGY_ADAPTIVE, options, document_text), notes
    notes.append("Komplexe Tabelle: beidseitige Zerlegung (Zeile und Spalte).")
    half = max(1, options.max_units_per_table // 2)
    row_options = replace(options, max_units_per_table=half)
    col_options = replace(options, max_units_per_table=half)
    units = _row_units(table, STRATEGY_ADAPTIVE, row_options, document_text)
    units += _column_units(table, STRATEGY_ADAPTIVE, col_options, document_text)
    if complexity.class_label == VERY_COMPLEX:
        notes.append("Sehr komplex: Zellennacharbeit fuer ungeklaerte Zellen vorgesehen.")
    return units, notes


def refinement_units(table: Table, addresses: Sequence[Tuple[int, int]],
                     options: Optional[PlanOptions] = None,
                     document_text: str = "", depth: int = 1,
                     parent_unit_id: str = "") -> List[ExtractionUnit]:
    """Zellgenaue Nachverarbeitung fuer ungeklaerte Adressen.

    Zellen, die nach der ersten Runde fehlen oder widerspruechlich sind, werden
    einzeln mit ihrem Header-Pfad, ihrem Zeilenlabel, den Nachbarzeilen
    derselben Spalte und den Fussnoten erneut gelesen. Die Zahl der Auftraege
    ist gedeckelt - Nacharbeit ist teuer und soll nicht zum Selbstzweck werden.
    """
    options = options or PlanOptions()
    units: List[ExtractionUnit] = []
    seen: set = set()
    for row_id, col_id in addresses:
        if (row_id, col_id) in seen:
            continue
        seen.add((row_id, col_id))
        if len(units) >= options.max_refinement_units:
            break
        if table.row(row_id) is None or table.column(col_id) is None:
            continue
        units.append(
            _make_unit(
                table, STRATEGY_ADAPTIVE, DIRECTION_CELL,
                unit_id=f"{table.table_id}/E/cell/d{depth}/r{row_id}c{col_id}",
                row_ids=[row_id], col_ids=[col_id], options=options,
                document_text=document_text, depth=depth,
                parent_unit_id=parent_unit_id,
                notes=["Nachverarbeitung nach ungeklaerter erster Lesung."],
            )
        )
    return units


def unresolved_addresses(table: Table, results: Sequence[Any],
                         reported: Dict[Tuple[int, int], List[float]]) -> List[Tuple[int, int]]:
    """Adressen, die eine zweite, kleinere Lesung verdienen.

    Ungeklaert ist eine Zelle, wenn sie im Quelltext steht, aber
    (a) keine Einheit einen Wert geliefert hat, oder (b) mehrere Einheiten
    verschiedene Werte geliefert haben.
    """
    del results  # die Ergebnisliste dient der Vollstaendigkeit, nicht der Regel
    unresolved: List[Tuple[int, int]] = []
    for table_row in table.rows:
        for col_id, cell in table_row.cells.items():
            if not _cell_text(cell):
                continue
            if table.column(col_id) is None or table.column(col_id).role == ROLE_LABEL:
                continue
            values = reported.get((table_row.row_id, col_id), [])
            if len(set(values)) > 1 or not values:
                unresolved.append((table_row.row_id, col_id))
    return unresolved
