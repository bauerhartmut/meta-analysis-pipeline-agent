#!/usr/bin/env python3
"""Groessen-FP sichten und die 37 Zellen in P5 einsetzen.

Offline, ohne Netzaufruf. Teil A sichtet die Groessen-FP des Endlaufs: steht der
Goldwert in einer anderen Tabelle, in derselben Tabelle oder gar nicht in einer
Groessenzeile? Teil B ersetzt die gelieferten Zellen in den P5-Vorhersagen und
rechnet die Bilanz ueber alle 699 Records.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/groessen_fp_einsatz_20261121.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
import zielzeile_alle_20261121 as leser  # noqa: E402
from zahlabgleich_20261121 import zahl_positionen  # noqa: E402

KAPITION = re.compile(r"^\s*(?:Table|TABLE)\s*\d|:::\s*caption", re.IGNORECASE)


def tabellen_id(zeilen: list[str], i: int) -> str:
    """Naechste Tabellenbeschriftung ueber Zeile `i` (leer, wenn keine)."""
    for j in range(i, max(-1, i - 80), -1):
        if KAPITION.search(zeilen[j]):
            return " ".join(zeilen[j].strip().split())[:80]
    return ""


def einsatz(zellen: list[dict[str, Any]], p5: dict[str, dict[str, Any]],
            records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Zellen in die P5-Vorhersagen einsetzen und die Bilanz ueber alle Records ziehen."""
    neu: dict[str, list[dict[str, Any]]] = {
        rid: json.loads(json.dumps(v.zellen(zeile))) for rid, zeile in p5.items()}
    ersetzt = neu_angelegt = 0
    for e in zellen:
        vor = neu.setdefault(e["record_id"], [])
        getroffen = False
        for z in vor:
            if (str(z.get("field") or ""), v.arm_von(z)) == (e["feld"], e["arm"]):
                z["value"] = e["regel"]["value"]
                getroffen = True
                break
        if getroffen:
            ersetzt += 1
        else:
            vor.append({"field": e["feld"], "group": e["arm"], "value": e["regel"]["value"]})
            neu_angelegt += 1

    vorher = {"tp": 0, "fp": 0, "fn": 0}
    nachher = {"tp": 0, "fp": 0, "fn": 0}
    geaendert = 0
    for rid, zeile in records.items():
        gold = (zeile.get("gold") or {}).get("cells") or []
        b_vor = v.bilanz_p5(gold, v.zellen(p5.get(rid)))
        b_nach = v.bilanz_p5(gold, neu.get(rid, []))
        for k in vorher:
            vorher[k] += b_vor[k]
            nachher[k] += b_nach[k]
        if b_vor != b_nach:
            geaendert += 1
    return {"vorher": vorher, "nachher": nachher, "records_geaendert": geaendert,
            "zellen_ersetzt": ersetzt, "zellen_neu": neu_angelegt}


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}
    texte = {rid: (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in faelle}}

    ergebnis = leser.messe(faelle, records, texte, leser.alias_mod.ALIAS, True,
                           mean_formate=("mittel_sd", "plus_minus"))
    zellen = list(ergebnis["detail"])
    fp_groesse = [e for e in ergebnis["detail"]
                  if not e["richtig"] and e["feld"].endswith("group_size")]

    sichtung: list[dict[str, Any]] = []
    for e in fp_groesse:
        rid = e["record_id"]
        zeilen = texte[rid].splitlines()
        regel_zeile = e["regel"]["zeile"] - 1
        gold = float(e["gold"])
        gold_zeilen = [i for i, z in enumerate(zeilen)
                       if leser.g.ist_groessenzeile(z) and zahl_positionen(gold, z)]
        if not gold_zeilen:
            # Gold kann in einer Datenzeile einer anderen Tabelle stehen
            # (etwa n = 24 in Tabelle 2 ohne `n =`-Marker).
            daten = [i for i, z in enumerate(zeilen)
                     if zahl_positionen(gold, z) and len(re.split(r"\s{2,}", z.strip())) >= 2]
            if daten and tabellen_id(zeilen, daten[0]) != tabellen_id(zeilen, regel_zeile):
                klasse = "gold_in_anderer_tabelle_ohne_groessenzeile"
            else:
                klasse = "gold_nicht_in_groessenzeile"
        elif regel_zeile in gold_zeilen:
            klasse = "falsche_spalte"
        else:
            tid_regel = tabellen_id(zeilen, regel_zeile)
            tid_gold = tabellen_id(zeilen, gold_zeilen[0])
            klasse = "falsche_tabelle" if tid_regel != tid_gold else "andere_groessenzeile_gleiche_tabelle"
        sichtung.append({"record_id": rid, "feld": e["feld"], "regelwert": e["regel"]["value"],
                         "regel_zeile": e["regel"]["zeile"], "gold": gold,
                         "gold_zeilen": [i + 1 for i in gold_zeilen][:3], "klasse": klasse,
                         "tabelle_regel": tabellen_id(zeilen, regel_zeile),
                         "tabelle_gold": tabellen_id(zeilen, gold_zeilen[0]) if gold_zeilen else ""})

    alle = einsatz(zellen, p5, records)
    gut = einsatz([e for e in zellen if e["richtig"]], p5, records)
    vorher, nachher = alle["vorher"], alle["nachher"]
    geaendert, ersetzt, neu_angelegt = alle["records_geaendert"], alle["zellen_ersetzt"], alle["zellen_neu"]

    ergebnis_json = {
        "stand": "2026-11-21",
        "zellen": len(zellen),
        "fp_groesse": len(fp_groesse),
        "sichtung": sichtung,
        "klassen": dict(Counter(x["klasse"] for x in sichtung)),
        "records": len(records),
        "vorher": vorher,
        "nachher": nachher,
        "delta": {k: nachher[k] - vorher[k] for k in vorher},
        "records_geaendert": geaendert,
        "zellen_ersetzt": ersetzt,
        "zellen_neu": neu_angelegt,
        "nur_richtige": gut,
    }
    (HIER / "groessen_fp_einsatz_20261121.json").write_text(
        json.dumps(ergebnis_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    sicht_tab = "\n".join(
        f"| `{x['record_id']}` | {x['feld']} | {x['regelwert']} | {x['gold']} | {x['klasse']} | "
        f"{x['regel_zeile']} | {', '.join(str(g) for g in x['gold_zeilen']) or '-'} |"
        for x in sichtung)
    bericht = f"""# Groessen-FP und Einsatz der Zellen (21.11.2026)

Offline, ohne Netzaufruf.

## Teil A: die {len(fp_groesse)} Groessen-FP

| Record | Feld | Regelwert | Gold | Klasse | Zeile Regel | Zeile Gold |
|---|---|---:|---:|---|---:|---|
{sicht_tab}

Klassen: {dict(Counter(x['klasse'] for x in sichtung))}

## Teil B: {len(zellen)} Zellen in P5 eingesetzt

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | {vorher['tp']} | {nachher['tp']} | {nachher['tp'] - vorher['tp']:+d} |
| FP | {vorher['fp']} | {nachher['fp']} | {nachher['fp'] - vorher['fp']:+d} |
| FN | {vorher['fn']} | {nachher['fn']} | {nachher['fn'] - vorher['fn']:+d} |

Betroffene Records: {geaendert} von {len(records)}.

## Teil C: nur die richtigen Zellen

Setzt man nur die {sum(1 for e in zellen if e['richtig'])} richtigen Zellen ein
(ohne die {sum(1 for e in zellen if not e['richtig'])} falschen), dann:

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | {gut['vorher']['tp']} | {gut['nachher']['tp']} | {gut['nachher']['tp'] - gut['vorher']['tp']:+d} |
| FP | {gut['vorher']['fp']} | {gut['nachher']['fp']} | {gut['nachher']['fp'] - gut['vorher']['fp']:+d} |
| FN | {gut['vorher']['fn']} | {gut['nachher']['fn']} | {gut['nachher']['fn'] - gut['vorher']['fn']:+d} |

Das ist die Obergrenze: {gut['zellen_neu']} Zellen waren neu, {gut['zellen_ersetzt']} ersetzten
einen vorhandenen falschen Wert.
"""
    (HIER / "groessen_fp_einsatz_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"Groessen-FP {len(fp_groesse)}: {dict(Counter(x['klasse'] for x in sichtung))}")
    for x in sichtung:
        print(f"  {x['record_id']:14s} {x['regelwert']:>6} vs gold {x['gold']:>6} | {x['klasse']:36s} "
              f"| Regelzeile {x['regel_zeile']} | Goldzeilen {x['gold_zeilen']}")
        print(f"      Tabelle Regel: {x['tabelle_regel'] or '-'}")
        print(f"      Tabelle Gold : {x['tabelle_gold'] or '-'}")
    print(f"Zellen {len(zellen)} | vorher {vorher} | nachher {nachher} | "
          f"delta {{'tp': {nachher['tp'] - vorher['tp']}, 'fp': {nachher['fp'] - vorher['fp']}, "
          f"'fn': {nachher['fn'] - vorher['fn']}}}")
    print(f"nur richtige Zellen {sum(1 for e in zellen if e['richtig'])}: {gut}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
