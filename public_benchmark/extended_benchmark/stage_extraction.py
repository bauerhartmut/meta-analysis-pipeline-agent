#!/usr/bin/env python3
"""Mehrstufige Extraktion fuer Ereigniszellen (Prototyp, Ansatz C).

Aufbau in zwei Stufen, damit die Zeilen-/Spaltenwahl pruefbar wird:

1. Stufe 1 nennt nur das Zeilenlabel und den Spaltenkopf, hinter denen die
   Ereigniszahl des jeweiligen Arms steht - noch keine Zahl.
2. Stufe 2 liest die Zahl an genau dieser Stelle aus.

Beide Stufen werden getrennt gespeichert und getrennt bewertet. Dieses Modul
enthaelt nur die reinen Prompt- und Parserfunktionen; der Netzlauf steht in
``run_stage_extraction.py``.
"""

from __future__ import annotations

import json
import re
from typing import Any

EVENT_FIELDS = ("intervention_events", "comparator_events")
ARMS = ("intervention", "comparator")

STAGE1_SYSTEM = (
    "You locate numerical results in randomised controlled trial publications. "
    "You answer with a single JSON object and nothing else. You never invent labels: "
    "every label you name must appear in the text."
)

STAGE2_SYSTEM = (
    "You read a single number from a randomised controlled trial publication at a "
    "location named by a previous step. You answer with a single JSON object and "
    "nothing else. You never compute, convert or estimate values."
)


def _context_block(context: dict[str, Any]) -> str:
    return (
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        f"Outcome type: {context.get('outcome_type') or 'unknown'}\n"
    )


def build_stage1_prompt(
    text: str,
    context: dict[str, Any],
    limit: int = 45000,
) -> str:
    """Stufe 1: Zeilenlabel und Spaltenkopf benennen, keine Zahl."""
    return (
        f"Publication excerpt:\n{text[:limit]}\n\n"
        + _context_block(context)
        + "\nThe outcome is reported as event counts: the number of participants who "
        "experienced the event, per arm.\n\n"
        "Before any number is read, locate where those counts are reported. Name, for "
        "each arm, the exact row label (the outcome line as printed), the exact column "
        "header (the measurement time point or arm label as printed) and the caption of "
        "the table or the paragraph. Use the measurement at the end of the intervention, "
        "not baseline values and not a later follow-up. If the count is only in running "
        "text, use \"running text\" as the column header and a short quoted phrase as the "
        "row label.\n\n"
        "Return exactly one JSON object:\n"
        '{"locators": [{"arm": "intervention", "row_label": "<as printed>", '
        '"column_header": "<as printed>", "caption": "<table or paragraph caption>", '
        '"found": true}, ...]}\n'
        "Return one entry per arm you can locate; set \"found\": false and omit the labels "
        "for an arm you cannot locate. Do not return any numbers. Do not add commentary, "
        "markdown or code fences."
    )


def parse_stage1(content: str) -> tuple[list[dict[str, Any]], str]:
    """Liest die Locators aus der Antwort der ersten Stufe."""
    payload = _load_json_object(content)
    if payload is None:
        return [], "kein_json"
    locators = payload.get("locators")
    if not isinstance(locators, list):
        return [], "keine_locators"
    cleaned: list[dict[str, Any]] = []
    for entry in locators:
        if not isinstance(entry, dict):
            continue
        arm = str(entry.get("arm") or "").strip().lower()
        if arm not in ARMS:
            continue
        if entry.get("found") is False:
            cleaned.append({"arm": arm, "found": False, "row_label": "", "column_header": "", "caption": ""})
            continue
        row_label = str(entry.get("row_label") or "").strip()
        column_header = str(entry.get("column_header") or "").strip()
        caption = str(entry.get("caption") or "").strip()
        if not row_label or not column_header:
            cleaned.append({"arm": arm, "found": False, "row_label": row_label, "column_header": column_header, "caption": caption})
            continue
        cleaned.append(
            {
                "arm": arm,
                "found": True,
                "row_label": row_label,
                "column_header": column_header,
                "caption": caption,
            }
        )
    if not cleaned:
        return [], "keine_verwertbaren_locators"
    return cleaned, ""


def build_stage2_prompt(
    text: str,
    context: dict[str, Any],
    arm: str,
    row_label: str,
    column_header: str,
    caption: str = "",
    limit: int = 45000,
) -> str:
    """Stufe 2: die Zahl an der benannten Stelle auslesen."""
    location = (
        f"A previous step located the event count of the {arm} arm in row "
        f"\"{row_label}\" and column \"{column_header}\""
    )
    if caption:
        location += f" (table or paragraph: \"{caption}\")"
    return (
        f"Publication excerpt:\n{text[:limit]}\n\n"
        + _context_block(context)
        + f"\n{location}.\n\n"
        "Read the event count at exactly that row and column: the absolute number of "
        "participants with the event, as printed. If the cell contains a fraction such "
        "as \"31/48\", return the numerator (31). If the row or column cannot be found, "
        "return null. Never compute or estimate the number from percentages or group "
        "sizes.\n\n"
        "Return exactly one JSON object:\n"
        '{"value": <number or null>, "quote": "<the cell exactly as printed>", '
        '"found": true}\n'
        "Set \"found\": false and \"value\": null if the location does not exist. Do not "
        "add commentary, markdown or code fences."
    )


def parse_stage2(content: str) -> tuple[float | None, str, bool, str]:
    """Liest (value, quote, found, fehler) aus der Antwort der zweiten Stufe."""
    payload = _load_json_object(content)
    if payload is None:
        return None, "", False, "kein_json"
    quote = str(payload.get("quote") or "").strip()
    found = payload.get("found") is not False
    raw = payload.get("value")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, quote, False, "" if found is False else "kein_wert"
    text = str(raw).replace(",", ".").strip()
    if "/" in text:
        # "31/48" ist Ereignis/Gruppe; die Ereigniszahl ist der Zaehler.
        text = text.split("/", 1)[0].strip()
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None, quote, False, "wert_keine_zahl"
    if value < 0:
        return None, quote, False, "wert_negativ"
    return value, quote, True, ""


def _load_json_object(content: str) -> dict[str, Any] | None:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def normalisiere(text: str) -> str:
    """Vergleichsform fuer den Belegabgleich: Kleinbuchstaben, einfache Leerzeichen."""
    lowered = (text or "").replace("\u00a0", " ").lower()
    return re.sub(r"\s+", " ", lowered).strip()


def beleg_im_text(label: str, text: str) -> bool:
    """Steht das Label woertlich im Artikeltext?

    Damit ist die Zwischenstufe ohne Modell pruefbar: Ein erfundenes Zeilenlabel
    oder ein erfundener Spaltenkopf faellt hier auf.
    """
    needle = normalisiere(label)
    if not needle:
        return False
    return needle in normalisiere(text)


def merge_event_cells(
    baseline_cells: list[dict[str, Any]],
    staged: dict[str, float],
    fields: tuple[str, ...] = EVENT_FIELDS,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Ersetzt die Ereigniszellen der Basisvorhersage durch die Stufenergebnisse.

    ``staged`` ist mit ``field`` geschluesselt (z.B. ``intervention_events``).
    Rueckgabe: (cells, ersetzt, zurueckgefallen). Ohne Stufenwert bleibt der
    Basiswert stehen und das Feld landet in ``zurueckgefallen``.
    """
    merged: list[dict[str, Any]] = []
    replaced: list[str] = []
    fallback: list[str] = []
    baseline_by_field = {cell.get("field"): cell for cell in baseline_cells}
    for cell in baseline_cells:
        field = cell.get("field")
        if field in fields:
            if field in staged:
                merged.append({"field": field, "arm": cell.get("arm"), "value": staged[field]})
                replaced.append(str(field))
                continue
            fallback.append(str(field))
        merged.append(dict(cell))
    for field in fields:
        if field in staged and field not in baseline_by_field:
            arm = field.split("_", 1)[0]
            merged.append({"field": field, "arm": arm, "value": staged[field]})
            replaced.append(field)
    return merged, replaced, fallback
