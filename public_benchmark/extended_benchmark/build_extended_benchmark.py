#!/usr/bin/env python3
"""Baut den erweiterten Benchmark aus den lokalen Rohdaten.

Erzeugt je Datensatz eine JSONL-Datei im einheitlichen Schema und ein Manifest
mit Zaehlungen, Hashes und Lizenzhinweisen. Es werden keine Werte erfunden und
keine Rohdaten veraendert.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extended_benchmark.adapters import ebm_nlp, evidence_inference, yun  # noqa: E402
from extended_benchmark.adapters.common import digest, write_jsonl  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
REQUIRED = ("record_id", "dataset", "task", "document", "context", "gold", "provenance")

BUILDERS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "yun": lambda limit, frozen: yun.build(include_frozen=frozen, limit=limit),
    "evidence_inference": lambda limit, frozen: evidence_inference.build(limit=limit),
    "ebm_nlp": lambda limit, frozen: ebm_nlp.build(limit=limit),
}

SOURCE_FILES = {
    "yun": [yun.SOURCE_JSON],
    "evidence_inference": [evidence_inference.ANNOTATIONS, evidence_inference.PROMPTS],
    "ebm_nlp": [
        ebm_nlp.ROOT.parent.parent / "downloads" / "ebm_nlp_2_00.tar.gz",
    ],
}

LICENSES = {
    "yun": "Apache-2.0 (Repository und Annotationen); Artikeltexte behalten die PMC-Lizenz je Artikel",
    "evidence_inference": "MIT (Code und Annotationen); Textdateien behalten die PMC-Lizenz je Artikel",
    "ebm_nlp": "EBM-NLP-Nutzungsbedingungen; Abstracts stammen aus PubMed",
}


def validate(records: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for record in records:
        for key in REQUIRED:
            if key not in record:
                problems.append(f"{record.get('record_id', '?')}: Feld fehlt: {key}")
        record_id = record.get("record_id")
        if record_id in seen:
            problems.append(f"doppelte record_id: {record_id}")
        seen.add(record_id)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", default=["yun", "evidence_inference", "ebm_nlp"], choices=sorted(BUILDERS))
    parser.add_argument("--limit", type=int, default=None, help="maximale Records je Datensatz")
    parser.add_argument("--include-frozen-yun", action="store_true", help="gesperrten Yun-Testsplit mit aufnehmen")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR / "records")
    args = parser.parse_args()

    manifest: dict[str, Any] = {
        "created": date.today().isoformat(),
        "schema": "schema.json",
        "datasets": {},
    }
    for name in args.datasets:
        records = BUILDERS[name](args.limit, args.include_frozen_yun)
        problems = validate(records)
        target = args.out_dir / f"{name}.jsonl"
        count = write_jsonl(target, records)
        cells = sum(len(r["gold"]["cells"]) for r in records)
        spans = sum(len(r["gold"]["spans"]) for r in records)
        labels = sum(1 for r in records if r["gold"].get("label"))
        manifest["datasets"][name] = {
            "records": count,
            "gold_cells": cells,
            "gold_spans": spans,
            "records_with_label": labels,
            "with_spans": sum(1 for r in records if r["gold"]["spans"]),
            "articles": len({r["document"]["id"] for r in records if r["document"]["id"]}),
            "splits": _counts(r["document"].get("split") for r in records),
            "tasks": _counts(r["task"] for r in records),
            "output": target.as_posix(),
            "sha256": digest(target) if target.exists() else None,
            "license": LICENSES.get(name, ""),
            "sources": [
                {"path": path.as_posix(), "sha256": digest(path), "bytes": path.stat().st_size}
                for path in SOURCE_FILES.get(name, [])
                if path.exists()
            ],
            "validation_problems": problems[:20],
            "validation_problem_count": len(problems),
        }
        print(f"{name}: {count} Records, {cells} Gold-Zellen, {spans} Spannen, {len(problems)} Probleme")

    manifest_path = args.out_dir.parent / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path}")
    return 0


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
