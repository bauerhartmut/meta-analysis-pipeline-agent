"""Automatische Pruefungen fuer Zerlegung und Rekonstruktion.

Zwei getrennte Fragen, zwei getrennte Antworten:

* **Strukturelle Vollstaendigkeit** - wurde jede Zelle des Quelltextes
  abgedeckt, trug jede Einheit ihren vollstaendigen Header-Kontext, Caption und
  Fussnoten, sind die Crops belegt?
* **Inhaltliche Plausibilitaet** - Regelpruefungen auf den gelesenen Werten
  (Ereignisse <= Gruppengroesse, SD gegen Mittelwert, Einheiten konsistent,
  Zitat im Ausschnitt auffindbar).

Ein Modellkonsens ist **kein** Beweis fuer Richtigkeit: stimmen Zeilen- und
Spaltenlesung ueberein, ist das ein Hinweis, keine Validierung gegen die Quelle.
Der Bericht traegt diesen Satz mit, damit die Zahl nicht als Urteil gelesen wird.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .model import ROLE_EVENTS, ROLE_LABEL, ROLE_MEAN, ROLE_SD, Table
from .reconstruct import ReconstructionResult
from .strategies import DIRECTION_COLUMN, DIRECTION_ROW, ExtractionUnit

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

STATUS_COMPLETE = "strukturell_vollstaendig"
STATUS_GAPS = "strukturell_luecken"


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    table_id: str = ""
    row_id: Optional[int] = None
    col_id: Optional[int] = None
    unit_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "table_id": self.table_id,
            "row_id": self.row_id,
            "col_id": self.col_id,
            "unit_id": self.unit_id,
        }


@dataclass
class ValidationReport:
    table_id: str
    status: str = STATUS_GAPS
    findings: List[Finding] = field(default_factory=list)
    structural: Dict[str, Any] = field(default_factory=dict)
    content: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def by_severity(self, severity: str) -> List[Finding]:
        return [f for f in self.findings if f.severity == severity]

    @property
    def errors(self) -> List[Finding]:
        return self.by_severity(SEVERITY_ERROR)

    @property
    def warnings(self) -> List[Finding]:
        return self.by_severity(SEVERITY_WARNING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "status": self.status,
            "structural": dict(self.structural),
            "content": dict(self.content),
            "notes": list(self.notes),
            "findings": [f.to_dict() for f in self.findings],
            "counts": {
                "error": len(self.by_severity(SEVERITY_ERROR)),
                "warning": len(self.by_severity(SEVERITY_WARNING)),
                "info": len(self.by_severity(SEVERITY_INFO)),
            },
        }


def _present_data_cells(table: Table) -> List[Tuple[int, int]]:
    labels = set(table.label_columns)
    cells: List[Tuple[int, int]] = []
    for row in table.rows:
        for col_id, cell in sorted(row.cells.items()):
            if col_id in labels:
                continue
            if (cell.text or "").strip():
                cells.append((row.row_id, col_id))
    return cells


MAX_CELL_FINDINGS = 20


def _check_structure(table: Table, units: Sequence[ExtractionUnit],
                     findings: List[Finding]) -> Dict[str, Any]:
    """Abdeckung im Ausschnitt und Abdeckung der ganzen Tabelle getrennt.

    Eine spaltenweise Zerlegung liest nur Spalten mit belegtem Arm. Das ist
    beabsichtigt, aber es darf nicht als Vollstaendigkeit erscheinen: die
    Zellen ausserhalb des Ausschnitts werden als Zahl ausgewiesen, nicht als
    erledigt. Innerhalb des Ausschnitts muss jede vorhandene Zelle gelesen
    werden - dort ist eine Luecke ein Fehler.
    """
    present = _present_data_cells(table)
    scope_cols = {col_id for unit in units for col_id in unit.col_ids}
    scope_rows = {row_id for unit in units for row_id in unit.row_ids}
    covered: set = set()
    for unit in units:
        covered.update(unit.expected_cells)
    in_scope = [c for c in present if c[1] in scope_cols and c[0] in scope_rows]
    outside = [c for c in present
               if c[1] not in scope_cols or c[0] not in scope_rows]
    missing = [c for c in in_scope if c not in covered]
    coverage = (len(in_scope) - len(missing)) / len(in_scope) if in_scope else 1.0
    coverage_total = (len(present) - len(missing) - len(outside)) / len(present) if present else 1.0
    for row_id, col_id in missing[:MAX_CELL_FINDINGS]:
        findings.append(
            Finding(
                code="zelle_nicht_abgedeckt",
                severity=SEVERITY_ERROR,
                message=(
                    f"Zelle row {row_id}/col {col_id} steht im Quelltext und "
                    "liegt im Ausschnitt, wird aber von keiner Einheit gelesen."
                ),
                table_id=table.table_id,
                row_id=row_id,
                col_id=col_id,
            )
        )
    if len(missing) > MAX_CELL_FINDINGS:
        findings.append(
            Finding(
                code="zelle_nicht_abgedeckt_sammel",
                severity=SEVERITY_ERROR,
                message=(
                    f"{len(missing) - MAX_CELL_FINDINGS} weitere nicht gelesene "
                    "Zellen im Ausschnitt (einzeln aufgelistet bis 20)."
                ),
                table_id=table.table_id,
            )
        )
    if outside:
        findings.append(
            Finding(
                code="zelle_ausserhalb_scope",
                severity=SEVERITY_INFO,
                message=(
                    f"{len(outside)} Zellen ausserhalb des Auftrags (Spalten ohne "
                    f"belegten Arm oder Zeilen ausserhalb der Outcome-Zeile; "
                    f"Spalten {sorted({c[1] for c in outside})}) werden nicht "
                    "gelesen und nicht bewertet."
                ),
                table_id=table.table_id,
            )
        )

    unit_ids = [u.unit_id for u in units]
    if len(unit_ids) != len(set(unit_ids)):
        findings.append(
            Finding(
                code="einheit_id_doppelt",
                severity=SEVERITY_ERROR,
                message="Einheit-IDs sind nicht eindeutig; Belege waeren nicht trennbar.",
                table_id=table.table_id,
            )
        )

    header_gaps = 0
    label_gaps = 0
    for unit in units:
        prompt = unit.prompt or ""
        if table.caption and table.caption not in prompt:
            findings.append(
                Finding(
                    code="caption_fehlt",
                    severity=SEVERITY_ERROR,
                    message="Die Caption steht nicht im Ausschnitt.",
                    table_id=table.table_id,
                    unit_id=unit.unit_id,
                )
            )
        if table.footnote_block.strip() and table.footnote_block.strip() not in prompt:
            findings.append(
                Finding(
                    code="fussnote_fehlt",
                    severity=SEVERITY_WARNING,
                    message="Der Fussnotenblock der Tabelle fehlt im Ausschnitt.",
                    table_id=table.table_id,
                    unit_id=unit.unit_id,
                )
            )
        for col_id in unit.col_ids:
            column = table.column(col_id)
            if column is None:
                findings.append(
                    Finding(
                        code="spalte_unbekannt",
                        severity=SEVERITY_ERROR,
                        message=f"Spalte {col_id} existiert nicht in der Tabelle.",
                        table_id=table.table_id,
                        col_id=col_id,
                        unit_id=unit.unit_id,
                    )
                )
                continue
            for band in table.header_bands:
                if not (band.col_start <= col_id <= band.col_end):
                    continue
                if band.text and band.text not in prompt:
                    header_gaps += 1
                    findings.append(
                        Finding(
                            code="header_kontext_fehlt",
                            severity=SEVERITY_ERROR,
                            message=(
                                f"Header-Text {band.text!r} (Ebene {band.level}) "
                                f"fehlt im Ausschnitt von Spalte {col_id}."
                            ),
                            table_id=table.table_id,
                            col_id=col_id,
                            unit_id=unit.unit_id,
                        )
                    )
            if not column.header_path:
                findings.append(
                    Finding(
                        code="spaltenkopf_fehlt",
                        severity=SEVERITY_WARNING,
                        message=f"Spalte {col_id} hat keinen Header-Pfad.",
                        table_id=table.table_id,
                        col_id=col_id,
                        unit_id=unit.unit_id,
                    )
                )
        for row_id, _col_id in unit.expected_cells:
            row = table.row(row_id)
            if row is not None and not (row.label or "").strip():
                label_gaps += 1
                findings.append(
                    Finding(
                        code="zeilenlabel_fehlt",
                        severity=SEVERITY_WARNING,
                        message=f"Zeile {row_id} hat kein Label; der Wert steht ohne Bezug.",
                        table_id=table.table_id,
                        row_id=row_id,
                        unit_id=unit.unit_id,
                    )
                )

    combined = [c.col_id for c in table.columns if c.secondary_role]
    if combined:
        findings.append(
            Finding(
                code="verbundwert_getrennt",
                severity=SEVERITY_INFO,
                message=(
                    f"Spalten {combined} tragen zwei Zahlen je Zelle; der zweite "
                    "Wert wird als eigener Beleg mit derselben Fundstelle gefuehrt."
                ),
                table_id=table.table_id,
            )
        )

    row_roles = sorted({row.value_role for row in table.rows if row.value_role})
    if row_roles:
        findings.append(
            Finding(
                code="rolle_aus_zeilenlabel",
                severity=SEVERITY_INFO,
                message=(
                    f"Rollen aus Zeilenlabels: {row_roles}. Sie greifen nur, wo "
                    "der Spaltenkopf keine Rolle traegt."
                ),
                table_id=table.table_id,
            )
        )

    row_arms = sorted({row.arm for row in table.rows if getattr(row, "arm", None)})
    if row_arms and not any(c.arm for c in table.columns):
        findings.append(
            Finding(
                code="arm_aus_zeilenlabel",
                severity=SEVERITY_INFO,
                message=(
                    f"Arm aus Zeilenlabels: {row_arms}. Die Spalten tragen das "
                    "Outcome; ohne belegten Outcome-Namen entsteht kein Feld."
                ),
                table_id=table.table_id,
            )
        )

    transferred = [c.col_id for c in table.columns if c.arm_basis == "uebertrag"]
    if transferred:
        findings.append(
            Finding(
                code="armzuordnung_uebertragen",
                severity=SEVERITY_INFO,
                message=(
                    f"Spalten {transferred} haben ihren Arm aus einer Schwestertabelle "
                    "desselben Dokuments (identischer Gruppenkopf)."
                ),
                table_id=table.table_id,
            )
        )

    assumed = [c.col_id for c in table.columns if c.arm_basis == "reihenfolge"]
    if assumed:
        findings.append(
            Finding(
                code="armzuordnung_angenommen",
                severity=SEVERITY_INFO,
                message=(
                    f"Spalten {assumed} haben ihren Arm aus der Leserichtung "
                    "(erste Armspalte = Intervention), nicht aus dem Header. "
                    "Die Annahme ist markiert und pruefpflichtig."
                ),
                table_id=table.table_id,
            )
        )

    # Header-Spannen duerfen sich auf einer Ebene nicht ueberlappen.
    for level in sorted({b.level for b in table.header_bands}):
        bands = sorted(
            (b for b in table.header_bands if b.level == level),
            key=lambda b: b.col_start,
        )
        for left, right in zip(bands, bands[1:]):
            if right.col_start <= left.col_end:
                findings.append(
                    Finding(
                        code="header_span_ueberlappt",
                        severity=SEVERITY_ERROR,
                        message=(
                            f"Header {left.text!r} und {right.text!r} ueberlappen "
                            f"sich auf Ebene {level}."
                        ),
                        table_id=table.table_id,
                    )
                )

    crops_ok = 0
    for unit in units:
        crop = unit.crop
        if crop is None:
            findings.append(
                Finding(
                    code="crop_fehlt",
                    severity=SEVERITY_ERROR,
                    message="Einheit ohne Crop; die Fundstelle ist nicht belegt.",
                    table_id=table.table_id,
                    unit_id=unit.unit_id,
                )
            )
            continue
        if crop.char_start < 0 or crop.char_end <= crop.char_start:
            findings.append(
                Finding(
                    code="crop_spanne_unbelegt",
                    severity=SEVERITY_ERROR,
                    message="Crop ohne gueltige Zeichenspanne.",
                    table_id=table.table_id,
                    unit_id=unit.unit_id,
                )
            )
        else:
            crops_ok += 1
        if not crop.includes_caption and table.caption:
            findings.append(
                Finding(
                    code="crop_ohne_caption",
                    severity=SEVERITY_WARNING,
                    message="Crop umfasst die Caption nicht.",
                    table_id=table.table_id,
                    unit_id=unit.unit_id,
                )
            )

    return {
        "cells_in_source": len(present),
        "cells_in_scope": len(in_scope),
        "cells_covered": len(in_scope) - len(missing),
        "cells_uncovered": len(missing),
        "cells_outside_scope": len(outside),
        "cells_outside_rows": len([c for c in outside if c[0] not in scope_rows]),
        "coverage": round(coverage, 4),
        "coverage_total": round(coverage_total, 4),
        "n_units": len(units),
        "n_units_expected": len(units),
        "header_context_gaps": header_gaps,
        "label_gaps": label_gaps,
        "crops_with_span": crops_ok,
        "caption_in_all_units": all(
            (table.caption in (u.prompt or "")) for u in units
        ) if table.caption else True,
        "footnotes_withheld": bool(
            table.footnote_block.strip()
            and any(table.footnote_block.strip() not in (u.prompt or "") for u in units)
        ),
    }


def _find_cell_value(recon: ReconstructionResult, row_id: int, col_id: int) -> Optional[float]:
    for cell in recon.cells:
        if cell.row_id == row_id and cell.col_id == col_id and cell.value is not None:
            return cell.value
    return None


def _check_content(table: Table, units: Sequence[ExtractionUnit],
                   recon: ReconstructionResult, findings: List[Finding]) -> Dict[str, Any]:
    prompts = {unit.unit_id: unit.prompt or "" for unit in units}
    n_quote_missing = 0
    n_beleg_fehlt = 0
    for cell in recon.cells:
        for evidence in cell.evidence:
            prompt = prompts.get(evidence.unit_id, "")
            raw = (evidence.raw or evidence.quote or "").strip()
            if not raw:
                n_quote_missing += 1
                findings.append(
                    Finding(
                        code="ohne_rohwert",
                        severity=SEVERITY_WARNING,
                        message="Beleg ohne Rohwert; der Originaltext ist nicht nachpruefbar.",
                        table_id=table.table_id,
                        row_id=evidence.row_id,
                        col_id=evidence.col_id,
                        unit_id=evidence.unit_id,
                    )
                )
                continue
            if prompt and raw not in prompt:
                n_beleg_fehlt += 1
                findings.append(
                    Finding(
                        code="beleg_nicht_im_ausschnitt",
                        severity=SEVERITY_ERROR,
                        message=(
                            f"Rohwert {raw!r} steht nicht im Ausschnitt der Einheit; "
                            "die Fundstelle ist nicht belegt."
                        ),
                        table_id=table.table_id,
                        row_id=evidence.row_id,
                        col_id=evidence.col_id,
                        unit_id=evidence.unit_id,
                    )
                )
            if evidence.source_present and evidence.source_value is not None \
                    and evidence.value is not None:
                if abs(evidence.source_value - evidence.value) > 1e-9:
                    findings.append(
                        Finding(
                            code="abweichend_von_quellzelle",
                            severity=SEVERITY_INFO,
                            message=(
                                f"Wert {evidence.value} weicht von der Quellzelle "
                                f"{evidence.source_value} ab (die Quellzelle ist die "
                                "gedruckte Zelle, nicht das Gold)."
                            ),
                            table_id=table.table_id,
                            row_id=evidence.row_id,
                            col_id=evidence.col_id,
                            unit_id=evidence.unit_id,
                        )
                    )

    # Ereignisse <= Gruppengroesse (gleiche Zeile, gleicher Arm).
    n_events_over = 0
    for cell in recon.cells:
        if not cell.field or not cell.field.endswith("_events") or cell.value is None:
            continue
        arm = cell.field[: -len("_events")]
        n_value = _find_cell_value(recon, cell.row_id, _column_of_field(table, f"{arm}_group_size"))
        if n_value is None:
            source_n = _source_group_size(table, cell.row_id, arm)
            n_value = source_n
        if n_value is not None and cell.value > n_value:
            n_events_over += 1
            findings.append(
                Finding(
                    code="ereignisse_ueber_gruppengroesse",
                    severity=SEVERITY_WARNING,
                    message=(
                        f"{cell.field} = {cell.value} ist groesser als die "
                        f"Gruppengroesse {n_value}."
                    ),
                    table_id=table.table_id,
                    row_id=cell.row_id,
                    col_id=cell.col_id,
                )
            )

    # SD gegen Mittelwert: |mean| > 0 und SD > 3*|mean| ist auffaellig.
    n_sd_odd = 0
    for cell in recon.cells:
        if not cell.field or not cell.field.endswith("_standard_deviation"):
            continue
        if cell.value is None or cell.value < 0:
            continue
        arm = cell.field[: -len("_standard_deviation")]
        mean_col = _column_of_field(table, f"{arm}_mean")
        mean_value = _find_cell_value(recon, cell.row_id, mean_col) if mean_col is not None else None
        if mean_value is None or abs(mean_value) < 1e-9:
            continue
        if cell.value > 3 * abs(mean_value):
            n_sd_odd += 1
            findings.append(
                Finding(
                    code="sd_gegen_mittel",
                    severity=SEVERITY_WARNING,
                    message=(
                        f"SD {cell.value} ist mehr als dreimal so gross wie der "
                        f"Mittelwert {mean_value}."
                    ),
                    table_id=table.table_id,
                    row_id=cell.row_id,
                    col_id=cell.col_id,
                )
            )

    # Einheiten je Feld konsistent?
    units_by_field: Dict[str, set] = {}
    for cell in recon.cells:
        if not cell.field:
            continue
        for evidence in cell.evidence:
            if evidence.unit:
                units_by_field.setdefault(cell.field, set()).add(evidence.unit)
    inconsistent = {f: sorted(u) for f, u in units_by_field.items() if len(u) > 1}
    for field_name, unit_values in inconsistent.items():
        findings.append(
            Finding(
                code="einheit_inkonsistent",
                severity=SEVERITY_WARNING,
                message=f"Feld {field_name} traegt mehrere Einheiten: {unit_values}.",
                table_id=table.table_id,
            )
        )

    # Spalten ohne Zielfeld, aus denen trotzdem gelesen wurde.
    without_field = sorted({
        cell.col_id for cell in recon.cells
        if cell.field is None and cell.evidence
    })
    if without_field:
        findings.append(
            Finding(
                code="spalte_ohne_feld",
                severity=SEVERITY_INFO,
                message=(
                    f"Spalten ohne belegten Arm: {without_field}. Gelesene Werte "
                    "bleiben ohne Feld und gehen in keine Bewertung ein."
                ),
                table_id=table.table_id,
            )
        )

    header_facts = [cell for cell in recon.cells if cell.origin == "kopf_fakt"]
    if header_facts:
        findings.append(
            Finding(
                code="gruppengroesse_aus_kopf",
                severity=SEVERITY_INFO,
                message=(
                    f"{len(header_facts)} Gruppengroessen aus Kopfangaben "
                    "(z. B. n = 434) ohne Modellaufruf gelesen: "
                    + ", ".join(
                        f"{cell.field}={cell.value}" for cell in header_facts
                    )
                    + "."
                ),
                table_id=table.table_id,
            )
        )

    if recon.stats.get("n_conflict"):
        findings.append(
            Finding(
                code="konflikt",
                severity=SEVERITY_INFO,
                message=(
                    f"{recon.stats['n_conflict']} Adressen mit widerspruechlichen "
                    "Werten; sie bleiben als Konflikt stehen und werden nicht "
                    "ueberschrieben."
                ),
                table_id=table.table_id,
            )
        )

    timepoint_labels = {
        (band.text or "").strip()
        for band in table.header_bands
        if band.level > 0 and any(ch.isdigit() for ch in (band.text or ""))
    }
    if len(timepoint_labels) > 3:
        findings.append(
            Finding(
                code="mehrere_zeitpunkte_im_kopf",
                severity=SEVERITY_INFO,
                message=(
                    f"{len(timepoint_labels)} Kopfzellen mit Zahlen deuten auf "
                    "mehrere Messzeitpunkte; die Zuordnung bleibt pruefpflichtig."
                ),
                table_id=table.table_id,
            )
        )

    return {
        "n_evidence": recon.stats.get("n_evidence", 0),
        "n_cells": recon.stats.get("n_cells", 0),
        "n_conflict": recon.stats.get("n_conflict", 0),
        "n_agreed": recon.stats.get("n_agreed", 0),
        "n_bidirectional": recon.stats.get("bidirectional", {}).get("both", 0),
        "n_bidirectional_agree": recon.stats.get("bidirectional", {}).get("agreed", 0),
        "n_bidirectional_differ": recon.stats.get("bidirectional", {}).get("differ", 0),
        "quote_missing": n_quote_missing,
        "quote_not_in_unit": n_beleg_fehlt,
        "events_over_group_size": n_events_over,
        "sd_vs_mean_odd": n_sd_odd,
        "inconsistent_units": len(inconsistent),
        "columns_without_field": without_field,
        "header_facts": len(header_facts),
    }


def _column_of_field(table: Table, field_name: str) -> Optional[int]:
    for column in table.columns:
        if column.field == field_name:
            return column.col_id
    return None


def _source_group_size(table: Table, row_id: int, arm: str) -> Optional[float]:
    col_id = _column_of_field(table, f"{arm}_group_size")
    if col_id is None:
        return None
    row = table.row(row_id)
    if row is None:
        return None
    cell = row.cells.get(col_id)
    return cell.value if cell is not None else None


_ARM_STOPWORTER = {"group", "groups", "arm", "arms", "the", "n", "value",
                  "values", "patients", "subjects", "mg", "day", "mean",
                  "median", "baseline", "total", "change", "difference",
                  "ratio", "month", "months", "week", "weeks", "year", "years",
                  "from", "to", "at", "in", "of", "and", "versus", "vs",
                  "follow", "up", "end", "study", "screening", "visit"}
_ARM_ROLLEN = {"intervention": {"intervention"},
               "comparator": {"comparator", "control"}}


def _arm_worte(text: Optional[str]) -> set:
    return {
        wort for wort in re.split(r"[^a-z0-9]+", (text or "").lower())
        if wort and wort not in _ARM_STOPWORTER
    }


def _baender_mit_n(table: Table) -> List[Tuple[Any, Any]]:
    """Gruppenbaender, unter denen ein n gedruckt steht, mit dem ersten n-Wert.

    Reine Zahlen- oder Periodenbaender (``(n=16)``, ``S1``) tragen nach dem
    Stopwort-Filter keine Worte und fallen damit heraus - gemeldet wird die
    Gruppe, nicht das Raster.
    """
    treffer: List[Tuple[Any, Any]] = []
    for band in table.header_bands:
        worte = _arm_worte(band.text)
        if not any(len(wort) >= 3 for wort in worte):
            continue
        werte = [
            fact["value"] for fact in table.header_facts
            if fact.get("value") is not None
            and band.col_start <= fact["col_end"]
            and fact["col_start"] <= band.col_end
        ]
        if werte:
            treffer.append((band, werte[0]))
    return treffer


def _n_hinweis(baender: List[Tuple[Any, Any]]) -> str:
    teile = [f"{band.text!r} ({wert})" for band, wert in baender[:3]]
    rest = len(baender) - len(teile)
    return "n steht auf " + ", ".join(teile) + (f" und {rest} weiteren" if rest else "")


def validate_arm_context(table: Table, context: Optional[Dict[str, Any]]) -> List[Finding]:
    """Meldet, wenn der gedruckte n-Kopf dem Record-Kontext widerspricht.

    Der Kontext bleibt die massgebliche Armquelle. Der Kopf wird nur geprueft,
    nicht umgehaengt:

    * ``kopf_n_widerspricht_kontext`` - ein Kontextarm ist im Kopf auffindbar,
      traegt dort aber kein n, waehrend andere Gruppen eins drucken.
    * ``kontextarm_nicht_im_kopf`` - ein Kontextarm ist im Kopf nicht
      auffindbar, waehrend andere Gruppen ein n drucken. Ist der Kontextarm
      eine Beschreibung statt eines Namens, bleibt der Befund ein Hinweis.
    """
    if not context:
        return []
    arme = {
        arm: _arm_worte(context.get(arm))
        for arm in ("intervention", "comparator")
        if context.get(arm)
    }
    baender = _baender_mit_n(table)
    if not arme or not baender:
        return []
    hinweis = _n_hinweis(baender)
    mit_n = {id(band) for band, _ in baender}
    findings: List[Finding] = []
    for arm, worte in arme.items():
        treffer = [
            band for band in table.header_bands
            if _arm_worte(band.text)
            and (worte | _ARM_ROLLEN[arm]) & _arm_worte(band.text)
        ]
        if any(id(band) in mit_n for band in treffer):
            continue
        anzeige = context.get(arm)
        if treffer and len(worte) <= 2:
            findings.append(Finding(
                code="kopf_n_widerspricht_kontext",
                severity=SEVERITY_WARNING,
                message=(
                    f"Kontextarm {anzeige!r} ({arm}) traegt im Kopf kein n; "
                    f"{hinweis}. Der Kontext bleibt massgeblich, der Kopf ist zu pruefen."
                ),
                table_id=table.table_id,
            ))
        elif len(worte) > 2:
            findings.append(Finding(
                code="kontextarm_nicht_im_kopf",
                severity=SEVERITY_INFO,
                message=(
                    f"Kontextarm {anzeige!r} ({arm}) ist eine Beschreibung und im "
                    f"Kopf nicht auffindbar; {hinweis}. Kein Namenskonflikt."
                ),
                table_id=table.table_id,
            ))
        else:
            findings.append(Finding(
                code="kontextarm_nicht_im_kopf",
                severity=SEVERITY_WARNING,
                message=(
                    f"Kontextarm {anzeige!r} ({arm}) ist im Kopf nicht auffindbar; "
                    f"{hinweis}. Der Kontext bleibt massgeblich, der Kopf ist zu pruefen."
                ),
                table_id=table.table_id,
            ))
    return findings


def validate(table: Table, units: Sequence[ExtractionUnit],
             recon: Optional[ReconstructionResult] = None) -> ValidationReport:
    """Struktur und Inhalt pruefen; das Urteil bleibt getrennt."""
    findings: List[Finding] = []
    structural = _check_structure(table, units, findings)
    content: Dict[str, Any] = {}
    if recon is not None:
        content = _check_content(table, units, recon, findings)

    errors = [f for f in findings if f.severity == SEVERITY_ERROR]
    status = STATUS_COMPLETE if not errors and structural.get("coverage") == 1.0 else STATUS_GAPS
    notes = [
        "Strukturelle Vollstaendigkeit sagt, dass jede Zelle im Ausschnitt lag - "
        "nicht, dass der gelesene Wert stimmt.",
        "Ein Modellkonsens zwischen Zeilen- und Spaltenlesung ist ein Hinweis, "
        "kein Beweis: die Pruefung gegen die Quelle bleibt menschlich.",
    ]
    return ValidationReport(table_id=table.table_id, status=status,
                            findings=findings, structural=structural,
                            content=content, notes=notes)


def summarise(reports: Sequence[ValidationReport]) -> Dict[str, Any]:
    """Kurzuebersicht ueber mehrere Tabellen (Benchmark und Bericht)."""
    return {
        "n_tables": len(reports),
        "n_structurally_complete": len([r for r in reports if r.status == STATUS_COMPLETE]),
        "n_with_errors": len([r for r in reports if r.errors]),
        "n_with_warnings": len([r for r in reports if r.warnings]),
        "codes": _count_codes(reports),
        "coverage_mean": round(
            sum(r.structural.get("coverage", 0.0) for r in reports) / len(reports), 4
        ) if reports else 0.0,
    }


def _count_codes(reports: Sequence[ValidationReport]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for report in reports:
        for finding in report.findings:
            counts[finding.code] = counts.get(finding.code, 0) + 1
    return dict(sorted(counts.items()))
