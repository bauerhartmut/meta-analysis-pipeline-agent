#!/usr/bin/env python3
"""Bericht aus den Benchmark-Artefakten (Struktur, Auswertung) erzeugen.

Es wird nichts gerechnet, was nicht in den JSON-Dateien steht: der Bericht ist
eine Formatierung der Artefakte. Fehlt ein Modelllauf, steht das im Bericht -
ein Strukturvergleich ist kein Genauigkeitsvergleich.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

STRATEGY_ORDER = ("A", "B", "C", "D", "E")


def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, float):
        return f"{value:.{digits}f}".replace(".", ",")
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return str(value)


def _table(headers: List[str], rows: List[List[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(cell) for cell in row) + " |")
    return "\n".join(lines)


def build_report(structure: Optional[Dict[str, Any]],
                 evaluations: List[Dict[str, Any]],
                 selection: Optional[Dict[str, Any]]) -> str:
    parts: List[str] = []
    parts.append("# Table Decomposition & Reconstruction: Benchmarkbericht\n")
    parts.append(
        "Erzeugt am "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        + " aus den unten genannten Artefakten. Alle Zahlen sind aus diesen "
        "Dateien gelesen, keine ist geschaetzt.\n"
    )

    if selection:
        parts.append("## Auswahl\n")
        parts.append(_table(
            ["Feld", "Wert"],
            [
                ["Split", selection.get("role")],
                ["Tabellen", selection.get("n_tables")],
                ["Records", selection.get("n_records")],
                ["Dokumente", selection.get("n_documents")],
                ["Kandidaten", selection.get("n_candidates")],
                ["Gold erreichbar (Summe je Tabelle)", selection.get("gold_reachable_total")],
                ["Records-Hash", (selection.get("records_sha256") or "")[:16]],
                ["eingefroren", selection.get("frozen")],
            ],
        ))
        parts.append("")
        strata = selection.get("strata_counts") or {}
        parts.append(_table(
            ["Schicht", "Tabellen"],
            [[name, count] for name, count in sorted(strata.items(), key=lambda kv: -kv[1])],
        ))
        parts.append("")

    if structure:
        parts.append("## Struktur- und Aufwandsvergleich (ohne Modellaufruf)\n")
        summary = structure.get("strategy_summary") or {}
        rows = []
        for strategy in STRATEGY_ORDER:
            if strategy not in summary:
                continue
            row = summary[strategy]
            rows.append([
                strategy,
                row.get("strategy_label"),
                row.get("records"),
                row.get("tables"),
                row.get("units_per_record"),
                row.get("prompt_chars_per_record"),
                row.get("prompt_chars_per_unit"),
                row.get("est_tokens"),
                row.get("gold_reachable"),
                f"{row.get('tables_complete')}/{row.get('tables')}",
                row.get("errors"),
                row.get("warnings"),
            ])
        parts.append(_table(
            ["Var", "Verfahren", "Records", "Tabellen", "Einheiten/Record",
             "Zeichen/Record", "Zeichen/Einheit", "Tokens ges. (Sch.)",
             "Gold erreichbar (Vereinigung)", "strukturell komplett",
             "Prueffeheler", "Warnungen"],
            rows,
        ))
        parts.append("")
        parts.append(
            "`Tok. (Sch.)` ist eine Schaetzung aus Prompt-Zeichen / 4 und als "
            "solche markiert; sie ersetzt keine gemessene Tokenzahl.\n"
        )

    if evaluations:
        parts.append("## Modellvergleich\n")
        for evaluation in evaluations:
            strategies = evaluation.get("strategies") or {}
            rows = []
            for strategy in STRATEGY_ORDER:
                if strategy not in strategies:
                    continue
                data = strategies[strategy]
                cells = data.get("cells") or {}
                rows.append([
                    strategy,
                    data.get("strategy_label"),
                    data.get("records"),
                    cells.get("richtig"),
                    cells.get("falsch"),
                    cells.get("fehlend"),
                    cells.get("ohne_gold"),
                    data.get("precision"),
                    data.get("recall"),
                    data.get("f1"),
                    data.get("records_exakt"),
                    data.get("arm_tausch_records"),
                    data.get("technische_ausfaelle"),
                ])
            parts.append(_table(
                ["Var", "Verfahren", "Records", "richtig", "falsch", "fehlend",
                 "ohne Gold", "Precision", "Recall", "F1", "Records exakt",
                 "Armtausch", "Ausfaelle"],
                rows,
            ))
            parts.append("")

            parts.append("### Token, Laufzeit und Kosten\n")
            rows = []
            for strategy in STRATEGY_ORDER:
                if strategy not in strategies:
                    continue
                data = strategies[strategy]
                tokens = data.get("tokens") or {}
                rows.append([
                    strategy,
                    data.get("strategy_label"),
                    tokens.get("prompt"),
                    tokens.get("completion"),
                    tokens.get("gesamt"),
                    data.get("runtime_s"),
                    data.get("kosten"),
                    data.get("kosten_pro_100_richtige_zellen"),
                ])
            parts.append(_table(
                ["Var", "Verfahren", "Input-Tokens", "Output-Tokens", "Tokens",
                 "Laufzeit (s)", "Kosten", "Kosten/100 richtige Zellen"],
                rows,
            ))
            parts.append("")

            parts.append("### Aufschluesselung nach Tabellenkomplexitaet\n")
            rows = []
            for strategy in STRATEGY_ORDER:
                if strategy not in strategies:
                    continue
                for name, counts in (strategies[strategy].get("je_komplexitaet") or {}).items():
                    rows.append([
                        strategy,
                        name,
                        counts.get("records"),
                        counts.get("richtig"),
                        counts.get("falsch"),
                        counts.get("fehlend"),
                        counts.get("precision"),
                        counts.get("recall"),
                    ])
            parts.append(_table(
                ["Var", "Klasse", "Records", "richtig", "falsch", "fehlend",
                 "Precision", "Recall"],
                rows,
            ))
            parts.append("")

            parts.append("### Fehler- und Pruefklassen\n")
            rows = []
            for strategy in STRATEGY_ORDER:
                if strategy not in strategies:
                    continue
                data = strategies[strategy]
                for art, count in (data.get("fehlerklassen") or {}).items():
                    rows.append([strategy, "Fehler", art, count])
                for code, count in ((data.get("validierung") or {}).get("codes") or {}).items():
                    rows.append([strategy, "Pruefung", code, count])
            parts.append(_table(["Var", "Gruppe", "Klasse", "Anzahl"], rows))
            parts.append("")

            not_measurable = evaluation.get("nicht_messbar") or {}
            if not_measurable:
                parts.append("### Nicht messbar mit diesem Gold\n")
                for key, text in not_measurable.items():
                    parts.append(f"- **{key}**: {text}")
                parts.append("")
    else:
        parts.append("## Modellvergleich\n")
        parts.append(
            "Kein Modelllauf vorhanden. Precision, Recall, F1, Exact Match und "
            "Kosten pro richtiger Zelle sind daher **nicht gemessen**; der "
            "Strukturvergleich oben belegt nur, dass die Zerlegung den Kontext "
            "vollstaendig mitfuehrt und wie viele Aufrufe sie kostet.\n"
        )

    parts.append("## Grenzen\n")
    parts.append(
        "- Ein Modellkonsens zwischen Zeilen- und Spaltenlesung ist ein Hinweis, "
        "kein Beweis; die Pruefung gegen die Quelle bleibt menschlich.\n"
        "- `gold_reachable` ist die Obergrenze des Tabellenpfads, keine "
        "Modellleistung: Goldzellen, deren Feld eine Spalte der Tabelle traegt.\n"
        "- Der Weg von der Zelle zum Arm ist eine deterministische Header- und "
        "Kontextzuordnung. Wo sie keinen Arm belegt, bleibt die Spalte ohne Feld "
        "und geht nicht in die Bewertung ein.\n"
    )
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure", type=Path, default=None)
    parser.add_argument("--selection", type=Path, default=None)
    parser.add_argument("--evaluation", type=Path, nargs="*", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    structure = json.loads(args.structure.read_text(encoding="utf-8")) if args.structure else None
    selection = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None
    evaluations = [json.loads(path.read_text(encoding="utf-8")) for path in args.evaluation]
    text = build_report(structure, evaluations, selection)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
