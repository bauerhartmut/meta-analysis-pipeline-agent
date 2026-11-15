#!/usr/bin/env python3
"""Diagnose der Length-Ausfaelle ohne API-Aufrufe (Phase 0).

Liest eine abgeschlossene ``predictions.jsonl`` und die zugehoerigen Records und
beantwortet drei Fragen, ohne einen Token zu verbrauchen:

1. Wie hoch ist das Limit, das die gueltigen Antworten brauchen?
   (Quantile p50/p90/p95/max der Completion-Tokens gueltiger Zeilen)
2. Haengen die Ausfaelle an einem Merkmal des Records?
   (Zieltyp, Zahl der Goldzellen, Textlaenge, Tabellenzahl, Zielzahl im Text)
3. Wie viele Tokens kostet ein Ausfall im Verhaeltnis zum Nutzen?

Die Merkmale werden am Median geteilt (bzw. ja/nein), die Ausfallquote je Gruppe
mit exaktem zweiseitigem Fisher-Test verglichen. Bei mehreren Merkmalen sind das
Mehrfachvergleiche: die p-Werte sind Hinweise, keine Beweise.

Aufruf:

    python public_benchmark/extended_benchmark/analysis/run186_20261115/laenge_diagnose.py \
        --run yun_test186_v6_20261115 \
        --records public_benchmark/extended_benchmark/records/yun_test186.jsonl \
        --out public_benchmark/extended_benchmark/analysis/run186_20261115/laenge_diagnose.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402

AUSFALL = "length_ohne_ergebnis"
ZEIT_EINHEIT = re.compile(r"^(week|month|day|year|hour)\b", re.I)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def quantil(werte: Iterable[float], q: float) -> float | None:
    """Quantil nach linearer Interpolation (gleiche Definition wie numpy)."""
    reihe = sorted(float(w) for w in werte)
    if not reihe:
        return None
    if len(reihe) == 1:
        return reihe[0]
    pos = (len(reihe) - 1) * q
    unten, oben = math.floor(pos), math.ceil(pos)
    if unten == oben:
        return reihe[int(pos)]
    return reihe[unten] + (reihe[oben] - reihe[unten]) * (pos - unten)


def fisher_exakt(a: int, b: int, c: int, d: int) -> float:
    """Zweiseitiger exakter Fisher-Test fuer die Tafel [[a, b], [c, d]]."""
    n = a + b + c + d
    if n == 0:
        return 1.0

    def p_von(x: int) -> float:
        return math.comb(a + b, x) * math.comb(c + d, a + c - x) / math.comb(n, a + c)

    unten = max(0, a + c - (c + d))
    oben = min(a + b, a + c)
    beobachtet = p_von(a)
    summe = 0.0
    for x in range(unten, oben + 1):
        p = p_von(x)
        if p <= beobachtet * (1 + 1e-9):
            summe += p
    return min(1.0, summe)


def zieltyp(target: str) -> str:
    """Einheit des Zielzeitpunkts; 'kein Ziel' wenn nichts annotiert ist."""
    text = (target or "").strip()
    if not text:
        return "kein Ziel"
    if "not stated" in text.lower():
        return "kein Ziel"
    if text.lower() == "baseline":
        return "baseline"
    treffer = ZEIT_EINHEIT.match(text)
    return treffer.group(1).lower() if treffer else "sonstiges"


def zielzahl_im_text(target: str, text: str) -> bool:
    """Steht der Zielzeitpunkt sinngemaess im Artikeltext?"""
    treffer = re.match(r"^(week|month|day)\s+(\d{1,3})$", (target or "").strip(), re.I)
    if not treffer:
        return False
    einheit, zahl = treffer.group(1).lower(), treffer.group(2)
    muster = [
        rf"\b{zahl}\s*[- ]?\s*{einheit}s?\b",
        rf"\b{einheit}\s*{zahl}\b",
        rf"\b{zahl}\s*[- ]\s*(week|month|day)\b",
    ]
    return any(re.search(m, text, re.I) for m in muster)


def _zellen_korb(zellen: int) -> str:
    """Feste Koerbe fuer die Zahl der Goldzellen (der Median trennt hier nicht)."""
    if zellen <= 2:
        return "2"
    if zellen <= 4:
        return "3-4"
    return ">= 5"


def merkmale(record: dict[str, Any], text: str) -> dict[str, Any]:
    target = str((record.get("timepoint") or {}).get("target") or "")
    return {
        "zieltyp": zieltyp(target),
        "zielzahl_im_text": zielzahl_im_text(target, text),
        "goldzellen": _zellen_korb(len((record.get("gold") or {}).get("cells") or [])),
        "textlaenge": len(text),
        "tabellen": len(re.findall(r"table-wrap", text)),
    }


def gruppiere(
    zeilen: list[dict[str, Any]], werte: dict[str, dict[str, Any]], schluessel: str
) -> dict[str, dict[str, float] | str]:
    """Teilt nach einem Merkmal und rechnet die Ausfallquote je Gruppe."""
    ausfaelle_je_wert: Counter[str] = Counter()
    gesamt_je_wert: Counter[str] = Counter()
    for zeile in zeilen:
        wert = werte[zeile["record_id"]].get(schluessel)
        if isinstance(wert, bool):
            gruppe = "ja" if wert else "nein"
        elif isinstance(wert, int):
            grenze = median([w[schluessel] for w in werte.values()])
            gruppe = f">= {grenze:g}" if wert >= grenze else f"< {grenze:g}"
        else:
            gruppe = str(wert)
        gesamt_je_wert[gruppe] += 1
        if zeile.get("fehlerklasse") == AUSFALL:
            ausfaelle_je_wert[gruppe] += 1
    return {
        "merkmal": schluessel,
        "gruppen": {
            gruppe: {
                "zeilen": gesamt_je_wert[gruppe],
                "ausfaelle": ausfaelle_je_wert[gruppe],
                "quote": round(ausfaelle_je_wert[gruppe] / gesamt_je_wert[gruppe], 4),
            }
            for gruppe in sorted(gesamt_je_wert)
        },
        "fisher_p": _fisher_fuer_gruppen(ausfaelle_je_wert, gesamt_je_wert),
    }


def _fisher_fuer_gruppen(ausfaelle: Counter[str], gesamt: Counter[str]) -> float | None:
    """Fishers p fuer die zwei groessten Gruppen (bei mehr als zwei: beste Trennung)."""
    gruppen = sorted(gesamt, key=lambda g: gesamt[g], reverse=True)
    if len(gruppen) < 2:
        return None
    if len(gruppen) == 2:
        a, b = gruppen
        return round(
            fisher_exakt(
                ausfaelle[a], gesamt[a] - ausfaelle[a], ausfaelle[b], gesamt[b] - ausfaelle[b]
            ),
            4,
        )
    # Mehr als zwei Gruppen: die auffaelligste gegen den Rest.
    beste = None
    for gruppe in gruppen:
        rest_ausfall = sum(ausfaelle[g] for g in gruppen if g != gruppe)
        rest_gesamt = sum(gesamt[g] for g in gruppen if g != gruppe)
        p = fisher_exakt(
            ausfaelle[gruppe], gesamt[gruppe] - ausfaelle[gruppe], rest_ausfall, rest_gesamt - rest_ausfall
        )
        if beste is None or p < beste[1]:
            beste = (gruppe, p)
    return round(beste[1], 4) if beste else None


def diagnose(zeilen: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    texte: dict[str, str] = {}
    for record_id in {z["record_id"] for z in zeilen}:
        pfad = (records[record_id].get("document") or {}).get("path") or ""
        datei = REPO / pfad if pfad else None
        texte[record_id] = datei.read_text(encoding="utf-8", errors="replace") if datei and datei.exists() else ""
    werte = {rid: merkmale(records[rid], text) for rid, text in texte.items() if rid in records}

    gueltig = [z for z in zeilen if not z.get("fehlerklasse") and (z.get("rows") or z.get("predicted"))]
    tokens = [int(z.get("completion_tokens") or 0) for z in gueltig]
    ausfaelle = [z for z in zeilen if z.get("fehlerklasse") == AUSFALL]
    gold_gesamt = sum(len((r.get("gold") or {}).get("cells") or []) for r in records.values())
    gold_ausfall = sum(
        len((records[z["record_id"]].get("gold") or {}).get("cells") or []) for z in ausfaelle if z["record_id"] in records
    )
    limit = max((int(z.get("completion_tokens") or 0) + int(z.get("retry_tokens") or 0)) for z in ausfaelle) if ausfaelle else 0
    kosten_ausfall = sum(int(z.get("completion_tokens") or 0) + int(z.get("retry_tokens") or 0) for z in ausfaelle)
    kosten_gesamt = sum(int(z.get("completion_tokens") or 0) + int(z.get("retry_tokens") or 0) for z in zeilen)

    p = len(ausfaelle) / len(zeilen) if zeilen else 0.0
    mittel_gueltig = (sum(tokens) / len(tokens)) if tokens else 0.0
    p95 = quantil(tokens, 0.95) or 0.0

    return {
        "zeilen": len(zeilen),
        "gueltige_zeilen": len(gueltig),
        "ausfaelle": len(ausfaelle),
        "ausfallquote": round(p, 4),
        "tokens_gueltig": {
            "p50": int(quantil(tokens, 0.50) or 0),
            "p90": int(quantil(tokens, 0.90) or 0),
            "p95": int(p95),
            "max": max(tokens) if tokens else 0,
            "mittel": int(mittel_gueltig),
        },
        "limit_empfehlung": max(10000, int(math.ceil(1.25 * p95 / 1000.0) * 1000)) if p95 else None,
        "ausfallkosten": {
            "tokens": kosten_ausfall,
            "anteil_aller_tokens": round(kosten_ausfall / kosten_gesamt, 4) if kosten_gesamt else None,
            "je_ausfall": int(kosten_ausfall / len(ausfaelle)) if ausfaelle else None,
            "hoechstes_limit": limit,
        },
        "goldzellen": {
            "gesamt": gold_gesamt,
            "in_ausfaellen": gold_ausfall,
            "anteil": round(gold_ausfall / gold_gesamt, 4) if gold_gesamt else None,
        },
        "erwartung_je_record": round((1 - p) * mittel_gueltig + p * (limit or 0), 0),
        # Anteil gueltiger Antworten, die innerhalb von 5 Prozent am Limit lagen:
        # ein hoher Wert heisst, das Limit schneidet gute Antworten ab.
        "gueltig_nahe_limit": sum(1 for z in gueltig if int(z.get("completion_tokens") or 0) >= 0.95 * limit)
        if limit
        else 0,
        "merkmalstests": [gruppiere(zeilen, werte, name) for name in ("zieltyp", "zielzahl_im_text", "goldzellen", "textlaenge", "tabellen")],
    }


def markdown(ergebnis: dict[str, Any], run: str) -> str:
    t = ergebnis["tokens_gueltig"]
    zeilen = [
        f"# Length-Diagnose `{run}`",
        "",
        "Erzeugt von `laenge_diagnose.py` ohne API-Aufrufe. Merkmale am Median geteilt,",
        "p-Werte aus dem exakten zweiseitigen Fisher-Test (bei mehr als zwei Gruppen:",
        "auffaelligste Gruppe gegen den Rest). Mehrere Merkmale sind Mehrfachvergleiche.",
        "",
        f"* Zeilen: **{ergebnis['zeilen']}**, davon gueltig {ergebnis['gueltige_zeilen']}, "
        f"Length-Ausfaelle **{ergebnis['ausfaelle']}** ({ergebnis['ausfallquote']:.1%})",
        f"* Tokens gueltiger Zeilen: p50 {t['p50']}, p90 {t['p90']}, p95 {t['p95']}, max {t['max']}, "
        f"Mittel {t['mittel']}",
        f"* Limit-Empfehlung (1,25 x p95, mindestens 10.000): **{ergebnis['limit_empfehlung']}**",
        f"* Ausfaelle kosteten {ergebnis['ausfallkosten']['tokens']} Tokens "
        f"({ergebnis['ausfallkosten']['anteil_aller_tokens']:.1%} aller Tokens), "
        f"je Ausfall {ergebnis['ausfallkosten']['je_ausfall']}",
        f"* Goldzellen in Ausfaellen: {ergebnis['goldzellen']['in_ausfaellen']} von "
        f"{ergebnis['goldzellen']['gesamt']} ({ergebnis['goldzellen']['anteil']:.1%})",
        f"* Erwartung je Record: {ergebnis['erwartung_je_record']:.0f} Tokens",
        f"* Gueltige Antworten innerhalb von 5 % am hoechsten Limit: "
        f"{ergebnis['gueltig_nahe_limit']} von {ergebnis['gueltige_zeilen']}",
        "",
        "| Merkmal | Gruppe | Zeilen | Ausfaelle | Quote | p |",
        "|---|---|---|---|---|---|",
    ]
    for test in ergebnis["merkmalstests"]:
        for gruppe, werte in test["gruppen"].items():
            zeilen.append(
                f"| {test['merkmal']} | {gruppe} | {werte['zeilen']} | {werte['ausfaelle']} | "
                f"{werte['quote']:.1%} | {test['fisher_p'] if test['fisher_p'] is not None else '-'} |"
            )
    return "\n".join(zeilen) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--md", type=Path, default=None)
    args = parser.parse_args()

    zeilen = read_jsonl(BENCH / "runs" / args.run / "predictions.jsonl")
    records = {str(r["record_id"]): r for r in read_jsonl(args.records)}
    ergebnis = diagnose(zeilen, records)
    ergebnis["run"] = args.run

    text = markdown(ergebnis, args.run)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
