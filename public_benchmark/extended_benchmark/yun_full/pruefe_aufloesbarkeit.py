"""Sind die Ausfaelle eines Laufs noch aufloesbar? — offline, ohne Netzlauf.

Beantwortet drei Fragen je Zeile: Gibt es den Record noch, gibt es die
Dokumentdatei noch, und hat der Record Goldzellen? Zusaetzlich wird geprueft, ob
eine Ersatzquelle (z. B. ein aelterer 699er-Dump) den Record enthaelt, wenn er in
`records/` fehlt.

Hintergrund: `records/yun.jsonl` ist eine abgeleitete, unversionierte Datei mit
heute 450 Records; der Lauf `yun699_8000_alle_20261117` hatte 699. Die
versionierte Quelle ist `yun_full/records/yun699.jsonl`. Fuer eine Messung unter
P5 muss vorher feststehen, welche Records woher kommen.

Aufruf:
    python yun_full/pruefe_aufloesbarkeit.py            # Lesekopie, glm
    python yun_full/pruefe_aufloesbarkeit.py --modell qwen30
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
REPO = BENCH.parent.parent
LESEKOPIE = BENCH / "runs" / "_lesekopie_20261118" / "predictions.jsonl"
RECORDS = BENCH / "records"

#: Ersatzquellen, falls ein Record nicht mehr in `records/` steht. Die erste ist
#: die versionierte 699er-Datei des Laufs; die Handoff-Dumps sind lokale Kopien
#: und **nicht** versioniert.
ZUSATZ = [
    HIER / "records" / "yun699.jsonl",
    REPO / "handoff_20261116" / "daten" / "yun699.jsonl",
    REPO / "benchmark_analysis_handoff_20261116" / "goldstandard" / "yun699.jsonl",
]


def lade_jsonl(pfad: Path) -> list[dict[str, Any]]:
    if not pfad.exists():
        return []
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def index(quellen: list[Path]) -> dict[str, tuple[Path, dict[str, Any]]]:
    """record_id -> (Datei, Record); die erste Quelle gewinnt."""
    gefunden: dict[str, tuple[Path, dict[str, Any]]] = {}
    for quelle in quellen:
        for record in lade_jsonl(quelle):
            gefunden.setdefault(record["record_id"], (quelle, record))
    return gefunden


def versioniert(pfad: Path) -> bool:
    try:
        ergebnis = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "--error-unmatch", str(pfad)],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return ergebnis.returncode == 0


def pruefe(
    zeilen: list[dict[str, Any]],
    direkt: dict[str, tuple[Path, dict[str, Any]]],
    zusatz: dict[str, tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    gruppen: dict[str, dict[str, Any]] = {}
    for name, auswahl in (
        ("ausfall", [z for z in zeilen if z.get("fehlerklasse")]),
        ("erfolg", [z for z in zeilen if not z.get("fehlerklasse")]),
    ):
        ids = [z["record_id"] for z in auswahl]
        in_records, nur_zusatz, fehlt, ohne_doc, ohne_gold = [], [], [], [], []
        for rid in ids:
            if rid in direkt:
                quelle, record = direkt[rid]
                in_records.append(rid)
            elif rid in zusatz:
                quelle, record = zusatz[rid]
                nur_zusatz.append(rid)
            else:
                fehlt.append(rid)
                continue
            pfad = (record.get("document") or {}).get("path") or ""
            if not pfad or not (REPO / pfad).exists():
                ohne_doc.append(rid)
            if not ((record.get("gold") or {}).get("cells") or []):
                ohne_gold.append(rid)
        gruppen[name] = {
            "zeilen": len(auswahl),
            "in_records": len(in_records),
            "nur_in_zusatzquelle": len(nur_zusatz),
            "gar_nicht_gefunden": len(fehlt),
            "ohne_dokumentdatei": len(ohne_doc),
            "ohne_goldzellen": len(ohne_gold),
            "goldzellen": sum(
                len((zusatz.get(r) or direkt.get(r))[1].get("gold", {}).get("cells") or [])
                for r in ids
                if r in direkt or r in zusatz
            ),
            "beispiele_nur_zusatz": sorted(nur_zusatz)[:10],
            "beispiele_fehlt": sorted(fehlt)[:10],
            "beispiele_ohne_gold": sorted(ohne_gold)[:10],
        }
    return gruppen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quelle", default=str(LESEKOPIE))
    parser.add_argument("--modell", default="glm")
    parser.add_argument("--records-dir", default=str(RECORDS))
    parser.add_argument("--zusatz", nargs="*", default=[str(p) for p in ZUSATZ])
    parser.add_argument("--json", default="")
    parser.add_argument("--md", default="")
    args = parser.parse_args()

    zeilen = [z for z in lade_jsonl(Path(args.quelle)) if z.get("model") == args.modell]
    if not zeilen:
        print(f"FEHLER: keine Zeilen in {args.quelle}", flush=True)
        return 2

    records_quellen = sorted(Path(args.records_dir).glob("*.jsonl"))
    direkt = index(records_quellen)
    zusatz_pfade = [Path(p) for p in args.zusatz]
    zusatz = index([p for p in zusatz_pfade if p.exists()]) if zusatz_pfade else {}

    bericht = {
        "quelle": str(args.quelle),
        "modell": args.modell,
        "records_dateien": [p.name for p in records_quellen],
        "zusatzquellen": [
            {"pfad": str(p), "vorhanden": p.exists(), "versioniert": versioniert(p) if p.exists() else None}
            for p in zusatz_pfade
        ],
        "gruppen": pruefe(zeilen, direkt, zusatz),
    }

    a, e = bericht["gruppen"]["ausfall"], bericht["gruppen"]["erfolg"]
    zeilen_md = [
        "# Aufloesbarkeit der Ausfaelle",
        "",
        f"Quelle: `{args.quelle}` / {args.modell}. Records-Verzeichnis: "
        f"{', '.join(bericht['records_dateien'])}.",
        "",
        "| Gruppe | Zeilen | in `records/` | nur Ersatzquelle | nicht gefunden | ohne Dokument | ohne Gold | Goldzellen |",
        "|---|---|---|---|---|---|---|---|",
        f"| Ausfall | {a['zeilen']} | {a['in_records']} | {a['nur_in_zusatzquelle']} | {a['gar_nicht_gefunden']} | "
        f"{a['ohne_dokumentdatei']} | {a['ohne_goldzellen']} | {a['goldzellen']} |",
        f"| Erfolg | {e['zeilen']} | {e['in_records']} | {e['nur_in_zusatzquelle']} | {e['gar_nicht_gefunden']} | "
        f"{e['ohne_dokumentdatei']} | {e['ohne_goldzellen']} | {e['goldzellen']} |",
        "",
        "## Ersatzquellen",
        "",
    ]
    for quelle in bericht["zusatzquellen"]:
        zeilen_md.append(
            f"- `{quelle['pfad']}`: vorhanden={quelle['vorhanden']}, versioniert={quelle['versioniert']}"
        )
    if a["beispiele_nur_zusatz"]:
        zeilen_md += ["", "Nur über die Ersatzquelle erreichbar: " + ", ".join(a["beispiele_nur_zusatz"])]
    if a["beispiele_ohne_gold"]:
        zeilen_md += [
            "",
            "Ohne Goldzellen (nicht bewertbar): " + ", ".join(a["beispiele_ohne_gold"]),
        ]

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text("\n".join(zeilen_md) + "\n", encoding="utf-8")

    print("\n".join(zeilen_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
