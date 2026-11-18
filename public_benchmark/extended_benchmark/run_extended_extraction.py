#!/usr/bin/env python3
"""Extraktionslauf fuer den erweiterten Benchmark (numerische Aufgabe).

Jedes Modell bekommt den Artikeltext und die Liste der gesuchten Felder und
soll Zellen im Format von ``predictions_schema.json`` zurueckgeben. Es wird
nichts nachbearbeitet: Die Modellantwort wird so bewertet, wie sie kommt.

Ausgabe: ``runs/<run_id>/predictions.jsonl`` mit einer Zeile je (Record,
Modell). Ein abgebrochener Lauf wird mit demselben Befehl fortgesetzt.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parent
sys.path.insert(0, str(REPO))

from research_agent.config import get_config  # noqa: E402

RECORDS = HERE / "records" / "yun.jsonl"

MODELS = {
    "qwen30": {"id": "gwdg/qwen3-30b-a3b-instruct-2507", "max_tokens": 8000},
    "glm": {"id": "gwdg/glm-5.3", "max_tokens": 24000},
    "qwen": {"id": "gwdg/qwen3.5-397b-a17b", "max_tokens": 16000},
    "deepseek": {"id": "gwdg/deepseek-v4.1-flash-1017", "max_tokens": 8000},
}

FIELDS = (
    "intervention_group_size",
    "intervention_events",
    "intervention_mean",
    "intervention_standard_deviation",
    "comparator_group_size",
    "comparator_events",
    "comparator_mean",
    "comparator_standard_deviation",
)

# Standard ist die Referenzversion; v3 hat sich im Dev-Lauf nicht belegt und ist
# nur noch per --absolute-counts waehlbar.
PROMPT_VERSION = "v2_timepoint"
# Seit 15.11.2026 ist v6_target_fallback die Referenz. Der Zielzeitpunkt kommt
# aus dem Record; ohne Annotation faellt der Prompt auf die Standardregel
# zurueck, der Lauf behaelt aber sein Versionslabel.
DEFAULT_TARGET_FALLBACK = True
VERSION_ABSOLUTE_COUNTS = "v3_abs_count"
VERSION_LAST_TIMEPOINT = "v4_last_timepoint"
VERSION_TARGET_TIMEPOINT = "v5_target_timepoint"
VERSION_TARGET_FALLBACK = "v6_target_fallback"
VERSION_CELL_TIMEPOINT = "v7_zellzeitpunkt"
VERSION_QUELLENZEILE = "v8_quellenzeile"
RETRY_MAX_TOKENS = 32000
# Reparaturaufruf nach einem Length-Ausfall: kleines Budget, kurzer Text, wenige
# Zellen. Ein erneuter Loop kostet damit hoechstens REPAIR_MAX_TOKENS.
REPAIR_MAX_TOKENS = 6000
REPAIR_TEXT_LIMIT = 15000
# Die Gruppengroessen-Zeile ist opt-in: in der Fassung ``lang`` verdreifachte sie
# im 12-Record-Pilot die Primaerausfaelle (6 statt 2), in ``kurz`` ist sie eine
# reine Feldvorgabe. Standard ist keine Zeile (``aus``).
GROUP_SIZE_TEXTE = {
    "aus": "",
    "lang": (
        "Group sizes (*_group_size) are arm characteristics, not outcome values: report them without a time "
        "point, and they are exempt from the one-time-point rule. "
    ),
    "kurz": (
        "Report group sizes as intervention_group_size or comparator_group_size without a timepoint. "
    ),
}
# Der Armzeilen-Zusatz (--arm-row-mode) wurde am 16.11.2026 nach dem Prueflauf
# ueber 289-295 wieder entfernt: 0 von 10 Komparatorzellen richtig. Ursache war
# die Vorgabe, nicht der Prompt: die Records trugen `comparator: "baseline"`,
# waehrend das Gold die TAU-Gruppe fuehrt. In Version 3 der Testbasis heisst das
# Feld "treatment as usual (TAU)". Befunde:
# error_analysis/armzeile_pruefung_291_295.md, error_analysis/comparator_pruefung.md.
# Wird mit --cache-buster gesetzt; das Gateway liefert sonst die gecachte
# Antwort einer identischen Anfrage zurueck.
SESSION_TAG = ""

SYSTEM = (
    "You extract numerical results from randomised controlled trial publications. "
    "You answer with a single JSON object and nothing else. You never invent values: "
    "if a value is not reported, you omit the cell."
)

LOCK = threading.Lock()


def bestimme_version(
    *,
    absolute_counts: bool = False,
    last_timepoint: bool = False,
    target_timepoint: bool = False,
    target: str = "",
    fallback: bool = False,
    cell_timepoint: bool = False,
    cache_buster: bool = False,
) -> str:
    """Versionslabel fuer eine Antwort.

    Eine Fassung, die den Record-Zeitpunkt voraussetzt, wird nur dann so
    etikettiert, wenn der Record wirklich einen Zeitpunkt traegt. Ohne
    Annotation laeuft der Prompt-Text der vorherigen Referenz und heisst auch
    so, damit Laeufe nicht unter falscher Version in die Auswertung gehen.
    """
    if cell_timepoint and target:
        version = VERSION_CELL_TIMEPOINT
    elif absolute_counts:
        version = VERSION_ABSOLUTE_COUNTS
    elif last_timepoint:
        version = VERSION_LAST_TIMEPOINT
    elif target_timepoint and target:
        version = VERSION_TARGET_TIMEPOINT
    elif fallback and target:
        version = VERSION_TARGET_FALLBACK
    else:
        version = PROMPT_VERSION
    return f"{version}_cb" if cache_buster else version


def _felder() -> str:
    """Feldliste, wie sie in beiden Prompts steht."""
    return ", ".join(f'"{name}"' for name in FIELDS)


def _kopf(record: dict[str, Any], text: str, limit: int) -> str:
    """Gemeinsamer Prompt-Kopf: Textauszug, Kontext, JSON-zuerst-Regel."""
    context = record["context"]
    return (
        f"Publication excerpt:\n{text[:limit]}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n\n"
        "Return the JSON object first. Write no analysis before it.\n"
    )


def _prompt_v7(
    record: dict[str, Any],
    text: str,
    limit: int,
    target: str,
    group_size_mode: str = "aus",
) -> str:
    """v7: ein Zeitpunkt je Antwort, Header mit Einheit, JSON zuerst.

    Der Zeitpunkt ist Eigenschaft der Antwort, nicht des Feldes. Damit ist eine
    Mischung der Arme strukturell ausgeschlossen, nicht nur per Prompt verboten.
    """
    return (
        _kopf(record, text, limit)
        + "One time point for BOTH arms.\n"
        f'Target time point (binding): "{target}".\n'
        "1. If both arms are reported at the target time point, use it and set \"fallback\": false.\n"
        "2. Otherwise use the closest time point (same unit, smallest absolute difference, ties: the "
        "later one) at which BOTH arms are reported, and set \"fallback\": true.\n"
        "3. If there is no such time point, return an empty cell list and the target time point.\n"
        'Return exactly one JSON object: {"timepoint": "<label exactly as printed, e.g. 24>", '
        '"timepoint_header": "<shortest string copied character for character from the article that '
        'shows this time point together with its unit, e.g. Week 24; empty if there is none>", '
        '"fallback": true | false, "cells": [{"field": "<field>", "arm": "intervention" | '
        '"comparator", "value": <number>}, ...]}\n'
        f"Allowed fields: {_felder()}. "
        "Use the arm that the number belongs to: intervention for the experimental arm, comparator for the control arm. "
        + GROUP_SIZE_TEXTE.get(group_size_mode, "")
        + "Never report an outcome value without naming the time point of the answer, never mix two time points. "
        "Never invent a time point_header: copy it from the article or leave it empty. "
        "Copy numbers exactly as reported; do not convert, do not compute, do not guess. "
        "Omit a cell the paper does not report. "
        "Do not add commentary, markdown or code fences."
    )


def _prompt_v8(
    record: dict[str, Any],
    text: str,
    limit: int,
    target: str,
    group_size_mode: str = "aus",
) -> str:
    """v8 = v7 plus erzwungene Quellenangabe vor den Zellen.

    Anlass: In der Fehleranalyse vom 16.11.2026 waren 13 von 29 falschen Zellen
    Arm- oder Populationsfehler und 4 weitere falsche Tabellenzeilen. Das Modell
    liest die Zahl richtig und an der falschen Stelle. Deshalb muss es die
    gelesene Zeile und die Spaltenkoepfe beider Arme zuerst nennen; die Zellen
    muessen aus genau dieser Zeile stammen. v7 selbst bleibt unveraendert.

    Vorgeschichte: Ein reiner Armzeilen-Zusatz (--arm-row-mode) scheiterte am
    16.11. an falschen Comparator-Vorgaben in den Records, nicht am Prompt
    (error_analysis/armzeile_pruefung_291_295.md). Hier wird deshalb nichts
    vorgegeben, sondern nur benannt, was das Modell gelesen hat.
    """
    return (
        _prompt_v7(record, text, limit, target, group_size_mode)
        + "\nSource discipline (binding): name your source before the cells. "
        'Add "source": {"row_label": "<verbatim text of the table row or sentence you read>", '
        '"intervention_label": "<verbatim column header or group label of the intervention arm>", '
        '"comparator_label": "<verbatim column header or group label of the comparator arm>"} '
        "as the first key of the JSON object. "
        "Every cell must come from that single row and that single time point. "
        "If the outcome is reported in several rows (subgroups, several populations, several models), "
        "choose the row whose population matches the arms named in the request, quote only that row, "
        "and never merge values from two rows. "
        "If the labels are not printed in the excerpt, use an empty string rather than a guess."
    )


def _prompt_repair(
    record: dict[str, Any],
    text: str,
    target: str,
    limit: int = REPAIR_TEXT_LIMIT,
) -> str:
    """Kurzer Reparaturauftrag: kleinste moegliche Antwort, wenige Zellen.

    Ziel ist nicht die beste Extraktion, sondern eine Ausgabe ueberhaupt: Der
    Standardprompt ist bei diesen Records 6-mal mit leerem Inhalt am Limit
    gescheitert (siehe error_analysis/length_analysis.md).
    """
    return (
        _kopf(record, text, limit)
        + f'Target time point: "{target}".\n'
        "Give the smallest possible answer: at most six cells, at most one cell per field and arm. "
        'Return exactly one JSON object: {"timepoint": "<label as printed>", "cells": '
        '[{"field": "<field>", "arm": "intervention" | "comparator", "value": <number>}, ...]}\n'
        f"Allowed fields: {_felder()}. "
        "Group sizes (*_group_size) are arm characteristics and need no timepoint. "
        "Copy numbers exactly as reported; do not convert, do not compute. "
        "If a value is not reported, leave it out. "
        "Do not add commentary, markdown or code fences."
    )


def parse_v7_meta(content: str) -> dict[str, Any]:
    """Liest timepoint, timepoint_header und fallback der v7-Antwort."""
    payload, error = _load_payload(content)
    if payload is None:
        return {"timepoint": "", "header": "", "fallback": None, "error": error}
    timepoint = str(payload.get("timepoint") or "").strip()
    fallback = payload.get("fallback")
    return {
        "timepoint": timepoint,
        "header": str(payload.get("timepoint_header") or "").strip(),
        "fallback": fallback if isinstance(fallback, bool) else None,
        "error": "" if timepoint else "kein_zeitpunkt",
    }


def build_prompt(
    record: dict[str, Any],
    text: str,
    limit: int = 45000,
    absolute_counts: bool = False,
    last_timepoint: bool = False,
    target_timepoint: str | None = None,
    fallback: bool = False,
    cell_timepoint: bool = False,
    group_size_mode: str = "aus",
    quellenzeile: bool = False,
) -> str:
    if cell_timepoint and target_timepoint:
        if quellenzeile:
            return _prompt_v8(record, text, limit, target_timepoint, group_size_mode)
        return _prompt_v7(record, text, limit, target_timepoint, group_size_mode)
    context = record["context"]
    fields = ", ".join(f'"{name}"' for name in FIELDS)
    berichtet = bool(last_timepoint or target_timepoint)
    zelle = (
        '{"field": "<field>", "arm": "intervention" | "comparator", "value": <number>, '
        '"timepoint": "<label exactly as printed>"}'
        if fallback
        else '{"field": "<field>", "arm": "intervention" | "comparator", "value": <number>}'
    )
    schema = (
        f'{{"cells": [{zelle}, ...], '
        '"chosen_timepoint": "<label exactly as printed>", '
        '"discarded_timepoints": ["<label exactly as printed>", ...]}'
        if berichtet
        else f'{{"cells": [{zelle}, ...]}}'
    )
    if target_timepoint and fallback:
        timepoint_rule = (
            f'Target time point (binding): "{target_timepoint}". Extract each result at exactly this '
            "time point when the outcome is reported there. If a field is not reported at the target "
            "time point, use the closest reported time point instead (prefer the nearest later one, "
            "otherwise the nearest earlier one; baseline only if nothing else is reported) and name the "
            "time point you used for that cell in its \"timepoint\" field, copied exactly as printed. "
            "Never mix two time points inside one cell. Then state the target time point label as "
            "chosen_timepoint and list the other time point labels of this outcome as "
            "discarded_timepoints. "
        )
    elif target_timepoint:
        timepoint_rule = (
            f'Target time point (binding): "{target_timepoint}". Extract only the results measured at '
            "exactly this time point, as printed for this outcome. If the outcome is not reported at "
            "this time point, omit the cell instead of substituting another time point. Never use "
            "baseline values unless the target is a baseline value. Then state the time point label you "
            "used and the other time point labels of this outcome that you skipped, both copied exactly "
            'as printed (use "not applicable" if only one time point is reported, "running text" if '
            "the outcome is only reported in prose). "
        )
    elif last_timepoint:
        timepoint_rule = (
        "Use the results measured at the last time point reported for this outcome: the latest "
        "follow-up. If the table reports a cumulative total row or column, use the total. Never use "
        "baseline values. Then state which time point label you used and which other time point "
            "labels you skipped for this outcome, both copied exactly as printed (use \"not applicable\" "
            "if only one time point is reported, \"running text\" if the outcome is only reported in "
            "prose). "
        )
    else:
        timepoint_rule = (
            "Use the values measured at the end of the intervention (post-test), not baseline values "
            "and not follow-up values from a later measurement point. "
        )
    return (
        f"Publication excerpt:\n{text[:limit]}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n\n"
        "Extract the numerical results that belong to this comparison and outcome. "
        "Return exactly one JSON object:\n"
                    f"{schema}\n"
            f"Allowed fields: {_felder()}. "
        "Use the arm that the number belongs to: intervention for the experimental arm, comparator for the control arm. "
        + timepoint_rule
        + (
            "Report event counts as absolute numbers of events, never as percentages or rates. "
            if absolute_counts
            else ""
        )
        +
        "Copy numbers exactly as reported; do not convert, do not compute, do not guess. "
        "Omit a cell the paper does not report. "
        "Do not add commentary, markdown or code fences."
    )


def _load_payload(content: str) -> tuple[dict[str, Any] | None, str]:
    """Liest das JSON-Objekt aus der Antwort, auch mit Codefence oder Beiwerk."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None, "kein_json"
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            return None, f"json_fehler: {error}"
    if not isinstance(payload, dict):
        return None, "kein_objet"
    return payload, ""


def parse_timepoints(content: str) -> tuple[dict[str, Any], str]:
    """Liest chosen_timepoint und discarded_timepoints aus der Antwort."""
    payload, error = _load_payload(content)
    if payload is None:
        return {"chosen": "", "discarded": []}, error
    chosen = str(payload.get("chosen_timepoint") or "").strip()
    raw = payload.get("discarded_timepoints")
    discarded: list[str] = []
    if isinstance(raw, list):
        discarded = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str) and raw.strip():
        discarded = [part.strip() for part in raw.split(";") if part.strip()]
    if not chosen:
        return {"chosen": "", "discarded": discarded}, "kein_zeitpunkt"
    return {"chosen": chosen, "discarded": discarded}, ""


def json_kaputt(parse_error: str) -> bool:
    """Wahr, wenn die Antwort strukturell kein lesbares JSON war.

    Eine leere Zellenliste ist kein Fehler (Felder duerfen ausgelassen werden),
    unlesbares JSON dagegen ist ein Ausfall und wird einmal wiederholt.
    """
    return parse_error in ("kein_json", "kein_objet") or parse_error.startswith("json_fehler")




def fehlerklasse_aus(response: dict[str, Any], parse_error: str) -> str:
    """Klassifiziert einen Ausfall; leer heisst: verwertbare Antwort.

    `finish_reason = length` ist eine Reasoning-Schleife: der zweite Versuch mit
    groesserem Budget lieferte in drei von drei Faellen wieder `length` und
    kostete je 56.000 Tokens ohne eine Zelle. Deshalb kein Retry, sondern eine
    eindeutige Fehlzeile. Kaputtes JSON bleibt ein Retry-Fall: dort ist die
    Ursache Format, nicht Endlosschleife.
    """
    if (response.get("finish_reason") or "") == "length":
        return "length_ohne_ergebnis"
    if json_kaputt(parse_error):
        return "json_kaputt"
    return ""


def content_felder(inhalt: str, primaer_content: str) -> dict[str, str]:
    """Rohantwort fuer die Fehleranalyse: der Text, aus dem die Zellen stammen.

    `content` ist bewusst der wirksame Text (`inhalt`), nicht der Primaeraufruf:
    Nach einem Reparaturaufruf stammen die Zellen aus einer anderen Antwort, und
    nur dieser Text erklaert sie. Weicht er ab, bleibt der Primaeraufruf als
    `content_primaer` erhalten, damit sich Formatfehler und Reparatur trennen.
    """
    felder = {"content": inhalt}
    if inhalt != primaer_content:
        felder["content_primaer"] = primaer_content
    return felder


def parse_cells(content: str) -> tuple[list[dict[str, Any]], str]:
    """Liest die Zellen aus der Modellantwort; gibt (cells, fehler) zurueck."""
    payload, error = _load_payload(content)
    if payload is None:
        return [], error
    cells = payload.get("cells") if isinstance(payload, dict) else None
    if not isinstance(cells, list):
        return [], "keine_zellen"
    cleaned = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        field = str(cell.get("field") or "").strip()
        arm = str(cell.get("arm") or "").strip() or None
        value = cell.get("value")
        timepoint = str(cell.get("timepoint") or "").strip()
        if field not in FIELDS or arm not in ("intervention", "comparator"):
            continue
        try:
            number = float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            continue
        cleaned.append({"field": field, "arm": arm, "value": number, "timepoint": timepoint})
    return cleaned, "" if cleaned else "keine_verwertbaren_zellen"


def call(model: dict[str, Any], prompt: str, key: str, base: str, attempts: int = 4) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        last = _call_once(model, prompt, key, base)
        status = last.get("http_status")
        if status == 200 and last.get("content"):
            return last
        if status in (429, 500, 502, 503, 504) and attempt < attempts:
            wait = 20 * attempt + random.uniform(0, 5)
            print(f"  {model['id']} {status}, warte {wait:.1f}s (Versuch {attempt})", flush=True)
            time.sleep(wait)
            continue
        return last
    return last or {"http_status": 0, "error": "kein Versuch", "content": ""}


def _call_once(model: dict[str, Any], prompt: str, key: str, base: str) -> dict[str, Any]:
    payload = {
        "model": model["id"],
        "messages": [
            {"role": "system", "content": SYSTEM + (f"\nSession tag: {SESSION_TAG}" if SESSION_TAG else "")},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": model["max_tokens"],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        return {
            "http_status": exc.code,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": f"HTTPError {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}",
            "content": "",
            "finish_reason": "",
            "completion_tokens": None,
        }
    except Exception as exc:  # noqa: BLE001 - Lauf soll weiterlaufen
        return {
            "http_status": 0,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": f"{type(exc).__name__}: {exc}",
            "content": "",
            "finish_reason": "",
            "completion_tokens": None,
        }
    try:
        data = json.loads(body)
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or ""
        return {
            "http_status": status,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": "",
            "content": content,
            "finish_reason": choice.get("finish_reason", ""),
            "completion_tokens": (data.get("usage") or {}).get("completion_tokens"),
            "reasoning_chars": len((choice.get("message") or {}).get("reasoning_content") or ""),
        }
    except json.JSONDecodeError:
        return {
            "http_status": status,
            "elapsed_s": round(time.monotonic() - started, 2),
            "error": "antwort_kein_json",
            "content": "",
            "finish_reason": "",
            "completion_tokens": None,
        }


def load_records(split: str | None, limit: int | None, path: Path | None = None) -> list[dict[str, Any]]:
    # path erlaubt eine andere Record-Datei (z. B. den eingefrorenen Teilsatz mit
    # Zeitpunktannotation); Standard bleibt records/yun.jsonl.
    quelle = path or RECORDS
    records = [json.loads(line) for line in quelle.read_text(encoding="utf-8").splitlines() if line.strip()]
    if split:
        records = [record for record in records if record["document"].get("split") == split]
    if limit:
        records = records[:limit]
    return records


def waehle_records(records: list[dict[str, Any]], ids: str | None) -> list[dict[str, Any]]:
    """Beschraenkt die Auswahl auf die per --ids genannten record_ids."""
    if not ids:
        return records
    wanted = {value.strip() for value in ids.split(",") if value.strip()}
    return [record for record in records if record["record_id"] in wanted]


def done_keys(path: Path, *, retry_failed: bool = False) -> set[tuple[str, str]]:
    """Schon erledigte (record_id, model)-Paare.

    Jede vorhandene Zeile gilt als erledigt — auch eine Fehlzeile, damit ein
    Fortsetzen nicht automatisch dieselbe Endlosschleife erneut bezahlt. Mit
    `retry_failed=True` (Flag `--retry-failed`) werden Fehlzeilen ausgenommen und
    damit gezielt wiederholt.
    """
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not row.get("record_id") or not row.get("model"):
            continue
        fehlgeschlagen = bool(row.get("fehlerklasse")) or not row.get("rows")
        if fehlgeschlagen and retry_failed:
            continue
        keys.add((row["record_id"], row["model"]))
    return keys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen30", "glm"], choices=sorted(MODELS))
    parser.add_argument("--split", default="dev")
    parser.add_argument(
        "--records",
        type=Path,
        default=None,
        help="Record-Datei (JSONL); Pflicht, wenn kein --ids gesetzt ist. Fuer Teilsaetze die "
        "eingefrorene Datei mit Zeitpunktannotation uebergeben. Ohne --records gilt records/yun.jsonl.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--ids", default=None, help="Komma-getrennte record_ids, nur diese laufen")
    parser.add_argument(
        "--save-content",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rohantwort je Record mitspeichern (Standard; mit --no-save-content aus). "
        "Ohne sie laesst sich ein Parserfehler nicht von einer Modellauslassung trennen.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Fehlzeilen (z. B. length) gezielt wiederholen statt zu ueberspringen",
    )
    parser.add_argument("--max-tokens", type=int, default=None, help="Tokenbudget fuer alle Modelle ueberschreiben")
    parser.add_argument("--cache-buster", action="store_true", help="eindeutigen Session-Tag in den Systemprompt haengen")
    parser.add_argument("--absolute-counts", action="store_true", help="Prompt-Zusatz aus v3_abs_count aktivieren")
    parser.add_argument(
        "--target-timepoint",
        action="store_true",
        help="Zielzeitpunkt aus dem Record als verbindliche Vorgabe setzen (v5_target_timepoint)",
    )
    parser.add_argument(
        "--target-fallback",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_TARGET_FALLBACK,
        help="Zielzeitpunkt mit Rueckfall auf den naechsten berichteten Zeitpunkt (v6_target_fallback, Standard)",
    )
    parser.add_argument(
        "--group-size-mode",
        choices=("aus", "lang", "kurz"),
        default="aus",
        help="Zeile zu *_group_size im v7-Prompt: aus (Standard), lang (zwei Regelsaetze) oder kurz (Feldvorgabe)",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help=f"nach einem Length-Ausfall einmal mit {REPAIR_MAX_TOKENS} Tokens und kurzem Prompt nachfassen",
    )
    parser.add_argument(
        "--cell-timepoint",
        action="store_true",
        help="v7: ein Zeitpunkt je Antwort plus timepoint_header und fallback (v7_zellzeitpunkt)",
    )
    parser.add_argument(
        "--quellenzeile",
        action="store_true",
        help="v8: v7 plus erzwungene Quellenangabe (row_label, Spaltenkoepfe) vor den Zellen",
    )
    parser.add_argument(
        "--last-timepoint",
        action="store_true",
        help="letzten berichteten Messzeitpunkt verlangen und Zeitpunkte mitliefern (v4_last_timepoint)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="nur die Auswahl zeigen (Records, Auftraege, ids) und beenden; keine Anfrage, kein Schreiben",
    )
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("extended_%Y%m%d"))
    parser.add_argument(
        "--quelle",
        default="",
        help="Herkunft der Zeilen (z. B. v7_folgelauf), damit Folgelaeufe im Datensatz erkennbar bleiben",
    )
    args = parser.parse_args()
    if args.records is None and not args.ids:
        # Die Standarddatei hat 186 Records: ein Lauf "einfach so" kostet schnell
        # ein dreistelliges Tausenderbudget. Ohne ausdrueckliche Auswahl kein Start.
        print(
            "FEHLER: ohne --records oder --ids startet kein Lauf. Bitte die Record-Datei "
            "und/oder die ids ausdruecklich angeben.",
            flush=True,
        )
        return 2
    records_datei = args.records or RECORDS

    models = {name: dict(spec) for name, spec in MODELS.items()}
    if args.max_tokens:
        for spec in models.values():
            spec["max_tokens"] = args.max_tokens

    global SESSION_TAG
    prompt_version = (
        VERSION_CELL_TIMEPOINT
        if args.cell_timepoint
        else VERSION_ABSOLUTE_COUNTS
        if args.absolute_counts
        else PROMPT_VERSION
    )
    if args.cache_buster:
        SESSION_TAG = uuid.uuid4().hex[:12]

    records = waehle_records(load_records(args.split, args.limit, path=records_datei), args.ids)
    run_dir = HERE / "runs" / args.run_id
    out_path = run_dir / "predictions.jsonl"
    done = done_keys(out_path, retry_failed=args.retry_failed)

    jobs = [(record, model) for model in args.models for record in records if (record["record_id"], model) not in done]
    print(f"{len(records)} Records, {len(jobs)} offene Auftraege, {args.workers} Threads", flush=True)

    if args.dry_run:
        # Pruefpfad: zeigt genau die Auswahl, die ein echter Lauf anfassen
        # wuerde, ohne eine Anfrage zu senden oder eine Zeile zu schreiben.
        print("DRY-RUN: keine Anfrage, kein Schreiben", flush=True)
        for model in args.models:
            ids = [record["record_id"] for record, name in jobs if name == model]
            print(f"{model}: {len(ids)} Auftraege", flush=True)
            print(",".join(ids), flush=True)
        return 0

    # Erst nach dem Trockenlauf: Schluessel und Verzeichnis sind fuer die
    # Auswahl nicht noetig, und ein Trockenlauf soll nichts anlegen.
    config = get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2
    run_dir.mkdir(parents=True, exist_ok=True)

    def work(record: dict[str, Any], model: str) -> dict[str, Any]:
        path = record["document"].get("path") or ""
        text = ""
        if path:
            candidate = REPO / path
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8", errors="replace")
        target = ""
        if args.target_timepoint or args.target_fallback:
            target = str(((record.get("timepoint") or {}).get("target")) or "").strip()
            if "not stated" in target.lower():
                target = ""
        prompt = build_prompt(
            record,
            text,
            absolute_counts=args.absolute_counts,
            last_timepoint=args.last_timepoint,
            target_timepoint=target or None,
            fallback=args.target_fallback,
            cell_timepoint=args.cell_timepoint,
            group_size_mode=args.group_size_mode,
            quellenzeile=args.quellenzeile,
        )
        prompt_version = bestimme_version(
            absolute_counts=args.absolute_counts,
            last_timepoint=args.last_timepoint,
            target_timepoint=args.target_timepoint,
            target=target,
            fallback=args.target_fallback,
            cell_timepoint=args.cell_timepoint,
            cache_buster=args.cache_buster,
        )
        if args.quellenzeile:
            prompt_version = VERSION_QUELLENZEILE
        response = call(models[model], prompt, key, base)
        cells, parse_error = parse_cells(response.get("content") or "")
        timepoints, timepoint_error = parse_timepoints(response.get("content") or "")
        retry: dict[str, Any] | None = None
        retry_grund = ""
        fehlerklasse = fehlerklasse_aus(response, parse_error)
        # Nur strukturell kaputtes JSON bekommt einen zweiten Versuch (gleiches
        # Limit): die Ursache ist Format. Reasoning-Schleifen ("length") werden
        # nicht wiederholt, sie kosten nur Tokens ohne Ergebnis.
        if fehlerklasse == "json_kaputt":
            retry_grund = "json"
            retry = call(models[model], prompt, key, base)
            if retry.get("content"):
                response = retry
                cells, parse_error = parse_cells(response.get("content") or "")
                timepoints, timepoint_error = parse_timepoints(response.get("content") or "")
                fehlerklasse = fehlerklasse_aus(response, parse_error)
        # Gedeckelter Reparaturaufruf: nur nach einem Length-Ausfall, mit
        # kleinem Budget und kurzem Text. Ersetzt die Zellen nur bei Erfolg.
        repair: dict[str, Any] | None = None
        pfad = "standard"
        repair_fehlerklasse = ""
        # `content_len`/`content_chars` beschreiben immer die Antwort des
        # Primaeraufrufs (Vergleichbarkeit mit den alten Zeilen); der Inhalt, aus
        # dem der v7-Header gelesen wird, kann nach einer Reparatur ein anderer sein.
        primaer_content = response.get("content") or ""
        inhalt = primaer_content
        if args.repair and fehlerklasse == "length_ohne_ergebnis":
            budget = dict(models[model])
            budget["max_tokens"] = min(REPAIR_MAX_TOKENS, int(budget.get("max_tokens") or REPAIR_MAX_TOKENS))
            repair = call(budget, _prompt_repair(record, text, target), key, base)
            pfad = "repair"
            inhalt_repair = repair.get("content") or ""
            r_cells, r_parse = parse_cells(inhalt_repair)
            repair_fehlerklasse = fehlerklasse_aus(repair, r_parse)
            if r_cells:
                cells, parse_error, inhalt = r_cells, r_parse, inhalt_repair
                fehlerklasse = ""
        # v7 stellt den Zeitpunkt je Antwort; er wird hier auf die Zellen
        # verteilt, damit die Auswertung beide Schemata gleich liest.
        v7 = {"timepoint": "", "header": "", "fallback": None, "error": ""}
        if args.cell_timepoint:
            v7 = parse_v7_meta(inhalt)
            if v7["timepoint"]:
                for cell in cells:
                    cell["timepoint"] = v7["timepoint"]
                timepoints = {"chosen": v7["timepoint"], "discarded": []}
                timepoint_error = v7["error"]
        row = {
            "record_id": record["record_id"],
            "model": model,
            "model_id": models[model]["id"],
            "http_status": response.get("http_status"),
            "error": response.get("error", ""),
            "finish_reason": response.get("finish_reason", ""),
            "completion_tokens": response.get("completion_tokens"),
            "reasoning_chars": response.get("reasoning_chars", 0),
            "suspected_cache": (response.get("elapsed_s") or 0) < 1.0,
            "retried": retry is not None,
            "retry_grund": retry_grund,
            "fehlerklasse": fehlerklasse,
            "failed": bool(fehlerklasse),
            "retry_finish_reason": retry.get("finish_reason", "") if retry else "",
            "retry_tokens": retry.get("completion_tokens") if retry else None,
            "elapsed_s": response.get("elapsed_s"),
            "content_len": len(primaer_content),
            "parse_error": parse_error,
            "timepoints": timepoints
            if (args.last_timepoint or args.target_timepoint or args.target_fallback)
            else {},
            "timepoint_error": timepoint_error
            if (args.last_timepoint or args.target_timepoint or args.target_fallback)
            else "",
            "target_timepoint": target,
            "quelle": args.quelle,
            "schema_version": VERSION_CELL_TIMEPOINT if args.cell_timepoint else "v6_percell_timepoint",
            "timepoint_header": v7["header"],
            "fallback": v7["fallback"],
            "content_chars": len(primaer_content),
            "pfad": pfad,
            "group_size_mode": args.group_size_mode,
            "repair_tokens": repair.get("completion_tokens") if repair else None,
            "repair_finish_reason": repair.get("finish_reason", "") if repair else "",
            "repair_fehlerklasse": repair_fehlerklasse,
            "gateway_params": {"max_tokens": models[model]["max_tokens"], "temperature": 0.0},
            "prompt_version": prompt_version,
            "predicted": {"cells": cells},
            "rows": cells,
        }
        if args.save_content:
            row.update(content_felder(inhalt, primaer_content))
        with LOCK:
            with out_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        if fehlerklasse:
            status = f"FEHLER {fehlerklasse}"
            print(
                f"{model}: {record['record_id']} {status} "
                f"({response.get('completion_tokens') or 0} Tokens, kein Retry)",
                flush=True,
            )
        else:
            status = "ok" if cells else f"leer {parse_error}"
            print(f"{model}: {record['record_id']} {status} ({len(cells)} Zellen)", flush=True)
        return row

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, record, model): (record, model) for record, model in jobs}
        for future in as_completed(futures):
            try:
                future.result()
                completed += 1
            except Exception as error:  # noqa: BLE001
                print(f"FEHLER {futures[future]}: {error}", flush=True)

    print(f"fertig: {completed} Auftraege, Ausgabe {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
