#!/usr/bin/env python3
"""Kontext der 15 ueberzaehligen Zellen aus dem v7-Folgelauf (read-only).

Druckt je Zelle das Outcome, die Goldfelder und bis zu drei Fundstellen der Zahl
im Artikeltext, damit sich am Text entscheiden laesst, ob der Wert dort steht und
zum Outcome gehoert. Kein Modellaufruf.

Aufruf:

    python .../error_analysis/pruefe_ueberzaehlige.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parents[2]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402

V7 = BENCH / "runs" / "yun_test186_v7_folgelauf_20261116" / "predictions.jsonl"
RECORDS = BENCH / "records" / "yun_test186.jsonl"
FOLGE_IDS = BENCH / "analysis" / "run186_20261115" / "folge_ids.txt"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fundstellen(zahl: float, text: str, umfeld: int = 180) -> list[str]:
    """Bis zu drei Textausschnitte um die Zahl (Ganzzahl-Match, keine Dezimalteile)."""
    roh = f"{zahl:g}"
    muster = re.compile(r"(?<![\d.,])" + re.escape(roh) + r"(?![\d.,])")
    stellen: list[str] = []
    for treffer in muster.finditer(text):
        pos = treffer.start()
        stellen.append(" ".join(text[max(0, pos - umfeld):pos + umfeld].split()))
        if len(stellen) == 3:
            break
    return stellen


def main() -> int:
    ids = [teil for teil in FOLGE_IDS.read_text(encoding="utf-8").split(",") if teil.strip()]
    records = {str(r["record_id"]): r for r in read_jsonl(RECORDS)}
    v7 = {str(r["record_id"]): r for r in read_jsonl(V7)}

    zeilen: list[str] = []
    anzahl = 0
    for record_id in ids:
        vorhersage = v7.get(record_id) or {}
        if not vorhersage.get("rows"):
            continue
        record = records[record_id]
        gold = {(c["field"], c.get("arm")): float(c["value"]) for c in record["gold"]["cells"]}
        text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        for cell in vorhersage["rows"]:
            schluessel = (cell["field"], cell.get("arm"))
            if schluessel in gold:
                continue
            anzahl += 1
            zeilen.append(
                f"=== {record_id} | {cell['field']} = {cell['value']} @ {cell.get('timepoint')!r}"
                f" | Outcome: {record['context'].get('outcome')!r}"
            )
            zeilen.append(f"    Goldfelder: {sorted({c['field'] for c in record['gold']['cells']})}")
            zeilen.append(f"    Zieldokument: {record['document']['path'].split('/')[-1]}")
            stellen = fundstellen(float(cell["value"]), text)
            if not stellen:
                zeilen.append("    KEINE Fundstelle der Zahl im Artikeltext")
            for stelle in stellen:
                zeilen.append(f"    ... {stelle} ...")
            zeilen.append("")
    ausgabe = "\n".join(zeilen)
    (HIER / "ueberzaehlige_kontext.txt").write_text(ausgabe + "\n", encoding="utf-8")
    print(f"{anzahl} ueberzaehlige Zellen, Kontext in ueberzaehlige_kontext.txt")
    print(ausgabe[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
