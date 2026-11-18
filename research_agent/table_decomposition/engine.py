"""Engine: Planen, Extrahieren, Rekonstruieren, Pruefen.

Die Engine ist modellunabhaengig: sie bekommt eine ``ExtractionBackend``-
Instanz. Ohne Backend plant und prueft sie nur (``dry_run``), was fuer
Strukturanalysen und Kostenvergleiche ohne Netzzugriff genuegt.

Aktivierung in der bestehenden Pipeline (optional):

* ``TableDecompositionConfig.from_agent_config()`` liest
  ``table_decomposition`` aus der Agentenkonfiguration, falls vorhanden, und
  sonst die Umgebungsvariable ``TABLE_DECOMPOSITION``.
* ``augment_prompt_text`` haengt strukturierte Tabellenansichten an den
  Extraktionstext an, ohne den Originaltext zu veraendern (die Zitatpruefung
  bleibt damit intakt).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .backend import ExtractionBackend, ScriptedBackend, UnitResult
from .complexity import assess
from .model import DocumentTables, Table
from .parser import parse_document
from .reconstruct import Reconstruction, ReconstructionResult, unreported_addresses
from .semantics import enrich_table
from .strategies import (
    DIRECTION_CELL,
    DIRECTION_COLUMN,
    DIRECTION_FULL,
    DIRECTION_ROW,
    STRATEGY_ADAPTIVE,
    STRATEGY_FULL,
    STRATEGY_LABELS,
    DecompositionPlan,
    ExtractionUnit,
    PlanOptions,
    PlanOptions as _PlanOptions,
    plan as plan_table,
    refinement_units,
    render_table_view,
)
from .validation import ValidationReport, summarise, validate

_TRUTHY = {"1", "true", "yes", "on", "ja", "wahr"}


@dataclass
class TableDecompositionConfig:
    """Konfiguration; ``enabled`` ist der Schalter der Pipeline."""
    enabled: bool = False
    strategy: str = STRATEGY_FULL
    max_units_per_table: int = 24
    max_calls_per_table: int = 32
    max_depth: int = 2
    max_refinement_units: int = 8
    min_columns_for_split: int = 3
    include_footnotes: bool = True
    include_verbatim: bool = True
    arm_order_fallback: bool = False
    model_name: str = ""

    def options(self) -> PlanOptions:
        return PlanOptions(
            max_units_per_table=self.max_units_per_table,
            include_footnotes=self.include_footnotes,
            include_verbatim=self.include_verbatim,
            min_columns_for_split=self.min_columns_for_split,
            max_refinement_units=self.max_refinement_units,
        )

    @classmethod
    def from_value(cls, value: Any) -> "TableDecompositionConfig":
        """Schalter aus bool, String oder Mapping lesen (fail-soft)."""
        config = cls()
        if value is None:
            return config
        if isinstance(value, bool):
            config.enabled = value
            return config
        if isinstance(value, str):
            text = value.strip().lower()
            if text in _TRUTHY:
                config.enabled = True
            elif text in {"0", "false", "no", "off", "nein", "falsch", ""}:
                config.enabled = False
            else:
                # Ein Strategiebuchstabe schaltet die Engine ein.
                config.enabled = True
                config.strategy = text.upper()
            return config
        if isinstance(value, dict):
            config.enabled = bool(value.get("enabled", True))
            config.strategy = str(value.get("strategy") or STRATEGY_FULL).upper()
            config.max_units_per_table = int(
                value.get("max_units_per_table", config.max_units_per_table)
            )
            config.max_calls_per_table = int(
                value.get("max_calls_per_table", config.max_calls_per_table)
            )
            config.max_depth = int(value.get("max_depth", config.max_depth))
            config.max_refinement_units = int(
                value.get("max_refinement_units", config.max_refinement_units)
            )
            config.min_columns_for_split = int(
                value.get("min_columns_for_split", config.min_columns_for_split)
            )
            config.include_footnotes = bool(
                value.get("include_footnotes", config.include_footnotes)
            )
            config.include_verbatim = bool(
                value.get("include_verbatim", config.include_verbatim)
            )
            config.arm_order_fallback = bool(
                value.get("arm_order_fallback", config.arm_order_fallback)
            )
            config.model_name = str(value.get("model") or config.model_name)
        return config

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "TableDecompositionConfig":
        environment = os.environ if env is None else env
        raw = environment.get("TABLE_DECOMPOSITION")
        config = cls.from_value(raw)
        strategy = environment.get("TABLE_DECOMPOSITION_STRATEGY")
        if strategy:
            config.strategy = strategy.strip().upper()
        depth = environment.get("TABLE_DECOMPOSITION_MAX_DEPTH")
        if depth and depth.isdigit():
            config.max_depth = int(depth)
        return config

    @classmethod
    def from_agent_config(cls) -> "TableDecompositionConfig":
        """Konfigurationsoption ``table_decomposition`` der Agentenkonfiguration.

        Der Import ist absichtlich optional: die Engine bleibt auch ohne
        Agentenkontext nutzbar und aendert keine geschuetzte Konfigurationsdatei.
        """
        try:
            from ..config import get_config  # type: ignore
        except Exception:
            return cls.from_env()
        try:
            agent_config = get_config()
        except Exception:
            return cls.from_env()
        for attribute in ("table_decomposition", "TABLE_DECOMPOSITION"):
            if hasattr(agent_config, attribute):
                return cls.from_value(getattr(agent_config, attribute))
        raw = getattr(agent_config, "raw", None)
        if isinstance(raw, dict) and "table_decomposition" in raw:
            return cls.from_value(raw["table_decomposition"])
        return cls.from_env()


def table_decomposition_enabled(config: Optional[TableDecompositionConfig] = None) -> bool:
    """Ist die Engine in diesem Lauf aktiv?"""
    return (config or TableDecompositionConfig.from_agent_config()).enabled


@dataclass
class TableRun:
    table: Table
    plan: DecompositionPlan
    units: List[ExtractionUnit] = field(default_factory=list)
    results: List[UnitResult] = field(default_factory=list)
    reconstruction: Optional[ReconstructionResult] = None
    validation: Optional[ValidationReport] = None
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, with_prompts: bool = False) -> Dict[str, Any]:
        return {
            "table_id": self.table.table_id,
            "caption": self.table.caption,
            "plan": self.plan.to_dict(with_prompt=with_prompts),
            "n_units": len(self.units),
            "results": [r.to_dict() for r in self.results],
            "reconstruction": self.reconstruction.to_dict() if self.reconstruction else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "telemetry": dict(self.telemetry),
        }


@dataclass
class EngineResult:
    doc_id: str
    parse: DocumentTables
    tables: List[TableRun] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def prediction_cells(self) -> List[Dict[str, Any]]:
        cells: List[Dict[str, Any]] = []
        for run in self.tables:
            if run.reconstruction is not None:
                cells.extend(run.reconstruction.prediction_cells())
        return cells

    def conflicts(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for run in self.tables:
            if run.reconstruction is not None:
                result.extend(c.to_dict() for c in run.reconstruction.conflicts)
        return result

    def validation_summary(self) -> Dict[str, Any]:
        reports = [r.validation for r in self.tables if r.validation is not None]
        return summarise(reports)

    def to_dict(self, with_prompts: bool = False) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "n_tables": len(self.parse.tables),
            "unresolved_blocks": self.parse.unresolved_blocks,
            "telemetry": dict(self.telemetry),
            "validation_summary": self.validation_summary(),
            "tables": [t.to_dict(with_prompts=with_prompts) for t in self.tables],
        }


class TableDecompositionEngine:
    """Ablauf: planen -> extrahieren -> rekonstruieren -> pruefen."""

    def __init__(self, backend: Optional[ExtractionBackend] = None,
                 config: Optional[TableDecompositionConfig] = None):
        self.backend = backend
        self.config = config or TableDecompositionConfig.from_agent_config()

    # -- oeffentlich ------------------------------------------------------
    def plan(self, table: Table, document_text: str = "") -> DecompositionPlan:
        return plan_table(table, self.config.strategy, self.config.options(),
                          document_text)

    def run_document(self, text: str, doc_id: str,
                     context: Optional[Dict[str, Any]] = None,
                     contexts: Optional[Dict[str, Dict[str, Any]]] = None,
                     table_ids: Optional[Sequence[str]] = None) -> EngineResult:
        """Alle Tabellen eines Dokuments verarbeiten.

        ``table_ids`` beschraenkt den Lauf auf bestimmte Tabellen (Benchmark-
        auswahl), gespart wird der Aufruf, nicht die Pruefung.
        """
        parsed = parse_document(text, doc_id)
        result = EngineResult(doc_id=doc_id, parse=parsed)
        allowed = set(table_ids) if table_ids is not None else None
        for table in parsed.tables:
            if allowed is not None and table.table_id not in allowed:
                continue
            table_context = (contexts or {}).get(table.table_id, context) or {}
            enrich_table(table, table_context, assume_order=self.config.arm_order_fallback)
            run = self.run_table(table, text)
            result.tables.append(run)
        result.telemetry = _aggregate([run.telemetry for run in result.tables])
        return result

    def run_table(self, table: Table, document_text: str = "") -> TableRun:
        if not table.context:
            enrich_table(table, {}, assume_order=self.config.arm_order_fallback)
        plan = self.plan(table, document_text)
        table.complexity = plan.complexity.to_dict()
        run = TableRun(table=table, plan=plan, units=list(plan.units))
        recon = Reconstruction()
        recon.register_table(table)

        for unit in list(plan.units):
            unit_result = self._extract(unit)
            run.results.append(unit_result)
            recon.add_result(table, unit, unit_result)

        if self.config.strategy == STRATEGY_ADAPTIVE and self.backend is not None:
            self._refine(table, document_text, run, recon)

        run.reconstruction = recon.build()
        run.validation = validate(table, run.units, run.reconstruction)
        run.telemetry = _unit_telemetry(run.units, run.results,
                                        run.reconstruction, run.validation)
        return run

    # -- intern -----------------------------------------------------------
    def _extract(self, unit: ExtractionUnit) -> UnitResult:
        if self.backend is None:
            return UnitResult(unit_id=unit.unit_id, error="kein_backend")
        started = time.perf_counter()
        try:
            result = self.backend.extract(unit.prompt, unit)
        except Exception as error:  # Ein Ausfall darf den Lauf nicht beenden.
            return UnitResult(
                unit_id=unit.unit_id,
                error=f"backend_exception:{type(error).__name__}: {error}",
                runtime_s=time.perf_counter() - started,
            )
        if not result.runtime_s:
            result.runtime_s = time.perf_counter() - started
        return result

    def _refine(self, table: Table, document_text: str, run: TableRun,
                recon: Reconstruction) -> None:
        depth = 0
        done: set = set()
        while depth < self.config.max_depth:
            interim = recon.build()
            unresolved = unreported_addresses(table, interim)
            unresolved += [c.address for c in interim.conflicts]
            unresolved = [address for address in dict.fromkeys(unresolved)
                          if address not in done]
            budget = self.config.max_calls_per_table - len(run.results)
            if not unresolved or budget <= 0:
                break
            done.update(unresolved)
            options = replace(
                self.config.options(),
                max_refinement_units=min(self.config.max_refinement_units, budget),
            )
            parent = run.plan.units[0].unit_id if run.plan.units else ""
            extra = refinement_units(table, unresolved, options, document_text,
                                     depth=depth + 1, parent_unit_id=parent)
            if not extra:
                break
            depth += 1
            run.units.extend(extra)
            for unit in extra:
                unit_result = self._extract(unit)
                run.results.append(unit_result)
                recon.add_result(table, unit, unit_result)


def _aggregate(telemetries: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    total: Dict[str, Any] = {
        "n_tables": len(telemetries),
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "runtime_s": 0.0,
        "errors": 0,
        "prompt_chars": 0,
        "units_by_direction": {},
        "tables_with_conflict": 0,
    }
    for entry in telemetries:
        for key in ("calls", "prompt_tokens", "completion_tokens", "errors", "prompt_chars"):
            total[key] += int(entry.get(key, 0))
        total["runtime_s"] += float(entry.get("runtime_s", 0.0))
        if entry.get("n_conflict"):
            total["tables_with_conflict"] += 1
        for direction, count in (entry.get("units_by_direction") or {}).items():
            total["units_by_direction"][direction] = (
                total["units_by_direction"].get(direction, 0) + int(count)
            )
    total["runtime_s"] = round(total["runtime_s"], 3)
    total["total_tokens"] = total["prompt_tokens"] + total["completion_tokens"]
    return total


def _unit_telemetry(units: Sequence[ExtractionUnit], results: Sequence[UnitResult],
                    recon: ReconstructionResult, report: ValidationReport) -> Dict[str, Any]:
    by_direction: Dict[str, int] = {}
    for unit in units:
        by_direction[unit.direction] = by_direction.get(unit.direction, 0) + 1
    return {
        "calls": len(results),
        "prompt_tokens": sum(r.prompt_tokens for r in results),
        "completion_tokens": sum(r.completion_tokens for r in results),
        "runtime_s": round(sum(r.runtime_s for r in results), 3),
        "errors": len([r for r in results if r.error]),
        "prompt_chars": sum(len(u.prompt) for u in units),
        "units_by_direction": by_direction,
        "n_conflict": recon.stats.get("n_conflict", 0),
        "n_cells": recon.stats.get("n_cells", 0),
        "validation_status": report.status,
        "validation_errors": len(report.errors),
        "validation_warnings": len(report.warnings),
        "strategy": units[0].strategy if units else "",
        "strategy_label": STRATEGY_LABELS.get(units[0].strategy, "") if units else "",
    }


def augment_prompt_text(text: str, doc_id: str,
                        context: Optional[Dict[str, Any]] = None,
                        config: Optional[TableDecompositionConfig] = None,
                        max_tables: int = 4) -> Tuple[str, Dict[str, Any]]:
    """Pipeline-Haken fuer ``table_decomposition: true``.

    Haengt strukturierte Tabellenansichten (Header-Hierarchie, Zeilenlabels,
    Werte je Spalte, Fussnoten) an den Extraktionstext an. Der Originaltext
    bleibt unveraendert, damit die Zitatpruefung weiter greift; ohne aktive
    Konfiguration wird der Text unveraendert zurueckgegeben.
    """
    config = config or TableDecompositionConfig.from_agent_config()
    if not config.enabled:
        return text, {"enabled": False, "tables": 0, "appended_chars": 0}
    parsed = parse_document(text, doc_id)
    options = config.options()
    blocks: List[str] = []
    tables: List[Dict[str, Any]] = []
    for table in parsed.tables[:max_tables]:
        enrich_table(table, context or {}, assume_order=config.arm_order_fallback)
        complexity = assess(table)
        table.complexity = complexity.to_dict()
        blocks.append(f"[[table_structure {table.table_id} | {table.caption[:120]}]]")
        blocks.append(render_table_view(table, options))
        tables.append(
            {
                "table_id": table.table_id,
                "caption": table.caption,
                "rows": len(table.rows),
                "columns": len(table.columns),
                "complexity": complexity.to_dict(),
            }
        )
    if not blocks:
        return text, {"enabled": True, "tables": 0, "appended_chars": 0,
                      "unresolved_blocks": parsed.unresolved_blocks}
    header = (
        "=== Structured table view (table_decomposition; appendix, the "
        "original text above is unchanged) ==="
    )
    addition = header + "\n\n" + "\n\n".join(blocks)
    return text + "\n\n" + addition, {
        "enabled": True,
        "tables": len(tables),
        "table_details": tables,
        "appended_chars": len(addition),
        "unresolved_blocks": parsed.unresolved_blocks,
    }
