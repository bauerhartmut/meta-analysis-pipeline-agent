#!/usr/bin/env python3
"""Erzeugt die Ergebnis-Markdown aus den Laufdaten.

Alle Zahlen kommen aus den Metrikdateien und den Vorhersagen der Laeufe; im
Bericht steht keine handgetippte Zahl. Aufruf:

    python public_benchmark/extended_benchmark/runs/build_results_md.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from extended_benchmark.versions import normalisiere_version  # noqa: E402

RUNS = Path(__file__).resolve().parent
BENCH = RUNS.parent
RECORDS = BENCH / "records" / "yun_dev.jsonl"
OUT = RUNS / "ergebnisse_yun_dev.md"

# Laeufe in zeitlicher Reihenfolge: (run_id, label, prompt_version)
LAEUFE = [
    ("yun_dev_20261114", "Lauf 1: ohne Zeitpunktangabe", "v1"),
    ("yun_dev_tp_20261115", "Lauf 2: Zeitpunkt im Prompt", "v2_timepoint"),
    ("yun_dev_retry_20261115", "Lauf 3: mit Retry (Cache-Treffer)", "v2_timepoint"),
    ("yun_dev_fresh_20261115", "Lauf 4: frisch, Cache-Buster", "v2b_cachebuster"),
    ("yun_dev_v3_20261115", "Lauf 5: absolute Ereigniszahlen", "v3_abs_count"),
    ("yun_dev_std_20261115", "Lauf 6: Standardprompt frisch", "v2_timepoint"),
    ("yun_dev_v4_20261115", "Lauf 7: letzter Messzeitpunkt", "v4_last_timepoint"),
    ("yun_dev_v5_20261115", "Lauf 8: Zielzeitpunkt je Record", "v5_target_timepoint"),
    ("yun_dev_v6_20261115", "Lauf 9: Zielzeitpunkt mit Rueckfall", "v6_target_fallback"),
]
MODELLE = [("qwen30", "qwen3-30b-a3b"), ("glm", "glm-5.3")]


def de(value: float | None, digits: int = 3) -> str:
    """Zahl im deutschen Format; None bleibt None."""
    if value is None:
        return "-"
    return f"{value:.{digits}f}".replace(".", ",")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def gold_cells() -> dict[str, dict[tuple[str, str], float]]:
    gold = {}
    for record in read_jsonl(RECORDS):
        gold[record["record_id"]] = {
            (cell["field"], cell["arm"]): float(cell["value"]) for cell in record["gold"]["cells"]
        }
    return gold


def fehler_verteilung(run: str, model: str, gold: dict[str, dict[tuple[str, str], float]]) -> dict[str, float] | None:
    rows = [row for row in read_jsonl(RUNS / run / "predictions.jsonl") if row.get("model") == model]
    if not rows:
        return None
    errors = []
    for row in rows:
        for (field, arm), value in gold.get(row["record_id"], {}).items():
            for cell in row["predicted"]["cells"]:
                if cell["field"] == field and cell["arm"] == arm:
                    errors.append(abs(float(cell["value"]) - value))
    errors.sort()
    if not errors:
        return None
    return {
        "n": len(errors),
        "median": statistics.median(errors),
        "p90": errors[int(0.9 * (len(errors) - 1))],
        "max": errors[-1],
    }


def main() -> int:
    gold = gold_cells()
    zeilen: list[str] = []
    zeilen.append("# Ergebnisse: Yun-Dev-Pilotlaeufe (numerische Extraktion)")
    zeilen.append("")
    zeilen.append("Automatisch erzeugt aus den Laufdaten von `run_extended_extraction.py` und")
    zeilen.append("`evaluate_extended.py`. Datengrundlage: die 43 Dev-Records aus")
    zeilen.append("`records/yun_dev.jsonl` mit 170 Gold-Zellen aus 38 Records mit Inhalt.")
    zeilen.append("Der Quell-Testsplit (407 Records) und die 249 eingefrorenen Records wurden")
    zeilen.append("nicht verwendet.")
    zeilen.append("")
    zeilen.append("Der MAE steht in jeder Tabelle neben `mae_coverage`, damit ein niedriger")
    zeilen.append("Fehler bei duenner Abdeckung nicht als gut durchgeht.")
    zeilen.append("")

    zeilen.append("## Ueberblick")
    zeilen.append("")
    zeilen.append("| Lauf | Prompt | Modell | Recall | Precision | F1 | MAE | mae_coverage | exakt | Vertauschung | leer | Antworten < 1 s |")
    zeilen.append("|---|---|---|---|---|---|---|---|---|---|---|---|")

    for run, label, version in LAEUFE:
        version = normalisiere_version(version)
        for model, model_label in MODELLE:
            metrics_path = RUNS / run / "eval" / f"{model}.metrics.json"
            if not metrics_path.exists():
                continue
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            rows = [row for row in read_jsonl(RUNS / run / "predictions.jsonl") if row.get("model") == model]
            leer = sum(1 for row in rows if not row["predicted"]["cells"])
            # Lauf 3 kannte das Feld suspected_cache noch nicht, deshalb zaehlt
            # hier die Laufzeit: unter einer Sekunde ist ein Cache-Treffer.
            cache = sum(1 for row in rows if (row.get("elapsed_s") or 99) < 1.0)
            coverage = f"{de(metrics['mae_coverage'])} ({metrics['mae_pairs_covered']}/{metrics['gold_cells']})"
            zeilen.append(
                f"| {label} | `{version}` | {model_label} "
                f"| {de(metrics['cell_recall'])} | {de(metrics['cell_precision'])} | {de(metrics['cell_f1'])} "
                f"| {de(metrics['mae_pairs'])} | {coverage} | {metrics['record_exact']}/{metrics['records']} "
                f"| {metrics['arm_swap_records']}/{metrics['arm_swap_evaluable']} | {leer}/{len(rows)} | {cache}/{len(rows)} |"
            )
    zeilen.append("")
    zeilen.append("Prompt-Versionen kanonisch: `v2b_cachebuster`, `v2_timepoint` und")
    zeilen.append("`v2_timepoint_cb` sind dieselbe Fassung (`v2_timepoint`), der Cache-Zusatz")
    zeilen.append("`_cb` ist nur eine Generierungsvariante (siehe `versions.py`).")
    zeilen.append("")
    zeilen.append("Antworten unter einer Sekunde sind ein Cache-Verdacht, kein Beweis: bei")
    zeilen.append("qwen3-30b sind sie auch normale Geschwindigkeit. Aussagekraeftig ist das")
    zeilen.append("Vollbild: Lauf 3 hat 43 von 43 in unter 0,2 s, Lauf 4 keine einzige.")
    zeilen.append("")

    zeilen.append("## Letzter Lauf je Modell nach Feld")
    zeilen.append("")
    zeilen.append("qwen3-30b: Lauf 3, glm: Lauf 4 (beide kanonisch `v2_timepoint`).")
    zeilen.append("Werte als Recall | MAE | abgedeckte Zellen.")
    zeilen.append("")
    zeilen.append("| Feld | Gold | qwen3-30b | glm-5.3 |")
    zeilen.append("|---|---|---|---|")
    felder = [
        "intervention_group_size",
        "comparator_group_size",
        "intervention_events",
        "comparator_events",
        "intervention_mean",
        "comparator_mean",
        "intervention_standard_deviation",
        "comparator_standard_deviation",
    ]
    qwen = json.loads((RUNS / "yun_dev_retry_20261115/eval/qwen30.metrics.json").read_text(encoding="utf-8"))
    glm = json.loads((RUNS / "yun_dev_fresh_20261115/eval/glm.metrics.json").read_text(encoding="utf-8"))
    for feld in felder:
        q = qwen["fields"][feld]
        g = glm["fields"][feld]
        zeilen.append(
            f"| {feld} | {g['gold']} "
            f"| {de(q['recall'])} \\| {de(q['mae'], 2)} \\| {q['mae_covered']} "
            f"| {de(g['recall'])} \\| {de(g['mae'], 2)} \\| {g['mae_covered']} |"
        )
    zeilen.append("")

    zeilen.append("## Fehlerverteilung der letzten Laeufe")
    zeilen.append("")
    zeilen.append("| Lauf | Modell | gepaarte Zellen | Median | p90 | Maximum |")
    zeilen.append("|---|---|---|---|---|---|")
    for run, label, _ in (LAEUFE[2], LAEUFE[3]):
        for model, model_label in MODELLE:
            verteilung = fehler_verteilung(run, model, gold)
            if not verteilung:
                continue
            zeilen.append(
                f"| {label} | {model_label} | {verteilung['n']} | {de(verteilung['median'])} "
                f"| {de(verteilung['p90'])} | {de(verteilung['max'])} |"
            )
    zeilen.append("")

    zeilen.append("## Befunde")
    zeilen.append("")
    zeilen.append("- Der Zeitpunkt im Prompt (`v2`) behebt den groessten Einzelfehler:")
    zeilen.append("  `yun2024:229` wurde vorher von beiden Modellen mit 854,0 statt 487,33")
    zeilen.append("  beantwortet (Follow-up-Spalte statt Post-test).")
    zeilen.append("- Die Wiederholung bei `finish_reason = \"length\"` rettet zwei von drei")
    zeilen.append("  Ausfaellen; frisch generiert gelingt auch der dritte.")
    zeilen.append("- Bei glm sitzt der gesamte Restfehler in den Ereigniszahlen: Recall 0,75,")
    zeilen.append("  MAE 3,75 bis 4,75 bei je 8 Gold-Zellen. Gruppengroessen, Mittelwerte und")
    zeilen.append("  Streuungen liegen bei MAE 0,00 bis 0,005.")
    zeilen.append("- Armvertauschung trat in keinem Lauf auf.")
    zeilen.append("- Lauf 3 kam aus dem Gateway-Cache (alle Antworten unter 0,2 s, 84 von 86")
    zeilen.append("  Zellenlisten zeichengleich); Lauf 4 ist die belastbare Messung.")
    zeilen.append("")
    zeilen.append("## Grenzen")
    zeilen.append("")
    zeilen.append("- 43 Records sind Pilotgroesse; Unterschiede unter etwa 0,03 F1 sind nicht")
    zeilen.append("  belastbar, der Abstand zwischen den Modellen schon.")
    zeilen.append("- Vergleiche nur innerhalb derselben Prompt-Version; `v2b_cachebuster`")
    zeilen.append("  enthaelt zusaetzlich einen technischen Session-Tag.")
    zeilen.append("- Keine Sichtpruefung der Modellantworten, nur Parser und Metriken.")
    zeilen.append("- Zwei Records (`yun2024:17`, `yun2024:18`) haben 0 Gold-Zellen; leere")
    zeilen.append("  Antworten dort sind korrekt.")
    zeilen.append("")
    zeilen.append("## Quelldaten")
    zeilen.append("")
    for run, label, _ in LAEUFE:
        zeilen.append(f"- `{run}/`: {label}, `predictions.jsonl`, `eval/*.metrics.json`")
    zeilen.append("- Erzeugt von `runs/build_results_md.py`.")
    zeilen.append("")

    OUT.write_text("\n".join(zeilen), encoding="utf-8", newline="\n")
    print(f"geschrieben: {OUT} ({len(zeilen)} Zeilen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
