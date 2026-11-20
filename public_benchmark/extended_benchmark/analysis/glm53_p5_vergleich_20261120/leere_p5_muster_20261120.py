#!/usr/bin/env python
"""Die 33 leeren P5-Records: Zeigt sich dort dasselbe Muster wie auf yun2024:523?

Auf `yun2024:523` hat Stufe 1 das Budget im Reasoning verbraucht, ohne zu
antworten, weil das erste Wertepaar in einem Satz mit mehreren Paaren steht und
es dort kein Zeilenlabel zum Zitieren gibt. Diese Pruefung misst offline, ob die
33 Records ohne Inhalt dieselbe Textlage haben:

- steht der Goldwert in einer Tabellenzeile (Zeilenanker vorhanden),
- steht er nur in Prosa, und enthaelt dieser Satz mehrere Wertepaare
  (mehr als ein "+-", also keine eindeutige Zeile),
- steht er nur in Prosa mit genau einem Wertepaar,
- oder steht er gar nicht im Text.

Rein lesend: Predictions des P5-Laufs, Gold-Datensatz und Dokumenttexte werden
nur gelesen. Kein Modellaufruf, keine Prediction geschrieben.

Aufruf:
    .venv/bin/python analysis/glm53_p5_vergleich_20261120/leere_p5_muster_20261120.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402

SATZ_TRENNER = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
#: Ein Wertepaar je Arm sind mindestens vier Zahlen im selben Satz (zwei je Arm);
#: bei binaeren Outcomes stehen dort Anteile ohne "+-".
ZAHL = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d])")


def saetze(text: str) -> list[tuple[int, int]]:
    """Gibt (start, ende) je Satz zurueck, ohne den Text zu veraendern."""
    stellen = [0] + [t.start() for t in SATZ_TRENNER.finditer(text)] + [len(text)]
    return [(stellen[i], stellen[i + 1]) for i in range(len(stellen) - 1)]


def wert_treffer(text: str, wert: float) -> list[int]:
    muster = r"(?<![\d.])" + re.escape(str(wert)) + r"(?![\d])"
    return [m.start() for m in re.finditer(muster, text)]


def zeile_ist_tabelle(text: str, pos: int) -> bool:
    start = text.rfind("\n", 0, pos) + 1
    ende = text.find("\n", pos)
    zeile = text[start: ende if ende != -1 else len(text)]
    return zeile.lstrip().startswith("|")


def satz_um(text: str, pos: int, spanne: list[tuple[int, int]]) -> str:
    for start, ende in spanne:
        if start <= pos < ende:
            return text[start:ende]
    return ""


def klassifiziere(text: str, werte: list[float]) -> dict[str, Any]:
    spanne = saetze(text)
    befund = []
    fehlend = []
    for wert in werte:
        stellen = wert_treffer(text, wert)
        if not stellen:
            fehlend.append(wert)
            befund.append({"wert": wert, "gefunden": 0, "tabelle": 0, "prosa": 0,
                           "satz_pm_max": 0, "satz": ""})
            continue
        in_tabelle = [p for p in stellen if zeile_ist_tabelle(text, p)]
        in_prosa = [p for p in stellen if p not in in_tabelle]
        saetze_mit = [satz_um(text, p, spanne) for p in in_prosa]
        pm_max = max((s.count("+-") + s.count("±") for s in saetze_mit), default=0)
        zahlen_max = max((len(ZAHL.findall(s)) for s in saetze_mit), default=0)
        befund.append({
            "wert": wert,
            "gefunden": len(stellen),
            "tabelle": len(in_tabelle),
            "prosa": len(in_prosa),
            "satz_pm_max": pm_max,
            "satz_zahlen_max": zahlen_max,
            "mehrfach": bool(pm_max >= 2 or zahlen_max >= 4),
            "satz": (max(saetze_mit, key=len) if saetze_mit else "").strip()[:400],
        })

    gefunden = [b for b in befund if b["gefunden"]]
    if not gefunden:
        klasse = "fehlt_im_text"
    else:
        hat_tabelle = any(b["tabelle"] for b in gefunden)
        hat_prosa_mehrfach = any(b["prosa"] and b["mehrfach"] for b in gefunden)
        hat_prosa_einzeln = any(b["prosa"] and not b["mehrfach"] for b in gefunden)
        if hat_tabelle and (hat_prosa_mehrfach or hat_prosa_einzeln):
            klasse = "gemischt"
        elif hat_tabelle:
            klasse = "tabelle"
        elif hat_prosa_mehrfach:
            klasse = "prosa_mehrfachpaar"
        elif hat_prosa_einzeln:
            klasse = "prosa_einzelpaar"
        else:
            klasse = "unklar"
    return {"klasse": klasse, "befund": befund, "fehlend": fehlend,
            "werte_gesamt": len(werte), "werte_gefunden": len(gefunden)}


def main() -> int:
    leere = []
    with v.P5.open(encoding="utf-8") as handle:
        for zeile in handle:
            if not zeile.strip():
                continue
            row = json.loads(zeile)
            if row.get("content_chars") == 0 or not (row.get("content") or "").strip():
                leere.append(row)
    print(f"leere P5-Records: {len(leere)}")

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ergebnis: dict[str, Any] = {"quelle": str(v.P5), "n": len(leere), "faelle": {}}
    zaehler: Counter[str] = Counter()
    ohne_tabelle = 0

    for row in leere:
        rid = row.get("record_id")
        record = records.get(rid)
        if not record:
            ergebnis["faelle"][rid] = {"klasse": "kein_gold_record"}
            zaehler["kein_gold_record"] += 1
            continue
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        gold = (record.get("gold") or {}).get("cells") or []
        werte = sorted({round(float(z["value"]), 6) for z in gold
                        if z.get("value") is not None})
        if not text:
            ergebnis["faelle"][rid] = {"klasse": "kein_text", "dokument": pfad.name}
            zaehler["kein_text"] += 1
            continue
        befund = klassifiziere(text, werte)
        pipe = sum(1 for zeile in text.splitlines() if zeile.lstrip().startswith("|"))
        if pipe == 0:
            ohne_tabelle += 1
        if befund["fehlend"]:
            zaehler["mit_fehlendem_wert"] += 1
        ergebnis["faelle"][rid] = {
            "dokument": (record.get("document") or {}).get("id"),
            "outcome_typ": (record.get("context") or {}).get("outcome_type"),
            "goldzellen": len(gold),
            "text_zeichen": len(text),
            "pipe_zeilen": pipe,
            "reasoning": row.get("reasoning_chars"),
            "klasse": befund["klasse"],
            "werte_gesamt": befund["werte_gesamt"],
            "werte_gefunden": befund["werte_gefunden"],
            "werte_fehlend": befund["fehlend"],
            "befund": befund["befund"],
        }
        zaehler[befund["klasse"]] += 1

    ergebnis["klassen"] = dict(zaehler)
    ergebnis["ohne_pipe_tabelle"] = ohne_tabelle

    print("Klassen:", dict(zaehler))
    print("ohne Pipe-Tabelle:", ohne_tabelle, "von", len(leere))
    print()
    print("| Record | Dokument | Text | Werte gef./ges. | Klasse | Saetze mit mehreren Paaren |")
    print("|---|---|---:|---|---:|")
    for rid, fall in ergebnis["faelle"].items():
        if "klasse" not in fall:
            continue
        mehrfach = sum(1 for b in fall.get("befund", []) if b["prosa"] and b["mehrfach"])
        print(f"| `{rid}` | {fall.get('dokument', '')} | {fall.get('text_zeichen', 0)} | "
              f"{fall.get('werte_gefunden', 0)}/{fall.get('werte_gesamt', 0)} | "
              f"{fall['klasse']} | {mehrfach} |")

    (HIER / "leere_p5_muster_20261120.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\ngeschrieben:", HIER / "leere_p5_muster_20261120.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
