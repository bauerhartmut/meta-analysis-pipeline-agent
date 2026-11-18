"""Tests des Provenienzmodells (Sprint 45).

Geprueft wird, dass jede Fundstelle ihren Originaltext, ihren Arm und ihre
Regel traegt und dass direkt gedruckte Werte von abgeleiteten unterscheidbar
bleiben:

- zwei gedruckte Untergruppen (``n = 17``/``n = 16``) ergeben ``mehrfach``,
  nicht ``direkt`` - eine Summe ist damit nie eine gedruckte Gruppengroesse,
- eine einzelne Kopfangabe ist ``direkt`` mit hoher Sicherheit,
- eine Verbundzelle (``2.2 (1)``, ``15.2 +- 19.2``) ist ``abgeleitet`` und
  traegt keinen Wert.

Die Dokumenttests lesen die eingefrorenen Benchmark-Dokumente nur; fehlt der
Datensatz, werden sie uebersprungen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_agent.table_decomposition import provenienz as pv
from research_agent.table_decomposition.parser import parse_document
from research_agent.table_decomposition.semantics import (
    enrich_table,
    reachable_cells,
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


def _alle(table, context, feld):
    stellen = []
    for row_id, name in reachable_cells(table, context):
        if name != feld:
            continue
        for stelle in pv.stellen(table, row_id, feld):
            if stelle not in stellen:
                stellen.append(stelle)
    return stellen


def test_zwei_untergruppen_sind_mehrfach_und_nie_eine_summe():
    tables, _context = _tables("yun2024:172")
    table = tables["PMC5079604:T1"]
    kopf = pv.stellen(table, -1, "intervention_group_size")

    assert [s.wert for s in kopf] == [17.0, 16.0]
    assert [s.art for s in kopf] == [pv.DIREKT, pv.DIREKT]
    assert pv.feld_art(kopf) == pv.MEHRFACH
    assert pv.feld_arm(kopf) == "eindeutig"
    assert all(s.regel == "gruppengroesse_im_kopf" for s in kopf)


def test_einzelne_kopfangabe_ist_direkt_und_belegt_den_arm():
    tables, _context = _tables("yun2024:335")
    table = tables["PMC5617873:T2"]
    kopf = pv.stellen(table, -1, "intervention_group_size")

    assert len(kopf) == 1
    assert kopf[0].wert == 47.0
    assert kopf[0].arm == "intervention"
    assert kopf[0].art == pv.DIREKT
    assert kopf[0].sicherheit == pv.HOCH
    assert "Aripiprazole" in kopf[0].text


def test_verschobenes_band_traegt_die_gedruckte_zahl():
    tables, _context = _tables("yun2024:678")
    table = tables["PMC5777419:T2"]
    kopf = pv.stellen(table, -1, "intervention_group_size")

    assert [s.wert for s in kopf] == [15.0]
    assert kopf[0].arm == "intervention"
    assert kopf[0].text.strip() == "(n=15)"


def test_verbundzelle_ist_abgeleitet_ohne_wert():
    tables, context = _tables("yun2024:421")
    table = tables["PMC3877023:T3"]
    stellen = [s for s in _alle(table, context, "intervention_mean")
               if s.text.strip() == "2.2 (1)"]
    if not stellen:
        pytest.skip("Verbundzelle in dieser Tabelle nicht belegt")

    assert stellen[0].art == pv.ABGELEITET
    assert stellen[0].wert is None
    assert pv.feld_art(stellen) == pv.ABGELEITET
    assert stellen[0].quelle == pv.QUELLE_ZELLE


def test_streuung_aus_verbundzelle_traegt_eigene_regel():
    tables, context = _tables("yun2024:665")
    stellen = [s for table in tables.values()
               for s in _alle(table, context, "intervention_standard_deviation")
               if "±" in s.text or "+-" in s.text]
    if not stellen:
        pytest.skip("Verbundzelle mit Streuung nicht belegt")

    stelle = stellen[0]
    assert stelle.art == pv.ABGELEITET
    assert stelle.wert is None
    assert stelle.arm == "intervention"
    assert stelle.regel == "zweitwert_der_spalte"
