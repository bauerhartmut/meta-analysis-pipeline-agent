#!/usr/bin/env python
"""Schaetzt offline, was der laufende GLM-Reparaturlauf bringen kann.

Der Lauf fasst genau die 104 Ausfaelle an (`--retry-failed --repair`). Jede
Reparaturzeile ersetzt eine Fehlzeile; ihre Goldzellen zaehlen heute als
fehlend. Mehr richtige Zellen heben also den Recall, waehrend die Precision
gleich bleibt, solange die neuen Zellen so treffsicher sind wie der Bestand.

Grundlage sind ausschliesslich die 104 Ausfaelle und die 595 brauchbaren
GLM-Zeilen aus der Lesekopie. Weil es im Bestand keine einzige Zeile mit
`pfad=repair` gibt, ist die Trefferquote der Reparatur nicht gemessen — sie wird
deshalb in Szenarien variiert und als Schaetzung gekennzeichnet.

Aufruf:
    python schaetze_repair_gewinn.py --run _lesekopie_20261118 \
        --out ../iterativ/ergebnisse/qwen30_vs_glm_20261118/repair_schaetzung.md
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"


def lies(obj: Path) -> list[dict]:
    return [json.loads(z) for z in obj.read_text(encoding="utf-8").splitlines() if z.strip()]


def zellen_von(row: dict) -> dict[str, float]:
    gesehen: dict[str, float] = {}
    for zelle in row.get("rows") or []:
        gesehen.setdefault(zelle["field"], zelle["value"])
    return gesehen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--modell", default="glm")
    args = ap.parse_args()

    rows = [r for r in lies(RUNS / args.run / "predictions.jsonl") if r["model"] == args.modell]
    gold = {r["record_id"]: r for r in lies(RECORDS)}

    richtig = falsch = fehlend = 0
    for row in rows:
        gesehen = zellen_von(row)
        for c in gold[row["record_id"]]["gold"]["cells"]:
            if c["field"] not in gesehen:
                fehlend += 1
            elif abs(gesehen[c["field"]] - c["value"]) < 1e-9:
                richtig += 1
            else:
                falsch += 1
    goldzellen = richtig + falsch + fehlend

    ausfaelle = [r for r in rows if r.get("fehlerklasse")]
    gold_ausfaelle = sum(len(gold[r["record_id"]]["gold"]["cells"]) for r in ausfaelle)
    brauchbar = [r for r in rows if not r.get("fehlerklasse")]
    treffer_je_record = statistics.mean(
        sum(1 for c in gold[r["record_id"]]["gold"]["cells"]
            if c["field"] in zellen_von(r) and abs(zellen_von(r)[c["field"]] - c["value"]) < 1e-9)
        for r in brauchbar
    )
    praezision = richtig / (richtig + falsch) if richtig + falsch else 0.0

    def kennzahlen(zuwachs: int) -> dict:
        # Neue Zellen haben dieselbe Treffsicherheit wie der Bestand; die
        # zusaetzlichen Fehlgriffe wachsen entsprechend mit.
        neue_falsch = round(zuwachs * (1 - praezision) / praezision) if praezision else 0
        r2, f2 = richtig + zuwachs, falsch + neue_falsch
        rec2 = r2 / goldzellen
        p2 = r2 / (r2 + f2) if r2 + f2 else 0.0
        return {
            "richtig": r2,
            "falsch": f2,
            "recall": round(rec2, 4),
            "precision": round(p2, 4),
            "f1": round(2 * p2 * rec2 / (p2 + rec2), 4) if p2 + rec2 else 0.0,
            "zuwachs": zuwachs,
        }

    szenarien = [
        ("konservativ (40 % Erfolg, 60 % Zelltreffer)", round(gold_ausfaelle * 0.4 * 0.6)),
        ("mittel (60 % Erfolg, 78 % Zelltreffer)", round(gold_ausfaelle * 0.6 * 0.78)),
        ("Anker wie die brauchbaren Zeilen (3,09 richtige Zellen je Record)",
         round(treffer_je_record * len(ausfaelle))),
    ]
    basis = kennzahlen(0)

    z = [
        "# Was der GLM-Reparaturlauf bringen kann (Schätzung)\n",
        f"Grundlage: Lesekopie `runs/{args.run}/predictions.jsonl`, Modell {args.modell}. "
        f"{len(ausfaelle)} Ausfälle, davon "
        f"{sum(1 for r in ausfaelle if r['fehlerklasse'] == 'length_ohne_ergebnis')} `length_ohne_ergebnis` "
        f"und {sum(1 for r in ausfaelle if r['fehlerklasse'] == 'json_kaputt')} `json_kaputt`. "
        f"Diese Records tragen {gold_ausfaelle} Goldzellen; alle zählen heute als fehlend.\n",
        f"Bestand: {len(rows)} Records, {goldzellen} Goldzellen, richtig {richtig}, falsch {falsch}, "
        f"fehlend {fehlend}, Precision {basis['precision']:.4f}, Recall {basis['recall']:.4f}, "
        f"F1 {basis['f1']:.4f}.\n",
        "Die Quote der Reparatur ist **nicht gemessen**: Im Bestand gibt es keine Zeile mit "
        "`pfad=repair`. Die Szenarien spannen deshalb den plausiblen Bereich auf; alle Zahlen "
        "darin sind Schätzungen, keine Messungen. Die Precision bleibt konstant angenommen, weil "
        "neue Zellen dieselbe Treffsicherheit wie der Bestand haben dürften.\n",
        "| Szenario | richtige Zellen dazu | richtig | Recall | Precision | F1 | F1-Delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, zuwachs in szenarien:
        k = kennzahlen(zuwachs)
        z.append(
            f"| {name} | +{zuwachs} | {k['richtig']} | {k['recall']:.4f} | {k['precision']:.4f} "
            f"| {k['f1']:.4f} | {k['f1'] - basis['f1']:+.4f} |"
        )
    z.append("")
    z.append(
        f"Orientierung: Ein Recall-Punkt sind {goldzellen / 100:.0f} Zellen. Selbst das "
        f"optimistische Szenario hebt den Recall um "
        f"{(kennzahlen(szenarien[-1][1])['recall'] - basis['recall']) * 100:+.1f} Punkte, "
        f"das mittlere um {(kennzahlen(szenarien[1][1])['recall'] - basis['recall']) * 100:+.1f}.\n"
    )
    z.append(
        "Nicht enthalten: die 36 leeren Antworten ohne Ausfallklasse. Sie sind ein eigener Block "
        "(`retry_leer_ids.txt`) und laufen nicht in diesem Reparaturlauf mit.\n"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(z), encoding="utf-8")
    daten = {
        "run": args.run,
        "modell": args.modell,
        "bestand": {"records": len(rows), "goldzellen": goldzellen, "richtig": richtig,
                    "falsch": falsch, "fehlend": fehlend, **basis},
        "ausfaelle": {"records": len(ausfaelle), "goldzellen": gold_ausfaelle,
                      "richtige_zellen_je_brauchbarem_record": round(treffer_je_record, 2)},
        "szenarien": {name: kennzahlen(w) for name, w in szenarien},
    }
    args.out.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\n".join(z))
    print(f"geschrieben: {args.out} und {args.out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
