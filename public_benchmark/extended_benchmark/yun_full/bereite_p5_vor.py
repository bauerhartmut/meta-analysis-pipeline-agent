"""Bereitet P5 offline vor: die 103 Budget-Ausfaelle als Record-Auswahl pruefen.

Kein Netzlauf, keine Anfrage. Das Skript beantwortet nur: sind alle 103 ids in
`yun699.jsonl` vorhanden, gibt es ihre Dokumentdateien, wie viele Goldzellen
tragen sie, und welche sind nicht bewertbar? Ausgegeben wird die fertige
Kommandozeile fuer den Lauf und die Id-Liste.

Aufruf:
    python yun_full/bereite_p5_vor.py
    python yun_full/bereite_p5_vor.py --json ... --md ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
REPO = BENCH.parent.parent
LESEKOPIE = BENCH / "runs" / "_lesekopie_20261118" / "predictions.jsonl"
RECORDS = HIER / "records" / "yun699.jsonl"
MODELL = "glm"
BUDGET = 24000
RUN_ID = "yun699_p5_24000_20261118"


def lade(pfad: Path) -> list[dict[str, Any]]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def baue(zeilen: list[dict[str, Any]], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Teilt die Ausfaelle in bewertbar und nicht bewertbar."""
    ausfaelle = [
        z for z in zeilen if z.get("model") == MODELL and z.get("fehlerklasse") == "length_ohne_ergebnis"
    ]
    bewertbar: list[dict[str, Any]] = []
    nicht_bewertbar: list[dict[str, Any]] = []
    fehlend: list[str] = []
    ohne_dok: list[str] = []
    for zeile in ausfaelle:
        rid = zeile["record_id"]
        record = records.get(rid)
        if record is None:
            fehlend.append(rid)
            continue
        pfad = (record.get("document") or {}).get("path") or ""
        if not pfad or not (REPO / pfad).exists():
            ohne_dok.append(rid)
        zellen = (record.get("gold") or {}).get("cells") or []
        eintrag = {"record_id": rid, "goldzellen": len(zellen)}
        (bewertbar if zellen else nicht_bewertbar).append(eintrag)
    ids = [z["record_id"] for z in ausfaelle]
    try:
        records_pfad = RECORDS.relative_to(REPO).as_posix()
    except ValueError:  # im Test zeigt REPO woanders hin
        records_pfad = str(RECORDS)
    befehl = (
        ".venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py"
        f" --records {records_pfad}"
        ' --split ""'
        f" --ids {','.join(ids)}"
        f" --models {MODELL} --workers 2 --max-tokens {BUDGET}"
        f" --run-id {RUN_ID} --retry-strategie neu --quelle p5_{BUDGET}"
    )
    return {
        "modell": MODELL,
        "budget": BUDGET,
        "run_id": RUN_ID,
        "ausfaelle": len(ausfaelle),
        "ids": ids,
        "bewertbar": bewertbar,
        "nicht_bewertbar": [
            {**e, "grund": "keine Goldzellen"} for e in nicht_bewertbar
        ],
        "goldzellen_bewertbar": sum(e["goldzellen"] for e in bewertbar),
        "records_datei": records_pfad,
        "in_records_datei_fehlt": sorted(fehlend),
        "ohne_dokumentdatei": sorted(ohne_dok),
        "befehl": befehl,
    }


def bericht(werte: dict[str, Any]) -> str:
    zeilen = [
        "# P5-Vorbereitung: die 103 Budget-Ausfaelle",
        "",
        "Offline erstellt, **kein Netzlauf**. Grundlage: Lesekopie "
        "`runs/_lesekopie_20261118`, Klasse `length_ohne_ergebnis` (der Timeout "
        "`yun2024:87` gehoert nicht dazu), Records aus "
        f"`{werte['records_datei']}`.",
        "",
        "| Prüfpunkt | Wert |",
        "|---|---|",
        f"| Ausfälle | {werte['ausfaelle']} |",
        f"| bewertbar (Goldzellen > 0) | {len(werte['bewertbar'])} |",
        f"| nicht bewertbar | {len(werte['nicht_bewertbar'])} |",
        f"| Goldzellen der bewertbaren | {werte['goldzellen_bewertbar']} |",
        f"| nicht in der Record-Datei | {len(werte['in_records_datei_fehlt'])} |",
        f"| ohne Dokumentdatei | {len(werte['ohne_dokumentdatei'])} |",
        "",
    ]
    if werte["nicht_bewertbar"]:
        for eintrag in werte["nicht_bewertbar"]:
            zeilen.append(
                f"- **{eintrag['record_id']} ist nicht bewertbar** ({eintrag['grund']}): "
                "der Record liefert keine Trefferfläche, jede vorhergesagte Zelle wäre "
                "ein Fehlalarm. Er läuft mit, zählt aber nicht in Recall oder MAE."
            )
    zeilen += [
        "",
        "## Befehl für den Lauf",
        "",
        "```",
        werte["befehl"],
        "```",
        "",
        "Vorher `--dry-run` an dieselbe Zeile hängen: erwartet werden "
        f"{werte['ausfaelle']} Aufträge und keine Anfrage.",
        "",
        "## Id-Liste",
        "",
        "```",
        ",".join(werte["ids"]),
        "```",
    ]
    return "\n".join(zeilen) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(BENCH / "iterativ" / "ergebnisse" / "p5_vorbereitung_20261118.json"))
    parser.add_argument("--md", default=str(BENCH / "iterativ" / "ergebnisse" / "p5_vorbereitung_20261118.md"))
    args = parser.parse_args()

    records = {r["record_id"]: r for r in lade(RECORDS)}
    werte = baue(lade(LESEKOPIE), records)
    text = bericht(werte)

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(werte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.md).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
