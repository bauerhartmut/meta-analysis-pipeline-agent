#!/usr/bin/env python3
"""Benchmarklauf der Zerlegungsverfahren A-E.

Zwei Betriebsarten:

* ``--offline`` (Standard): baut je Tabelle und Verfahren den Plan, misst
  Einheiten, Ausschnittsgroesse, Prompt-Zeichen, erreichbare Zellen und die
  strukturelle Pruefung. **Kein Modellaufruf, keine Netzkosten.** Die
  Token-Zahl ist eine Schaetzung (Zeichen / 4) und als solche markiert.
* ``--model``: echter Extraktionslauf ueber das Gateway. Startet nur mit
  ``--allow-network`` **und** ``--confirm-kosten``; ohne diese Freigaben bricht
  der Lauf vor jedem Netzzugriff ab (Repository-Regel: kein Lauf ohne
  ausdrueckliche Freigabe).

Ergebnisse landen unter ``analysis/table_decomposition_<stamp>/<run_id>/`` und
ueberschreiben keine bestehenden Laeufe.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parents[1]
sys.path.insert(0, str(REPO))

from research_agent.table_decomposition.backend import UnitResult, parse_cells  # noqa: E402
from research_agent.table_decomposition.complexity import assess  # noqa: E402
from research_agent.table_decomposition.engine import (  # noqa: E402
    TableDecompositionConfig,
    TableDecompositionEngine,
)
from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.reconstruct import Reconstruction  # noqa: E402
from research_agent.table_decomposition.semantics import (
    enrich_table,
    reachable_cells,
    transfer_arms_within_document,
)  # noqa: E402
from research_agent.table_decomposition.strategies import (  # noqa: E402
    STRATEGY_ADAPTIVE,
    STRATEGY_LABELS,
    PlanOptions,
    plan as plan_table,
)
from research_agent.table_decomposition.validation import validate  # noqa: E402

STRATEGIES = ("A", "B", "C", "D", "E")
ANALYSIS = BENCH / "analysis"
DEFAULT_RECORDS = BENCH / "yun_full" / "records" / "yun699.jsonl"
DEFAULT_SELECTION = ANALYSIS / "table_decomposition_20261118" / "selection_test.json"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_records(path: Path) -> Dict[str, Dict[str, Any]]:
    return {record["record_id"]: record for record in read_jsonl(path)}


def context_of(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intervention": record["context"].get("intervention"),
        "comparator": record["context"].get("comparator"),
        "outcome": record["context"].get("outcome"),
        "outcome_type": record["context"].get("outcome_type"),
        "timepoint_target": (record.get("timepoint") or {}).get("target"),
    }


def load_tables(selection_entries: Sequence[Dict[str, Any]],
                record: Dict[str, Any], assume_order: bool = False) -> tuple:
    """Alle ausgewaehlten Tabellen eines Records, mit dessen Kontext."""
    entries = [entry for entry in selection_entries
               if record["record_id"] in entry["record_ids"]]
    if not entries:
        return [], ""
    path = REPO / entries[0]["document_path"]
    text = path.read_text(encoding="utf-8", errors="replace")
    doc_id = str(record["document"].get("id") or path.stem)
    parsed = parse_document(text, doc_id)
    context = context_of(record)
    wanted = {entry["table_id"] for entry in entries}
    for table in parsed.tables:
        enrich_table(table, context, assume_order=assume_order)
    transfer_arms_within_document(parsed.tables, context)
    tables = []
    for table in parsed.tables:
        if table.table_id not in wanted:
            continue
        table.complexity = assess(table).to_dict()
        tables.append(table)
    return tables, text


def group_by_record(selection: Dict[str, Any],
                    max_tables: Optional[int]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    entries = selection["tables"][:max_tables] if max_tables else selection["tables"]
    for entry in entries:
        grouped.setdefault(entry["record_ids"][0], []).append(entry)
    return grouped


def offline_run(selection: Dict[str, Any], records: Dict[str, Dict[str, Any]],
                strategies: List[str], max_tables: Optional[int],
                assume_order: bool = False,
                focus_outcome: bool = True) -> Dict[str, Any]:
    """Struktur und Aufwand je Record ueber alle ausgewaehlten Tabellen.

    Die Pipeline verarbeitet je Record mehrere Tabellen eines Dokuments; der
    Benchmark misst dieselbe Einheit. ``gold_reachable`` zaehlt nur Zellen der
    Outcome-Zeile (Spaltenfeld **und** Zeile) - die Obergrenze des
    Tabellenpfads, nicht die Modellleistung. Gruppenangaben aus dem Kopf
    (``n = 456``) zaehlen nicht mit: sie sind noch kein gelesener Zellwert.
    """
    per_strategy: Dict[str, Dict[str, Any]] = {
        strategy: {"records": [], "totals": Counter()} for strategy in strategies
    }
    for record_id, entries in sorted(group_by_record(selection, max_tables).items()):
        record = records.get(record_id)
        if record is None:
            continue
        tables, text = load_tables(entries, record, assume_order=assume_order)
        context = context_of(record)
        fields = {name for table in tables
                  for _row_id, name in reachable_cells(table, context)}
        focus_rows = {row_id for table in tables for row_id in table.focus_rows}
        reachable = sum(1 for cell in record["gold"]["cells"] if cell["field"] in fields)
        for strategy in strategies:
            units = 0
            prompt_chars = 0
            expected = 0
            in_scope = 0
            complete = 0
            errors = 0
            warnings = 0
            findings: Counter = Counter()
            complexity: Counter = Counter()
            per_table: List[Dict[str, Any]] = []
            for table in tables:
                decomposition = plan_table(
                    table, strategy, PlanOptions(focus_outcome=focus_outcome), text)
                report = validate(table, decomposition.units, None)
                chars = sum(len(unit.prompt) for unit in decomposition.units)
                scope_cols = {col for unit in decomposition.units for col in unit.col_ids}
                units += len(decomposition.units)
                prompt_chars += chars
                expected += len({c for unit in decomposition.units for c in unit.expected_cells})
                in_scope += sum(
                    1 for row in table.rows for col_id, cell in row.cells.items()
                    if col_id in scope_cols
                    and col_id not in set(table.label_columns) and (cell.text or "").strip()
                )
                complete += 1 if report.status == "strukturell_vollstaendig" else 0
                errors += len(report.errors)
                warnings += len(report.warnings)
                findings.update(f.code for f in report.findings)
                complexity[table.complexity.get("class", "unbekannt")] += 1
                per_table.append({
                    "table_id": table.table_id,
                    "units": len(decomposition.units),
                    "prompt_chars": chars,
                    "in_scope_cells": in_scope,
                    "validation_status": report.status,
                    "notes": decomposition.notes,
                })
            entry = {
                "record_id": record_id,
                "strategy": strategy,
                "tables": len(tables),
                "table_ids": [table.table_id for table in tables],
                "complexity": complexity.most_common(1)[0][0] if complexity else "unbekannt",
                "units": units,
                "expected_cells": expected,
                "in_scope_cells": in_scope,
                "prompt_chars": prompt_chars,
                "prompt_chars_per_unit": round(prompt_chars / max(units, 1), 1),
                "est_tokens_zeichen_durch_4": round(prompt_chars / 4),
                "gold_cells_record": len(record["gold"]["cells"]),
                "gold_reachable": reachable,
                "focus_rows": len(focus_rows),
                "no_outcome_row": not focus_rows,
                "structural_complete_tables": complete,
                "validation_errors": errors,
                "validation_warnings": warnings,
                "finding_codes": dict(findings),
                "per_table": per_table,
            }
            per_strategy[strategy]["records"].append(entry)
            totals = per_strategy[strategy]["totals"]
            totals["records"] += 1
            totals["tables"] += len(tables)
            totals["tables_complete"] += complete
            totals["units"] += units
            totals["prompt_chars"] += prompt_chars
            totals["expected_cells"] += expected
            totals["gold_reachable"] += reachable
            totals["errors"] += errors
            totals["warnings"] += warnings
    summary = {}
    for strategy, data in per_strategy.items():
        totals = data["totals"]
        records_count = max(totals.get("records", 0), 1)
        summary[strategy] = {
            "strategy_label": STRATEGY_LABELS.get(strategy, strategy),
            "records": totals.get("records", 0),
            "tables": totals.get("tables", 0),
            "tables_complete": totals.get("tables_complete", 0),
            "units": totals.get("units", 0),
            "units_per_record": round(totals.get("units", 0) / records_count, 2),
            "expected_cells": totals.get("expected_cells", 0),
            "prompt_chars": totals.get("prompt_chars", 0),
            "prompt_chars_per_record": round(totals.get("prompt_chars", 0) / records_count, 1),
            "prompt_chars_per_unit": round(
                totals.get("prompt_chars", 0) / max(totals.get("units", 0), 1), 1),
            "est_tokens": round(totals.get("prompt_chars", 0) / 4),
            "gold_reachable": totals.get("gold_reachable", 0),
            "errors": totals.get("errors", 0),
            "warnings": totals.get("warnings", 0),
        }
    return {
        "mode": "offline",
        "strategy_summary": summary,
        "records": {strategy: data["records"] for strategy, data in per_strategy.items()},
        "hinweise": [
            "est_tokens ist eine Schaetzung aus Zeichen/4, kein gemessener Tokenverbrauch.",
            "Ohne Modellaufruf gibt es keine Precision, keinen Recall und keinen F1.",
            "gold_reachable ist die Obergrenze des Tabellenpfads: Goldzellen, deren Feld eine Spalte der Tabelle traegt.",
        ],
    }


class GatewayBackend:
    """Minimaler OpenAI-kompatibler Client (kein SDK, kein Retry-Sturm)."""

    name = "gateway"

    def __init__(self, model_id: str, base: str, key: str, max_tokens: int = 8000,
                 attempts: int = 3):
        self.model_id = model_id
        self.base = base.rstrip("/")
        self.key = key
        self.max_tokens = max_tokens
        self.attempts = attempts

    def extract(self, prompt: str, unit) -> UnitResult:
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": (
                    "You read numbers from scientific tables. You answer with a single "
                    "JSON object and nothing else. You never invent a value."
                )},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"},
            method="POST",
        )
        started = time.monotonic()
        for attempt in range(1, self.attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    body = json.loads(response.read().decode("utf-8", "replace"))
            except urllib.error.HTTPError as error:
                if error.code in (429, 500, 502, 503, 504) and attempt < self.attempts:
                    time.sleep(20 * attempt + random.uniform(0, 3))
                    continue
                return UnitResult(unit_id=unit.unit_id, model=self.model_id,
                                  error=f"HTTP {error.code}",
                                  runtime_s=time.monotonic() - started)
            except Exception as error:  # noqa: BLE001 - Lauf soll weiterlaufen
                return UnitResult(unit_id=unit.unit_id, model=self.model_id,
                                  error=f"{type(error).__name__}: {error}",
                                  runtime_s=time.monotonic() - started)
            choice = (body.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            usage = body.get("usage") or {}
            result = UnitResult(
                unit_id=unit.unit_id,
                text=text,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                runtime_s=time.monotonic() - started,
                finish_reason=str(choice.get("finish_reason") or ""),
                model=self.model_id,
                retries=attempt - 1,
            )
            result.cells, parse_error = parse_cells(text)
            if parse_error and attempt < self.attempts:
                time.sleep(2 * attempt)
                continue
            result.error = "" if not parse_error else parse_error
            return result
        return UnitResult(unit_id=unit.unit_id, model=self.model_id,
                          error="keine_verwertbare_antwort")


def model_run(selection: Dict[str, Any], records: Dict[str, Dict[str, Any]],
              strategies: List[str], model_id: str, base: str, key: str,
              max_tables: Optional[int], config: TableDecompositionConfig,
              max_tokens: int = 24000,
              sink: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Echter Extraktionslauf je Record ueber dessen ausgewaehlte Tabellen.

    ``sink`` bekommt jede Zeile sofort, damit ein langer Lauf bei einem
    Abbruch nicht die bereits bezahlten Ergebnisse verliert.
    """
    backend = GatewayBackend(model_id, base, key, max_tokens=max_tokens)
    rows: List[Dict[str, Any]] = []
    for record_id, entries in sorted(group_by_record(selection, max_tables).items()):
        record = records.get(record_id)
        if record is None or not record["gold"]["cells"]:
            continue
        tables, text = load_tables(entries, record,
                                   assume_order=config.arm_order_fallback)
        if not tables:
            continue
        table_ids = [table.table_id for table in tables]
        doc_id = tables[0].doc_id
        for strategy in strategies:
            run_config = TableDecompositionConfig(
                enabled=True, strategy=strategy,
                max_units_per_table=config.max_units_per_table,
                max_calls_per_table=config.max_calls_per_table,
                max_depth=config.max_depth,
                max_refinement_units=config.max_refinement_units,
                include_footnotes=config.include_footnotes,
                include_verbatim=config.include_verbatim,
                focus_outcome=config.focus_outcome,
                model_name=model_id,
            )
            engine = TableDecompositionEngine(backend=backend, config=run_config)
            result = engine.run_document(text, doc_id, context=context_of(record),
                                        table_ids=table_ids)
            runs = result.tables
            complexities = Counter(
                (run.table.complexity or {}).get("class", "unbekannt") for run in runs
            )
            validations = [run.validation.to_dict() for run in runs if run.validation]
            codes: Counter = Counter()
            status: Counter = Counter()
            for validation in validations:
                status[validation["status"]] += 1
                for finding in validation.get("findings") or []:
                    codes[finding["code"]] += 1
            rows.append(
                {
                    "record_id": record_id,
                    "strategy": strategy,
                    "model": model_id,
                    "table_ids": table_ids,
                    "complexity": complexities.most_common(1)[0][0] if complexities else "unbekannt",
                    "cells": result.prediction_cells(),
                    "conflicts": result.conflicts(),
                    "telemetry": result.telemetry,
                    "validation": {
                        "status": dict(status),
                        "codes": dict(codes),
                        "tables": validations,
                    },
                    "unit_results": [r.to_dict() for run in runs for r in run.results],
                }
            )
            if sink is not None:
                sink(rows[-1])
            print(f"{record_id} {strategy}: {len(rows[-1]['cells'])} Zellen, "
                  f"{result.telemetry['errors']} Ausfaelle, "
                  f"{result.telemetry['total_tokens']} Tokens", flush=True)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--strategies", nargs="+", default=list(STRATEGIES), choices=list(STRATEGIES))
    parser.add_argument("--offline", action="store_true", help="nur Struktur und Kosten (Standard)")
    parser.add_argument("--model", default="", help="Modell-ID fuer einen echten Lauf")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--confirm-kosten", action="store_true")
    parser.add_argument("--max-tables", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-units", type=int, default=24)
    parser.add_argument("--max-calls", type=int, default=32)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--arm-order-fallback", action="store_true",
                        help="Arm aus der Leserichtung annehmen, wenn genau zwei "
                             "Armspalten vorliegen (markiert und pruefpflichtig)")
    parser.add_argument("--max-tokens", type=int, default=24000,
                        help="Completion-Limit je Aufruf (fuer alle Verfahren "
                             "identisch); 8000 reicht bei grossen Tabellen nicht")
    parser.add_argument("--all-rows", dest="all_rows", action="store_true",
                        help="ganze Tabelle lesen statt nur der Outcome-Zeile "
                             "(Vergleichsmessung; Standard ist die Outcome-Zeile)")
    args = parser.parse_args()

    if not args.selection.exists():
        print(f"FEHLT: {args.selection}. Zuerst select_tables.py --write laufen lassen.")
        return 2
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    records = load_records(args.records)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    run_id = args.run_id or (
        "offline_" + datetime.now(timezone.utc).strftime("%H%M%S") if not args.model
        else f"{args.model.replace('/', '_')}_" + datetime.now(timezone.utc).strftime("%H%M%S")
    )
    out_dir = args.out or (ANALYSIS / f"table_decomposition_{stamp}" / run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.model and not args.offline:
        if not (args.allow_network and args.confirm_kosten):
            print("ABBRUCH: Netzlauf ohne Freigabe. Es braucht --allow-network UND "
                  "--confirm-kosten (Repository-Regel: kein Lauf ohne ausdrueckliche "
                  "Freigabe).")
            return 2
        try:
            from research_agent.config import get_config  # type: ignore
            config_obj = get_config()
            key = getattr(config_obj, "tudagpt_api_key", "")
            base = str(getattr(config_obj, "tudagpt_api_base", "")).rstrip("/")
        except Exception as error:  # noqa: BLE001
            print(f"ABBRUCH: Konfiguration nicht lesbar ({error})")
            return 2
        if not key or not base:
            print("ABBRUCH: kein Gateway-Schluessel/keine Basis-URL in der Konfiguration")
            return 2
        config = TableDecompositionConfig(
            enabled=True, max_units_per_table=args.max_units,
            max_calls_per_table=args.max_calls, max_depth=args.max_depth,
            arm_order_fallback=args.arm_order_fallback,
            focus_outcome=not args.all_rows,
        )
        target = out_dir / "predictions.jsonl"
        with target.open("w", encoding="utf-8") as handle:
            def sink(row: Dict[str, Any]) -> None:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()

            rows = model_run(selection, records, args.strategies, args.model, base, key,
                             args.max_tables, config, max_tokens=args.max_tokens,
                             sink=sink)
        payload = {
            "mode": "model",
            "model": args.model,
            "max_tokens": args.max_tokens,
            "strategies": list(args.strategies),
            "arm_order_fallback": bool(args.arm_order_fallback),
            "focus_outcome": bool(not args.all_rows),
            "selection": str(args.selection),
            "selection_sha256": selection.get("records_sha256"),
            "records": len(rows),
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        (out_dir / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
        print(f"geschrieben: {target}")
        return 0

    result = offline_run(selection, records, args.strategies, args.max_tables,
                         assume_order=args.arm_order_fallback,
                         focus_outcome=not args.all_rows)
    result.update({
        "selection": str(args.selection),
        "selection_role": selection.get("role"),
        "selection_sha256": selection.get("records_sha256"),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    target = out_dir / "structure.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'Var':<4}{'Einheiten/Record':>19}{'Zeichen/Record':>17}{'Tok. ges. (Sch.)':>18}"
          f"{'Gold erreichbar':>17}{'Tabellen komplett':>20}")
    for strategy in args.strategies:
        row = result["strategy_summary"][strategy]
        complete = f"{row['tables_complete']}/{row['tables']}"
        print(f"{strategy:<4}{row['units_per_record']:>19}{row['prompt_chars_per_record']:>17}"
              f"{row['est_tokens']:>18}{row['gold_reachable']:>17}"
              f"{complete:>20}")
    print(f"geschrieben: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
