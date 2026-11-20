#!/usr/bin/env python
"""Abdeckung der 33 leeren P5-Records im 6.000-Zeichen-Locator-Ausschnitt.

Fuer jeden Record: wie viele der Goldwerte stehen im Ausschnitt, wie viele im
Volltext, wie viele Pipe-Zeilen hat der Ausschnitt. Offline, kein Modellaufruf.

Anlass: `baue_fall` meldet `goldwerte_im_volltext`; das ist die Zahl fuer das
ganze Dokument. Wer sie als Ausschnitt-Abdeckung liest, waehlt Records als Probe,
deren Zielwerte im Ausschnitt gar nicht stehen (674).

Aufruf:
    .venv/bin/python .../ausschnitt_abdeckung_20261120.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402
from zweistufig_trocken_20261120 import baue_fall  # noqa: E402

MUSTER = HIER / "leere_p5_muster_20261120.json"
AUS = HIER / "ausschnitt_abdeckung_20261120.json"


def main() -> int:
    faelle = json.loads(MUSTER.read_text(encoding="utf-8"))["faelle"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    zeilen = []
    for rid, muster in faelle.items():
        record = records[rid]
        fall = baue_fall(rid, record)
        werte = {round(float(z["value"]), 6) for z in (record.get("gold") or {}).get("cells") or []}
        im_ausschnitt, _, _ = zahlen_im_text(fall["ausschnitt_text"])
        gefunden = sorted(w for w in werte if im_ausschnitt.get(w))
        zeilen.append({
            "record_id": rid,
            "klasse": muster["klasse"],
            "dokument": fall["dokument"],
            "goldzellen": len(fall["gold"]),
            "goldwerte": len(werte),
            "im_ausschnitt": len(gefunden),
            "fehlend": sorted(w for w in werte if not im_ausschnitt.get(w)),
            "pipe_zeilen_ausschnitt": sum(1 for z in fall["ausschnitt_text"].splitlines()
                                          if z.count("|") >= 2),
            "p5_reasoning": muster["reasoning"],
        })
    zeilen.sort(key=lambda z: (-z["im_ausschnitt"], z["record_id"]))
    fair = [z for z in zeilen if z["im_ausschnitt"] == z["goldwerte"] and z["goldwerte"] >= 4]
    ergebnis = {
        "quelle": str(MUSTER.relative_to(ROOT.parent)).replace("\\", "/"),
        "n": len(zeilen),
        "ausschnitt_zeichen": 6000,
        "faelle": zeilen,
        "fair": [z["record_id"] for z in fair],
        "ohne_vollstaendige_abdeckung": len(zeilen) - len(fair),
        "ohne_jeden_goldwert": sum(1 for z in zeilen if z["im_ausschnitt"] == 0),
    }
    AUS.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{len(zeilen)} Records, Ausschnitt 6.000 Zeichen")
    for z in zeilen:
        print(f"  {z['record_id']:<14} {z['klasse']:<20} "
              f"{z['im_ausschnitt']}/{z['goldwerte']}  {z['dokument']}")
    print(f"\nfaire Proben (alle Goldwerte im Ausschnitt, >=4 Werte): {ergebnis['fair']}")
    print(f"ohne vollstaendige Abdeckung: {ergebnis['ohne_vollstaendige_abdeckung']}/{len(zeilen)}")
    print(f"ohne jeden Goldwert im Ausschnitt: {ergebnis['ohne_jeden_goldwert']}/{len(zeilen)}")
    print("geschrieben:", AUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
