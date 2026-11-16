"""Laufzeit-Telemetrie der bisherigen Extraktionslaeufe.

Liest alle runs/*/predictions.jsonl, gruppiert nach (Modell, Lauf) und gibt
n, Mittel, Median und Summe der elapsed_s aus. Zusaetzlich eine Hochrechnung
fuer den kompletten Datensatz.

Die Hochrechnung beruecksichtigt nur Laeufe mit 8000 Tokens und v7
(Zellzeitpunkt). Aeltere Laeufe mit 4000 Tokens oder anderen Promptversionen
haben kuerzere Antworten und wuerden die Schaetzung nach unten ziehen.

Cache-Treffer und Ausfaelle werden in beiden Auswertungen ausgeschlossen: Ein
Cache-Treffer antwortet in 4 s statt in 67 s und verzerrt den Median um eine
Groessenordnung.

Aufruf:  python public_benchmark/extended_benchmark/yun_full/laufzeit_telemetrie.py [--records N]
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
ZIEL_TOKENS = 8000
ZIEL_SCHEMA = "v7_zellzeitpunkt"


def ist_ziel_lauf(row: dict, lauf: str) -> bool:
    """8000 Tokens und v7 - erkannt an den Feldern, nicht am Laufnamen."""
    if row.get("schema_version") != ZIEL_SCHEMA:
        return False
    params = row.get("gateway_params") or {}
    tokens = params.get("max_tokens")
    if isinstance(tokens, int):
        return tokens == ZIEL_TOKENS
    # aeltere Laeufe ohne gateway_params: Notbehelf ueber den Laufnamen
    return "8000" in lauf


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=int, default=699, help="Records fuer die Hochrechnung")
    args = ap.parse_args()

    werte: dict[tuple[str, str], list[float]] = defaultdict(list)
    ziel: dict[str, list[float]] = defaultdict(list)
    ziel_laeufe: dict[str, int] = defaultdict(int)
    cache: dict[str, int] = defaultdict(int)

    for pfad in sorted(RUNS.glob("*/predictions.jsonl")):
        lauf = pfad.parent.name
        with pfad.open(encoding="utf-8") as fh:
            for zeile in fh:
                try:
                    r = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                e = r.get("elapsed_s")
                if r.get("suspected_cache") or r.get("failed"):
                    cache[lauf] += 1
                    continue
                if not isinstance(e, (int, float)):
                    continue
                werte[(r.get("model", "?"), lauf)].append(float(e))
                if ist_ziel_lauf(r, lauf):
                    ziel[r.get("model", "?")].append(float(e))
                    ziel_laeufe[lauf] += 1

    print(f"{'Modell':10} {'Lauf':44} {'n':>4} {'mean':>7} {'median':>7} {'Summe_min':>9}")
    for (modell, lauf), v in sorted(werte.items()):
        print(
            f"{modell:10} {lauf[:44]:44} {len(v):4d} {statistics.mean(v):7.1f} "
            f"{statistics.median(v):7.1f} {sum(v) / 60:9.1f}"
        )

    print("\nAusgeschlossen (Cache-Treffer oder Ausfall) je Lauf:")
    for lauf, n in sorted(cache.items()):
        print(f"  {lauf[:44]:44} {n:4d}")

    print(f"\nBeruecksichtigt fuer die Hochrechnung (8000 Tokens, {ZIEL_SCHEMA}):")
    for lauf, n in sorted(ziel_laeufe.items()):
        print(f"  {lauf[:44]:44} {n:4d}")

    print(f"\nHochrechnung auf {args.records} Records:")
    gesamt = 0.0
    for modell, v in sorted(ziel.items()):
        med = statistics.median(v)
        dauer = med * args.records
        gesamt += dauer
        print(
            f"  {modell:10} n={len(v):4d} median {med:6.1f} s  ->  "
            f"{dauer / 3600:6.1f} h fuer {args.records} Records"
        )
    if not ziel:
        print("  keine passenden Laeufe gefunden")
        return 1
    print(f"  {'Summe':10} {'':26}->  {gesamt / 3600:6.1f} h sequentiell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
