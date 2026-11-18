"""Regressionstests der Rollenerkennung aus der Zellform.

In ``PMC3278655:T2`` nennt der Kopf keine Rolle (``TM``, ``Cemented``), die
Zellen tragen aber ``Mittel (Streuung)`` (``--0.38 (0.37)``). Die Rolle ``mean``
entsteht deshalb aus der Zellform - und nur, wenn ein Arm belegt ist (sonst
entstuende kein Feld), die Zellen mehrheitlich genau diese Form zeigen und
nichts nach Ereignis oder Prozent aussieht (``12 (34)``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_agent.table_decomposition.model import (
    Cell,
    Column,
    HeaderBand,
    Row,
    Table,
)
from research_agent.table_decomposition.parser import parse_document
from research_agent.table_decomposition.semantics import (
    enrich_table,
    reachable_fields,
)

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "public_benchmark" / "raw_data" / "yun_llm_meta_analysis" / "evaluation"
       / "data" / "no_attributes_markdown_files" / "PMC3278655.md")

TM = "The trabecular metal tibial monoblock component (TM)"
CEMENTED = "cemented component."


def _tabelle(zelltexte, label: str = "Subsidence") -> Table:
    table = Table(table_id="FORM:T1", doc_id="FORM", index=1)
    table.columns = [
        Column(col_id=0, x_start=0, x_end=9),
        Column(col_id=1, x_start=10, x_end=19),
    ]
    rows = []
    for index, text in enumerate(zelltexte):
        row = Row(row_id=index, index=index, label=label, label_path=(label,))
        row.cells = {
            0: Cell(row_id=index, col_id=0, text=label),
            1: Cell(row_id=index, col_id=1, text=text),
        }
        rows.append(row)
    table.rows = rows
    table.header_bands = [HeaderBand(level=0, text="TM", col_start=1, col_end=1)]
    return table


def test_cell_form_makes_mean_and_sd():
    """``PMC3278655:T2``: ``--0.38 (0.37)`` wird zu Mittel plus Streuung."""
    if not DOC.exists():
        pytest.skip("PMC3278655 nicht vorhanden")
    parsed = parse_document(DOC.read_text(encoding="utf-8", errors="replace"),
                            "PMC3278655")
    table = next(t for t in parsed.tables if t.table_id == "PMC3278655:T2")
    enrich_table(table, {"intervention": TM, "comparator": CEMENTED,
                         "outcome": "subsidence"})
    assert table.role_decision == "kandidat:uebernommen:c1,c2,c3,c4,c6,c7,c8"
    assert [(c.col_id, c.role, c.secondary_role) for c in table.columns
            if c.role == "mean"] == [
        (1, "mean", "sd"), (2, "mean", "sd"), (3, "mean", "sd"),
        (4, "mean", "sd"), (6, "mean", "sd"), (7, "mean", "sd"),
        (8, "mean", "sd"),
    ]
    assert sorted(reachable_fields(table)) == [
        "comparator_mean", "comparator_standard_deviation",
        "intervention_mean", "intervention_standard_deviation",
    ]


def test_cell_form_without_arm_stays_unknown():
    table = _tabelle(["--0.38 (0.37)", "--0.04 (0.11)"])
    enrich_table(table, {"intervention": "trabecular metal",
                         "comparator": "cemented component."})
    assert table.column(1).arm is None
    assert table.column(1).role == "unknown"
    assert table.role_decision == "original:kein_kandidat"


def test_event_cells_are_not_read_as_mean():
    """``12 (34)`` sieht wie Mittel (Streuung) aus, ist aber ``n (%)``."""
    table = _tabelle(["12 (34)", "9 (27)"], label="Not complying, n (%)")
    enrich_table(table, {"intervention": TM, "comparator": CEMENTED})
    assert table.column(1).role == "unknown"
    assert table.role_decision == "original:kein_kandidat"


def test_plain_values_are_not_read_as_mean():
    table = _tabelle(["0.85", "0.92"])
    enrich_table(table, {"intervention": TM, "comparator": CEMENTED})
    assert table.column(1).role == "unknown"
    assert table.role_decision == "original:kein_kandidat"
