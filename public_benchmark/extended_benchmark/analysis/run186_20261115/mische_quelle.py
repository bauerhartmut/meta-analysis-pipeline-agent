#!/usr/bin/env python3
"""Fuehrt Hauptlauf und Folgelauf zu einer Ergebnisdatei zusammen.

Regel: Der Hauptlauf bleibt die Quelle der Wahrheit. Ein Record aus dem
Folgelauf ersetzt die Hauptlauf-Zeile nur dann, wenn er Zellen liefert (oder
wenigstens gueltiges JSON ohne Ausfall). Jede Zeile traegt ein `quelle`-Feld,
damit die Auswertung die Anteile trennen kann; bestehende Zeilen werden nur um
dieses Feld ergaenzt, nie inhaltlich veraendert.

Schutz: Das Ziel darf weder der Haupt- noch der Folgelauf sein. Folgelauf-IDs
ohne Gegenstueck im Hauptlauf werden gezaehlt und in der Zusammenfassung
ausgewiesen, statt still zu verschwinden.

Aufruf:

    python .../mische_quelle.py --haupt yun_test186_v6_20261115 \
        --folge yun_test186_v7_folgelauf_20261116 \
        --out-run yun_test186_kombiniert_20261116
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fuehre_zusammen(haupt_pfad: Path, folge_pfad: Path, ziel: Path) -> dict[str, Any]:
    """Schreibt die zusammengefuehrte Datei; bricht bei gleichem Zielpfad ab."""
    ziel_pfad = ziel.resolve()
    gesperrt = {haupt_pfad.resolve(), haupt_pfad.resolve().parent, folge_pfad.resolve(), folge_pfad.resolve().parent}
    if ziel_pfad in gesperrt:
        raise ValueError("Zielpfad darf Haupt- oder Folgelauf nicht ueberschreiben")

    haupt = read_jsonl(haupt_pfad)
    folge = {str(row["record_id"]): row for row in read_jsonl(folge_pfad)}
    haupt_ids = {str(row["record_id"]) for row in haupt}
    nicht_zugeordnet = sorted(record_id for record_id in folge if record_id not in haupt_ids)

    zaehler: Counter[str] = Counter()
    zusammengefuehrt: list[dict[str, Any]] = []
    for row in haupt:
        record_id = str(row["record_id"])
        quelle = str(row.get("quelle") or "v6_hauptlauf")
        neuer = folge.get(record_id)
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

    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in zusammengefuehrt:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    zusammenfassung = {
        "haupt": haupt_pfad.parent.name,
        "folge": folge_pfad.parent.name,
        "zeilen": len(zusammengefuehrt),
        **zaehler,
        "folge_nicht_zugeordnet": len(nicht_zugeordnet),
        "folge_nicht_zugeordnet_ids": nicht_zugeordnet[:20],
        "je_quelle": dict(Counter(str(row.get("quelle")) for row in zusammengefuehrt)),
    }
    (ziel / "zusammenfuehrung.json").write_text(
        json.dumps(zusammenfassung, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return zusammenfassung


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--haupt", required=True)
    parser.add_argument("--folge", required=True)
    parser.add_argument("--out-run", required=True)
    args = parser.parse_args()

    try:
        zusammenfassung = fuehre_zusammen(
            BENCH / "runs" / args.haupt / "predictions.jsonl",
            BENCH / "runs" / args.folge / "predictions.jsonl",
            BENCH / "runs" / args.out_run,
        )
    except ValueError as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        return 2
    print(json.dumps(zusammenfassung, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
