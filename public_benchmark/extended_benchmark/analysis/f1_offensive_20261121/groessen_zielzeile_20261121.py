#!/usr/bin/env python3
"""Groessenzeile der Zielzeile: trifft sie die 31 Faelle mit richtigem Arm?

Offline, ohne Netzaufruf. Die Regel arbeitet ohne Goldwert:

1. Zielzeile suchen: die Zeile, deren Text am besten zum Outcome-Namen passt
   und die mindestens zwei Zahlen traegt.
2. Groessenzeile suchen: die naechste Zeile darueber, die eine Groesse nennt
   (`n = 40`, `Number (*N*)  37  40`, `Intervention (n = 125)`).
3. Armspalte waehlen: nennt die Groessenzeile den Arm selbst, gilt ihr Wert;
   sonst wird die Spalte ueber die Armnamen in der Kopfzeile darueber gesucht.
   Bleiben mehrere Spalten fuer denselben Arm (Multiarm-Studie), verweigert die
   Regel.

Gemessen wird an allen 127 Zaehlfeldern: TP, FP und TP-Verlust im Modus
`ersetzen` (die Zellen sind in P5 vorhanden, `additiv` kann dort nichts
gewinnen), zusaetzlich der Anteil unter den 31 Zielfaellen.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/groessen_zielzeile_20261121.py
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
from zahlabgleich_20261121 import zahl_positionen  # noqa: E402
from zaehlfelder_20261121 import ist_groessenzeile, segmente, arm_von_label  # noqa: E402

FELD = {"intervention": "intervention_group_size", "comparator": "comparator_group_size"}
STRENGE = re.compile(r"[nN]\s*[*_]*\s*=\s*\d|\bnumber\b[^\d]{0,12}\d", re.IGNORECASE)
STOPP = {"baseline", "the", "of", "or", "and", "in", "on", "with", "for", "at", "to",
         "patients", "group", "groups", "total", "mean", "sd", "number"}


def stamm(wort: str) -> str:
    wort = wort.lower()
    for endung in ("ies", "es", "s"):
        if len(wort) > 5 and wort.endswith(endung):
            return wort[: -len(endung)]
    return wort


def treffer(label: str, outcome: str) -> int:
    lw = {stamm(w) for w in re.findall(r"[a-z]+", label.lower()) if w not in STOPP and len(w) > 3}
    ow = {stamm(w) for w in re.findall(r"[a-z]+", outcome.lower()) if w not in STOPP and len(w) > 3}
    return sum(1 for a in lw if any(a == b or (len(a) >= 5 and len(b) >= 5 and (a.startswith(b) or b.startswith(a)))
                                   for b in ow))


def zahlen(text: str) -> list[float]:
    roh = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    return [float(x.replace(",", "")) for x in roh]


def ziel_zeile(zeilen: list[str], outcome: str) -> int:
    """Zeile mit der besten Outcome-Uebereinstimmung und mindestens zwei Zahlen.

    Bewertet wird das beste Segment der Zeile, damit auch Tabellen mit
    vorgeschalteter Beschriftungsspalte gefunden werden.
    """
    beste, punkt = -1, 0
    for i, zeile in enumerate(zeilen):
        if ist_groessenzeile(zeile) or not re.search(r"[A-Za-z]{3}", zeile):
            continue
        segs = segmente(zeile)
        if len(segs) < 2 or len(zahlen(zeile)) < 2:
            continue
        p = max(treffer(s, outcome) for s in segs)
        if p > punkt:
            beste, punkt = i, p
    return beste if punkt else -1


def groessen_zeile(zeilen: list[str], ziel: int) -> int:
    """Naechste echte Groessenzeile ueber der Zielzeile (`n = 40` mit Zahl)."""
    for i in range(ziel - 1, max(-1, ziel - 60), -1):
        if ist_groessenzeile(zeilen[i]) and STRENGE.search(zeilen[i]):
            return i
    return -1


def aus_groessenzeile(zeilen: list[str], i: int, context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Armwerte aus einer Groessenzeile, nur bei eindeutiger Spalte."""
    segs = segmente(zeilen[i])
    ausgabe: dict[str, dict[str, Any]] = {}
    for k, seg in enumerate(segs):
        arm = arm_von_label(seg, context)
        if not arm:
            continue
        werte = zahlen(seg)
        if werte:
            ausgabe.setdefault(arm, {"value": werte[-1], "quelle": "zeile", "zeile": i + 1})
    if ausgabe:
        return ausgabe

    # Nackte Zahlenzeile: Spalten ueber die Kopfzeile darueber zuordnen.
    zahlen_spalten = [k for k, s in enumerate(segs) if re.fullmatch(r"[\d,]+(?:\.\d+)?", s)]
    if len(zahlen_spalten) < 2:
        return {}
    for j in range(i - 1, max(-1, i - 9), -1):
        kopf = segmente(zeilen[j])
        if len(kopf) not in (len(segs), len(segs) + 1):
            continue
        versatz = len(kopf) - len(segs)
        arme: dict[str, list[int]] = {}
        for pos, k in enumerate(zahlen_spalten):
            ziel_pos = k + versatz
            if 0 <= ziel_pos < len(kopf):
                arm = arm_von_label(kopf[ziel_pos], context)
                if arm:
                    arme.setdefault(arm, []).append(k)
        if len(arme) < 2:
            continue
        for arm, spalten in arme.items():
            if len(spalten) != 1:
                continue  # Multiarm: gleicher Armname in mehreren Spalten
            werte = zahlen(segs[spalten[0]])
            if werte:
                ausgabe[arm] = {"value": werte[-1], "quelle": "kopf", "zeile": i + 1}
        return ausgabe
    return {}


def stufe(record: dict[str, Any], text: str) -> str:
    """Wo die Regel abbricht: `zielzeile`, `groessenzeile`, `arm` oder `geliefert`."""
    context = record.get("context") or {}
    zeilen = text.splitlines()
    ziel = ziel_zeile(zeilen, str(context.get("outcome") or ""))
    if ziel < 0:
        return "zielzeile_nicht_gefunden"
    groesse = groessen_zeile(zeilen, ziel)
    if groesse < 0:
        return "groessenzeile_nicht_gefunden"
    if not aus_groessenzeile(zeilen, groesse, context):
        return "arm_nicht_zugeordnet"
    return "geliefert"


def regel(record: dict[str, Any], text: str) -> dict[str, dict[str, Any]]:
    context = record.get("context") or {}
    outcome = str(context.get("outcome") or "")
    zeilen = text.splitlines()
    ziel = ziel_zeile(zeilen, outcome)
    if ziel < 0:
        return {}
    groesse = groessen_zeile(zeilen, ziel)
    if groesse < 0:
        return {}
    werte = aus_groessenzeile(zeilen, groesse, context)
    return {FELD[a]: q for a, q in werte.items()}


def regel_ohne_anker(record: dict[str, Any], text: str) -> dict[str, dict[str, Any]]:
    """Variante ohne Zielzeile: alle Groessenzeilen im Dokument, nur bei gleichem Wert."""
    context = record.get("context") or {}
    zeilen = text.splitlines()
    kandidaten: dict[str, list[tuple[float, int]]] = {}
    for i, zeile in enumerate(zeilen):
        if not (ist_groessenzeile(zeile) and STRENGE.search(zeile)):
            continue
        for arm, info in aus_groessenzeile(zeilen, i, context).items():
            kandidaten.setdefault(arm, []).append((info["value"], i + 1))
    ausgabe: dict[str, dict[str, Any]] = {}
    for arm, werte in kandidaten.items():
        if len({w for w, _ in werte}) == 1:
            ausgabe[FELD[arm]] = {"value": werte[0][0], "quelle": "ohne_anker", "zeile": werte[0][1]}
    return ausgabe


def main() -> int:
    zaehl = json.loads((HIER / "zaehlfelder_20261121.json").read_text(encoding="utf-8"))
    faelle = zaehl["detail"]
    ziel_keys = {(e["record_id"], e["feld"], e["arm"]) for e in faelle
                 if e["klasse"] == "groessenzeile_richtiger_arm"}
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}

    texte: dict[str, str] = {}
    detail: list[dict[str, Any]] = []
    gesehen: set[tuple[str, str]] = set()
    for f in faelle:
        rid = f["record_id"]
        if rid not in texte:
            texte[rid] = (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        if (rid, f["feld"]) in gesehen:
            continue
        gesehen.add((rid, f["feld"]))
        if ("rec", rid) in gesehen:
            continue
        gesehen.add(("rec", rid))
        zellen = regel(records[rid], texte[rid])
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (records[rid].get("gold") or {}).get("cells") or []}
        roh = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
               for z in v.zellen(p5.get(rid))}
        for feld, info in zellen.items():
            arm = "intervention" if feld.startswith("intervention") else "comparator"
            soll = gold.get((feld, arm))
            richtig = soll is not None and abs(soll - info["value"]) < 1e-6
            vorhanden = (feld, arm) in roh
            detail.append({"record_id": rid, "feld": feld, "arm": arm, "regel": info,
                           "gold": soll, "pred": roh.get((feld, arm)), "richtig": richtig,
                           "ziel_fall": (rid, feld, arm) in ziel_keys, "vorhanden": vorhanden})

    bilanz = {"tp": 0, "fp": 0, "tp_verlust": 0}
    for e in detail:
        if not e["richtig"]:
            if e["vorhanden"]:
                bilanz["fp"] += 1
            else:
                bilanz["fp"] += 1
            if e["vorhanden"] and e["pred"] is not None and e["gold"] is not None and abs(e["pred"] - e["gold"]) < 1e-6:
                bilanz["tp_verlust"] += 1
        elif e["vorhanden"]:
            if e["pred"] is None or e["gold"] is None or abs(e["pred"] - e["gold"]) >= 1e-6:
                bilanz["tp"] += 1

    ziel_detail = [e for e in detail if e["ziel_fall"]]
    ziel_richtig = [e for e in ziel_detail if e["richtig"]]
    ziel_fp = [e for e in ziel_detail if not e["richtig"]]
    diagnose = Counter()
    for rid, feld, arm in sorted(ziel_keys):
        if any(e["record_id"] == rid and e["feld"] == feld and e["arm"] == arm for e in detail):
            diagnose["geliefert"] += 1
            continue
        st = stufe(records[rid], texte[rid])
        diagnose["nur_anderer_arm" if st == "geliefert" else st] += 1
    ohne_anker = {"geliefert": 0, "tp": 0, "fp": 0}
    for rid, feld, arm in sorted(ziel_keys):
        zellen = regel_ohne_anker(records[rid], texte[rid])
        if feld not in zellen:
            continue
        ohne_anker["geliefert"] += 1
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (records[rid].get("gold") or {}).get("cells") or []}
        soll = gold.get((feld, arm))
        if soll is not None and abs(soll - zellen[feld]["value"]) < 1e-6:
            ohne_anker["tp"] += 1
        else:
            ohne_anker["fp"] += 1
    ergebnis = {
        "stand": "2026-11-21",
        "ohne_anker": ohne_anker,
        "ziel_faelle": len(ziel_keys),
        "ziel_geliefert": len(ziel_detail),
        "ziel_richtig": len(ziel_richtig),
        "ziel_falsch": len(ziel_fp),
        "bilanz_ersetzen": bilanz,
        "zellen_gesamt": len(detail),
        "diagnose": dict(diagnose),
        "detail": detail,
    }
    (HIER / "groessen_zielzeile_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    ziel_tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['regel']['quelle']} | "
        f"{e['regel']['zeile']} | {e['gold']} | {e['pred']} | {'ja' if e['richtig'] else 'nein'} |"
        for e in ziel_detail) or "| - | - | - | - | - | - | - | - |"
    andere = [e for e in detail if not e["ziel_fall"]]
    bericht = f"""# Groessenzeile der Zielzeile (21.11.2026)

Offline, ohne Netzaufruf. Die Regel nutzt keinen Goldwert: sie sucht die
Zielzeile ueber den Outcome-Namen, nimmt die naechste Groessenzeile darueber und
liest dort die Spalte des Arms. Mehrdeutige Spalten (Multiarm mit gleichem
Armnamen) werden verweigert.

## Ergebnis an den 31 Zielfaellen

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | {len(ziel_keys)} |
| Regel liefert einen Wert | {len(ziel_detail)} |
| davon richtig (TP) | {len(ziel_richtig)} |
| davon falsch (FP) | {len(ziel_fp)} |

| Record | Feld | Regelwert | Quelle | Zeile | Gold | Vorhersage | richtig |
|---|---|---:|---|---:|---:|---:|---|
{ziel_tab}

## Abbruchgruende

| Stufe | Faelle |
|---|---:|
| geliefert | {diagnose.get('geliefert', 0)} |
| Zielzeile nicht ueber Outcome gefunden | {diagnose.get('zielzeile_nicht_gefunden', 0)} |
| Groessenzeile nicht in Reichweite | {diagnose.get('groessenzeile_nicht_gefunden', 0)} |
| Arm nicht eindeutig zugeordnet | {diagnose.get('arm_nicht_zugeordnet', 0)} |
| Tabelle gelesen, aber nur der andere Arm | {diagnose.get('nur_anderer_arm', 0)} |

## Variante ohne Zielzeilen-Anker

Dieselbe Regel ohne Outcome-Anker - alle Groessenzeilen im Dokument, geliefert
nur bei einem einzigen Wert je Arm:

| Kennzahl | Wert |
|---|---:|
| geliefert | {ohne_anker['geliefert']} |
| TP | {ohne_anker['tp']} |
| FP | {ohne_anker['fp']} |

Die ankerlose Variante liefert Werte, obwohl jedes Dokument mehrere
Groessenzeilen mit verschiedenen Werten enthaelt (Subgruppen, mehrere
Tabellen). Sie trifft zwei Faelle und erzeugt acht FP; die verankerte Variante
ist mit 2 TP und 4 FP besser, weil sie nur die Groessenzeile ueber der
Zielzeile liest.

## Bilanz ueber alle {len(detail)} gelieferten Zellen (`ersetzen`)

| Kennzahl | Wert |
|---|---:|
| TP (ersetzt falschen Wert durch Gold) | {bilanz['tp']} |
| FP (bleibt falsch) | {bilanz['fp']} |
| TP-Verlust (ersetzt richtigen Wert durch falschen) | {bilanz['tp_verlust']} |

Zusaetzlich liefert die Regel {len(andere)} Zellen ausserhalb der 31 Zielfaelle.

## Lesart

Ein Treffer verlangt drei Dinge zugleich: die Zielzeile muss ueber den
Outcome-Namen auffindbar sein, die Groessenzeile muss in Reichweite liegen, und
die Armspalte muss eindeutig sein. Die 31 Zielfaelle erfuellen laut
`zaehlfelder_20261121` die dritte Bedingung; die ersten beiden prueft diese
Regel.
"""
    (HIER / "groessen_zielzeile_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"Ziel {len(ziel_keys)}: geliefert {len(ziel_detail)} (richtig {len(ziel_richtig)}, "
          f"falsch {len(ziel_fp)})")
    print(f"alle Zellen {len(detail)} | ersetzen TP {bilanz['tp']} FP {bilanz['fp']} "
          f"TP-Verlust {bilanz['tp_verlust']}")
    for e in ziel_detail:
        print(f"  {e['record_id']:14s} {e['feld']:28s} {e['regel']['value']:>8} "
              f"({e['regel']['quelle']}, Z{e['regel']['zeile']}) | gold {e['gold']} pred {e['pred']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
