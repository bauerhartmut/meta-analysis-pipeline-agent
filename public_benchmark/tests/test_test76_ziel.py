"""Tests fuer die eingefrorene Testbasis der zweiten Kohorte.

Der SHA-256 haelt `records/yun_test76_ziel.jsonl` fest: Aendert sich ein
Goldwert, ein Zielzeitpunkt oder die Reihenfolge, schlaegt der Test fehl und
zwingt zu einer bewussten neuen Version samt neuem Hash im Bericht.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import evaluate_fallback  # noqa: E402

ZIEL = BENCH / "extended_benchmark" / "records" / "yun_test76_ziel.jsonl"
# Version 2 (16.11.2026): Gold von yun2024:479 korrigiert, siehe
# analysis/run186_20261115/error_analysis/korrektur_yun2024_479.md
SHA256 = "74fd0c057356c22831fae45d71644d8b7640a8a109fb48a60cc7782cfb1db704"
UNSICHER = {"yun2024:63", "yun2024:71", "yun2024:693", "yun2024:694"}


def lies() -> list[dict]:
    return [json.loads(line) for line in ZIEL.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_datei_hat_den_eingefrorenen_hash() -> None:
    assert hashlib.sha256(ZIEL.read_bytes()).hexdigest() == SHA256


def test_umfang_und_ziele() -> None:
    records = lies()
    assert len(records) == 76
    assert sum(len(r["gold"]["cells"]) for r in records) == 243
    assert [r["record_id"] for r in records if not r["timepoint"]["target"]] == []


def test_gold_von_479_ist_korrigiert() -> None:
    """Tabelle 4 druckt "1,922 / 1,919"; die Kommata sind Tausendertrenner."""
    record = next(r for r in lies() if r["record_id"] == "yun2024:479")
    werte = {c["field"]: c["value"] for c in record["gold"]["cells"]}
    assert werte["comparator_group_size"] == 1922
    assert werte["intervention_group_size"] == 1919
    assert werte["comparator_events"] == 976
    assert werte["intervention_events"] == 1078
    # Gegenprobe ueber die im Artikel berichteten Anteile (0.508 und 0.562).
    assert round(werte["comparator_events"] / werte["comparator_group_size"], 3) == 0.508
    assert round(werte["intervention_events"] / werte["intervention_group_size"], 3) == 0.562


def test_korrektur_ueberlebt_eine_neuerzeugung() -> None:
    """Die Korrektur steht im Annotationsskript, nicht nur in der Datei."""
    from extended_benchmark import annotate_test76

    assert annotate_test76.GOLD_KORREKTUREN["yun2024:479"]["comparator_group_size"] == 1922.0


def test_ziel_at_admission_ist_aufloesbar() -> None:
    """yun2024:71 traegt "at admission"; das ist der Baseline-Zeitpunkt."""
    record = next(r for r in lies() if r["record_id"] == "yun2024:71")
    ziel = record["timepoint"]["target"]
    assert ziel == "at admission"
    assert evaluate_fallback.klassifiziere(ziel, "baseline") == "zieltreu"
    assert evaluate_fallback.klassifiziere(ziel, "at admission") == "zieltreu"
    assert evaluate_fallback.klassifiziere(ziel, "month 6") == "rueckfall"


def test_abgeleitete_ziele_sind_als_unsicher_markiert() -> None:
    records = lies()
    markiert = {r["record_id"] for r in records if r["timepoint"].get("unsicher")}
    assert markiert == UNSICHER
    for record in records:
        if record["record_id"] in UNSICHER:
            assert record["timepoint"]["target"]
            assert record["timepoint"]["evidence"]
        else:
            assert not record["timepoint"].get("unsicher")


def _schreibe(path: Path, zeilen: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(z, ensure_ascii=False) for z in zeilen) + "\n", encoding="utf-8"
    )
    return path


def test_auswertung_weist_unsichere_ziele_getrennt_aus(tmp_path: Path, monkeypatch) -> None:
    zelle = {"field": "intervention_mean", "arm": "intervention", "value": 1.0}
    records = _schreibe(
        tmp_path / "records.jsonl",
        [
            {
                "record_id": "a",
                "document": {"split": "test", "path": ""},
                "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
                "timepoint": {"target": "week 24", "unsicher": True},
                "gold": {"cells": [dict(zelle)]},
            },
            {
                "record_id": "b",
                "document": {"split": "test", "path": ""},
                "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
                "timepoint": {"target": "week 24"},
                "gold": {"cells": [dict(zelle)]},
            },
        ],
    )
    _schreibe(
        tmp_path / "runs" / "t1" / "predictions.jsonl",
        [
            {
                "record_id": "a",
                "finish_reason": "stop",
                "fehlerklasse": "",
                "parse_error": "",
                "completion_tokens": 10,
                "rows": [dict(zelle, timepoint="24")],
                "predicted": {"cells": [dict(zelle, timepoint="24")]},
            },
            {
                "record_id": "b",
                "finish_reason": "stop",
                "fehlerklasse": "",
                "parse_error": "",
                "completion_tokens": 10,
                "rows": [dict(zelle, value=9.0, timepoint="24")],
                "predicted": {"cells": [dict(zelle, value=9.0, timepoint="24")]},
            },
        ],
    )
    ausgabe = tmp_path / "out.json"
    monkeypatch.setattr(evaluate_fallback, "HERE", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_fallback.py", "--run", "t1", "--records", str(records), "--out", str(ausgabe)],
    )
    assert evaluate_fallback.main() == 0
    ergebnis = json.loads(ausgabe.read_text(encoding="utf-8"))
    unsicher = ergebnis["unsichere_ziele"]
    assert unsicher["records"] == 1
    assert unsicher["zellen"] == 1
    assert unsicher["richtig"] == 1
    assert unsicher["beispiele"] == ["a"]
    # Die Hauptmetriken zaehlen weiter beide Records.
    assert ergebnis["zieltreu"]["richtig"] == 1
    assert ergebnis["zieltreu"]["falsch"] == 1
