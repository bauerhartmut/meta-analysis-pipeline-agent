#!/usr/bin/env python3
"""Zeilenbindung ueber alle 699 Records: verschwinden die Zusatz-FP der 41?

Die Regel ist dieselbe wie in `zeilenbindung_20261121.py` (importiert, nicht
kopiert). Gemessen wird additiv, weil `ersetzen` in der 41er-Auswahl zahlengleich
war. Zusaetzlich wird getrennt ausgewiesen, wie viel davon auf die 41 schweren
Records entfaellt und wie viel auf die uebrigen 658.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zeilenbindung_gesamt_20261121.py
"""
from __future__ import annotations

import json
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
from zeilenbindung_20261121 import binde, wende_an  # noqa: E402


def summe(werte: list[dict[str, int]]) -> dict[str, int]:
    return {k: sum(w[k] for w in werte) for k in ("tp", "fp", "fn")}


def main() -> int:
    records = list(v.lade(v.RECORDS))
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}
    auswahl = json.loads(
        (ANALYSE / "schwere_records_20261121" / "auswahl_20261121.json").read_text(encoding="utf-8")
    )["records"]
    ids41 = {a["record_id"] for a in auswahl}
    texte = {
        r["record_id"]: (REPO / r["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        for r in records
    }

    laeufe: list[dict[str, Any]] = []
    for gruppe_modus in ("streng", "erstes"):
        vor: list[dict[str, int]] = []
        nach: list[dict[str, int]] = []
        vor41: list[dict[str, int]] = []
        nach41: list[dict[str, int]] = []
        gebunden = 0
        gebunden41 = 0
        zellen = richtig = 0
        zellen41 = richtig41 = 0
        for r in records:
            rid = r["record_id"]
            gold = (r.get("gold") or {}).get("cells") or []
            roh = v.zellen(p5.get(rid))
            bindung = binde(r, texte[rid], gruppe_modus)
            neu, _ = wende_an(roh, bindung, "additiv")
            b_vor = v.bilanz_p5(gold, roh)
            b_nach = v.bilanz_p5(gold, neu)
            vor.append(b_vor)
            nach.append(b_nach)
            if rid in ids41:
                vor41.append(b_vor)
                nach41.append(b_nach)
            if bindung.get("zellen"):
                gebunden += 1
                if rid in ids41:
                    gebunden41 += 1
                gold_keys = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in gold}
                for z in bindung["zellen"]:
                    zellen += 1
                    if rid in ids41:
                        zellen41 += 1
                    wert = gold_keys.get((z["field"], z["arm"]))
                    if wert is not None and abs(wert - z["value"]) < 1e-6:
                        richtig += 1
                        if rid in ids41:
                            richtig41 += 1
        s_vor, s_nach = summe(vor), summe(nach)
        s_vor41, s_nach41 = summe(vor41), summe(nach41)
        laeufe.append(
            {
                "gruppe_modus": gruppe_modus,
                "records": len(records),
                "gebunden": gebunden,
                "zellen_gebunden": zellen,
                "zellen_richtig": richtig,
                "vorher": s_vor,
                "nachher": s_nach,
                "tp_delta": s_nach["tp"] - s_vor["tp"],
                "fp_delta": s_nach["fp"] - s_vor["fp"],
                "fn_delta": s_nach["fn"] - s_vor["fn"],
                "auswahl41": {
                    "records": len(ids41),
                    "gebunden": gebunden41,
                    "zellen_gebunden": zellen41,
                    "zellen_richtig": richtig41,
                    "vorher": s_vor41,
                    "nachher": s_nach41,
                    "tp_delta": s_nach41["tp"] - s_vor41["tp"],
                    "fp_delta": s_nach41["fp"] - s_vor41["fp"],
                    "fn_delta": s_nach41["fn"] - s_vor41["fn"],
                },
                "rest658": {
                    "records": len(records) - len(ids41),
                    "gebunden": gebunden - gebunden41,
                    "zellen_gebunden": zellen - zellen41,
                    "zellen_richtig": richtig - richtig41,
                    "vorher": {k: s_vor[k] - s_vor41[k] for k in ("tp", "fp", "fn")},
                    "nachher": {k: s_nach[k] - s_nach41[k] for k in ("tp", "fp", "fn")},
                    "tp_delta": (s_nach["tp"] - s_nach41["tp"]) - (s_vor["tp"] - s_vor41["tp"]),
                    "fp_delta": (s_nach["fp"] - s_nach41["fp"]) - (s_vor["fp"] - s_vor41["fp"]),
                    "fn_delta": (s_nach["fn"] - s_nach41["fn"]) - (s_vor["fn"] - s_vor41["fn"]),
                },
            }
        )

    ergebnis = {"stand": "2026-11-21", "records": len(records), "laeufe": laeufe}
    (HIER / "zeilenbindung_gesamt_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    zeilen = "\n".join(
        f"| {e['gruppe_modus']} | {e['records']} | {e['gebunden']} | {e['zellen_gebunden']} "
        f"({e['zellen_richtig']} richtig) | {e['vorher']['tp']} -> {e['nachher']['tp']} | "
        f"{e['vorher']['fp']} -> {e['nachher']['fp']} | {e['fp_delta']:+d} | {e['tp_delta']:+d} |"
        for e in laeufe
    )
    zeilen41 = "\n".join(
        f"| {e['gruppe_modus']} | {e['auswahl41']['gebunden']} | {e['auswahl41']['zellen_gebunden']} "
        f"({e['auswahl41']['zellen_richtig']} richtig) | {e['auswahl41']['fp_delta']:+d} | "
        f"{e['auswahl41']['tp_delta']:+d} |"
        for e in laeufe
    )
    zeilen_rest = "\n".join(
        f"| {e['gruppe_modus']} | {e['rest658']['gebunden']} | {e['rest658']['zellen_gebunden']} "
        f"({e['rest658']['zellen_richtig']} richtig) | {e['rest658']['fp_delta']:+d} | "
        f"{e['rest658']['tp_delta']:+d} |"
        for e in laeufe
    )
    bericht = f"""# Zeilenbindung ueber alle {len(records)} Records (21.11.2026)

Dieselbe Regel wie in der 41er-Auswahl, offline und ohne Netzaufruf, additiver
Modus. `ersetzen` bleibt aussen vor, weil es in der Auswahl zahlengleich war.

## Gesamtbild

| Gruppenmodus | Records | gebundene Records | gebundene Zellen (richtig) | TP | FP | FP-Delta | TP-Delta |
|---|---:|---:|---:|---|---|---:|---:|
{zeilen}

## Aufteilung

| Gruppenmodus | gebunden (41) | Zellen (richtig) | FP-Delta (41) | TP-Delta (41) |
|---|---:|---:|---:|---:|
{zeilen41}

| Gruppenmodus | gebunden (658) | Zellen (richtig) | FP-Delta (658) | TP-Delta (658) |
|---|---:|---:|---:|---:|
{zeilen_rest}

## Antwort

Die Zusatz-FP der 41 verschwinden nicht. Bei `erstes` sind es 11 der 76
Zusatz-FP; die uebrigen 65 stammen aus 19 weiteren Records, die dafuer 21 TP
liefern. `streng` liegt bei 2 TP und 10 FP. Die Regel skaliert also nicht:
22 von 699 Records werden gebunden, 34 von 126 Zellen treffen das Gold
(27 Prozent).

## Lesart

Die Zusatz-FP der 41 schweren Records verschwinden nicht, sie sind nur ein
Teil der Gesamtbilanz. Entscheidend ist das Verhaeltnis von neuen TP zu neuen
FP: gebundene Zellen, die nicht im Gold stehen, kosten eine FP, gleichgueltig
in welchem Record sie liegen. Die Tabelle zeigt dieses Verhaeltnis getrennt
fuer die Auswahl und fuer die uebrigen Records.
"""
    (HIER / "zeilenbindung_gesamt_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")
    for e in laeufe:
        print(
            f"{e['gruppe_modus']:7s} records {e['records']} | gebunden {e['gebunden']} | "
            f"Zellen {e['zellen_gebunden']} ({e['zellen_richtig']} richtig) | "
            f"TP {e['vorher']['tp']}->{e['nachher']['tp']} FP {e['vorher']['fp']}->{e['nachher']['fp']} "
            f"(Delta {e['fp_delta']:+d}) | FN {e['vorher']['fn']}->{e['nachher']['fn']}"
        )
        print(
            f"        41: gebunden {e['auswahl41']['gebunden']}, FP {e['auswahl41']['fp_delta']:+d}, "
            f"TP {e['auswahl41']['tp_delta']:+d} | 658: gebunden {e['rest658']['gebunden']}, "
            f"FP {e['rest658']['fp_delta']:+d}, TP {e['rest658']['tp_delta']:+d}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
