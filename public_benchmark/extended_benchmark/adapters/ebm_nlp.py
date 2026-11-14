"""Adapter fuer EBM-NLP (PICO-Spannen in RCT-Abstracts).

Quelle: ``raw_data/ebm_nlp/extracted/ebm_nlp_2_00`` (4.993 Abstracts).
Ein Record entspricht einem Abstract; die Gold-Spannen sind Tokenbereiche.

Labelkodierung der aggregierten Startspannen: 0 = keine Spanne, 1 = Spanne.
Die hierarchischen Labels liefern die Feinklasse je Element (Age, Sex, Sample
size, Condition bzw. Surgical, Physical, Drug, ...).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .common import RAW_ROOT, rel

DATASET = "ebm_nlp"
VERSION = "2.00"

ROOT = RAW_ROOT / "ebm_nlp" / "extracted" / "ebm_nlp_2_00"
DOCUMENTS = ROOT / "documents"
ANNOTATIONS = ROOT / "annotations" / "aggregated"

ELEMENTS = ("participants", "interventions", "outcomes")

HIERARCHICAL = {
    "participants": {0: "No label", 1: "Age", 2: "Sex", 3: "Sample size", 4: "Condition"},
    "interventions": {
        0: "No label",
        1: "Surgical",
        2: "Physical",
        3: "Pharmacological",
        4: "Educational",
        5: "Psychological",
        6: "Other",
        7: "Control",
    },
    "outcomes": {0: "No label", 1: "Physical", 2: "Pain", 3: "Mortality", 4: "Adverse effects", 5: "Mental", 6: "Other"},
}


def _read_labels(path: Path) -> list[int]:
    labels = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value:
            continue
        try:
            labels.append(int(float(value)))
        except ValueError:
            labels.append(0)
    return labels


def _spans(
    labels: list[int],
    tokens: list[str],
    element: str,
    detailed: dict[int, str] | None,
    hier_labels: list[int] | None = None,
) -> list[dict[str, Any]]:
    spans = []
    start = None
    for index, label in enumerate(labels + [0]):
        if label and start is None:
            start = index
        elif not label and start is not None:
            end = index
            text = " ".join(tokens[start:end]).strip()
            item = {
                "kind": "pico_span",
                "element": element,
                "start": start,
                "end": end,
                "text": text,
            }
            if detailed and hier_labels and len(hier_labels) == len(labels):
                codes = {hier_labels[i] for i in range(start, end) if hier_labels[i]}
                names = [detailed.get(code, str(code)) for code in sorted(codes)]
                item["label"] = "|".join(names)
            spans.append(item)
            start = None
    return spans


def available_pmids() -> list[str]:
    if not DOCUMENTS.exists():
        return []
    return sorted({path.stem for path in DOCUMENTS.glob("*.tokens")})


def split_of(path: Path) -> str | None:
    """Liest den Split aus dem Pfad (train direkt, test unter crowd/gold)."""
    parts = [part.lower() for part in path.parts]
    for name in ("test", "train", "dev", "validation"):
        if name in parts:
            return name
    return None


def annotation_index() -> dict[tuple[str, str], Path]:
    """Bildet (Element, PMID) auf die aggregierte Startspannendatei ab.

    Die Trainingslabels liegen direkt im Split-Ordner, die Testlabels unter
    ``crowd`` und ``gold``. Bei doppelten Eintraegen gewinnt ``crowd``.
    """
    index: dict[tuple[str, str], Path] = {}
    for element in ELEMENTS:
        base = ANNOTATIONS / "starting_spans" / element
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.ann")):
            pmid = path.name.split(".")[0]
            key = (element, pmid)
            current = index.get(key)
            if current is None or ("gold" in current.parts and "gold" not in path.parts):
                index[key] = path
    return index


def build(limit: int | None = None, require_spans: bool = True) -> list[dict[str, Any]]:
    """Liefert Records im einheitlichen Schema."""
    pmids = available_pmids()
    if not pmids:
        raise FileNotFoundError(f"Keine Tokendateien unter {DOCUMENTS}")
    index = annotation_index()

    records: list[dict[str, Any]] = []
    for pmid in pmids:
        token_path = DOCUMENTS / f"{pmid}.tokens"
        tokens = [t for t in token_path.read_text(encoding="utf-8").splitlines() if t != ""]
        text_path = DOCUMENTS / f"{pmid}.text"
        if not text_path.exists():
            text_path = DOCUMENTS / f"{pmid}.txt"
        text_chars = len(text_path.read_text(encoding="utf-8", errors="replace")) if text_path.exists() else None

        spans: list[dict[str, Any]] = []
        split = None
        for element in ELEMENTS:
            match = index.get((element, pmid))
            if match is None:
                continue
            split = split or split_of(match)
            labels = _read_labels(match)
            if len(labels) != len(tokens):
                continue
            hier_candidates = sorted((ANNOTATIONS / "hierarchical_labels" / element).rglob(f"{pmid}.AGGREGATED.ann"))
            same_split = [p for p in hier_candidates if split_of(p) == split_of(match)]
            hier_candidates = same_split or [p for p in hier_candidates if "gold" not in p.parts] or hier_candidates
            hier_path = hier_candidates[0] if hier_candidates else None
            detailed = HIERARCHICAL[element] if hier_path is not None else None
            hier_labels = _read_labels(hier_path) if hier_path is not None else None
            spans.extend(_spans(labels, tokens, element, detailed, hier_labels))

        if require_spans and not spans:
            continue
        records.append(
            {
                "record_id": f"{DATASET}:{pmid}",
                "dataset": DATASET,
                "task": "pico_span",
                "document": {
                    "id": pmid,
                    "kind": "abstract_text",
                    "path": rel(text_path) if text_path.exists() else "",
                    "split": split,
                    "text_chars": text_chars,
                },
                "context": {"intervention": None, "comparator": None, "outcome": None, "outcome_type": None},
                "gold": {"cells": [], "label": None, "spans": spans},
                "provenance": {
                    "source_file": rel(token_path),
                    "source_id": pmid,
                    "dataset_version": VERSION,
                },
                "issues": ["spans_in_tokenindizes"],
            }
        )
        if limit is not None and len(records) >= limit:
            break
    return records
