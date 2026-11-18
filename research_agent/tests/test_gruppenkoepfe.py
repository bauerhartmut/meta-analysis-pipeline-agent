"""Tests der Sprint-47-Luecken: Gruppenkopf-Zeile und Zielwahl.

Geprueft wird die Regel, nicht die Messung:

- ein Gruppenkopf in einer Datenzeile wird zur Kopfangabe (79/83/80) und
  behaelt seinen gedruckten Arm,
- eine gewoehnliche Datenzeile wird nicht zur Kopfangabe.

Die Caption-Tests liegen in diesem Zwischenstand noch nicht bei; sie kommen mit
der eigenen Caption-Aenderung.

Die Dokumenttests lesen die eingefrorenen Benchmark-Dokumente nur.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_agent.table_decomposition import provenienz as pv
from research_agent.table_decomposition.parser import parse_document
from research_agent.table_decomposition.semantics import (
    enrich_table,
    transfer_arms_from_document,
    transfer_arms_within_document,
)

REPO = Path(__file__).resolve().parents[2]
RECORDS = (REPO / "public_benchmark" / "extended_benchmark" / "yun_full"
           / "records" / "yun699.jsonl")


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


def _tables(record_id: str):
    record = _record(record_id)
    context = {
        key: record["context"].get(key)
        for key in ("intervention", "comparator", "outcome", "outcome_type")
    }
    text = Path(record["document"]["path"]).read_text(encoding="utf-8",
                                                      errors="replace")
    parsed = parse_document(text, str(record["document"]["id"]))
    for table in parsed.tables:
        enrich_table(table, context)
    transfer_arms_within_document(parsed.tables, context)
    transfer_arms_from_document(parsed.tables, context, text)
    return {table.table_id: table for table in parsed.tables}, context


def test_gruppenkopf_in_datenzeile_wird_kopfangabe():
    tables, context = _tables("yun2024:265")
    t4 = tables["PMC2430617:T4"]

    facts = [(f["value"], f["arm"], f["basis"]) for f in t4.header_facts]
    assert facts == [
        (79, "comparator", "zeile_angabe"),
        (83, "intervention", "zeile_angabe"),
        (80, "intervention", "zeile_angabe"),
    ]

    stellen = pv.feld_stellen([t4], context)
    assert {s.wert for s in stellen["intervention_group_size"]} == {83.0, 80.0}
    comparator = stellen["comparator_group_size"]
    assert [s.arm for s in comparator] == ["comparator"]
    assert comparator[0].regel == "gruppengroesse_in_datenzeile"
    assert comparator[0].zeile == 0


def test_datenzeile_wird_keine_kopfangabe():
    tables, _context = _tables("yun2024:194")
    t1 = tables["PMC5360580:T1"]

    assert not [f for f in t1.header_facts if f["basis"] == "zeile_angabe"]
    assert [f["value"] for f in t1.header_facts] == [145, 140]
