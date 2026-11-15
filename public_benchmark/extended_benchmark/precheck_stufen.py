"""Reproduziert die Lockerungsleiter der Gold-Vorpruefung.

Die Befundstufe steht in `precheck_gold.py`. Ob ein Nullergebnis an der Regel
oder an den Daten liegt, laesst sich nur durch Lockern der Regel beantworten:
`mittel` nimmt den Abstandsfilter weg, `weit` zusaetzlich den Prosa- und den
Outcome-Filter. Dieses Skript faehrt alle drei Stufen ueber den Dev-Satz und
die noch nicht verwendeten Records, schreibt die Trefferlisten und rechnet die
Kennzahlen der Leiter.

Es liest nur; Gold, Records und Predictions bleiben unveraendert.

Aufruf:
    python public_benchmark/extended_benchmark/precheck_stufen.py \
        --out public_benchmark/extended_benchmark/analysis/gold_precheck_20261115
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # als Modul (Tests) oder als Skript
    from .precheck_gold import RECORDS, ist_prosa, pruefe_record, schreibe
except ImportError:  # pragma: no cover
    from precheck_gold import RECORDS, ist_prosa, pruefe_record, schreibe

STUFEN = ("eng", "mittel", "weit")


def entdopple(alle: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gelockerte Stufen treffen denselben Wert in vielen Saetzen: einmal zaehlen."""
    gesehen: set[tuple[Any, ...]] = set()
    gefiltert = []
    for eintrag in alle:
        schluessel = (
            eintrag["record_id"],
            eintrag.get("field"),
            eintrag.get("arm"),
            eintrag.get("wert_b"),
        )
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        gefiltert.append(eintrag)
    return gefiltert


def leiter(weit: list[dict[str, Any]], mittel: list[dict[str, Any]]) -> dict[str, Any]:
    """Kennzahlen der Lockerungsleiter aus den Trefferlisten."""
    doppel = [e for e in weit if e["art"] == "doppelangabe"]
    beide_prosa = [e for e in doppel if ist_prosa(e["satz_a"]) and ist_prosa(e["satz_b"])]
    nur_tabelle = [e for e in doppel if not (ist_prosa(e["satz_a"]) and ist_prosa(e["satz_b"]))]
    prozent = [e for e in doppel if "%" in (e["satz_a"] + e["satz_b"])]
    mittel_doppel = [e for e in mittel if e["art"] == "doppelangabe"]
    mittel_prosa = [e for e in mittel_doppel if ist_prosa(e["satz_a"]) and ist_prosa(e["satz_b"])]
    return {
        "weit_treffer": len(weit),
        "weit_doppelangaben": len(doppel),
        "weit_mindestens_ein_tabellensatz": len(nur_tabelle),
        "weit_beide_saetze_prosa": len(beide_prosa),
        "weit_mit_prozentzeichen": len(prozent),
        "mittel_treffer": len(mittel),
        "mittel_doppelangaben": len(mittel_doppel),
        "mittel_beide_saetze_prosa": len(mittel_prosa),
        "weit_beide_saetze_prosa_records": sorted({e["record_id"] for e in beide_prosa}),
        "mittel_beide_saetze_prosa_records": sorted({e["record_id"] for e in mittel_prosa}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    alle_records = [
        json.loads(line)
        for line in args.records.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gruppen = {
        "": [r for r in alle_records if r["document"].get("split") != "dev"],
        "_dev": [r for r in alle_records if r["document"].get("split") == "dev"],
    }

    ergebnis: dict[str, Any] = {"module_aufrufe": 0}
    for suffix, records in gruppen.items():
        treffer: dict[str, list[dict[str, Any]]] = {}
        for stufe in STUFEN:
            gesammelt: list[dict[str, Any]] = []
            for record in records:
                gesammelt.extend(pruefe_record(record, stufe=stufe))
            if stufe != "eng":
                gesammelt = entdopple(gesammelt)
            treffer[stufe] = gesammelt
            schreibe(args.out / f"stufe_{stufe}{suffix}", gesammelt, len(records), stufe)
        ergebnis[suffix.lstrip("_") or "neue_records"] = {
            "records": len(records),
            **leiter(treffer["weit"], treffer["mittel"]),
        }
        print(
            f"{suffix.lstrip('_') or 'neue Records'}: {len(records)} Records | "
            f"eng {len(treffer['eng'])} | mittel {len(treffer['mittel'])} | weit {len(treffer['weit'])}"
        )

    (args.out / "stufen.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"geschrieben: {args.out / 'stufen.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
