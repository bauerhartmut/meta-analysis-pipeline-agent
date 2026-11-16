#!/usr/bin/env python
"""Zieht eine geschichtete Stichprobe von 60 Testrecords (deterministisch).

Schichten: Outcome-Typ und Anzahl der Goldzellen je Record, weil beides die
Aufgabe bestimmt (6 Zellen = vollstaendig kontinuierlich, 2 Zellen = nur
Mittelwerte, 4 Zellen = binaer bzw. N+Mean). Die Zahl je Schicht ist proportional
zur Schichtgroesse im Testsplit, auf 60 aufgerundet.

Auswahl innerhalb einer Schicht: die Records werden nach numerischer id sortiert
und mit einem festen Schritt (Index * Laenge / Anzahl, ganzzahlig) gezogen. Das
ist reproduzierbar, ohne Zufallsgenerator und ohne Blick auf Modellausgaben.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "records" / "yun699.jsonl"
AUSGABE = HERE / "stichprobe60.json"
GESAMT = 60


def schicht(record: dict) -> str:
    return f"{record['context']['outcome_type']}:{len(record['gold']['cells'])}"


def main() -> int:
    rows = [json.loads(z) for z in RECORDS.read_text(encoding="utf-8").splitlines() if z.strip()]
    test = [r for r in rows if r["document"]["split"] == "test"]
    schichten: dict[str, list[dict]] = {}
    for record in test:
        schichten.setdefault(schicht(record), []).append(record)
    gesamt_test = len(test)

    # Groesste-Reste-Verfahren fuer die Schichtgroessen.
    roh = {name: len(mitglieder) / gesamt_test * GESAMT for name, mitglieder in schichten.items()}
    ziel = {name: int(wert) for name, wert in roh.items()}
    rest = GESAMT - sum(ziel.values())
    for name, _ in sorted(roh.items(), key=lambda paar: paar[1] - int(paar[1]), reverse=True)[:rest]:
        ziel[name] += 1

    gewaehlt: list[dict] = []
    for name in sorted(schichten):
        mitglieder = sorted(schichten[name], key=lambda r: int(r["record_id"].split(":")[1]))
        anzahl = ziel[name]
        indizes = [int(i * len(mitglieder) / anzahl) for i in range(anzahl)]
        gewaehlt += [mitglieder[i] for i in indizes]

    ids = [r["record_id"] for r in gewaehlt]
    ergebnis = {
        "methode": "geschichtet nach outcome_type und Goldzellenzahl, proportional, "
        "gleichmaessiger Schritt ueber die nach id sortierte Schicht",
        "gesamttest": gesamt_test,
        "stichprobe": len(ids),
        "schichten": {
            name: {
                "test": len(schichten[name]),
                "ziel": ziel[name],
                "gewaehlt": sum(1 for r in gewaehlt if schicht(r) == name),
            }
            for name in sorted(schichten)
        },
        "ids": ids,
    }
    AUSGABE.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(ids)} Records aus {gesamt_test} Testrecords")
    print("Schichten:", Counter(schicht(r) for r in gewaehlt))
    print("IDs:", ",".join(ids))
    print(f"geschrieben: {AUSGABE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
