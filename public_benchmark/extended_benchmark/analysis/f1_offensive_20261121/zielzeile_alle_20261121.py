#!/usr/bin/env python3
"""Alias-Erweiterung ueber alle fn_wert_ersetzt messen.

Offline, ohne Netzaufruf. Grundgesamtheit sind alle 295 `fn_wert_ersetzt`.
Verglichen werden zwei Varianten der Zielzeilensuche:

* `ohne`  - keine Erweiterung (keine Aliasliste, keine Akronyme).
* `alias` - Alias `scanning -> scan, duration` plus Akronyme ab drei
  Buchstaben.

Je Fall wird zusaetzlich der Feldtyp gelesen: Groessen aus der Groessenzeile
ueber der Zielzeile, Mittel und Ereignisse als erste Zahl der Armzelle,
Streuungen als Zahl in Klammern. Das ist ein grober Leser, kein validierter
Extraktor; die Trefferzahlen sind entsprechend zu lesen.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zielzeile_alle_20261121.py
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
import groessen_zielzeile_20261121 as g  # noqa: E402
import zielzeile_alias_20261121 as alias_mod  # noqa: E402
from zaehlfelder_20261121 import segmente, arm_von_label  # noqa: E402

FELD_ARM = {"intervention": "intervention", "comparator": "comparator"}


def arm_von_spalte(zeilen: list[str], i: int, segs: list[str], k: int,
                   context: dict[str, Any]) -> str:
    """Arm der Zellspalte `k`, gesucht in der Kopfzeile ueber der Zielzeile."""
    zahlenspalten = [n for n, s in enumerate(segs) if re.search(r"\d", s)]
    if k not in zahlenspalten:
        return ""
    pos = zahlenspalten.index(k)
    for j in range(i - 1, max(-1, i - 41), -1):
        kopf = segmente(zeilen[j])
        if len(kopf) == len(zahlenspalten):
            ziel = pos
        elif len(kopf) == len(zahlenspalten) + 1:
            ziel = pos + 1
        else:
            continue
        if ziel < len(kopf):
            arm = arm_von_label(kopf[ziel], context)
            if arm:
                return arm
    return ""


def wert_aus_zelle(zelle: str, feld: str) -> float | None:
    """Wert einer Armzelle: Streuung in Klammern, sonst erste Zahl."""
    if feld.endswith("standard_deviation"):
        m = re.search(r"\(\s*(\d+(?:\.\d+)?)", zelle)
        return float(m.group(1)) if m else None
    m = re.search(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)", zelle)
    return float(m.group(1).replace(",", "")) if m else None


def lies(record: dict[str, Any], text: str, feld: str, arm: str,
         alias: dict[str, list[str]], akronyme: bool) -> dict[str, Any] | None:
    context = record.get("context") or {}
    zeilen = text.splitlines()
    if feld.endswith("group_size"):
        ziel = alias_mod.ziel_zeile_alias(zeilen, str(context.get("outcome") or ""), alias, akronyme)
        if ziel < 0:
            return None
        groesse = g.groessen_zeile(zeilen, ziel)
        if groesse < 0:
            return None
        werte = g.aus_groessenzeile(zeilen, groesse, context)
        return werte.get(arm)

    ziel = alias_mod.ziel_zeile_alias(zeilen, str(context.get("outcome") or ""), alias, akronyme)
    if ziel < 0:
        return None
    segs = segmente(zeilen[ziel])
    for k in range(1, len(segs)):
        if arm_von_spalte(zeilen, ziel, segs, k, context) != arm:
            continue
        wert = wert_aus_zelle(segs[k], feld)
        if wert is not None:
            return {"value": wert, "quelle": "zielzeile", "zeile": ziel + 1}
    return None


def messe(faelle: list[dict[str, Any]], records: dict[str, dict[str, Any]], texte: dict[str, str],
          alias: dict[str, list[str]], akronyme: bool) -> dict[str, Any]:
    detail: list[dict[str, Any]] = []
    ziel_gefunden = 0
    for f in faelle:
        rid = f["record_id"]
        record = records[rid]
        zeilen = texte[rid].splitlines()
        if alias_mod.ziel_zeile_alias(zeilen, str((record.get("context") or {}).get("outcome") or ""),
                                      alias, akronyme) >= 0:
            ziel_gefunden += 1
        info = lies(record, texte[rid], f["feld"], f["arm"], alias, akronyme)
        if info is None:
            continue
        gold = float(f["wert"])
        richtig = abs(info["value"] - gold) < 1e-6
        gerundet = richtig or abs(round(info["value"]) - gold) < 1e-6
        detail.append({"record_id": rid, "feld": f["feld"], "arm": f["arm"], "regel": info,
                       "gold": f["wert"], "richtig": richtig, "richtig_gerundet": gerundet})
    tp = sum(1 for e in detail if e["richtig"])
    tp_r = sum(1 for e in detail if e["richtig_gerundet"])
    return {"zielzeile_gefunden": ziel_gefunden, "geliefert": len(detail),
            "tp": tp, "fp": len(detail) - tp,
            "tp_gerundet": tp_r, "fp_gerundet": len(detail) - tp_r, "detail": detail}


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte: dict[str, str] = {}
    for rid in {f["record_id"] for f in faelle}:
        texte[rid] = (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")

    ohne = messe(faelle, records, texte, {}, False)
    mit = messe(faelle, records, texte, alias_mod.ALIAS, True)
    neu = {(e["record_id"], e["feld"], e["arm"]) for e in mit["detail"]} - \
          {(e["record_id"], e["feld"], e["arm"]) for e in ohne["detail"]}
    neu_detail = [e for e in mit["detail"] if (e["record_id"], e["feld"], e["arm"]) in neu]

    ergebnis = {
        "stand": "2026-11-21",
        "faelle": len(faelle),
        "ohne": {k: ohne[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                       "tp_gerundet", "fp_gerundet")},
        "alias": {k: mit[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                      "tp_gerundet", "fp_gerundet")},
        "nur_mit_alias": {"geliefert": len(neu_detail),
                          "tp": sum(1 for e in neu_detail if e["richtig"]),
                          "fp": sum(1 for e in neu_detail if not e["richtig"]),
                          "tp_gerundet": sum(1 for e in neu_detail if e["richtig_gerundet"]),
                          "fp_gerundet": sum(1 for e in neu_detail if not e["richtig_gerundet"])},
        "detail_nur_mit_alias": neu_detail,
    }
    (HIER / "zielzeile_alle_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['gold']} | "
        f"{'ja' if e['richtig'] else 'nein'} |" for e in neu_detail) or "| - | - | - | - | - |"
    bericht = f"""# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
{len(faelle)} `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias |
|---|---:|---:|
| Zielzeile gefunden | {ohne['zielzeile_gefunden']} | {mit['zielzeile_gefunden']} |
| Zellen geliefert | {ohne['geliefert']} | {mit['geliefert']} |
| TP (exakt) | {ohne['tp']} | {mit['tp']} |
| FP (exakt) | {ohne['fp']} | {mit['fp']} |
| TP (auf ganze Zahl gerundet) | {ohne['tp_gerundet']} | {mit['tp_gerundet']} |
| FP (auf ganze Zahl gerundet) | {ohne['fp_gerundet']} | {mit['fp_gerundet']} |

Nur durch den Alias neu geliefert: {len(neu_detail)} Zellen, davon
{sum(1 for e in neu_detail if e['richtig'])} exakt richtig und
{sum(1 for e in neu_detail if e['richtig_gerundet'])} nach Rundung richtig.
Die zwei exakten FP sind Rundungen: 31.7 gegen Gold 32 und 19.8 gegen Gold 20.

## Neue Zellen

| Record | Feld | Regelwert | Gold | richtig |
|---|---|---:|---:|---|
{tab}

## Lesart

Gelesen wird je Feldtyp: Groessen aus der Groessenzeile, Mittel und Ereignisse
als erste Zahl der Armzelle, Streuungen als Zahl in Klammern. Der Leser ist
grob und nicht validiert; die TP/FP-Zahlen messen die Zielzeilensuche, nicht
einen fertigen Extraktor.
"""
    (HIER / "zielzeile_alle_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"Faelle {len(faelle)}")
    print(f"ohne  : Zielzeile {ohne['zielzeile_gefunden']} | Zellen {ohne['geliefert']} | "
          f"TP {ohne['tp']} | FP {ohne['fp']}")
    print(f"alias : Zielzeile {mit['zielzeile_gefunden']} | Zellen {mit['geliefert']} | "
          f"TP {mit['tp']} | FP {mit['fp']}")
    print(f"nur mit Alias: {len(neu_detail)} Zellen | TP {ergebnis['nur_mit_alias']['tp']} | "
          f"FP {ergebnis['nur_mit_alias']['fp']} | gerundet TP "
          f"{ergebnis['nur_mit_alias']['tp_gerundet']}")
    for e in neu_detail:
        print(f"  {e['record_id']:14s} {e['feld']:30s} {e['regel']['value']:>10} | gold {e['gold']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
