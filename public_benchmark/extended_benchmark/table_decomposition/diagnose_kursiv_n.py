"""Offline-Messung: kursiv gesetzte Gruppengroessen (``*n* = 103``).

Verglichen wird derselbe Record-Satz mit dem alten und dem neuen Muster der
Gruppengroessen-Erkennung (Monkeypatch der Modulmuster, kein zweiter
Codepfad). Je Tabelle und Record werden festgehalten:

* Kopfbaender mit ``n``/``=``: alter Fund, neuer Fund, Geometrie,
  uebergeordnete Baender und der Goldarm des zugehoerigen Feldes,
* neue ``header_facts`` und neue erreichbare Felder,
* neu erreichbare, korrekt adressierte und wertgleiche Goldfelder,
* Goldfelder mit Armkonflikt (Wert gedruckt, aber an einen anderen Arm
  gebunden),
* Lauf A-E vorher/nachher (Einheiten, Zellen, Warnungen, Strukturfehler).

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
from typing import Any, Dict, List, Sequence, Tuple

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

FOKUS = (
    ("yun2024:15", "PMC2667135:T4"),
    ("yun2024:662", "PMC4987981:T1"),
    ("yun2024:275", "PMC3654355:T1"),
    ("yun2024:282", "PMC3654355:T2"),
)
KONFLIKTE = ("PMC5777419:T2", "PMC5617873:T2")


@contextmanager
def _alter_stand():
    """Modulmuster auf den Stand vor der Erweiterung setzen."""
    alt = (semantics._GROUP_SIZE_ANY_RE, semantics._GROUP_SIZE_DECL_RE)
    semantics._GROUP_SIZE_ANY_RE, semantics._GROUP_SIZE_DECL_RE = ALT_ANY, ALT_DECL
    try:
        yield
    finally:
        semantics._GROUP_SIZE_ANY_RE, semantics._GROUP_SIZE_DECL_RE = alt


def _gold_cells(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((record.get("gold") or {}).get("cells") or [])


def _felder(tables: Sequence[Any], context: Dict[str, Any]) -> set:
    return {name for table in tables for _row, name in reachable_cells(table, context)}


def _facts(tables: Sequence[Any]) -> List[Dict[str, Any]]:
    return [{**fact, "table_id": table.table_id}
            for table in tables for fact in table.header_facts]


def _baender(table) -> List[Dict[str, Any]]:
    """Alle Kopfbaender, die eine Gruppengroesse drucken koennten."""
    out = []
    for band in sorted(table.header_bands, key=lambda b: (b.level, b.col_start)):
        text = band.text or ""
        if "=" not in text or "n" not in text.lower():
            continue
        out.append({
            "text": text,
            "level": band.level,
            "col_start": band.col_start,
            "col_end": band.col_end,
            "alt_wert": int(ALT_ANY.search(text).group(1)) if ALT_ANY.search(text) else None,
            "neu_wert": int(semantics._GROUP_SIZE_ANY_RE.search(text).group(1))
            if semantics._GROUP_SIZE_ANY_RE.search(text) else None,
            "reine_angabe": group_size_declaration(text) is not None,
            "uebergeordnet": [
                other.text for other in table.header_bands
                if other.level < band.level
                and other.col_start <= band.col_start <= other.col_end
            ],
        })
    return out


def _arm_von_feld(field: str) -> str:
    for arm in ("intervention", "comparator"):
        if field.startswith(arm + "_"):
            return arm
    return ""


def _bilanz(tables: Sequence[Any], context: Dict[str, Any],
            gold: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Erreichbar, wertgleich an der Adresse, Armkonflikt - je Goldzelle."""
    erreichbar = wertgleich = armkonflikt = 0
    for cell in gold:
        feld = cell["field"]
        arm = _arm_von_feld(feld)
        gedruckt = False
        fremder_arm = False
        gefunden = False
        for table in tables:
            for row_id, name in reachable_cells(table, context):
                if name != feld:
                    continue
                gefunden = True
                if row_id == -1:
                    for fact in table.header_facts:
                        if field_for(ROLE_N, fact.get("arm") or None) != feld:
                            continue
                        if fact["value"] == cell["value"]:
                            gedruckt = True
                        elif fact.get("arm") and fact["arm"] != arm:
                            fremder_arm = True
                else:
                    for stelle in _zellen_fuer_feld(table, row_id, feld):
                        if _zelltreffer(stelle["text"], cell["value"]):
                            gedruckt = True
        if not gefunden:
            continue
        erreichbar += 1
        wertgleich += 1 if gedruckt else 0
        if not gedruckt and fremder_arm:
            armkonflikt += 1
    return {"erreichbar": erreichbar, "wertgleich": wertgleich,
            "armkonflikt": armkonflikt}


def _konflikte(tables: Sequence[Any], gold: Sequence[Dict[str, Any]],
               facts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Kopfangaben, die einen Goldwert an einen anderen Arm binden."""
    treffer = []
    for cell in gold:
        if not cell["field"].endswith("group_size"):
            continue
        arm = _arm_von_feld(cell["field"])
        for fact in facts:
            if fact["value"] != cell["value"]:
                continue
            if fact.get("arm") == arm:
                continue
            # Traegt das richtige Band denselben Wert, ist das kein Konflikt,
            # sondern ein Mehrfachdruck (etwa beide Arme mit n = 44).
            if any(other["table_id"] == fact["table_id"]
                   and other.get("arm") == arm
                   and other["value"] == cell["value"] for other in facts):
                continue
            treffer.append({
                "table_id": fact["table_id"],
                "text": fact["text"],
                "value": fact["value"],
                "arm": fact.get("arm"),
                "arm_basis": fact.get("arm_basis"),
                "gold_feld": cell["field"],
                "gold_arm": arm,
            })
    return treffer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    selection = json.loads(rb.DEFAULT_SELECTION.read_text(encoding="utf-8"))
    records = rb.load_records(rb.DEFAULT_RECORDS)
    grouped = rb.group_by_record(selection, None)

    tabellen: List[Dict[str, Any]] = []
    bilanz_alt = {"erreichbar": 0, "wertgleich": 0, "armkonflikt": 0}
    bilanz_neu = {"erreichbar": 0, "wertgleich": 0, "armkonflikt": 0}
    records_diff: List[Dict[str, Any]] = []
    neue_fakten: List[Dict[str, Any]] = []
    neue_felder: List[Dict[str, Any]] = []
    korrekt: List[Dict[str, Any]] = []
    wertgleich: List[Dict[str, Any]] = []
    verloren: List[Dict[str, Any]] = []
    konflikte: List[Dict[str, Any]] = []
    for record_id, entries in sorted(grouped.items()):
        record = records.get(record_id)
        if record is None:
            continue
        with _alter_stand():
            alt_tables, _text, _red = rb.load_tables(entries, record)
        neu_tables, neu_text, _red = rb.load_tables(entries, record)
        if not neu_tables and not alt_tables:
            continue
        context = rb.context_of(record)
        gold = _gold_cells(record)
        alt_felder = _felder(alt_tables, context)
        neu_felder = _felder(neu_tables, context)
        alt_facts = _facts(alt_tables)
        neu_facts = _facts(neu_tables)

        for table in neu_tables:
            alt_t = next((t for t in alt_tables if t.table_id == table.table_id), None)
            if alt_t is None:
                continue
            alt_b = _baender(alt_t)
            neu_b = _baender(table)
            geaendert = [
                {**neu, "alt_wert": alt["alt_wert"], "alt_text": alt["text"]}
                for alt, neu in zip(alt_b, neu_b) if neu["neu_wert"] != alt["alt_wert"]
            ]
            f_alt = {f"{f['text']}|{f['value']}" for f in _facts([alt_t])}
            f_neu = {f"{f['text']}|{f['value']}" for f in _facts([table])}
            if not geaendert and f_alt == f_neu:
                continue
            tabellen.append({
                "record_id": record_id,
                "table_id": table.table_id,
                "baender_geaendert": geaendert,
                "facts_vorher": sorted(f_alt),
                "facts_nachher": sorted(f_neu),
                "felder_vorher": sorted({n for _r, n in reachable_cells(alt_t, context)}),
                "felder_nachher": sorted({n for _r, n in reachable_cells(table, context)}),
            })
            for fact in _facts([table]):
                if f"{fact['text']}|{fact['value']}" not in f_alt:
                    neue_fakten.append({
                        "record_id": record_id,
                        "table_id": table.table_id,
                        "text": fact["text"],
                        "value": fact["value"],
                        "arm": fact.get("arm"),
                        "arm_basis": fact.get("arm_basis"),
                        "level": fact["level"],
                        "cols": [fact["col_start"], fact["col_end"]],
                    })

        # Goldzellen: neu erreichbar, korrekt adressiert, wertgleich.
        for cell in gold:
            feld = cell["field"]
            war = feld in alt_felder
            ist = feld in neu_felder
            if ist and not war:
                neu = {"record_id": record_id, "field": feld, "raw": cell.get("raw"),
                       "value": cell["value"]}
                neue_felder.append(neu)
                arm = _arm_von_feld(feld)
                zutreffend = [
                    fact for fact in _facts(neu_tables)
                    if fact.get("arm") == arm and fact["value"] == cell["value"]
                    and feld.endswith("group_size")
                ]
                if zutreffend:
                    korrekt.append({**neu, "adresse": zutreffend[0]["text"],
                                    "stelle": f"kopf c{zutreffend[0]['col_start']}-"
                                              f"c{zutreffend[0]['col_end']}"})
                    wertgleich.append({**neu, "adresse": zutreffend[0]["text"]})
            if war and not ist:
                verloren.append({"record_id": record_id, "field": feld,
                                 "raw": cell.get("raw")})

        for schluessel, wert in _bilanz(alt_tables, context, gold).items():
            bilanz_alt[schluessel] += wert
        for schluessel, wert in _bilanz(neu_tables, context, gold).items():
            bilanz_neu[schluessel] += wert
        konflikte.extend(_konflikte(neu_tables, gold, _facts(neu_tables)))
        records_diff.append({
            "record_id": record_id,
            "gold_vorher": sum(1 for c in gold if c["field"] in alt_felder),
            "gold_nachher": sum(1 for c in gold if c["field"] in neu_felder),
        })

    with _alter_stand():
        lauf_alt = rb.offline_run(selection, records, list(rb.STRATEGIES), None)
    lauf_neu = rb.offline_run(selection, records, list(rb.STRATEGIES), None)
    summarum = {
        "vorher": {s: lauf_alt["strategy_summary"][s] for s in rb.STRATEGIES},
        "nachher": {s: lauf_neu["strategy_summary"][s] for s in rb.STRATEGIES},
    }
    record_unterschiede = []
    for strategy in rb.STRATEGIES:
        alt = {r["record_id"]: r for r in lauf_alt["records"][strategy]}
        neu = {r["record_id"]: r for r in lauf_neu["records"][strategy]}
        for rid in sorted(set(alt) | set(neu)):
            a, n = alt.get(rid), neu.get(rid)
            if a is None or n is None:
                continue
            felder = ("units", "expected_cells", "validation_warnings",
                      "validation_errors", "gold_reachable")
            if any(a[f] != n[f] for f in felder):
                record_unterschiede.append({
                    "record_id": rid,
                    "strategy": strategy,
                    "vorher": {f: a[f] for f in felder},
                    "nachher": {f: n[f] for f in felder},
                })

    # Phase 1: die vier Fokus-Tabellen mit allen Baendern.
    fokus = []
    for rid, tid in FOKUS:
        record = records.get(rid)
        if record is None:
            continue
        with _alter_stand():
            alt_tables, _t, _r = rb.load_tables(grouped[rid], record)
        neu_tables, _t, _r = rb.load_tables(grouped[rid], record)
        for table in neu_tables:
            if table.table_id != tid:
                continue
            alt = next((t for t in alt_tables if t.table_id == tid), None)
            gold = _gold_cells(record)
            fokus.append({
                "record_id": rid,
                "table_id": tid,
                "baender": _baender(table),
                "facts_vorher": _facts([alt]) if alt else [],
                "facts_nachher": _facts([table]),
                "spalten": [
                    {"col": c.col_id, "arm": c.arm, "basis": c.arm_basis,
                     "role": c.role, "field": c.field, "header": list(c.header_path)}
                    for c in table.columns
                ],
                "gold": [{"field": c["field"], "raw": c.get("raw"), "value": c["value"]}
                         for c in gold if c["field"].endswith("group_size")],
            })

    # Phase 6: Armkonflikte nur diagnostizieren.
    diagnosen = []
    for tid in KONFLIKTE:
        for rid, entries in sorted(grouped.items()):
            record = records.get(rid)
            if record is None:
                continue
            tables, _t, _r = rb.load_tables(entries, record)
            table = next((t for t in tables if t.table_id == tid), None)
            if table is None:
                continue
            diagnosen.append({
                "record_id": rid,
                "table_id": tid,
                "kontext": {
                    "intervention": record["context"].get("intervention"),
                    "comparator": record["context"].get("comparator"),
                },
                "facts": _facts([table]),
                "baender": _baender(table),
                "gold": [{"field": c["field"], "raw": c.get("raw"), "value": c["value"]}
                         for c in _gold_cells(record) if c["field"].endswith("group_size")],
                "fussnoten": [n.text for n in table.footnotes],
                "caption": table.caption,
                "spalten": [{"col": c.col_id, "arm": c.arm, "basis": c.arm_basis,
                             "role": c.role, "field": c.field} for c in table.columns],
            })

    bericht = {
        "bilanz": {"vorher": bilanz_alt, "nachher": bilanz_neu},
        "neue_fakten_eindeutig": len({(f["table_id"], f["text"], f["value"])
                                       for f in neue_fakten}),
        "fokus": fokus,
        "tabellen_geaendert": tabellen,
        "neue_fakten": neue_fakten,
        "neue_felder": neue_felder,
        "korrekt_adressiert": korrekt,
        "wertgleich": wertgleich,
        "verloren": verloren,
        "armkonflikte": konflikte,
        "records_gold": [r for r in records_diff
                         if r["gold_vorher"] != r["gold_nachher"]],
        "lauf": summarum,
        "record_unterschiede": record_unterschiede,
        "armdiagnosen": diagnosen,
    }
    Path(args.out).write_text(
        json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Tabellen mit Aenderung:", len(tabellen))
    print("Bilanz:", bericht["bilanz"])
    print("Neue Fakten:", len(neue_fakten), "eindeutig",
          bericht["neue_fakten_eindeutig"],
          "| neue Goldfelder:", len(neue_felder),
          "| korrekt adressiert:", len(korrekt), "| wertgleich:", len(wertgleich),
          "| verloren:", len(verloren), "| Armkonflikte:", len(konflikte))
    for s in rb.STRATEGIES:
        a, n = summarum["vorher"][s], summarum["nachher"][s]
        print(f"  {s}: gold {a['gold_reachable']} -> {n['gold_reachable']}, "
              f"zellen {a['expected_cells']} -> {n['expected_cells']}, "
              f"einheiten {a['units']} -> {n['units']}, "
              f"warn {a['warnings']} -> {n['warnings']}, "
              f"fehler {a['errors']} -> {n['errors']}")
    for eintrag in tabellen:
        print(f"  {eintrag['record_id']} {eintrag['table_id']}: "
              f"{[b['text'] for b in eintrag['baender_geaendert']]} "
              f"facts +{len(set(eintrag['facts_nachher']) - set(eintrag['facts_vorher']))}")
    if verloren:
        print("VERLOREN:", verloren)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
