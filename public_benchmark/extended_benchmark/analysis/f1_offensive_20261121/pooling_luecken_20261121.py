"""Warum sind 76 der 103 P5-Records fuer ein Pooling unvollstaendig?

Offline, ohne Netzaufruf. Drei Fragen:

1. Welches Feld fehlt je Record (feldweise Zaehlung ueber alle 103)?
2. Welche Records koennten allein mit den vorhandenen Regel bausteinen
   (Groessenzeile, Mittel) vollstaendig werden? Voraussetzung: es fehlt kein
   Feld, das die Regeln nicht lesen (Standardabweichung, Ereignisse).
3. Liefert die Regel dort auch den richtigen Wert, gemessen gegen Gold?

Grundlage sind die P5-Vorhersagen, Gold aus den Records und dieselben Regeln wie
in `zielzeile_alle_20261121.py` - kein neuer Regelcode, nur die vorhandenen
Funktionen mit Zellauftraegen aus Gold.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(ANALYSE / "f1_offensive_20261121"))

import vergleiche_20261120 as v  # noqa: E402
import zielzeile_alle_20261121 as m  # noqa: E402

FORMATE = ("mittel_sd", "plus_minus")
CONT = ("intervention_mean", "comparator_mean", "intervention_standard_deviation",
        "comparator_standard_deviation", "intervention_group_size", "comparator_group_size")
BIN = ("intervention_events", "comparator_events", "intervention_group_size",
       "comparator_group_size")
LESBAR = ("intervention_group_size", "comparator_group_size",
          "intervention_mean", "comparator_mean")
ARM = {"intervention_group_size": "intervention", "comparator_group_size": "comparator",
       "intervention_mean": "intervention", "comparator_mean": "comparator"}


def p5_zellen(zeile: dict[str, Any]) -> dict[str, float]:
    aus: dict[str, float] = {}
    for zelle in ((zeile.get("predicted") or {}).get("cells") or []):
        if zelle.get("value") is None:
            continue
        try:
            aus[str(zelle.get("field"))] = float(zelle.get("value"))
        except (TypeError, ValueError):
            continue
    return aus


def gold_zellen(record: dict[str, Any]) -> dict[str, float]:
    aus: dict[str, float] = {}
    for zelle in (record.get("gold") or {}).get("cells") or []:
        if zelle.get("value") is None:
            continue
        try:
            aus[str(zelle.get("field"))] = float(zelle.get("value"))
        except (TypeError, ValueError):
            continue
    return aus


def main() -> int:
    p5 = v.lade(v.P5)
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte: dict[str, str] = {}
    for rid in {z["record_id"] for z in p5}:
        pfad = Path(".") / recs[rid]["document"]["path"]
        texte[rid] = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""

    zeilen: list[dict[str, Any]] = []
    feld_luecke: Counter[str] = Counter()
    feld_luecke_nur: Counter[str] = Counter()
    for z in p5:
        rid = z["record_id"]
        typ = str((recs[rid].get("context") or {}).get("outcome_type") or "")
        soll = CONT if typ == "continuous" else BIN
        ist = p5_zellen(z)
        fehlt = [f for f in soll if f not in ist]
        for f in fehlt:
            feld_luecke[f] += 1
        if len(fehlt) == 1:
            feld_luecke_nur[fehlt[0]] += 1
        zeilen.append({"record_id": rid, "typ": typ, "fehlt": fehlt,
                       "nur_lesbar": bool(fehlt) and all(f in LESBAR for f in fehlt)})

    voll = [z for z in zeilen if not z["fehlt"]]
    luecken = [z for z in zeilen if z["fehlt"]]
    kandidaten = [z for z in luecken if z["nur_lesbar"]]

    # Kategorien der Luecke: fehlt nur SD, nur Ereignisse, oder mehr?
    kategorien: Counter[str] = Counter()
    for z in luecken:
        fehlt = set(z["fehlt"])
        if z["typ"] == "continuous":
            sd = {"intervention_standard_deviation", "comparator_standard_deviation"} & fehlt
            rest = fehlt - {"intervention_standard_deviation", "comparator_standard_deviation"}
            if sd and not rest:
                kategorien["nur Standardabweichung fehlt"] += 1
            elif sd:
                kategorien["Standardabweichung und weitere Felder"] += 1
            else:
                kategorien["nur Groesse/Mittel (Regeln vorhanden)"] += 1
        else:
            ereignisse = {"intervention_events", "comparator_events"} & fehlt
            rest = fehlt - {"intervention_events", "comparator_events"}
            if ereignisse and rest:
                kategorien["Ereignisse und weitere Felder"] += 1
            elif ereignisse:
                kategorien["nur Ereignisse fehlen"] += 1
            else:
                kategorien["nur Groesse (Regeln vorhanden)"] += 1

    # Sichtung der SD-Luecke: steht neben dem Goldmittel ein zweiter Wert im
    # Format, das der Mittel-Leser schon kennt ("Mittel +/- SD" oder
    # "Mittel (SD)")? Reine Textzaehlung, keine neue Regel.
    sd_ids = [z["record_id"] for z in luecken if z["typ"] == "continuous" and z["fehlt"]
             and set(z["fehlt"]) <= {"intervention_standard_deviation",
                                      "comparator_standard_deviation"}]
    sd_streng = sd_locker = 0
    je_sd: dict[str, int] = {}
    for rid in sd_ids:
        text = texte[rid]
        gold = gold_zellen(recs[rid])
        arme_streng = arme_locker = 0
        for feld in ("intervention_mean", "comparator_mean"):
            wert = gold.get(feld)
            if wert is None:
                continue
            m1, m2 = re.escape(f"{wert:g}"), re.escape(f"{wert:.1f}")
            if re.search(rf"(?:{m1}|{m2})\s*[\u00b1+\-]\s*\d", text) or \
                    re.search(rf"(?:{m1}|{m2})\s*\(\s*\d", text):
                arme_streng += 1
                arme_locker += 1
            elif re.search(rf"(?:{m1}|{m2})", text):
                arme_locker += 1
        je_sd[rid] = arme_streng
        sd_streng += arme_streng == 2
        sd_locker += arme_locker == 2

    # Warum liefert die Regel bei einem Kandidaten nichts?
    gruende: dict[str, str] = {}
    for z in kandidaten:
        rid = z["record_id"]
        rec = recs[rid]
        text = texte[rid]
        oc = str((rec.get("context") or {}).get("outcome") or "")
        zi = text.splitlines()
        ziel = m.zeitverlauf_ziel(zi, oc, m.alias_mod.ALIAS, True)
        if ziel < 0:
            ziel = m.alias_mod.ziel_zeile_alias(zi, oc, m.alias_mod.ALIAS, True)
        if ziel < 0:
            gruende[rid] = "Zielzeile nicht gefunden"
        elif set(z["fehlt"]) <= {"intervention_group_size", "comparator_group_size"}:
            werte = m.groesse_in_tabelle(zi, ziel, rec.get("context") or {})
            gruende[rid] = ("keine n-Zeile in der Tabelle der Zielzeile" if not werte
                            else "Gate verwirft (Label und Position uneinig)")
        else:
            gruende[rid] = "Mittel nicht aus der Zeile lesbar"

    # Regelauftraege aus Gold fuer die fehlenden lesbaren Felder.
    faelle = []
    for z in kandidaten:
        gold = gold_zellen(recs[z["record_id"]])
        for feld in z["fehlt"]:
            if feld in gold:
                faelle.append({"record_id": z["record_id"], "feld": feld,
                               "arm": ARM[feld], "wert": gold[feld]})
    ergebnis = {"gate": {}, "ohne_gate": {}}
    for name, gate in (("gate", True), ("ohne_gate", False)):
        m.GATE = gate
        ergebnis[name] = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True,
                                 mean_formate=FORMATE)
    m.GATE = True

    # Welche Records werden dadurch vollstaendig, und stimmt der Wert?
    geschlossen: dict[str, list[dict[str, Any]]] = {"gate": [], "ohne_gate": []}
    for name in ("gate", "ohne_gate"):
        geliefert: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for e in ergebnis[name]["detail"]:
            geliefert[e["record_id"]][e["feld"]] = e
        for z in kandidaten:
            fehlt = z["fehlt"]
            if all(f in geliefert.get(z["record_id"], {}) for f in fehlt):
                eintraege = [geliefert[z["record_id"]][f] for f in fehlt]
                geschlossen[name].append({
                    "record_id": z["record_id"], "felder": fehlt,
                    "richtig": [e["richtig"] for e in eintraege]})
    # Vollstaendig, aber fuer das Pooling trotzdem nicht brauchbar?
    nicht_poolbar: dict[str, str] = {}
    for z in voll:
        ist = p5_zellen(next(x for x in p5 if x["record_id"] == z["record_id"]))
        if z["typ"] == "continuous":
            n1, n2 = ist["intervention_group_size"], ist["comparator_group_size"]
            s1 = ist["intervention_standard_deviation"]
            s2 = ist["comparator_standard_deviation"]
            if n1 < 2 or n2 < 2:
                nicht_poolbar[z["record_id"]] = "Gruppengroesse unter 2"
            elif s1 <= 0 or s2 <= 0:
                nicht_poolbar[z["record_id"]] = "Standardabweichung null"
        else:
            n1, n2 = ist["intervention_group_size"], ist["comparator_group_size"]
            a, c = ist["intervention_events"], ist["comparator_events"]
            if n1 < 1 or n2 < 1:
                nicht_poolbar[z["record_id"]] = "Gruppengroesse null"
            elif a > n1 or c > n2:
                nicht_poolbar[z["record_id"]] = "Ereignisse groesser als Gruppe"

    ohne_gold = [z["record_id"] for z in kandidaten
                 if any(f not in gold_zellen(recs[z["record_id"]]) for f in z["fehlt"])]

    daten = {
        "p5_records": len(p5), "vollstaendig": len(voll), "luecken": len(luecken),
        "feld_luecke": dict(feld_luecke), "feld_luecke_allein": dict(feld_luecke_nur),
        "kandidaten": len(kandidaten), "kandidaten_ids": [z["record_id"] for z in kandidaten],
        "ohne_goldwert": ohne_gold,
        "auftraege": len(faelle),
        "geliefert": {n: ergebnis[n]["geliefert"] for n in ergebnis},
        "tp": {n: ergebnis[n]["tp"] for n in ergebnis},
        "fp": {n: ergebnis[n]["fp"] for n in ergebnis},
        "geschlossen": {n: len(geschlossen[n]) for n in geschlossen},
        "geschlossen_richtig": {
            n: sum(1 for g in geschlossen[n] if all(g["richtig"])) for n in geschlossen},
        "geschlossen_detail": geschlossen,
        "kategorien": dict(kategorien), "gruende": gruende,
        "sd_sichtung": {"records": len(sd_ids), "beide_arme_format": sd_streng,
                        "beide_arme_vorhanden": sd_locker, "je_record": je_sd},
        "nicht_poolbar": nicht_poolbar,
        "je_record": zeilen,
    }
    (HIER / "pooling_luecken_20261121.json").write_text(
        json.dumps(daten, indent=2, ensure_ascii=True), encoding="utf-8")

    md = ["# Warum 76 P5-Records fuer das Pooling unvollstaendig sind", "",
          "Offline, ohne Netzaufruf. `pooling_luecken_20261121.py`. Sollfelder je",
          "Outcome-Typ: bei kontinuierlich sechs Zellen (Mittel, SD, Groesse je Arm),",
          "bei binaer vier (Ereignisse, Groesse je Arm).", "",
          f"## Feldweise Luecken (103 Records, {len(voll)} vollstaendig, {len(luecken)} mit Luecke)", "",
          "| Feld | fehlt in Records | davon einzige Luecke |", "|---|---:|---:|"]
    for feld in CONT + ("intervention_events", "comparator_events"):
        if feld in feld_luecke:
            md.append(f"| `{feld}` | {feld_luecke[feld]} | {feld_luecke_nur.get(feld, 0)} |")
    md += ["", f"## Vollstaendig, aber nicht poolbar ({len(nicht_poolbar)})", "",
           "| Record | Grund |", "|---|---|"]
    for rid, grund in sorted(nicht_poolbar.items()):
        md.append(f"| `{rid}` | {grund} |")
    md += ["", f"## Kategorien der {len(luecken)} Luecken", "",
           "| Kategorie | Records |", "|---|---:|"]
    for name, anzahl in sorted(kategorien.items(), key=lambda x: -x[1]):
        md.append(f"| {name} | {anzahl} |")
    md += ["", f"## Sichtung der SD-Luecke ({len(sd_ids)} Records mit ausschliesslich fehlender SD)", "",
           "Reine Textzaehlung, keine Regel: Steht neben beiden Goldmitteln ein",
           "zweiter Wert im Format `Mittel +/- SD` oder `Mittel (SD)`?", "",
           f"- beide Arme im bekannten Format: {sd_streng}",
           f"- beide Arme irgendwo im Dokument: {sd_locker}",
           "", "Die Zaehlung sagt nur, ob der Wert im Text steht - nicht, ob die",
           "Zielzeile gefunden wird (bei den Kandidaten oben war sie es nicht).", "",
           f"## Records, die die vorhandenen Regeln schliessen koennten ({len(kandidaten)})", "",
           "Bedingung: kein fehlendes Feld ausser Groesse und Mittel, also keine",
           "fehlende SD und keine fehlenden Ereignisse. Regelauftraege aus Gold:",
           f"{len(faelle)} Zellen.", "",
           "| Stand | geliefert | richtig | falsch | Records geschlossen | davon ganz richtig |",
           "|---|---:|---:|---:|---:|---:|"]
    for name, label in (("gate", "mit Gate"), ("ohne_gate", "ohne Gate")):
        md.append(f"| {label} | {ergebnis[name]['geliefert']} | {ergebnis[name]['tp']} | "
                  f"{ergebnis[name]['fp']} | {daten['geschlossen'][name]} | "
                  f"{daten['geschlossen_richtig'][name]} |")
    md += ["", "| Record | fehlende Felder | Werte richtig |", "|---|---|---|"]
    for g in geschlossen["gate"]:
        md.append(f"| `{g['record_id']}` | {', '.join(g['felder'])} | "
                  f"{'ja' if all(g['richtig']) else 'nein'} |")
    md += ["", "| Record | Grund, warum nichts geliefert wird |", "|---|---|"]
    for rid in [z["record_id"] for z in kandidaten]:
        md.append(f"| `{rid}` | {gruende.get(rid, '')} |")
    if ohne_gold:
        md += ["", f"Ohne Goldwert im Dokument (also nicht pruefbar): {', '.join(ohne_gold)}"]
    md += ["", "## Grenzen", "",
           "- Die Kandidatenpruefung setzt voraus, dass die Regeln auf jedes Dokument",
           "  anwendbar sind; gemessen wird nur, ob sie fuer das fehlende Feld einen",
           "  Wert liefern. Ein Treffer sagt nichts ueber Records, denen SD oder",
           "  Ereignisse fehlen - dort helfen die vorhandenen Regeln nicht.",
           "- Gold dient als Auftrag und als Pruefmass; ein Record ohne Goldwert ist",
           "  als Kandidat gezaehlt, aber nicht bewertbar."]
    (HIER / "pooling_luecken_20261121.md").write_text("\n".join(md) + "\n",
                                                      encoding="ascii", errors="replace")
    print(f"Records {len(p5)} | vollstaendig {len(voll)} | Luecken {len(luecken)} | "
          f"Kandidaten {len(kandidaten)} | Auftraege {len(faelle)}")
    print("Feldluecken:", dict(feld_luecke))
    print("nur diese Luecke:", dict(feld_luecke_nur))
    print("Kategorien:", dict(kategorien))
    print("Gruende:", gruende)
    print(f"SD-Sichtung: {len(sd_ids)} Records, beide Arme im Format {sd_streng}, "
          f"irgendwo vorhanden {sd_locker}")
    for name in ("gate", "ohne_gate"):
        print(f"{name}: geliefert {ergebnis[name]['geliefert']} richtig "
              f"{ergebnis[name]['tp']} falsch {ergebnis[name]['fp']} | "
              f"geschlossen {daten['geschlossen'][name]} "
              f"(ganz richtig {daten['geschlossen_richtig'][name]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
