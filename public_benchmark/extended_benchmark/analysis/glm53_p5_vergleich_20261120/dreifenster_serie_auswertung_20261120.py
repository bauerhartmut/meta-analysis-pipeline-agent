#!/usr/bin/env python
"""Auswertung der Dreifenster-Serie auf yun2024:30, 673 und 674.

Liest die drei Predictions der Stufe 1 (`predictions_dreifenster_*_qwen_16000.jsonl`)
und rechnet offline nach:

* welche Goldwerte in den drei 2.000er-Stuecken stehen (naiv) und welche davon
  in einem Umfeld mit Outcome-Stichwort (belastbar),
* wo die Goldzeile im Dokument liegt und ob sie in einem Stueck liegt,
* welche Zahlen der zitierte Satz traegt (Zahlenlesart aus `falschwert_*.py`,
  damit "36%" als 36.0 und nicht als 36.4 gelesen wird),
* was ein blindes Tabellendichte-Fenster (2.000 Zeichen, Ergebnisteil, Schritt
  250) erreichen wuerde.

Kein Modellaufruf, kein Netz. Gold und Predictions bleiben unveraendert.

Aufruf:
    .venv/bin/python .../dreifenster_serie_auswertung_20261120.py
"""

from __future__ import annotations

import json
import re
import sys
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
from falschwert_20261120 import TOKEN, lesarten  # noqa: E402
from fensterlage_20261120 import werte_index  # noqa: E402
from fundstellen_20261120 import abschnitte  # noqa: E402

LAUF = HIER / "zweistufig_lauf_20261120"
AUS_JSON = HIER / "dreifenster_serie_20261120.json"
AUS_MD = HIER / "dreifenster_serie_ergebnis_20261120.md"
RECORDS = ["yun2024:30", "yun2024:673", "yun2024:674"]
MARKE = re.compile(r"\b(n\s*=|mean|SD|95%\s*CI|CI\b|Table|%)", re.I)
STUECK = 2000
SCHRITT = 250


def zahlen_im_satz(satz: str) -> list[float]:
    return sorted({round(x, 6) for m in TOKEN.finditer(satz) for x in lesarten(m.group(0))})


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: dict[str, Any] = {}

    for rid in RECORDS:
        record = records[rid]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        context = record.get("context") or {}
        worte = [w for w in re.split(r"[\s/,()-]+", str(context.get("outcome") or "")) if len(w) >= 4]
        zellen = (record.get("gold") or {}).get("cells") or []
        werte = sorted({round(float(z["value"]), 6) for z in zellen if z.get("value") is not None})
        index = werte_index(text, werte)

        datei = LAUF / f"predictions_dreifenster_{rid.split(':')[1]}_qwen_16000.jsonl"
        zeile = json.loads(datei.read_text(encoding="utf-8").splitlines()[-1])
        stuecke = [tuple(s) for s in zeile["stuecke"]]

        in_stueck = {w: [p for p in index[w] if any(a <= p[0] < b for a, b in stuecke)]
                     for w in werte}

        # Goldzeile: Stelle, an der Goldmittel und zugehoerige SD dicht beieinander
        # stehen. Die erste Fundstelle des Mittels allein ist irrefuehrend, weil
        # derselbe Wert in einer anderen Tabelle vorkommen kann (30: 38.1 auch als
        # Role-Emotional-Wert).
        mittel = next((v.zahl(z.get("value")) for z in zellen
                       if str(z.get("field") or "").endswith("_mean")), None)
        sd = next((v.zahl(z.get("value")) for z in zellen
                   if str(z.get("field") or "").endswith("_standard_deviation")), None)
        paare = []
        if mittel is not None and sd is not None:
            for pm in index.get(round(float(mittel), 6), []):
                for ps in index.get(round(float(sd), 6), []):
                    if abs(pm[0] - ps[0]) <= 120:
                        paare.append((abs(pm[0] - ps[0]), min(pm[0], ps[0])))
        goldzeile = (min(paare)[1] if paare else
                     (min((p[0] for p in index.get(round(float(mittel), 6), [])), default=None)
                      if mittel is not None else None))

        zitiert: list[dict[str, Any]] = []
        for loc in zeile.get("locators") or []:
            satz = loc.get("satz") or ""
            zahlen = zahlen_im_satz(satz)
            zitiert.append({
                "arm": loc.get("arm"),
                "timepoint": loc.get("timepoint"),
                "satz": satz,
                "zahlen": zahlen,
                "goldwerte_im_satz": sorted(set(zahlen) & set(werte)),
                "goldmittel_im_satz": bool(mittel is not None
                                           and round(float(mittel), 6) in zahlen),
            })

        sp = abschnitte(text)["spans"]
        ergebnis = [(a, b) for a, b, n in sp if n == "ergebnisse"]
        if ergebnis:
            a, b = ergebnis[0]
            start = max(range(a, max(a + 1, b - STUECK + 1), SCHRITT),
                        key=lambda s: len(MARKE.findall(text[s:s + STUECK])))
        else:
            start = None
        tabelle_abgedeckt = (sum(1 for w in werte
                                 if start is not None
                                 and any(start <= p[0] < start + STUECK for p in index[w]))
                             if start is not None else 0)

        faelle[rid] = {
            "record_id": rid,
            "outcome": context.get("outcome"),
            "outcome_type": context.get("outcome_type"),
            "stuecke": stuecke,
            "goldzeile": goldzeile,
            "goldzeile_in_stueck": bool(goldzeile is not None
                                        and any(a <= goldzeile < b for a, b in stuecke)),
            "goldwerte": werte,
            "naiv_abgedeckt": sum(1 for w in werte if in_stueck[w]),
            "status": zeile.get("status"),
            "finish_reason": zeile.get("finish_reason"),
            "completion_tokens": zeile.get("completion_tokens"),
            "elapsed_s": zeile.get("elapsed_s"),
            "prompt_zeichen": zeile.get("prompt_zeichen"),
            "prompt_sha256": zeile.get("prompt_sha256"),
            "locators": zitiert,
            "tabellenfenster_start": start,
            "tabellenfenster_abgedeckt": tabelle_abgedeckt,
        }

    tokens = sum(f["completion_tokens"] or 0 for f in faelle.values())
    sekunden = sum(f["elapsed_s"] or 0 for f in faelle.values())
    mit_mittel = sum(1 for f in faelle.values()
                     if any(l["goldmittel_im_satz"] for l in f["locators"]))
    ergebnis = {"n": len(faelle), "tokens": tokens, "sekunden": round(sekunden, 2),
                "records_mit_goldmittel": mit_mittel, "faelle": faelle}
    AUS_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    md = [
        "# Dreifenster-Serie auf 30, 673 und 674 (20.11.2026)",
        "",
        "Drei disjunkte 2.000er-Stuecke je Record, ausgewaehlt mit derselben blinden",
        "Score-Regel wie `mehrfach_3x2000` (Abweichungspruefung ueber 699 Records: 0).",
        "Modell `gwdg/qwen3.5-397b`, Budget 16.000, Lesezeit 420 s, je ein Aufruf.",
        "Abbruchkriterium: `content_chars == 0` oder `finish_reason == length`.",
        "",
        "## Ergebnis je Record",
        "",
        "| Record | Stuecke | Goldzeile | Goldzeile im Stueck | Goldwerte naiv | Status | Tokens | Zeit | Locators | Goldmittel im Satz |",
        "|---|---|---:|---|---:|---|---:|---:|---:|---:|",
    ]
    for rid, f in faelle.items():
        md.append(
            f"| `{rid}` | {f['stuecke']} | {f['goldzeile']} | "
            f"{'ja' if f['goldzeile_in_stueck'] else '**nein**'} | "
            f"{f['naiv_abgedeckt']}/{len(f['goldwerte'])} | {f['status']} | "
            f"{f['completion_tokens']} | {f['elapsed_s']} s | {len(f['locators'])} | "
            f"{sum(1 for l in f['locators'] if l['goldmittel_im_satz'])} |")

    md += [
        "",
        f"Kosten: **{tokens}** Completion-Tokens, {round(sekunden, 2)} s. Records, deren",
        f"zitierter Satz das **Goldmittel** traegt: **{mit_mittel} von {len(faelle)}**.",
        "Einzelne Goldwerte im Satz sind kein Treffer: auf 673/674 ist die 23.0 die",
        "Standardabweichung des Goldes, im Satz steht aber `23 % control`.",
        "",
        "## Was die Modelle zitiert haben",
        "",
    ]
    for rid, f in faelle.items():
        md.append(f"### {rid}")
        md.append("")
        for loc in f["locators"]:
            md.append(f"- **{loc['arm']}**, timepoint {loc['timepoint']!r}, Zahlen "
                      f"{loc['zahlen']}: {loc['satz']}")
        md.append("")

    md += [
        "## Befund",
        "",
        "- Die Goldzeile liegt in **allen drei** Faellen zwischen den Stuecken:",
        *[f"  {rid} bei Zeichen {f['goldzeile']} (Stuecke {f['stuecke']})"
          for rid, f in faelle.items()],
        "- Die vorab gemessene Abdeckung (2/6, 4/6, 4/6) war teils zufaellig: die",
        "  Treffer auf 673/674 sind `23 % drug stores`, `32 % facilities`, `26 % education`",
        "  und nicht die Goldzeile `36.4 % (32)` bzw. `22.6 % (23)`.",
        "- Das Modell antwortet in allen drei Faellen mit einem Satz zum richtigen",
        "  Outcome, aber mit einer anderen Kennzahl: auf 30 mit der Aenderung 6,4/6,4/2,1",
        "  statt der Tabelle 38,1 (9,5) / 31,5 (7,4); auf 673/674 mit `36 % provider,",
        "  23 % control, 24 % ...` statt `36.4 % (32)` / `22.6 % (23)`.",
        "- Damit misst die Serie erneut die Fensterwahl, nicht die Bindung des Modells:",
        "  die richtige Zeile war in keinem Aufruf sichtbar.",
        "",
        "## Blinde Tabellenregel als Gegenprobe",
        "",
        "| Record | Tabellenfenster ab | Goldwerte darin |",
        "|---|---:|---:|",
    ]
    for rid, f in faelle.items():
        md.append(f"| `{rid}` | {f['tabellenfenster_start']} | "
                  f"{f['tabellenfenster_abgedeckt']}/{len(f['goldwerte'])} |")
    md += [
        "",
        "Die Regel nimmt im Ergebnisteil das 2.000er-Fenster mit den meisten",
        "Tabellenmerkern (`n =`, `mean`, `SD`, `CI`, `Table`, `%`). Sie erreicht auf 30",
        "alle sechs Werte, auf 673/674 vier bzw. drei, weil dort mehrere Tabellen",
        "konkurrieren. Sie ist blind und braucht kein Goldwissen.",
        "",
        "## Empfehlung",
        "",
        "Keine weitere Serie mit Prosa-Fenstern. Vor dem naechsten Aufruf ein",
        "Tabellenfenster plus ein Prosa-Stueck kombinieren und offline pruefen, ob",
        "die Goldzeile dann in beiden Records mit sechs Werten liegt; erst danach",
        "einen Aufruf auf 30 mit diesem Prompt.",
        "",
    ]
    AUS_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"{len(faelle)} Records, {tokens} Tokens, {sekunden:.2f} s, "
          f"{mit_mittel} mit Goldmittel im Satz")
    for rid, f in faelle.items():
        print(f"  {rid}: Goldzeile {f['goldzeile']} im Stueck "
              f"{f['goldzeile_in_stueck']}, naiv {f['naiv_abgedeckt']}/"
              f"{len(f['goldwerte'])}, Tabellenfenster {f['tabellenfenster_start']} -> "
              f"{f['tabellenfenster_abgedeckt']}")
    print("geschrieben:", AUS_JSON)
    print("geschrieben:", AUS_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
