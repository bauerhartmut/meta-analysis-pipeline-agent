#!/usr/bin/env python3
"""Ereigniszaehler mit Zeitpunktzuordnung: bringen die vier lesbaren Faelle TP?

Offline, ohne Netzaufruf. Die Regel sucht in den vier Records die Tabelle, deren
Zeilenbeschriftung zum Outcome-Namen passt, und liest dort den Zielzeitpunkt.

Zwei Varianten:

* `zaehler` - nur Tabellen mit `n`-Spalte und `(%)`-Spalte je Zeitpunkt, also
  echte Ereigniszaehler.
* `prozent` - zusaetzlich Prozentzeilen (`Diabetes, %   52   59`) aus
  Baseline-Tabellen, in denen Gold ebenfalls einen Wert fuehrt.

Der Zielzeitpunkt folgt der Record-Regel: letzter berichteter Zeitpunkt.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zaehler_zeitpunkt_20261121.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from ereignisse_20261121 import arm_allgemein  # noqa: E402
from zaehlfelder_20261121 import segmente  # noqa: E402

FELD = {"intervention": "intervention_events", "comparator": "comparator_events"}
ZEIT = re.compile(r"\b(?:\d+\s*(?:weeks?|months?|days?|years?)|baseline)\b", re.IGNORECASE)
STOPP = {
    "baseline", "the", "of", "or", "and", "in", "on", "with", "for", "at", "to",
    "patients", "intake", "use", "rate", "mean", "sd",
}


def stamm(wort: str) -> str:
    wort = wort.lower()
    for endung in ("ies", "es", "s"):
        if len(wort) > 5 and wort.endswith(endung):
            return wort[: -len(endung)]
    return wort


def treffer(label: str, outcome: str) -> int:
    """Zahl der gemeinsamen Wortstaemme zwischen Zeilenlabel und Outcome."""
    lw = {stamm(w) for w in re.findall(r"[a-z]+", label.lower()) if w not in STOPP and len(w) > 3}
    ow = {stamm(w) for w in re.findall(r"[a-z]+", outcome.lower()) if w not in STOPP and len(w) > 3}
    gemeinsam = 0
    for a in lw:
        for b in ow:
            if a == b or (len(a) >= 5 and len(b) >= 5 and (a.startswith(b) or b.startswith(a))):
                gemeinsam += 1
                break
    return gemeinsam


def ziel_spalte(zeitpunkte: list[str], ziel: str) -> int:
    z = (ziel or "").lower()
    if z:
        exakt = [i for i, w in enumerate(zeitpunkte) if w.lower() == z]
        if len(exakt) == 1:
            return exakt[0]
    return len(zeitpunkte) - 1


def tabellen(zeilen: list[str], context: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle Tabellen mit Armbezug: Bloecke, Zeitpunkte und Zellwerte."""
    gefunden: list[dict[str, Any]] = []
    for i, zeile in enumerate(zeilen):
        zeitpunkte = [" ".join(m.group(0).split()) for m in ZEIT.finditer(zeile)]
        segs = segmente(zeile)
        arm_spalten = [(k, arm_allgemein(s, context)) for k, s in enumerate(segs) if arm_allgemein(s, context)]
        if len(arm_spalten) >= 2 and len(segs) >= 3:
            zeilen_daten = []
            for j in range(i + 1, min(len(zeilen), i + 40)):
                reihe = segmente(zeilen[j])
                if len(reihe) < 3:
                    continue
                if ZEIT.search(zeilen[j]) and len(ZEIT.findall(zeilen[j])) >= 2:
                    break
                zahlen = [float(s) for s in reihe[1:] if re.fullmatch(r"\d+(?:\.\d+)?", s)]
                if len(zahlen) < 2:
                    continue
                zeilen_daten.append({"label": reihe[0], "zahlen": zahlen})
            if zeilen_daten:
                gefunden.append({"art": "prozent", "kopf_zeile": i + 1,
                                 "arme": [a for _, a in arm_spalten], "zeilen": zeilen_daten})
        if len(zeitpunkte) >= 2:
            pct = None
            for j in range(i + 1, min(len(zeilen), i + 5)):
                if re.search(r"\(\s*%\s*\)|\(%\)", zeilen[j]):
                    pct = j
                    break
            if pct is None:
                continue
            block = ""
            bloecke: list[dict[str, Any]] = []
            for k in range(pct + 1, min(len(zeilen), pct + 40)):
                reihe = segmente(zeilen[k])
                if not reihe:
                    continue
                if len(ZEIT.findall(zeilen[k])) >= 2:
                    break
                if len(reihe) == 1:
                    block = reihe[0]
                    continue
                arm = arm_allgemein(reihe[0], context)
                if not arm:
                    continue
                zahlen = [float(s) for s in reihe[1:] if re.fullmatch(r"\d+(?:\.\d+)?", s)]
                prozente = [s for s in reihe[1:] if re.fullmatch(r"\(\s*\d+(?:\.\d+)?\s*%?\s*\)\**", s)]
                if len(zahlen) < len(zeitpunkte) or len(prozente) < len(zeitpunkte):
                    continue
                bloecke.append({"block": block, "arm": arm,
                                "werte": zahlen[: len(zeitpunkte)]})
            if bloecke:
                gefunden.append({"art": "zaehler", "kopf_zeile": i + 1,
                                 "zeitpunkte": zeitpunkte, "bloecke": bloecke})
    return gefunden


def regel(record: dict[str, Any], text: str, mit_prozent: bool) -> dict[str, dict[str, Any]]:
    context = record.get("context") or {}
    outcome = str(context.get("outcome") or "")
    ziel = str((record.get("timepoint") or {}).get("target") or "")
    zeilen = text.splitlines()
    beste: dict[str, Any] | None = None
    bester_punkt = 0
    for t in tabellen(zeilen, context):
        if t["art"] == "zaehler":
            for b in t["bloecke"]:
                punkt = treffer(b["block"], outcome)
                if punkt > bester_punkt:
                    bester_punkt, beste = punkt, {"tab": t, "block": b["block"]}
        elif mit_prozent:
            for z in t["zeilen"]:
                punkt = treffer(z["label"], outcome)
                if punkt > bester_punkt:
                    bester_punkt, beste = punkt, {"tab": t, "zeile": z["label"]}
    if beste is None or bester_punkt == 0:
        return {}
    t = beste["tab"]
    if t["art"] == "zaehler":
        spalte = ziel_spalte(t["zeitpunkte"], ziel)
        ausgabe: dict[str, dict[str, Any]] = {}
        for b in t["bloecke"]:
            if b["block"] != beste["block"]:
                continue
            ausgabe[b["arm"]] = {"value": b["werte"][spalte], "quelle": "zaehler",
                                 "spalte": t["zeitpunkte"][spalte], "zeile": t["kopf_zeile"]}
        return {FELD[a]: q for a, q in ausgabe.items()}
    for z in t["zeilen"]:
        if z["label"] != beste["zeile"]:
            continue
        if len(z["zahlen"]) < len(t["arme"]):
            return {}
        return {FELD[a]: {"value": w, "quelle": "prozent", "spalte": "Prozentzeile",
                          "zeile": t["kopf_zeile"]}
                for a, w in zip(t["arme"], z["zahlen"])}
    return {}


def main() -> int:
    ereignisse = json.loads((HIER / "ereignisse_20261121.json").read_text(encoding="utf-8"))
    ziel_faelle = [e for e in ereignisse["detail"] if e["klasse"] == "zaehler_prozent_in_kopfzeile"]
    ids = sorted({e["record_id"] for e in ziel_faelle})
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}

    detail: list[dict[str, Any]] = []
    summen: dict[str, dict[str, int]] = {}
    for variante, mit_prozent in (("zaehler", False), ("prozent", True)):
        bilanz = {"tp": 0, "fp": 0, "tp_verlust": 0, "zellen": 0}
        for rid in ids:
            record = records[rid]
            text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
            zellen = regel(record, text, mit_prozent)
            gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                    for z in (record.get("gold") or {}).get("cells") or []}
            roh = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                   for z in v.zellen(p5.get(rid))}
            for feld, info in zellen.items():
                key = (feld, "intervention" if feld.startswith("intervention") else "comparator")
                soll = gold.get(key)
                richtig = soll is not None and abs(soll - info["value"]) < 1e-6
                bilanz["zellen"] += 1
                if key not in roh:
                    bilanz["tp" if richtig else "fp"] += 1
                else:
                    vorher_richtig = soll is not None and abs(roh[key] - soll) < 1e-6
                    if vorher_richtig and not richtig:
                        bilanz["tp_verlust"] += 1
                    if richtig and not vorher_richtig:
                        bilanz["tp"] += 1
                    if not richtig:
                        bilanz["fp"] += 1
                detail.append({"variante": variante, "record_id": rid, "feld": feld,
                               "regel": info, "gold": soll, "richtig": richtig,
                               "schon_vorhanden": key in roh})
        summen[variante] = bilanz

    ergebnis = {"stand": "2026-11-21", "ziel_records": ids, "ziel_faelle": len(ziel_faelle),
                "summen": summen, "detail": detail}
    (HIER / "zaehler_zeitpunkt_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    def tab(variante: str) -> str:
        return "\n".join(
            f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['regel']['quelle']} | "
            f"{e['regel'].get('spalte', '-')} | {e['gold'] if e['gold'] is not None else '-'} | "
            f"{'ja' if e['richtig'] else 'nein'} |"
            for e in detail if e["variante"] == variante) or "| - | - | - | - | - | - | - |"

    bericht = f"""# Ereigniszaehler mit Zeitpunktzuordnung (21.11.2026)

Offline, ohne Netzaufruf. Regel: Tabelle suchen, deren Zeilenbeschriftung zum
Outcome-Namen passt, Arm aus Zeile oder Kopfzeile, Spalte des Zielzeitpunkts
(Record-Regel: letzter berichteter Zeitpunkt). Zwei Varianten, weil die drei
Baseline-Faelle keine Zaehler, sondern Prozentwerte sind.

## Ergebnis

| Variante | Zellen | TP | FP | TP-Verlust |
|---|---:|---:|---:|---:|
| `zaehler` (nur `n` + `(%)`) | {summen['zaehler']['zellen']} | {summen['zaehler']['tp']} | {summen['zaehler']['fp']} | {summen['zaehler']['tp_verlust']} |
| `prozent` (auch Prozentzeilen) | {summen['prozent']['zellen']} | {summen['prozent']['tp']} | {summen['prozent']['fp']} | {summen['prozent']['tp_verlust']} |

## Zellen, Variante `zaehler`

| Record | Feld | Regelwert | Quelle | Spalte | Gold | richtig |
|---|---|---:|---|---|---:|---|
{tab('zaehler')}

## Zellen, Variante `prozent`

| Record | Feld | Regelwert | Quelle | Spalte | Gold | richtig |
|---|---|---:|---|---|---:|---|
{tab('prozent')}

## Lesart

Nur `yun2024:190` ist ein echter Zaehler: Arm in der Zeile (`Intervention`,
`TAU`), Zeitpunkt in der Spalte (`Baseline`, 3, 6, 12 Monate), je Zelle `n` und
`(%)`. Die Zielspalte ist der letzte Zeitpunkt, dort steht 52/51 - beide Gold.
Die drei uebrigen Faelle sind Prozentwerte aus Baseline-Tabellen ohne
Zeitpunktachse; ihre Goldpaare stehen in keiner Tabellenzeile, die
Outcome-Zeile liefert andere Zahlen (etwa `Diabetes, %  52  59` bei Gold 35/33).
Die Variante `prozent` zahlt diese Fehlgriffe als FP.
"""
    (HIER / "zaehler_zeitpunkt_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    for variante in ("zaehler", "prozent"):
        b = summen[variante]
        print(f"{variante:8s} Zellen {b['zellen']} TP {b['tp']} FP {b['fp']} TP-Verlust {b['tp_verlust']}")
    for e in detail:
        print(f"  {e['variante']:8s} {e['record_id']:14s} {e['feld']:24s} {e['regel']['value']:>6} "
              f"({e['regel']['quelle']}, {e['regel'].get('spalte', '-')}) | gold {e['gold']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
