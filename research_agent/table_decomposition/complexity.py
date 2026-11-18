"""Tabellenkomplexitaet - deterministisch, ohne Modell.

Die Komplexitaet steuert die adaptive Zerlegung (Verfahren E) und die
geschichtete Auswahl im Benchmark. Sie ist bewusst aus messbaren
Strukturmerkmalen gebildet, nicht aus einer Modellmeinung: Anzahl Header-Ebenen,
Gruppenheader, Spalten, Zeilen, Fussnoten, unregelmaessige Zeilen und nicht
zuordenbare Spalten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .model import ROLE_LABEL, Table
from .semantics import target_columns, unassigned_columns

_TIMEPOINT_RE = re.compile(
    r"\b(?:baseline|week|weeks|wk|month|months|mo|day|days|year|years|"
    r"follow[- ]?up|endpoint|post|pre|t\d|\d+\s*(?:h|hr|hrs|d|w|mo|y))\b",
    re.IGNORECASE,
)

SIMPLE = "einfach"
MEDIUM = "mittel"
COMPLEX = "komplex"
VERY_COMPLEX = "sehr_komplex"


@dataclass
class ComplexityScore:
    score: float
    class_label: str
    features: Dict[str, Any] = field(default_factory=dict)
    drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "class": self.class_label,
            "features": dict(self.features),
            "drivers": list(self.drivers),
        }


def assess(table: Table) -> ComplexityScore:
    """Komplexitaet einer Tabelle als Punktwert plus benannte Treiber."""
    header_levels = len({band.level for band in table.header_bands})
    group_headers = [b for b in table.header_bands if b.span > 1]
    arm_groups = {
        (b.text or "").strip().lower()
        for b in group_headers
        if b.text and b.level == min((x.level for x in table.header_bands), default=0)
    }
    data_cols = [c for c in table.columns if c.role != ROLE_LABEL]
    irregular = len([r for r in table.rows if r.irregular])
    rows = max(len(table.rows), 1)
    unassigned = unassigned_columns(table)
    timepoints = any(
        _TIMEPOINT_RE.search(b.text or "") for b in table.header_bands
    ) or any(_TIMEPOINT_RE.search(r.label or "") for r in table.rows)

    dr: List[str] = []
    score = 0.0

    levels_part = min(max(header_levels - 1, 0) * 0.18, 0.36)
    if levels_part:
        dr.append(f"{header_levels} Header-Ebenen")
    score += levels_part

    if group_headers:
        score += 0.12
        dr.append(f"{len(group_headers)} zusammengefuehrte Header-Zellen")
    if len(arm_groups) >= 3:
        score += 0.08
        dr.append(f"{len(arm_groups)} Spaltengruppen")
    score += min(len(data_cols) / 12, 1.0) * 0.15
    if len(data_cols) > 8:
        dr.append(f"{len(data_cols)} Datenspalten")
    score += min(rows / 20, 1.0) * 0.10
    if rows > 12:
        dr.append(f"{len(table.rows)} Datenzeilen")
    if table.footnotes:
        score += 0.08
        dr.append(f"{len(table.footnotes)} Fussnoten")
    if irregular:
        share = irregular / rows
        score += 0.20 * share
        dr.append(f"{irregular}/{rows} unregelmaessige Zeilen")
    if unassigned:
        share = len(unassigned) / max(len(data_cols), 1)
        score += 0.15 * share
        dr.append(f"{len(unassigned)} Spalten ohne Zielfeld")
    if timepoints:
        score += 0.10
        dr.append("Zeitpunktangaben in Kopf oder Zeilen")

    score = max(0.0, min(1.0, score))
    if score < 0.25:
        label = SIMPLE
    elif score < 0.45:
        label = MEDIUM
    elif score < 0.65:
        label = COMPLEX
    else:
        label = VERY_COMPLEX

    features = {
        "n_rows": len(table.rows),
        "n_data_columns": len(data_cols),
        "n_columns": len(table.columns),
        "n_header_levels": header_levels,
        "n_group_headers": len(group_headers),
        "n_column_groups": len(arm_groups),
        "n_footnotes": len(table.footnotes),
        "n_irregular_rows": irregular,
        "n_target_columns": len(target_columns(table)),
        "n_unassigned_columns": len(unassigned),
        "has_timepoints": timepoints,
        "n_data_cells": len(table.data_cells()),
    }
    return ComplexityScore(score=score, class_label=label, features=features, drivers=dr)
