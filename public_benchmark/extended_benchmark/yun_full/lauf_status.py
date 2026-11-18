"""Status eines laufenden Extraktionslaufs in einer Zeile pruefen.

Beantwortet die drei Fragen, die beim Doppelprozess-Fehler von
yun699_8000_alle_20261117 schiefgingen:

1. Laeuft genau ein Prozess? (zwei Prozesse schreiben in dieselbe Datei und
   erzeugen Duplikate und zerhackte Zeilen)
2. Hat die Datei Duplikate je (record_id, model)?
3. Wie weit ist der Lauf, und wie hoch ist die Ausfallquote je Modell?

Aufruf:
    python lauf_status.py --run yun699_8000_alle_20261117
    python lauf_status.py --run yun699_8000_alle_20261117 --erwartet 2094

Exit-Code 0 = alles in Ordnung, 1 = Warnung (mehrere Prozesse, Duplikate,
kaputte Zeilen), 2 = Datei fehlt.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
MUSTER = "run_extended_extraction"


RUN_ID_MUSTER = re.compile(r"--run-id[= ]([^\s\"']+)")


def run_id_aus_cmdline(cmdline: str) -> str:
    """Liest den Wert von --run-id aus einer Kommandozeile; leer, wenn keiner da ist."""
    treffer = RUN_ID_MUSTER.search(cmdline or "")
    return treffer.group(1) if treffer else ""


def laufende_prozesse(nur_run: str | None = None) -> list[str]:
    """PIDs der laufenden Extraktionsprozesse.

    Ohne `nur_run`: alle Prozesse, die `run_extended_extraction` ausfuehren.
    Mit `nur_run`: nur diejenigen, deren Kommandozeile `--run-id <nur_run>`
    traegt. Das ist der Unterschied zwischen "irgendein Lauf arbeitet" und
    "dieser Lauf arbeitet": ein fremder Lauf darf einen Nachzug nicht blockieren.
    """
    if os.name == "nt":
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*{MUSTER}*' }} | "
            'ForEach-Object { "$($_.ProcessId)|$($_.CommandLine)" }',
        ]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as fehler:
            print(f"Prozessabfrage fehlgeschlagen: {fehler}")
            return []
        paare = []
        for zeile in out.stdout.splitlines():
            pid, _, cmdline = zeile.partition("|")
            if pid.strip().isdigit():
                paare.append((pid.strip(), cmdline))
    else:
        try:
            out = subprocess.run(["pgrep", "-f", MUSTER], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as fehler:
            print(f"Prozessabfrage fehlgeschlagen: {fehler}")
            return []
        paare = []
        for teil in out.stdout.split():
            if not teil.isdigit():
                continue
            try:
                cmdline = Path(f"/proc/{teil}/cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
            except OSError:
                cmdline = ""
            paare.append((teil, cmdline))

    if nur_run is None:
        return [pid for pid, _ in paare]
    return [pid for pid, cmdline in paare if run_id_aus_cmdline(cmdline) == nur_run]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="Run-Verzeichnis unter runs/")
    ap.add_argument("--erwartet", type=int, default=None,
                    help="erwartete Zeilen am Ende (Records x Modelle)")
    args = ap.parse_args()

    pfad = RUNS / args.run / "predictions.jsonl"

    # Der Prozessstand wird zuerst geprueft: Er haengt nicht davon ab, ob die
    # Datei existiert, und ein Aufrufer (z.B. der Nachzug) liest die erste
    # Zeile als Zustandssignal.
    warnung = False
    pids = laufende_prozesse(args.run)
    alle = laufende_prozesse()
    fremd = [pid for pid in alle if pid not in pids]
    if len(pids) == 1:
        print(f"Prozesse: 1 (PID {pids[0]})  ok")
    elif not pids:
        print("Prozesse: 0  - der Lauf steht (abgebrochen oder fertig)")
        warnung = True
    else:
        print(f"Prozesse: {len(pids)}  ACHTUNG, mehrere Laeufe schreiben in dieselbe Datei: {', '.join(pids)}")
        warnung = True
    if fremd:
        # Fremde Laeufe sind kein Warnfall fuer diesen Run.
        print(f"Fremde Laeufe: {len(fremd)} (andere run-id)  - blockieren diesen Lauf nicht")

    if not pfad.exists():
        print(f"FEHLER: {pfad} fehlt")
        return 2

    zeilen = [z for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
    reihen: list[dict] = []
    kaputt = 0
    for zeile in zeilen:
        try:
            reihen.append(json.loads(zeile))
        except json.JSONDecodeError:
            kaputt += 1

    paare = collections.Counter((r["record_id"], r["model"]) for r in reihen)
    doppelt = sum(n - 1 for n in paare.values() if n > 1)
    print(f"Zeilen: {len(zeilen)} roh, {len(paare)} eindeutige Paare, "
          f"{doppelt} Duplikate, {kaputt} unlesbar"
          + ("  ok" if not doppelt and not kaputt else "  ACHTUNG"))
    if doppelt or kaputt:
        warnung = True

    if args.erwartet:
        rest = max(args.erwartet - len(paare), 0)
        print(f"Fortschritt: {len(paare)}/{args.erwartet} ({len(paare) / args.erwartet * 100:.1f} %), offen: {rest}")

    for modell in sorted({r["model"] for r in reihen}):
        teil = [r for r in reihen if r["model"] == modell]
        failed = sum(1 for r in teil if r["failed"])
        leer = sum(1 for r in teil if not r["failed"]
                   and r["parse_error"] == "keine_verwertbaren_zellen")
        n = len(teil)
        print(f"  {modell:8} n={n:4d}  failed {failed:3d} ({failed / n * 100:4.1f} %)"
              f"  leer {leer:3d} ({leer / n * 100:4.1f} %)")

    if warnung:
        print("\nBefund: pruefen. Bei mehreren Prozessen den aelteren beenden:")
        print("  taskkill //F //PID <pid>   (Windows)")
        print("  kill <pid>                 (Linux)")
    return 1 if warnung else 0


if __name__ == "__main__":
    sys.exit(main())
