#!/usr/bin/env python
"""Synthetischer Test des Auswertungspfads (A bis D) ohne Netzzugriff.

Der Test legt eigene Kopien der Stichprobe an, schreibt erfundene, aber gezielt
konstruierte Modellantworten und laesst `experiment.py --auswerten` darueber
laufen. Geprueft werden vier Dateizustaende:

* `vollstaendig` – jede Zelle hat Antworten beider Modelle, sechs Falltypen:
  beide richtig, Streit mit Armbezug, nur ein Modell belegt, Streit ohne
  Armbezug (Enthaltung), beide gleich falsch, harter Verstoss.
* `unvollstaendig` – jede dritte Antwortzeile fehlt; der Auswerter muss
  trotzdem laufen und darf nicht mehr gewinnen als mit vollstaendiger Datei.
* `doppelt` – jede Zeile zweimal; die Duplikate muessen verworfen werden und
  das Ergebnis muss identisch zum vollstaendigen Fall sein.
* `leer` – Datei ohne Zeilen; B, C und D bleiben dann gleich A.

Die Antworten sind **synthetisch** und haben keinen Beweiswert fuer die
Modellqualitaet; geprueft wird ausschliesslich die Auswertelogik. Die echte
Stichprobe unter `ergebnisse/exp1` wird nicht angefasst.

Aufruf:
    python synthetik_test.py --quelle ergebnisse/exp1 --out-dir ergebnisse/synthetik
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import gemeinsam as g
import experiment as exp


def baue_antworten(zellen: list[dict], records: dict[str, dict]) -> tuple[list[dict], dict]:
    """Konstruiert die Antwortzeilen und merkt sich, was geprueft werden soll."""
    zeilen: list[dict] = []
    faelle: list[str] = []
    streit_ohne_arm: set[tuple[str, str]] = set()
    harte_faelle: set[tuple[str, str]] = set()
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
    return zeilen, {
        "faelle": faelle,
        "streit_ohne_arm": streit_ohne_arm,
        "harte_faelle": harte_faelle,
    }


def schreibe(ziel: Path, quelle: Path, zeilen: list[dict]) -> None:
    ziel.mkdir(parents=True, exist_ok=True)
    for name in ("stichprobe.json", "zellen.json"):
        shutil.copyfile(quelle / name, ziel / name)
    ziel.joinpath("antworten.jsonl").write_text(
        "\n".join(json.dumps(z, ensure_ascii=False) for z in zeilen) + ("\n" if zeilen else ""),
        encoding="utf-8",
    )


def werte_aus(ziel: Path) -> dict:
    exp.auswerten(argparse.Namespace(out_dir=ziel, n_records=0, seed=0, plan=False, auswerten=True))
    return json.loads((ziel / "ergebnis.json").read_text(encoding="utf-8"))


def prinzipal(ergebnis: dict, meta: dict) -> dict[str, bool]:
    """Pruefungen fuer die vollstaendige Datei."""
    v = ergebnis["varianten"]
    return {
        "A_unveraendert": v["A"]["hinzugefuegt"] == 0,
        "B_gewinn_moeglich": v["B"]["metriken"]["richtig"] >= v["A"]["metriken"]["richtig"],
        "B_nur_belegte": v["B"]["hinzugefuegt"] > 0,
        "C_nicht_schlechter_als_B": v["C"]["metriken"]["richtig"] >= v["B"]["metriken"]["richtig"],
        "C_enthaltung_bei_streit": bool(meta["streit_ohne_arm"])
        and not any(
            (d["record_id"], d["feld"]) in meta["streit_ohne_arm"]
            for d in ergebnis["detail"].get("C", [])
        ),
        "D_verwirft_nur_den_harten_fall": bool(meta["harte_faelle"])
        and not any(
            (d["record_id"], d["feld"]) in meta["harte_faelle"]
            for d in ergebnis["detail"].get("D", [])
        ),
        "D_verwirft_harten_verstoss": any(
            set(w.get("gruende") or []) & {"negatives_ereignis", "sd_nicht_positiv", "gruppengroesse_nicht_positiv"}
            for w in ergebnis["verworfen_durch_pruefung"]
        ),
        "D_nicht_mehr_falsch_als_C": v["D"]["metriken"]["falsch"] <= v["C"]["metriken"]["falsch"],
        "D_nicht_weniger_richtig_als_A": v["D"]["metriken"]["richtig"] >= v["A"]["metriken"]["richtig"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quelle", type=Path, default=Path("ergebnisse/exp1"))
    parser.add_argument("--out-dir", type=Path, default=Path("ergebnisse/synthetik"))
    args = parser.parse_args()

    records = g.lade_records()
    zellen = json.loads((args.quelle / "zellen.json").read_text(encoding="utf-8"))
    zeilen, meta = baue_antworten(zellen, records)

    print(f"{len(zellen)} Zellen, {len(zeilen)} synthetische Antworten, Faelle:")
    for name, anzahl in Counter(meta["faelle"]).most_common():
        print(f"  {name:34} {anzahl}")

    ergebnisse: dict[str, dict] = {}
    pruefungen: dict[str, bool] = {}

    # 1. vollstaendig
    voll = args.out_dir / "vollstaendig"
    schreibe(voll, args.quelle, zeilen)
    ergebnisse["vollstaendig"] = werte_aus(voll)
    pruefungen.update(prinzipal(ergebnisse["vollstaendig"], meta))

    # 2. unvollstaendig: jede dritte Zeile fehlt
    unvoll = args.out_dir / "unvollstaendig"
    gekuerzt = [z for i, z in enumerate(zeilen) if i % 3 != 2]
    schreibe(unvoll, args.quelle, gekuerzt)
    ergebnisse["unvollstaendig"] = werte_aus(unvoll)
    v_unvoll = ergebnisse["unvollstaendig"]["varianten"]
    v_voll = ergebnisse["vollstaendig"]["varianten"]
    pruefungen["U_laeuft_ohne_fehler"] = all(
        isinstance(v_unvoll[n]["metriken"]["recall"], float) for n in "ABCD"
    )
    pruefungen["U_hoechstens_so_viel_wie_vollstaendig"] = all(
        v_unvoll[n]["metriken"]["richtig"] <= v_voll[n]["metriken"]["richtig"] for n in "BCD"
    )
    pruefungen["U_B_bleibt_bei_A_ohne_beleg"] = v_unvoll["B"]["hinzugefuegt"] <= v_voll["B"]["hinzugefuegt"]

    # 3. doppelt: jede Zeile zweimal
    doppelt = args.out_dir / "doppelt"
    schreibe(doppelt, args.quelle, zeilen + zeilen)
    ergebnisse["doppelt"] = werte_aus(doppelt)
    d = ergebnisse["doppelt"]
    pruefungen["V_duplikate_erkannt"] = d["antworten"]["doppelte_verworfen"] == len(zeilen)
    pruefungen["V_ergebnis_wie_vollstaendig"] = all(
        d["varianten"][n]["metriken"] == v_voll[n]["metriken"] for n in "ABCD"
    )

    # 4. leer: Datei ohne Inhalt
    leer = args.out_dir / "leer"
    schreibe(leer, args.quelle, [])
    ergebnisse["leer"] = werte_aus(leer)
    l_erg = ergebnisse["leer"]
    a_metriken = l_erg["varianten"]["A"]["metriken"]
    pruefungen["W_leer_laeuft_ohne_fehler"] = l_erg["antworten"]["zeilen_roh"] == 0
    pruefungen["W_leer_gleich_A"] = all(l_erg["varianten"][n]["metriken"] == a_metriken for n in "BCD")
    pruefungen["W_leer_ohne_zuwachs"] = all(l_erg["varianten"][n]["hinzugefuegt"] == 0 for n in "ABCD")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "synthetik_pruefung.json").write_text(
        json.dumps(
            {
                "pruefungen": pruefungen,
                "varianten": {name: e["varianten"] for name, e in ergebnisse.items()},
                "antworten": {name: e["antworten"] for name, e in ergebnisse.items()},
                "faelle": Counter(meta["faelle"]),
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    print()
    for name, ok in pruefungen.items():
        print(f"  {'OK  ' if ok else 'FEHL'} {name}")
    print(f"bestanden: {sum(pruefungen.values())}/{len(pruefungen)}")
    return 0 if all(pruefungen.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
