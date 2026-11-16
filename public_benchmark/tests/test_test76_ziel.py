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
# Version 3 (16.11.2026): Comparator von 289-295 auf "treatment as usual (TAU)"
# und zwei Goldzellen (291 SD, 294 Komparator) korrigiert, siehe
# analysis/run186_20261115/error_analysis/korrektur_v3_comparator.md
SHA256 = "3f811bed35653bda0da92a5ab13dc16a13a23dfc79c04a0808b0d2ec8267b587"
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


def test_comparator_von_289_bis_295_ist_tau() -> None:
    """PMC4215531 randomisiert auf FAT, CE und TAU; einen Arm "baseline" gibt es nicht."""
    records = lies()
    mccb = [r for r in records if r["record_id"] in {f"yun2024:{n}" for n in range(289, 296)}]
    assert len(mccb) == 7
    assert {r["context"]["comparator"] for r in mccb} == {"treatment as usual (TAU)"}
    # Die Zielangabe bleibt der Post-Zeitpunkt; das Gold vergleicht FAT gegen TAU.
    assert {r["timepoint"]["target"] for r in mccb} == {"post (after 4-week training)"}


def test_gold_zellen_von_291_und_294_sind_korrigiert() -> None:
    """291: SD aus der Post-Zeile (14.0) statt aus Pre (12.8); 294: Reasoning-Spalte."""
    werte291 = {c["field"]: c["value"] for c in next(r for r in lies() if r["record_id"] == "yun2024:291")["gold"]["cells"]}
    assert werte291["intervention_mean"] == 49.4
    assert werte291["intervention_standard_deviation"] == 14.0
    assert werte291["comparator_mean"] == 46.5
    werte294 = {c["field"]: c["value"] for c in next(r for r in lies() if r["record_id"] == "yun2024:294")["gold"]["cells"]}
    assert werte294["intervention_mean"] == 47.9
    assert werte294["comparator_mean"] == 45.4
    assert werte294["comparator_standard_deviation"] == 7.7


def test_korrekturen_ueberleben_eine_neuerzeugung() -> None:
    """Beide Korrekturarten stehen im Annotationsskript, nicht nur in der Datei."""
    from extended_benchmark import annotate_test76

    assert annotate_test76.GOLD_KORREKTUREN["yun2024:291"]["intervention_standard_deviation"] == 14.0
    assert annotate_test76.GOLD_KORREKTUREN["yun2024:294"]["comparator_mean"] == 45.4
    for nummer in range(289, 296):
        assert annotate_test76.KONTEXT_KORREKTUREN[f"yun2024:{nummer}"] == {
            "comparator": "treatment as usual (TAU)"
        }


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
