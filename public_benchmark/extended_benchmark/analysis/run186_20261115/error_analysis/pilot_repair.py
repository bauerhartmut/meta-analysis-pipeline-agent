#!/usr/bin/env python3
"""Auswahl und Urteil fuer den 12-Record-Pilot mit Reparaturaufruf.

Drei Gruppen zu je drei Records aus den 47 Fehlzeilen des v7-Folgelaufs plus
drei normale Records mit vollstaendig richtigen Zellen:

* ``length``: die 18 Length-Ausfaelle, bevorzugt die, die auch unter v6 mit
  16.000 Tokens leer blieben; deterministisch ueber die Textlaenge verteilt.
* ``leer``: die 6 gueltigen Antworten ohne Zellen (Gruppengroessen-Gold).
* ``armgemischt``: Records, deren v7-Zellen die Arme mischen
  (``arme_gemischt`` aus ``evaluate_fallback``).
* ``normal``: Antworten mit Zellen, alle richtig, ohne Befund.

Alle drei Gruppen werden nach Textlaenge sortiert und gleichmaessig abgetastet,
damit die Auswahl reproduzierbar ist und nicht an einer Stelle klebt.

Aufruf::

    python .../pilot_repair.py --waehlen
    python .../pilot_repair.py --urteilen --run pilot_repair_20261116
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parents[2]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402
from evaluate_fallback import arme_gemischt  # noqa: E402

CSV = HIER / "fehlerklassifikation_47_records.csv"
RECORDS = BENCH / "records" / "yun_test186.jsonl"
FOLGE_IDS = BENCH / "analysis" / "run186_20261115" / "folge_ids.txt"
JE_GRUPPE = 3


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def lies_csv() -> list[dict[str, str]]:
    import csv

    with CSV.open(encoding="utf-8", newline="") as datei:
        return list(csv.DictReader(datei, delimiter=";"))


def textlaenge(record: dict[str, Any]) -> int:
    pfad = (record.get("document") or {}).get("path") or ""
    datei = REPO / pfad if pfad else None
    return len(datei.read_text(encoding="utf-8", errors="replace")) if datei and datei.exists() else 0


def abtasten(kandidaten: list[dict[str, Any]], k: int) -> list[str]:
    """Deterministisch k ids, gleichmaessig ueber die sortierte Liste verteilt."""
    if len(kandidaten) <= k:
        return [kandidat["record_id"] for kandidat in kandidaten]
    indizes = sorted({round(i * (len(kandidaten) - 1) / (k - 1)) for i in range(k)})
    return [kandidaten[index]["record_id"] for index in indizes]


def waehlen() -> dict[str, Any]:
    zeilen = lies_csv()
    records = {str(r["record_id"]): r for r in read_jsonl(RECORDS)}
    v7 = {str(r["record_id"]): r for r in read_jsonl(
        BENCH / "runs" / "yun_test186_v7_folgelauf_20261116" / "predictions.jsonl")}

    # Die armgemischten Records stehen nicht in den 47 Fehlzeilen, sondern im
    # kombinierten Lauf (v6-Zeilen); ihre Liste stammt aus dessen Auswertung.
    kombiniert = json.loads((HIER.parent / "fallback_eval_kombiniert.json").read_text(encoding="utf-8"))
    gemischt_ids = list((kombiniert.get("arm_gemischt") or {}).get("beispiele") or [])

    gruppen: dict[str, list[dict[str, Any]]] = {"length": [], "leer": [], "armgemischt": [], "normal": []}
    for record_id in gemischt_ids:
        if record_id in records:
            gruppen["armgemischt"].append(
                {"record_id": record_id, "textlaenge": textlaenge(records[record_id]), "v6": "gemischt"}
            )
    for zeile in zeilen:
        record_id = zeile["record_id"]
        record = records[record_id]
        kandidat = {"record_id": record_id, "textlaenge": textlaenge(record), "v6": zeile["v6_status"]}
        status = zeile["v7_status"]
        if status == "length":
            gruppen["length"].append(kandidat)
        elif status == "leer":
            gruppen["leer"].append(kandidat)
        elif status == "zellen":
            rows = (v7.get(record_id) or {}).get("rows") or []
            ziel = str((record.get("context") or {}).get("target_timepoint") or "")
            if rows and arme_gemischt(rows, ziel):
                gruppen["armgemischt"].append(kandidat)
            elif not zeile["kategorien"] and zeile["falscher_wert"] == "0" and zeile["ueberzaehlig"] == "0":
                gruppen["normal"].append(kandidat)

    # Length: die Doppelausfaelle (auch v6 leer) zuerst, dann nach Textlaenge.
    gruppen["length"].sort(key=lambda k: (k["v6"] != "length", k["textlaenge"], k["record_id"]))
    doppelt = [k for k in gruppen["length"] if k["v6"] == "length"]
    if len(doppelt) > JE_GRUPPE:
        gruppen["length"] = doppelt
    gruppen["length"].sort(key=lambda k: (k["textlaenge"], k["record_id"]))

    auswahl = {name: abtasten(sorted(liste, key=lambda k: (k["textlaenge"], k["record_id"])), JE_GRUPPE)
               for name, liste in gruppen.items()}
    ids = [record_id for liste in auswahl.values() for record_id in liste]
    return {
        "auswahl": auswahl,
        "ids": ids,
        "kandidaten": {name: len(liste) for name, liste in gruppen.items()},
        "doppelausfaelle_v6": [k["record_id"] for k in doppelt],
        "textlaenge": {k["record_id"]: k["textlaenge"] for liste in gruppen.values() for k in liste},
    }


def urteil(zeilen: list[dict[str, Any]], gruppen: dict[str, list[str]]) -> dict[str, Any]:
    tokens_gesamt = 0
    repair_tokens = 0
    repair_aufrufe = 0
    length = []
    leer = []
    zellen = []
    for zeile in zeilen:
        tokens_gesamt += int(zeile.get("completion_tokens") or 0)
        if zeile.get("repair_tokens") is not None:
            repair_aufrufe += 1
            repair_tokens += int(zeile["repair_tokens"])
        if zeile.get("fehlerklasse") == "length_ohne_ergebnis":
            length.append(zeile["record_id"])
        elif not zeile.get("rows"):
            leer.append(zeile["record_id"])
        zellen.append(zeile)
    return {
        "zeilen": len(zeilen),
        "length": {"anzahl": len(length), "quote": round(len(length) / len(zeilen), 4) if zeilen else None,
                   "records": length},
        "leer": {"anzahl": len(leer), "quote": round(len(leer) / len(zeilen), 4) if zeilen else None,
                 "records": leer},
        "repair": {"aufrufe": repair_aufrufe, "tokens": repair_tokens},
        "tokens": {
            "gesamt": tokens_gesamt + repair_tokens,
            "primaer": tokens_gesamt,
            "reparatur": repair_tokens,
            "je_record": round((tokens_gesamt + repair_tokens) / len(zeilen), 1) if zeilen else None,
        },
        "gruppen": gruppen,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--waehlen", action="store_true")
    parser.add_argument("--urteilen", action="store_true")
    parser.add_argument("--ohne-regel", action="store_true", help="Urteil als Gegenprobe ablegen")
    parser.add_argument("--run", default="pilot_repair_20261116")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.waehlen:
        ergebnis = waehlen()
        (HIER / "pilot_repair_ids.json").write_text(
            json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(ergebnis["auswahl"], ensure_ascii=False, indent=2))
        print("Kandidaten:", ergebnis["kandidaten"])
        print("IDs:", ",".join(ergebnis["ids"]))
        return 0

    auswahl = json.loads((HIER / "pilot_repair_ids.json").read_text(encoding="utf-8"))
    zeilen = read_jsonl(BENCH / "runs" / args.run / "predictions.jsonl")
    ergebnis = urteil(zeilen, auswahl["auswahl"])
    ziel = args.out or (HIER / ("pilot_ohne_regel_urteil.json" if args.ohne_regel else "pilot_repair_urteil.json"))
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
