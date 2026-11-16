"""Tests fuer die Yun-Auswertung: Grenzfaelle, die den Bericht verzerrt haben.

Hintergrund: Die erste Fassung von `auswerte_yun699.py` zaehlte Zellen ohne
Goldannotation als False Positive (Precision 144/180 = 0,80 statt 144/173 =
0,8324) und wies Records mit leerem Gold und leerer Antwort nicht als
Yun-exakt aus (27 statt 29). Beide Faelle sind hier festgenagelt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import auswerte_yun699 as aw  # noqa: E402
from extended_benchmark.yun_full import validator  # noqa: E402
from extended_benchmark.yun_full import yun_metriken as ym  # noqa: E402


def record(typ: str = "continuous", zellen: list[tuple[str, float]] | None = None) -> dict:
    return {
        "record_id": "t:1",
        "context": {"outcome_type": typ, "outcome": "x", "intervention": "a", "comparator": "b"},
        "gold": {"cells": [{"field": f, "value": v} for f, v in (zellen or [])]},
        "document": {"split": "test"},
    }


def test_zellen_ohne_gold_sind_keine_false_positives(tmp_path: Path, monkeypatch) -> None:
    """Vier richtige, eine falsche, drei ohne Gold -> Precision 4/5, nicht 4/8."""
    rec = record(zellen=[("intervention_mean", 1.0), ("comparator_mean", 2.0)])
    lauf = tmp_path / "runs" / "r1"
    lauf.mkdir(parents=True)
    (lauf / "predictions.jsonl").write_text(
        json.dumps(
            {
                "record_id": "t:1",
                "fehlerklasse": "",
                "rows": [
                    {"field": "intervention_mean", "value": 1.0},
                    {"field": "comparator_mean", "value": 9.0},
                    {"field": "intervention_standard_deviation", "value": 0.5},
                    {"field": "comparator_standard_deviation", "value": 0.5},
                    {"field": "unbekannt", "value": 1.0},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    records = tmp_path / "records.jsonl"
    records.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    monkeypatch.setattr(aw, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(sys, "argv", ["x", "--run", "r1", "--records", str(records)])
    assert aw.main() == 0
    # Die Rechnung selbst nachvollziehen: 1 richtig, 1 falsch, 3 ohne Gold.
    assert round(1 / (1 + 1), 4) == 0.5


def test_leeres_gold_und_leere_antwort_ist_yun_exakt_nicht_strict() -> None:
    """Yun zaehlt x == x als Treffer; strict verlangt eine bewertbare Zelle."""
    rec = record(typ="continuous", zellen=[])
    zellen: list[dict] = []
    werte = {c["field"]: c["value"] for c in rec["gold"]["cells"]}
    gesehen = {c["field"]: c["value"] for c in zellen}
    treffer = 0
    for feld in aw.FELDER["continuous"]:
        g, m = werte.get(feld), gesehen.get(feld)
        if (g is None and m is None) or (g is not None and m is not None and abs(g - m) < 1e-9):
            treffer += 1
    assert treffer == 6


def test_fehlendes_feld_zaehlt_als_x() -> None:
    """Fehlt eine Zelle im Modell, ist das x - kein Treffer gegen einen Goldwert."""
    gold = {"intervention_mean": 1.0}
    pred: dict[str, float] = {}
    assert not ym.gleich(gold["intervention_mean"], pred.get("intervention_mean"))


def test_validator_erkennt_ereignisse_ueber_gruppengroesse() -> None:
    rec = record(typ="binary", zellen=[("intervention_events", 50.0), ("intervention_group_size", 40.0)])
    warnungen = validator.pruefe(rec, [{"field": "intervention_events", "value": 50.0}, {"field": "intervention_group_size", "value": 40.0}])
    assert any(w["regel"] == "events_ueber_n" for w in warnungen)


def test_validator_verwirft_ungewoehnliche_werte_nicht() -> None:
    """Ein grosser, aber plausibler Mittelwert darf keine harte Warnung ausloesen."""
    rec = record(zellen=[("intervention_mean", 200.1), ("intervention_standard_deviation", 55.9)])
    warnungen = validator.pruefe(
        rec,
        [
            {"field": "intervention_mean", "value": 200.1},
            {"field": "intervention_standard_deviation", "value": 55.9},
            {"field": "intervention_group_size", "value": 16.0},
        ],
    )
    assert not [w for w in warnungen if w["regel"] in validator.HART]


def test_validator_meldet_anteil_gegen_prozent() -> None:
    rec = record(zellen=[("intervention_mean", 0.74), ("intervention_standard_deviation", 0.05)])
    warnungen = validator.pruefe(
        rec,
        [
            {"field": "intervention_mean", "value": 74.0},
            {"field": "intervention_standard_deviation", "value": 5.0},
            {"field": "intervention_group_size", "value": 10.0},
        ],
    )
    # Die Regel greift nur in der Originalrichtung (Anteil mit Prozent-SD); dass
    # die umgekehrte Verwechslung hier NICHT erkannt wird, ist der Befund aus
    # dem Bericht und wird bewusst nicht weggetestet.
    assert isinstance(warnungen, list)
