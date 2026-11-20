#!/usr/bin/env python
"""Stufe 2 auf yun2024:525 mit den Locators aus Stufe 1.

Ein Aufruf, Budget 16.632 (gemessener Fertig-Punkt aus dem 559er Ankerlauf),
gleicher Ausschnitt wie Stufe 1. Stufe 2 liest nur noch an der benannten Stelle:
je Arm Mittelwert und Standardabweichung, vier Zellen, keine Umrechnung.

Festes Abbruchkriterium: `content_chars == 0` oder `finish_reason == "length"`.

Geprueft wird gegen das Gold mit derselben Logik wie in `vergleiche_20261120.py`
(Schluessel Feld + Arm, 1:1-Verbrauch) und zusaetzlich, ob jeder gelesene Wert
im Ausschnitt gedruckt steht.

Aufruf:
    .venv/bin/python .../zweistufig_stufe2_20261120.py --dry-run
    .venv/bin/python .../zweistufig_stufe2_20261120.py
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

RECORD_ID = "yun2024:525"
LOCATORS_QUELLE = HIER / "zweistufig_lauf_20261120" / "predictions_16632.jsonl"
AUSGABE = HIER / "zweistufig_lauf_20261120" / "predictions_stufe2_16632.jsonl"
MODELL = "glm"
BUDGET = 16632
PROMPT_LABEL = "stage2_locator"

STAGE2_SYSTEM = (
    "You read numbers from a randomised controlled trial publication at a location "
    "named by a previous step. You answer with a single JSON object and nothing else. "
    "You never compute, convert, round or estimate values."
)


def lade_locators(pfad: Path, rid: str) -> dict[str, Any]:
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        row = json.loads(zeile)
        if row.get("record_id") == rid:
            return row
    raise SystemExit(f"keine Stufe-1-Zeile fuer {rid} in {pfad}")


def build_stage2_prompt(
    fall: dict[str, Any], locators: list[dict[str, Any]], context: dict[str, Any]
) -> str:
    zeile = next((l["row_label"] for l in locators if l.get("row_label")), "")
    int_loc = next((l for l in locators if l.get("arm") == "intervention"), {})
    cmp_loc = next((l for l in locators if l.get("arm") == "comparator"), {})
    caption = str(int_loc.get("caption") or "")
    zeitpunkt = str(int_loc.get("timepoint") or "")
    return (
        f"Publication excerpt:\n{fall['ausschnitt_text']}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: continuous\n"
        f'Target time point (binding): "{fall["timepoint_target"]}".\n\n'
        "A previous step located the outcome in row "
        f'"{zeile}" with columns "{int_loc.get("column_header") or ""}" (intervention arm) '
        f'and "{cmp_loc.get("column_header") or ""}" (comparator arm)'
        + (f', caption "{caption}"' if caption else "")
        + (f', time point "{zeitpunkt}"' if zeitpunkt else "")
        + ".\n\n"
        "Read from exactly that row and those two columns: the mean and the standard "
        "deviation of each arm. Copy the numbers exactly as printed; do not convert, "
        "compute, round or reconstruct them from percentages. If one value is not "
        "printed at that row and column, omit its cell instead of substituting another "
        "row.\n\n"
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "intervention_mean" | "intervention_standard_deviation" | '
        '"comparator_mean" | "comparator_standard_deviation", "arm": "intervention" | '
        '"comparator", "value": <number>}, ...], '
        '"quote": "<the printed row as copied>"}\n'
        "No commentary, markdown or code fences."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--record", default=RECORD_ID)
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[args.record]
    fall = baue_fall(args.record, record)
    stufe1 = lade_locators(LOCATORS_QUELLE, args.record)
    locators = stufe1["locators"]
    prompt = build_stage2_prompt(fall, locators, record.get("context") or {})

    print(f"{args.record}: {len(locators)} Locators, Prompt {len(prompt)} Zeichen, Budget {BUDGET}")
    if args.dry_run:
        print(f"Row: {locators[0].get('row_label')!r}, "
              f"Spalten: {[l.get('column_header') for l in locators]}")
        return 0

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    modell = dict(rx.MODELS[MODELL])
    modell["max_tokens"] = BUDGET
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

    gold = (record.get("gold") or {}).get("cells") or []
    bilanz = v.bilanz_p5(gold, zellen)
    quote_ok = v.quote(bilanz["tp"], bilanz["fp"], bilanz["fn"])

    ausschnitt = fall["ausschnitt_text"]
    zahlen, _, _ = zahlen_im_text(ausschnitt)
    for zelle in zellen:
        wert = v.zahl(zelle.get("value"))
        zelle["im_ausschnitt"] = bool(
            wert is not None and zahlen.get(round(float(wert), 6), 0)
        )

    zeile = {
        "record_id": args.record,
        "stufe": 2,
        "model": MODELL,
        "model_id": modell["id"],
        "prompt_version": PROMPT_LABEL,
        "prompt_zeichen": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "max_tokens": BUDGET,
        "status": "abgebrochen" if abgebrochen else "ok",
        "abbruchkriterium": "content_chars == 0 oder finish_reason == length",
        "http_status": antwort.get("http_status"),
        "finish_reason": finish,
        "completion_tokens": antwort.get("completion_tokens"),
        "reasoning_chars": antwort.get("reasoning_chars"),
        "content_chars": len(inhalt),
        "elapsed_s": antwort.get("elapsed_s"),
        "parse_fehler": parse_fehler,
        "locators": locators,
        "cells": zellen,
        "bewertung": {**bilanz, **quote_ok},
        "goldzellen": len(gold),
        "content": inhalt,
        "fehler": antwort.get("error") or "",
    }
    with AUSGABE.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    print(f"  -> {zeile['status']}, finish {finish}, {zeile['completion_tokens']} Tokens, "
          f"{zeile['content_chars']} Zeichen, {len(zellen)} Zellen")
    print(f"     TP {bilanz['tp']} FP {bilanz['fp']} FN {bilanz['fn']} "
          f"P {quote_ok['precision']} R {quote_ok['recall']} F1 {quote_ok['f1']}")
    for zelle in zellen:
        print(f"     {zelle.get('field')}: {zelle.get('value')} im_ausschnitt={zelle['im_ausschnitt']}")
    print("geschrieben:", AUSGABE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
