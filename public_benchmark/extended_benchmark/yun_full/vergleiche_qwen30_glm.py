#!/usr/bin/env python
"""Vergleicht zwei Modelle eines Yun-699-Laufs auf einer Lesekopie.

Grundlage sind die Einzelauswertungen von `auswerte_yun699.py` (je Modell eine
JSON-Datei). Dieses Skript liest zusaetzlich die Predictions der Kopie, um die
Fragen zu beantworten, die eine Kennzahl allein nicht beantwortet:

- Woraus bestehen die fehlenden Zellen (leere Antwort oder Feld nicht gemeldet)?
- Wo ist ein Modell richtig, wo das andere, wo beide?
- Was kostet eine richtige Zelle in Tokens?

Es schreibt einen Markdown-Bericht und ein JSON mit den Rohzahlen.

Aufruf:
    python vergleiche_qwen30_glm.py --run _lesekopie_20261118 \
        --out-dir ../iterativ/ergebnisse/qwen30_vs_glm_20261118 \
        --modell-a qwen30 --modell-b glm
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"

# Gruppenfelder sind bei manchen Modellen keine Frage der Extraktion, sondern
# der Prompt-Einstellung (group_size_mode); sie werden getrennt gezaehlt.
GRUPPENFELDER = {"intervention_group_size", "comparator_group_size"}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def ist_leer(row: dict) -> bool:
    return not row.get("rows") and not row.get("fehlerklasse")


def zellen_von(row: dict) -> dict[str, float]:
    """Erste gemeldete Zahl je Feld; spaetere Doppelungen zaehlen nicht."""
    gesehen: dict[str, float] = {}
    for zelle in row.get("rows") or []:
        gesehen.setdefault(zelle["field"], zelle["value"])
    return gesehen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="Run-Verzeichnis unter runs/ (Lesekopie)")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--modell-a", default="qwen30")
    ap.add_argument("--modell-b", default="glm")
    args = ap.parse_args()
    a, b = args.modell_a, args.modell_b

    lauf = RUNS / args.run
    rows = lies(lauf / "predictions.jsonl")
    gold_zellen = {
        r["record_id"]: {c["field"]: c["value"] for c in r["gold"]["cells"]}
        for r in lies(RECORDS)
    }

    res = {}
    for modell in (a, b):
        pfad = args.out_dir / f"{modell}_lesekopie.json"
        if not pfad.exists():
            print(f"FEHLER: {pfad} fehlt - erst auswerte_yun699.py --model {modell}")
            return 2
        res[modell] = json.loads(pfad.read_text(encoding="utf-8"))

    # Ein Durchgang je Modell: Zellstatus je Record, leere Records, Tokens.
    je_record: dict[str, dict[str, dict]] = defaultdict(dict)
    gemeldet: dict[tuple[str, str], dict[str, float]] = {}
    leer_records: dict[str, set[str]] = {}
    gruppen_modus: dict[str, Counter] = {}
    tokens_je_modell: dict[str, int] = {}

    for modell in (a, b):
        eigene = [r for r in rows if r["model"] == modell]
        leer_records[modell] = {r["record_id"] for r in eigene if ist_leer(r)}
        gruppen_modus[modell] = Counter(r.get("group_size_mode") or "?" for r in eigene)
        tokens_je_modell[modell] = sum(
            sum(wert or 0 for wert in (r.get("completion_tokens"), r.get("retry_tokens"), r.get("repair_tokens")))
            for r in eigene
        )
        for row in eigene:
            rid = row["record_id"]
            gesehen = gemeldet.setdefault((rid, modell), zellen_von(row))
            gold = gold_zellen[rid]
            je_record[rid][modell] = {
                "richtig": sum(1 for f, w in gold.items()
                               if f in gesehen and abs(gesehen[f] - w) < 1e-9),
                "falsch": sum(1 for f, w in gold.items()
                              if f in gesehen and abs(gesehen[f] - w) >= 1e-9),
                "fehlend": sum(1 for f in gold if f not in gesehen),
                "leer": ist_leer(row),
            }

    # Zerlegung der fehlenden Zellen des Modells A.
    fehlend_zerlegt = Counter()
    for stand in je_record.values():
        info = stand[a]
        if info["fehlend"]:
            schluessel = "leere_antwort" if info["leer"] else "nicht_gemeldet"
            fehlend_zerlegt[schluessel] += info["fehlend"]

    # Zellstatus von A, getrennt nach Gruppen- und uebrigen Feldern.
    gruppenanalyse = Counter()
    for rid in je_record:
        for feld, wert in gold_zellen[rid].items():
            gruppe = "gruppe" if feld in GRUPPENFELDER else "sonstiges"
            gesehen = gemeldet[(rid, a)].get(feld)
            if gesehen is None:
                gruppenanalyse[f"{gruppe}_fehlend"] += 1
            elif abs(gesehen - wert) < 1e-9:
                gruppenanalyse[f"{gruppe}_richtig"] += 1
            else:
                gruppenanalyse[f"{gruppe}_falsch"] += 1

    # Record-Ebene: wer ist wo vollstaendig exakt, wer hat nur dort Treffer?
    rekord_vergleich = Counter()
    nur_a_treffer = nur_b_treffer = 0
    for stand in je_record.values():
        exakt = {
            m: stand[m]["richtig"] > 0 and stand[m]["falsch"] == 0 and stand[m]["fehlend"] == 0
            for m in (a, b)
        }
        if exakt[a] and exakt[b]:
            rekord_vergleich["beide_exakt"] += 1
        elif exakt[a]:
            rekord_vergleich["nur_a_exakt"] += 1
        elif exakt[b]:
            rekord_vergleich["nur_b_exakt"] += 1
        else:
            rekord_vergleich["keiner_exakt"] += 1
        nur_a_treffer += 1 if stand[a]["richtig"] > 0 and stand[b]["richtig"] == 0 else 0
        nur_b_treffer += 1 if stand[b]["richtig"] > 0 and stand[a]["richtig"] == 0 else 0

    zus = {
        "leere_records": {m: len(leer_records[m]) for m in (a, b)},
        "leere_records_ueberlappung": len(leer_records[a] & leer_records[b]),
        "gruppen_modus": {m: dict(gruppen_modus[m]) for m in (a, b)},
        "fehlend_zerlegt": dict(fehlend_zerlegt),
        "gruppenanalyse": dict(gruppenanalyse),
        "rekord_vergleich": dict(rekord_vergleich),
        "nur_a_treffer": nur_a_treffer,
        "nur_b_treffer": nur_b_treffer,
        "tokens": tokens_je_modell,
    }

    # Die Abweichungsliste steht vollstaendig in den Modell-JSONs; hier wird sie
    # nicht noch einmal dupliziert.
    auswertung = {m: {k: v for k, v in z.items() if k != "abweichungen"} for m, z in res.items()}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "vergleich.json").write_text(
        json.dumps({"run": args.run, "modelle": [a, b], "auswertung": auswertung, "zusatz": zus},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    def kennzahl(m: str) -> dict:
        z = res[m]["zellen"]
        return {
            "richtig": z["richtig"],
            "falsch": z["falsch"],
            "fehlend": z["fehlend"],
            "ohne_gold": z["ohne_gold"],
            "precision": res[m]["precision"],
            "recall": res[m]["recall"],
            "f1": res[m]["f1"],
            "mae": res[m]["mae"],
            "exakt": res[m]["records_status"].get("exakt_strict", 0),
            "ausfaelle": res[m]["technische_ausfaelle"],
            "leer": res[m]["leere_antworten"],
            "tokens": res[m]["tokens"],
        }

    ka, kb = kennzahl(a), kennzahl(b)
    z: list[str] = [
        f"# {a} gegen {b} auf Yun-699 (Lesekopie)\n",
        f"Quelle: `runs/{args.run}/predictions.jsonl` (Lesekopie der laufenden Datei), "
        f"Gold: `records/yun699.jsonl`. Beide Modelle mit 699 Records, 2773 Goldzellen. "
        f"Alle Zahlen aus `{a}_lesekopie.json`, `{b}_lesekopie.json` und `vergleich.json` "
        "in diesem Ordner.\n",
        "## Gesamtkennzahlen\n",
        f"| Kennzahl | {a} | {b} | Differenz |",
        "|---|---:|---:|---:|",
    ]
    for label, schluessel, ganz in (
        ("richtig", "richtig", True),
        ("falsch", "falsch", True),
        ("fehlend", "fehlend", True),
        ("Zellen ohne Gold", "ohne_gold", True),
        ("Precision", "precision", False),
        ("Recall", "recall", False),
        ("F1", "f1", False),
        ("MAE", "mae", False),
        ("Records exakt (strict)", "exakt", True),
        ("technische Ausfaelle", "ausfaelle", True),
        ("leere Antworten", "leer", True),
        ("Tokens", "tokens", True),
    ):
        va, vb = ka[schluessel], kb[schluessel]
        if va is None or vb is None:
            z.append(f"| {label} | {va} | {vb} | - |")
        elif ganz:
            z.append(f"| {label} | {va} | {vb} | {va - vb:+d} |")
        else:
            z.append(f"| {label} | {va:.4f} | {vb:.4f} | {va - vb:+.4f} |")
    z.append("")
    z.append(
        f"Bezugsgroesse Precision: {ka['richtig'] + ka['falsch']} bewertbare Meldungen von {a}, "
        f"{kb['richtig'] + kb['falsch']} von {b}.\n"
    )

    zerlegt = zus["fehlend_zerlegt"]
    z += [
        "## Woher die fehlenden Zellen kommen\n",
        "| Ursache | Zellen |",
        "|---|---:|",
        f"| leere Antwort ({zus['leere_records'][a]} Records) | {zerlegt.get('leere_antwort', 0)} |",
        f"| geantwortet, Feld nicht gemeldet | {zerlegt.get('nicht_gemeldet', 0)} |",
        f"| Summe | {sum(zerlegt.values())} |\n",
        f"Zellstatus von {a}, getrennt nach Gruppenfeldern (N je Arm):\n",
        "| Feldgruppe | richtig | falsch | fehlend |",
        "|---|---:|---:|---:|",
    ]
    g = zus["gruppenanalyse"]
    for gruppe, label in (("gruppe", "Gruppengroesse"), ("sonstiges", "Mittelwerte, SD, Events")):
        z.append(
            f"| {label} | {g.get(gruppe + '_richtig', 0)} | {g.get(gruppe + '_falsch', 0)} | "
            f"{g.get(gruppe + '_fehlend', 0)} |"
        )
    z.append(
        "\nEinstellung `group_size_mode` je Modell: "
        + ", ".join(f"{m}: {zus['gruppen_modus'][m]}" for m in (a, b)) + "\n"
    )

    z += [
        "## Feldebene\n",
        f"| Feld | {a} richtig | {a} falsch | {a} fehlend | {b} richtig | {b} fehlend |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for feld in sorted(set(res[a]["je_feld"]) | set(res[b]["je_feld"])):
        fa, fb = res[a]["je_feld"].get(feld, {}), res[b]["je_feld"].get(feld, {})
        z.append(
            f"| {feld} | {fa.get('richtig', 0)} | {fa.get('falsch', 0)} | {fa.get('fehlend', 0)} | "
            f"{fb.get('richtig', 0)} | {fb.get('fehlend', 0)} |"
        )
    z.append("")

    z += [
        "## Nach Outcome-Typ\n",
        f"| Typ | {a} richtig | {a} fehlend | {b} richtig | {b} fehlend |",
        "|---|---:|---:|---:|---:|",
    ]
    for typ in sorted(set(res[a]["je_outcome_typ"]) | set(res[b]["je_outcome_typ"])):
        ta, tb = res[a]["je_outcome_typ"].get(typ, {}), res[b]["je_outcome_typ"].get(typ, {})
        z.append(
            f"| {typ} | {ta.get('richtig', 0)} | {ta.get('fehlend', 0)} | "
            f"{tb.get('richtig', 0)} | {tb.get('fehlend', 0)} |"
        )
    z.append("")

    rv = zus["rekord_vergleich"]
    z += [
        "## Record-Ebene\n",
        "| Lage | Records |",
        "|---|---:|",
        f"| beide vollstaendig exakt | {rv.get('beide_exakt', 0)} |",
        f"| nur {a} vollstaendig exakt | {rv.get('nur_a_exakt', 0)} |",
        f"| nur {b} vollstaendig exakt | {rv.get('nur_b_exakt', 0)} |",
        f"| keiner vollstaendig exakt | {rv.get('keiner_exakt', 0)} |",
        "",
        f"Records, in denen nur {a} mindestens eine richtige Zelle hat: {zus['nur_a_treffer']}. "
        f"Records, in denen nur {b} mindestens eine richtige Zelle hat: {zus['nur_b_treffer']}.\n",
        f"Leere Antworten: {a} {zus['leere_records'][a]}, {b} {zus['leere_records'][b]}, "
        f"in beiden leer: {zus['leere_records_ueberlappung']}.\n",
        "## Kosten je richtiger Zelle\n",
        "| Modell | Tokens | richtige Zellen | Tokens je richtige Zelle |",
        "|---|---:|---:|---:|",
    ]
    je_zelle = {m: k["tokens"] / k["richtig"] for m, k in ((a, ka), (b, kb))}
    for m, k in ((a, ka), (b, kb)):
        z.append(f"| {m} | {k['tokens']} | {k['richtig']} | {je_zelle[m]:.1f} |")
    z.append("")
    z.append(
        f"Faktor: {b} kostet je richtiger Zelle das {je_zelle[b] / je_zelle[a]:.1f}-fache von {a}.\n"
    )

    (args.out_dir / "vergleich.md").write_text("\n".join(z), encoding="utf-8")
    print("\n".join(z))
    print(f"geschrieben: {args.out_dir / 'vergleich.md'}")
    print(f"geschrieben: {args.out_dir / 'vergleich.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
