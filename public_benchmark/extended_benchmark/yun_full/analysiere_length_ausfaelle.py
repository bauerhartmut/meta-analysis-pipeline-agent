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

        # Nicht-zirkulaer wird der Vergleich erst im Laengenband: Ein Ausfall
        # setzt verbrauchtes Budget voraus, sein Reasoning ist also bei 8000
        # Tokens abgeschnitten und damit eine UNTERgrenze des Bedarfs. Erst bei
        # gleicher Textlaenge sagt der Unterschied etwas ueber das Modell aus.
        def intensitaet(row: dict) -> float | None:
            laenge = text_laenge(records[row["record_id"]], cache) or 0
            if not laenge:
                return None
            return (row.get("reasoning_chars") or 0) / laenge * 1000

        def laenge_von(row: dict) -> int:
            return text_laenge(records[row["record_id"]], cache) or 0

        laengen = sorted(x for x in (laenge_von(r) for r in teil) if x)
        if len(laengen) >= 5:
            grenzen = [laengen[int(len(laengen) * q / 5)] for q in range(1, 5)]
        else:
            grenzen = []

        def band(wert: int) -> int:
            for i, grenze in enumerate(grenzen):
                if wert <= grenze:
                    return i
            return len(grenzen)

        print("  Ausfallquote und Reasoning je Textlaengenband:")
        print(f"    {'Band':4} {'Textzeichen':>18} {'n':>4} {'Ausfall':>7} {'Quote':>6} "
              f"{'R/1k Erfolg':>12} {'R/1k Ausfall':>12}")
        for i in range(len(grenzen) + 1):
            block = [r for r in teil if band(laenge_von(r)) == i]
            if not block:
                continue
            faelle = [r for r in block if r["fehlerklasse"] == "length_ohne_ergebnis"]
            erfolge_block = [r for r in block if r not in faelle]
            unten = 0 if i == 0 else grenzen[i - 1]
            oben = grenzen[i] if i < len(grenzen) else laengen[-1]
            int_ok = [x for x in (intensitaet(r) for r in erfolge_block) if x is not None]
            int_fail = [x for x in (intensitaet(r) for r in faelle) if x is not None]
            print(f"    B{i + 1:<3} {unten:>7}..{oben:<7} {len(block):4d} {len(faelle):7d} "
                  f"{len(faelle) / len(block) * 100:5.1f}% "
                  f"{statistics.median(int_ok) if int_ok else 0:12.2f} "
                  f"{statistics.median(int_fail) if int_fail else 0:12.2f}")

        # Gepaarte Gegenprobe: je Ausfall die Erfolge mit aehnlicher Laenge
        # (Faktor 0,8 bis 1,25) und deren Reasoning-Intensitaet.
        paare: list[tuple[float, float]] = []
        for r in ausfall:
            l = laenge_von(r)
            if not l:
                continue
            nachbarn = [e for e in erfolg if l * 0.8 <= laenge_von(e) <= l * 1.25]
            werte = [x for x in (intensitaet(e) for e in nachbarn) if x is not None]
            eigen = intensitaet(r)
            if werte and eigen is not None:
                paare.append((eigen, statistics.median(werte)))
        if paare:
            f_aus = statistics.median(p[0] for p in paare)
            f_ok = statistics.median(p[1] for p in paare)
            faktor = f"{f_aus / f_ok:.1f}" if f_ok else "n/a"
            print(f"  Gepaart nach Textlaenge (+-25 %): {len(paare)} Ausfaelle mit "
                  f"Vergleichsgruppe, Reasoning je 1000 Zeichen "
                  f"{f_aus:.2f} (Ausfall) gegen {f_ok:.2f} (Erfolg) = Faktor {faktor}")
            print("    Hinweis: Der Wert der Ausfaelle ist bei 8000 Tokens abgeschnitten,")
            print("    also eine Untergrenze des tatsaechlichen Bedarfs.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
