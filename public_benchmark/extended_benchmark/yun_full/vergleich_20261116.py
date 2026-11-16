#!/usr/bin/env python
"""Zentrale Vergleichsdatei: alle Laeufe des 16.11.2026 in einer Tabelle.

Berechnet die Kennzahlen einheitlich aus `predictions.jsonl` und den Goldzellen,
damit die Zahlen im Bericht nachpruefbar sind. Definitionen:

* Precision = richtige Zellen / (richtige + falsche Zellen). Zellen ohne
  Goldannotation zaehlen nicht als falsch, werden aber mitgezaehlt.
* Recall = richtige Zellen / alle Goldzellen (fehlende und falsche zaehlen als
  nicht erinnert). Das ist die Zaehlweise von `auswerte_yun699.py`.
* F1 = 2PR/(P+R).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"

LAEUFE = [
    ("yun699_test60_20261116", "GLM-5.3 v7, 60 Records, 4000 Tokens", "glm"),
    ("yun20_4000_glm_20261116", "GLM-5.3 v7, 20 Records, 4000 Tokens", "glm"),
    ("yun20_4000_qwen_20261116", "Qwen3.5-397B v7, 20 Records, 4000 Tokens", "qwen"),
    ("yun20_4000_qwen30_20261116", "Qwen3-30B v7, 20 Records, 4000 Tokens", "qwen30"),
    ("yun20_4000_glm_gskcb_20261116", "GLM-5.3 v7 + Gruppengroessenregel, 20 Records, 4000 Tokens", "glm"),
    ("yun20_8000_glm_cb_20261116", "GLM-5.3 v7, 20 Records, 8000 Tokens, frisch generiert", "glm"),
    ("yun20_8000_qwen_cb_20261116", "Qwen3.5-397B v7, 20 Records, 8000 Tokens, frisch generiert", "qwen"),
    ("yun20_8000_qwen30_cb_20261116", "Qwen3-30B v7, 20 Records, 8000 Tokens, frisch generiert", "qwen30"),
    ("yun20_8000_glm_v8_20261116", "GLM-5.3 v8 (Quellenzeile im Prompt), 20 Records, 8000 Tokens", "glm"),
]


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def kennzahlen(run: str) -> dict:
    rows = lies(RUNS / run / "predictions.jsonl")
    recs = {r["record_id"]: r for r in lies(HERE / "records" / "yun699.jsonl")}
    richtig = falsch = fehlend = ohne_gold = 0
    je_feld: dict[str, dict[str, int]] = {}
    for row in rows:
        gold = {c["field"]: c["value"] for c in recs[row["record_id"]]["gold"]["cells"]}
        pred: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            pred.setdefault(zelle["field"], zelle["value"])
        for feld, wert in gold.items():
            eintrag = je_feld.setdefault(feld, {"richtig": 0, "falsch": 0, "fehlend": 0})
            m = pred.get(feld)
            if m is None:
                fehlend += 1
                eintrag["fehlend"] += 1
            elif abs(m - wert) > 1e-9:
                falsch += 1
                eintrag["falsch"] += 1
            else:
                richtig += 1
                eintrag["richtig"] += 1
        ohne_gold += sum(1 for feld in pred if feld not in gold)
    p = richtig / (richtig + falsch) if richtig + falsch else None
    r = richtig / (richtig + falsch + fehlend) if richtig + falsch + fehlend else None
    f1 = 2 * p * r / (p + r) if p and r else None
    klassen: dict[str, int] = {}
    for row in rows:
        k = row.get("fehlerklasse") or "ok"
        klassen[k] = klassen.get(k, 0) + 1
    tokens = sum(row.get("completion_tokens") or 0 for row in rows)
    return {
        "run": run,
        "records": len(rows),
        "goldzellen": richtig + falsch + fehlend,
        "richtig": richtig,
        "falsch": falsch,
        "fehlend": fehlend,
        "zellen_ohne_gold": ohne_gold,
        "precision": round(p, 4) if p else None,
        "recall": round(r, 4) if r else None,
        "f1": round(f1, 4) if f1 else None,
        "tokens_output": tokens,
        "tokens_pro_richtiger_zelle": round(tokens / richtig, 1) if richtig else None,
        "zeit_summe_s": round(sum(row.get("elapsed_s") or 0 for row in rows)),
        "cached": sum(1 for row in rows if row.get("suspected_cache")),
        "fehlerklassen": klassen,
        "je_feld": je_feld,
        "modell": sorted({row.get("model_id") or "" for row in rows}),
    }


def main() -> int:
    ergebnis = []
    for run, label, modell in LAEUFE:
        if not (RUNS / run / "predictions.jsonl").exists():
            continue
        ergebnis.append({"label": label, "modell": modell, **kennzahlen(run)})
    ziel = HERE / "vergleich_20261116.json"
    ziel.write_text(json.dumps({"stand": "2026-11-16", "laeufe": ergebnis}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{ziel} ({len(ergebnis)} Laeufe)")
    for eintrag in ergebnis:
        print(
            f"  {eintrag['run']:<34} n={eintrag['records']:<3} "
            f"P={eintrag['precision']} R={eintrag['recall']} F1={eintrag['f1']} "
            f"({eintrag['richtig']}/{eintrag['falsch']}/{eintrag['fehlend']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
