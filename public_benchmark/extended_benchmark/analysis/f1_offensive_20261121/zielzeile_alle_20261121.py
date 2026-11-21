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
from zaehlfelder_20261121 import segmente, arm_von_label, STOPP_ARM  # noqa: E402


def arm_weit(label: str, context: dict[str, Any]) -> str:
    """Armerkennung wie `arm_von_label`, aber auch fuer drei Buchstaben (`Pls`)."""
    arm = arm_von_label(label, context)
    if arm:
        return arm
    li = label.lower()
    inter = [w for w in re.findall(r"[a-z][a-z-]{2,}", str(context.get("intervention") or "").lower())
             if w not in STOPP_ARM and w not in {"the", "and", "for", "per", "day", "mg", "with"}]
    comp = [w for w in re.findall(r"[a-z][a-z-]{2,}", str(context.get("comparator") or "").lower())
            if w not in STOPP_ARM and w not in {"the", "and", "for", "per", "day", "mg", "with"}]
    si = sum(1 for w in inter if w in li)
    sc = sum(1 for w in comp if w in li)
    if si > sc and si:
        return "intervention"
    if sc > si and sc:
        return "comparator"
    return ""

KAPITION = re.compile(r"^\s*(?:Table|TABLE)\s*\d|:::\s*caption", re.IGNORECASE)


def tabellengrenzen(zeilen: list[str], ziel: int) -> tuple[int, int]:
    """Anfang und Ende der Tabelle, in der die Zielzeile steht."""
    start = 0
    for j in range(ziel - 1, -1, -1):
        if KAPITION.search(zeilen[j]):
            start = j
            break
    ende = len(zeilen)
    for j in range(ziel + 1, len(zeilen)):
        if KAPITION.search(zeilen[j]):
            ende = j
            break
    return start, ende


def zeitverlauf_ziel(zeilen: list[str], outcome: str, alias: dict[str, list[str]],
                     akronyme: bool, spaeter: bool = False) -> int:
    """Zielzeile aus einer Tabelle mit Wochenspalte: letzter Zeitpunkt des Blocks.

    Gesucht werden Tabellen, deren Kopf `Week` nennt. In ihnen tragen nur die
    ersten Zeilen eines Blocks das Outcome-Label; die Wochenzeilen darunter sind
    nackt. Bei gleichem Treffer entscheidet die spaetere (oder fruehere) Tabelle.
    """
    grenzen: list[tuple[int, int]] = []
    start = 0
    for i, zeile in enumerate(zeilen):
        if KAPITION.search(zeile):
            if i > start:
                grenzen.append((start, i))
            start = i
    grenzen.append((start, len(zeilen)))

    beste: list[tuple[int, int, int]] = []  # (score, zeile, tabelle)
    for t_index, (a, b) in enumerate(grenzen):
        kopf = " ".join(zeilen[max(a, b - 80):min(b, a + 10)]).lower()
        if not re.search(r"\bweek\b", kopf):
            continue
        bloecke: dict[str, list[tuple[float, int]]] = {}
        label = ""
        for i in range(a, b):
            segs = segmente(zeilen[i])
            if not segs:
                continue
            if re.search(r"[A-Za-z]{3}", segs[0]):
                label = segs[0]
                if (len(segs) > 1 and re.fullmatch(r"\d{1,2}", segs[1])
                        and len(g.zahlen(zeilen[i])) >= 2):
                    bloecke.setdefault(label, []).append((float(segs[1]), i))
                continue
            if label and re.fullmatch(r"\d{1,2}", segs[0]) and len(g.zahlen(zeilen[i])) >= 2:
                bloecke.setdefault(label, []).append((float(segs[0]), i))
        for lab, reihen in bloecke.items():
            if len(reihen) < 2:
                continue
            p = alias_mod.treffer_alias(lab, outcome, alias, akronyme)
            if p <= 0:
                continue
            woche, i = max(reihen, key=lambda x: x[0])
            beste.append((p, i, t_index))
    if not beste:
        return -1
    top = max(p for p, _, _ in beste)
    kandidaten = [(i, t) for p, i, t in beste if p == top]
    return max(kandidaten)[0] if spaeter else min(kandidaten)[0]


def groesse_in_tabelle(zeilen: list[str], ziel: int, context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Groesse aus der Tabelle der Zielzeile: `n =`-Zeile oder Zeilen-`n`."""
    start, ende = tabellengrenzen(zeilen, ziel)
    for i in range(ziel - 1, start - 1, -1):
        if g.ist_groessenzeile(zeilen[i]) and g.STRENGE.search(zeilen[i]):
            werte = g.aus_groessenzeile(zeilen, i, context)
            if werte:
                return werte
    # Zeilenlayout `n  Mean (95% CI)` je Arm: n steht in der Zielzeile selbst.
    kopf: list[str] | None = None
    for j in range(ziel - 1, start - 1, -1):
        segs = segmente(zeilen[j])
        arme = [arm_weit(s, context) for s in segs if arm_weit(s, context)]
        if len(arme) >= 2:
            fenster = " ".join(zeilen[j:min(j + 3, ziel + 1)]).lower()
            if "mean" in fenster and re.search(r"\bn\b", fenster):
                kopf = arme[:2]
            break
    if not kopf:
        # Rueckfall: naechste Groessenzeile ueber der Zielzeile, auch ausserhalb
        # der Tabellengrenzen (Tabellen ohne Beschriftung).
        for i in range(ziel - 1, max(-1, ziel - 61), -1):
            if g.ist_groessenzeile(zeilen[i]) and g.STRENGE.search(zeilen[i]):
                werte = g.aus_groessenzeile(zeilen, i, context)
                if werte:
                    return werte
        return {}
    segs = segmente(zeilen[ziel])
    if len(kopf) != 2:
        return {}

    def ganz(s: str) -> int | None:
        return int(s) if re.fullmatch(r"\d{1,6}", s) else None

    n1 = ganz(segs[1]) if len(segs) > 1 else None
    n2 = None
    for k, s in enumerate(segs[2:], start=2):
        if s.startswith("(") and k + 1 < len(segs):
            n2 = ganz(segs[k + 1])
            break
    if not n1 or not n2:
        return {}
    return {kopf[0]: {"value": float(n1), "quelle": "zeile_n", "zeile": ziel + 1},
            kopf[1]: {"value": float(n2), "quelle": "zeile_n", "zeile": ziel + 1}}

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


MITTEL_SD = re.compile(r"^[\s*]*\d+(?:\.\d+)?\s*\(\s*\d+(?:\.\d+)?\s*\)[\s*^a-z(\[]*$", re.IGNORECASE)


def zellformat(zelle: str) -> str:
    """Zellform erkennen: `mittel_sd`, `mittel_ki`, `nackt`, `prozent`, `anzahl_prozent`."""
    z = zelle.strip()
    if MITTEL_SD.match(z):
        return "mittel_sd"
    if re.search(r"\(\s*\d+(?:\.\d+)?\s*;\s*\d+(?:\.\d+)?\s*\)", z):
        return "mittel_ki"
    if re.fullmatch(r"\d+(?:\.\d+)?", z):
        return "nackt"
    if re.fullmatch(r"\d+(?:\.\d+)?\s*\(\s*[\d.]+\s*%?\s*\)\**", z):
        return "anzahl_prozent"
    if "%" in z:
        return "prozent"
    if "\u00b1" in z:
        return "plus_minus"
    return "sonstig"


def wert_aus_zelle(zelle: str, feld: str, mean_formate: tuple[str, ...] | None) -> float | None:
    """Wert einer Armzelle: Streuung in Klammern, Mittel nur in erlaubten Formaten.

    `mean_formate=None` heisst: erste Zahl der Zelle, ohne Formatpruefung.
    """
    if feld.endswith("standard_deviation"):
        m = re.search(r"\(\s*(\d+(?:\.\d+)?)", zelle)
        return float(m.group(1)) if m else None
    if feld.endswith("mean"):
        if mean_formate is not None and zellformat(zelle) not in mean_formate:
            return None
        m = re.search(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)", zelle)
        return float(m.group(1).replace(",", "")) if m else None
    m = re.search(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)", zelle)
    return float(m.group(1).replace(",", "")) if m else None


def lies(record: dict[str, Any], text: str, feld: str, arm: str,
         alias: dict[str, list[str]], akronyme: bool,
         mean_formate: tuple[str, ...] | None = None) -> dict[str, Any] | None:
    if feld.endswith("events"):
        return None  # Ereignis-Leser abgeschaltet: 0 TP, 7 FP
    context = record.get("context") or {}
    zeilen = text.splitlines()
    if feld.endswith("group_size"):
        outcome = str(context.get("outcome") or "")
        ziel = zeitverlauf_ziel(zeilen, outcome, alias, akronyme)
        if ziel < 0:
            ziel = alias_mod.ziel_zeile_alias(zeilen, outcome, alias, akronyme)
        if ziel < 0:
            return None
        treffer = groesse_in_tabelle(zeilen, ziel, context).get(arm)
        if not treffer:
            return None
        # Gruppengroessen sind Zaehlungen: keine Dezimalwerte, keine Kleinstwerte.
        if float(treffer["value"]).is_integer() is False or float(treffer["value"]) < 5:
            return None
        return treffer

    ziel = alias_mod.ziel_zeile_alias(zeilen, str(context.get("outcome") or ""), alias, akronyme)
    if ziel < 0:
        return None
    segs = segmente(zeilen[ziel])
    for k in range(1, len(segs)):
        if arm_von_spalte(zeilen, ziel, segs, k, context) != arm:
            continue
        wert = wert_aus_zelle(segs[k], feld, mean_formate)
        if wert is not None:
            return {"value": wert, "quelle": "zielzeile", "zeile": ziel + 1,
                    "zellformat": zellformat(segs[k])}
    return None


def messe(faelle: list[dict[str, Any]], records: dict[str, dict[str, Any]], texte: dict[str, str],
          alias: dict[str, list[str]], akronyme: bool,
          mean_formate: tuple[str, ...] | None = None) -> dict[str, Any]:
    detail: list[dict[str, Any]] = []
    ziel_gefunden = 0
    for f in faelle:
        rid = f["record_id"]
        record = records[rid]
        zeilen = texte[rid].splitlines()
        if alias_mod.ziel_zeile_alias(zeilen, str((record.get("context") or {}).get("outcome") or ""),
                                      alias, akronyme) >= 0:
            ziel_gefunden += 1
        info = lies(record, texte[rid], f["feld"], f["arm"], alias, akronyme, mean_formate)
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
    streng = messe(faelle, records, texte, alias_mod.ALIAS, True, mean_formate=("mittel_sd",))
    beide = messe(faelle, records, texte, alias_mod.ALIAS, True,
                  mean_formate=("mittel_sd", "plus_minus"))
    neu = {(e["record_id"], e["feld"], e["arm"]) for e in mit["detail"]} - \
          {(e["record_id"], e["feld"], e["arm"]) for e in ohne["detail"]}
    neu_detail = [e for e in mit["detail"] if (e["record_id"], e["feld"], e["arm"]) in neu]

    def gruppe(feld: str) -> str:
        if feld.endswith("group_size"):
            return "groesse"
        if feld.endswith("standard_deviation"):
            return "streuung"
        if feld.endswith("events"):
            return "ereignis"
        return "mittel"

    from collections import Counter  # lokal, nur fuer die Aufschluesselung

    zell_aufschl = Counter((gruppe(e["feld"]), e["regel"].get("zellformat", "groessenzeile"),
                            e["richtig"]) for e in mit["detail"])
    zell_aufschl_neu = Counter((gruppe(e["feld"]), e["regel"].get("zellformat", "groessenzeile"),
                                e["richtig"]) for e in beide["detail"])
    fp = [e for e in mit["detail"] if not e["richtig"]]
    fp_feldtyp = Counter(gruppe(e["feld"]) for e in fp)
    fp_format = Counter((gruppe(e["feld"]), e["regel"].get("zellformat", "groessenzeile")) for e in fp)

    ergebnis = {
        "stand": "2026-11-21",
        "faelle": len(faelle),
        "alias_streng": {k: streng[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                                "tp_gerundet", "fp_gerundet")},
        "neu": {k: beide[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                     "tp_gerundet", "fp_gerundet")},
        "neu_zellformate": {f"{a}|{b}|{'richtig' if r else 'falsch'}": c
                            for (a, b, r), c in zell_aufschl_neu.items()},
        "fp_nach_feldtyp": dict(fp_feldtyp),
        "fp_nach_format": {f"{a}|{b}": c for (a, b), c in fp_format.items()},
        "zellformate": {f"{a}|{b}|{'richtig' if r else 'falsch'}": c
                        for (a, b, r), c in zell_aufschl.items()},
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

    zell_paar: dict[tuple[str, str], list[int]] = {}
    for (a, b, r), c in zell_aufschl_neu.items():
        zell_paar.setdefault((a, b), [0, 0])[0 if r else 1] += c
    format_tab = "\n".join(f"| {a} | {b} | {v[0]} | {v[1]} |"
                            for (a, b), v in sorted(zell_paar.items())) or "| - | - | - | - |"
    fp_feldtyp_tab = "\n".join(f"| {k} | {v} |" for k, v in fp_feldtyp.most_common()) or "| - | - |"
    fp_format_tab = "\n".join(f"| {a} | {b} | {c} |" for (a, b), c in fp_format.most_common()) or "| - | - | - |"
    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['gold']} | "
        f"{'ja' if e['richtig'] else 'nein'} |" for e in neu_detail) or "| - | - | - | - | - |"
    bericht = f"""# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
{len(faelle)} `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias | nur `Mittel (SD)` | Ereignisse aus, Mittel beide Formate |
|---|---:|---:|---:|---:|
| Zielzeile gefunden | {ohne['zielzeile_gefunden']} | {mit['zielzeile_gefunden']} | {streng['zielzeile_gefunden']} | {beide['zielzeile_gefunden']} |
| Zellen geliefert | {ohne['geliefert']} | {mit['geliefert']} | {streng['geliefert']} | {beide['geliefert']} |
| TP (exakt) | {ohne['tp']} | {mit['tp']} | {streng['tp']} | {beide['tp']} |
| FP (exakt) | {ohne['fp']} | {mit['fp']} | {streng['fp']} | {beide['fp']} |
| TP (auf ganze Zahl gerundet) | {ohne['tp_gerundet']} | {mit['tp_gerundet']} | {streng['tp_gerundet']} | {beide['tp_gerundet']} |
| FP (auf ganze Zahl gerundet) | {ohne['fp_gerundet']} | {mit['fp_gerundet']} | {streng['fp_gerundet']} | {beide['fp_gerundet']} |

## FP nach Feldtyp (Alias-Lauf vor der Umstellung, {mit['fp']} FP)

| Feldtyp | FP |
|---|---:|
{fp_feldtyp_tab}

## Formate der gelieferten Zellen (Endvariante)

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
{format_tab}

## FP nach Zellformat

| Feldtyp | Zellformat | FP |
|---|---|---:|
{fp_format_tab}


Nur durch den Alias neu geliefert: {len(neu_detail)} Zellen, davon
{sum(1 for e in neu_detail if e['richtig'])} exakt richtig und
{sum(1 for e in neu_detail if e['richtig_gerundet'])} nach Rundung richtig.
Die zwei exakten FP sind Rundungen: 31.7 gegen Gold 32 und 19.8 gegen Gold 20.

## Neue Zellen

| Record | Feld | Regelwert | Gold | richtig |
|---|---|---:|---:|---|
{tab}

## Lesart

Gelesen wird je Feldtyp: Groessen aus der Groessenzeile, Mittel nur in den
Formaten `Zahl +/- Zahl` und `Zahl (Zahl)`, Streuungen als Zahl in Klammern.
Der Ereignis-Leser ist in allen Laeufen abgeschaltet (vorher 0 TP, 7 FP).

Groessenzeilen kommen aus der Tabelle der Zielzeile; erst wenn dort keine
Groessenzeile steht, gilt der Rueckfall auf die naechste Zeile darueber. Das
Zellformat `n  Mean (95% CI)` einer Zeitverlaufstabelle wird als Zeilen-`n`
gelesen (n nach der Wochenzahl, zweites n nach dem ersten Klammerblock).

In der Endvariante stellen sich die {beide['fp']} FP so:

* Groesse 10, davon 10 richtig (siehe Format-Tabelle).
* Mittel 5 im Format `+/-`, 12 richtig.
* Mittel 2 im Format `Mittel (SD)`, 0 richtig - dort ist die Zeile oder Spalte
  falsch, nicht das Format.

Enthaelt ein Dokument eine Tabelle mit Wochenspalte, in der das Outcome
mehrfach vorkommt, gilt die Zeile des letzten Zeitpunkts statt der
Baseline-Zeile; bei mehreren solchen Tabellen entscheidet die fruehste (die
Haupttabelle steht vor den Subgruppentabellen).

`yun2024:193` wird damit richtig (138/131 aus Tabelle 2, Woche 28).
`yun2024:196` bleibt falsch: die Haupttabelle 2 nennt fuer Woche 28 die Werte
80/78, Gold (24/24) stammt aus Tabelle 3, einer Subgruppe (MMSE-J 20 bis 23).

Trefferquote: {beide['tp']} von {beide['geliefert']} Zellen, also
{100 * beide['tp'] // max(1, beide['geliefert'])} Prozent. Ereignisse tragen
nichts bei, Groessen und Mittel teilen sich die Treffer. Die Umstellung von der
ersten Zahl auf zwei erlaubte Formate kostet 3 weitere Zellen des Formats
`sonstig`, alle drei waren falsch.
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
    print(f"alias + Mittel nur (SD): Zellen {streng['geliefert']} | TP {streng['tp']} | "
          f"FP {streng['fp']} | gerundet TP {streng['tp_gerundet']}")
    print(f"Ereignisse aus + Mittel beide Formate: Zellen {beide['geliefert']} | TP {beide['tp']} | "
          f"FP {beide['fp']} | gerundet TP {beide['tp_gerundet']} | gerundet FP {beide['fp_gerundet']}")
    print(f"FP nach Feldtyp: {dict(fp_feldtyp)}")
    print(f"FP nach Format: {ergebnis['fp_nach_format']}")
    for e in neu_detail:
        print(f"  {e['record_id']:14s} {e['feld']:30s} {e['regel']['value']:>10} | gold {e['gold']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
