#!/usr/bin/env python
"""Stufe 2: liest die Zellen aus dem Satz, den Stufe 1 zitiert hat.

Der Satz aus Stufe 1 berichtet je Arm zwei Wertepaare (zwei Evaluationen bzw.
zwei Schnittstellen). Gelesen werden soll nur das erste, also je Arm ein
Mittelwert und eine Standardabweichung - vier Zellen. Die Zuordnung des Zitats
zur Stufe-1-Prediction kommt ueber `--locators`.

Budget standardmaessig 16.632 (gemessener Fertig-Punkt), Abbruchkriterium wie
zuvor: `content_chars == 0` oder `finish_reason == "length"`. Ein 503 oder
Timeout ist kein Abbruch am Tokenlimit und wird als `status = fehler` mit
`transport_fehler = true` geschrieben. Eine **bewusst leere Zellenliste**
(`{"cells": [], "quote": ...}`) ist dagegen eine inhaltliche Antwort: sie wird
mit `inhaltliche_antwort = true`, `leere_zellenliste = true` und leerem
`parse_fehler` geschrieben, damit spaetere Zaehlungen sie nicht als Abbruch
lesen. Bewertung gegen Gold mit der Logik aus `vergleiche_20261120.py`
(Feld + Arm, 1:1-Verbrauch).

Aufruf (Vorgabe = yun2024:523, glm, erstes Wertepaar):
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
from aufruf_20261120 import lesezeit  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402
from zweistufig_trocken_20261120 import baue_fall  # noqa: E402

RECORD_ID = "yun2024:523"
LOCATORS = HIER / "zweistufig_lauf_20261120" / "predictions_satz_523_16632.jsonl"
AUSGABE = HIER / "zweistufig_lauf_20261120" / "predictions_stufe2_satz_523_16632.jsonl"
MODELL = "glm"
BUDGET = 16632
PROMPT_LABEL = "stage2_satz_erstes_paar"  # Zellenliste; leer = inhaltliche Antwort
#: Der Satz von 523 nennt die Arme nicht mit den Kontextnamen; der Hinweis
#: musste deshalb gesetzt werden. Vorgabe haelt den 523er Prompt byte-gleich.
ARM_HINWEIS = (
    'The intervention arm appears as "feedback receivers", the comparator arm as '
    '"others".'
)

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


def build_prompt(
    fall: dict[str, Any], context: dict[str, Any], satz: str, arm_hinweis: str,
    paare: int = 2,
) -> str:
    if paare == 2:
        # Satz mit zwei Wertepaaren je Arm (523, 420): das erste Paar ist das Ziel.
        sachverhalt = (
            "In that sentence each arm is reported twice: the first value is the first "
            "evaluation, the second value is the second evaluation. The target is the "
            "FIRST evaluation only. "
            f"{arm_hinweis}\n\n"
            "Read for each arm the mean and the standard deviation of the FIRST evaluation. "
            "Copy the numbers exactly as printed; do not convert, compute, round or fall back "
            "to the second evaluation. If a value is not printed, omit its cell.\n\n"
        )
    else:
        # Satz mit einem Wert je Arm, Arme nur ueber Richtungsworte unterschieden (52).
        sachverhalt = (
            "In that sentence each arm is reported once. The order of the numbers and the "
            "direction words of the sentence state which period each printed value belongs "
            "to. "
            f"{arm_hinweis}\n\n"
            "Read for each arm the mean as printed. Copy the numbers exactly as printed; do "
            "not convert, compute, round, swap the arms or infer a value that is not "
            "printed. If a value is not printed, omit its cell.\n\n"
        )
    return (
        f"Publication excerpt:\n{fall['ausschnitt_text']}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: continuous\n"
        f'Target time point (binding): "{fall["timepoint_target"]}".\n\n'
        "A previous step located this sentence, copied verbatim:\n"
        f'"{satz}"\n\n'
        f"{sachverhalt}"
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
    parser.add_argument("--record", default=RECORD_ID)
    parser.add_argument("--locators", default=str(LOCATORS))
    parser.add_argument("--model", default=MODELL, choices=sorted(rx.MODELS))
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--out", default=AUSGABE.name)
    parser.add_argument("--arm-hinweis", default=ARM_HINWEIS,
                        help="Satz, der die Armnamen des Zitats den Kontextarmen zuordnet")
    parser.add_argument("--paare", type=int, default=2, choices=(1, 2),
                        help="Wertepaare je Arm im Satz: 2 = erstes Paar zaehlt (523, 420), "
                             "1 = ein Wert je Arm, Arme nur ueber Richtungsworte (52)")
    parser.add_argument("--timeout", type=float, default=300.0,
                        help="Socket-Lesezeit je HTTP-Versuch in Sekunden")
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[args.record]
    context = record.get("context") or {}
    fall = baue_fall(args.record, record)
    stufe1 = lade_satz(Path(args.locators), args.record)
    prompt = build_prompt(fall, context, stufe1["satz"], args.arm_hinweis, args.paare)
    gold = (record.get("gold") or {}).get("cells") or []

    print(f"{args.record}: Satz {len(stufe1['satz'])} Zeichen, Prompt {len(prompt)} Zeichen, "
          f"Modell {args.model}, Budget {args.budget}, Lesezeit {args.timeout:.0f}s")
    if args.dry_run:
        print("Satz:", stufe1["satz"][:200])
        print("Prompt-Ende:", prompt[-320:])
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
    # `rx.parse_cells` meldet eine *bewusst leere* Zellenliste genauso wie eine
    # unbrauchbare Antwort ("keine_verwertbaren_zellen"). Fuer die Auswertung ist
    # das der Unterschied zwischen "kein Abbruch, aber nichts zu lesen" und
    # "Antwort nicht lesbar" - auf yun2024:119 hat das Modell mit
    # `{"cells": [], "quote": ...}` geantwortet. Der produktive Parser bleibt
    # unangetastet; gekennzeichnet wird hier.
    payload, _ = rx._load_payload(inhalt) if inhalt else (None, "")
    roh_zellen = payload.get("cells") if isinstance(payload, dict) else None
    leere_liste = isinstance(roh_zellen, list) and not roh_zellen
    zitat = str(payload.get("quote") or "").strip() if isinstance(payload, dict) else ""
    if leere_liste and not zellen:
        parse_fehler = ""
    abgebrochen = (len(inhalt) == 0) or finish == "length"
    # 503 oder Timeout ist kein Abbruch am Tokenlimit (siehe Satz-Locator-Runner).
    transport_fehler = bool(antwort.get("error")) or antwort.get("completion_tokens") is None
    status = "fehler" if transport_fehler else ("abgebrochen" if abgebrochen else "ok")

    bilanz = v.bilanz_p5(gold, zellen)
    quote_ok = v.quote(bilanz["tp"], bilanz["fp"], bilanz["fn"])
    zahlen, _, _ = zahlen_im_text(fall["ausschnitt_text"])
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
        "arm_hinweis": args.arm_hinweis,
        "wertepaare_je_arm": args.paare,
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
        # Kennzeichnung fuer spaetere Zaehlungen: eine leere Zellenliste ist eine
        # inhaltliche Antwort, kein Abbruch und kein Parse-Fehler.
        "inhaltliche_antwort": not transport_fehler and not abgebrochen,
        "leere_zellenliste": leere_liste,
        "zitat": zitat,
        "zitat_zeichen": len(zitat),
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

    print(f"  -> {status}{'' if not transport_fehler else ' (kein Modellkontakt: ' + str(zeile['fehler'])[:80] + ')'}, "
          f"{'' if not leere_liste else 'leere Zellenliste (inhaltliche Antwort, kein Abbruch), '}"
          f"finish {finish}, {zeile['completion_tokens']} Tokens, "
          f"{zeile['content_chars']} Zeichen, {len(zellen)} Zellen")
    print(f"     TP {bilanz['tp']} FP {bilanz['fp']} FN {bilanz['fn']} "
          f"P {quote_ok['precision']} R {quote_ok['recall']} F1 {quote_ok['f1']}")
    for zelle in zellen:
        print(f"     {zelle.get('field')}: {zelle.get('value')} im_ausschnitt={zelle['im_ausschnitt']}")
    print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
