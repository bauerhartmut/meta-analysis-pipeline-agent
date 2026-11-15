#!/usr/bin/env python3
"""Fuehrt Hauptlauf und Folgelauf zu einer Ergebnisdatei zusammen.

Regel: Der Hauptlauf bleibt die Quelle der Wahrheit. Ein Record aus dem
Folgelauf ersetzt die Hauptlauf-Zeile nur dann, wenn er Zellen liefert (oder
wenigstens gueltiges JSON ohne Ausfall). Jede Zeile traegt ein `quelle`-Feld,
damit die Auswertung die Anteile trennen kann; bestehende Zeilen werden nur um
dieses Feld ergaenzt, nie inhaltlich veraendert.

Aufruf:

    python .../mische_quelle.py --haupt yun_test186_v6_20261115 \
        --folge yun_test186_v7_folgelauf_20261116 \
        --out-run yun_test186_kombiniert_20261116
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--haupt", required=True)
    parser.add_argument("--folge", required=True)
    parser.add_argument("--out-run", required=True)
    args = parser.parse_args()

    haupt = read_jsonl(BENCH / "runs" / args.haupt / "predictions.jsonl")
    folge = {str(row["record_id"]): row for row in read_jsonl(BENCH / "runs" / args.folge / "predictions.jsonl")}

    zaehler: Counter[str] = Counter()
    zusammengefuehrt: list[dict[str, Any]] = []
    for row in haupt:
        record_id = str(row["record_id"])
        quelle = str(row.get("quelle") or "v6_hauptlauf")
        neuer = folge.get(record_id)
        # Der Folgelauf uebernimmt nur, wenn er verwendbare Zellen liefert.
        if neuer and (neuer.get("rows") or (not neuer.get("fehlerklasse") and neuer.get("finish_reason") == "stop")):
            ersatz = dict(neuer)
            ersatz["quelle"] = str(neuer.get("quelle") or "v7_folgelauf")
            zusammengefuehrt.append(ersatz)
            zaehler["aus_folgelauf"] += 1
        else:
            kopie = dict(row)
            kopie["quelle"] = quelle
            zusammengefuehrt.append(kopie)
            zaehler["aus_hauptlauf"] += 1
            if neuer:
                zaehler["folge_verworfen"] += 1

    ziel = BENCH / "runs" / args.out_run
    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in zusammengefuehrt:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    zusammenfassung = {
        "haupt": args.haupt,
        "folge": args.folge,
        "zeilen": len(zusammengefuehrt),
        **zaehler,
        "je_quelle": dict(Counter(str(row.get("quelle")) for row in zusammengefuehrt)),
    }
    (ziel / "zusammenfuehrung.json").write_text(
        json.dumps(zusammenfassung, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(zusammenfassung, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
