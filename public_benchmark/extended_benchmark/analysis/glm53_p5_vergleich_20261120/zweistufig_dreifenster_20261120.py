#!/usr/bin/env python
"""Stufe 1 mit drei 2.000er-Stuecken statt einem 6.000er-Fenster.

Die Fenstermessung hat gezeigt: die Breite ist nicht der Engpass, die
Startregel ist es. Diese Fassung schickt deshalb drei disjunkte Stuecke zu
2.000 Zeichen, gierig nach derselben blinden Bewertung wie
`mehrfach_3x2000` in `fensterlage_20261120.py`
(3 x Outcome-Treffer + 2 x Tabellenzeilen + Ziffern/100, Schritt 250).

Die Aufgabenstellung ist woertlich die aus `zweistufig_satz_20261120.py`
(`PROMPT_REGELN`); nur der Ausschnitt ist anders: drei Stuecke in
Dokumentreihenfolge, jedes mit Zeichenbereich, dazwischen ausgelassener Text.

Geprueft wird offline je Locator: steht der Satz woertlich in einem der
Stuecke, in welchem, und enthaelt er Zielwerte des Goldes.

Aufruf:
    .venv/bin/python .../zweistufig_dreifenster_20261120.py --dry-run \
        --records yun2024:30 yun2024:673 yun2024:674
    .venv/bin/python .../zweistufig_dreifenster_20261120.py --record yun2024:30
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
from fensterlage_20261120 import regeln, werte_index  # noqa: E402
from zweistufig_satz_20261120 import PROMPT_REGELN, normalisiere  # noqa: E402
from zweistufig_trocken_20261120 import (  # noqa: E402
    BREITE,
    STAGE1_SYSTEM,
    tabellenzeilen,
    zaehle,
)

MODELL = "qwen"
BUDGET = 16000
PROMPT_LABEL = "stage1_dreifenster"
STUECK = 2000
STUECKE = 3
SCHRITT = 250
LAUF = HIER / "zweistufig_lauf_20261120"


def bewerte(text: str, stichworte: list[str]) -> float:
    return (3 * zaehle(text, stichworte)
            + 2 * tabellenzeilen(text)
            + len(re.findall(r"\d", text)) / 100)


def waehle_stuecke(text: str, stichworte: list[str]) -> list[tuple[int, int]]:
    """Drei disjunkte 2.000er-Stuecke, gierig nach `bewerte`, Schritt 250."""
    if len(text) <= STUECK * STUECKE:
        return [(0, len(text))]
    frei = [True] * (len(text) // SCHRITT + 2)
    stuecke: list[tuple[int, int]] = []
    for _ in range(STUECKE):
        bestes = None
        for start in range(0, len(text) - STUECK + 1, SCHRITT):
            if not all(frei[start // SCHRITT:(start + STUECK) // SCHRITT + 1]):
                continue
            note = bewerte(text[start:start + STUECK], stichworte)
            if bestes is None or note > bestes[0]:
                bestes = (note, start)
        if bestes is None:
            break
        _, start = bestes
        stuecke.append((start, start + STUECK))
        for i in range(start // SCHRITT, (start + STUECK) // SCHRITT + 1):
            if i < len(frei):
                frei[i] = False
    return sorted(stuecke)


def baue_prompt(text: str, stuecke: list[tuple[int, int]],
                context: dict[str, Any], ziel: str) -> str:
    teile = []
    for nummer, (start, ende) in enumerate(stuecke, 1):
        teile.append(f"--- piece {nummer} of {len(stuecke)}, characters {start}-{ende} ---\n"
                     f"{text[start:ende]}")
    ausschnitt = ("Three non-contiguous pieces of the same article, in the order they "
                  "appear in the document; text between them is omitted.\n\n"
                  + "\n\n".join(teile))
    return (
        f"Publication excerpt:\n{ausschnitt}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n"
        f'Target time point (binding): "{ziel}".\n\n'
        f"{PROMPT_REGELN}"
    )


def pruefe(locators: list[dict[str, Any]], stuecke: list[tuple[int, int]],
           text: str, gold: list[dict[str, Any]]) -> None:
    normiert = [normalisiere(text[a:b]) for a, b in stuecke]
    werte = [float(z["value"]) for z in gold if z.get("value") is not None]
    for loc in locators:
        satz = normalisiere(loc["satz"])
        loc["satz_im_stueck"] = next(
            (i + 1 for i, teil in enumerate(normiert) if satz and satz in teil), None)
        loc["satz_zeichen"] = len(loc["satz"])
        loc["zielwerte_im_satz"] = sorted({w for w in werte if re.search(
            r"(?<![\d.])" + re.escape(str(w)) + r"(?![\d])", loc["satz"])})
        loc["zeilenlabel_im_stueck"] = any(
            loc["zeilenlabel"] and normalisiere(loc["zeilenlabel"]) in teil
            for teil in normiert)


def dateiname(record_id: str, modell: str, budget: int) -> str:
    return f"predictions_dreifenster_{record_id.split(':')[-1]}_{modell}_{budget}.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", nargs="+",
                        default=["yun2024:30", "yun2024:673", "yun2024:674"])
    parser.add_argument("--record")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pruefe-auswahl", action="store_true",
                        help="Vergleicht die Auswahl mit mehrfach_3x2000 aus fensterlage")
    parser.add_argument("--model", default=MODELL, choices=sorted(rx.MODELS))
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--timeout", type=float, default=420.0)
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ids = [args.record] if args.record else args.records

    if args.pruefe_auswahl:
        abweichungen = []
        for rid, record in records.items():
            pfad = ROOT / (record.get("document") or {}).get("path", "")
            text = pfad.read_text(encoding="utf-8", errors="replace")
            context = record.get("context") or {}
            outcome = str(context.get("outcome") or "")
            stichworte = [w for w in re.split(r"[\s/,()-]+", outcome) if len(w) >= 4] or [outcome]
            meine = waehle_stuecke(text, stichworte)
            if len(text) <= BREITE:
                gemessen = [(0, len(text))]
            else:
                gemessen = regeln(text, stichworte, outcome,
                                  str((record.get("timepoint") or {}).get("target") or ""),
                                  {})["mehrfach_3x2000"]["stuecke"]
            if sorted(meine) != sorted(gemessen):
                abweichungen.append((rid, meine, gemessen))
        print(f"Auswahlvergleich ueber {len(records)} Records: "
              f"{len(abweichungen)} Abweichungen")
        for rid, meine, gemessen in abweichungen:
            print(" ", rid, meine, gemessen)
        return 1 if abweichungen else 0

    faelle = {}
    for rid in ids:
        record = records[rid]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace")
        context = record.get("context") or {}
        ziel = str((record.get("timepoint") or {}).get("target") or "")
        outcome = str(context.get("outcome") or "")
        stichworte = [w for w in re.split(r"[\s/,()-]+", outcome) if len(w) >= 4] or [outcome]
        stuecke = waehle_stuecke(text, stichworte)
        prompt = baue_prompt(text, stuecke, context, ziel)
        gold = (record.get("gold") or {}).get("cells") or []
        werte = sorted({round(float(z["value"]), 6) for z in gold
                        if z.get("value") is not None})
        index = werte_index(text, werte)
        abgedeckt = sum(1 for w in werte
                        if any(any(a <= s[0] < b for s in index[w]) for a, b in stuecke))
        faelle[rid] = {"stuecke": stuecke, "prompt": prompt, "text": text, "gold": gold,
                       "werte": len(werte), "abgedeckt": abgedeckt}
        print(f"{rid}: {len(stuecke)} Stuecke {stuecke}, Prompt {len(prompt)} Zeichen, "
              f"Goldwerte im Ausschnitt {abgedeckt}/{len(werte)}, "
              f"SHA {hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]}")

    if args.dry_run:
        return 0

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    for rid, fall in faelle.items():
        modell = dict(rx.MODELS[args.model])
        modell["max_tokens"] = args.budget
        original = rx.SYSTEM
        try:
            with lesezeit(args.timeout):
                rx.SYSTEM = STAGE1_SYSTEM
                antwort = rx.call(modell, fall["prompt"], key, base, attempts=3)
        finally:
            rx.SYSTEM = original

        inhalt = antwort.get("content") or ""
        finish = antwort.get("finish_reason") or ""
        tokens = antwort.get("completion_tokens")
        locators: list[dict[str, Any]] = []
        parse_fehler = ""
        if inhalt.strip():
            try:
                daten, fehler = rx._load_payload(inhalt)
                if isinstance(daten, dict) and isinstance(daten.get("locators"), list):
                    for eintrag in daten["locators"]:
                        if isinstance(eintrag, dict):
                            locators.append({
                                "arm": str(eintrag.get("arm") or "").strip(),
                                "satz": str(eintrag.get("satz") or "").strip(),
                                "zeilenlabel": str(eintrag.get("zeilenlabel") or "").strip(),
                                "spaltenkopf": str(eintrag.get("spaltenkopf") or "").strip(),
                                "caption": str(eintrag.get("caption") or "").strip(),
                                "timepoint": str(eintrag.get("timepoint") or "").strip(),
                                "found": bool(eintrag.get("found")),
                            })
                else:
                    parse_fehler = fehler or "keine locators"
            except Exception as exc:  # noqa: BLE001 - Rohantwort bleibt erhalten
                parse_fehler = f"payload: {exc}"
        else:
            parse_fehler = "leer"

        pruefe(locators, fall["stuecke"], fall["text"], fall["gold"])
        transport_fehler = bool(antwort.get("error")) or tokens is None
        abgebrochen = (len(inhalt) == 0) or finish == "length"
        status = "fehler" if transport_fehler else ("abgebrochen" if abgebrochen else "ok")

        zeile = {
            "record_id": rid,
            "stufe": 1,
            "variante": PROMPT_LABEL,
            "model": args.model,
            "model_id": modell["id"],
            "stuecke": fall["stuecke"],
            "prompt_zeichen": len(fall["prompt"]),
            "ausschnitt_zeichen": sum(b - a for a, b in fall["stuecke"]),
            "prompt_sha256": hashlib.sha256(fall["prompt"].encode("utf-8")).hexdigest(),
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
            "locators": locators,
            "goldzellen": len(fall["gold"]),
            "goldwerte": fall["werte"],
            "goldwerte_im_ausschnitt": fall["abgedeckt"],
            "content": inhalt,
            "fehler": antwort.get("error") or "",
        }
        ziel = LAUF / dateiname(rid, args.model, args.budget)
        with ziel.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

        treffer = sum(1 for loc in locators if loc["zielwerte_im_satz"])
        print(f"  -> {rid}: {status}, finish {finish}, {tokens} Tokens, "
              f"{len(inhalt)} Zeichen, {len(locators)} Locators, "
              f"{treffer} mit Zielwert, {zeile['elapsed_s']} s")
        for loc in locators:
            print(f"     {loc['arm']}: stueck={loc['satz_im_stueck']} "
                  f"werte={loc['zielwerte_im_satz']} tp={loc['timepoint']!r}")
            print(f"       {loc['satz'][:150]!r}")
        print("geschrieben:", ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
