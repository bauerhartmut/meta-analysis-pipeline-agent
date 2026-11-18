"""Modellunabhaengige Extraktionsschnittstelle.

Die Engine kennt kein Modell. Sie uebergibt einer ``ExtractionBackend``-Instanz
den Prompt einer Einheit und erwartet eine Antwort im festen JSON-Format.
Damit laesst sich jedes Modell (Gateway, lokal, Vision, Testdouble) anschliessen,
ohne die Zerlegung zu beruehren.

Beigefuegt sind nur zwei Umsetzungen ohne Netzzugriff:
``ScriptedBackend`` (Tests, deterministisch) und ``CallableBackend`` (Wrapper um
eine beliebige Funktion). Ein echter Modellaufruf wird ausserhalb dieses Moduls
verdrahtet (siehe ``README.md``).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Sequence

from .parser import normalise_number_text
from .strategies import ExtractionUnit

SYSTEM_PROMPT = (
    "You read numbers from scientific tables. You answer with a single JSON "
    "object and nothing else. You never invent a value: a cell that is not "
    "printed is omitted."
)

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


@dataclass
class PredictedCell:
    row_id: int
    col_id: int
    value: Optional[float]
    raw: str = ""
    quote: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "col_id": self.col_id,
            "value": self.value,
            "raw": self.raw,
            "quote": self.quote,
        }


@dataclass
class UnitResult:
    unit_id: str
    cells: List[PredictedCell] = field(default_factory=list)
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    runtime_s: float = 0.0
    error: str = ""
    finish_reason: str = ""
    model: str = ""
    retries: int = 0

    @property
    def failed(self) -> bool:
        return bool(self.error)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "model": self.model,
            "cells": [c.to_dict() for c in self.cells],
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "runtime_s": round(self.runtime_s, 3),
            "error": self.error,
            "finish_reason": self.finish_reason,
            "retries": self.retries,
            "text_chars": len(self.text),
        }


class ExtractionBackend(Protocol):
    name: str

    def extract(self, prompt: str, unit: ExtractionUnit) -> UnitResult:
        ...


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("%", "").strip()
    try:
        return float(normalise_number_text(text))
    except ValueError:
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_cells(text: str) -> tuple[List[PredictedCell], str]:
    """JSON-Antwort einer Einheit lesen; (Zellen, Fehlertext)."""
    if not text or not text.strip():
        return [], "leere_antwort"
    cleaned = _FENCE_RE.sub("", text.strip())
    payload: Optional[Dict[str, Any]] = None
    try:
        candidate = json.loads(cleaned)
        if isinstance(candidate, dict):
            payload = candidate
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                candidate = json.loads(cleaned[start:end + 1])
                if isinstance(candidate, dict):
                    payload = candidate
            except json.JSONDecodeError:
                payload = None
    if payload is None:
        return [], "kein_json"
    raw_cells = payload.get("cells")
    if raw_cells is None:
        return [], "kein_zellenfeld"
    if not isinstance(raw_cells, list):
        return [], "zellen_keine_liste"

    cells: List[PredictedCell] = []
    for entry in raw_cells:
        if not isinstance(entry, dict):
            continue
        row_id = _as_int(entry.get("row", entry.get("row_id")))
        col_id = _as_int(entry.get("column", entry.get("col", entry.get("col_id"))))
        if row_id is None or col_id is None:
            continue
        raw = str(entry.get("raw") or "").strip()
        quote = str(entry.get("quote") or "").strip()
        value = _as_float(entry.get("value"))
        if value is None and raw:
            value = _as_float(raw)
        cells.append(PredictedCell(row_id=row_id, col_id=col_id, value=value,
                                   raw=raw, quote=quote))
    if not cells and raw_cells:
        return [], "zellen_unlesbar"
    return cells, ""


class CallableBackend:
    """Backend um eine Funktion ``fn(prompt, unit) -> UnitResult | str | dict``."""

    def __init__(self, fn: Callable[[str, ExtractionUnit], Any], name: str = "callable"):
        self._fn = fn
        self.name = name

    def extract(self, prompt: str, unit: ExtractionUnit) -> UnitResult:
        reply = self._fn(prompt, unit)
        if isinstance(reply, UnitResult):
            if not reply.model:
                reply.model = self.name
            return reply
        if isinstance(reply, dict):
            text = str(reply.get("text") or "")
            result = UnitResult(
                unit_id=unit.unit_id,
                text=text,
                prompt_tokens=int(reply.get("prompt_tokens") or 0),
                completion_tokens=int(reply.get("completion_tokens") or 0),
                runtime_s=float(reply.get("runtime_s") or 0.0),
                finish_reason=str(reply.get("finish_reason") or ""),
                model=str(reply.get("model") or self.name),
            )
            result.cells, error = parse_cells(text)
            result.error = str(reply.get("error") or error)
            return result
        text = "" if reply is None else str(reply)
        result = UnitResult(unit_id=unit.unit_id, text=text, model=self.name)
        result.cells, result.error = parse_cells(text)
        return result


class ScriptedBackend:
    """Deterministisches Backend fuer Tests und Trockenlaeufe.

    ``script`` ist eine Zuordnung ``unit_id -> Zellen`` oder eine Funktion
    ``unit -> Zellen``. Nicht gescriptete Einheiten antworten leer - kein
    Zufall, keine erfundene Zahl.
    """

    def __init__(self, script: Optional[Dict[str, Any]] = None,
                 fn: Optional[Callable[[ExtractionUnit], Iterable[Any]]] = None,
                 name: str = "scripted"):
        self._script = script or {}
        self._fn = fn
        self.name = name

    def _cells_for(self, unit: ExtractionUnit) -> Iterable[Any]:
        if self._fn is not None:
            return self._fn(unit)
        entry = self._script.get(unit.unit_id, [])
        if callable(entry):
            return entry(unit)
        return entry

    def extract(self, prompt: str, unit: ExtractionUnit) -> UnitResult:
        raw = list(self._cells_for(unit))
        cells: List[PredictedCell] = []
        for entry in raw:
            if isinstance(entry, PredictedCell):
                cells.append(entry)
                continue
            if isinstance(entry, dict):
                cells.append(
                    PredictedCell(
                        row_id=int(entry["row"]),
                        col_id=int(entry["column"]),
                        value=_as_float(entry.get("value")),
                        raw=str(entry.get("raw") or ""),
                    )
                )
                continue
            row_id, col_id, value = entry
            cells.append(
                PredictedCell(row_id=int(row_id), col_id=int(col_id),
                              value=float(value), raw=str(value))
            )
        payload = {
            "cells": [
                {"row": c.row_id, "column": c.col_id, "value": c.value, "raw": c.raw}
                for c in cells
            ]
        }
        text = json.dumps(payload, ensure_ascii=False)
        result = UnitResult(
            unit_id=unit.unit_id,
            text=text,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(text) // 4,
            model=self.name,
        )
        result.cells = cells
        return result
