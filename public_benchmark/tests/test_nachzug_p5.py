"""Offline-Tests fuer die Wiederaufnahme-Schleife und den Nachzug.

Kein Netz, kein Anbieter, keine Wartezeit. Geprueft wird zweierlei: Ein
temporaerer Ausfall hinterlaesst keine Zwischenzeile, und nach dem Nachzug steht
je Record genau eine Zeile in `predictions.jsonl` — sonst zaehlt
`auswerte_yun699.py` denselben Record doppelt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import nachzug_p5, wiederaufnahme  # noqa: E402


def _zeile(record_id: str, *, failed: bool, rows: list | None = None) -> str:
    return json.dumps(
        {
            "record_id": record_id,
            "model": "glm",
            "rows": [] if failed else (rows if rows is not None else [{"zeitpunkt": "t1"}]),
            "failed": failed,
        }
    )


def test_temporaerer_ausfall_schreibt_keine_zwischenzeile(tmp_path: Path) -> None:
    """Zwei 503 nacheinander: bis zum Erfolg bleibt die Datei leer."""
    datei = tmp_path / "predictions.jsonl"
    abgelaufen: list[str] = []

    def arbeit(record_id: str) -> dict[str, object]:
        abgelaufen.append(record_id)
        if len(abgelaufen) <= 2:
            # Wie im Harness: der Auftrag kehrt nur mit dem Wiederaufnahme-Signal
            # zurueck, `row` und damit die Datei bleiben unberuehrt.
            assert not datei.exists() or not datei.read_text(encoding="utf-8").strip()
            return {"record_id": record_id, "wiederaufnahme": True}
        with datei.open("a", encoding="utf-8") as handle:
            handle.write(_zeile(record_id, failed=False) + "\n")
        return {"record_id": record_id, "model": "glm"}

    fertig, erneut = wiederaufnahme.abwickeln([("yun2024:6",)], arbeit, threads=1)

    assert (fertig, erneut) == (1, 2)
    assert abgelaufen == ["yun2024:6"] * 3
    zeilen = datei.read_text(encoding="utf-8").splitlines()
    assert len(zeilen) == 1, zeilen
    assert json.loads(zeilen[0])["record_id"] == "yun2024:6"


def test_schleife_reiht_nur_wiederaufnahmen_erneut_ein() -> None:
    stands: dict[str, int] = {}

    def arbeit(name: str) -> dict[str, object]:
        stands[name] = stands.get(name, 0) + 1
        if name == "b" and stands[name] == 1:
            return {"wiederaufnahme": True}
        return {"record_id": name}

    fertig, erneut = wiederaufnahme.abwickeln([("a",), ("b",), ("c",)], arbeit, threads=2)

    assert (fertig, erneut) == (3, 1)
    assert stands == {"a": 1, "b": 2, "c": 1}


def test_ausnahme_beendet_die_schleife_nicht() -> None:
    meldungen: list[str] = []

    def arbeit(name: str) -> dict[str, object]:
        if name == "kaputt":
            raise RuntimeError("Anbieter weg")
        return {"record_id": name}

    fertig, erneut = wiederaufnahme.abwickeln(
        [("kaputt",), ("ok",)], arbeit, threads=1, melde=meldungen.append
    )

    assert (fertig, erneut) == (1, 0)
    assert any("Anbieter weg" in meldung for meldung in meldungen)


def test_null_threads_ist_ein_fehler() -> None:
    with pytest.raises(ValueError):
        wiederaufnahme.abwickeln([], lambda: {}, threads=0)


def test_nachzug_hinterlaesst_genau_eine_zeile_je_record(tmp_path: Path) -> None:
    datei = tmp_path / "predictions.jsonl"
    alt = [
        _zeile("yun2024:6", failed=True),
        _zeile("yun2024:30", failed=True),
        _zeile("yun2024:32", failed=True),
    ]
    # Der Nachzug haengt an, statt zu ersetzen: je Paar steht die Zeile zweimal.
    neu = [
        _zeile("yun2024:6", failed=False),
        _zeile("yun2024:30", failed=True),
        _zeile("yun2024:32", failed=False, rows=[{"zeitpunkt": "t2"}]),
    ]
    datei.write_text("".join(zeile + "\n" for zeile in alt + neu), encoding="utf-8")

    bericht = nachzug_p5.eindeutig_machen(
        datei, ["yun2024:6", "yun2024:30", "yun2024:32", "yun2024:54"]
    )

    zeilen = [json.loads(zeile) for zeile in datei.read_text(encoding="utf-8").splitlines()]
    assert len(zeilen) == 3
    assert [z["record_id"] for z in zeilen] == ["yun2024:6", "yun2024:30", "yun2024:32"]
    assert zeilen[0]["failed"] is False
    assert zeilen[2]["rows"] == [{"zeitpunkt": "t2"}]
    assert zeilen[1]["failed"] is True  # weiterhin Ausfall, aber nur eine Zeile
    assert bericht.zeilen == 6
    assert bericht.duplikate == 3
    assert bericht.fehlend == [("yun2024:54", 0)]
    assert bericht.verbleibende_ausfaelle == ["yun2024:30"]
    assert bericht.sicherung is not None and bericht.sicherung.exists()


def test_aufraeumen_ist_wiederholbar(tmp_path: Path) -> None:
    datei = tmp_path / "predictions.jsonl"
    datei.write_text("".join(_zeile(f"yun2024:{i}", failed=False) + "\n" for i in range(3)), encoding="utf-8")
    ids = [f"yun2024:{i}" for i in range(3)]

    erster = nachzug_p5.eindeutig_machen(datei, ids)
    inhalt = datei.read_text(encoding="utf-8")
    zweiter = nachzug_p5.eindeutig_machen(datei, ids)

    assert erster.duplikate == 0
    assert zweiter.duplikate == 0 and zweiter.sicherung is None
    assert datei.read_text(encoding="utf-8") == inhalt
    assert zweiter.fehlend == [] and zweiter.verbleibende_ausfaelle == []
