#!/usr/bin/env python3
"""Bewertung der Rueckfallregel (v6_target_fallback).

Das Modell nennt je Zelle den benutzten Messzeitpunkt. Dieses Skript trennt die
Zellen in zwei Klassen und zaehlt sie getrennt:

* **zieltreu**: Zelle nennt den im Record annotierten Zielzeitpunkt
* **rueckfall**: Zelle nennt einen anderen Zeitpunkt (dann muss sie stimmen,
  sonst ist die Rueckfallregel schaedlich)

Zusaetzlich: Auslassungen je Feld, Gesamtmetriken und die Zeitdistanz der
Rueckfaelle in Monaten (aus den Labels, ohne Modell).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from check_timepoints import rang  # noqa: E402
from evaluate_extended import _close, _f1, _safe_div, evaluate_numeric, read_jsonl  # noqa: E402
from stage_extraction import normalisiere  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=HERE / "records" / "yun_dev.jsonl")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    records = read_jsonl(args.records)
    by_id = {str(record["record_id"]): record for record in records}
    rows = read_jsonl(HERE / "runs" / args.run / "predictions.jsonl")
    predictions = {str(row["record_id"]): row for row in rows}

    zaehler = Counter()
    pro_feld: dict[str, Counter] = defaultdict(Counter)
    distanzen: list[float] = []
    rueckfall_beispiele: list[dict[str, Any]] = []
    fehlend: Counter[str] = Counter()

    for record_id, record in by_id.items():
        gold = {(cell["field"], cell.get("arm")): float(cell["value"]) for cell in record["gold"]["cells"]}
        target = normalisiere((record.get("timepoint") or {}).get("target") or "")
        cells = (predictions.get(record_id, {}).get("predicted") or {}).get("cells", [])
        gesehen: set[tuple[str, str | None]] = set()
        for cell in cells:
            key = (cell["field"], cell.get("arm"))
            label = normalisiere(cell.get("timepoint") or "")
            zieltreu = bool(target) and (not label or label == target)
            art = "zieltreu" if zieltreu else "rueckfall"
            zaehler[f"{art}_zellen"] += 1
            pro_feld[cell["field"]][f"{art}_zellen"] += 1
            if key in gold:
                gesehen.add(key)
                if _close(cell["value"], gold[key], 1e-6, 0.0):
                    zaehler[f"{art}_richtig"] += 1
                    pro_feld[cell["field"]][f"{art}_richtig"] += 1
                else:
                    zaehler[f"{art}_falsch"] += 1
            else:
                zaehler[f"{art}_ohne_gold"] += 1
            if not zieltreu:
                ziel_rang, label_rang = rang(target), rang(label)
                if ziel_rang is not None and label_rang is not None:
                    distanzen.append(abs(label_rang - ziel_rang))
                if len(rueckfall_beispiele) < 20:
                    rueckfall_beispiele.append(
                        {
                            "record_id": record_id,
                            "field": cell["field"],
                            "target": (record.get("timepoint") or {}).get("target"),
                            "timepoint": cell.get("timepoint"),
                            "value": cell["value"],
                            "gold": gold.get(key),
                        }
                    )
        for key in gold:
            if key not in gesehen:
                fehlend[key[0]] += 1
                zaehler["auslassungen"] += 1

    gesamt = evaluate_numeric(records, predictions)
    gold_cells = sum(len(record["gold"]["cells"]) for record in records)
    ergebnis = {
        "run": args.run,
        "records": len(records),
        "gesamt": gesamt,
        "zieltreu": {
            "zellen": zaehler["zieltreu_zellen"],
            "richtig": zaehler["zieltreu_richtig"],
            "falsch": zaehler["zieltreu_falsch"],
            "ohne_gold": zaehler["zieltreu_ohne_gold"],
            "precision": round(
                _safe_div(zaehler["zieltreu_richtig"], zaehler["zieltreu_richtig"] + zaehler["zieltreu_falsch"]), 4
            ),
        },
        "rueckfall": {
            "zellen": zaehler["rueckfall_zellen"],
            "richtig": zaehler["rueckfall_richtig"],
            "falsch": zaehler["rueckfall_falsch"],
            "ohne_gold": zaehler["rueckfall_ohne_gold"],
            "precision": round(
                _safe_div(zaehler["rueckfall_richtig"], zaehler["rueckfall_richtig"] + zaehler["rueckfall_falsch"]), 4
            ),
            "zeitdistanz_median_monate": round(sorted(distanzen)[len(distanzen) // 2], 2) if distanzen else None,
            "zeitdistanz_bekannt": len(distanzen),
            "beispiele": rueckfall_beispiele,
        },
        "auslassungen": {
            "gesamt": zaehler["auslassungen"],
            "je_feld": dict(sorted(fehlend.items())),
            "quote": round(_safe_div(zaehler["auslassungen"], gold_cells), 4),
        },
        "je_feld": {field: dict(counts) for field, counts in sorted(pro_feld.items())},
        "zell_f1_aus_klassen": round(
            _f1(
                _safe_div(
                    zaehler["zieltreu_richtig"] + zaehler["rueckfall_richtig"],
                    zaehler["zieltreu_richtig"] + zaehler["zieltreu_falsch"]
                    + zaehler["rueckfall_richtig"] + zaehler["rueckfall_falsch"]
                    + zaehler["zieltreu_ohne_gold"] + zaehler["rueckfall_ohne_gold"],
                ),
                _safe_div(zaehler["zieltreu_richtig"] + zaehler["rueckfall_richtig"], gold_cells),
            ),
            4,
        ),
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"[gesamt] F1 {gesamt['cell_f1']:.4f} recall {gesamt['cell_recall']:.4f} precision "
        f"{gesamt['cell_precision']:.4f} MAE {gesamt['mae_pairs']} coverage {gesamt['mae_coverage']} "
        f"({gesamt['mae_pairs_covered']}/{gold_cells}) exakt {gesamt['record_exact']}/{len(records)}"
    )
    for art in ("zieltreu", "rueckfall"):
        block = ergebnis[art]
        print(
            f"[{art}] {block['zellen']} Zellen, richtig {block['richtig']}, falsch {block['falsch']}, "
            f"ohne Gold {block['ohne_gold']}, Precision {block['precision']}"
        )
    if ergebnis["rueckfall"]["beispiele"]:
        print(f"[rueckfall] Zeitdistanz Median {ergebnis['rueckfall']['zeitdistanz_median_monate']} Monate "
              f"({ergebnis['rueckfall']['zeitdistanz_bekannt']} bestimmbar)")
    print(f"[auslassungen] {ergebnis['auslassungen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
