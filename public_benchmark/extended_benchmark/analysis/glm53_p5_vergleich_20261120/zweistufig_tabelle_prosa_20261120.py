#!/usr/bin/env python
"""Stufe 1 aus einem Tabellendichte-Fenster plus einem Prosa-Stueck.

Die Dreifenster-Serie hat gezeigt: die blinde Score-Regel waehlt Prosa mit
Outcome-Nennungen und schneidet die Ergebnistabelle ab. Diese Fassung schickt
zwei Stuecke zu je 2.000 Zeichen:

* **Tabellenfenster**: im Ergebnisteil das Fenster mit den meisten
  Tabellenmerkern (`n =`, `mean`, `SD`, `CI`, `Table`, `%`), Schritt 250.
  Blind, ohne Goldwissen.
* **Prosastueck**: im Ergebnisteil das Fenster mit der hoechsten
  Score-Bewertung (3 x Outcome-Treffer + 2 x Tabellenzeilen + Ziffern/100),
  das das Tabellenfenster nicht ueberlappt.

Beide Stuecke werden in Dokumentreihenfolge und mit ihrer Art (prose region /
table region) ausgewiesen. Die Aufgabenstellung ist woertlich die aus
`zweistufig_satz_20261120.py` (`PROMPT_REGELN`).

Aufruf:
    .venv/bin/python .../zweistufig_tabelle_prosa_20261120.py --dry-run
    .venv/bin/python .../zweistufig_tabelle_prosa_20261120.py --record yun2024:30
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
from falschwert_20261120 import TOKEN, lesarten  # noqa: E402
from fensterlage_20261120 import werte_index  # noqa: E402
from fundstellen_20261120 import abschnitte  # noqa: E402
from zweistufig_satz_20261120 import PROMPT_REGELN, normalisiere  # noqa: E402
from zweistufig_trocken_20261120 import (  # noqa: E402
    STAGE1_SYSTEM,
    tabellenzeilen,
    zaehle,
)

MODELL = "qwen"
BUDGET = 16000
PROMPT_LABEL = "stage1_tabelle_prosa"
STUECK = 2000
SCHRITT = 250
LAUF = HIER / "zweistufig_lauf_20261120"
MARKE = re.compile(r"\b(n\s*=|mean|SD|95%\s*CI|CI\b|Table|%)", re.I)


def score(text: str, stichworte: list[str]) -> float:
    return (3 * zaehle(text, stichworte) + 2 * tabellenzeilen(text)
            + len(re.findall(r"\d", text)) / 100)


def bereiche(text: str) -> tuple[int, int]:
    """Ergebnisteil, sonst ganzer Text."""
    for start, ende, name in abschnitte(text)["spans"]:
        if name == "ergebnisse":
            return start, ende
    return 0, len(text)


def waehle_stuecke(text: str, stichworte: list[str],
                   nur_tabelle: bool = False) -> list[tuple[int, int, str]]:
    start, ende = bereiche(text)
    if ende - start <= STUECK:
        return [(start, ende, "results region")]
    tabelle = max(range(start, ende - STUECK + 1, SCHRITT),
                  key=lambda s: (len(MARKE.findall(text[s:s + STUECK])), -s))
    if nur_tabelle:
        return [(tabelle, tabelle + STUECK, "table region")]
    kandidaten = [s for s in range(start, ende - STUECK + 1, SCHRITT)
                  if s + STUECK <= tabelle or s >= tabelle + STUECK]
    if kandidaten:
        prosa = max(kandidaten, key=lambda s: (score(text[s:s + STUECK], stichworte), -s))
    else:
        prosa = start if start + STUECK <= tabelle else tabelle + STUECK
        prosa = max(start, min(prosa, ende - STUECK))
    stuecke = [(prosa, "prose region"), (tabelle, "table region")]
    return [(s, s + STUECK, art) for s, art in sorted(stuecke)]


def baue_prompt(text: str, stuecke: list[tuple[int, int, str]],
                context: dict[str, Any], ziel: str) -> str:
    teile = []
    for nummer, (start, ende, art) in enumerate(stuecke, 1):
        teile.append(f"--- piece {nummer} of {len(stuecke)}, {art}, "
                     f"characters {start}-{ende} ---\n{text[start:ende]}")
    if len(stuecke) == 1:
        ausschnitt = ("One piece of the article: the table region of the results, "
                      "printed as flattened rows without column borders.\n\n"
                      + "\n\n".join(teile))
    else:
        ausschnitt = ("Two non-contiguous pieces of the same article, in the order they "
                      "appear in the document; text between them is omitted. The table "
                      "region may be printed as flattened rows without column borders.\n\n"
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


def zahlen_im_satz(satz: str) -> list[float]:
    return sorted({round(x, 6) for m in TOKEN.finditer(satz) for x in lesarten(m.group(0))})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", default="yun2024:30")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--nur-tabelle", action="store_true",
                        help="nur das Tabellenfenster, ohne Prosastueck")
    parser.add_argument("--model", default=MODELL, choices=sorted(rx.MODELS))
    parser.add_argument("--budget", type=int, default=BUDGET)
    parser.add_argument("--timeout", type=float, default=420.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[args.record]
    pfad = ROOT / (record.get("document") or {}).get("path", "")
    text = pfad.read_text(encoding="utf-8", errors="replace")
    context = record.get("context") or {}
    ziel = str((record.get("timepoint") or {}).get("target") or "")
    stichworte = [w for w in re.split(r"[\s/,()-]+", str(context.get("outcome") or ""))
                  if len(w) >= 4] or [str(context.get("outcome") or "")]

    label = "stage1_tabelle_allein" if args.nur_tabelle else PROMPT_LABEL
    stuecke = waehle_stuecke(text, stichworte, nur_tabelle=args.nur_tabelle)
    prompt = baue_prompt(text, stuecke, context, ziel)
    zellen = (record.get("gold") or {}).get("cells") or []
    werte = sorted({round(float(z["value"]), 6) for z in zellen if z.get("value") is not None})
    index = werte_index(text, werte)
    abgedeckt = {w: [i + 1 for i, (a, b, _) in enumerate(stuecke)
                     if any(a <= p[0] < b for p in index[w])] for w in werte}
    treffer = sum(1 for w in werte if abgedeckt[w])

    print(f"{args.record}: {stuecke}")
    print(f"  Prompt {len(prompt)} Zeichen, Goldwerte im Ausschnitt {treffer}/{len(werte)}, "
          f"SHA {hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]}")
    for w in werte:
        print(f"   {w}: Stueck {abgedeckt[w] or '-'}")
    if args.dry_run:
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
            rx.SYSTEM = STAGE1_SYSTEM
            antwort = rx.call(modell, prompt, key, base, attempts=3)
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
                        satz = str(eintrag.get("satz") or "").strip()
                        zahlen = zahlen_im_satz(satz)
                        locators.append({
                            "arm": str(eintrag.get("arm") or "").strip(),
                            "satz": satz,
                            "zeilenlabel": str(eintrag.get("zeilenlabel") or "").strip(),
                            "spaltenkopf": str(eintrag.get("spaltenkopf") or "").strip(),
                            "caption": str(eintrag.get("caption") or "").strip(),
                            "timepoint": str(eintrag.get("timepoint") or "").strip(),
                            "found": bool(eintrag.get("found")),
                            "zahlen_im_satz": zahlen,
                            "goldwerte_im_satz": sorted(set(zahlen) & set(werte)),
                        })
            else:
                parse_fehler = fehler or "keine locators"
        except Exception as exc:  # noqa: BLE001 - Rohantwort bleibt erhalten
            parse_fehler = f"payload: {exc}"
    else:
        parse_fehler = "leer"

    normiert = [normalisiere(text[a:b]) for a, b, _ in stuecke]
    for loc in locators:
        loc["satz_im_stueck"] = next(
            (i + 1 for i, teil in enumerate(normiert)
             if normalisiere(loc["satz"]) and normalisiere(loc["satz"]) in teil), None)

    transport_fehler = bool(antwort.get("error")) or tokens is None
    abgebrochen = (len(inhalt) == 0) or finish == "length"
    status = "fehler" if transport_fehler else ("abgebrochen" if abgebrochen else "ok")

    zeile = {
        "record_id": args.record,
        "stufe": 1,
        "variante": label,
        "model": args.model,
        "model_id": modell["id"],
        "stuecke": stuecke,
        "prompt_zeichen": len(prompt),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "max_tokens": args.budget,
        "timeout_s": args.timeout,
        "status": status,
        "transport_fehler": transport_fehler,
        "abbruchkriterium": "content_chars == 0 oder finish_reason == length",
        "http_status": antwort.get("http_status"),
        "finish_reason": finish,
        "completion_tokens": tokens,
        "reasoning_chars": antwort.get("reasoning_chars"),
        "content_chars": len(inhalt),
        "elapsed_s": antwort.get("elapsed_s"),
        "parse_fehler": parse_fehler,
        "locators": locators,
        "goldwerte": werte,
        "goldwerte_im_ausschnitt": treffer,
        "content": inhalt,
        "fehler": antwort.get("error") or "",
    }
    praefix = "tabelle_allein" if args.nur_tabelle else "tabelle_prosa"
    ziel_pfad = LAUF / (args.out or
                        f"predictions_{praefix}_{args.record.split(':')[1]}"
                        f"_{args.model}_{args.budget}.jsonl")
    with ziel_pfad.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    print(f"  -> {status}, finish {finish}, {tokens} Tokens, {len(inhalt)} Zeichen, "
          f"{len(locators)} Locators, {zeile['elapsed_s']} s")
    for loc in locators:
        print(f"     {loc['arm']}: stueck={loc['satz_im_stueck']} "
              f"werte={loc['goldwerte_im_satz']} tp={loc['timepoint']!r}")
        print(f"       {loc['satz'][:180]!r}")
    print("geschrieben:", ziel_pfad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
