"""Tests fuer den Tokenzaehler (Ledger, DB-Zusammenfuehrung, Bericht)."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from research_agent.llm import token_zaehler as tz  # noqa: E402

TZ = timezone(timedelta(hours=1))


def _zeit(hh: int, mm: int = 5) -> datetime:
    return datetime(2026, 11, 18, hh, mm, 0, tzinfo=TZ)


def _db_mit_usage(pfad: Path, zeilen: list[tuple]) -> Path:
    verbindung = sqlite3.connect(pfad)
    verbindung.execute(
        "CREATE TABLE llm_usage (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, day TEXT, "
        "phase TEXT, backend TEXT, model TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, "
        "total_tokens INTEGER, time_ms REAL, success INTEGER)"
    )
    verbindung.executemany(
        "INSERT INTO llm_usage (timestamp, day, phase, backend, model, prompt_tokens, "
        "completion_tokens, total_tokens) VALUES (?,?,?,?,?,?,?,?)",
        zeilen,
    )
    verbindung.commit()
    verbindung.close()
    return pfad


def test_zaehle_schreibt_tag_stunde_und_summe(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    assert tz.zaehle("gwdg/glm-5.3", 1200, 300, quelle="test", zeitpunkt=_zeit(14), ledger=ledger)

    zeile = tz.lade_ledger(ledger)[0]
    assert zeile["tag"] == "2026-11-18"
    assert zeile["stunde"] == "14"
    assert zeile["modell"] == "gwdg/glm-5.3"
    assert zeile["prompt_tokens"] == 1200
    assert zeile["completion_tokens"] == 300
    assert zeile["total_tokens"] == 1500
    assert zeile["quelle"] == "test"


def test_zaehle_ohne_tokens_schreibt_nichts(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    assert not tz.zaehle("m", None, 0, ledger=ledger)
    assert not tz.zaehle("m", 0, 0, ledger=ledger)
    assert tz.lade_ledger(ledger) == []


def test_zaehle_wirft_nicht_bei_unschreibbarem_pfad(tmp_path: Path) -> None:
    sperre = tmp_path / "datei"
    sperre.write_text("kein Verzeichnis", encoding="utf-8")
    assert not tz.zaehle("m", 10, 5, ledger=sperre / "unter" / "ledger.jsonl")


def test_kaputte_ledger_zeile_wird_uebersprungen(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        '{"modell": "a", "tag": "2026-11-18", "stunde": "10", "prompt_tokens": 5, "completion_tokens": 1, "ts": "t1"}\n'
        "kein json\n"
        '{"ohne": "modell"}\n',
        encoding="utf-8",
    )
    assert len(tz.lade_ledger(ledger)) == 1


def test_gruppiere_summiert_je_stunde_und_modell() -> None:
    zeilen = [
        {"tag": "2026-11-18", "stunde": "10", "modell": "a", "prompt_tokens": 10, "completion_tokens": 1},
        {"tag": "2026-11-18", "stunde": "10", "modell": "a", "prompt_tokens": 20, "completion_tokens": 2},
        {"tag": "2026-11-18", "stunde": "10", "modell": "b", "prompt_tokens": 5, "completion_tokens": 5},
        {"tag": "2026-11-18", "stunde": "11", "modell": "a", "prompt_tokens": 1, "completion_tokens": 1},
    ]
    gruppen = tz.gruppiere(zeilen)
    assert [(g["tag"], g["stunde"], g["modell"], g["aufrufe"]) for g in gruppen] == [
        ("2026-11-18", "10", "a", 2),
        ("2026-11-18", "10", "b", 1),
        ("2026-11-18", "11", "a", 1),
    ]
    assert gruppen[0]["prompt_tokens"] == 30
    assert gruppen[0]["total_tokens"] == 33


def test_gruppiere_filtert_modell_und_tag() -> None:
    zeilen = [
        {"tag": "2026-11-17", "stunde": "10", "modell": "a", "prompt_tokens": 1, "completion_tokens": 0},
        {"tag": "2026-11-18", "stunde": "10", "modell": "a", "prompt_tokens": 2, "completion_tokens": 0},
        {"tag": "2026-11-18", "stunde": "10", "modell": "b", "prompt_tokens": 3, "completion_tokens": 0},
    ]
    assert [g["tag"] for g in tz.gruppiere(zeilen, seit="2026-11-18")] == ["2026-11-18", "2026-11-18"]
    assert [g["modell"] for g in tz.gruppiere(zeilen, modell="b")] == ["b"]
    assert tz.gruppiere(zeilen, bis="2026-11-17")[0]["prompt_tokens"] == 1


def test_ledger_und_datenbank_werden_zusammengefuehrt(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    tz.zaehle("gwdg/glm-5.3", 100, 10, zeitpunkt=_zeit(9), ledger=ledger)
    _db_mit_usage(
        tmp_path / "harness.db",
        [("2026-11-18T09:30:00+01:00", "2026-11-18", "synthesizing", "tudagpt", "gwdg/glm-5.3", 200, 20, 220)],
    )

    zeilen = tz.eintraege(ledger, "*.db", tmp_path)
    gruppen = tz.gruppiere(zeilen)

    assert len(gruppen) == 1
    assert gruppen[0]["aufrufe"] == 2
    assert gruppen[0]["prompt_tokens"] == 300
    assert gruppen[0]["completion_tokens"] == 30


def test_doppelte_zeile_wird_nur_einmal_gezaehlt(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    tz.zaehle("m", 10, 2, zeitpunkt=_zeit(8), ledger=ledger)
    doppelt = ledger.read_text(encoding="utf-8")
    ledger.write_text(doppelt + doppelt, encoding="utf-8")
    assert len(tz.eintraege(ledger, "*.db", tmp_path)) == 1


def test_bericht_nennt_summen_und_leere_lage(tmp_path: Path) -> None:
    zeilen = [
        {"tag": "2026-11-18", "stunde": "10", "modell": "a", "prompt_tokens": 10, "completion_tokens": 1},
        {"tag": "2026-11-18", "stunde": "11", "modell": "a", "prompt_tokens": 20, "completion_tokens": 2},
    ]
    text = tz.bericht(tz.gruppiere(zeilen))
    assert "| 2026-11-18 | 10 | `a` |" in text
    assert "## Summe je Modell" in text
    assert "| `a` | 2 | 30 | 3 | 33 |" in text
    assert "Gesamt: 2 Aufrufe" in text
    assert "keine aufrufe" in tz.bericht([]).lower()
