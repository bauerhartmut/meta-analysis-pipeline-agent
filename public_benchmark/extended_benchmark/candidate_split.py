"""Kandidaten-Split: steht jede Goldzahl woertlich im Artikeltext?

Reine Textpruefung ohne Modellaufrufe: fuer jede Goldzelle der noch nicht
verwendeten Records wird gesucht, ob die Zahl woertlich im Artikel steht
(deutsche und englische Schreibweise, Tausendertrennzeichen, Minus mit
Leerzeichen). Ausgegeben werden Belegposition und Textfenster; Gold, Records
und Predictions bleiben unveraendert.

Aufruf:
    python public_benchmark/extended_benchmark/candidate_split.py \
        --out public_benchmark/extended_benchmark/analysis/candidate_split_20261115
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

try:  # als Modul (Tests) oder als Skript
    from .analyze_errors import zahlenvarianten
    from .precheck_gold import region, teile
except ImportError:  # pragma: no cover
    from analyze_errors import zahlenvarianten
    from precheck_gold import region, teile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECORDS = HERE / "records" / "yun.jsonl"
FENSTER = 90


def finde(text: str, wert: float) -> list[dict[str, Any]]:
    """Alle woertlichen Fundstellen einer Zahl mit Position und Fenster."""
    treffer: list[dict[str, Any]] = []
    grenze = teile(text)
    for variante in zahlenvarianten(wert):
        if not variante or not re.search(r"\d", variante):
            continue
        muster = re.compile(rf"(?<![\d.,]){re.escape(variante)}(?![\d.,])")
        for match in muster.finditer(text):
            treffer.append(
                {
                    "variante": variante,
                    "position": match.start(),
                    "region": region(match.start(), grenze),
                    "fenster": text[max(0, match.start() - FENSTER) : match.end() + FENSTER]
                    .replace("\n", " ")
                    .strip(),
                }
            )
    treffer.sort(key=lambda t: t["position"])
    return treffer


def finde_gerundet(text: str, wert: float) -> tuple[str, dict[str, Any] | None]:
    """Steht die Zahl nur gerundet im Text? Hilft, Lesefehler von Rundung zu trennen."""
    for name, kandidat in (("eine Nachkommastelle", round(wert, 1)), ("Ganzzahl", float(round(wert)))):
        if abs(kandidat - wert) < 1e-9:
            continue
        if name == "Ganzzahl" and abs(kandidat) < 1:
            # "0" als Ganzzahl waere in jedem Text zu finden und sagt nichts.
            continue
        funde = finde(text, kandidat)
        if funde:
            return name, funde[0]
    return "", None


def pruefe_record(record: dict[str, Any]) -> dict[str, Any]:
    pfad = REPO / (record["document"].get("path") or "")
    text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
    zellen = []
    for cell in record["gold"]["cells"]:
        funde = finde(text, float(cell["value"]))
        naehe, naehe_fund = ("", None) if funde else finde_gerundet(text, float(cell["value"]))
        zellen.append(
            {
                "record_id": record["record_id"],
                "document": record["document"]["id"],
                "field": cell["field"],
                "arm": cell.get("arm") or "",
                "gold": f"{float(cell['value']):g}",
                "gefunden": bool(funde),
                "anzahl": len(funde),
                "variante": funde[0]["variante"] if funde else "",
                "position": funde[0]["position"] if funde else "",
                "region": funde[0]["region"] if funde else "",
                "fenster": funde[0]["fenster"] if funde else "",
                "naehe": naehe,
                "naehe_position": naehe_fund["position"] if naehe_fund else "",
                "naehe_fenster": naehe_fund["fenster"] if naehe_fund else "",
                "text_vorhanden": bool(text),
                "text_laenge": len(text),
            }
        )
    return {
        "record_id": record["record_id"],
        "document": record["document"]["id"],
        "split": record["document"].get("split", ""),
        "text_vorhanden": bool(text),
        "text_laenge": len(text),
        "outcome": (record.get("context") or {}).get("outcome", ""),
        "timepoint": ((record.get("timepoint") or {}).get("target") or ""),
        "zellen": zellen,
        "zellen_gesamt": len(zellen),
        "zellen_gefunden": sum(1 for z in zellen if z["gefunden"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ohne-split", default="dev", help="Records dieses Splits auslassen")
    parser.add_argument("--nur-split", default="", help="nur Records dieses Splits pruefen")
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in args.records.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.nur_split:
        records = [r for r in records if r["document"].get("split") == args.nur_split]
    if args.ohne_split:
        records = [r for r in records if r["document"].get("split") != args.ohne_split]

    geprueft = [pruefe_record(record) for record in records]
    zellen = [z for r in geprueft for z in r["zellen"]]
    gefunden = sum(1 for z in zellen if z["gefunden"])

    args.out.mkdir(parents=True, exist_ok=True)
    felder = [
        "record_id", "document", "field", "arm", "gold", "gefunden", "anzahl",
        "variante", "position", "region", "fenster", "naehe", "naehe_position",
        "naehe_fenster", "text_vorhanden", "text_laenge",
    ]
    with (args.out / "zellen.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=felder, extrasaction="ignore")
        writer.writeheader()
        for zelle in zellen:
            writer.writerow(zelle)
    (args.out / "kandidaten.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "record_id": r["record_id"],
                    "document": r["document"],
                    "outcome": r["outcome"],
                    "timepoint": r["timepoint"],
                    "text_laenge": r["text_laenge"],
                    "zellen_gesamt": r["zellen_gesamt"],
                    "zellen_gefunden": r["zellen_gefunden"],
                    "zellen": [
                        {"field": z["field"], "arm": z["arm"], "gold": z["gold"], "gefunden": z["gefunden"]}
                        for z in r["zellen"]
                    ],
                },
                ensure_ascii=False,
            )
            for r in geprueft
        )
        + "\n",
        encoding="utf-8",
    )

    je_feld: dict[str, dict[str, int]] = {}
    for zelle in zellen:
        block = je_feld.setdefault(zelle["field"], {"zellen": 0, "gefunden": 0})
        block["zellen"] += 1
        block["gefunden"] += 1 if zelle["gefunden"] else 0
    # Ein Record ohne Goldzellen ist nicht "komplett belegt", sondern leer.
    komplett = [
        r for r in geprueft if r["zellen_gesamt"] > 0 and r["zellen_gefunden"] == r["zellen_gesamt"]
    ]
    ohne_beleg = [r for r in geprueft if r["zellen_gefunden"] == 0]
    summary = {
        "records": len(geprueft),
        "zellen": len(zellen),
        "zellen_gefunden": gefunden,
        "zellen_ohne_beleg": len(zellen) - gefunden,
        "quote": round(gefunden / len(zellen), 4) if zellen else 0.0,
        "records_komplett_belegt": len(komplett),
        "records_ohne_beleg": len(ohne_beleg),
        "records_mit_luecke": len(geprueft) - len(komplett),
        "records_ohne_text": sum(1 for r in geprueft if not r["text_vorhanden"]),
        "records_ohne_zellen": sum(1 for r in geprueft if not r["zellen"]),
        # Kurztext = nur Abstract (unter 5.000 Zeichen); dort fehlen Tabellenwerte
        # strukturell, unabhaengig von der Goldqualitaet.
        "zellen_ohne_beleg_kurztext": sum(
            1 for r in geprueft if r["text_laenge"] < 5000 for z in r["zellen"] if not z["gefunden"]
        ),
        "zellen_ohne_beleg_langtext": sum(
            1 for r in geprueft if r["text_laenge"] >= 5000 for z in r["zellen"] if not z["gefunden"]
        ),
        "zellen_ohne_beleg_gerundet": sum(
            1 for r in geprueft for z in r["zellen"] if not z["gefunden"] and z["naehe"]
        ),
        "zellen_ohne_beleg_ohne_naehe": sum(
            1 for r in geprueft for z in r["zellen"] if not z["gefunden"] and not z["naehe"]
        ),
        "je_feld": je_feld,
        "module_aufrufe": 0,
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Records: {summary['records']} | Zellen: {summary['zellen']} | "
        f"woertlich belegt: {gefunden} ({summary['quote']:.4f}) | "
        f"Records komplett: {summary['records_komplett_belegt']}"
    )
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
