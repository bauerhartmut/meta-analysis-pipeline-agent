#!/usr/bin/env python
"""Yun-Zaehlweise (Exact/Partial/Unknown) fuer einen eigenen Lauf.

Nachgebaut nach `evaluation/calculate_metrics.py` und
`evaluation/evaluate_output.py` des Yun-Repositories:

* Gold- und Modellzellen werden je Feld verglichen. Fehlt ein Wert im Gold oder
  in der Antwort, gilt er als `x`; `x == x` ist ein Treffer (so zaehlt das
  Original).
* `exact_match` = Anteil der Instanzen, in denen **alle** Felder des Tasks
  uebereinstimmen (6 bei kontinuierlich, 4 bei binaer).
* `partial_match_k` = Anteil der Instanzen mit mindestens k Treffern.
* `model_unknowns` = Antwort `x`, obwohl das Gold einen Wert hat.
* `reference_unknowns` = Gold `x`.

Die Punkt-Schaetzer (SMD/logOR) werden **nicht** berechnet: Das Original nutzt
dafuer `statsmodels`, das hier nicht installiert ist. Eine eigene Naeherung waere
nicht mit Yun vergleichbar und wird deshalb weggelassen.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"

FELDER = {
    "continuous": [
        "intervention_mean",
        "intervention_standard_deviation",
        "intervention_group_size",
        "comparator_mean",
        "comparator_standard_deviation",
        "comparator_group_size",
    ],
    "binary": [
        "intervention_events",
        "intervention_group_size",
        "comparator_events",
        "comparator_group_size",
    ],
}
PARTIAL = {"continuous": 5, "binary": 3}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def gleich(gold: float | None, modell: float | None) -> bool:
    if gold is None and modell is None:
        return True
    if gold is None or modell is None:
        return False
    return abs(gold - modell) < 1e-9


def block(rows: list[dict], alle: dict[str, dict], typ: str) -> dict:
    felder = FELDER[typ]
    treffer = {feld: 0 for feld in felder}
    modell_unknown = {feld: 0 for feld in felder}
    gold_unknown = {feld: 0 for feld in felder}
    exakt = 0
    partial = {k: 0 for k in range(1, PARTIAL[typ] + 1)}
    for row in rows:
        record = alle[row["record_id"]]
        gold = {c["field"]: c["value"] for c in record["gold"]["cells"]}
        modell: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            modell.setdefault(zelle["field"], zelle["value"])
        anzahl = 0
        for feld in felder:
            g, m = gold.get(feld), modell.get(feld)
            if g is None:
                gold_unknown[feld] += 1
            if m is None and g is not None:
                modell_unknown[feld] += 1
            if gleich(g, m):
                treffer[feld] += 1
                anzahl += 1
        if anzahl == len(felder):
            exakt += 1
        for k in partial:
            if anzahl >= k:
                partial[k] += 1
    n = len(rows) or 1
    return {
        "instanzen": len(rows),
        "exact_match": round(exakt / n, 4),
        "partial_match": {f"partial_{k}": round(v / n, 4) for k, v in partial.items()},
        "je_feld_trefferquote": {feld: round(treffer[feld] / n, 4) for feld in felder},
        "model_unknowns": {**modell_unknown, "total": sum(modell_unknown.values())},
        "reference_unknowns": {**gold_unknown, "total": sum(gold_unknown.values())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = lies(RUNS / args.run / "predictions.jsonl")
    alle = {r["record_id"]: r for r in lies(args.records)}
    rows = [r for r in rows if r["record_id"] in alle]

    ergebnis = {"run": args.run, "records": len(rows), "tasks": {}}
    for typ in ("continuous", "binary"):
        teil = [r for r in rows if alle[r["record_id"]]["context"]["outcome_type"] == typ]
        ergebnis["tasks"][typ] = block(teil, alle, typ)

    print(f"{args.run}: {len(rows)} Records, Zaehlweise wie Yun (x == x ist Treffer)")
    for typ, block_ in ergebnis["tasks"].items():
        if not block_["instanzen"]:
            print(f"  {typ}: keine Instanzen")
            continue
        print(
            f"  {typ:<11} n={block_['instanzen']:>3} | exact {block_['exact_match']:.4f} | "
            f"partial_1 {block_['partial_match']['partial_1']:.4f} | "
            f"model_unknowns {block_['model_unknowns']['total']} | "
            f"reference_unknowns {block_['reference_unknowns']['total']}"
        )
        for feld, quote in block_["je_feld_trefferquote"].items():
            print(f"      {feld:<34} {quote:.4f}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
