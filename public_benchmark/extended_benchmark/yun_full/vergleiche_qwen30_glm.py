#!/usr/bin/env python
"""Vergleicht zwei Modelle eines Yun-699-Laufs auf einer Lesekopie.

Grundlage sind die Einzelauswertungen von `auswerte_yun699.py` (je Modell eine
JSON-Datei). Dieses Skript liest zusaetzlich die Predictions der Kopie, um die
Fragen zu beantworten, die eine Kennzahl allein nicht beantwortet:

- Woraus bestehen die fehlenden Zellen (leere Antwort, Gruppenfeld, Rest)?
- Sind die Ausfaelle technisch oder inhaltlich (Modell antwortet, aber leer)?
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

# Gruppenfelder werden getrennt gezaehlt: Sie sind bei manchen Modellen nicht
# eine Frage der Extraktion, sondern der Prompt-Einstellung (group_size_mode).
GRUPPENFELDER = {"intervention_group_size", "comparator_group_size"}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def ist_leer(row: dict) -> bool:
    return not row.get("rows") and not row.get("fehlerklasse")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, help="Run-Verzeichnis unter runs/ (Lesekopie)")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--modell-a", default="qwen30")
    ap.add_argument("--modell-b", default="glm")
    args = ap.parse_args()

    lauf = RUNS / args.run
    rows = lies(lauf / "predictions.jsonl")
    gold_records = {r["record_id"]: r for r in lies(RECORDS)}

    res = {}
    for modell in (args.modell_a, args.modell_b):
        pfad = args.out_dir / f"{modell}_lesekopie.json"
        if not pfad.exists():
            print(f"FEHLER: {pfad} fehlt - erst auswerte_yun699.py --model {modell}")
            return 2
        res[modell] = json.loads(pfad.read_text(encoding="utf-8"))

    # --- Zellstatus je Record und Modell, damit die Fehlbetraege zerlegbar sind ---
    je_record: dict[str, dict[str, dict]] = defaultdict(dict)
    leer_records: dict[str, set[str]] = {}
    gruppen_modus: dict[str, Counter] = {}
    pfade: dict[str, Counter] = {}
    tokens_je_record: dict[str, float] = {}

    for modell in (args.modell_a, args.modell_b):
        eigene = [r for r in rows if r["model"] == modell]
        leer_records[modell] = {r["record_id"] for r in eigene if ist_leer(r)}
        gruppen_modus[modell] = Counter(r.get("group_size_mode") or "?" for r in eigene)
        pfade[modell] = Counter(r.get("pfad") or "?" for r in eigene)
        tokens_je_record[modell] = sum(
            sum(wert or 0 for wert in (r.get("completion_tokens"), r.get("retry_tokens"), r.get("repair_tokens")))
            for r in eigene
        )
        for row in eigene:
            record = gold_records[row["record_id"]]
            gold = {c["field"]: c["value"] for c in record["gold"]["cells"]}
            gesehen = {}
            for zelle in row.get("rows") or []:
                gesehen.setdefault(zelle["field"], zelle["value"])
            richtig = falsch = fehlend = 0
            for feld, wert in gold.items():
                if feld not in gesehen:
                    fehlend += 1
                elif abs(gesehen[feld] - wert) < 1e-9:
                    richtig += 1
                else:
                    falsch += 1
            je_record[row["record_id"]][modell] = {
                "richtig": richtig,
                "falsch": falsch,
                "fehlend": fehlend,
                "leer": ist_leer(row),
            }

    # Zerlegung der fehlenden Zellen des Modells A.
    a = args.modell_a
    fehlend_zerlegt = Counter()
    for stand in je_record.values():
        info = stand[a]
        if info["fehlend"] == 0:
            continue
        if info["leer"]:
            fehlend_zerlegt["leere_antwort"] += info["fehlend"]
        else:
            fehlend_zerlegt["nicht_gemeldet"] += info["fehlend"]

    # Aufteilung nach Gruppenfeld / Nicht-Gruppenfeld aus Sicht des Modells A.
    gruppenanalyse = Counter()
    for rid in je_record:
        gold = {c["field"]: c["value"] for c in gold_records[rid]["gold"]["cells"]}
        row = next(r for r in rows if r["record_id"] == rid and r["model"] == a)
        gesehen = {}
        for zelle in row.get("rows") or []:
            gesehen.setdefault(zelle["field"], zelle["value"])
        for feld, wert in gold.items():
            schluessel_gruppe = "gruppe" if feld in GRUPPENFELDER else "sonstiges"
            if feld not in gesehen:
                gruppenanalyse[f"{schluessel_gruppe}_fehlend"] += 1
            elif abs(gesehen[feld] - wert) < 1e-9:
                gruppenanalyse[f"{schluessel_gruppe}_richtig"] += 1
            else:
                gruppenanalyse[f"{schluessel_gruppe}_falsch"] += 1

    # Record-Ebene: wer ist wo richtig (vollstaendig richtige Records je Modell).
    rekord_vergleich = Counter()
    for rid, stand in je_record.items():
        a_ok = stand[a]["richtig"] > 0 and stand[a]["falsch"] == 0 and stand[a]["fehlend"] == 0
        b_ok = stand[args.modell_b]["richtig"] > 0 and stand[args.modell_b]["falsch"] == 0 and stand[args.modell_b]["fehlend"] == 0
        if a_ok and b_ok:
            rekord_vergleich["beide_exakt"] += 1
        elif a_ok:
            rekord_vergleich["nur_a_exakt"] += 1
        elif b_ok:
            rekord_vergleich["nur_b_exakt"] += 1
        else:
            rekord_vergleich["keiner_exakt"] += 1

    # Records, in denen ein Modell mindestens eine richtige Zelle hat, das andere keine.
    nur_a_treffer = sum(
        1 for stand in je_record.values()
        if stand[a]["richtig"] > 0 and stand[args.modell_b]["richtig"] == 0
    )
    nur_b_treffer = sum(
        1 for stand in je_record.values()
        if stand[args.modell_b]["richtig"] > 0 and stand[a]["richtig"] == 0
    )

    zus = {
        "leere_records": {m: len(leer_records[m]) for m in (a, args.modell_b)},
        "leere_records_ueberlappung": len(leer_records[a] & leer_records[args.modell_b]),
        "gruppen_modus": {m: dict(gruppen_modus[m]) for m in (a, args.modell_b)},
        "pfade": {m: dict(pfade[m]) for m in (a, args.modell_b)},
        "fehlend_zerlegt": dict(fehlend_zerlegt),
        "gruppenanalyse": dict(gruppenanalyse),
        "rekord_vergleich": dict(rekord_vergleich),
        "nur_a_treffer": nur_a_treffer,
        "nur_b_treffer": nur_b_treffer,
        "tokens": {m: tokens_je_record[m] for m in (a, args.modell_b)},
    }

    # Die Abweichungsliste steht vollstaendig in den Modell-JSONs; hier wird sie
    # nicht noch einmal dupliziert, sondern nur auf die Kennzahlen verwiesen.
    auswertung = {
        m: {k: v for k, v in z.items() if k != "abweichungen"} for m, z in res.items()
    }
    ausgabe = {"run": args.run, "modelle": [a, args.modell_b], "auswertung": auswertung, "zusatz": zus}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "vergleich.json").write_text(
        json.dumps(ausgabe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # --- Markdown ---
    def kennzahl(m: str) -> dict:
        z = res[m]
        return {
            "richtig": z["zellen"]["richtig"],
            "falsch": z["zellen"]["falsch"],
            "fehlend": z["zellen"]["fehlend"],
            "ohne_gold": z["zellen"]["ohne_gold"],
            "precision": z["precision"],
            "recall": z["recall"],
            "f1": z["f1"],
            "mae": z["mae"],
            "exakt": z["records_status"].get("exakt_strict", 0),
            "ausfaelle": z["technische_ausfaelle"],
            "leer": z["leere_antworten"],
            "tokens": z["tokens"],
        }

    ka, kb = kennzahl(a), kennzahl(args.modell_b)
    zeilen: list[str] = []
    zeilen.append(f"# {a} gegen {args.modell_b} auf Yun-699 (Lesekopie)\n")
    zeilen.append(
        f"Quelle: `runs/{args.run}/predictions.jsonl` (Lesekopie der laufenden Datei), "
        f"Gold: `records/yun699.jsonl`. Beide Modelle mit 699 Records, "
        f"2773 Goldzellen. Alle Zahlen aus `{a}_lesekopie.json`, `{args.modell_b}_lesekopie.json` "
        "und `vergleich.json` in diesem Ordner.\n"
    )
    zeilen.append("## Gesamtkennzahlen\n")
    zeilen.append(f"| Kennzahl | {a} | {args.modell_b} | Differenz |")
    zeilen.append("|---|---:|---:|---:|")

    def diff(x: float, y: float, fmt: str = "{:+.4f}") -> str:
        return fmt.format(x - y)

    paare = [
        ("richtig", "richtig", "", True),
        ("falsch", "falsch", "", True),
        ("fehlend", "fehlend", "", True),
        ("Zellen ohne Gold", "ohne_gold", "", True),
        ("Precision", "precision", "", False),
        ("Recall", "recall", "", False),
        ("F1", "f1", "", False),
        ("MAE", "mae", "", False),
        ("Records exakt (strict)", "exakt", "", True),
        ("technische Ausfaelle", "ausfaelle", "", True),
        ("leere Antworten", "leer", "", True),
        ("Tokens", "tokens", "", True),
    ]
    for label, schluessel, _, ganz in paare:
        va, vb = ka[schluessel], kb[schluessel]
        if va is None or vb is None:
            zeilen.append(f"| {label} | {va} | {vb} | - |")
        elif ganz:
            zeilen.append(f"| {label} | {va} | {vb} | {va - vb:+d} |")
        else:
            zeilen.append(f"| {label} | {va:.4f} | {vb:.4f} | {diff(va, vb)} |")
    zeilen.append("")

    zellen_a = res[a]["zellen"]["richtig"] + res[a]["zellen"]["falsch"]
    zeilen.append(
        f"Bezugsgroesse Precision: {zellen_a} bewertbare Meldungen von {a}, "
        f"{res[args.modell_b]['zellen']['richtig'] + res[args.modell_b]['zellen']['falsch']} von {args.modell_b}.\n"
    )

    zeilen.append("## Woher die fehlenden Zellen kommen\n")
    z = zus["fehlend_zerlegt"]
    zeilen.append(f"| Ursache | Zellen |")
    zeilen.append("|---|---:|")
    zeilen.append(f"| leere Antwort ({zus['leere_records'][a]} Records) | {z.get('leere_antwort', 0)} |")
    zeilen.append(f"| geantwortet, Feld nicht gemeldet | {z.get('nicht_gemeldet', 0)} |")
    zeilen.append(
        f"| Summe | {z.get('leere_antwort', 0) + z.get('nicht_gemeldet', 0)} |\n"
    )

    g = zus["gruppenanalyse"]
    zeilen.append(f"Zellstatus von {a}, getrennt nach Gruppenfeldern (N je Arm):\n")
    zeilen.append("| Feldgruppe | richtig | falsch | fehlend |")
    zeilen.append("|---|---:|---:|---:|")
    for gruppe, label in (("gruppe", "Gruppengroesse"), ("sonstiges", "Mittelwerte, SD, Events")):
        zeilen.append(
            f"| {label} | {g.get(gruppe + '_richtig', 0)} | {g.get(gruppe + '_falsch', 0)} | "
            f"{g.get(gruppe + '_fehlend', 0)} |"
        )
    zeilen.append(
        "\nEinstellung `group_size_mode` je Modell: "
        + ", ".join(f"{m}: {zus['gruppen_modus'][m]}" for m in (a, args.modell_b))
        + "\n"
    )

    zeilen.append("## Feldebene\n")
    zeilen.append(f"| Feld | {a} richtig | {a} falsch | {a} fehlend | {args.modell_b} richtig | {args.modell_b} fehlend |")
    zeilen.append("|---|---:|---:|---:|---:|---:|")
    felder = sorted(set(res[a]["je_feld"]) | set(res[args.modell_b]["je_feld"]))
    for feld in felder:
        fa = res[a]["je_feld"].get(feld, {})
        fb = res[args.modell_b]["je_feld"].get(feld, {})
        zeilen.append(
            f"| {feld} | {fa.get('richtig', 0)} | {fa.get('falsch', 0)} | {fa.get('fehlend', 0)} | "
            f"{fb.get('richtig', 0)} | {fb.get('fehlend', 0)} |"
        )
    zeilen.append("")

    zeilen.append("## Nach Outcome-Typ\n")
    zeilen.append(f"| Typ | {a} richtig | {a} fehlend | {args.modell_b} richtig | {args.modell_b} fehlend |")
    zeilen.append("|---|---:|---:|---:|---:|")
    typen = sorted(set(res[a]["je_outcome_typ"]) | set(res[args.modell_b]["je_outcome_typ"]))
    for typ in typen:
        ta = res[a]["je_outcome_typ"].get(typ, {})
        tb = res[args.modell_b]["je_outcome_typ"].get(typ, {})
        zeilen.append(
            f"| {typ} | {ta.get('richtig', 0)} | {ta.get('fehlend', 0)} | "
            f"{tb.get('richtig', 0)} | {tb.get('fehlend', 0)} |"
        )
    zeilen.append("")

    rv = zus["rekord_vergleich"]
    zeilen.append("## Record-Ebene\n")
    zeilen.append("| Lage | Records |")
    zeilen.append("|---|---:|")
    zeilen.append(f"| beide vollstaendig exakt | {rv.get('beide_exakt', 0)} |")
    zeilen.append(f"| nur {a} vollstaendig exakt | {rv.get('nur_a_exakt', 0)} |")
    zeilen.append(f"| nur {args.modell_b} vollstaendig exakt | {rv.get('nur_b_exakt', 0)} |")
    zeilen.append(f"| keiner vollstaendig exakt | {rv.get('keiner_exakt', 0)} |")
    zeilen.append("")
    zeilen.append(
        f"Records, in denen nur {a} mindestens eine richtige Zelle hat: {zus['nur_a_treffer']}. "
        f"Records, in denen nur {args.modell_b} mindestens eine richtige Zelle hat: {zus['nur_b_treffer']}.\n"
    )
    zeilen.append(
        f"Leere Antworten: {a} {zus['leere_records'][a]}, {args.modell_b} {zus['leere_records'][args.modell_b]}, "
        f"in beiden leer: {zus['leere_records_ueberlappung']}.\n"
    )

    ta_, tb_ = ka["tokens"], kb["tokens"]
    ra_, rb_ = ka["richtig"], kb["richtig"]
    zeilen.append("## Kosten je richtiger Zelle\n")
    zeilen.append("| Modell | Tokens | richtige Zellen | Tokens je richtige Zelle |")
    zeilen.append("|---|---:|---:|---:|")
    zeilen.append(f"| {a} | {ta_} | {ra_} | {ta_ / ra_:.1f} |")
    zeilen.append(f"| {args.modell_b} | {tb_} | {rb_} | {tb_ / rb_:.1f} |")
    zeilen.append("")
    zeilen.append(
        f"Faktor: {args.modell_b} kostet je richtiger Zelle das "
        f"{(tb_ / rb_) / (ta_ / ra_):.1f}-fache von {a}.\n"
    )

    (args.out_dir / "vergleich.md").write_text("\n".join(zeilen) + "", encoding="utf-8")
    print("\n".join(zeilen))
    print(f"geschrieben: {args.out_dir / 'vergleich.md'}")
    print(f"geschrieben: {args.out_dir / 'vergleich.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
