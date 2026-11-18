#!/usr/bin/env python
"""Offline-Messungen zur iterativen Extraktion (ohne API).

Zwei Auswertungen, die ohne Netzzugriff belastbar sind:

1. **Pruefregeln gegen den bestehenden GLM-Lauf.** Wie viele der 281 falschen
   Zellen faengt die Pruefung ab, und wie viele der 1.840 richtigen Zellen
   verwirft sie faelschlich? Das ist die Wirksamkeit des Gates aus Variante D,
   gemessen ohne einen einzigen Modellaufruf.

2. **Auffindbarkeit im gelieferten Auszug.** Fuer die Stichprobenzellen: steht
   die Goldzahl ueberhaupt im Text? Nur solche Zellen kann ein Retrieval
   gewinnen; der Rest ist eine Obergrenze fuer jede Retrieval-Variante.

Aufruf:
    python pruefung_offline.py --out ergebnisse/pruefung_offline.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import gemeinsam as g
import zell_pruefung as pruefung


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--modell", default="glm")
    args = parser.parse_args()

    records = g.lade_records()
    zeilen = g.lade_modell(g.lies(g.VORLAUF), args.modell)
    gold_alle = {rid: g.gold_werte(r) for rid, r in records.items()}

    richtig = falsch = 0
    flag_richtig = flag_falsch = 0
    hart_richtig = hart_falsch = 0
    je_regel = Counter()
    regel_richtig = Counter()
    beispiele: list[dict] = []

    for rid, record in records.items():
        zeile = zeilen.get(rid, {})
        modell = g.modell_werte(zeile)
        gold = gold_alle[rid]
        for feld, wert in modell.items():
            if feld not in gold:
                continue
            korrekt = abs(float(gold[feld]) - float(wert)) < 1e-9
            verstoesse = pruefung.pruefe_zelle(record, feld, wert, modell)
            if korrekt:
                richtig += 1
            else:
                falsch += 1
            if any(v in pruefung.HARTE_REGELN for v in verstoesse):
                if korrekt:
                    hart_richtig += 1
                else:
                    hart_falsch += 1
            if verstoesse:
                if korrekt:
                    flag_richtig += 1
                else:
                    flag_falsch += 1
                    if len(beispiele) < 12:
                        beispiele.append(
                            {
                                "record_id": rid,
                                "feld": feld,
                                "modell": wert,
                                "gold": gold[feld],
                                "gruende": verstoesse,
                            }
                        )
                for regel in verstoesse:
                    je_regel[regel] += 1
                    if korrekt:
                        regel_richtig[regel] += 1

    gesamt = richtig + falsch
    ergebnis = {
        "modell": args.modell,
        "zellen_bewertet": gesamt,
        "richtig": richtig,
        "falsch": falsch,
        "gate": {
            "geflaggt_gesamt": flag_richtig + flag_falsch,
            "geflaggt_falsch": flag_falsch,
            "geflaggt_richtig": flag_richtig,
            "trefferquote_des_gates": round(flag_falsch / max(flag_richtig + flag_falsch, 1), 4),
            "anteil_falscher_zellen_erkannt": round(flag_falsch / max(falsch, 1), 4),
            "anteil_richtiger_zellen_verworfen": round(flag_richtig / max(richtig, 1), 4),
            "precision_der_verbleibenden": round(max(richtig - flag_richtig, 0) / max(gesamt - flag_richtig - flag_falsch, 1), 4),
        },
        "gate_hart": {
            "regeln": sorted(pruefung.HARTE_REGELN),
            "geflaggt_gesamt": hart_richtig + hart_falsch,
            "geflaggt_falsch": hart_falsch,
            "geflaggt_richtig": hart_richtig,
            "trefferquote_des_gates": round(hart_falsch / max(hart_richtig + hart_falsch, 1), 4),
            "anteil_falscher_zellen_erkannt": round(hart_falsch / max(falsch, 1), 4),
            "anteil_richtiger_zellen_verworfen": round(hart_richtig / max(richtig, 1), 4),
            "precision_der_verbleibenden": round(
                max(richtig - hart_richtig, 0) / max(gesamt - hart_richtig - hart_falsch, 1), 4
            ),
        },
        "je_regel": {regel: {"gesamt": n, "davon_richtig": regel_richtig[regel]} for regel, n in je_regel.most_common()},
        "beispiele": beispiele,
    }

    # Auffindbarkeit in der Experiment-Stichprobe
    stichprobe = Path("ergebnisse/exp1/stichprobe.json")
    if stichprobe.exists():
        plan = json.loads(stichprobe.read_text(encoding="utf-8"))
        auffindbar = 0
        gesamt_stich = 0
        je_kat = Counter()
        for eintrag in plan["records"]:
            rid = eintrag["record_id"]
            record = records[rid]
            doc = g.dokument(record)
            roh = g.gold_roh(record)
            for feld in eintrag["fehlende_zellen"]:
                gesamt_stich += 1
                gefunden = bool(g.finde_zahl(doc, roh.get(feld, "")))
                auffindbar += int(gefunden)
                je_kat["im_auszug" if gefunden else "nicht_im_auszug"] += 1
        ergebnis["stichprobe_auffindbarkeit"] = {
            "zellen": gesamt_stich,
            "im_auszug": auffindbar,
            "anteil": round(auffindbar / max(gesamt_stich, 1), 4),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")

    gate = ergebnis["gate"]
    print(f"Zellen: {gesamt} ({richtig} richtig, {falsch} falsch)")
    print(
        f"Gate: {gate['geflaggt_gesamt']} markiert, davon {gate['geflaggt_falsch']} falsch und "
        f"{gate['geflaggt_richtig']} richtig"
    )
    print(
        f"  erkennt {gate['anteil_falscher_zellen_erkannt']:.1%} der falschen Zellen, "
        f"verwirft {gate['anteil_richtiger_zellen_verworfen']:.1%} der richtigen"
    )
    print(f"  Precision der verbleibenden Zellen: {gate['precision_der_verbleibenden']:.4f}")
    hart = ergebnis["gate_hart"]
    print(
        f"Gate (nur harte Regeln): {hart['geflaggt_gesamt']} markiert, davon {hart['geflaggt_falsch']} falsch / "
        f"{hart['geflaggt_richtig']} richtig -> {hart['anteil_falscher_zellen_erkannt']:.1%} der falschen erkannt, "
        f"{hart['anteil_richtiger_zellen_verworfen']:.1%} der richtigen verworfen, Precision danach "
        f"{hart['precision_der_verbleibenden']:.4f}"
    )
    for regel, werte in ergebnis["je_regel"].items():
        print(f"  {regel:34} {werte['gesamt']:4} (davon richtig {werte['davon_richtig']:3})")
    if "stichprobe_auffindbarkeit" in ergebnis:
        st = ergebnis["stichprobe_auffindbarkeit"]
        print(f"Stichprobe: {st['im_auszug']}/{st['zellen']} fehlende Zellen im Auszug auffindbar ({st['anteil']:.1%})")
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
