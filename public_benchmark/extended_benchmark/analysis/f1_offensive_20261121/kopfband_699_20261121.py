#!/usr/bin/env python3
"""Kostet die Kopfband-Regel richtige Groessenzellen ausserhalb der P5-Records?

Offline, ohne Netzaufruf. Ueber alle 699 Records aus `yun699.jsonl` wird jede
Goldzelle der Gruppengroesse zweimal gelesen: mit `KOPFBAND_ARM = False` (jede
`n =`-Zeile im Kopfband gilt) und mit `True` (nur mit Armbezeichnung). Gezaehlt
wird, welche Zellen in beiden Staenden richtig sind, welche die Regel kostet und
welche sie gewinnt. Das ist die Gegenprobe zur P5-Messung, die nur die 103
Records mit gespeicherten Vorhersagen abdeckt.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/kopfband_699_20261121.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(ANALYSE / "f1_offensive_20261121"))

import vergleiche_20261120 as v  # noqa: E402
import zielzeile_alle_20261121 as m  # noqa: E402

FORMATE = ("mittel_sd", "plus_minus")


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5_ids = {z["record_id"] for z in v.lade(v.P5)}
    zellen: list[dict[str, Any]] = []
    fehlende_dokumente = 0
    for rid, record in records.items():
        felder = [(str(z.get("field") or ""), v.arm_von(z), v.zahl(z.get("value")))
                  for z in (record.get("gold") or {}).get("cells") or []]
        felder = [f for f in felder if f[0].endswith("group_size") and f[2] is not None]
        if not felder:
            continue
        pfad = m.REPO / record["document"]["path"]
        if not pfad.exists():
            fehlende_dokumente += 1
            continue
        text = pfad.read_text(encoding="utf-8", errors="replace")
        for feld, arm, gold in felder:
            m.KOPFBAND_ARM = False
            ohne = m.lies(record, text, feld, arm, m.alias_mod.ALIAS, True, FORMATE)
            m.KOPFBAND_ARM = True
            mit = m.lies(record, text, feld, arm, m.alias_mod.ALIAS, True, FORMATE)

            def richtig(x: dict[str, Any] | None) -> bool:
                return x is not None and abs(float(x["value"]) - gold) < 1e-6

            zellen.append({
                "record_id": rid, "feld": feld, "arm": arm, "gold": gold,
                "p5": rid in p5_ids,
                "ohne_wert": None if ohne is None else ohne["value"],
                "mit_wert": None if mit is None else mit["value"],
                "ohne_richtig": richtig(ohne), "mit_richtig": richtig(mit),
                "mit_quelle": None if mit is None else mit.get("quelle"),
                "ohne_quelle": None if ohne is None else ohne.get("quelle"),
            })
    m.KOPFBAND_ARM = True

    verloren = [z for z in zellen if z["ohne_richtig"] and not z["mit_richtig"]]
    gewonnen = [z for z in zellen if z["mit_richtig"] and not z["ohne_richtig"]]
    ergebnis = {
        "stand": "2026-11-21",
        "records": len(records),
        "records_mit_goldgroesse": len({z["record_id"] for z in zellen}),
        "fehlende_dokumente": fehlende_dokumente,
        "zellen": len(zellen),
        "ohne_regel": {"richtig": sum(1 for z in zellen if z["ohne_richtig"]),
                       "falsch": sum(1 for z in zellen if not z["ohne_richtig"])},
        "mit_regel": {"richtig": sum(1 for z in zellen if z["mit_richtig"]),
                      "falsch": sum(1 for z in zellen if not z["mit_richtig"])},
        "ausserhalb_p5": {
            "zellen": sum(1 for z in zellen if not z["p5"]),
            "verloren": sum(1 for z in verloren if not z["p5"]),
            "gewonnen": sum(1 for z in gewonnen if not z["p5"]),
        },
        "verloren": verloren,
        "gewonnen": gewonnen,
    }
    (HIER / "kopfband_699_20261121.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=True), encoding="utf-8")

    md = ["# Kopfband-Regel ausserhalb der P5-Records (21.11.2026)", "",
          "Offline, ohne Netzaufruf. `kopfband_699_20261121.py`. Jede Goldzelle der",
          f"Gruppengroesse ueber alle {len(records)} Records, zweimal gelesen: ohne und",
          "mit `KOPFBAND_ARM`.", "",
          "| Kennzahl | Wert |", "|---|---:|",
          f"| Records mit Goldgroesse | {ergebnis['records_mit_goldgroesse']} |",
          f"| Groessenzellen | {ergebnis['zellen']} |",
          f"| davon in P5-Records | {ergebnis['zellen'] - ergebnis['ausserhalb_p5']['zellen']} |",
          f"| richtig ohne Regel | {ergebnis['ohne_regel']['richtig']} |",
          f"| richtig mit Regel | {ergebnis['mit_regel']['richtig']} |",
          f"| Zellen verloren | {len(verloren)} (davon ausserhalb P5: "
          f"{ergebnis['ausserhalb_p5']['verloren']}) |",
          f"| Zellen gewonnen | {len(gewonnen)} (davon ausserhalb P5: "
          f"{ergebnis['ausserhalb_p5']['gewonnen']}) |", "",
          "## Verlorene Zellen", "",
          "| Record | Feld | Arm | Gold | ohne | mit | P5 |",
          "|---|---|---|---:|---:|---:|---|"]
    for z in verloren:
        md.append(f"| `{z['record_id']}` | {z['feld'].replace('_group_size', '')} | "
                  f"{z['arm']} | {z['gold']} | {z['ohne_wert']} | {z['mit_wert']} | "
                  f"{'ja' if z['p5'] else 'nein'} |")
    md += ["", "## Gewonnene Zellen", "",
           "| Record | Feld | Arm | Gold | ohne | mit | P5 |",
           "|---|---|---|---:|---:|---:|---|"]
    for z in gewonnen:
        md.append(f"| `{z['record_id']}` | {z['feld'].replace('_group_size', '')} | "
                  f"{z['arm']} | {z['gold']} | {z['ohne_wert']} | {z['mit_wert']} | "
                  f"{'ja' if z['p5'] else 'nein'} |")
    (HIER / "kopfband_699_20261121.md").write_text(
        "\n".join(md) + "\n", encoding="ascii", errors="replace")

    print(f"Records {len(records)} | Zellen {len(zellen)} | "
          f"ohne {ergebnis['ohne_regel']} | mit {ergebnis['mit_regel']}")
    print(f"verloren {len(verloren)} (ausserhalb P5 "
          f"{ergebnis['ausserhalb_p5']['verloren']}) | gewonnen {len(gewonnen)} "
          f"(ausserhalb P5 {ergebnis['ausserhalb_p5']['gewonnen']})")
    for z in verloren:
        print(f"  verloren {z['record_id']:14s} {z['feld']:24s} {z['arm']:11s} "
              f"gold {z['gold']:>7} ohne {z['ohne_wert']} mit {z['mit_wert']} "
              f"p5={z['p5']}")
    for z in gewonnen:
        print(f"  gewonnen {z['record_id']:14s} {z['feld']:24s} {z['arm']:11s} "
              f"gold {z['gold']:>7} ohne {z['ohne_wert']} mit {z['mit_wert']} "
              f"p5={z['p5']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
