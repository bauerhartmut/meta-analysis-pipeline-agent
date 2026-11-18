"""Offline-Tests fuer Job-Journal und Doppelstart-Sperre (P2).

Kein Netz, keine echte Zeit: die Sperre wird ueber `os.utime` gealtert, nicht
ueber Warten.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import jobs  # noqa: E402


def test_journal_zeigt_unterbrochenen_auftrag_bis_zum_abschluss(tmp_path: Path) -> None:
    journal = jobs.JobJournal(tmp_path / "jobs.jsonl")
    journal.schreibe("yun2024:1", "glm", "running")
    assert [e["record_id"] for e in journal.unterbrochene()] == ["yun2024:1"]
    journal.schreibe("yun2024:1", "glm", "completed")
    assert journal.unterbrochene() == []


def test_journal_meldet_nur_offene_auftraege(tmp_path: Path) -> None:
    journal = jobs.JobJournal(tmp_path / "jobs.jsonl")
    journal.schreibe("a", "glm", "running")
    journal.schreibe("a", "glm", "completed")
    journal.schreibe("b", "glm", "running")
    journal.schreibe("c", "glm", "failed", fehlerklasse="timeout")
    offen = journal.unterbrochene()
    assert [e["record_id"] for e in offen] == ["b"]
    assert offen[0]["status"] == "running"


def test_journal_ignoriert_halb_geschriebene_zeile(tmp_path: Path) -> None:
    pfad = tmp_path / "jobs.jsonl"
    pfad.write_text(
        '{"record_id": "a", "model": "glm", "status": "running"}\n{"record_id": "b", \n',
        encoding="utf-8",
    )
    offen = jobs.JobJournal(pfad).unterbrochene()
    assert [e["record_id"] for e in offen] == ["a"]


def test_journal_haengt_an_und_synct(tmp_path: Path) -> None:
    journal = jobs.JobJournal(tmp_path / "jobs.jsonl")
    journal.schreibe("a", "glm", "running")
    journal.schreibe("a", "glm", "failed", fehlerklasse="budget_im_reasoning")
    zeilen = [json.loads(z) for z in (tmp_path / "jobs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [z["status"] for z in zeilen] == ["running", "failed"]
    assert zeilen[1]["fehlerklasse"] == "budget_im_reasoning"


def test_journal_lehnt_unbekannten_status_ab(tmp_path: Path) -> None:
    try:
        jobs.JobJournal(tmp_path / "jobs.jsonl").schreibe("a", "glm", "fertig")
    except ValueError:
        return
    raise AssertionError("unbekannter Status muss abgelehnt werden")


def test_sperre_haelt_und_gibt_frei(tmp_path: Path) -> None:
    sperre = jobs.RunSperre(tmp_path / "harness.lock")
    assert sperre.nehmen() is True
    assert sperre.pfad.exists()
    assert sperre.pid() == str(os.getpid())
    assert sperre.freigeben() is True
    assert not sperre.pfad.exists()


def test_zweite_sperre_wird_abgelehnt(tmp_path: Path) -> None:
    pfad = tmp_path / "harness.lock"
    jobs.RunSperre(pfad).nehmen()
    try:
        jobs.RunSperre(pfad).nehmen()
    except jobs.SperreBelegt as fehler:
        assert "PID" in str(fehler)
        return
    raise AssertionError("zweite Sperre muss abgelehnt werden")


def test_eigene_pid_gilt_als_lebendig() -> None:
    assert jobs._lebt(os.getpid()) is True


def test_beendeter_prozess_gilt_als_tot() -> None:
    # Genau der Zustand nach `os._exit`: der Prozess ist weg.
    lauf = subprocess.Popen([sys.executable, "-c", "pass"])
    lauf.wait()
    assert jobs._lebt(lauf.pid) is False


def test_sperre_eines_beendeten_prozesses_wird_sofort_uebernommen(tmp_path: Path) -> None:
    lauf = subprocess.Popen([sys.executable, "-c", "pass"])
    lauf.wait()
    pfad = tmp_path / "harness.lock"
    pfad.write_text(json.dumps({"pid": lauf.pid}), encoding="utf-8")
    sperre = jobs.RunSperre(pfad)
    assert sperre.nehmen() is False  # uebernommen, ohne 90 Minuten zu warten
    assert sperre.pid() == str(os.getpid())


def test_altersregel_gilt_wenn_sich_das_leben_nicht_entscheiden_laesst(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(jobs, "_lebt", lambda pid: None)
    pfad = tmp_path / "harness.lock"
    pfad.write_text(json.dumps({"pid": 4242}), encoding="utf-8")
    try:
        jobs.RunSperre(pfad).nehmen()
    except jobs.SperreBelegt:
        pass
    else:
        raise AssertionError("junge Sperre muss halten, wenn das Leben unklar ist")

    alt = time.time() - 91 * 60
    os.utime(pfad, (alt, alt))
    assert jobs.RunSperre(pfad).nehmen() is False


def test_freigeben_laesst_fremde_sperre_stehen(tmp_path: Path) -> None:
    pfad = tmp_path / "harness.lock"
    pfad.write_text(json.dumps({"pid": 4242}), encoding="utf-8")
    assert jobs.RunSperre(pfad).freigeben() is False
    assert pfad.exists()
