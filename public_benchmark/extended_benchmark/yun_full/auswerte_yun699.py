#!/usr/bin/env python
"""Auswertung eines Yun-699-Laufs gegen die offiziellen Goldzellen.

Getrennt von `evaluate_fallback.py`, weil der Yun-Datensatz kein Zeitpunktfeld
hat und die Zaehlung deshalb ohne Zeitpunktklassen laeuft. Die Zellwerte werden
exakt verglichen (kein Toleranzfenster): Yun annotiert gedruckte Werte, und eine
Abweichung ist eine Abweichung.

Ausgewiesen werden getrennt: falsche Extraktion, fehlende Extraktion (Gold
vorhanden, Modell schweigt), Zelle ohne Gold (Modell meldet, Annotation nicht),
technischer Ausfall und leere Antwort. Zellen ohne Gold zaehlen nicht als
Modellfehler.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def klasse(feld: str) -> str:
    if feld.endswith("_events"):
        return "events"
    if feld.endswith("_group_size"):
        return "N"
    if feld.endswith("_mean"):
        return "mean"
    if feld.endswith("_standard_deviation"):
        return "SD"
    return "sonstiges"


def arm(feld: str) -> str:
    return "intervention" if feld.startswith("intervention") else "comparator"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--split", default=None, help="nur Records dieses Splits zaehlen")
    args = parser.parse_args()

    lauf = RUNS / args.run
    rows = lies(lauf / "predictions.jsonl")
    alle = {r["record_id"]: r for r in lies(args.records)}

    if args.split:
        rows = [z for z in rows if alle[z["record_id"]]["document"]["split"] == args.split]

    richtig = falsch = fehlend = ohne_gold = 0
    summe_abw = 0.0
    je_feld: dict[str, Counter] = defaultdict(Counter)
    je_arm: dict[str, Counter] = defaultdict(Counter)
    je_typ: dict[str, Counter] = defaultdict(Counter)
    record_status: Counter = Counter()
    ausfaelle = leere = 0
    tokens = 0
    zeit = 0.0
    abweichungen: list[dict] = []

    for row in rows:
        record = alle[row["record_id"]]
        gold = {c["field"]: c["value"] for c in record["gold"]["cells"]}
        typ = record["context"]["outcome_type"]
        tokens += sum(
            wert or 0
            for wert in (row.get("completion_tokens"), row.get("retry_tokens"), row.get("repair_tokens"))
        )
        zeit += row.get("elapsed_s") or 0
        if row.get("fehlerklasse"):
            ausfaelle += 1
        if not row.get("rows") and not row.get("fehlerklasse"):
            leere += 1

        gesehen: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            gesehen.setdefault(zelle["field"], zelle["value"])
        record_komplett = True
        for feld, wert in gold.items():
            if feld not in gesehen:
                fehlend += 1
                je_feld[feld]["fehlend"] += 1
                je_arm[arm(feld)]["fehlend"] += 1
                je_typ[typ]["fehlend"] += 1
                record_komplett = False
                continue
            if abs(gesehen[feld] - wert) < 1e-9:
                richtig += 1
                je_feld[feld]["richtig"] += 1
                je_arm[arm(feld)]["richtig"] += 1
                je_typ[typ]["richtig"] += 1
            else:
                falsch += 1
                je_feld[feld]["falsch"] += 1
                je_arm[arm(feld)]["falsch"] += 1
                je_typ[typ]["falsch"] += 1
                summe_abw += abs(gesehen[feld] - wert)
                record_komplett = False
                abweichungen.append(
                    {
                        "record_id": row["record_id"],
                        "field": feld,
                        "gold": wert,
                        "modell": gesehen[feld],
                        "outcome": record["context"]["outcome"],
                    }
                )
        for feld in gesehen:
            if feld not in gold:
                ohne_gold += 1
                je_feld[feld]["ohne_gold"] += 1
                je_arm[arm(feld)]["ohne_gold"] += 1
                record_komplett = False
        if row.get("fehlerklasse"):
            record_status["technischer_ausfall"] += 1
        elif not row.get("rows"):
            record_status["leere_antwort"] += 1
        elif record_komplett and gold:
            record_status["exakt"] += 1
        elif gold and any(f in gesehen and abs(gesehen[f] - v) < 1e-9 for f, v in gold.items()):
            record_status["teilweise"] += 1
        else:
            record_status["ohne_treffer"] += 1

    goldzellen = richtig + falsch + fehlend
    gemeldet = richtig + falsch + ohne_gold
    precision = richtig / gemeldet if gemeldet else 0.0
    recall = richtig / goldzellen if goldzellen else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    ergebnis = {
        "run": args.run,
        "records": len(rows),
        "tokens": tokens,
        "zeit_summiert_s": round(zeit, 1),
        "zellen": {
            "gold": goldzellen,
            "richtig": richtig,
            "falsch": falsch,
            "fehlend": fehlend,
            "ohne_gold": ohne_gold,
        },
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "abdeckung": round(richtig / goldzellen, 4) if goldzellen else 0.0,
        "mae": round(summe_abw / (richtig + falsch), 4) if (richtig + falsch) else None,
        "records_status": dict(record_status),
        "technische_ausfaelle": ausfaelle,
        "leere_antworten": leere,
        "je_feld": {f: dict(z) for f, z in sorted(je_feld.items())},
        "je_arm": {a: dict(z) for a, z in sorted(je_arm.items())},
        "je_outcome_typ": {t: dict(z) for t, z in sorted(je_typ.items())},
        "abweichungen": abweichungen,
    }
    print(f"{args.run}: {len(rows)} Records, {goldzellen} Goldzellen")
    print(
        f"  richtig {richtig} | falsch {falsch} | fehlend {fehlend} | ohne Gold {ohne_gold}"
    )
    print(f"  Precision {precision:.4f} | Recall {recall:.4f} | F1 {f1:.4f}")
    print(f"  Abdeckung {ergebnis['abdeckung']:.4f} | MAE {ergebnis['mae']}")
    print(f"  Records exakt {record_status['exakt']} | teilweise {record_status['teilweise']} "
          f"| ohne Treffer {record_status['ohne_treffer']} | Ausfaelle {ausfaelle} | leer {leere}")
    print(f"  Tokens {tokens} | Zeit summiert {zeit:.0f}s")
    for feld, z in sorted(je_feld.items()):
        print(f"    {feld:<34} richtig {z['richtig']:>4} falsch {z['falsch']:>4} fehlend {z['fehlend']:>4}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
