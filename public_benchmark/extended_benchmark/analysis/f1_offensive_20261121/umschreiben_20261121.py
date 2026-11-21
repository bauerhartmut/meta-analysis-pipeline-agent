#!/usr/bin/env python3
"""Verwirft oder ueberschreibt die Tabellenwahl bereits richtige Zellen?

Offline, ohne Netzaufruf. Ueber alle 699 Records aus `yun699.jsonl` wird jedes
Goldfeld zweimal gelesen:

* `alt` - Tabellenwahl aus, die erste Zeile mit dem hoechsten Alias-Treffer
  gewinnt (Baseline-Tabelle),
* `neu` - Tabellenwahl an (Nachher-Tabelle mit Armkuerzeln in der Unterschrift).

Je Zelle eine Klasse:

| Klasse | Bedeutung |
|---|---|
| `gleich` | alt richtig, neu richtig mit demselben Wert |
| `verworfen` | alt richtig, neu liefert nichts |
| `umgeschrieben_falsch` | alt richtig, neu liefert einen anderen, falschen Wert |
| `umgeschrieben_richtig` | alt richtig, neu richtig mit anderem Wert (Rundung) |
| `neu_richtig` | alt nichts oder falsch, neu richtig |
| `neu_falsch` | alt nichts oder falsch, neu falsch geliefert |
| `keine` | beide liefern nichts |

Ereignisfelder bleiben aussen vor: der Ereignisleser ist abgeschaltet und
liefert in beiden Staenden nichts.

Zweiter Teil: die gespeicherten P5-Vorhersagen. Gezaehlt wird, wie viele dort
bereits richtige Zellen die neue Regel ueberschreiben wuerde (anderer Wert) und
wie die TP/FP/FN-Bilanz ueber alle 699 Records mit den alten und den neuen
Zellen aussieht. Die Regel leert keine Zelle; "verworfen" heisst hier deshalb
nur: sie liefert nichts, wo die alte Regel etwas Richtiges lieferte.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/umschreiben_20261121.py
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


def art(feld: str) -> str:
    for ende, name in FELDART.items():
        if feld.endswith(ende):
            return name
    return "sonstig"


def schalter(**werte: bool) -> None:
    m.ZEITPUNKT_TABELLE = werte.get("zeitpunkt", True)
    m.TABELLE_ARMBEDINGUNG = werte.get("armbedingung", True)
    m.ARMZEILE = werte.get("armzeile", True)
    m.VORZEICHEN = werte.get("vorzeichen", True)
    m.SD_AUS_KI = werte.get("sd_ki", True)
    m.POSITIONAL = True
    m.GATE = True
    m.WOCHENSPALTE = True
    m.MESSWORT_BLOCK = True
    m.TABELLENLOKAL = True


def goldfelder(record: dict[str, Any]) -> list[tuple[str, str, float]]:
    """(Feld, Arm, Goldwert) fuer alle Goldzellen ausser Ereignissen."""
    aus: list[tuple[str, str, float]] = []
    for zelle in (record.get("gold") or {}).get("cells") or []:
        feld = str(zelle.get("field") or "")
        if not feld or feld.endswith("events"):
            continue
        wert = v.zahl(zelle.get("value"))
        if wert is None:
            continue
        aus.append((feld, v.arm_von(zelle), float(wert)))
    return aus


def klasse(alt: dict[str, Any] | None, neu: dict[str, Any] | None,
           gold: float) -> str:
    def richtig(x: dict[str, Any] | None) -> bool:
        return x is not None and abs(x["value"] - gold) < 1e-6

    if richtig(alt):
        if neu is None:
            return "verworfen"
        if richtig(neu):
            return "gleich" if abs(neu["value"] - alt["value"]) < 1e-6 else "umgeschrieben_richtig"
        return "umgeschrieben_falsch"
    if richtig(neu):
        return "neu_richtig"
    return "neu_falsch" if neu is not None else "keine"


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5)}
    grenze = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if grenze:
        records = dict(list(records.items())[:grenze])
    texte: dict[str, str] = {}

    bilanzen: dict[str, int] = {}
    je_art: dict[str, dict[str, int]] = {}
    beispiele: dict[str, list[dict[str, Any]]] = {}
    zellen_neu: dict[str, list[dict[str, Any]]] = {}
    zellen_alt: dict[str, list[dict[str, Any]]] = {}
    abgeleitet: list[dict[str, Any]] = []

    for rid, record in records.items():
        felder = goldfelder(record)
        if not felder:
            continue
        text = texte.get(rid)
        if text is None:
            text = (m.REPO / record["document"]["path"]).read_text(encoding="utf-8",
                                                                   errors="replace")
            texte[rid] = text
        schalter(zeitpunkt=False, armzeile=False, vorzeichen=False, sd_ki=False)
        alt = {f: m.lies(record, text, f, a, m.alias_mod.ALIAS, True, FORMATE)
               for f, a, _ in felder}
        schalter()
        neu = {f: m.lies(record, text, f, a, m.alias_mod.ALIAS, True, FORMATE)
               for f, a, _ in felder}
        for feld, arm, gold in felder:
            k = klasse(alt[feld], neu[feld], gold)
            if k == "neu_falsch":
                # Unterscheiden: die neue Regel liefert neu (alt nichts) oder beide falsch.
                k = "neu_falsch_ohne_alt" if alt[feld] is None else "neu_falsch_mit_alt"
            bilanzen[k] = bilanzen.get(k, 0) + 1
            eimer = je_art.setdefault(art(feld), {})
            eimer[k] = eimer.get(k, 0) + 1
            if k in ("verworfen", "umgeschrieben_falsch", "umgeschrieben_richtig",
                     "neu_richtig", "neu_falsch") and len(beispiele.setdefault(k, [])) < 40:
                beispiele[k].append({
                    "record_id": rid, "feld": feld, "arm": arm, "gold": gold,
                    "alt": None if alt[feld] is None else alt[feld]["value"],
                    "alt_zeile": None if alt[feld] is None else alt[feld].get("zeile"),
                    "neu": None if neu[feld] is None else neu[feld]["value"],
                    "neu_zeile": None if neu[feld] is None else neu[feld].get("zeile"),
                    "abgeleitet": bool((neu[feld] or {}).get("abgeleitet"))})
            if (neu[feld] or {}).get("abgeleitet"):
                abgeleitet.append({"record_id": rid, "feld": feld, "arm": arm,
                                   "wert": neu[feld]["value"], "gold": gold,
                                   "richtig": abs(neu[feld]["value"] - gold) < 1e-6})
            if neu[feld] is not None:
                zellen_neu.setdefault(rid, []).append(
                    {"field": feld, "group": arm, "value": neu[feld]["value"],
                     "abgeleitet": bool(neu[feld].get("abgeleitet"))})
            if alt[feld] is not None:
                zellen_alt.setdefault(rid, []).append(
                    {"field": feld, "group": arm, "value": alt[feld]["value"]})

    # Zweiter Teil: P5-Vorhersagen.
    ueberschrieben: list[dict[str, Any]] = []
    bestaetigt = 0
    leere = 0
    ursache: dict[str, int] = {}
    alt_lookup = {(rid, c["field"], c["group"]): c["value"]
                  for rid, liste in zellen_alt.items() for c in liste}
    for rid, zeile in p5.items():
        if rid not in records:
            continue
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (records[rid].get("gold") or {}).get("cells") or []}
        for zelle in v.zellen(zeile):
            schluessel = (str(zelle.get("field") or ""), v.arm_von(zelle))
            soll = gold.get(schluessel)
            wert = v.zahl(zelle.get("value"))
            if soll is None or wert is None or abs(wert - soll) >= 1e-6:
                continue
            neu_zelle = next((x for x in zellen_neu.get(rid, [])
                              if (x["field"], x["group"]) == schluessel), None)
            if neu_zelle is None:
                leere += 1
                continue
            if abs(neu_zelle["value"] - wert) < 1e-6:
                bestaetigt += 1
            else:
                vor_alt = alt_lookup.get((rid, schluessel[0], schluessel[1]))
                if vor_alt is None:
                    grund = "ohne_alt"
                elif abs(vor_alt - soll) < 1e-6:
                    grund = "alt_richtig"
                else:
                    grund = "alt_falsch"
                ursache[grund] = ursache.get(grund, 0) + 1
                ueberschrieben.append({"record_id": rid, "feld": schluessel[0],
                                       "arm": schluessel[1], "vorhersage": wert,
                                       "gold": soll, "regel_neu": neu_zelle["value"],
                                       "abgeleitet": neu_zelle["abgeleitet"],
                                       "regel_alt": vor_alt, "ursache": grund})

    def einsatz(zellen: dict[str, list[dict[str, Any]]]) -> dict[str, float]:
        summe: dict[str, float] = {"tp": 0, "fp": 0, "fn": 0}
        for rid, record in records.items():
            b = v.bilanz_p5((record.get("gold") or {}).get("cells") or [],
                            zellen.get(rid, []))
            for k in ("tp", "fp", "fn"):
                summe[k] += b[k]
        tp, fp, fn = summe["tp"], summe["fp"], summe["fn"]
        genau = tp / (tp + fp) if tp + fp else 0.0
        treffer = tp / (tp + fn) if tp + fn else 0.0
        summe["f1"] = 2 * genau * treffer / (genau + treffer) if genau + treffer else 0.0
        return summe

    karten: dict[str, dict[str, list[dict[str, Any]]]] = {
        "p5": {}, "p5_plus_alt": {}, "p5_plus_neu": {},
        "p5_plus_alt_luecken": {}, "p5_plus_neu_luecken": {}}
    uebersprungen: dict[str, int] = {}
    for rid, zeile in p5.items():
        if rid not in records:
            continue
        basis = {(str(c.get("field") or ""), v.arm_von(c)): c for c in v.zellen(zeile)}
        karten["p5"][rid] = list(basis.values())
        for name, extra in (("p5_plus_alt", zellen_alt.get(rid, [])),
                            ("p5_plus_neu", zellen_neu.get(rid, []))):
            zusammen = {k: dict(c) for k, c in basis.items()}
            for c in extra:
                # Regelzellen ersetzen gleichnamige Vorhersagezellen, sonst anhaengen.
                zusammen[(c["field"], c["group"])] = {
                    "field": c["field"], "group": c["group"], "value": c["value"]}
            karten[name][rid] = list(zusammen.values())
            # Nur Luecken fuellen: eine vorhandene Vorhersagezelle bleibt stehen,
            # auch wenn die Regel einen anderen Wert liest.
            luecken = {k: dict(c) for k, c in basis.items()}
            for c in extra:
                schluessel = (c["field"], c["group"])
                if schluessel in basis:
                    uebersprungen[name + "_luecken"] = \
                        uebersprungen.get(name + "_luecken", 0) + 1
                    continue
                luecken[schluessel] = {"field": c["field"], "group": c["group"],
                                       "value": c["value"]}
            karten[name + "_luecken"][rid] = list(luecken.values())
    bilanz = {name: einsatz(karte) for name, karte in karten.items()}

    ergebnis = {"stand": "2026-11-21", "records": len(records), "p5_records": len(p5),
                "klassen": bilanzen,
                "je_feldart": je_art,
                "beispiele": beispiele,
                "abgeleitete_streuungen": abgeleitet,
                "p5": {"ueberschrieben": ueberschrieben, "bestaetigt": bestaetigt,
                       "regel_liefert_nichts": leere, "bilanz": bilanz,
                       "ursache": ursache, "uebersprungen": uebersprungen}}
    (HIER / "umschreiben_20261121.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=True), encoding="utf-8")

    reihenfolge = ("gleich", "verworfen", "umgeschrieben_falsch", "umgeschrieben_richtig",
                   "neu_richtig", "neu_falsch_ohne_alt", "neu_falsch_mit_alt", "keine")
    md = ["# Verwirft oder ueberschreibt die Tabellenwahl richtige Zellen? (21.11.2026)", "",
          "Offline, ohne Netzaufruf. `umschreiben_20261121.py`. Alle "
          f"{len(records)} Records aus `yun699.jsonl`, je Goldfeld einmal mit",
          "ausgeschalteter (`alt`) und einmal mit eingeschalteter (`neu`)",
          "Tabellenwahl gelesen. Ereignisfelder sind ausgenommen, weil der",
          "Ereignisleser in beiden Staenden abgeschaltet ist.", "",
          "## Klassen je Zelle", "",
          "| Klasse | Zellen |", "|---|---:|"]
    for k in reihenfolge:
        md.append(f"| {k} | {bilanzen.get(k, 0)} |")
    md += ["", "| Feldart | " + " | ".join(reihenfolge) + " |",
           "|---|" + "---:|" * len(reihenfolge)]
    for a in sorted(je_art):
        md.append(f"| {a} | " + " | ".join(str(je_art[a].get(k, 0)) for k in reihenfolge) + " |")
    md += ["", "## Beispiele", ""]
    for k in ("verworfen", "umgeschrieben_falsch", "umgeschrieben_richtig"):
        eintraege = beispiele.get(k) or []
        md += [f"### {k} ({len(eintraege)} gezeigt)", ""]
        if not eintraege:
            md += ["keine", ""]
            continue
        md += ["| Record | Feld | Arm | alt | neu | Gold |", "|---|---|---|---:|---:|---:|"]
        for e in eintraege:
            md.append(f"| `{e['record_id']}` | {e['feld']} | {e['arm']} | "
                      f"{'-' if e['alt'] is None else e['alt']} | "
                      f"{'-' if e['neu'] is None else e['neu']} | {e['gold']} |")
        md.append("")
    md += ["## Abgeleitete Streuungen", "",
           f"{len(abgeleitet)} Zellen der neuen Regel stammen aus einem 95%-KI; "
           f"davon richtig {sum(1 for e in abgeleitet if e['richtig'])}.", "",
           "| Record | Feld | Arm | Wert | Gold | richtig |", "|---|---|---|---:|---:|---|"]
    for e in abgeleitet:
        md.append(f"| `{e['record_id']}` | {e['feld']} | {e['arm']} | {e['wert']} | "
                  f"{e['gold']} | {'ja' if e['richtig'] else 'nein'} |")
    md += ["", "## P5-Vorhersagen", "",
           f"- richtige Vorhersagezellen von der neuen Regel bestaetigt: {bestaetigt}",
           f"- richtige Vorhersagezellen mit anderem Wert ueberschrieben: "
           f"{len(ueberschrieben)}",
           f"  - davon die alte Regel ohne Wert: {ursache.get('ohne_alt', 0)}",
           f"  - davon die alte Regel mit demselben falschen Wert: "
           f"{ursache.get('alt_falsch', 0)}",
           f"  - davon die alte Regel richtig, neu falsch: {ursache.get('alt_richtig', 0)}",
           f"- richtige Vorhersagezellen, zu denen die neue Regel nichts liefert: {leere}",
           "", "| Stand | TP | FP | FN | F1 | uebersprungene Regelzellen |",
           "|---|---:|---:|---:|---:|---:|"]
    for name in ("p5", "p5_plus_alt", "p5_plus_neu", "p5_plus_alt_luecken",
                 "p5_plus_neu_luecken"):
        b = bilanz[name]
        md.append(f"| {name} | {b['tp']:.0f} | {b['fp']:.0f} | {b['fn']:.0f} | "
                  f"{b['f1']:.3f} | {uebersprungen.get(name, 0)} |")
    b_p5, b_alt, b_neu = bilanz["p5"], bilanz["p5_plus_alt"], bilanz["p5_plus_neu"]
    g_alt, g_neu = bilanz["p5_plus_alt_luecken"], bilanz["p5_plus_neu_luecken"]
    md += ["", "Lesart: Ersetzen kostet TP, weil 31 richtige Vorhersagezellen durch einen",
           "falschen Regelwert ersetzt werden. `nur Luecken fuellen` laesst diese Zellen",
           f"stehen: {g_neu['tp'] - b_p5['tp']:+.0f} TP und {g_neu['fp'] - b_p5['fp']:+.0f} FP "
           f"gegenueber der unveraenderten Vorhersage (F1 {b_p5['f1']:.3f} -> "
           f"{g_neu['f1']:.3f}). Mit der alten Tabellenwahl waere es "
           f"{g_alt['tp'] - b_p5['tp']:+.0f} TP / {g_alt['fp'] - b_p5['fp']:+.0f} FP; die neue "
           f"Wahl bringt unter dieser Strategie {g_neu['tp'] - g_alt['tp']:+.0f} TP und "
           f"{g_neu['fp'] - g_alt['fp']:+.0f} FP.", ""]
    if ueberschrieben:
        md += ["", "| Record | Feld | Arm | Vorhersage | Gold | Regel neu | abgeleitet |",
               "|---|---|---|---:|---:|---:|---|"]
        for e in ueberschrieben:
            md.append(f"| `{e['record_id']}` | {e['feld']} | {e['arm']} | {e['vorhersage']} | "
                      f"{e['gold']} | {e['regel_neu']} | {'ja' if e['abgeleitet'] else 'nein'} |")
    (HIER / "umschreiben_20261121.md").write_text("\n".join(md) + "\n", encoding="ascii",
                                                  errors="replace")

    print(f"Records {len(records)} | P5 {len(p5)}")
    for k in reihenfolge:
        print(f"  {k:22s} {bilanzen.get(k, 0)}")
    print(f"abgeleitete Streuungen: {len(abgeleitet)} "
          f"(richtig {sum(1 for e in abgeleitet if e['richtig'])})")
    print(f"P5: bestaetigt {bestaetigt} | ueberschrieben {len(ueberschrieben)} | "
          f"Regel liefert nichts {leere}")
    for name in ("p5", "p5_plus_alt", "p5_plus_neu", "p5_plus_alt_luecken",
                 "p5_plus_neu_luecken"):
        b = bilanz[name]
        print(f"  {name:20s} TP {b['tp']:.0f} FP {b['fp']:.0f} FN {b['fn']:.0f} "
              f"F1 {b['f1']:.3f} uebersprungen {uebersprungen.get(name, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
