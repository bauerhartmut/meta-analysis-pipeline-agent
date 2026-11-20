#!/usr/bin/env python
"""GLM-5.3-Referenz gegen P5 auf identischen Record-Mengen.

Rein lesend. Kein Netzaufruf, keine geschriebene Prediction, kein Gold
angefasst. Das Skript liest drei vorhandene Dateien und rechnet die Zellbilanz
zweimal:

- `p5`   : Schluessel Feld **und** Arm, 1:1-Verbrauch jeder Vorhersagezelle,
           Dubletten und Fremdschluessel sind falsch positiv (Logik aus
           `yun_full/werte_p5_aus.py`, hier unabhaengig nachgebaut).
- `yun699`: Schluessel nur Feld, erste Zelle je Feld gewinnt, Zellen ohne
           Goldannotation zaehlen nicht als falsch positiv (Logik aus
           `yun_full/auswerte_yun699.py`).

Damit wird sichtbar, wie viel der Differenz aus der Bewertungslogik und wie
viel aus der Record-Auswahl kommt.

Aufruf:
    .venv/bin/python analysis/glm53_p5_vergleich_20261120/vergleiche_20261120.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
RUNS = BENCH / "runs"
RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"

GLM = RUNS / "glm_auswertung_20261117" / "predictions.jsonl"
LESEKOPIE = RUNS / "_lesekopie_20261118" / "predictions.jsonl"
P5 = RUNS / "yun699_p5_24000_20261118" / "predictions.jsonl"
AUSWAHL = BENCH / "iterativ" / "ergebnisse" / "p5_vorbereitung_20261118.json"

NICHT_BEWERTBAR = "yun2024:653"


def lade(pfad: Path) -> list[dict[str, Any]]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def zahl(wert: Any) -> float | None:
    if wert is None:
        return None
    text = str(wert).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def arm_von(zelle: dict[str, Any]) -> str:
    """Arm aus der Zelle, sonst aus dem Feldpraefix (Gold traegt beides)."""
    arm = str(zelle.get("arm") or "").strip().lower()
    if arm:
        return arm
    feld = str(zelle.get("field") or "")
    if feld.startswith("intervention"):
        return "intervention"
    if feld.startswith("comparator"):
        return "comparator"
    return ""


def zellen(zeile: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not zeile:
        return []
    return list(((zeile.get("predicted") or {}).get("cells")) or [])


def bilanz_p5(gold: list[dict[str, Any]], vor: list[dict[str, Any]]) -> dict[str, int]:
    """Feld+Arm, 1:1-Verbrauch, Dubletten und Fremdschluessel sind FP."""
    verbraucht = [False] * len(vor)
    gold_schluessel = {(str(z.get("field") or ""), arm_von(z)) for z in gold}
    tp = fn = 0
    for zelle in gold:
        soll = zahl(zelle.get("value"))
        if soll is None:
            continue
        key = (str(zelle.get("field") or ""), arm_von(zelle))
        treffer = None
        for i, kandidat in enumerate(vor):
            if verbraucht[i]:
                continue
            if (str(kandidat.get("field") or ""), arm_von(kandidat)) != key:
                continue
            ist = zahl(kandidat.get("value"))
            if ist is not None and abs(ist - soll) < 1e-6:
                treffer = i
                break
        if treffer is None:
            fn += 1
        else:
            verbraucht[treffer] = True
            tp += 1
    fp = 0
    ueberzaehlig = 0
    for i, kandidat in enumerate(vor):
        if verbraucht[i] or zahl(kandidat.get("value")) is None:
            continue
        fp += 1
        if (str(kandidat.get("field") or ""), arm_von(kandidat)) in gold_schluessel:
            ueberzaehlig += 1
    return {"tp": tp, "fp": fp, "fn": fn, "ueberzaehlig": ueberzaehlig,
            "fremdschluessel": fp - ueberzaehlig}


def bilanz_yun(gold: list[dict[str, Any]], vor: list[dict[str, Any]]) -> dict[str, int]:
    """Nur Feld, erste Zelle je Feld gewinnt, Zellen ohne Gold separat."""
    gesehen: dict[str, float] = {}
    for zelle in vor:
        feld = str(zelle.get("field") or "")
        wert = zahl(zelle.get("value"))
        if wert is not None and feld not in gesehen:
            gesehen[feld] = wert
    tp = fn = 0
    for zelle in gold:
        feld = str(zelle.get("field") or "")
        soll = zahl(zelle.get("value"))
        if soll is None:
            continue
        if feld not in gesehen:
            fn += 1
        elif abs(gesehen[feld] - soll) < 1e-9:
            tp += 1
        else:
            fn += 1  # im Yun-Skript "falsch"; fuer Precision zaehlt es als Fehler
    falsch = 0
    for zelle in gold:
        feld = str(zelle.get("field") or "")
        soll = zahl(zelle.get("value"))
        if soll is None or feld not in gesehen:
            continue
        if abs(gesehen[feld] - soll) >= 1e-9:
            falsch += 1
    ohne_gold = sum(1 for feld in gesehen if feld not in {str(z.get("field") or "") for z in gold})
    return {"tp": tp, "fp": falsch, "fn": fn, "ohne_gold": ohne_gold}


def quote(tp: int, fp: int, fn: int) -> dict[str, float | None]:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = None
    if precision is not None and recall is not None and precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def summiere(bilanzen: list[dict[str, int]], schluessel: tuple[str, ...]) -> dict[str, int]:
    summe = {k: 0 for k in schluessel}
    for b in bilanzen:
        for k in schluessel:
            summe[k] += b.get(k, 0)
    return summe


def kennzahlen(bilanzen: list[dict[str, int]], variante: str) -> dict[str, Any]:
    if variante == "p5":
        s = summiere(bilanzen, ("tp", "fp", "fn", "ueberzaehlig", "fremdschluessel"))
    else:
        s = summiere(bilanzen, ("tp", "fp", "fn", "ohne_gold"))
    q = quote(s["tp"], s["fp"], s["fn"])
    return {**s, **q}


def fehlerklassen_record(
    gold: list[dict[str, Any]], vor: list[dict[str, Any]]
) -> dict[str, int]:
    """Zerlegt die Bilanz eines Records in benennbare Fehlerarten."""
    klassen = Counter()
    gold_keys = {(str(z.get("field") or ""), arm_von(z)) for z in gold}
    gold_felder = {str(z.get("field") or "") for z in gold}
    vor_keys = Counter((str(z.get("field") or ""), arm_von(z)) for z in vor)
    verbraucht = [False] * len(vor)
    for zelle in gold:
        soll = zahl(zelle.get("value"))
        if soll is None:
            continue
        key = (str(zelle.get("field") or ""), arm_von(zelle))
        treffer = None
        for i, kandidat in enumerate(vor):
            if verbraucht[i]:
                continue
            if (str(kandidat.get("field") or ""), arm_von(kandidat)) != key:
                continue
            ist = zahl(kandidat.get("value"))
            if ist is not None and abs(ist - soll) < 1e-6:
                treffer = i
                break
        if treffer is not None:
            verbraucht[treffer] = True
            continue
        # FN: fehlt der Schluessel ganz, ist es eine fehlende Extraktion. Gibt es
        # das Feld mit anderem Arm, ist es eine Armverwechslung. Sonst steht der
        # Schluessel da, aber mit falschem Wert.
        feld = str(zelle.get("field") or "")
        arm = arm_von(zelle)
        # Der Arm steckt im Feldnamen: intervention_* gegen comparator_*.
        if feld.startswith("intervention"):
            spiegel_feld = "comparator" + feld[len("intervention"):]
        elif feld.startswith("comparator"):
            spiegel_feld = "intervention" + feld[len("comparator"):]
        else:
            spiegel_feld = feld
        spiegel = (spiegel_feld, "comparator" if arm == "intervention" else "intervention")
        # Armverwechslung: der gespiegelte Schluessel traegt genau diesen Goldwert.
        # Das ist der Fall 456/459: die Zellen stehen da, aber unter dem anderen Arm.
        spiegel_traegt_wert = any(
            (str(k.get("field") or ""), arm_von(k)) == spiegel
            and zahl(k.get("value")) is not None
            and abs(zahl(k.get("value")) - soll) < 1e-6
            for k in vor
        )
        if spiegel_traegt_wert:
            klassen["arm_vertauscht"] += 1
        elif vor_keys.get(key):
            klassen["wert_abweichend"] += 1
        elif any(str(k.get("field") or "") == feld for k in vor):
            klassen["arm_vertauscht"] += 1
        else:
            klassen["fehlende_extraktion"] += 1
    for i, kandidat in enumerate(vor):
        if verbraucht[i]:
            continue
        key = (str(kandidat.get("field") or ""), arm_von(kandidat))
        if key in gold_keys:
            klassen["dublette_oder_wert"] += 1
        elif str(kandidat.get("field") or "") in gold_felder:
            klassen["arm_vertauscht"] += 1
        else:
            klassen["fremdschluessel"] += 1
    return dict(klassen)


def meta(zeilen: list[dict[str, Any]]) -> dict[str, Any]:
    versionen = Counter(str(z.get("prompt_version") or "") for z in zeilen)
    modelle = Counter(str(z.get("model_id") or "") for z in zeilen)
    tokens = [z.get("completion_tokens") for z in zeilen if z.get("completion_tokens")]
    return {
        "zeilen": len(zeilen),
        "prompt_version": dict(versionen),
        "modell": dict(modelle),
        "completion_tokens_median": sorted(tokens)[len(tokens) // 2] if tokens else None,
        "completion_tokens_max": max(tokens) if tokens else None,
        "fehlerklassen": dict(Counter(str(z.get("fehlerklasse") or "ok") for z in zeilen)),
        "finish_reason": dict(Counter(str(z.get("finish_reason") or "") for z in zeilen)),
        "mit_zellen": sum(1 for z in zeilen if zellen(z)),
    }


def main() -> int:
    records = {r["record_id"]: r for r in lade(RECORDS)}
    ids = list(json.loads(AUSWAHL.read_text(encoding="utf-8")).get("ids") or [])
    ids = [i for i in ids if i in records]

    def index(pfad: Path) -> dict[str, dict[str, Any]]:
        return {z["record_id"]: z for z in lade(pfad) if z.get("model") == "glm"}

    glm = index(GLM)
    lese = index(LESEKOPIE)
    p5 = index(P5)

    print("GLM-Zeilen:", len(glm), "| Lesekopie-Zeilen:", len(lese), "| P5-Zeilen:", len(p5))
    print("Auswahl-IDs:", len(ids))
    print("GLM-Meta:", json.dumps(meta(list(glm.values())), ensure_ascii=False))
    print("P5-Meta:", json.dumps(meta(list(p5.values())), ensure_ascii=False))

    mengen = {
        "alle_699": sorted(records),
        "auswahl_103": sorted(ids),
        "auswahl_102": [i for i in sorted(ids) if i != NICHT_BEWERTBAR],
        "rest_596": sorted(set(records) - set(ids)),
        # Die 559 Zeilen, auf denen der dokumentierte Pilot F1 0,809 meldet:
        # nur Records, deren GLM-Zeile mindestens eine Zelle traegt.
        "nur_mit_zellen_559": sorted(r for r in records if zellen(glm.get(r))),
    }
    if len(ids) != 103:
        mengen["auswahl_103"] = sorted(ids)

    ergebnis: dict[str, Any] = {
        "quellen": {"glm": str(GLM), "lesekopie": str(LESEKOPIE), "p5": str(P5),
                    "records": str(RECORDS), "auswahl": str(AUSWAHL)},
        "meta": {"glm_referenz": meta(list(glm.values())), "p5": meta(list(p5.values())),
                 "lesekopie": meta(list(lese.values()))},
        "mengen": {}, "records": {},
    }

    for name, menge in mengen.items():
        block: dict[str, Any] = {"records": len(menge)}
        for system, quelle in (("glm", glm), ("p5", p5), ("lesekopie", lese)):
            goldzellen = sum(len((records[r]["gold"] or {}).get("cells") or []) for r in menge
                             if r in records)
            b_p5 = [bilanz_p5((records[r]["gold"] or {}).get("cells") or [], zellen(quelle.get(r)))
                    for r in menge]
            b_yun = [bilanz_yun((records[r]["gold"] or {}).get("cells") or [], zellen(quelle.get(r)))
                     for r in menge]
            block[system] = {
                "goldzellen": goldzellen,
                "ohne_zeile": sum(1 for r in menge if r not in quelle),
                "logik_p5": kennzahlen(b_p5, "p5"),
                "logik_yun699": kennzahlen(b_yun, "yun699"),
            }
        ergebnis["mengen"][name] = block

    # Szenarien ohne Modellaufruf, nur aus vorhandenen Predictions gerechnet:
    # (a) Hybrid = GLM auf den 596 uebrigen Records plus P5 auf den 102 bewertbaren
    #     der Auswahl. Beantwortet: was bringt P5 fuer die Gesamtpipeline?
    # (b) Dedupe = je (Feld, Arm) nur eine Vorhersagezelle behalten. Beantwortet:
    #     was bringt ein reiner Nachfilter gegen Dubletten, ohne Modellaufruf?
    hybrid_bilanzen = []
    for r in mengen["rest_596"]:
        hybrid_bilanzen.append(bilanz_p5((records[r]["gold"] or {}).get("cells") or [], zellen(glm.get(r))))
    for r in mengen["auswahl_102"]:
        hybrid_bilanzen.append(bilanz_p5((records[r]["gold"] or {}).get("cells") or [], zellen(p5.get(r))))
    ergebnis["szenarien"] = {"hybrid_596_plus_102": kennzahlen(hybrid_bilanzen, "p5")}

    def dedupe(gold: list[dict[str, Any]], vor: list[dict[str, Any]], beste: bool) -> dict[str, int]:
        gruppen: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for zelle in vor:
            gruppen.setdefault((str(zelle.get("field") or ""), arm_von(zelle)), []).append(zelle)
        gewaehlt = []
        for kandidaten in gruppen.values():
            if not beste:
                gewaehlt.append(kandidaten[0])
                continue
            soll = next((zahl(z.get("value")) for z in gold
                         if (str(z.get("field") or ""), arm_von(z)) ==
                         (str(kandidaten[0].get("field") or ""), arm_von(kandidaten[0]))), None)
            treffer = next((k for k in kandidaten if soll is not None and zahl(k.get("value")) is not None
                            and abs(zahl(k.get("value")) - soll) < 1e-6), kandidaten[0])
            gewaehlt.append(treffer)
        return bilanz_p5(gold, gewaehlt)

    for name, beste in (("dedupe_erste_zelle", False), ("dedupe_beste_zelle", True)):
        b = [dedupe((records[r]["gold"] or {}).get("cells") or [], zellen(p5.get(r)), beste)
             for r in mengen["auswahl_102"]]
        ergebnis["szenarien"][name] = kennzahlen(b, "p5")

    # Record-Ebene auf der Auswahl: beide Systeme, beide Logiken.
    detail: dict[str, Any] = {}
    for r in mengen["auswahl_103"]:
        gold = (records[r]["gold"] or {}).get("cells") or []
        eintrag: dict[str, Any] = {"goldzellen": len(gold)}
        for system, quelle in (("glm", glm), ("p5", p5)):
            vor = zellen(quelle.get(r))
            b = bilanz_p5(gold, vor)
            eintrag[system] = {
                **b, **quote(b["tp"], b["fp"], b["fn"]),
                "zellen": len(vor),
                "klassen": fehlerklassen_record(gold, vor),
                "fehlerklasse": (quelle.get(r) or {}).get("fehlerklasse") or "",
                "completion_tokens": (quelle.get(r) or {}).get("completion_tokens"),
                "reasoning_chars": (quelle.get(r) or {}).get("reasoning_chars"),
            }
        detail[r] = eintrag
    ergebnis["records"] = detail

    # Fehlerklassen ueber die Auswahl, je System.
    klassen_summe: dict[str, Counter] = {"glm": Counter(), "p5": Counter()}
    for eintrag in detail.values():
        for system in ("glm", "p5"):
            klassen_summe[system].update(eintrag[system]["klassen"])
    ergebnis["fehlerklassen_auswahl"] = {k: dict(v) for k, v in klassen_summe.items()}

    # Nach Fehlerart sortierte Schwerpunktlisten: wo P5 trotz Zellen verliert.
    ergebnis["schwachstellen_p5"] = {
        "meiste_fn": sorted((r for r in detail if detail[r]["goldzellen"]),
                            key=lambda r: detail[r]["p5"]["fn"], reverse=True)[:10],
        "meiste_fp": sorted((r for r in detail if detail[r]["goldzellen"]),
                            key=lambda r: detail[r]["p5"]["fp"], reverse=True)[:10],
    }

    # Top-Abweichungen in TP und F1.
    def f1_von(e: dict[str, Any], system: str) -> float:
        return e[system]["f1"] or 0.0

    top_tp = sorted(
        (r for r in detail if detail[r]["goldzellen"]),
        key=lambda r: (detail[r]["p5"]["tp"] - detail[r]["glm"]["tp"]),
        reverse=True,
    )[:12]
    top_f1 = sorted(
        (r for r in detail if detail[r]["goldzellen"]),
        key=lambda r: (f1_von(detail[r], "p5") - f1_von(detail[r], "glm")),
        reverse=True,
    )[:12]
    ergebnis["top"] = {"tp_plus": top_tp, "f1_plus": top_f1}

    (HIER / "vergleich_20261120.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("geschrieben:", HIER / "vergleich_20261120.json")

    for name, block in ergebnis["mengen"].items():
        print(f"\n=== {name} ({block['records']} Records, {block['glm']['goldzellen']} Goldzellen)")
        for system in ("glm", "p5", "lesekopie"):
            s = block[system]
            for logik in ("logik_p5", "logik_yun699"):
                k = s[logik]
                print(f"  {system:<10} {logik:<12} TP {k['tp']:>4} FP {k['fp']:>4} "
                      f"FN {k['fn']:>4} P {k['precision']} R {k['recall']} F1 {k['f1']}")
    print("\nSzenarien:", json.dumps(ergebnis["szenarien"], ensure_ascii=False))
    print("\nFehlerklassen auf der Auswahl:", json.dumps(ergebnis["fehlerklassen_auswahl"], ensure_ascii=False))
    print("\nTop TP-Gewinn P5 gegen GLM:")
    for r in top_tp:
        d = detail[r]
        print(f"  {r:<14} gold {d['goldzellen']:>2} TP glm {d['glm']['tp']} p5 {d['p5']['tp']} "
              f"FP p5 {d['p5']['fp']} FN p5 {d['p5']['fn']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
