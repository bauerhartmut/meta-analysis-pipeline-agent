#!/usr/bin/env python
"""Offline-Auswahl von 5 der 33 Abbruchrecords fuer die Kette.

Befund der strengen Fassung: mit der Forderung "Wochenlabel im Ausschnitt"
erfuellt nur **ein** Record die Kriterien (yun2024:30). 25 der 33 haben keine
Score-Zeile, 30 kein Wochenlabel, 8 einen binaeren Outcome, 3 nur ein Stueck.
Die Auswahl ist deshalb auf Strukturmerkmale gelockert, die die Kette wirklich
braucht; das Wochenlabel wird nur noch protokolliert, nicht verlangt.

Kriterien, alle aus Text und Kontext, nicht aus dem Gold:

1. Record ohne Inhalt im P5-Lauf (`content_chars == 0` oder leerer `content`).
2. Zwei Stuecke aus dem blinden Verfahren (Prosa plus Tabellenfenster).
3. Mindestens eine Score-Zeile im Ausschnitt.
4. Outcome-Typ `continuous` (Stufe 2 liest Mittelwert, SD, n).
5. Noch nicht gemessen (yun2024:30 ist bereits durchgelaufen).
6. Je Dokument hoechstens zwei Records.

Ausgewaehlt werden die fuenf Records mit der kleinsten Nummer, die alle
Kriterien erfuellen. Das Gold wird nur gemessen (Abdeckung im Ausschnitt), nie
zur Auswahl benutzt. Kein Modellaufruf.

Aufruf:
    .venv/bin/python .../stichprobe_20261120.py
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
from fensterlage_20261120 import werte_index  # noqa: E402
from zweistufig_tabelle_prosa_20261120 import (  # noqa: E402
    BUDGET,
    baue_prompt,
    bindung_pruefen,
    waehle_stuecke,
)

ANZAHL = 5
STUFE2_BUDGET = 8000
JE_DOKUMENT = 2
BEREITS_GEMESSEN = {"yun2024:30"}
#: Gemessen auf yun2024:30 (Stufe 1 8.003 Tokens, Stufe 2 3.262 Tokens).
GEMESSEN_JE_RECORD = 11265


def stichworte_von(record: dict[str, Any]) -> list[str]:
    context = record.get("context") or {}
    worte = [w for w in re.split(r"[\s/,()-]+", str(context.get("outcome") or ""))
             if len(w) >= 4]
    return worte or [str(context.get("outcome") or "")]


def main() -> int:
    leere: list[dict[str, Any]] = []
    for zeile in v.P5.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        row = json.loads(zeile)
        if row.get("content_chars") == 0 or not (row.get("content") or "").strip():
            leere.append(row)
    print(f"leere P5-Records: {len(leere)}")

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: dict[str, Any] = {}
    streng = 0

    for row in leere:
        rid = row.get("record_id")
        record = records.get(rid)
        if not record:
            faelle[rid] = {"auswahl": False, "gruende": ["kein_gold_record"]}
            continue
        context = record.get("context") or {}
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        stuecke = waehle_stuecke(text, stichworte_von(record)) if text else []
        bind = bindung_pruefen(text, stuecke) if stuecke else {"score_zeilen": [], "wochen": {}}
        zellen = (record.get("gold") or {}).get("cells") or []
        werte = sorted({round(float(z["value"]), 6) for z in zellen
                        if z.get("value") is not None})
        index = werte_index(text, werte) if text else {}
        abgedeckt = sum(1 for w in werte
                        if any(any(a <= p[0] < b for p in index.get(w, []))
                               for a, b, _ in stuecke))
        prompt = (baue_prompt(text, stuecke, context,
                              str((record.get("timepoint") or {}).get("target") or ""),
                              zeilenbindung=True) if stuecke else "")

        gruende = []
        if len(stuecke) < 2:
            gruende.append("kein_zweites_stueck")
        if not bind["score_zeilen"]:
            gruende.append("keine_score_zeile")
        if str(context.get("outcome_type") or "") != "continuous":
            gruende.append(f"outcome_typ={context.get('outcome_type')}")
        if rid in BEREITS_GEMESSEN:
            gruende.append("bereits_gemessen")
        hat_wochen = bool(bind["wochen"])
        if gruende == [] and hat_wochen:
            streng += 1

        faelle[rid] = {
            "dokument": (record.get("document") or {}).get("id"),
            "outcome_typ": context.get("outcome_type"),
            "outcome": context.get("outcome"),
            "stuecke": stuecke,
            "score_zeilen": len(bind["score_zeilen"]),
            "score_labels": sorted({t["label"] for t in bind["score_zeilen"]}),
            "wochenlabel": bind["wochen"],
            "goldwerte": len(werte),
            "goldwerte_im_ausschnitt": abgedeckt,
            "prompt_zeichen": len(prompt),
            "gruende": gruende,
            "auswahl": not gruende,
        }

    kandidaten = sorted((rid for rid, f in faelle.items() if f["auswahl"]),
                        key=lambda r: int(r.split(":")[1]))
    gewaehlt: list[str] = []
    je_dokument: dict[str, int] = {}
    for rid in kandidaten:
        dokument = faelle[rid]["dokument"]
        if je_dokument.get(dokument, 0) >= JE_DOKUMENT:
            faelle[rid]["auswahl"] = False
            faelle[rid]["gruende"].append("dokument_ausgeschoepft")
            continue
        je_dokument[dokument] = je_dokument.get(dokument, 0) + 1
        gewaehlt.append(rid)
        if len(gewaehlt) == ANZAHL:
            break

    kosten = {
        "je_record_gemessen": GEMESSEN_JE_RECORD,
        "erwartet": GEMESSEN_JE_RECORD * len(gewaehlt),
        "obergrenze": (BUDGET + STUFE2_BUDGET) * len(gewaehlt),
        "budget_stufe1": BUDGET,
        "budget_stufe2": STUFE2_BUDGET,
        "hinweis": "Obergrenze gilt, wenn Stufe 1 das Budget wie im P5-Lauf "
                   "ausschopft; auf yun2024:30 waren es 8.003 und 3.262.",
    }

    ergebnis = {
        "quelle": str(v.P5),
        "n_leere": len(leere),
        "n_streng": streng,
        "n_kandidaten": len(kandidaten),
        "gewaehlt": gewaehlt,
        "kosten": kosten,
        "faelle": faelle,
    }
    (HIER / "stichprobe_20261120.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"streng geeignet: {streng} von {len(leere)}")
    print(f"gelockert geeignet: {len(kandidaten)}; gewaehlt: {gewaehlt}")
    print("| Record | Dokument | Outcome | Score-Zeilen | Wochenlabel | Gold im Ausschnitt | Prompt |")
    print("|---|---|---|---:|---|---:|---:|")
    for rid in gewaehlt:
        f = faelle[rid]
        print(f"| `{rid}` | {f['dokument']} | {str(f['outcome'])[:38]} | "
              f"{f['score_zeilen']} {','.join(f['score_labels'])} | "
              f"{'ja' if f['wochenlabel'] else 'nein'} | "
              f"{f['goldwerte_im_ausschnitt']}/{f['goldwerte']} | {f['prompt_zeichen']} |")
    print()
    print(f"Kosten erwartet: {kosten['erwartet']} Tokens, "
          f"Obergrenze: {kosten['obergrenze']} Tokens")

    md = ["# Stichprobe fuer die Kette (20.11.2026)", "",
          f"Quelle: `{v.P5}`. Leere P5-Records: **{len(leere)}**.", "",
          "## Warum gelockert", "",
          "Die strenge Fassung (Wochenlabel im Ausschnitt) trifft **"
          f"{streng} von {len(leere)}** Records. Gruende ueber alle 33: 25 ohne "
          "Score-Zeile, 30 ohne Wochenlabel, 8 mit binaerem Outcome, 3 mit nur "
          "einem Stueck. Die Kette braucht aber nur eine Zeile mit Outcome-Wert, "
          "also wird das Wochenlabel protokolliert statt verlangt.", "",
          "## Kriterien", "",
          "1. Record ohne Inhalt im P5-Lauf.",
          "2. Zwei Stuecke (Prosa plus Tabellenfenster).",
          "3. Mindestens eine Score-Zeile im Ausschnitt.",
          "4. Outcome-Typ `continuous`.",
          "5. Noch nicht gemessen (yun2024:30 ausgenommen).",
          "6. Je Dokument hoechstens zwei Records.", ""]
    md += ["## Auswahl", "",
           "| Record | Dokument | Outcome | Score-Zeilen | Wochenlabel | Gold im Ausschnitt | Prompt |",
           "|---|---|---|---:|---|---:|---:|"]
    for rid in gewaehlt:
        f = faelle[rid]
        md.append(f"| `{rid}` | {f['dokument']} | {str(f['outcome'])[:38]} | "
                  f"{f['score_zeilen']} {','.join(f['score_labels'])} | "
                  f"{'ja' if f['wochenlabel'] else 'nein'} | "
                  f"{f['goldwerte_im_ausschnitt']}/{f['goldwerte']} | {f['prompt_zeichen']} |")
    md += ["", "## Kosten", "",
           f"Gemessen auf yun2024:30: 8.003 Tokens Stufe 1, 3.262 Tokens Stufe 2, "
           f"zusammen {GEMESSEN_JE_RECORD}.",
           f"Fuenf Records: erwartet **{kosten['erwartet']}** Completion-Tokens.",
           f"Obergrenze bei ausgeschoepftem Budget (16.000 + 8.000 je Record): "
           f"**{kosten['obergrenze']}** Tokens.", "",
           "Die 33 Records haben im P5-Lauf ihr Budget im Reasoning verbraucht; "
           "die Obergrenze ist deshalb der erwartbare Worst Case.", "",
           "## Offen vor dem Lauf", "",
           "Nur yun2024:30 traegt ein Wochenlabel. Fuer die anderen vier muss "
           "Stufe 2 ohne Wochenblock auskommen (eine Tabelle, ein Block) und der "
           "Ausschnitt je Record offline geprueft werden.", ""]
    (HIER / "stichprobe_20261120.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("geschrieben:", HIER / "stichprobe_20261120.json")
    print("geschrieben:", HIER / "stichprobe_20261120.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
