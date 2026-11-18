#!/usr/bin/env python
"""Kontrollierter Versuch zur iterativen Extraktion.

Zwei Phasen, damit der Ablauf reproduzierbar bleibt:

1. `--plan`: zieht eine Zufallsstichprobe von Records, die mindestens eine
   fehlende GLM-Zelle haben, und schreibt `stichprobe.json` sowie
   `zellen.json` (die fehlenden Zellen, die das Retrieval bearbeitet).
2. `--auswerten`: liest die Retrieval-Antworten und vergleicht vier Varianten
   gegen denselben Goldstandard:

   A  urspruengliche GLM-Extraktion
   B  A + Cell-Level-Retrieval (GLM), nur belegte Antworten
   C  A + Evidenzaufloesung aus zwei Modellen (kein Mehrheitsentscheid)
   D  C + Pruefregeln (Zellen mit hartem Verstoss fallen weg)

Gemessen wird ueber **alle** Goldzellen der Stichproben-Records, nicht nur
ueber die fehlenden: sonst waere die Precision der Variante A nicht definiert.

Aufruf:
    python experiment.py --plan --n-records 20 --seed 20261117 --out-dir ergebnisse/exp1
    python zell_retrieval.py --zellen ergebnisse/exp1/zellen.json --modelle glm qwen30 \
        --out ergebnisse/exp1/antworten.jsonl --workers 2
    python experiment.py --auswerten --out-dir ergebnisse/exp1
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import gemeinsam as g
import zell_pruefung as pruefung


def lade_gold(records: dict[str, dict]) -> dict[str, dict[str, float]]:
    return {rid: g.gold_werte(rec) for rid, rec in records.items()}


def plan(args: argparse.Namespace) -> int:
    records = g.lade_records()
    zeilen = g.lade_modell(g.lies(g.VORLAUF), "glm")
    kandidaten = []
    for rid in sorted(records):
        gold = g.gold_werte(records[rid])
        modell = g.modell_werte(zeilen.get(rid, {}))
        fehlend = [feld for feld in gold if feld not in modell]
        if fehlend:
            kandidaten.append((rid, fehlend, bool(zeilen.get(rid, {}).get("fehlerklasse"))))

    zufall = random.Random(args.seed)
    # Stratifiziert: die Haelfte aus Records mit technischem Ausfall, die andere
    # Haelfte aus Records, die geantwortet haben. Sonst waere die Stichprobe zu
    # 65 % Ausfaelle, und der Retrieval-Effekt auf echte Auslassungen bliebe
    # unbeobachtet.
    ausfall = [k for k in kandidaten if k[2]]
    normal = [k for k in kandidaten if not k[2]]
    je = args.n_records // 2
    gewaehlt = zufall.sample(ausfall, min(je, len(ausfall))) + zufall.sample(normal, min(args.n_records - je, len(normal)))
    gewaehlt.sort()

    zellen = [{"record_id": rid, "feld": feld} for rid, felder, _ in gewaehlt for feld in felder]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "stichprobe.json").write_text(
        json.dumps(
            {
                "seed": args.seed,
                "n_records": len(gewaehlt),
                "records": [
                    {"record_id": rid, "technischer_ausfall": ausf, "fehlende_zellen": felder}
                    for rid, felder, ausf in gewaehlt
                ],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    (args.out_dir / "zellen.json").write_text(json.dumps(zellen, ensure_ascii=False, indent=1), encoding="utf-8")

    gold_zellen = sum(len(g.gold_werte(records[rid])) for rid, _, _ in gewaehlt)
    print(f"{len(gewaehlt)} Records, {gold_zellen} Goldzellen, {len(zellen)} fehlende Zellen")
    print(f"  davon technische Ausfaelle: {sum(1 for _, _, a in gewaehlt if a)} Records")
    print(f"geschrieben: {args.out_dir}/stichprobe.json, zellen.json")
    return 0


def _treffer(gold: float, wert: float) -> bool:
    return abs(float(gold) - float(wert)) < 1e-9


def _metriken(richtig: int, falsch: int, fehlend: int) -> dict:
    praezision = richtig / (richtig + falsch) if (richtig + falsch) else 0.0
    recall = richtig / (richtig + falsch + fehlend) if (richtig + falsch + fehlend) else 0.0
    f1 = 2 * praezision * recall / (praezision + recall) if (praezision + recall) else 0.0
    return {
        "richtig": richtig,
        "falsch": falsch,
        "fehlend": fehlend,
        "precision": round(praezision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def loese_evidenz(antworten: list[dict], record: dict, feld: str) -> dict | None:
    """Evidenzaufloesung zwischen zwei Modellen (kein Mehrheitsentscheid).

    Akzeptiert wird eine Antwort nur, wenn ihr Zitat woertlich im Dokument steht
    und den Wert enthaelt. Bei zwei belegten, aber unterschiedlichen Werten
    entscheidet der Armbezug im Zitat; bleibt er unklar, wird die Zelle
    ausgelassen.
    """
    belegt = [a for a in antworten if a.get("verifiziert") and a.get("wert") is not None]
    if not belegt:
        return None
    if len({round(a["wert"], 9) for a in belegt}) == 1:
        return belegt[0]
    arm_name = str(
        record["context"].get("intervention" if feld.startswith("intervention") else "comparator") or ""
    ).lower()
    passend = [a for a in belegt if arm_name and arm_name in f"{a.get('column_label','')} {a.get('zitat','')}".lower()]
    if len(passend) == 1:
        return passend[0]
    return None


def auswerten(args: argparse.Namespace) -> int:
    records = g.lade_records()
    zeilen = g.lade_modell(g.lies(g.VORLAUF), "glm")
    plan_daten = json.loads((args.out_dir / "stichprobe.json").read_text(encoding="utf-8"))
    gewaehlt = [e["record_id"] for e in plan_daten["records"]]

    # Fehlende Antwortdatei ist kein Fehler, sondern der Fall "noch nichts
    # gelaufen": dann bleiben B, C und D gleich A.
    antwort_pfad = args.out_dir / "antworten.jsonl"
    roh = g.lies(antwort_pfad) if antwort_pfad.exists() else []
    # Doppelte Zeilen (z. B. nach einem abgebrochenen und neu gestarteten
    # Durchlauf) werden auf die letzte Zeile je Zelle und Modell reduziert.
    gesehen: dict[tuple[str, str, str], dict] = {}
    doppelt = 0
    for antwort in roh:
        schluessel = (antwort["record_id"], antwort["feld"], str(antwort.get("modell")))
        if schluessel in gesehen:
            doppelt += 1
        gesehen[schluessel] = antwort
    antworten = list(gesehen.values())

    nach_zelle: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for antwort in antworten:
        nach_zelle[(antwort["record_id"], antwort["feld"])].append(antwort)

    erg: dict[str, dict] = {"A": {}, "B": {}, "C": {}, "D": {}}
    detail: dict[str, list[dict]] = defaultdict(list)
    verworfen: list[dict] = []

    for rid in gewaehlt:
        record = records[rid]
        gold = g.gold_werte(record)
        basis = g.modell_werte(zeilen.get(rid, {}))

        # A: unveraendert
        zellen_a = dict(basis)

        # B: belegte GLM-Retrieval-Antworten ergaenzen
        zellen_b = dict(basis)
        for feld in gold:
            if feld in zellen_b:
                continue
            kandidaten = [a for a in nach_zelle.get((rid, feld), []) if a["modell"] == "glm"]
            belegt = [a for a in kandidaten if a.get("verifiziert") and a.get("wert") is not None]
            if belegt:
                zellen_b[feld] = belegt[0]["wert"]
                detail["B"].append({"record_id": rid, "feld": feld, "wert": belegt[0]["wert"]})

        # C: Evidenzaufloesung ueber beide Modelle
        zellen_c = dict(basis)
        zellen_c_neu: dict[str, dict] = {}
        for feld in gold:
            if feld in zellen_c:
                continue
            gewaehlt_antwort = loese_evidenz(nach_zelle.get((rid, feld), []), record, feld)
            if gewaehlt_antwort:
                zellen_c[feld] = gewaehlt_antwort["wert"]
                zellen_c_neu[feld] = gewaehlt_antwort
                detail["C"].append(
                    {
                        "record_id": rid,
                        "feld": feld,
                        "wert": gewaehlt_antwort["wert"],
                        "modell": gewaehlt_antwort["modell"],
                        "zitat": (gewaehlt_antwort.get("zitat") or "")[:300],
                    }
                )

        # D: C mit Pruefregeln
        akzeptiert, abgelehnt = pruefung.filtere(record, zellen_c_neu, basis=zellen_c)
        verworfen.extend({"record_id": rid, **eintrag} for eintrag in abgelehnt)
        zellen_d = dict(basis)
        gemischt = pruefung.pruefe_zeitpunkt(list(akzeptiert.values()))
        if gemischt:
            verworfen.append({"record_id": rid, "gruende": gemischt, "feld": "*"})
            akzeptiert = {}
        for feld, eintrag in akzeptiert.items():
            zellen_d[feld] = eintrag["wert"]
            detail["D"].append({"record_id": rid, "feld": feld, "wert": eintrag["wert"]})

        for name, zellen in (("A", zellen_a), ("B", zellen_b), ("C", zellen_c), ("D", zellen_d)):
            richtig = falsch = fehlend = 0
            for feld, wert in gold.items():
                if feld not in zellen:
                    fehlend += 1
                elif _treffer(wert, zellen[feld]):
                    richtig += 1
                else:
                    falsch += 1
            erg[name].setdefault("zellen", {"richtig": 0, "falsch": 0, "fehlend": 0})
            erg[name]["zellen"]["richtig"] += richtig
            erg[name]["zellen"]["falsch"] += falsch
            erg[name]["zellen"]["fehlend"] += fehlend

    for name in erg:
        z = erg[name]["zellen"]
        erg[name]["metriken"] = _metriken(z["richtig"], z["falsch"], z["fehlend"])
        erg[name]["hinzugefuegt"] = len(detail.get(name, []))

    # Wie viele der Stichproben-Zellen waeren ueberhaupt auffindbar?
    auffindbar = 0
    zellen_gesamt = 0
    for rid in gewaehlt:
        record = records[rid]
        doc = g.dokument(record)
        gold = g.gold_werte(record)
        basis = g.modell_werte(zeilen.get(rid, {}))
        # Nicht `roh` nennen: der Name traegt oben die eingelesenen
        # Antwortzeilen und wird hier sonst ueberschrieben.
        gold_roh = g.gold_roh(record)
        for feld in gold:
            if feld in basis:
                continue
            zellen_gesamt += 1
            if g.finde_zahl(doc, gold_roh.get(feld, "")):
                auffindbar += 1

    token = Counter()
    for antwort in antworten:
        token[antwort["modell"]] += int(antwort.get("completion_tokens") or 0)
    zeit = sum(float(a.get("elapsed_s") or 0) for a in antworten)

    ergebnis = {
        "antworten": {
            "zeilen_roh": len(roh),
            "eindeutig": len(antworten),
            "doppelte_verworfen": doppelt,
            "datei_vorhanden": antwort_pfad.exists(),
        },
        "stichprobe": plan_daten,
        "varianten": erg,
        "auffindbarkeit": {
            "fehlende_zellen": zellen_gesamt,
            "wert_im_auszug_vorhanden": auffindbar,
            "anteil": round(auffindbar / zellen_gesamt, 4) if zellen_gesamt else 0.0,
        },
        "verworfen_durch_pruefung": verworfen,
        "detail": {k: v for k, v in detail.items()},
        "tokens": dict(token),
        "zeit_summiert_s": round(zeit, 1),
    }
    (args.out_dir / "ergebnis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Stichprobe: {len(gewaehlt)} Records, {zellen_gesamt} fehlende Zellen, "
          f"davon {auffindbar} im Auszug vorhanden ({auffindbar / max(zellen_gesamt, 1):.1%})")
    print(f"{'Var':4} {'richtig':>7} {'falsch':>7} {'fehlend':>8} {'Prec':>7} {'Recall':>7} {'F1':>7} {'neu':>4}")
    for name in ("A", "B", "C", "D"):
        m = erg[name]["metriken"]
        print(
            f"{name:4} {m['richtig']:7} {m['falsch']:7} {m['fehlend']:8} "
            f"{m['precision']:7.3f} {m['recall']:7.3f} {m['f1']:7.3f} {erg[name]['hinzugefuegt']:4}"
        )
    print(f"verworfen durch Pruefung: {len(verworfen)}; Tokens: {dict(token)}; Zeit: {zeit:.0f}s")
    print(f"geschrieben: {args.out_dir / 'ergebnis.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--auswerten", action="store_true")
    parser.add_argument("--n-records", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261117)
    args = parser.parse_args()
    if args.plan:
        return plan(args)
    if args.auswerten:
        return auswerten(args)
    parser.error("--plan oder --auswerten angeben")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
