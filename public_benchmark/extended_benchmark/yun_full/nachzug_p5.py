#!/usr/bin/env python
"""Nachzug der Fehlzeilen aus dem abgebrochenen P5-Lauf (19.11.2026).

Der P5-Lauf hat vor dem Abbruch Records als Ausfall verbucht, weil der Anbieter
503/429/Timeout lieferte und keinen Token ausgab. `done_keys` in
`run_extended_extraction.py` zaehlt jede vorhandene Zeile als erledigt, auch
eine Fehlzeile — sie bleibt also dauerhaft im Ergebnis, wenn sie nicht mit
`--retry-failed` wiederholt wird.

`--retry-failed` haengt die neue Zeile an, ohne die Fehlzeile zu ersetzen. Nach
dem Lauf stuende jedes wiederholte Paar damit zweimal in `predictions.jsonl`,
und `auswerte_yun699.py` zaehlte den Record doppelt. Deshalb raeumt dieses
Skript nach dem Harness-Lauf selbst auf (`eindeutig_machen`): je
(record_id, model) bleibt genau eine Zeile stehen, die letzte brauchbare. Die
Datei wird gesichert und erst dann ersetzt; hat danach ein Record nicht genau
eine brauchbare Zeile, endet das Skript mit Exitcode 4.

Das Skript startet nichts von selbst. `--pruefen` (Standard) zeigt Auswahl,
Sperrlage, Eindeutigkeit und den Befehl; `--starten` verlangt, dass kein
P5-Prozess und keine Wache mehr laufen, sichert die Datei und haengt die neuen
Zeilen an dieselbe `predictions.jsonl`, damit die Auswertung weiterhin alle
103 ids sieht.

Aufruf:
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/nachzug_p5.py --pruefen
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/nachzug_p5.py --starten

Exitcodes:
  0  Pruefung in Ordnung bzw. Nachzug gelaufen und eindeutig
  1  keine Fehlzeilen gefunden (nichts zu tun)
  3  P5 oder die Startwache laeuft noch - nichts angefasst
  4  nach dem Nachzug hat ein Record nicht genau eine brauchbare Zeile
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parents[1]  # public_benchmark: Wurzel des Pakets extended_benchmark
ROOT = HIER.parents[2]
sys.path.insert(0, str(BENCH))

from extended_benchmark.yun_full import dedupe_predictions as dedupe  # noqa: E402
from extended_benchmark.yun_full import jobs as jobprotokoll  # noqa: E402

RUN_ID = "yun699_p5_24000_20261118"
RUNS = HIER.parent / "runs"
RUN = RUNS / RUN_ID
GATE = RUNS / "p5_gate_20261118.pid"
PYTHON = ROOT / ".venv/bin/python"
HARNESS = HIER.parent / "run_extended_extraction.py"
RECORDS = HIER / "records" / "yun699.jsonl"
BUDGET = 24000


@dataclass
class Aufraeumbericht:
    """Ergebnis von `eindeutig_machen`."""

    zeilen: int
    duplikate: int
    kaputt: int
    sicherung: Path | None
    fehlend: list[tuple[str, int]]
    verbleibende_ausfaelle: list[str]


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


def eindeutigkeit(pfad: Path) -> tuple[list[str], int, int]:
    """Zeilen ohne Doppel, Zahl der Duplikate, Zahl unlesbarer Zeilen."""
    if not pfad.exists():
        return [], 0, 0
    return dedupe.entdopple(pfad.read_text(encoding="utf-8").splitlines())


def eindeutig_machen(pfad: Path, ids: list[str]) -> Aufraeumbericht:
    """Schreibt je (record_id, model) genau eine Zeile und prueft jede id.

    Die Datei wird nur angefasst, wenn es Duplikate oder unlesbare Zeilen gibt;
    vorher entsteht eine Sicherung, geschrieben wird ueber eine Zwischendatei.
    `fehlend` nennt ids ohne genau eine Zeile, `verbleibende_ausfaelle` ids,
    deren einzige Zeile weiterhin ein Ausfall ist.
    """
    roh = pfad.read_text(encoding="utf-8").splitlines()
    bereinigt, duplikate, kaputt = dedupe.entdopple(roh)
    sicherung: Path | None = None
    if duplikate or kaputt:
        sicherung = pfad.with_name(pfad.name + ".bak")
        shutil.copy2(pfad, sicherung)
        temp = pfad.with_name(pfad.name + ".tmp")
        temp.write_text("".join(zeile + "\n" for zeile in bereinigt), encoding="utf-8")
        temp.replace(pfad)

    zaehler: Counter[str] = Counter()
    ausfall: set[str] = set()
    for zeile in bereinigt:
        row = json.loads(zeile)
        zaehler[row["record_id"]] += 1
        if row.get("failed") or not row.get("rows"):
            ausfall.add(row["record_id"])
        else:
            ausfall.discard(row["record_id"])
    fehlend = [(record_id, zaehler.get(record_id, 0)) for record_id in ids if zaehler.get(record_id, 0) != 1]
    verbleibend = sorted(record_id for record_id in ids if zaehler.get(record_id) == 1 and record_id in ausfall)
    return Aufraeumbericht(len(roh), duplikate, kaputt, sicherung, fehlend, verbleibend)


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

    bereinigt, duplikate, kaputt = eindeutigkeit(RUN / "predictions.jsonl")
    print(
        f"Eindeutigkeit: {len(bereinigt)} Zeilen ohne Doppel, "
        f"{duplikate} Duplikate, {kaputt} unlesbar",
        flush=True,
    )
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

    # `--retry-failed` haengt Zeilen an, statt die Fehlzeile zu ersetzen. Ohne
    # diesen Schritt zaehlte `auswerte_yun699.py` jeden wiederholten Record
    # doppelt; deshalb steht hier genau eine Zeile je Record.
    bericht = eindeutig_machen(RUN / "predictions.jsonl", ids)
    if bericht.sicherung is not None:
        print(f"Sicherung vor dem Aufraeumen: {bericht.sicherung}", flush=True)
    print(
        f"Aufgeraeumt: {bericht.zeilen} Zeilen, {bericht.duplikate} Duplikate entfernt, "
        f"{bericht.kaputt} unlesbar, {len(bericht.fehlend)} Records ohne genau eine Zeile",
        flush=True,
    )
    for record_id, anzahl in bericht.fehlend:
        print(f"  {record_id}: {anzahl} Zeilen", flush=True)
    for record_id in bericht.verbleibende_ausfaelle:
        print(f"  {record_id}: einzige Zeile ist weiterhin ein Ausfall", flush=True)
    return 4 if (bericht.fehlend or bericht.verbleibende_ausfaelle) else 0


if __name__ == "__main__":
    sys.exit(main())
