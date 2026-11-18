"""Deterministischer Parser fuer Tabellen in Textdokumenten.

Der Parser erzeugt aus dem gespeicherten Dokumenttext die semantische
Tabellenstruktur (Blattspalten, Header-Baender mit Spannen, Datenzeilen,
Fussnoten). Er raet nichts: was nicht belegt ist, bleibt leer und wird als
Irregularitaet notiert.

Unterstuetzte Formen:

1. ``pandoc-rule``: Strichregel-Zeile (``-----  -----  -----``) setzt die
   Blattspalten; Header-Zeilen stehen darueber und/oder darunter. Das ist die
   Form der Yun-Markdown-Dokumente.
2. ``pipe``: Pandoc-Pipetabelle (``| a | b |`` mit ``|---|---|``).
3. ``whitespace``: Caption plus spaltenweise gesetzter Text ohne Regel; die
   Spaltenintervalle werden aus den Zellpositionen geclustert.

Alle Positionen sind Zeichen-Offsets im uebergebenen Text; ``page`` bleibt
``None``, wenn die Quelle keine Seitenangabe traegt (Markdown: keine).
"""

from __future__ import annotations

import re
from dataclasses import replace as dc_replace
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .model import (
    HEADER_GEOMETRY_CODES,
    ROLE_LABEL,
    Cell,
    Column,
    DocumentTables,
    Footnote,
    HeaderBand,
    Row,
    Table,
)

# --- Zahlennormalisierung -------------------------------------------------
# Dieselben Regeln wie in der Vision-Lesung (definiert, nicht geraten):
# Unicode-Minus -> ASCII-Minus, Dezimalkomma -> Dezimalpunkt, kein
# Tausenderraten. Zusaetzlich: reine Prozentangaben und "x ± y"-Zellen sind
# keine Armfelder und liefern None; "13 (n)" ist eine Ereigniszahl.
_PLAIN_NUMBER_RE = re.compile(r"^[-+]?\d+(?:[.,]\d+)?$")
_COUNT_WITH_N_RE = re.compile(r"^([-+]?\d+)\s*\(\s*n\s*\)$", re.IGNORECASE)
_PERCENT_RE = re.compile(r"^[-+]?\d+(?:[.,]\d+)?\s*%$")
_PLUSMINUS_RE = re.compile(r"\d\s*[±]\s*\d")
_TRAILING_MARK_RE = re.compile(r"[*†‡§¶^]+$")


def normalise_number_text(value: str) -> str:
    """Dokumentierte Normalisierung vor dem Zahlenvergleich."""
    s = str(value)
    s = s.replace("\u2212", "-")
    s = s.replace("\u00a0", " ")
    s = s.replace(",", ".")
    s = " ".join(s.split())
    return s.strip()


def parse_value(text: str) -> Optional[float]:
    """Zahl aus einem Zelltext, sonst None.

    ``None`` ist die ehrliche Antwort fuer Prozentangaben, ``mean ± sd`` in
    einer Zelle, Text und leere Zellen - solche Zellen werden nie zu einem
    Armwert umgedeutet.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    # Fussnotenzeichen am Zellende ("0.02*", "4.13**") sind Verweise, keine
    # Wertbestandteile; sie werden entfernt, der verbatim-Text bleibt erhalten.
    raw = _TRAILING_MARK_RE.sub("", raw).strip()
    if not raw:
        return None
    if _PERCENT_RE.match(raw) or _PLUSMINUS_RE.search(raw):
        return None
    count = _COUNT_WITH_N_RE.match(raw)
    if count:
        try:
            return float(count.group(1))
        except ValueError:
            return None
    if _PLAIN_NUMBER_RE.match(raw):
        try:
            return float(normalise_number_text(raw))
        except ValueError:
            return None
    return None


# --- Zeilen-Hilfen -------------------------------------------------------
_RULE_RE = re.compile(
    r"^\s*(?:(?:-{3,}|={3,}|\u2014{3,})[ \t]+)+(?:-{3,}|={3,}|\u2014{3,})\s*$"
)
_DASH_RUN_RE = re.compile(r"(?:-{3,}|={3,}|\u2014{3,})")
_PIPE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$")
_FENCE_RE = re.compile(r"^\s*:::+\s*[\w.-]*\s*$")
_CAPTION_HINT_RE = re.compile(
    r"^\s*(?:Supplementary\s+)?(?:Table|TABLE|Tabelle)\s*[A-Z]?\d+", re.IGNORECASE
)
_GAP_RE = re.compile(r"[ \t]{2,}")
_WORD_RE = re.compile(r"[A-Za-z]{3,}")
_DIGIT_RE = re.compile(r"\d")
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_DECIMAL_RE = re.compile(r"\d[.,]\d")
_FOOTNOTE_MARK_RE = re.compile(r"^\s*([*†‡§¶^]|\(?[a-z]\)|\(?[ivx]+\)|\d\))\s*")
_COMPARISON_LABEL_RE = re.compile(r"\bvs\.?\b|\bversus\b", re.IGNORECASE)
_BOLD_LABEL_RE = re.compile(r"^\*\*[^*]+\*\*[.,]?$")


def _plain_label(text: str) -> str:
    """Labeltext ohne Fett- und Fussnotenzeichen."""
    value = (text or "").strip()
    value = re.sub(r"^\*\*|\*\*$", "", value)
    value = value.strip("*^ ")
    return " ".join(value.split())


def _is_group_label_row(line: str, cells: Sequence[Tuple[int, int, str]]) -> bool:
    """Fette Zeilengruppe (``**Dietary intake**``) ist Label, keine Kopfzeile.

    Solche Zeilen tragen genau eine Zelle. Wird die Zeile als Tabellenende
    gelesen, fehlen alle Datenzeilen darunter (belegt: ``PMC4319071:T1`` mit
    nur einer gelesenen Zeile).
    """
    if len(cells) != 1:
        return False
    if not _BOLD_LABEL_RE.match((cells[0][2] or "").strip()):
        return False
    return not _looks_prose(line)


def _is_row_label_header(cells: Sequence[Tuple[int, int, str]]) -> bool:
    """Kopfzeile, die in Wahrheit Zeilenlabels traegt.

    Vergleichszeilen (``Basic vs control``) stehen in PDF-Abzuegen an
    Kopfposition, bezeichnen aber Auswertungen, nicht Spalten. Wird eine solche
    Zeile als Kopf gelesen, bekommen die ersten Spalten einen falschen
    Header-Pfad - und damit einen falschen Arm. Sie wird deshalb weder Kopf
    noch Datenzeile, sondern als unregelmaessig notiert.
    """
    texts = [(cell[2] or "").strip() for cell in cells]
    if not texts:
        return False
    if any(_COMPARISON_LABEL_RE.search(text) for text in texts):
        return True
    return len(texts) == 1 and bool(_BOLD_LABEL_RE.match(texts[0]))


def split_cells(line: str) -> List[Tuple[int, int, str]]:
    """Zellen einer Zeile als (start, end, text) - Trenner sind 2+ Leerzeichen.

    Einzelne Wortabstaende bleiben in der Zelle: ``Mean RT`` ist eine Zelle.
    """
    if not line or not line.strip():
        return []
    cells: List[Tuple[int, int, str]] = []
    position = 0
    for chunk in _GAP_RE.split(line):
        if not chunk:
            position += 0
            continue
        start = line.find(chunk, position)
        if start < 0:
            start = position
        cells.append((start, start + len(chunk), chunk.strip()))
        position = start + len(chunk)
    return [c for c in cells if c[2]]


def rule_intervals(rule_line: str) -> List[Tuple[int, int]]:
    """x-Intervalle der Blattspalten aus einer Strichregel-Zeile."""
    return [(m.start(), m.end()) for m in _DASH_RUN_RE.finditer(rule_line)]


def _covered(span: Tuple[int, int], intervals: Sequence[Tuple[int, int]]) -> List[int]:
    _lo, _hi = span
    hits = []
    for idx, (i_start, i_end) in enumerate(intervals):
        if min(i_end, _hi) - max(i_start, _lo) > 0:
            hits.append(idx)
    return hits


def _anchor_column(span: Tuple[int, int],
                   intervals: Sequence[Tuple[int, int]]) -> Optional[int]:
    """Ankerspalte einer Zelle: die Spalte, die den Grossteil der Zelle traegt.

    Reine Ueberlappung genuegt nicht - ein 2 Zeichen breites ``SD`` beruehrt
    durch den Spaltenabstand auch die Nachbarspalte. Deshalb zaehlt die Spalte
    mit dem groessten Ueberlappungsanteil; bei Gleichstand entscheidet die
    Naehe zur Spaltenmitte. Mehrspaltige Zellen (echter colspan) werden ueber
    ``_covered`` nur dann als Spanne gelesen, wenn sie in mehreren Spalten
    mehr als die Haelfte ihrer Breite belegen.
    """
    if not intervals:
        return None
    width = max(span[1] - span[0], 1)
    best = None
    best_share = 0.0
    for idx, (i_start, i_end) in enumerate(intervals):
        overlap = min(i_end, span[1]) - max(i_start, span[0])
        share = overlap / width
        if share > best_share:
            best, best_share = idx, share
    if best is not None and best_share > 0:
        return best
    return _nearest(span, intervals)


def _resolve_header_spans(table: Table) -> None:
    """Spannen der Header-Zellen aus der Verschachtelung der Header-Ebenen.

    Vorgehen (deterministisch, ohne Modell):

    1. Die unterste Header-Ebene ist die Blaetterebene; ihre Anker spannen den
       Header-Bereich ``[min, max]`` auf.
    2. Jede hoehere Ebene teilt den Bereich ihrer Elternebene gleichmaessig
       unter ihren Zellen auf (Reihenfolge der Anker). Das ist die Form, die
       echte Tabellen mit Arm- und Zeitpunktgruppen haben: 6 Wertspalten, 3
       Arme -> je 2 Spalten pro Gruppe.
    3. Zellen ausserhalb des Blaetterbereichs (etwa eine einzelne
       ``P value``-Spalte) bleiben einspaltig.
    4. Geht die Teilung nicht auf, bleibt die Spanne konservativ einspaltig und
       die Tabelle wird als unregelmaessig markiert - keine erfundene Gruppe.
    """
    if not table.header_bands:
        return

    def set_span(band: HeaderBand, start: int, end: int, basis: str) -> None:
        if start > end:
            start, end = end, start
        band.col_start = max(0, start)
        band.col_end = min(len(table.columns) - 1, end)
        band.basis = basis

    levels = sorted({b.level for b in table.header_bands})
    leaf_level = levels[-1]
    leaf_bands = [b for b in table.header_bands if b.level == leaf_level]
    # Doppelte Anker auf der Blaetterebene sind ein Layoutfehler der Quelle
    # (zwei Kopfzellen auf derselben x-Position). Der erste bleibt, der zweite
    # wird als unregelmaessig notiert - keine erfundene Spalte.
    seen_anchors: set = set()
    unique_leaf: List[HeaderBand] = []
    for band in leaf_bands:
        if band.anchor in seen_anchors:
            table.irregularities.append(f"header_doppelter_anker:{band.text}")
            continue
        seen_anchors.add(band.anchor)
        unique_leaf.append(band)
    leaf_bands = unique_leaf
    leaf_anchors = sorted(b.anchor for b in leaf_bands if b.anchor >= 0)
    if not leaf_anchors:
        return
    leaf_min, leaf_max = leaf_anchors[0], leaf_anchors[-1]

    for band in leaf_bands:
        set_span(band, band.anchor, band.anchor, "blatt")

    # Wiederholungsperiode der Blattkoepfe: 'chi SD chi SD chi SD' hat die
    # Periode 2 und damit drei Wertgruppen. Das ist die verlaesslichere
    # Gruppengroesse als die x-Position der Gruppentexte.
    period = _leaf_period([b.text for b in leaf_bands])
    groups = None
    if period and period < (leaf_max - leaf_min + 1):
        if (leaf_max - leaf_min + 1) % period == 0:
            groups = (leaf_max - leaf_min + 1) // period

    parents: List[Tuple[int, int]] = [(leaf_min, leaf_max)]
    for level in levels[:-1]:
        bands = [b for b in table.header_bands if b.level == level]
        inside = sorted(
            (b for b in bands if leaf_min <= b.anchor <= leaf_max),
            key=lambda b: b.anchor,
        )
        outside = [b for b in bands if not (leaf_min <= b.anchor <= leaf_max)]
        next_parents: List[Tuple[int, int]] = []

        for parent_start, parent_end in parents:
            group = [b for b in inside if parent_start <= b.anchor <= parent_end]
            if not group:
                next_parents.append((parent_start, parent_end))
                continue
            width = parent_end - parent_start + 1
            is_root = (parent_start, parent_end) == (leaf_min, leaf_max)
            if groups and is_root and len(inside) == groups:
                # Periodenregel: jede Gruppenzeile deckt eine Wertperiode ab.
                for position, band in enumerate(group):
                    start = leaf_min + position * period
                    set_span(band, start, start + period - 1, "periode")
                    next_parents.append((start, start + period - 1))
                continue
            if width % len(group) == 0:
                size = width // len(group)
                for position, band in enumerate(group):
                    start = parent_start + position * size
                    set_span(band, start, start + size - 1, "gleichverteilung")
                    next_parents.append((start, start + size - 1))
                continue
            if groups and is_root and len(inside) > groups:
                # Mehr Gruppenzeilen als Wertgruppen: die ueberzaehligen
                # gehoeren zu Einzelspalten ausserhalb des Blaetterbereichs
                # (typisch eine P-Wert-Spalte).
                for position, band in enumerate(inside[:groups]):
                    start = leaf_min + position * period
                    set_span(band, start, start + period - 1, "periode")
                    next_parents.append((start, start + period - 1))
                spare = [c for c in range(len(table.columns)) if c > leaf_max] + [
                    c for c in range(len(table.columns)) if c < leaf_min
                ]
                for band, col in zip(inside[groups:], spare):
                    set_span(band, col, col, "einzelspalte")
                    next_parents.append((col, col))
                for band in inside[groups + len(spare):]:
                    set_span(band, band.anchor, band.anchor, "einzelspalte")
                if len(inside) - groups > len(spare):
                    table.irregularities.append(
                        f"header_ueberzaehlig_ohne_spalte:ebene{level}"
                    )
                continue
            # Keine belegte Teilung: einspaltig und als unregelmaessig notieren.
            table.irregularities.append(f"header_gruppe_nicht_teilbar:ebene{level}")
            for band in group:
                set_span(band, band.anchor, band.anchor, "einzelspalte")
                next_parents.append((band.anchor, band.anchor))

        for band in outside:
            set_span(band, band.anchor, band.anchor, "ausserhalb")
            next_parents.append((band.anchor, band.anchor))
        parents = next_parents

    _deoverlap_levels(table)


def _deoverlap_levels(table: Table) -> None:
    """Ueberlappende Kopfzellen einer Ebene auf freie Spalten schieben.

    In PDF-Abzuegen stehen Kopfzellen oft an derselben x-Position, obwohl sie
    verschiedene Spalten meinen. Eine Ueberlappung wuerde den Header-Pfad einer
    Spalte mit zwei Geschwistern fuellen - der Kontext waere falsch. Deshalb
    bekommt die zweite Zelle die naechste freie Spalte; ohne freie Spalte
    bleibt sie einspaltig und die Tabelle gilt als unregelmaessig.
    """
    for level in sorted({b.level for b in table.header_bands}):
        bands = sorted(
            (b for b in table.header_bands if b.level == level),
            key=lambda b: (b.col_start, b.anchor, b.text),
        )
        used: set = set()
        for band in bands:
            span = set(range(band.col_start, band.col_end + 1))
            if not (span & used):
                used |= span
                continue
            free = next(
                (col for col in range(band.anchor, len(table.columns)) if col not in used),
                None,
            )
            if free is None:
                free = next(
                    (col for col in range(len(table.columns)) if col not in used), None
                )
            if free is None:
                table.irregularities.append(f"header_ohne_spalte:{band.text}")
                band.col_start = band.col_end = band.anchor
                continue
            band.col_start = band.col_end = free
            band.basis = "verschoben"
            used.add(free)


def _leaf_period(texts: Sequence[str]) -> Optional[int]:
    """Kleinste Wiederholungsperiode der Blattkoepfe (sonst None)."""
    def normalise(text: str) -> str:
        return re.sub(r"[^a-z0-9%]", "", (text or "").lower())

    values = [normalise(t) for t in texts]
    if len(values) < 2:
        return None
    for period in range(1, len(values)):
        if all(values[i] == values[i + period] for i in range(len(values) - period)):
            return period
    return None


def _nearest(span: Tuple[int, int], intervals: Sequence[Tuple[int, int]]) -> Optional[int]:
    if not intervals:
        return None
    center = (span[0] + span[1]) / 2
    best = None
    best_distance = None
    for idx, (i_start, i_end) in enumerate(intervals):
        distance = 0.0 if i_start <= center <= i_end else min(
            abs(center - i_start), abs(center - i_end)
        )
        if best_distance is None or distance < best_distance:
            best, best_distance = idx, distance
    return best


_HEADER_CELL_MAX_WORDS = 4


def _looks_like_header_row(line: str) -> bool:
    """Zeile aus mehreren kurzen Zellen - ein Tabellenkopf, keine Prosa.

    ``Time point  Fruit (pieces)  Vegetables (grams)  ...`` traegt viele
    Woerter, aber keine Satzstruktur: jede Zelle bleibt kurz. Ohne diese
    Ausnahme verwirft ``_looks_prose`` die Outcome-Kopfzeile, und die Spalten
    verlieren ihren Outcome-Namen (belegt: ``PMC4319071:T2``).
    """
    cells = split_cells(line)
    if len(cells) < 3:
        return False
    return all(
        len(_WORD_RE.findall(text)) <= _HEADER_CELL_MAX_WORDS
        for _start, _end, text in cells
    )


def _looks_prose(line: str) -> bool:
    stripped = (line or "").strip()
    if len(stripped) < 90:
        return False
    if _looks_like_header_row(stripped):
        return False
    return len(_WORD_RE.findall(stripped)) >= 10 and len(_DIGIT_RE.findall(stripped)) <= 3


def _is_subheader(cells: Sequence[Tuple[int, int, str]]) -> bool:
    """Header-Zeile: kurze Zellen, wenige Ziffern, keine reinen Zahlwerte.

    Eine Zeile mit ``9.5`` ist eine Datenzeile, auch wenn sie nur zwei Ziffern
    traegt; ein Spaltenkopf (``chi``, ``SD``, ``n = 30``) ist keine Zahl.
    """
    if len(cells) < 2:
        return False
    for _s, _e, text in cells:
        if len(text) > 40:
            return False
        if len(_DIGIT_RE.findall(text)) > 2:
            return False
        if parse_value(text) is not None or _PERCENT_RE.match(text.strip()):
            return False
    return True


def _line_offsets(text: str) -> Tuple[List[str], List[int]]:
    lines = text.splitlines()
    starts: List[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    return lines, starts


def _include_wrapper(lines: Sequence[str], fence_index: int) -> int:
    """Optionale ``::::table-wrap``-Klammer vor dem Caption-Block mitnehmen."""
    previous = fence_index - 1
    while previous >= 0 and not lines[previous].strip():
        previous -= 1
    if previous >= 0 and lines[previous].strip().startswith("::::"):
        return previous
    return fence_index


def _walk_back_to_caption(
    lines: Sequence[str], start_index: int
) -> Tuple[str, int, Tuple[int, int]]:
    """Caption oberhalb der Header-Zeilen suchen.

    Erkannt werden der Pandoc-Block (``::: caption`` + Text + ``:::``) und
    eine Zeile, die mit ``Table N`` beginnt. Sonst bleibt die Caption leer -
    eine erfundene Caption waere schlimmer als keine.
    """
    i = start_index - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0:
        return "", start_index, (-1, -1)
    if re.fullmatch(r"\s*:+\s*", lines[i] or ""):
        parts: List[str] = []
        j = i - 1
        while j >= 0 and not _FENCE_RE.match(lines[j]):
            if lines[j].strip():
                parts.append(lines[j].strip())
            j -= 1
        if j >= 0:
            caption = " ".join(reversed(parts)).strip()
            return caption, _include_wrapper(lines, j), (_include_wrapper(lines, j), i)
        return "", start_index, (-1, -1)
    stripped = lines[i].strip()
    if _CAPTION_HINT_RE.match(stripped):
        return stripped, i, (i, i)
    if stripped.startswith(":") and "caption" in stripped.lower():
        j = i - 1
        parts = []
        while j >= 0 and not _FENCE_RE.match(lines[j]):
            if lines[j].strip():
                parts.append(lines[j].strip())
            j -= 1
        return " ".join(reversed(parts)).strip(), max(j, 0), (max(j, 0), i)
    return "", start_index, (-1, -1)


def _collect_footnotes(
    lines: Sequence[str], starts: Sequence[int], body_end: int, limit_lines: int = 18
) -> Tuple[List[Footnote], str]:
    """Fussnoten unterhalb des Tabellenkoerpers sammeln (bis zur naechsten Tabelle)."""
    collected: List[str] = []
    i = body_end
    total = 0
    while i < len(lines) and len(collected) < limit_lines:
        line = lines[i]
        stripped = line.strip()
        if _FENCE_RE.match(line) or _RULE_RE.match(line):
            break
        if _CAPTION_HINT_RE.match(stripped):
            break
        if not stripped:
            if collected and total > 400:
                break
            i += 1
            continue
        if _looks_prose(line) and not collected:
            # Zwischen Koerper und Fussnoten steht oft ein Ergebnisabsatz.
            i += 1
            total += len(line)
            if total > 1200:
                break
            continue
        collected.append(stripped)
        total += len(line)
        i += 1
        if total > 1200:
            break
    footnotes: List[Footnote] = []
    for line in collected:
        match = _FOOTNOTE_MARK_RE.match(line)
        if match or re.match(r"^\s*n\s*=", line, re.IGNORECASE):
            footnotes.append(
                Footnote(text=line, marker=(match.group(1) if match else ""), line=-1)
            )
    return footnotes, "\n".join(collected)


class _Builder:
    """Baut aus Header-Zeilen und Datenzeilen eine Table."""

    def __init__(self, doc_id: str, index: int, intervals: List[Tuple[int, int]],
                 parser: str):
        self.doc_id = doc_id
        self.index = index
        self.intervals = intervals
        self.parser = parser

    # -- Header -----------------------------------------------------------
    def header_band(self, line: str, level: int, line_no: int,
                    cells: Sequence[Tuple[int, int, str]],
                    line_start: int = 0) -> List[HeaderBand]:
        """Header-Zellen mit Ankerspalte; die Spanne kommt spaeter.

        Ein Header-Text steht in PDF-Abzuegen nicht zwingend mittig ueber
        seiner Gruppe ("White Grape Juice n = 30" beginnt in der Spalte des
        Nachbararms). Deshalb wird hier nur die Ankerspalte bestimmt; die
        Gruppenbreite loest ``_resolve_header_spans`` aus der Verschachtelung
        der Header-Ebenen auf.
        """
        bands: List[HeaderBand] = []
        for (start, end, text) in cells:
            anchor = _anchor_column((start, end), self.intervals)
            if anchor is None:
                continue
            bands.append(
                HeaderBand(
                    level=level,
                    text=text,
                    col_start=anchor,
                    col_end=anchor,
                    anchor=anchor,
                    start_char=line_start + start,
                    end_char=line_start + end,
                    line=line_no,
                )
            )
        return bands

    # -- Datenzeilen ------------------------------------------------------
    def data_row(self, line: str, line_no: int, start_char: int,
                 cells: Sequence[Tuple[int, int, str]], row_id: int,
                 label_cols: Iterable[int]) -> Row:
        row = Row(row_id=row_id, index=row_id, line=line_no,
                  start_char=start_char, end_char=start_char + len(line))
        used: Dict[int, Cell] = {}
        label_set = set(label_cols)
        for (start, end, text) in cells:
            span = (start, end)
            col_id = _anchor_column(span, self.intervals)
            if col_id is None:
                continue
            mapping = "overlap"
            if not _covered(span, [(self.intervals[col_id])]):
                mapping = "nearest"
            strong = [
                idx for idx, (i_start, i_end) in enumerate(self.intervals)
                if (min(i_end, span[1]) - max(i_start, span[0]))
                >= 0.5 * max(span[1] - span[0], 1)
            ]
            if len(strong) > 1:
                # Eine Datenzelle ueber zwei Spalten: die Zeile ist unregelmaessig.
                row.irregular = True
            if col_id in used:
                row.irregular = True
                continue
            cell = Cell(
                row_id=row_id,
                col_id=col_id,
                text=text,
                value=_cell_value(text, col_id in label_set),
                line=line_no,
                start_char=start_char + start,
                end_char=start_char + end,
                x_start=start,
                x_end=end,
                col_span=1,
                mapping=mapping,
            )
            used[col_id] = cell
        row.cells = used
        return row


def _cell_value(text: str, is_label: bool) -> Optional[float]:
    """Zahlenwert einer Zelle; Verbundwerte tragen den ersten Wert.

    ``12.4 (3.1)`` ist ein Messwert mit Streuung in Klammern. Der erste Wert
    ist der Zellwert; der zweite wird beim Rekonstruieren als eigener Beleg
    mit derselben Fundstelle gefuehrt. Ohne diese Regel bliebe die ganze
    Zelle wertlos.
    """
    if is_label:
        return None
    parsed = parse_value(text)
    if isinstance(parsed, (int, float)):
        return float(parsed)
    if parsed is not None and getattr(parsed, "value", None) is not None:
        return float(parsed.value)
    numbers = _NUMBER_RE.findall(text or "")
    if len(numbers) >= 2:
        first = parse_value(numbers[0])
        if isinstance(first, (int, float)):
            return float(first)
        if first is not None and getattr(first, "value", None) is not None:
            return float(first.value)
    return None


def _label_columns(table: Table) -> List[int]:
    """Spalten ohne Zahlen: die Zeilenlabels.

    Zwei deterministische Kriterien, beide an den Daten gemessen:

    1. In mindestens 60 Prozent der gefuellten Zellen steht keine Ziffer
       (Textspalte).
    2. Fuehrende Spalte (Rand 0/1) ohne Header, deren Zellen sich ueberwiegend
       nicht als Zahl lesen lassen. Zeitpunkt- und Gruppenzellen wie
       ``Visit 5:`` oder ``5 min`` enthalten Ziffern, sind aber Labels; die
       Ziffernregel allein wuerde sie als Daten spenden.
    """
    label_cols: List[int] = []
    leading = {c.col_id for c in table.columns[:2]}
    for column in table.columns:
        filled = 0
        texty = 0
        strong = 0
        for row in table.rows:
            cell = row.cells.get(column.col_id)
            if not cell or not cell.text.strip():
                continue
            filled += 1
            if not _DIGIT_RE.search(cell.text):
                texty += 1
            if _looks_numeric(cell.text):
                strong += 1
        if not filled:
            continue
        if texty / filled >= 0.6:
            label_cols.append(column.col_id)
            continue
        if (column.col_id in leading and not (column.header or "").strip()
                and strong / filled < 0.5):
            label_cols.append(column.col_id)
    return label_cols


def _looks_numeric(text: str) -> bool:
    """Traegt die Zelle einen echten Messwert (nicht nur eine Ordnungszahl)?

    ``5 min`` und ``Visit 5:`` sind Text mit Ziffer; ``12.4``, ``12,4`` und
    ``12.4 (3.1)`` sind Werte. Kriterium: Dezimalzahl oder zwei Zahlen in einer
    Zelle - das trennt Zeitpunkt- und Gruppenzellen von Messwerten.
    """
    stripped = text.strip().strip("*^")
    if _PLAIN_NUMBER_RE.match(stripped) or _DECIMAL_RE.search(stripped):
        return True
    if len(_NUMBER_RE.findall(stripped)) >= 2:
        return True
    parsed = parse_value(stripped)
    if isinstance(parsed, (int, float)):
        return True
        return parsed is not None and getattr(parsed, "value", None) is not None


def _candidate_header_bands(table: Table) -> Optional[List[HeaderBand]]:
    """Kandidat der ordinalen Kopfzuordnung; ``None`` = kein Kandidat.

    Die Kandidaten werden nur berechnet, nie angewendet: ob einer die gedruckte
    Geometrie ersetzen darf, entscheidet ``semantics.enrich_table`` anhand von
    Ueberlappungen, Feldverlust und Spaltenzuordnung.

    Zwei Alternativen, beste zuerst:

    1. ``ordnung_mit_gedruckten_ebenen``: teilbare Ebenen werden neu verteilt,
       nicht teilbare behalten ihre gedruckte Spanne.
    2. ``ordnung_ohne_unteilbare_ebenen``: nicht teilbare Ebenen entfallen
       (das entspricht der Zuordnung aus Sprint 38, die ``PMC4319071:T2``
       den exakten Wert liefert).

    Welche Variante gilt, entscheidet die Validierung - nicht der Studienname.
    """
    if not any(
        code in irregularity
        for irregularity in table.irregularities
        for code in HEADER_GEOMETRY_CODES
    ):
        return None
    if len(table.columns) < 3 or not table.header_bands:
        return None
    numeric = {
        column.col_id
        for column in table.columns
        if any(
            row.cells.get(column.col_id) is not None
            and row.cells[column.col_id].value is not None
            for row in table.rows
        )
    }
    value_cols = sorted(numeric)
    label_cols = [column.col_id for column in table.columns if column.col_id not in numeric]
    if len(value_cols) < 2 or not label_cols:
        return None

    def build(keep_unplaced: bool) -> Tuple[List[HeaderBand], bool]:
        kept: List[HeaderBand] = []
        changed = False
        for level in sorted({band.level for band in table.header_bands}):
            bands = sorted(
                (band for band in table.header_bands if band.level == level),
                key=lambda band: (band.anchor, band.start_char),
            )
            m = len(bands)
            spans: List[Tuple[int, int]] = []
            if m == len(value_cols):
                spans = [(col, col) for col in value_cols]
            elif m > 1 and len(value_cols) % (m - 1) == 0:
                size = len(value_cols) // (m - 1)
                spans = [(label_cols[0], label_cols[-1])] + [
                    (value_cols[position * size], value_cols[position * size + size - 1])
                    for position in range(m - 1)
                ]
            elif keep_unplaced:
                kept.extend(dc_replace(band) for band in bands)
                continue
            else:
                continue
            for band, (start, end) in zip(bands, spans):
                kept.append(
                    dc_replace(band, col_start=start, col_end=end, anchor=start,
                               basis="ordnung")
                )
                changed = True
        return kept, changed

    candidates: List[Tuple[str, List[HeaderBand]]] = []
    for name, keep in (("ordnung_mit_gedruckten_ebenen", True),
                       ("ordnung_ohne_unteilbare_ebenen", False)):
        bands, changed = build(keep)
        if changed and bands:
            candidates.append((name, bands))
    return candidates


def _header_band_candidates(table: Table) -> List[Tuple[str, List[HeaderBand]]]:
    """Wie ``_candidate_header_bands``, aber immer eine Liste."""
    return _candidate_header_bands(table) or []


def _finish_table(table: Table) -> Table:
    """Rollen, Labels, Vererbung leerer Zeilenlabels, Irregularitaeten."""
    label_cols = _label_columns(table)
    if not label_cols and table.columns:
        # Ohne Textspalte gibt es kein Zeilenlabel; Spalte 0 bleibt dann
        # Numerik und die Tabelle wird als unregelmaessig markiert.
        table.irregularities.append("keine_label_spalte")
    for column in table.columns:
        column.role = ROLE_LABEL if column.col_id in label_cols else column.role
    if label_cols:
        first_label = min(label_cols)
        previous_label = ""
        previous_row_id: Optional[int] = None
        for row in table.rows:
            cell = row.cells.get(first_label)
            text = (cell.text.strip() if cell else "")
            if not text:
                row.label = previous_label
                if cell is not None:
                    cell.inherited_from_row = previous_row_id
                elif previous_row_id is not None:
                    # Label-Zelle fehlt ganz: Vererbung dokumentieren, ohne
                    # eine Zelle zu erfinden.
                    row.cells[first_label] = Cell(
                        row_id=row.row_id,
                        col_id=first_label,
                        text="",
                        value=None,
                        line=row.line,
                        start_char=row.start_char,
                        end_char=row.start_char,
                        inherited_from_row=previous_row_id,
                    )
            else:
                row.label = text
                previous_label = text
                previous_row_id = row.row_id

    # Zeilenpfad: Gruppenlabels (fette Zeilen) plus eigenes Label. Erst der
    # Pfad macht eine Zeile eindeutig; ``Mean (SD)`` allein nennt kein Outcome.
    ordered_labels = sorted(label_cols)
    stack: List[Tuple[int, str]] = []
    for row in table.rows:
        if row.group_label:
            # Die Spalte des Gruppenlabels zeigt seine Tiefe: gleiche Spalte =
            # Geschwister (``Background characteristics`` / ``Dietary intake``),
            # weiter rechts = Untergruppe (``Vegetable intake``).
            col_id = next(
                (col for col, cell in sorted(row.cells.items())
                 if (cell.text or "").strip()),
                0,
            )
            while stack and stack[-1][0] >= col_id:
                stack.pop()
            stack.append((col_id, row.group_label))
            row.label_path = tuple(text for _col, text in stack)
            continue
        specific = ""
        for col_id in ordered_labels:
            cell = row.cells.get(col_id)
            if cell is None or cell.inherited_from_row is not None:
                continue
            text = (cell.text or "").strip()
            if text:
                specific = _plain_label(text)
                break
        path = [text for _col, text in stack]
        if specific:
            path.append(specific)
        elif (row.label or "").strip():
            path.append(_plain_label(row.label))
        row.label_path = tuple(path)
    return table


def _parse_rule_table(
    lines: Sequence[str], starts: Sequence[int], rule_index: int,
    doc_id: str, table_index: int, page_of_offset: Optional[Callable[[int], Optional[int]]],
) -> Optional[Table]:
    intervals = rule_intervals(lines[rule_index])
    if len(intervals) < 2:
        return None
    builder = _Builder(doc_id, table_index, intervals, "pandoc-rule/1")

    # Header oberhalb der Regel (maximal 4 Zeilen)
    header_lines: List[int] = []
    j = rule_index - 1
    while j >= 0 and rule_index - j <= 4 and lines[j].strip():
        if _FENCE_RE.match(lines[j]) or _CAPTION_HINT_RE.match(lines[j]):
            break
        if _looks_prose(lines[j]):
            break
        cells = split_cells(lines[j])
        if len(cells) < 2:
            break
        if _is_row_label_header(cells):
            break
        header_lines.insert(0, j)
        j -= 1

    caption, caption_index, caption_span = _walk_back_to_caption(
        lines, header_lines[0] if header_lines else rule_index
    )

    # Koerper unterhalb der Regel. ``kind`` ist ``header``, ``data`` oder
    # ``group`` (fette Zeilengruppe ohne Werte).
    body_lines: List[Tuple[int, str, List[Tuple[int, int, str]], str]] = []
    skipped_header_lines: List[int] = []
    i = rule_index + 1
    data_seen = 0
    blanks = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if _FENCE_RE.match(line) or _RULE_RE.match(line):
            break
        if _CAPTION_HINT_RE.match(stripped):
            break
        if not stripped:
            blanks += 1
            if data_seen and blanks >= 2:
                break
            i += 1
            continue
        blanks = 0
        cells = split_cells(line)
        if len(cells) < 2:
            if _is_group_label_row(line, cells):
                # Fette Zeilengruppe: gehoert zum Koerper, nicht zum Tabellenende.
                body_lines.append((i, line, cells, "group"))
                data_seen += 1
                i += 1
                continue
            if data_seen:
                break
            i += 1
            continue
        if _looks_prose(line) and data_seen:
            break
        is_header = _is_subheader(cells)
        if is_header and _is_row_label_header(cells):
            # Kopfzeile mit Zeilenlabels (Vergleichszeilen): nicht als
            # Spaltenkopf lesen, sonst bekommt die erste Spalte einen falschen
            # Arm. Die Zeile traegt keine Zahlen und wird nur notiert.
            skipped_header_lines.append(i)
            i += 1
            continue
        if is_header and data_seen:
            # Header nach Datenzeilen ist kein Header mehr - Tabelle endet.
            break
        body_lines.append((i, line, cells, "header" if is_header else "data"))
        if not is_header:
            data_seen += 1
        i += 1

    if not body_lines:
        return None

    table = Table(
        table_id=f"{doc_id}:T{table_index}",
        doc_id=doc_id,
        index=table_index,
        caption=caption,
        page=None,
        parser=builder.parser,
        line_start=(caption_index if caption else (header_lines[0] if header_lines else rule_index)),
        line_end=body_lines[-1][0],
        char_start=starts[max(caption_index if caption else (header_lines[0] if header_lines else rule_index), 0)],
        char_end=starts[body_lines[-1][0]] + len(lines[body_lines[-1][0]]),
        caption_char_span=(starts[caption_span[0]], starts[caption_span[1]] + len(lines[caption_span[1]])) if caption_span[0] >= 0 else (-1, -1),
    )
    table.columns = [
        Column(col_id=idx, x_start=start, x_end=end)
        for idx, (start, end) in enumerate(intervals)
    ]

    level = 0
    for line_no in header_lines:
        bands = builder.header_band(lines[line_no], level, line_no,
                                    split_cells(lines[line_no]), starts[line_no])
        table.header_bands.extend(bands)
        level += 1

    row_id = 0
    for line_no, line, cells, kind in body_lines:
        if kind == "header":
            bands = builder.header_band(line, level, line_no, cells, starts[line_no])
            table.header_bands.extend(bands)
            level += 1
            continue
        row = builder.data_row(line, line_no, starts[line_no], cells, row_id, [])
        if kind == "group" and cells:
            row.group_label = _plain_label(cells[0][2])
        table.rows.append(row)
        row_id += 1

    _resolve_header_spans(table)
    table.header_band_candidates = _header_band_candidates(table)
    table = _finish_table(table)
    footnotes, block = _collect_footnotes(lines, starts, body_lines[-1][0] + 1)
    table.footnotes = footnotes
    table.footnote_block = block
    units: List[str] = []
    for match in re.finditer(r"\(([^()]{1,18})\)", caption):
        token = match.group(1).strip()
        if token and not token.isdigit():
            units.append(token)
    table.units = units
    if page_of_offset:
        try:
            table.page = page_of_offset(table.char_start)
        except Exception:
            table.page = None
    for row in table.rows:
        if row.irregular:
            table.irregularities.append(f"unregelmaessige_zeile:{row.row_id}")
    for line_no in skipped_header_lines:
        table.irregularities.append(f"kopfzeile_ist_zeilenlabel:{line_no}")
    return table


def _pipe_cells(line: str) -> List[Tuple[int, int, str]]:
    cells: List[Tuple[int, int, str]] = []
    for match in re.finditer(r"([^|]+)", line):
        text = match.group(1).strip()
        if text:
            cells.append((match.start(1), match.end(1), text))
    return cells


def _parse_pipe_table(
    lines: Sequence[str], starts: Sequence[int], header_index: int,
    doc_id: str, table_index: int,
    page_of_offset: Optional[Callable[[int], Optional[int]]],
) -> Optional[Table]:
    """Pandoc-Pipetabelle: Kopfzeilen, Trennzeile, Datenzeilen."""
    header_lines: List[int] = []
    i = header_index
    while i < len(lines) and lines[i].strip().startswith("|") and not _PIPE_SEP_RE.match(lines[i]):
        header_lines.append(i)
        i += 1
    if i >= len(lines) or not _PIPE_SEP_RE.match(lines[i]):
        return None
    separator = i
    body: List[int] = []
    i = separator + 1
    while i < len(lines) and lines[i].strip().startswith("|"):
        body.append(i)
        i += 1
    if not body:
        return None

    header_cells = _pipe_cells(lines[header_lines[-1]]) if header_lines else _pipe_cells(lines[separator])
    if len(header_cells) < 2:
        return None
    intervals: List[Tuple[int, int]] = []
    for idx, (start, end, _text) in enumerate(header_cells):
        right = (header_cells[idx + 1][0] - 1) if idx + 1 < len(header_cells) else end
        intervals.append((start, max(right, end)))

    builder = _Builder(doc_id, table_index, intervals, "pipe/1")
    caption, caption_index, caption_span = _walk_back_to_caption(lines, header_lines[0])
    table = Table(
        table_id=f"{doc_id}:T{table_index}",
        doc_id=doc_id,
        index=table_index,
        caption=caption,
        parser="pipe/1",
        line_start=caption_index if caption else header_lines[0],
        line_end=body[-1],
        char_start=starts[caption_index if caption else header_lines[0]],
        char_end=starts[body[-1]] + len(lines[body[-1]]),
        caption_char_span=(starts[caption_span[0]], starts[caption_span[1]] + len(lines[caption_span[1]])) if caption_span[0] >= 0 else (-1, -1),
    )
    table.columns = [
        Column(col_id=idx, x_start=start, x_end=end) for idx, (start, end) in enumerate(intervals)
    ]
    for level, line_no in enumerate(header_lines):
        cells = _pipe_cells(lines[line_no])
        bands = builder.header_band(lines[line_no], level, line_no, cells, starts[line_no])
        table.header_bands.extend(bands)
    row_id = 0
    for line_no in body:
        row = builder.data_row(lines[line_no], line_no, starts[line_no],
                               _pipe_cells(lines[line_no]), row_id, [])
        table.rows.append(row)
        row_id += 1
    _resolve_header_spans(table)
    table.header_band_candidates = _header_band_candidates(table)
    table = _finish_table(table)
    footnotes, block = _collect_footnotes(lines, starts, body[-1] + 1)
    table.footnotes, table.footnote_block = footnotes, block
    if page_of_offset:
        try:
            table.page = page_of_offset(table.char_start)
        except Exception:
            table.page = None
    return table


def _cluster_intervals(
    line_cells: Sequence[Sequence[Tuple[int, int, str]]], tolerance: int = 2
) -> List[Tuple[int, int]]:
    """Spaltenintervalle aus den Zellpositionen mehrerer Zeilen clustern."""
    starts = sorted({cell[0] for cells in line_cells for cell in cells})
    if len(starts) < 2:
        return []
    clusters: List[List[int]] = [[starts[0]]]
    for start in starts[1:]:
        if start - clusters[-1][-1] <= tolerance:
            clusters[-1].append(start)
        else:
            clusters.append([start])
    if len(clusters) < 2:
        return []
    boundaries = [min(cluster) for cluster in clusters]
    intervals: List[Tuple[int, int]] = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] - 1 if idx + 1 < len(boundaries) else max(
            cell[1] for cells in line_cells for cell in cells
        )
        intervals.append((start, end))
    return intervals


def _parse_whitespace_table(
    lines: Sequence[str], starts: Sequence[int], caption_index: int,
    doc_id: str, table_index: int,
    page_of_offset: Optional[Callable[[int], Optional[int]]],
) -> Optional[Table]:
    """Caption plus spaltenweise gesetzter Text ohne Strichregel."""
    candidate_lines: List[int] = []
    i = caption_index + 1
    while i < len(lines) and len(candidate_lines) < 40:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            if candidate_lines:
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if not nxt.strip() or _CAPTION_HINT_RE.match(nxt.strip()):
                    break
            i += 1
            continue
        if _FENCE_RE.match(line) or _RULE_RE.match(line) or _CAPTION_HINT_RE.match(stripped):
            break
        if _looks_prose(line) and candidate_lines:
            break
        if len(split_cells(line)) >= 2:
            candidate_lines.append(i)
        elif candidate_lines:
            break
        i += 1
    if len(candidate_lines) < 3:
        return None
    line_cells = [split_cells(lines[idx]) for idx in candidate_lines]
    numeric_lines = sum(
        1 for cells in line_cells if any(parse_value(text) is not None for _s, _e, text in cells)
    )
    if numeric_lines < 2:
        return None
    intervals = _cluster_intervals(line_cells)
    if len(intervals) < 2:
        return None
    builder = _Builder(doc_id, table_index, intervals, "whitespace/1")
    caption = lines[caption_index].strip()
    table = Table(
        table_id=f"{doc_id}:T{table_index}",
        doc_id=doc_id,
        index=table_index,
        caption=caption,
        parser="whitespace/1",
        line_start=caption_index,
        line_end=candidate_lines[-1],
        char_start=starts[caption_index],
        char_end=starts[candidate_lines[-1]] + len(lines[candidate_lines[-1]]),
        caption_char_span=(starts[caption_index],
                           starts[caption_index] + len(lines[caption_index])),
    )
    table.columns = [
        Column(col_id=idx, x_start=start, x_end=end) for idx, (start, end) in enumerate(intervals)
    ]
    level = 0
    row_id = 0
    for idx in candidate_lines:
        cells = split_cells(lines[idx])
        if _is_subheader(cells):
            table.header_bands.extend(
                builder.header_band(lines[idx], level, idx, cells, starts[idx])
            )
            level += 1
            continue
        table.rows.append(
            builder.data_row(lines[idx], idx, starts[idx], cells, row_id, [])
        )
        row_id += 1
    if not table.rows:
        return None
    _resolve_header_spans(table)
    table.header_band_candidates = _header_band_candidates(table)
    table = _finish_table(table)
    footnotes, block = _collect_footnotes(lines, starts, candidate_lines[-1] + 1)
    table.footnotes, table.footnote_block = footnotes, block
    if page_of_offset:
        try:
            table.page = page_of_offset(table.char_start)
        except Exception:
            table.page = None
    return table


def _assigned_lines(tables: Sequence[Table], lines: Sequence[str]) -> set:
    used: set = set()
    for table in tables:
        if table.line_start >= 0:
            used.update(range(table.line_start, table.line_end + 1))
    return used


def parse_document(
    text: str,
    doc_id: str,
    page_of_offset: Optional[Callable[[int], Optional[int]]] = None,
    include_whitespace_fallback: bool = True,
) -> DocumentTables:
    """Alle Tabellen eines Dokumenttextes parsen (deterministisch, ohne Modell)."""
    lines, starts = _line_offsets(text)
    tables: List[Table] = []
    used: set = set()

    for index, line in enumerate(lines):
        if index in used or not _RULE_RE.match(line):
            continue
        if _PIPE_SEP_RE.match(line):
            continue
        table = _parse_rule_table(lines, starts, index, doc_id, len(tables) + 1, page_of_offset)
        if table is None:
            continue
        tables.append(table)
        used.update(range(table.line_start, table.line_end + 1))

    for index, line in enumerate(lines):
        if index in used or not _PIPE_SEP_RE.match(line):
            continue
        header_index = index - 1
        while header_index >= 0 and lines[header_index].strip().startswith("|"):
            header_index -= 1
        header_index += 1
        if header_index >= index:
            continue
        table = _parse_pipe_table(lines, starts, header_index, doc_id,
                                  len(tables) + 1, page_of_offset)
        if table is None:
            continue
        tables.append(table)
        used.update(range(table.line_start, table.line_end + 1))

    if include_whitespace_fallback:
        for index, line in enumerate(lines):
            if index in used or not _CAPTION_HINT_RE.match(line.strip()):
                continue
            table = _parse_whitespace_table(lines, starts, index, doc_id,
                                            len(tables) + 1, page_of_offset)
            if table is None:
                continue
            tables.append(table)
            used.update(range(table.line_start, table.line_end + 1))

    tables.sort(key=lambda t: t.char_start)
    for position, table in enumerate(tables, start=1):
        table.index = position
        table.table_id = f"{doc_id}:T{position}"
    unresolved = []
    for index, line in enumerate(lines):
        if _RULE_RE.match(line) and index not in used:
            unresolved.append({"line": index, "reason": "regel_ohne_tabelle"})
    return DocumentTables(doc_id=doc_id, tables=tables, unresolved_blocks=unresolved)
