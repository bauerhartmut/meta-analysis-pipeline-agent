#!/usr/bin/env python
"""Stufe 2 auf dem Tabellen-Locator von yun2024:30.

Stufe 1 hat die Zeile `Mean score (SD)` benannt (Variante
`stage1_tabelle_prosa_zeile`, 8.003 Tokens). Stufe 2 liest aus genau dieser
Zeile die Werte des Zielzeitpunkts: je Arm Mittelwert, Standardabweichung und
Gruppengroesse, sechs Zellen.

Die Zeile traegt neun Wertepaare, weil die Tabelle drei Zeitpunktbloecke
(Week 12, Week 24, Week 52) mit je drei Armspalten hintereinander druckt.
Welcher Block der Zielzeitpunkt ist, steht in der Kopfzeile. Offline wird diese
Zuordnung nachgerechnet (`wochenblock`), bevor der Aufruf startet: die
Goldwerte muessen im Block des Zielzeitpunkts liegen.

Abbruchkriterium wie zuvor: `content_chars == 0` oder `finish_reason ==
"length"`; ein Transportfehler wird als `status = fehler` geschrieben und nicht
als Abbruch gezaehlt. Bewertung gegen Gold mit der Logik aus
`vergleiche_20261120.py` (Feld + Arm, 1:1-Verbrauch).

Aufruf:
    .venv/bin/python .../zweistufig_stufe2_zeile_20261120.py --dry-run
    .venv/bin/python .../zweistufig_stufe2_zeile_20261120.py --budget 8000
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
from aufruf_20261120 import lesezeit  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402
from zweistufig_trocken_20261120 import baue_fall  # noqa: E402

RECORD_ID = "yun2024:30"
LOCATORS = (HIER / "zweistufig_lauf_20261120"
            / "predictions_tabelle_zeile_30_qwen_16000.jsonl")
AUSGABE = (HIER / "zweistufig_lauf_20261120"
           / "predictions_stufe2_zeile_30_qwen_8000.jsonl")
MODELL = "qwen"
BUDGET = 8000
PROMPT_LABEL = "stage2_zeile_wochenblock"

#: Arme in Druckreihenfolge je Block (aus der Kopfzeile der Tabelle).
ARME = ("CZP 200 mg + MTX", "CZP 400 mg + MTX", "PBO + MTX")
WOCHEN = ("Week 12", "Week 24", "Week 52")
PAAR = re.compile(r"(-?\d+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*\)")

STAGE2_SYSTEM = (
    "You read numbers from a randomised controlled trial publication at a table "
    "row named by a previous step. You answer with a single JSON object and "
    "nothing else. You never compute, convert, round or estimate values."
)


def lade_locator(pfad: Path, rid: str) -> dict[str, Any]:
    treffer = [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines()
               if z.strip()]
    zeilen = [r for r in treffer if r.get("record_id") == rid]
    if not zeilen:
        raise SystemExit(f"keine Stufe-1-Zeile fuer {rid} in {pfad}")
    return zeilen[-1]


def baue_ausschnitt(text: str, start: int, label: str) -> dict[str, Any]:
    """Kopfzeilen (Wochen, Arme, n) und die benannte Zeile als Ausschnitt."""
    row_pos = text.find(label, start)
    if row_pos < 0:
        raise SystemExit(f"Zeilenlabel {label!r} nicht ab {start} gefunden")
    m = re.search(r"Week\s*12.*?Week\s*52", text[:row_pos])
    wochen = " ".join(m.group(0).split()) if m else ""
    kopf_pos = text.find("CZP 200 mg", max(0, row_pos - 1500))
    if kopf_pos < 0:
        raise SystemExit("Spaltenkopf nicht vor der Zeile gefunden")
    kopf = "\n".join(zeile.strip() for zeile in
                     text[kopf_pos:row_pos].splitlines() if zeile.strip())
    ende = row_pos + 400
    naechste = re.search(r"\bMean (?:change|score)\b", text[row_pos + len(label):ende])
    if naechste:
        ende = row_pos + len(label) + naechste.start()
    zeile = text[row_pos:ende].strip()
    ausschnitt = "\n\n".join(t for t in (wochen, kopf, zeile) if t)
    return {"ausschnitt_text": ausschnitt, "wochenzeile": wochen,
            "kopf": kopf, "zeile": zeile, "row_pos": row_pos}


def wochenblock(zeile: str, gold: list[dict[str, Any]]) -> dict[str, Any]:
    """Rechnet die neun Wertepaare der Zeile auf Bloecke und Arme um."""
    paare = PAAR.findall(zeile)
    raster = []
    for i, (mean, sd) in enumerate(paare[:len(WOCHEN) * len(ARME)]):
        raster.append({"woche": WOCHEN[i // len(ARME)], "arm": ARME[i % len(ARME)],
                       "mean": float(mean), "sd": float(sd)})
    treffer = []
    for zelle in gold:
        if zelle.get("field") not in ("intervention_mean", "comparator_mean"):
            continue
        wert = float(zelle["value"])
        passt = [r for r in raster if abs(r["mean"] - wert) < 1e-9]
        treffer.append({"field": zelle["field"], "value": wert,
                        "bloecke": sorted({r["woche"] for r in passt}),
                        "arme": sorted({r["arm"] for r in passt})})
    return {"paare": len(paare), "raster": raster, "goldtreffer": treffer}


def build_prompt(ausschnitt: dict[str, Any], fall: dict[str, Any],
                 context: dict[str, Any], int_loc: dict[str, Any],
                 cmp_loc: dict[str, Any]) -> str:
    ziel = str(int_loc.get("timepoint") or fall.get("timepoint_target") or "")
    caption = str(int_loc.get("caption") or "")
    return (
        f"Publication excerpt (one table: header rows, then one row):\n"
        f"{ausschnitt['ausschnitt_text']}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: continuous\n"
        f'Target time point (binding): "{ziel}".\n\n'
        "A previous step located the outcome in row "
        f"\"{int_loc.get('zeilenlabel')}\" with column header "
        f"\"{int_loc.get('spaltenkopf')}\" (intervention arm) and "
        f"\"{cmp_loc.get('spaltenkopf')}\" (comparator arm)"
        + (f", caption \"{caption}\"" if caption else "")
        + ".\n\n"
        "The header row prints the same three arm columns three times, once per "
        "time point, in the order Week 12, Week 24, Week 52, together with the "
        "group size of each arm. Read only the block of the binding target time "
        "point and only the located row.\n\n"
        "Read for each arm the mean, the standard deviation and the group size as "
        "printed. Copy the numbers exactly as printed; do not convert, compute, "
        "round, average across blocks or read a change row. If a value is not "
        "printed, omit its cell.\n\n"
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "intervention_mean" | "intervention_standard_deviation" '
        '| "intervention_group_size" | "comparator_mean" | '
        '"comparator_standard_deviation" | "comparator_group_size", '
        '"arm": "intervention" | "comparator", "value": <number>}, ...], '
        '"quote": "<the printed row you read>", '
        '"block": "<time point of the block you read>"}\n'
        "No commentary, markdown or code fences."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--record", default=RECORD_ID)
    parser.add_argument("--locators", default=str(LOCATORS))
    parser.add_argument("--out", default=AUSGABE.name)
    parser.add_argument("--model", default=MODELL, choices=sorted(rx.MODELS))
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--timeout", type=float, default=420.0)
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[args.record]
    context = record.get("context") or {}
    gold = (record.get("gold") or {}).get("cells") or []
    fall = baue_fall(args.record, record)
    stufe1 = lade_locator(Path(args.locators), args.record)
    locators = stufe1.get("locators") or []
    int_loc = next((l for l in locators if l.get("arm") == "intervention"), {})
    cmp_loc = next((l for l in locators if l.get("arm") == "comparator"), {})
    label = str(int_loc.get("zeilenlabel") or "").strip()
    if not label:
        raise SystemExit("Stufe-1-Locator ohne Zeilenlabel")

    text = (ROOT / (record.get("document") or {}).get("path", "")).read_text(
        encoding="utf-8", errors="replace")
    start = (stufe1.get("stuecke") or [[0, 0]])[-1][0]
    ausschnitt = baue_ausschnitt(text, start, label)
    block = wochenblock(ausschnitt["zeile"], gold)
    prompt = build_prompt(ausschnitt, fall, context, int_loc, cmp_loc)

    print(f"{args.record}: Zeile {label!r}, Zeitpunkt {int_loc.get('timepoint')!r}, "
          f"Prompt {len(prompt)} Zeichen, Budget {args.budget}")
    print(f"  Ausschnitt {len(ausschnitt['ausschnitt_text'])} Zeichen, "
          f"{block['paare']} Wertepaare in der Zeile")
    for r in block["raster"]:
        print(f"   {r['woche']:8s} {r['arm']:18s} {r['mean']:6.1f} (SD {r['sd']:4.1f})")
    for t in block["goldtreffer"]:
        print(f"  Gold {t['field']} {t['value']}: Block {t['bloecke']}, Arm {t['arme']}")
    if args.dry_run:
        print("--- Ausschnitt ---")
        print(ausschnitt["ausschnitt_text"])
        return 0

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    modell = dict(rx.MODELS[args.model])
    modell["max_tokens"] = args.budget
    original = rx.SYSTEM
    try:
        with lesezeit(args.timeout):
            rx.SYSTEM = STAGE2_SYSTEM
            antwort = rx.call(modell, prompt, key, base, attempts=3)
    finally:
        rx.SYSTEM = original

    inhalt = antwort.get("content") or ""
    finish = antwort.get("finish_reason") or ""
    zellen, parse_fehler = rx.parse_cells(inhalt) if inhalt else ([], "leer")
    payload, _ = rx._load_payload(inhalt) if inhalt else (None, "")
    roh = payload.get("cells") if isinstance(payload, dict) else None
    leere_liste = isinstance(roh, list) and not roh
    if leere_liste and not zellen:
        parse_fehler = ""
    zitat = str(payload.get("quote") or "").strip() if isinstance(payload, dict) else ""
    gelesener_block = str(payload.get("block") or "").strip() if isinstance(
        payload, dict) else ""

    abgebrochen = (len(inhalt) == 0) or finish == "length"
    transport_fehler = bool(antwort.get("error")) or antwort.get("completion_tokens") is None
    status = "fehler" if transport_fehler else ("abgebrochen" if abgebrochen else "ok")

    bilanz = v.bilanz_p5(gold, zellen)
    quote_ok = v.quote(bilanz["tp"], bilanz["fp"], bilanz["fn"])
    zahlen, _, _ = zahlen_im_text(ausschnitt["ausschnitt_text"])
    for zelle in zellen:
        wert = v.zahl(zelle.get("value"))
        zelle["im_ausschnitt"] = bool(wert is not None and zahlen.get(round(float(wert), 6), 0))

    zeile = {
        "record_id": args.record,
        "stufe": 2,
        "variante": PROMPT_LABEL,
        "model": args.model,
        "model_id": modell["id"],
        "prompt_zeichen": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "max_tokens": args.budget,
        "timeout_s": args.timeout,
        "status": status,
        "transport_fehler": transport_fehler,
        "abbruchkriterium": "content_chars == 0 oder finish_reason == length",
        "http_status": antwort.get("http_status"),
        "finish_reason": finish,
        "completion_tokens": antwort.get("completion_tokens"),
        "reasoning_chars": antwort.get("reasoning_chars"),
        "content_chars": len(inhalt),
        "elapsed_s": antwort.get("elapsed_s"),
        "parse_fehler": parse_fehler,
        "leere_zellenliste": leere_liste,
        "zitat": zitat,
        "gelesener_block": gelesener_block,
        "zeilenlabel": label,
        "zeitpunkt": int_loc.get("timepoint"),
        "ausschnitt_zeichen": len(ausschnitt["ausschnitt_text"]),
        "wochenblock": block,
        "cells": zellen,
        "bewertung": {**bilanz, **quote_ok},
        "goldzellen": len(gold),
        "content": inhalt,
        "fehler": antwort.get("error") or "",
    }
    ziel = HIER / "zweistufig_lauf_20261120" / args.out
    with ziel.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    print(f"  -> {status}{'' if not transport_fehler else ' (' + str(zeile['fehler'])[:80] + ')'}, "
          f"finish {finish}, {zeile['completion_tokens']} Tokens, "
          f"{zeile['content_chars']} Zeichen, {len(zellen)} Zellen, "
          f"Block {gelesener_block!r}")
    print(f"     TP {bilanz['tp']} FP {bilanz['fp']} FN {bilanz['fn']} "
          f"P {quote_ok['precision']} R {quote_ok['recall']} F1 {quote_ok['f1']}")
    for zelle in zellen:
        print(f"     {zelle.get('field')}: {zelle.get('value')} "
              f"im_ausschnitt={zelle['im_ausschnitt']}")
    print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
