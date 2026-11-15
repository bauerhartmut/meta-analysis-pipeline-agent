#!/usr/bin/env python3
"""Prueft die vom Modell genannten Messzeitpunkte ohne Modell gegen den Artikeltext.

Drei Fragen, alle offline entscheidbar:

1. Stehen der gewaehlte Zeitpunkt und die verworfenen Zeitpunkte woertlich im
   Artikel? (erfundene Labels fallen hier auf)
2. Ist der gewaehlte Zeitpunkt der spaeteste der genannten? (Widerspruch, wenn
   ein verworfener Zeitpunkt spaeter liegt)
3. Wie oft fehlt die Zeitpunktangabe ganz?

Es wird nichts korrigiert; die Pruefung markiert nur.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from stage_extraction import beleg_im_text, normalisiere  # noqa: E402

ZEIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*-?\s*(day|week|month|year)s?\b")
# Kumulative Angaben stehen fuer den gesamten Beobachtungszeitraum und werden
# deshalb als spaetester Zeitpunkt behandelt.
KUMMULATIV = ("total", "overall", "cumulative", "all follow-up", "whole study")
# Platzhalter sind keine Labels aus dem Artikel; sie werden nicht gegen den
# Text geprueft, sondern separat gezaehlt.
PLATZHALTER = ("running text", "not applicable", "not stated")


def rang(label: str) -> float | None:
    """Ordnet ein Zeitpunktlabel in Monaten ein; None, wenn unbestimmbar."""
    text = normalisiere(label)
    if not text:
        return None
    if any(marker in text for marker in KUMMULATIV):
        return 999.0
    if "baseline" in text or "before intervention" in text:
        return 0.0
    match = ZEIT_RE.search(text)
    if not match:
        return None
    value = float(match.group(1).replace(",", "."))
    unit = match.group(2)
    if unit == "day":
        return value / 30.44
    if unit == "week":
        return value * 7 / 30.44
    if unit == "year":
        return value * 12
    return value


def pruefe_zeitpunkte(timepoints: dict[str, Any], text: str) -> dict[str, Any]:
    """Prueft eine Zeitpunktangabe gegen den Artikeltext."""
    chosen = str(timepoints.get("chosen") or "").strip()
    discarded = [str(item).strip() for item in (timepoints.get("discarded") or []) if str(item).strip()]
    chosen_rang = rang(chosen)
    verworfen = {label: rang(label) for label in discarded}
    widerspruch = [
        label
        for label, label_rang in verworfen.items()
        if chosen_rang is not None and label_rang is not None and label_rang > chosen_rang
    ]
    ist_platzhalter = normalisiere(chosen) in PLATZHALTER
    return {
        "chosen": chosen,
        "chosen_rang": chosen_rang,
        "chosen_platzhalter": ist_platzhalter,
        "chosen_belegt": ist_platzhalter or beleg_im_text(chosen, text),
        "discarded": discarded,
        "discarded_belegt": {label: beleg_im_text(label, text) for label in discarded},
        "discarded_unbelegt": [label for label in discarded if not beleg_im_text(label, text)],
        "spaeter_verworfen": widerspruch,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Laufverzeichnis unter runs/")
    parser.add_argument("--records", type=Path, default=HERE / "records" / "yun_dev.jsonl")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    run_dir = HERE / "runs" / args.run if not Path(args.run).is_absolute() else Path(args.run)
    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {str(record["record_id"]): record for record in records}
    rows = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    details: list[dict[str, Any]] = []
    for row in rows:
        record = by_id.get(str(row["record_id"]))
        if record is None:
            continue
        path = record["document"].get("path") or ""
        candidate = REPO / path if path else None
        text = candidate.read_text(encoding="utf-8", errors="replace") if candidate and candidate.exists() else ""
        timepoints = row.get("timepoints") or {}
        result = pruefe_zeitpunkte(timepoints, text)
        result["record_id"] = row["record_id"]
        result["model"] = row.get("model")
        result["timepoint_error"] = row.get("timepoint_error", "")
        details.append(result)

    geprueft = [item for item in details if item["chosen"]]
    echte_labels = [item for item in geprueft if not item.get("chosen_platzhalter")]
    zusammenfassung = {
        "records": len(details),
        "mit_zeitpunkt": len(geprueft),
        "ohne_zeitpunkt": len(details) - len(geprueft),
        "chosen_platzhalter": len(geprueft) - len(echte_labels),
        "chosen_belegt": sum(1 for item in echte_labels if item["chosen_belegt"]),
        "echte_labels": len(echte_labels),
        "chosen_rang_bekannt": sum(1 for item in geprueft if item["chosen_rang"] is not None),
        "discarded_labels": sum(len(item["discarded"]) for item in geprueft),
        "discarded_unbelegt": sum(len(item["discarded_unbelegt"]) for item in geprueft),
        "widersprueche": sum(1 for item in geprueft if item["spaeter_verworfen"]),
        "chosen_verteilung": dict(Counter(item["chosen"] for item in geprueft)),
        "fehler": dict(Counter(item["timepoint_error"] for item in details if item["timepoint_error"])),
    }
    ergebnis = {"run": args.run, "zusammenfassung": zusammenfassung, "details": details}

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(zusammenfassung, ensure_ascii=False, indent=2))
    for item in geprueft:
        if (not item["chosen_belegt"] and not item.get("chosen_platzhalter")) or item["spaeter_verworfen"]:
            print(
                f"  {item['record_id']}: chosen={item['chosen']!r} belegt={item['chosen_belegt']} "
                f"spaeter_verworfen={item['spaeter_verworfen']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
