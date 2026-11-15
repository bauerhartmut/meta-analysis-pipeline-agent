"""Tests fuer die Analysesktripte: Piloturteil, Zusammenfuehrung, je_quelle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
ANALYSE = BENCH / "extended_benchmark" / "analysis" / "run186_20261115"
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(ANALYSE))

import mische_quelle  # noqa: E402
import pilot_len  # noqa: E402
from extended_benchmark import evaluate_fallback  # noqa: E402


def _zeile(record_id: str, **rest) -> dict:
    basis = {
        "record_id": record_id,
        "finish_reason": "stop",
        "fehlerklasse": "",
        "parse_error": "",
        "completion_tokens": 1000,
        "rows": [{"field": "intervention_mean", "arm": "intervention", "value": 1.0, "timepoint": "24"}],
    }
    basis.update(rest)
    return basis


def test_piloturteil_trennt_json_von_zellen() -> None:
    zeilen = [
        _zeile("a"),
        _zeile("b"),
        _zeile("c", rows=[], parse_error="keine_verwertbaren_zellen"),
        _zeile("d", finish_reason="length", fehlerklasse="length_ohne_ergebnis", parse_error="kein_json", rows=[]),
    ]
    urteil = pilot_len.urteil(zeilen)
    assert urteil["erfolge_json"] == 3  # a, b, c
    assert urteil["erfolge_mit_zellen"] == 2  # a, b
    assert urteil["quote_json"] == 0.75
    assert urteil["quote_mit_zellen"] == 0.5
    # Vorab festgelegtes Kriterium: mindestens 5 parsebare Antworten, Median <= 6000.
    assert urteil["kriterium_erfuellt_json"] is False
    assert urteil["bestanden"] is False


def test_piloturteil_bestanden_verlangt_fuenf_parsebare() -> None:
    zeilen = [_zeile(str(i)) for i in range(5)] + [_zeile("x", finish_reason="length", fehlerklasse="length", rows=[])]
    urteil = pilot_len.urteil(zeilen)
    assert urteil["erfolge_json"] == 5
    assert urteil["medien_tokens"] == 1000
    assert urteil["bestanden"] is True


def _schreibe(path: Path, zeilen: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(z, ensure_ascii=False) for z in zeilen) + "\n", encoding="utf-8")
    return path


def test_zusammenfuehrung_schuetzt_vor_ueberschreiben(tmp_path: Path) -> None:
    haupt = _schreibe(tmp_path / "haupt" / "predictions.jsonl", [_zeile("a")])
    folge = _schreibe(tmp_path / "folge" / "predictions.jsonl", [_zeile("a")])
    for ziel in (tmp_path / "haupt", tmp_path / "folge"):
        try:
            mische_quelle.fuehre_zusammen(haupt, folge, ziel)
        except ValueError as fehler:
            assert "ueberschreiben" in str(fehler)
        else:  # pragma: no cover - Sicherheitsnetz
            raise AssertionError("Zielpfad haette abgelehnt werden muessen")
    assert len(haupt.read_text(encoding="utf-8").splitlines()) == 1


def test_zusammenfuehrung_ersetzt_nur_mit_zellen_und_zaehlt_fremde_ids(tmp_path: Path) -> None:
    haupt = _schreibe(
        tmp_path / "haupt" / "predictions.jsonl",
        [
            _zeile("a", rows=[]),
            _zeile("b", rows=[], fehlerklasse="length_ohne_ergebnis"),
            _zeile("c", rows=[], fehlerklasse="length_ohne_ergebnis"),
        ],
    )
    folge = _schreibe(
        tmp_path / "folge" / "predictions.jsonl",
        [
            _zeile("a", quelle="v7_folgelauf"),
            _zeile("b", quelle="v7_folgelauf"),
            _zeile("c", rows=[], fehlerklasse="length_ohne_ergebnis", quelle="v7_folgelauf"),
            _zeile("zzz", quelle="v7_folgelauf"),
        ],
    )
    zusammenfassung = mische_quelle.fuehre_zusammen(haupt, folge, tmp_path / "ziel")
    assert zusammenfassung["aus_folgelauf"] == 2  # a und b liefern Zellen
    assert zusammenfassung["aus_hauptlauf"] == 1  # c bleibt Fehlzeile des Hauptlaufs
    assert zusammenfassung["folge_verworfen"] == 1
    assert zusammenfassung["folge_nicht_zugeordnet"] == 1
    assert zusammenfassung["folge_nicht_zugeordnet_ids"] == ["zzz"]
    assert zusammenfassung["je_quelle"] == {"v6_hauptlauf": 1, "v7_folgelauf": 2}


def _records(path: Path) -> Path:
    zeilen = []
    for record_id in ("a", "b", "c"):
        zeilen.append(
            {
                "record_id": record_id,
                "document": {"split": "test", "path": ""},
                "context": {"intervention": "A", "comparator": "B", "outcome": "C", "outcome_type": "continuous"},
                "timepoint": {"target": "week 24"},
                "gold": {"cells": [{"field": "intervention_mean", "arm": "intervention", "value": 1.0}]},
            }
        )
    return _schreibe(path, zeilen)


def test_je_quelle_trennt_ausfaelle_und_leere_antworten(tmp_path: Path, monkeypatch) -> None:
    lauf = tmp_path / "runs" / "t1"
    _schreibe(
        lauf / "predictions.jsonl",
        [
            _zeile("a", quelle="v6_hauptlauf", predicted={"cells": [{"field": "intervention_mean", "arm": "intervention", "value": 1.0, "timepoint": "24"}]}),
            _zeile("b", quelle="v7_folgelauf", rows=[], predicted={"cells": []}, fehlerklasse="length_ohne_ergebnis"),
            _zeile("c", quelle="v7_folgelauf", rows=[], predicted={"cells": []}, parse_error="keine_verwertbaren_zellen"),
        ],
    )
    records = _records(tmp_path / "records.jsonl")
    ausgabe = tmp_path / "out.json"
    monkeypatch.setattr(evaluate_fallback, "HERE", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_fallback.py", "--run", "t1", "--records", str(records), "--out", str(ausgabe)],
    )
    assert evaluate_fallback.main() == 0
    ergebnis = json.loads(ausgabe.read_text(encoding="utf-8"))
    v6 = ergebnis["je_quelle"]["v6_hauptlauf"]
    v7 = ergebnis["je_quelle"]["v7_folgelauf"]
    assert v6["records"] == 1 and v6["richtig"] == 1 and v6.get("technische_ausfaelle", 0) == 0
    assert v7["records"] == 2
    assert v7["technische_ausfaelle"] == 1
    assert v7["leere_antworten"] == 1

    # --nur-ids beschraenkt die Auswertung auf die genannten Records.
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_fallback.py", "--run", "t1", "--records", str(records),
            "--nur-ids", "b", "--out", str(ausgabe),
        ],
    )
    assert evaluate_fallback.main() == 0
    beschraenkt = json.loads(ausgabe.read_text(encoding="utf-8"))
    assert beschraenkt["records"] == 1
    assert set(beschraenkt["je_quelle"]) == {"v7_folgelauf"}
