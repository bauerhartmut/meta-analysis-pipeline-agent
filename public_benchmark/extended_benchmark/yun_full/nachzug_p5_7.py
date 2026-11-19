#!/usr/bin/env python
"""Nachzug der Fehlzeilen aus dem abgebrochenen P5-Lauf (19.11.2026).

Der P5-Lauf hat vor dem Abbruch sieben Records als Ausfall verbucht, weil der
Anbieter 503/429/Timeout lieferte und keinen Token ausgab. `done_keys` in
`run_extended_extraction.py` zaehlt jede vorhandene Zeile als erledigt, auch
eine Fehlzeile — die sieben bleiben also dauerhaft im Ergebnis, wenn sie nicht
mit `--retry-failed` wiederholt werden.

Das Skript startet nichts von selbst. `--pruefen` (Standard) zeigt Auswahl,
Sperrlage und den Befehl; `--starten` verlangt, dass kein P5-Prozess und keine
Wache mehr laufen, sichert die Datei und haengt die neuen Zeilen an dieselbe
`predictions.jsonl`, damit die Auswertung weiterhin alle 103 ids sieht.

Aufruf:
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/nachzug_p5_7.py --pruefen
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/nachzug_p5_7.py --starten

Exitcodes:
  0  Pruefung in Ordnung bzw. Nachzug gelaufen
  1  keine Fehlzeilen gefunden (nichts zu tun)
  3  P5 oder die Startwache laeuft noch - nichts angefasst
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parents[1]  # public_benchmark: Wurzel des Pakets extended_benchmark
ROOT = HIER.parents[2]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import jobs as jobprotokoll  # noqa: E402

RUN_ID = "yun699_p5_24000_20261118"
RUNS = HIER.parent / "runs"
RUN = RUNS / RUN_ID
GATE = RUNS / "p5_gate_20261118.pid"
PYTHON = ROOT / ".venv/bin/python"
HARNESS = HIER.parent / "run_extended_extraction.py"
RECORDS = HIER / "records" / "yun699.jsonl"
BUDGET = 24000


def fehlzeilen() -> list[dict]:
    """Zeilen des P5-Laufs, die als Ausfall zaehlen.

    Gleiche Definition wie `done_keys`: Fehlerklasse gesetzt oder keine Zellen.
    """
    pfad = RUN / "predictions.jsonl"
    if not pfad.exists():
        return []
    treffer = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        try:
            row = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if row.get("fehlerklasse") or not row.get("rows"):
            treffer.append(row)
    return treffer


def laeuft_noch() -> str:
    """Text, wenn P5- oder Wachenprozess lebt; sonst leerer String."""
    for name, pfad in (("Startwache", GATE), ("Harness", RUN / "harness.lock")):
        if not pfad.exists():
            continue
        try:
            inhalt = pfad.read_text(encoding="utf-8").strip()
            pid = str(json.loads(inhalt).get("pid")) if inhalt.startswith("{") else inhalt
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if jobprotokoll._lebt(pid):  # noqa: SLF001 - bewusst dieselbe Live-Pruefung
            return f"{name} laeuft (PID {pid}, {pfad.name})"
    return ""


def befehl(ids: list[str]) -> list[str]:
    return [
        str(PYTHON),
        str(HARNESS),
        "--records",
        str(RECORDS),
        "--split",
        "",
        "--ids",
        ",".join(ids),
        "--models",
        "glm",
        "--workers",
        "2",
        "--max-tokens",
        str(BUDGET),
        "--run-id",
        RUN_ID,
        "--retry-strategie",
        "neu",
        "--retry-failed",
        "--quelle",
        "p5_24000_nachzug",
    ]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--pruefen", action="store_true", help="nur Lagebild (Standard)")
    g.add_argument("--starten", action="store_true", help="Nachzug wirklich starten")
    args = p.parse_args()

    zeilen = fehlzeilen()
    ids = [row["record_id"] for row in zeilen]
    print(f"Lauf: {RUN_ID}", flush=True)
    print(f"Fehlzeilen: {len(ids)}", flush=True)
    for row in zeilen:
        print(
            f"  {row['record_id']}: HTTP {row.get('http_status')} "
            f"{row.get('fehlerklasse') or 'ohne Zellen'}, "
            f"{row.get('completion_tokens') or 0} Tokens",
            flush=True,
        )
    if not ids:
        print("nichts zu tun: keine Fehlzeile im Lauf.", flush=True)
        return 1

    belegt = laeuft_noch()
    print(f"Sperrlage: {belegt or 'frei'}", flush=True)
    print("Befehl:", " ".join(befehl(ids)), flush=True)

    if not args.starten:
        print("Pruefung beendet; nichts gestartet, nichts geschrieben.", flush=True)
        return 0

    if belegt:
        print(f"ABBRUCH: {belegt}; der laufende P5-Lauf wird nicht angefasst.", flush=True)
        return 3

    sicherung = RUN / "predictions.vor_nachzug_20261119.jsonl"
    if not sicherung.exists():
        shutil.copy2(RUN / "predictions.jsonl", sicherung)
        print(f"Sicherung: {sicherung}", flush=True)
    else:
        print(f"Sicherung vorhanden, nicht ueberschrieben: {sicherung}", flush=True)

    print(f"Start {datetime.now().strftime('%H:%M:%S')}", flush=True)
    ergebnis = subprocess.run(  # noqa: S603 - feste Argumentliste, kein Shell
        befehl(ids), cwd=ROOT, text=True, encoding="utf-8"
    )
    print(f"Harness beendet mit Exitcode {ergebnis.returncode}", flush=True)
    if ergebnis.returncode != 0:
        return ergebnis.returncode

    # `--retry-failed` haengt Zeilen an, statt die Fehlzeile zu ersetzen. Ob
    # dadurch Doppelzeilen entstanden sind, zeigt der Dedupe-Bericht; geschrieben
    # wird hier nichts (`--write` bleibt eine bewusste Einzelentscheidung).
    dedupe = HIER / "dedupe_predictions.py"
    subprocess.run(  # noqa: S603 - Bericht ohne --write
        [str(PYTHON), str(dedupe), "--run", RUN_ID], cwd=ROOT, text=True, encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
