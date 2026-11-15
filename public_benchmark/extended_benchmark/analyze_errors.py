#!/usr/bin/env python3
"""Systematische Fehleranalyse der Yun-Laeufe.

Vergleicht jede Vorhersage mit den Gold-Zellen, klassifiziert Abweichungen nach
einem festen Schema und schreibt vier Ausgaben. Jede Klasse ist aus den Daten
nachrechenbar; wo die Ursache nicht belegbar ist, steht "nicht eindeutig".

Die Metriken selbst werden nicht neu erfunden: Sie kommen aus
``evaluate_extended.evaluate_numeric``, und das Modul prueft, dass die Werte
mit den gespeicherten ``eval/*.metrics.json`` uebereinstimmen.

Aufruf:

    python public_benchmark/extended_benchmark/analyze_errors.py \
        --out public_benchmark/extended_benchmark/analysis/v1_20261115
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from extended_benchmark.evaluate_extended import evaluate_numeric  # noqa: E402
from extended_benchmark.versions import BESCHREIBUNG, normalisiere_version, status_von  # noqa: E402

RUNS = HERE / "runs"
RECORDS = HERE / "records" / "yun_dev.jsonl"

KLASSEN = {
    1: "Falsche Tabellenzeile",
    2: "Falsche Tabellenspalte",
    3: "Falscher Messzeitpunkt",
    4: "Falsche Studienpopulation",
    5: "Interventions-/Kontrollgruppe verwechselt",
    6: "Ereignisse und Teilnehmer verwechselt",
    7: "Prozentwert und absolute Zahl verwechselt",
    8: "Falsche statistische Kennzahl",
    9: "Zahlenwert falsch gelesen",
    10: "Zahl nicht extrahiert",
    11: "Halluzinierter Wert",
    12: "Parser- oder Formatierungsfehler",
    13: "Unvollstaendige Modellantwort",
    14: "Sonstiger Fehler",
    15: "Nicht eindeutig klassifizierbar",
}

# Manuell am Artikel geprueft, mit Quelle. Nur hier eingetragen, wenn ein
# Bericht den Fall belegt; alles andere bleibt Klassifikation aus den Daten.
# Schluessel ist (record_id, field, arm): Die Belege stammen aus dem Artikel,
# nicht aus einem einzelnen Lauf, und gelten deshalb fuer jede Prompt-Version.
GEPRUEFTE_FAELLE: dict[tuple[str, str, str], tuple[int, str]] = {
    ("yun2024:229", "intervention_mean", "intervention"): (
        3,
        "geprueft am 15.11.2026: 854 ist die Follow-up-Spalte nach vier Monaten in PMC5498715 "
        "(runs/yun_dev_20261114/report.md)",
    ),
    ("yun2024:229", "intervention_standard_deviation", "intervention"): (
        3,
        "geprueft am 15.11.2026: 271,60 ist die Follow-up-Spalte nach vier Monaten in PMC5498715",
    ),
    ("yun2024:229", "comparator_mean", "comparator"): (
        3,
        "geprueft am 15.11.2026: 470 ist die Follow-up-Spalte nach vier Monaten in PMC5498715",
    ),
    ("yun2024:229", "comparator_standard_deviation", "comparator"): (
        3,
        "geprueft am 15.11.2026: 80,46 ist die Follow-up-Spalte nach vier Monaten in PMC5498715",
    ),
    # Sichtpruefung 15.11.2026 (analysis/v1_20261115/events_review.md): 48 ist die
    # Ereigniszahl der Zeile "0-3 months" in PMC5244530; die Uebereinstimmung mit
    # der Rate 64/133 = 48,1 Prozent ist Zufall. Prozentklasse zurueckgenommen.
    ("yun2024:191", "comparator_events", "comparator"): (
        1,
        "geprueft am 15.11.2026: 48 ist die Ereigniszahl der Zeile '0-3 months' "
        "(Gold 64 = 'Total 0-12 months'); die Prozentrate 48,1 ist Koinzidenz",
    ),
    ("yun2024:191", "intervention_events", "intervention"): (
        1,
        "geprueft am 15.11.2026: 31 ist die Ereigniszahl der Zeile '0-3 months' "
        "(Gold 49 = 'Total 0-12 months'), gleiche Zeile wie die Partnerzelle",
    ),
    ("yun2024:3", "intervention_mean", "intervention"): (
        15,
        "Artikel nennt fuer denselben Wert 50,7 und 50,6 (Selbstwiderspruch im Text); "
        "Gold 50,6, Modell 50,7 - beide Schreibweisen belegt",
    ),
}

# Auffaellige Gold-Zellen, die am Artikel geprueft wurden (Punkt Aufgabe C).
MANUELLE_GOLD_HINWEISE: dict[tuple[str, str, str], str] = {
    ("yun2024:3", "intervention_mean", "intervention"): (
        "Artikel nennt 50,6 und 50,7 gm fuer denselben Wert; Gold nutzt 50,6"
    ),
}

# Lauf 1 entstand vor Einfuehrung des Feldes prompt_version.
VERSION_FALLBACK = {"yun_dev_20261114": "v1"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def zahlenvarianten(value: float) -> list[str]:
    """Schreibweisen, mit denen eine Zahl im Artikeltext auftauchen kann."""
    variants = []
    for digits in (2, 1, 0):
        text = f"{value:.{digits}f}"
        if text.endswith(".0"):
            text = text[:-2]
        variants.append(text)
        variants.append(text.replace(".", ","))
    if value < 0:
        for digits in (2, 1):
            ohne = f"- {abs(value):.{digits}f}".rstrip("0").rstrip(".")
            variants.append(ohne)
            variants.append(ohne.replace(".", ","))
    # Tausendertrennzeichen, wie in groesseren Tabellen ueblich.
    if abs(value) >= 1000:
        variants.append(f"{value:,.0f}")
        variants.append(f"{value:,.2f}")
        variants.append(f"{value:,.0f}".replace(",", "."))
    seen = []
    for variant in variants:
        if variant not in seen:
            seen.append(variant)
    return seen


class Dokument:
    """Artikeltext mit Zwischenspeicher fuer Zahlensuchen."""

    def __init__(self, path: Path) -> None:
        roh = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        # Unicode-Minus und Gedankenstrich auf ASCII-Minus normalisieren.
        self.text = roh.replace("\u2212", "-").replace("\u2013", "-")
        self._cache: dict[float, tuple[int, int]] = {}

    def finde(self, value: float) -> tuple[int, int]:
        if value in self._cache:
            return self._cache[value]
        best = (0, -1)
        for variant in zahlenvarianten(value):
            pattern = r"(?<![\d.,])" + re.escape(variant) + r"(?![\d])"
            matches = list(re.finditer(pattern, self.text))
            if matches and len(matches) > best[0]:
                best = (len(matches), matches[0].start())
        self._cache[value] = best
        return best

    def ausschnitt(self, index: int, radius: int = 90) -> str:
        if index < 0:
            return ""
        snippet = self.text[max(0, index - radius) : index + radius]
        return re.sub(r"\s+", " ", snippet).strip()


def klassifiziere(
    *,
    gold: float,
    pred: float,
    field: str,
    arm: str,
    gold_cells: dict[tuple[str, str], float],
    pred_cells: dict[tuple[str, str], float],
    dokument: Dokument,
    geschwister: list[tuple[float, str]],
) -> tuple[int, str]:
    """Ordnet einer falschen Vorhersage eine Klasse zu, mit Beleg."""
    if pred == gold:
        return 14, "keine Abweichung"

    other_arm = "comparator" if arm == "intervention" else "intervention"
    partner = (field, other_arm)

    if partner in gold_cells and pred == gold_cells[partner]:
        vollstaendig = pred_cells.get(partner) == gold
        zusatz = "beide Arme vollstaendig vertauscht" if vollstaendig else "Wert des anderen Arms uebernommen"
        return 5, zusatz

    if field.endswith("_events"):
        size = gold_cells.get((field.replace("_events", "_group_size"), arm))
        other_size = gold_cells.get((field.replace("_events", "_group_size"), other_arm))
        if size is not None and pred == size:
            return 6, f"Vorhersage entspricht der Gruppengroesse ({size:g}) desselben Arms"
        if other_size is not None and pred == other_size:
            return 6, f"Vorhersage entspricht der Gruppengroesse ({other_size:g}) des anderen Arms"
        if size and gold and abs(pred - gold / size * 100) <= 1.0:
            return 7, f"Vorhersage entspricht dem Prozentwert ({gold / size * 100:.2f}) der Ereignisrate"
        if gold and abs(pred - gold * 100) <= 0.5:
            return 7, "Vorhersage ist der Prozentwert zur Gold-Ereigniszahl"
        if other_arm in dict(gold_cells) or True:
            other_events = gold_cells.get((field, other_arm))
            if other_events is not None and pred == other_events:
                return 5, f"Ereigniszahl des anderen Arms ({other_events:g}) uebernommen"

    # Wert eines anderen Feldes desselben Records?
    for (other_field, other_arm_name), other_value in gold_cells.items():
        if (other_field, other_arm_name) == (field, arm):
            continue
        if pred == other_value:
            if {field, other_field} <= {"intervention_mean", "intervention_standard_deviation", "comparator_mean", "comparator_standard_deviation"}:
                return 8, f"Vorhersage entspricht {other_field}/{other_arm_name} ({other_value:g})"
            return 1, f"Vorhersage entspricht {other_field}/{other_arm_name} ({other_value:g})"

    # Wert eines anderen Outcomes im selben Artikel? Das ist der haeufigste
    # Tabellenfehler: die Zahl stimmt, die Zeile nicht.
    for other_value, label in geschwister:
        if pred == other_value:
            return 1, f"Wert stammt aus der Zeile {label} desselben Artikels"

    treffer, index = dokument.finde(pred)
    if treffer:
        mehrfach = f", {treffer} Treffer im Text" if treffer > 1 else ""
        return 15, f"Wert steht wortwoertlich im Artikel{mehrfach}; Zeile, Spalte oder Zeitpunkt nicht belegbar"

    return 11, "Wert kommt im Artikeltext nicht vor"


def baue_faelle(
    run_id: str,
    model: str,
    prompt_version: str,
    records: list[dict[str, Any]],
    rows: dict[str, dict[str, Any]],
    dokumente: dict[str, Dokument],
    cache_verdacht: bool,
    geschwister_index: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    faelle: list[dict[str, Any]] = []
    zusatz: list[dict[str, Any]] = []
    zellen = 0
    for record in records:
        rid = record["record_id"]
        row = rows.get(rid)
        gold = {(c["field"], c["arm"]): float(c["value"]) for c in record["gold"]["cells"]}
        pred: dict[tuple[str, str], float] = {}
        pred_list: list[dict[str, Any]] = []
        if row:
            pred_list = row["predicted"]["cells"]
            for cell in pred_list:
                pred[(cell["field"], cell["arm"])] = float(cell["value"])
        dokument = dokumente[record["document"]["id"]]
        technisch = not pred_list
        zellen += len(gold)

        for (field, arm), gold_value in gold.items():
            treffer = pred.get((field, arm))
            basis = {
                "run_id": run_id,
                "prompt_version": prompt_version,
                "model": model,
                "record_id": rid,
                "field": field,
                "arm": arm,
                "gold": gold_value,
                "prediction": "" if treffer is None else treffer,
                "abs_error": "" if treffer is None else round(abs(treffer - gold_value), 4),
                "pmcid": record["document"]["id"],
                "quelle": record["document"]["path"],
                "cache_verdacht": cache_verdacht,
            }
            if treffer is None:
                if technisch:
                    klasse, beleg = 13, "Modell lieferte keine verwertbaren Zellen"
                else:
                    klasse, beleg = 10, "Feld im Artikel nicht extrahiert"
                abs_index = -1
                snippet = ""
                fall_typ = "fehlend"
            elif treffer == gold_value:
                continue
            else:
                geprueft = GEPRUEFTE_FAELLE.get((rid, field, arm))
                if geprueft:
                    klasse, beleg = geprueft
                else:
                    klasse, beleg = klassifiziere(
                        gold=gold_value,
                        pred=treffer,
                        field=field,
                        arm=arm,
                        gold_cells=gold,
                        pred_cells=pred,
                        dokument=dokument,
                        geschwister=[
                            (entry["value"], f"{entry['outcome']} ({entry['field']}, {entry['arm']})")
                            for entry in geschwister_index.get(record["document"]["id"], [])
                            if entry["field"] == field
                        ],
                    )
                _, abs_index = dokument.finde(treffer)
                snippet = dokument.ausschnitt(abs_index)
                fall_typ = "falsch"

            faelle.append(
                {
                    **basis,
                    "klasse": klasse,
                    "klasse_name": KLASSEN[klasse],
                    "fall_typ": fall_typ,
                    "beleg": beleg,
                    "textstelle": snippet,
                    "zeitpunkt": "nicht erfasst",
                    "population": "nicht erfasst",
                    "gruppe": arm,
                }
            )

        for cell in pred_list:
            key = (cell["field"], cell["arm"])
            if key in gold:
                continue
            dokument_hat, abs_index = dokument.finde(float(cell["value"]))
            zusatz.append(
                {
                    "run_id": run_id,
                    "prompt_version": prompt_version,
                    "model": model,
                    "record_id": rid,
                    "field": cell["field"],
                    "arm": cell["arm"],
                    "gold": "",
                    "prediction": float(cell["value"]),
                    "abs_error": "",
                    "pmcid": record["document"]["id"],
                    "quelle": record["document"]["path"],
                    "cache_verdacht": cache_verdacht,
                    "klasse": 15,
                    "klasse_name": "Zusaetzliche Zelle ohne Gold-Pendant",
                    "fall_typ": "zusaetzlich",
                    "beleg": "Vorhersage fuer Feld/Arm ohne Gold-Zelle"
                    + (" (Wert steht im Text)" if dokument_hat else " (Wert nicht im Text)"),
                    "textstelle": dokument.ausschnitt(abs_index) if dokument_hat else "",
                    "zeitpunkt": "nicht erfasst",
                    "population": "nicht erfasst",
                    "gruppe": cell["arm"],
                }
            )

    zusammenfassung = {
        "zaehler": Counter(f["klasse"] for f in faelle),
        "zellen": zellen,
        "zusatz": len(zusatz),
    }
    return faelle, zusatz, zusammenfassung


def pruefe_gold(records: list[dict[str, Any]], dokumente: dict[str, Dokument]) -> list[dict[str, Any]]:
    """Prueft jede Gold-Zelle gegen den Artikeltext und auf Plausibilitaet."""
    befunde = []
    for record in records:
        dokument = dokumente[record["document"]["id"]]
        gold = {(c["field"], c["arm"]): float(c["value"]) for c in record["gold"]["cells"]}
        for cell in record["gold"]["cells"]:
            field, arm, value = cell["field"], cell["arm"], float(cell["value"])
            treffer, index = dokument.finde(value)
            probleme = []
            if not dokument.text:
                probleme.append("kein Artikeltext vorhanden")
            elif treffer == 0:
                probleme.append("Wert nicht wortwoertlich im Text (Umrechnung, Rundung oder Fehler)")
            if field.endswith("_events"):
                size = gold.get((field.replace("_events", "_group_size"), arm))
                if size and value > size:
                    probleme.append("Ereignisse groesser als Gruppengroesse")
            hinweis = MANUELLE_GOLD_HINWEISE.get((record["record_id"], field, arm))
            if hinweis:
                probleme.append(hinweis)
            befunde.append(
                {
                    "record_id": record["record_id"],
                    "pmcid": record["document"]["id"],
                    "field": field,
                    "arm": arm,
                    "gold": value,
                    "treffer_im_text": treffer,
                    "probleme": probleme,
                    "textstelle": dokument.ausschnitt(index) if index >= 0 else "",
                    "braucht_pruefung": bool(probleme),
                }
            )
    return befunde


def metrik_abgleich(run_dir: Path, records: list[dict[str, Any]], model: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Rechnet die Metriken neu und vergleicht sie mit eval/<model>.metrics.json."""
    predictions = {row["record_id"]: {"predicted": row["predicted"]} for row in rows}
    frisch = evaluate_numeric(records, predictions)
    gespeichert = None
    path = run_dir / "eval" / f"{model}.metrics.json"
    if path.exists():
        gespeichert = json.loads(path.read_text(encoding="utf-8"))
    abweichung = []
    if gespeichert:
        for key in ("cell_recall", "cell_precision", "cell_f1", "mae_pairs", "mae_coverage"):
            if gespeichert.get(key) != frisch.get(key):
                abweichung.append(f"{key}: gespeichert {gespeichert.get(key)} vs neu {frisch.get(key)}")
    return {
        "metriken": {k: frisch[k] for k in ("cell_recall", "cell_precision", "cell_f1", "mae_pairs", "mae_coverage", "mae_pairs_covered", "gold_cells", "record_exact", "records")},
        "ableitung_identisch": not abweichung,
        "abweichungen": abweichung,
    }


def baue_queue(faelle: list[dict[str, Any]], korrekte: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pruefwarteschlange mit fester Prioritaetsreihenfolge."""
    queue: list[dict[str, Any]] = []
    for fall in faelle:
        abs_error = fall["abs_error"] if fall["abs_error"] != "" else None
        if fall["field"].endswith("_events") and fall["fall_typ"] == "falsch":
            prio, grund = 1, "falsche Ereigniszahl"
        elif fall["fall_typ"] == "fehlend":
            prio, grund = 2, "fehlende Zelle"
        elif abs_error is not None and abs_error >= 5:
            prio, grund = 3, f"grosse Abweichung ({abs_error})"
        elif fall["klasse"] == 15:
            prio, grund = 4, "Zuordnung mehrdeutig"
        else:
            prio, grund = 4, "sonstiger Fehlerfall"
        queue.append(
            {
                "prioritaet": prio,
                "grund": grund,
                "prompt_version": fall["prompt_version"],
                "status": status_von(fall["prompt_version"]),
                "run_id": fall["run_id"],
                "model": fall["model"],
                "record_id": fall["record_id"],
                "field": fall["field"],
                "arm": fall["arm"],
                "gold": fall["gold"],
                "prediction": fall["prediction"],
                "abs_error": fall["abs_error"],
                "klasse": fall["klasse_name"],
                "beleg": fall["beleg"],
                "quelle": f"{fall['pmcid']} ({fall['quelle']})",
                "pruefstatus": "offen",
            }
        )
    for fall in korrekte:
        queue.append(
            {
                "prioritaet": 5,
                "grund": "Kontrollfall korrekt",
                "prompt_version": fall["prompt_version"],
                "status": status_von(fall["prompt_version"]),
                "run_id": fall["run_id"],
                "model": fall["model"],
                "record_id": fall["record_id"],
                "field": fall["field"],
                "arm": fall["arm"],
                "gold": fall["gold"],
                "prediction": fall["prediction"],
                "abs_error": 0,
                "klasse": "korrekt",
                "beleg": "Kontrollstichprobe",
                "quelle": f"{fall['pmcid']} ({fall['quelle']})",
                "pruefstatus": "offen",
            }
        )
    queue.sort(key=lambda row: (row["prioritaet"], row["record_id"]))
    return queue


def schreibe_csv(path: Path, rows: list[dict[str, Any]], felder: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=felder, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(HERE / "analysis" / "v1_20261115"))
    parser.add_argument("--seed", type=int, default=20261115)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = read_jsonl(RECORDS)
    dokumente = {r["document"]["id"]: Dokument(HERE.parent.parent / r["document"]["path"]) for r in records}
    geschwister_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for other in records:
        for cell in other["gold"]["cells"]:
            geschwister_index[other["document"]["id"]].append(
                {
                    "pmcid": other["document"]["id"],
                    "outcome": other["context"].get("outcome") or other["record_id"],
                    "field": cell["field"],
                    "arm": cell["arm"],
                    "value": float(cell["value"]),
                }
            )

    laeufe = []
    for run_dir in sorted(path for path in RUNS.iterdir() if path.is_dir()):
        rows = read_jsonl(run_dir / "predictions.jsonl")
        if not rows:
            continue
        modelle = sorted({row["model"] for row in rows})
        versionen = sorted({row.get("prompt_version", "unbekannt") for row in rows})
        laeufe.append(
            {
                "run_id": run_dir.name,
                "rows": rows,
                "modelle": modelle,
                "versionen": versionen,
                "diagnose": len(rows) < 10,
            }
        )

    alle_faelle: list[dict[str, Any]] = []
    alle_zusatz: list[dict[str, Any]] = []
    alle_korrekt: list[dict[str, Any]] = []
    lauf_uebersicht = []
    abgleich = []
    rng = random.Random(args.seed)

    for lauf in laeufe:
        if lauf["diagnose"]:
            continue
        cache_rate = sum(1 for row in lauf["rows"] if (row.get("elapsed_s") or 99) < 1.0) / len(lauf["rows"])
        for model in lauf["modelle"]:
            rows = [row for row in lauf["rows"] if row["model"] == model]
            roh_version = rows[0].get("prompt_version") or VERSION_FALLBACK.get(lauf["run_id"], "unbekannt")
            version = normalisiere_version(roh_version)
            faelle, zusatz, zusammenfassung = baue_faelle(
                lauf["run_id"],
                model,
                version,
                records,
                {row["record_id"]: row for row in rows},
                dokumente,
                cache_rate >= 0.9,
                geschwister_index,
            )
            alle_faelle.extend(faelle)
            alle_zusatz.extend(zusatz)
            metric = metrik_abgleich(RUNS / lauf["run_id"], records, model, rows)
            abgleich.append({"run_id": lauf["run_id"], "model": model, **metric})
            lauf_uebersicht.append(
                {
                    "run_id": lauf["run_id"],
                    "model": model,
                    "prompt_version": version,
                    "prompt_version_roh": roh_version,
                    "antworten": len(rows),
                    "cache_anteil": round(cache_rate, 3),
                    "leere_antworten": sum(1 for row in rows if not row["predicted"]["cells"]),
                    "gold_zellen": zusammenfassung["zellen"],
                    "fehlerhafte_zellen": len(faelle),
                    "zusaetzliche_zellen": len(zusatz),
                    "klassen": {KLASSEN[k]: v for k, v in sorted(zusammenfassung["zaehler"].items())},
                    "metriken": metric["metriken"],
                    "metriken_identisch": metric["ableitung_identisch"],
                }
            )

            korrekt = []
            for record in records:
                row = next((r for r in rows if r["record_id"] == record["record_id"]), None)
                if not row or not row["predicted"]["cells"]:
                    continue
                gold = {(c["field"], c["arm"]): float(c["value"]) for c in record["gold"]["cells"]}
                for cell in row["predicted"]["cells"]:
                    key = (cell["field"], cell["arm"])
                    if key in gold and float(cell["value"]) == gold[key]:
                        korrekt.append(
                            {
                                "run_id": lauf["run_id"],
                                "prompt_version": version,
                                "model": model,
                                "record_id": record["record_id"],
                                "field": cell["field"],
                                "arm": cell["arm"],
                                "gold": gold[key],
                                "prediction": float(cell["value"]),
                                "pmcid": record["document"]["id"],
                                "quelle": record["document"]["path"],
                            }
                        )
            if korrekt:
                stichprobe = rng.sample(korrekt, k=max(1, min(30, len(korrekt) // 8 or 1)))
                alle_korrekt.extend(stichprobe)

    gold_befunde = pruefe_gold(records, dokumente)

    def aggregat(faelle: list[dict[str, Any]], zusatz: list[dict[str, Any]]) -> dict[str, Any]:
        klassen = Counter(f["klasse_name"] for f in faelle)
        return {
            "fehler": len(faelle),
            "klassen": dict(klassen),
            "technisch": sum(1 for f in faelle if f["klasse"] == 13),
            "inhaltlich": sum(1 for f in faelle if f["klasse"] != 13),
            "nach_modell": {m: dict(Counter(f["klasse_name"] for f in faelle if f["model"] == m)) for m in sorted({f["model"] for f in faelle})},
            "nach_feld": {feld: dict(Counter(f["klasse_name"] for f in faelle if f["field"] == feld)) for feld in sorted({f["field"] for f in faelle})},
            "ereignis_fehler": [
                {
                    "run_id": f["run_id"],
                    "model": f["model"],
                    "record_id": f["record_id"],
                    "field": f["field"],
                    "arm": f["arm"],
                    "gold": f["gold"],
                    "prediction": f["prediction"],
                    "abs_error": f["abs_error"],
                    "klasse": f["klasse_name"],
                }
                for f in faelle
                if f["field"].endswith("_events")
            ],
            "zusaetzliche_zellen": sum(1 for z in zusatz if z["prompt_version"] == (faelle[0]["prompt_version"] if faelle else "")),
            "laeufe": sorted({f["run_id"] for f in faelle}),
            "status": status_von(faelle[0]["prompt_version"] if faelle else ""),
        }

    versionen: dict[str, dict[str, Any]] = {}
    for version in sorted({f["prompt_version"] for f in alle_faelle}):
        faelle_version = [f for f in alle_faelle if f["prompt_version"] == version]
        aggregate = aggregat(faelle_version, alle_zusatz)
        aggregate["beschreibung"] = BESCHREIBUNG.get(version, "")
        versionen[version] = aggregate

    nach_klasse = Counter(f["klasse_name"] for f in alle_faelle)
    nach_feld = defaultdict(Counter)
    for fall in alle_faelle:
        nach_feld[fall["field"]][fall["klasse_name"]] += 1
    nach_modell = defaultdict(Counter)
    for fall in alle_faelle:
        nach_modell[fall["model"]][fall["klasse_name"]] += 1
    nach_version = defaultdict(Counter)
    for fall in alle_faelle:
        nach_version[fall["prompt_version"]][fall["klasse_name"]] += 1

    ereignisse = [f for f in alle_faelle if f["field"].endswith("_events")]
    ereignis_details = []
    for fall in ereignisse:
        ereignis_details.append(
            {
                "run_id": fall["run_id"],
                "prompt_version": fall["prompt_version"],
                "model": fall["model"],
                "record_id": fall["record_id"],
                "field": fall["field"],
                "arm": fall["arm"],
                "gold": fall["gold"],
                "prediction": fall["prediction"],
                "abs_error": fall["abs_error"],
                "klasse": fall["klasse_name"],
                "beleg": fall["beleg"],
                "textstelle": fall["textstelle"][:200],
            }
        )

    queue = baue_queue(alle_faelle, alle_korrekt)
    queue.sort(key=lambda row: (row["prioritaet"], row["run_id"], row["model"], row["record_id"]))
    # Nur die Referenzversion bekommt Pruefzeit. Verworfene und historische
    # Faelle werden getrennt abgelegt, damit nichts verloren geht.
    queue_referenz = [row for row in queue if row["status"] == "referenz"]
    queue_verworfen = [row for row in queue if row["status"] == "verworfen"]
    queue_historisch = [row for row in queue if row["status"] not in ("referenz", "verworfen")]

    ergebnis = {
        "datengrundlage": {
            "records": len(records),
            "gold_zellen": sum(len(r["gold"]["cells"]) for r in records),
            "laeufe": [lauf["run_id"] for lauf in laeufe if not lauf["diagnose"]],
            "diagnoselaeufe": [lauf["run_id"] for lauf in laeufe if lauf["diagnose"]],
        },
        "lauf_uebersicht": lauf_uebersicht,
        "metrik_abgleich": abgleich,
        "versionen": versionen,
        "fehler_nach_klasse": dict(nach_klasse),
        "fehler_nach_modell": {k: dict(v) for k, v in nach_modell.items()},
        "fehler_nach_feld": {k: dict(v) for k, v in nach_feld.items()},
        "fehler_nach_prompt_version": {k: dict(v) for k, v in nach_version.items()},
        "ereigniszahlen": {
            "anzahl_fehler": len(ereignisse),
            "details": ereignis_details,
        },
        "gold_pruefung": {
            "zellen": len(gold_befunde),
            "mit_problem": sum(1 for b in gold_befunde if b["braucht_pruefung"]),
            "befunde": gold_befunde,
        },
        "pruefqueue": {
            "eintraege": len(queue),
            "nach_prioritaet": dict(Counter(q["prioritaet"] for q in queue)),
            "referenz": {
                "datei": "human_review_queue.csv",
                "eintraege": len(queue_referenz),
                "nach_prioritaet": dict(Counter(q["prioritaet"] for q in queue_referenz)),
            },
            "verworfen": {
                "datei": "human_review_discarded.csv",
                "status": "verworfen",
                "eintraege": len(queue_verworfen),
                "versionen": sorted({q["prompt_version"] for q in queue_verworfen}),
            },
            "historisch": {
                "datei": "human_review_historical.csv",
                "eintraege": len(queue_historisch),
                "versionen": sorted({q["prompt_version"] for q in queue_historisch}),
            },
        },
    }
    (out_dir / "error_analysis.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")

    fall_felder = [
        "run_id", "prompt_version", "model", "record_id", "field", "arm", "gold", "prediction",
        "abs_error", "klasse", "klasse_name", "fall_typ", "beleg", "pmcid", "quelle",
        "textstelle", "zeitpunkt", "population", "gruppe", "cache_verdacht",
    ]
    schreibe_csv(out_dir / "error_cases.csv", alle_faelle + alle_zusatz, fall_felder)

    queue_felder = [
        "prioritaet", "grund", "prompt_version", "status", "run_id", "model", "record_id", "field", "arm", "gold",
        "prediction", "abs_error", "klasse", "beleg", "quelle", "pruefstatus",
    ]
    schreibe_csv(out_dir / "human_review_queue.csv", queue_referenz, queue_felder)
    schreibe_csv(out_dir / "human_review_discarded.csv", queue_verworfen, queue_felder)
    schreibe_csv(out_dir / "human_review_historical.csv", queue_historisch, queue_felder)

    zeilen = ["# Fehleranalyse Yun-Dev", ""]
    zeilen.append(f"Datengrundlage: {ergebnis['datengrundlage']['records']} Records, "
                  f"{ergebnis['datengrundlage']['gold_zellen']} Gold-Zellen, "
                  f"Laeufe: {', '.join(ergebnis['datengrundlage']['laeufe'])}.")
    zeilen.append("")
    zeilen.append("## Laeufe")
    zeilen.append("")
    zeilen.append("| Lauf | Modell | Prompt | Cache-Anteil | leer | F1 | MAE | mae_coverage | Metriken identisch |")
    zeilen.append("|---|---|---|---|---|---|---|---|---|")
    for eintrag in lauf_uebersicht:
        m = eintrag["metriken"]
        zeilen.append(
            f"| {eintrag['run_id']} | {eintrag['model']} | `{eintrag['prompt_version']}` "
            f"| {eintrag['cache_anteil']} | {eintrag['leere_antworten']}/{eintrag['antworten']} "
            f"| {m['cell_f1']} | {m['mae_pairs']} | {m['mae_coverage']} "
            f"| {'ja' if eintrag['metriken_identisch'] else 'nein'} |"
        )
    zeilen.append("")
    zeilen.append("## Fehler je Prompt-Version")
    zeilen.append("")
    zeilen.append("Versionen werden getrennt ausgewiesen und nicht summiert: `verworfen`")
    zeilen.append("bedeutet, dass die Fassung im Dev-Lauf schlechter war als die Referenz.")
    zeilen.append("")
    zeilen.append("| Version | Status | Fehler | technisch | inhaltlich | zusätzliche Zellen | Läufe |")
    zeilen.append("|---|---|---|---|---|---|---|")
    for version, werte in versionen.items():
        zeilen.append(
            f"| `{version}` | {werte['status']} | {werte['fehler']} | {werte['technisch']} "
            f"| {werte['inhaltlich']} | {werte['zusaetzliche_zellen']} | {len(werte['laeufe'])} |"
        )
    zeilen.append("")
    for version, werte in versionen.items():
        zeilen.append(f"### {version} ({werte['status']})")
        zeilen.append("")
        zeilen.append("| Klasse | Anzahl |")
        zeilen.append("|---|---|")
        for name, count in sorted(werte["klassen"].items(), key=lambda item: -item[1]):
            zeilen.append(f"| {name} | {count} |")
        zeilen.append("")
        zeilen.append("| Feld | Klassen |")
        zeilen.append("|---|---|")
        for feld, zaehler in sorted(werte["nach_feld"].items()):
            verteilung = ", ".join(f"{name} ({count})" for name, count in sorted(zaehler.items(), key=lambda item: -item[1]))
            zeilen.append(f"| {feld} | {verteilung} |")
        zeilen.append("")
    zeilen.append("## Ereigniszahlen")
    zeilen.append("")
    zeilen.append("| Version | Lauf | Modell | Record | Feld | Arm | Gold | Vorhersage | Fehler | Klasse |")
    zeilen.append("|---|---|---|---|---|---|---|---|---|---|")
    for fall in ereignis_details:
        zeilen.append(
            f"| `{fall['prompt_version']}` | {fall['run_id']} | {fall['model']} | {fall['record_id']} | {fall['field']} | {fall['arm']} "
            f"| {fall['gold']} | {fall['prediction']} | {fall['abs_error']} | {fall['klasse']} |"
        )
    zeilen.append("")
    zeilen.append("## Gold-Pruefung")
    zeilen.append("")
    zeilen.append(f"{ergebnis['gold_pruefung']['mit_problem']} von {ergebnis['gold_pruefung']['zellen']} Gold-Zellen haben einen Pruefhinweis.")
    zeilen.append("")
    zeilen.append("| Record | Feld | Arm | Gold | Treffer im Text | Hinweis |")
    zeilen.append("|---|---|---|---|---|---|")
    for befund in gold_befunde:
        if not befund["braucht_pruefung"]:
            continue
        zeilen.append(
            f"| {befund['record_id']} | {befund['field']} | {befund['arm']} | {befund['gold']} "
            f"| {befund['treffer_im_text']} | {'; '.join(befund['probleme'])} |"
        )
    zeilen.append("")
    zeilen.append("## Pruefqueue")
    zeilen.append("")
    pruef = ergebnis["pruefqueue"]
    zeilen.append(f"Gesamt {pruef['eintraege']} Eintraege, getrennt nach Version:")
    zeilen.append("")
    zeilen.append("| Datei | Status | Versionen | Eintraege | Prioritaeten |")
    zeilen.append("|---|---|---|---|---|")
    referenz_versionen = [v for v in BESCHREIBUNG if status_von(v) == "referenz"]
    zeilen.append(
        f"| `{pruef['referenz']['datei']}` | referenz | "
        f"{', '.join(referenz_versionen) or '-'} | {pruef['referenz']['eintraege']} "
        f"| {pruef['referenz']['nach_prioritaet']} |"
    )
    zeilen.append(
        f"| `{pruef['verworfen']['datei']}` | verworfen | {', '.join(pruef['verworfen']['versionen']) or '-'} "
        f"| {pruef['verworfen']['eintraege']} | - |"
    )
    zeilen.append(
        f"| `{pruef['historisch']['datei']}` | historisch | {', '.join(pruef['historisch']['versionen']) or '-'} "
        f"| {pruef['historisch']['eintraege']} | - |"
    )
    zeilen.append("")
    zeilen.append("Nur die Referenzdatei ist zur Pruefung vorgesehen; die uebrigen")
    zeilen.append("liegen vollstaendig vor, damit nichts verloren geht.")
    zeilen.append("")
    (out_dir / "error_analysis.md").write_text("\n".join(zeilen), encoding="utf-8", newline="\n")

    print(f"geschrieben: {out_dir}")
    print(f"  Fehlerfaelle: {len(alle_faelle)}, zusaetzliche Zellen: {len(alle_zusatz)}")
    print(f"  Metriken identisch: {all(a['ableitung_identisch'] for a in abgleich)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
