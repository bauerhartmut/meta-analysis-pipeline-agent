"""Tests der Table-Decomposition-Engine (alle fuenf Verfahren).

Die Fixtures sind synthetische Dokumente im Format der Yun-Markdown-Quellen
(Pandoc-Table-Wrap, Strichregel, mehrstufiger Kopf, Fussnoten). Keine echten
Studienwerte, keine Abhaengigkeit von Rohdaten im Repo.
"""

from __future__ import annotations

import json

import pytest

from research_agent.table_decomposition.backend import (
    PredictedCell,
    ScriptedBackend,
    UnitResult,
    parse_cells,
)
from research_agent.table_decomposition.complexity import (
    COMPLEX,
    SIMPLE,
    assess,
)
from research_agent.table_decomposition.crops import make_crop
from research_agent.table_decomposition.engine import (
    TableDecompositionConfig,
    TableDecompositionEngine,
    augment_prompt_text,
    table_decomposition_enabled,
)
from research_agent.table_decomposition.model import (
    ARM_COMPARATOR,
    ARM_INTERVENTION,
    ROLE_LABEL,
    ROLE_MEAN,
    ROLE_PVALUE,
    ROLE_SD,
    field_for,
)
from research_agent.table_decomposition.parser import (
    normalise_number_text,
    parse_document,
    parse_value,
)
from research_agent.table_decomposition.reconstruct import (
    STATUS_AGREED,
    STATUS_CONFLICT,
)
from research_agent.table_decomposition.semantics import (
    bind_arm,
    enrich_table,
    group_size_declaration,
    outcome_rows,
    reachable_cells,
    reachable_fields,
    role_for_header,
    target_columns,
    transfer_arms_within_document,
)
from research_agent.table_decomposition.strategies import (
    DIRECTION_CELL,
    DIRECTION_COLUMN,
    DIRECTION_FULL,
    DIRECTION_ROW,
    STRATEGY_ADAPTIVE,
    STRATEGY_BIDIRECTIONAL,
    STRATEGY_FULL,
    STRATEGY_HORIZONTAL,
    STRATEGY_VERTICAL,
    PlanOptions,
    plan,
    refinement_units,
)
from research_agent.table_decomposition.validation import STATUS_COMPLETE, validate

CONTEXT = {
    "intervention": "Arm B (AB)",
    "comparator": "Arm C (AC)",
    "outcome": "Body weight",
    "outcome_type": "continuous",
}


def render_dash_table(groups, subheaders, rows, widths, caption, footnotes=()):
    """Synthetische Pandoc-Tabelle im Stil der Yun-Markdownquellen."""
    starts = []
    position = 0
    for width in widths:
        starts.append(position)
        position += width + 2

    def place(cells):
        line = ""
        for index, text in cells:
            target = starts[index]
            if len(line) < target:
                line += " " * (target - len(line))
            line += text
        return line

    def data_line(label, values):
        line = label
        for index, value in values:
            target = starts[index] + widths[index] - len(value)
            if len(line) < target:
                line += " " * (target - len(line))
            line += value
        return line

    lines = ["::::table-wrap", "::: caption", caption, ":::", ""]
    lines.append(place([(start, text) for start, text in zip(groups[0], groups[1])]))
    lines.append((" " * 2).join("-" * width for width in widths))
    lines.append("")
    lines.append(place([(start, text) for start, text in zip(subheaders[0], subheaders[1])]))
    for label, values in rows:
        lines.append(data_line(label, values))
    if footnotes:
        lines.append("")
        lines.extend(footnotes)
    return "\n".join(lines)


WIDTHS = [24, 9, 9, 9, 9, 9, 9]

DOCUMENT = "\n\n".join(
    [
        "# Results",
        "The patients were similar between groups (Table 1).",
        render_dash_table(
            groups=(
                (1, 3, 5),
                ("Arm A (n = 10)", "Arm B (n = 12)", "Arm C (n = 9)"),
            ),
            subheaders=((1, 2, 3, 4, 5, 6), ("Mean", "SD", "Mean", "SD", "Mean", "SD")),
            rows=[
                ("Weight (kg)", [(1, "70.10"), (2, "8.40"), (3, "72.30"), (4, "7.90"), (5, "69.80"), (6, "9.10")]),
                ("Height (cm)", [(1, "171.20"), (2, "6.10"), (3, "170.40"), (4, "6.30"), (5, "169.90"), (6, "7.20")]),
                ("Events (n)", [(1, "4"), (2, "2.10"), (3, "3"), (4, "1.90"), (5, "5"), (6, "2.30")]),
            ],
            widths=WIDTHS,
            caption="Clinical characteristics at baseline",
            footnotes=[
                "* Values are printed as mean and standard deviation.",
                "n = number of patients per arm.",
            ],
        ),
        "Body weight was higher in Arm B.",
    ]
)

PIPE_DOCUMENT = """# Results

| Outcome | Arm B mean | Arm B SD | Arm C mean | Arm C SD |
|---|---|---|---|---|
| Weight (kg) | 72.30 | 7.90 | 69.80 | 9.10 |
| Height (cm) | 170.40 | 6.30 | 169.90 | 7.20 |
"""

WHITESPACE_DOCUMENT = """# Results

Table 3. Follow-up measurements

Outcome            Arm B mean   Arm B SD   Arm C mean   Arm C SD
Weight (kg)        72.30        7.90       69.80        9.10
Height (cm)        170.40       6.30       169.90       7.20
"""


def _table(document=DOCUMENT, context=CONTEXT):
    parsed = parse_document(document, "TESTDOC")
    assert parsed.tables, "Fixture wurde nicht als Tabelle erkannt"
    table = parsed.tables[0]
    enrich_table(table, context)
    return table


def perfect_backend(table):
    """Backend, das die gedruckten Zellwerte verbatim zurueckgibt."""
    def fn(unit):
        cells = []
        for row_id, col_id in unit.expected_cells:
            cell = table.cell(row_id, col_id)
            if cell is not None and cell.value is not None:
                cells.append(
                    {"row": row_id, "column": col_id, "value": cell.value, "raw": cell.text}
                )
        return cells
    return ScriptedBackend(fn=fn, name="perfect")


def test_label_column_with_digits_is_still_a_label():
    """Zeitpunkt-Labels enthalten Ziffern und duerfen keine Datenspalte werden."""
    document = """Table 2. Plasma values by visit

Visit        Placebo mean   Placebo SD   Verum mean   Verum SD
5 min        1.9            0.4          1.5          0.3
7 min        1.9            0.5          1.4          0.3
Visit 4:
3 min        2.1            0.8          1.4          0.4
"""
    parsed = parse_document(document, "VISITS")
    assert parsed.tables
    table = parsed.tables[0]
    assert table.columns[0].role == ROLE_LABEL
    assert table.rows[0].label == "5 min"
    assert table.rows[1].label == "7 min"
    assert 0 not in table.data_columns


# --- Erwartete Zellen: Kopf, Gruppengroesse, Outcome-Zeile ----------------

GROUPED_WIDTHS = [26, 16, 16, 16, 16, 16, 16]
GROUPED_STARTS = [0, 28, 46, 64, 82, 100, 118]


def _grouped_line(cells):
    """Zellen an feste Spaltenpositionen setzen (PDF-Abzug als Fixture)."""
    line = ""
    for index, text in cells:
        if len(line) < GROUPED_STARTS[index]:
            line += " " * (GROUPED_STARTS[index] - len(line))
        else:
            line += "  "
        line += text
    return line


GROUPED_DOCUMENT = "\n".join([
    "Table 1. Participant characteristics at baseline.",
    "",
    _grouped_line([(0, "Characteristic"), (1, "Total"), (2, "Control"),
                   (3, "Basic"), (4, "Plus"),
                   (5, "Group comparison, OR (95% CI)")]),
    _grouped_line([(1, "n=1349"), (2, "n=434"), (3, "n=459"), (4, "n=456")]),
    "  ".join("-" * width for width in GROUPED_WIDTHS),
    "",
    _grouped_line([(0, "Basic vs control"), (1, "Plus vs control"), (2, "Plus vs basic")]),
    "",
    "**Background characteristics**",
    "",
    _grouped_line([(0, "Age (years), mean (SD)"), (1, "49.05 (10.62)"),
                   (2, "50.01 (10.40)"), (3, "48.63 (11.10)"), (4, "48.54 (10.30)")]),
    "",
    "**Dietary intake**",
    "",
    _grouped_line([(1, "**Vegetable intake (grams)**")]),
    "",
    _grouped_line([(0, "Mean (SD)"), (1, "159.12 (69.24)"), (2, "157.73 (64.54)"),
                   (3, "162.68 (72.76)"), (4, "156.91 (69.94)")]),
])

GROUPED_CONTEXT = {"intervention": "Plus", "comparator": "Control",
                   "outcome": "Vegetable intake", "outcome_type": "continuous"}


def _grouped_table(context=GROUPED_CONTEXT):
    parsed = parse_document(GROUPED_DOCUMENT, "GROUPED")
    assert parsed.tables, "Fixture wurde nicht als Tabelle erkannt"
    table = parsed.tables[0]
    enrich_table(table, context)
    return table


def test_comparison_line_is_not_a_column_header():
    """``Basic vs control`` ist eine Auswertung, kein Spaltenkopf."""
    table = _grouped_table()
    assert not any("vs" in band.text for band in table.header_bands)
    assert all("vs" not in " ".join(column.header_path) for column in table.columns)
    assert table.columns[2].header_path == ("Control",)
    assert any(item.startswith("kopfzeile_ist_zeilenlabel")
               for item in table.irregularities)


def test_header_group_size_is_a_fact_not_a_column_role():
    """``n = 456`` ist eine Kopfangabe, keine Spalte mit Zeilenwerten."""
    table = _grouped_table()
    assert group_size_declaration("n=434") == 434
    assert group_size_declaration("n = 12") == 12
    assert group_size_declaration("Arm B (n = 12)") is None

    sizes = {(fact["arm"], fact["value"]) for fact in table.header_facts}
    assert ("comparator", 434) in sizes
    assert ("intervention", 456) in sizes
    assert ("intervention", 459) not in sizes      # Basic ist nicht der Arm
    assert all(column.role != "n" for column in table.columns)
    assert all(column.field is None for column in table.columns[:5])
    # Kopfangaben sind kein gelesener Zellwert und zaehlen nicht als erwartbar.
    fields = {name for _row_id, name in reachable_cells(table, GROUPED_CONTEXT)}
    assert "comparator_group_size" not in fields


def test_group_labels_extend_the_table_and_carry_a_label_path():
    """Fette Zeilengruppen beenden die Tabelle nicht und bilden den Pfad."""
    table = _grouped_table()
    labels = [row.group_label for row in table.rows if row.group_label]
    assert labels == ["Background characteristics", "Dietary intake",
                      "Vegetable intake (grams)"]
    vegetable = next(row for row in table.rows if "Vegetable" in row.group_label)
    below = table.rows[table.rows.index(vegetable) + 1]
    assert below.label_path == ("Dietary intake", "Vegetable intake (grams)",
                                "Mean (SD)")
    assert outcome_rows(table, "Vegetable intake") == [below.row_id]
    assert outcome_rows(table, "Age") == [1]
    assert outcome_rows(table, "Quality of life") == []


def test_reachable_cells_are_limited_to_the_outcome_row():
    table = _table()
    cells = reachable_cells(table, CONTEXT)
    assert {row_id for row_id, _field in cells} == {0}
    assert "intervention_mean" in {name for _row_id, name in cells}
    assert reachable_cells(table, {"outcome": "Quality of life"}) == set()


def test_focused_plan_reads_only_the_outcome_row():
    table = _table()
    focused = plan(table, STRATEGY_FULL, PlanOptions(focus_outcome=True), DOCUMENT)
    unit = focused.units[0]
    assert {row_id for row_id, _col_id in unit.expected_cells} == {0}
    assert 1 in unit.context_row_ids
    assert "Outcome-Zeile" in " ".join(unit.notes)
    report = validate(table, focused.units, None)
    assert report.structural["cells_outside_rows"] > 0
    assert report.status == STATUS_COMPLETE

    unfocused = plan(table, STRATEGY_FULL, PlanOptions(), DOCUMENT)
    assert len(unfocused.units[0].expected_cells) > len(unit.expected_cells)


# --- Parser ---------------------------------------------------------------

def test_parser_builds_multilevel_header_with_spans():
    table = _table()
    assert len(table.columns) == 7
    assert len({band.level for band in table.header_bands}) == 2
    groups = [b for b in table.header_bands if b.level == 0]
    assert [(b.text, b.col_start, b.col_end) for b in groups] == [
        ("Arm A (n = 10)", 1, 2),
        ("Arm B (n = 12)", 3, 4),
        ("Arm C (n = 9)", 5, 6),
    ]
    assert table.columns[3].header_path == ("Arm B (n = 12)", "Mean")
    assert table.columns[0].role == ROLE_LABEL
    assert table.caption == "Clinical characteristics at baseline"


def test_parser_keeps_footnotes_and_positions():
    text = DOCUMENT
    table = _table()
    assert table.footnote_block.startswith("* Values are printed")
    assert len(table.footnotes) >= 2
    cell = table.cell(0, 3)
    assert cell.text == "72.30"
    assert text[cell.start_char:cell.end_char] == "72.30"
    assert text[table.char_start:table.char_end].strip().startswith("::::table-wrap")


def test_parser_handles_pipe_and_whitespace_tables():
    pipe = parse_document(PIPE_DOCUMENT, "PIPE").tables
    assert len(pipe) == 1
    assert len(pipe[0].columns) == 5
    assert pipe[0].cell(0, 1).text == "72.30"

    whitespace = parse_document(WHITESPACE_DOCUMENT, "WS").tables
    assert len(whitespace) == 1
    assert whitespace[0].caption.startswith("Table 3.")
    assert whitespace[0].cell(0, 1).text == "72.30"


def test_parse_value_rules():
    assert parse_value("10.27") == pytest.approx(10.27)
    assert parse_value("10,27") == pytest.approx(10.27)
    assert parse_value("0.02*") == pytest.approx(0.02)
    assert parse_value("13 (n)") == pytest.approx(13.0)
    assert parse_value("43.3%") is None
    assert parse_value("10.2 \u00b1 3.1") is None
    assert parse_value("n/a") is None
    assert normalise_number_text("\u22120,53") == "-0.53"


def test_cell_mapping_marks_no_drift():
    table = _table()
    # Jede Datenzelle muss in ihrer Spalte liegen, nicht in der Nachbarspalte.
    assert table.cell(0, 1).text == "70.10"
    assert table.cell(0, 2).text == "8.40"
    assert table.cell(0, 6).text == "9.10"
    assert all(not row.irregular for row in table.rows)


# --- Semantik -------------------------------------------------------------

def test_roles_and_arm_binding():
    assert role_for_header(("Arm B (n = 12)", "Mean")) == ROLE_MEAN
    assert role_for_header(("Arm B (n = 12)", "SD")) == ROLE_SD
    assert role_for_header(("P value",)) == ROLE_PVALUE
    assert field_for(ROLE_MEAN, ARM_INTERVENTION) == "intervention_mean"
    assert field_for(ROLE_MEAN, None) is None

    bound = bind_arm(("Arm B (n = 12)", "Mean"), CONTEXT["intervention"], CONTEXT["comparator"])
    assert bound.arm == ARM_INTERVENTION
    ambiguous = bind_arm(("Arm A (n = 10)", "Mean"), CONTEXT["intervention"], CONTEXT["comparator"])
    assert ambiguous.arm is None
    assert ambiguous.basis == "kein_treffer"


def test_enrich_table_binds_only_named_arms():
    table = _table()
    fields = {c.col_id: c.field for c in table.columns}
    assert fields[1] is None          # Arm A steht nicht im Kontext
    assert fields[3] == "intervention_mean"
    assert fields[4] == "intervention_standard_deviation"
    assert fields[5] == "comparator_mean"
    assert fields[6] == "comparator_standard_deviation"
    assert [c.col_id for c in target_columns(table)] == [3, 4, 5, 6]


# --- Verfahren A-E --------------------------------------------------------

def test_strategy_a_full_table_is_single_unit():
    table = _table()
    decomposition = plan(table, STRATEGY_FULL, PlanOptions(), DOCUMENT)
    assert len(decomposition.units) == 1
    unit = decomposition.units[0]
    assert unit.direction == DIRECTION_FULL
    assert unit.col_ids == table.data_columns
    assert len(unit.expected_cells) == len(table.data_cells())
    for marker in (table.caption, table.footnote_block.strip(), "Arm B (n = 12)", "VERBATIM TABLE"):
        assert marker in unit.prompt
    assert unit.crop is not None and unit.crop.includes_caption


def test_strategy_b_vertical_units_carry_their_header_path():
    table = _table()
    decomposition = plan(table, STRATEGY_VERTICAL, PlanOptions(), DOCUMENT)
    assert len(decomposition.units) == 4
    assert {u.direction for u in decomposition.units} == {DIRECTION_COLUMN}
    for unit in decomposition.units:
        assert len(unit.col_ids) == 1
        column = table.column(unit.col_ids[0])
        for band in column.header_path:
            assert band in unit.prompt
        for row_id, col_id in unit.expected_cells:
            assert col_id == unit.col_ids[0]
            assert table.row(row_id).label in unit.prompt
        assert table.footnote_block.strip() in unit.prompt


def test_strategy_c_horizontal_units_carry_all_headers():
    table = _table()
    decomposition = plan(table, STRATEGY_HORIZONTAL, PlanOptions(), DOCUMENT)
    assert len(decomposition.units) == len(table.rows)
    for unit in decomposition.units:
        assert len(unit.row_ids) == 1
        row = table.row(unit.row_ids[0])
        assert row.label in unit.prompt
        for col_id in table.data_columns:
            assert table.column(col_id).header_path[-1] in unit.prompt
        assert all(rid == row.row_id for rid, _cid in unit.expected_cells)


def test_strategy_d_bidirectional_marks_overlapping_crops():
    table = _table()
    decomposition = plan(table, STRATEGY_BIDIRECTIONAL, PlanOptions(), DOCUMENT)
    directions = {u.direction for u in decomposition.units}
    assert directions == {DIRECTION_ROW, DIRECTION_COLUMN}
    assert len({u.unit_id for u in decomposition.units}) == len(decomposition.units)
    row_unit = next(u for u in decomposition.units if u.direction == DIRECTION_ROW)
    column_unit = next(u for u in decomposition.units if u.direction == DIRECTION_COLUMN)
    shared = set(row_unit.expected_cells) & set(column_unit.expected_cells)
    assert shared, "Zeilen- und Spalteneinheit muessen dieselben Zellen lesen"
    assert row_unit.crop.overlaps and column_unit.crop.overlaps


def test_strategy_e_scales_with_complexity():
    simple_table = _table(WHITESPACE_DOCUMENT)
    simple_decomposition = plan(simple_table, STRATEGY_ADAPTIVE, PlanOptions(), WHITESPACE_DOCUMENT)
    assert assess(simple_table).class_label == SIMPLE
    assert len(simple_decomposition.units) == 1
    assert simple_decomposition.units[0].direction == DIRECTION_FULL

    complex_table = _table()
    complex_decomposition = plan(complex_table, STRATEGY_ADAPTIVE, PlanOptions(), DOCUMENT)
    assert assess(complex_table).class_label in {COMPLEX, "sehr_komplex"}
    assert len(complex_decomposition.units) > 1
    assert {u.direction for u in complex_decomposition.units} == {DIRECTION_ROW, DIRECTION_COLUMN}


def test_unit_budget_is_respected_by_chunking():
    table = _table()
    for strategy in (STRATEGY_VERTICAL, STRATEGY_HORIZONTAL, STRATEGY_BIDIRECTIONAL):
        for limit in (1, 2, 3):
            decomposition = plan(table, strategy, PlanOptions(max_units_per_table=limit), DOCUMENT)
            assert len(decomposition.units) <= limit, (strategy, limit)
            covered = {cell for unit in decomposition.units for cell in unit.expected_cells}
            scope_cols = {col for unit in decomposition.units for col in unit.col_ids}
            in_scope = {c.address for c in table.data_cells() if c.col_id in scope_cols}
            assert covered == in_scope, (strategy, limit)
            if strategy in (STRATEGY_HORIZONTAL, STRATEGY_BIDIRECTIONAL):
                assert len(covered) == len({c.address for c in table.data_cells()})


def test_vertical_falls_back_without_bound_arms():
    table = _table(context={"intervention": "unknown drug", "comparator": "placebo"})
    decomposition = plan(table, STRATEGY_VERTICAL, PlanOptions(), DOCUMENT)
    assert len(decomposition.units) == 1
    assert decomposition.units[0].direction == DIRECTION_FULL
    assert any("vertikale" in note for note in decomposition.notes)


# --- Crops ----------------------------------------------------------------

def test_crop_documents_coordinates_without_inventing_pages():
    table = _table()
    crop = make_crop(table, [0], [3], "crop-1")
    assert crop.crop_id == "crop-1"
    assert crop.char_start >= 0 and crop.char_end > crop.char_start
    assert crop.bbox_norm is not None
    assert all(0 <= value <= 1000 for value in crop.bbox_norm)
    assert crop.coordinate_system == "text-layout/1000"
    assert crop.image["available"] is False
    assert "keine Seitenangabe" in crop.image["note"]


# --- Backend --------------------------------------------------------------

def test_parse_cells_tolerates_fences_and_commas():
    cells, error = parse_cells('```json\n{"cells": [{"row": 0, "column": 3, "value": "72,3", "raw": "72.30"}]}\n```')
    assert error == ""
    assert cells[0].row_id == 0 and cells[0].col_id == 3
    assert cells[0].value == pytest.approx(72.3)
    assert parse_cells("kein json")[1] == "kein_json"
    assert parse_cells("")[1] == "leere_antwort"


# --- Rekonstruktion -------------------------------------------------------

def test_reconstruction_agrees_and_keeps_provenance():
    table = _table()
    engine = TableDecompositionEngine(
        backend=perfect_backend(table),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_BIDIRECTIONAL),
    )
    run = engine.run_table(table, DOCUMENT)
    reconstruction = run.reconstruction
    assert reconstruction.stats["n_conflict"] == 0
    cell = reconstruction.by_address()[(0, 3)]
    assert cell.status == STATUS_AGREED
    assert cell.value == pytest.approx(72.30)
    assert cell.field == "intervention_mean"
    assert cell.arm == ARM_INTERVENTION
    assert cell.support == 2
    evidence = cell.evidence[0]
    assert evidence.table_id == table.table_id
    assert evidence.doc_id == "TESTDOC"
    assert evidence.unit_id and evidence.strategy == STRATEGY_BIDIRECTIONAL
    assert evidence.direction in {DIRECTION_ROW, DIRECTION_COLUMN}
    assert evidence.crop_id
    assert evidence.header_path == ("Arm B (n = 12)", "Mean")
    assert evidence.row_label == "Weight (kg)"


def test_conflicting_values_are_not_overwritten():
    table = _table()
    decomposition = plan(table, STRATEGY_BIDIRECTIONAL, PlanOptions(), DOCUMENT)
    row_unit = next(u for u in decomposition.units if u.direction == DIRECTION_ROW and 0 in u.row_ids)
    column_unit = next(u for u in decomposition.units if u.direction == DIRECTION_COLUMN and 3 in u.col_ids)
    script = {
        row_unit.unit_id: [(0, 3, 72.3)],
        column_unit.unit_id: [(0, 3, 73.2)],
    }
    engine = TableDecompositionEngine(
        backend=ScriptedBackend(script=script),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_BIDIRECTIONAL),
    )
    run = engine.run_table(table, DOCUMENT)
    cell = run.reconstruction.by_address()[(0, 3)]
    assert cell.status == STATUS_CONFLICT
    assert cell.value is None
    assert cell.candidates == pytest.approx([72.3, 73.2])
    assert run.reconstruction.stats["n_conflict"] >= 1
    assert all(p["row_id"] != 0 or p["col_id"] != 3
               for p in run.reconstruction.prediction_cells())


def test_adaptive_refinement_reads_a_missing_cell():
    table = _table()

    def partial(unit):
        cells = []
        for row_id, col_id in unit.expected_cells:
            if (row_id, col_id) == (1, 3) and unit.direction != DIRECTION_CELL:
                continue  # genau eine Zelle fehlt in der ersten Runde
            cell = table.cell(row_id, col_id)
            if cell is not None and cell.value is not None:
                cells.append({"row": row_id, "column": col_id,
                              "value": cell.value, "raw": cell.text})
        return cells

    engine = TableDecompositionEngine(
        backend=ScriptedBackend(fn=partial),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_ADAPTIVE,
                                        max_refinement_units=4, max_depth=1),
    )
    run = engine.run_table(table, DOCUMENT)
    cell_units = [u for u in run.units if u.direction == DIRECTION_CELL]
    assert len(cell_units) == 1
    assert cell_units[0].row_ids == [1] and cell_units[0].col_ids == [3]
    assert "FOCUS CELL CONTEXT" in cell_units[0].prompt
    assert table.row(1).label in cell_units[0].prompt
    resolved = run.reconstruction.by_address()[(1, 3)]
    assert resolved.value == pytest.approx(170.40)
    assert resolved.evidence[0].depth == 1


def test_refinement_is_capped():
    table = _table()
    units = refinement_units(
        table, [(0, 3), (1, 3), (2, 3), (0, 4), (1, 4)],
        PlanOptions(max_refinement_units=2), DOCUMENT,
    )
    assert len(units) == 2
    assert all(u.direction == DIRECTION_CELL for u in units)


def test_backend_failure_does_not_break_the_run():
    table = _table()

    def broken(prompt, unit):
        raise RuntimeError("gateway down")

    engine = TableDecompositionEngine(
        backend=ScriptedBackend(script={}),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_FULL),
    )
    engine.backend.extract = broken  # type: ignore[assignment]
    run = engine.run_table(table, DOCUMENT)
    assert run.results[0].error.startswith("backend_exception")
    assert run.telemetry["errors"] == 1
    assert run.reconstruction.stats["n_cells"] == 0


# --- Validierung ----------------------------------------------------------

def test_validation_structural_completeness_and_severance():
    table = _table()
    engine = TableDecompositionEngine(
        backend=perfect_backend(table),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_FULL),
    )
    run = engine.run_table(table, DOCUMENT)
    report = run.validation
    assert report.structural["coverage"] == 1.0
    assert report.status == STATUS_COMPLETE
    assert not report.errors
    assert any("Modellkonsens" in note for note in report.notes)


def test_validation_flags_missing_cell_and_plausibility_rules():
    table = _table()

    def wrong(unit):
        cells = []
        for row_id, col_id in unit.expected_cells:
            cell = table.cell(row_id, col_id)
            if cell is None or cell.value is None:
                continue
            value = cell.value
            raw = cell.text
            if (row_id, col_id) == (0, 3):
                value = 720.0      # absichtlich falsch
                raw = "720.0"      # und im Ausschnitt nicht belegt
            if (row_id, col_id) == (1, 4):
                value = 900.0      # SD weit ueber dem Mittelwert
                raw = "900.0"
            cells.append({"row": row_id, "column": col_id,
                          "value": value, "raw": raw})
        return cells

    engine = TableDecompositionEngine(
        backend=ScriptedBackend(fn=wrong),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_FULL),
    )
    run = engine.run_table(table, DOCUMENT)
    codes = {f.code for f in run.validation.findings}
    assert "beleg_nicht_im_ausschnitt" in codes
    assert "sd_gegen_mittel" in codes


def test_validation_detects_uncovered_cell_and_header_gaps():
    table = _table()
    decomposition = plan(table, STRATEGY_FULL, PlanOptions(), DOCUMENT)
    unit = decomposition.units[0]
    unit.expected_cells = [c for c in unit.expected_cells if c != (0, 3)]
    unit.prompt = unit.prompt.replace("Arm B (n = 12)", "")
    from research_agent.table_decomposition.validation import validate

    report = validate(table, [unit], None)
    codes = {f.code for f in report.findings}
    assert "zelle_nicht_abgedeckt" in codes
    assert "header_kontext_fehlt" in codes
    assert report.status != STATUS_COMPLETE


def test_validation_flags_events_over_group_size():
    document = render_dash_table(
        groups=((1, 3), ("Arm B (n = 3)", "Arm C (n = 9)")),
        subheaders=((1, 2, 3, 4), ("n", "Events", "n", "Events")),
        rows=[("Weight (kg)", [(1, "3"), (2, "12"), (3, "9"), (4, "4")])],
        widths=[20, 8, 8, 8, 8],
        caption="Events per arm",
    )
    parsed = parse_document(document, "EVENTS")
    table = parsed.tables[0]
    enrich_table(table, CONTEXT)
    engine = TableDecompositionEngine(
        backend=perfect_backend(table),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_FULL),
    )
    run = engine.run_table(table, document)
    codes = {f.code for f in run.validation.findings}
    assert "ereignisse_ueber_gruppengroesse" in codes


# --- Konfiguration und Pipeline-Haken ------------------------------------

COMBINED_DOCUMENT = render_dash_table(
    groups=((1, 3), ("Verum (n = 12)", "Placebo (n = 11)")),
    subheaders=((1, 2, 3, 4), ("Mean (SD)", "Mean (SD)", "Mean (SD)", "Mean (SD)")),
    rows=[
        ("HbA1c (%)", [(1, "12.4 (3.1)"), (2, "1.2 (0.4)"), (3, "11.9 (2.8)"), (4, "1.1 (0.3)")]),
        ("BMI", [(1, "27.5 (4.2)"), (2, "0.9 (0.3)"), (3, "27.1 (3.9)"), (4, "0.8 (0.4)")]),
    ],
    widths=[20, 16, 16, 16, 16],
    caption="Changes by arm",
)

COMBINED_CONTEXT = {"intervention": "Verum", "comparator": "Placebo",
                    "outcome": "HbA1c", "outcome_type": "continuous"}


def test_combined_cell_yields_secondary_value_with_same_source():
    """``12.4 (3.1)`` traegt Mittelwert und Streuung; beide bleiben belegt."""
    parsed = parse_document(COMBINED_DOCUMENT, "COMBINED")
    table = parsed.tables[0]
    enrich_table(table, COMBINED_CONTEXT)
    mean_column = table.columns[1]
    assert mean_column.role == ROLE_MEAN
    assert mean_column.secondary_role == ROLE_SD
    assert mean_column.field == field_for(ROLE_MEAN, ARM_INTERVENTION)
    assert field_for(ROLE_SD, ARM_INTERVENTION) in reachable_fields(table)

    engine = TableDecompositionEngine(
        backend=perfect_backend(table),
        config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_FULL),
    )
    run = engine.run_table(table, COMBINED_DOCUMENT)
    fields = {(cell["field"], cell["value"]) for cell in run.reconstruction.prediction_cells()}
    assert (field_for(ROLE_MEAN, ARM_INTERVENTION), 12.4) in fields
    assert (field_for(ROLE_SD, ARM_INTERVENTION), 3.1) in fields
    codes = {finding.code for finding in run.validation.findings}
    assert "verbundwert_getrennt" in codes


def test_arm_transfer_marks_columns_and_keeps_provenance():
    """Ein belegter Gruppenkopf belegt denselben Kopf in der Schwestertabelle."""
    document = "\n\n".join([
        render_dash_table(
            groups=((1, 3), ("Verum (n = 12)", "Placebo (n = 11)")),
            subheaders=((1, 2, 3, 4), ("Mean", "SD", "Mean", "SD")),
            rows=[("HbA1c (%)", [(1, "12.4"), (2, "3.1"), (3, "11.9"), (4, "2.8")])],
            widths=[20, 14, 14, 14, 14],
            caption="First table",
        ),
        render_dash_table(
            groups=((1, 3), ("Verum (n = 12)", "Placebo (n = 11)")),
            subheaders=((1, 2, 3, 4), ("Mean", "SD", "Mean", "SD")),
            rows=[("BMI", [(1, "27.5"), (2, "4.2"), (3, "27.1"), (4, "3.9")])],
            widths=[20, 14, 14, 14, 14],
            caption="Second table",
        ),
    ])
    parsed = parse_document(document, "SIBLINGS")
    assert len(parsed.tables) == 2
    context = {"intervention": "Initiative X", "comparator": "Control"}
    for table in parsed.tables:
        enrich_table(table, context)
    # Der Kopf nennt den Arm nicht; ohne Beleg bleibt die Spalte ohne Feld.
    assert not any(column.field for column in parsed.tables[1].columns)

    proven = parsed.tables[0].columns[1]
    proven.arm = ARM_INTERVENTION
    proven.arm_basis = "header_treffer"
    proven.field = field_for(proven.role, ARM_INTERVENTION)
    transferred = transfer_arms_within_document(parsed.tables, context)
    assert transferred >= 1
    moved = [column for column in parsed.tables[1].columns if column.arm_basis == "uebertrag"]
    assert moved and all(column.arm == ARM_INTERVENTION for column in moved)
    assert all(column.field for column in moved)

    report = validate(parsed.tables[1], [], None)
    assert "armzuordnung_uebertragen" in {finding.code for finding in report.findings}


def test_config_reads_switch_from_bool_dict_and_env():
    assert TableDecompositionConfig.from_value(True).enabled
    assert not TableDecompositionConfig.from_value("false").enabled
    by_letter = TableDecompositionConfig.from_value("E")
    assert by_letter.enabled and by_letter.strategy == STRATEGY_ADAPTIVE
    by_dict = TableDecompositionConfig.from_value({"strategy": "B", "max_depth": 1})
    assert by_dict.enabled and by_dict.strategy == STRATEGY_VERTICAL and by_dict.max_depth == 1
    from_env = TableDecompositionConfig.from_env(
        {"TABLE_DECOMPOSITION": "true", "TABLE_DECOMPOSITION_STRATEGY": "D"}
    )
    assert from_env.enabled and from_env.strategy == STRATEGY_BIDIRECTIONAL
    assert table_decomposition_enabled(TableDecompositionConfig(enabled=True))


def test_augment_prompt_text_keeps_original_text():
    disabled, info = augment_prompt_text(DOCUMENT, "TESTDOC", CONTEXT,
                                         TableDecompositionConfig(enabled=False))
    assert disabled == DOCUMENT
    assert info["enabled"] is False

    enabled, info = augment_prompt_text(
        DOCUMENT, "TESTDOC", CONTEXT, TableDecompositionConfig(enabled=True)
    )
    assert enabled.startswith(DOCUMENT)
    assert "Structured table view" in enabled
    assert "Arm B (n = 12) > Mean" in enabled
    assert info["tables"] == 1
    assert info["appended_chars"] > 0


def test_engine_document_run_aggregates_telemetry():
    engine = TableDecompositionEngine(
        backend=None, config=TableDecompositionConfig(enabled=True, strategy=STRATEGY_FULL)
    )
    result = engine.run_document(DOCUMENT, "TESTDOC", context=CONTEXT)
    assert len(result.tables) == 1
    assert result.telemetry["calls"] == 1
    assert result.telemetry["errors"] == 1  # ohne Backend: ehrlicher Ausfall
    assert result.to_dict()["doc_id"] == "TESTDOC"
    json.dumps(result.to_dict())  # muss serialisierbar sein


def test_unit_prompt_never_leaks_gold_like_extra_fields():
    table = _table()
    decomposition = plan(table, STRATEGY_FULL, PlanOptions(), DOCUMENT)
    prompt = decomposition.units[0].prompt
    assert "intervention_mean" in prompt  # Zielfeld ist erlaubt und gewollt
    assert "gold" not in prompt.lower()
