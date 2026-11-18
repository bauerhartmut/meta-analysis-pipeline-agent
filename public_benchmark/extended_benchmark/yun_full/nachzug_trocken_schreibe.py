#!/usr/bin/env python
"""Schreibt fuer den Trockenlauf des Nachzugs Ersatzzeilen in eine Kopie.

Der Trockenlauf soll auch Dedupe und Zusammenfassung durchlaufen. Dafuer braucht
er Zeilen, die ein geglueckter Nachzug erzeugt haette. Dieses Hilfsskript haengt
fuer die ersten `--anzahl` Records mit `length_ohne_ergebnis` je eine solche
Zeile an — deutlich markiert als `dry_run`, damit sie nie fuer eine Messung
gehalten wird.

Es wird ausschliesslich in das uebergebene Verzeichnis geschrieben; der Aufrufer
ist dafuer verantwortlich, dass es eine Kopie ist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-verzeichnis", type=Path, required=True)
    parser.add_argument("--anzahl", type=int, default=2)
    parser.add_argument("--modell", default="glm")
    args = parser.parse_args()

    pfad = args.run_verzeichnis / "predictions.jsonl"
    zeilen = [z for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
    kandidaten: list[str] = []
    for zeile in zeilen:
        try:
            row = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if (
            row.get("model") == args.modell
            and row.get("fehlerklasse") == "length_ohne_ergebnis"
            and row["record_id"] not in kandidaten
        ):
            kandidaten.append(row["record_id"])
        if len(kandidaten) >= args.anzahl:
            break

    if not kandidaten:
        print("keine Length-Ausfaelle gefunden, nichts angehaengt")
        return 1

    with pfad.open("a", encoding="utf-8", newline="\n") as handle:
        for record_id in kandidaten:
            ersatz = {
                "record_id": record_id,
                "model": args.modell,
                "model_id": "gwdg/glm-5.3",
                "http_status": 200,
                "error": "",
                "finish_reason": "stop",
                "completion_tokens": 120,
                "fehlerklasse": "",
                "failed": False,
                "parse_error": "",
                "rows": [
                    {
                        "field": "intervention_group_size",
                        "arm": "intervention",
                        "value": 1.0,
                        "timepoint": "dry-run",
                    }
                ],
                "quelle": "v7_nachzug_trocken",
                "dry_run": True,
            }
            handle.write(json.dumps(ersatz, ensure_ascii=False) + "\n")
    print(f"{len(kandidaten)} Ersatzzeilen angehaengt (dry_run): {', '.join(kandidaten)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
