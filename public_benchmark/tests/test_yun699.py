"""Tests fuer den Yun-699-Adapter und die Trennung von Gold und Prompt."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))

YUN = BENCH / "extended_benchmark" / "yun_full"
RECORDS = YUN / "records" / "yun699.jsonl"
MANIFEST = YUN / "manifest.json"


def lies() -> list[dict]:
    return [json.loads(z) for z in RECORDS.read_text(encoding="utf-8").splitlines() if z.strip()]


def test_umfang_und_hash() -> None:
    rows = lies()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(rows) == 699
    assert manifest["records"]["gesamt"] == 699
    assert hashlib.sha256(RECORDS.read_bytes()).hexdigest() == manifest["ausgabe"]["sha256"]
    assert len({r["document"]["id"] for r in rows}) == 120


def test_splits_sind_getrennt() -> None:
    rows = lies()
    test = [r for r in rows if r["document"]["split"] == "test"]
    dev = [r for r in rows if r["document"]["split"] == "dev"]
    assert len(test) == 656 and len(dev) == 43
    assert not {r["document"]["id"] for r in test} & {r["document"]["id"] for r in dev}
    assert sum(len(r["gold"]["cells"]) for r in test) == 2603


def test_jede_zelle_traegt_ihren_originalwert() -> None:
    for record in lies():
        for zelle in record["gold"]["cells"]:
            assert zelle["raw"]
            assert zelle["source"]
            if "normalisiert" in zelle:
                assert zelle["raw"] != f"{zelle['value']:g}"


def test_prompt_kopf_enthaelt_keinen_goldwert() -> None:
    """Der Agent sieht Text und Kontext, nie die Annotation."""
    from extended_benchmark import run_extended_extraction as rx

    for record in lies():
        if record["record_id"] not in {"yun2024:6", "yun2024:7", "yun2024:12", "yun2024:10", "yun2024:11"}:
            continue
        kopf = rx.build_prompt(
            record,
            "",
            45000,
            cell_timepoint=True,
            target_timepoint=record["timepoint"]["target"],
            group_size_mode="aus",
        )
        for zelle in record["gold"]["cells"]:
            assert zelle["raw"] not in kopf, (record["record_id"], zelle["field"])
