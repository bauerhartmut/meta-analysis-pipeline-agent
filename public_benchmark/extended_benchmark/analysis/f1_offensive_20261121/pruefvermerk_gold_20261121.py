#!/usr/bin/env python3
"""Pruefvermerk fuer die fuenf Gold-Verdachtsfaelle.

Offline, ohne Netzaufruf, ohne Aenderung an Gold. Je Fall werden die
Belegzeilen aus dem Dokument zitiert und ein Verdikt gesetzt:

* `armtausch_bestaetigt` - das Dokument nennt die Arme andersherum als Gold.
* `verdacht_widerlegt`  - der Goldwert ist im Dokument belegt.
* `gold_aus_subgruppentabelle` - der Goldwert steht in einer Subgruppentabelle,
  nicht in der Haupttabelle.
* `gold_nicht_belegt` - der Goldwert steht im Dokument nicht als Zellwert; er
  erscheint nur als Grenze eines Intervalls oder wurde zurueckgerechnet.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/pruefvermerk_gold_20261121.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))

import vergleiche_20261120 as v  # noqa: E402

ERSATZ = {"\u00b1": "+/-", "\u2212": "-", "\u2265": ">=", "\u2264": "<=",
          "\u00d7": "x", "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
          "\u201c": "\"", "\u201d": "\"", "\u00a0": " ", "\u2007": " ",
          "\u2009": " ", "\u202f": " ", "\u2002": " ", "\u2003": " "}


def ascii_text(text: str) -> str:
    """Zitate ASCII-fest machen (Regel: keine Nicht-ASCII-Zeichen im Repo)."""
    for zeichen, ersatz in ERSATZ.items():
        text = text.replace(zeichen, ersatz)
    return text.encode("ascii", "replace").decode()


FAELLE: list[dict[str, Any]] = [
    {"record_id": "yun2024:331", "beleg": [6, 40, 93], "verdikt": "armtausch_bestaetigt",
     "notiz": "Drei Tabellenkoepfe nennen Placebo vor Aripiprazole; Gold fuehrt 45 als Intervention."},
    {"record_id": "yun2024:334", "beleg": [6, 40, 93], "verdikt": "armtausch_bestaetigt",
     "notiz": "Gleiches Dokument wie 331, gleiche Zellwerte."},
    {"record_id": "yun2024:335", "beleg": [6, 40, 93], "verdikt": "armtausch_bestaetigt",
     "notiz": "Gleiches Dokument wie 331, gleiche Zellwerte."},
    {"record_id": "yun2024:336", "beleg": [6, 40, 93], "verdikt": "armtausch_bestaetigt",
     "notiz": "Gleiches Dokument wie 331, gleiche Zellwerte."},
    {"record_id": "yun2024:345", "beleg": [13, 28, 51, 56], "verdikt": "gold_nicht_belegt",
     "notiz": "Gold nennt Mittel 2.3 (SD 2.63, laut Record aus CI zurueckgerechnet). Im Dokument"
              " steht 2.3 nur als obere Grenze der Median-Differenz (Zeile 51: 0.75 (--1.6 to 2.3),"
              " Zeile 56: 0.35 (--2.3 to 2.8), Abstract Zeile 28 ebenso); die Baseline-Zeile 13"
              " nennt 5.4 +/- 2.6 bzw. 5.7 +/- 2. Eine Mittelwertzelle mit 2.3 gibt es nicht."},
    {"record_id": "yun2024:196", "beleg": [8, 65, 82], "verdikt": "gold_aus_subgruppentabelle",
     "notiz": "Gold (n = 24, Mittel 1.29/1.08) steht in Tabelle 3, Woche 28; deren Kopf nennt "
              "die Subgruppe MMSE-J 20 bis 23. Die Haupttabelle 2 nennt fuer Woche 28 die Werte "
              "80/78 (Mittel 2.30/2.46). Der Wert ist belegt, gehoert aber zur Subgruppe."},
]


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ergebnis: list[dict[str, Any]] = []
    for fall in FAELLE:
        record = records[fall["record_id"]]
        pfad = REPO / record["document"]["path"]
        zeilen = pfad.read_text(encoding="utf-8", errors="replace").splitlines()
        context = record.get("context") or {}
        gold = [(str(z.get("field") or ""), v.arm_von(z), v.zahl(z.get("value")))
                for z in (record.get("gold") or {}).get("cells") or []
                if "group_size" in str(z.get("field") or "")]
        zitate = [{"zeile": n, "text": ascii_text(zeilen[n - 1].strip()[:200])} for n in fall["beleg"]]
        ergebnis.append({
            "record_id": fall["record_id"],
            "dokument": pfad.name,
            "intervention": context.get("intervention"),
            "comparator": context.get("comparator"),
            "gold_group_size": gold,
            "beleg": zitate,
            "verdikt": fall["verdikt"],
            "notiz": fall["notiz"],
        })

    (HIER / "pruefvermerk_gold_20261121.json").write_text(
        json.dumps({"stand": "2026-11-21", "gold_geaendert": False, "faelle": ergebnis},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    bloecke = []
    for e in ergebnis:
        zitate = "\n".join(f"  - Zeile {z['zeile']}: `{z['text']}`" for z in e["beleg"])
        gold = ", ".join(f"{feld} ({arm}) = {wert}" for feld, arm, wert in e["gold_group_size"])
        bloecke.append(f"""### `{e['record_id']}` ({e['dokument']})

- Kontext: intervention = `{e['intervention']}`, comparator = `{e['comparator']}`
- Gold: {gold}
- Verdikt: `{e['verdikt']}`
- Notiz: {e['notiz']}

Belegstellen:

{zitate}
""")
    bericht = f"""# Pruefvermerk Gold (21.11.2026)

Offline erstellt, ohne Netzaufruf. Gold wurde **nicht** geaendert; der Vermerk
haelt nur fest, ob das Dokument die Goldbeschriftung stuetzt.

| Record | Verdikt |
|---|---|
""" + "\n".join(f"| `{e['record_id']}` | `{e['verdikt']}` |" for e in ergebnis) + """

## Faelle

""" + "\n".join(bloecke) + """
## Folge

Bei den vier `PMC5617873`-Records sind die Arme im Dokument eindeutig anders
herum beschriftet als in Gold. Ein Gold-Fix waere eine Datenentscheidung und
bleibt offen; bis dahin zaehlen diese vier Zellen in jeder Regelbilanz als FP.
Bei `yun2024:196` ist Gold belegt, der Fehler liegt bei der Regel, die die
Kopfzeile von Tabelle 1 statt der Zeile aus Tabelle 2 liest.
"""
    (HIER / "pruefvermerk_gold_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    for e in ergebnis:
        print(f"{e['record_id']:14s} {e['verdikt']:22s} {e['dokument']}")
    print(f"Gold geaendert: nein | Faelle: {len(ergebnis)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
