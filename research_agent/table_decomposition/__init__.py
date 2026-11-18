"""Table Decomposition & Reconstruction Engine (modellunabhaengig).

Zerlegt wissenschaftliche Tabellen in kontextbewahrende Einheiten, extrahiert
diese separat und setzt die Teilresultate zu einer konsistenten Tabelle
zusammen. Oeffentliche Schnittstelle siehe ``README.md``.
"""

from __future__ import annotations

from .model import (  # noqa: F401
    ARM_COMPARATOR,
    ARM_INTERVENTION,
    FIELDS,
    Cell,
    Column,
    DocumentTables,
    Footnote,
    HeaderBand,
    Row,
    Table,
    field_for,
)
from .parser import parse_document, parse_value  # noqa: F401
from .semantics import bind_arm, enrich_table, role_for_header  # noqa: F401

__all__ = [
    "ARM_COMPARATOR",
    "ARM_INTERVENTION",
    "FIELDS",
    "Cell",
    "Column",
    "DocumentTables",
    "Footnote",
    "HeaderBand",
    "Row",
    "Table",
    "field_for",
    "parse_document",
    "parse_value",
    "bind_arm",
    "enrich_table",
    "role_for_header",
]
