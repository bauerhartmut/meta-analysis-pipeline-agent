"""Gemeinsame Helfer der Adapter.

Alle Adapter liefern Records nach ``schema.json``. Fehlende Werte bleiben
fehlend; es wird nichts geschaetzt oder aufgefuellt.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

BENCH_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = BENCH_ROOT / "raw_data"
OUT_ROOT = Path(__file__).resolve().parents[1]

_NUMBER = re.compile(r"^-?\d+(?:[.,]\d+)?$")


def to_float(value: Any) -> float | None:
    """Parst eine Zahl aus String oder Zahl. Leere und unparsebare Werte ergeben None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "NAN", "NONE", "NULL"}:
        return None
    text = text.replace("\u2212", "-").replace(" ", "")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    if not _NUMBER.match(text):
        return None
    return float(text)


def cell(field: str, arm: str | None, value: Any, unit: str, source: str = "") -> dict[str, Any] | None:
    """Baut eine Gold-Zelle; gibt None zurueck, wenn der Wert fehlt."""
    number = to_float(value)
    if number is None:
        return None
    return {"field": field, "arm": arm, "value": number, "unit": unit, "source": source}


def cells_from(values: dict[str, Any], mapping: dict[str, tuple[str, str, str]]) -> list[dict[str, Any]]:
    """Erzeugt Zellen aus einem Quell-Dict.

    ``mapping`` bildet Ziel-Feld auf (Quell-Schluessel, Arm, Einheit) ab.
    """
    result = []
    for target, (source_key, arm, unit) in mapping.items():
        item = cell(target, arm, values.get(source_key), unit, source_key)
        if item is not None:
            result.append(item)
    return result


def rel(path: Path) -> str:
    """Relativer Pfad ab dem Projektwurzelverzeichnis, mit Forward-Slashes."""
    try:
        return path.resolve().relative_to(BENCH_ROOT.parent).as_posix()
    except ValueError:
        return path.as_posix()


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
