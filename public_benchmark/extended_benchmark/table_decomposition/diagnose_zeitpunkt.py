"""Offline-Messung Sprint 48: gedruckter Zeitpunkt als Fundstellen-Filter.

Frage: Lassen sich die sechs `timepoint_mismatch`-Felder aufloesen, wenn eine
Fundstelle nur dann an einen Zeitpunkt gebunden wird, wenn **beides gedruckt**
ist - der Zielzeitpunkt im Outcome-Text und derselbe Zeitpunkt in der
Spaltenbeschriftung?

Regel: `research_agent.table_decomposition.zeitpunkt`. Kein Gold in der Regel,
keine Ableitung aus der Spaltenposition: fehlt eine der beiden gedruckten
Seiten, entsteht keine Bindung.

Read-only: Gold und eingefrorene Eingaben werden nur gelesen.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_zeitpunkt.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition import provenienz as pv  # noqa: E402
from research_agent.table_decomposition import tabellenwahl as tw  # noqa: E402
from research_agent.table_decomposition import zeitpunkt as zp  # noqa: E402

from diagnose_populationswahl import _dokument, _gold  # noqa: E402

SPRINT45 = (BENCH / "analysis" / "table_decomposition_20261118"
            / "provenienz_20261118" / "messung.json")


def _kategorien() -> List[Dict[str, Any]]:
    if not SPRINT45.exists():
        return []
    alt = json.loads(SPRINT45.read_text(encoding="utf-8"))
    return [f for f in alt.get("nicht_wertgleich") or []
            if f["kategorie"] == "timepoint_mismatch"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    kategorien = _kategorien()
    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    stellen_gesamt = 0
    stellen_mit_zeitpunkt = 0
    felder_gebunden: List[str] = []
    felder_zeitpunkt: Dict[str, Any] = {}

    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        tables, text, _redundant = rb.load_tables(entries, record)
        if not tables:
            continue
        context = rb.context_of(record)
        alle = _dokument(text, str(record["document"]["id"]), context)
        wahl = tw.waehle(tables, alle, context)
        gelesen = [wahl.tabelle] if (wahl and wahl.wechsel) else list(tables)
        stellen = pv.feld_stellen(gelesen, context)
        gebunden = zp.stellen(stellen, context)

        for orte in stellen.values():
            for stelle in orte:
                stellen_gesamt += 1
                if stelle.zeitpunkt:
                    stellen_mit_zeitpunkt += 1
        for feld in gebunden:
            felder_gebunden.append(f"{record_id}.{feld}")
            felder_zeitpunkt[f"{record_id}.{feld}"] = {
                "tabelle": wahl.tabelle.table_id if wahl and wahl.wechsel
                else gelesen[0].table_id,
                "werte": sorted({stelle.wert for stelle in gebunden[feld]
                                 if stelle.wert is not None}),
                "koepfe": sorted({stelle.zeitpunkt for stelle in gebunden[feld]}),
            }

    sechs: List[Dict[str, Any]] = []
    for eintrag in kategorien:
        record_id, feld = eintrag["record_id"], eintrag["feld"]
        record = records.get(record_id)
        if record is None:
            continue
        tables, text, _redundant = rb.load_tables(grouped[record_id], record)
        context = rb.context_of(record)
        alle = _dokument(text, str(record["document"]["id"]), context)
        wahl = tw.waehle(tables, alle, context)
        gelesen = [wahl.tabelle] if (wahl and wahl.wechsel) else list(tables)
        stellen = pv.feld_stellen(gelesen, context)
        befund = zp.lage(str(context.get("outcome") or ""), stellen, feld)
        sechs.append({
            "record_id": record_id,
            "feld": feld,
            "gold": eintrag["wert"],
            "befund_sprint45": eintrag["befund"],
            "outcome": context.get("outcome"),
            "zeitpunkt_zitat": record.get("timepoint"),
            "ziel": befund["ziel"],
            "koepfe": befund["koepfe"],
            "gebunden": befund["gebunden"],
            "werte": sorted({stelle.wert for stelle in stellen.get(feld) or []
                             if stelle.wert is not None}),
            "entschieden": befund["gebunden"] > 0,
        })

    bericht = {
        "selection": {
            "role": selection.get("role"),
            "n_tables": len(selection.get("tables") or []),
            "n_records": len(selection.get("record_ids") or []),
        },
        "bilanz": {
            "stellen": stellen_gesamt,
            "stellen_mit_gedrucktem_zeitpunkt": stellen_mit_zeitpunkt,
            "felder_gebunden": len(felder_gebunden),
            "timepoint_mismatch": len(sechs),
            "davon_mit_zielzeitpunkt": sum(1 for e in sechs if e["ziel"]),
            "davon_mit_zeitpunkt_im_kopf": sum(1 for e in sechs if e["koepfe"]),
            "davon_entschieden": sum(1 for e in sechs if e["entschieden"]),
        },
        "felder_gebunden": felder_zeitpunkt,
        "timepoint_mismatch": sechs,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bilanz = bericht["bilanz"]
    print(f"Stellen mit gedrucktem Zeitpunkt im Spaltenkopf: "
          f"{bilanz['stellen_mit_gedrucktem_zeitpunkt']} von {bilanz['stellen']}")
    print(f"Felder durch die Zeitpunkt-Regel gebunden: {bilanz['felder_gebunden']}")
    print(f"timepoint_mismatch: {bilanz['timepoint_mismatch']} Felder, "
          f"davon mit Zielzeitpunkt {bilanz['davon_mit_zielzeitpunkt']}, "
          f"mit Zeitpunkt im Kopf {bilanz['davon_mit_zeitpunkt_im_kopf']}, "
          f"entschieden {bilanz['davon_entschieden']}")
    for eintrag in sechs:
        print(f"  {eintrag['record_id']} {eintrag['feld']:<30} "
              f"gold={eintrag['gold']} ziel={eintrag['ziel']} "
              f"koepfe={eintrag['koepfe']} gebunden={eintrag['gebunden']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
