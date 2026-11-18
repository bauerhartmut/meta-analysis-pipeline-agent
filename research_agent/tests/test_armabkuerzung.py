"""Regressionstests der Armzuordnung aus gedruckten Abkuerzungen.

``PMC3278655:T2`` trennt die Arme mit den Kopfteilen ``TM`` und ``Cemented``.
``TM`` ist zwei Zeichen lang, traegt kein Token und matcht die Armbezeichnung
``The trabecular metal tibial monoblock component (TM)`` deshalb nicht - die
vier Interventions-Stichproben ``(n=30)`` bis ``(n=27)`` blieben ohne Arm.

Geprueft wird, dass die Zuordnung nur ueber die gedruckte Abkuerzung entsteht
und nur mit Feldgewinn uebernommen wird; ohne Klammerabkuerzung, ohne Gewinn
oder bei bereits gesetztem Arm bleibt alles beim Alten.
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
    reachable_cells,
)

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "public_benchmark" / "raw_data" / "yun_llm_meta_analysis" / "evaluation"
       / "data" / "no_attributes_markdown_files" / "PMC3278655.md")

TM_INTERVENTION = "The trabecular metal tibial monoblock component (TM)"
CEMENTED = "cemented component."


def _table_mit_tm_spalte(mit_groesse: bool = True) -> Table:
    table = Table(table_id="TM:T1", doc_id="TM", index=1)
    table.columns = [
        Column(col_id=0, x_start=0, x_end=9),
        Column(col_id=1, x_start=10, x_end=19),
    ]
    row = Row(row_id=0, index=0, label="Subsidence", label_path=("Subsidence",))
    row.cells = {
        0: Cell(row_id=0, col_id=0, text="Subsidence"),
        1: Cell(row_id=0, col_id=1, text="0.85", value=0.85),
    }
    table.rows = [row]
    table.header_bands = [HeaderBand(level=0, text="TM", col_start=1, col_end=1)]
    if mit_groesse:
        table.header_bands.append(
            HeaderBand(level=1, text="(n=27)", col_start=1, col_end=1)
        )
    return table


def test_printed_abbreviation_binds_the_arm():
    table = _table_mit_tm_spalte()
    enrich_table(table, {"intervention": TM_INTERVENTION, "comparator": CEMENTED})
    column = table.column(1)
    assert column.arm == "intervention"
    assert column.arm_basis == "abkuerzung"
    assert table.arm_decision == "kandidat:uebernommen:c1"
    assert [(f["text"], f["arm"], f["arm_basis"]) for f in table.header_facts] == [
        ("(n=27)", "intervention", "spalte")]


def test_abbreviation_needs_the_printed_brackets():
    table = _table_mit_tm_spalte()
    enrich_table(table, {"intervention": "trabecular metal tibial component",
                         "comparator": CEMENTED})
    assert table.column(1).arm is None
    assert table.arm_decision == "original:kein_kandidat"


def test_abbreviation_without_field_gain_is_refused():
    table = _table_mit_tm_spalte(mit_groesse=False)
    enrich_table(table, {"intervention": TM_INTERVENTION, "comparator": CEMENTED})
    assert table.column(1).arm is None
    assert table.arm_decision == "original:kein_gewinn"


def test_abbreviation_keeps_an_existing_arm():
    """Der belegte Arm der Nachbarspalte bleibt, nur die leere wird gefuellt."""
    table = _table_mit_tm_spalte()
    table.columns.append(Column(col_id=2, x_start=20, x_end=29))
    table.header_bands.append(HeaderBand(level=0, text="Cemented", col_start=2, col_end=2))
    table.header_bands.append(HeaderBand(level=1, text="(n=18)", col_start=2, col_end=2))
    table.rows[0].cells[2] = Cell(row_id=0, col_id=2, text="0.9", value=0.9)
    enrich_table(table, {"intervention": TM_INTERVENTION, "comparator": CEMENTED})
    assert (table.column(1).arm, table.column(1).arm_basis) == ("intervention", "abkuerzung")
    assert (table.column(2).arm, table.column(2).arm_basis) == ("comparator", "header_treffer")
    assert table.arm_decision == "kandidat:uebernommen:c1"


def test_tm_table_reaches_all_four_group_sizes():
    """``PMC3278655:T2``: vier ``(n=…)``-Baender bekommen ihren Arm."""
    if not DOC.exists():
        pytest.skip("PMC3278655 nicht vorhanden")
    parsed = parse_document(DOC.read_text(encoding="utf-8", errors="replace"),
                            "PMC3278655")
    table = next(t for t in parsed.tables if t.table_id == "PMC3278655:T2")
    context = {"intervention": TM_INTERVENTION, "comparator": CEMENTED,
               "outcome": "subsidence"}
    enrich_table(table, context)
    assert table.arm_decision == "kandidat:uebernommen:c1,c3,c5,c7"
    assert [(c.col_id, c.arm, c.arm_basis) for c in table.columns
            if c.arm == "intervention"] == [
        (1, "intervention", "abkuerzung"),
        (3, "intervention", "abkuerzung"),
        (5, "intervention", "abkuerzung"),
        (7, "intervention", "abkuerzung"),
    ]
    assert [(f["text"], f["arm"], f["value"]) for f in table.header_facts] == [
        ("(n=30)", "intervention", 30),
        ("(n=24)", "comparator", 24),
        ("(n=29)", "intervention", 29),
        ("(n=23)", "comparator", 23),
        ("(n=28)", "intervention", 28),
        ("(n=21)", "comparator", 21),
        ("(n=27)", "intervention", 27),
        ("(n=18)", "comparator", 18),
    ]
    cells = reachable_cells(table, context)
    assert (-1, "intervention_group_size") in cells
    assert (-1, "comparator_group_size") in cells


def test_order_based_arm_does_not_prove_a_group_size():
    """Ein Arm aus der Spaltenreihenfolge traegt keine Stichprobengroesse."""
    from research_agent.table_decomposition.semantics import reachable_cells

    table = Table(table_id="ORD:T1", doc_id="ORD", index=1)
    table.columns = [
        Column(col_id=0, x_start=0, x_end=9),
        Column(col_id=1, x_start=10, x_end=19),
        Column(col_id=2, x_start=20, x_end=29),
    ]
    row = Row(row_id=0, index=0, label="Subsidence", label_path=("Subsidence",))
    row.cells = {
        0: Cell(row_id=0, col_id=0, text="Subsidence"),
        1: Cell(row_id=0, col_id=1, text="0.4 (0.1)"),
        2: Cell(row_id=0, col_id=2, text="0.5 (0.2)"),
    }
    table.rows = [row]
    table.header_bands = [
        HeaderBand(level=0, text="Arm X", col_start=1, col_end=1),
        HeaderBand(level=0, text="Arm Y", col_start=2, col_end=2),
        HeaderBand(level=1, text="Mean (SD)", col_start=1, col_end=1),
        HeaderBand(level=1, text="Mean (SD)", col_start=2, col_end=2),
        HeaderBand(level=2, text="(n=27)", col_start=1, col_end=1),
    ]
    context = {"intervention": "Plus", "comparator": "Control"}
    enrich_table(table, context, assume_order=True)
    assert (table.column(1).arm, table.column(1).arm_basis) == ("intervention", "reihenfolge")
    assert [(f["text"], f["arm"], f["arm_basis"]) for f in table.header_facts] == [
        ("(n=27)", None, "kein_treffer")]
    assert (-1, "intervention_group_size") not in reachable_cells(table, context)


def test_mixed_arms_under_a_group_size_band_leave_the_arm_empty():
    """Zwei belegte, aber verschiedene Arme unter einem Band: kein Arm."""
    from research_agent.table_decomposition.semantics import _group_size_facts

    table = Table(table_id="MIX:T1", doc_id="MIX", index=1)
    table.columns = [
        Column(col_id=0, x_start=0, x_end=9),
        Column(col_id=1, x_start=10, x_end=19, arm="comparator",
               arm_basis="header_treffer"),
        Column(col_id=2, x_start=20, x_end=29, arm="intervention",
               arm_basis="header_treffer"),
    ]
    table.header_bands = [
        HeaderBand(level=0, text="Group A", col_start=1, col_end=1),
        HeaderBand(level=0, text="Group B", col_start=2, col_end=2),
        HeaderBand(level=1, text="(n=20)", col_start=1, col_end=2),
    ]
    facts = _group_size_facts(table, "Plus", "Control")
    assert [(f["text"], f["arm"], f["arm_basis"]) for f in facts] == [
        ("(n=20)", None, "kein_treffer")]
