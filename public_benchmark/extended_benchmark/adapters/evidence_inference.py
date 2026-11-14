"""Adapter fuer Evidence Inference 2.0 (Evidenzrichtung samt Textbeleg).

Quelle: ``raw_data/evidence_inference_v2_0`` mit ``annotations_merged.csv``
(24.686 Zeilen), ``prompts_merged.csv`` und ``txt_files/PMC*.txt``.

Ein Record entspricht einem Prompt (PromptID + PMCID). Mehrere Annotationszeilen
mehrerer User werden zusammengefasst: Label per Mehrheit, alle Belegspannen
bleiben erhalten.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .common import RAW_ROOT, rel

DATASET = "evidence_inference_v2"
VERSION = "v2.0"

ROOT = RAW_ROOT / "evidence_inference_v2_0"
ANNOTATIONS = ROOT / "annotations_merged.csv"
PROMPTS = ROOT / "prompts_merged.csv"
TEXT_DIR = ROOT / "txt_files"

LABEL_FIX = {"significantly increase": "significantly increased"}


def _load_prompts() -> dict[str, dict[str, str]]:
    if not PROMPTS.exists():
        return {}
    with PROMPTS.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {str(row.get("PromptID") or row.get("prompt_id")): row for row in reader}


def _load_splits() -> dict[str, str]:
    """Bildet PMCID auf Split ab, sofern die Splits von Evidence Inference 2.0 vorliegen."""
    mapping: dict[str, str] = {}
    for split in ("train", "validation", "test"):
        for prefix in ("ev2_", ""):
            path = ROOT / "splits" / f"{prefix}{split}_article_ids.txt"
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                value = line.strip()
                if value:
                    mapping.setdefault(value.removeprefix("PMC"), split)
    return mapping


def normalize_pmcid(value: str) -> str:
    """Fuehrt PMCID-Schreibweisen auf die Form PMC<nummer> zusammen."""
    text = (value or "").strip()
    if not text:
        return ""
    upper = text.upper()
    if upper.startswith("PMC"):
        return upper
    return f"PMC{text}"


def _document(pmcid: str, splits: dict[str, str]) -> dict[str, Any]:
    path = TEXT_DIR / f"{pmcid}.txt"
    text_chars = None
    if path.exists():
        text_chars = len(path.read_text(encoding="utf-8", errors="replace"))
    return {
        "id": pmcid,
        "kind": "fulltext_text",
        "path": rel(path) if path.exists() else "",
        "split": splits.get(pmcid.upper().removeprefix("PMC")),
        "text_chars": text_chars,
    }


def build(limit: int | None = None, require_valid: bool = True) -> list[dict[str, Any]]:
    """Liefert Records im einheitlichen Schema."""
    if not ANNOTATIONS.exists():
        raise FileNotFoundError(f"Fehlende Datei: {ANNOTATIONS}")
    prompts = _load_prompts()
    splits = _load_splits()

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with ANNOTATIONS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            prompt_id = str(row.get("PromptID") or "").strip()
            pmcid = normalize_pmcid(str(row.get("PMCID") or ""))
            if not prompt_id or not pmcid:
                continue
            grouped[(prompt_id, pmcid)].append(row)

    records: list[dict[str, Any]] = []
    for (prompt_id, pmcid), rows in sorted(grouped.items(), key=lambda item: (int(item[0][0]) if item[0][0].isdigit() else 0, item[0][1])):
        valid_rows = [r for r in rows if str(r.get("Valid Label", "")).strip().lower() != "false"]
        usable = valid_rows if require_valid else rows
        if not usable:
            continue
        labels = [LABEL_FIX.get(str(r.get("Label") or "").strip(), str(r.get("Label") or "").strip()) for r in usable]
        counts = Counter(label for label in labels if label)
        issues: list[str] = []
        if not counts:
            continue
        ranked = counts.most_common()
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            label = None
            issues.append("label_patt: keine Mehrheit")
        else:
            label = ranked[0][0]

        spans = []
        text_cache: dict[str, str] = {}
        for row in usable:
            try:
                start = int(float(row.get("Evidence Start", -1)))
                end = int(float(row.get("Evidence End", -1)))
            except (TypeError, ValueError):
                continue
            if start < 0 or end <= start:
                continue
            path = TEXT_DIR / f"{pmcid}.txt"
            if pmcid not in text_cache:
                text_cache[pmcid] = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            text = text_cache[pmcid][start:end]
            if not text:
                continue
            spans.append({"kind": "evidence", "element": "result", "start": start, "end": end, "text": text})

        if len(counts) > 1:
            issues.append("mehrere_labels: " + ", ".join(f"{k}={v}" for k, v in ranked))
        if not spans:
            issues.append("keine_gueltige_evidenzspanne")

        context_row = prompts.get(prompt_id, {})
        document = _document(pmcid, splits)
        records.append(
            {
                "record_id": f"{DATASET}:{prompt_id}:{pmcid}",
                "dataset": DATASET,
                "task": "evidence_direction",
                "document": document,
                "context": {
                    "intervention": context_row.get("Intervention") or None,
                    "comparator": context_row.get("Comparator") or None,
                    "outcome": context_row.get("Outcome") or None,
                    "outcome_type": None,
                },
                "gold": {"cells": [], "label": label, "spans": spans},
                "provenance": {
                    "source_file": rel(ANNOTATIONS),
                    "source_id": f"{prompt_id}:{pmcid}",
                    "dataset_version": VERSION,
                },
                "issues": issues,
            }
        )
        if limit is not None and len(records) >= limit:
            break
    return records
