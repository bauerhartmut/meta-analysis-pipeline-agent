#!/usr/bin/env python
"""Der eine freigegebene Stufe-1-Aufruf auf yun2024:525.

Ein Aufruf, Modell `gwdg/glm-5.3`, Budget 2.000 Completion-Tokens (statt 24.000).
Prompt und Ausschnitt kommen unveraendert aus `zweistufig_trocken_20261120.py`,
Systemtext ist der Locator-Text (keine Zahlen).

Festes Abbruchkriterium: `content_chars == 0` oder `finish_reason == "length"`.
Dann wird die Zeile als `abgebrochen` geschrieben, ohne Wiederholung.

Geprueft wird anschliessend ohne Modell, ob die Locators das dritte
Mittelwert-Paar treffen: das genannte Zeilenlabel muss im Ausschnitt stehen,
und in seiner Umgebung muessen die Zielwerte des jeweiligen Arms (18,53 bzw.
18,99) gedruckt sein.

Aufruf:
    .venv/bin/python .../zweistufig_lauf_20261120.py --dry-run
    .venv/bin/python .../zweistufig_lauf_20261120.py
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
from stage_extraction import parse_stage1  # noqa: E402
from zweistufig_trocken_20261120 import STAGE1_SYSTEM, STAGE1_MAX_TOKENS, baue_fall  # noqa: E402

RECORD_ID = "yun2024:525"
AUSGABE = HIER / "zweistufig_lauf_20261120"
MODELL = "glm"
PROMPT_LABEL = "stage1_ankerlos"
#: Budget des zweiten Aufrufs: der einzige gemessene Punkt, an dem dieses Modell
#: mit vergleichbarem Prompt fertig wurde (yun2024:559 mit Anker, Fassung 1,
#: finish_reason = stop). Keine Schaetzung.
BUDGET_GEMESSEN = 16632


def umgebung(text: str, label: str, breite: int = 400) -> tuple[int, str]:
    """Fenster um das erste Vorkommen des Labels, sonst (-1, '')."""
    stelle = text.lower().find(label.lower()) if label else -1
    if stelle < 0:
        return -1, ""
    return stelle, text[max(0, stelle - breite):stelle + len(label) + breite]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--record", default=RECORD_ID)
    parser.add_argument("--budget", type=int, default=BUDGET_GEMESSEN)
    parser.add_argument("--out", default="predictions.jsonl")
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[args.record]
    fall = baue_fall(args.record, record)
    prompt = fall["prompt"]

    print(f"{args.record}: Prompt {len(prompt)} Zeichen, Budget {args.budget}, "
          f"Goldwerte im Ausschnitt {fall['goldwerte_im_volltext']}/{len(fall['gold'])}")
    if args.dry_run:
        print("DRY-RUN: keine Anfrage")
        return 0

    AUSGABE.mkdir(parents=True, exist_ok=True)
    ziel = AUSGABE / args.out
    fertig = {json.loads(z)["record_id"] for z in ziel.read_text(encoding="utf-8").splitlines()
              if z.strip()} if ziel.exists() else set()
    if args.record in fertig:
        print("schon vorhanden, keine zweite Anfrage")
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
    locators, parse_fehler = parse_stage1(inhalt) if inhalt else ([], "leer")
    # `stage_extraction.parse_stage1` uebernimmt das Feld `timepoint` nicht; es
    # wird deshalb aus der Rohantwort nachgezogen, sonst geht ein geliefertes
    # Zeitpunktlabel still verloren (auf yun2024:525 war es "third").
    payload, _ = rx._load_payload(inhalt) if inhalt else (None, "")
    roh = payload.get("locators") if isinstance(payload, dict) else None
    if isinstance(roh, list):
        je_arm = {str(e.get("arm") or "").lower(): str(e.get("timepoint") or "").strip()
                  for e in roh if isinstance(e, dict)}
        for loc in locators:
            loc["timepoint"] = je_arm.get(str(loc.get("arm") or ""), "")
    abgebrochen = (len(inhalt) == 0) or finish == "length"

    # Zielwerte je Arm aus dem Gold, fuer den Abgleich mit der Umgebung.
    ziele: dict[str, list[float]] = {}
    for zelle in (record.get("gold") or {}).get("cells") or []:
        arm = str(zelle.get("arm") or "")
        wert = v.zahl(zelle.get("value"))
        if arm and wert is not None and "mean" in str(zelle.get("field")):
            ziele.setdefault(arm, []).append(float(wert))

    ausschnitt = fall["ausschnitt_text"]
    zahlen, _, _ = zahlen_im_text(ausschnitt)
    for loc in locators:
        stelle, text = umgebung(ausschnitt, str(loc.get("row_label") or ""))
        loc["label_im_ausschnitt"] = stelle >= 0
        loc["umgebung_zeichen"] = text
        alle_werte = [float(zi["wert"]) for zi in fall["gold"] if zi["wert"] is not None]
        loc["umgebung_zahlen"] = sorted({z for z in alle_werte if text and str(z) in text})
        loc["zielwerte_arm"] = ziele.get(str(loc.get("arm") or ""), [])
        loc["trifft_zielwert"] = bool(
            text and any(str(z) in text for z in loc["zielwerte_arm"])
        )

    zeile = {
        "record_id": args.record,
        "stufe": 1,
        "model": MODELL,
        "model_id": modell["id"],
        "prompt_version": PROMPT_LABEL,
        "prompt_zeichen": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "max_tokens": args.budget,
        "budget_begruendung": "gemessener Fertig-Punkt von yun2024:559 mit Anker (16.632 Tokens)",
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
        "locators_roh": roh if isinstance(roh, list) else [],
        "content": inhalt,
        "fehler": antwort.get("error") or "",
        "gold": fall["gold"],
    }
    with ziel.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    print(f"  -> {zeile['status']}, finish {finish}, {zeile['completion_tokens']} Tokens, "
          f"{zeile['content_chars']} Zeichen Inhalt, {len(locators)} Locators")
    for loc in locators:
        print(f"     {loc.get('arm')}: row={loc.get('row_label')!r} col={loc.get('column_header')!r} "
              f"zeit={loc.get('timepoint')!r} im_ausschnitt={loc.get('label_im_ausschnitt')} "
              f"trifft_zielwert={loc.get('trifft_zielwert')} umgebung_zahlen={loc.get('umgebung_zahlen')}")
    print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
