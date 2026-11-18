"""Tests fuer die P5-Vorbereitung: reine Auswahl, kein Netzlauf."""

from __future__ import annotations

import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import bereite_p5_vor as p5  # noqa: E402


def _zeile(rid: str, klasse: str, modell: str = "glm") -> dict:
    return {"record_id": rid, "model": modell, "fehlerklasse": klasse}


def _record(rid: str, zellen: int, pfad: str = "doc.md") -> dict:
    return {"record_id": rid, "document": {"path": pfad}, "gold": {"cells": [{"f": 1}] * zellen}}


def test_baue_trennt_bewertbar_und_nicht(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(p5, "REPO", tmp_path)
    (tmp_path / "doc.md").write_text("text", encoding="utf-8")
    records = {"a": _record("a", 2), "b": _record("b", 0)}
    zeilen = [
        _zeile("a", "length_ohne_ergebnis"),
        _zeile("b", "length_ohne_ergebnis"),
        _zeile("c", "json_kaputt"),  # der Timeout-Fall gehoert nicht dazu
        _zeile("d", "length_ohne_ergebnis", modell="qwen30"),  # anderes Modell
    ]

    werte = p5.baue(zeilen, records)

    assert werte["ausfaelle"] == 2
    assert [e["record_id"] for e in werte["bewertbar"]] == ["a"]
    assert werte["nicht_bewertbar"] == [
        {"record_id": "b", "goldzellen": 0, "grund": "keine Goldzellen"}
    ]
    assert werte["goldzellen_bewertbar"] == 2
    assert werte["in_records_datei_fehlt"] == []
    assert werte["ohne_dokumentdatei"] == []


def test_baue_meldet_fehlende_records_und_dokumente(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(p5, "REPO", tmp_path)
    records = {"a": _record("a", 2, pfad="gibt_es_nicht.md")}
    werte = p5.baue([_zeile("a", "length_ohne_ergebnis"), _zeile("x", "length_ohne_ergebnis")], records)
    assert werte["ohne_dokumentdatei"] == ["a"]
    assert werte["in_records_datei_fehlt"] == ["x"]


def test_befehl_enthaelt_budget_und_ids(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(p5, "REPO", tmp_path)
    (tmp_path / "doc.md").write_text("text", encoding="utf-8")
    werte = p5.baue([_zeile("a", "length_ohne_ergebnis")], {"a": _record("a", 2)})
    befehl = werte["befehl"]
    assert "--max-tokens 24000" in befehl
    assert "--retry-strategie neu" in befehl
    assert "--ids yun2024" not in befehl  # die Ids sind echte record_ids
    assert befehl.endswith("--quelle p5_24000")
