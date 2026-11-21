#!/usr/bin/env python3
"""Bewertet Modellantworten auf die Claude-Testanfragen aus `prompts/`.

Erwartet je Record eine Datei ``antworten/<record>_antwort.json`` mit dem rohen
Antworttext des Modells (Codefences und Beiwerk sind erlaubt; gelesen wird das
erste JSON-Objekt). Verglichen wird gegen ``../loesungen/<record>_loesung.json``.

Treffer ist `(field, arm)` gleich und `|Wert - Gold| < 1e-6`. Daraus TP, FP, FN
je Record und als Summe. Eine Zelle mit falschem Wert zaehlt als FP (falsche
Zelle) und als FN (verpasster Goldwert). `timepoint` und `quote` werden nicht
bewertet.

Ausgabe: ``bewertung_20261121.json`` und ``BEWERTUNG.md`` im Testordner.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/schwere_records_20261121/bewerte_claude_20261121.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
PAKET = HIER.parents[2]  # public_benchmark
BENCH = PAKET / "extended_benchmark"
REPO = PAKET.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(PAKET))

from extended_benchmark import run_extended_extraction as rx  # noqa: E402

TEST = HIER / "claude_test_20261121"
PROMPTS = TEST / "prompts"
ANTWORTEN = TEST / "antworten"
LOESUNGEN = HIER / "loesungen"
AUSWAHL = HIER / "auswahl_20261121.json"
TOLERANZ = 1e-6


def dateiname(record_id: str) -> str:
    return record_id.replace(":", "_").replace("/", "_")


def zellen_aus_antwort(text: str) -> tuple[list[dict], str]:
    """Liest die Zellenliste aus der Modellantwort, auch mit Codefence."""
    payload, fehler = rx._load_payload(text)  # noqa: SLF001 - derselbe Leser wie im Harness
    if payload is None:
        return [], fehler or "kein JSON"
    zellen = payload.get("cells")
    if zellen is None and isinstance(payload.get("predicted"), dict):
        zellen = payload["predicted"].get("cells")
    if not isinstance(zellen, list):
        return [], "kein Feld cells"
    sauber = [z for z in zellen if isinstance(z, dict) and z.get("field") and "value" in z]
    return sauber, "" if len(sauber) == len(zellen) else "Zellen ohne field/value ignoriert"


def bilanz(gold: list[dict], pred: list[dict]) -> dict:
    """TP/FP/FN einer Antwort gegen die Goldzellen."""
    gold_map: dict[tuple[str, str], float] = {}
    for c in gold:
        gold_map.setdefault((c["field"], c.get("arm") or ""), float(c["value"]))
    pred_map: dict[tuple[str, str], float] = {}
    for c in pred:
        try:
            pred_map.setdefault((c["field"], c.get("arm") or ""), float(c["value"]))
        except (TypeError, ValueError):
            continue
    tp = sum(1 for k, wert in gold_map.items() if k in pred_map and abs(pred_map[k] - wert) < TOLERANZ)
    fp = sum(1 for k in pred_map if k not in gold_map) + sum(
        1 for k, wert in gold_map.items() if k in pred_map and abs(pred_map[k] - wert) >= TOLERANZ
    )
    fn = sum(1 for k in gold_map if k not in pred_map) + sum(
        1 for k, wert in gold_map.items() if k in pred_map and abs(pred_map[k] - wert) >= TOLERANZ
    )
    return {"tp": tp, "fp": fp, "fn": fn}


def f1(tp: int, fp: int, fn: int) -> float | None:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    if not precision or not recall:
        return None
    return 2 * precision * recall / (precision + recall)


def main() -> int:
    auswahl = json.loads(AUSWAHL.read_text(encoding="utf-8"))["records"]
    if not ANTWORTEN.exists():
        print(f"FEHLER: {ANTWORTEN} fehlt. Lege je Record <record>_antwort.json ab.", flush=True)
        return 2

    zeilen, details = [], []
    vorhanden = 0
    for eintrag in auswahl:
        rid = eintrag["record_id"]
        datei = ANTWORTEN / f"{dateiname(rid)}_antwort.json"
        loesung = json.loads((LOESUNGEN / f"{dateiname(rid)}_loesung.json").read_text(encoding="utf-8"))
        gold = loesung["gold_zellen"]
        if not datei.exists():
            zeilen.append(f"| `{rid}` | - | {len(gold)} | - | - | - | - | fehlt |")
            continue
        vorhanden += 1
        zellen, hinweis = zellen_aus_antwort(datei.read_text(encoding="utf-8"))
        b = bilanz(gold, zellen)
        wert = f1(b["tp"], b["fp"], b["fn"])
        details.append(
            {
                "record_id": rid,
                "gold_im_text": loesung["goldwerte_im_text"]["status"],
                **b,
                "f1": None if wert is None else round(wert, 4),
                "zellen": len(zellen),
                "hinweis": hinweis,
            }
        )
        zeilen.append(
            f"| `{rid}` | {len(zellen)} | {len(gold)} | {b['tp']} | {b['fp']} | {b['fn']} | "
            f"{'-' if wert is None else f'{wert:.3f}'} | {loesung['goldwerte_im_text']['status']} |"
        )

    tp = sum(d["tp"] for d in details)
    fp = sum(d["fp"] for d in details)
    fn = sum(d["fn"] for d in details)
    gesamt = f1(tp, fp, fn)
    mit_text = [d for d in details if d["gold_im_text"] == "ja"]
    ohne_text = [d for d in details if d["gold_im_text"] == "nein"]

    def summe(teil: list[dict]) -> dict:
        t = sum(d["tp"] for d in teil)
        p = sum(d["fp"] for d in teil)
        n = sum(d["fn"] for d in teil)
        return {"records": len(teil), "tp": t, "fp": p, "fn": n, "f1": None if f1(t, p, n) is None else round(f1(t, p, n), 4)}

    ergebnis = {
        "stand": "2026-11-21",
        "toleranz": TOLERANZ,
        "antworten_vorhanden": vorhanden,
        "records_erwartet": len(auswahl),
        "gesamt": summe(details),
        "gold_im_text_ja": summe(mit_text),
        "gold_im_text_nein": summe(ohne_text),
        "details": details,
    }
    (TEST / "bewertung_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    tabelle = (
        "# Bewertung der Fremdmodell-Antworten (21.11.2026)\n\n"
        f"Antworten vorhanden: {vorhanden} von {len(auswahl)}. "
        f"Treffer bei `(field, arm)` und `|Differenz| < {TOLERANZ}`.\n\n"
        "| Record | Zellen | Gold | TP | FP | FN | F1 | Gold im Text |\n"
        "|---|---:|---:|---:|---:|---:|---:|:---:|\n"
        + "\n".join(zeilen)
        + "\n\n## Summen\n\n"
        "| Teilmenge | Records | TP | FP | FN | F1 |\n|---|---:|---:|---:|---:|---:|\n"
        + f"| alle | {ergebnis['gesamt']['records']} | {tp} | {fp} | {fn} | "
        + ("-" if gesamt is None else f"{gesamt:.4f}") + " |\n"
        + f"| Gold im Text = ja | {ergebnis['gold_im_text_ja']['records']} | {ergebnis['gold_im_text_ja']['tp']} | "
        f"{ergebnis['gold_im_text_ja']['fp']} | {ergebnis['gold_im_text_ja']['fn']} | "
        + ("-" if ergebnis["gold_im_text_ja"]["f1"] is None else f"{ergebnis['gold_im_text_ja']['f1']:.4f}") + " |\n"
        + f"| Gold im Text = nein | {ergebnis['gold_im_text_nein']['records']} | {ergebnis['gold_im_text_nein']['tp']} | "
        f"{ergebnis['gold_im_text_nein']['fp']} | {ergebnis['gold_im_text_nein']['fn']} | "
        + ("-" if ergebnis["gold_im_text_nein"]["f1"] is None else f"{ergebnis['gold_im_text_nein']['f1']:.4f}") + " |\n"
        + "\nBei `Gold im Text = nein` steht kein Goldwert im Dokumenttext (Werte nur in "
        "Bildtabellen oder Anhaengen); dort ist eine leere Zellenliste die richtige Antwort. "
        "Die Teilmenge misst deshalb die Dokumentaufbereitung, nicht die Extraktion.\n"
    )
    (TEST / "BEWERTUNG.md").write_text(tabelle, encoding="utf-8", newline="\n")

    print(f"Antworten: {vorhanden} von {len(auswahl)}")
    print(f"Gesamt: TP {tp}, FP {fp}, FN {fn}, F1 {'-' if gesamt is None else f'{gesamt:.4f}'}")
    print(f"Gold im Text ja: F1 {ergebnis['gold_im_text_ja']['f1']}, nein: {ergebnis['gold_im_text_nein']['f1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
