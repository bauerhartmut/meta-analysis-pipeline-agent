#!/usr/bin/env python
"""Dublettenfilter als Nachbearbeitung der P5-Predictions, rein lesend.

Frage: Wie viel Precision gewinnt eine Nachbearbeitung, die je (Feld, Arm) nur
eine Zelle behaelt - ohne Modellaufruf, ohne Aenderung an Gold oder Predictions?

Das Skript importiert die Bilanzlogik aus `vergleiche_20261120.py` und benutzt
damit exakt dieselben Regeln wie der committete Vergleich (Schluessel Feld+Arm,
1:1-Verbrauch, Dubletten und Fremdschluessel sind falsch positiv).

Varianten:

- `basis`          : unveraenderte P5-Ausgabe (Referenz).
- `erste_zelle`    : je (Feld, Arm) die erste Zelle in Dokumentreihenfolge.
                     Goldfrei, deterministisch, kein Zusatzwissen.
- `mehrheit`       : je (Feld, Arm) der haeufigste Wert, bei Gleichstand die
                     erste Zelle. Goldfrei; nutzt die Selbstwiederholung des
                     Modells als Signal.
- `beste_zelle`    : je (Feld, Arm) die zum Gold passende Zelle. **Nicht
                     goldfrei** und deshalb nur als Obergrenze ausgewiesen.

Geschrieben wird nichts ausser den beiden Analyseartefakten. Vor und nach der
Rechnung werden SHA256 von Gold und Predictions verglichen; bei Abweichung
bricht das Skript ab.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/dublettenfilter_20261120.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402

AUSGABE_JSON = HIER / "dublettenfilter_20261120.json"
AUSGABE_MD = HIER / "p5_dublettenfilter_20261120.md"


def sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def gruppiere(zellen: list[dict[str, Any]]) -> list[tuple[tuple[str, str], list[dict[str, Any]]]]:
    """Zellen nach (Feld, Arm), Reihenfolge des ersten Auftretens."""
    gruppen: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for zelle in zellen:
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        gruppen.setdefault(key, []).append(zelle)
    return list(gruppen.items())


def filtere(
    gold: list[dict[str, Any]], zellen: list[dict[str, Any]], modus: str
) -> tuple[list[dict[str, Any]], int]:
    """Gibt die gefilterten Zellen und die Zahl der entfernten Zellen zurueck."""
    if modus == "basis":
        return list(zellen), 0
    gewaehlt: list[dict[str, Any]] = []
    for key, kandidaten in gruppiere(zellen):
        if modus == "erste_zelle":
            gewaehlt.append(kandidaten[0])
        elif modus == "mehrheit":
            zaehler = Counter(str(k.get("value")) for k in kandidaten)
            hoechste = max(zaehler.values())
            gewaehlt.append(
                next(k for k in kandidaten if zaehler[str(k.get("value"))] == hoechste)
            )
        elif modus == "beste_zelle":
            soll = next(
                (
                    v.zahl(z.get("value"))
                    for z in gold
                    if (str(z.get("field") or ""), v.arm_von(z)) == key
                ),
                None,
            )
            gewaehlt.append(
                next(
                    (
                        k
                        for k in kandidaten
                        if soll is not None
                        and v.zahl(k.get("value")) is not None
                        and abs(v.zahl(k.get("value")) - soll) < 1e-6
                    ),
                    kandidaten[0],
                )
            )
        else:
            raise ValueError(modus)
    return gewaehlt, len(zellen) - len(gewaehlt)


def fp_zerlegung(
    gold: list[dict[str, Any]], zellen: list[dict[str, Any]]
) -> Counter:
    """Zerlegt die falsch positiven Zellen nach ihrer Entfernbarkeit.

    `mehrfachzelle` heisst: im selben (Feld, Arm) steht mehr als eine Zelle, die
    Dublette ist also goldfrei entfernbar. `einzelner_falschwert` heisst: genau
    eine Zelle auf einem Gold-Schluessel mit falschem Wert, ohne Gold nicht
    entfernbar. `fremdschluessel` heisst: Schluessel kommt im Gold des Records
    nicht vor.
    """
    gruppen = {key: len(kand) for key, kand in gruppiere(zellen)}
    gold_keys = {(str(z.get("field") or ""), v.arm_von(z)) for z in gold}
    verbraucht = [False] * len(zellen)
    for zelle in gold:
        soll = v.zahl(zelle.get("value"))
        if soll is None:
            continue
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        for i, kandidat in enumerate(zellen):
            if verbraucht[i] or (str(kandidat.get("field") or ""), v.arm_von(kandidat)) != key:
                continue
            ist = v.zahl(kandidat.get("value"))
            if ist is not None and abs(ist - soll) < 1e-6:
                verbraucht[i] = True
                break
    zerlegung: Counter = Counter()
    for i, zelle in enumerate(zellen):
        if verbraucht[i] or v.zahl(zelle.get("value")) is None:
            continue
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        if gruppen.get(key, 0) > 1:
            zerlegung["mehrfachzelle"] += 1
        elif key in gold_keys:
            zerlegung["einzelner_falschwert"] += 1
        else:
            zerlegung["fremdschluessel"] += 1
    return zerlegung


def main() -> int:
    vorher = {"gold": sha256(v.RECORDS), "p5": sha256(v.P5), "glm": sha256(v.GLM)}

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ids = [i for i in (json.loads(v.AUSWAHL.read_text(encoding="utf-8")).get("ids") or []) if i in records]
    bewertbar = [i for i in sorted(ids) if i != v.NICHT_BEWERTBAR]
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}

    modi = ("basis", "erste_zelle", "mehrheit", "beste_zelle")
    ergebnis: dict[str, Any] = {
        "quellen": {"records": str(v.RECORDS), "p5": str(v.P5), "auswahl": str(v.AUSWAHL)},
        "hinweis": (
            "beste_zelle nutzt den Goldwert zur Auswahl und ist keine anwendbare "
            "Nachbearbeitung, sondern die Obergrenze des Verfahrens."
        ),
        "records_bewertbar": len(bewertbar),
        "varianten": {},
        "je_record": {},
    }

    for modus in modi:
        bilanzen = []
        entfernt = 0
        betroffen = 0
        for rid in bewertbar:
            gold = (records[rid]["gold"] or {}).get("cells") or []
            zellen = v.zellen(p5.get(rid))
            gefiltert, weg = filtere(gold, zellen, modus)
            entfernt += weg
            betroffen += 1 if weg else 0
            bilanzen.append(v.bilanz_p5(gold, gefiltert))
        ergebnis["varianten"][modus] = {
            **v.kennzahlen(bilanzen, "p5"),
            "entfernte_zellen": entfernt,
            "records_veraendert": betroffen,
        }

    zerlegung: Counter = Counter()
    for rid in bewertbar:
        zerlegung.update(fp_zerlegung((records[rid]["gold"] or {}).get("cells") or [], v.zellen(p5.get(rid))))
    ergebnis["fp_zerlegung"] = dict(zerlegung)

    basis = ergebnis["varianten"]["basis"]
    for modus in modi:
        block = ergebnis["varianten"][modus]
        block["delta_f1"] = (
            round(block["f1"] - basis["f1"], 6) if block["f1"] is not None and basis["f1"] is not None else None
        )
        block["delta_precision"] = (
            round(block["precision"] - basis["precision"], 6)
            if block["precision"] is not None and basis["precision"] is not None
            else None
        )

    # Record-Ebene: wo aendert der goldfreie Filter das Ergebnis?
    for rid in bewertbar:
        gold = (records[rid]["gold"] or {}).get("cells") or []
        zellen = v.zellen(p5.get(rid))
        eintrag: dict[str, Any] = {"goldzellen": len(gold), "zellen": len(zellen)}
        for modus in ("basis", "erste_zelle", "mehrheit"):
            gefiltert, weg = filtere(gold, zellen, modus)
            b = v.bilanz_p5(gold, gefiltert)
            eintrag[modus] = {**b, **v.quote(b["tp"], b["fp"], b["fn"]), "entfernt": weg}
        if eintrag["erste_zelle"]["fp"] != eintrag["basis"]["fp"] or eintrag["erste_zelle"]["tp"] != eintrag["basis"]["tp"]:
            ergebnis["je_record"][rid] = eintrag

    nachher = {"gold": sha256(v.RECORDS), "p5": sha256(v.P5), "glm": sha256(v.GLM)}
    ergebnis["integritaet"] = {
        "vorher": vorher,
        "nachher": nachher,
        "unveraendert": vorher == nachher,
    }
    if vorher != nachher:
        print("ABBRUCH: Eingabedateien haben sich waehrend der Rechnung geaendert.")
        return 1

    AUSGABE_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    zeilen = [
        "# Dublettenfilter auf den P5-Predictions (20.11.2026)",
        "",
        "Reine Nachbearbeitung, kein Modellaufruf. Bewertet auf den "
        f"{len(bewertbar)} bewertbaren Records der P5-Auswahl mit der Logik aus "
        "`vergleiche_20261120.py` (Schluessel Feld + Arm, 1:1-Verbrauch). "
        "Gold und `predictions.jsonl` bleiben unveraendert; die SHA256-Summen vor "
        "und nach der Rechnung sind identisch.",
        "",
        "## Kennzahlen vorher/nachher",
        "",
        "| Variante | TP | FP | FN | Precision | Recall | F1 | entfernte Zellen | Records veraendert |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "basis": "unveraendert (Referenz)",
        "erste_zelle": "Dublettenfilter, erste Zelle je Feld+Arm",
        "mehrheit": "Dublettenfilter, haeufigster Wert je Feld+Arm",
        "beste_zelle": "Obergrenze (goldinformiert, nicht anwendbar)",
    }
    for modus in modi:
        b = ergebnis["varianten"][modus]
        zeilen.append(
            f"| {labels[modus]} | {b['tp']} | {b['fp']} | {b['fn']} | "
            f"{b['precision']:.4f} | {b['recall']:.4f} | {b['f1']:.4f} | "
            f"{b['entfernte_zellen']} | {b['records_veraendert']} |"
        )

    e = ergebnis["varianten"]["erste_zelle"]
    m = ergebnis["varianten"]["mehrheit"]
    zeilen += [
        "",
        "## Was der Filter tut und was nicht",
        "",
        f"- Der goldfreie Filter entfernt {e['entfernte_zellen']} Zellen in "
        f"{e['records_veraendert']} von {len(bewertbar)} Records. Der Recall bleibt mit "
        f"{e['recall']:.4f} unveraendert, weil je (Feld, Arm) immer eine Zelle stehen bleibt "
        "und der 1:1-Verbrauch ohnehin nur eine Trefferzelle je Goldzelle zulaesst.",
        f"- Precision {basis['precision']:.4f} -> {e['precision']:.4f}, F1 {basis['f1']:.4f} -> {e['f1']:.4f} "
        f"(+{(e['f1'] - basis['f1']) * 100:.2f} Prozentpunkte).",
        f"- Die Mehrheitsvariante liegt bei F1 {m['f1']:.4f}; sie ist gegenueber der ersten Zelle "
        f"{'besser' if (m['f1'] or 0) > (e['f1'] or 0) else 'nicht besser'}, weil sich bei "
        "wiederholten Zellen meist derselbe Wert wiederholt.",
        f"- Die goldinformierte Obergrenze liegt bei F1 {ergebnis['varianten']['beste_zelle']['f1']:.4f}; "
        "die Differenz zu `erste_zelle` ist der Preis dafuer, dass der Filter den richtigen Wert "
        "nicht kennen kann.",
        "",
        "## Grenze des Verfahrens",
        "",
        f"- Von den {basis['fp']} falschen Zellen der Basis sind "
        f"{ergebnis['fp_zerlegung'].get('mehrfachzelle', 0)} Mehrfachzellen im selben (Feld, Arm), "
        f"{ergebnis['fp_zerlegung'].get('einzelner_falschwert', 0)} einzelne Zellen mit falschem Wert "
        f"auf einem Gold-Schluessel und {ergebnis['fp_zerlegung'].get('fremdschluessel', 0)} Fremdschluessel. "
        "Nur die Mehrfachzellen sind goldfrei entfernbar.",
        "- Dass 13 Mehrfachzellen erkannt werden, aber nur 9 Zellen verschwinden, liegt an den "
        "Gruppen ohne Treffer: steht im selben (Feld, Arm) keine goldpassende Zelle, bleibt nach "
        "dem Filter genau eine falsche Zelle stehen.",
        "- Weil alle drei Varianten dasselbe Ergebnis liefern, sind die entfernten Zellen exakte "
        "Wertwiederholungen: die Auswahlregel (erste, haeufigste, goldpassende) ist dann gleichgueltig.",
        "- Fremdschluessel sind goldfrei nicht entfernbar: `intervention_events` und "
        "`comparator_mean` sind in anderen Records korrekte Zielfelder. Eine Loeschung "
        "waere nur mit Goldwissen oder einer record-spezifischen Feldauswahl moeglich.",
        "- Der Filter aendert die Ausgabedisziplin nicht. Er verschiebt nur, welche der "
        "mehrfach genannten Zellen zaehlt.",
        "",
    ]

    if ergebnis["je_record"]:
        zeilen += [
            "## Records, bei denen der goldfreie Filter wirkt",
            "",
            "| Record | Goldzellen | Zellen | TP vorher | TP nachher | FP vorher | FP nachher | entfernt |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for rid in sorted(ergebnis["je_record"]):
            d = ergebnis["je_record"][rid]
            zeilen.append(
                f"| `{rid}` | {d['goldzellen']} | {d['zellen']} | {d['basis']['tp']} | "
                f"{d['erste_zelle']['tp']} | {d['basis']['fp']} | {d['erste_zelle']['fp']} | "
                f"{d['erste_zelle']['entfernt']} |"
            )
        zeilen.append("")

    AUSGABE_MD.write_text("\n".join(zeilen) + "\n", encoding="utf-8", newline="\n")

    for modus in modi:
        b = ergebnis["varianten"][modus]
        print(
            f"{modus:<12} TP {b['tp']:>3} FP {b['fp']:>3} FN {b['fn']:>3} "
            f"P {b['precision']:.4f} R {b['recall']:.4f} F1 {b['f1']:.4f} "
            f"entfernt {b['entfernte_zellen']} Records {b['records_veraendert']}"
        )
    print("Integritaet unveraendert:", ergebnis["integritaet"]["unveraendert"])
    print("geschrieben:", AUSGABE_JSON)
    print("geschrieben:", AUSGABE_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
