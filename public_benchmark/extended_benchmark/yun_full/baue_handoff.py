#!/usr/bin/env python
"""Baut den vollstaendigen Uebergabeordner `handoff_20261116/` und die ZIP-Datei.

Der Export kopiert ausschliesslich vorhandene Artefakte, rendert die Prompts aus
dem echten Produktivcode und rechnet die zentralen Metriken aus den Rohdaten
erneut nach. Es werden keine Modellaufrufe gemacht und keine Ergebnisse
veraendert.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/yun_full/baue_handoff.py

Ergebnis:
    handoff_20261116/            (Ordner, im Projektwurzelverzeichnis)
    benchmark_handoff_20261116.zip
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parent.parent
ZIEL = REPO / "handoff_20261116"
ZIP = REPO / "benchmark_handoff_20261116.zip"

sys.path.insert(0, str(BENCH))

import run_extended_extraction as rx  # noqa: E402

KONFLIKTE = {
    "yun2024:524": "Fliesstext nennt 17.73 +- 0.46, Tabelle 17.73 +- 1.09",
    "yun2024:447": "Text nennt intervention n=114, Tabellenkopf n=104",
    "yun2024:669": "Modellwerte im Artikel nicht auffindbar, Gold passt zur Tabelle",
}
# Belegt geprueften Einzelfaelle: Fundstelle und Klassifikation stehen im Bericht.
FUNDSTELLEN = {
    "yun2024:359": ("PMC5971365", "Results, Absatz Descriptive data: 'n = 919' / 'n = 922'", "Population"),
    "yun2024:335": ("PMC5617873", "Abstract: 'placebo (n = 45) or aripiprazole (n = 47)'", "Armzuordnung"),
    "yun2024:110": ("PMC4319071", "Methods: 'basic ... n=456), plus ... n=459), and control ... n=434'", "Armzuordnung"),
    "yun2024:369": ("PMC1475568", "Tabelle Baseline: 'Hypertension, % 89 86'", "Einheit/Statistik"),
    "yun2024:246": ("PMC5571493", "Ergebnisabschnitt: '0.83 +- 0.05 ... g/l'", "Skalierung"),
    "yun2024:669": ("PMC4987981", "Tabelle Triglycerides (mg/dl), Spalten 181,8 / 194,3 / 200,1", "Tabellenzeile"),
    "yun2024:573": ("PMC5541727", "Tabelle: '6 months --1.4 (5.3)', '24 months --3.7 (3.4)'", "Zeitpunkt"),
    "yun2024:118": ("PMC4323894", "Methods: 'mild cooling consisted of 10 patients'", "Population"),
    "yun2024:524": ("PMC5325897", "Fliesstext gegen Tabelle (17.73 +- 0.46 vs 1.09)", "Goldfehler"),
    "yun2024:447": ("PMC4879328", "Tabelle vs. Text (n=104 vs n=114)", "Goldfehler"),
}
TEXTQUELLE = REPO / "public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/no_attributes_markdown_files"
SKRIPTE = [
    "run_extended_extraction.py",
    "run_stage_extraction.py",
    "stage_extraction.py",
    "evaluate_stage_extraction.py",
    "evaluate_extended.py",
    "analyze_errors.py",
    "yun_full/baue_yun699.py",
    "yun_full/baue_stichprobe.py",
    "yun_full/auswerte_yun699.py",
    "yun_full/yun_metriken.py",
    "yun_full/validator.py",
    "yun_full/vergleich_20261116.py",
    "yun_full/ausschluss_konflikte.py",
    "yun_full/ergebnisse_md.py",
    "yun_full/baue_handoff.py",
]
TESTS = ["public_benchmark/tests/test_yun699.py", "public_benchmark/tests/test_yun_metriken.py"]


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def kopiere(quelle: Path, ziel: Path) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(quelle, ziel)


def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def kennzahlen(run_dir: Path, recs: dict[str, dict]) -> dict:
    rows = lies(run_dir / "predictions.jsonl")
    richtig = falsch = fehlend = ohne_gold = 0
    for row in rows:
        gold = {c["field"]: c["value"] for c in recs[row["record_id"]]["gold"]["cells"]}
        pred: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            pred.setdefault(zelle["field"], zelle["value"])
        for feld, wert in gold.items():
            m = pred.get(feld)
            if m is None:
                fehlend += 1
            elif abs(m - wert) > 1e-9:
                falsch += 1
            else:
                richtig += 1
        ohne_gold += sum(1 for feld in pred if feld not in gold)
    p = richtig / (richtig + falsch) if richtig + falsch else None
    r = richtig / (richtig + falsch + fehlend) if richtig + falsch + fehlend else None
    klassen: dict[str, int] = {}
    for row in rows:
        k = row.get("fehlerklasse") or "ok"
        klassen[k] = klassen.get(k, 0) + 1
    return {
        "records": len(rows),
        "richtig": richtig,
        "falsch": falsch,
        "fehlend": fehlend,
        "ohne_gold": ohne_gold,
        "precision": round(p, 4) if p else None,
        "recall": round(r, 4) if r else None,
        "f1": round(2 * p * r / (p + r), 4) if p and r else None,
        "tokens_output": sum(row.get("completion_tokens") or 0 for row in rows),
        "elapsed_s": round(sum(row.get("elapsed_s") or 0 for row in rows)),
        "cached": sum(1 for row in rows if row.get("suspected_cache")),
        "klassen": klassen,
        "modelle": sorted({row.get("model_id") or "" for row in rows}),
    }


def main() -> int:
    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    (ZIEL / "daten").mkdir(parents=True)
    (ZIEL / "laeufe").mkdir()
    (ZIEL / "skripte").mkdir()
    (ZIEL / "konfiguration").mkdir()
    (ZIEL / "fehleranalyse").mkdir()
    (ZIEL / "protokolle").mkdir()

    # 1. Daten
    for name in ("records/yun699.jsonl", "manifest.json", "official_metrics.json", "stichprobe60.json", "stichprobe20.json", "texte_manifest.txt"):
        kopiere(HERE / name, ZIEL / "daten" / Path(name).name)
    kopiere(HERE / "vergleich_20261116.json", ZIEL / "daten" / "vergleich_20261116.json")
    kopiere(HERE / "ausschluss_konflikte_20261116.json", ZIEL / "daten" / "ausschluss_konflikte.json")
    recs = {r["record_id"]: r for r in lies(HERE / "records" / "yun699.jsonl")}

    # 1b. Volltexte der 120 Artikel (Quelle der Fundstellenpruefung, Apache-2.0)
    if TEXTQUELLE.exists():
        ziele = ZIEL / "daten" / "volltexte"
        ziele.mkdir()
        for text_datei in sorted(TEXTQUELLE.glob("*.md")):
            kopiere(text_datei, ziele / text_datei.name)

    # 2. Laeufe (alles, was Inhalt hat)
    lauf_zeilen = []
    for lauf in sorted((BENCH / "runs").iterdir()):
        if not lauf.is_dir() or not any(lauf.iterdir()):
            continue
        for datei in lauf.iterdir():
            if datei.is_file():
                kopiere(datei, ZIEL / "laeufe" / lauf.name / datei.name)
        if (lauf / "predictions.jsonl").exists():
            try:
                k = kennzahlen(lauf, recs)
            except (KeyError, json.JSONDecodeError) as exc:
                k = {"fehler_bei_auswertung": f"{type(exc).__name__}: {exc}"}
            lauf_zeilen.append({"run": lauf.name, "stand": datetime.fromtimestamp((lauf / "predictions.jsonl").stat().st_mtime).strftime("%Y-%m-%d %H:%M"), **k})
    (ZIEL / "daten" / "laufkennzahlen.json").write_text(
        json.dumps({"hinweis": "Neu berechnet aus predictions.jsonl; Zeitstempel aus Dateizeit, nicht aus einem Laufprotokoll", "laeufe": lauf_zeilen}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 3. Skripte und Tests
    for name in SKRIPTE:
        kopiere(BENCH / name, ZIEL / "skripte" / Path(name).name)
    for name in TESTS:
        kopiere(REPO / name, ZIEL / "skripte" / "tests" / Path(name).name)

    # 4. Prompts aus dem echten Code rendern
    ref = recs["yun2024:107"]
    text = (REPO / ref["document"]["path"]).read_text(encoding="utf-8", errors="replace")
    target = str(((ref.get("timepoint") or {}).get("target")) or "week 24").strip()
    varianten = {
        "prompt_v7_zellzeitpunkt.txt": dict(cell_timepoint=True, target_timepoint=target, group_size_mode="aus"),
        "prompt_v8_quellenzeile.txt": dict(cell_timepoint=True, target_timepoint=target, group_size_mode="aus", quellenzeile=True),
        "prompt_v7_gruppengroesse_kurz.txt": dict(cell_timepoint=True, target_timepoint=target, group_size_mode="kurz"),
        "prompt_standard_ohne_zellzeitpunkt.txt": dict(),
        "prompt_repair.txt": None,
    }
    for name, kwargs in varianten.items():
        if kwargs is None:
            inhalt = rx._prompt_repair(ref, text, target)
        else:
            inhalt = rx.build_prompt(ref, text, **kwargs)
        (ZIEL / "konfiguration" / name).write_text(inhalt + "\n", encoding="utf-8")
    (ZIEL / "konfiguration" / "systemprompt.txt").write_text(rx.SYSTEM + "\n", encoding="utf-8")

    modelle = {k: {"id": v.get("id"), "max_tokens": v.get("max_tokens")} for k, v in rx.MODELS.items()}
    (ZIEL / "konfiguration" / "modelle_und_parameter.json").write_text(
        json.dumps(
            {
                "hinweis": "IDs und Default-Limits aus run_extended_extraction.py; der API-Schluessel wird aus der lokalen Konfiguration gelesen und ist NICHT Teil dieser Uebergabe",
                "modelle": modelle,
                "temperatur": 0.0,
                "prompt_versionen": {
                    "v7_zellzeitpunkt": "ein Zeitpunkt je Antwort, timepoint_header, fallback",
                    "v8_quellenzeile": "v7 plus erzwungene Quellenangabe (Experiment C, gescheitert)",
                },
                "retry": {"json_kaputt": "ein Wiederholungsaufruf mit gleichem Limit", "length": "kein Retry, optional Reparaturaufruf mit REPAIR_MAX_TOKENS"},
                "REPAIR_MAX_TOKENS": rx.REPAIR_MAX_TOKENS,
                "SESSION_TAG": "Cache-Buster, setzt einen zufaelligen Tag in den Systemprompt",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # 5. Falsche Zellen als CSV (Reference 60 und alle 20er-Laeufe)
    zeilen = []
    for lauf in sorted((BENCH / "runs").iterdir()):
        pfad = lauf / "predictions.jsonl"
        if not pfad.exists() or not lauf.name.startswith(("yun699_test60", "yun20_")):
            continue
        for row in lies(pfad):
            rec = recs[row["record_id"]]
            gold = {c["field"]: c["value"] for c in rec["gold"]["cells"]}
            pred: dict[str, float] = {}
            for zelle in row.get("rows") or []:
                pred.setdefault(zelle["field"], zelle["value"])
            for feld, wert in gold.items():
                m = pred.get(feld)
                if m is None or abs(m - wert) < 1e-9:
                    continue
                pmc, stelle, klasse = FUNDSTELLEN.get(row["record_id"], ("", "", ""))
                zeilen.append(
                    {
                        "run": lauf.name,
                        "record_id": row["record_id"],
                        "pmc": rec["document"]["id"],
                        "outcome": rec["context"]["outcome"],
                        "feld": feld,
                        "gold": wert,
                        "modell": m,
                        "fundstelle": stelle,
                        "fehlerklasse": klasse,
                        "gold_konflikt": KONFLIKTE.get(row["record_id"], ""),
                    }
                )
    with (ZIEL / "fehleranalyse" / "falsche_zellen.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(zeilen[0].keys()))
        writer.writeheader()
        writer.writerows(zeilen)

    # 6. Laufprotokolle als Markdown
    protokoll = ["# Laufprotokolle\n", "Start- und Endzeit wurden im Harness nicht je Lauf protokolliert; angegeben ist der\nDateizeitstempel von `predictions.jsonl` und die Summe der je Anfrage gemessenen\n`elapsed_s`. Kosten sind nicht verfuegbar (kein Preisaushang fuer den Endpunkt).\n\n"]
    protokoll.append("| Lauf | Records | ok | Ausfaelle | Klassen | Output-Tokens | Summe Zeit | Cache | Modelle | Stand |\n|---|---:|---:|---:|---|---:|---:|---:|---|---|\n")
    for eintrag in lauf_zeilen:
        k = eintrag.get("klassen", {})
        ausfaelle = sum(v for key, v in k.items() if key != "ok")
        klassen = ", ".join(f"{key}={v}" for key, v in sorted(k.items()) if key != "ok") or "-"
        protokoll.append(
            f"| {eintrag['run']} | {eintrag.get('records', '')} | {k.get('ok', '')} | {ausfaelle} | {klassen} | "
            f"{eintrag.get('tokens_output', '')} | {eintrag.get('elapsed_s', '')} s | {eintrag.get('cached', '')} | "
            f"{', '.join(eintrag.get('modelle', []))} | {eintrag['stand']} |\n"
        )
    (ZIEL / "protokolle" / "laufprotokolle.md").write_text("".join(protokoll), encoding="utf-8")

    # 7. Dokumentation
    kopiere(REPO / "benchmark_research_report_20261116.md", ZIEL / "benchmark_report.md")
    kopiere(HERE / "ergebnisse_20261116.md", ZIEL / "ergebnisse.md")
    kopiere(HERE / "README.md", ZIEL / "daten" / "README_yun_full.md")
    for name in ("README.md", "methodik.md", "offene_probleme.md"):
        kopiere(HERE / "handoff_doku" / name, ZIEL / name)

    # 8. Manifest und Pruefung
    dateien = sorted(p for p in ZIEL.rglob("*") if p.is_file())
    for p in dateien:
        if p.suffix == ".json":
            json.loads(p.read_text(encoding="utf-8"))
    manifest = [f"{sha256(p)}  {p.relative_to(ZIEL).as_posix()}" for p in dateien]
    (ZIEL / "MANIFEST_SHA256.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    anhang = ["# Anhang: vollstaendige Dateiliste\n\n", f"Stand: {datetime.now().strftime('%Y-%m-%d %H:%M')}, {len(dateien) + 2} Dateien.\n\n"]
    anhang.append("| Datei | Groesse |\n|---|---:|\n")
    for p in dateien:
        anhang.append(f"| `{p.relative_to(ZIEL).as_posix()}` | {p.stat().st_size:,} B |\n".replace(",", " "))
    (ZIEL / "ANHANG_DATEILISTE.md").write_text("".join(anhang), encoding="utf-8")
    dateien.append(ZIEL / "ANHANG_DATEILISTE.md")
    manifest = [f"{sha256(p)}  {p.relative_to(ZIEL).as_posix()}" for p in sorted(dateien)]
    (ZIEL / "MANIFEST_SHA256.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    dateien.append(ZIEL / "MANIFEST_SHA256.txt")

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archiv:
        for p in sorted(ZIEL.rglob("*")):
            if p.is_file():
                archiv.write(p, Path("handoff_20261116") / p.relative_to(ZIEL))

    # 9. Konsistenzpruefung: zentrale Metriken aus den Rohdaten nachrechnen
    geprueft, abweichungen = 0, []
    vergleich_pfad = HERE / "vergleich_20261116.json"
    if vergleich_pfad.exists():
        for eintrag in json.loads(vergleich_pfad.read_text(encoding="utf-8"))["laeufe"]:
            lauf = BENCH / "runs" / eintrag["run"]
            if not (lauf / "predictions.jsonl").exists():
                abweichungen.append(f"{eintrag['run']}: predictions.jsonl fehlt")
                continue
            neu = kennzahlen(lauf, recs)
            geprueft += 1
            for feld in ("richtig", "falsch", "fehlend", "precision", "recall", "f1"):
                if eintrag.get(feld) != neu.get(feld):
                    abweichungen.append(f"{eintrag['run']}.{feld}: Datei {eintrag.get(feld)} != neu {neu.get(feld)}")
    (ZIEL / "pruefung.md").write_text(
        "# Qualitaetskontrolle der Uebergabe\n\n"
        f"- JSON-Dateien geparst: alle {sum(1 for p in dateien if p.suffix == '.json')}, ohne Fehler.\n"
        f"- Laeufe mit Rohdaten: {len(lauf_zeilen)}; Kennzahlen neu berechnet: {geprueft}.\n"
        f"- Abweichungen zu `daten/vergleich_20261116.json`: {len(abweichungen)}\n"
        + ("".join(f"  - {a}\n" for a in abweichungen) if abweichungen else "  - keine\n")
        + "- Volltexte enthalten: "
        + str(len(list((ZIEL / 'daten' / 'volltexte').glob('*.md'))) if (ZIEL / 'daten' / 'volltexte').exists() else 0)
        + " von 120\n"
        "- Nicht enthalten: API-Schluessel, Geldkosten, Start-/Endzeit je Lauf (Begruendung in README.md).\n",
        encoding="utf-8",
    )
    print(f"Konsistenz: {geprueft} Laeufe nachgerechnet, {len(abweichungen)} Abweichungen")
    for a in abweichungen:
        print("  ABWEICHUNG:", a)

    print(f"Dateien im Handoff: {len(dateien) + 1}")
    print(f"ZIP: {ZIP} ({ZIP.stat().st_size / 1e6:.2f} MB)")
    print(f"falsche Zellen in CSV: {len(zeilen)}")
    print(f"Laeufe mit predictions.jsonl: {len(lauf_zeilen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
