#!/usr/bin/env python
"""Auswertung ohne die Records, deren Goldannotation belegt konflikt aer ist.

Drei Records der 60er-Stichprobe enthalten im Originalartikel zwei verschiedene
Angaben; Gold und Modell lesen unterschiedliche Stellen. Sie sind keine
Modellfehler und verzerren Precision und Recall in beide Richtungen:

* yun2024:524 - Fliesstext "17.73 +- 0.46" gegen Tabelle "17.73 +- 1.09"
* yun2024:447 - "intervention, n=114" gegen Tabellenkopf "I; n=104"
* yun2024:669 - Tabellenzeile mit drei Spalten, Modellwert im Artikel nicht auffindbar

Das Skript rechnet die Kennzahlen mit und ohne diese Records und schreibt beide
Varianten nebeneinander, damit der Unterschied nachvollziehbar bleibt.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"
KONFLIKT = ["yun2024:524", "yun2024:447", "yun2024:669"]
LAEUFE = [
    ("yun699_test60_20261116", "60 Records, 4000 Tokens"),
    ("yun20_4000_glm_20261116", "20 Records, 4000 Tokens"),
]


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def kenn(rows: list[dict], recs: dict[str, dict], ausschluss: set[str]) -> dict:
    richtig = falsch = fehlend = 0
    for row in rows:
        if row["record_id"] in ausschluss:
            continue
        gold = {c["field"]: c["value"] for c in recs[row["record_id"]]["gold"]["cells"]}
        pred: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            pred.setdefault(zelle["field"], zelle["value"])
        for feld, wert in gold.items():
            m = pred.get(feld)
            if m is None:
                fehlend += 1
            elif abs(m - wert) > 1e-9:
                falsch += 1
            else:
                richtig += 1
    p = richtig / (richtig + falsch) if richtig + falsch else None
    r = richtig / (richtig + falsch + fehlend) if richtig + falsch + fehlend else None
    return {
        "richtig": richtig,
        "falsch": falsch,
        "fehlend": fehlend,
        "precision": round(p, 4) if p else None,
        "recall": round(r, 4) if r else None,
        "f1": round(2 * p * r / (p + r), 4) if p and r else None,
    }


def main() -> int:
    recs = {r["record_id"]: r for r in lies(HERE / "records" / "yun699.jsonl")}
    ergebnis = []
    for run, label in LAEUFE:
        pfad = RUNS / run / "predictions.jsonl"
        if not pfad.exists():
            continue
        rows = lies(pfad)
        ergebnis.append(
            {
                "run": run,
                "label": label,
                "mit_konflikten": kenn(rows, recs, set()),
                "ohne_konflikte": kenn(rows, recs, set(KONFLIKT)),
                "ausgeschlossen": [r for r in KONFLIKT if any(x["record_id"] == r for x in rows)],
            }
        )
    ziel = HERE / "ausschluss_konflikte_20261116.json"
    ziel.write_text(json.dumps({"stand": "2026-11-16", "ergebnisse": ergebnis}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for eintrag in ergebnis:
        m, o = eintrag["mit_konflikten"], eintrag["ohne_konflikte"]
        print(f"{eintrag['run']}:")
        print(f"  mit Konflikten : P {m['precision']} R {m['recall']} F1 {m['f1']} ({m['richtig']}/{m['falsch']}/{m['fehlend']})")
        print(f"  ohne Konflikte : P {o['precision']} R {o['recall']} F1 {o['f1']} ({o['richtig']}/{o['falsch']}/{o['fehlend']})")
    print(f"geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
