#!/usr/bin/env python
"""Vortest vor dem P5-Lauf: hat gwdg/glm-5.3 wieder Kapazitaet?

Der Lauf vom 19.11.2026 (siehe docs/internal/p5_wiederanlauf_20261119.md) ist
nach 7 von 103 Records abgebrochen, weil der Anbieter 503 "all instances at max
capacity", 429 und Timeouts lieferte und keinen einzigen Token ausgab. Ein
Neustart des vollen Laufs in dieser Lage laeuft leer durch und hinterlaesst einen
Bericht mit 103 Ausfaellen, der die Startwache gegen jeden spaeteren Lauf sperrt.

Dieses Skript sendet deshalb genau einen Record aus der P5-Auswahl mit denselben
Harness-Parametern wie der echte Lauf, aber kleinem Budget und einem eigenen
Laufverzeichnis. Gemessen wird nur, ob die Gegenseite ueberhaupt antwortet:
HTTP 200 und mehr als 0 Completion-Tokens. Ein `length`-Abschluss ist bei 1400
Tokens zu erwarten und kein Fehler.

Aufruf:
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/pruefe_glm_kapazitaet.py
  ... --versuche 3 --pause 60 --budget 1400 --id yun2024:6

Exitcodes:
  0  Anbieter antwortet (HTTP 200, Tokens > 0) - P5 darf starten
  1  Anbieter antwortet nicht - P5 nicht starten
  2  Aufruffehler (keine Auswahl, Harness nicht startbar)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[3]
VORBEREITUNG = (
    WURZEL
    / "public_benchmark/extended_benchmark/iterativ/ergebnisse/p5_vorbereitung_20261118.json"
)
RECORDS = WURZEL / "public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl"
HARNESS = WURZEL / "public_benchmark/extended_benchmark/run_extended_extraction.py"
RUNS = WURZEL / "public_benchmark/extended_benchmark/runs"
PYTHON = WURZEL / ".venv/bin/python"


def lies_auswahl() -> tuple[list[str], int]:
    """Erste bewertbare id und Gesamtzahl der Ausfaelle aus der Vorbereitung."""
    if not VORBEREITUNG.exists():
        raise SystemExit(f"FEHLER: {VORBEREITUNG} fehlt")
    daten = json.loads(VORBEREITUNG.read_text(encoding="utf-8"))
    ids = [e["record_id"] for e in daten.get("bewertbar", [])]
    if not ids:
        raise SystemExit("FEHLER: keine bewertbaren ids in der Vorbereitung")
    return ids, len(daten.get("ids", []))


def letzte_zeile(pfad: Path) -> dict | None:
    """Letzte geschriebene Prediction-Zeile, oder None."""
    if not pfad.exists():
        return None
    zeilen = [z for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
    if not zeilen:
        return None
    try:
        return json.loads(zeilen[-1])
    except json.JSONDecodeError:
        return None


def bewerte(zeile: dict | None) -> tuple[bool, str]:
    """Antwortet der Anbieter? Gibt (erreichbar, Begruendung) zurueck."""
    if zeile is None:
        return False, "keine Zeile geschrieben"
    status = zeile.get("http_status")
    tokens = (zeile.get("completion_tokens") or 0) + (zeile.get("retry_tokens") or 0)
    klasse = zeile.get("fehlerklasse") or "OK"
    detail = (zeile.get("error") or "").strip().replace("\n", " ")[:160]
    if status == 200 and tokens > 0:
        return True, f"HTTP 200, {tokens} Tokens, Abschluss {zeile.get('finish_reason')}"
    return False, f"HTTP {status}, {tokens} Tokens, Klasse {klasse}: {detail}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--id", default=None, help="record_id; Standard: erste bewertbare id")
    p.add_argument("--budget", type=int, default=1400, help="max-tokens fuer den Vortest")
    p.add_argument("--versuche", type=int, default=3, help="Wiederholungen bei Ausfall")
    p.add_argument("--pause", type=int, default=60, help="Sekunden zwischen zwei Versuchen")
    args = p.parse_args()

    ids, gesamt = lies_auswahl()
    record_id = args.id or ids[0]
    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"p5_vortest_{stempel}"
    run_dir = RUNS / run_id
    ziel = run_dir / "predictions.jsonl"

    print(f"Auswahl: {gesamt} Ausfaelle, Vortest mit {record_id}", flush=True)
    print(f"Lauf: {run_id}, Budget {args.budget}, Versuche {args.versuche}", flush=True)

    befehl = [
        str(PYTHON),
        str(HARNESS),
        "--records",
        str(RECORDS),
        "--split",
        "",
        "--ids",
        record_id,
        "--models",
        "glm",
        "--workers",
        "1",
        "--max-tokens",
        str(args.budget),
        "--run-id",
        run_id,
        "--retry-strategie",
        "neu",
        "--quelle",
        "p5_vortest",
    ]

    for n in range(1, args.versuche + 1):
        print(f"--- Versuch {n}/{args.versuche} ---", flush=True)
        ergebnis = subprocess.run(  # noqa: S603 - feste Argumentliste, kein Shell
            befehl, cwd=WURZEL, capture_output=True, text=True, encoding="utf-8"
        )
        print((ergebnis.stdout or "").strip()[-600:], flush=True)
        if ergebnis.returncode != 0:
            print(f"Harness Exit {ergebnis.returncode}", flush=True)
            print((ergebnis.stderr or "").strip()[-400:], flush=True)

        zeile = letzte_zeile(ziel)
        erreichbar, begruendung = bewerte(zeile)
        print(f"Ergebnis: {begruendung}", flush=True)
        if erreichbar:
            print(f"OK: Anbieter antwortet, P5 darf starten (Daten in {run_dir})", flush=True)
            return 0
        if n < args.versuche:
            print(f"warte {args.pause}s", flush=True)
            time.sleep(args.pause)

    print("NICHT ERREICHBAR: P5 nicht starten, spaeter erneut pruefen.", flush=True)
    print(f"Belege: {run_dir}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
