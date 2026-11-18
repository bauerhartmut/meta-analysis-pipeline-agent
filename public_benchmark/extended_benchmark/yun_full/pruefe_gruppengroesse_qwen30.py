#!/usr/bin/env python
"""Prueft offline, warum qwen30 fast keine Gruppengroessen liefert.

Zwei moegliche Ursachen, die sich trennen lassen:

1. Der Parser verwirft die Zellen (Feldname, Arm oder Wert passen nicht).
2. Das Modell nennt die Gruppengroesse gar nicht.

Dafuer wird zuerst der echte Parser (`run_extended_extraction.parse_cells`) mit
typischen Schreibweisen gefuettert. Danach werden die gespeicherten Antworten
der Lesekopie ausgewertet: Wie oft nennt ein Modell bei vorhandenem Gold-N
ueberhaupt eine Gruppengroesse, wie viele Zellen kommen je Record, wie lang ist
die Antwort, und tragen die Gruppen-Zellen einen Zeitpunkt?

Rohantworten speichert der Lauf nicht, deshalb ist der Parsertest der einzige
direkte Beleg; alles Weitere sind Messungen am gespeicherten Bestand.

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

# Schreibweisen, die ein Modell fuer eine Gruppengroesse liefern koennte.
# Die ersten beiden sind die vorgeschriebene Form und muessen durchkommen.
PARSER_FAELLE = [
    ("vorschrift", {"field": "intervention_group_size", "arm": "intervention", "value": 120}),
    ("vorschrift_komparator", {"field": "comparator_group_size", "arm": "comparator", "value": 118}),
    ("wert_mit_komma", {"field": "intervention_group_size", "arm": "intervention", "value": "120,5"}),
    ("wert_als_text", {"field": "intervention_group_size", "arm": "intervention", "value": "120 patients"}),
    ("feld_n", {"field": "n", "arm": "intervention", "value": 120},),
    ("feld_intervention_n", {"field": "intervention_n", "arm": "intervention", "value": 120}),
    ("feld_group_size", {"field": "group_size", "arm": "intervention", "value": 120}),
    ("arm_control", {"field": "comparator_group_size", "arm": "control", "value": 118}),
    ("arm_fehlt", {"field": "intervention_group_size", "value": 120}),
    ("wert_als_string_zahl", {"field": "intervention_group_size", "arm": "intervention", "value": "120"}),
]


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def lade_parser():
    """Importiert parse_cells aus dem Harness, ohne den Lauf zu starten."""
    spec = importlib.util.spec_from_file_location("harness", HARNESS)
    modul = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(BENCH.parent))
    spec.loader.exec_module(modul)
    return modul.parse_cells


def parser_test(parse_cells) -> list[dict]:
    ergebnisse = []
    for fall in PARSER_FAELLE:
        name, zelle = fall[0], fall[1]
        roh = json.dumps({"timepoint": "24", "cells": [zelle]})
        cells, fehler = parse_cells(roh)
        ergebnisse.append(
            {
                "fall": name,
                "zelle": zelle,
                "durchgekommen": bool(cells),
                "fehler": fehler,
                "geparst": cells,
            }
        )
    return ergebnisse


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--modelle", nargs="+", default=["qwen30", "glm"])
    args = ap.parse_args()

    parse_cells = lade_parser()
    pt = parser_test(parse_cells)
    print("--- Parsertest ---")
    for fall in pt:
        print(f"  {'JA ' if fall['durchgekommen'] else 'NEIN'} {fall['fall']:<24} {fall['fehler'] or ''}")

    rows = lies(RUNS / args.run / "predictions.jsonl")
    gold = {r["record_id"]: r for r in lies(RECORDS)}

    # Records, deren Gold ueberhaupt eine Gruppengroesse traegt.
    mit_gold_n = {
        rid for rid, rec in gold.items()
        if any(c["field"] in GRUPPENFELDER for c in rec["gold"]["cells"])
    }

    bericht: dict = {"run": args.run, "parser": pt, "modelle": {}}
    for modell in args.modelle:
        eigene = [r for r in rows if r["model"] == modell]
        zellen_je_record: list[int] = []
        zeichen_je_zelle: list[float] = []
        zeichen: list[int] = []
        n_gemeldet = 0
        n_cells_mit_zeitpunkt = 0
        n_cells_gesamt = 0
        sonstige_mit_zeitpunkt = 0
        sonstige_gesamt = 0
        feldnamen = Counter()
        beispiele: list[dict] = []

        for row in eigene:
            if row["record_id"] not in mit_gold_n:
                continue
            cells = row.get("rows") or []
            zellen_je_record.append(len(cells))
            if row.get("content_chars"):
                zeichen.append(row["content_chars"])
                if cells:
                    zeichen_je_zelle.append(row["content_chars"] / len(cells))
            gruppen = [c for c in cells if c["field"] in GRUPPENFELDER]
            n_gemeldet += 1 if gruppen else 0
            for c in gruppen:
                n_cells_gesamt += 1
                if (c.get("timepoint") or "").strip():
                    n_cells_mit_zeitpunkt += 1
            for c in cells:
                if c["field"] in GRUPPENFELDER:
                    continue
                sonstige_gesamt += 1
                if (c.get("timepoint") or "").strip():
                    sonstige_mit_zeitpunkt += 1
            for c in cells:
                feldnamen[c["field"]] += 1
            if not gruppen and len(beispiele) < 3 and cells:
                beispiele.append(
                    {
                        "record_id": row["record_id"],
                        "felder": [c["field"] for c in cells],
                        "content_chars": row.get("content_chars"),
                        "komplett_leer": False,
                    }
                )

        bericht["modelle"][modell] = {
            "records_mit_gold_n": len(zellen_je_record),
            "records_davon_mit_gemeldetem_n": n_gemeldet,
            "anteil_n_gemeldet": round(n_gemeldet / len(zellen_je_record), 4) if zellen_je_record else None,
            "zellen_je_record_median": statistics.median(zellen_je_record) if zellen_je_record else None,
            "content_chars_median": statistics.median(zeichen) if zeichen else None,
            "chars_je_zelle_median": round(statistics.median(zeichen_je_zelle), 1) if zeichen_je_zelle else None,
            "gruppen_zellen": n_cells_gesamt,
            "gruppen_zellen_mit_zeitpunkt": n_cells_mit_zeitpunkt,
            "sonstige_zellen": sonstige_gesamt,
            "sonstige_zellen_mit_zeitpunkt": sonstige_mit_zeitpunkt,
            "feldnamen": dict(feldnamen.most_common()),
            "beispiele_ohne_n": beispiele,
        }
        z = bericht["modelle"][modell]
        print(f"\n--- {modell} (Records mit Gold-N: {z['records_mit_gold_n']}) ---")
        print(f"  N gemeldet: {z['records_davon_mit_gemeldetem_n']} ({z['anteil_n_gemeldet']:.1%})")
        print(f"  Zellen je Record (Median): {z['zellen_je_record_median']}, "
              f"Zeichen je Zelle (Median): {z['chars_je_zelle_median']}")
        print(f"  Gruppen-Zellen: {z['gruppen_zellen']}, davon mit Zeitpunkt: {z['gruppen_zellen_mit_zeitpunkt']}")
        print(f"  sonstige Zellen: {z['sonstige_zellen']}, davon mit Zeitpunkt: {z['sonstige_zellen_mit_zeitpunkt']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\ngeschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
