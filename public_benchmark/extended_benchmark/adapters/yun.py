"""Adapter fuer Yun et al. 2024 (numerische Armwerte aus RCT-Abstracts).

Quelle: ``raw_data/yun_llm_meta_analysis``, Datei
``evaluation/data/annotated_rct_dataset.json`` (699 Records, 120 Artikel).

Der eingefrorene C1-Testsplit (249 Records) ist gesperrt und wird ohne
``--include-frozen`` nicht aufgenommen.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import RAW_ROOT, cell, read_jsonl, rel

DATASET = "yun2024"
VERSION = "1bc768d4d098c727c9866eeff909297c38a3e84c"

SOURCE_JSON = RAW_ROOT / "yun_llm_meta_analysis" / "evaluation" / "data" / "annotated_rct_dataset.json"
MARKDOWN_DIR = SOURCE_JSON.parent / "no_attributes_markdown_files"
FROZEN_TEST = Path(__file__).resolve().parents[2] / "processed_data" / "yun_c1_test_249.jsonl"


def frozen_test_ids() -> set[int]:
    """IDs des eingefrorenen Testsplits, falls die Datei lokal vorliegt."""
    ids: set[int] = set()
    for row in read_jsonl(FROZEN_TEST):
        value = row.get("record_id")
        if isinstance(value, int):
            ids.add(value)
    return ids


def _document(pmcid: Any) -> dict[str, Any]:
    path = MARKDOWN_DIR / f"PMC{pmcid}.md"
    if not path.exists():
        path = MARKDOWN_DIR / f"PMC{pmcid}.markdown"
    text_chars = None
    if path.exists():
        text_chars = len(path.read_text(encoding="utf-8", errors="replace"))
    return {
        "id": f"PMC{pmcid}" if pmcid not in (None, "") else "",
        "kind": "abstract_markdown",
        "path": rel(path) if path.exists() else "",
        "split": None,
        "text_chars": text_chars,
    }


def build(include_frozen: bool = False, limit: int | None = None) -> list[dict[str, Any]]:
    """Liefert Records im einheitlichen Schema."""
    payload = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Unerwartete Struktur in annotated_rct_dataset.json")
    frozen = set() if include_frozen else frozen_test_ids()

    records: list[dict[str, Any]] = []
    for raw in payload:
        source_id = raw.get("id")
        if not isinstance(source_id, int):
            continue
        if source_id in frozen:
            continue
        outcome_type = (raw.get("outcome_type") or "").strip().lower() or None
        cells = []
        for name, arm, unit in (
            ("intervention_group_size", "intervention", "participants"),
            ("intervention_events", "intervention", "events"),
            ("intervention_mean", "intervention", "reported"),
            ("intervention_standard_deviation", "intervention", "reported"),
            ("comparator_group_size", "comparator", "participants"),
            ("comparator_events", "comparator", "events"),
            ("comparator_mean", "comparator", "reported"),
            ("comparator_standard_deviation", "comparator", "reported"),
        ):
            item = cell(name, arm, raw.get(name), unit, name)
            if item is not None:
                cells.append(item)

        issues: list[str] = []
        notes = (raw.get("notes") or "").strip()
        if notes:
            issues.append(f"annotator_note: {notes}")
        if not cells:
            issues.append("keine_zahlenwerte")
        if outcome_type == "binary" and any(c["field"].endswith("_mean") for c in cells):
            issues.append("binary_record_mit_mean_wert")

        document = _document(raw.get("pmcid"))
        document["split"] = (raw.get("split") or "").strip().lower() or None

        records.append(
            {
                "record_id": f"{DATASET}:{source_id}",
                "dataset": DATASET,
                "task": "numeric_extraction",
                "document": document,
                "context": {
                    "intervention": raw.get("intervention") or None,
                    "comparator": raw.get("comparator") or None,
                    "outcome": raw.get("outcome") or None,
                    "outcome_type": outcome_type,
                },
                "gold": {"cells": cells, "label": None, "spans": []},
                "provenance": {
                    "source_file": rel(SOURCE_JSON),
                    "source_id": str(source_id),
                    "dataset_version": VERSION,
                },
                "issues": issues,
            }
        )
        if limit is not None and len(records) >= limit:
            break
    return records
