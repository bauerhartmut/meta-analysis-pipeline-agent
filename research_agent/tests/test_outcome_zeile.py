"""Tests der Outcome-Zeilen-Erkennung aus der Zellform.

Der Name entscheidet, wenn er trifft. Trifft er nicht, haelt
``consider_outcome_row_candidate`` nur fest, was die Zellform hergibt: eine
einzige vollstaendige Datenzeile ist ein Vorschlag, mehrere sind mehrdeutig.
Gesetzt wird nichts - ein Feld entsteht durch die Zeilenwahl nicht, also waere
ein "Gewinn" an erwartbaren Zellen eine selbstbestaetigende Pruefung.

Belegt am echten Dokument: in ``PMC3278655:T2`` sind acht Zeilen vollstaendig,
und die Goldwerte ``-0.38 (0.37)`` stehen in ``Superior/inferior translation``,
nicht in ``Mean maximum total point motion``.
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
    consider_outcome_row_candidate,
    enrich_table,
    reachable_cells,
)

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "public_benchmark" / "raw_data" / "yun_llm_meta_analysis" / "evaluation"
       / "data" / "no_attributes_markdown_files" / "PMC3278655.md")

TM = "The trabecular metal tibial monoblock component (TM)"
CEMENTED = "cemented component."


def _tabelle(zeilen, label="Mean maximum total point motion"):
    """Zwei Messspalten (Mittel, Streuung) mit je einem Arm."""
    table = Table(table_id="ZEILE:T1", doc_id="ZEILE", index=1)
    table.columns = [
        Column(col_id=0, x_start=0, x_end=9),
        Column(col_id=1, x_start=10, x_end=19, role="mean",
               arm="intervention", arm_basis="header_treffer",
               field="intervention_mean"),
        Column(col_id=2, x_start=20, x_end=29, role="sd",
               arm="intervention", arm_basis="header_treffer",
               field="intervention_standard_deviation"),
    ]
    table.header_bands = [
        HeaderBand(level=0, text="TM", col_start=1, col_end=2),
        HeaderBand(level=1, text="Mean", col_start=1, col_end=1),
        HeaderBand(level=1, text="SD", col_start=2, col_end=2),
    ]
    rows = []
    for index, (text, zellen) in enumerate(zeilen):
        row = Row(row_id=index, index=index, label=text, label_path=(label, text))
        row.cells = {0: Cell(row_id=index, col_id=0, text=text)}
        for col_id, wert in zellen.items():
            row.cells[col_id] = Cell(row_id=index, col_id=col_id, text=wert)
        rows.append(row)
    table.rows = rows
    return table


def test_unique_complete_row_is_a_proposal_without_adoption():
    table = _tabelle([("Superior/inferior translation", {1: "-0.38", 2: "0.37"}),
                      ("Kommentar", {})])
    assert consider_outcome_row_candidate(
        table, {"outcome": "subsidence"}) == "vorschlag:r0"
    # Ohne gedruckten Beleg bleibt die erwartbare Menge beim Namen - leer.
    assert table.focus_rows == []


def test_two_complete_rows_are_ambiguous():
    table = _tabelle([("A", {1: "-0.38", 2: "0.37"}),
                      ("B", {1: "0.98", 2: "0.79"})])
    assert consider_outcome_row_candidate(
        table, {"outcome": "subsidence"}) == "original:mehrdeutig"
    assert table.focus_rows == []
    assert any(code.startswith("outcome_zeile_mehrdeutig:0|1")
               for code in table.irregularities)


def test_row_with_a_gap_is_no_candidate():
    table = _tabelle([("A", {1: "-0.38"}), ("B", {1: "0.98", 2: "0.79"})])
    assert consider_outcome_row_candidate(
        table, {"outcome": "subsidence"}) == "vorschlag:r1"


def test_name_match_keeps_priority():
    table = _tabelle([("Subsidence", {1: "-0.38", 2: "0.37"})])
    assert consider_outcome_row_candidate(
        table, {"outcome": "subsidence"}) == "original:treffer"


@pytest.mark.skipif(not DOC.exists(), reason="PMC3278655 nicht vorhanden")
def test_pmc3278655_the_gold_row_is_not_the_mtpm_row():
    parsed = parse_document(DOC.read_text(encoding="utf-8", errors="replace"),
                            "PMC3278655")
    table = next(t for t in parsed.tables if t.table_id == "PMC3278655:T2")
    context = {"intervention": TM, "comparator": CEMENTED,
               "outcome": "subsidence"}
    enrich_table(table, context)
    assert table.outcome_row_decision == "original:mehrdeutig"
    assert table.focus_rows == []
    assert len(reachable_cells(table, context)) == 2
    mtpm = table.row(0)
    subsidence = next(row for row in table.rows
                      if "Superior/inferior" in row.label)
    # 60 Monate: TM = c7, Cemented = c8.
    assert mtpm.cells[7].text.strip() == "0.79"
    assert mtpm.cells[8].text.strip() == "0.9"
    assert subsidence.cells[7].text.strip() == "--0.38 (0.37)"
    assert subsidence.cells[8].text.strip() == "--0.04 (0.11)"
