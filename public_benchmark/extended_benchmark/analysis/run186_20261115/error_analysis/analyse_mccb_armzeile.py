#!/usr/bin/env python3
"""Read-only: aus welcher Tabellenzeile stammt der Komparatorwert bei 289-295?

Die MCCB-Tabelle in PMC4215531 hat die Zeilen `FAT Pre`, `FAT Post`, `TAU Pre`,
`TAU Post`, `CE Pre`, `CE Post`; die Spalten sind die Untertests. Gold ist
`TAU Post`. Dieses Skript sucht jede abweichende Modellzahl im Artikeltext und
nennt den naechsten Armzeilen-Kopf davor. Es schreibt nichts und ruft kein
Modell.

    python analyse_mccb_armzeile.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402

RECORDS = BENCH / "records" / "yun_test76_ziel.jsonl"
RUN = BENCH / "runs" / "test76_hauptlauf_20261116" / "predictions.jsonl"
ARMZEILE = re.compile(r"(FAT|TAU|CE)\s*(Pre|Post)")


def lies(pfad: Path) -> dict[str, dict]:
    return {r["record_id"]: r for r in (json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip())}


def armzeile_zu(wert: float, text: str) -> str | None:
    """Naechster Armzeilen-Kopf vor der ersten Fundstelle der Zahl."""
    for treffer in re.finditer(re.escape(f"{wert:g}"), text):
        labels = ARMZEILE.findall(text[max(0, treffer.start() - 300) : treffer.start()])
        if labels:
            return f"{labels[-1][0]} {labels[-1][1]}"
    return None


def main() -> int:
    records, rows = lies(RECORDS), lies(RUN)
    print(f"{'Record':<12} {'Feld':<32} {'Modell':>7} {'Gold':>7}  Armzeile")
    treffer: dict[str, int] = {}
    for nummer in range(289, 296):
        record_id = f"yun2024:{nummer}"
        record, zeile = records[record_id], rows[record_id]
        text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        gold = {(c["field"], c.get("arm")): c["value"] for c in record["gold"]["cells"]}
        for cell in (zeile.get("predicted") or {}).get("cells") or []:
            key = (cell["field"], cell.get("arm"))
            if key not in gold or cell["value"] == gold[key]:
                continue
            if "mean" not in cell["field"] and "standard_deviation" not in cell["field"]:
                continue
            zeile_name = armzeile_zu(cell["value"], text) or "(keine)"
            treffer[zeile_name] = treffer.get(zeile_name, 0) + 1
            print(f"{record_id:<12} {cell['field']:<32} {cell['value']:>7g} {gold[key]:>7g}  {zeile_name}")
    print("Verteilung:", dict(sorted(treffer.items(), key=lambda paar: -paar[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
