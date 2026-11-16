"""Warum laufen Antworten in das Tokenlimit? Vergleich Ausfall gegen Erfolg.

Untersucht je Modell, ob sich Records mit `length_ohne_ergebnis` von
erfolgreichen Records unterscheiden in:
  - Textlaenge des Quelldokuments (Zeichen)
  - Anzahl der Gold-Zellen (bestimmt den noetigen Output)
  - Outcome-Typ
  - Reasoning-Umfang der Antwort (verbraucht das Tokenbudget)

Aufruf:
    python analysiere_length_ausfaelle.py --run yun699_8000_alle_20261117
    python analysiere_length_ausfaelle.py --run ... --modell glm
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parent
RUNS = BENCH / "runs"
STANDARD_RECORDS = HERE / "records" / "yun699.jsonl"


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def text_laenge(record: dict, cache: dict[str, int]) -> int | None:
    """Zeichenzahl des Quelltextes. Steht als document.text_chars im Record;
    nur wenn sie fehlt, wird die Datei gelesen."""
    doc = record.get("document") or {}
    vorab = doc.get("text_chars")
    if isinstance(vorab, int) and vorab > 0:
        return vorab
    pfad = doc.get("path") or ""
    if not pfad:
        return None
    if pfad in cache:
        return cache[pfad]
    datei = REPO / pfad
    if not datei.exists():
        return None
    laenge = len(datei.read_text(encoding="utf-8", errors="replace"))
    cache[pfad] = laenge
    return laenge


def kennzahlen(werte: list[float]) -> str:
    if not werte:
        return "  -  "
    return f"n={len(werte):3d} median={statistics.median(werte):7.0f} mean={statistics.mean(werte):7.0f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--records", type=Path, default=STANDARD_RECORDS)
    ap.add_argument("--modell", default=None, help="nur dieses Modell (Standard: alle)")
    args = ap.parse_args()

    rows = lies(RUNS / args.run / "predictions.jsonl")
    records = {r["record_id"]: r for r in lies(args.records)}
    if args.modell:
        rows = [r for r in rows if r["model"] == args.modell]

    cache: dict[str, int] = {}
    for modell in sorted({r["model"] for r in rows}):
        teil = [r for r in rows if r["model"] == modell]
        ausfall = [r for r in teil if r["fehlerklasse"] == "length_ohne_ergebnis"]
        erfolg = [r for r in teil if not r["failed"] and not r["parse_error"]
                  and r["fehlerklasse"] == ""]
        if not ausfall:
            print(f"\n{modell}: keine Length-Ausfaelle (n={len(teil)})")
            continue

        print(f"\n=== {modell} ===")
        print(f"Length-Ausfaelle: {len(ausfall)} von {len(teil)} "
              f"({len(ausfall) / len(teil) * 100:.1f} %)")

        for name, gruppe in (("Ausfall", ausfall), ("Erfolg", erfolg)):
            laengen = [text_laenge(records[r["record_id"]], cache) for r in gruppe]
            laengen = [x for x in laengen if x is not None]
            zellen = [len((records[r["record_id"]].get("gold") or {}).get("cells") or [])
                      for r in gruppe]
            reasoning = [r.get("reasoning_chars") or 0 for r in gruppe]
            print(f"  {name:8} Textzeichen {kennzahlen(laengen)}")
            print(f"  {name:8} Gold-Zellen {kennzahlen(zellen)}")
            print(f"  {name:8} Reasoning   {kennzahlen(reasoning)}")

        print("  Outcome-Typen:")
        for name, gruppe in (("Ausfall", ausfall), ("Erfolg", erfolg)):
            typen = collections.Counter(
                (records[r["record_id"]].get("context") or {}).get("outcome_type") or "?"
                for r in gruppe
            )
            gesamt = sum(typen.values()) or 1
            verteilung = ", ".join(f"{t} {n} ({n / gesamt * 100:.0f} %)" for t, n in typen.most_common())
            print(f"    {name:8} {verteilung}")

        # Steigt die Quote mit der Position im Datensatz, und haengt das an der
        # Textlaenge? Beides getrennt zeigen, sonst wird eine Korrelation mit der
        # Laenge behauptet, die es nicht gibt.
        position = {r["record_id"]: i for i, r in enumerate(lies(args.records))}
        sortiert = sorted(teil, key=lambda r: position.get(r["record_id"], 0))
        viertel = max(len(sortiert) // 4, 1)
        print("  Quartile nach Position im Datensatz:")
        for i in range(4):
            block = sortiert[i * viertel:(i + 1) * viertel] if i < 3 else sortiert[3 * viertel:]
            if not block:
                continue
            n_fail = sum(1 for r in block if r["fehlerklasse"] == "length_ohne_ergebnis")
            laengen = [text_laenge(records[r["record_id"]], cache) for r in block]
            laengen = [x for x in laengen if x]
            median = statistics.median(laengen) if laengen else 0
            print(f"    Q{i + 1} {block[0]['record_id']:>12}..{block[-1]['record_id']:<12} "
                  f"n={len(block):3d} Ausfaelle {n_fail:2d} ({n_fail / len(block) * 100:4.1f} %) "
                  f"Textzeichen {median:7.0f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
