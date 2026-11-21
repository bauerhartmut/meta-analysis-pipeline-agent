#!/usr/bin/env python3
"""Warum liest PMC3877023 (yun2024:420/:421) die Groesse aus der falschen Tabelle?

Offline, ohne Netzaufruf. Der Report zeigt die Kette: Outcome-Text, Zielzeile der
drei Suchfunktionen, Tabellengrenzen der Zielzeile, die `n =`-Zeile der
Outcome-Tabelle (wird sie als Groessenzeile erkannt und was liest sie?) und die
Kopfzeile der Baseline-Tabelle, aus der die Regel tatsaechlich liest.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/pmc3877023_20261121.py
"""
from __future__ import annotations

import json
import re
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
    befund: list[dict[str, Any]] = []
    for rid in ("yun2024:420", "yun2024:421"):
        record = records[rid]
        text = (m.REPO / record["document"]["path"]).read_text(encoding="utf-8",
                                                               errors="replace")
        zeilen = text.splitlines()
        context = record.get("context") or {}
        outcome = str(context.get("outcome") or "")
        z_verlauf = m.zeitverlauf_ziel(zeilen, outcome, m.alias_mod.ALIAS, True)
        z_zeitpunkt = m.ziel_zeile_zeitpunkt(zeilen, outcome, m.alias_mod.ALIAS, True)
        z_alias = m.alias_mod.ziel_zeile_alias(zeilen, outcome, m.alias_mod.ALIAS, True)
        ziel = z_zeitpunkt if z_verlauf < 0 and m.ZEITPUNKT_TABELLE else z_verlauf
        start, ende = m.tabellengrenzen(zeilen, ziel)
        # `n =`-Zeilen im Dokument mit ihrer Auswertung.
        n_zeilen: list[dict[str, Any]] = []
        for j, z in enumerate(zeilen):
            if not re.search(r"[nN]\s*[*_]*\s*=", z):
                continue
            if not (m.g.ist_groessenzeile(z) and m.g.STRENGE.search(z)):
                continue
            werte = m.g.aus_groessenzeile(zeilen, j, context)
            n_zeilen.append({
                "zeile": j + 1,
                "text": z.strip()[:120],
                "werte": None if not werte else {k: x["value"] for k, x in werte.items()},
                "in_zieltabelle": start <= j <= ende,
            })
        gelesen = m.lies(record, text, "intervention_group_size", "intervention",
                         m.alias_mod.ALIAS, True, FORMATE)
        befund.append({
            "record_id": rid, "outcome": outcome,
            "ziel_verlauf": z_verlauf, "ziel_zeitpunkt": z_zeitpunkt,
            "ziel_alias": z_alias, "ziel_zeile": ziel + 1,
            "ziel_text": zeilen[ziel].strip()[:120] if ziel >= 0 else "",
            "ziel_tabelle": [start + 1, ende + 1],
            "n_zeilen": n_zeilen,
            "gelesen": None if gelesen is None else {
                "wert": gelesen["value"], "quelle": gelesen.get("quelle"),
                "zeile": gelesen.get("zeile") + 1 if isinstance(gelesen.get("zeile"), int)
                else None},
        })

    (HIER / "pmc3877023_20261121.json").write_text(
        json.dumps({"stand": "2026-11-21", "befund": befund}, indent=2,
                   ensure_ascii=True), encoding="utf-8")

    md = ["# PMC3877023: warum die Groesse aus der Baseline-Tabelle kommt (21.11.2026)", "",
          "Offline, ohne Netzaufruf. `pmc3877023_20261121.py`.", ""]
    for e in befund:
        md += [f"## `{e['record_id']}`", "",
               f"- Outcome: `{e['outcome']}`",
               f"- Zielzeile: `zeitverlauf_ziel` {e['ziel_verlauf']}, "
               f"`ziel_zeile_zeitpunkt` {e['ziel_zeitpunkt']}, "
               f"`ziel_zeile_alias` {e['ziel_alias']}",
               f"- genutzte Zeile {e['ziel_zeile']}: `{e['ziel_text']}`",
               f"- Tabellengrenzen: {e['ziel_tabelle'][0]} bis {e['ziel_tabelle'][1]}",
               f"- gelesene Groesse: {e['gelesen']}", "",
               "| `n =`-Zeile | Text | Werte | in Ziel-Tabelle |",
               "|---:|---|---|---|"]
        for n in e["n_zeilen"]:
            md.append(f"| {n['zeile']} | `{n['text'][:80]}` | "
                      f"{n['werte']} | {'ja' if n['in_zieltabelle'] else 'nein'} |")
        md.append("")
    md += ["## Befund", "",
           "Die Kette bis zur falschen Zahl, alles vor der Kopfband-Regel:", "",
           "1. Die Zielzeile liegt in der falschen Tabelle. Der Outcome-Text nennt "
           "die Region (`Cervicothoracic spine`) und die Kenngroesse (`contour "
           "sharpness`) getrennt; die Region steht in der Demografie-Tabelle "
           "(Zeile 29: `Cervicothoracic spine 14 (31.8) 15 (30.6)`), die Kenngroesse "
           "nur als Blockzeile ueber den Daten. Die Alias-Suche nimmt die "
           "Region-Zeile, die Ziel-Tabelle ist damit die Demografie-Tabelle, und "
           "deren Kopfzeile `Short-Bore MR (n = 44) / Open MR (n = 49)` liefert "
           "die Groesse.",
           "2. Selbst mit richtiger Zielzeile wuerde die `n =`-Zeile der "
           "Bildqualitaetstabelle (Zeile 146: `**T2w sagittal** n = 18 n = 21 "
           "n = 30 n = 34`) nichts liefern: `ist_groessenzeile` und `STRENGE` "
           "greifen, aber `aus_groessenzeile` gibt `{}` zurueck. Die Zellen sind "
           "weder armbeschriftet (kein Label) noch nackte Zahlen (`n = 18` mit "
           "schmalen Leerzeichen trifft `^[\\d,]+$` nicht), also scheitern beide "
           "Pfade des Parsers.",
           "3. Auch ein Nachbessern des Parsers reicht nicht: die Tabelle hat zwei "
           "Regionbloecke nebeneinander (`Cervicothoracic Spine` und "
           "`Thoracolumbar Spine` als Gruppenzeile 141, darunter je Short-Bore, "
           "Open und P-Wert = sechs Spalten), die `n =`-Zeile hat fuenf Segmente. "
           "Ohne Regionbewusstsein ist nicht entscheidbar, welche zwei `n` zu "
           "welchem Arm gehoeren - genau deshalb trennt Gold 420 (Brustregion, "
           "18/21) von 421 (Lendenregion, 30/34).",
           ""]
    (HIER / "pmc3877023_20261121.md").write_text("".join(
        zeile + "\n" for zeile in md), encoding="ascii", errors="replace")

    for e in befund:
        print(f"{e['record_id']} ziel={e['ziel_zeile']} "
              f"({e['ziel_verlauf']}/{e['ziel_zeitpunkt']}/{e['ziel_alias']}) "
              f"tabelle={e['ziel_tabelle']} gelesen={e['gelesen']}")
        for n in e["n_zeilen"]:
            print(f"   n-Zeile {n['zeile']} in_zieltabelle={n['in_zieltabelle']} "
                  f"werte={n['werte']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
