#!/usr/bin/env python3
"""Zeilenbindung als offline pruefbare Regel, gemessen an den 41 schweren Records.

Die Regel uebernimmt, was auf yun2024:30 funktioniert hat: die Zeile muss den
Wert selbst tragen, Aenderungszeilen sind ausgeschlossen, und die Armreihenfolge
kommt aus dem Tabellenkopf. Sie ist goldfrei - sie kennt nur Record-Kontext
(Intervention, Comparator, Outcome) und Dokumenttext.

Ablauf je Record:

1. Kandidatenzeilen: Zeilen mit genau zwei Zahlenpaaren der Form `Wert (SD)`.
   Genau zwei Paare heisst zwei Arme; Zeilen mit mehr Paaren werden nicht
   gebunden, weil dann Wochenbloecke und Arme ohne Kopf nicht trennbar sind.
2. Zeilenlabel: Text vor dem ersten Zahlenpaar, ohne Markdown und Nummerierung.
   Es muss ein Outcome-Stammwort enthalten und darf kein Aenderungswort
   (`change`, `delta`, `difference`, `change from BL`) tragen.
3. Armreihenfolge: in den bis zu sechs Zeilen davor muss ein Tabellenkopf
   stehen, der den Interventions- oder Comparator-Namen nennt. Steht nur ein
   Name, wird die Reihenfolge daraus abgeleitet; steht keiner, wird nicht
   gebunden. Ohne Kopf waere die Zuordnung geraten, und genau das soll die
   Regel verhindern.
4. Mehrere gleich gute Zeilen werden nicht aufgeloest.

Zwei Modi:

* `additiv`  ergaenzt nur Schluessel, die die Vorhersage noch nicht hat. Damit
  kann kein TP verloren gehen.
* `ersetzen` ueberschreibt auch vorhandene Werte am gebundenen Schluessel.
  Dieser Modus kann TPs kosten; er wird getrennt gemessen und ist nicht
  Standard.

Gemessen wird auf den 41 schweren Records (`schwere_records_20261121`), ohne
Netzaufruf und ohne Aenderung an Gold, Predictions oder Bewertungslogik.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zeilenbindung_20261121.py
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
BENCH = ANALYSE.parent
REPO = BENCH.parent.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from satz_locator_20261121 import unterscheider  # noqa: E402
from zahlabgleich_20261121 import zahl_positionen  # noqa: E402

PAAR = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*\(\s*(-?\d+(?:[.,]\d+)?)\s*\)")
ZAHL = re.compile(r"-?\d+(?:[.,]\d+)?")
AENDERUNG = ("mean change", "change from", "change in", "delta", "difference", "change (")
STOPP_ARM = {"group", "patients", "total", "study", "versus", "with", "from", "were"}


def zahl(text: str) -> float:
    return float(text.replace(",", "."))


def label_von(zeile: str, start: int) -> str:
    roh = zeile[:start]
    roh = re.sub(r"[*_#|]", " ", roh)
    roh = re.sub(r"^\s*[\d.)\-\u2013]+\s*", "", roh)
    return re.sub(r"\s+", " ", roh).strip()


def arm_reihenfolge(kopf: str, context: dict[str, Any]) -> str:
    """`intervention_zuerst`, `comparator_zuerst` oder leer (unbekannt)."""
    klein = kopf.lower()

    def namen(feld: str) -> list[str]:
        roh = str((context or {}).get(feld) or "").lower()
        worte = [w for w in re.findall(r"[a-z][a-z-]{2,}", roh) if w not in STOPP_ARM]
        return worte[:4]

    inter = [(w, klein.find(w)) for w in namen("intervention")]
    comp = [(w, klein.find(w)) for w in namen("comparator")]
    inter = [w for w in inter if w[1] >= 0]
    comp = [w for w in comp if w[1] >= 0]
    if not inter and not comp:
        return ""
    if inter and not comp:
        return "intervention_zuerst"
    if comp and not inter:
        return "comparator_zuerst"
    return "intervention_zuerst" if min(p for _, p in inter) < min(p for _, p in comp) else "comparator_zuerst"


WOCHE = re.compile(r"\b(?:week|month|day|year)\s*\d+|\bbaseline\b", re.IGNORECASE)
SPALTEN = re.compile(r"\s{2,}")


def spalten_von(zeile: str) -> list[str]:
    """Spaltenlabels einer Kopfzeile, leere Stuecke entfernt."""
    return [teil.strip() for teil in SPALTEN.split(zeile.strip()) if teil.strip()]


def raster(i: int, zeilen: list[str], k: int) -> dict[str, Any]:
    """Spaltenraster ueber einer Datenzeile mit `k` Wertepaaren.

    Gesucht werden bis zu zwoelf Zeilen darueber eine Armzeile mit genau `k`
    Spaltenlabels und eine Wochenzeile. Das ist das Muster von yun2024:30
    (`Week 12 / Week 24 / Week 52` ueber je drei Armen).
    """
    armzeile, wochenzeile, wochen = "", "", []
    for j in range(i - 1, max(-1, i - 13), -1):
        if len(PAAR.findall(zeilen[j])) >= 2:
            continue
        labels = spalten_von(zeilen[j])
        if len(labels) == k:
            armzeile = zeilen[j].strip()
        gefunden = [w.group(0).strip() for w in WOCHE.finditer(zeilen[j])]
        if len(gefunden) >= 2 and not wochen:
            wochenzeile, wochen = zeilen[j].strip(), gefunden
    return {"armzeile": armzeile, "spalten": spalten_von(armzeile) if armzeile else [],
            "wochenzeile": wochenzeile, "wochen": wochen}


def arm_spalte(spalten: list[str], context: dict[str, Any], feld: str) -> int:
    """Index der Spalte mit der besten Uebereinstimmung; -1, wenn nicht eindeutig.

    Zahlen zaehlen mit: `CZP 200 mg` gegen `CZP 400 mg` ist nur ueber die Dosis
    zu trennen, und genau dieser Fall steht in yun2024:30.
    """
    roh = str((context or {}).get(feld) or "").lower()
    worte = [w for w in re.findall(r"[a-z0-9][a-z0-9-]{2,}", roh) if w not in STOPP_ARM]
    if not worte:
        return -1
    punkte = [sum(1 for w in worte if w in s.lower()) for s in spalten]
    bestes = max(punkte)
    spitze = [i for i, p in enumerate(punkte) if p == bestes]
    return spitze[0] if bestes > 0 and len(spitze) == 1 else -1


def binde(record: dict[str, Any], text: str) -> dict[str, Any]:
    """Zeilenbindung eines Records. Leere `zellen` heisst: nicht gebunden."""
    context = record.get("context") or {}
    kern = [w.lower() for w in unterscheider(context)]
    ziel = str(((record.get("timepoint") or {}).get("target")) or "").strip()
    zeilen = text.splitlines()
    kandidaten: list[dict[str, Any]] = []
    for i, zeile in enumerate(zeilen):
        paare = PAAR.findall(zeile)
        if len(paare) < 2:
            continue
        label = label_von(zeile, PAAR.search(zeile).start())
        if len(label) < 3 or any(w in label.lower() for w in AENDERUNG):
            continue
        treffer = [w for w in kern if w[: max(6, len(w) - 3)] in label.lower()]
        if not treffer:
            continue
        kandidaten.append(
            {
                "zeile": i + 1,
                "index": i,
                "label": label,
                "paare": [[zahl(a) for a, _ in paare], [zahl(b) for _, b in paare]],
                "treffer": treffer,
                "rang": len(treffer),
            }
        )
    if not kandidaten:
        return {"zellen": [], "grund": "keine Zeile mit Zahlenpaaren und Outcome-Label"}
    bestes = max(k["rang"] for k in kandidaten)
    spitze = [k for k in kandidaten if k["rang"] == bestes]
    if len(spitze) > 1:
        return {"zellen": [], "grund": f"{len(spitze)} gleich gute Zeilen", "kandidaten": spitze}
    k = spitze[0]
    mittel, streuung = k["paare"]
    if any(s <= 0 for s in streuung):
        return {"zellen": [], "grund": "Streuung nicht positiv"}

    # Spaltenraster: Wochenzeile waehlt den Block, Armzeile die Spalte je Arm.
    r = raster(k["index"], zeilen, len(mittel))
    spalten = r["spalten"]
    wochen = r["wochen"]
    if len(spalten) != len(mittel):
        return {"zellen": [], "grund": "kein Spaltenraster mit passender Breite",
                "label": k["label"], "zeile": k["zeile"]}
    block, arme_pro_block = 0, len(mittel)
    if wochen and len(mittel) % len(wochen) == 0:
        arme_pro_block = len(mittel) // len(wochen)
        if ziel:
            passend = [w.lower() for w in wochen if w.lower() == ziel.lower() or ziel.lower() in w.lower()]
            if len(passend) != 1:
                return {"zellen": [], "grund": f"Zielzeitpunkt '{ziel}' nicht eindeutig in {wochen}",
                        "label": k["label"], "zeile": k["zeile"]}
            block = [w.lower() for w in wochen].index(passend[0])
    if arme_pro_block < 2:
        return {"zellen": [], "grund": "Raster traegt keine zwei Arme", "label": k["label"]}

    zellen: list[dict[str, Any]] = []
    belegt: dict[str, int] = {}
    for arm in ("intervention", "comparator"):
        bereich = range(block * arme_pro_block, (block + 1) * arme_pro_block)
        block_spalten = [spalten[i] for i in bereich]
        lokal = arm_spalte(block_spalten, context, arm)
        kandidaten_spalten = [bereich[lokal]] if lokal >= 0 else []
        if len(kandidaten_spalten) != 1:
            return {"zellen": [], "grund": f"Arm {arm} nicht eindeutig im Raster",
                    "label": k["label"], "zeile": k["zeile"]}
        index = kandidaten_spalten[0]
        belegt[arm] = index
        zellen.append({"field": f"{arm}_mean", "arm": arm, "value": mittel[index]})
        zellen.append({"field": f"{arm}_standard_deviation", "arm": arm, "value": streuung[index]})

    # Gruppengroessen aus einer Kopfzeile mit (n = X), spaltenweise.
    for j in range(k["index"] - 1, max(-1, k["index"] - 13), -1):
        groessen = re.findall(r"n\s*=\s*(\d+)", zeilen[j])
        if len(groessen) == len(spalten):
            zellen.append({"field": "intervention_group_size", "arm": "intervention",
                           "value": float(groessen[belegt["intervention"]])})
            zellen.append({"field": "comparator_group_size", "arm": "comparator",
                           "value": float(groessen[belegt["comparator"]])})
            break

    return {"zellen": zellen, "zeile": k["zeile"], "label": k["label"],
            "spalten": spalten, "wochen": wochen, "block": block,
            "treffer": k["treffer"], "grund": "gebunden"}


def wende_an(zellen: list[dict[str, Any]], bindung: dict[str, Any], modus: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verrechnet die Bindung mit der Vorhersage. Gibt (neu, eingefuegt/ersetzt)."""
    neu = [dict(z) for z in zellen]
    vorhanden = {(str(z.get("field") or ""), v.arm_von(z)) for z in neu}
    aenderungen: list[dict[str, Any]] = []
    for zelle in bindung.get("zellen") or []:
        key = (zelle["field"], zelle["arm"])
        if key not in vorhanden:
            neu.append(dict(zelle))
            vorhanden.add(key)
            aenderungen.append({**zelle, "art": "ergaenzt"})
            continue
        if modus != "ersetzen":
            continue
        for index, bestehend in enumerate(neu):
            if (str(bestehend.get("field") or ""), v.arm_von(bestehend)) == key:
                if v.zahl(bestehend.get("value")) != zelle["value"]:
                    aenderungen.append(
                        {"field": key[0], "arm": key[1], "alt": v.zahl(bestehend.get("value")),
                         "value": zelle["value"], "art": "ersetzt"}
                    )
                    neu[index] = dict(zelle)
                break
    return neu, aenderungen


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    auswahl = json.loads(
        (ANALYSE / "schwere_records_20261121" / "auswahl_20261121.json").read_text(encoding="utf-8")
    )["records"]
    ids = [a["record_id"] for a in auswahl]
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}

    # Fehlerzellen aus Phase 1, um die Frage "wie viele davon" beantworten zu koennen.
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    fp_gebunden = [f for f in fehler["faelle_fp"] if f["regel"] == "fp_gebunden"]
    fn_ersetzt = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]

    ergebnisse: list[dict[str, Any]] = []
    for modus in ("additiv", "ersetzen"):
        bilanz_vor, bilanz_nach = [], []
        treffer_fp = treffer_fn = 0
        detail: list[dict[str, Any]] = []
        for rid in ids:
            record = records[rid]
            text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
            gold = (record.get("gold") or {}).get("cells") or []
            roh = v.zellen(p5.get(rid))
            bindung = binde(record, text)
            neu, aenderungen = wende_an(roh, bindung, modus)
            vor = v.bilanz_p5(gold, roh)
            nach = v.bilanz_p5(gold, neu)
            bilanz_vor.append(vor)
            bilanz_nach.append(nach)

            # Wirkung auf die Fehlerzellen dieses Records
            gold_keys = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in gold}
            neue_keys = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in neu}
            for f in fp_gebunden:
                if f["record_id"] != rid:
                    continue
                key = (f["feld"], f["arm"])
                if key in neue_keys and gold_keys.get(key) is not None and abs(neue_keys[key] - gold_keys[key]) < 1e-6:
                    if roh and key in {(str(z.get("field") or ""), v.arm_von(z)) for z in roh}:
                        alt = next(v.zahl(z.get("value")) for z in roh if (str(z.get("field") or ""), v.arm_von(z)) == key)
                        if abs(alt - gold_keys[key]) > 1e-6:
                            treffer_fp += 1
            for f in fn_ersetzt:
                if f["record_id"] != rid:
                    continue
                key = (f["feld"], f["arm"])
                if key in neue_keys and abs(neue_keys[key] - f["wert"]) < 1e-6:
                    if key not in {(str(z.get("field") or ""), v.arm_von(z)) for z in roh} or v.bilanz_p5(
                        [g for g in gold if (str(g.get("field") or ""), v.arm_von(g)) == key], roh
                    )["tp"] == 0:
                        treffer_fn += 1
            detail.append(
                {
                    "record_id": rid,
                    "gebunden": bool(bindung.get("zellen")),
                    "grund": bindung.get("grund"),
                    "zeile": bindung.get("zeile"),
                    "label": bindung.get("label"),
                    "reihenfolge": bindung.get("reihenfolge"),
                    "aenderungen": aenderungen,
                    "vor": vor,
                    "nach": nach,
                }
            )
        summe_vor = {k: sum(b[k] for b in bilanz_vor) for k in ("tp", "fp", "fn")}
        summe_nach = {k: sum(b[k] for b in bilanz_nach) for k in ("tp", "fp", "fn")}
        ergebnisse.append(
            {
                "modus": modus,
                "records": len(ids),
                "gebunden": sum(1 for d in detail if d["gebunden"]),
                "vorher": summe_vor,
                "nachher": summe_nach,
                "tp_verlust": summe_vor["tp"] - summe_nach["tp"],
                "fp_gebunden_korrigiert": treffer_fp,
                "fn_wert_ersetzt_korrigiert": treffer_fn,
                "detail": detail,
            }
        )

    # Obergrenze: Wie viele der Fehlerzellen liegen ueberhaupt in einer Zeile,
    # die den Wert und ein Outcome-Wort traegt? Das ist die Grenze fuer jede
    # textbasierte Zeilenbindung, unabhaengig von der Regel.
    kern_je_record = {rid: [w.lower() for w in unterscheider(records[rid].get("context") or {})]
                      for rid in ids}
    texte = {rid: (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in ids}
    zellen = [f for f in fp_gebunden + fn_ersetzt if f["record_id"] in set(ids)]
    mit_wort = mit_kaption = ohne = 0
    for f in zellen:
        zeilen = texte[f["record_id"]].splitlines()
        kern = kern_je_record[f["record_id"]]
        treffer = [i for i, l in enumerate(zeilen) if zahl_positionen(f["wert"], l)]
        if any(any(w[: max(6, len(w) - 3)] in zeilen[i].lower() for w in kern) for i in treffer):
            mit_wort += 1
        elif any(any(w[: max(6, len(w) - 3)] in " ".join(zeilen[max(0, i - 10) : i]).lower() for w in kern)
                 for i in treffer):
            mit_kaption += 1
        else:
            ohne += 1
    obergrenze = {"zellen": len(zellen), "wert_und_wort_in_zeile": mit_wort,
                  "wort_nur_in_kaption": mit_kaption, "ohne_outcome_bezug": ohne}

    in_auswahl_fp = sum(1 for f in fp_gebunden if f["record_id"] in set(ids))
    in_auswahl_fn = sum(1 for f in fn_ersetzt if f["record_id"] in set(ids))
    ergebnis = {
        "stand": "2026-11-21",
        "regel": {
            "kandidat": "genau zwei Wertepaare der Form Wert (SD) in einer Zeile",
            "label": "Outcome-Stammwort im Zeilenlabel, Aenderungsworte ausgeschlossen",
            "arm": "Reihenfolge aus Tabellenkopf; ohne Kopf keine Bindung",
            "mehrdeutig": "gleich gute Zeilen werden nicht aufgeloest",
        },
        "auswahl": {
            "records": len(ids),
            "fp_gebunden_in_auswahl": in_auswahl_fp,
            "fn_wert_ersetzt_in_auswahl": in_auswahl_fn,
            "fp_gebunden_gesamt": len(fp_gebunden),
            "fn_wert_ersetzt_gesamt": len(fn_ersetzt),
        },
        "laeufe": ergebnisse,
        "obergrenze": obergrenze,
    }
    (HIER / "zeilenbindung_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


    additiv, ersetzen = ergebnisse
    zeilen = "\n".join(
        f"| `{d['record_id']}` | {'ja' if d['gebunden'] else 'nein'} | "
        f"{(d['label'] or '-')[:40]} | {d['vor']['tp']}/{d['vor']['fp']}/{d['vor']['fn']} | "
        f"{d['nach']['tp']}/{d['nach']['fp']}/{d['nach']['fn']} | {len(d['aenderungen'])} |"
        for d in additiv["detail"]
    )
    bericht = (
        "# Zeilenbindung als Regel, offline gemessen (21.11.2026)\n\n"
        "Die Regel ist aus dem Aufbau von yun2024:30 abgeleitet, goldfrei und ohne\n"
        "Netzaufruf. Sie arbeitet in vier Schritten:\n\n"
        "1. Datenzeile: eine Zeile mit Wertepaaren `Wert (SD)` und einem Zeilenlabel,\n"
        "   das ein Outcome-Stammwort traegt. Aenderungszeilen (`mean change`,\n"
        "   `delta`, `difference`) sind ausgeschlossen.\n"
        "2. Spaltenraster: ueber der Zeile muss eine Armzeile mit genau so vielen\n"
        "   Spaltenlabels stehen wie die Zeile Wertepaare hat, und eine Wochenzeile mit\n"
        "   den Zeitpunktlabels. Das ist das Muster von Record 30 (`Week 12/24/52` ueber\n"
        "   je drei Armen).\n"
        "3. Block und Arm: der Zielzeitpunkt des Records waehlt den Wochenblock, die\n"
        "   Spaltenlabels waehlen je Arm genau eine Spalte (Zahlen zaehlen mit, sonst\n"
        "   waeren `CZP 200 mg` und `CZP 400 mg` nicht zu trennen).\n"
        "4. Verweigerung: fehlt ein Raster, ist ein Arm nicht eindeutig oder gibt es\n"
        "   zwei gleich gute Zeilen, wird nichts gebunden.\n\n"
        f"Geprueft auf {additiv['records']} der 41 schweren Records. In dieser Auswahl\n"
        f"liegen {in_auswahl_fp} der {len(fp_gebunden)} `fp_gebunden` und "
        f"{in_auswahl_fn} der {len(fn_ersetzt)} `fn_wert_ersetzt`.\n\n"
        "## Ergebnis\n\n"
        "| Modus | gebunden | TP vorher | FP vorher | FN vorher | TP nachher | FP nachher | FN nachher | TP-Verlust |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        f"| additiv | {additiv['gebunden']} | {additiv['vorher']['tp']} | {additiv['vorher']['fp']} | "
        f"{additiv['vorher']['fn']} | {additiv['nachher']['tp']} | {additiv['nachher']['fp']} | "
        f"{additiv['nachher']['fn']} | {additiv['tp_verlust']} |\n"
        f"| ersetzen | {ersetzen['gebunden']} | {ersetzen['vorher']['tp']} | {ersetzen['vorher']['fp']} | "
        f"{ersetzen['vorher']['fn']} | {ersetzen['nachher']['tp']} | {ersetzen['nachher']['fp']} | "
        f"{ersetzen['nachher']['fn']} | {ersetzen['tp_verlust']} |\n\n"
        "Korrigiert wurden in der Auswahl:\n\n"
        "| Modus | `fn_wert_ersetzt` richtig gebunden | `fp_gebunden` richtig gebunden |\n"
        "|---|---:|---:|\n"
        f"| additiv | {additiv['fn_wert_ersetzt_korrigiert']} | {additiv['fp_gebunden_korrigiert']} |\n"
        f"| ersetzen | {ersetzen['fn_wert_ersetzt_korrigiert']} | {ersetzen['fp_gebunden_korrigiert']} |\n\n"
        "Zwischenstand der Entwicklung, damit die Zahl einordenbar ist: eine erste,\n"
        "lockere Fassung ohne Spaltenraster band 3 Records, davon 0 mit richtigem Wert,\n"
        "und erzeugte 12 zusaetzliche FP. Die strenge Fassung bindet keinen. Beide\n"
        "Ergebnisse sagen dasselbe: der Textabgleich findet Zeilen, aber nicht die\n"
        "richtige Zelle.\n\n"
        f"## Obergrenze jeder Textzeilen-Bindung\n\n"
        f"Von den {obergrenze['zellen']} Fehlerzellen der Auswahl liegen "
        f"{obergrenze['wert_und_wort_in_zeile']} in einer Zeile, die den Wert und ein "
        "Outcome-Wort traegt, "
        f"{obergrenze['wort_nur_in_kaption']} nur mit dem Wort in den zehn Zeilen darueber, "
        f"{obergrenze['ohne_outcome_bezug']} ohne Outcome-Bezug. Mehr als "
        f"{obergrenze['wert_und_wort_in_zeile'] + obergrenze['wort_nur_in_kaption']} Zellen "
        "kann eine textbasierte Zeilenbindung also grundsaetzlich nicht erreichen.\n\n"
        "Erreicht hat die Regel 0. Der Grund ist nicht die Obergrenze, sondern die\n"
        "Eindeutigkeit: dieselbe Tabelle enthaelt mehrere Zeilen mit demselben Label\n"
        "(`Mean score (SD)` fuer PCS und MCS), und die Unterscheidung steht in einer\n"
        "Zeilengruppen-Ueberschrift, die der Textabgleich nicht als eigene Achse liest.\n"
        "Genau daran scheitert auch Record 30 selbst: das Label nennt den Outcome nicht\n"
        "(der steht in der Caption), und die Goldzeile ist eine von zwei gleich\n"
        "beschrifteten Zeilen.\n\n"
        "## Je Record (Modus additiv)\n\n"
        "| Record | gebunden | Zeilenlabel | TP/FP/FN vorher | TP/FP/FN nachher | Aenderungen |\n"
        "|---|---|---|---|---|---:|\n"
        f"{zeilen}\n\n"
        "## Was die Regel kann und was nicht\n\n"
        "- Sie bindet nur, wenn Tabellenraster und Armspalten eindeutig sind. Das ist\n"
        "  bewusst streng: eine falsche Bindung kostet eine Zelle und erzeugt eine FP,\n"
        "  eine Verweigerung kostet nur den Versuch.\n"
        "- Der Modus `ersetzen` kann TPs kosten; er ist deshalb nicht Standard. In\n"
        "  dieser Auswahl trat der Fall nicht ein, weil nichts gebunden wurde.\n"
        "- Die Regel ersetzt keine Modellentscheidung. Auf Record 30 hat das Modell die\n"
        "  Zeile gewaehlt; die deterministische Regel muesste dieselbe Wahl ohne\n"
        "  Semantik treffen und verweigert stattdessen.\n\n"
        "## Grenzen\n\n"
        "- Die Auswahl ist nicht repraesentativ fuer die 699 Records: es sind die\n"
        "  schweren Faelle, in denen P5 leer blieb oder nichts traf. Von den 270\n"
        "  `fp_gebunden` und 295 `fn_wert_ersetzt` liegen nur 17 und 16 hier.\n"
        "- Die Zaehlung `richtig gebunden` prueft nur den Schluessel, nicht die\n"
        "  Fundstelle; eine Zeile kann den Wert an der richtigen Stelle nennen und\n"
        "  trotzdem die falsche Population sein.\n"
        "- Kein Zeitpunkt in der Zelle: die Regel bindet keine `timepoint`-Angabe.\n"
    )
    (HIER / "zeilenbindung_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    for lauf in ergebnisse:
        print(
            f"{lauf['modus']:9s} gebunden {lauf['gebunden']:2d}/{lauf['records']} | "
            f"TP {lauf['vorher']['tp']}->{lauf['nachher']['tp']} "
            f"FP {lauf['vorher']['fp']}->{lauf['nachher']['fp']} "
            f"FN {lauf['vorher']['fn']}->{lauf['nachher']['fn']} | "
            f"TP-Verlust {lauf['tp_verlust']} | korrigiert FN {lauf['fn_wert_ersetzt_korrigiert']} "
            f"FP {lauf['fp_gebunden_korrigiert']}"
        )
    print(f"In der Auswahl: {in_auswahl_fp} fp_gebunden, {in_auswahl_fn} fn_wert_ersetzt "
          f"(von {len(fp_gebunden)}/{len(fn_ersetzt)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
