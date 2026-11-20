#!/usr/bin/env python
"""Zweistufiger Test auf yun2024:559, Stufe 1 trocken.

Kein Modellaufruf, kein Netz. Gebaut wird, was Stufe 1 bekommen wuerde:

* einen Ausschnitt von rund 6.000 Zeichen, gewaehlt nach Nennungen des Outcomes
  und nach Tabellenzeilen (der Volltext hat 13.122 Zeichen),
* einen Prompt, der nur Zeile, Spaltenkoepfe und Zeitpunkt benennen darf,
  ausdruecklich keine Zahlen,
* ein Budget von 2.000 Completion-Tokens statt 24.000.

Der Ausschnitt wird nach einer festen, hier dokumentierten Regel gewaehlt: ein
Fenster von 6.000 Zeichen, Start in 500er-Schritten, Bewertung =
3 x Outcome-Treffer + 2 x Tabellenzeilen + 1 x Zahlentreffer im Fenster.
Das ist eine Heuristik ohne Modell und ohne Goldwissen; sie dient dazu, den
Prompt zu bauen, nicht ihn zu bewerten.

Aufruf:
    .venv/bin/python .../zweistufig_trocken_20261120.py
"""

from __future__ import annotations

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
from falschwert_20261120 import lesarten, zahlen_im_text  # noqa: E402

RECORD_ID = "yun2024:559"
BREITE = 6000
SCHRITT = 500
STAGE1_MAX_TOKENS = 2000
AUSGABE = HIER / "zweistufig_trocken_20261120.json"
AUSGABE_MD = HIER / "zweistufig_trocken_20261120.md"

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
                "kandidaten": []}
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
    return {**bestes, "fenster": text[bestes["start"]:bestes["ende"]], "kandidaten": kandidaten}


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


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    record = records[RECORD_ID]
    pfad = ROOT / (record.get("document") or {}).get("path", "")
    text = pfad.read_text(encoding="utf-8", errors="replace")
    context = record.get("context") or {}
    target = str((record.get("timepoint") or {}).get("target") or "")
    outcome = str(context.get("outcome") or "")
    stichworte = [w for w in re.split(r"[\s/,()-]+", outcome) if len(w) >= 4]
    if not stichworte:
        stichworte = [outcome] if outcome else []

    wahl = waehle_ausschnitt(text, stichworte, BREITE, SCHRITT)
    prompt = build_stage1_prompt(wahl["fenster"], context, target)

    # Kann Stufe 1 ueberhaupt finden, was das Gold verlangt? Gezaehlt wird mit
    # derselben Trennzeichen-Regel wie im Falschwert-Bericht.
    gold = (record.get("gold") or {}).get("cells") or []
    voll_zahlen, _, _ = zahlen_im_text(text)
    aus_zahlen, _, _ = zahlen_im_text(wahl["fenster"])
    zielwerte = []
    for zelle in gold:
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

    ergebnis = {
        "record_id": RECORD_ID,
        "hinweis": "Trockenbau: Ausschnitt und Prompt fuer Stufe 1, kein Modellaufruf.",
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
            "anteil_prozent": round(100 * len(wahl["fenster"]) / len(text), 1),
            "outcome_treffer": wahl["outcome_treffer"],
            "tabellenzeilen": wahl["tabellenzeilen"],
            "bewertung": round(wahl["bewertung"], 2) if wahl["bewertung"] is not None else None,
            "kandidaten": len(wahl["kandidaten"]),
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
    }
    AUSGABE.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Zweistufiger Test auf yun2024:559, Stufe 1 trocken (20.11.2026)",
        "",
        "Kein Modellaufruf. Gebaut ist nur, was Stufe 1 bekommen wuerde: Ausschnitt, "
        "Prompt und Budget.",
        "",
        "## Eckdaten",
        "",
        f"- Dokument: {(record.get('document') or {}).get('id')}, Volltext {len(text)} Zeichen",
        f"- Outcome: {outcome}",
        f"- Zielzeitpunkt: {target or 'nicht gesetzt'}",
        f"- Stichworte fuer die Fenstersuche: {', '.join(stichworte) or '-'}",
        f"- Ausschnitt: {len(wahl['fenster'])} Zeichen (Zeichen {wahl['start']} bis "
        f"{wahl['ende']}, {round(100 * len(wahl['fenster']) / len(text), 1)} % des Textes)",
        f"- Prompt: {len(prompt)} Zeichen, geschaetzt {round(len(prompt) / 4)} Tokens",
        f"- Budget Stufe 1: {STAGE1_MAX_TOKENS} Completion-Tokens (statt 24.000 im Einzelaufruf)",
        "",
        "## Ausschnitt",
        "",
        "```markdown",
        wahl["fenster"],
        "```",
        "",
        "## Prompt Stufe 1",
        "",
        "```text",
        prompt,
        "```",
        "",
        "## Koennen die Goldwerte ueberhaupt im Ausschnitt stehen?",
        "",
        "| Feld | Arm | Goldwert | Vorkommen im Volltext | im Ausschnitt |",
        "|---|---|---:|---:|---:|",
        *[
            f"| {z['field']} | {z['arm']} | {z['wert']} | {z['im_volltext']} | {z['im_ausschnitt']} |"
            for z in zielwerte
        ],
        "",
        f"{len(zielwerte) - len(fehlend)} von {len(zielwerte)} Goldwerten stehen im Volltext, "
        f"{len(fehlend)} von {len(zielwerte)} nicht. Fehlt ein Wert im Volltext, kann ihn weder "
        "Stufe 1 noch Stufe 2 finden: die Tabelle steht im Markdown nur als Caption mit "
        "Bildplatzhalter, der Tabellenkoerper fehlt.",
        "",
        "## Was Stufe 1 nicht bekommt",
        "",
        "- keine Zahlenauftrag: der Prompt verbietet das Lesen von Werten ausdruecklich",
        "- keine Feldliste mit acht Feldern, nur Outcome, Arme und Zielzeitpunkt",
        "- kein Volltext: 6.000 statt 13.122 Zeichen, also 46 Prozent",
        "",
        "## Vorbehalt",
        "",
        "Die Fensterwahl ist eine Heuristik (Outcome-Treffer, Tabellenzeilen, Ziffern), "
        "kein Modell. Ob der Ausschnitt die richtige Zeile enthaelt, entscheidet erst "
        "Stufe 1; ob Stufe 1 ihn richtig liest, erst der Aufruf.",
        "",
    ]
    AUSGABE_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"Text {len(text)} Zeichen, Outcome {outcome!r}, Ziel {target!r}")
    print(f"Ausschnitt {wahl['start']}..{wahl['ende']} = {len(wahl['fenster'])} Zeichen, "
          f"Treffer {wahl['outcome_treffer']}, Tabellenzeilen {wahl['tabellenzeilen']}")
    print(f"Prompt {len(prompt)} Zeichen (~{round(len(prompt)/4)} Tokens), Budget {STAGE1_MAX_TOKENS}")
    print("geschrieben:", AUSGABE)
    print("geschrieben:", AUSGABE_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
