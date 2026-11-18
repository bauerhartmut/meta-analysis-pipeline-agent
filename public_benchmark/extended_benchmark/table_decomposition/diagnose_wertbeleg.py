"""Offline-Messung: steht der Goldwert in der Zelle, die sein Feld belegt?

Zwei Fragen:

1. **Wertabgleich ueber alle erreichbaren Goldfelder**: fuer jede Goldzelle,
   deren Feld eine Zelle oder Kopfangabe der Tabelle traegt, wird die Stelle
   gesucht, die das Feld tatsaechlich belegt (``_spaltenfeld`` spiegelt die
   Zweige aus ``semantics.row_fields``), und dort der gedruckte Wert verglichen.
   Die Feldebene allein ist zu grosszuegig: der Zwangslauf aus
   ``outcome_zeile_20261118`` zeigte, dass jede vollstaendige Zeile dieselben
   Felder erreichbar macht.
2. **Einheiten-Rueckgang**: derselbe Record-Satz wird einmal mit und einmal
   ohne p-Wert-Korroboration geplant (Monkeypatch der Produktionsfunktion, kein
   zweiter Codepfad). Je Record und Verfahren werden die Auftraege verglichen;
   jeder verschwundene Auftrag wird daraufhin geprueft, ob er einen gedruckten
   Goldwert traegt.

Read-only: aendert weder Gold noch eingefrorene Eingaben noch Messartefakte.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_wertbeleg.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition.model import (  # noqa: E402
    ROLE_LABEL,
    ROLE_N,
    ROLE_UNKNOWN,
)
from research_agent.table_decomposition.semantics import (  # noqa: E402
    _NUMBER_RE,
    cell_arm,
    field_for,
    reachable_cells,
)
from research_agent.table_decomposition.strategies import (  # noqa: E402
    PlanOptions,
    plan as plan_table,
)

# Werteabgleich wie in der Spaltenzeitpunkt- und Outcome-Zeilen-Messung.
from diagnose_spaltenzeitpunkte import _zelltreffer  # noqa: E402


def _gold_cells(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    gold = record.get("gold") or {}
    return list(gold.get("cells") or [])


def _zellen_fuer_feld(table, row_id: int, field: str) -> List[Dict[str, Any]]:
    """Zellen dieser Zeile, die ``field`` belegen.

    Spiegelt beide Zweige der Produktion: ``row_fields`` (Spaltenfeld, Rolle aus
    dem Zeilenlabel, Arm-als-Zeile, zweiter Wert einer Verbundzelle) und
    ``reachable_fields`` (Streuungswert aus ``secondary_role`` der Spalte).
    """
    row = table.row(row_id)
    if row is None:
        return []
    role = getattr(row, "value_role", "")
    secondary = getattr(row, "secondary_role", "")
    treffer = []
    for column in table.columns:
        if column.role == ROLE_LABEL:
            continue
        cell = row.cells.get(column.col_id)
        text = (cell.text or "") if cell is not None else ""
        if not text.strip():
            continue
        arm = cell_arm(column, row)
        felder = set()
        if column.field:
            felder.add(column.field)
        elif column.role == ROLE_UNKNOWN and role:
            felder.add(field_for(role, arm))
        elif column.is_outcome and column.role != ROLE_UNKNOWN:
            felder.add(field_for(column.role, arm))
        if column.secondary_role and column.arm:
            felder.add(field_for(column.secondary_role, column.arm))
        if secondary and arm and len(_NUMBER_RE.findall(text)) >= 2:
            felder.add(field_for(secondary, arm))
        if field in felder:
            treffer.append({"col": column.col_id, "text": text})
    return treffer


def _zeile_druckt(table, row_id: int, value: float) -> List[str]:
    """Messzellen dieser Zeile, in denen ``value`` woertlich steht."""
    row = table.row(row_id)
    if row is None:
        return []
    treffer = []
    for col_id in sorted(row.cells):
        if col_id in set(table.label_columns):
            continue
        zelle = row.cells[col_id]
        if _zelltreffer((zelle.text or ""), value):
            treffer.append(f"c{col_id}")
    return treffer


def _kopfangaben(table, field: str) -> List[Dict[str, Any]]:
    """Kopfangaben (``n = 456``), die ``field`` belegen."""
    treffer = []
    for fact in table.header_facts:
        arm = fact.get("arm")
        if field_for(ROLE_N, arm if isinstance(arm, str) else None) != field:
            continue
        treffer.append({"col_start": fact.get("col_start"),
                        "text": str(fact.get("text") or "")})
    return treffer


def _anderswo(table, value: float, ausschluss: Sequence[Tuple[int, int]]) -> List[str]:
    """Wo der Wert sonst noch gedruckt steht (nicht an der belegenden Stelle)."""
    treffer = []
    for row in table.rows:
        for col_id in sorted(row.cells):
            zelle = row.cells[col_id]
            if (row.row_id, col_id) in ausschluss:
                continue
            if _zelltreffer((zelle.text or ""), value):
                treffer.append(f"r{row.row_id}/c{col_id}")
    for band in table.header_bands:
        if _zelltreffer((band.text or ""), value):
            treffer.append(f"kopf:{band.text.strip()[:40]}")
    for note in table.footnotes:
        if _zelltreffer((note.text or ""), value):
            treffer.append(f"fussnote:{note.marker or ''}")
    return treffer


def _felder(record: Dict[str, Any], tables: List[Any],
            context: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    """Je Goldzelle: belegende Stelle, gedruckter Wert, Ort des Werts."""
    gold = _gold_cells(record)
    erreichbar = []
    for table in tables:
        for row_id, field in sorted(reachable_cells(table, context)):
            erreichbar.append((table, row_id, field))
    felder: List[Dict[str, Any]] = []
    for gold_cell in gold:
        field = gold_cell["field"]
        stellen = [(t, r) for t, r, f in erreichbar if f == field]
        if not stellen:
            continue
        belegte_zeilen = {
            row_id for table in tables
            for row_id in (table.corroborated_row or {}).values()
        }
        geprueft: List[Dict[str, Any]] = []
        in_zeile: List[str] = []
        quelle = ""
        for table, row_id in stellen:
            if row_id == -1:
                quelle = "kopf"
                for fact in _kopfangaben(table, field):
                    geprueft.append({"row": -1, "col": fact["col_start"],
                                     "text": fact["text"],
                                     "gedruckt": _zelltreffer(fact["text"],
                                                              gold_cell["value"])})
                continue
            quelle = "zelle"
            for stelle in _zellen_fuer_feld(table, row_id, field):
                geprueft.append({"row": row_id, "col": stelle["col"],
                                 "text": stelle["text"],
                                 "gedruckt": _zelltreffer(stelle["text"],
                                                          gold_cell["value"])})
            in_zeile.extend(f"r{row_id}/{col}" for col in
                            _zeile_druckt(table, row_id, gold_cell["value"]))
        kopf_gedruckt = any(p["gedruckt"] for p in geprueft if p["row"] == -1)
        zell_gedruckt = any(p["gedruckt"] for p in geprueft if p["row"] != -1)
        gedruckt = kopf_gedruckt or zell_gedruckt
        ausschluss = [(p["row"], p["col"]) for p in geprueft]
        anderswo = sorted({
            ort for table in tables
            for ort in _anderswo(table, gold_cell["value"], ausschluss)
        })
        felder.append({
            "record_id": record["record_id"],
            "table_id": next(iter({t.table_id for t, _r in stellen})),
            "field": field,
            "raw": gold_cell.get("raw"),
            "value": gold_cell["value"],
            "zeilen": sorted({r for _t, r in stellen}),
            "belegte_zeile": any(r in belegte_zeilen for _t, r in stellen),
            "quelle": quelle,
            "gedruckt_in_kopf": kopf_gedruckt,
            "gedruckt_in_zelle": zell_gedruckt,
            "gedruckt_belegend": gedruckt,
            "gedruckt_in_zeile": bool(in_zeile) or gedruckt,
            "zeilen_mit_wert": sorted(set(in_zeile)),
            "gepruefte_stellen": geprueft,
            "wert_sonst_gedruckt": anderswo,
        })
    return felder, len(gold)


def _units(tables: List[Any], text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Auftraege je Verfahren (dieselben Aufrufe wie ``offline_run``)."""
    geplant: Dict[str, List[Dict[str, Any]]] = {}
    for strategy in rb.STRATEGIES:
        units: List[Dict[str, Any]] = []
        for table in tables:
            decomposition = plan_table(
                table, strategy, PlanOptions(focus_outcome=True), text)
            for unit in decomposition.units:
                units.append({
                    "strategy": strategy,
                    "table_id": table.table_id,
                    "direction": unit.direction,
                    "row_ids": list(unit.row_ids),
                    "col_ids": list(unit.col_ids),
                    "expected_cells": len(unit.expected_cells),
                })
        geplant[strategy] = units
    return geplant


def _signatur(unit: Dict[str, Any]) -> Tuple[Any, ...]:
    return (unit["table_id"], unit["direction"],
            tuple(unit["row_ids"]), tuple(unit["col_ids"]))


def _unit_gold(table, unit: Dict[str, Any], gold: List[Dict[str, Any]]) -> List[str]:
    """Gedruckte Goldwerte in den erwarteten Zellen dieses Auftrags."""
    if table is None:
        return []
    treffer = []
    for gold_cell in gold:
        for row_id in unit["row_ids"]:
            row = table.row(row_id)
            if row is None:
                continue
            for col_id in unit["col_ids"]:
                cell = row.cells.get(col_id)
                if cell is not None and _zelltreffer((cell.text or ""),
                                                     gold_cell["value"]):
                    treffer.append(f"{gold_cell['field']}={gold_cell['raw']}"
                                   f"@r{row_id}/c{col_id}")
    return treffer


def _abdeckung(tabellen: Dict[str, Any], units: List[Dict[str, Any]],
               gold: List[Dict[str, Any]]) -> List[str]:
    """Goldfelder, deren Wert in einer erwarteten Zelle dieser Auftraege steht."""
    abgedeckt = set()
    for unit in units:
        for hit in _unit_gold(tabellen.get(unit["table_id"]), unit, gold):
            abgedeckt.add(hit.split("=")[0])
    return sorted(abgedeckt)


def _einheiten_diff(record: Dict[str, Any], entries: Sequence[Dict[str, Any]],
                    records: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Plan mit und ohne p-Wert-Korroboration, je Verfahren verglichen."""
    original = rb.corroborate_outcome_row_from_document
    try:
        rb.corroborate_outcome_row_from_document = lambda *a, **k: None
        vorher_tables, text, _redundant = rb.load_tables(list(entries), record)
        vorher = _units(vorher_tables, text)
    finally:
        rb.corroborate_outcome_row_from_document = original
    nachher_tables, _text, _redundant = rb.load_tables(list(entries), record)
    nachher = _units(nachher_tables, _text)

    gold = _gold_cells(record)
    tabellen = {table.table_id: table for table in nachher_tables}
    tabellen_vorher = {table.table_id: table for table in vorher_tables}
    je_verfahren: Dict[str, Any] = {}
    for strategy in rb.STRATEGIES:
        alt = {_signatur(u): u for u in vorher[strategy]}
        neu = {_signatur(u): u for u in nachher[strategy]}
        entfernt = [alt[s] for s in alt if s not in neu]
        dazu = [neu[s] for s in neu if s not in alt]
        klassifiziert = []
        for unit in entfernt:
            table = tabellen.get(unit["table_id"])
            werte = _unit_gold(table, unit, gold) if table is not None else []
            ersetzt = [
                u for u in dazu
                if u["table_id"] == unit["table_id"]
                and u["direction"] == unit["direction"]
                and u["col_ids"] == unit["col_ids"]
                and set(u["row_ids"]) <= set(unit["row_ids"])
            ]
            zeilen = [
                (table.row(row_id).label_path[-1]
                 if table is not None and table.row(row_id) is not None
                 and table.row(row_id).label_path
                 else (table.row(row_id).label
                       if table is not None and table.row(row_id) is not None
                       else f"r{row_id}"))
                for row_id in unit["row_ids"]
            ]
            if werte and ersetzt:
                urteil = "eingeengt_weiter_abgedeckt"
            elif werte:
                urteil = "belegte_messzeile_verloren"
            elif unit["direction"] == "row":
                urteil = "unbelegte_messzeile"
            else:
                urteil = "spalteneinheit_ohne_goldwert"
            klassifiziert.append({
                "table_id": unit["table_id"],
                "direction": unit["direction"],
                "row_ids": unit["row_ids"],
                "labels": zeilen,
                "col_ids": unit["col_ids"],
                "expected_cells": unit["expected_cells"],
                "goldwerte_gedruckt": werte,
                "ersetzt_von": [list(_signatur(u)) for u in ersetzt],
                "urteil": urteil,
            })
        je_verfahren[strategy] = {
            "einheiten_vorher": len(vorher[strategy]),
            "einheiten_nachher": len(nachher[strategy]),
            "goldabdeckung_vorher": _abdeckung(tabellen_vorher, vorher[strategy], gold),
            "goldabdeckung_nachher": _abdeckung(tabellen, nachher[strategy], gold),
            "entfernt": klassifiziert,
            "hinzugekommen": [
                {k: unit[k] for k in ("table_id", "direction", "row_ids", "col_ids")}
                for unit in dazu
            ],
        }
    return {
        "record_id": record["record_id"],
        "vorher_focus_rows": {t.table_id: list(t.focus_rows) for t in vorher_tables},
        "nachher_focus_rows": {t.table_id: list(t.focus_rows) for t in nachher_tables},
        "nachher_corroborated": {t.table_id: dict(t.corroborated_row)
                                 for t in nachher_tables},
        "verfahren": je_verfahren,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)

    felder: List[Dict[str, Any]] = []
    gold_gesamt = 0
    tabellen_je_record: Dict[str, List[str]] = {}
    grouped = rb.group_by_record(selection, None)
    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        tables, _text, _redundant = rb.load_tables(entries, record)
        if not tables:
            continue
        context = rb.context_of(record)
        gefunden, anzahl = _felder(record, tables, context)
        felder.extend(gefunden)
        gold_gesamt += anzahl
        tabellen_je_record[record_id] = [t.table_id for t in tables]

    # Einheiten-Vergleich ueber alle Records; auffaellige Records vollstaendig.
    diffs = []
    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        diff = _einheiten_diff(record, entries, records)
        geaendert = any(
            data["einheiten_vorher"] != data["einheiten_nachher"]
            for data in diff["verfahren"].values()
        )
        if not geaendert:
            continue
        diff["verfahren"] = {
            strategy: data for strategy, data in diff["verfahren"].items()
            if data["einheiten_vorher"] != data["einheiten_nachher"]
        }
        diffs.append(diff)

    je_urteil: Counter = Counter()
    for diff in diffs:
        for data in diff["verfahren"].values():
            for unit in data["entfernt"]:
                je_urteil[unit["urteil"]] += 1

    bericht = {
        "goldzellen_gesamt": gold_gesamt,
        "goldzellen_erreichbar": len(felder),
        "goldzellen_wert_in_kopf": sum(1 for f in felder if f["gedruckt_in_kopf"]),
        "goldzellen_wert_in_zelle": sum(1 for f in felder if f["gedruckt_in_zelle"]),
        "goldzellen_wert_belegend": sum(1 for f in felder if f["gedruckt_belegend"]),
        "goldzellen_wert_in_zeile": sum(1 for f in felder if f["gedruckt_in_zeile"]),
        "goldzellen_wert_nirgends": sum(1 for f in felder if not f["gedruckt_in_zeile"]),
        "tabellen_je_record": tabellen_je_record,
        "felder": felder,
        "einheiten_diff": diffs,
        "urteile": dict(sorted(je_urteil.items())),
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Goldzellen {bericht['goldzellen_erreichbar']}/{gold_gesamt} erreichbar, "
          f"Wert in belegender Stelle {bericht['goldzellen_wert_belegend']} "
          f"(Kopf {bericht['goldzellen_wert_in_kopf']}, "
          f"Zelle {bericht['goldzellen_wert_in_zelle']}), "
          f"in belegter Zeile {bericht['goldzellen_wert_in_zeile']}, "
          f"nirgends {bericht['goldzellen_wert_nirgends']}")
    for feld in felder:
        if not feld["gedruckt_belegend"]:
            print(f"  FEHLT {feld['record_id']} {feld['table_id']} {feld['field']}"
                  f"={feld['raw']} zeilen={feld['zeilen']} "
                  f"sonst={feld['wert_sonst_gedruckt']}")
        elif not feld["gedruckt_in_zelle"]:
            print(f"  ZEILE-OK/ZELLE-NEIN {feld['record_id']} {feld['table_id']} "
                  f"{feld['field']}={feld['raw']} zeilen={feld['zeilen']} "
                  f"wert_in={feld['zeilen_mit_wert']}")
    for diff in diffs:
        print(f"  Einheiten {diff['record_id']}:")
        for strategy, data in diff["verfahren"].items():
            print(f"    {strategy} {data['einheiten_vorher']} -> "
                  f"{data['einheiten_nachher']} gold_vorher="
                  f"{len(data['goldabdeckung_vorher'])} gold_nachher="
                  f"{len(data['goldabdeckung_nachher'])}")
            for unit in data["entfernt"]:
                print(f"      - {unit['direction']} {unit['labels']} "
                      f"gold={unit['goldwerte_gedruckt']} -> {unit['urteil']}")
    print("Urteile:", bericht["urteile"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
