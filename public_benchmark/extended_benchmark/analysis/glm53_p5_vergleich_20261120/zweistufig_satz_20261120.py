#!/usr/bin/env python
"""Stufe 1 als Satz-Locator: gibt den berichtenden Satz woertlich zurueck.

Unterschied zur Fassung mit Zeilenlabel: verlangt wird der Satz, der das Outcome
zum Zielzeitpunkt berichtet (bei Tabellen stattdessen das Zeilenlabel). Damit
passt das Schema auch auf Abstract-Text, in dem mehrere Wertepaare in einer
Kommaliste stehen - dort existiert kein einzelnes Zeilenlabel.

Ein Aufruf, Budget 16.632 (gemessener Fertig-Punkt aus dem 559er Ankerlauf),
festes Abbruchkriterium: `content_chars == 0` oder `finish_reason == "length"`.

Geprueft wird offline: steht der zurueckgegebene Satz woertlich im Ausschnitt,
und enthaelt er die Zielwerte des Goldes?

Aufruf:
    .venv/bin/python .../zweistufig_satz_20261120.py --dry-run
    .venv/bin/python .../zweistufig_satz_20261120.py --record yun2024:523
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
from zweistufig_trocken_20261120 import STAGE1_SYSTEM, baue_fall  # noqa: E402

MODELL = "glm"
BUDGET = 16632
PROMPT_LABEL = "stage1_satz"

PROMPT_REGELN = (
    "Locate where the outcome is reported for both arms at the target time point.\n"
    "Do not extract, convert or interpret values; only locate.\n"
    "Copy verbatim, exactly as printed: the sentence that reports the values for that "
    "arm, or - if the values are printed in a table - the row label of that table row.\n"
    "If one sentence reports the values for both arms, return that sentence for both.\n"
    "If neither a sentence nor a table row reports the outcome at the target time point, "
    'set "found": false, leave the labels empty and do not switch to another time point.\n'
    "Answer without weighing alternative readings.\n\n"
    "Return exactly one JSON object:\n"
    '{"locators": [{"arm": "intervention" | "comparator", '
    '"satz": "<verbatim sentence, empty if the arm is a table row>", '
    '"zeilenlabel": "<row label as printed, empty if it is a sentence>", '
    '"spaltenkopf": "<column header as printed, or empty>", '
    '"caption": "<caption or paragraph label>", "timepoint": "<as printed>", '
    '"found": true}, ...]}\n'
    "No commentary, markdown or code fences."
)


def build_satz_prompt(ausschnitt: str, context: dict[str, Any], target: str) -> str:
    return (
        f"Publication excerpt:\n{ausschnitt}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n"
        f'Target time point (binding): "{target}".\n\n'
        f"{PROMPT_REGELN}"
    )


def parse_satz(inhalt: str) -> tuple[list[dict[str, Any]], str | None]:
    """Liest die Locators aus der Antwort; gibt (locators, fehler) zurueck."""
    if not inhalt.strip():
        return [], "leer"
    try:
        daten, fehler = rx._load_payload(inhalt)
    except Exception as exc:  # noqa: BLE001 - Rohantwort bleibt im JSON erhalten
        return [], f"payload: {exc}"
    if not isinstance(daten, dict):
        return [], fehler or "kein objekt"
    roh = daten.get("locators")
    if not isinstance(roh, list) or not roh:
        return [], "keine locators"
    locators = []
    for eintrag in roh:
        if not isinstance(eintrag, dict):
            continue
        locators.append({
            "arm": str(eintrag.get("arm") or "").strip(),
            "satz": str(eintrag.get("satz") or "").strip(),
            "zeilenlabel": str(eintrag.get("zeilenlabel") or "").strip(),
            "spaltenkopf": str(eintrag.get("spaltenkopf") or "").strip(),
            "caption": str(eintrag.get("caption") or "").strip(),
            "timepoint": str(eintrag.get("timepoint") or "").strip(),
            "found": bool(eintrag.get("found")),
        })
    return locators, None


def normalisiere(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def pruefe(locators: list[dict[str, Any]], ausschnitt: str, gold: list[dict[str, Any]]) -> None:
    """Setzt je Locator die Pruefmerker, ohne das Gold zu veraendern."""
    aus_norm = normalisiere(ausschnitt)
    werte = [float(z["value"]) for z in gold if z.get("value") is not None]
    for loc in locators:
        satz = loc["satz"]
        satz_norm = normalisiere(satz)
        loc["satz_im_ausschnitt"] = bool(satz_norm) and satz_norm in aus_norm
        loc["satz_zeichen"] = len(satz)
        loc["zielwerte_im_satz"] = sorted({w for w in werte if re.search(
            r"(?<![\d.])" + re.escape(str(w)) + r"(?![\d])", satz)})
        loc["zeilenlabel_im_ausschnitt"] = bool(loc["zeilenlabel"]) and \
            normalisiere(loc["zeilenlabel"]) in aus_norm


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--record", default="yun2024:523")
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--out", default="predictions_satz_523_16632.jsonl")
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[args.record]
    fall = baue_fall(args.record, record)
    context = record.get("context") or {}
    prompt = build_satz_prompt(fall["ausschnitt_text"], context, fall["timepoint_target"])
    gold = record.get("gold", {}).get("cells") or []

    print(f"{args.record}: Prompt {len(prompt)} Zeichen (Ausschnitt {len(fall['ausschnitt_text'])}, "
          f"Zusatz {len(prompt) - len(fall['ausschnitt_text'])}), Budget {args.budget}")
    if args.dry_run:
        print("--- Prompt-Ende ---")
        print(prompt[-(len(PROMPT_REGELN) + 200):])
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
        rx.SYSTEM = STAGE1_SYSTEM
        antwort = rx.call(modell, prompt, key, base, attempts=3)
    finally:
        rx.SYSTEM = original

    inhalt = antwort.get("content") or ""
    finish = antwort.get("finish_reason") or ""
    locators, parse_fehler = parse_satz(inhalt)
    pruefe(locators, fall["ausschnitt_text"], gold)
    abgebrochen = (len(inhalt) == 0) or finish == "length"

    zeile = {
        "record_id": args.record,
        "stufe": 1,
        "variante": PROMPT_LABEL,
        "model": MODELL,
        "model_id": modell["id"],
        "prompt_zeichen": len(prompt),
        "ausschnitt_zeichen": len(fall["ausschnitt_text"]),
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
        "locators": locators,
        "goldzellen": len(gold),
        "content": inhalt,
        "fehler": antwort.get("error") or "",
    }
    ziel = HIER / "zweistufig_lauf_20261120" / args.out
    with ziel.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    print(f"  -> {zeile['status']}, finish {finish}, {zeile['completion_tokens']} Tokens, "
          f"{zeile['content_chars']} Zeichen, {len(locators)} Locators")
    for loc in locators:
        print(f"     {loc['arm']}: satz_im_ausschnitt={loc['satz_im_ausschnitt']} "
              f"zielwerte={loc['zielwerte_im_satz']} timepoint={loc['timepoint']!r}")
        print(f"       {loc['satz'][:160]!r}")
    print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
