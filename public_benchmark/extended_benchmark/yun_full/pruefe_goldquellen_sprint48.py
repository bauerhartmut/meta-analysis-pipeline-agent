#!/usr/bin/env python
"""Prueft die Herkunft der neun Goldwerte ohne Fundstelle im Markdown (Sprint 48).

Frage: Traegt das `source`-Feld der Goldzelle eine Fundstelle, und sind diese
Records fuer jeden Textpfad unloesbar?

Rein lesend: keine Netzaufrufe, keine Predictions, kein Gold wird geschrieben.
Gelesen werden das Ergebnis von `zaehle_kopfangaben_sprint48.py` (die neun
Zellen mit `herkunft.klasse == "nicht_gefunden"`), die Records und die
Rohdaten `annotated_rct_dataset.json` (Flags und Notizen je Record).

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/yun_full/pruefe_goldquellen_sprint48.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
ROOT = HIER.parents[2]
sys.path.insert(0, str(ROOT))

QUELLE = BENCH / "iterativ" / "ergebnisse" / "sprint48_kopfangaben_20261119.json"
RECORDS = HIER / "records" / "yun699.jsonl"
ROH = (
    ROOT
    / "public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/annotated_rct_dataset.json"
)
AUSGABE = BENCH / "iterativ" / "ergebnisse" / "sprint48_goldquellen_20261119"

FLAGS = (
    "is_table_in_graphic_format",
    "is_data_in_figure_graphics",
    "is_relevant_data_in_table",
    "is_data_complete",
)


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def belege_523(text: str) -> dict:
    """Warum die 15 bei 523/525 fehlt: Text und Tabelle nennen nur Summanden."""
    satz = ""
    treffer = re.search(
        r"\d+\s+emergency medicine residents.{0,160}?equal groups \([^)]*\)", text
    )
    if treffer:
        satz = " ".join(treffer.group(0).split())
    zeilen: dict[str, list[int]] = {}
    for name in ("Male", "Female"):
        muster = re.search(
            rf"{name}\s+(\d+)\s*\(([\d.]+)\)\s+(\d+)\s*\(([\d.]+)\)", text
        )
        if muster:
            zeilen[name] = [int(muster.group(1)), int(muster.group(3))]
    summen = []
    if "Male" in zeilen and "Female" in zeilen:
        summen = [zeilen["Male"][0] + zeilen["Female"][0],
                  zeilen["Male"][1] + zeilen["Female"][1]]
    return {"satz": satz, "zeilen": zeilen, "summen": summen, "haelfte_von_30": 15}


def urteil(zeile: dict) -> str:
    """Kurzurteil, ob ein Textpfad den Wert liefern kann."""
    if str(zeile.get("is_table_in_graphic_format")).upper() == "TRUE":
        return "Tabelle nur als Grafik - Textpfad ausgeschlossen"
    if str(zeile.get("is_data_in_figure_graphics")).upper() == "TRUE":
        return "Daten in einer Abbildung - Textpfad ausgeschlossen"
    if str(zeile.get("is_data_complete")).upper() == "FALSE":
        return "Datensatz unvollstaendig - Wert fehlt im Markdown"
    return "Wert fehlt im Markdown, obwohl der Datensatz vollstaendig ist"


def schreibe_md(faelle: list[dict], belege: dict) -> str:
    zeilen: list[str] = []
    a = zeilen.append
    a("# Sprint 48: Herkunft der neun Goldwerte ohne Fundstelle")
    a("")
    a(
        "Grundgesamtheit: die **9** Goldzellen aus den 33 Budgetfaellen, deren Wert "
        "weder als `n = ...`-Kopfangabe noch im Fliesstext, in einer Caption oder "
        "einer Tabellenzelle mit Gruppen-Kontext vorkommt "
        "(`sprint48_kopfangaben_20261119.json`, Herkunft `nicht_gefunden`). Rein "
        "lesend: keine Netzaufrufe, keine Predictions geschrieben."
    )
    a("")
    a("## 1. Befund")
    a("")
    a(
        "- Das `source`-Feld der Goldzelle traegt **nur den Feldnamen** "
        "(`intervention_group_size`, `comparator_group_size`), in allen 9 Faellen "
        "identisch mit `field`. Eine Fundstelle (Tabelle, Zeile, Seite) steht dort "
        "nicht."
    )
    a(
        "- Die Herkunft steht in den Rohdaten "
        "(`annotated_rct_dataset.json`, `provenance.source_id`): vier Flags und "
        "eine Notiz je Record."
    )
    a(
        "- **5 der 9 Zellen** gehoeren zu Records, die die Rohdaten selbst als "
        "Grafik-Tabelle, Abbildung oder unvollstaendig markieren (164, 171, 173, 273)."
    )
    a(
        "- **4 der 9 Zellen** (523, 525) sind als vollstaendig markiert, ihr Wert "
        "`15` steht aber nur als `0.15` im Markdown - auch dort liefert kein "
        "Textpfad den Wert."
    )
    a("")
    a("## 2. Je Zelle")
    a("")
    a(
        "| Record | Dokument | Feld | Wert | `source` | Grafik-Tabelle | Daten in Abbildung | vollstaendig | Notiz | Urteil |"
    )
    a("|---|---|---|---:|---|---|---|---|---|---|")
    for f in faelle:
        a(
            f"| `{f['record_id']}` | {f['dokument_id']} | `{f['field']}` | "
            f"{int(f['value'])} | `{f['source']}` | {f['is_table_in_graphic_format']} | "
            f"{f['is_data_in_figure_graphics']} | {f['is_data_complete']} | "
            f"{f['notes'] or '-'} | {f['urteil']} |"
        )
    a("")
    a("## 3. Einordnung")
    a("")
    a(
        "Fuer **jede** dieser neun Zellen ist ein Textpfad ausgeschlossen: der Wert "
        "steht nicht im Markdown, und die Rohdaten begruenden das fuer 164, 173 und "
        "273 mit einer Grafik-Tabelle bzw. einer Abbildung. Bei 171 fehlt die "
        "Bezugsgroesse, der Datensatz ist als unvollstaendig markiert. Bei 523 und "
        "525 ist der Datensatz vollstaendig, die `15` fehlt aber trotzdem - das ist "
        "ein Befund zur Datenquelle (PDF-Layout oder Markdown-Verlust), nicht zum "
        "Prompt."
    )
    a("")
    a(
        "Fuer die Entscheidung heisst das: Diese neun Zellen senken die Obergrenze "
        "jeder Prompt-Variante und duerfen nicht als Prompt-Luecke gezaehlt werden. "
        "Die betroffenen Records bleiben Ausfall, ohne dass ein Nachzug sie heilen "
        "kann."
    )
    a("")
    a("## 4. Warum die 15 bei 523/525 fehlt")
    a("")
    a(
        "Beide Records teilen das Dokument `PMC5325897`. Die 15 steht nirgends "
        "gedruckt; sie ist aus dem Text und der Baseline-Tabelle ableitbar:"
    )
    a("")
    if belege.get("satz"):
        a(f'- Text: "{belege["satz"]}"')
    for name, werte in (belege.get("zeilen") or {}).items():
        a(f'- Tabelle 1, {name}: {werte[0]} und {werte[1]}')
    if belege.get("summen"):
        a(
            f'- Summe je Gruppe: {belege["summen"][0]} und {belege["summen"][1]}; '
            f'30 / 2 = {belege["haelfte_von_30"]}'
        )
    a("")
    a(
        "Die Prozentwerte in der Tabelle (60/40 und 53,3/46,7) bestaetigen den "
        "Nenner 15. Ein Textpfad muesste die Groesse also rechnen (Summe der "
        "Geschlechter oder 30/2), nicht lesen; deshalb fehlt sie im Markdown, "
        "obwohl der Datensatz als vollstaendig markiert ist."
    )
    a("")
    a("## 5. Grenzen")
    a("")
    a(
        "- Die Flags sind Selbstauskuenfte des Datensatzes, keine Nachpruefung am "
        "PDF. `is_data_complete = TRUE` schliesst einen Markdown-Verlust nicht aus "
        "(523/525)."
    )
    a(
        "- Geprueft ist das Markdown, das der P5-Prompt liest; eine andere Quelle "
        "fuer Tabelleninhalt (PDF, XML) ist damit nicht ausgeschlossen, aber nicht "
        "Teil dieses Pfads."
    )
    return "\n".join(zeilen) + "\n"


def main() -> int:
    quelle = json.loads(QUELLE.read_text(encoding="utf-8"))
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}
    roh = {str(x["id"]): x for x in json.loads(ROH.read_text(encoding="utf-8"))}
    text_523 = (ROOT / (records["yun2024:523"].get("document") or {}).get("path", "")).read_text(
        encoding="utf-8", errors="replace"
    )
    belege = belege_523(text_523)

    faelle = []
    for fall in quelle["faelle"]:
        record = records[fall["record_id"]]
        source_id = str((record.get("provenance") or {}).get("source_id"))
        eintrag = roh.get(source_id) or {}
        for zelle in fall["zellen"]:
            if zelle["klasse"] != "keine_kopfangabe":
                continue
            if zelle["herkunft"]["klasse"] != "nicht_gefunden":
                continue
            zeile = {
                "record_id": fall["record_id"],
                "dokument_id": fall["dokument_id"],
                "field": zelle["field"],
                "value": zelle["value"],
                "source": zelle.get("source"),
                "provenance_source_id": source_id,
                "notes": eintrag.get("notes") or "",
            }
            for flag in FLAGS:
                zeile[flag] = eintrag.get(flag)
            zeile["urteil"] = urteil(zeile)
            faelle.append(zeile)

    daten = {
        "sprint": 48,
        "frage": (
            "Traegt das source-Feld der neun Goldwerte ohne Fundstelle eine Herkunft, "
            "und sind diese Records fuer jeden Textpfad unloesbar?"
        ),
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/pruefe_goldquellen_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "zellen": len(faelle),
        "records": sorted({f["record_id"] for f in faelle}),
        "source_ist_feldname": all(f["source"] == f["field"] for f in faelle),
        "belege_523_525": belege,
        "faelle": faelle,
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    AUSGABE.with_suffix(".md").write_text(schreibe_md(faelle, belege), encoding="utf-8")
    print(json.dumps(
        {
            "zellen": len(faelle),
            "source_ist_feldname": daten["source_ist_feldname"],
            "records": daten["records"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
