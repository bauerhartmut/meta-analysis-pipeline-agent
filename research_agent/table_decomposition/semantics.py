"""Spaltenrollen und Armzuordnung - deterministisch, ohne Modell.

Die Engine soll nicht das Modell raten lassen, welcher Arm zu welcher Spalte
gehoert. Aus der Header-Hierarchie werden Rollen (Mittelwert, SD, n,
Ereignisse, Prozent, p-Wert, ...) und Arme abgeleitet. Was sich nicht
belegen laesst, bleibt ``None`` und wird als ``unassigned``/``ambiguous``
ausgewiesen - nie stillschweigend dem Interventionsarm zugeschlagen.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .model import (
    ARM_COMPARATOR,
    ARM_INTERVENTION,
    HEADER_GEOMETRY_CODES,
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


_GROUP_SIZE_DECL_RE = re.compile(r"^\(?\s*n\s*=\s*(\d{1,6})\s*\)?$", re.IGNORECASE)
_GROUP_SIZE_ANY_RE = re.compile(r"\bn\s*=\s*(\d{1,6})\b", re.IGNORECASE)


def group_size_declaration(text: str) -> Optional[int]:
    """Zahl aus einer reinen Kopfangabe ``n = 456`` (sonst ``None``).

    Eine solche Kopfzelle ist eine feste Gruppengroesse, keine Spalte mit
    Zeilenwerten. Sie wird als Kopf-Fakt gefuehrt (``Table.header_facts``) und
    darf keine Spaltenrolle ``n`` erzeugen - sonst liest der Extraktor
    Zeilenwerte als Gruppengroesse (belegt: ``PMC4319071:T1``, dort wurde
    ``49.05`` aus der Zeile ``Age (years)`` zur Gruppengroesse).
    """
    match = _GROUP_SIZE_DECL_RE.match((text or "").strip())
    return int(match.group(1)) if match else None


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
        if group_size_declaration(text) is not None:
            continue
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


def bind_row_arm(row_label: str, intervention: str = "",
                 comparator: str = "") -> ArmBinding:
    """Arm aus dem Zeilenlabel - nur bei belegtem Vorsprung.

    Manche Tabellen fuehren die Arme als Zeilen (``Control``, ``Basic``,
    ``Plus``) und die Outcomes als Spalten. Dann traegt der Spaltenkopf keinen
    Arm, das Zeilenlabel schon. Es gelten dieselben Grenzen wie im Kopf:
    ohne belegten Vorsprung bleibt der Arm leer.

    Die Schwelle liegt hier bei 0.6 statt 0.5: Zeilenlabels sind kurz und
    generisch, ein einzelnes gemeinsames Wort reicht nicht. ``Apple Juice``
    teilt mit ``White Grape Juice (WGJ)`` nur ``juice`` (0.5) und ist ein
    dritter Arm, kein Interventionsarm; ``Water`` gegen ``colored and flavored
    water (WA)`` trifft dagegen das ganze Label (1.0).
    """
    label = (row_label or "").strip()
    if not label:
        return ArmBinding(None, "kein_label", 0.0)
    return bind_arm((label,), intervention, comparator, min_score=0.6)


def cell_arm(column: Column, row) -> Optional[str]:
    """Arm einer Zelle: Spaltenkopf zuerst, sonst das Zeilenlabel."""
    if column.arm:
        return column.arm
    return getattr(row, "arm", None)


_DEFINITION_RE = re.compile(r"\b([A-Za-z][A-Za-z\-]{2,24})\s*\(([^()]{15,400})\)")
_ARM_DEFINITION_RE = re.compile(
    r"\bn\s*=\s*\d+|\bintervention\b|\bcontrol\b|\bgroup\b|\binstruction\b|\busual\b",
    re.IGNORECASE,
)
_COMPARISON_RE = re.compile(r"\bvs\b|\bversus\b|\bcomparison\b", re.IGNORECASE)


def document_arm_definitions(text: str) -> Dict[str, str]:
    """Armname -> gedruckte Definition aus dem Dokumenttext.

    ``PMC4319071`` definiert im Abstract: ``basic (tailored intervention
    targeting individual cognition and self-regulation processes; n=456),
    plus (basic intervention additionally targeting environmental-level
    factors; n=459), and control (generic nutrition information; n=434)``.
    Der Record nennt nur ``Intervention + targeting environmental-level
    factors``; erst die Definition im Dokument belegt, dass ``Plus`` der
    Interventionsarm ist und nicht ``Basic``.

    Aufgenommen wird nur, was wie eine Armdefinition aussieht (``n =``,
    ``intervention``, ``control``, ``group``, ``instruction``, ``usual``);
    andere Klammerzusaetze sind keine Arme.
    """
    definitions: Dict[str, str] = {}
    for match in _DEFINITION_RE.finditer(text or ""):
        label = match.group(1).strip().lower()
        body = " ".join(match.group(2).split())
        if len(body) < 15 or not _ARM_DEFINITION_RE.search(body):
            continue
        definitions.setdefault(label, body)
    return definitions


def _document_label(text: str) -> str:
    """Erstes Wort eines Labels, ohne Klammerzusatz und Vergleichsform."""
    cleaned = re.sub(r"\([^)]*\)", " ", text or "")
    if _COMPARISON_RE.search(cleaned):
        return ""
    cleaned = re.sub(r"[^0-9A-Za-z\-\s]", " ", cleaned).strip().lower()
    return cleaned.split()[0] if cleaned else ""


def transfer_arms_from_document(tables: Sequence[Table],
                                context: Optional[Dict[str, object]] = None,
                                document_text: str = "") -> int:
    """Arm aus der gedruckten Armdefinition belegen (``arm_basis="dokument"``).

    Der Armname steht in der Tabelle (``Plus`` als Zeilenlabel), die Definition
    im Text. Nur wenn die Definition den Arm des Records belegt, bekommen
    Zeilen mit diesem Label den Arm; ohne Definition bleibt er leer. Es gelten
    dieselben Schwellen wie im Kopf.

    Nur **Zeilenlabels** werden gesetzt, keine Spaltenkoepfe: der Armname einer
    Zeile benennt die Zeile selbst, ihre Werte gehoeren also zu diesem Arm -
    auch wenn das Strichraster verschoben ist. Bei Spalten haengt der Arm an
    der Spaltenposition; in ``PMC4319071:T1`` traegt die Spalte unter ``Plus``
    den Wert von ``Control`` (157.73), ein Arm daraus waere ein falscher Wert.
    """
    context = context or {}
    intervention = str(context.get("intervention") or "")
    comparator = str(context.get("comparator") or "")
    definitions = document_arm_definitions(document_text)
    if not definitions:
        return 0
    proven: Dict[str, str] = {}
    for label, body in definitions.items():
        binding = bind_arm((body,), intervention, comparator)
        if binding.arm and binding.basis == "header_treffer":
            proven[label] = binding.arm
    if not proven:
        return 0
    assigned = 0
    for table in tables:
        for row in table.rows:
            if row.arm or not row.label_path:
                continue
            arm = proven.get(_document_label(row.label_path[-1]))
            if not arm:
                continue
            row.arm = arm
            row.arm_basis = "dokument"
            assigned += 1
    return assigned


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
            # ``n = 434`` ist eine Kopfangabe, kein Spaltenkopf: sie darf den
            # Header-Pfad (und damit Arm und Rolle) nicht besetzen.
            if group_size_declaration(band.text) is not None:
                continue
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


def _bands_overlap(bands: Sequence[object]) -> bool:
    """Ueberlappen sich zwei Kopfbaender derselben Ebene?"""
    for level in sorted({band.level for band in bands}):
        ordered = sorted(
            (band for band in bands if band.level == level),
            key=lambda band: band.col_start,
        )
        for left, right in zip(ordered, ordered[1:]):
            if right.col_start <= left.col_end:
                return True
    return False


def _field_counts(table: Table) -> Counter:
    return Counter(column.field for column in table.columns if column.field)


def consider_header_band_candidate(table: Table,
                                   context: Optional[Dict[str, object]] = None,
                                   assume_order: bool = False) -> str:
    """Kandidat der ordinalen Kopfzuordnung pruefen und nur mit Beleg uebernehmen.

    Die gedruckte Geometrie bleibt der Standard. Jeder Kandidat wird an einer
    Kopie durchgerechnet und nur uebernommen, wenn er

    1. keine Baender derselben Ebene ueberlappen laesst,
    2. alle Baender innerhalb der Spalten haelt,
    3. kein bisher erreichbares Feld verliert,
    4. keine Spalte mit Feld auf ein anderes Feld oder einen anderen Arm
       verschiebt und
    5. kein Feld auf mehr Spalten als vorher legt.

    Geprueft werden alle Kandidaten; uebernommen wird der gueltige mit den
    meisten Feldern - und nur, wenn er mindestens ein Feld hinzugewinnt. Ein
    Umbau ohne Gewinn bleibt aussen vor, sonst aendert sich die Geometrie ohne
    Beleg. Ist keiner gueltig, bleibt die gedruckte Geometrie.

    Rueckgabe: Begruendung (``kandidat:uebernommen:<variante>`` oder
    ``original:<grund>``); leer, wenn es keinen Kandidaten gibt.
    """
    candidates = list(table.header_band_candidates)
    if not candidates:
        return ""
    gruende: List[str] = []
    before_counts = _field_counts(table)
    before_fields = {name for _row_id, name in reachable_cells(table, context)}
    best: Optional[Tuple[str, object, set]] = None
    for name, bands in candidates:
        if not bands:
            gruende.append("kein_band")
            continue
        if any(band.col_end >= len(table.columns) for band in bands):
            gruende.append("spanne_ausserhalb")
            continue
        if _bands_overlap(bands):
            gruende.append("ueberlappung")
            continue
        probe = copy.deepcopy(table)
        probe.header_band_candidates = []
        # Der Kandidat ersetzt die unaufloesbare Geometrie: erst danach ist die
        # Kopfgeometrie fuer die Outcome-Markierung wieder belastbar.
        probe.apply_header_bands(bands)
        enrich_table(probe, context, assume_order=assume_order)
        after_fields = {name_ for _row_id, name_ in reachable_cells(probe, context)}
        if not before_fields <= after_fields:
            gruende.append("feldverlust")
            continue
        verschoben = False
        for column in table.columns:
            twin = probe.column(column.col_id)
            if twin is None:
                gruende.append("spalte_fehlt")
                verschoben = True
                break
            if column.field and twin.field != column.field:
                gruende.append("feld_verschoben")
                verschoben = True
                break
            if column.arm and twin.arm != column.arm:
                gruende.append("arm_verschoben")
                verschoben = True
                break
        if verschoben:
            continue
        if any(count > before_counts[field]
               for field, count in _field_counts(probe).items()
               if field in before_counts):
            gruende.append("mehrfachzuordnung")
            continue
        if best is None or len(after_fields) > len(best[2]):
            best = (name, probe, after_fields)
    if best is None:
        return "original:" + (gruende[0] if gruende else "kein_kandidat")
    name, probe, after_fields = best
    if len(after_fields) <= len(before_fields):
        return "original:kein_gewinn"
    table.apply_header_bands(probe.header_bands)
    table.columns = probe.columns
    table.rows = probe.rows
    table.header_facts = probe.header_facts
    table.focus_rows = probe.focus_rows
    table.context = probe.context
    return f"kandidat:uebernommen:{name}"


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

    if assume_order:
        _assume_arm_order(table)
    # Arme aus gedruckten Abkuerzungen (``TM``) und Rollen aus der Zellform
    # (``Mittel (Streuung)``) - gleiche Pruefung wie bei den Kopfbändern:
    # Kandidat rechnen, nur mit Feldgewinn uebernehmen.
    table.arm_decision = consider_arm_candidate(table, context)
    table.role_decision = consider_role_candidate(table, context)
    _detect_combined_columns(table)
    table.context = dict(context)
    for row in table.rows:
        if row.group_label:
            row.value_role, row.secondary_role = "", ""
            row.arm, row.arm_basis = None, ""
            continue
        label = row.label_path[-1] if row.label_path else row.label
        row.value_role, row.secondary_role = row_roles(label)
        binding = bind_row_arm(label, intervention, comparator)
        row.arm, row.arm_basis = binding.arm, binding.basis
    _mark_outcome_columns(table, str(context.get("outcome") or ""))
    table.header_facts = _group_size_facts(table, intervention, comparator)
    table.focus_rows = outcome_rows(table, str(context.get("outcome") or ""))
    if table.header_band_candidates:
        table.band_decision = consider_header_band_candidate(
            table, context, assume_order=assume_order
        )
        table.header_band_candidates = []
    # Outcome-Zeile aus der Zellform - zuletzt, damit sie auf der uebernommenen
    # Geometrie und den uebernommenen Rollen aufsetzt.
    table.outcome_row_decision = consider_outcome_row_candidate(table, context)
    return table


_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _column_header_text(column: Column) -> str:
    return " ".join(t for t in column.header_path if t) or (column.header or "")


def header_geometry_trustworthy(table: Table) -> bool:
    """Sind die Kopfspannen belegt - oder nur notduerftig verteilt?

    Ohne belegte Spanne landet ein Kopfname auf irgendeiner Spalte. In
    ``PMC4319071:T2`` steht ``Vegetables (grams)`` bei x=43 (Spaltenstart),
    der zugehoerige Wert ``158.93`` aber rechtsbuendig bei x=93 in der
    Folgespalte; das Strichraster (10 Spalten) und der Kopf (5 Zellen) passen
    nicht zusammen. Eine Outcome-Zuordnung waere dort geraten - deshalb wird
    sie verweigert, statt einen falschen Wert an ein Feld zu haengen.
    """
    return not any(
        code in irregularity
        for irregularity in table.irregularities
        for code in HEADER_GEOMETRY_CODES
    )


def _mark_outcome_columns(table: Table, outcome: str) -> None:
    """Spalten, deren Kopf das Outcome des Records nennt.

    Fuer Tabellen mit Armen als Zeilen (``PMC4319071:T2``): der Arm steht im
    Zeilenlabel (``Control``), das Outcome im Spaltenkopf
    (``Vegetables (grams)``). Nur solche Spalten duerfen mit einem Zeilenarm
    ein Feld bilden; ohne belegten Outcome-Namen bleibt die Spalte neutral.
    """
    for column in table.columns:
        column.is_outcome = False
    if not outcome:
        return
    if not header_geometry_trustworthy(table):
        table.irregularities.append("outcome_spalte_ohne_kopfgeometrie")
        return
    scored: List[Tuple[float, Column]] = []
    for column in table.columns:
        if column.role == ROLE_LABEL:
            continue
        score = _outcome_match_score(
            outcome, _column_header_text(column), forward_only=True
        )
        if score >= _MIN_OUTCOME_SCORE:
            scored.append((score, column))
    if not scored:
        return
    best = max(score for score, _column in scored)
    kept: Dict[str, int] = {}
    for score, column in sorted(scored, key=lambda item: item[1].col_id):
        if score != best:
            continue
        first = kept.setdefault(column.role, column.col_id)
        if first == column.col_id:
            column.is_outcome = True
            continue
        # Zwei gedruckte Spalten nennen dasselbe Outcome (``Total losses`` und
        # ``First day losses``): es gilt die erste, der Rest wird notiert statt
        # stillschweigend mitgelesen.
        table.irregularities.append(
            f"outcome_spalte_mehrdeutig:{column.role}:{first}|{column.col_id}"
        )


# Zellform eines Mittelwerts mit Streuung in Klammern (``--0.38 (0.37)``).
_MEAN_FORM_RE = re.compile(
    r"^[-+]?\d+(?:[.,]\d+)?\s*\(\s*[-+]?\d+(?:[.,]\d+)?\s*\)$"
)
# Formen, die *nicht* als Mittelwert gelesen werden duerfen: Ereignis mit
# Prozentbeigabe, Anteil, p-Wert.
_KEIN_MEAN_RE = re.compile(
    r"\bn\s*\(\s*%\s*\)|\bpercent|%|\bevents?\b|\bp\s*-?\s*value|\banteil",
    re.IGNORECASE,
)


def _zellform_mean(table: Table, column: Column) -> bool:
    """Sprechen die Zellen einer Spalte fuer ``Mittel (Streuung)``?

    Beleg ist die gedruckte Form: mindestens zwei gefuellte Zellen, davon 60
    Prozent genau ``Zahl (Zahl)``. Sobald eine Zelle nach Ereignis oder Prozent
    aussieht (``n (%)``, ``%``) oder ein Zeilenlabel das sagt (``Not complying,
    n (%)``), faellt der Kandidat weg - ``12 (34)`` sieht sonst wie ein Mittel
    mit Streuung aus.
    """
    if _KEIN_MEAN_RE.search(_column_header_text(column)):
        return False
    for row in table.rows:
        if _KEIN_MEAN_RE.search(row.label or "") or _KEIN_MEAN_RE.search(
                " ".join(row.label_path or ())):
            return False
    gefuellt = 0
    doppelt = 0
    for row in table.rows:
        zelle = row.cells.get(column.col_id)
        text = (zelle.text or "").strip() if zelle is not None else ""
        if not text:
            continue
        gefuellt += 1
        sauber = re.sub(r"\[([^\]]*)\]\(#[^)]*\)|[*\u2020\u2021]+", " ", text)
        sauber = re.sub(r"-{2,}", "-", sauber.translate({
            "\u2212": "-", "\u2013": "-", "\u2014": "-"})).strip()
        if _MEAN_FORM_RE.match(sauber):
            doppelt += 1
    return gefuellt >= 2 and doppelt / gefuellt >= 0.6


def consider_role_candidate(table: Table,
                            context: Optional[Dict[str, object]] = None) -> str:
    """Rolle ``mean`` aus der Zellform - nur mit Beleg und Feldgewinn.

    Der Kopf nennt in solchen Spalten keine Rolle (``TM``, ``Cemented``); die
    Zellen tragen aber ``Mittel (Streuung)``. Wie bei den Kopfbändern und den
    Armen entscheidet die Validierung an einer Kopie: die Rolle wird nur
    uebernommen, wenn dadurch ein Feld entsteht und keines verloren geht. Ohne
    Arm entsteht kein Feld - dann bleibt die Rolle unbekannt.
    """
    context = context or {}
    intervention = str(context.get("intervention") or "")
    comparator = str(context.get("comparator") or "")
    kandidaten = [
        column for column in table.columns
        if column.role == ROLE_UNKNOWN and column.arm and _zellform_mean(table, column)
    ]
    if not kandidaten:
        return "original:kein_kandidat"
    probe = copy.deepcopy(table)
    for column in kandidaten:
        twin = probe.column(column.col_id)
        if twin is None:
            continue
        twin.role = ROLE_MEAN
        twin.field = field_for(ROLE_MEAN, twin.arm)
    _detect_combined_columns(probe)
    vorher = _felder_mit_fakten(table, intervention, comparator)
    nachher = _felder_mit_fakten(probe, intervention, comparator)
    if not vorher <= nachher:
        return "original:feldverlust"
    if len(nachher) <= len(vorher):
        return "original:kein_gewinn"
    for column in kandidaten:
        column.role = ROLE_MEAN
        column.field = field_for(ROLE_MEAN, column.arm)
    _detect_combined_columns(table)
    return "kandidat:uebernommen:" + ",".join(
        f"c{column.col_id}" for column in kandidaten)


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
        # ``Mean (SE)`` und ``Mean (95% CI)``: die zweite Zahl ist keine
        # Streuung. Sie als Standardabweichung zu fuehren waere ein falscher
        # Wert am richtigen Feld.
        if re.search(r"\bse\b|standard error|\bci\b|confidence",
                     _column_header_text(column).lower()):
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


# Armzuordnungen, die als Beleg zaehlen. ``reihenfolge`` fehlt bewusst: die
# Zuordnung aus der Spaltenposition ist eine Annahme, kein Nachweis.
_BELEGTE_ARM_BASIS = {"header_treffer", "abkuerzung", "uebertrag", "dokument"}

_ARM_ABKUERZUNG_RE = re.compile(r"\(([A-Za-z][A-Za-z0-9\-]{1,9})\)")


def _arm_abkuerzungen(name: str) -> set:
    """Gedruckte Abkuerzungen einer Armbezeichnung (``... component (TM)``)."""
    return {
        re.sub(r"[^a-z0-9]", "", treffer.lower())
        for treffer in _ARM_ABKUERZUNG_RE.findall(name or "")
    }


def _abkuerzungs_arm(header_path: Sequence[str], intervention: str,
                     comparator: str) -> Optional[str]:
    """Arm, dessen gedruckte Abkuerzung als eigener Kopfteil steht.

    ``TM`` allein traegt kein unterscheidendes Token (zwei Zeichen) und matcht
    deshalb keine Armbezeichnung. Steht die Abkuerzung aber in Klammern im
    Armnamen (``The trabecular metal tibial monoblock component (TM)``), ist sie
    ein belegter Verweis. Fuehren beide Arme dieselbe Abkuerzung, bleibt der Arm
    leer - dann ist nichts entschieden.
    """
    kurz_intervention = _arm_abkuerzungen(intervention)
    kurz_comparator = _arm_abkuerzungen(comparator)
    for teil in header_path or ():
        name = _normalise_arm(teil)
        if not name:
            continue
        treffer = []
        if name in kurz_intervention:
            treffer.append(ARM_INTERVENTION)
        if name in kurz_comparator:
            treffer.append(ARM_COMPARATOR)
        if len(treffer) == 1:
            return treffer[0]
        if treffer:
            return None
    return None


def _felder_mit_fakten(table: Table, intervention: str, comparator: str) -> set:
    """Felder aus Spalten **und** Kopfangaben - der Gewinn eines Kandidaten."""
    felder = set(reachable_fields(table))
    for fact in _group_size_facts(table, intervention, comparator):
        feld = field_for(ROLE_N, fact.get("arm") or None)
        if feld:
            felder.add(feld)
    return felder


def consider_arm_candidate(table: Table,
                           context: Optional[Dict[str, object]] = None) -> str:
    """Leere Spaltenarme aus gedruckter Abkuerzung - nur mit Beleg und Gewinn.

    Wie bei den Kopfbändern entscheidet die Validierung, nicht der Studienname:
    der Kandidat wird an einer Kopie durchgerechnet und nur uebernommen, wenn er
    mindestens ein Feld gewinnt und keines verliert. Gefuellt werden
    ausschliesslich leere Arme; ein bereits gesetzter Arm wird nie
    ueberschrieben, und ohne gedruckte Abkuerzung gibt es keinen Kandidaten.
    """
    context = context or {}
    intervention = str(context.get("intervention") or "")
    comparator = str(context.get("comparator") or "")
    kandidat = {
        column.col_id: arm
        for column in table.columns
        if not column.arm and column.role != ROLE_LABEL
        for arm in (_abkuerzungs_arm(column.header_path, intervention, comparator),)
        if arm
    }
    if not kandidat:
        return "original:kein_kandidat"
    probe = copy.deepcopy(table)
    for col_id, arm in kandidat.items():
        twin = probe.column(col_id)
        if twin is None:
            continue
        twin.arm = arm
        twin.arm_basis = "abkuerzung"
        twin.field = field_for(twin.role, arm)
    vorher = _felder_mit_fakten(table, intervention, comparator)
    nachher = _felder_mit_fakten(probe, intervention, comparator)
    if not vorher <= nachher:
        return "original:feldverlust"
    if len(nachher) <= len(vorher):
        return "original:kein_gewinn"
    for col_id, arm in kandidat.items():
        column = table.column(col_id)
        if column is None:
            continue
        column.arm = arm
        column.arm_basis = "abkuerzung"
        column.field = field_for(column.role, arm)
    return "kandidat:uebernommen:" + ",".join(f"c{col_id}" for col_id in sorted(kandidat))


def _group_size_facts(table: Table, intervention: str,
                      comparator: str) -> List[Dict[str, object]]:
    """Feste Gruppengroessen aus Kopfangaben (``n = 456``).

    Der Wert steht woertlich im Kopf und gilt fuer die ganze Spaltengruppe.
    Der Arm kommt aus dem uebrigen Header-Pfad an dieser Stelle; laesst er sich
    nicht belegen, bleibt ``arm`` leer (kein Raten aus der Spaltenposition).
    """
    facts: List[Dict[str, object]] = []
    ordered = sorted(table.header_bands, key=lambda b: b.level)
    for band in sorted(table.header_bands, key=lambda b: (b.level, b.col_start)):
        match = _GROUP_SIZE_ANY_RE.search(band.text or "")
        if not match:
            continue
        path = [
            other.text for other in ordered
            if other.level <= band.level
            and other.col_start <= band.col_start <= other.col_end
            and group_size_declaration(other.text) is None
        ]
        binding = bind_arm(path, intervention, comparator)
        arm, arm_basis = binding.arm, binding.basis
        if arm is None:
            # Der Arm kann auch an den Spalten unter dem Band belegt sein
            # (etwa ``TM``-Spalten ueber eine gedruckte Abkuerzung); dann gilt
            # er fuer diese Kopfangabe. Ein nur aus der Reihenfolge stammender
            # Arm ist kein Beleg, und gemischte Arme unter dem Band lassen die
            # Angabe ohne Arm - sie gilt dann fuer keine Gruppe eindeutig.
            betroffen = [
                column for column in table.columns
                if band.col_start <= column.col_id <= band.col_end and column.arm
            ]
            gesetzt = {column.arm for column in betroffen}
            belegt = {
                column.arm for column in betroffen
                if column.arm_basis in _BELEGTE_ARM_BASIS
            }
            if len(gesetzt) == 1 and len(belegt) == 1:
                arm, arm_basis = belegt.pop(), "spalte"
        facts.append({
            "kind": "group_size",
            "text": band.text,
            "value": int(match.group(1)),
            "level": band.level,
            "col_start": band.col_start,
            "col_end": band.col_end,
            "basis": "kopf_angabe",
            "arm": arm,
            "arm_basis": arm_basis,
        })
    return facts


_ROW_MEAN_RE = re.compile(r"\bmean\b|\bmittelwert\b|\baverage\b", re.IGNORECASE)
_ROW_SD_RE = re.compile(r"\(\s*s\.?\s*d\.?\s*\)|\bstandard deviation\b", re.IGNORECASE)
_ROW_EVENTS_RE = re.compile(r"\bn\s*\(\s*%\s*\)", re.IGNORECASE)
_ROW_N_RE = re.compile(r"^\(?\s*n\s*\)?$", re.IGNORECASE)


def row_roles(row_label: str) -> Tuple[str, str]:
    """Rolle und Zweitrolle aus einem Zeilenlabel.

    In Tabellen wie ``PMC4319071:T1`` steht die Rolle nicht im Spaltenkopf
    (die Spalten heissen ``Control``, ``Basic``, ``Plus``), sondern in der
    Zeile: ``Mean (SD)`` traegt Mittelwert und Streuung, ``Not complying,
    n (%)`` eine Ereigniszahl. Ohne diese Ableitung bleiben solche Tabellen
    ohne jedes Feld.
    """
    text = (row_label or "").strip()
    if not text:
        return "", ""
    if _ROW_MEAN_RE.search(text):
        return ROLE_MEAN, (ROLE_SD if _ROW_SD_RE.search(text) else "")
    if _ROW_EVENTS_RE.search(text):
        return ROLE_EVENTS, ""
    if _ROW_N_RE.match(text):
        return ROLE_N, ""
    return "", ""


_MIN_OUTCOME_SCORE = 0.5


def _stem(token: str) -> str:
    """Einfache Pluralnormalisierung fuer den Outcome-Abgleich.

    ``deaths``/``Death`` und ``events``/``event`` sind dasselbe Outcome; ohne
    diese Normalisierung faellt die haeufigste Schreibweise durch. Nur der
    Outcome-Abgleich nutzt sie - die Armzuordnung bleibt unveraendert.
    """
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _row_text(row) -> str:
    if row.label_path:
        return " ".join(row.label_path)
    return row.group_label or row.label or ""


def _outcome_match_score(outcome: str, text: str,
                         forward_only: bool = False) -> float:
    """Belegte Uebereinstimmung zwischen Outcome und Label/Kopfzeile.

    Zwei Richtungen wie bei der Armzuordnung: das Outcome darf lang sein
    (``rate of clinical success at the test-of-cure visit``), das Label kurz
    (``Clinical success``). Eine reine Zahlenuebereinstimmung (``10``) belegt
    kein Outcome und ergibt 0.

    ``forward_only`` gilt fuer Spaltenkoepfe: dort ist die Rueckwaertsrichtung
    schaedlich, weil ein kurzer Kopf sonst schon mit einem gemeinsamen Wort
    gewinnt. ``6 months follow-up`` traf so das Outcome ``continued
    antidepressants until the 6-month`` und lieferte eine falsche Zelle.
    """
    target = {_stem(token) for token in _tokens(outcome)}
    tokens = {_stem(token) for token in _tokens(text)}
    if not target or not tokens:
        return 0.0
    shared = target & tokens
    if not shared or not any(not token.isdigit() for token in shared):
        return 0.0
    forward = len(shared) / len(target)
    if forward_only:
        return forward
    return max(forward, len(shared) / len(tokens))


def outcome_rows(table: Table, outcome: str) -> List[int]:
    """Zeilen, die das gesuchte Outcome tragen (Zeilenlabel-Pfad, kein Gold).

    Der Pfad enthaelt die Zeilengruppen (``Dietary intake``, ``Vegetable
    intake (grams)``) und das eigene Label (``Mean (SD)``); erst zusammen ist
    die Zeile eindeutig. Ohne Treffer bleibt die Liste leer - dann ist keine
    Zelle erwartbar, und der Lauf meldet das, statt alle Zeilen zu lesen.
    """
    scored: List[Tuple[float, int]] = []
    for row in table.rows:
        if row.group_label:
            continue
        score = _outcome_match_score(outcome, _row_text(row))
        if score >= _MIN_OUTCOME_SCORE:
            scored.append((score, row.row_id))
    if not scored:
        return []
    best = max(score for score, _row_id in scored)
    return [row_id for score, row_id in scored if score == best]


def _messspalten(table: Table) -> List[Column]:
    """Spalten, die ein Feld tragen - die Messspalten einer Datenzeile."""
    return [
        column for column in table.columns
        if column.field and column.role != ROLE_LABEL
    ]


def _zeile_vollstaendig(table: Table, row, spalten: Sequence[Column]) -> bool:
    """Steht in jeder Messspalte eine Zahl?"""
    for column in spalten:
        cell = row.cells.get(column.col_id)
        text = (cell.text or "") if cell is not None else ""
        if not _NUMBER_RE.search(text.translate(
                {"\u2212": "-", "\u2013": "-", "\u2014": "-"})):
            return False
    return True


def consider_outcome_row_candidate(table: Table,
                                   context: Optional[Dict[str, object]] = None) -> str:
    """Outcome-Zeile aus der Zellform - als Vorschlag, nicht als Uebernahme.

    Nennt kein Zeilenlabel das Outcome, bleibt die Tabelle ohne erwartbare
    Zelle. Kandidat ist eine **vollstaendige Datenzeile**: in jeder Messspalte
    (Spalte mit Feld) steht eine Zahl. Diese Form trennt eine Ergebniszeile von
    Zwischenueberschriften, Definitions- und Leerzeilen - mehr nicht.

    Deshalb wird hier nichts gesetzt: die Pruefung der Kopfbänder, Arme und
    Rollen verlangt einen Gewinn an **Feldern**, und ein Feld entsteht durch die
    Zeilenwahl nicht. Wollte man stattdessen erwartbare Zellen als Gewinn
    nehmen, waere die Pruefung selbstbestaetigend - jede gesetzte Zeile gewinnt
    Zellen. Eine Zeile braucht daher einen gedruckten Beleg ueber die Form
    hinaus; die Entscheidung haelt nur fest, was die Form hergibt
    (``original:treffer``, ``original:mehrdeutig``, ``vorschlag:r<id>``).
    """
    context = context or {}
    outcome = str(context.get("outcome") or "")
    if not outcome:
        return "original:kein_outcome"
    if outcome_rows(table, outcome):
        return "original:treffer"
    spalten = _messspalten(table)
    if len(spalten) < 2:
        return "original:kein_kandidat"
    voll = [
        row for row in table.rows
        if not row.group_label and _zeile_vollstaendig(table, row, spalten)
    ]
    if not voll:
        return "original:kein_kandidat"
    if len(voll) > 1:
        table.irregularities.append(
            "outcome_zeile_mehrdeutig:" + "|".join(str(row.row_id) for row in voll)
        )
        return "original:mehrdeutig"
    return f"vorschlag:r{voll[0].row_id}"


def reachable_cells(table: Table,
                    context: Optional[Dict[str, object]] = None) -> set:
    """Erwartbare Werte: Zellen der Outcome-Zeile **und** Kopfangaben.

    Zellwerte zaehlen nur in der Outcome-Zeile (Spaltenfeld **und** Zeile).
    Feste Kopfangaben (``header_facts``, etwa ``n = 456``) haengen an keiner
    Zeile; sie sind erwartbar, sobald der Arm belegt ist, und werden ohne
    Modellaufruf als Beleg gefuehrt (Adresse ``(-1, col_start)``).
    """
    context = context if context is not None else (table.context or {})
    cells = set()
    for fact in table.header_facts:
        arm = fact.get("arm")
        field = field_for(ROLE_N, arm if isinstance(arm, str) else None)
        if field:
            cells.add((-1, field))
    rows = outcome_rows(table, str(context.get("outcome") or ""))
    if rows:
        column_fields = reachable_fields(table)
        for row_id in rows:
            row = table.row(row_id)
            cells |= {(row_id, name) for name in column_fields}
            if row is not None:
                cells |= {(row_id, name) for name in row_fields(table, row)}
    # Arme als Zeilen: die Zeile traegt den Arm, die Spalte das Outcome. Der
    # Wert steht woertlich in der Zelle, nur die Zuordnung kommt aus Label und
    # Kopf; ohne belegten Arm entsteht kein Feld.
    for row in table.rows:
        arm = getattr(row, "arm", None)
        if not arm:
            continue
        for column in table.columns:
            if not column.is_outcome or column.role == ROLE_UNKNOWN:
                continue
            cell = row.cells.get(column.col_id)
            if cell is None or not (cell.text or "").strip():
                continue
            field = field_for(column.role, arm)
            if field:
                cells.add((row.row_id, field))
    return cells


def row_fields(table: Table, row) -> set:
    """Felder, die eine Zeile aus ihren Zellen hergibt.

    Spaltenfeld zuerst. Traegt der Spaltenkopf keine Rolle (``Control``), gilt
    die Rolle aus dem Zeilenlabel (``Mean (SD)`` -> mean + sd, ``n (%)`` ->
    events) - aber nur dann, und nur bei vorhandener Zelle: eine leere Zelle
    belegt nichts.
    """
    fields: set = set()
    role = getattr(row, "value_role", "")
    secondary = getattr(row, "secondary_role", "")
    for column in table.columns:
        if column.role == ROLE_LABEL:
            continue
        cell = row.cells.get(column.col_id)
        text = (cell.text or "") if cell is not None else ""
        if not text.strip():
            continue
        arm = cell_arm(column, row)
        if column.field:
            fields.add(column.field)
            continue
        if column.role == ROLE_UNKNOWN and role:
            field = field_for(role, arm)
            if field:
                fields.add(field)
        elif column.is_outcome and column.role != ROLE_UNKNOWN:
            # Arme als Zeilen, Outcome als Spalte: der Arm kommt aus der Zeile.
            field = field_for(column.role, arm)
            if field:
                fields.add(field)
        if secondary and arm and len(_NUMBER_RE.findall(text)) >= 2:
            second = field_for(secondary, arm)
            if second:
                fields.add(second)
    return fields


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
        if not column.is_outcome or column.role == ROLE_UNKNOWN:
            continue
        for row in table.rows:
            arm = getattr(row, "arm", None)
            cell = row.cells.get(column.col_id)
            if not arm or cell is None or not (cell.text or "").strip():
                continue
            field = field_for(column.role, arm)
            if field:
                fields.add(field)
    return fields


def _timepoint_key(table: Table) -> Tuple[str, ...]:
    """Zeitpunkte einer Tabelle aus ihren Gruppenzeilen (normalisiert)."""
    labels: List[str] = []
    for row in table.rows:
        if not row.group_label:
            continue
        label = _norm_label(row.group_label)
        if label and label not in labels:
            labels.append(label)
    return tuple(labels)


def primary_tables(tables: Sequence[Table],
                   context: Optional[Dict[str, object]] = None) -> Dict[str, str]:
    """Je Outcome und Zeitpunkt nur eine Tabelle - die erste gedruckte.

    ``PMC4319071`` druckt dieselben Outcomes und Zeitpunkte zweimal:
    ``T2`` (Gesamtstichprobe) und ``T4`` (Risikogruppen, ``n=803``/``n=1014``).
    Beide liefern ``intervention_mean`` und ``comparator_mean`` mit anderen
    Werten (158.67 gegen 143.25); zwei Kandidaten fuer ein Feld kosten
    Precision.

    Gewaehlt wird je Zeitpunktmenge die erste gedruckte Tabelle - und nur
    dann, wenn sie die Felder der uebrigen abdeckt. Deckt sie sie nicht ab,
    bleiben alle stehen, sonst ginge ein Feld verloren. Tabellen ohne
    Zielfeld sind keine Kandidaten.

    Rueckgabe: Zuordnung ``verdraengt -> gewaehlt``; leer, wenn nichts
    verdraengt wird.
    """
    context = context or {}

    def served(table: Table) -> set:
        """Felder, die diese Tabelle fuer **dieses** Outcome hergibt.

        Nicht ``reachable_fields``: das zaehlt alle Spaltenfelder der Tabelle,
        auch die fremder Outcomes. In ``PMC1216327`` deckt die
        Baseline-Charakteristik-Tabelle sonst scheinbar alles ab und verdraengt
        die Ergebnistabelle.
        """
        return {name for _row_id, name in reachable_cells(table, context)}

    groups: Dict[Tuple[str, ...], List[Table]] = {}
    for table in tables:
        key = _timepoint_key(table)
        # Ohne Zeitpunkt-Gruppen ist die Tabelle keine Zeitpunkt-Tabelle
        # (Baseline-Charakteristika, Elektrolyte, ...). Sie wird nie verdraengt.
        if not key or not served(table):
            continue
        groups.setdefault(key, []).append(table)
    redundant: Dict[str, str] = {}
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda table: (table.index, table.table_id))
        first = ordered[0]
        first_fields = served(first)
        # Nur verdraengen, wenn die erste Tabelle alle Felder der uebrigen
        # abdeckt - sonst ginge ein Feld verloren.
        if not all(served(table) <= first_fields for table in ordered[1:]):
            continue
        for table in ordered[1:]:
            redundant[table.table_id] = first.table_id
    return redundant


_TIMEPOINT_RE = re.compile(
    r"(?i)\b(baselines?|follow[\s-]?ups?|weeks?|wks?|days?|months?|mths?|years?|yrs?"
    r"|visits?|endpoints?|screenings?|t0|t1|t2)\b"
)


def column_timepoints(table: Table) -> Tuple[str, ...]:
    """Zeitpunkte, die im **Spaltenkopf** stehen, in Leserichtung.

    Getrennt von der Zeilenlogik (``_timepoint_key``): dort stehen Zeitpunkte in
    Gruppenzeilen, hier in den Kopfbaendern. Erkannt wird ein Band nur, wenn

    1. sein Text ein Zeitpunktwort traegt (``baseline``, ``3 months``, ``week 4``),
    2. es ueber mindestens eine Wertspalte laeuft,
    3. es weder Rollen- noch Armtext ist (``Mean (SD)``, ``n = 45``,
       ``Placebo`` werden nicht zu Zeitpunkten).

    Rueckgabe: normalisierte Zeitpunkte in Leserichtung; leer, wenn weniger als
    zwei verschiedene Zeitpunkte im Kopf stehen. Die Auswahlregel
    (``primary_tables``) nutzt weiterhin nur die Zeilenlogik - die Erweiterung
    ist absichtlich noch nicht verdrahtet, weil sie die eingefrorene Messung
    veraendern wuerde.
    """
    found: List[Tuple[int, str]] = []
    for band in sorted(table.header_bands, key=lambda b: (b.col_start, b.level)):
        text = (band.text or "").strip()
        if not text or band.col_end < band.col_start:
            continue
        if group_size_declaration(text) is not None:
            continue
        if role_for_header((text,)) != ROLE_UNKNOWN:
            continue
        match = _TIMEPOINT_RE.search(text)
        if not match:
            continue
        label = _norm_label(text)
        if not label:
            continue
        if label not in [name for _start, name in found]:
            found.append((band.col_start, label))
    if len(found) < 2:
        return ()
    return tuple(name for _start, name in found)


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
