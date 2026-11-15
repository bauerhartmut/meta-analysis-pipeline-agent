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
import uuid
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

# Standard ist die Referenzversion; v3 hat sich im Dev-Lauf nicht belegt und ist
# nur noch per --absolute-counts waehlbar.
PROMPT_VERSION = "v2_timepoint"
VERSION_ABSOLUTE_COUNTS = "v3_abs_count"
VERSION_LAST_TIMEPOINT = "v4_last_timepoint"
RETRY_MAX_TOKENS = 32000
# Wird mit --cache-buster gesetzt; das Gateway liefert sonst die gecachte
# Antwort einer identischen Anfrage zurueck.
SESSION_TAG = ""

SYSTEM = (
    "You extract numerical results from randomised controlled trial publications. "
    "You answer with a single JSON object and nothing else. You never invent values: "
    "if a value is not reported, you omit the cell."
)

LOCK = threading.Lock()


def build_prompt(
    record: dict[str, Any],
    text: str,
    limit: int = 45000,
    absolute_counts: bool = False,
    last_timepoint: bool = False,
) -> str:
    context = record["context"]
    fields = ", ".join(f'"{name}"' for name in FIELDS)
    schema = (
        '{"cells": [{"field": "<field>", "arm": "intervention" | "comparator", "value": <number>}, ...], '
        '"chosen_timepoint": "<label exactly as printed>", '
        '"discarded_timepoints": ["<label exactly as printed>", ...]}'
        if last_timepoint
        else '{"cells": [{"field": "<field>", "arm": "intervention" | "comparator", "value": <number>}, ...]}'
    )
    timepoint_rule = (
        "Use the results measured at the last time point reported for this outcome: the latest "
        "follow-up. If the table reports a cumulative total row or column, use the total. Never use "
        "baseline values. Then state which time point label you used and which other time point "
        "labels you skipped for this outcome, both copied exactly as printed (use \"not applicable\" "
        "if only one time point is reported, \"running text\" if the outcome is only reported in "
        "prose). "
        if last_timepoint
        else "Use the values measured at the end of the intervention (post-test), not baseline values "
        "and not follow-up values from a later measurement point. "
    )
    return (
        f"Publication excerpt:\n{text[:limit]}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n\n"
        "Extract the numerical results that belong to this comparison and outcome. "
        "Return exactly one JSON object:\n"
                    f"{schema}\n"
            f"Allowed fields: {fields}. "
        "Use the arm that the number belongs to: intervention for the experimental arm, comparator for the control arm. "
        + timepoint_rule
        + (
            "Report event counts as absolute numbers of events, never as percentages or rates. "
            if absolute_counts
            else ""
        )
        +
        "Copy numbers exactly as reported; do not convert, do not compute, do not guess. "
        "Omit a cell the paper does not report. "
        "Do not add commentary, markdown or code fences."
    )


def _load_payload(content: str) -> tuple[dict[str, Any] | None, str]:
    """Liest das JSON-Objekt aus der Antwort, auch mit Codefence oder Beiwerk."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None, "kein_json"
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            return None, f"json_fehler: {error}"
    if not isinstance(payload, dict):
        return None, "kein_objet"
    return payload, ""


def parse_timepoints(content: str) -> tuple[dict[str, Any], str]:
    """Liest chosen_timepoint und discarded_timepoints aus der Antwort."""
    payload, error = _load_payload(content)
    if payload is None:
        return {"chosen": "", "discarded": []}, error
    chosen = str(payload.get("chosen_timepoint") or "").strip()
    raw = payload.get("discarded_timepoints")
    discarded: list[str] = []
    if isinstance(raw, list):
        discarded = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str) and raw.strip():
        discarded = [part.strip() for part in raw.split(";") if part.strip()]
    if not chosen:
        return {"chosen": "", "discarded": discarded}, "kein_zeitpunkt"
    return {"chosen": chosen, "discarded": discarded}, ""


def parse_cells(content: str) -> tuple[list[dict[str, Any]], str]:
    """Liest die Zellen aus der Modellantwort; gibt (cells, fehler) zurueck."""
    payload, error = _load_payload(content)
    if payload is None:
        return [], error
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
            {"role": "system", "content": SYSTEM + (f"\nSession tag: {SESSION_TAG}" if SESSION_TAG else "")},
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
            "reasoning_chars": len((choice.get("message") or {}).get("reasoning_content") or ""),
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
    parser.add_argument("--ids", default=None, help="Komma-getrennte record_ids, nur diese laufen")
    parser.add_argument("--save-content", action="store_true", help="Rohantwort im Ergebnis mitspeichern")
    parser.add_argument("--max-tokens", type=int, default=None, help="Tokenbudget fuer alle Modelle ueberschreiben")
    parser.add_argument("--cache-buster", action="store_true", help="eindeutigen Session-Tag in den Systemprompt haengen")
    parser.add_argument("--absolute-counts", action="store_true", help="Prompt-Zusatz aus v3_abs_count aktivieren")
    parser.add_argument(
        "--last-timepoint",
        action="store_true",
        help="letzten berichteten Messzeitpunkt verlangen und Zeitpunkte mitliefern (v4_last_timepoint)",
    )
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("extended_%Y%m%d"))
    args = parser.parse_args()

    models = {name: dict(spec) for name, spec in MODELS.items()}
    if args.max_tokens:
        for spec in models.values():
            spec["max_tokens"] = args.max_tokens

    global SESSION_TAG
    prompt_version = VERSION_ABSOLUTE_COUNTS if args.absolute_counts else PROMPT_VERSION
    if args.last_timepoint:
        prompt_version = VERSION_LAST_TIMEPOINT
    if args.cache_buster:
        SESSION_TAG = uuid.uuid4().hex[:12]
        prompt_version = f"{prompt_version}_cb"

    config = get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    records = load_records(args.split, args.limit)
    if args.ids:
        wanted = {value.strip() for value in args.ids.split(",") if value.strip()}
        records = [record for record in records if record["record_id"] in wanted]
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
        prompt = build_prompt(
            record, text, absolute_counts=args.absolute_counts, last_timepoint=args.last_timepoint
        )
        response = call(models[model], prompt, key, base)
        retry: dict[str, Any] | None = None
        # Reasoning-Schleifen enden mit finish_reason "length" und leerem Inhalt.
        # Ein zweiter Versuch mit groesserem Budget behebt einen Teil davon.
        if response.get("finish_reason") == "length" and models[model]["max_tokens"] < RETRY_MAX_TOKENS:
            retry = call({**models[model], "max_tokens": RETRY_MAX_TOKENS}, prompt, key, base)
            if retry.get("content"):
                response = retry
        cells, parse_error = parse_cells(response.get("content") or "")
        timepoints, timepoint_error = parse_timepoints(response.get("content") or "")
        row = {
            "record_id": record["record_id"],
            "model": model,
            "model_id": models[model]["id"],
            "http_status": response.get("http_status"),
            "error": response.get("error", ""),
            "finish_reason": response.get("finish_reason", ""),
            "completion_tokens": response.get("completion_tokens"),
            "reasoning_chars": response.get("reasoning_chars", 0),
            "suspected_cache": (response.get("elapsed_s") or 0) < 1.0,
            "retried": retry is not None,
            "retry_finish_reason": retry.get("finish_reason", "") if retry else "",
            "retry_tokens": retry.get("completion_tokens") if retry else None,
            "elapsed_s": response.get("elapsed_s"),
            "content_len": len(response.get("content") or ""),
            "parse_error": parse_error,
            "timepoints": timepoints if args.last_timepoint else {},
            "timepoint_error": timepoint_error if args.last_timepoint else "",
            "prompt_version": prompt_version,
            "predicted": {"cells": cells},
            "rows": cells,
        }
        if args.save_content:
            row["content"] = response.get("content") or ""
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
