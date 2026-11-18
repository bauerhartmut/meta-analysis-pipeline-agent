"""Echter Abbruchtest: ein Subprozess beendet sich mit `os._exit` mitten im Lauf.

Der Unterschied zum nachgestellten Fall in `test_run_extended_extraction.py`:
hier laeuft der echte Harness in einem eigenen Prozess, schreibt eine Zeile,
beginnt den zweiten Auftrag und stirbt dann hart. Damit bleiben genau die
Zustaende stehen, die ein Absturz hinterlaesst — inklusive der Sperre, deren
`finally` nie gelaufen ist.

Der zweite Prozess muss den Auftrag nachholen, den ersten ueberspringen und die
Sperre uebernehmen; am Ende steht genau eine Zeile je Auftrag.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]

#: Kindprozess: echter Harness, gefaelschter Aufruf, harter Abbruch nach n Aufrufen.
SKRIPT = '''
import json
import os
import sys
from pathlib import Path

bench, lauf, records, grenze, strategie = sys.argv[1:6]
sys.path.insert(0, bench)
from extended_benchmark import run_extended_extraction as runner

runner.HERE = Path(lauf)
zaehler = {"n": 0}


def fake_call(model, prompt, key, base, attempts=4, **kwargs):
    zaehler["n"] += 1
    if zaehler["n"] > int(grenze):
        os._exit(1)  # harter Abbruch: kein finally, kein Flush
    return {
        "http_status": 200,
        "content": json.dumps({"cells": [{"field": "intervention_mean",
                                          "arm": "intervention", "value": 1.0}]}),
        "finish_reason": "stop",
        "completion_tokens": 20,
        "elapsed_s": 1.0,
        "error": "",
    }


def fake_config():
    return type("Cfg", (), {"tudagpt_api_key": "test",
                            "tudagpt_api_base": "http://127.0.0.1:9"})()


runner.get_config = fake_config
runner.call = fake_call
sys.argv = [
    "runner", "--records", records, "--split", "", "--ids", "yun2024:1,yun2024:2",
    "--models", "glm", "--run-id", "t1", "--workers", "1", "--target-fallback",
    "--retry-strategie", strategie,
]
raise SystemExit(runner.main())
'''


def _lauf(tmp_path: Path, grenze: int, strategie: str = "neu") -> subprocess.CompletedProcess:
    skript = tmp_path / "kind.py"
    skript.write_text(SKRIPT, encoding="utf-8")
    records = tmp_path / "rec.jsonl"
    if not records.exists():
        zeilen = [
            {
                "record_id": f"yun2024:{nummer}",
                "document": {"split": "test", "path": ""},
                "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
                "gold": {"cells": []},
                "timepoint": {"target": "week 24"},
            }
            for nummer in (1, 2)
        ]
        records.write_text("\n".join(json.dumps(z) for z in zeilen) + "\n", encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(skript), str(BENCH), str(tmp_path), str(records), str(grenze), strategie],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def _zeilen(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def test_absturz_hinterlaesst_zeile_journal_und_sperre(tmp_path: Path) -> None:
    erster = _lauf(tmp_path, grenze=1)
    assert erster.returncode == 1  # os._exit
    lauf = tmp_path / "runs" / "t1"

    zeilen = _zeilen(lauf / "predictions.jsonl")
    assert len(zeilen) == 1  # der erste Auftrag war fertig
    assert zeilen[0]["record_id"] == "yun2024:1"

    status = [z["status"] for z in _zeilen(lauf / "jobs.jsonl")]
    assert status == ["running", "completed", "running"]  # zweiter Auftrag offen
    assert (lauf / "harness.lock").exists()  # das finally lief nie


def test_zweiter_prozess_holt_nach_und_verdoppelt_nichts(tmp_path: Path) -> None:
    assert _lauf(tmp_path, grenze=1).returncode == 1
    zweiter = _lauf(tmp_path, grenze=99)
    assert zweiter.returncode == 0, zweiter.stderr
    assert "unterbrochen" in zweiter.stdout  # der Replay hat den Rest gemeldet
    lauf = tmp_path / "runs" / "t1"

    zeilen = _zeilen(lauf / "predictions.jsonl")
    schluessel = [(z["record_id"], z["model"]) for z in zeilen]
    assert schluessel == [("yun2024:1", "glm"), ("yun2024:2", "glm")]  # je genau einmal
    assert not (lauf / "harness.lock").exists()  # diesmal freigegeben

    journal = _zeilen(lauf / "jobs.jsonl")
    assert journal[-1]["status"] == "completed"
    assert [z["record_id"] for z in journal if z["status"] == "running"] == [
        "yun2024:1",
        "yun2024:2",
        "yun2024:2",
    ]
    offen = [z for z in journal if z["record_id"] == "yun2024:2"]
    assert offen[-1]["status"] == "completed"


def test_absturz_unter_alt_legt_kein_journal_an(tmp_path: Path) -> None:
    assert _lauf(tmp_path, grenze=1, strategie="alt").returncode == 1
    lauf = tmp_path / "runs" / "t1"
    assert not (lauf / "jobs.jsonl").exists()
    assert not (lauf / "harness.lock").exists()
