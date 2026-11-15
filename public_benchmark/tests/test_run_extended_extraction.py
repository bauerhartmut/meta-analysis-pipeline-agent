"""Tests fuer Prompt-Versionen im Extraktionsrunner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark import run_extended_extraction as runner  # noqa: E402

RECORD = {"context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "binary"}}


def test_standardversion_ist_v2_timepoint() -> None:
    assert runner.PROMPT_VERSION == "v2_timepoint"
    assert runner.VERSION_ABSOLUTE_COUNTS == "v3_abs_count"


def test_standardprompt_ohne_absolute_counts_zusatz() -> None:
    prompt = runner.build_prompt(RECORD, "Text")
    assert "post-test" in prompt
    assert "never as percentages" not in prompt


def test_records_option_liest_andere_datei(tmp_path: Path) -> None:
    datei = tmp_path / "teil.jsonl"
    zeilen = [
        {"record_id": "yun2024:1", "document": {"split": "test"}},
        {"record_id": "yun2024:2", "document": {"split": "dev"}},
        {"record_id": "yun2024:3", "document": {"split": "test"}},
    ]
    datei.write_text("\n".join(json.dumps(z) for z in zeilen) + "\n", encoding="utf-8")

    alle = runner.load_records(None, None, path=datei)
    assert [r["record_id"] for r in alle] == ["yun2024:1", "yun2024:2", "yun2024:3"]
    assert [r["record_id"] for r in runner.load_records("test", None, path=datei)] == [
        "yun2024:1",
        "yun2024:3",
    ]
    # Ohne path bleibt der Standardpfad aktiv.
    assert runner.load_records(None, None) == runner.load_records(None, None, path=runner.RECORDS)


def test_ids_waehlen_aus_der_alternativen_datei(tmp_path: Path) -> None:
    datei = tmp_path / "teil.jsonl"
    zeilen = [
        {"record_id": f"yun2024:{i}", "document": {"split": "test"}} for i in (1, 2, 3)
    ]
    datei.write_text("\n".join(json.dumps(z) for z in zeilen) + "\n", encoding="utf-8")

    auswahl = runner.waehle_records(runner.load_records("test", None, path=datei), "yun2024:1, yun2024:3")
    assert [r["record_id"] for r in auswahl] == ["yun2024:1", "yun2024:3"]
    # Unbekannte IDs werden ignoriert, leere Auswahl bleibt unveraendert.
    assert runner.waehle_records(runner.load_records("test", None, path=datei), "yun2024:99") == []
    assert len(runner.waehle_records(runner.load_records("test", None, path=datei), None)) == 3


def test_record_ohne_ziel_laeuft_als_v2_timepoint() -> None:
    ohne = {"timepoint": {"target": ""}}
    mit = {"timepoint": {"target": "week 24"}}
    assert runner.bestimme_version(fallback=True, target=ohne["timepoint"]["target"]) == "v2_timepoint"
    assert runner.bestimme_version(fallback=True, target=mit["timepoint"]["target"]) == "v6_target_fallback"


def test_flag_schaltet_absolute_counts_zu() -> None:
    prompt = runner.build_prompt(RECORD, "Text", absolute_counts=True)
    assert "never as percentages" in prompt
    assert "post-test" in prompt


def test_letzter_zeitpunkt_ersetzt_die_zeitpunktregel() -> None:
    prompt = runner.build_prompt(RECORD, "Text", last_timepoint=True)
    assert runner.VERSION_LAST_TIMEPOINT == "v4_last_timepoint"
    assert "last time point reported" in prompt
    assert "chosen_timepoint" in prompt and "discarded_timepoints" in prompt
    assert "post-test" not in prompt


def test_zielzeitpunkt_ist_verbindlich() -> None:
    prompt = runner.build_prompt(RECORD, "Text", target_timepoint="Post-test")
    assert runner.VERSION_TARGET_TIMEPOINT == "v5_target_timepoint"
    assert 'Target time point (binding): "Post-test"' in prompt
    assert "omit the cell instead of substituting" in prompt
    assert "chosen_timepoint" in prompt and "discarded_timepoints" in prompt
    assert "post-test" not in prompt


def test_rueckfallregel_mit_zelleigenem_zeitpunkt() -> None:
    prompt = runner.build_prompt(RECORD, "Text", target_timepoint="Post-test", fallback=True)
    assert runner.VERSION_TARGET_FALLBACK == "v6_target_fallback"
    assert "closest reported time point" in prompt
    assert '"timepoint": "<label exactly as printed>"' in prompt
    cells, error = runner.parse_cells(
        '{"cells": [{"field": "intervention_mean", "arm": "intervention", "value": 1.5, '
        '"timepoint": "Post-test"}]}'
    )
    assert error == ""
    assert cells == [{"field": "intervention_mean", "arm": "intervention", "value": 1.5, "timepoint": "Post-test"}]


def test_zeitpunkt_parser_liest_labels() -> None:
    timepoints, error = runner.parse_timepoints(
        '{"cells": [], "chosen_timepoint": "12 months follow-up", '
        '"discarded_timepoints": ["Baseline", "3 months follow-up"]}'
    )
    assert error == ""
    assert timepoints == {"chosen": "12 months follow-up", "discarded": ["Baseline", "3 months follow-up"]}
    leer, fehler = runner.parse_timepoints('{"cells": []}')
    assert leer["chosen"] == "" and fehler == "kein_zeitpunkt"
    assert runner.parse_timepoints("keine antwort")[1] == "kein_json"
