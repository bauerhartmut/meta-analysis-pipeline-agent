#!/usr/bin/env python3
"""Ordnet die falschen Groessenzellen der Lueckenfuellung nach Ursache.

Offline, ohne Netzaufruf. Grundlage ist derselbe Lauf wie
`umschreiben_20261121.py`: alle 699 Records, Goldfelder ohne Ereignisse, neue
Tabellenwahl an, Lueckenfuellung ohne Mittel. Fuer jede Groessenzelle, die die
Regel neu liefert, wird die benutzte Zeile mitgedruckt. Die Ursache ist eine
manuelle Zuordnung anhand dieser Zeile und des Goldenwerts; sie steht als
Tabelle `URSACHE` im Skript, damit sie nachpruefbar bleibt.

Kategorien:

* `falsche_zeile` - die Zahl steht in einer anderen Zeile als der Goldwert
  (Bildunterschrift, Baseline-Kopfzeile statt Outcome-Zeile),
* `abweichende_definition` - die Zeile ist richtig, aber sie zaehlt eine andere
  Population (randomisiert statt ausgewertet, Charakteristika statt Outcome),
* `rechenfehler` - die gelesene Zahl passt nicht zur gedruckten Arithmetik.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/groessen_ursachen_20261121.py
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
FELDART = {"group_size": "groesse", "mean": "mittel",
           "standard_deviation": "streuung", "events": "ereignis"}

# Zuordnung je Zelle: (Ursache, Begruendung). Grundlage sind die gedruckten
# Zeilen der jeweiligen Tabelle, siehe `beleg` im Ergebnis.
URSACHE: dict[tuple[str, str, str], tuple[str, str]] = {
    ("yun2024:159", "intervention_group_size", "intervention"): (
        "falsche_zeile",
        "Die 24 stammt aus der Bildunterschrift 'at baseline, 12 and 24 months'; "
        "Gold 592 steht in der Armzeile 'Intervention (n=592)' der 12-Monats-Spalte."),
    ("yun2024:251", "intervention_group_size", "intervention"): (
        "abweichende_definition",
        "Kopfzeile nennt randomisiert n=406, die Outcome-Zeile rechnet mit 42/402; "
        "Gold nimmt die 402."),
    ("yun2024:251", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Kopfzeile nennt randomisiert n=393, die Outcome-Zeile rechnet mit 41/388; "
        "Gold nimmt die 388."),
    ("yun2024:252", "intervention_group_size", "intervention"): (
        "abweichende_definition",
        "Charakteristika-Tabelle nennt randomisiert n=398, Gold 402 ist der Nenner "
        "der Outcome-Zeilen."),
    ("yun2024:252", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Charakteristika-Tabelle nennt randomisiert n=389, Gold 388 ist der Nenner "
        "der Outcome-Zeilen."),
    ("yun2024:356", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Baseline-Kopfzeile nennt randomisiert n=15, Gold 13 ist die Haelfte der 26 "
        "Kinder, die die Studie abgeschlossen haben."),
    ("yun2024:420", "intervention_group_size", "intervention"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=44; Gold 18 steht als n=18 in der "
        "Outcome-Zeile 'T2w sagittal' der Bildqualitaetstabelle."),
    ("yun2024:420", "comparator_group_size", "comparator"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=49; Gold 21 steht als n=21 in "
        "derselben Outcome-Zeile."),
    ("yun2024:421", "intervention_group_size", "intervention"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=44; Gold 30 steht als n=30 in der "
        "Outcome-Zeile fuer die Brustwirbelsaeule."),
    ("yun2024:421", "comparator_group_size", "comparator"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=49; Gold 34 steht als n=34 in "
        "derselben Outcome-Zeile."),
    ("yun2024:451", "intervention_group_size", "intervention"): (
        "abweichende_definition",
        "Die Tabellenunterschrift nennt I; n=104, Gold 99 ist die Auswertungsgroesse "
        "der MVPA-Zeile; sie steht nicht als n im Dokument."),
    ("yun2024:451", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Die Tabellenunterschrift nennt C; n=114, Gold 108 ist die Auswertungsgroesse "
        "der MVPA-Zeile; sie steht nicht als n im Dokument."),
}


def art(feld: str) -> str:
    for ende, name in FELDART.items():
        if feld.endswith(ende):
            return name
    return "sonstig"


def kopfzeile(zeile: str) -> bool:
    """Bildunterschrift, Ueberschrift oder Trennlinie statt Datenzeile."""
    text = zeile.strip()
    return (text.startswith("#") or text.startswith(":::") or not text
            or set(text) <= set("- "))


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5)}
    befund: list[dict[str, Any]] = []
    for rid, zeile in p5.items():
        if rid not in records:
            continue
        record = records[rid]
        felder = [(str(z.get("field") or ""), v.arm_von(z), v.zahl(z.get("value")))
                  for z in (record.get("gold") or {}).get("cells") or []]
        felder = [f for f in felder if art(f[0]) == "groesse" and f[2] is not None]
        if not felder:
            continue
        text = (m.REPO / record["document"]["path"]).read_text(encoding="utf-8",
                                                               errors="replace")
        zeilen = text.splitlines()
        vorher = {(str(c.get("field") or ""), v.arm_von(c)) for c in v.zellen(zeile)}
        for feld, arm, gold in felder:
            if (feld, arm) in vorher:
                continue
            neu = m.lies(record, text, feld, arm, m.alias_mod.ALIAS, True, FORMATE)
            if neu is None:
                continue
            i = neu.get("zeile")
            zeilentext = zeilen[i] if isinstance(i, int) and i < len(zeilen) else ""
            richtig = abs(neu["value"] - gold) < 1e-6
            ursache, grund = URSACHE.get((rid, feld, arm), ("offen", ""))
            befund.append({
                "record_id": rid, "feld": feld, "arm": arm, "wert": neu["value"],
                "gold": gold, "richtig": richtig, "zeile": i,
                "zeilentext": zeilentext.strip()[:160],
                "kopfzeile": kopfzeile(zeilentext),
                "gold_im_dokument": str(int(float(gold))) in text if float(gold).is_integer()
                else str(gold) in text,
                "ursache": None if richtig else ursache,
                "begruendung": None if richtig else grund,
            })

    falsch = [e for e in befund if not e["richtig"]]
    zaehler: dict[str, int] = {}
    for e in falsch:
        zaehler[e["ursache"]] = zaehler.get(e["ursache"], 0) + 1
    offen = zaehler.pop("offen", 0)
    ergebnis = {"stand": "2026-11-21", "records": len(records),
                "groessenzellen": len(befund),
                "richtig": sum(1 for e in befund if e["richtig"]),
                "falsch": len(falsch), "ursachen": zaehler, "ohne_zuordnung": offen,
                "zellen": befund}
    (HIER / "groessen_ursachen_20261121.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=True), encoding="utf-8")

    md = ["# Ursachen der falschen Groessenzellen (21.11.2026)", "",
          "Offline, ohne Netzaufruf. `groessen_ursachen_20261121.py`. Grundlage ist",
          "die Lueckenfuellung ohne Mittel ueber alle "
          f"{len(records)} Records: {len(befund)} neue Groessenzellen, davon "
          f"{ergebnis['richtig']} richtig und {len(falsch)} falsch. Die Ursache ist",
          "je Zelle an der benutzten Zeile und am Goldwert zugeordnet; die",
          "Begruendung steht in der Tabelle.", "",
          "## Zahlen je Ursache", "", "| Ursache | Zellen |", "|---|---:|"]
    for name in ("falsche_zeile", "abweichende_definition", "rechenfehler"):
        md.append(f"| {name} | {zaehler.get(name, 0)} |")
    if offen:
        md.append(f"| offen | {offen} |")
    md += ["", "## Zellen", "",
           "| Record | Feld | Arm | Wert | Gold | Zeile | Kopfzeile | Gold im Dokument "
           "| Ursache |", "|---|---|---|---:|---:|---:|---|---|---|"]
    for e in falsch:
        md.append(f"| `{e['record_id']}` | {e['feld'].replace('_group_size', '')} | "
                  f"{e['arm']} | {e['wert']} | {e['gold']} | {e['zeile']} | "
                  f"{'ja' if e['kopfzeile'] else 'nein'} | "
                  f"{'ja' if e['gold_im_dokument'] else 'nein'} | {e['ursache']} |")
    md += ["", "## Begruendung je Zelle", ""]
    for e in falsch:
        md += [f"- `{e['record_id']}` {e['feld']} ({e['arm']}, Regel {e['wert']} gegen "
               f"Gold {e['gold']}): {e['begruendung']}",
               f"  Zeile {e['zeile']}: `{e['zeilentext']}`"]
    md += ["", "## Richtige Zellen", "",
           "| Record | Feld | Arm | Wert | Gold |", "|---|---|---|---:|---:|"]
    for e in befund:
        if e["richtig"]:
            md.append(f"| `{e['record_id']}` | {e['feld'].replace('_group_size', '')} | "
                      f"{e['arm']} | {e['wert']} | {e['gold']} |")
    (HIER / "groessen_ursachen_20261121.md").write_text(
        "\n".join(md) + "\n", encoding="ascii", errors="replace")

    print(f"Groessenzellen {len(befund)} | richtig {ergebnis['richtig']} | "
          f"falsch {len(falsch)}")
    print("Ursachen:", zaehler or "keine", "| ohne Zuordnung:", offen)
    for e in falsch:
        print(f"  {e['record_id']:14s} {e['arm']:11s} {e['wert']:>8} gegen "
              f"{e['gold']:>7} Zeile {e['zeile']:>4} Kopfzeile={e['kopfzeile']} "
              f"gold_im_dokument={e['gold_im_dokument']} {e['ursache']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
