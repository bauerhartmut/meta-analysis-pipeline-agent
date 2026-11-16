"""Doppelte (record_id, model)-Zeilen aus einer predictions.jsonl entfernen.

Noetig, weil `--retry-failed` neue Zeilen anhaengt, ohne die alten Fehlzeilen zu
loeschen: Nach einem Nachzieh-Lauf steht jedes wiederholte Paar zweimal in der
Datei. `auswerte_yun699.py` liest die Zeilen ohne Dedupe und wuerde den Record
doppelt zaehlen.

Je Paar bleibt die letzte brauchbare Zeile stehen: eine ohne `failed`, sonst die
letzte vorhandene.

Aufruf:
    python dedupe_predictions.py --run yun699_8000_alle_20261117            # nur Bericht
    python dedupe_predictions.py --run yun699_8000_alle_20261117 --write    # schreibt zurueck
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"


def _fehlgeschlagen(zeile: str) -> bool:
    """True, wenn die Zeile als Ausfall markiert ist (unlesbar gilt als Ausfall)."""
    try:
        return bool(json.loads(zeile).get("failed"))
    except json.JSONDecodeError:
        return True


def entdopple(zeilen: list[str]) -> tuple[list[str], int, int]:
    """Bereinigt Zeilen einer predictions.jsonl.

    Rueckgabe: (bereinigte Zeilen in Reihenfolge des ersten Auftretens,
    Anzahl Duplikate, Anzahl unlesbarer Zeilen).

    Regel je (record_id, model): Die letzte nicht fehlgeschlagene Zeile gewinnt.
    Gibt es keine erfolgreiche, bleibt die letzte fehlgeschlagene stehen, damit
    der Record als Ausfall sichtbar bleibt statt zu verschwinden.
    """
    gefiltert = [z for z in zeilen if z.strip()]
    reihenfolge: list[tuple[str, str]] = []
    beste: dict[tuple[str, str], str] = {}
    kaputt = 0

    for zeile in gefiltert:
        try:
            row = json.loads(zeile)
        except json.JSONDecodeError:
            kaputt += 1
            continue
        key = (row["record_id"], row["model"])
        if key not in beste:
            reihenfolge.append(key)
            beste[key] = zeile
        elif _fehlgeschlagen(beste[key]) or not row.get("failed"):
            # bisheriger Stand ist ein Ausfall, oder die neue Zeile ist brauchbar
            beste[key] = zeile

    duplikate = len(gefiltert) - len(reihenfolge) - kaputt
    return [beste[key] for key in reihenfolge], duplikate, kaputt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="Run-Verzeichnis unter runs/")
    ap.add_argument("--write", action="store_true", help="bereinigte Datei zurueckschreiben")
    args = ap.parse_args()

    pfad = RUNS / args.run / "predictions.jsonl"
    if not pfad.exists():
        print(f"FEHLER: {pfad} fehlt", flush=True)
        return 2

    roh = pfad.read_text(encoding="utf-8").splitlines()
    bereinigt, duplikate, kaputt = entdopple(roh)
    print(f"Zeilen roh: {len(roh)}, eindeutige Paare: {len(bereinigt)}, "
          f"Duplikate: {duplikate}, unlesbar: {kaputt}")

    if not duplikate and not kaputt:
        print("nichts zu tun")
        return 0
    if not args.write:
        print("Trockenlauf - mit --write wird die Datei ersetzt")
        return 0

    sicherung = pfad.with_suffix(".jsonl.bak")
    shutil.copy2(pfad, sicherung)
    with pfad.open("w", encoding="utf-8", newline="\n") as fh:
        for zeile in bereinigt:
            fh.write(zeile + "\n")
    print(f"geschrieben: {len(bereinigt)} Zeilen (Sicherung: {sicherung.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
