"""Tests fuer die Aufloesbarkeitspruefung: reine Funktionen, keine echten Laeufe."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import pruefe_aufloesbarkeit as pa  # noqa: E402


def _record(rid: str, pfad: str, zellen: int) -> dict:
    return {
        "record_id": rid,
        "document": {"path": pfad},
        "gold": {"cells": [{"field": "x"}] * zellen},
    }


def test_index_nimmt_die_erste_quelle(tmp_path: Path) -> None:
    erste = tmp_path / "a.jsonl"
    zweite = tmp_path / "b.jsonl"
    erste.write_text(json.dumps(_record("r1", "d1.md", 1)) + "\n", encoding="utf-8")
    zweite.write_text(
        json.dumps(_record("r1", "d2.md", 9)) + "\n" + json.dumps(_record("r2", "d2.md", 2)) + "\n",
        encoding="utf-8",
    )
    gefunden = pa.index([erste, zweite])
    assert gefunden["r1"][0] == erste
    assert gefunden["r1"][1]["gold"]["cells"] == [{"field": "x"}]
    assert gefunden["r2"][0] == zweite


def test_pruefe_trennt_ausfall_und_erfolg(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pa, "REPO", tmp_path)
    (tmp_path / "doc.md").write_text("text", encoding="utf-8")
    direkt = {"a": (Path("records/yun.jsonl"), _record("a", "doc.md", 4))}
    zusatz = {"b": (Path("yun699.jsonl"), _record("b", "fehlt.md", 0))}
    zeilen = [
        {"record_id": "a", "fehlerklasse": "length_ohne_ergebnis"},
        {"record_id": "b", "fehlerklasse": "length_ohne_ergebnis"},
        {"record_id": "c", "fehlerklasse": ""},
    ]

    ergebnis = pa.pruefe(zeilen, direkt, zusatz)

    ausfall = ergebnis["ausfall"]
    assert ausfall["zeilen"] == 2
    assert ausfall["in_records"] == 1
    assert ausfall["nur_in_zusatzquelle"] == 1
    assert ausfall["gar_nicht_gefunden"] == 0
    assert ausfall["ohne_dokumentdatei"] == 1  # b zeigt auf fehlt.md
    assert ausfall["ohne_goldzellen"] == 1  # b hat keine Zellen
    assert ausfall["goldzellen"] == 4
    assert ausfall["beispiele_ohne_gold"] == ["b"]

    erfolg = ergebnis["erfolg"]
    assert erfolg["zeilen"] == 1
    assert erfolg["gar_nicht_gefunden"] == 1  # c steht in keiner Quelle
    assert erfolg["in_records"] == 0


def test_pruefe_zaehlt_nur_bewertbare_goldzellen(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pa, "REPO", tmp_path)
    (tmp_path / "doc.md").write_text("text", encoding="utf-8")
    direkt = {
        "a": (Path("r.jsonl"), _record("a", "doc.md", 4)),
        "b": (Path("r.jsonl"), _record("b", "doc.md", 0)),
    }
    ergebnis = pa.pruefe(
        [{"record_id": "a", "fehlerklasse": "length_ohne_ergebnis"},
         {"record_id": "b", "fehlerklasse": "length_ohne_ergebnis"}],
        direkt,
        {},
    )
    assert ergebnis["ausfall"]["ohne_goldzellen"] == 1
    assert ergebnis["ausfall"]["goldzellen"] == 4
