#!/usr/bin/env python
"""Retry-Liste und Telemetrie der GLM-Ausfaelle im Yun-699-Lauf.

Liest den Lauf read-only, gruppiert die Ausfaelle nach Fehlerbild und schreibt
eine sortierte Liste, die direkt als Nachzug abgearbeitet werden kann. Es wird
nichts gestartet und nichts an `predictions.jsonl` geaendert.

Gruppen:

* `repair`  – `length_ohne_ergebnis`: Budget war ausgeschoepft, ein zweiter
  Aufruf mit kleinem Budget (`--repair`) hat die besten Chancen.
* `leer`    – Antwort ohne Fehlerklasse, aber ohne Zellen: reiner
  Wiederholungsfall (`--retry-failed`).
* `json_kaputt` – strukturell unlesbares JSON; der Harness hat es bereits
  einmal automatisch wiederholt, Prioritaet niedrig.

Sortiert wird nach erwarteter Ausbeute: Anzahl der Goldzellen, die in diesem
Record fehlen. Ein Record mit sechs fehlenden Zellen bringt mehr als einer mit
zwei.

Aufruf:
    python retry_liste_glm.py --run yun699_8000_alle_20261117 \
        --out ergebnisse/retry_liste_glm.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = HERE.parents[2]
RUNS = BENCH / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"


def lies(pfad: Path) -> list[dict]:
    zeilen = []
    for roh in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        roh = roh.strip()
        if not roh:
            continue
        try:
            zeilen.append(json.loads(roh))
        except json.JSONDecodeError:
            # Der Lauf schreibt waehrenddessen; eine halbe Zeile wird ignoriert.
            continue
    return zeilen


def median(werte: list[float]) -> float | None:
    return round(statistics.median(werte), 1) if werte else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--modell", default="glm")
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = [r for r in lies(RUNS / args.run / "predictions.jsonl") if r.get("model") == args.modell]
    records = {r["record_id"]: r for r in lies(args.records)}

    # Letzte Zeile je Record gewinnt (Neustarts erzeugen mehrere).
    je_record: dict[str, dict] = {}
    for row in rows:
        je_record[row["record_id"]] = row

    gruppen: dict[str, list[dict]] = {"repair": [], "leer": [], "json_kaputt": [], "anderer_fehler": []}
    ok_tokens: list[float] = []
    ok_text: list[float] = []
    fehl_text: list[float] = []

    for rid, record in records.items():
        row = je_record.get(rid)
        if row is None:
            continue
        gold = record.get("gold", {}).get("cells") or []
        modell = {z["field"] for z in row.get("rows") or []}
        fehlend = [z["field"] for z in gold if z["field"] not in modell]
        text_laenge = (record.get("document") or {}).get("text_chars") or 0
        eintrag = {
            "record_id": rid,
            "outcome_type": (record.get("context") or {}).get("outcome_type"),
            "fehlerklasse": row.get("fehlerklasse") or "",
            "zellen": len(row.get("rows") or []),
            "gold_zellen": len(gold),
            "fehlende_zellen": len(fehlend),
            "completion_tokens": row.get("completion_tokens"),
            "reasoning_chars": row.get("reasoning_chars") or 0,
            "elapsed_s": row.get("elapsed_s"),
            "finish_reason": row.get("finish_reason") or "",
            "text_chars": text_laenge,
        }
        if not eintrag["fehlerklasse"] and eintrag["zellen"] == 0:
            eintrag["gruppe"] = "leer"
        elif eintrag["fehlerklasse"] == "length_ohne_ergebnis":
            eintrag["gruppe"] = "repair"
        elif eintrag["fehlerklasse"] == "json_kaputt":
            eintrag["gruppe"] = "json_kaputt"
        elif eintrag["fehlerklasse"]:
            eintrag["gruppe"] = "anderer_fehler"
        else:
            eintrag["gruppe"] = "ok"
        if eintrag["gruppe"] == "ok":
            if eintrag["completion_tokens"]:
                ok_tokens.append(float(eintrag["completion_tokens"]))
            ok_text.append(text_laenge)
        elif eintrag["gruppe"] in ("repair", "leer", "json_kaputt", "anderer_fehler"):
            fehl_text.append(text_laenge)
            gruppen[eintrag["gruppe"]].append(eintrag)

    for eintraege in gruppen.values():
        eintraege.sort(key=lambda e: (-e["fehlende_zellen"], e["record_id"]))

    zusammenfassung = {}
    for name, eintraege in gruppen.items():
        zusammenfassung[name] = {
            "records": len(eintraege),
            "fehlende_zellen": sum(e["fehlende_zellen"] for e in eintraege),
            "tokens_verbraucht": sum(int(e["completion_tokens"] or 0) for e in eintraege),
            "median_tokens": median([float(e["completion_tokens"]) for e in eintraege if e["completion_tokens"]]),
            "median_reasoning_zeichen": median([float(e["reasoning_chars"]) for e in eintraege]),
            "median_text_zeichen": median([float(e["text_chars"]) for e in eintraege]),
            "mit_reasoning": sum(1 for e in eintraege if e["reasoning_chars"] > 0),
        }

    telemetrie = {
        "records_gesamt": len(je_record),
        "ok": sum(1 for e in je_record.values() if not e.get("fehlerklasse") and (e.get("rows") or [])),
        "ok_median_tokens": median(ok_tokens),
        "ok_median_text_zeichen": median([float(t) for t in ok_text]),
        "ausfall_median_text_zeichen": median([float(t) for t in fehl_text]),
        "summe_fehlende_zellen": sum(z["fehlende_zellen"] for z in gruppen["repair"] + gruppen["leer"] + gruppen["json_kaputt"] + gruppen["anderer_fehler"]),
    }

    ergebnis = {
        "run": args.run,
        "modell": args.modell,
        "telemetrie": telemetrie,
        "gruppen": zusammenfassung,
        "records": {name: [e["record_id"] for e in eintraege] for name, eintraege in gruppen.items()},
        "details": gruppen,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding="utf-8")

    def liste(name: str) -> Path:
        pfad = args.out.parent / f"retry_{name}_ids.txt"
        pfad.write_text(",".join(ergebnis["records"][name]) + "\n", encoding="utf-8")
        return pfad

    print(f"{args.modell}: {telemetrie['records_gesamt']} Records, {telemetrie['ok']} verwertbar")
    print(f"  Median Tokens ok: {telemetrie['ok_median_tokens']}, Median Textzeichen ok: {telemetrie['ok_median_text_zeichen']}")
    for name, wert in zusammenfassung.items():
        print(
            f"  {name:14} records={wert['records']:3}  fehlende Zellen={wert['fehlende_zellen']:4}  "
            f"tokens={wert['tokens_verbraucht']:7}  median_tokens={wert['median_tokens']}  "
            f"median_text={wert['median_text_zeichen']}  mit_reasoning={wert['mit_reasoning']}"
        )
        if wert["records"]:
            print(f"                 Liste: {liste(name)}")
    print(f"Summe fehlender Zellen in allen Ausfallgruppen: {telemetrie['summe_fehlende_zellen']}")
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
