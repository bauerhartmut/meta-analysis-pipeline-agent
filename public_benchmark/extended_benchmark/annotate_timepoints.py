#!/usr/bin/env python3
"""Annotiert den Zielmesszeitpunkt je Dev-Record (manuell, mit Beleg).

Die Gold-Werte bleiben unberuehrt: Das Skript prueft vor dem Schreiben, dass
jede Gold-Zelle unveraendert ist, und bricht sonst ab. Jeder Eintrag nennt den
Zeitpunkt und eine woertliche Belegstelle aus dem Artikel; wo der Artikel
keinen Zeitpunkt nennt, steht "not stated" statt einer Vermutung.

Aufruf:
    python annotate_timepoints.py            # nur pruefen, nichts schreiben
    python annotate_timepoints.py --write    # Feld in records/yun_dev.jsonl setzen
    python annotate_timepoints.py --write --md analysis/timepoints_annotation.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
# Der Lauf liest records/yun.jsonl und filtert den Split; die Dev-Kopie ist die
# ausgewertete Datei. Beide tragen dasselbe Feld, damit sie nicht auseinanderlaufen.
RECORDS = (HERE / "records" / "yun_dev.jsonl", HERE / "records" / "yun.jsonl")

# record_id -> (Zielzeitpunkt, Belegstelle im Artikel)
ZEITPUNKTE: dict[str, tuple[str, str]] = {
    # PMC57750: nur Prozentwerte, keine Gold-Zellen
    "yun2024:1": ("30 days", "event rates (%) at 30 days; nur Prozentwerte, kein Gold-Wert"),
    "yun2024:2": ("30 days", "event rates (%) at 30 days; nur Prozentwerte, kein Gold-Wert"),
    # PMC1216327: Gewichtszunahme und Krankheitsdauer ueber die gesamte Studie
    "yun2024:3": (
        "whole treatment period (until recovery)",
        "mean body weight gain +50.7 gm; Angabe ohne Messzeitpunkt, Studie bis zur Genesung",
    ),
    "yun2024:4": (
        "whole treatment period (until recovery)",
        "duration of diarrhea in hours after randomization, through recovery (49.4 / 47.5 / 26.5 h)",
    ),
    "yun2024:5": ("not stated", "Tabellenkopf der fecal-loss-Tabelle im Markdown nicht lesbar"),
    # PMC2681019: kein Gold-Wert
    "yun2024:17": ("not stated", "Record ohne Gold-Zellen"),
    "yun2024:18": ("not stated", "Record ohne Gold-Zellen"),
    "yun2024:19": ("not stated", "Record ohne Gold-Zellen"),
    # PMC3276927: Textbefunde nach der Intervention
    "yun2024:55": ("after intervention (post-test)", "'All nineteen subjects showed ... after intervention'"),
    "yun2024:56": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:57": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:58": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:59": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    "yun2024:60": ("after intervention (post-test)", "Textbefund nach Intervention, Abschnitt Results"),
    # PMC3580751: Periodenvergleich
    "yun2024:83": (
        "Period 2 (2007 to 2010)",
        "intervention group 9.3 +/- 11.9 days vs. 9.9 +/- 14.8 days (period 1 vs period 2)",
    ),
    # PMC3751573: T1 nach dem Praktikum
    "yun2024:88": ("T1 (after practicum training)", "Spalten T0/T1; T1 = nach dem Praktikum"),
    # PMC4450164: DTPA-Scan, Zeitpunkt im Artikel nicht genannt
    "yun2024:120": (
        "post-operative DTPA scan (timepoint not stated)",
        "DTPA scan: Partial obstruction 8/20 13/44; kein Zeitpunkt im Text",
    ),
    # PMC5244530: alle Variablen zu baseline, 3, 6 und 12 Monaten
    "yun2024:186": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:187": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:188": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:189": (
        "12 months follow-up",
        "'All variables were measured at baseline and 3, 6, and 12 months.'",
    ),
    "yun2024:190": (
        "12 months follow-up",
        "Sedatives: Intervention 26/64/53/52, TAU 32/73/56/51 (baseline, 3, 6, 12 months); Gold 52/51 = 12 Monate",
    ),
    "yun2024:191": (
        "Total 0-12 months",
        "sick leave: 0-3 months 31/48, 4-12 months 35/47, Total 0-12 months 49/64",
    ),
    "yun2024:192": (
        "6 months follow-up",
        "Antidepressants: Intervention 27/90/86/74, TAU 43/96/78/77; Gold 86/78 = 6 Monate",
    ),
    # PMC5771543: Wirksamkeit zu Woche 8, Nebenwirkungen im On-Therapy-Zeitraum
    "yun2024:260": ("Week 8", "'Summary of Secondary Efficacy Outcomes at Week 8' (CGI-I 79/101, 62/99)"),
    "yun2024:261": ("Week 8", "'Summary of Secondary Efficacy Outcomes at Week 8' (CGI-I 68/99, 62/99)"),
    "yun2024:262": ("On-Therapy Period", "'Adverse Events ... On-Therapy Period' (69/115, 79/112)"),
    "yun2024:263": ("On-Therapy Period", "'Adverse Events ... On-Therapy Period' (72/112, 79/112)"),
}

# PMC5498715: Tabelle mit Pre-test, Post-test, Follow up after 4 months; Gold = Post-test
for _nummer in range(224, 239):
    ZEITPUNKTE[f"yun2024:{_nummer}"] = (
        "Post-test",
        "Spalten 'Pre-test', 'Post-test', 'Follow up after 4 months'; Gold entspricht Post-test",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Feld in die Records schreiben")
    parser.add_argument("--md", type=Path, default=None, help="Uebersicht als Markdown schreiben")
    parser.add_argument("--records", type=Path, nargs="+", default=list(RECORDS))
    args = parser.parse_args()

    dev = [json.loads(line) for line in (HERE / "records" / "yun_dev.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = {record["record_id"] for record in dev}
    fehlend = sorted(ids - set(ZEITPUNKTE))
    ueberzaehlig = sorted(set(ZEITPUNKTE) - ids)
    if fehlend or ueberzaehlig:
        print(f"FEHLER: ohne Annotation {fehlend}, ohne Record {ueberzaehlig}")
        return 2

    for pfad in args.records:
        records = [json.loads(line) for line in pfad.read_text(encoding="utf-8").splitlines() if line.strip()]
        vorher = {record["record_id"]: json.dumps(record["gold"], sort_keys=True, ensure_ascii=False) for record in records}
        geschrieben = 0
        for record in records:
            if record["record_id"] not in ZEITPUNKTE:
                continue
            target, beleg = ZEITPUNKTE[record["record_id"]]
            record["timepoint"] = {"target": target, "evidence": beleg, "annotated": "2026-11-15"}
            geschrieben += 1
        nachher = {record["record_id"]: json.dumps(record["gold"], sort_keys=True, ensure_ascii=False) for record in records}
        if vorher != nachher:
            print("FEHLER: Gold-Werte wuerden sich aendern, Abbruch")
            return 3
        if args.write:
            pfad.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8"
            )
            print(f"geschrieben: {pfad} ({geschrieben} von {len(records)} Records, Gold unveraendert)")

    records = dev
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        zeilen = ["# Zielmesszeitpunkt je Dev-Record", "", "| Record | Zielzeitpunkt | Beleg |", "|---|---|---|"]
        for record in records:
            info = record["timepoint"]
            zeilen.append(f"| `{record['record_id']}` | {info['target']} | {info['evidence']} |")
        args.md.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.md}")

    from collections import Counter

    print("Verteilung:", dict(Counter(record["timepoint"]["target"] for record in records)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
