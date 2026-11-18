"""Tests der Outcome-Zeilen-Korroboration ueber den gedruckten p-Wert.

Der Record-Text nennt einen p-Wert im Satz zum Outcome, die Tabelle druckt
denselben p-Wert in einer Zeile. Uebernommen wird nur, wenn genau **eine**
Zeile passt und der Wertabgleich besteht (jede Messspalte traegt einen
gedruckten Zahlenwert). Mehrere Treffer, kein Satz zum Outcome oder eine
Spanne statt eines Werts verhindern die Uebernahme.
"""

from __future__ import annotations

import re
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
    corroborate_outcome_row_from_document,
    enrich_table,
    p_werte_zum_outcome,
    reachable_cells,
)

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "public_benchmark" / "raw_data" / "yun_llm_meta_analysis" / "evaluation"
       / "data" / "no_attributes_markdown_files" / "PMC3278655.md")

TM = "The trabecular metal tibial monoblock component (TM)"
CEMENTED = "cemented component."


def _zelle(row_id: int, col_id: int, text: str) -> Cell:
    """Zelle wie im Parser: ``text`` verbatim, ``value`` die erste Zahl."""
    zelle = Cell(row_id=row_id, col_id=col_id, text=text)
    treffer = re.search(r"[-+]?\d+(?:[.,]\d+)?", text.translate(
        {"\u2212": "-", "\u2013": "-", "\u2014": "-"}), )
    if treffer:
        zelle.value = float(treffer.group(0).replace(",", "."))
    return zelle


def _tabelle(zeilen) -> Table:
    """Zwei Messspalten (Mittel, Streuung) je Interventionsarm plus p-Wert."""
    table = Table(table_id="PW:T1", doc_id="PW", index=1)
    table.columns = [
        Column(col_id=0, x_start=0, x_end=9, role="label"),
        Column(col_id=1, x_start=10, x_end=19, role="mean",
               arm="intervention", arm_basis="header_treffer",
               field="intervention_mean"),
        Column(col_id=2, x_start=20, x_end=29, role="sd",
               arm="intervention", arm_basis="header_treffer",
               field="intervention_standard_deviation"),
        Column(col_id=3, x_start=30, x_end=39, role="p_value"),
    ]
    table.header_bands = [
        HeaderBand(level=0, text="TM", col_start=1, col_end=2),
        HeaderBand(level=0, text="p-value", col_start=3, col_end=3),
        HeaderBand(level=1, text="Mean", col_start=1, col_end=1),
        HeaderBand(level=1, text="SD", col_start=2, col_end=2),
    ]
    rows = []
    for index, (text, mittel, streuung, p_wert) in enumerate(zeilen):
        row = Row(row_id=index, index=index, label=text, label_path=(text,))
        row.cells = {0: _zelle(index, 0, text)}
        for col_id, wert in ((1, mittel), (2, streuung), (3, p_wert)):
            if wert is None:
                continue
            row.cells[col_id] = _zelle(index, col_id, wert)
        rows.append(row)
    table.rows = rows
    return table


TEXT = ("The implants had significantly greater subsidence than the cemented "
        "components (p = 0.001). The other measures did not differ (p = 0.9).")


def test_p_wert_selects_the_row_and_sets_it():
    table = _tabelle([("Other measure", "0.02", "0.12", "0.9"),
                      ("Superior/inferior translation", "-0.38", "0.37", "0.001")])
    gesetzt = corroborate_outcome_row_from_document(
        [table], {"outcome": "subsidence"}, TEXT)
    assert gesetzt == 1
    assert table.outcome_row_decision == "p_wert:uebernommen:r1"
    assert table.focus_rows == [1]
    felder = {name for _row_id, name in reachable_cells(table, {"outcome": "subsidence"})}
    assert felder == {"intervention_mean", "intervention_standard_deviation"}


def test_two_rows_with_the_same_p_value_are_refused():
    table = _tabelle([("A", "-0.38", "0.37", "0.001"),
                      ("B", "0.02", "0.12", "0.001")])
    gesetzt = corroborate_outcome_row_from_document(
        [table], {"outcome": "subsidence"}, TEXT)
    assert gesetzt == 0
    assert table.outcome_row_decision == "p_wert:mehrdeutig"
    assert table.focus_rows == []
    assert any(code.startswith("outcome_zeile_mehrdeutig:0|1")
               for code in table.irregularities)


def test_sentence_without_the_outcome_is_no_beleg():
    table = _tabelle([("Superior/inferior translation", "-0.38", "0.37", "0.001")])
    gesetzt = corroborate_outcome_row_from_document(
        [table], {"outcome": "subsidence"},
        "The other measures did not differ (p = 0.001).")
    assert gesetzt == 0
    assert table.focus_rows == []
    assert p_werte_zum_outcome(
        "The other measures did not differ (p = 0.001).", "subsidence") == set()


def test_a_sentence_ending_with_a_bracket_does_not_leak_a_p_value():
    """``MTPM ... (p = 0.9) ([Table 2](#)).`` endet - der naechste Satz zaehlt nicht."""
    text = ('There was no difference in maximum total point motion (p = 0.9) '
            '([Table 2](#)). The proportion of "at risk" components was 2 of '
            '18 and 0 of 27 (p = 0.2).')
    outcome = 'The proportion of "at risk" components at 5 years'
    assert p_werte_zum_outcome(text, outcome) == {0.2}


def test_a_shared_years_token_does_not_bind_the_sentence():
    """``At the 5-year follow-up ... (p = 0.9)`` nennt das Outcome nicht."""
    text = ('At the 5-year follow-up, there was no difference in maximum total '
            'point motion (p = 0.9). The proportion of "at risk" components was '
            '2 of 18 and 0 of 27 (p = 0.2).')
    outcome = 'The proportion of "at risk" components at 5 years'
    assert p_werte_zum_outcome(text, outcome) == {0.2}


def test_range_cell_fails_the_value_check():
    """Eine Spanne ist kein Wert - das Feld darf nicht ohne Wert entstehen."""
    table = _tabelle([("Superior/inferior translation", "(0.07--3.11)", "0.37", "0.001")])
    gesetzt = corroborate_outcome_row_from_document(
        [table], {"outcome": "subsidence"}, TEXT)
    assert gesetzt == 0
    assert table.outcome_row_decision == "p_wert:kein_wert:r0"
    assert table.focus_rows == []


@pytest.mark.skipif(not DOC.exists(), reason="PMC3278655 nicht vorhanden")
def test_pmc3278655_row_is_confirmed_by_the_printed_p_value():
    parsed = parse_document(DOC.read_text(encoding="utf-8", errors="replace"),
                            "PMC3278655")
    table = next(t for t in parsed.tables if t.table_id == "PMC3278655:T2")
    context = {"intervention": TM, "comparator": CEMENTED,
               "outcome": "subsidence"}
    enrich_table(table, context)
    assert table.outcome_row_decision == "original:mehrdeutig"
    gesetzt = corroborate_outcome_row_from_document(
        parsed.tables, context,
        DOC.read_text(encoding="utf-8", errors="replace"))
    assert gesetzt == 1
    assert table.outcome_row_decision == "p_wert:uebernommen:r3"
    assert table.focus_rows == [3]
    felder = {name for _row_id, name in reachable_cells(table, context)}
    assert felder == {
        "intervention_group_size", "comparator_group_size",
        "intervention_mean", "intervention_standard_deviation",
        "comparator_mean", "comparator_standard_deviation",
    }
