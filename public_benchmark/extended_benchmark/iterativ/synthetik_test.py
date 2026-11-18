#!/usr/bin/env python
"""Synthetischer Test des Auswertungspfads (A bis D) ohne Netzzugriff.

Der Test legt eine eigene Kopie der Stichprobe an, schreibt erfundene, aber
gezielt konstruierte Modellantworten und laesst `experiment.py --auswerten`
darueber laufen. Damit ist jede Verzweigung mindestens einmal belegt:

* A  unveraenderte GLM-Zellen,
* B  belegte Retrieval-Antwort (nur GLM),
* C  Evidenzaufloesung zweier Modelle inklusive Enthaltung bei Streit,
* D  Pruefregeln, die eine Zelle mit hartem Verstoss verwerfen.

Die Antworten sind **synthetisch** und haben keinen Beweiswert fuer die
Modellqualitaet; geprueft wird ausschliesslich die Auswertelogik. Die echte
Stichprobe unter `ergebnisse/exp1` wird nicht angefasst.

Aufruf:
    python synthetik_test.py --quelle ergebnisse/exp1 --out-dir ergebnisse/exp1_synthetisch
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import gemeinsam as g
import experiment as exp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quelle", type=Path, default=Path("ergebnisse/exp1"))
    parser.add_argument("--out-dir", type=Path, default=Path("ergebnisse/exp1_synthetisch"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("stichprobe.json", "zellen.json"):
        shutil.copyfile(args.quelle / name, args.out_dir / name)

    records = g.lade_records()
    zellen = json.loads((args.out_dir / "zellen.json").read_text(encoding="utf-8"))

    zeilen: list[dict] = []
    faelle: list[str] = []
    streit_ohne_arm: set[tuple[str, str]] = set()
    harte_faelle: set[tuple[str, str]] = set()
    # Der harte Verstoss braucht eine Ereigniszelle (negatives Ereignis).
    # Deshalb wird der Fall nicht ueber den Index, sondern ueber das Feld
    # zugewiesen; sonst faellt er auf Zellen, bei denen er nicht greift.
    ereignis_indizes = [i for i, z in enumerate(zellen) if z["feld"].endswith("_events")]
    harte_indizes = set(ereignis_indizes[:2])
    for nummer, zelle in enumerate(zellen):
        rid, feld = zelle["record_id"], zelle["feld"]
        record = records[rid]
        gold = g.gold_werte(record).get(feld)
        if gold is None:
            continue
        arm = "intervention" if feld.startswith("intervention") else "comparator"
        arm_name = str(record["context"].get(arm) or "")
        anderer = str(record["context"].get("comparator" if arm == "intervention" else "intervention") or "")
        fall = nummer % 6
        if nummer in harte_indizes:
            # Harter Verstoss: nur auf Zellen, bei denen eine harte Regel
            # ueberhaupt greifen kann (Ereignis, SD, Gruppengroesse).
            fall = 5
        elif fall == 5:
            fall = 0
        werte = {
            "glm": {"wert": gold, "verifiziert": True, "column_label": arm_name, "zitat": "synthetisch"},
            "qwen30": {"wert": gold, "verifiziert": True, "column_label": arm_name, "zitat": "synthetisch"},
        }
        if fall == 1:
            werte["qwen30"] = {"wert": gold + 1, "verifiziert": True, "column_label": anderer, "zitat": "synthetisch"}
            name = "streit_armbezug_glm"
        elif fall == 2:
            werte["glm"]["verifiziert"] = False
            name = "nur_qwen_belegt"
        elif fall == 3:
            werte["glm"] = {"wert": gold + 1, "verifiziert": True, "column_label": "", "zitat": "synthetisch"}
            werte["qwen30"] = {"wert": gold + 2, "verifiziert": True, "column_label": "", "zitat": "synthetisch"}
            name = "streit_ohne_armbezug_enthaltung"
            streit_ohne_arm.add((rid, feld))
        elif fall == 4:
            werte["glm"] = {"wert": gold + 5, "verifiziert": True, "column_label": "", "zitat": "synthetisch"}
            werte["qwen30"] = {"wert": gold + 5, "verifiziert": True, "column_label": "", "zitat": "synthetisch"}
            name = "beide_gleich_falsch"
        elif fall == 5:
            werte["glm"] = {"wert": -5, "verifiziert": True, "column_label": "", "zitat": "synthetisch"}
            werte["qwen30"] = {"wert": -5, "verifiziert": True, "column_label": "", "zitat": "synthetisch"}
            name = "harter_verstoss_negativ"
            harte_faelle.add((rid, feld))
        else:
            name = "beide_richtig"
        faelle.append(name)
        for modell, eintrag in werte.items():
            zeilen.append(
                {
                    "record_id": rid,
                    "feld": feld,
                    "modell": modell,
                    "wert": eintrag["wert"],
                    "verifiziert": eintrag["verifiziert"],
                    "zitat": eintrag["zitat"],
                    "column_label": eintrag["column_label"],
                    "row_label": "",
                    "note": "synthetisch",
                    "http_status": 200,
                    "completion_tokens": 10,
                    "elapsed_s": 0.1,
                }
            )

    (args.out_dir / "antworten.jsonl").write_text(
        "\n".join(json.dumps(z, ensure_ascii=False) for z in zeilen) + "\n", encoding="utf-8"
    )

    print(f"{len(zellen)} Zellen, {len(zeilen)} synthetische Antworten, Faelle:")
    from collections import Counter

    for name, anzahl in Counter(faelle).most_common():
        print(f"  {name:34} {anzahl}")

    # Auswertung ueber denselben Code wie im echten Versuch.
    args_aus = argparse.Namespace(out_dir=args.out_dir, n_records=0, seed=0, plan=False, auswerten=True)
    exp.auswerten(args_aus)

    ergebnis = json.loads((args.out_dir / "ergebnis.json").read_text(encoding="utf-8"))
    v = ergebnis["varianten"]
    pruefungen = {
        "A_unveraendert": v["A"]["hinzugefuegt"] == 0,
        "B_gewinn_moeglich": v["B"]["metriken"]["richtig"] >= v["A"]["metriken"]["richtig"],
        "B_nur_belegte": v["B"]["hinzugefuegt"] > 0,
        "C_nicht_schlechter_als_B": v["C"]["metriken"]["richtig"] >= v["B"]["metriken"]["richtig"],
        "C_enthaltung_bei_streit": bool(streit_ohne_arm)
        and not any((d["record_id"], d["feld"]) in streit_ohne_arm for d in ergebnis["detail"].get("C", [])),
        "D_verwirft_nur_den_harten_fall": bool(harte_faelle)
        and not any((d["record_id"], d["feld"]) in harte_faelle for d in ergebnis["detail"].get("D", [])),
        "D_verwirft_harten_verstoss": any(
            "negatives_ereignis" in (w.get("gruende") or []) for w in ergebnis["verworfen_durch_pruefung"]
        ),
        "D_nicht_mehr_falsch_als_C": v["D"]["metriken"]["falsch"] <= v["C"]["metriken"]["falsch"],
        "D_nicht_weniger_richtig_als_A": v["D"]["metriken"]["richtig"] >= v["A"]["metriken"]["richtig"],
    }
    args.out_dir.joinpath("synthetik_pruefung.json").write_text(
        json.dumps({"pruefungen": pruefungen, "varianten": v, "faelle": Counter(faelle)}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print()
    for name, ok in pruefungen.items():
        print(f"  {'OK  ' if ok else 'FEHL'} {name}")
    print(f"bestanden: {sum(pruefungen.values())}/{len(pruefungen)}")
    return 0 if all(pruefungen.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
