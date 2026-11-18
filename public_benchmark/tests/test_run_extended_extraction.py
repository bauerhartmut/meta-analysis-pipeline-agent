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


def _auftrag(tmp_path: Path, monkeypatch, antworten: list[dict], extra: list[str] | None = None) -> tuple[list[str], dict]:
    """Fuehrt main() mit gefaelschtem API-Aufruf aus; gibt (aufrufe, zeile)."""
    datei = tmp_path / "rec.jsonl"
    record = {
        "record_id": "yun2024:1",
        "document": {"split": "test", "path": ""},
        "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "binary"},
        "gold": {"cells": []},
        "timepoint": {"target": "week 24"},
    }
    datei.write_text(json.dumps(record) + "\n", encoding="utf-8")
    aufrufe: list[str] = []

    def fake_call(model, prompt, key, base, attempts=4):
        aufrufe.append(dict(model))
        return antworten[min(len(aufrufe) - 1, len(antworten) - 1)]

    monkeypatch.setattr(runner, "call", fake_call)
    monkeypatch.setattr(runner, "HERE", tmp_path)
    monkeypatch.setattr(
        runner, "get_config", lambda: type("Cfg", (), {"tudagpt_api_key": "test", "tudagpt_api_base": "http://x"})()
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner", "--records", str(datei), "--split", "test", "--ids", "yun2024:1",
         "--models", "glm", "--run-id", "t1", "--target-fallback", *(extra or [])],
    )
    assert runner.main() == 0
    zeile = json.loads((tmp_path / "runs" / "t1" / "predictions.jsonl").read_text(encoding="utf-8").splitlines()[0])
    return aufrufe, zeile


def test_length_loest_keinen_zweiten_api_aufruf_aus(tmp_path: Path, monkeypatch) -> None:
    lang = {
        "http_status": 200, "content": "", "finish_reason": "length",
        "completion_tokens": 24000, "elapsed_s": 1.0, "error": "",
    }
    aufrufe, zeile = _auftrag(tmp_path, monkeypatch, [lang])
    assert len(aufrufe) == 1, aufrufe
    assert zeile["fehlerklasse"] == "length_ohne_ergebnis"
    assert zeile["failed"] is True
    assert zeile["rows"] == []
    assert zeile["retried"] is False


def test_kaputtes_json_bekommt_genau_einen_zweiten_aufruf(tmp_path: Path, monkeypatch) -> None:
    kaputt = {
        "http_status": 200, "content": "kein json", "finish_reason": "stop",
        "completion_tokens": 900, "elapsed_s": 1.0, "error": "",
    }
    gut = {
        "http_status": 200,
        "content": json.dumps({"cells": [{"field": "intervention_mean", "arm": "intervention", "value": 1.5, "timepoint": "24"}],
                              "chosen_timepoint": "24", "discarded_timepoints": ["0"]}),
        "finish_reason": "stop", "completion_tokens": 800, "elapsed_s": 1.0, "error": "",
    }
    aufrufe, zeile = _auftrag(tmp_path, monkeypatch, [kaputt, gut])
    assert len(aufrufe) == 2, aufrufe
    assert zeile["fehlerklasse"] == ""
    assert zeile["retry_grund"] == "json"
    assert len(zeile["rows"]) == 1


def test_repair_fasst_nur_nach_length_nach_und_mit_kleinem_budget(tmp_path: Path, monkeypatch) -> None:
    lang = {
        "http_status": 200, "content": "", "finish_reason": "length",
        "completion_tokens": 19000, "elapsed_s": 1.0, "error": "",
    }
    reparatur = {
        "http_status": 200,
        "content": json.dumps({"timepoint": "24", "cells": [{"field": "intervention_mean", "arm": "intervention", "value": 13.72}]}),
        "finish_reason": "stop", "completion_tokens": 900, "elapsed_s": 1.0, "error": "",
    }
    aufrufe, zeile = _auftrag(tmp_path, monkeypatch, [lang, reparatur], extra=["--repair", "--cell-timepoint"])
    assert len(aufrufe) == 2
    assert aufrufe[0]["max_tokens"] == 24000  # erster Aufruf unveraendert
    assert aufrufe[1]["max_tokens"] == runner.REPAIR_MAX_TOKENS == 6000
    assert zeile["pfad"] == "repair"
    assert zeile["repair_tokens"] == 900
    assert zeile["fehlerklasse"] == ""  # Reparatur liefert Zellen
    # Seit 586dd18 zaehlen `content_len` und `content_chars` den wirksamen Text,
    # also die Reparaturantwort — dieselbe, aus der die Zellen stammen.
    assert zeile["content_len"] == zeile["content_chars"] == len(zeile["content"])
    assert len(zeile["rows"]) == 1
    assert zeile["rows"][0]["timepoint"] == "24"


def test_ohne_repair_flag_bleibt_es_bei_einem_aufruf(tmp_path: Path, monkeypatch) -> None:
    lang = {
        "http_status": 200, "content": "", "finish_reason": "length",
        "completion_tokens": 19000, "elapsed_s": 1.0, "error": "",
    }
    aufrufe, zeile = _auftrag(tmp_path, monkeypatch, [lang])
    assert len(aufrufe) == 1
    assert zeile["pfad"] == "standard"
    assert zeile["fehlerklasse"] == "length_ohne_ergebnis"


def test_erfolglose_reparatur_bleibt_fehlzeile(tmp_path: Path, monkeypatch) -> None:
    lang = {
        "http_status": 200, "content": "", "finish_reason": "length",
        "completion_tokens": 19000, "elapsed_s": 1.0, "error": "",
    }
    defekt = {**lang, "completion_tokens": 6000}
    aufrufe, zeile = _auftrag(tmp_path, monkeypatch, [lang, defekt], extra=["--repair"])
    assert len(aufrufe) == 2
    assert zeile["pfad"] == "repair"
    assert zeile["repair_fehlerklasse"] == "length_ohne_ergebnis"
    assert zeile["fehlerklasse"] == "length_ohne_ergebnis"
    assert zeile["rows"] == []


def test_v7_prompt_nimmt_gruppengroessen_von_der_zeitpunktregel_aus() -> None:
    record = {
        "record_id": "yun2024:1",
        "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
    }
    prompt = runner.build_prompt(
        record, "Text", target_timepoint="baseline", fallback=True, cell_timepoint=True, group_size_mode="lang"
    )
    assert "Group sizes (*_group_size) are arm characteristics" in prompt
    assert "exempt from the one-time-point rule" in prompt
    # Der Reparaturprompt sagt dasselbe knapper.
    kurz = runner._prompt_repair(record, "Text", "baseline")
    assert "need no timepoint" in kurz
    assert "smallest possible answer" in kurz


def test_gruppenzeile_ist_opt_in_und_hat_drei_fassungen() -> None:
    record = {
        "record_id": "yun2024:1",
        "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
    }

    def prompt(modus: str) -> str:
        return runner.build_prompt(
            record, "Text", target_timepoint="baseline", cell_timepoint=True, group_size_mode=modus
        )

    aus, lang, kurz = prompt("aus"), prompt("lang"), prompt("kurz")
    # Standard ist aus: ohne Angabe keine Zeile.
    assert prompt("aus") == runner.build_prompt(record, "Text", target_timepoint="baseline", cell_timepoint=True)
    assert runner.GROUP_SIZE_TEXTE["lang"] not in aus
    assert runner.GROUP_SIZE_TEXTE["kurz"] not in aus
    assert "arm characteristics" in lang and "exempt from the one-time-point rule" in lang
    assert "Report group sizes as intervention_group_size" in kurz
    assert "arm characteristics" not in kurz
    assert len(lang) > len(kurz) > len(aus)
    assert "Never report an outcome value without naming the time point" in aus


def test_ohne_records_und_ids_startet_kein_lauf(tmp_path: Path, monkeypatch, capsys) -> None:
    """Ein Lauf braucht --records oder --ids; sonst bricht er vor jedem API-Zugriff ab."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner", "--split", "test", "--models", "glm", "--run-id", "t1"],
    )
    # Der Abbruch steht vor jedem API-Zugriff: kein Schluessel, kein Aufruf, kein Lauf.
    monkeypatch.setattr(
        runner, "get_config", lambda: (_ for _ in ()).throw(AssertionError("get_config darf nicht laufen"))
    )
    assert runner.main() == 2
    assert "ohne --records oder --ids" in capsys.readouterr().out
    assert not (tmp_path / "runs").exists()


def test_ids_allein_reicht_als_auswahl(tmp_path: Path, monkeypatch) -> None:
    """--ids ohne --records ist erlaubt: die Standarddatei wird dann gefiltert."""
    monkeypatch.setattr(
        runner,
        "load_records",
        lambda split, limit, path=None: [
            {
                "record_id": "yun2024:1",
                "document": {"split": "test", "path": ""},
                "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
                "gold": {"cells": []},
                "timepoint": {"target": "week 24"},
            }
        ],
    )
    monkeypatch.setattr(runner, "HERE", tmp_path)
    monkeypatch.setattr(
        runner, "call", lambda model, prompt, key, base, attempts=4: {
            "http_status": 200, "content": '{"timepoint": "week 24", "cells": []}', "completion_tokens": 1,
            "finish_reason": "stop", "error": "",
        }
    )
    monkeypatch.setattr(
        runner, "get_config", lambda: type("Cfg", (), {"tudagpt_api_key": "test", "tudagpt_api_base": "http://x"})()
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner", "--split", "test", "--models", "glm", "--run-id", "t2",
         "--ids", "yun2024:1", "--target-fallback"],
    )
    assert runner.main() == 0
    assert (tmp_path / "runs" / "t2" / "predictions.jsonl").exists()


def test_v7_hat_eigene_version_und_zeitpunkt_je_antwort() -> None:
    assert runner.bestimme_version(cell_timepoint=True, target="week 24") == "v7_zellzeitpunkt"
    # Ohne Ziel bleibt es beim alten Etikett: der Prompt braucht den Zeitpunkt.
    assert runner.bestimme_version(cell_timepoint=True, target="") == runner.PROMPT_VERSION
    # v6-Zeilen behalten ihr Etikett.
    assert runner.bestimme_version(fallback=True, target="week 24") == "v6_target_fallback"


def test_v7_prompt_verlangt_json_zuerst_und_einen_zeitpunkt() -> None:
    record = {
        "record_id": "yun2024:1",
        "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "binary"},
    }
    prompt = runner.build_prompt(record, "Text", target_timepoint="week 24", fallback=True, cell_timepoint=True)
    assert "Return the JSON object first" in prompt
    assert "One time point for BOTH arms" in prompt
    assert "timepoint_header" in prompt
    # Kein Zeitpunktfeld je Zelle mehr.
    assert '"timepoint": "<label exactly as printed>"}' not in prompt
    v6 = runner.build_prompt(record, "Text", target_timepoint="week 24", fallback=True)
    assert "closest reported time point" in v6


def test_v7_zeile_parst_zeitpunkt_und_header(tmp_path: Path, monkeypatch) -> None:
    antwort = {
        "http_status": 200,
        "content": json.dumps(
            {
                "timepoint": "24",
                "timepoint_header": "Week 24",
                "fallback": False,
                "cells": [{"field": "intervention_mean", "arm": "intervention", "value": 13.72}],
            }
        ),
        "finish_reason": "stop",
        "completion_tokens": 900,
        "elapsed_s": 1.0,
        "error": "",
    }
    aufrufe, zeile = _auftrag(tmp_path, monkeypatch, [antwort], extra=["--cell-timepoint"])
    assert len(aufrufe) == 1
    assert zeile["prompt_version"] == "v7_zellzeitpunkt"
    assert zeile["schema_version"] == "v7_zellzeitpunkt"
    assert zeile["timepoint_header"] == "Week 24"
    assert zeile["fallback"] is False
    # Der Zeitpunkt wird auf die Zellen verteilt, damit die Auswertung gleich liest.
    assert zeile["rows"][0]["timepoint"] == "24"
    assert zeile["timepoints"]["chosen"] == "24"


def test_length_bekommt_keinen_zweiten_versuch(tmp_path: Path) -> None:
    # Reasoning-Schleife: eindeutige Fehlzeile statt Retry mit groesserem Budget.
    assert runner.fehlerklasse_aus({"finish_reason": "length"}, "") == "length_ohne_ergebnis"
    # Kaputtes JSON bleibt ein Retry-Fall (Format, keine Endlosschleife).
    assert runner.fehlerklasse_aus({"finish_reason": "stop"}, "kein_json") == "json_kaputt"
    assert runner.fehlerklasse_aus({"finish_reason": "stop"}, "json_fehler: x") == "json_kaputt"
    # Verwertbare Antwort ist keine Fehlzeile.
    assert runner.fehlerklasse_aus({"finish_reason": "stop"}, "") == ""


def test_fehlzeile_ist_im_datensatz_erkennbar() -> None:
    # Die Zeile traegt Klassenname und Flag; "rows" bleibt leer.
    zeile = {"record_id": "yun2024:159", "model": "glm", "rows": [], "fehlerklasse": "length_ohne_ergebnis"}
    assert zeile["fehlerklasse"] and zeile["rows"] == []
    assert bool(zeile.get("fehlerklasse")) is True


def test_fortsetzen_ueberspringt_erfolgreiche_und_fehlzeilen(tmp_path: Path) -> None:
    datei = tmp_path / "predictions.jsonl"
    zeilen = [
        {"record_id": "a", "model": "glm", "rows": [{"field": "x"}], "fehlerklasse": ""},
        {"record_id": "b", "model": "glm", "rows": [], "fehlerklasse": "length_ohne_ergebnis"},
        {"record_id": "c", "model": "glm", "rows": [], "fehlerklasse": "json_kaputt"},
    ]
    datei.write_text("\n".join(json.dumps(z) for z in zeilen) + "\n", encoding="utf-8")

    # Standard: nichts wird erneut verarbeitet (auch keine Fehlzeile — sonst
    # wuerde dieselbe Endlosschleife erneut bezahlt).
    assert runner.done_keys(datei) == {("a", "glm"), ("b", "glm"), ("c", "glm")}
    # Gezielte Wiederholung bleibt moeglich.
    assert runner.done_keys(datei, retry_failed=True) == {("a", "glm")}


def test_kaputtes_json_zaehlt_nicht_als_erfolg() -> None:
    cells, fehler = runner.parse_cells("das ist kein json")
    assert cells == []
    assert runner.fehlerklasse_aus({"finish_reason": "stop"}, fehler) == "json_kaputt"


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


def _timeout_antwort() -> dict:
    return {
        "http_status": 0,
        "content": "",
        "finish_reason": "",
        "completion_tokens": None,
        "elapsed_s": 300.03,
        "error": "TimeoutError: The read operation timed out",
    }


def test_standardstrategie_schreibt_keine_neuen_felder(tmp_path: Path, monkeypatch) -> None:
    # Ohne Schalter bleibt die Zeile wie bisher: kein `attempts`, kein `job_status`.
    lang = {
        "http_status": 200, "content": "", "finish_reason": "length",
        "completion_tokens": 24000, "elapsed_s": 1.0, "error": "",
    }
    _, zeile = _auftrag(tmp_path, monkeypatch, [lang])
    assert "attempts" not in zeile
    assert "job_status" not in zeile


def test_neue_strategie_schreibt_versuchsspur(tmp_path: Path, monkeypatch) -> None:
    lang = {
        "http_status": 200, "content": "", "finish_reason": "length",
        "completion_tokens": 8000, "reasoning_chars": 32448, "elapsed_s": 42.0, "error": "",
    }
    _, zeile = _auftrag(tmp_path, monkeypatch, [lang], extra=["--retry-strategie", "neu"])
    assert zeile["fehlerklasse"] == "length_ohne_ergebnis"
    assert zeile["job_status"] == "failed"
    assert [v["rolle"] for v in zeile["attempts"]] == ["primaer"]
    assert zeile["attempts"][0]["fehlerklasse"] == "budget_im_reasoning"
    assert zeile["attempts"][0]["temporaer"] is False
    assert zeile["attempts"][0]["completion_tokens"] == 8000


def test_neue_strategie_versucht_timeout_nicht_als_json(tmp_path: Path, monkeypatch) -> None:
    # Bisher: Timeout -> leere Antwort -> json_kaputt -> zweiter Aufruf, der
    # dieselben 300 s erneut abwartet. Neu: eigene Klasse, kein JSON-Retry.
    aufrufe_alt, zeile_alt = _auftrag(tmp_path, monkeypatch, [_timeout_antwort()])
    assert len(aufrufe_alt) == 2
    assert zeile_alt["fehlerklasse"] == "json_kaputt"

    monkeypatch.setattr(runner, "HERE", tmp_path / "neu")
    (tmp_path / "neu").mkdir()
    aufrufe_neu, zeile_neu = _auftrag(
        tmp_path / "neu", monkeypatch, [_timeout_antwort()], extra=["--retry-strategie", "neu"]
    )
    assert len(aufrufe_neu) == 1
    assert zeile_neu["fehlerklasse"] == "timeout"
    assert zeile_neu["job_status"] == "failed"
    assert [v["fehlerklasse"] for v in zeile_neu["attempts"]] == ["timeout"]


def test_neue_strategie_protokolliert_json_wiederholung(tmp_path: Path, monkeypatch) -> None:
    kaputt = {
        "http_status": 200, "content": "kein json", "finish_reason": "stop",
        "completion_tokens": 10, "elapsed_s": 1.0, "error": "",
    }
    gut = {
        "http_status": 200,
        "content": json.dumps({"cells": [{"field": "intervention_mean", "arm": "intervention", "value": 1.0}]}),
        "finish_reason": "stop",
        "completion_tokens": 20,
        "elapsed_s": 1.0,
        "error": "",
    }
    _, zeile = _auftrag(tmp_path, monkeypatch, [kaputt, gut], extra=["--retry-strategie", "neu"])
    assert zeile["fehlerklasse"] == ""
    assert zeile["job_status"] == "completed"
    assert [(v["rolle"], v["fehlerklasse"]) for v in zeile["attempts"]] == [
        ("primaer", "json_kaputt"),
        ("json", "ok"),
    ]
