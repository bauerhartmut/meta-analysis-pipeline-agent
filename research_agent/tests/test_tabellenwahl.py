"""Tests der Tabellenwahl aus dem Dokument (Sprint 46).

Geprueft wird die Regel, nicht die Messung:

- eine Baseline-Tabelle wird erkannt (Caption oder Kopfband),
- eine Baseline-Tabelle ohne Outcome-Zeile wird durch die Outcome-Tabelle
  ersetzt,
- eine aktuelle Tabelle, die selbst eine Outcome-Zeile traegt, bleibt - auch
  wenn ihre Beschriftung nach Baseline klingt,
- der Wechsel haengt keinen Arm um.

Die Dokumenttests lesen die eingefrorenen Benchmark-Dokumente nur.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_agent.table_decomposition import provenienz as pv
from research_agent.table_decomposition import tabellenwahl as tw
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


def test_baseline_wird_an_der_beschriftung_erkannt():
    tables, _context = _tables("yun2024:645")

    assert tw.ist_baseline(tables["PMC4675066:T1"])
    assert not tw.ist_baseline(tables["PMC4675066:T2"])


def test_baseline_ohne_outcome_zeile_waehlt_die_outcome_tabelle():
    tables, context = _tables("yun2024:645")
    wahl = tw.waehle([tables["PMC4675066:T1"]], list(tables.values()), context)

    assert wahl is not None and wahl.wechsel
    assert wahl.grund == "outcome_tabelle"
    assert wahl.tabelle.table_id == "PMC4675066:T2"


def test_aktuelle_tabelle_mit_outcome_zeile_bleibt():
    tables, context = _tables("yun2024:445")
    aktuelle = [tables["PMC4140238:T1"], tables["PMC4140238:T2"]]
    wahl = tw.waehle(aktuelle, list(tables.values()), context)

    assert wahl is not None
    assert not wahl.wechsel
    assert wahl.grund == "aktuelle_tabelle_traegt_outcome"


def test_wechsel_haengt_keinen_arm_um():
    tables, context = _tables("yun2024:645")
    wahl = tw.waehle([tables["PMC4675066:T1"]], list(tables.values()), context)
    ziel = wahl.tabelle

    stellen = pv.feld_stellen([ziel], context)
    assert pv.feld_arm(stellen["intervention_group_size"]) == "eindeutig"
    assert pv.feld_arm(stellen["comparator_group_size"]) == "eindeutig"
    assert {s.arm for s in stellen["intervention_group_size"]} == {"intervention"}
    assert {s.arm for s in stellen["comparator_group_size"]} == {"comparator"}
