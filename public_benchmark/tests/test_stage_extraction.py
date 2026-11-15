"""Tests fuer die zweistufige Ereignisextraktion (nur reine Funktionen)."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "extended_benchmark"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from stage_extraction import (  # noqa: E402
    beleg_im_text,
    build_stage1_prompt,
    build_stage2_prompt,
    merge_event_cells,
    normalisiere,
    parse_stage1,
    parse_stage2,
)

CONTEXT = {
    "intervention": "sedatives",
    "comparator": "treatment as usual",
    "outcome": "sick leave",
    "outcome_type": "binary",
}


def test_stage1_prompt_fragt_nur_nach_label_und_kopf() -> None:
    prompt = build_stage1_prompt("TEXT", CONTEXT)
    assert "row label" in prompt and "column header" in prompt
    assert "locators" in prompt
    assert "sedatives" in prompt and "sick leave" in prompt
    assert "Do not return any numbers" in prompt


def test_stage2_prompt_nennt_die_stelle() -> None:
    prompt = build_stage2_prompt("TEXT", CONTEXT, "intervention", "0-3 months", "Total 0-12 months", "Table 3")
    assert '"0-3 months"' in prompt
    assert '"Total 0-12 months"' in prompt
    assert "Table 3" in prompt


def test_parse_stage1_liest_locators_und_codefence() -> None:
    content = '```json\n{"locators": [{"arm": "intervention", "row_label": "0-3 months", ' \
        '"column_header": "Total", "caption": "Table 3", "found": true}]}\n```'
    locators, error = parse_stage1(content)
    assert error == ""
    assert locators == [
        {
            "arm": "intervention",
            "found": True,
            "row_label": "0-3 months",
            "column_header": "Total",
            "caption": "Table 3",
        }
    ]


def test_parse_stage1_behandelt_fehlenden_arm_und_muell() -> None:
    locators, error = parse_stage1('{"locators": [{"arm": "comparator", "found": false}]}')
    assert error == ""
    assert locators[0]["found"] is False
    assert parse_stage1("keine antwort") == ([], "kein_json")
    assert parse_stage1('{"locators": []}') == ([], "keine_verwertbaren_locators")


def test_parse_stage2_liest_zahl_und_bruch() -> None:
    assert parse_stage2('{"value": 48, "quote": "48", "found": true}')[0] == 48.0
    assert parse_stage2('{"value": "31/48", "quote": "31/48", "found": true}')[0] == 31.0
    value, _quote, found, error = parse_stage2('{"value": null, "quote": "", "found": false}')
    assert (value, found, error) == (None, False, "")
    assert parse_stage2('{"value": null, "found": true}')[3] == "kein_wert"
    assert parse_stage2('{"value": "keine Angabe"}')[3] == "wert_keine_zahl"


def test_beleg_abgleich_ignoriert_grossschreibung_und_abstaende() -> None:
    text = "Sick  leave\n0-3 months:   31/48"
    assert beleg_im_text("0-3 MONTHS", text) is True
    assert beleg_im_text("0-3  months", text) is True
    assert beleg_im_text("Total 0-12 months", text) is False
    assert normalisiere(" A\n B ") == "a b"
    assert beleg_im_text("", text) is False


def test_merge_ersetzt_nur_ereigniszellen() -> None:
    baseline = [
        {"field": "intervention_mean", "arm": "intervention", "value": 50.6},
        {"field": "intervention_events", "arm": "intervention", "value": 31.0},
        {"field": "comparator_events", "arm": "comparator", "value": 48.0},
    ]
    merged, replaced, fallback = merge_event_cells(
        baseline, {"intervention_events": 49.0, "comparator_events": 64.0}
    )
    assert [cell["value"] for cell in merged] == [50.6, 49.0, 64.0]
    assert replaced == ["intervention_events", "comparator_events"]
    assert fallback == []


def test_merge_faellt_ohne_stufenwert_auf_basis_zurueck() -> None:
    baseline = [{"field": "comparator_events", "arm": "comparator", "value": 48.0}]
    merged, replaced, fallback = merge_event_cells(baseline, {"intervention_events": 49.0})
    assert replaced == ["intervention_events"]
    assert fallback == ["comparator_events"]
    assert {cell["field"]: cell["value"] for cell in merged} == {
        "comparator_events": 48.0,
        "intervention_events": 49.0,
    }
