#!/usr/bin/env python3
"""Netzlauf fuer die mehrstufige Ereignisextraktion (Prototyp, Ansatz C).

Liest die Basisvorhersagen eines vorhandenen Laufs, ersetzt nur die beiden
Ereignisfelder durch die zweistufige Extraktion und schreibt drei Dateien:

* ``stage1.jsonl`` - Zeilenlabel und Spaltenkopf je Arm (Zwischenstufe)
* ``stage2.jsonl`` - gelesene Zahl mit Zitatstelle je Feld (Zwischenstufe)
* ``predictions.jsonl`` - Basisvorhersage mit ersetzten Ereigniszellen

Damit bleiben die Stufen einzeln pruefbar; die Gesamtbewertung steht in
``evaluate_stage_extraction.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import run_extended_extraction as rx  # noqa: E402
from stage_extraction import (  # noqa: E402
    EVENT_FIELDS,
    build_stage1_prompt,
    build_stage2_prompt,
    merge_event_cells,
    parse_stage1,
    parse_stage2,
)

LOCK = threading.Lock()


def load_baseline(run_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    path = run_dir / "predictions.jsonl"
    if not path.exists():
        raise SystemExit(f"FEHLER: Basisvorhersage fehlt: {path}")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[(row["record_id"], row["model"])] = row
    return rows


def append(path: Path, row: dict[str, Any]) -> None:
    with LOCK:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_text(record: dict[str, Any]) -> str:
    path = record["document"].get("path") or ""
    candidate = REPO / path if path else None
    if candidate and candidate.exists():
        return candidate.read_text(encoding="utf-8", errors="replace")
    return ""


def call_with_retry(model: dict[str, Any], prompt: str, key: str, base: str) -> dict[str, Any]:
    response = rx.call(model, prompt, key, base)
    retry = None
    if response.get("finish_reason") == "length" and model["max_tokens"] < rx.RETRY_MAX_TOKENS:
        retry = rx.call({**model, "max_tokens": rx.RETRY_MAX_TOKENS}, prompt, key, base)
        if retry.get("content"):
            response = retry
    response = dict(response)
    response["retried"] = retry is not None
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", default="yun_dev_std_20261115")
    parser.add_argument("--models", nargs="+", default=["glm"], choices=sorted(rx.MODELS))
    parser.add_argument("--split", default="dev")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", default=None, help="Komma-getrennte record_ids")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--cache-buster", action="store_true")
    parser.add_argument("--save-content", action="store_true")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("stage_%Y%m%d"))
    args = parser.parse_args()

    models = {name: dict(spec) for name, spec in rx.MODELS.items()}
    if args.cache_buster:
        rx.SESSION_TAG = uuid.uuid4().hex[:12]
    prompt_version = f"{rx.PROMPT_VERSION}_stage2" + ("_cb" if args.cache_buster else "")

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    baseline = load_baseline(HERE / "runs" / args.baseline_run)
    records = rx.load_records(args.split, args.limit)
    if args.ids:
        wanted = {value.strip() for value in args.ids.split(",") if value.strip()}
        records = [record for record in records if record["record_id"] in wanted]

    run_dir = HERE / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    stage1_path = run_dir / "stage1.jsonl"
    stage2_path = run_dir / "stage2.jsonl"
    out_path = run_dir / "predictions.jsonl"
    done = rx.done_keys(out_path)

    jobs = [
        (record, model)
        for model in args.models
        for record in records
        if (record["record_id"], model) in baseline and (record["record_id"], model) not in done
    ]
    print(
        f"{len(records)} Records, {len(jobs)} offene Auftraege, {args.workers} Threads, "
        f"Basis {args.baseline_run}",
        flush=True,
    )

    def work(record: dict[str, Any], model: str) -> dict[str, Any]:
        rid = record["record_id"]
        text = read_text(record)
        context = record["context"]
        started = time.monotonic()

        stage1 = call_with_retry(models[model], build_stage1_prompt(text, context), key, base)
        locators, stage1_error = parse_stage1(stage1.get("content") or "")
        row1 = {
            "record_id": rid,
            "model": model,
            "prompt_version": prompt_version,
            "http_status": stage1.get("http_status"),
            "error": stage1.get("error", ""),
            "parse_error": stage1_error,
            "elapsed_s": stage1.get("elapsed_s"),
            "retried": stage1.get("retried", False),
            "locators": locators,
        }
        if args.save_content:
            row1["content"] = stage1.get("content") or ""
        append(stage1_path, row1)

        staged: dict[str, float] = {}
        stage2_rows: list[dict[str, Any]] = []
        for field in EVENT_FIELDS:
            arm = "intervention" if field.startswith("intervention") else "comparator"
            locator = next((item for item in locators if item["arm"] == arm and item["found"]), None)
            if locator is None:
                stage2_rows.append({"field": field, "value": None, "quote": "", "found": False, "error": "kein_locator"})
                continue
            prompt = build_stage2_prompt(
                text,
                context,
                arm,
                locator["row_label"],
                locator["column_header"],
                locator["caption"],
            )
            stage2 = call_with_retry(models[model], prompt, key, base)
            value, quote, found, stage2_error = parse_stage2(stage2.get("content") or "")
            if found and value is not None:
                staged[field] = value
            stage2_rows.append(
                {
                    "field": field,
                    "value": value,
                    "quote": quote,
                    "found": found,
                    "error": stage2_error,
                    "http_status": stage2.get("http_status"),
                    "elapsed_s": stage2.get("elapsed_s"),
                    "row_label": locator["row_label"],
                    "column_header": locator["column_header"],
                }
            )
        for item in stage2_rows:
            append(
                stage2_path,
                {"record_id": rid, "model": model, "prompt_version": prompt_version, **item},
            )

        baseline_cells = (baseline[(rid, model)].get("predicted") or {}).get("cells", [])
        merged, replaced, fallback = merge_event_cells(baseline_cells, staged)
        row = {
            "record_id": rid,
            "model": model,
            "model_id": models[model]["id"],
            "http_status": 200 if merged else 0,
            "error": "",
            "finish_reason": "",
            "completion_tokens": None,
            "suspected_cache": False,
            "prompt_version": prompt_version,
            "baseline_run": args.baseline_run,
            "staged_fields": replaced,
            "fallback_fields": fallback,
            "stage1_error": stage1_error,
            "elapsed_s": round(time.monotonic() - started, 2),
            "predicted": {"cells": merged},
            "rows": merged,
        }
        append(out_path, row)
        print(
            f"{model}: {rid} stage1 {len(locators)} locators, ersetzt {len(replaced)}, "
            f"zurueckgefallen {len(fallback)}",
            flush=True,
        )
        return row

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, record, model): (record, model) for record, model in jobs}
        for future in as_completed(futures):
            try:
                future.result()
                completed += 1
            except Exception as error:  # noqa: BLE001 - Lauf soll weiterlaufen
                print(f"FEHLER {futures[future]}: {error}", flush=True)

    print(f"fertig: {completed} Auftraege, Ausgabe {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
