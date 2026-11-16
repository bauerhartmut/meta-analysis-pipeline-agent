#!/usr/bin/env python3
"""Prueft die 14 bekannten falschen Komparatorzellen von 289-295.

Die sieben MCCB-Records (`yun2024:289`-`295`, PMC4215531) tragen je einen
Komparator-Mittelwert und eine SD, die im Hauptlauf aus der falschen Zeile
stammten (`FAT Pre` statt `TAU Post`). Dieses Skript vergleicht die Vorhersagen
eines Laufs mit dem Gold, nennt je Zelle die Zeile, aus der der Modellwert im
Artikel steht, und zaehlt die Treffer. Es ruft kein Modell auf.

    python pruefe_armzeile_289_295.py --run test76_hauptlauf_20261116
    python pruefe_armzeile_289_295.py --run armzeile_291_295_20261116
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402
from evaluate_extended import _close  # noqa: E402

RECORDS = BENCH / "records" / "yun_test76_ziel.jsonl"
FELDER = ("comparator_mean", "comparator_standard_deviation")
ARMZEILE = re.compile(r"(FAT|TAU|CE)\s*(Pre|Post)")


def lies(pfad: Path) -> dict[str, dict]:
    return {
        r["record_id"]: r
        for r in (json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip())
    }


def armzeile_zu(wert: float, text: str) -> str:
    """Naechster Armzeilen-Kopf vor der ersten Fundstelle der Zahl."""
    for treffer in re.finditer(re.escape(f"{wert:g}"), text):
        labels = ARMZEILE.findall(text[max(0, treffer.start() - 300) : treffer.start()])
        if labels:
            return f"{labels[-1][0]} {labels[-1][1]}"
    return "-"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run-ID unter runs/")
    args = parser.parse_args()

    records = lies(RECORDS)
    zeilen = lies(BENCH / "runs" / args.run / "predictions.jsonl")
    print(f"{'Record':<13} {'Feld':<30} {'Gold':>7} {'Modell':>7} {'ok':<3} {'Zeile im Artikel':<10} arm_row")
    richtig = 0
    gesamt = 0
    for nummer in range(289, 296):
        record_id = f"yun2024:{nummer}"
        record, zeile = records.get(record_id), zeilen.get(record_id)
        if record is None or zeile is None:
            print(f"{record_id:<13} fehlt im Lauf")
            continue
        text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        gold = {(c["field"], c.get("arm")): c["value"] for c in record["gold"]["cells"]}
        predicted = {(c["field"], c.get("arm")): c for c in (zeile.get("predicted") or {}).get("cells") or []}
        for feld in FELDER:
            key = (feld, "comparator")
            if key not in gold:
                continue
            gesamt += 1
            zelle = predicted.get(key)
            wert = zelle["value"] if zelle else None
            treffer = wert is not None and _close(wert, gold[key], 1e-6, 0.0)
            richtig += int(treffer)
            zeile_name = armzeile_zu(wert, text) if wert is not None else "-"
            arm_row = (zelle or {}).get("arm_row", "")
            print(
                f"{record_id:<13} {feld:<30} {gold[key]:>7g} "
                f"{'—' if wert is None else format(wert, '>7g')} {'ja' if treffer else 'nein':<3} "
                f"{zeile_name:<10} {arm_row}"
            )
    print(f"\nKomparatorzellen richtig: {richtig}/{gesamt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
