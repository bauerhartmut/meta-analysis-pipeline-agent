#!/usr/bin/env python3
"""Bewertung der Rueckfallregel (v6_target_fallback).

Das Modell nennt je Zelle den benutzten Messzeitpunkt. Dieses Skript trennt die
Zellen in zwei Klassen und zaehlt sie getrennt:

* **zieltreu**: Zelle nennt den im Record annotierten Zielzeitpunkt
* **rueckfall**: Zelle nennt einen anderen Zeitpunkt (dann muss sie stimmen,
  sonst ist die Rueckfallregel schaedlich)

Zusaetzlich: Auslassungen je Feld, Gesamtmetriken und die Zeitdistanz der
Rueckfaelle in Monaten (aus den Labels, ohne Modell).
"""

from __future__ import annotations

import argparse
import re
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from check_timepoints import rang  # noqa: E402
from evaluate_extended import _close, _f1, _safe_div, evaluate_numeric, read_jsonl  # noqa: E402
from stage_extraction import normalisiere  # noqa: E402


def klassifiziere(target: str, label: str) -> str:
    """Ordnet eine Zelle einer Klasse zu (Eingaben bereits normalisiert)."""
    if not target:
        return "ohne_ziel"
    if not label:
        return "ohne_zeitpunkt"
    if label == target:
        return "zieltreu"
    return "rueckfall"


NUMMER = re.compile(r"^(\d{1,3})$")
ZEIT_LABEL = re.compile(r"^(week|month|day)\s+(\d{1,3})$")


def normalisiere_label(label: str, target: str) -> tuple[str, str]:
    """Ergaenzt eine Einheit nur, wenn sie belegt ist; gibt (label, status).

    Status: "ok" (vergleichbar), "leer" (keine Angabe), "unklar" (Zahl ohne
    belegte Einheit). Die Einheit kommt ausschliesslich aus dem annotierten
    Zielzeitpunkt: "24" bei Ziel "week 24" ist Woche 24, "24" bei Ziel
    "month 6" bleibt unklar. Aus der Zahl allein wird nichts abgeleitet, und
    "0" wird nur dann zu baseline, wenn das Ziel baseline sagt.
    """
    roh = normalisiere(label)
    ziel = normalisiere(target)
    if not roh or roh in ("not applicable", "running text", "not stated"):
        return "", "leer"
    if NUMMER.match(roh):
        zahl = int(roh)
        if zahl == 0 and ziel in ("baseline", "week 0", "month 0", "day 0"):
            return "baseline", "ok"
        treffer = ZEIT_LABEL.match(ziel)
        if treffer and int(treffer.group(2)) == zahl:
            return f"{treffer.group(1)} {zahl}", "ok"
        return "", "unklar"
    return roh, "ok"


def arme_gemischt(cells: list[dict[str, Any]], target: str) -> bool:
    """Wahr, wenn die Arme verschiedene Zeitpunkte tragen.

    Ein Zeitpunkt gilt je Arm; weicht der Komparator vom Interventionsarm ab,
    wurde ueber die Arme hinweg gemischt (z. B. Intervention Woche 24,
    Komparator Baseline) und die Zuordnung ist nicht mehr eindeutig.
    """
    pro_arm: dict[str, set[str]] = defaultdict(set)
    for cell in cells:
        # Rohvergleich: auch '24' gegen '0' ist ein Unterschied, unabhaengig
        # davon, ob die Einheit belegt ist.
        label = normalisiere(cell.get("timepoint") or "")
        if label and label not in ("not applicable", "running text", "not stated"):
            pro_arm[str(cell.get("arm"))].add(label)
    if len(pro_arm) < 2:
        return False
    mengen = list(pro_arm.values())
    return any(m != mengen[0] for m in mengen[1:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=HERE / "records" / "yun_dev.jsonl")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    records = read_jsonl(args.records)
    by_id = {str(record["record_id"]): record for record in records}
    rows = read_jsonl(HERE / "runs" / args.run / "predictions.jsonl")
    predictions = {str(row["record_id"]): row for row in rows}

    zaehler = Counter()
    pro_feld: dict[str, Counter] = defaultdict(Counter)
    distanzen: list[float] = []
    rueckfall_beispiele: list[dict[str, Any]] = []
    unklar_beispiele: list[dict[str, Any]] = []
    arm_gemischt: list[str] = []
    fehlend: Counter[str] = Counter()

    for record_id, record in by_id.items():
        gold = {(cell["field"], cell.get("arm")): float(cell["value"]) for cell in record["gold"]["cells"]}
        target = normalisiere((record.get("timepoint") or {}).get("target") or "")
        if "not stated" in target:
            # Kein Zielzeitpunkt im Record: Zellen lassen sich nicht als
            # zieltreu oder Rueckfall bewerten und zaehlen als "ohne_ziel".
            target = ""
        cells = (predictions.get(record_id, {}).get("predicted") or {}).get("cells", [])
        gesehen: set[tuple[str, str | None]] = set()
        for cell in cells:
            key = (cell["field"], cell.get("arm"))
            label, label_status = normalisiere_label(cell.get("timepoint") or "", target)
            if label_status == "unklar":
                zaehler["unklar_zellen"] += 1
                if len(unklar_beispiele) < 20:
                    unklar_beispiele.append(
                        {
                            "record_id": record_id,
                            "field": cell["field"],
                            "roh": cell.get("timepoint"),
                            "ziel": (record.get("timepoint") or {}).get("target"),
                        }
                    )
                continue
            # Drei getrennte Faelle: Record ohne Annotation, Zelle ohne
            # Zeitpunktangabe und Zelle mit abweichendem Zeitpunkt.
            art = klassifiziere(target, label)
            zaehler[f"{art}_zellen"] += 1
            pro_feld[cell["field"]][f"{art}_zellen"] += 1
            if key in gold:
                gesehen.add(key)
                if _close(cell["value"], gold[key], 1e-6, 0.0):
                    zaehler[f"{art}_richtig"] += 1
                    pro_feld[cell["field"]][f"{art}_richtig"] += 1
                else:
                    zaehler[f"{art}_falsch"] += 1
            else:
                zaehler[f"{art}_ohne_gold"] += 1
            if art == "rueckfall":
                ziel_rang, label_rang = rang(target), rang(label)
                if ziel_rang is not None and label_rang is not None:
                    distanzen.append(abs(label_rang - ziel_rang))
                if len(rueckfall_beispiele) < 20:
                    rueckfall_beispiele.append(
                        {
                            "record_id": record_id,
                            "field": cell["field"],
                            "target": (record.get("timepoint") or {}).get("target"),
                            "timepoint": cell.get("timepoint"),
                            "value": cell["value"],
                            "gold": gold.get(key),
                        }
                    )
        if arme_gemischt(cells, target):
            zaehler["records_arm_gemischt"] += 1
            if len(arm_gemischt) < 20:
                arm_gemischt.append(record_id)
        for key in gold:
            if key not in gesehen:
                fehlend[key[0]] += 1
                zaehler["auslassungen"] += 1

    gesamt = evaluate_numeric(records, predictions)
    gold_cells = sum(len(record["gold"]["cells"]) for record in records)
    ergebnis = {
        "run": args.run,
        "records": len(records),
        "gesamt": gesamt,
        "ohne_ziel": {
            "zellen": zaehler["ohne_ziel_zellen"],
            "richtig": zaehler["ohne_ziel_richtig"],
            "falsch": zaehler["ohne_ziel_falsch"],
            "ohne_gold": zaehler["ohne_ziel_ohne_gold"],
        },
        "ohne_zeitpunkt": {
            "zellen": zaehler["ohne_zeitpunkt_zellen"],
            "richtig": zaehler["ohne_zeitpunkt_richtig"],
            "falsch": zaehler["ohne_zeitpunkt_falsch"],
            "ohne_gold": zaehler["ohne_zeitpunkt_ohne_gold"],
        },
        "zieltreu": {
            "zellen": zaehler["zieltreu_zellen"],
            "richtig": zaehler["zieltreu_richtig"],
            "falsch": zaehler["zieltreu_falsch"],
            "ohne_gold": zaehler["zieltreu_ohne_gold"],
            "precision": round(
                _safe_div(zaehler["zieltreu_richtig"], zaehler["zieltreu_richtig"] + zaehler["zieltreu_falsch"]), 4
            ),
        },
        "rueckfall": {
            "zellen": zaehler["rueckfall_zellen"],
            "richtig": zaehler["rueckfall_richtig"],
            "falsch": zaehler["rueckfall_falsch"],
            "ohne_gold": zaehler["rueckfall_ohne_gold"],
            "precision": round(
                _safe_div(zaehler["rueckfall_richtig"], zaehler["rueckfall_richtig"] + zaehler["rueckfall_falsch"]), 4
            ),
            "zeitdistanz_median_monate": round(sorted(distanzen)[len(distanzen) // 2], 2) if distanzen else None,
            "zeitdistanz_bekannt": len(distanzen),
            "beispiele": rueckfall_beispiele,
        },
        "unklar": {
            "zellen": zaehler["unklar_zellen"],
            "anteil": round(_safe_div(zaehler["unklar_zellen"], gold_cells), 4),
            "beispiele": unklar_beispiele,
        },
        "arm_gemischt": {
            "records": zaehler["records_arm_gemischt"],
            "beispiele": arm_gemischt,
        },
        "auslassungen": {
            "gesamt": zaehler["auslassungen"],
            "je_feld": dict(sorted(fehlend.items())),
            "quote": round(_safe_div(zaehler["auslassungen"], gold_cells), 4),
        },
        "je_feld": {field: dict(counts) for field, counts in sorted(pro_feld.items())},
        "zell_f1_aus_klassen": round(
            _f1(
                _safe_div(
                    zaehler["zieltreu_richtig"] + zaehler["rueckfall_richtig"],
                    zaehler["zieltreu_richtig"] + zaehler["zieltreu_falsch"]
                    + zaehler["rueckfall_richtig"] + zaehler["rueckfall_falsch"]
                    + zaehler["zieltreu_ohne_gold"] + zaehler["rueckfall_ohne_gold"],
                ),
                _safe_div(zaehler["zieltreu_richtig"] + zaehler["rueckfall_richtig"], gold_cells),
            ),
            4,
        ),
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"[gesamt] F1 {gesamt['cell_f1']:.4f} recall {gesamt['cell_recall']:.4f} precision "
        f"{gesamt['cell_precision']:.4f} MAE {gesamt['mae_pairs']} coverage {gesamt['mae_coverage']} "
        f"({gesamt['mae_pairs_covered']}/{gold_cells}) exakt {gesamt['record_exact']}/{len(records)}"
    )
    for art in ("zieltreu", "rueckfall", "ohne_zeitpunkt", "ohne_ziel"):
        block = ergebnis[art]
        precision = block.get("precision")
        zusatz = f", Precision {precision}" if precision is not None else ""
        print(
            f"[{art}] {block['zellen']} Zellen, richtig {block['richtig']}, falsch {block['falsch']}, "
            f"ohne Gold {block['ohne_gold']}{zusatz}"
        )
    if ergebnis["rueckfall"]["beispiele"]:
        print(f"[rueckfall] Zeitdistanz Median {ergebnis['rueckfall']['zeitdistanz_median_monate']} Monate "
              f"({ergebnis['rueckfall']['zeitdistanz_bekannt']} bestimmbar)")
    print(f"[auslassungen] {ergebnis['auslassungen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
