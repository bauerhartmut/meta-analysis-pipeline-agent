"""Laufzeit-Telemetrie der bisherigen Extraktionslaeufe.

Liest alle runs/*/predictions.jsonl, gruppiert nach (Modell, Lauf) und gibt
n, Mittel, Median und Summe der elapsed_s aus. Zusaetzlich eine Hochrechnung
fuer den kompletten Datensatz.

Aufruf:  python public_benchmark/extended_benchmark/yun_full/laufzeit_telemetrie.py [--records N]
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=int, default=699, help="Records fuer die Hochrechnung")
    args = ap.parse_args()

    werte: dict[tuple[str, str], list[float]] = defaultdict(list)
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
                # Cache-Treffer und Ausfaelle verfaelschen die Laufzeit massiv
                if r.get("suspected_cache") or r.get("failed"):
                    cache[lauf] += 1
                    continue
                if isinstance(e, (int, float)):
                    werte[(r.get("model", "?"), lauf)].append(float(e))

    print(f"{'Modell':10} {'Lauf':44} {'n':>4} {'mean':>7} {'median':>7} {'Summe_min':>9}")
    for (modell, lauf), v in sorted(werte.items()):
        print(
            f"{modell:10} {lauf[:44]:44} {len(v):4d} {statistics.mean(v):7.1f} "
            f"{statistics.median(v):7.1f} {sum(v) / 60:9.1f}"
        )

    print("\nAusgeschlossen (Cache-Treffer oder Ausfall) je Lauf:")
    for lauf, n in sorted(cache.items()):
        print(f"  {lauf[:44]:44} {n:4d}")

    print("\nHochrechnung auf", args.records, "Records (nur echte API-Antworten, alle Laeufe):")
    je_modell: dict[str, list[float]] = defaultdict(list)
    for (modell, lauf), v in werte.items():
        je_modell[modell].extend(v)
    gesamt = 0.0
    for modell, v in sorted(je_modell.items()):
        med = statistics.median(v)
        dauer = med * args.records
        gesamt += dauer
        print(f"  {modell:10} median {med:6.1f} s  ->  {dauer / 3600:6.1f} h fuer {args.records} Records")
    print(f"  {'Summe':10} {'':18}->  {gesamt / 3600:6.1f} h sequentiell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
