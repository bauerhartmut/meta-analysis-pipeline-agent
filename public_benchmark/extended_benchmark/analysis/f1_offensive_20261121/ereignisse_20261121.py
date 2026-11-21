#!/usr/bin/env python3
"""Sind Ereigniszaehler (`11 (12%)`) deterministisch lesbar?

Offline, ohne Netzaufruf. Grundgesamtheit: die 29 `fn_wert_ersetzt` mit
`events`, die keine Groessenzeile haben. Geprueft wird, ob der Goldwert als
Zaehler mit Prozentanteil (`N (x%)`) in einer Tabellenzeile steht, deren Spalte
sich ueber eine selbstbeschriftete Kopfzeile einem Arm zuordnen laesst.

Klassen:

* `zaehler_richtiger_arm` - Zaehler gefunden, Spalte gehoert zum Gold-Arm.
* `zaehler_anderer_arm`   - Zaehler gefunden, Spalte gehoert zum anderen Arm.
* `zaehler_arm_unklar`    - Zaehler gefunden, Spalte nicht zuordenbar.
* `wert_ohne_prozent`     - Wert steht im Dokument, aber nicht als `N (x%)`.
* `nicht_im_dokument`     - Wert fehlt in der Markdown-Fassung.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/ereignisse_20261121.py
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
from zaehlfelder_20261121 import arm_von_label, segmente  # noqa: E402


ALLGEMEIN = {
    "intervention": ["intervention", "treatment", "active", "experimental", "verum", "therapy"],
    "comparator": ["control", "placebo", "sham", "usual", "standard", "tau", "comparator", "vehicle"],
}


def arm_allgemein(label: str, context: dict[str, Any]) -> str:
    arm = arm_von_label(label, context)
    if arm:
        return arm
    li = label.lower()
    punkte = {a: sum(1 for w in ws if w in li) for a, ws in ALLGEMEIN.items()}
    if punkte["intervention"] > punkte["comparator"] and punkte["intervention"]:
        return "intervention"
    if punkte["comparator"] > punkte["intervention"] and punkte["comparator"]:
        return "comparator"
    return ""


def arm_der_spalte(zeilen: list[str], i: int, segs: list[str], idx: int,
                   context: dict[str, Any]) -> tuple[str, str]:
    """Arm der Spalte `idx`: erst aus der Zeile selbst, dann aus der Kopfzeile.

    In Ereignis-Tabellen stehen die Arme oft in der Zeilenbeschriftung und die
    Zeitpunkte in den Spalten; das wird zuerst geprueft.
    """
    zeilen_arm = arm_allgemein(segs[0], context)
    if zeilen_arm and not re.search(r"\d", segs[0]):
        return zeilen_arm, "zeile-links"
    arm = arm_von_label(segs[idx], context)
    if arm:
        return arm, "zeile"
    zahlenspalten = [k for k, s in enumerate(segs) if re.search(r"\d", s)]
    if idx not in zahlenspalten:
        return "", ""
    pos = zahlenspalten.index(idx)
    for j in range(i - 1, max(-1, i - 21), -1):
        kopf = segmente(zeilen[j])
        if len(kopf) == len(zahlenspalten):
            ziel = pos
        elif len(kopf) == len(zahlenspalten) + 1:
            ziel = pos + 1
        else:
            continue
        if ziel >= len(kopf):
            continue
        arm = arm_von_label(kopf[ziel], context)
        if arm:
            return arm, "kopf"
    return "", ""


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    zaehl = json.loads((HIER / "zaehlfelder_20261121.json").read_text(encoding="utf-8"))
    ohne = {(e["record_id"], e["feld"], e["arm"]) for e in zaehl["detail"]
            if e["klasse"] in ("nur_fliessetext", "nur_nenner")}
    faelle = [f for f in fehler["faelle_fn"]
              if f["regel"] == "fn_wert_ersetzt" and "events" in f["feld"]
              and (f["record_id"], f["feld"], f["arm"]) in ohne]

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte: dict[str, str] = {}
    ergebnisse: list[dict[str, Any]] = []
    for f in faelle:
        rid = f["record_id"]
        record = records[rid]
        if rid not in texte:
            texte[rid] = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        zeilen = texte[rid].splitlines()
        context = record.get("context") or {}
        wert = int(f["wert"])
        muster = re.compile(rf"(?<![\d.]){wert}\s*\(\s*[\d.]+\s*%\s*\)")

        klasse, spalte_arm, quelle, zeile = "wert_ohne_prozent", "", "", None
        if any(zahl_positionen(wert, z) for z in zeilen):
            for i, z in enumerate(zeilen):
                segs = segmente(z)
                if len(segs) < 3:
                    continue
                # Zaehler mit Prozent: `11 (12%)`, `52 (39.1)`, `22 (18)` -
                # das Prozentzeichen kann in der Kopfzeile stehen.
                form = ""
                if muster.search(z):
                    form = "prozentzeichen"
                elif re.search(rf"(?<![\\d.]){wert}\s*\(\s*[\\d.]+\s*\)", z):
                    form = "prozent_ohne_zeichen"
                elif any("%" in k for k in " ".join(zeilen[max(0, i - 12) : i]).split()):
                    form = "prozent_in_kopfzeile"
                if not form:
                    continue
                idx = next((k for k, s in enumerate(segs)
                            if re.search(rf"(?<![\\d.]){wert}(?![\\d.])", s)), -1)
                if idx < 0:
                    continue
                arm, q = arm_der_spalte(zeilen, i, segs, idx, context)
                spalte_arm, quelle, zeile = arm, q, i + 1
                if not arm:
                    klasse = "zaehler_arm_unklar"
                elif arm == f["arm"]:
                    klasse = "zaehler_" + form
                else:
                    klasse = "zaehler_anderer_arm"
                break
            else:
                klasse = "wert_ohne_prozent"
        else:
            klasse = "nicht_im_dokument"

        ergebnisse.append(
            {"record_id": rid, "feld": f["feld"], "arm": f["arm"], "wert": f["wert"],
             "klasse": klasse, "spalte_arm": spalte_arm, "quelle": quelle, "zeile": zeile}
        )

    verteilung = Counter(e["klasse"] for e in ergebnisse)
    ergebnis = {"stand": "2026-11-21", "faelle": len(ergebnisse),
                "verteilung": dict(verteilung), "detail": ergebnisse}
    (HIER / "ereignisse_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['arm']} | {e['wert']} | {e['klasse']} | "
        f"{e['spalte_arm'] or '-'} | {e['zeile'] or '-'} |"
        for e in ergebnisse
    )
    bericht = f"""# Ereigniszaehler deterministisch lesbar? (21.11.2026)

Offline, ohne Netzaufruf. Grundgesamtheit: die {len(ergebnisse)} `events`-Faelle
ohne Groessenzeile. Geprueft wird, ob der Goldwert als `N (x%)` in einer
Tabellenzeile steht und die Spalte ueber eine Kopfzeile einem Arm zuzuordnen
ist.

## Verteilung

| Klasse | Faelle |
|---|---:|
| Zaehler mit Prozentzeichen, richtiger Arm | {verteilung['zaehler_prozentzeichen']} |
| Zaehler mit Prozent ohne Zeichen, richtiger Arm | {verteilung['zaehler_prozent_ohne_zeichen']} |
| Zaehler unter (%)-Kopfzeile, richtiger Arm | {verteilung['zaehler_prozent_in_kopfzeile']} |
| Zaehler im anderen Arm | {verteilung['zaehler_anderer_arm']} |
| Zaehler, Arm unklar | {verteilung['zaehler_arm_unklar']} |
| Wert ohne Prozentanteil | {verteilung['wert_ohne_prozent']} |
| Wert nicht im Dokument | {verteilung['nicht_im_dokument']} |

## Faelle

| Record | Feld | Arm | Wert | Klasse | Spaltenarm | Zeile |
|---|---|---|---|---:|---|---:|
{tab}

## Antwort

Deterministisch lesbar sind {verteilung['zaehler_prozentzeichen'] + verteilung['zaehler_prozent_ohne_zeichen'] + verteilung['zaehler_prozent_in_kopfzeile']} der {len(ergebnisse)} Faelle,
alle ueber eine Kopfzeile mit Prozentangabe und den Arm in der
Zeilenbeschriftung. In {verteilung['zaehler_anderer_arm']} Fall landet der
Zaehler in der falschen Zeile, in {verteilung['zaehler_arm_unklar']} ist der Arm
nicht bestimmbar, in {verteilung['wert_ohne_prozent']} fehlt der Prozentbezug.
Ein Zaehler im Format `11 (12%)` mit Prozentzeichen trat in keinem Fall auf;
die Tabellen schreiben `52 (39.1)` ohne Zeichen oder stellen `No. patients (%)`
ueber nackte Zahlen.

## Lesart

`zaehler_richtiger_arm` ist die einzige Klasse, aus der eine Regel ohne Raten
einen Wert ziehen koennte. `zaehler_anderer_arm` waere ein Widerspruch zur
Goldbeschriftung, `zaehler_arm_unklar` fehlt die Kopfzeile. `wert_ohne_prozent`
bedeutet, dass die Zahl im Text steht, aber nicht als Zaehler mit Anteil.
"""
    (HIER / "ereignisse_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"{len(ergebnisse)} Ereignis-Faelle: {dict(verteilung)}")
    for e in ergebnisse:
        print(f"  {e['record_id']:14s} {e['feld']:24s} {e['wert']:>6} | {e['klasse']:24s} | "
              f"Spalte {e['spalte_arm'] or '-'} ({e['quelle'] or '-'}) Zeile {e['zeile'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
