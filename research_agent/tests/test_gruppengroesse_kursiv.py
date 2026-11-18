"""Regressionstests der kursiv gesetzten Gruppengroessen (Sprint 44).

Vor der Erweiterung erkannte ``_GROUP_SIZE_ANY_RE`` nur ``n = 103``. In den
eingefrorenen Dokumenten steht die Angabe aber haeufig als ``*n* = 103``,
``( *n* = 71)`` oder ``***n*** = 298``; diese Bänder erzeugten keinen
``header_fact``. Geprueft wird:

- die Schreibweisen (kursiv, fett, Klammern, Leerzeichen) ergeben dieselbe Zahl
  wie die schlichte Form,
- gewoehnliche Zahlen und tiefgestellte Zaehler werden nicht zur
  Gruppengroesse,
- die vier betroffenen Tabellen binden den Wert an das richtige Band,
- die Spaltengeometrie und die Armzuordnung bleiben unveraendert.

Die Dokumenttests lesen die eingefrorenen Benchmark-Dokumente nur; sie
schreiben nichts. Fehlt der Datensatz, werden sie uebersprungen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_agent.table_decomposition.parser import parse_document
from research_agent.table_decomposition.semantics import (
    _GROUP_SIZE_ANY_RE,
    enrich_table,
    group_size_declaration,
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
    text = Path(record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
    parsed = parse_document(text, str(record["document"]["id"]))
    for table in parsed.tables:
        enrich_table(table, context)
    transfer_arms_within_document(parsed.tables, context)
    transfer_arms_from_document(parsed.tables, context, text)
    return {table.table_id: table for table in parsed.tables}, context


def _felder(table, context):
    return {name for _row, name in reachable_cells(table, context)}


def _fakten(table):
    return {(fact["text"], fact["value"], fact["arm"]) for fact in table.header_facts}


# --- Schreibweisen --------------------------------------------------------


@pytest.mark.parametrize("text,wert", [
    ("n = 103", 103),
    ("(n = 103)", 103),
    ("*n* = 103", 103),
    ("(*n* = 103)", 103),
    ("( *n* = 71)", 71),
    ("(*n*\u2009=\u200923)", 23),
    ("**N** = 12", 12),
    ("***n*** = 298", 298),
    ("(***n***\u2009=\u2009214)", 214),
    ("N = 456", 456),
])
def test_group_size_declaration_accepts_emphasis(text, wert):
    """Kursive und fette Auszeichnung sind Dekoration, keine andere Zahl."""
    assert group_size_declaration(text) == wert
    assert int(_GROUP_SIZE_ANY_RE.search(text).group(1)) == wert


@pytest.mark.parametrize("text", [
    "season = 5",
    "df = 2",
    "p = 0.05",
    "no = 12",
    "n = 1234567",          # mehr als sechs Ziffern
    "**N**~**c**~**= 12**",  # tiefgestellter Zaehler, keine Gruppengroesse
    "(*n* = )",
    "n 103",
])
def test_group_size_declaration_rejects_other_numbers(text):
    assert group_size_declaration(text) is None
    assert _GROUP_SIZE_ANY_RE.search(text) is None


def test_group_size_in_a_caption_is_not_a_pure_declaration():
    """``Placebo (n = 45)`` traegt einen Namen - reine Angabe ist nur ``n = 45``."""
    assert group_size_declaration("Placebo (n = 45)") is None
    assert _GROUP_SIZE_ANY_RE.search("Placebo (n = 45)").group(1) == "45"


# --- Die vier betroffenen Tabellen ---------------------------------------


def test_kursives_n_ist_die_intervention_und_bleibt_am_band():
    """``PMC2667135:T4``: ``CoPAT (*n* = 103)``, ``IPAT (*n* = 97)``."""
    tables, context = _tables("yun2024:15")
    table = tables["PMC2667135:T4"]

    assert ("CoPAT^a^ (*n* = 103)", 103, "intervention") in _fakten(table)
    assert ("IPAT (*n* = 97)", 97, None) in _fakten(table)
    baender = {band.text: (band.level, band.col_start, band.col_end)
               for band in table.header_bands}
    assert baender["CoPAT^a^ (*n* = 103)"] == (0, 1, 1)
    assert baender["IPAT (*n* = 97)"] == (0, 2, 2)
    assert "intervention_group_size" in _felder(table, context)


def test_placebo_und_untergruppen_bleiben_getrennt():
    """``PMC4987981:T1``: 23 Placebo, 21 Metformin, 16 Pioglitazon."""
    tables, context = _tables("yun2024:662")
    table = tables["PMC4987981:T1"]

    assert ("Placebo (*n*\u2009=\u200923)", 23, "comparator") in _fakten(table)
    assert ("Metformin (*n*\u2009=\u200921)", 21, "intervention") in _fakten(table)
    assert ("Pioglitazone (*n*\u2009=\u200916)", 16, "intervention") in _fakten(table)
    felder = _felder(table, context)
    assert {"comparator_group_size", "intervention_group_size"} <= felder
    # Die Goldsumme 37 steht nicht im Kopf; nur die Einzelgruppen sind gedruckt.
    assert 37 not in {fact["value"] for fact in table.header_facts}


def test_band_mit_namen_behaelt_geometrie_und_arm():
    """``PMC3654355:T1``: ``ILI ( *n* = 71)`` und ``Control ( *n* = 33)``."""
    tables, context = _tables("yun2024:275")
    table = tables["PMC3654355:T1"]

    assert ("ILI ( *n* = 71)", 71, "intervention") in _fakten(table)
    assert ("Control ( *n* = 33)", 33, None) in _fakten(table)
    baender = {band.text: (band.level, band.col_start, band.col_end)
               for band in table.header_bands}
    assert baender["ILI ( *n* = 71)"] == (0, 1, 1)
    assert baender["Control ( *n* = 33)"] == (0, 2, 2)
    assert _felder(table, context) == {"intervention_group_size"}


def test_reine_kursive_angabe_ist_kein_spaltenkopf():
    """``PMC3654355:T2``: ``( *n* = 71)`` unter ``ILI`` ist eine Kopfangabe."""
    tables, context = _tables("yun2024:282")
    table = tables["PMC3654355:T2"]

    assert group_size_declaration("( *n* = 71)") == 71
    assert ("( *n* = 71)", 71, "intervention") in _fakten(table)
    assert ("( *n* = 33)", 33, None) in _fakten(table)
    spalte = next(column for column in table.columns if column.col_id == 1)
    assert spalte.role != "n"
    assert _felder(table, context) == {"intervention_group_size"}


# --- Keine neuen Armkonflikte --------------------------------------------


def test_armkonflikte_bleiben_wie_sie_waren():
    """Die Erweiterung erkennt Werte, sie ordnet keinen Arm neu zu."""
    tables, _context = _tables("yun2024:678")
    table = tables["PMC5777419:T2"]
    arme = {(fact["value"], fact["arm"]) for fact in table.header_facts}
    assert (15, "intervention") in arme
    assert (16, None) in arme

    tables, _context = _tables("yun2024:335")
    table = tables["PMC5617873:T2"]
    arme = {(fact["value"], fact["arm"]) for fact in table.header_facts}
    assert (45, None) in arme
    assert (47, "intervention") in arme
