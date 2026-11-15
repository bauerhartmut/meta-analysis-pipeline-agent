"""Tests fuer die Fehleranalyse (analyze_errors.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.analyze_errors import (  # noqa: E402
    GEPRUEFTE_FAELLE,
    Dokument,
    baue_faelle,
    baue_queue,
    klassifiziere,
    pruefe_gold,
    zahlenvarianten,
)


@pytest.fixture()
def dokument(tmp_path: Path):
    def bauen(text: str) -> Dokument:
        path = tmp_path / "artikel.md"
        path.write_text(text, encoding="utf-8")
        return Dokument(path)

    return bauen


def test_zahlenvarianten_enthalten_schreibweisen() -> None:
    varianten = zahlenvarianten(487.33)
    assert "487.33" in varianten
    assert "487,33" in varianten
    assert "487" in varianten


def test_dokument_findet_unicode_minus(dokument) -> None:
    doc = dokument("Die Kontrollgruppe zeigte \u2212 0,7 gm.")
    treffer, index = doc.finde(-0.7)
    assert treffer == 1
    assert "0,7" in doc.ausschnitt(index)


def test_dokument_findet_tausendertrennzeichen(dokument) -> None:
    doc = dokument("Insgesamt 1,831 Teilnehmer wurden eingeschlossen.")
    treffer, _ = doc.finde(1831)
    assert treffer == 1


def _leer() -> dict:
    return {}


def test_klassifiziert_gruppenverwechslung(dokument) -> None:
    doc = dokument("ohne Zahlen")
    gold = {("intervention_mean", "intervention"): 10.0, ("intervention_mean", "comparator"): 20.0}
    pred = {("intervention_mean", "intervention"): 20.0, ("intervention_mean", "comparator"): 10.0}
    klasse, beleg = klassifiziere(
        gold=10.0, pred=20.0, field="intervention_mean", arm="intervention",
        gold_cells=gold, pred_cells=pred, dokument=doc, geschwister=[],
    )
    assert klasse == 5
    assert "vertauscht" in beleg


def test_klassifiziert_ereignisse_als_gruppengroesse(dokument) -> None:
    doc = dokument("ohne Zahlen")
    gold = {("intervention_events", "intervention"): 8.0, ("intervention_group_size", "intervention"): 120.0}
    klasse, beleg = klassifiziere(
        gold=8.0, pred=120.0, field="intervention_events", arm="intervention",
        gold_cells=gold, pred_cells={}, dokument=doc, geschwister=[],
    )
    assert klasse == 6
    assert "Gruppengroesse" in beleg


def test_klassifiziert_prozentwert_als_ereigniszahl(dokument) -> None:
    doc = dokument("ohne Zahlen")
    # 10 von 120 Teilnehmern sind 8,33 Prozent; das Modell liefert die Rate.
    gold = {("intervention_events", "intervention"): 10.0, ("intervention_group_size", "intervention"): 120.0}
    klasse, beleg = klassifiziere(
        gold=10.0, pred=8.3, field="intervention_events", arm="intervention",
        gold_cells=gold, pred_cells={}, dokument=doc, geschwister=[],
    )
    assert klasse == 7
    assert "Prozentwert" in beleg

    # Identische Werte sind keine Abweichung, auch wenn die Rate zufaellig passt.
    klasse, _ = klassifiziere(
        gold=12.0, pred=12.0, field="intervention_events", arm="intervention",
        gold_cells={("intervention_events", "intervention"): 12.0, ("intervention_group_size", "intervention"): 100.0},
        pred_cells={}, dokument=doc, geschwister=[],
    )
    assert klasse != 7


def test_klassifiziert_vertauschte_kennzahl(dokument) -> None:
    doc = dokument("ohne Zahlen")
    gold = {
        ("intervention_mean", "intervention"): 10.0,
        ("intervention_standard_deviation", "intervention"): 3.5,
    }
    klasse, beleg = klassifiziere(
        gold=10.0, pred=3.5, field="intervention_mean", arm="intervention",
        gold_cells=gold, pred_cells={}, dokument=doc, geschwister=[],
    )
    assert klasse == 8
    assert "standard_deviation" in beleg


def test_klassifiziert_geschwisterzeile(dokument) -> None:
    doc = dokument("ohne Zahlen")
    klasse, beleg = klassifiziere(
        gold=10.0, pred=99.0, field="intervention_mean", arm="intervention",
        gold_cells={("intervention_mean", "intervention"): 10.0},
        pred_cells={}, dokument=doc, geschwister=[(99.0, "Body mass index (intervention_mean, intervention)")],
    )
    assert klasse == 1
    assert "Body mass index" in beleg


def test_klassifiziert_wert_im_text_als_mehrdeutig(dokument) -> None:
    doc = dokument("Follow up nach vier Monaten: 854 \u00b1 271,60 (470 \u00b1 80,46).")
    klasse, beleg = klassifiziere(
        gold=487.33, pred=854.0, field="intervention_mean", arm="intervention",
        gold_cells={("intervention_mean", "intervention"): 487.33},
        pred_cells={}, dokument=doc, geschwister=[],
    )
    assert klasse == 15
    assert "wortwoertlich" in beleg


def test_klassifiziert_halluzinierten_wert(dokument) -> None:
    doc = dokument("Im Text steht keine passende Zahl.")
    klasse, beleg = klassifiziere(
        gold=10.0, pred=4711.0, field="intervention_mean", arm="intervention",
        gold_cells={("intervention_mean", "intervention"): 10.0},
        pred_cells={}, dokument=doc, geschwister=[],
    )
    assert klasse == 11
    assert "nicht vor" in beleg


def _record(rid: str, cells: list[tuple[str, str, float]], path: Path, pmcid: str = "PMC1") -> dict:
    return {
        "record_id": rid,
        "context": {"outcome": "Test"},
        "document": {"id": pmcid, "path": str(path), "kind": "abstract_markdown", "split": "dev", "text_chars": 10},
        "gold": {"cells": [{"field": f, "arm": a, "value": v} for f, a, v in cells]},
    }


def test_baue_faelle_trennt_fehlend_und_technisch(tmp_path: Path, dokument) -> None:
    doc_path = tmp_path / "a.md"
    doc_path.write_text("Zahlen 10 und 12.", encoding="utf-8")
    records = [_record("r1", [("intervention_mean", "intervention", 10.0)], doc_path)]
    docs = {"PMC1": Dokument(doc_path)}

    leer = {"r1": {"predicted": {"cells": []}}}
    faelle, zusatz, zusammenfassung = baue_faelle(
        "lauf", "m", "v1", records, leer, docs, False, {}
    )
    assert faelle[0]["klasse"] == 13
    assert zusammenfassung["zellen"] == 1

    ohne_feld = {"r1": {"predicted": {"cells": [{"field": "comparator_mean", "arm": "comparator", "value": 12.0}]}}}
    faelle, zusatz, _ = baue_faelle("lauf", "m", "v1", records, ohne_feld, docs, False, {})
    assert faelle[0]["klasse"] == 10
    assert len(zusatz) == 1

    richtig = {"r1": {"predicted": {"cells": [{"field": "intervention_mean", "arm": "intervention", "value": 10.0}]}}}
    faelle, zusatz, _ = baue_faelle("lauf", "m", "v1", records, richtig, docs, False, {})
    assert faelle == []
    assert zusatz == []


def test_pruefe_gold_meldet_fehlenden_wert_und_unmoegliche_ereignisse(tmp_path: Path) -> None:
    doc_path = tmp_path / "b.md"
    doc_path.write_text("Ereignisse 12 von 10 Teilnehmern.", encoding="utf-8")
    records = [
        _record(
            "r2",
            [
                ("intervention_events", "intervention", 12.0),
                ("intervention_group_size", "intervention", 10.0),
                ("comparator_mean", "comparator", 5.5),
            ],
            doc_path,
        )
    ]
    befunde = pruefe_gold(records, {"PMC1": Dokument(doc_path)})
    nach_feld = {b["field"]: b for b in befunde}
    assert nach_feld["intervention_events"]["braucht_pruefung"] is True
    assert "groesser als Gruppengroesse" in " ".join(nach_feld["intervention_events"]["probleme"])
    assert nach_feld["comparator_mean"]["braucht_pruefung"] is True
    assert "nicht wortwoertlich" in " ".join(nach_feld["comparator_mean"]["probleme"])


def test_baue_queue_priorisiert_ereignisse_vor_fehlenden_zellen() -> None:
    faelle = [
        {"run_id": "l", "prompt_version": "v2_timepoint", "model": "m", "record_id": "r1", "field": "intervention_mean", "arm": "intervention", "gold": 1.0, "prediction": "", "abs_error": "", "fall_typ": "fehlend", "klasse": 10, "klasse_name": "Zahl nicht extrahiert", "beleg": "", "pmcid": "PMC1", "quelle": "a.md"},
        {"run_id": "l", "prompt_version": "v2_timepoint", "model": "m", "record_id": "r2", "field": "intervention_events", "arm": "intervention", "gold": 12.0, "prediction": 120.0, "abs_error": 108.0, "fall_typ": "falsch", "klasse": 6, "klasse_name": "Ereignisse und Teilnehmer verwechselt", "beleg": "", "pmcid": "PMC1", "quelle": "a.md"},
    ]
    queue = baue_queue(faelle, [])
    assert queue[0]["prioritaet"] == 1
    assert queue[0]["record_id"] == "r2"
    assert queue[1]["prioritaet"] == 2
    assert all(eintrag["pruefstatus"] == "offen" for eintrag in queue)


def test_prozentklasse_fuer_191_zurueckgenommen() -> None:
    """48 ist die Ereigniszahl der 0-3-Monats-Zeile, nicht der Prozentwert.

    Die Belege gelten recordweit, nicht pro Lauf.
    """
    eintrag = GEPRUEFTE_FAELLE[("yun2024:191", "comparator_events", "comparator")]
    assert eintrag[0] == 1
    assert "Koinzidenz" in eintrag[1]
    partner = GEPRUEFTE_FAELLE[("yun2024:191", "intervention_events", "intervention")]
    assert partner[0] == 1
    assert "0-3 months" in partner[1]


def test_queue_traegt_status_je_version() -> None:
    fall = {
        "run_id": "l", "prompt_version": "v3_abs_count", "model": "m", "record_id": "r1",
        "field": "intervention_events", "arm": "intervention", "gold": 12.0, "prediction": 120.0,
        "abs_error": 108.0, "fall_typ": "falsch", "klasse": 6,
        "klasse_name": "Ereignisse und Teilnehmer verwechselt", "beleg": "", "pmcid": "PMC1", "quelle": "a.md",
    }
    queue = baue_queue([fall], [])
    assert queue[0]["status"] == "verworfen"
    referenz = {**fall, "prompt_version": "v6_target_fallback"}
    assert baue_queue([referenz], [])[0]["status"] == "referenz"
    alt = {**fall, "prompt_version": "v2_timepoint"}
    assert baue_queue([alt], [])[0]["status"] == "historisch"
