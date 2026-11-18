"""Offline-Messung: kursiv gesetzte Gruppengroessen (``*n* = 103``).

Verglichen wird derselbe Record-Satz mit dem alten und dem neuen Muster der
Gruppengroessen-Erkennung (Monkeypatch der Modulmuster, kein zweiter
Codepfad). Je Record:

* Bilanz der Goldzellen: erreichbar, wertgleich an der Adresse, Armkonflikt,
* neue und verlorene Goldfelder (mit Wertgleichheit),
* je Tabelle die neuen ``header_facts`` und die geaenderten Baender.

Dazu der Lauf A-E vorher/nachher (Zellen, Einheiten, Warnungen, Fehler).

Read-only: aendert weder Gold noch eingefrorene Eingaben noch Messartefakte.
Aufruf:

    python public_benchmark/extended_benchmark/table_decomposition/diagnose_kursiv_n.py \
        --out public_benchmark/extended_benchmark/analysis/.../messung.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Sequence

HIER = Path(__file__).resolve()
BENCH = HIER.parent.parent
REPO = BENCH.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

import run_benchmark as rb  # noqa: E402

from research_agent.table_decomposition import semantics  # noqa: E402
from research_agent.table_decomposition.model import ROLE_N  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    field_for,
    group_size_declaration,
    reachable_cells,
)

from diagnose_spaltenzeitpunkte import _zelltreffer  # noqa: E402
from diagnose_wertbeleg import _zellen_fuer_feld  # noqa: E402

# Muster vor der Erweiterung (fuer den Vorher-Lauf).
ALT_ANY = re.compile(r"\bn\s*=\s*(\d{1,6})\b", re.IGNORECASE)
ALT_DECL = re.compile(r"^\(?\s*n\s*=\s*(\d{1,6})\s*\)?$", re.IGNORECASE)

# Tabellen, deren Baender der Bericht einzeln zeigt.
FOKUS = {"PMC2667135:T4", "PMC4987981:T1", "PMC3654355:T1", "PMC3654355:T2"}


@contextmanager
def _alter_stand():
    """Modulmuster auf den Stand vor der Erweiterung setzen."""
    alt = (semantics._GROUP_SIZE_ANY_RE, semantics._GROUP_SIZE_DECL_RE)
    semantics._GROUP_SIZE_ANY_RE, semantics._GROUP_SIZE_DECL_RE = ALT_ANY, ALT_DECL
    try:
        yield
    finally:
        semantics._GROUP_SIZE_ANY_RE, semantics._GROUP_SIZE_DECL_RE = alt


def _gold(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((record.get("gold") or {}).get("cells") or [])


def _adressen(tables: Sequence[Any], context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Je Feld alle Stellen, an denen die Tabelle es erwartet.

    Kopfangabe: ``arm`` und gedruckter ``wert`` der Angabe. Messzelle: der
    Zelltext. Beides wird spaeter gegen den Goldwert gehalten.
    """
    adressen: Dict[str, List[Dict[str, Any]]] = {}
    for table in tables:
        for row_id, feld in reachable_cells(table, context):
            if row_id == -1:
                for fact in table.header_facts:
                    if field_for(ROLE_N, fact.get("arm") or None) != feld:
                        continue
                    adressen.setdefault(feld, []).append({
                        "art": "kopf", "arm": fact.get("arm"),
                        "wert": fact["value"], "text": fact["text"],
                        "cols": [fact["col_start"], fact["col_end"]],
                    })
            else:
                for stelle in _zellen_fuer_feld(table, row_id, feld):
                    adressen.setdefault(feld, []).append({
                        "art": "zelle", "arm": None, "wert": None,
                        "text": stelle["text"], "row": row_id,
                    })
    return adressen


def _arm_von_feld(feld: str) -> str:
    return "intervention" if feld.startswith("intervention_") else (
        "comparator" if feld.startswith("comparator_") else "")


def _gedruckt(platz: Dict[str, Any], wert: float) -> bool:
    return (platz["wert"] == wert if platz["art"] == "kopf"
            else _zelltreffer(platz["text"], wert))


def _baender(table) -> List[Dict[str, Any]]:
    """Kopfbaender mit einer Gruppengroesse - alt und neu gelesen."""
    out = []
    for band in sorted(table.header_bands, key=lambda b: (b.level, b.col_start)):
        text = band.text or ""
        alt = ALT_ANY.search(text)
        neu = semantics._GROUP_SIZE_ANY_RE.search(text)
        if not (alt or neu):
            continue
        out.append({
            "text": text, "level": band.level,
            "cols": [band.col_start, band.col_end],
            "alt_wert": int(alt.group(1)) if alt else None,
            "neu_wert": int(neu.group(1)) if neu else None,
            "reine_angabe": group_size_declaration(text) is not None,
        })
    return out


def _zahl(record: Dict[str, Any], adressen: Dict[str, List[Dict[str, Any]]],
          bilanz: Dict[str, int]) -> None:
    """Bilanz eines Records fortschreiben."""
    for cell in _gold(record):
        plaetze = adressen.get(cell["field"])
        if not plaetze:
            continue
        bilanz["erreichbar"] += 1
        if any(_gedruckt(p, cell["value"]) for p in plaetze):
            bilanz["wertgleich"] += 1
        elif any(p["art"] == "kopf" and p["wert"] == cell["value"]
                 and p["arm"] and p["arm"] != _arm_von_feld(cell["field"])
                 for p in plaetze):
            bilanz["armkonflikt"] += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    bilanz = {"vorher": {"erreichbar": 0, "wertgleich": 0, "armkonflikt": 0},
              "nachher": {"erreichbar": 0, "wertgleich": 0, "armkonflikt": 0}}
    tabellen: List[Dict[str, Any]] = []
    neu_an_adresse: List[Dict[str, Any]] = []
    verloren: List[Dict[str, Any]] = []
    neue_fakten: set = set()
    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is not None:
            with _alter_stand():
                alt_tables, _text, _red = rb.load_tables(entries, record)
            neu_tables, _text, _red = rb.load_tables(entries, record)
        else:
            alt_tables = neu_tables = []
        if not neu_tables:
            continue
        context = rb.context_of(record)
        adressen_alt = _adressen(alt_tables, context)
        adressen_neu = _adressen(neu_tables, context)
        _zahl(record, adressen_alt, bilanz["vorher"])
        _zahl(record, adressen_neu, bilanz["nachher"])

        for cell in _gold(record):
            feld = cell["field"]
            war, ist = feld in adressen_alt, feld in adressen_neu
            if ist and not war:
                neu_an_adresse.append({
                    "record_id": record_id, "field": feld,
                    "raw": cell.get("raw"),
                    "wertgleich": any(_gedruckt(p, cell["value"])
                                      for p in adressen_neu[feld]),
                })
            elif war and not ist:
                verloren.append({"record_id": record_id, "field": feld,
                                 "raw": cell.get("raw")})

        for table in neu_tables:
            alt = next((t for t in alt_tables if t.table_id == table.table_id), None)
            if alt is None:
                continue
            alt_keys = {(f["text"], f["value"]) for f in alt.header_facts}
            facts = [f for f in table.header_facts
                     if (f["text"], f["value"]) not in alt_keys]
            if not facts:
                continue
            neue_fakten |= {(table.table_id, f["text"], f["value"]) for f in facts}
            eintrag = {
                "record_id": record_id,
                "table_id": table.table_id,
                "facts_neu": [{"text": f["text"], "value": f["value"],
                               "arm": f.get("arm"), "arm_basis": f.get("arm_basis"),
                               "cols": [f["col_start"], f["col_end"]]}
                              for f in facts],
            }
            if table.table_id in FOKUS:
                eintrag["baender"] = _baender(table)
                eintrag["spalten"] = [{"col": c.col_id, "arm": c.arm,
                                       "role": c.role, "field": c.field}
                                      for c in table.columns]
            tabellen.append(eintrag)

    with _alter_stand():
        lauf_alt = rb.offline_run(selection, records, list(rb.STRATEGIES), None)
    lauf_neu = rb.offline_run(selection, records, list(rb.STRATEGIES), None)
    lauf = {
        s: {"vorher": {k: lauf_alt["strategy_summary"][s][k] for k in
                       ("gold_reachable", "expected_cells", "units", "warnings", "errors")},
            "nachher": {k: lauf_neu["strategy_summary"][s][k] for k in
                        ("gold_reachable", "expected_cells", "units", "warnings", "errors")}}
        for s in rb.STRATEGIES
    }
    record_unterschiede = []
    for strategy in rb.STRATEGIES:
        alt = {r["record_id"]: r for r in lauf_alt["records"][strategy]}
        neu = {r["record_id"]: r for r in lauf_neu["records"][strategy]}
        for rid in sorted(set(alt) & set(neu)):
            felder = ("units", "expected_cells", "validation_warnings",
                      "validation_errors", "gold_reachable")
            if any(alt[rid][f] != neu[rid][f] for f in felder):
                record_unterschiede.append({
                    "record_id": rid, "strategy": strategy,
                    "vorher": {f: alt[rid][f] for f in felder},
                    "nachher": {f: neu[rid][f] for f in felder},
                })

    bericht = {
        "bilanz": bilanz,
        "neue_fakten_eindeutig": len(neue_fakten),
        "tabellen_mit_neuen_fakten": len({t["table_id"] for t in tabellen}),
        "tabellen": tabellen,
        "neu_an_adresse": neu_an_adresse,
        "verloren": verloren,
        "lauf": lauf,
        "record_unterschiede": record_unterschiede,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Bilanz:", bilanz)
    print(f"Neue Kopfangaben: {len(neue_fakten)} eindeutig in "
          f"{bericht['tabellen_mit_neuen_fakten']} Tabellen")
    neu = bericht["neu_an_adresse"]
    print(f"Neu erreichbare Goldfelder: {len(neu)} "
          f"(wertgleich {sum(1 for x in neu if x['wertgleich'])}), "
          f"verloren {len(verloren)}")
    for s, werte in lauf.items():
        a, n = werte["vorher"], werte["nachher"]
        print(f"  {s}: gold {a['gold_reachable']} -> {n['gold_reachable']}, "
              f"zellen {a['expected_cells']} -> {n['expected_cells']}, "
              f"einheiten {a['units']} -> {n['units']}, "
              f"warn {a['warnings']} -> {n['warnings']}, "
              f"fehler {a['errors']} -> {n['errors']}")
    for t in tabellen:
        print(f"  {t['record_id']} {t['table_id']}: "
              f"{[(f['text'], f['value'], f['arm']) for f in t['facts_neu']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
