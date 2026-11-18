"""Tests fuer die Zuverlaessigkeitsmetriken.

Die Beispielzeilen sind bewusst erfunden und tragen nur die Felder, die der
Harness schreibt; verglichen werden die gerechneten Kennzahlen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import reliabilitaets_metriken as rm  # noqa: E402


def _zeile(**felder) -> dict:
    basis = {
        "record_id": "x",
        "model": "glm",
        "rows": [],
        "fehlerklasse": "",
        "elapsed_s": 0.0,
        "completion_tokens": 0,
    }
    basis.update(felder)
    return basis


def _versuch(klasse: str, wartete: float | None = None) -> dict:
    return {"fehlerklasse": klasse, "temporaer": klasse in rm.TRANSPORT, "wartete_s": wartete}


ZEILEN = [
    _zeile(
        record_id="a",
        job_status="completed",
        http_versuche=1,
        elapsed_s=10,
        completion_tokens=1000,
        rows=[{"field": "x"}],
        attempts=[_versuch("ok")],
    ),
    _zeile(
        record_id="b",
        job_status="completed",
        http_versuche=2,
        elapsed_s=70,
        completion_tokens=2000,
        rows=[{"field": "x"}, {"field": "y"}],
        attempts=[_versuch("timeout"), _versuch("ok", wartete=2.0)],
    ),
    _zeile(
        record_id="c",
        job_status="failed",
        http_versuche=1,
        elapsed_s=40,
        completion_tokens=8000,
        fehlerklasse="length_ohne_ergebnis",
        attempts=[_versuch("budget_im_reasoning")],
    ),
    _zeile(record_id="d", elapsed_s=30, completion_tokens=900),  # Zeile aus der alt-Zeit
]


def test_zaehlt_technische_zuverlaessigkeit() -> None:
    werte = rm.metriken(ZEILEN)
    assert werte["auftraege"] == 4
    assert werte["zeilen_mit_versuchsspur"] == 3
    # Die alt-Zeile d hat keine Fehlerklasse und gilt damit als abgeschlossen.
    assert werte["job_status"] == {"completed": 3, "failed": 1, "abgeleitet": 1}
    assert werte["erfolg_im_ersten_versuch"] == 1
    assert werte["erfolg_nach_wiederholung"] == 1
    assert werte["endgueltig_fehlgeschlagen"] == 1
    assert werte["quote_erfolg"] == 0.75


def test_zaehlt_jeden_aufgetretenen_transportfehler() -> None:
    # Der Timeout im zweiten Auftrag wurde geheilt, ist aber aufgetreten.
    assert rm.metriken(ZEILEN)["transportfehler"] == 1


def test_versuche_und_wartezeit() -> None:
    werte = rm.metriken(ZEILEN)
    assert werte["versuche_je_auftrag"]["n"] == 3
    assert werte["versuche_je_auftrag"]["mittel"] == 1.33
    assert werte["versuche_je_auftrag"]["max"] == 2
    assert werte["wartezeit_s"] == {"summe": 2.0, "mittel": 2.0}


def test_latenz_und_tokens() -> None:
    werte = rm.metriken(ZEILEN)
    assert werte["latenz_s"]["mittel"] == 37.5
    assert werte["latenz_s"]["median"] == 35
    assert werte["latenz_s"]["p90"] == 70.0
    assert werte["tokens"]["gesamt"] == 11900
    assert werte["tokens"]["je_auftrag"] == 2975.0
    # Erfolgreiche Auftraege: a, b und die leere alt-Zeile d.
    assert werte["tokens"]["je_erfolgreichem_auftrag"] == 1300.0


def test_extraktion_getrennt_von_technik() -> None:
    werte = rm.metriken(ZEILEN)
    assert werte["extraktion"] == {"mit_zellen": 2, "leere_antworten": 1, "anteil_leer": 0.25}
    # Die leere Antwort ist kein technischer Ausfall.
    assert werte["finale_klassen"]["ok"] == 3


def test_finale_klasse_nimmt_den_letzten_versuch() -> None:
    assert rm.finale_klasse(ZEILEN[1]) == "ok"
    assert rm.finale_klasse(ZEILEN[2]) == "budget_im_reasoning"
    assert rm.finale_klasse(ZEILEN[3]) == ""


def test_ohne_versuchsspur_bleiben_retry_werte_leer() -> None:
    werte = rm.metriken([ZEILEN[3]])
    assert werte["erfolg_im_ersten_versuch"] is None
    assert werte["erfolg_nach_wiederholung"] is None
    assert werte["versuche_je_auftrag"] is None
    assert werte["http_versuche"] is None
    bericht = rm.bericht(werte, "test")
    assert "Keine Versuchsspur" in bericht
    assert "1 Zeilen ohne `job_status`" in bericht


def test_bericht_nennt_transportluecke_unter_alt() -> None:
    alt = [
        _zeile(record_id="e", fehlerklasse="json_kaputt", elapsed_s=300.0, completion_tokens=0),
    ]
    werte = rm.metriken(alt)
    assert werte["transportfehler"] == 0
    assert "Transportfehler sind hier nicht separat sichtbar" in rm.bericht(werte, "alt")


def test_skript_liest_datei_und_schreibt_bericht(tmp_path: Path) -> None:
    pfad = tmp_path / "predictions.jsonl"
    pfad.write_text("\n".join(json.dumps(z) for z in ZEILEN) + "\n", encoding="utf-8")
    ziel_json = tmp_path / "out.json"
    ziel_md = tmp_path / "out.md"

    argv = sys.argv
    sys.argv = ["metriken", "--run", str(pfad), "--json", str(ziel_json), "--md", str(ziel_md)]
    try:
        assert rm.main() == 0
    finally:
        sys.argv = argv

    assert json.loads(ziel_json.read_text(encoding="utf-8"))["auftraege"] == 4
    assert "Zuverlaessigkeitsmetriken" in ziel_md.read_text(encoding="utf-8")
