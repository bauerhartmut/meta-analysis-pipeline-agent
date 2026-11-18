"""Tests der Fliesstext-Fundstellen (Sprint 48).

Geprueft wird die Regel, nicht die Messung:

- ``placebo, n = 28`` bindet den Arm an der Zahl,
- eine Zahlenliste zaehlt nur mit ``respectively`` und genannter Population,
- ``5.1% (4/79)`` liefert Ereigniszahl (Zaehler) und Groesse (Nenner),
- eine Tabellenzone ist kein Fliesstext,
- ohne Outcome im Satz (oder dessen gedruckter Abkuerzung) entsteht kein Fakt,
- ungleiche Listen ergeben keinen Fakt.

Die Dokumenttests lesen die eingefrorenen Benchmark-Dokumente nur.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_agent.table_decomposition import fliesstext as fl
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


def _record_text_context(record_id: str):
    record = _record(record_id)
    context = {
        key: record["context"].get(key)
        for key in ("intervention", "comparator", "outcome", "outcome_type")
    }
    text = Path(record["document"]["path"]).read_text(encoding="utf-8",
                                                      errors="replace")
    tables = list(parse_document(text, str(record["document"]["id"])).tables)
    for table in tables:
        enrich_table(table, context)
    transfer_arms_within_document(tables, context)
    transfer_arms_from_document(tables, context, text)
    return text, context, tables


def test_label_n_bindet_den_arm_an_der_zahl():
    text, context, tables = _record_text_context("yun2024:185")
    stellen = fl.stellen(text, context, tables)

    comparator = stellen["comparator_group_size"]
    assert {stelle.wert for stelle in comparator} == {28.0}
    assert {stelle.arm for stelle in comparator} == {"comparator"}
    assert all(stelle.regel.startswith(fl.REGEL_LABEL) for stelle in comparator)


def test_zahlenliste_mit_beziehungsweise_und_genannter_population():
    text, context, tables = _record_text_context("yun2024:531")
    stellen = fl.stellen(text, context, tables)

    intervention = {(stelle.wert, stelle.regel) for stelle in
                    stellen["intervention_group_size"]}
    assert (283.0, f"{fl.REGEL_LISTE}:itt") in intervention
    assert (289.0, f"{fl.REGEL_LISTE}:itt") in intervention
    assert (298.0, f"{fl.REGEL_LISTE}:sicherheit") in intervention
    comparator = {(stelle.wert, stelle.regel) for stelle in
                  stellen["comparator_group_size"]}
    assert (204.0, f"{fl.REGEL_LISTE}:itt") in comparator


def test_bruchliste_liefert_ereignis_und_groesse():
    text, context, tables = _record_text_context("yun2024:265")
    stellen = fl.stellen(text, context, tables)

    assert {stelle.wert for stelle in stellen["intervention_events"]} == {3.0, 4.0}
    assert {stelle.wert for stelle in stellen["comparator_events"]} == {4.0}
    assert {stelle.wert for stelle in stellen["comparator_group_size"]} == {79.0}


def test_tabellenzone_ist_kein_fliesstext():
    text, context, tables = _record_text_context("yun2024:185")

    ohne = fl.stellen(text, context, [])
    mit = fl.stellen(text, context, tables)
    # 33 steht nur in der Tabelle (Baseline-Kopf), 28 im CTT-Satz daneben.
    assert {stelle.wert for stelle in ohne["comparator_group_size"]} == {28.0, 33.0}
    assert {stelle.wert for stelle in mit["comparator_group_size"]} == {28.0}


def test_ohne_outcome_im_satz_kein_fakt():
    text, context, tables = _record_text_context("yun2024:184")
    stellen = fl.stellen(text, context, tables)

    # Der CTT-Satz desselben Dokuments nennt nicht das Outcome dieses Records.
    assert "comparator_group_size" not in stellen


def test_korroboration_markiert_itt_und_nicht_safety():
    text, context, tables = _record_text_context("yun2024:531")
    stellen = fl.stellen(text, context, tables)

    # 204 steht im Ergebnissatz als n = 204 (ITT), 214 nur in der
    # Safety-Liste.
    alle = {stelle.wert for stelle in stellen["comparator_group_size"]}
    belegt = {stelle.wert for stelle in stellen["comparator_group_size"]
              if stelle.belegt}
    assert alle == {204.0, 214.0}
    assert belegt == {204.0}


def test_korroboration_braucht_das_n_im_ergebnis():
    context = {"outcome": "pain"}

    assert fl.im_ergebnis("Pain scores fell (−14.88 [n = 289]).", context, 289)
    assert not fl.im_ergebnis("Pain scores fell (−14.88 [n = 289]).",
                              {"outcome": "sleep"}, 289)
    # Dieselbe Zahl, aber nicht als Stichprobengroesse im Ergebnissatz.
    assert not fl.im_ergebnis("289 patients were included in the study.",
                              context, 289)


def test_ungleiche_listen_ergeben_keinen_fakt():
    context = {"intervention": "drug", "comparator": "placebo",
               "outcome": "pain"}
    stellen = fl.stellen("(12, 13 patients received drug, respectively)", context)

    assert stellen == {}
