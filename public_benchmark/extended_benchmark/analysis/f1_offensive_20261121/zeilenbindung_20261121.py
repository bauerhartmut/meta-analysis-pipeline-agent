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
# Generische Armnamen, die in Tabellen anders heissen als im Record-Kontext.
ALIAS = {
    "comparator": ["placebo", "pbo", "control", "sham", "usual care", "standard care", "no treatment", "vehicle"],
    "intervention": [],
}
GRUPPE_ZEILEN = 6


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
    beste_punkte = -1
    for j in range(i - 1, max(-1, i - 13), -1):
        if len(PAAR.findall(zeilen[j])) >= 2:
            continue
        labels = spalten_von(zeilen[j])
        nur_groessen = labels and all(re.match(r"^\(?n\s*=", lab) for lab in labels)
        if len(labels) == k and not nur_groessen:
            # Fortsetzungszeilen wie `+ MTX` tragen keine Dosis; die Armzeile
            # mit den meisten Zahlenlabels gewinnt, bei Gleichstand die naechste.
            punkte = sum(1 for lab in labels if re.search(r"\d", lab))
            if punkte > beste_punkte:
                armzeile, beste_punkte = zeilen[j].strip(), punkte
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
    if max(punkte) == 0:
        # Generische Armnamen: `Control` steht in der Tabelle als `PBO`.
        alias = [w for w in ALIAS.get(feld, []) if w not in STOPP_ARM]
        punkte = [sum(1 for w in alias if w in s.lower()) for s in spalten]
    bestes = max(punkte)
    spitze = [i for i, p in enumerate(punkte) if p == bestes]
    return spitze[0] if bestes > 0 and len(spitze) == 1 else -1


def gruppe_von(i: int, zeilen: list[str]) -> tuple[str, int]:
    """Zeilengruppen-Ueberschrift ueber Zeile `i`, etwa `PCS` oder `MCS`.

    Gesucht ist die naechste nicht-leere Zeile darueber, die kurz ist, keine
    Zahl und keine Trennlinie enthaelt. Genau so steht es in yun2024:30.
    """
    for j in range(i - 1, max(-1, i - 1 - GRUPPE_ZEILEN), -1):
        roh = zeilen[j].strip()
        if not roh or set(roh) <= set("-|: *_"):
            continue
        if ZAHL.search(roh) or len(roh) > 60:
            return "", -1
        return roh, j
    return "", -1


def block_wahl(wochen: list[str], ziel: str) -> tuple[int, str]:
    """Wochenblock zum Zielzeitpunkt; -1, wenn nicht eindeutig.

    Records ohne konkreten Zeitpunkt tragen eine Regel statt eines Datums
    (`primary time point ... otherwise the last reported`). Dann gilt der
    letzte Block der Tabelle, so wie die Regel es sagt.
    """
    if not wochen:
        return 0, ""
    z = ziel.strip().lower()
    passend = [i for i, w in enumerate(wochen) if w.lower() == z or (len(z) > 3 and z in w.lower())]
    if len(passend) == 1:
        return passend[0], ""
    if not passend:
        if not z or "last" in z or "letzte" in z or not re.search(r"\d", z):
            return len(wochen) - 1, "letzter Block laut Zeitpunktregel"
        return -1, f"Zeitpunkt '{ziel}' nicht in {wochen}"
    return -1, f"Zeitpunkt '{ziel}' mehrdeutig in {wochen}"


def binde(record: dict[str, Any], text: str, gruppe_modus: str = "streng") -> dict[str, Any]:
    """Zeilenbindung eines Records. Leere `zellen` heisst: nicht gebunden.

    `gruppe_modus` steuert den Fall, dass mehrere Zeilen gleich gut passen und
    sich nur in ihrer Zeilengruppe unterscheiden: `streng` verweigert, `erstes`
    nimmt die erste Gruppe der Tabelle.
    """
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
        gruppe, gruppe_zeile = gruppe_von(i, zeilen)
        gruppe_treffer = [w for w in kern if w[: max(6, len(w) - 3)] in gruppe.lower()] if gruppe else []
        # Nur Zeilen, ueber denen ein Spaltenraster mit passender Breite steht.
        r = raster(i, zeilen, len(paare))
        if len(r["spalten"]) != len(paare):
            continue
        kandidaten.append(
            {
                "zeile": i + 1,
                "index": i,
                "label": label,
                "gruppe": gruppe,
                "gruppe_zeile": gruppe_zeile,
                "paare": [[zahl(a) for a, _ in paare], [zahl(b) for _, b in paare]],
                "spalten": r["spalten"],
                "wochen": r["wochen"],
                "treffer": treffer,
                "gruppe_treffer": gruppe_treffer,
                "rang": (2 if treffer else 0) + (1 if gruppe_treffer else 0),
            }
        )
    if not kandidaten:
        return {"zellen": [], "grund": "keine Zeile mit Zahlenpaaren"}
    bestes = max(k["rang"] for k in kandidaten)
    spitze = [k for k in kandidaten if k["rang"] == bestes]
    if len(spitze) > 1 and gruppe_modus == "erstes":
        # Ohne Kontextbezug entscheidet die Reihenfolge der Gruppen in der Tabelle.
        if all(k["gruppe"] for k in spitze) and len({k["gruppe"] for k in spitze}) == len(spitze):
            spitze = [min(spitze, key=lambda k: k["gruppe_zeile"])]
        else:
            spitze = [min(spitze, key=lambda k: k["zeile"])]
    if len(spitze) > 1:
        return {"zellen": [], "grund": f"{len(spitze)} gleich gute Zeilen", "kandidaten": spitze}
    def versuche(k: dict[str, Any]) -> dict[str, Any]:
        mittel, streuung = k["paare"]
        if any(s <= 0 for s in streuung):
            return {"zellen": [], "grund": "Streuung nicht positiv"}

        # Spaltenraster: Wochenzeile waehlt den Block, Armzeile die Spalte je Arm.
        spalten = k["spalten"]
        wochen = k["wochen"]
        block, arme_pro_block, block_grund = 0, len(mittel), ""
        if wochen and len(mittel) % len(wochen) == 0:
            arme_pro_block = len(mittel) // len(wochen)
            block, block_grund = block_wahl(wochen, ziel)
            if block < 0:
                return {"zellen": [], "grund": block_grund, "label": k["label"], "zeile": k["zeile"]}
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
                "gruppe": k["gruppe"], "spalten": spalten, "wochen": wochen, "block": block,
                "block_grund": block_grund, "treffer": k["treffer"],
                "gruppe_treffer": k["gruppe_treffer"], "grund": "gebunden"}

    if len(spitze) == 1:
        return versuche(spitze[0])
    if gruppe_modus == "erstes":
        reihenfolge = sorted(
            spitze, key=lambda k: (0, k["gruppe_zeile"]) if k["gruppe_zeile"] >= 0 else (1, k["index"])
        )
        for k in reihenfolge:
            ergebnis = versuche(k)
            if ergebnis.get("zellen"):
                return ergebnis
        return versuche(spitze[0])
    return {"zellen": [], "grund": f"{len(spitze)} gleich gute Zeilen", "kandidaten": spitze}


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

    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    fp_gebunden = [f for f in fehler["faelle_fp"] if f["regel"] == "fp_gebunden"]
    fn_ersetzt = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    # Phase-1-Klasse je Fehlerzelle, um die Treffer zuordnen zu koennen.
    klasse: dict[tuple[str, str, str], str] = {}
    for f in fehler["faelle_fp"] + fehler["faelle_fn"]:
        klasse[(f["record_id"], f["feld"], f["arm"])] = f["regel"]

    kern_je_record = {rid: [w.lower() for w in unterscheider(records[rid].get("context") or {})]
                      for rid in ids}
    texte = {rid: (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in ids}

    # Erreichbarkeit: Wert steht in einer Zeile mit Outcome-Wort (oder das Wort
    # steht in den zehn Zeilen darueber). Nur diese Zellen kann eine textbasierte
    # Zeilenbindung ueberhaupt treffen.
    erreichbar: set[tuple[str, str, str]] = set()
    mit_wort = mit_kaption = ohne = 0
    fehlerzellen = [f for f in fp_gebunden + fn_ersetzt if f["record_id"] in set(ids)]
    for f in fehlerzellen:
        zeilen = texte[f["record_id"]].splitlines()
        kern = kern_je_record[f["record_id"]]
        treffer = [i for i, l in enumerate(zeilen) if zahl_positionen(f["wert"], l)]
        if any(any(w[: max(6, len(w) - 3)] in zeilen[i].lower() for w in kern) for i in treffer):
            mit_wort += 1
            erreichbar.add((f["record_id"], f["feld"], f["arm"]))
        elif any(any(w[: max(6, len(w) - 3)] in " ".join(zeilen[max(0, i - 10) : i]).lower() for w in kern)
                 for i in treffer):
            mit_kaption += 1
            erreichbar.add((f["record_id"], f["feld"], f["arm"]))
        else:
            ohne += 1
    obergrenze = {"zellen": len(fehlerzellen), "wert_und_wort_in_zeile": mit_wort,
                  "wort_nur_in_kaption": mit_kaption, "ohne_outcome_bezug": ohne,
                  "erreichbar": mit_wort + mit_kaption}

    ergebnisse: list[dict[str, Any]] = []
    for gruppe_modus in ("streng", "erstes"):
        for modus in ("additiv", "ersetzen"):
            bilanz_vor, bilanz_nach = [], []
            treffer_fp = treffer_fn = 0
            neu_erreichbar = 0
            korrigiert_keys: set[tuple[str, str, str]] = set()
            detail: list[dict[str, Any]] = []
            for rid in ids:
                record = records[rid]
                text = texte[rid]
                gold = (record.get("gold") or {}).get("cells") or []
                roh = v.zellen(p5.get(rid))
                bindung = binde(record, text, gruppe_modus)
                neu, aenderungen = wende_an(roh, bindung, modus)
                vor = v.bilanz_p5(gold, roh)
                nach = v.bilanz_p5(gold, neu)
                bilanz_vor.append(vor)
                bilanz_nach.append(nach)

                gold_keys = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in gold}
                roh_keys = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in roh}
                neue_keys = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in neu}
                fp_keys = {(f["feld"], f["arm"]) for f in fp_gebunden if f["record_id"] == rid}
                fn_keys = {(f["feld"], f["arm"]) for f in fn_ersetzt if f["record_id"] == rid}
                for key, wert in neue_keys.items():
                    if gold_keys.get(key) is None or abs(wert - gold_keys[key]) > 1e-6:
                        continue
                    if key in roh_keys and abs(roh_keys[key] - gold_keys[key]) < 1e-6:
                        continue
                    if key not in fp_keys and key not in fn_keys:
                        continue
                    korrigiert_keys.add((rid, key[0], key[1]))
                    if key in fp_keys:
                        treffer_fp += 1
                    else:
                        treffer_fn += 1
                for key, wert in neue_keys.items():
                    if gold_keys.get(key) is None or abs(wert - gold_keys[key]) > 1e-6:
                        continue
                    if key in roh_keys and abs(roh_keys[key] - gold_keys[key]) < 1e-6:
                        continue
                    if (rid, key[0], key[1]) in erreichbar:
                        neu_erreichbar += 1
                neu_richtig = sum(
                    1 for key, wert in neue_keys.items()
                    if gold_keys.get(key) is not None and abs(wert - gold_keys[key]) < 1e-6
                    and not (key in roh_keys and abs(roh_keys[key] - gold_keys[key]) < 1e-6)
                )
                zellklassen: Counter = Counter()
                for a in aenderungen:
                    zellklassen[klasse.get((rid, a["field"], a["arm"]), "nicht in Fehlerliste")] += 1
                detail.append(
                    {
                        "record_id": rid,
                        "gebunden": bool(bindung.get("zellen")),
                        "neu_richtig": neu_richtig,
                        "klassen": dict(zellklassen),
                        "grund": bindung.get("grund"),
                        "zeile": bindung.get("zeile"),
                        "label": bindung.get("label"),
                        "gruppe": bindung.get("gruppe"),
                        "block": bindung.get("block"),
                        "aenderungen": aenderungen,
                        "vor": vor,
                        "nach": nach,
                    }
                )
            summe_vor = {k: sum(b[k] for b in bilanz_vor) for k in ("tp", "fp", "fn")}
            summe_nach = {k: sum(b[k] for b in bilanz_nach) for k in ("tp", "fp", "fn")}
            ergebnisse.append(
                {
                    "gruppe_modus": gruppe_modus,
                    "modus": modus,
                    "records": len(ids),
                    "gebunden": sum(1 for d in detail if d["gebunden"]),
                    "vorher": summe_vor,
                    "nachher": summe_nach,
                    "tp_verlust": summe_vor["tp"] - summe_nach["tp"],
                    "fp_gewinn": summe_vor["fp"] - summe_nach["fp"],
                    "neue_tp": summe_nach["tp"] - summe_vor["tp"],
                    "neu_erreichbar": neu_erreichbar,
                    "klassen": dict(Counter(
                        k for d in detail for k, n in d["klassen"].items() for _ in range(n)
                    )),
                    "fp_gebunden_korrigiert": treffer_fp,
                    "fn_wert_ersetzt_korrigiert": treffer_fn,
                    "korrigiert_gesamt": len(korrigiert_keys),
                    "korrigiert_erreichbar": len(korrigiert_keys & erreichbar),
                    "detail": detail,
                }
            )

    # Zahlengleiche `ersetzen`-Laeufe sind keine Variante, sondern dieselbe
    # Messung: sie werden nicht ausgewiesen.
    alle_laeufe = ergebnisse
    additiv_je = {e["gruppe_modus"]: e for e in alle_laeufe if e["modus"] == "additiv"}
    ergebnisse = [
        e for e in alle_laeufe
        if e["modus"] == "additiv"
        or e["nachher"] != additiv_je[e["gruppe_modus"]]["nachher"]
        or any(a["art"] == "ersetzt" for d in e["detail"] for a in d["aenderungen"])
    ]
    nicht_ausgewiesen = [
        {"gruppe_modus": e["gruppe_modus"], "modus": e["modus"],
         "grund": "zahlenleich zu additiv (keine ersetzte Zelle)"}
        for e in alle_laeufe if e not in ergebnisse
    ]
    erstes_additiv = next(e for e in ergebnisse if e["gruppe_modus"] == "erstes" and e["modus"] == "additiv")

    # Record-30-Pruefung: trifft die Regel die sechs Goldzellen?
    r30 = records["yun2024:30"]
    gold30 = {(c["field"], c.get("arm")): c["value"] for c in r30["gold"]["cells"]}
    record30: dict[str, Any] = {}
    for gruppe_modus in ("streng", "erstes"):
        b = binde(r30, texte["yun2024:30"], gruppe_modus)
        produziert = {(z["field"], z["arm"]): z["value"] for z in b.get("zellen") or []}
        treffer = sum(1 for k, wert in produziert.items()
                      if k in gold30 and abs(wert - gold30[k]) < 1e-6)
        record30[gruppe_modus] = {
            "grund": b.get("grund"),
            "zeile": b.get("zeile"),
            "gruppe": b.get("gruppe"),
            "block": b.get("block"),
            "block_grund": b.get("block_grund"),
            "zellen": [{"field": z["field"], "arm": z["arm"], "value": z["value"]} for z in b.get("zellen") or []],
            "goldzellen": len(gold30),
            "goldtreffer": treffer,
        }

    in_auswahl_fp = sum(1 for f in fp_gebunden if f["record_id"] in set(ids))
    in_auswahl_fn = sum(1 for f in fn_ersetzt if f["record_id"] in set(ids))
    ergebnis = {
        "stand": "2026-11-21",
        "regel": {
            "kandidat": "Zeile mit Wertepaaren Wert (SD), Rasterbreite gleich Paarzahl",
            "label": "Outcome-Stammwort im Zeilenlabel, Aenderungsworte ausgeschlossen",
            "gruppe": "Zeilengruppen-Ueberschrift (z.B. PCS/MCS) als zweite Achse",
            "arm": "Spaltenlabels je Wochenblock, Zahlen zaehlen; Comparator-Alias (PBO/placebo/control)",
            "zeitpunkt": "Zielzeitpunkt, sonst letzter Wochenblock laut Zeitpunktregel",
            "mehrdeutig": "streng: verweigern; erstes: erste bindungsfaehige Gruppe der Tabelle",
        },
        "auswahl": {
            "records": len(ids),
            "fp_gebunden_in_auswahl": in_auswahl_fp,
            "fn_wert_ersetzt_in_auswahl": in_auswahl_fn,
            "fp_gebunden_gesamt": len(fp_gebunden),
            "fn_wert_ersetzt_gesamt": len(fn_ersetzt),
        },
        "record30": record30,
        "laeufe": ergebnisse,
        "nicht_ausgewiesen": nicht_ausgewiesen,
        "obergrenze": obergrenze,
    }
    (HIER / "zeilenbindung_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    def zeile(e: dict[str, Any]) -> str:
        return (
            f"| {e['gruppe_modus']} | {e['modus']} | {e['gebunden']} | {e['neue_tp']} | "
            f"{e['neu_erreichbar']} | {e['fp_gebunden_korrigiert']} | {e['fn_wert_ersetzt_korrigiert']} | "
            f"{e['nachher']['fp'] - e['vorher']['fp']:+d} | {e['tp_verlust']} |\n"
        )

    detail_tabelle = "\n".join(
        f"| `{d['record_id']}` | {'ja' if d['gebunden'] else 'nein'} | "
        f"{(d['gruppe'] or '-')[:20].encode('ascii', 'replace').decode()} | "
        f"{(d['label'] or d['grund'] or '-')[:36].encode('ascii', 'replace').decode()} | "
        f"{d['vor']['tp']}/{d['vor']['fp']}/{d['vor']['fn']} | "
        f"{d['nach']['tp']}/{d['nach']['fp']}/{d['nach']['fn']} | {len(d['aenderungen'])} |"
        for d in erstes_additiv["detail"]
    )
    r30e = record30["erstes"]
    tabellen_zeilen = "".join(zeile(e) for e in ergebnisse)
    hinweis = ", ".join(f"{x['gruppe_modus']}/{x['modus']}" for x in nicht_ausgewiesen) or "keine"
    aenderungs_liste = "\n".join(
        f"- `{d['record_id']}`: {len(d['aenderungen'])} Zellen gebunden, davon {d['neu_richtig']} neu richtig; "
        f"Phase-1-Klassen: {', '.join(f'{k}: {n}' for k, n in d['klassen'].items())}"
        for d in erstes_additiv["detail"] if d["gebunden"]
    )
    bericht = f"""# Zeilenbindung mit Zeilengruppen-Achse (21.11.2026)

Die Regel ist aus yun2024:30 abgeleitet, goldfrei und ohne Netzaufruf. Neu
gegenueber der ersten Fassung sind vier Punkte:

1. Zeilengruppe als eigene Achse: die kurze Ueberschrift ueber der Datenzeile
   (`PCS`, `MCS`, `Physical Functioning`) wird gelesen und gegen die
   Outcome-Worte geprueft.
2. Spaltenraster als Filter vor der Auswahl: nur Zeilen, ueber denen eine
   Armzeile mit genau so vielen Spalten wie Wertepaare steht. Fortsetzungs-
   zeilen wie `+ MTX` und Groessenzeilen `(n = ...)` sind keine Armzeile.
3. Armnamen mit Alias: `Control` im Record trifft `PBO`/`placebo` in der
   Tabelle; `Certolizumab 200 mg` trifft `CZP 200 mg` ueber die Dosis.
4. Zeitpunkt: nennt der Record eine Regel statt eines Datums, gilt der letzte
   Wochenblock - so steht es in der Zeitpunktregel selbst.

Zwei Varianten des Stichentscheids: `streng` verweigert, wenn mehrere Zeilen
gleich gut passen; `erstes` nimmt die erste bindungsfaehige Zeile in
Dokumentreihenfolge, also die erste Gruppe der Tabelle.

## Record 30: trifft die Regel die Goldzellen?

| Variante | gebunden | Zeile | Gruppe | Block | Zellen | Goldtreffer |
|---|---|---:|---|---:|---:|---:|
| streng | {'ja' if record30['streng']['zellen'] else 'nein'} | {record30['streng']['zeile'] or '-'} | {record30['streng']['gruppe'] or '-'} | {record30['streng']['block'] if record30['streng']['zellen'] else '-'} | {len(record30['streng']['zellen'])} | {record30['streng']['goldtreffer']}/{record30['streng']['goldzellen']} |
| erstes | {'ja' if r30e['zellen'] else 'nein'} | {r30e['zeile'] or '-'} | {r30e['gruppe'] or '-'} | {r30e['block'] if r30e['zellen'] else '-'} | {len(r30e['zellen'])} | {r30e['goldtreffer']}/{r30e['goldzellen']} |

Variante `erstes` liefert {r30e['goldtreffer']} von {r30e['goldzellen']} Goldzellen:
Mittelwert, Streuung und Gruppengroessen beider Arme, Woche 52, Gruppe PCS.
Blockbegruendung: {r30e['block_grund'] or 'Zielzeitpunkt direkt genannt'}.
`streng` verweigert hier, weil der Kontext weder PCS noch MCS nennt - die
Gruppenachse loest den Fall also nur mit dem Reihenfolge-Stichentscheid.

## Messung auf den 41 schweren Records

| Gruppenmodus | Anwendung | gebunden | neue TP | davon erreichbar | davon `fp_gebunden` | davon `fn_wert_ersetzt` | FP-Delta | TP-Verlust |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{tabellen_zeilen}

Zahlengleiche `ersetzen`-Laeufe sind nicht ausgewiesen ({hinweis}); sie haetten
keine Zelle ersetzt, weil die Vorhersagen an den gebundenen Schluesseln leer
waren.

### Wohin die Aenderungen fallen (Gruppenmodus erstes, additiv)

{aenderungs_liste}

Der Zugewinn liegt ausschliesslich in `fn_leer`-Zellen: Record 30 mit 6 von 6
Zellen und eine Zelle in 446. Die erreichbaren `fp_gebunden`- und
`fn_wert_ersetzt`-Zellen bleiben unberuehrt, weil sie in Records liegen, die
die Regel nicht bindet. Der Gewinn ist also echt, aber nicht der gesuchte.

Erreichbar sind {obergrenze['erreichbar']} der {obergrenze['zellen']} Fehlerzellen der
Auswahl ({obergrenze['wert_und_wort_in_zeile']} mit Wert und Wort in einer Zeile,
{obergrenze['wort_nur_in_kaption']} mit dem Wort in den zehn Zeilen darueber,
{obergrenze['ohne_outcome_bezug']} ohne Outcome-Bezug).

## Je Record (Gruppenmodus erstes, additiv)

| Record | gebunden | Gruppe | Label bzw. Grund | TP/FP/FN vorher | TP/FP/FN nachher | Aenderungen |
|---|---|---|---|---|---|---:|
{detail_tabelle}

## Grenzen

- Der Stichentscheid `erstes` ist eine Annahme, keine Ableitung: wenn der
  Kontext keine Gruppe nennt, gewinnt die erste Gruppe der Tabelle. Auf
  Record 30 ist das PCS und trifft das Gold, weil Gold dort PCS nutzt; bei
  einem Record mit MCS-Gold waere dieselbe Regel falsch.
- Die 41 Records sind die schweren Faelle, nicht die Gesamtmenge: von den
  Fehlerzellen liegen nur 33 hier, davon {obergrenze['erreichbar']} erreichbar.
- Die Regel bindet keinen Zeitpunkt in der Zelle und keine Gruppengroesse
  ausserhalb einer `(n = ...)`-Kopfzeile.
- Der Modus `ersetzen` kann TPs kosten; er ist getrennt ausgewiesen.
"""
    (HIER / "zeilenbindung_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")
    for e in ergebnisse:
        print(
            f"{e['gruppe_modus']:7s} {e['modus']:9s} gebunden {e['gebunden']:2d}/41 | "
            f"neue TP {e['neue_tp']:2d} (erreichbar {e['neu_erreichbar']:2d}) | "
            f"TP {e['vorher']['tp']}->{e['nachher']['tp']} FP {e['vorher']['fp']}->{e['nachher']['fp']} "
            f"FN {e['vorher']['fn']}->{e['nachher']['fn']} | TP-Verlust {e['tp_verlust']}"
        )
    print(f"Record 30: streng {record30['streng']['goldtreffer']}/6, erstes {r30e['goldtreffer']}/6 "
          f"(Gruppe {r30e['gruppe']}, Block {r30e['block']})")
    print(f"Erreichbar: {obergrenze['erreichbar']} von {obergrenze['zellen']} Fehlerzellen der Auswahl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
