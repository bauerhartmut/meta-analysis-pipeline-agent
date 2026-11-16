#!/usr/bin/env python
"""Packt die Rohdaten fuer eine externe Analyse in ein ZIP mit MANIFEST.md.

Enthalten sind Gesamtbericht, Goldstandard, Auswertungs-JSONs, die drei
Auswertungsskripte und die predictions.jsonl samt validator.json der neun
Vergleichslaeufe (inklusive Experiment B, `yun20_4000_glm_gskcb_20261116`).

Es werden keine Dateien veraendert, keine Platzhalter erzeugt und keine
Modellaufrufe gemacht.

Sicherheit: Ein vorhandener Zielordner wird **nicht** stillschweigend geloescht.
Ohne `--neu` bricht das Skript ab; mit `--neu` wird der Ordner neu aufgebaut.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/yun_full/baue_analyse_handoff.py [--neu]

Exit-Code 0 nur, wenn alle Pruefungen bestehen und keine Datei fehlt.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
REPO = BENCH.parent.parent
ZIEL = REPO / "benchmark_analysis_handoff_20261116"
ZIP = REPO / "benchmark_analysis_handoff_20261116.zip"
GOLD = "public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl"
VERGLEICH = "public_benchmark/extended_benchmark/yun_full/vergleich_20261116.json"

# quelle, ziel, zweck, erwartete_zeilen (None = keine Vorgabe)
DATEIEN = [
    ("public_benchmark/extended_benchmark/yun_full/ergebnisse_komplett_20261116.md",
     "bericht/ergebnisse_komplett_20261116.md", "Gesamtbericht, aus den Messdaten erzeugt", None),
    (GOLD, "goldstandard/yun699.jsonl", "Goldstandard: 699 Records mit Goldzellen, Kontext und PMC-ID", 699),
    (VERGLEICH, "auswertung/vergleich_20261116.json", "Kennzahlen aller neun Vergleichslaeufe", None),
    ("public_benchmark/extended_benchmark/yun_full/ausschluss_konflikte_20261116.json",
     "auswertung/ausschluss_konflikte_20261116.json", "Kennzahlen mit und ohne bestreitbare Goldannotationen", None),
    ("public_benchmark/extended_benchmark/yun_full/ergebnisse_komplett_md.py",
     "skripte/ergebnisse_komplett_md.py", "erzeugt den Gesamtbericht aus den Messdaten", None),
    ("public_benchmark/extended_benchmark/yun_full/vergleich_20261116.py",
     "skripte/vergleich_20261116.py", "berechnet die Vergleichstabelle aus predictions.jsonl", None),
    ("public_benchmark/extended_benchmark/yun_full/ausschluss_konflikte.py",
     "skripte/ausschluss_konflikte.py", "berechnet die Auswertung ohne konfliktaere Records", None),
    ("public_benchmark/extended_benchmark/runs/yun699_test60_20261116/predictions.jsonl",
     "laeufe/yun699_test60_20261116/predictions.jsonl", "Referenzlauf 60 Records, 4000 Tokens, GLM-5.3", 60),
    ("public_benchmark/extended_benchmark/runs/yun699_test60_20261116/validator.json",
     "laeufe/yun699_test60_20261116/validator.json", "Validatormessung auf dem Referenzlauf", None),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_glm_20261116/predictions.jsonl",
     "laeufe/yun20_4000_glm_20261116/predictions.jsonl", "GLM-5.3, 20 Records, 4000 Tokens", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_qwen_20261116/predictions.jsonl",
     "laeufe/yun20_4000_qwen_20261116/predictions.jsonl", "Qwen3.5-397B, 20 Records, 4000 Tokens", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_qwen30_20261116/predictions.jsonl",
     "laeufe/yun20_4000_qwen30_20261116/predictions.jsonl", "Qwen3-30B, 20 Records, 4000 Tokens", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_glm_gskcb_20261116/predictions.jsonl",
     "laeufe/yun20_4000_glm_gskcb_20261116/predictions.jsonl",
     "Experiment B: GLM-5.3 mit Gruppengroessenregel, 20 Records, 4000 Tokens, frisch generiert", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_glm_cb_20261116/predictions.jsonl",
     "laeufe/yun20_8000_glm_cb_20261116/predictions.jsonl", "GLM-5.3, 20 Records, 8000 Tokens, frisch generiert", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_qwen_cb_20261116/predictions.jsonl",
     "laeufe/yun20_8000_qwen_cb_20261116/predictions.jsonl", "Qwen3.5-397B, 20 Records, 8000 Tokens, frisch generiert", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_qwen30_cb_20261116/predictions.jsonl",
     "laeufe/yun20_8000_qwen30_cb_20261116/predictions.jsonl", "Qwen3-30B, 20 Records, 8000 Tokens, frisch generiert", 20),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_glm_v8_20261116/predictions.jsonl",
     "laeufe/yun20_8000_glm_v8_20261116/predictions.jsonl",
     "Experiment C: GLM-5.3 mit Quellenzeile (v8), 20 Records, 8000 Tokens", 20),
]


def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def zeilen(pfad: Path) -> int:
    return sum(1 for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip())


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def kennzahlen(rows: list[dict], gold: dict[str, set[str]]) -> dict:
    """Precision/Recall/F1 aus Rohdaten, identisch zu auswerte_yun699.py."""
    richtig = falsch = fehlend = 0
    for row in rows:
        g = gold[row["record_id"]]
        pred: dict[str, float] = {}
        for zelle in row.get("rows") or []:
            pred.setdefault(zelle["field"], zelle["value"])
        for feld in g["felder"]:
            m = pred.get(feld)
            if m is None:
                fehlend += 1
            elif abs(m - g["werte"][feld]) > 1e-9:
                falsch += 1
            else:
                richtig += 1
    p = richtig / (richtig + falsch) if richtig + falsch else None
    r = richtig / (richtig + falsch + fehlend) if richtig + falsch + fehlend else None
    return {
        "richtig": richtig,
        "falsch": falsch,
        "fehlend": fehlend,
        "precision": round(p, 4) if p else None,
        "recall": round(r, 4) if r else None,
        "f1": round(2 * p * r / (p + r), 4) if p and r else None,
    }


def pruefe(pfad: Path) -> str:
    """Syntaktische Pruefung; liefert Hinweistext oder wirft."""
    if pfad.suffix == ".json":
        json.loads(pfad.read_text(encoding="utf-8"))
        return "JSON valide"
    if pfad.suffix == ".jsonl":
        for zeile in pfad.read_text(encoding="utf-8").splitlines():
            if zeile.strip():
                json.loads(zeile)
        return f"JSONL valide, {zeilen(pfad)} Zeilen"
    if pfad.suffix == ".py":
        compile(pfad.read_text(encoding="utf-8"), str(pfad), "exec")
        return "Python syntaktisch valide"
    return "Textdatei"


def main() -> int:
    neu = "--neu" in sys.argv[1:]
    if ZIEL.exists():
        if not neu:
            print(f"ABBRUCH: {ZIEL} existiert bereits. Nichts wurde veraendert.")
            print("Mit --neu wird der Ordner neu aufgebaut (vorhandene Ergebnisse werden dann ersetzt).")
            return 2
        shutil.rmtree(ZIEL)
    ZIEL.mkdir(parents=True)

    fehler: list[str] = []
    fehlend: list[str] = []
    kopiert: list[dict] = []

    gold: dict[str, dict] = {}
    for eintrag in lies_jsonl(REPO / GOLD):
        gold[eintrag["record_id"]] = {
            "felder": {c["field"] for c in eintrag["gold"]["cells"]},
            "werte": {c["field"]: c["value"] for c in eintrag["gold"]["cells"]},
        }
    if len(gold) != 699:
        fehler.append(f"Goldstandard: {len(gold)} eindeutige record_ids, erwartet 699")

    erwartete_kennzahlen = {}
    if (REPO / VERGLEICH).exists():
        for eintrag in json.loads((REPO / VERGLEICH).read_text(encoding="utf-8"))["laeufe"]:
            erwartete_kennzahlen[eintrag["run"]] = eintrag

    for quelle_rel, ziel_rel, zweck, erwartet in DATEIEN:
        quelle = REPO / quelle_rel
        if not quelle.exists():
            fehlend.append(quelle_rel)
            continue
        ziel = ZIEL / ziel_rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ziel)

        try:
            hinweis = pruefe(ziel)
        except Exception as exc:  # noqa: BLE001 - Sammelpruefung
            hinweis = "FEHLER"
            fehler.append(f"{ziel_rel}: {type(exc).__name__}: {exc}")

        if ziel.suffix == ".jsonl":
            rows = lies_jsonl(ziel)
            ids = [r["record_id"] for r in rows]
            if erwartet is not None and len(rows) != erwartet:
                fehler.append(f"{ziel_rel}: {len(rows)} Records, erwartet {erwartet}")
            doppelt = {i for i in ids if ids.count(i) > 1}
            if doppelt:
                fehler.append(f"{ziel_rel}: doppelte record_ids {sorted(doppelt)}")
            unbekannt = [i for i in ids if i not in gold]
            if unbekannt:
                fehler.append(f"{ziel_rel}: {len(unbekannt)} record_ids nicht im Goldstandard, z. B. {unbekannt[:3]}")
            run = ziel.stem if ziel.stem != "yun699" else ""
            run = Path(ziel_rel).parent.name
            if run in erwartete_kennzahlen and not unbekannt:
                neu_k = kennzahlen(rows, gold)
                alt_k = erwartete_kennzahlen[run]
                for feld in ("richtig", "falsch", "fehlend", "precision", "recall", "f1"):
                    if neu_k[feld] != alt_k.get(feld):
                        fehler.append(f"{ziel_rel}: {feld} neu {neu_k[feld]} != vergleich {alt_k.get(feld)}")
                hinweis += f"; Kennzahlen nachgerechnet (P {neu_k['precision']}, R {neu_k['recall']}, F1 {neu_k['f1']})"

        kopiert.append(
            {
                "quelle": quelle_rel,
                "ziel": ziel_rel,
                "bytes": ziel.stat().st_size,
                "sha256": sha256(ziel),
                "zweck": zweck,
                "pruefung": hinweis,
                "zeilen": zeilen(ziel) if ziel.suffix in (".jsonl", ".md", ".py") else None,
            }
        )

    # Bericht gegen Messdaten: alle Laeufe mit P, R und F1
    bericht = ZIEL / "bericht" / "ergebnisse_komplett_20261116.md"
    bericht_pruefung: list[tuple[str, str, bool]] = []
    if bericht.exists():
        text = bericht.read_text(encoding="utf-8")
        for run, eintrag in sorted(erwartete_kennzahlen.items()):
            fehlend_im_text = []
            for feld in ("precision", "recall", "f1"):
                wert = eintrag.get(feld)
                if wert is None:
                    continue
                darstellung = f"{wert:.4f}".replace(".", ",")
                if darstellung not in text:
                    fehlend_im_text.append(f"{feld}={darstellung}")
            bericht_pruefung.append((run, ", ".join(fehlend_im_text) or "alle Werte gefunden", not fehlend_im_text))
            if fehlend_im_text:
                fehler.append(f"Bericht: Kennzahlen fuer {run} nicht gefunden ({', '.join(fehlend_im_text)})")
    else:
        fehler.append("Bericht fehlt, Kennzahlenpruefung nicht moeglich")

    # Manifest
    enthalten = {Path(e["ziel"]).parent.name for e in kopiert if e["ziel"].startswith("laeufe/")}
    vergleichslaeufe = sorted(erwartete_kennzahlen)
    nicht_enthalten = [r for r in vergleichslaeufe if r not in enthalten]
    weitere = sorted(
        p.parent.name
        for p in (BENCH / "runs").glob("*/predictions.jsonl")
        if p.parent.name not in vergleichslaeufe
    )

    md = [
        "# MANIFEST: Rohdaten fuer die externe Analyse\n\n",
        "**Erzeugt:** 16.11.2026  \n",
        "**Zweck:** unabhaengige Nachrechnung aller Metriken und Fehleranalyse auf Zellebene  \n",
        f"**Dateien im Archiv:** {len(kopiert)} von {len(DATEIEN)} angeforderten, dazu diese MANIFEST.md  \n",
        f"**Fehlende Dateien:** {', '.join(fehlend) if fehlend else 'keine'}  \n",
        f"**Validierungsfehler:** {len(fehler)}\n\n",
        "## Hinweis zu den Pfaden\n\n",
        "Die Laeufe liegen im Projekt unter `public_benchmark/extended_benchmark/runs/`,\n"
        "nicht unter `public_benchmark/runs/`. Die Quellpfade unten sind die tatsaechlichen\nProjektpfade.\n\n",
        "## Dateien\n\n",
        "| # | Projektpfad (Quelle) | Pfad im Archiv | Groesse | Zeilen | Zweck | Pruefung |\n",
        "|---:|---|---|---:|---:|---|---|\n",
    ]
    for i, eintrag in enumerate(kopiert, 1):
        groesse = f"{eintrag['bytes']:,} B".replace(",", " ")
        md.append(
            f"| {i} | `{eintrag['quelle']}` | `{eintrag['ziel']}` | {groesse} | "
            f"{eintrag['zeilen'] if eintrag['zeilen'] is not None else '-'} | {eintrag['zweck']} | {eintrag['pruefung']} |\n"
        )

    md.append("\n## Vergleichslaeufe: enthalten und nicht enthalten\n\n")
    md.append("Grundgesamtheit ist `vergleich_20261116.json` (neun Laeufe, die im Gesamtbericht ausgewertet werden).\n\n")
    md.append("| Vergleichslauf | im Archiv |\n|---|---|\n")
    for run in vergleichslaeufe:
        md.append(f"| `{run}` | {'ja' if run in enthalten else '**nein**'} |\n")
    if nicht_enthalten:
        md.append("\n**Fehlende Vergleichslaeufe:** " + ", ".join(f"`{r}`" for r in nicht_enthalten) + "\n")
    else:
        md.append("\n**Fehlende Vergleichslaeufe:** keine, alle neun sind enthalten.\n")

    md.append("\n### Weitere Laeufe im Projekt, bewusst nicht im Archiv\n\n")
    if weitere:
        md.append("Diese Laeufe sind weder Teil von `vergleich_20261116.json` noch des Gesamtberichts:\n\n")
        for run in weitere:
            md.append(f"- `{run}`\n")
    else:
        md.append("- keine\n")

    md.append("\n## Pruefungen im Detail\n\n")
    md.append("1. Jede Datei syntaktisch geparst (JSON, JSONL zeilenweise, Python via `compile`).\n")
    md.append("2. Erwartete Record-Anzahl je Lauf (60 fuer den Referenzlauf, 20 fuer alle 20er-Laeufe) geprueft.\n")
    md.append("3. Eindeutigkeit der `record_id` je Lauf geprueft.\n")
    md.append("4. Jede `record_id` gegen den Goldstandard aufgeloest.\n")
    md.append("5. Precision, Recall und F1 je Lauf aus den Rohdaten neu berechnet und mit `vergleich_20261116.json` verglichen (exakt, keine Toleranz).\n")
    md.append("6. Im Gesamtbericht wurden fuer **alle neun** Laeufe Precision, Recall und F1 gesucht.\n\n")
    md.append("### Ergebnis\n\n")
    if fehler:
        md.append(f"**{len(fehler)} Fehler:**\n\n")
        for eintrag in fehler:
            md.append(f"- {eintrag}\n")
    else:
        md.append("Alle Pruefungen bestanden, keine Abweichung.\n")

    md.append("\n### Bericht gegen Messdaten\n\n")
    for run, status, _ in bericht_pruefung:
        md.append(f"- `{run}`: {status}\n")

    md.append("\n## SHA-256\n\n```\n")
    for eintrag in kopiert:
        md.append(f"{eintrag['sha256']}  {eintrag['ziel']}\n")
    md.append("```\n")

    md.append("\n## So rechnet man nach\n\n```\n")
    md.append("# Gesamtbericht aus den Rohdaten\n.venv/bin/python skripte/ergebnisse_komplett_md.py\n\n")
    md.append("# Vergleichstabelle aus den Laeufen\n.venv/bin/python skripte/vergleich_20261116.py\n\n")
    md.append("# bereinigte Auswertung\n.venv/bin/python skripte/ausschluss_konflikte.py\n```\n")
    md.append(
        "\nDie Skripte erwarten die Projektstruktur (`yun_full/` neben `runs/`); im Archiv\n"
        "liegen die Laeufe unter `laeufe/`. Fuer eine eigene Auswertung genuegen\n"
        "`goldstandard/yun699.jsonl` und die `predictions.jsonl` je Lauf.\n"
    )
    (ZIEL / "MANIFEST.md").write_text("".join(md), encoding="utf-8")

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archiv:
        for p in sorted(ZIEL.rglob("*")):
            if p.is_file():
                archiv.write(p, Path("benchmark_analysis_handoff_20261116") / p.relative_to(ZIEL))

    print(f"Archiv: {ZIP} ({ZIP.stat().st_size / 1e6:.2f} MB, {len(list(ZIEL.rglob('*'))) } Eintraege)")
    print(f"Dateien: {len(kopiert)} + MANIFEST.md")
    print(f"Fehlend: {fehlend or 'keine'}")
    print(f"Fehlende Vergleichslaeufe: {nicht_enthalten or 'keine'}")
    print(f"Berichtpruefung: {sum(1 for _, _, ok in bericht_pruefung if ok)}/{len(bericht_pruefung)} Laeufe vollstaendig")
    print(f"Validierungsfehler: {len(fehler)}")
    for eintrag in fehler:
        print("  -", eintrag)
    return 0 if not (fehlend or fehler) else 1


if __name__ == "__main__":
    sys.exit(main())
