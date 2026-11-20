#!/usr/bin/env python
"""Zwei freigegebene Anker-Aufrufe auf yun2024:559 und yun2024:615.

Ein Aufruf je Record, Modell und Budget wie im P5-Lauf (glm, 24.000 Completion-
Tokens), Prompt = `build_prompt` plus Ankerblock aus `tabellenanker_20261120.py`.
Kein Reparaturaufruf, keine Budgeterhoehung.

Festes Abbruchkriterium: eine Antwort gilt als Ausfall, wenn `content_chars == 0`
oder `finish_reason == "length"`. Dann wird die Zeile als `abgebrochen` geschrieben
und der Record nicht erneut angefragt.

Geschrieben wird ausschliesslich unter `anker_lauf_20261120/`. Gold und die
bestehenden Predictions werden nur gelesen.

Aufruf:
    .venv/bin/python .../anker_lauf_20261120.py --dry-run   # ohne Anfrage
    .venv/bin/python .../anker_lauf_20261120.py             # zwei Aufrufe
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
from tabellenanker_20261120 import ANKER  # noqa: E402

AUSGABE = HIER / "anker_lauf_20261120"
IDS = ("yun2024:559", "yun2024:615")
MODELL = "glm"
PROMPT_LABEL = "v2_timepoint_anker"


def lade(pfad: Path) -> list[dict[str, Any]]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def zeile_bewerten(gold: list[dict[str, Any]], zellen: list[dict[str, Any]]) -> dict[str, Any]:
    bilanz = v.bilanz_p5(gold, zellen)
    return {**bilanz, **v.quote(bilanz["tp"], bilanz["fp"], bilanz["fn"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="nur Prompt bauen, keine Anfrage")
    parser.add_argument("--ids", nargs="+", default=list(IDS))
    args = parser.parse_args()

    records = {r["record_id"]: r for r in lade(v.RECORDS)}
    AUSGABE.mkdir(parents=True, exist_ok=True)
    ziel = AUSGABE / "predictions.jsonl"
    fertig = {
        z["record_id"] for z in lade(ziel) if z.get("record_id")
    } if ziel.exists() else set()

    offen = [rid for rid in args.ids if rid in records and rid not in fertig]
    print(f"{len(args.ids)} angefragt, {len(fertig)} schon vorhanden, {len(offen)} offen", flush=True)

    prompts: dict[str, str] = {}
    for rid in offen or [rid for rid in args.ids if rid in records]:
        record = records[rid]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        prompts[rid] = rx.build_prompt(record, text) + ANKER

    if args.dry_run:
        for rid, prompt in prompts.items():
            print(f"DRY-RUN {rid}: {len(prompt)} Zeichen, Goldzellen "
                  f"{len((records[rid].get('gold') or {}).get('cells') or [])}, keine Anfrage")
        return 0

    if not offen:
        print("nichts zu tun")
        return 0

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    modell = dict(rx.MODELS[MODELL])
    for rid in offen:
        prompt = prompts[rid]
        print(f"Anfrage {rid}: {len(prompt)} Zeichen, max_tokens {modell['max_tokens']}", flush=True)
        gestartet = time.monotonic()
        antwort = rx.call(modell, prompt, key, base, attempts=3)
        inhalt = antwort.get("content") or ""
        finish = antwort.get("finish_reason") or ""
        if inhalt:
            zellen, parse_fehler = rx.parse_cells(inhalt)
        else:
            zellen, parse_fehler = [], "leer"
        payload, _ = rx._load_payload(inhalt) if inhalt else (None, "")
        anker = payload.get("anchor") if isinstance(payload, dict) else None
        abgebrochen = (len(inhalt) == 0) or finish == "length"
        gold = (records[rid].get("gold") or {}).get("cells") or []
        zeile = {
            "record_id": rid,
            "model": MODELL,
            "model_id": modell["id"],
            "prompt_version": PROMPT_LABEL,
            "prompt_zeichen": len(prompt),
            "anker_zeichen": len(ANKER),
            "status": "abgebrochen" if abgebrochen else "ok",
            "abbruchkriterium": "content_chars == 0 oder finish_reason == length",
            "http_status": antwort.get("http_status"),
            "finish_reason": finish,
            "completion_tokens": antwort.get("completion_tokens"),
            "reasoning_chars": antwort.get("reasoning_chars"),
            "content_chars": len(inhalt),
            "elapsed_s": antwort.get("elapsed_s"),
            "parse_fehler": parse_fehler,
            "anker": anker,
            "timepoint": payload.get("timepoint") if isinstance(payload, dict) else None,
            "chosen_timepoint": payload.get("chosen_timepoint") if isinstance(payload, dict) else None,
            "cells": zellen,
            "bewertung": zeile_bewerten(gold, zellen),
            "goldzellen": len(gold),
            "content": inhalt,
            "fehler": antwort.get("error") or "",
            "dauer_gesamt_s": round(time.monotonic() - gestartet, 1),
        }
        with ziel.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        print(f"  -> {zeile['status']}, {len(zellen)} Zellen, {zeile['content_chars']} Zeichen, "
              f"finish {finish}, {zeile['completion_tokens']} Completion-Tokens", flush=True)

    print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
