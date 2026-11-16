#!/usr/bin/env python
"""Packt die Rohdaten fuer eine externe Analyse in ein ZIP mit MANIFEST.md.

Enthalten sind ausschliesslich die angeforderten Dateien: Gesamtbericht,
Goldstandard, Auswertungs-JSONs, die drei Auswertungsskripte und die
predictions.jsonl samt validator.json der neun Vergleichslaeufe.

Es werden keine Dateien veraendert, keine Platzhalter erzeugt und keine
Modellaufrufe gemacht. Fehlende Dateien werden im Manifest als FEHLT gelistet
und fuehren zu einem Exit-Code ungleich 0.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/yun_full/baue_analyse_handoff.py
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

# (Quellpfad relativ zum Projekt, Zielpfad im Archiv, Zweck)
DATEIEN = [
    ("public_benchmark/extended_benchmark/yun_full/ergebnisse_komplett_20261116.md",
     "bericht/ergebnisse_komplett_20261116.md",
     "Gesamtbericht, aus den Messdaten erzeugt"),
    ("public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl",
     "goldstandard/yun699.jsonl",
     "Goldstandard: 699 Records mit Goldzellen, Kontext und PMC-ID"),
    ("public_benchmark/extended_benchmark/yun_full/vergleich_20261116.json",
     "auswertung/vergleich_20261116.json",
     "Kennzahlen aller neun Vergleichslaeufe, einheitlich berechnet"),
    ("public_benchmark/extended_benchmark/yun_full/ausschluss_konflikte_20261116.json",
     "auswertung/ausschluss_konflikte_20261116.json",
     "Kennzahlen mit und ohne bestreitbare Goldannotationen"),
    ("public_benchmark/extended_benchmark/yun_full/ergebnisse_komplett_md.py",
     "skripte/ergebnisse_komplett_md.py",
     "erzeugt den Gesamtbericht aus den Messdaten"),
    ("public_benchmark/extended_benchmark/yun_full/vergleich_20261116.py",
     "skripte/vergleich_20261116.py",
     "berechnet die Vergleichstabelle aus predictions.jsonl"),
    ("public_benchmark/extended_benchmark/yun_full/ausschluss_konflikte.py",
     "skripte/ausschluss_konflikte.py",
     "berechnet die Auswertung ohne konfliktaere Records"),
    ("public_benchmark/extended_benchmark/runs/yun699_test60_20261116/predictions.jsonl",
     "laeufe/yun699_test60_20261116/predictions.jsonl",
     "Referenzlauf 60 Records, 4000 Tokens, GLM-5.3"),
    ("public_benchmark/extended_benchmark/runs/yun699_test60_20261116/validator.json",
     "laeufe/yun699_test60_20261116/validator.json",
     "Validatormessung auf dem Referenzlauf"),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_glm_20261116/predictions.jsonl",
     "laeufe/yun20_4000_glm_20261116/predictions.jsonl",
     "GLM-5.3, 20 Records, 4000 Tokens"),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_qwen_20261116/predictions.jsonl",
     "laeufe/yun20_4000_qwen_20261116/predictions.jsonl",
     "Qwen3.5-397B, 20 Records, 4000 Tokens"),
    ("public_benchmark/extended_benchmark/runs/yun20_4000_qwen30_20261116/predictions.jsonl",
     "laeufe/yun20_4000_qwen30_20261116/predictions.jsonl",
     "Qwen3-30B, 20 Records, 4000 Tokens"),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_glm_cb_20261116/predictions.jsonl",
     "laeufe/yun20_8000_glm_cb_20261116/predictions.jsonl",
     "GLM-5.3, 20 Records, 8000 Tokens, frisch generiert"),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_qwen_cb_20261116/predictions.jsonl",
     "laeufe/yun20_8000_qwen_cb_20261116/predictions.jsonl",
     "Qwen3.5-397B, 20 Records, 8000 Tokens, frisch generiert"),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_qwen30_cb_20261116/predictions.jsonl",
     "laeufe/yun20_8000_qwen30_cb_20261116/predictions.jsonl",
     "Qwen3-30B, 20 Records, 8000 Tokens, frisch generiert"),
    ("public_benchmark/extended_benchmark/runs/yun20_8000_glm_v8_20261116/predictions.jsonl",
     "laeufe/yun20_8000_glm_v8_20261116/predictions.jsonl",
     "Experiment C: GLM-5.3 mit Quellenzeile (v8), 8000 Tokens"),
]


def sha256(pfad: Path) -> str:
    h = hashlib.sha256()
    with pfad.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def zeilen(pfad: Path) -> int:
    return sum(1 for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip())


def pruefe(pfad: Path) -> tuple[bool, str]:
    """Syntaktische Pruefung; liefert (ok, Hinweis)."""
    try:
        if pfad.suffix == ".json":
            json.loads(pfad.read_text(encoding="utf-8"))
            return True, "JSON valide"
        if pfad.suffix == ".jsonl":
            for nummer, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
                if zeile.strip():
                    json.loads(zeile)
            return True, f"JSONL valide, {zeilen(pfad)} Zeilen"
        if pfad.suffix == ".py":
            compile(pfad.read_text(encoding="utf-8"), str(pfad), "exec")
            return True, "Python syntaktisch valide"
        return True, "Textdatei"
    except Exception as exc:  # noqa: BLE001 - Pruefung soll weiterlaufen
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    if ZIEL.exists():
        shutil.rmtree(ZIEL)
    ZIEL.mkdir(parents=True)

    fehlend: list[str] = []
    kopiert: list[dict] = []
    for quelle_rel, ziel_rel, zweck in DATEIEN:
        quelle = REPO / quelle_rel
        if not quelle.exists():
            fehlend.append(quelle_rel)
            continue
        ziel = ZIEL / ziel_rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ziel)
        ok, hinweis = pruefe(ziel)
        kopiert.append(
            {
                "quelle": quelle_rel,
                "ziel": ziel_rel,
                "bytes": ziel.stat().st_size,
                "sha256": sha256(ziel),
                "zweck": zweck,
                "pruefung": ("ok: " if ok else "FEHLER: ") + hinweis,
                "zeilen": zeilen(ziel) if ziel.suffix in (".jsonl", ".md", ".py") else None,
            }
        )

    # Bericht gegen Messdaten pruefen: Kennzahlen muessen im Text stehen.
    bericht = ZIEL / "bericht" / "ergebnisse_komplett_20261116.md"
    vergleich = ZIEL / "auswertung" / "vergleich_20261116.json"
    bericht_pruefung = []
    if bericht.exists() and vergleich.exists():
        text = bericht.read_text(encoding="utf-8")
        daten = {e["run"]: e for e in json.loads(vergleich.read_text(encoding="utf-8"))["laeufe"]}
        for run in ("yun699_test60_20261116", "yun20_8000_glm_cb_20261116", "yun20_8000_qwen_cb_20261116"):
            e = daten[run]
            f1 = f"{e['f1']:.4f}".replace(".", ",")
            treffer = f1 in text
            bericht_pruefung.append((run, f1, treffer))
    alle_ok = all(ok for _, _, ok in bericht_pruefung) if bericht_pruefung else False

    zeilen_md = [
        "# MANIFEST: Rohdaten fuer die externe Analyse\n\n",
        "**Erzeugt:** 16.11.2026  \n",
        "**Zweck:** unabhaengige Nachrechnung aller Metriken und Fehleranalyse auf Zellebene  \n",
        f"**Dateien im Archiv:** {len(kopiert)} von {len(DATEIEN)} angeforderten  \n",
        f"**Fehlende Dateien:** {', '.join(fehlend) if fehlend else 'keine'}\n\n",
        "## Hinweis zu den Pfaden\n\n",
        "Die Laeufe liegen im Projekt unter `public_benchmark/extended_benchmark/runs/`,\n"
        "nicht unter `public_benchmark/runs/`. Die Quellpfade in der Tabelle sind die\n"
        "tatsaechlichen Projektpfade.\n\n",
        "## Dateien\n\n",
        "| # | Projektpfad (Quelle) | Pfad im Archiv | Groesse | Zeilen | Zweck | Pruefung |\n",
        "|---:|---|---|---:|---:|---|---|\n",
    ]
    for i, eintrag in enumerate(kopiert, 1):
        groesse = f"{eintrag['bytes']:,} B".replace(",", " ")
        zeilen_md.append(
            f"| {i} | `{eintrag['quelle']}` | `{eintrag['ziel']}` | {groesse} | "
            f"{eintrag['zeilen'] if eintrag['zeilen'] is not None else '-'} | {eintrag['zweck']} | {eintrag['pruefung']} |\n"
        )
    if fehlend:
        zeilen_md.append("\n## Fehlende Dateien\n\n")
        for name in fehlend:
            zeilen_md.append(f"- `{name}`: **nicht vorhanden**, nicht ersetzt\n")

    zeilen_md.append("\n## SHA-256\n\n```\n")
    for eintrag in kopiert:
        zeilen_md.append(f"{eintrag['sha256']}  {eintrag['ziel']}\n")
    zeilen_md.append("```\n")

    zeilen_md.append("\n## Bericht gegen Messdaten geprueft\n\n")
    if bericht_pruefung:
        for run, f1, treffer in bericht_pruefung:
            zeilen_md.append(f"- `{run}`: F1 {f1} im Bericht {'gefunden' if treffer else 'NICHT gefunden'}\n")
    else:
        zeilen_md.append("- Bericht oder Vergleichsdatei fehlt, Pruefung nicht moeglich\n")

    zeilen_md.append("\n## So rechnet man nach\n\n```\n")
    zeilen_md.append("# Gesamtbericht aus den Rohdaten\n.venv/bin/python skripte/ergebnisse_komplett_md.py\n\n")
    zeilen_md.append("# Vergleichstabelle aus den Laeufen\n.venv/bin/python skripte/vergleich_20261116.py\n\n")
    zeilen_md.append("# bereinigte Auswertung\n.venv/bin/python skripte/ausschluss_konflikte.py\n```\n")
    zeilen_md.append(
        "\nDie Skripte erwarten die Projektstruktur (`yun_full/` neben `runs/`); im Archiv\n"
        "liegen die Laeufe unter `laeufe/`. Fuer eine eigene Auswertung genuegen\n"
        "`goldstandard/yun699.jsonl` und die `predictions.jsonl` je Lauf.\n"
    )
    (ZIEL / "MANIFEST.md").write_text("".join(zeilen_md), encoding="utf-8")

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archiv:
        for p in sorted(ZIEL.rglob("*")):
            if p.is_file():
                archiv.write(p, Path("benchmark_analysis_handoff_20261116") / p.relative_to(ZIEL))

    print(f"Archiv: {ZIP} ({ZIP.stat().st_size / 1e6:.2f} MB)")
    print(f"Dateien: {len(kopiert)} + MANIFEST.md = {len(kopiert) + 1}")
    print(f"Fehlend: {fehlend or 'keine'}")
    print(f"Bericht gegen Messdaten: {'ok' if alle_ok else 'PRUEFUNG FEHLGESCHLAGEN'}")
    for run, f1, treffer in bericht_pruefung:
        print(f"  {run}: F1 {f1} {'gefunden' if treffer else 'FEHLT'}")
    fehler = [e for e in kopiert if not e["pruefung"].startswith("ok")]
    print(f"Validierungsfehler: {len(fehler)}")
    for e in fehler:
        print("  ", e["ziel"], e["pruefung"])
    return 1 if (fehlend or fehler or not alle_ok) else 0


if __name__ == "__main__":
    sys.exit(main())
