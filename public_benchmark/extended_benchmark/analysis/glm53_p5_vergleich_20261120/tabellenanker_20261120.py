#!/usr/bin/env python
"""Tabellenanker-Prompt trocken fuer die 13 Budgetfaelle ohne Strukturhypothese.

Kein Modellaufruf, kein Netz, keine geschriebene Prediction. Der Prompt wird mit
dem echten Prompt-Bauer des Harness (`build_prompt`, Version `v2_timepoint`)
gebaut und um einen Ankerblock ergaenzt; gemessen wird nur die Laenge.

Der Anker ist bewusst additiv: der bestehende Prompt bleibt Zeichen fuer Zeichen
erhalten, damit ein spaeterer Lauf genau eine Veraenderung traegt. Er verlangt
vor den Zellen eine Quelle (Caption oder Satz, Zeilenlabel, beide Spaltenkoepfe),
bindet alle Zellen an diese eine Zeile und diesen einen Zeitpunkt und beendet
die Suche, sobald der Anker den Zielzeitpunkt traegt.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/tabellenanker_20261120.py
"""

from __future__ import annotations

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

from extended_benchmark.run_extended_extraction import build_prompt  # noqa: E402

QUELLE_BUDGET = HIER / "budget_20261120.json"
RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"
AUSGABE_JSON = HIER / "tabellenanker_20261120.json"
AUSGABE_MD = HIER / "p5_tabellenanker_20261120.md"
LIMIT = 45000

ANKER = """

Table anchor (binding, before any cell):
1. Name the one place that reports this outcome: the table caption (table number and title) or, if the outcome is reported only in prose, the sentence. Copy it character for character.
2. Add "anchor" as the first key: {"source": "<caption or sentence>", "row": "<row label exactly as printed>", "intervention_column": "<column head of the intervention arm>", "comparator_column": "<column head of the comparator arm>"}.
3. Every cell must come from this one row and this one time point. Never combine two rows, two populations or two tables.
4. If that row reports the target time point, answer immediately and do not search another candidate.
5. If it does not report the target time point, return an empty cell list and name its label in "discarded_timepoints"; never substitute another time point.
Do not describe tables you did not use."""


def lade(pfad: Path) -> list[dict[str, Any]]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def main() -> int:
    budget = json.loads(QUELLE_BUDGET.read_text(encoding="utf-8"))
    ohne = sorted(rid for rid, e in budget["faelle"].items() if e["gruppe"] == "ohne_struktur")
    records = {r["record_id"]: r for r in lade(RECORDS)}

    zeilen: list[dict[str, Any]] = []
    for rid in ohne:
        record = records[rid]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        alt = build_prompt(record, text)
        neu = alt + ANKER
        zeilen.append(
            {
                "record_id": rid,
                "dokument": (record.get("document") or {}).get("id"),
                "outcome_typ": (record.get("context") or {}).get("outcome_type"),
                "goldzellen": len((record.get("gold") or {}).get("cells") or []),
                "text_zeichen": len(text),
                "text_im_prompt": min(len(text), LIMIT),
                "prompt_alt": len(alt),
                "prompt_neu": len(neu),
                "delta": len(neu) - len(alt),
                "delta_prozent": round(100 * (len(neu) - len(alt)) / len(alt), 2) if alt else None,
                "prompt_gedeckt": len(text) > LIMIT,
                "anker_zeichen": len(ANKER),
                "sha256_alt": hashlib.sha256(alt.encode("utf-8")).hexdigest(),
                "sha256_neu": hashlib.sha256(neu.encode("utf-8")).hexdigest(),
                "budget_json_prompt": budget["faelle"][rid]["prompt"],
                "budget_json_prompt_gleich": budget["faelle"][rid]["prompt"] == len(alt),
                "tabellen": budget["faelle"][rid]["tabellen"],
                "prozess": budget["faelle"][rid]["pipe_zeilen"],
            }
        )

    summe_alt = sum(z["prompt_alt"] for z in zeilen)
    summe_neu = sum(z["prompt_neu"] for z in zeilen)
    ergebnis = {
        "hinweis": (
            "Trockenbau: build_prompt(record, text) plus Ankerblock, ohne Aufruf. "
            "Der Anker ist additiv; der bestehende Prompt bleibt unveraendert."
        ),
        "anker": ANKER,
        "faelle": {z["record_id"]: z for z in zeilen},
        "summe": {
            "n": len(zeilen),
            "prompt_alt": summe_alt,
            "prompt_neu": summe_neu,
            "delta": summe_neu - summe_alt,
            "delta_prozent": round(100 * (summe_neu - summe_alt) / summe_alt, 2) if summe_alt else None,
            "alle_reproduzierbar": all(z["budget_json_prompt_gleich"] for z in zeilen),
            "anker_zeichen": len(ANKER),
        },
    }
    AUSGABE_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Tabellenanker-Prompt fuer die 13 Budgetfaelle (20.11.2026)",
        "",
        "Trockenbau, kein Modellaufruf. Basis ist der echte Prompt-Bauer des Harness "
        "(`build_prompt`, Version `v2_timepoint`) mit demselben Markdown, das der P5-Lauf "
        "gelesen hat. Der Ankerblock wird angehaengt; der bestehende Prompt bleibt Zeichen "
        "fuer Zeichen erhalten.",
        "",
        f"## Ankerblock ({len(ANKER)} Zeichen)",
        "",
        "```text",
        ANKER.strip(),
        "```",
        "",
        "## Prompt-Laenge je Record",
        "",
        "| Record | Dokument | Typ | Gold | Text | Prompt alt | Prompt neu | Delta | Delta % | Tabelle | Pipe-Zeilen |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for z in zeilen:
        md.append(
            f"| `{z['record_id']}` | {z['dokument']} | {z['outcome_typ']} | {z['goldzellen']} | "
            f"{z['text_zeichen']} | {z['prompt_alt']} | {z['prompt_neu']} | +{z['delta']} | "
            f"+{z['delta_prozent']} | {z['tabellen']} | {z['prozess']} |"
        )
    md += [
        "",
        f"Summe: {summe_alt} -> {summe_neu} Zeichen (+{summe_neu - summe_alt}). Der Anker kostet "
        f"{len(ANKER)} Zeichen je Aufruf, also rund {round(100 * len(ANKER) / (summe_alt / len(zeilen)), 1)} "
        "Prozent eines durchschnittlichen Prompts dieser Gruppe.",
        "",
        "## Was der Anker aendert und was nicht",
        "",
        "- Er aendert nur die Prompt-Oberflaeche: Quelle, Zeilenlabel und beide Spaltenkoepfe "
        "muessen vor den Zellen benannt werden, alle Zellen stammen aus dieser einen Zeile, "
        "und die Suche endet am Anker. Die Extraktionsregeln, die Feldliste und der Zeitpunktzwang "
        "bleiben unveraendert; der Anker uebernimmt die v2-Regel, bei fehlendem Zielzeitpunkt "
        "Zellen wegzulassen statt einen anderen Zeitpunkt einzusetzen.",
        "- Er beantwortet nicht die Frage, ob der Anker den Reasoning-Verbrauch senkt. Das ist "
        "eine Hypothese; ohne Aufruf ist die Wirkung nicht gemessen. Gemessen ist nur die Prompt-Laenge.",
        "- Fuer die sechs Records ohne Tabellentext im Markdown greift Regel 1 auf den Satz zurueck; "
        "der Anker verlangt dort keine Tabelle, die es nicht gibt.",
        "- Die Laenge ist fuer die kurzen Dokumente der Gruppe der groesste relative Eingriff "
        "(bis +21,8 Prozent), fuer die langen der kleinste (+4,7 Prozent). Absolut ist der Zuwachs "
        "in allen 13 Faellen identisch.",
        "- Ein spaeterer Lauf braucht genau eine freigegebene Aenderung: den Ankerblock im Prompt. "
        "Das Abbruchkriterium bleibt `content_chars > 0` und `finish_reason = stop`.",
        "",
        "Die SHA256-Summen je Prompt stehen in `tabellenanker_20261120.json`; damit ist "
        "nachpruefbar, dass nur der Anker hinzugekommen ist.",
        "",
    ]
    AUSGABE_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    print("| Record | Dokument | Typ | Gold | Text | Prompt alt | Prompt neu | Delta | Delta % | reproduziert |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for z in zeilen:
        print(
            f"| `{z['record_id']}` | {z['dokument']} | {z['outcome_typ']} | {z['goldzellen']} | "
            f"{z['text_zeichen']} | {z['prompt_alt']} | {z['prompt_neu']} | +{z['delta']} | "
            f"+{z['delta_prozent']} | {'ja' if z['budget_json_prompt_gleich'] else 'NEIN'} |"
        )
    print(f"\nSumme: {summe_alt} -> {summe_neu} (+{summe_neu - summe_alt} Zeichen), "
          f"Ankerblock {len(ANKER)} Zeichen, alle Laengen reproduziert: "
          f"{ergebnis['summe']['alle_reproduzierbar']}")
    print("geschrieben:", AUSGABE_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
