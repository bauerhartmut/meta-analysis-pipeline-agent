"""Regressionstests der Kopfband-Zuordnung (Sprint 43).

Die ordinale Neuordnung der Kopfbaender aus Sprint 38 lieferte in
``PMC4319071:T2`` den exakten Wert, zerstoerte aber in fuenf Tabellen Felder
und erzeugte sieben Strukturfehler. Geprueft wird hier:

- der Gewinn bleibt (``PMC4319071:T2``: 158.67 und 167.61),
- die Regressionen treten nicht mehr auf (Ueberlappung, Feldverlust),
- die gedruckte Geometrie bleibt der Rueckfall,
- Arm-, Outcome- und Streuungszuordnung bleiben unveraendert.

Die Dokumenttests lesen die eingefrorenen Benchmark-Dokumente nur; sie
schreiben nichts. Fehlt der Datensatz, werden sie uebersprungen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_agent.table_decomposition.model import (
    Cell,
    Column,
    HeaderBand,
    Row,
    Table,
)
from research_agent.table_decomposition.parser import (
    _candidate_header_bands,
    _header_band_candidates,
    parse_document,
)
from research_agent.table_decomposition.semantics import (
    _bands_overlap,
    _timepoint_key,
    column_timepoints,
    enrich_table,
    reachable_cells,
    reachable_fields,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

REPO = Path(__file__).resolve().parents[2]
RECORDS = REPO / "public_benchmark" / "extended_benchmark" / "yun_full" / "records" / "yun699.jsonl"


def _record(record_id: str):
    if not RECORDS.exists():
        pytest.skip("Yun-699-Records nicht vorhanden")
    for line in RECORDS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["record_id"] == record_id:
            return record
    pytest.skip(f"Record {record_id} fehlt")


def _fields(table, context):
    """Felder, die die Tabelle fuer dieses Record-Outcome hergibt."""
    return {name for _row_id, name in reachable_cells(table, context)}


def _tables(record_id: str, transfer: bool = True):
    """Alle Tabellen des Dokuments, angereichert wie im Benchmark."""
    record = _record(record_id)
    context = {
        key: record["context"].get(key)
        for key in ("intervention", "comparator", "outcome", "outcome_type")
    }
    text = Path(record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
    parsed = parse_document(text, str(record["document"]["id"]))
    for table in parsed.tables:
        enrich_table(table, context)
    if transfer:
        transfer_arms_within_document(parsed.tables, context)
        transfer_arms_from_document(parsed.tables, context, text)
    return {table.table_id: table for table in parsed.tables}, context


# --- Der Gewinn aus Sprint 38 bleibt -------------------------------------


def test_ordinal_bands_are_adopted_and_keep_the_exact_values():
    """``PMC4319071:T2``: Vegetables 4 Monate, Control 158.67, Plus 167.61."""
    tables, context = _tables("yun2024:112")
    table = tables["PMC4319071:T2"]

    assert table.band_decision.startswith("kandidat:uebernommen")
    assert any(band.basis == "ordnung" for band in table.header_bands)
    assert not _bands_overlap(table.header_bands)
    assert "header_gruppe_nicht_teilbar:ebene0" not in table.irregularities

    vegetables = next(column for column in table.columns
                      if column.is_outcome and column.header_path[:1] == ("Vegetables (grams)",)
                      and column.role == "mean")
    assert vegetables.col_id == 4
    assert vegetables.header_path == ("Vegetables (grams)", "Mean (SE)")

    control = next(row for row in table.rows if row.row_id == 12)
    plus = next(row for row in table.rows if row.row_id == 16)
    assert (control.arm, plus.arm) == ("comparator", "intervention")
    assert control.cells[4].text == "158.67 (3.76)"
    assert plus.cells[4].text == "167.61 (3.92)"
    assert ("4-month follow-up" in control.label)


def test_adopted_bands_reach_both_means_in_the_record_context():
    tables, context = _tables("yun2024:112")
    table = tables["PMC4319071:T2"]
    cells = reachable_cells(table, context)
    assert (12, "comparator_mean") in cells
    assert (16, "intervention_mean") in cells
    assert {field for _row_id, field in cells} == {"comparator_mean", "intervention_mean"}


def test_standard_error_stays_standard_error_after_adoption():
    """``Mean (SE)`` und ``(95% CI)`` werden nicht zur Streuung."""
    tables, _context = _tables("yun2024:112")
    fields = reachable_fields(tables["PMC4319071:T2"])
    assert "comparator_standard_deviation" not in fields
    assert "intervention_standard_deviation" not in fields


# --- Die Regressionen aus Sprint 38 treten nicht mehr auf -----------------


def test_overlapping_candidate_is_refused_and_keeps_the_fields():
    """``PMC3877023:T3``: die Ordinalteilung ueberlappte und leerte die Felder."""
    tables, context = _tables("yun2024:421")
    table = tables["PMC3877023:T3"]

    assert table.band_decision == "original:ueberlappung"
    assert not _bands_overlap(table.header_bands)
    assert sorted(_fields(table, context)) == [
        "intervention_group_size",
        "intervention_mean",
        "intervention_standard_deviation",
    ]
    mean = next(column for column in table.columns if column.field == "intervention_mean")
    assert mean.header_path[0] == "Cervicothoracic Spine"
    assert mean.role == "mean"


def test_overlapping_candidate_is_refused_for_the_second_table():
    """``PMC3877023:T4``: derselbe Ueberlappungsfall mit Comparator-Feld."""
    tables, context = _tables("yun2024:426")
    table = tables["PMC3877023:T4"]
    assert table.band_decision == "original:ueberlappung"
    assert not _bands_overlap(table.header_bands)
    assert _fields(table, context) == {"comparator_group_size"}


def test_candidate_without_gain_keeps_the_printed_geometry():
    """``PMC4987981:T2``: Arme stehen im Kopf; kein Umbau ohne Feldgewinn."""
    tables, context = _tables("yun2024:665")
    table = tables["PMC4987981:T2"]
    assert table.band_decision == "original:kein_gewinn"
    assert sorted(_fields(table, context)) == [
        "comparator_mean",
        "comparator_standard_deviation",
        "intervention_mean",
        "intervention_standard_deviation",
    ]
    arms = {column.field: column.arm for column in table.columns if column.field}
    assert arms == {"comparator_mean": "comparator",
                   "intervention_mean": "intervention"}
    assert any(band.text.startswith("Placebo") for band in table.header_bands)


def test_group_size_table_keeps_its_print_geometry():
    """``PMC5777419:T2``: Zeitpunkte im Kopf, kein Feldgewinn durch Umbau."""
    tables, context = _tables("yun2024:678")
    table = tables["PMC5777419:T2"]
    assert table.band_decision == "original:kein_gewinn"
    assert _fields(table, context) == {"intervention_group_size"}
    assert any(band.text == "Probiotic group" for band in table.header_bands)


def test_arm_table_with_overlapping_candidate_is_refused():
    """``PMC3654355:T1``: der Umbau haette ein Feld auf drei Spalten gelegt."""
    tables, context = _tables("yun2024:275")
    table = tables["PMC3654355:T1"]
    assert table.band_decision == "original:ueberlappung"
    assert not _bands_overlap(table.header_bands)
    assert _fields(table, context) == {"intervention_group_size"}
    assert len([column for column in table.columns if column.field]) == 1


# --- Rueckfall und Randfaelle --------------------------------------------


def _simple_table() -> Table:
    table = Table(table_id="X:T1", doc_id="X", index=1)
    table.columns = [Column(col_id=index, x_start=index * 10, x_end=index * 10 + 9)
                     for index in range(4)]
    row = Row(row_id=0, index=0)
    row.cells = {
        0: Cell(row_id=0, col_id=0, text="Outcome"),
        1: Cell(row_id=0, col_id=1, text="Control Mean (SD)"),
        2: Cell(row_id=0, col_id=2, text="1.5", value=1.5),
        3: Cell(row_id=0, col_id=3, text="Plus Mean (SD)"),
    }
    row.cells[2].text = "1.5"
    table.rows = [row]
    table.header_bands = [
        HeaderBand(level=0, text="Control Mean (SD)", col_start=1, col_end=1),
        HeaderBand(level=0, text="Plus Mean (SD)", col_start=2, col_end=2),
    ]
    return table


def test_without_geometry_code_there_is_no_candidate():
    table = _simple_table()
    assert _candidate_header_bands(table) is None
    assert _header_band_candidates(table) == []
    enrich_table(table, {"intervention": "Plus", "comparator": "Control"})
    assert table.band_decision == ""
    assert [band.text for band in table.header_bands] == [
        "Control Mean (SD)", "Plus Mean (SD)"]


def test_candidate_that_breaks_the_field_assignment_is_refused():
    """Ein Kandidat, der die Baender auf die Labelspalte legt, ist unbrauchbar."""
    table = _simple_table()
    table.irregularities.append("header_gruppe_nicht_teilbar:ebene0")
    context = {"intervention": "Plus", "comparator": "Control"}
    enrich_table(table, context)
    before = sorted(reachable_fields(table))
    bands_before = [(band.level, band.text, band.col_start, band.col_end)
                    for band in table.header_bands]

    table.header_band_candidates = [(
        "test_verlust",
        [HeaderBand(level=0, text="Control Mean (SD)", col_start=0, col_end=0)],
    )]
    table.band_decision = ""
    enrich_table(table, context)
    assert table.band_decision in {"original:feldverlust", "original:mehrfachzuordnung"}
    assert sorted(reachable_fields(table)) == before
    assert [(band.level, band.text, band.col_start, band.col_end)
            for band in table.header_bands] == bands_before


def test_overlapping_candidate_is_refused_structurally():
    table = _simple_table()
    table.irregularities.append("header_gruppe_nicht_teilbar:ebene0")
    bands_before = [(band.level, band.text, band.col_start, band.col_end)
                    for band in table.header_bands]
    table.header_band_candidates = [(
        "test_ueberlappung",
        [
            HeaderBand(level=0, text="Control Mean (SD)", col_start=0, col_end=2),
            HeaderBand(level=0, text="Plus Mean (SD)", col_start=2, col_end=3),
        ],
    )]
    enrich_table(table, {"intervention": "Plus", "comparator": "Control"})
    assert table.band_decision == "original:ueberlappung"
    assert [(band.level, band.text, band.col_start, band.col_end)
            for band in table.header_bands] == bands_before


def test_first_candidate_is_applied_by_the_parser_helper():
    """Der Parser-Helfer ordnet Ebenen ordinal zu (ohne semantische Pruefung)."""
    table = Table(table_id="SHIFT:T1", doc_id="SHIFT", index=1)
    table.columns = [Column(col_id=index, x_start=index * 10, x_end=index * 10 + 9)
                     for index in range(6)]
    row = Row(row_id=0, index=0)
    row.cells = {0: Cell(row_id=0, col_id=0, text="Group"),
                 2: Cell(row_id=0, col_id=2, text="1.0", value=1.0),
                 3: Cell(row_id=0, col_id=3, text="2.0", value=2.0),
                 4: Cell(row_id=0, col_id=4, text="3.0", value=3.0),
                 5: Cell(row_id=0, col_id=5, text="4.0", value=4.0)}
    table.rows = [row]
    table.header_bands = [
        HeaderBand(level=0, text="Group", col_start=0, col_end=0),
        HeaderBand(level=0, text="Baseline", col_start=1, col_end=1),
        HeaderBand(level=0, text="Follow-up", col_start=2, col_end=2),
    ]
    table.irregularities.append("header_gruppe_nicht_teilbar:ebene0")

    candidates = _candidate_header_bands(table)
    assert candidates, "Kandidat fehlt"
    name, bands = candidates[0]
    assert name == "ordnung_mit_gedruckten_ebenen"
    assert [(band.text, band.col_start, band.col_end) for band in bands] == [
        ("Group", 0, 1), ("Baseline", 2, 3), ("Follow-up", 4, 5)]
    table.apply_header_bands(bands)
    assert "header_gruppe_nicht_teilbar:ebene0" not in table.irregularities
    assert "spalten_ordnung:kopf_nach_wertspalten" in table.irregularities


# --- Phase 5: Zeitpunkte im Spaltenkopf --------------------------------


def test_column_timepoints_read_from_the_header():
    """``PMC5777419:T2``: Baseline, 3, 6 und 9 Monate stehen im Kopf."""
    tables, _context = _tables("yun2024:678")
    assert column_timepoints(tables["PMC5777419:T2"]) == (
        "baseline", "3 months", "6 months", "9 months")


def test_column_timepoints_ignore_arm_and_role_headers():
    """Arm- und Rollenkoepfe sind keine Zeitpunkte."""
    tables, _context = _tables("yun2024:665")
    assert column_timepoints(tables["PMC4987981:T2"]) == ()


def test_column_timepoints_need_at_least_two():
    table = _simple_table()
    table.header_bands = [HeaderBand(level=0, text="Baseline", col_start=1, col_end=2)]
    enrich_table(table, {"intervention": "Plus", "comparator": "Control"})
    assert column_timepoints(table) == ()
    table.header_bands = [
        HeaderBand(level=0, text="Baseline", col_start=1, col_end=1),
        HeaderBand(level=0, text="Week 4", col_start=2, col_end=2),
    ]
    enrich_table(table, {"intervention": "Plus", "comparator": "Control"})
    assert column_timepoints(table) == ("baseline", "week 4")


def test_row_timepoints_stay_in_the_row_logic():
    """``PMC4319071:T2``: Zeitpunkte stehen in Gruppenzeilen, nicht im Kopf."""
    tables, _context = _tables("yun2024:112")
    table = tables["PMC4319071:T2"]
    assert column_timepoints(table) == ()
    assert _timepoint_key(table) == ("baseline", "1 month follow up", "4 month follow up")


def test_adoption_is_idempotent():
    """Zweimal anreichern aendert weder Baender noch Spaltenfelder."""
    tables, context = _tables("yun2024:112", transfer=False)
    table = tables["PMC4319071:T2"]
    before = reachable_fields(table)
    bands = [(band.level, band.text, band.col_start, band.col_end)
             for band in table.header_bands]
    enrich_table(table, context)
    assert reachable_fields(table) == before
    assert [(band.level, band.text, band.col_start, band.col_end)
            for band in table.header_bands] == bands
