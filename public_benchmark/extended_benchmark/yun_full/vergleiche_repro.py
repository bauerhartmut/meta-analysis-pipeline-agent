"""Denselben Record ueber mehrere Laeufe vergleichen: stabiler oder zufaelliger Ausfall?

Hintergrund: Bei Temperatur 0.0 liefert das Gateway fuer identische Auftraege
nicht zuverlaessig dasselbe Ergebnis. Wer die Length-Ausfallquote als
Record-Eigenschaft liest, zaehlt dabei Reproduktionsvarianz mit. Dieses Skript
stellt dieselben Records aus mehreren Laeufen nebeneinander und trennt beide
Anteile.

Aufruf:
    python vergleiche_repro.py --runs yun699_8000_alle_20261117 q3_repro_a_20261116 q3_repro_b_20261116
    python vergleiche_repro.py --runs A B --modell qwen
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
AUSFALL = "length_ohne_ergebnis"


def lade(run: str, modell: str) -> dict[str, str]:
    pfad = RUNS / run / "predictions.jsonl"
    if not pfad.exists():
        return {}
    ergebnis: dict[str, str] = {}
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        row = json.loads(zeile)
        if row.get("model") != modell:
            continue
        ergebnis[row["record_id"]] = row.get("fehlerklasse") or (
            "leer" if not row.get("rows") else "ok"
        )
    return ergebnis


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--modell", default="glm")
    args = ap.parse_args()

    daten = {run: lade(run, args.modell) for run in args.runs}
    gemeinsam = set.intersection(*(set(d) for d in daten.values()))
    if not gemeinsam:
        print("Keine Records in allen Laeufen gefunden.")
        return 1
    ids = sorted(gemeinsam, key=lambda x: (x.split(":")[0], int(x.split(":")[1])))

    breite = max(len(r) for r in args.runs) + 2
    print(f"{'Record':>12} " + " ".join(f"{r[:breite]:<{breite}}" for r in args.runs))
    zaehler: collections.Counter[int] = collections.Counter()
    for rid in ids:
        stati = [daten[run].get(rid, "-") for run in args.runs]
        zaehler[sum(1 for s in stati if s == AUSFALL)] += 1
        print(f"{rid:>12} " + " ".join(f"{s:<{breite}}" for s in stati))

    print(f"\n{len(ids)} Records in allen {len(args.runs)} Laeufen")
    for anzahl in sorted(zaehler):
        print(f"  in {anzahl} von {len(args.runs)} Laeufen Ausfall: {zaehler[anzahl]} Records")
    stabil = zaehler.get(len(args.runs), 0)
    mindestens_einmal = len(ids) - stabil
    print(f"\n  stabil (in jedem Lauf Ausfall):      {stabil} ({stabil / len(ids) * 100:.0f} %)")
    print(f"  mindestens einmal erfolgreich:       {mindestens_einmal} "
          f"({mindestens_einmal / len(ids) * 100:.0f} %)")
    if stabil and len(args.runs) > 1:
        print(f"\n  -> Ein einzelner Lauf zaehlt zusaetzlich zufaellige Ausfaelle. "
              f"Stabil scheitern {stabil / len(ids) * 100:.0f} %; der Rest der "
              f"beobachteten Quote ist Reproduktionsvarianz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
