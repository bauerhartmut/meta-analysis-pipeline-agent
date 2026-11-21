#!/usr/bin/env python3
"""Phase 3: Record yun2024:30 als Proof of Concept, offline nachgerechnet.

Die Kette auf diesem Record wurde am 20.11.2026 mit Netzaufrufen gefahren
(Tabellenfenster, Zeilenbindung, Stufe 2; F1 1,0). Dieses Skript liest die
gespeicherten Antworten, versieht jede Zelle mit einer konkreten Fundstelle im
Dokument und prueft die deterministische Validierung darauf.

Erwartung: sechs Zellen, F1 1,0 vorher, F1 1,0 nachher (keine Regression), jede
Zelle mit Fundstelle.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/record30_kette_20261121.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
BENCH = ANALYSE.parent
REPO = BENCH.parent.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
import validiere_zellen_20261121 as vz  # noqa: E402

LAUF = ANALYSE / "glm53_p5_vergleich_20261120" / "zweistufig_lauf_20261120"
STUFE2 = LAUF / "predictions_stufe2_zeile_30_qwen_8000.jsonl"
STUFE1 = LAUF / "predictions_tabelle_zeile_30_qwen_16000.jsonl"
RECORD = "yun2024:30"


def lies(pfad: Path) -> list[dict[str, Any]]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def fundstelle(zelle: dict[str, Any], text: str) -> dict[str, Any]:
    """Konkrete Fundstelle einer Zelle: Position, Zeile und Textausschnitt."""
    wert = v.zahl(zelle.get("value"))
    stellen = vz.zahl_positionen(wert, text) if wert is not None else []
    if not stellen:
        return {"position": None, "zeile": "", "ausschnitt": "", "belegt": False}
    pos = stellen[0]
    anfang = text.rfind("\n", 0, max(0, pos - 1)) + 1
    ende = text.find("\n", pos)
    zeile = text[anfang : ende if ende != -1 else len(text)].strip()
    return {
        "position": pos,
        "zeile": zeile[:200],
        "ausschnitt": text[max(0, pos - 60) : pos + 60].replace("\n", " "),
        "belegt": True,
    }


def main() -> int:
    record = next(r for r in v.lade(v.RECORDS) if r["record_id"] == RECORD)
    text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
    stufe2 = lies(STUFE2)[0]
    zellen = list(stufe2.get("cells") or v.zellen(stufe2) or [])
    stufe1 = lies(STUFE1)[0] if STUFE1.exists() else {}
    locators = (stufe1.get("locators") or (stufe1.get("stufe1") or {}).get("locators") or [])

    for zelle in zellen:
        zelle["fundstelle"] = fundstelle(zelle, text)

    gold = (record.get("gold") or {}).get("cells") or []
    vorher = v.bilanz_p5(gold, zellen)
    sauber, verworfen, befund = vz.validiere(zellen, text)
    nachher = v.bilanz_p5(gold, sauber)

    def f1(b: dict[str, int]) -> float:
        p = b["tp"] / (b["tp"] + b["fp"]) if b["tp"] + b["fp"] else 0.0
        r = b["tp"] / (b["tp"] + b["fn"]) if b["tp"] + b["fn"] else 0.0
        return 2 * p * r / (p + r) if p + r else 0.0

    ergebnis = {
        "stand": "2026-11-21",
        "record_id": RECORD,
        "stufe1_locators": locators,
        "stufe2_zellen": zellen,
        "gold": gold,
        "bilanz_vorher": vorher,
        "bilanz_nachher": nachher,
        "f1_vorher": round(f1(vorher), 4),
        "f1_nachher": round(f1(nachher), 4),
        "validierung": befund,
        "fundstellen_belegt": sum(1 for z in zellen if z["fundstelle"]["belegt"]),
    }
    (HIER / "record30_kette_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    zeilen = "\n".join(
        f"| {z.get('field')} | {z.get('arm')} | {z.get('value')} | "
        f"{'ja' if z['fundstelle']['belegt'] else 'nein'} | "
        f"{(z['fundstelle']['zeile'] or '')[:70]} |"
        for z in zellen
    )
    bericht = (
        "# Record yun2024:30, Kette offline nachgerechnet (21.11.2026)\n\n"
        "Gelesen werden die gespeicherten Antworten der Stufe 1 (Zeilenbindung) und der\n"
        "Stufe 2 aus `zweistufig_lauf_20261120/`. Kein Modellaufruf.\n\n"
        "## Stufe 1 (gespeichert)\n\n"
        + (
            "\n".join(
                f"- Arm {l.get('arm')}: Zeile `{l.get('zeilenlabel')}`, Spalte `{l.get('spaltenkopf')}`, "
                f"Zeitpunkt `{l.get('timepoint')}`"
                for l in locators
            )
            or "- keine Locators gespeichert"
        )
        + "\n\n## Stufe 2, Zellen mit Fundstelle\n\n"
        "| Feld | Arm | Wert | Fundstelle belegt | Zeile im Dokument |\n|---|---|---:|:---:|---|\n"
        f"{zeilen}\n\n"
        f"Fundstellen belegt: {ergebnis['fundstellen_belegt']} von {len(zellen)}.\n\n"
        "## Bilanz\n\n"
        f"| Stand | TP | FP | FN | F1 |\n|---|---:|---:|---:|---:|\n"
        f"| vorher | {vorher['tp']} | {vorher['fp']} | {vorher['fn']} | {f1(vorher):.4f} |\n"
        f"| nach Validierung | {nachher['tp']} | {nachher['fp']} | {nachher['fn']} | {f1(nachher):.4f} |\n\n"
        f"Verworfen: {len(verworfen)} Zellen.\n\n"
        "## Was der Fall zeigt\n\n"
        "Die Kette traegt auf diesem Record: Zeile `Mean score (SD)`, Wochenblock 52,\n"
        "sechs Zellen, F1 1,0, jede Zelle im Text belegt. Die Validierung aendert nichts,\n"
        "weil keine Zelle gegen eine strukturelle Regel verstoesst. Das ist die\n"
        "Referenz fuer die Frage, ob eine Verallgemeinerung Regressionen erzeugt: hier\n"
        "darf keine entstehen.\n\n"
        "Grenzen: ein Record, ein Modell (qwen 3.5 397b), gespeicherte Antworten vom\n"
        "20.11.2026. Die Fundstelle ist die erste Fundstelle der Zahl im Dokument, nicht\n"
        "notwendig die vom Modell gelesene; bei mehrfach gedruckten Zahlen ist sie daher\n"
        "nur ein Beleg, dass die Zahl im Artikel steht.\n"
    )
    (HIER / "record30_kette_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print("Zellen:", len(zellen), "| Fundstellen:", ergebnis["fundstellen_belegt"])
    print("vorher:", vorher, "F1", round(f1(vorher), 4))
    print("nachher:", nachher, "F1", round(f1(nachher), 4), "| verworfen", len(verworfen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
