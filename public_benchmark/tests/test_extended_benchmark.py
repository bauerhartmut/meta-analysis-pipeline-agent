"""Tests fuer den erweiterten Benchmark: Adapter, Schema und NXML-Parser."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extended_benchmark import download_pmc_oa  # noqa: E402
from extended_benchmark.adapters import ebm_nlp, evidence_inference, yun  # noqa: E402
from extended_benchmark.build_extended_benchmark import REQUIRED, validate  # noqa: E402


def test_yun_records_match_schema_and_exclude_frozen_split() -> None:
    records = yun.build(limit=5)
    assert records, "Yun-Adapter lieferte keine Records"
    assert validate(records) == []
    for record in records:
        for key in REQUIRED:
            assert key in record
        assert record["record_id"].startswith("yun2024:")
        assert record["task"] == "numeric_extraction"
        assert record["document"]["id"].startswith("PMC")

    frozen = yun.frozen_test_ids()
    if frozen:
        ids = {int(record["record_id"].split(":")[1]) for record in records}
        assert not ids & frozen


def test_yun_cells_have_arms_and_numbers() -> None:
    records = yun.build(limit=20)
    cells = [cell for record in records for cell in record["gold"]["cells"]]
    assert cells, "Keine Gold-Zellen extrahiert"
    for cell in cells:
        assert cell["arm"] in {"intervention", "comparator"}
        assert isinstance(cell["value"], float)
        assert cell["field"]


def test_evidence_inference_groups_prompts_with_spans() -> None:
    records = evidence_inference.build(limit=3)
    assert records
    assert validate(records) == []
    record = records[0]
    assert record["task"] == "evidence_direction"
    assert record["gold"]["label"] in {
        "no significant difference",
        "significantly increased",
        "significantly decreased",
        None,
    }
    assert isinstance(record["gold"]["spans"], list)


def test_ebm_nlp_spans_are_ordered_ranges() -> None:
    records = ebm_nlp.build(limit=3)
    assert records
    assert validate(records) == []
    for record in records:
        assert record["task"] == "pico_span"
        for span in record["gold"]["spans"]:
            assert span["element"] in {"participants", "interventions", "outcomes"}
            assert 0 <= span["start"] < span["end"]
            assert span["text"]


NXML = """<?xml version="1.0"?>
<article>
  <front><article-meta>
    <title-group><article-title>Testtitel</article-title></title-group>
    <abstract><p>Abstracttext.</p></abstract>
  </article-meta></front>
  <body>
    <sec><title>Ergebnisse</title><p>Absatz eins.</p></sec>
    <table-wrap>
      <label>Tabelle 1</label>
      <caption><p>Hauptergebnisse</p></caption>
      <table>
        <thead><tr><th>Arm</th><th>n</th></tr></thead>
        <tbody><tr><td>Intervention</td><td>143</td></tr><tr><td>Kontrolle</td><td>97</td></tr></tbody>
      </table>
      <table-wrap-foot><p>HR aus Cox-Modell.</p></table-wrap-foot>
    </table-wrap>
  </body>
  <supplementary-material><label>Anhang A</label></supplementary-material>
</article>
"""


def test_parse_nxml_keeps_table_structure_and_footnotes() -> None:
    parsed = download_pmc_oa.parse_nxml(NXML)
    assert parsed["title"] == "Testtitel"
    assert "Abstracttext" in parsed["abstract"]
    assert parsed["sections"][0]["heading"] == "Ergebnisse"
    table = parsed["tables"][0]
    assert table["label"] == "Tabelle 1"
    assert table["header_rows"] == [["Arm", "n"]]
    assert ["Intervention", "143"] in table["rows"]
    assert table["footnotes"] == ["HR aus Cox-Modell."]
    assert parsed["supplementary"][0]["label"] == "Anhang A"


@pytest.mark.parametrize(
    ("license_text", "expected"),
    [
        ("CC BY", True),
        ("CC BY 4.0", True),
        ("CC BY-SA", True),
        ("CC0", True),
        ("CC BY-NC", False),
        ("CC BY-ND", False),
        ("CC BY-NC-ND", False),
        ("", False),
        ("TBD", False),
    ],
)
def test_license_filter(license_text: str, expected: bool) -> None:
    assert download_pmc_oa.license_allowed(license_text) is expected
