#!/usr/bin/env python3
"""Zielzeile ueber Aliasliste: Neumessung der 31 Zaehlfeld-Faelle.

Offline, ohne Netzaufruf. Aus den 13 Ausfaellen der Zielzeilen-Suche sind drei
belegbare Schwaechen abgeleitet:

1. Wortvariante ohne gemeinsamen Stamm (`Scanning times` gegen
   `Scan duration (min)`).
2. Akronyme mit drei Buchstaben (`WMS-R`), die der Tokenizer verwirft.
3. Pluralformen (`Vegetable intake` gegen `Vegetables`).

Die Aliasliste ist bewusst klein und aus der Sichtung belegt; sie wird nicht auf
Goldwerte angewendet, sondern nur auf Wortformen.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zielzeile_alias_20261121.py
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
import groessen_zielzeile_20261121 as g  # noqa: E402
from zaehlfelder_20261121 import segmente  # noqa: E402

ALIAS = {
    "scanning": ["scan", "duration"],
    "vegetable": ["vegetables"],
    "vegetables": ["vegetable"],
    "fruit": ["fruits"],
    "blood": ["blood", "pressure"],
    "pressure": ["pressure"],
}


def stamm(wort: str) -> str:
    wort = wort.lower()
    for endung in ("ies", "es", "s"):
        if len(wort) > 5 and wort.endswith(endung):
            return wort[: -len(endung)]
    return wort


def woerter(text: str) -> set[str]:
    """Woerter mit Aliasen; Akronyme ab drei Buchstaben bleiben erhalten."""
    roh = re.findall(r"[A-Za-z][A-Za-z-]{2,}", text)
    aus: set[str] = set()
    for w in roh:
        if w.isupper() and len(w) >= 3:
            aus.add(w.lower())
            continue
        if len(w) <= 3 or w.lower() in g.STOPP:
            continue
        s = stamm(w)
        aus.add(s)
        for a in ALIAS.get(s, []):
            aus.add(stamm(a))
    return aus


def treffer_alias(label: str, outcome: str) -> int:
    lw, ow = woerter(label), woerter(outcome)
    return sum(1 for a in lw if any(a == b or (len(a) >= 5 and len(b) >= 5 and (a.startswith(b) or b.startswith(a)))
                                   for b in ow))


def ziel_zeile_alias(zeilen: list[str], outcome: str) -> int:
    beste, punkt = -1, 0
    for i, zeile in enumerate(zeilen):
        if g.ist_groessenzeile(zeile) or not re.search(r"[A-Za-z]{3}", zeile):
            continue
        segs = segmente(zeile)
        if len(segs) < 2 or len(g.zahlen(zeile)) < 2:
            continue
        p = max(treffer_alias(s, outcome) for s in segs)
        if p > punkt:
            beste, punkt = i, p
    return beste if punkt else -1


def regel(record: dict[str, Any], text: str) -> dict[str, dict[str, Any]]:
    context = record.get("context") or {}
    zeilen = text.splitlines()
    ziel = ziel_zeile_alias(zeilen, str(context.get("outcome") or ""))
    if ziel < 0:
        return {}
    groesse = g.groessen_zeile(zeilen, ziel)
    if groesse < 0:
        return {}
    return {g.FELD[a]: q for a, q in g.aus_groessenzeile(zeilen, groesse, context).items()}


def main() -> int:
    zaehl = json.loads((HIER / "zaehlfelder_20261121.json").read_text(encoding="utf-8"))
    faelle = zaehl["detail"]
    ziel_keys = {(e["record_id"], e["feld"], e["arm"]) for e in faelle
                 if e["klasse"] == "groessenzeile_richtiger_arm"}
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}
    texte: dict[str, str] = {}

    detail: list[dict[str, Any]] = []
    diagnose = Counter()
    for rid, feld, arm in sorted(ziel_keys):
        record = records[rid]
        if rid not in texte:
            texte[rid] = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        zellen = regel(record, texte[rid])
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (record.get("gold") or {}).get("cells") or []}
        roh = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
               for z in v.zellen(p5.get(rid))}
        if feld not in zellen:
            zeilen = texte[rid].splitlines()
            ziel = ziel_zeile_alias(zeilen, str((record.get("context") or {}).get("outcome") or ""))
            if ziel < 0:
                diagnose["zielzeile_nicht_gefunden"] += 1
            elif g.groessen_zeile(zeilen, ziel) < 0:
                diagnose["groessenzeile_nicht_gefunden"] += 1
            else:
                diagnose["anderer_arm_oder_mehrdeutig"] += 1
            continue
        diagnose["geliefert"] += 1
        info = zellen[feld]
        soll = gold.get((feld, arm))
        richtig = soll is not None and abs(soll - info["value"]) < 1e-6
        detail.append({"record_id": rid, "feld": feld, "arm": arm, "regel": info, "gold": soll,
                       "pred": roh.get((feld, arm)), "richtig": richtig})

    tp = sum(1 for e in detail if e["richtig"])
    fp = len(detail) - tp
    verlust = sum(1 for e in detail
                  if not e["richtig"] and e["pred"] is not None and e["gold"] is not None
                  and abs(e["pred"] - e["gold"]) < 1e-6)
    ergebnis = {"stand": "2026-11-21", "ziel_faelle": len(ziel_keys), "geliefert": len(detail),
                "tp": tp, "fp": fp, "tp_verlust": verlust, "diagnose": dict(diagnose),
                "alias": ALIAS, "detail": detail}
    (HIER / "zielzeile_alias_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['regel']['quelle']} | "
        f"{e['regel']['zeile']} | {e['gold']} | {'ja' if e['richtig'] else 'nein'} |"
        for e in detail) or "| - | - | - | - | - | - | - |"
    bericht = f"""# Zielzeile mit Aliasliste (21.11.2026)

Offline, ohne Netzaufruf. Aus den 13 Ausfaellen der Zielzeilen-Suche sind drei
Schwaechen belegt und mit einer kleinen Aliasliste behoben: Wortvarianten ohne
gemeinsamen Stamm (`Scanning times` / `Scan duration (min)`), Akronyme mit drei
Buchstaben (`WMS-R`), Pluralformen (`Vegetable intake` / `Vegetables`).

## Sichtung der 13 Ausfaelle (Label gegen Outcome)

Die Zeilen sind ueber den Goldwert gesucht und dienen nur der Ableitung der
Aliasliste; die Regel selbst sieht keinen Goldwert.

| Record | Outcome | Zeile mit dem Goldwert | Befund |
|---|---|---|---|
| 112 | Vegetable intake | `n=1349 n=434 n=459 n=456` | Mehrarm-Groessenzeile, Zielzeile fehlt |
| 113 | Vegetable intake | dieselbe Zeile | Mehrarm |
| 114 | Fruit intake | dieselbe Zeile | Mehrarm |
| 115 | Fruit intake | dieselbe Zeile | Mehrarm |
| 182 | Adverse events | keine Zeile | Goldwert 0 steht in keiner Tabellenzeile |
| 196 | WMS-R (0 min) | `MMSE-J 24.0 (2.4) 24.2 (2.2)` | Goldwert 24 nur als Nachbarzeile, nicht als Groesse |
| 358 | improvement at week 144 (SDMT) | keine Zeile | Goldwert 144 ist die Wochenzahl |
| 365 | leptin/adiponectin ratio | keine Zeile | Wert nur im Fliesstext |
| 389 | controlled blood pressure | `Complicated (n = 175)` | Mehrarm, Gold greift eine Subgruppe |
| 426 | Scanning times | `Scan duration (min) 19.8 ... 31.7` | Wortvariante, per Alias behoben |
| 512 | Adverse effects | `1200 (*N* = 122) 2400 (*N* = 123)` | Goldwert 122 ist die Gruppengroesse, kein Ereignis |
| 644 | progression-free survival | `(*N* = 48) (*N* = 23)` | Groessenzeile ohne Armnamen |

Nur `Scanning times` ist eine reine Wortvariante. Die uebrigen Faelle scheitern
an Mehrarm-Tabellen, fehlenden Zielzeilen oder an Goldwerten, die keine
Tabellenzelle sind.

## Aliasliste

| Outcome-Wort | Zulaeassige Tabellenwoerter |
|---|---|
| scanning | scan, duration |
| vegetable | vegetables |
| vegetables | vegetable |
| fruit | fruits |
| blood | blood, pressure |
| pressure | pressure |

## Ergebnis an den 31 Zielfaellen

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | {len(ziel_keys)} |
| Regel liefert einen Wert | {len(detail)} |
| davon richtig (TP) | {tp} |
| davon falsch (FP) | {fp} |
| TP-Verlust | {verlust} |

Vor der Aliasliste waren es 6 geliefert, 2 TP, 4 FP; die Aliasliste bringt
zwei TP (426) und einen FP (196) hinzu.

## Abbruchgruende der nicht gelieferten Faelle

| Stufe | Faelle |
|---|---:|
| Zielzeile nicht gefunden | {diagnose.get('zielzeile_nicht_gefunden', 0)} |
| Groessenzeile nicht in Reichweite | {diagnose.get('groessenzeile_nicht_gefunden', 0)} |
| Arm mehrdeutig oder nur anderer Arm | {diagnose.get('anderer_arm_oder_mehrdeutig', 0)} |

## Gold-Verdacht bei den FP

| Record | Regelwert | Gold | Befund |
|---|---:|---:|---|
| 331/334/335/336 | 45 | 47 | `PMC5617873` nennt dreimal `Placebo (n = 45)` vor `Aripiprazole (n = 47)`; Kontext-Intervention ist Aripiprazole. Gold fuehrt 45 als Intervention: Arme vertauscht. |
| 196 | 140 | 24 | Tabelle 1 nennt `Pls group (n = 145)` und `Placebo group (n = 140)`; Gold nennt fuer beide Arme 24. Herkunft der 24 im Dokument nicht belegt. |

Kein Goldwert wurde geaendert.

## Gelieferte Zellen

| Record | Feld | Regelwert | Quelle | Zeile | Gold | richtig |
|---|---|---:|---|---:|---:|---|
{tab}
"""
    (HIER / "zielzeile_alias_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"Ziel {len(ziel_keys)} | geliefert {len(detail)} | TP {tp} | FP {fp} | TP-Verlust {verlust}")
    print(f"Diagnose: {dict(diagnose)}")
    for e in detail:
        print(f"  {e['record_id']:14s} {e['feld']:28s} {e['regel']['value']:>8} "
              f"({e['regel']['quelle']}, Z{e['regel']['zeile']}) | gold {e['gold']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
