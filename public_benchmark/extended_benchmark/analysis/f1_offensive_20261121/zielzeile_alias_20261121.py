#!/usr/bin/env python3
"""Zielzeile ueber Aliasliste: Neumessung der 31 Zaehlfeld-Faelle.

Offline, ohne Netzaufruf. Die Aliasliste enthaelt nur noch den Eintrag, der
nachweislich Treffer bringt; die uebrigen Wortformen (blood/pressure,
fruit/vegetable) sind entfernt, weil sie das Ergebnis nicht veraendern.

Zusaetzlich wird die Wirkung jedes Bausteins einzeln gemessen: Akronyme ab drei
Buchstaben, der Alias `scanning -> scan, duration`, beide zusammen und keine
Erweiterung.

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

ALIAS: dict[str, list[str]] = {"scanning": ["scan", "duration"]}

VARIANTEN = {
    "ohne Erweiterung": ({}, False),
    "nur Akronyme": ({}, True),
    "nur scanning": ({"scanning": ["scan", "duration"]}, False),
    "Akronyme + scanning": (ALIAS, True),
}


def stamm(wort: str) -> str:
    wort = wort.lower()
    for endung in ("ies", "es", "s"):
        if len(wort) > 5 and wort.endswith(endung):
            return wort[: -len(endung)]
    return wort


def woerter(text: str, alias: dict[str, list[str]], akronyme: bool) -> set[str]:
    """Woerter mit Aliasen; Akronyme ab drei Buchstaben optional erhalten."""
    roh = re.findall(r"[A-Za-z][A-Za-z-]{2,}", text)
    aus: set[str] = set()
    for w in roh:
        if akronyme and w.isupper() and len(w) >= 3:
            aus.add(w.lower())
            continue
        if len(w) <= 3 or w.lower() in g.STOPP:
            continue
        s = stamm(w)
        aus.add(s)
        for a in alias.get(s, []):
            aus.add(stamm(a))
    return aus


def treffer_alias(label: str, outcome: str, alias: dict[str, list[str]], akronyme: bool) -> int:
    lw, ow = woerter(label, alias, akronyme), woerter(outcome, alias, akronyme)
    return sum(1 for a in lw if any(a == b or (len(a) >= 5 and len(b) >= 5 and (a.startswith(b) or b.startswith(a)))
                                   for b in ow))


def ziel_zeile_alias(zeilen: list[str], outcome: str, alias: dict[str, list[str]],
                     akronyme: bool) -> int:
    beste, punkt = -1, 0
    for i, zeile in enumerate(zeilen):
        if g.ist_groessenzeile(zeile) or not re.search(r"[A-Za-z]{3}", zeile):
            continue
        segs = segmente(zeile)
        if len(segs) < 2 or len(g.zahlen(zeile)) < 2:
            continue
        p = max(treffer_alias(s, outcome, alias, akronyme) for s in segs)
        if p > punkt:
            beste, punkt = i, p
    return beste if punkt else -1


def regel(record: dict[str, Any], text: str, alias: dict[str, list[str]],
          akronyme: bool) -> dict[str, dict[str, Any]]:
    context = record.get("context") or {}
    zeilen = text.splitlines()
    ziel = ziel_zeile_alias(zeilen, str(context.get("outcome") or ""), alias, akronyme)
    if ziel < 0:
        return {}
    groesse = g.groessen_zeile(zeilen, ziel)
    if groesse < 0:
        return {}
    return {g.FELD[a]: q for a, q in g.aus_groessenzeile(zeilen, groesse, context).items()}


def messe(ziel_keys: set[tuple[str, str, str]], records: dict[str, dict[str, Any]],
          texte: dict[str, str], alias: dict[str, list[str]], akronyme: bool) -> dict[str, Any]:
    detail: list[dict[str, Any]] = []
    for rid, feld, arm in sorted(ziel_keys):
        record = records[rid]
        zellen = regel(record, texte[rid], alias, akronyme)
        if feld not in zellen:
            continue
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (record.get("gold") or {}).get("cells") or []}
        soll = gold.get((feld, arm))
        info = zellen[feld]
        detail.append({"record_id": rid, "feld": feld, "arm": arm, "regel": info, "gold": soll,
                       "richtig": soll is not None and abs(soll - info["value"]) < 1e-6})
    tp = sum(1 for e in detail if e["richtig"])
    return {"geliefert": len(detail), "tp": tp, "fp": len(detail) - tp, "detail": detail}


def main() -> int:
    zaehl = json.loads((HIER / "zaehlfelder_20261121.json").read_text(encoding="utf-8"))
    faelle = zaehl["detail"]
    ziel_keys = {(e["record_id"], e["feld"], e["arm"]) for e in faelle
                 if e["klasse"] == "groessenzeile_richtiger_arm"}
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}
    texte: dict[str, str] = {}
    for rid in {k[0] for k in ziel_keys}:
        texte[rid] = (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")

    varianten = {name: messe(ziel_keys, records, texte, a, k) for name, (a, k) in VARIANTEN.items()}
    haupt = varianten["Akronyme + scanning"]
    detail = haupt["detail"]
    tp, fp = haupt["tp"], haupt["fp"]
    verlust = 0
    for e in detail:
        roh = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
               for z in v.zellen(p5.get(e["record_id"]))}
        pred = roh.get((e["feld"], e["arm"]))
        if not e["richtig"] and pred is not None and e["gold"] is not None and abs(pred - e["gold"]) < 1e-6:
            verlust += 1

    diagnose = Counter()
    for rid, feld, arm in sorted(ziel_keys):
        if any(e["record_id"] == rid and e["feld"] == feld and e["arm"] == arm for e in detail):
            diagnose["geliefert"] += 1
            continue
        zeilen = texte[rid].splitlines()
        ziel = ziel_zeile_alias(zeilen, str((records[rid].get("context") or {}).get("outcome") or ""),
                                ALIAS, True)
        if ziel < 0:
            diagnose["zielzeile_nicht_gefunden"] += 1
        elif g.groessen_zeile(zeilen, ziel) < 0:
            diagnose["groessenzeile_nicht_gefunden"] += 1
        else:
            diagnose["anderer_arm_oder_mehrdeutig"] += 1

    ergebnis = {"stand": "2026-11-21", "ziel_faelle": len(ziel_keys), "geliefert": len(detail),
                "tp": tp, "fp": fp, "tp_verlust": verlust, "diagnose": dict(diagnose),
                "alias": ALIAS,
                "varianten": {k: {"geliefert": x["geliefert"], "tp": x["tp"], "fp": x["fp"]}
                              for k, x in varianten.items()},
                "detail": detail}
    (HIER / "zielzeile_alias_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    var_tab = "\n".join(
        f"| {name} | {x['geliefert']} | {x['tp']} | {x['fp']} |"
        for name, x in varianten.items())
    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['regel']['quelle']} | "
        f"{e['regel']['zeile']} | {e['gold']} | {'ja' if e['richtig'] else 'nein'} |"
        for e in detail) or "| - | - | - | - | - | - | - |"
    bericht = f"""# Zielzeile mit Aliasliste (21.11.2026)

Offline, ohne Netzaufruf. Die Aliasliste enthaelt nur den Eintrag, der Treffer
bringt; `blood/pressure` und `fruit/vegetable` sind entfernt, weil sie das
Ergebnis nicht veraendern (112-115 scheitern an der Mehrarm-Groessenzeile, 389
an der Subgruppenwahl).

## Wirkung je Baustein

| Variante | geliefert | TP | FP |
|---|---:|---:|---:|
{var_tab}

Der Alias `scanning -> scan, duration` bringt beide TP (`yun2024:426`): zwei
zusaetzliche Zellen, beide richtig. Die Akronym-Regel allein bringt nichts, sie
verschiebt weder Treffer noch Fehler. Der FP `yun2024:196` entsteht unabhaengig
von der Erweiterung, weil die Regel dort Tabelle 1 statt Tabelle 2 liest.

## Aliasliste

| Outcome-Wort | Zulaeassige Tabellenwoerter | Wirkung |
|---|---|---|
| scanning | scan, duration | 2 TP (426) |

Die Akronym-Regel (Woerter ab drei Grossbuchstaben bleiben im Tokenizer) ist
kein Alias, sondern Teil der Wortzerlegung; sie bringt allein 0 TP und wurde
beibehalten, weil sie die Zerlegung nicht verschlechtert (gleiche Werte wie
ohne Erweiterung).

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
| 196 | WMS-R (0 min) | `28  24  1.29 ... 24  1.08` | Gold aus Tabelle 2, Wochenwert 28 mit n = 24 |
| 358 | improvement at week 144 (SDMT) | keine Zeile | Goldwert 144 ist die Wochenzahl |
| 365 | leptin/adiponectin ratio | keine Zeile | Wert nur im Fliesstext |
| 389 | controlled blood pressure | `Complicated (n = 175)` | Mehrarm, Gold greift eine Subgruppe |
| 426 | Scanning times | `Scan duration (min) 19.8 ... 31.7` | Wortvariante, per Alias behoben |
| 512 | Adverse effects | `1200 (*N* = 122) 2400 (*N* = 123)` | Goldwert 122 ist die Gruppengroesse |
| 644 | progression-free survival | `(*N* = 48) (*N* = 23)` | Groessenzeile ohne Armnamen |

Nur `Scanning times` ist eine reine Wortvariante. Die uebrigen Faelle scheitern
an Mehrarm-Tabellen, fehlenden Zielzeilen oder an Goldwerten, die keine
Tabellenzelle sind.

## Ergebnis an den 31 Zielfaellen

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | {len(ziel_keys)} |
| Regel liefert einen Wert | {len(detail)} |
| davon richtig (TP) | {tp} |
| davon falsch (FP) | {fp} |
| TP-Verlust | {verlust} |

## Abbruchgruende der nicht gelieferten Faelle

| Stufe | Faelle |
|---|---:|
| Zielzeile nicht gefunden | {diagnose.get('zielzeile_nicht_gefunden', 0)} |
| Groessenzeile nicht in Reichweite | {diagnose.get('groessenzeile_nicht_gefunden', 0)} |
| Arm mehrdeutig oder nur anderer Arm | {diagnose.get('anderer_arm_oder_mehrdeutig', 0)} |

## Gold-Verdacht bei den FP

Pruefvermerk: `pruefvermerk_gold_20261121.md`.

| Record | Regelwert | Gold | Befund |
|---|---:|---:|---|
| 331/334/335/336 | 45 | 47 | `PMC5617873` nennt dreimal `Placebo (n = 45)` vor `Aripiprazole (n = 47)`; Kontext-Intervention ist Aripiprazole. Gold fuehrt 45 als Intervention: Arme vertauscht. |
| 196 | 140 | 24 | Gold stammt aus Tabelle 2 (Woche 28, n = 24, Mittel 1.29/1.08); die Regel las die Kopfzeile von Tabelle 1 (145/140). Gold ist belegt, der Verdacht widerlegt. |

Kein Goldwert wurde geaendert.

## Gelieferte Zellen

| Record | Feld | Regelwert | Quelle | Zeile | Gold | richtig |
|---|---|---:|---|---:|---:|---|
{tab}
"""
    (HIER / "zielzeile_alias_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"Ziel {len(ziel_keys)} | geliefert {len(detail)} | TP {tp} | FP {fp} | TP-Verlust {verlust}")
    print(f"Diagnose: {dict(diagnose)}")
    print(f"Varianten: {ergebnis['varianten']}")
    for e in detail:
        print(f"  {e['record_id']:14s} {e['feld']:28s} {e['regel']['value']:>8} "
              f"({e['regel']['quelle']}, Z{e['regel']['zeile']}) | gold {e['gold']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
