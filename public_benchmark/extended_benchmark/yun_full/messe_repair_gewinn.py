#!/usr/bin/env python
"""Misst, was der Reparaturlauf tatsaechlich gebracht hat.

Vergleicht zwei Staende einer `predictions.jsonl`: die Sicherung, die
`nachzug_ausfaelle.sh` vor dem Nachzug anlegt (`predictions.vor_nachzug.jsonl`),
und den Stand danach. Beide werden je (record_id, model) entdoppelt, damit
Fehlzeile und Reparaturzeile nicht doppelt zaehlen.

Gemessen wird genau der freie Parameter der Schaetzung: Wie viele der
Ausfallzeilen liefern danach eine brauchbare Antwort, und wie viele Goldzellen
kommen hinzu. Zusaetzlich wird die gemessene Kennzahl neben die Spanne aus
`repair_schaetzung.json` gelegt.

Aufruf:
    python messe_repair_gewinn.py --run yun699_8000_alle_20261117 --modell glm
    python messe_repair_gewinn.py --vor a.jsonl --nach b.jsonl
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"


def lies(pfad: Path) -> list[str]:
    return [z for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def entdopple(zeilen: list[str]) -> dict[tuple[str, str], dict]:
    """Letzte brauchbare Zeile je Paar gewinnt, wie in dedupe_predictions.py."""
    beste: dict[tuple[str, str], dict] = {}
    for zeile in zeilen:
        try:
            row = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        key = (row["record_id"], row["model"])
        if key not in beste or beste[key].get("failed") or not row.get("failed"):
            beste[key] = row
    return beste


def zellen_von(row: dict) -> dict[str, float]:
    gesehen: dict[str, float] = {}
    for zelle in row.get("rows") or []:
        gesehen.setdefault(zelle["field"], zelle["value"])
    return gesehen


def kennzahlen(stand: dict[tuple[str, str], dict], gold: dict, modell: str) -> dict:
    richtig = falsch = fehlend = 0
    for (rid, m), row in stand.items():
        if m != modell:
            continue
        gesehen = zellen_von(row)
        for c in gold[rid]["gold"]["cells"]:
            if c["field"] not in gesehen:
                fehlend += 1
            elif abs(gesehen[c["field"]] - c["value"]) < 1e-9:
                richtig += 1
            else:
                falsch += 1
    goldzellen = richtig + falsch + fehlend
    precision = richtig / (richtig + falsch) if richtig + falsch else 0.0
    recall = richtig / goldzellen if goldzellen else 0.0
    return {
        "richtig": richtig,
        "falsch": falsch,
        "fehlend": fehlend,
        "goldzellen": goldzellen,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", help="Run-Verzeichnis unter runs/ (nutzt die Sicherung)")
    ap.add_argument("--vor", type=Path, help="predictions.jsonl vor dem Nachzug")
    ap.add_argument("--nach", type=Path, help="predictions.jsonl nach dem Nachzug")
    ap.add_argument("--modell", default="glm")
    ap.add_argument("--out", type=Path, default=None, help="optionaler JSON-Bericht")
    args = ap.parse_args()

    if args.run:
        lauf = RUNS / args.run
        vor_pfad = lauf / "predictions.vor_nachzug.jsonl"
        nach_pfad = lauf / "predictions.jsonl"
        schaetzung = lauf.parent.parent / "iterativ" / "ergebnisse" / "qwen30_vs_glm_20261118" / "repair_schaetzung.json"
    else:
        if not (args.vor and args.nach):
            print("FEHLER: entweder --run oder --vor und --nach")
            return 2
        vor_pfad, nach_pfad, schaetzung = args.vor, args.nach, None
    if not vor_pfad.exists():
        print(f"FEHLER: {vor_pfad} fehlt")
        return 2

    gold = {r["record_id"]: r for r in (json.loads(z) for z in lies(RECORDS))}
    vor = entdopple(lies(vor_pfad))
    nach = entdopple(lies(nach_pfad))

    ausfaelle = [k for k, row in vor.items() if k[1] == args.modell and row.get("failed")]
    gerettet, weiter_ausfall, zellen_gerettet, treffer_gerettet = [], [], 0, 0
    for key in ausfaelle:
        row = nach.get(key)
        if row is None or row.get("failed") or not row.get("rows"):
            weiter_ausfall.append(key)
            continue
        gerettet.append(key)
        zellen_gerettet += len(row.get("rows") or [])
        treffer_gerettet += sum(
            1 for c in gold[key[0]]["gold"]["cells"]
            if c["field"] in (gesehen := zellen_von(row)) and abs(gesehen[c["field"]] - c["value"]) < 1e-9
        )

    v = kennzahlen(vor, gold, args.modell)
    n = kennzahlen(nach, gold, args.modell)
    quote = len(gerettet) / len(ausfaelle) if ausfaelle else 0.0
    je_record = treffer_gerettet / len(gerettet) if gerettet else 0.0
    print(f"{args.modell}: {len(ausfaelle)} Ausfaelle vor dem Nachzug")
    print(f"  gerettet {len(gerettet)} ({quote:.1%}), weiter Ausfall {len(weiter_ausfall)}")
    print(f"  gelieferte Zellen {zellen_gerettet}, davon richtig {treffer_gerettet} "
          f"({je_record:.2f} je geretteter Zeile)")
    print(f"  richtig {v['richtig']} -> {n['richtig']} ({n['richtig'] - v['richtig']:+d})")
    print(f"  Recall {v['recall']:.4f} -> {n['recall']:.4f} ({n['recall'] - v['recall']:+.4f})")
    print(f"  Precision {v['precision']:.4f} -> {n['precision']:.4f} | F1 {v['f1']:.4f} -> {n['f1']:.4f}")

    bericht = {
        "modell": args.modell,
        "vorher": v,
        "nachher": n,
        "ausfaelle": len(ausfaelle),
        "gerettet": len(gerettet),
        "weiter_ausfall": len(weiter_ausfall),
        "reparaturquote": round(quote, 4),
        "richtige_zellen_je_geretteter_zeile": round(je_record, 2),
        "gelieferte_zellen": zellen_gerettet,
    }
    if schaetzung and schaetzung.exists():
        s = json.loads(schaetzung.read_text(encoding="utf-8"))
        spanne = sorted(s["szenarien"][k]["recall"] for k in s["szenarien"])
        bericht["schaetzung_recall_spanne"] = [spanne[0], spanne[-1]]
        print(f"  Schaetzung von damals: Recall {spanne[0]:.4f} bis {spanne[-1]:.4f}, "
              f"gemessen {n['recall']:.4f}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
