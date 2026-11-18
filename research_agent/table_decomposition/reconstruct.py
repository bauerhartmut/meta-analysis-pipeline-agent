"""Reconstruction Engine: Teilresultate zu einer Tabelle zusammensetzen.

Regeln:

* Jede Evidenz traegt ihre volle Herkunft: Adresse, Feld, Arm, Rolle, Einheit,
  Tabellen- und Dokument-ID, Seite, Einheit-ID, Verfahren, Richtung, Modell,
  Zitat und Crop.
* Gleiche Adresse + gleicher normalisierter Wert = **ein** Befund mit mehreren
  Belegen (Duplikat erkannt, nicht doppelt gezaehlt).
* Verschiedene Werte an derselben Adresse = **Konflikt**. Es wird nichts
  ueberschrieben, nichts gemittelt und nichts stillschweigend ausgewaehlt; der
  Konflikt bleibt mit allen Kandidaten stehen.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .parser import parse_value

import re

from .backend import PredictedCell, UnitResult
from .model import ROLE_LABEL, ROLE_SD, Table, field_for, header_path_text

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
from .strategies import DIRECTION_COLUMN, DIRECTION_ROW, ExtractionUnit

STATUS_AGREED = "agreed"
STATUS_SINGLE = "single"
STATUS_CONFLICT = "conflict"


@dataclass
class Evidence:
    row_id: int
    col_id: int
    value: Optional[float]
    table_id: str
    doc_id: str
    raw: str = ""
    quote: str = ""
    field: Optional[str] = None
    arm: Optional[str] = None
    role: str = ""
    unit: str = ""
    page: Optional[int] = None
    unit_id: str = ""
    strategy: str = ""
    direction: str = ""
    model: str = ""
    crop_id: str = ""
    depth: int = 0
    row_label: str = ""
    header_path: Tuple[str, ...] = ()
    source_value: Optional[float] = None
    source_present: bool = False
    derived: bool = False   # zweiter Wert aus derselben Zelle (Verbundwert)

    @property
    def address(self) -> Tuple[int, int]:
        return (self.row_id, self.col_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "col_id": self.col_id,
            "value": self.value,
            "value_raw": self.raw,
            "quote": self.quote,
            "field": self.field,
            "arm": self.arm,
            "role": self.role,
            "unit": self.unit,
            "table_id": self.table_id,
            "doc_id": self.doc_id,
            "page": self.page,
            "unit_id": self.unit_id,
            "strategy": self.strategy,
            "direction": self.direction,
            "model": self.model,
            "crop_id": self.crop_id,
            "depth": self.depth,
            "row_label": self.row_label,
            "header_path": list(self.header_path),
            "source_value": self.source_value,
            "source_present": self.source_present,
            "derived": self.derived,
        }


@dataclass
class CellResult:
    row_id: int
    col_id: int
    table_id: str
    field: Optional[str] = None
    arm: Optional[str] = None
    role: str = ""
    unit: str = ""
    status: str = STATUS_SINGLE
    value: Optional[float] = None
    candidates: List[float] = dc_field(default_factory=list)
    evidence: List[Evidence] = dc_field(default_factory=list)
    row_label: str = ""
    header_path: Tuple[str, ...] = ()
    page: Optional[int] = None
    derived: bool = False

    @property
    def address(self) -> Tuple[int, int]:
        return (self.row_id, self.col_id)

    @property
    def support(self) -> int:
        return len({e.unit_id for e in self.evidence})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "col_id": self.col_id,
            "table_id": self.table_id,
            "field": self.field,
            "arm": self.arm,
            "role": self.role,
            "unit": self.unit,
            "status": self.status,
            "value": self.value,
            "candidates": list(self.candidates),
            "support": self.support,
            "row_label": self.row_label,
            "header_path": list(self.header_path),
            "page": self.page,
            "derived": self.derived,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class ReconstructionResult:
    table_id: str
    doc_id: str
    cells: List[CellResult] = dc_field(default_factory=list)
    conflicts: List[CellResult] = dc_field(default_factory=list)
    stats: Dict[str, Any] = dc_field(default_factory=dict)
    notes: List[str] = dc_field(default_factory=list)

    def by_address(self) -> Dict[Tuple[int, int], CellResult]:
        """Zelle je Adresse; abgeleitete Zweitwerte bleiben aussen vor."""
        return {(c.row_id, c.col_id): c for c in self.cells if not c.derived}

    def values_by_address(self) -> Dict[Tuple[int, int], List[float]]:
        result: Dict[Tuple[int, int], List[float]] = {}
        for cell in self.cells:
            result[cell.address] = [e.value for e in cell.evidence if e.value is not None]
        return result

    def prediction_cells(self) -> List[Dict[str, Any]]:
        """Zellen mit Feld und eindeutigem Wert (Konflikte bleiben draussen)."""
        cells: List[Dict[str, Any]] = []
        for cell in self.cells:
            if cell.status == STATUS_CONFLICT or cell.field is None or cell.value is None:
                continue
            cells.append(
                {
                    "field": cell.field,
                    "arm": cell.arm,
                    "value": cell.value,
                    "row_id": cell.row_id,
                    "col_id": cell.col_id,
                    "table_id": cell.table_id,
                    "row_label": cell.row_label,
                    "page": cell.page,
                    "support": cell.support,
                    "status": cell.status,
                    "unit": cell.unit,
                    "quote": cell.evidence[0].raw if cell.evidence else "",
                }
            )
        return cells

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "doc_id": self.doc_id,
            "stats": dict(self.stats),
            "notes": list(self.notes),
            "cells": [c.to_dict() for c in self.cells],
            "conflicts": [c.to_dict() for c in self.conflicts],
        }


class Reconstruction:
    """Sammelt Belege und setzt sie zu einer Tabelle zusammen."""

    def __init__(self):
        self._evidence: List[Evidence] = []
        self._table: Optional[Table] = None
        self.notes: List[str] = []

    def register_table(self, table: Table) -> None:
        self._table = table

    def add_result(self, table: Table, unit: ExtractionUnit, result: UnitResult) -> int:
        """Alle Zellen einer Einheit als Belege uebernehmen; Anzahl zurueck."""
        added = 0
        for cell in result.cells:
            if self.add_cell(table, unit, cell, model=result.model):
                added += 1
        return added

    def add_cell(self, table: Table, unit: ExtractionUnit, cell: PredictedCell,
                 model: str = "") -> bool:
        column = table.column(cell.col_id)
        row = table.row(cell.row_id)
        if column is None or row is None:
            self.notes.append(
                f"{unit.unit_id}: Adresse row {cell.row_id}/col {cell.col_id} "
                "existiert nicht in der Tabelle und wurde verworfen."
            )
            return False
        if column.role == ROLE_LABEL:
            self.notes.append(
                f"{unit.unit_id}: Adresse row {cell.row_id}/col {cell.col_id} "
                "ist eine Labelspalte und traegt kein numerisches Feld."
            )
            return False
        source_cell = row.cells.get(cell.col_id)
        self._evidence.append(
            Evidence(
                row_id=cell.row_id,
                col_id=cell.col_id,
                value=cell.value,
                raw=cell.raw,
                quote=cell.quote,
                table_id=table.table_id,
                doc_id=table.doc_id,
                field=column.field,
                arm=column.arm,
                role=column.role,
                unit=column.unit,
                page=table.page,
                unit_id=unit.unit_id,
                strategy=unit.strategy,
                direction=unit.direction,
                model=model,
                crop_id=unit.crop.crop_id if unit.crop else "",
                depth=unit.depth,
                row_label=row.label,
                header_path=column.header_path,
                source_value=source_cell.value if source_cell is not None else None,
                source_present=bool(source_cell is not None and (source_cell.text or "").strip()),
            )
        )
        self._add_secondary(table, unit, cell, column, row, model)
        return True

    def _add_secondary(self, table: Table, unit: ExtractionUnit, cell: PredictedCell,
                       column: Any, row: Any, model: str) -> None:
        """Zweiten Wert einer Verbundzelle (``12.4 (3.1)``) als eigenen Beleg.

        Der Wert wird nicht geschaetzt, sondern woertlich aus dem Zitat
        gelesen, das das Modell zurueckgibt; die Fundstelle bleibt dieselbe
        Zelle. Ohne zweite Zahl entsteht kein Beleg.
        """
        if not column.secondary_role or not column.arm:
            return
        text = (cell.raw or "").strip() or (cell.quote or "").strip()
        numbers = _NUMBER_RE.findall(text)
        if len(numbers) < 2:
            return
        value = parse_value(numbers[1])
        if isinstance(value, (int, float)):
            secondary_value = float(value)
        elif value is not None and getattr(value, "value", None) is not None:
            secondary_value = float(value.value)
        else:
            return
        self._evidence.append(
            Evidence(
                row_id=cell.row_id,
                col_id=cell.col_id,
                value=secondary_value,
                raw=cell.raw or text,
                quote=cell.quote,
                table_id=table.table_id,
                doc_id=table.doc_id,
                field=field_for(column.secondary_role, column.arm),
                arm=column.arm,
                role=column.secondary_role,
                unit=column.unit,
                page=table.page,
                unit_id=unit.unit_id,
                strategy=unit.strategy,
                direction=unit.direction,
                model=model,
                crop_id=unit.crop.crop_id if unit.crop else "",
                depth=unit.depth,
                row_label=row.label,
                header_path=column.header_path,
                source_value=None,
                source_present=True,
                derived=True,
            )
        )

    def build(self) -> ReconstructionResult:
        grouped: Dict[Tuple[int, int, str], List[Evidence]] = {}
        for evidence in self._evidence:
            grouped.setdefault(
                (evidence.address[0], evidence.address[1], evidence.role), []
            ).append(evidence)

        cells: List[CellResult] = []
        conflicts: List[CellResult] = []
        direction_pairs: Dict[str, int] = {"both": 0, "agreed": 0, "differ": 0}
        for _key, evidences in sorted(grouped.items()):
            address = evidences[0].address
            values = [e.value for e in evidences if e.value is not None]
            distinct = sorted(set(values))
            first = evidences[0]
            status = STATUS_SINGLE
            value: Optional[float] = None
            candidates: List[float] = []
            if len(distinct) > 1:
                status = STATUS_CONFLICT
                candidates = distinct
            elif len(distinct) == 1:
                value = distinct[0]
                if len({e.unit_id for e in evidences}) > 1:
                    status = STATUS_AGREED
            else:
                # Nur Belege ohne Zahl: Zelle wurde gelesen, traegt aber keinen Wert.
                status = STATUS_SINGLE
            cell = CellResult(
                row_id=address[0],
                col_id=address[1],
                table_id=first.table_id,
                field=first.field,
                arm=first.arm,
                role=first.role,
                unit=first.unit,
                status=status,
                value=value,
                candidates=candidates,
                evidence=evidences,
                row_label=first.row_label,
                header_path=first.header_path,
                page=first.page,
                derived=first.derived,
            )
            cells.append(cell)
            if status == STATUS_CONFLICT:
                conflicts.append(cell)

            directions = {e.direction for e in evidences}
            if DIRECTION_ROW in directions and DIRECTION_COLUMN in directions:
                direction_pairs["both"] += 1
                if status == STATUS_CONFLICT:
                    direction_pairs["differ"] += 1
                elif value is not None:
                    direction_pairs["agreed"] += 1

        by_direction: Dict[str, int] = {}
        for evidence in self._evidence:
            by_direction[evidence.direction] = by_direction.get(evidence.direction, 0) + 1

        stats = {
            "n_evidence": len(self._evidence),
            "n_cells": len(cells),
            "n_agreed": len([c for c in cells if c.status == STATUS_AGREED]),
            "n_single": len([c for c in cells if c.status == STATUS_SINGLE]),
            "n_conflict": len(conflicts),
            "n_with_value": len([c for c in cells if c.value is not None]),
            "n_field_cells": len([c for c in cells if c.field]),
            "n_derived": len([c for c in cells if c.derived]),
            "evidence_by_direction": by_direction,
            "bidirectional": direction_pairs,
        }
        return ReconstructionResult(
            table_id=self._table.table_id if self._table else "",
            doc_id=self._table.doc_id if self._table else "",
            cells=cells,
            conflicts=conflicts,
            stats=stats,
            notes=list(self.notes),
        )


def unreported_addresses(table: Table, result: ReconstructionResult,
                         only_fields: bool = True) -> List[Tuple[int, int]]:
    """Zellen, die im Quelltext stehen, aber in keiner Lesung auftauchen.

    ``only_fields`` beschraenkt die Liste auf Spalten mit Zielfeld. Zellen in
    Prozent- oder p-Wert-Spalten sind keine Armfelder; sie nachzulesen waere
    Aufwand ohne Ertrag und wuerde das Budget der Nacharbeit verbrauchen.
    """
    seen = set(result.values_by_address())
    missing: List[Tuple[int, int]] = []
    labels = set(table.label_columns)
    for row in table.rows:
        for col_id, cell in sorted(row.cells.items()):
            if col_id in labels or not (cell.text or "").strip():
                continue
            column = table.column(col_id)
            if only_fields and (column is None or column.field is None):
                continue
            if (row.row_id, col_id) not in seen:
                missing.append((row.row_id, col_id))
    return missing


def conflicts(result: ReconstructionResult) -> List[CellResult]:
    return [c for c in result.cells if c.status == STATUS_CONFLICT]
