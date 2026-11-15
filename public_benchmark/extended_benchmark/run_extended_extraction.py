#!/usr/bin/env python3
"""Extraktionslauf fuer den erweiterten Benchmark (numerische Aufgabe).

Jedes Modell bekommt den Artikeltext und die Liste der gesuchten Felder und
soll Zellen im Format von ``predictions_schema.json`` zurueckgeben. Es wird
nichts nachbearbeitet: Die Modellantwort wird so bewertet, wie sie kommt.

Ausgabe: ``runs/<run_id>/predictions.jsonl`` mit einer Zeile je (Record,
Modell). Ein abgebrochener Lauf wird mit demselben Befehl fortgesetzt.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parent
sys.path.insert(0, str(REPO))

from research_agent.config import get_config  # noqa: E402

RECORDS = HERE / "records" / "yun.jsonl"

MODELS = {
    "qwen30": {"id": "gwdg/qwen3-30b-a3b-instruct-2507", "max_tokens": 8000},
    "glm": {"id": "gwdg/glm-5.3", "max_tokens": 24000},
    "qwen": {"id": "gwdg/qwen3.5-397b-a17b", "max_tokens": 16000},
    "deepseek": {"id": "gwdg/deepseek-v4.1-flash-1017", "max_tokens": 8000},
}

FIELDS = (
    "intervention_group_size",
    "intervention_events",
    "intervention_mean",
    "intervention_standard_deviation",
    "comparator_group_size",
    "comparator_events",
    "comparator_mean",
    "comparator_standard_deviation",
)

PROMPT_VERSION = "v2_timepoint"

SYSTEM = (
    "You extract numerical results from randomised controlled trial publications. "
    "You answer with a single JSON object and nothing else. You never invent values: "
    "if a value is not reported, you omit the cell."
)

LOCK = threading.Lock()


def build_prompt(record: dict[str, Any], text: str, limit: int = 45000) -> str:
    context = record["context"]
    fields = ", ".join(f'"{name}"' for name in FIELDS)
    return (
        f"Publication excerpt:\n{text[:limit]}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n\n"
        "Extract the numerical results that belong to this comparison and outcome. "
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "<field>", "arm": "intervention" | "comparator", "value": <number>}, ...]}\n'
        f"Allowed fields: {fields}. "
        "Use the arm that the number belongs to: intervention for the experimental arm, comparator for the control arm. "
        "Use the values measured at the end of the intervention (post-test), not baseline values "
        "and not follow-up values from a later measurement point. "
        "Copy numbers exactly as reported; do not convert, do not compute, do not guess. "
        "Omit a cell the paper does not report. "
        "Do not add commentary, markdown or code fences."
    )


def parse_cells(content: str) -> tuple[list[dict[str, Any]], str]:
    """Liest die Zellen aus der Modellantwort; gibt (cells, fehler) zurueck."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return [], "kein_json"
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            return [], f"json_fehler: {error}"
    cells = payload.get("cells") if isinstance(payload, dict) else None
    if not isinstance(cells, list):
        return [], "keine_zellen"
    cleaned = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        field = str(cell.get("field") or "").strip()
        arm = str(cell.get("arm") or "").strip() or None
        value = cell.get("value")
        if field not in FIELDS or arm not in ("intervention", "comparator"):
            continue
        try:
            number = float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            continue
        cleaned.append({"field": field, "arm": arm, "value": number})
    return cleaned, "" if cleaned else "keine_verwertbaren_zellen"


def call(model: dict[str, Any], prompt: str, key: str, base: str, attempts: int = 4) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        last = _call_once(model, prompt, key, base)
        status = last.get("http_status")
        if status == 200 and last.get("content"):
            return last
        if status in (429, 500, 502, 503, 504) and attempt < attempts:
            wait = 20 * attempt + random.uniform(0, 5)
            print(f"  {model['id']} {status}, warte {wait:.1f}s (Versuch {attempt})", flush=True)
            time.sleep(wait)
            continue
        return last
    return last or {"http_status": 0, "error": "kein Versuch", "content": ""}


def _call_once(model: dict[str, Any], prompt: str, key: str, base: str) -> dict[str, Any]:
    payload = {
        "model": model["id"],
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": model["max_tokens"],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        return {
            "http_status": exc.code,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": f"HTTPError {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}",
            "content": "",
            "finish_reason": "",
            "completion_tokens": None,
        }
    except Exception as exc:  # noqa: BLE001 - Lauf soll weiterlaufen
        return {
            "http_status": 0,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": f"{type(exc).__name__}: {exc}",
            "content": "",
            "finish_reason": "",
            "completion_tokens": None,
        }
    try:
        data = json.loads(body)
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or ""
        return {
            "http_status": status,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": "",
            "content": content,
            "finish_reason": choice.get("finish_reason", ""),
            "completion_tokens": (data.get("usage") or {}).get("completion_tokens"),
        }
    except json.JSONDecodeError:
        return {
            "http_status": status,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": "antwort_kein_json",
            "content": "",
            "finish_reason": "",
            "completion_tokens": None,
        }


def load_records(split: str | None, limit: int | None) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]
    if split:
        records = [record for record in records if record["document"].get("split") == split]
    if limit:
        records = records[:limit]
    return records


def done_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("rows"):
            keys.add((row["record_id"], row["model"]))
    return keys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen30", "glm"], choices=sorted(MODELS))
    parser.add_argument("--split", default="dev")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("extended_%Y%m%d"))
    args = parser.parse_args()

    config = get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    records = load_records(args.split, args.limit)
    run_dir = HERE / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "predictions.jsonl"
    done = done_keys(out_path)

    jobs = [(record, model) for model in args.models for record in records if (record["record_id"], model) not in done]
    print(f"{len(records)} Records, {len(jobs)} offene Auftraege, {args.workers} Threads", flush=True)

    def work(record: dict[str, Any], model: str) -> dict[str, Any]:
        path = record["document"].get("path") or ""
        text = ""
        if path:
            candidate = REPO / path
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8", errors="replace")
        prompt = build_prompt(record, text)
        response = call(MODELS[model], prompt, key, base)
        cells, parse_error = parse_cells(response.get("content") or "")
        row = {
            "record_id": record["record_id"],
            "model": model,
            "model_id": MODELS[model]["id"],
            "http_status": response.get("http_status"),
            "error": response.get("error", ""),
            "finish_reason": response.get("finish_reason", ""),
            "completion_tokens": response.get("completion_tokens"),
            "elapsed_s": response.get("elapsed_s"),
            "content_len": len(response.get("content") or ""),
            "parse_error": parse_error,
            "prompt_version": PROMPT_VERSION,
            "predicted": {"cells": cells},
            "rows": cells,
        }
        with LOCK:
            with out_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        status = "ok" if cells else f"leer {parse_error}"
        print(f"{model}: {record['record_id']} {status} ({len(cells)} Zellen)", flush=True)
        return row

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, record, model): (record, model) for record, model in jobs}
        for future in as_completed(futures):
            try:
                future.result()
                completed += 1
            except Exception as error:  # noqa: BLE001
                print(f"FEHLER {futures[future]}: {error}", flush=True)

    print(f"fertig: {completed} Auftraege, Ausgabe {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
