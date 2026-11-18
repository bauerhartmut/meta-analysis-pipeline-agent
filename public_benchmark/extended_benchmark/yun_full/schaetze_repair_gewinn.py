#!/usr/bin/env python
"""Schaetzt offline, was der GLM-Reparaturlauf bringen kann.

Der Lauf fasst die Ausfallzeilen an (`--retry-failed --repair`). Jede
Reparaturzeile ersetzt eine Fehlzeile; ihre Goldzellen zaehlen heute als
fehlend. Mehr richtige Zellen heben den Recall, die Precision bleibt nur dann
gleich, wenn die neuen Zellen so treffsicher sind wie der Bestand.

Gemessen wird am Bestand, geschaetzt wird nur die Reparaturquote:

* Anker: richtige Zellen je brauchbarer Zeile. Der Median (2) ist der ehrliche
  Wert, der Mittelwert (3,09) ist nach oben verzogen, weil ein Teil der Zeilen
  gar nichts trifft.
* Obergrenze: die Goldzellen der Ausfallzeilen. Mehr kann eine Reparatur
  strukturell nicht gewinnen, egal wie gut sie ist.

Die Reparaturquote selbst ist **nicht gemessen**: Im Bestand gibt es keine
einzige Zeile mit `pfad=repair`. Genau deshalb ist sie der freie Parameter.

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


def treffer(row: dict, gold: dict) -> int:
    gesehen = zellen_von(row)
    return sum(
        1 for c in gold[row["record_id"]]["gold"]["cells"]
        if c["field"] in gesehen and abs(gesehen[c["field"]] - c["value"]) < 1e-9
    )


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
    praezision = richtig / (richtig + falsch) if richtig + falsch else 0.0

    ausfaelle = [r for r in rows if r.get("fehlerklasse")]
    brauchbar = [r for r in rows if not r.get("fehlerklasse")]
    treffer_je_record = [treffer(r, gold) for r in brauchbar]
    anker_median = statistics.median(treffer_je_record)
    anker_mittel = statistics.mean(treffer_je_record)
    quote_ohne_treffer = sum(1 for t in treffer_je_record if t == 0) / len(treffer_je_record)

    gold_ausfaelle = sum(len(gold[r["record_id"]]["gold"]["cells"]) for r in ausfaelle)
    # Zellen, die in den Ausfallzeilen schon richtig stehen, zaehlen heute als
    # richtig. Nur der Rest ist ueberhaupt gewinnbar.
    bereits_richtig = sum(treffer(r, gold) for r in ausfaelle)
    gewinnbar = gold_ausfaelle - bereits_richtig
    zellen_in_ausfaellen = sum(len(r.get("rows") or []) for r in ausfaelle)

    def kennzahlen(zuwachs: int) -> dict:
        zuwachs = min(zuwachs, gewinnbar)
        neue_falsch = round(zuwachs * (1 - praezision) / praezision) if praezision else 0
        r2, f2 = richtig + zuwachs, falsch + neue_falsch
        rec2 = r2 / goldzellen
        p2 = r2 / (r2 + f2) if r2 + f2 else 0.0
        return {
            "zuwachs": zuwachs,
            "richtig": r2,
            "falsch": f2,
            "recall": round(rec2, 4),
            "precision": round(p2, 4),
            "f1": round(2 * p2 * rec2 / (p2 + rec2), 4) if p2 + rec2 else 0.0,
        }

    basis = kennzahlen(0)
    szenarien = [
        (f"zurueckhaltend: 50 % der {len(ausfaelle)} Records brauchbar, je {anker_median:g} richtige Zellen",
         round(len(ausfaelle) * 0.5 * anker_median)),
        (f"mittel: 75 % brauchbar, je {anker_median:g} richtige Zellen",
         round(len(ausfaelle) * 0.75 * anker_median)),
        (f"optimistisch: alle brauchbar, je {anker_mittel:.2f} richtige Zellen",
         round(len(ausfaelle) * anker_mittel)),
        (f"Obergrenze: alle Goldzellen der Ausfaelle ({gewinnbar} gewinnbar)",
         gewinnbar),
    ]

    z = [
        "# Was der GLM-Reparaturlauf bringen kann (Schätzung)\n",
        f"Grundlage: Lesekopie `runs/{args.run}/predictions.jsonl`, Modell {args.modell}. "
        f"{len(ausfaelle)} Ausfallzeilen "
        f"({sum(1 for r in ausfaelle if r['fehlerklasse'] == 'length_ohne_ergebnis')} `length_ohne_ergebnis`, "
        f"{sum(1 for r in ausfaelle if r['fehlerklasse'] == 'json_kaputt')} `json_kaputt`) "
        f"mit {gold_ausfaelle} Goldzellen, davon {bereits_richtig} schon richtig; die Zeilen liefern "
        f"{zellen_in_ausfaellen} Zellen, also ist alles Gewinnbare noch offen ({gewinnbar} Zellen).\n",
        f"Bestand: {len(rows)} Records, {goldzellen} Goldzellen, richtig {richtig}, falsch {falsch}, "
        f"fehlend {fehlend}, Precision {praezision:.4f}, Recall {basis['recall']:.4f}, F1 {basis['f1']:.4f}.\n",
        "**Gemessen** ist der Anker: brauchbare Zeilen treffen im Mittel "
        f"{anker_mittel:.2f} Goldzellen, im Median {anker_median:g}; "
        f"{quote_ohne_treffer:.1%} der brauchbaren Zeilen trifft gar nichts. "
        "**Geschätzt** ist allein die Reparaturquote — im Bestand gibt es keine Zeile mit "
        "`pfad=repair`. Die Szenarien variieren deshalb nur diesen einen Parameter.\n",
        "| Szenario | Zellen dazu | richtig | Recall | Precision | F1 | F1-Delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, zuwachs in szenarien:
        k = kennzahlen(zuwachs)
        z.append(
            f"| {name} | +{k['zuwachs']} | {k['richtig']} | {k['recall']:.4f} | {k['precision']:.4f} "
            f"| {k['f1']:.4f} | {k['f1'] - basis['f1']:+.4f} |"
        )
    z.append("")
    z.append(
        f"Orientierung: Ein Recall-Punkt sind {goldzellen / 100:.0f} Zellen. Das mittlere Szenario "
        f"hebt den Recall um {(kennzahlen(szenarien[1][1])['recall'] - basis['recall']) * 100:+.1f} Punkte, "
        f"das optimistische um {(kennzahlen(szenarien[2][1])['recall'] - basis['recall']) * 100:+.1f}.\n"
    )
    z.append(
        "Annahmen und Grenzen:\n\n"
        "- Die Precision bleibt konstant; fallen die Reparaturantworten schlechter aus, sinkt sie.\n"
        "- Der Anker stammt aus normalen Laeufen. Reparaturantworten entstehen aus gekuerztem Text und "
        "6.000 statt 24.000 Tokens und duerften deshalb schwaecher sein; das spricht gegen die "
        "optimistischen Szenarien, nicht gegen die Obergrenze.\n"
        "- Die Obergrenze verlangt in jeder Ausfallzeile jede Goldzelle richtig, im Mittel "
        f"{gold_ausfaelle / len(ausfaelle):.2f} je Record. Der Reparatur-Prompt erlaubt bis zu sechs "
        "Zellen (\"at most six cells\"), schliesst sie also nicht aus, macht sie aber unwahrscheinlich.\n"
        "- Nicht enthalten sind die leeren Antworten ohne Ausfallklasse; sie laufen in einem "
        "eigenen Block (`retry_leer_ids.txt`), nicht in diesem Reparaturlauf.\n"
        "- Bei `json_kaputt` greift kein Reparaturaufruf, sondern der einfache Retry.\n"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(z), encoding="utf-8")
    args.out.with_suffix(".json").write_text(
        json.dumps(
            {
                "run": args.run,
                "modell": args.modell,
                "bestand": {"records": len(rows), "goldzellen": goldzellen, "richtig": richtig,
                            "falsch": falsch, "fehlend": fehlend, **basis},
                "ausfaelle": {"records": len(ausfaelle), "goldzellen": gold_ausfaelle,
                              "bereits_richtig": bereits_richtig, "gewinnbar": gewinnbar,
                              "gelieferte_zellen": zellen_in_ausfaellen},
                "anker": {"richtige_zellen_je_record_mittel": round(anker_mittel, 2),
                          "median": anker_median, "anteil_ohne_treffer": round(quote_ohne_treffer, 3)},
                "szenarien": {name: kennzahlen(w) for name, w in szenarien},
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("\n".join(z))
    print(f"geschrieben: {args.out} und {args.out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
