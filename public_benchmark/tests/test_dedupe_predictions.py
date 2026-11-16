"""Tests fuer die Dedupe-Regel in dedupe_predictions.py.

Hintergrund: `--retry-failed` haengt neue Zeilen an und laesst die alten
Fehlzeilen stehen. `auswerte_yun699.py` dedupliziert nicht, also muss vor der
Auswertung eindeutig geklaert sein, welche Zeile je (record_id, model) gilt:
die letzte nicht fehlgeschlagene. Diese Regel ist hier festgenagelt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full.dedupe_predictions import entdopple  # noqa: E402


def zeile(record: str, modell: str = "glm", *, failed: bool = False, marke: str = "") -> str:
    return json.dumps(
        {"record_id": record, "model": modell, "failed": failed, "marke": marke}
    )


def marken(zeilen: list[str]) -> list[str]:
    return [json.loads(z)["marke"] for z in zeilen]


def test_erfolgreiche_zeile_gewinnt_gegen_spaetere_fehlzeile() -> None:
    """Ein spaeterer Retry, der scheitert, darf das gute Ergebnis nicht verdraengen."""
    bereinigt, duplikate, kaputt = entdopple(
        [zeile("r1", marke="ok"), zeile("r1", failed=True, marke="fehler")]
    )
    assert marken(bereinigt) == ["ok"]
    assert duplikate == 1
    assert kaputt == 0


def test_spaetere_erfolgreiche_zeile_gewinnt_gegen_fehlzeile() -> None:
    """Der Normalfall: Nachzug nach einem Length-Ausfall."""
    bereinigt, duplikate, _ = entdopple(
        [zeile("r1", failed=True, marke="length"), zeile("r1", marke="nachzug")]
    )
    assert marken(bereinigt) == ["nachzug"]
    assert duplikate == 1


def test_letzte_von_zwei_erfolgreichen_gewinnt() -> None:
    """Bei zwei brauchbaren Zeilen gilt die spaetere."""
    bereinigt, _, _ = entdopple(
        [zeile("r1", marke="alt"), zeile("r1", marke="neu")]
    )
    assert marken(bereinigt) == ["neu"]


def test_nur_fehlzeilen_bleiben_als_ausfall_sichtbar() -> None:
    """Ohne Erfolg bleibt die letzte Fehlzeile stehen, statt zu verschwinden."""
    bereinigt, duplikate, _ = entdopple(
        [zeile("r1", failed=True, marke="erst"), zeile("r1", failed=True, marke="dann")]
    )
    assert marken(bereinigt) == ["dann"]
    assert json.loads(bereinigt[0])["failed"] is True
    assert duplikate == 1


def test_reihenfolge_des_ersten_auftretens_bleibt() -> None:
    bereinigt, _, _ = entdopple(
        [zeile("r2", marke="a"), zeile("r1", marke="b"), zeile("r2", marke="c")]
    )
    assert [json.loads(z)["record_id"] for z in bereinigt] == ["r2", "r1"]
    assert marken(bereinigt) == ["c", "b"]


def test_verschiedene_modelle_bleiben_getrennt() -> None:
    """Dedupe laeuft je (record_id, model), nicht je Record allein."""
    bereinigt, duplikate, _ = entdopple(
        [zeile("r1", "glm", marke="g"), zeile("r1", "qwen", marke="q")]
    )
    assert sorted(marken(bereinigt)) == ["g", "q"]
    assert duplikate == 0


def test_unlesbare_zeile_wird_gezaehlt_nicht_uebernommen() -> None:
    bereinigt, duplikate, kaputt = entdopple([zeile("r1", marke="ok"), "{kaputt"])
    assert marken(bereinigt) == ["ok"]
    assert kaputt == 1
    assert duplikate == 0


def test_leere_zeilen_zaehlen_nicht_als_duplikat() -> None:
    bereinigt, duplikate, kaputt = entdopple(["", "   ", zeile("r1", marke="ok"), ""])
    assert marken(bereinigt) == ["ok"]
    assert duplikate == 0
    assert kaputt == 0
