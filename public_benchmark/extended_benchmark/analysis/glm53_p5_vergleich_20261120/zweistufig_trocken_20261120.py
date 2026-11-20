#!/usr/bin/env python
"""Zweistufiger Test, Stufe 1 trocken, fuer einen oder mehrere Records.

Kein Modellaufruf, kein Netz. Gebaut wird, was Stufe 1 bekommen wuerde:

* ein Ausschnitt von rund 6.000 Zeichen, gewaehlt nach Nennungen des Outcomes
  und nach Tabellenzeilen,
* ein Prompt, der nur Zeile, Spaltenkoepfe und Zeitpunkt benennen darf,
  ausdruecklich keine Zahlen,
* ein Budget von 2.000 Completion-Tokens statt 24.000.

Dazu die entscheidende Vorabpruefung: stehen die Goldwerte des Records
ueberhaupt im Volltext und im Ausschnitt? Fehlt ein Wert im Volltext, kann ihn
keine Stufe finden.

Die Fensterwahl ist eine feste Heuristik ohne Modell und ohne Goldwissen:
Fenster von 6.000 Zeichen, Start in 500er-Schritten, Bewertung =
3 x Outcome-Treffer + 2 x Tabellenzeilen + 1/100 x Ziffern im Fenster.

Aufruf:
    .venv/bin/python .../zweistufig_trocken_20261120.py
    .venv/bin/python .../zweistufig_trocken_20261120.py --records yun2024:523 yun2024:525 \
        --out-prefix zweistufig_trocken_523_525_20261120
"""

from __future__ import annotations

import argparse
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

import vergleiche_20261120 as v  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402

BREITE = 6000
SCHRITT = 500
STAGE1_MAX_TOKENS = 2000

STAGE1_SYSTEM = (
    "You locate numerical results in randomised controlled trial publications. "
    "You answer with a single JSON object and nothing else. You never invent labels: "
    "every label you name must appear in the text."
)


def zaehle(text: str, stichworte: list[str]) -> int:
    klein = text.lower()
    return sum(klein.count(wort.lower()) for wort in stichworte)


def tabellenzeilen(text: str) -> int:
    return sum(1 for zeile in text.splitlines() if zeile.count("|") >= 2)


def waehle_ausschnitt(text: str, stichworte: list[str], breite: int, schritt: int) -> dict[str, Any]:
    """Bestes Fenster nach der oben dokumentierten Bewertungsregel."""
    if len(text) <= breite:
        return {"start": 0, "ende": len(text), "fenster": text, "bewertung": None,
                "outcome_treffer": zaehle(text, stichworte),
                "tabellenzeilen": tabellenzeilen(text), "zahlen": len(re.findall(r"\d", text)),
                "kandidaten": 0}
    kandidaten = []
    for start in range(0, max(1, len(text) - breite + 1), schritt):
        fenster = text[start:start + breite]
        treffer = zaehle(fenster, stichworte)
        zeilen = tabellenzeilen(fenster)
        zahlen = len(re.findall(r"\d", fenster))
        kandidaten.append({
            "start": start, "ende": start + breite,
            "outcome_treffer": treffer, "tabellenzeilen": zeilen, "zahlen": zahlen,
            "bewertung": 3 * treffer + 2 * zeilen + zahlen / 100,
        })
    bestes = max(kandidaten, key=lambda k: k["bewertung"])
    return {**bestes, "fenster": text[bestes["start"]:bestes["ende"]],
            "kandidaten": len(kandidaten)}


def build_stage1_prompt(ausschnitt: str, context: dict[str, Any], target: str) -> str:
    return (
        f"Publication excerpt:\n{ausschnitt}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n"
        f'Target time point (binding): "{target}".\n\n'
        "Read no numbers. Only locate where the outcome is reported at the target time point.\n"
        "Name, for each arm, the exact row label (the outcome line as printed), the exact "
        "column header of that arm as printed, the caption of the table or the paragraph, and "
        "the time point label as printed.\n"
        "If the excerpt does not report the outcome at the target time point for an arm, set "
        '"found": false for that arm and leave the labels empty. Do not guess a row.\n'
        "If the outcome is reported in several rows (subgroups, populations), choose the row "
        "that matches the arms named in the request.\n\n"
        "Return exactly one JSON object:\n"
        '{"locators": [{"arm": "intervention" | "comparator", "row_label": "<as printed>", '
        '"column_header": "<as printed>", "caption": "<caption or short paragraph label>", '
        '"timepoint": "<as printed>", "found": true}, ...]}\n'
        "No numbers. No commentary, markdown or code fences."
    )


def baue_fall(rid: str, record: dict[str, Any]) -> dict[str, Any]:
    pfad = ROOT / (record.get("document") or {}).get("path", "")
    text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
    context = record.get("context") or {}
    target = str((record.get("timepoint") or {}).get("target") or "")
    outcome = str(context.get("outcome") or "")
    stichworte = [w for w in re.split(r"[\s/,()-]+", outcome) if len(w) >= 4]
    if not stichworte:
        stichworte = [outcome] if outcome else []

    wahl = waehle_ausschnitt(text, stichworte, BREITE, SCHRITT)
    prompt = build_stage1_prompt(wahl["fenster"], context, target)

    voll_zahlen, _, _ = zahlen_im_text(text)
    aus_zahlen, _, _ = zahlen_im_text(wahl["fenster"])
    zielwerte = []
    for zelle in (record.get("gold") or {}).get("cells") or []:
        wert = v.zahl(zelle.get("value"))
        schluessel = round(float(wert), 6) if wert is not None else None
        zielwerte.append({
            "field": zelle.get("field"),
            "arm": zelle.get("arm"),
            "wert": wert,
            "im_volltext": voll_zahlen.get(schluessel, 0) if schluessel is not None else 0,
            "im_ausschnitt": aus_zahlen.get(schluessel, 0) if schluessel is not None else 0,
        })
    fehlend = [z for z in zielwerte if z["im_volltext"] == 0]

    return {
        "record_id": rid,
        "dokument": (record.get("document") or {}).get("id"),
        "text_zeichen": len(text),
        "outcome": outcome,
        "timepoint_target": target,
        "stichworte": stichworte,
        "ausschnitt": {
            "breite": BREITE,
            "start": wahl["start"],
            "ende": wahl["ende"],
            "zeichen": len(wahl["fenster"]),
            "anteil_prozent": round(100 * len(wahl["fenster"]) / len(text), 1) if text else 0,
            "outcome_treffer": wahl["outcome_treffer"],
            "tabellenzeilen": wahl["tabellenzeilen"],
            "bewertung": round(wahl["bewertung"], 2) if wahl["bewertung"] is not None else None,
            "kandidaten": wahl["kandidaten"],
        },
        "prompt_zeichen": len(prompt),
        "prompt_tokens_geschaetzt": round(len(prompt) / 4),
        "max_tokens": STAGE1_MAX_TOKENS,
        "prompt": prompt,
        "ausschnitt_text": wahl["fenster"],
        "system": STAGE1_SYSTEM,
        "gold": zielwerte,
        "goldwerte_im_volltext": len(zielwerte) - len(fehlend),
        "goldwerte_fehlend": len(fehlend),
        "fehlende_felder": [z["field"] for z in fehlend],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", nargs="+", default=["yun2024:559"])
    parser.add_argument("--out-prefix", default="zweistufig_trocken_20261120")
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    unbekannt = [rid for rid in args.records if rid not in records]
    if unbekannt:
        raise SystemExit(f"unbekannte Records: {unbekannt}")

    faelle = {rid: baue_fall(rid, records[rid]) for rid in args.records}
    summe = {
        "n": len(faelle),
        "prompt_median": sorted(f["prompt_zeichen"] for f in faelle.values())[len(faelle) // 2],
        "goldwerte": sum(len(f["gold"]) for f in faelle.values()),
        "goldwerte_im_volltext": sum(f["goldwerte_im_volltext"] for f in faelle.values()),
        "goldwerte_fehlend": sum(f["goldwerte_fehlend"] for f in faelle.values()),
        "max_tokens": STAGE1_MAX_TOKENS,
        "hinweis": "Trockenbau: Ausschnitt und Prompt fuer Stufe 1, kein Modellaufruf.",
    }
    ergebnis = {"summe": summe, "faelle": faelle}

    json_pfad = HIER / f"{args.out_prefix}.json"
    md_pfad = HIER / f"{args.out_prefix}.md"
    json_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        f"# Zweistufiger Test, Stufe 1 trocken: {', '.join(args.records)} (20.11.2026)",
        "",
        "Kein Modellaufruf. Gebaut ist nur, was Stufe 1 bekommen wuerde: Ausschnitt, "
        "Prompt und Budget, dazu die Vorabpruefung, ob die Goldwerte ueberhaupt im "
        "Text stehen.",
        "",
        "## Uebersicht",
        "",
        "| Record | Dokument | Text | Ausschnitt | Anteil | Outcome-Treffer | Tabellenzeilen | Prompt | Goldwerte im Text |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rid, f in faelle.items():
        md.append(
            f"| `{rid}` | {f['dokument']} | {f['text_zeichen']} | {f['ausschnitt']['zeichen']} | "
            f"{f['ausschnitt']['anteil_prozent']} % | {f['ausschnitt']['outcome_treffer']} | "
            f"{f['ausschnitt']['tabellenzeilen']} | {f['prompt_zeichen']} | "
            f"{f['goldwerte_im_volltext']}/{len(f['gold'])} |"
        )
    md += [
        "",
        f"Budget je Aufruf: {STAGE1_MAX_TOKENS} Completion-Tokens (statt 24.000 im "
        "Einzelaufruf). Prompt-Laenge je Record unten.",
        "",
    ]
    for rid, f in faelle.items():
        md += [
            f"## {rid}",
            "",
            f"- Dokument: {f['dokument']}, Volltext {f['text_zeichen']} Zeichen",
            f"- Outcome: {f['outcome']}",
            f"- Zielzeitpunkt: {f['timepoint_target'] or 'nicht gesetzt'}",
            f"- Ausschnitt: Zeichen {f['ausschnitt']['start']} bis {f['ausschnitt']['ende']}, "
            f"{f['ausschnitt']['zeichen']} Zeichen ({f['ausschnitt']['anteil_prozent']} %)",
            f"- Prompt: {f['prompt_zeichen']} Zeichen, geschaetzt {f['prompt_tokens_geschaetzt']} Tokens",
            "",
            "### Stehen die Goldwerte im Text?",
            "",
            "| Feld | Arm | Goldwert | Volltext | Ausschnitt |",
            "|---|---|---:|---:|---:|",
            *[
                f"| {z['field']} | {z['arm']} | {z['wert']} | {z['im_volltext']} | {z['im_ausschnitt']} |"
                for z in f["gold"]
            ],
            "",
            f"{f['goldwerte_im_volltext']} von {len(f['gold'])} Goldwerten stehen im Volltext, "
            f"{f['goldwerte_fehlend']} nicht. Fehlt ein Wert im Volltext, kann ihn keine Stufe "
            "finden: die Tabelle steht im Markdown nur als Caption mit Bildplatzhalter.",
            "",
            "### Ausschnitt",
            "",
            "```markdown",
            f["ausschnitt_text"],
            "```",
            "",
            "### Prompt Stufe 1",
            "",
            "```text",
            f["prompt"],
            "```",
            "",
        ]
    md += [
        "## Vorbehalt",
        "",
        "Die Fensterwahl ist eine Heuristik (Outcome-Treffer, Tabellenzeilen, Ziffern), kein "
        "Modell. Ob der Ausschnitt die richtige Zeile enthaelt, entscheidet erst Stufe 1; ob "
        "Stufe 1 ihn richtig liest, erst der Aufruf.",
        "",
    ]
    md_pfad.write_text("\n".join(md), encoding="utf-8", newline="\n")

    for rid, f in faelle.items():
        print(f"{rid}: Text {f['text_zeichen']}, Ausschnitt {f['ausschnitt']['zeichen']} "
              f"({f['ausschnitt']['anteil_prozent']} %), Prompt {f['prompt_zeichen']} Zeichen "
              f"(~{f['prompt_tokens_geschaetzt']} Tokens), Goldwerte im Text "
              f"{f['goldwerte_im_volltext']}/{len(f['gold'])}"
              + (f", fehlend: {', '.join(f['fehlende_felder'])}" if f["fehlende_felder"] else ""))
    print("geschrieben:", json_pfad)
    print("geschrieben:", md_pfad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
