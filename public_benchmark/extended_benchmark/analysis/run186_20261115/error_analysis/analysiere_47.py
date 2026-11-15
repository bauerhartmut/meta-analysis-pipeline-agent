#!/usr/bin/env python3
"""Systematische Fehleranalyse der 47 v7-Records (read-only, ohne API).

Liest die vorhandenen Ergebnisdateien und die Golddaten, rekonstruiert je Record
den v6- und v7-Status und schreibt eine CSV plus eine Kennzahlendatei. Es wird
nichts ueberschrieben und kein Modell aufgerufen.

Aufruf:

    python .../error_analysis/analysiere_47.py
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parents[2]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402
from extended_benchmark import run_extended_extraction as runner  # noqa: E402
from extended_benchmark.analyze_errors import GEPRUEFTE_FAELLE  # noqa: E402
from extended_benchmark.evaluate_extended import _close  # noqa: E402
from extended_benchmark.evaluate_fallback import belegstufe, klassifiziere, normalisiere  # noqa: E402

V6 = BENCH / "runs" / "yun_test186_v6_20261115" / "predictions.jsonl"
V7 = BENCH / "runs" / "yun_test186_v7_folgelauf_20261116" / "predictions.jsonl"
RECORDS = BENCH / "records" / "yun_test186.jsonl"
FOLGE_IDS = BENCH / "analysis" / "run186_20261115" / "folge_ids.txt"
KEIN_KOMPARATOR = {"yun2024:149", "yun2024:150"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def record_werte(record: dict[str, Any], vorhersage: dict[str, Any]) -> dict[str, Any]:
    """Zellmetriken eines Records gegen Gold."""
    gold = {(c["field"], c.get("arm")): float(c["value"]) for c in record["gold"]["cells"]}
    cells = (vorhersage.get("predicted") or {}).get("cells") or []
    ziel = normalisiere((record.get("timepoint") or {}).get("target") or "")
    ergebnis = Counter()
    gesehen: set[tuple[str, str | None]] = set()
    for cell in cells:
        key = (cell["field"], cell.get("arm"))
        label, stufe = belegstufe(cell.get("timepoint") or "", ziel, "")
        if key not in gold:
            ergebnis["ueberzaehlig"] += 1
            continue
        gesehen.add(key)
        if _close(cell["value"], gold[key], 1e-6, 0.0):
            ergebnis["treffer"] += 1
        else:
            ergebnis["falscher_wert"] += 1
        if label and stufe in ("gedruckt", "artikel", "ziel"):
            ergebnis[klassifiziere(ziel, label) if ziel else "ohne_ziel"] += 1
        elif stufe == "unklar":
            ergebnis["zeitpunkt_unklar"] += 1
    ergebnis["auslassung"] = len([key for key in gold if key not in gesehen])
    ergebnis["gold"] = len(gold)
    return dict(ergebnis)


def text_und_prompt(record: dict[str, Any]) -> tuple[int, int]:
    pfad = (record.get("document") or {}).get("path") or ""
    text = (REPO / pfad).read_text(encoding="utf-8", errors="replace") if pfad and (REPO / pfad).exists() else ""
    ziel = str(((record.get("timepoint") or {}).get("target")) or "")
    prompt = runner.build_prompt(record, text, target_timepoint=ziel or None, fallback=True, cell_timepoint=True)
    return len(text), len(prompt)


def kategorien(zeile: dict[str, Any]) -> str:
    """Ordnet Fehlerkategorien nach A/B/C zu; nur belegte Zuordnungen."""
    teile: list[str] = []
    if zeile["v7_status"] == "length":
        teile.append("A:length_abbruch")
    elif zeile["v7_zellen"] == 0:
        teile.append("A:leere_ausgabe")
    # Extraktionsfehler nur dort, wo ueberhaupt Zellen vorliegen; sonst waeren
    # alle Goldzellen eines technischen Ausfalls kuenstlich "Auslassungen".
    if zeile["v7_zellen"]:
        if zeile["falscher_wert"]:
            teile.append("B:falscher_wert")
        if zeile.get("rueckfall"):
            teile.append("B:rueckfall_zeitpunkt")
        if zeile["zeitpunkt_unklar"]:
            teile.append("B:zeitpunkt_unklar")
        if zeile["ueberzaehlig"]:
            teile.append("B:ueberzaehlige_zelle")
        if zeile["auslassung"]:
            teile.append("B:auslassung")
    if zeile["gold_konflikt"] == "ja":
        teile.append("C:gold_konflikt")
    if zeile["record_id"] in KEIN_KOMPARATOR:
        teile.append("C:komparator_nur_baseline")
    return ";".join(teile)


def main() -> int:
    ids = [teil for teil in FOLGE_IDS.read_text(encoding="utf-8").split(",") if teil.strip()]
    records = {str(r["record_id"]): r for r in read_jsonl(RECORDS)}
    v6 = {str(r["record_id"]): r for r in read_jsonl(V6)}
    v7 = {str(r["record_id"]): r for r in read_jsonl(V7)}

    zeilen: list[dict[str, Any]] = []
    for record_id in ids:
        record = records.get(record_id)
        if record is None:  # pragma: no cover - Sicherheitsnetz
            raise SystemExit(f"Record fehlt: {record_id}")
        alt, neu = v6.get(record_id, {}), v7.get(record_id, {})
        werte = record_werte(record, neu) if neu else {}
        texte, prompt = text_und_prompt(record)
        ziel = str(((record.get("timepoint") or {}).get("target")) or "")
        treffer = werte.get("treffer", 0)
        falsch = werte.get("falscher_wert", 0)
        zeile = {
            "record_id": record_id,
            "dokument": (record["document"]["path"] or "").split("/")[-1].replace(".md", ""),
            "ziel": ziel,
            "text_zeichen": texte,
            "prompt_zeichen": prompt,
            "v6_status": "length" if alt.get("fehlerklasse") == "length_ohne_ergebnis" else ("zellen" if alt.get("rows") else "leer"),
            "v6_tokens": int(alt.get("completion_tokens") or 0),
            "v6_zellen": len(alt.get("rows") or []),
            "v7_status": "length" if neu.get("fehlerklasse") == "length_ohne_ergebnis" else ("zellen" if neu.get("rows") else "leer"),
            "v7_tokens": int(neu.get("completion_tokens") or 0),
            "v7_zellen": len(neu.get("rows") or []),
            "v7_content_len": int(neu.get("content_len") or 0),
            "v7_finish": neu.get("finish_reason") or "",
            "v7_parse_error": neu.get("parse_error") or "",
            "v7_header": neu.get("timepoint_header") or "",
            "v7_fallback": neu.get("fallback"),
            "gold": werte.get("gold", len(record["gold"]["cells"])),
            "treffer": treffer,
            "falscher_wert": falsch,
            "ueberzaehlig": werte.get("ueberzaehlig", 0),
            "auslassung": werte.get("auslassung", 0),
            "zieltreu": werte.get("zieltreu", 0),
            "rueckfall": werte.get("rueckfall", 0),
            "zeitpunkt_unklar": werte.get("zeitpunkt_unklar", 0),
            "precision": round(treffer / (treffer + falsch + werte.get("ueberzaehlig", 0)), 4) if (treffer + falsch + werte.get("ueberzaehlig", 0)) else "",
            "recall": round(treffer / werte.get("gold", 1), 4) if werte.get("gold") else "",
            "zell_f1": round(2 * treffer / (2 * treffer + falsch + werte.get("ueberzaehlig", 0) + werte.get("auslassung", 0)), 4)
            if treffer or falsch or werte.get("auslassung")
            else "",
            "gold_konflikt": "ja" if any(schluessel[0] == record_id for schluessel in GEPRUEFTE_FAELLE) else "nein",
            "tokens_gesamt": int(alt.get("completion_tokens") or 0) + int(neu.get("completion_tokens") or 0),
        }
        zeile["kategorien"] = kategorien(zeile)
        zeilen.append(zeile)

    felder = [
        "record_id", "dokument", "ziel", "text_zeichen", "prompt_zeichen",
        "v6_status", "v6_tokens", "v6_zellen",
        "v7_status", "v7_tokens", "v7_zellen", "v7_content_len", "v7_finish", "v7_parse_error",
        "v7_header", "v7_fallback",
        "gold", "treffer", "falscher_wert", "ueberzaehlig", "auslassung",
        "zieltreu", "rueckfall", "zeitpunkt_unklar", "precision", "recall", "zell_f1",
        "gold_konflikt", "tokens_gesamt", "kategorien",
    ]
    with (HIER / "fehlerklassifikation_47_records.csv").open("w", encoding="utf-8", newline="") as handle:
        schreiber = csv.DictWriter(handle, fieldnames=felder, delimiter=";")
        schreiber.writeheader()
        for zeile in zeilen:
            schreiber.writerow({feld: zeile.get(feld, "") for feld in felder})

    def prozent(zaehler: int, nenner: int) -> float:
        return round(zaehler / nenner, 4) if nenner else 0.0

    length = [z for z in zeilen if z["v7_status"] == "length"]
    mit_zellen = [z for z in zeilen if z["v7_status"] == "zellen"]
    leer = [z for z in zeilen if z["v7_status"] == "leer"]
    fehlende_texte = [z["record_id"] for z in zeilen if z["text_zeichen"] == 0]

    def quote_je(gruppe: list[dict[str, Any]], feld: str) -> dict[str, dict[str, float]]:
        eimer: dict[str, list[dict[str, Any]]] = {}
        for zeile in gruppe:
            eimer.setdefault(str(zeile[feld]), []).append(zeile)
        return {
            wert: {
                "records": len(liste),
                "length": sum(1 for z in liste if z["v7_status"] == "length"),
                "quote": prozent(sum(1 for z in liste if z["v7_status"] == "length"), len(liste)),
            }
            for wert, liste in sorted(eimer.items())
        }

    def textkorb(z: dict[str, Any]) -> str:
        laenge = z["text_zeichen"]
        if laenge < 8000:
            return "< 8k"
        if laenge < 16000:
            return "8-16k"
        if laenge < 24000:
            return "16-24k"
        return ">= 24k"

    dokumente = Counter(z["dokument"] for z in length)
    kennzahlen = {
        "records": len(zeilen),
        "status_v7": {"zellen": len(mit_zellen), "leer": len(leer), "length": len(length)},
        "tokens": {
            "v6": sum(z["v6_tokens"] for z in zeilen),
            "v7": sum(z["v7_tokens"] for z in zeilen),
            "gesamt": sum(z["tokens_gesamt"] for z in zeilen),
            "length_v7": sum(z["v7_tokens"] for z in length),
            "length_anteil_v7": prozent(sum(z["v7_tokens"] for z in length), sum(z["v7_tokens"] for z in zeilen)),
        },
        "zellen": {
            "gold": sum(z["gold"] for z in zeilen),
            "extrahiert": sum(z["v7_zellen"] for z in zeilen),
            "treffer": sum(z["treffer"] for z in zeilen),
            "falscher_wert": sum(z["falscher_wert"] for z in zeilen),
            "auslassung": sum(z["auslassung"] for z in zeilen),
            "ueberzaehlig": sum(z["ueberzaehlig"] for z in zeilen),
            "precision": prozent(
                sum(z["treffer"] for z in zeilen),
                sum(z["treffer"] + z["falscher_wert"] + z["ueberzaehlig"] for z in zeilen),
            ),
            "recall": prozent(sum(z["treffer"] for z in zeilen), sum(z["gold"] for z in zeilen)),
        },
        "zeitpunkte": {
            "zieltreu": sum(z["zieltreu"] for z in zeilen),
            "rueckfall": sum(z["rueckfall"] for z in zeilen),
            "unklar": sum(z["zeitpunkt_unklar"] for z in zeilen),
        },
        "kategorien": dict(Counter(teil for z in zeilen for teil in z["kategorien"].split(";") if teil)),
        "length_details": [
            {
                "record_id": z["record_id"],
                "dokument": z["dokument"],
                "ziel": z["ziel"],
                "text_zeichen": z["text_zeichen"],
                "prompt_zeichen": z["prompt_zeichen"],
                "v6_tokens": z["v6_tokens"],
                "v7_tokens": z["v7_tokens"],
                "v7_content_len": z["v7_content_len"],
                "v7_parse_error": z["v7_parse_error"],
                "tokens_gesamt": z["tokens_gesamt"],
            }
            for z in sorted(length, key=lambda z: -z["tokens_gesamt"])
        ],
        "length_nach_dokument": dict(dokumente.most_common()),
        "length_nach_textkorb": quote_je([{**z, "korb": textkorb(z)} for z in zeilen], "korb"),
        "length_nach_ziel": quote_je(zeilen, "ziel"),
        "length_nach_gold": quote_je(zeilen, "gold"),
        "length_content_len": dict(Counter(z["v7_content_len"] for z in length)),
        "length_parse_error": dict(Counter(z["v7_parse_error"] for z in length)),
        "length_tokens": dict(Counter(z["v7_tokens"] for z in length)),
        "mit_zellen_metrics": {
            "records": len(mit_zellen),
            "precision": prozent(
                sum(z["treffer"] for z in mit_zellen),
                sum(z["treffer"] + z["falscher_wert"] + z["ueberzaehlig"] for z in mit_zellen),
            ),
            "recall": prozent(sum(z["treffer"] for z in mit_zellen), sum(z["gold"] for z in mit_zellen)),
            "median_prompt": statistics.median([z["prompt_zeichen"] for z in mit_zellen]),
        },
        "length_prompt_median": statistics.median([z["prompt_zeichen"] for z in length]),
        "prompt_median_alle": statistics.median([z["prompt_zeichen"] for z in zeilen]),
        "gold_konflikte": [z["record_id"] for z in zeilen if z["gold_konflikt"] == "ja"],
        "fehlende_texte": fehlende_texte,
        "kosten_je_gerettetem_record": round(sum(z["v7_tokens"] for z in zeilen) / max(1, len(mit_zellen)), 0),
    }
    (HIER / "kennzahlen.json").write_text(json.dumps(kennzahlen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in kennzahlen.items() if k not in ("length_details",)}, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
