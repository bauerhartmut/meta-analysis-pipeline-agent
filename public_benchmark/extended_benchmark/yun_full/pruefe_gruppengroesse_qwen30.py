#!/usr/bin/env python
"""Prueft offline, ob qwen30 Gruppengroessen auslaesst oder der Parser sie verwirft.

Rohantworten speichert der Lauf nicht, deshalb zwei Messungen:

1. Der echte Parser (`run_extended_extraction.parse_cells`) wird mit typischen
   Schreibweisen einer Gruppengroesse gefuettert. Damit steht fest, welche Formen
   durchkommen und welche stillschweigend verschwinden.
2. Die Antworten der Lesekopie werden je Modell in zwei Gruppen geteilt: Records,
   deren Gold eine Gruppengroesse traegt, und solche ohne. Die zweite Gruppe ist
   die Vergleichsbasis: Dort ist nichts zu melden, also zeigt sie, wie viele
   Zeichen das Modell je gelieferter Zelle ohnehin braucht.

Weicht die erste Gruppe davon ab, steckt ungenutzter Text in der Antwort — das
waere das Signal fuer still verworfene Zellen. Bleibt sie gleich, hat das Modell
die Zellen nicht geschrieben.

Aufruf:
    python pruefe_gruppengroesse_qwen30.py --run _lesekopie_20261118 \
        --out ../iterativ/ergebnisse/qwen30_vs_glm_20261118/gruppengroesse.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"
HARNESS = BENCH / "run_extended_extraction.py"
GRUPPENFELDER = {"intervention_group_size", "comparator_group_size"}

# Schreibweisen, die ein Modell fuer eine Gruppengroesse liefern koennte. Die
# ersten vier sind die vorgeschriebene Form und muessen durchkommen.
PARSER_FAELLE = {
    "vorschrift": {"field": "intervention_group_size", "arm": "intervention", "value": 120},
    "vorschrift_komparator": {"field": "comparator_group_size", "arm": "comparator", "value": 118},
    "wert_mit_komma": {"field": "intervention_group_size", "arm": "intervention", "value": "120,5"},
    "wert_als_string_zahl": {"field": "intervention_group_size", "arm": "intervention", "value": "120"},
    "wert_als_text": {"field": "intervention_group_size", "arm": "intervention", "value": "120 patients"},
    "feld_n": {"field": "n", "arm": "intervention", "value": 120},
    "feld_intervention_n": {"field": "intervention_n", "arm": "intervention", "value": 120},
    "feld_group_size": {"field": "group_size", "arm": "intervention", "value": 120},
    "arm_control": {"field": "comparator_group_size", "arm": "control", "value": 118},
    "arm_fehlt": {"field": "intervention_group_size", "value": 120},
}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def lade_parser():
    """Importiert parse_cells aus dem Harness, ohne den Lauf zu starten."""
    spec = importlib.util.spec_from_file_location("harness", HARNESS)
    modul = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(BENCH.parent))
    spec.loader.exec_module(modul)
    return modul.parse_cells


def parser_test(parse_cells) -> dict:
    ergebnisse = {}
    for name, zelle in PARSER_FAELLE.items():
        roh = json.dumps({"timepoint": "24", "cells": [zelle]})
        cells, fehler = parse_cells(roh)
        ergebnisse[name] = {"durchgekommen": bool(cells), "fehler": fehler}
    return ergebnisse


def messe(zeilen: list[dict]) -> dict:
    """Kennzahlen einer Record-Gruppe eines Modells."""
    zellen_je_record: list[int] = []
    zeichen_je_zelle_record: list[float] = []
    zeichen_summe = zellen_summe = 0
    gruppen_zellen = gruppen_zeitpunkt = 0
    sonstige_zellen = sonstige_zeitpunkt = 0
    meldet_n = 0

    for row in zeilen:
        cells = row.get("rows") or []
        zellen_je_record.append(len(cells))
        zeichen = row.get("content_chars") or 0
        if cells and zeichen:
            zeichen_je_zelle_record.append(zeichen / len(cells))
        zeichen_summe += zeichen
        zellen_summe += len(cells)
        if any(c["field"] in GRUPPENFELDER for c in cells):
            meldet_n += 1
        for c in cells:
            mit_zeitpunkt = bool((c.get("timepoint") or "").strip())
            if c["field"] in GRUPPENFELDER:
                gruppen_zellen += 1
                gruppen_zeitpunkt += mit_zeitpunkt
            else:
                sonstige_zellen += 1
                sonstige_zeitpunkt += mit_zeitpunkt

    return {
        "records": len(zeilen),
        "records_mit_gemeldetem_n": meldet_n,
        "zellen_je_record_median": statistics.median(zellen_je_record) if zellen_je_record else None,
        "zellen": zellen_summe,
        "zeichen": zeichen_summe,
        "zeichen_je_zelle": round(zeichen_summe / zellen_summe, 1) if zellen_summe else None,
        "zeichen_je_zelle_median": round(statistics.median(zeichen_je_zelle_record), 1)
        if zeichen_je_zelle_record else None,
        "zeichen_je_zelle_streuung": (
            [round(q, 1) for q in statistics.quantiles(zeichen_je_zelle_record, n=4)]
            if len(zeichen_je_zelle_record) > 3 else None
        ),
        "gruppen_zellen": gruppen_zellen,
        "gruppen_zellen_mit_zeitpunkt": gruppen_zeitpunkt,
        "sonstige_zellen": sonstige_zellen,
        "sonstige_zellen_mit_zeitpunkt": sonstige_zeitpunkt,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--modelle", nargs="+", default=["qwen30", "glm"])
    args = ap.parse_args()

    pt = parser_test(lade_parser())
    print("--- Parsertest ---")
    for name, fall in pt.items():
        print(f"  {'JA ' if fall['durchgekommen'] else 'NEIN'} {name}")

    rows = lies(RUNS / args.run / "predictions.jsonl")
    mit_gold_n = {
        rid for rid, rec in ((r["record_id"], r) for r in lies(RECORDS))
        if any(c["field"] in GRUPPENFELDER for c in rec["gold"]["cells"])
    }

    bericht: dict = {"run": args.run, "parser": pt, "modelle": {}}
    for modell in args.modelle:
        eigene = [r for r in rows if r["model"] == modell]
        mit_n = messe([r for r in eigene if r["record_id"] in mit_gold_n])
        ohne_n = messe([r for r in eigene if r["record_id"] not in mit_gold_n])

        # Wie viele Zellen steckten in der Antwort, wenn sie je Zelle so viele
        # Zeichen braucht wie in der Gruppe ohne Gold-N? Alles ueber der
        # gelieferten Zellzahl waere Text, der beim Parsen verloren ging. Die
        # Schaetzung ist eine grobe Schranke: Eine Gruppen-Zelle ist im JSON nur
        # rund 75 Zeichen lang, also nahe am Durchschnitt; ihr Verlust bewegt die
        # Kennzahl deshalb kaum, und 56 Baseline-Records schwanken.
        # Zwei Baselines, weil die Gruppen unterschiedlich gross sind: der
        # Gesamtquotient gewichtet lange Antworten stark, der Median je Record
        # nicht. Die Spanne der beiden ist die ehrliche Unsicherheit.
        schaetzungen = {}
        for name, basis in (
            ("gesamt", ohne_n["zeichen_je_zelle"]),
            ("median", ohne_n["zeichen_je_zelle_median"]),
        ):
            schaetzungen[name] = (
                round(mit_n["zeichen"] / basis - mit_n["zellen"], 1) if basis else None
            )
        mit_n["geschaetzt_verlorene_zellen"] = schaetzungen

        bericht["modelle"][modell] = {"mit_gold_n": mit_n, "ohne_gold_n": ohne_n}
        print(f"\n--- {modell} ---")
        for gruppe, k in (("mit Gold-N", mit_n), ("ohne Gold-N", ohne_n)):
            print(f"  {gruppe:<12} Records {k['records']:4d} | N gemeldet {k['records_mit_gemeldetem_n']:4d} "
                  f"| Zellen/Record {k['zellen_je_record_median']} | Zeichen je Zelle {k['zeichen_je_zelle']}")
        print(f"  Median je Record {mit_n['zeichen_je_zelle_median']} (mit) / {ohne_n['zeichen_je_zelle_median']} (ohne) "
              f"| Quartile mit {mit_n['zeichen_je_zelle_streuung']}")
        print(f"  geschaetzt beim Parsen verlorene Zellen: {schaetzungen}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\ngeschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
