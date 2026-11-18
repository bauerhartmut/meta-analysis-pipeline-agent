"""Spaltenrollen und Armzuordnung - deterministisch, ohne Modell.

Die Engine soll nicht das Modell raten lassen, welcher Arm zu welcher Spalte
gehoert. Aus der Header-Hierarchie werden Rollen (Mittelwert, SD, n,
Ereignisse, Prozent, p-Wert, ...) und Arme abgeleitet. Was sich nicht
belegen laesst, bleibt ``None`` und wird als ``unassigned``/``ambiguous``
ausgewiesen - nie stillschweigend dem Interventionsarm zugeschlagen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .model import (
    ARM_COMPARATOR,
    ARM_INTERVENTION,
    ROLE_CI,
    ROLE_EVENTS,
    ROLE_LABEL,
    ROLE_MEAN,
    ROLE_N,
    ROLE_PERCENT,
    ROLE_PVALUE,
    ROLE_SD,
    ROLE_SE,
    ROLE_UNKNOWN,
    Column,
    Table,
    field_for,
    header_path_text,
)

_STOPWORDS = {
    "group", "groups", "arm", "arms", "the", "and", "with", "versus", "vs",
    "study", "patients", "participants", "total", "value", "values", "mean",
    "standard", "deviation", "number", "control", "controls", "treated",
    "treatment", "intervention", "comparator", "n", "sd", "se", "ci", "of",
    "in", "for", "a", "an", "at", "to", "on", "by",
}

_ROLE_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (ROLE_MEAN, r"\b(?:mean|mittelwert|average|avg|arithmetic mean|m)\b|[χx̄]"),
    (ROLE_SD, r"\b(?:sd|s\.d\.|standard deviation|std\.? dev\.?|streuung)\b|[σ]"),
    (ROLE_SE, r"\b(?:se|s\.e\.|standard error|std\.? error)\b"),
    (ROLE_CI, r"\b(?:95\s*%?\s*ci|confidence interval|ci)\b"),
    (ROLE_N, r"\b(?:n|no\.|number|patients|participants|group size|sample size)\b"),
    (ROLE_EVENTS, r"\b(?:events?|cases?|deaths?|responders?|responded|"
                  r"infections?|relapses?|incidents?|counts?|n \(%\)|n\(%\))\b"),
    (ROLE_PERCENT, r"\b(?:%|percent|percentage|proportion)\b"),
    (ROLE_PVALUE, r"\b(?:p|p-value|p value)\b"),
)


@dataclass
class ArmBinding:
    arm: Optional[str]
    basis: str
    confidence: float


def role_for_header(header_path: Sequence[str]) -> str:
    """Rolle einer Spalte aus ihrer Header-Hierarchie.

    Von der tiefsten Ebene nach oben: die erste belegte Rolle gewinnt. Eine
    Zelle mit ``n (%)`` ist eine Ereignisangabe mit Prozentbeigabe, kein
    Prozentwert; ``%`` allein ist kein Armfeld.
    """
    texts = [t for t in reversed(list(header_path)) if t]
    for text in texts:
        lowered = text.lower()
        for role, pattern in _ROLE_PATTERNS:
            if re.search(pattern, lowered):
                if role == ROLE_PERCENT and re.search(r"\bn\s*\(\s*%\s*\)", lowered):
                    return ROLE_EVENTS
                return role
    return ROLE_UNKNOWN


def _tokens(text: str) -> set:
    # Klammerinhalte bleiben hier stehen: in Studienkontexten steht die
    # brauchbare Abkuerzung oft nur dort ("... outside of the hospital (CoPAT)").
    cleaned = (text or "").lower()
    cleaned = cleaned.replace("_", " ")
    tokens = set()
    for token in re.findall(r"[a-zäöüß0-9]+", cleaned):
        if len(token) < 3 and not token.isdigit():
            continue
        if token in _STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def _normalise_arm(text: str) -> str:
    """Armbezeichnung auf Kleinbuchstaben/Ziffern reduzieren.

    Klammerzusaetze (``(WGJ)``) sind Abkuerzungen und gehoeren nicht in den
    Namensvergleich; ``Arm B (AB)`` wird damit zu ``armb`` - und ``armb`` steht
    im Header ``Arm B (n = 12)`` wortgleich. Das traegt auch Ein-Buchstaben-Arme
    (``Group A``/``Group B``), bei denen eine reine Tokenzaehlung versagt.
    """
    without_brackets = re.sub(r"\([^)]*\)", " ", (text or "").lower())
    return re.sub(r"[^a-z0-9]", "", without_brackets)


def _score(arm_text: str, header_text: str) -> float:
    """Belegte Uebereinstimmung zwischen Armbezeichnung und Header.

    Zwei Richtungen, weil Tabellen abkuerzen: die Armbezeichnung
    ``colored and flavored water (WA)`` steht im Header nur als ``Water``.
    Vorwaerts (Anteil der Arm-Tokens im Header) verfehlt das, rueckwaerts
    (Anteil der Header-Tokens in der Armbezeichnung) trifft es. Es zaehlt die
    staerkere Richtung; mindestens ein unterscheidendes Token muss passen.
    """
    arm_name = _normalise_arm(arm_text)
    header_name = _normalise_arm(header_text)
    if len(arm_name) >= 4 and arm_name in header_name:
        return 1.0
    arm_tokens = _tokens(arm_text)
    header_tokens = _tokens(header_text)
    if not arm_tokens or not header_tokens:
        return 0.0
    shared = arm_tokens & header_tokens
    if not shared:
        return 0.0
    forward = len(shared) / len(arm_tokens)
    backward = len(shared) / len(header_tokens)
    return max(forward, backward)


def bind_arm(
    header_path: Sequence[str],
    intervention: str = "",
    comparator: str = "",
    min_score: float = 0.5,
    min_margin: float = 0.15,
) -> ArmBinding:
    """Ordnet eine Spalte einem Arm zu - nur bei belegtem Vorsprung.

    Grundlage sind die im Dokument gedruckten Header-Texte und die im Record
    genannten Armbezeichnungen. Ein Gleichstand oder ein knapper Vorsprung
    ergibt ``None`` (ambiguous), nicht eine Vermutung.
    """
    header_text = " ".join(t for t in header_path if t)
    if not header_text:
        return ArmBinding(None, "kein_header", 0.0)
    scores = {
        ARM_INTERVENTION: _score(intervention, header_text) if intervention else 0.0,
        ARM_COMPARATOR: _score(comparator, header_text) if comparator else 0.0,
    }
    best_arm = max(scores, key=lambda arm: scores[arm])
    best = scores[best_arm]
    other_arm = ARM_COMPARATOR if best_arm == ARM_INTERVENTION else ARM_INTERVENTION
    if best < min_score:
        return ArmBinding(None, "kein_treffer", round(best, 3))
    if best - scores[other_arm] < min_margin:
        return ArmBinding(None, "ambiguous", round(best, 3))
    return ArmBinding(best_arm, "header_treffer", round(best, 3))


def header_unit(header_path: Sequence[str]) -> str:
    """Einheit aus der Header-Hierarchie, wenn sie dort gedruckt steht."""
    for text in reversed(list(header_path)):
        match = re.search(r"\(([^()]{1,18})\)", text or "")
        if match:
            token = match.group(1).strip()
            if token and not token.isdigit():
                return token
    return ""


def _column_path(table: Table, column: Column) -> Tuple[str, ...]:
    path: List[str] = []
    for band in sorted(table.header_bands, key=lambda b: b.level):
        if band.col_start <= column.col_id <= band.col_end:
            path.append(band.text)
    return tuple(path)


def _arm_slots(table: Table) -> List[Tuple[str, List[int]]]:
    """Moegliche Armspalten in Leserichtung (Gruppen oder Einzelspalten)."""
    levels = sorted({b.level for b in table.header_bands})
    if levels:
        top = [b for b in table.header_bands if b.level == levels[0]]
        if top and any(b.span > 1 for b in top):
            top = sorted(top, key=lambda b: b.col_start)
            return [(b.text, list(range(b.col_start, b.col_end + 1))) for b in top]
    roles = {ROLE_N, ROLE_MEAN, ROLE_SD, ROLE_EVENTS}
    columns = sorted((c for c in table.columns if c.role in roles), key=lambda c: c.col_id)
    return [(c.header or f"col {c.col_id}", [c.col_id]) for c in columns]


def enrich_table(table: Table, context: Optional[Dict[str, object]] = None,
                 assume_order: bool = False) -> Table:
    """Spaltenpfade, Rollen, Arme und Zielfelder in die Tabelle schreiben.

    Idempotent: derselbe Aufruf auf einer bereits angereicherten Tabelle
    aendert nichts, weil Pfade aus den Header-Baendern neu gebildet werden.
    """
    context = context or {}
    intervention = str(context.get("intervention") or "")
    comparator = str(context.get("comparator") or "")
    for column in table.columns:
        path = _column_path(table, column)
        if not path:
            path = ((column.header or ""),) if column.header else ()
        column.header_path = path
        column.header = path[-1] if path else ""
        column.role = ROLE_LABEL if column.role == ROLE_LABEL else role_for_header(path)
        column.unit = header_unit(path)
        if column.role == ROLE_LABEL:
            column.arm = None
            column.arm_basis = "label"
            column.field = None
            continue
        binding = bind_arm(path, intervention, comparator)
        column.arm = binding.arm
        column.arm_basis = binding.basis
        column.field = field_for(column.role, binding.arm)

    _detect_combined_columns(table)
    if assume_order:
        _assume_arm_order(table)
    table.context = dict(context)
    return table


_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _detect_combined_columns(table: Table) -> None:
    """Spalten, deren Zellen zwei Zahlen tragen (``12.4 (3.1)``).

    In vielen Tabellen steht die Streuung nicht in einer eigenen Spalte,
    sondern in Klammern hinter dem Mittelwert. Die zweite Zahl ist damit
    woertlich belegt, nicht geschaetzt: sie wird beim Rekonstruieren als
    eigener Wert mit derselben Fundstelle gefuehrt. Die Regel greift nur,
    wenn mindestens 60 Prozent der gefuellten Zellen zwei Zahlen zeigen.
    """
    for column in table.columns:
        column.secondary_role = ""
        if column.role != ROLE_MEAN:
            continue
        filled = 0
        double = 0
        for row in table.rows:
            cell = row.cells.get(column.col_id)
            text = (cell.text or "") if cell is not None else ""
            if not text.strip():
                continue
            filled += 1
            if len(_NUMBER_RE.findall(text)) >= 2:
                double += 1
        if filled and double / filled >= 0.6:
            column.secondary_role = ROLE_SD


def _norm_label(text: str) -> str:
    """Vergleichsform eines Gruppenlabels (Klammerzusatz und Satzzeichen weg)."""
    value = re.sub(r"\([^)]*\)", " ", text or "")
    value = re.sub(r"[^0-9A-Za-z]+", " ", value).strip().lower()
    return value


def _group_label(table: Table, column: Column) -> str:
    """Tiefster Gruppenkopf ueber einer Spalte (nur mehrspaltige Baender)."""
    bands = [
        band for band in table.header_bands
        if band.span > 1 and band.col_start <= column.col_id <= band.col_end
    ]
    if not bands:
        return ""
    return max(bands, key=lambda band: band.level).text


def transfer_arms_within_document(tables: Sequence[Table],
                                  context: Optional[Dict[str, object]] = None) -> int:
    """Arm einer Spalte aus einer Schwestertabelle desselben Dokuments belegen.

    Traegt eine Tabelle den Gruppenkopf ``Verum`` belegt und eine andere
    denselben Gruppenkopf unbelegt, gilt der Arm auch dort: gleicher Kontext,
    gleiches Dokument, gleiches Label. Der Beleg wird als ``uebertrag``
    markiert und in der Validierung gezaehlt. Ohne identisches Label wird
    nichts uebertragen; es wird kein Arm aus der Position geraten.
    """
    context = context or {}
    proven: Dict[Tuple[str, str], str] = {}
    for table in tables:
        for column in table.columns:
            if not column.field or not column.arm:
                continue
            label = _norm_label(_group_label(table, column))
            if label:
                proven.setdefault((label, column.role), column.arm)
    if not proven:
        return 0
    transferred = 0
    for table in tables:
        for column in table.columns:
            if column.field is not None:
                continue
            if column.role not in {ROLE_N, ROLE_MEAN, ROLE_SD, ROLE_EVENTS}:
                continue
            label = _norm_label(_group_label(table, column))
            if not label:
                continue
            arm = proven.get((label, column.role))
            if not arm:
                continue
            column.arm = arm
            column.arm_basis = "uebertrag"
            column.field = field_for(column.role, arm)
            transferred += 1
    return transferred


def _assume_arm_order(table: Table) -> None:
    """Reihenfolge-Annahme fuer genau zwei Armspalten, sichtbar markiert.

    Wenn die Kopfzeile zwei Armspalten traegt und der Kontext nur einen davon
    benennt, bleibt die zweite ohne Arm. In RCT-Tabellen steht der
    Interventionsarm konventionell links. Diese Annahme wird **nicht** still
    getroffen: sie setzt ``arm_basis='reihenfolge'``, und die Validierung zaehlt
    jede so gesetzte Zuordnung. Bei mehr oder weniger als zwei Armspalten wird
    nichts angenommen.
    """
    slots = _arm_slots(table)
    if len(slots) != 2:
        return
    bound = {c.arm for c in table.columns if c.arm}
    unbound_arms = [arm for arm in (ARM_INTERVENTION, ARM_COMPARATOR) if arm not in bound]
    free_slots = [
        (text, col_ids) for text, col_ids in slots
        if not any((table.column(col_id) is not None and table.column(col_id).arm)
                   for col_id in col_ids)
    ]
    if not unbound_arms or len(unbound_arms) != len(free_slots):
        return
    for arm, (text, col_ids) in zip(unbound_arms, free_slots):
        for col_id in col_ids:
            column = table.column(col_id)
            if column is None or column.field is not None:
                continue
            column.arm = arm
            column.arm_basis = "reihenfolge"
            column.field = field_for(column.role, arm)


def reachable_fields(table: Table) -> set:
    """Felder, die diese Tabelle hergeben kann.

    Spaltenfeld plus der zweite Wert einer Verbundzelle (``12.4 (3.1)``): der
    Streuungswert steht woertlich in der Zelle und wird beim Rekonstruieren
    als eigener Beleg gefuehrt. Beides zusammen ist die Obergrenze des
    Tabellenpfads - keine Modellleistung.
    """
    fields = set()
    for column in table.columns:
        if column.field:
            fields.add(column.field)
        if column.secondary_role and column.arm:
            secondary = field_for(column.secondary_role, column.arm)
            if secondary:
                fields.add(secondary)
    return fields


def column_summary(column: Column) -> str:
    """Einzeilige Spaltenbeschreibung fuer Prompt und Bericht."""
    path = header_path_text(column.header_path) or "(ohne Kopf)"
    parts = [f"col {column.col_id}: {path}"]
    if column.role != ROLE_UNKNOWN:
        parts.append(f"role={column.role}")
    if column.arm:
        parts.append(f"arm={column.arm}")
    elif column.role != ROLE_LABEL:
        parts.append(f"arm=unassigned({column.arm_basis})")
    if column.unit:
        parts.append(f"unit={column.unit}")
    if column.field:
        parts.append(f"field={column.field}")
    return " | ".join(parts)


def target_columns(table: Table) -> List[Column]:
    """Spalten mit eindeutigem Zielfeld (Rolle und Arm belegt)."""
    return [c for c in table.columns if c.field]


def unassigned_columns(table: Table) -> List[Column]:
    return [c for c in table.columns if c.role != ROLE_LABEL and not c.field]


def role_counts(table: Table) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for column in table.columns:
        counts[column.role] = counts.get(column.role, 0) + 1
    return counts


def repeated_header_texts(table: Table) -> List[str]:
    """Header-Texte, die ueber mehrere Spalten mehrfach auftreten.

    Sie sind der Hinweis auf Gruppenheader (Arm-/Zeitpunktgruppen), die bei
    der Zerlegung mitgefuehrt werden muessen.
    """
    counts: Dict[str, int] = {}
    for band in table.header_bands:
        if band.span > 1:
            counts[band.text] = counts.get(band.text, 0) + 1
    return [text for text, count in counts.items() if count >= 1]
