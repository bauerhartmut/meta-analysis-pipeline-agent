#!/usr/bin/env python
"""Stufe 2 auf yun2024:523 mit dem Satz-Locator und der Auflage: erstes Wertepaar.

Der Satz aus `predictions_satz_523_16632.jsonl` berichtet zwei Evaluationen je
Arm. Gelesen werden soll nur die erste (Zielzeitpunkt des Records), also je Arm
ein Mittelwert und eine Standardabweichung - vier Zellen.

Budget 16.632 (gemessener Fertig-Punkt), Abbruchkriterium wie zuvor:
`content_chars == 0` oder `finish_reason == "length"`. Bewertung gegen Gold mit
der Logik aus `vergleiche_20261120.py` (Feld + Arm, 1:1-Verbrauch).

Aufruf:
    .venv/bin/python .../zweistufig_stufe2_satz_20261120.py --dry-run
    .venv/bin/python .../zweistufig_stufe2_satz_20261120.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import run_extended_extraction as rx  # noqa: E402
import vergleiche_20261120 as v  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402
from zweistufig_trocken_20261120 import baue_fall  # noqa: E402

RECORD_ID = "yun2024:523"
LOCATORS = HIER / "zweistufig_lauf_20261120" / "predictions_satz_523_16632.jsonl"
AUSGABE = HIER / "zweistufig_lauf_20261120" / "predictions_stufe2_satz_523_16632.jsonl"
MODELL = "glm"
BUDGET = 16632
PROMPT_LABEL = "stage2_satz_erstes_paar"

STAGE2_SYSTEM = (
    "You read numbers from a randomised controlled trial publication at a sentence "
    "named by a previous step. You answer with a single JSON object and nothing else. "
    "You never compute, convert, round or estimate values."
)


def lade_satz(pfad: Path, rid: str) -> dict[str, Any]:
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        row = json.loads(zeile)
        if row.get("record_id") == rid:
            satz = next((l["satz"] for l in row["locators"] if l.get("satz")), "")
            if not satz:
                raise SystemExit(f"kein Satz-Locator fuer {rid}")
            return {"satz": satz, "locators": row["locators"]}
    raise SystemExit(f"keine Zeile fuer {rid} in {pfad}")


def build_prompt(fall: dict[str, Any], context: dict[str, Any], satz: str) -> str:
    return (
        f"Publication excerpt:\n{fall['ausschnitt_text']}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: continuous\n"
        f'Target time point (binding): "{fall["timepoint_target"]}".\n\n'
        "A previous step located this sentence, copied verbatim:\n"
        f'"{satz}"\n\n'
        "In that sentence each arm is reported twice: the first value is the first "
        "evaluation, the second value is the second evaluation. The target is the "
        "FIRST evaluation only. The intervention arm appears as \"feedback receivers\", "
        "the comparator arm as \"others\".\n\n"
        "Read for each arm the mean and the standard deviation of the FIRST evaluation. "
        "Copy the numbers exactly as printed; do not convert, compute, round or fall back "
        "to the second evaluation. If a value is not printed, omit its cell.\n\n"
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "intervention_mean" | "intervention_standard_deviation" | '
        '"comparator_mean" | "comparator_standard_deviation", "arm": "intervention" | '
        '"comparator", "value": <number>}, ...], '
        '"quote": "<the fragment of the sentence you read>"}\n'
        "No commentary, markdown or code fences."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--out", default=AUSGABE.name)
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[RECORD_ID]
    context = record.get("context") or {}
    fall = baue_fall(RECORD_ID, record)
    stufe1 = lade_satz(LOCATORS, RECORD_ID)
    prompt = build_prompt(fall, context, stufe1["satz"])
    gold = (record.get("gold") or {}).get("cells") or []

    print(f"{RECORD_ID}: Satz {len(stufe1['satz'])} Zeichen, Prompt {len(prompt)} Zeichen, "
          f"Budget {args.budget}")
    if args.dry_run:
        print("Satz:", stufe1["satz"][:200])
        return 0

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    modell = dict(rx.MODELS[MODELL])
    modell["max_tokens"] = args.budget
    original = rx.SYSTEM
    try:
        rx.SYSTEM = STAGE2_SYSTEM
        antwort = rx.call(modell, prompt, key, base, attempts=3)
    finally:
        rx.SYSTEM = original

    inhalt = antwort.get("content") or ""
    finish = antwort.get("finish_reason") or ""
    zellen, parse_fehler = rx.parse_cells(inhalt) if inhalt else ([], "leer")
    abgebrochen = (len(inhalt) == 0) or finish == "length"

    bilanz = v.bilanz_p5(gold, zellen)
    quote_ok = v.quote(bilanz["tp"], bilanz["fp"], bilanz["fn"])
    zahlen, _, _ = zahlen_im_text(fall["ausschnitt_text"])
    for zelle in zellen:
        wert = v.zahl(zelle.get("value"))
        zelle["im_ausschnitt"] = bool(wert is not None and zahlen.get(round(float(wert), 6), 0))

    zeile = {
        "record_id": RECORD_ID,
        "stufe": 2,
        "variante": PROMPT_LABEL,
        "model": MODELL,
        "model_id": modell["id"],
        "prompt_zeichen": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "max_tokens": args.budget,
        "status": "abgebrochen" if abgebrochen else "ok",
        "abbruchkriterium": "content_chars == 0 oder finish_reason == length",
        "http_status": antwort.get("http_status"),
        "finish_reason": finish,
        "completion_tokens": antwort.get("completion_tokens"),
        "reasoning_chars": antwort.get("reasoning_chars"),
        "content_chars": len(inhalt),
        "elapsed_s": antwort.get("elapsed_s"),
        "parse_fehler": parse_fehler,
        "satz": stufe1["satz"],
        "cells": zellen,
        "bewertung": {**bilanz, **quote_ok},
        "goldzellen": len(gold),
        "content": inhalt,
        "fehler": antwort.get("error") or "",
    }
    ziel = HIER / "zweistufig_lauf_20261120" / args.out
    with ziel.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    print(f"  -> {zeile['status']}, finish {finish}, {zeile['completion_tokens']} Tokens, "
          f"{zeile['content_chars']} Zeichen, {len(zellen)} Zellen")
    print(f"     TP {bilanz['tp']} FP {bilanz['fp']} FN {bilanz['fn']} "
          f"P {quote_ok['precision']} R {quote_ok['recall']} F1 {quote_ok['f1']}")
    for zelle in zellen:
        print(f"     {zelle.get('field')}: {zelle.get('value')} im_ausschnitt={zelle['im_ausschnitt']}")
    print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
