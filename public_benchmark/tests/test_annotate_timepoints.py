"""Tests fuer die Zeitpunkt-Annotation der Dev-Records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "extended_benchmark"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from annotate_timepoints import ZEITPUNKTE  # noqa: E402

RECORDS = BENCH / "records" / "yun_dev.jsonl"


def lade_records() -> list[dict]:
    return [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_jeder_record_hat_einen_zielzeitpunkt() -> None:
    records = lade_records()
    ids = {record["record_id"] for record in records}
    assert ids == set(ZEITPUNKTE)
    for record in records:
        info = record.get("timepoint") or {}
        assert info.get("target"), record["record_id"]
        assert info.get("evidence"), record["record_id"]


def test_annotation_aendert_keine_gold_werte() -> None:
    records = lade_records()
    # Die Annotation ist ein eigenes Feld; die Gold-Struktur bleibt unberuehrt.
    for record in records:
        assert set(record["gold"]) == {"cells", "label", "spans"}
        assert all({"field", "value"} <= set(cell) for cell in record["gold"]["cells"])
