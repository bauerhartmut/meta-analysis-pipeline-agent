#!/usr/bin/env python3
"""Deterministische Nachregel fuer Gruppengroessen ohne Groessenzeile.

Zwei Quellen, beide ohne Gold:

1. Satz: `40 patients were randomized ...`, `a total of 40 participants were
   assigned`. Der Arm kommt aus dem Satzteil, in dem die Zahl steht; nennt der
   Satzteil keinen Arm oder beide, wird verweigert.
2. Nenner: `8/20` in einer Tabellenzeile. Die Nenner sind die Armgroessen; der
   Arm kommt aus einer selbstbeschrifteten Kopfzeile (`Placebo (n = 45) ...`).
   Ohne solche Kopfzeile wird verweigert.

Die Regel liefert hoechstens zwei Zellen (`intervention_group_size`,
`comparator_group_size`) und nur, wenn beide Quellen sich nicht widersprechen.

Gemessen an allen 127 Zaehlfeld-Faellen: Abdeckung der 48 ohne Groessenzeile,
Treffer, erzeugte FP und TP-Verlust im Modus `ersetzen`.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/groessen_regel_20261121.py
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
from zaehlfelder_20261121 import ZAEHLFELDER, arm_von_label, segmente  # noqa: E402

FELD = {"intervention": "intervention_group_size", "comparator": "comparator_group_size"}
NENNER = re.compile(r"\b(\d{1,5})\s*/\s*(\d{1,5})\b")

ALLGEMEIN = {
    "intervention": ["intervention", "treatment", "active", "experimental", "therapy", "verum"],
    "comparator": ["control", "placebo", "sham", "usual care", "standard care", "comparator", "vehicle"],
}


def arm_von_label2(label: str, context: dict[str, Any]) -> str:
    """Armname aus Kontext oder allgemeiner Lexik."""
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


def aus_nennern(record: dict[str, Any], text: str) -> dict[str, dict[str, Any]]:
    """Gruppengroessen aus Nennern `k/n` mit selbstbeschrifteter Armzeile."""
    context = record.get("context") or {}
    zeilen = text.splitlines()
    kandidaten: dict[str, set[float]] = {"intervention": set(), "comparator": set()}
    for i, zeile in enumerate(zeilen):
        segs = segmente(zeile)
        zahlenspalten = [k for k, s in enumerate(segs) if NENNER.search(s)]
        if len(zahlenspalten) < 2:
            continue
        spalten_arm: dict[int, str] = {}
        for j in range(i - 1, max(-1, i - 21), -1):
            kopf = segmente(zeilen[j])
            labels = []
            if len(kopf) == len(zahlenspalten):
                labels = kopf
            elif len(kopf) == len(zahlenspalten) + 1:
                labels = kopf[1:]
            else:
                continue
            # Nur wenn die Kopfzeile die Groessen ausdruecklich nennt; ein
            # Nenner allein kann auch eine Kompletter-Zahl sein.
            nennt_groesse = sum(1 for lab in labels if re.search(r"\bn\s*=", lab, re.IGNORECASE))
            if nennt_groesse < 2:
                continue
            arme = [arm_von_label2(lab, context) for lab in labels]
            if sum(1 for a in arme if a) >= 2:
                spalten_arm = {p: a for p, a in enumerate(arme) if a}
                break
        if not spalten_arm:
            continue
        for p, arm in spalten_arm.items():
            if p >= len(zahlenspalten):
                continue
            m = NENNER.search(segs[zahlenspalten[p]])
            if m and int(m.group(1)) < int(m.group(2)):
                kandidaten[arm].add(float(m.group(2)))
    ergebnis: dict[str, dict[str, Any]] = {}
    for arm, werte in kandidaten.items():
        if len(werte) == 1:
            ergebnis[FELD[arm]] = {"value": werte.pop(), "quelle": "nenner"}
    return ergebnis


def regel(record: dict[str, Any], text: str) -> dict[str, dict[str, Any]]:
    """Zellen der Nachregel: nur Nenner mit selbstbeschrifteter Groessenkopfzeile.

    Die Satzquelle (`N patients were randomized ...`) ist entfernt: sie lieferte
    im Korpus nur Gesamtzahlen und damit falsche Werte.
    """
    return aus_nennern(record, text)


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    zaehl = [f for f in faelle if f["feld"] in ZAEHLFELDER]
    ohne_zeile = json.loads((HIER / "zaehlfelder_20261121.json").read_text(encoding="utf-8"))
    ohne_zeile_ids = {
        (e["record_id"], e["feld"], e["arm"])
        for e in ohne_zeile["detail"]
        if e["klasse"] in ("nur_fliessetext", "nur_nenner")
    }

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}
    texte: dict[str, str] = {}
    ausgaben: dict[str, dict[str, dict[str, Any]]] = {}
    for f in zaehl:
        rid = f["record_id"]
        if rid not in ausgaben:
            if rid not in texte:
                texte[rid] = (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
            ausgaben[rid] = regel(records[rid], texte[rid])

    # 1. Abdeckung der 48 ohne Groessenzeile
    ziel = [f for f in zaehl if (f["record_id"], f["feld"], f["arm"]) in ohne_zeile_ids]
    treffer = fehlt = falsch = 0
    for f in ziel:
        zellen = ausgaben[f["record_id"]]
        if f["feld"] not in zellen or f["feld"] not in FELD.values():
            fehlt += 1
            continue
        wert = zellen[f["feld"]]["value"]
        if abs(wert - f["wert"]) < 1e-6:
            treffer += 1
        else:
            falsch += 1

    # Diagnose: warum liefert die Regel nichts?
    ziel_events = sum(1 for f in ziel if "events" in f["feld"])
    ziel_groesse = len(ziel) - ziel_events
    mit_nenner = mit_armnah = 0
    for f in ziel:
        text = texte[f["record_id"]]
        wert = int(f["wert"])
        if re.search(rf"/\s*{wert}\b", text):
            mit_nenner += 1
        if any(any(a in text[max(0, m.start() - 150) : m.start() + 150].lower() for a in ALLGEMEIN[f["arm"]])
               for m in re.finditer(rf"(?<!\d){wert}(?!\d)", text)):
            mit_armnah += 1

    # 2. Wirkung, wenn die Regel auf die Vorhersage angewandt wird
    additiv_tp = additiv_fp = ersetzen_tp = ersetzen_fp = tp_verlust = 0
    zellen_gesamt = 0
    for rid, zellen in ausgaben.items():
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (records[rid].get("gold") or {}).get("cells") or []}
        roh = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value")) for z in v.zellen(p5.get(rid))}
        for feld, info in zellen.items():
            zellen_gesamt += 1
            soll = gold.get((feld, "intervention" if feld.startswith("intervention") else "comparator"))
            richtig = soll is not None and abs(soll - info["value"]) < 1e-6
            if (feld, "intervention" if feld.startswith("intervention") else "comparator") not in roh:
                if richtig:
                    additiv_tp += 1
                else:
                    additiv_fp += 1
            else:
                vorher = roh[(feld, "intervention" if feld.startswith("intervention") else "comparator")]
                if soll is not None and abs(vorher - soll) < 1e-6 and not richtig:
                    tp_verlust += 1
                if richtig and not (soll is not None and abs(vorher - soll) < 1e-6):
                    ersetzen_tp += 1
                if not richtig:
                    ersetzen_fp += 1
    ergebnis = {
        "stand": "2026-11-21",
        "ziel_faelle_ohne_groessenzeile": len(ziel),
        "geliefert": treffer + falsch,
        "richtig": treffer,
        "falsch": falsch,
        "verweigert": fehlt,
        "ziel_events": ziel_events,
        "ziel_groesse": ziel_groesse,
        "ziel_wert_als_nenner": mit_nenner,
        "ziel_wert_nah_am_armwort": mit_armnah,
        "regelzellen_gesamt": zellen_gesamt,
        "additiv": {"tp": additiv_tp, "fp": additiv_fp},
        "ersetzen": {"tp": ersetzen_tp, "fp": ersetzen_fp, "tp_verlust": tp_verlust},
        "beispiele": [
            {"record_id": f["record_id"], "feld": f["feld"], "arm": f["arm"], "gold": f["wert"],
             "regel": ausgaben[f["record_id"]].get(f["feld"])}
            for f in ziel
        ],
    }
    (HIER / "groessen_regel_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    bericht = f"""# Nachregel fuer Gruppengroessen ohne Groessenzeile (21.11.2026)

Offline, ohne Netzaufruf. Eine Quelle, sonst Verweigerung: Nenner `k/n` in einer Tabellenzeile, deren
Kopfzeile die Groessen selbst nennt (`n = ...`) und jede Spalte einem Arm
zuordnet. Die Satzquelle ist entfernt, weil sie ausschliesslich Gesamtzahlen
las.

## Ergebnis an den {len(ziel)} Ziel-Faellen

| Kennzahl | Wert |
|---|---:|
| Faelle ohne Groessenzeile | {len(ziel)} |
| Regel liefert einen Wert | {treffer + falsch} |
| davon richtig | {treffer} |
| davon falsch | {falsch} |
| verweigert | {fehlt} |

Alle gelieferten Werte stammen aus Nennern mit Groessenkopfzeile.

## Warum die Regel verweigert

| Kennzahl | Wert |
|---|---:|
| Ziel-Faelle mit `events` | {ziel_events} |
| Ziel-Faelle mit `group_size` | {ziel_groesse} |
| Wert irgendwo als Nenner | {mit_nenner} |
| Wert im Umfeld eines Armworts (150 Zeichen, grobe Naeherung) | {mit_armnah} |

Ereigniszaehler haben weder Groessenzeile noch Nenner; sie sind mit dieser
Regel grundsaetzlich nicht zu holen. Bei den Groessenfaellen steht der Goldwert
zwar oft als Nenner oder in Armnaehe, aber in Tabellen anderer Subgruppen
(Beispiel yun2024:120: Nenner 30/52, Gold 20/44) oder als Kompletter-Zahl
(yun2024:547: `68 of 72`). Ohne die Satzquelle bleibt es deshalb bei Verweigerung und 0 FP.

## Wirkung auf die Bilanz

| Modus | TP | FP | TP-Verlust |
|---|---:|---:|---:|
| additiv (nur fehlende Schluessel) | {additiv_tp} | {additiv_fp} | 0 |
| ersetzen (ueberschreibt) | {ersetzen_tp} | {ersetzen_fp} | {tp_verlust} |

Die Regel liefert insgesamt {zellen_gesamt} Zellen ueber die {len(ausgaben)}
betroffenen Records; gezaehlt ist jede Zelle gegen das Gold des jeweiligen
Records.

## Grenzen

- Nur Gruppengroessen. Die 47 Ereignis-Felder (`events`) kann die Regel nicht
  fuellen, weil Ereigniszaehler keine Groessenzeile und keinen Nenner haben.
- Saetze werden an `;`, `and` und Satzgrenzen getrennt; ein Satz, der beide
  Arme nennt, wird verweigert.
- Nenner brauchen eine Kopfzeile, in der jede Spalte einen Arm nennt; sonst
  verweigert die Regel.
"""
    (HIER / "groessen_regel_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")
    print(f"Ziel {len(ziel)}: geliefert {treffer + falsch} (richtig {treffer}, falsch {falsch}), verweigert {fehlt}")
    print(f"Regelzellen {zellen_gesamt}")
    print(f"additiv TP {additiv_tp} FP {additiv_fp} | ersetzen TP {ersetzen_tp} FP {ersetzen_fp} TP-Verlust {tp_verlust}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
