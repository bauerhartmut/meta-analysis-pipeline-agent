"""Kontextbewahrende Ausschnitte (Crops) einer Tabelle.

Ein Crop beschreibt zwei Dinge zugleich:

* den **strukturierten** Ausschnitt (welche Zeilen und Spalten gelesen werden,
  welche Zeilen/Spalten nur als Kontext mitlaufen), und
* die **Fundstelle** im Dokument: Zeichenspanne, Zeilenspanne und eine
  normalisierte Bounding-Box.

Die Bounding-Box bezieht sich auf das Textlayout der Quelle
(``text-layout/1000``), nicht auf Pixel: die Yun-Markdown-Dokumente tragen
keine Seitenkoordinaten. Fuer PDF-Quellen liefert ``image`` den Seitenverweis
mit, damit ein Bild-Crop dieselbe Box benutzen kann; fehlt die Seite, steht
``available: false`` - es wird keine Koordinate erfunden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import Table

COORDINATE_SYSTEM = "text-layout/1000"


@dataclass
class TableCrop:
    crop_id: str
    table_id: str
    doc_id: str
    row_ids: List[int] = field(default_factory=list)
    col_ids: List[int] = field(default_factory=list)
    context_row_ids: List[int] = field(default_factory=list)
    context_col_ids: List[int] = field(default_factory=list)
    page: Optional[int] = None
    line_start: int = -1
    line_end: int = -1
    char_start: int = -1
    char_end: int = -1
    focus_char_span: Tuple[int, int] = (-1, -1)
    bbox_norm: Optional[Tuple[int, int, int, int]] = None
    coordinate_system: str = COORDINATE_SYSTEM
    includes_caption: bool = False
    includes_footnotes: bool = False
    overlaps: List[str] = field(default_factory=list)
    image: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop_id": self.crop_id,
            "table_id": self.table_id,
            "doc_id": self.doc_id,
            "row_ids": list(self.row_ids),
            "col_ids": list(self.col_ids),
            "context_row_ids": list(self.context_row_ids),
            "context_col_ids": list(self.context_col_ids),
            "page": self.page,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "focus_char_span": list(self.focus_char_span),
            "bbox_norm": list(self.bbox_norm) if self.bbox_norm else None,
            "coordinate_system": self.coordinate_system,
            "includes_caption": self.includes_caption,
            "includes_footnotes": self.includes_footnotes,
            "overlaps": list(self.overlaps),
            "image": dict(self.image),
        }


def _bbox(table: Table, row_ids: Sequence[int], col_ids: Sequence[int]) -> Optional[Tuple[int, int, int, int]]:
    """Normalisierte Box (x1, y1, x2, y2) im Textlayout der Tabelle."""
    if not table.columns or not table.rows:
        return None
    x_min = min(c.x_start for c in table.columns)
    x_max = max(c.x_end for c in table.columns)
    if x_max <= x_min:
        return None
    focus_cols = [c for c in table.columns if c.col_id in set(col_ids)] or table.columns
    focus_rows = [r for r in table.rows if r.row_id in set(row_ids)] or table.rows
    left = min(c.x_start for c in focus_cols)
    right = max(c.x_end for c in focus_cols)
    top_row = min(focus_rows, key=lambda r: r.line if r.line >= 0 else 0)
    bottom_row = max(focus_rows, key=lambda r: r.line if r.line >= 0 else 0)
    first_line = table.line_start if table.line_start >= 0 else top_row.line
    last_line = table.line_end if table.line_end >= 0 else bottom_row.line
    height = max(last_line - first_line, 1)
    x1 = int(round((left - x_min) / (x_max - x_min) * 1000))
    x2 = int(round((right - x_min) / (x_max - x_min) * 1000))
    y1 = int(round((top_row.line - first_line) / height * 1000))
    y2 = int(round((bottom_row.line + 1 - first_line) / height * 1000))
    return (
        max(0, min(1000, x1)),
        max(0, min(1000, y1)),
        max(0, min(1000, x2)),
        max(0, min(1000, y2)),
    )


def make_crop(
    table: Table,
    row_ids: Sequence[int],
    col_ids: Sequence[int],
    crop_id: str,
    context_row_ids: Sequence[int] = (),
    context_col_ids: Sequence[int] = (),
) -> TableCrop:
    """Crop fuer einen Ausschnitt; Caption und Fussnoten laufen immer mit.

    Die Zeichenspanne umfasst bewusst die ganze Tabellenregion (Caption bis
    Fussnotenblock): ein Ausschnitt ohne Ueberschrift und ohne Legende ist
    nicht interpretierbar. Die *Fokus*-Spanne der gelesenen Zellen steht
    getrennt in ``focus_char_span``.
    """
    focus_cells = [
        row.cells[col_id]
        for row in table.rows if row.row_id in set(row_ids)
        for col_id in col_ids if col_id in row.cells
    ]
    if focus_cells:
        focus_start = min(c.start_char for c in focus_cells if c.start_char >= 0)
        focus_end = max(c.end_char for c in focus_cells if c.end_char >= 0)
    else:
        focus_start, focus_end = -1, -1

    char_start = table.char_start
    if table.caption_char_span[0] >= 0:
        char_start = min(char_start, table.caption_char_span[0]) if char_start >= 0 else table.caption_char_span[0]
    char_end = table.char_end
    crop = TableCrop(
        crop_id=crop_id,
        table_id=table.table_id,
        doc_id=table.doc_id,
        row_ids=list(row_ids),
        col_ids=list(col_ids),
        context_row_ids=list(context_row_ids),
        context_col_ids=list(context_col_ids),
        page=table.page,
        line_start=table.line_start,
        line_end=table.line_end,
        char_start=char_start,
        char_end=char_end,
        focus_char_span=(focus_start, focus_end),
        bbox_norm=_bbox(table, row_ids, col_ids),
        includes_caption=bool(table.caption),
        includes_footnotes=bool(table.footnote_block),
    )
    crop.image = {
        "available": table.page is not None,
        "page": table.page,
        "bbox_norm": list(crop.bbox_norm) if crop.bbox_norm else None,
        "coordinate_system": COORDINATE_SYSTEM,
        "note": (
            "Seite aus der Quelle uebernommen"
            if table.page is not None
            else "Quelle traegt keine Seitenangabe; keine Pixelkoordinaten erfunden"
        ),
    }
    return crop


def mark_overlaps(crops: Sequence[TableCrop]) -> List[TableCrop]:
    """Ueberlappende Crops an den Schnittgrenzen benennen.

    Zwei Ausschnitte, die dieselbe Zelle als Fokus lesen, ueberlappen; das wird
    notiert, damit die Rekonstruktion weiss, wo ein Vergleich moeglich ist.
    """
    by_cell: Dict[Tuple[int, int], List[str]] = {}
    for crop in crops:
        for row_id in crop.row_ids:
            for col_id in crop.col_ids:
                by_cell.setdefault((row_id, col_id), []).append(crop.crop_id)
    for crop in crops:
        shared = set()
        for row_id in crop.row_ids:
            for col_id in crop.col_ids:
                others = [c for c in by_cell.get((row_id, col_id), []) if c != crop.crop_id]
                shared.update(others)
        crop.overlaps = sorted(shared)
    return list(crops)
