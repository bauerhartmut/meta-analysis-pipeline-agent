#!/usr/bin/env python
"""Baut aus dem Yun-2024-Datensatz eine Record-Datei fuer den Extraktions-Harness.

Quelle ist ausschliesslich `evaluation/data/annotated_rct_dataset.json` aus dem
Repository `hyesunyun/llm-meta-analysis` (Commit 1bc768d, Apache-2.0). Die Datei
wird nicht veraendert; dieser Adapter liest sie nur und schreibt eine neue
Record-Datei im Schema des Harness (`records/yun699.jsonl`).

Kein Goldwert wird umgerechnet, gerundet oder ergaenzt: Jede Zelle traegt ihren
Originalstring in `raw`. Werte, die sich nicht als Zahl lesen lassen, werden
nicht erfunden, sondern im Manifest als Anomalie gemeldet.

Das Original hat kein Zeitpunktfeld. Der Zielzeitpunkt ist deshalb eine Regel
(Yun: primaerer Zeitpunkt, sonst der zuletzt berichtete) und kein Datum; er steht
als Regeltext im Record und ist in der Auswertung nicht bewertbar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = HERE.parents[2]

QUELLE = REPO / "public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/annotated_rct_dataset.json"
TEXTE = REPO / "public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/no_attributes_markdown_files"
AUSGABE = HERE / "records" / "yun699.jsonl"
MANIFEST = HERE / "manifest.json"

# Hash der Quelle, gegen den gebaut wird (SHA-256 der heruntergeladenen Datei).
QUELLE_SHA256 = "d8f666fdd70a2e7f4ed9d4334cda8f949c85f9c4ef45c3c66e69ba555a4d7e9a"

# Ein Feldname des Originals -> Feldname des Harness.
FELDER = {
    "intervention_group_size": "intervention_group_size",
    "intervention_events": "intervention_events",
    "intervention_mean": "intervention_mean",
    "intervention_standard_deviation": "intervention_standard_deviation",
    "comparator_group_size": "comparator_group_size",
    "comparator_events": "comparator_events",
    "comparator_mean": "comparator_mean",
    "comparator_standard_deviation": "comparator_standard_deviation",
}

# Zeitpunktregel des Papers, woertlich als Vorgabe fuer v7. Kein Datum, weil der
# Datensatz keines enthaelt.
ZEITPUNKT_REGEL = "primary time point of the trial (if not stated: the last reported time point)"


def quelle_hash() -> str:
    return hashlib.sha256(QUELLE.read_bytes()).hexdigest()


TAUSENDER = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")


def zahl(text: str) -> tuple[float | None, bool]:
    """Liest einen Originalwert; zweiter Wert sagt, ob normalisiert wurde.

    Einzige Normalisierung: Tausendertrenner-Kommas nach Muster `1,919` oder
    `6,032.37`. Sie wird im Record als `normalisiert: true` markiert und der
    Originalstring bleibt in `raw` erhalten; ohne dieses Muster wird nichts
    geraten.
    """
    roh = str(text).strip()
    if not roh:
        return None, False
    versuch = roh.replace(" ", "")
    if TAUSENDER.match(versuch):
        return float(versuch.replace(",", "")), True
    try:
        return float(versuch), False
    except ValueError:
        return None, False


def repo_stand() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(QUELLE.parents[2]), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - nur Metadatum, kein Abbruchgrund
        return "unbekannt"


def baue(records: list[dict]) -> tuple[list[dict], list[str], Counter]:
    ziel: list[dict] = []
    anomalien: list[str] = []
    zaehler: Counter = Counter()
    for roh in records:
        pmcid = str(roh["pmcid"])
        pfad = TEXTE / f"PMC{pmcid}.md"
        zellen: list[dict] = []
        for original, name in FELDER.items():
            text = roh.get(original)
            wert, normalisiert = zahl(text) if text not in (None, "") else (None, False)
            if text not in (None, "") and wert is None:
                anomalien.append(f"yun2024:{roh['id']}:{original} nicht numerisch: {text!r}")
                continue
            if wert is None:
                continue
            if normalisiert:
                zaehler["normalisiert"] += 1
                anomalien.append(
                    f"yun2024:{roh['id']}:{original} Tausendertrenner {text!r} -> {wert:g}"
                )
            zelle = {
                "field": name,
                "arm": "intervention" if name.startswith("intervention") else "comparator",
                "value": wert,
                "raw": str(text),
                "timepoint": None,
                "source": original,
            }
            if normalisiert:
                zelle["normalisiert"] = True
            zellen.append(zelle)
        zaehler["zellen"] += len(zellen)
        if not zellen:
            zaehler["ohne_zelle"] += 1
        zaehler[f"split:{str(roh['split']).lower()}"] += 1
        ziel.append(
            {
                "record_id": f"yun2024:{roh['id']}",
                "dataset": "yun2024",
                "task": "numeric_extraction",
                "document": {
                    "id": f"PMC{pmcid}",
                    "kind": "abstract_results_markdown",
                    "path": str(pfad.relative_to(REPO)).replace("\\", "/"),
                    "split": str(roh["split"]).lower(),
                    "text_chars": pfad.stat().st_size if pfad.exists() else 0,
                },
                "context": {
                    "intervention": roh["intervention"],
                    "comparator": roh["comparator"],
                    "outcome": roh["outcome"],
                    "outcome_type": roh["outcome_type"],
                },
                "gold": {"cells": zellen, "label": None, "spans": []},
                "provenance": {
                    "source_file": "public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/annotated_rct_dataset.json",
                    "source_id": str(roh["id"]),
                    "dataset_version": "1bc768d4d098c727c9866eeff909297c38a3e84c",
                    "evidence_inference_prompt_id": roh.get("evidence_inference_prompt_id"),
                    "is_data_complete": roh.get("is_data_complete"),
                },
                "issues": [roh["notes"]] if roh.get("notes") else [],
                "timepoint": {
                    "target": ZEITPUNKT_REGEL,
                    "status": "Regel (Yun kennt kein Zeitpunktfeld)",
                    "evidence": "Paper: primaerer Zeitpunkt des RCT, sonst der zuletzt berichtete",
                    "quelle": "regel",
                    "unsicher": False,
                },
            }
        )
    return ziel, anomalien, zaehler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    digest = quelle_hash()
    if digest != QUELLE_SHA256:
        print(f"FEHLER: Quellhash {digest} weicht von {QUELLE_SHA256} ab, Abbruch")
        return 2
    records = json.loads(QUELLE.read_text(encoding="utf-8"))
    if len(records) != 699:
        print(f"FEHLER: {len(records)} Records statt 699, Abbruch")
        return 2

    ziel, anomalien, zaehler = baue(records)
    fehlende_texte = [r["record_id"] for r in ziel if not (REPO / r["document"]["path"]).exists()]
    inhalt = "\n".join(json.dumps(r, ensure_ascii=False) for r in ziel) + "\n"
    print(f"{len(ziel)} Records, {zaehler['zellen']} Goldzellen, {zaehler['ohne_zelle']} ohne Zelle")
    print("Splits:", {k: v for k, v in zaehler.items() if k.startswith("split:")})
    print("Anomalien:", anomalien or "keine")
    print("Records ohne Text:", fehlende_texte or "keine")
    print("SHA-256 (Vorschau):", hashlib.sha256(inhalt.encode("utf-8")).hexdigest())

    if args.write:
        AUSGABE.parent.mkdir(parents=True, exist_ok=True)
        AUSGABE.write_text(inhalt, encoding="utf-8")
        manifest = {
            "quelle": {
                "repository": "https://github.com/hyesunyun/llm-meta-analysis",
                "commit": repo_stand(),
                "datei": str(QUELLE.relative_to(REPO)).replace("\\", "/"),
                "sha256": digest,
                "bytes": QUELLE.stat().st_size,
                "lizenz": "Apache License 2.0 (LICENSE im Repository)",
            },
            "texte": {
                "verzeichnis": str(TEXTE.relative_to(REPO)).replace("\\", "/"),
                "dateien": len(list(TEXTE.glob("*.md"))),
                "fehlend": fehlende_texte,
            },
            "records": {
                "gesamt": len(ziel),
                "dev": sum(1 for r in ziel if r["document"]["split"] == "dev"),
                "test": sum(1 for r in ziel if r["document"]["split"] == "test"),
                "artikel_gesamt": len({r["document"]["id"] for r in ziel}),
                "artikel_dev": len({r["document"]["id"] for r in ziel if r["document"]["split"] == "dev"}),
                "artikel_test": len({r["document"]["id"] for r in ziel if r["document"]["split"] == "test"}),
                "goldzellen": zaehler["zellen"],
                "goldzellen_dev": sum(len(r["gold"]["cells"]) for r in ziel if r["document"]["split"] == "dev"),
                "goldzellen_test": sum(len(r["gold"]["cells"]) for r in ziel if r["document"]["split"] == "test"),
                "ohne_zelle": zaehler["ohne_zelle"],
            },
            "schema_mapping": {
                "pmcid": "document.id (mit PMC-Praefix) + provenance.source_id",
                "intervention": "context.intervention",
                "comparator": "context.comparator",
                "outcome": "context.outcome",
                "outcome_type": "context.outcome_type",
                "intervention_mean": "gold.cells[field=intervention_mean].value",
                "intervention_sd": "gold.cells[field=intervention_standard_deviation].value",
                "intervention_n": "gold.cells[field=intervention_group_size].value",
                "comparator_mean": "gold.cells[field=comparator_mean].value",
                "comparator_sd": "gold.cells[field=comparator_standard_deviation].value",
                "comparator_n": "gold.cells[field=comparator_group_size].value",
                "intervention_events": "gold.cells[field=intervention_events].value",
                "comparator_events": "gold.cells[field=comparator_events].value",
                "timepoint": "nicht vorhanden; timepoint.target traegt die Regel des Papers",
                "split": "document.split (DEV -> dev, TEST -> test)",
                "notes": "issues[0] + provenance",
            },
            "anomalien": anomalien,
            "feld_typ_abweichungen": [
                f"{r['record_id']}:{c['field']} bei outcome_type={r['context']['outcome_type']}"
                for r in ziel
                for c in r["gold"]["cells"]
                if (
                    (r["context"]["outcome_type"] == "continuous" and c["field"].endswith("events"))
                    or (
                        r["context"]["outcome_type"] == "binary"
                        and ("mean" in c["field"] or "standard_deviation" in c["field"])
                    )
                )
            ],
            "ausgabe": {
                "datei": str(AUSGABE.relative_to(REPO)).replace("\\", "/"),
                "sha256": hashlib.sha256(AUSGABE.read_bytes()).hexdigest(),
                "bytes": AUSGABE.stat().st_size,
            },
        }
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"geschrieben: {AUSGABE}")
        print(f"geschrieben: {MANIFEST}")
        print("SHA-256:", manifest["ausgabe"]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
