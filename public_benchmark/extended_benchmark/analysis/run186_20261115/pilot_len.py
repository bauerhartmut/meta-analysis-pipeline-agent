#!/usr/bin/env python3
"""Pilotwahl und Piloturteil fuer die Length-Ausfaelle (Phase 2 des Konzepts).

Zwei Schritte, beide ohne API-Aufruf:

1. ``--waehlen``: aus den Fehlzeilen eines Laufs sechs Records deterministisch
   auswaehlen, gleichmaessig ueber die Artikellaenge verteilt.
2. ``--urteilen``: die Pilotzeilen formal bewerten (finish_reason, parsebares
   JSON, Tokens). Bewertet wird nur die Form, nie ein Treffer — die Auswahl
   besteht aus bereits gescheiterten Records, ein Erfolg dort ist ein strenger
   Test, kein Schaetzer fuer die Gesamtquote.

Aufruf:

    python .../pilot_len.py --waehlen --run yun_test186_v6_20261115 \
        --records .../records/yun_test186.jsonl --ids-out .../pilot_ids.txt
    python .../pilot_len.py --urteilen --run pilot_len_b_20261116
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402

AUSFALL = "length_ohne_ergebnis"
KAPUTT = ("kein_json", "kein_objet")
ZIEL_ERFOLGE = 5
ZIEL_MEDIAN = 6000


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def waehle_pilot(kandidaten: list[dict[str, Any]], k: int = 6) -> list[str]:
    """Deterministisch k ids, gleichmaessig ueber die sortierte Textlaenge."""
    if len(kandidaten) <= k:
        return [kandidat["record_id"] for kandidat in kandidaten]
    indizes = sorted({round(i * (len(kandidaten) - 1) / (k - 1)) for i in range(k)})
    return [kandidaten[index]["record_id"] for index in indizes]


def urteil(zeilen: list[dict[str, Any]]) -> dict[str, Any]:
    """Formales Urteil ueber einen Pilotlauf."""
    erfolge: list[dict[str, Any]] = []
    for zeile in zeilen:
        parse_error = str(zeile.get("parse_error") or "")
        kaputt = parse_error in KAPUTT or parse_error.startswith("json_fehler")
        if (zeile.get("finish_reason") == "stop") and not zeile.get("fehlerklasse") and not kaputt:
            erfolge.append(zeile)
    tokens = [int(zeile.get("completion_tokens") or 0) for zeile in erfolge]
    median = statistics.median(tokens) if tokens else None
    bestanden = len(erfolge) >= ZIEL_ERFOLGE and median is not None and median <= ZIEL_MEDIAN
    return {
        "zeilen": len(zeilen),
        "erfolge": len(erfolge),
        "quote": round(len(erfolge) / len(zeilen), 4) if zeilen else None,
        "medien_tokens": median,
        "kriterium": f"mindestens {ZIEL_ERFOLGE} Erfolge, Median <= {ZIEL_MEDIAN} Tokens",
        "bestanden": bestanden,
        "details": [
            {
                "record_id": zeile.get("record_id"),
                "finish_reason": zeile.get("finish_reason"),
                "fehlerklasse": zeile.get("fehlerklasse"),
                "parse_error": zeile.get("parse_error"),
                "tokens": zeile.get("completion_tokens"),
                "zellen": len(zeile.get("rows") or []),
                "timepoint_header": zeile.get("timepoint_header"),
                "fallback": zeile.get("fallback"),
            }
            for zeile in zeilen
        ],
    }


def textlaenge(record: dict[str, Any]) -> int:
    pfad = (record.get("document") or {}).get("path") or ""
    datei = REPO / pfad if pfad else None
    return len(datei.read_text(encoding="utf-8", errors="replace")) if datei and datei.exists() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--waehlen", action="store_true")
    parser.add_argument("--urteilen", action="store_true")
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=None)
    parser.add_argument("--ids-out", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--k", type=int, default=6)
    args = parser.parse_args()

    lauf = BENCH / "runs" / args.run / "predictions.jsonl"
    zeilen = read_jsonl(lauf)

    if args.waehlen:
        if not args.records:
            parser.error("--waehlen braucht --records")
        records = {str(r["record_id"]): r for r in read_jsonl(args.records)}
        fehl = [z["record_id"] for z in zeilen if z.get("fehlerklasse") == AUSFALL and z["record_id"] in records]
        kandidaten = sorted(
            ({"record_id": rid, "textlaenge": textlaenge(records[rid])} for rid in fehl),
            key=lambda k: (k["textlaenge"], k["record_id"]),
        )
        ids = waehle_pilot(kandidaten, args.k)
        ausgabe = {"gewaehlt": ids, "kandidaten": len(kandidaten), "verteilung": [k["textlaenge"] for k in kandidaten]}
        if args.ids_out:
            args.ids_out.parent.mkdir(parents=True, exist_ok=True)
            args.ids_out.write_text(",".join(ids), encoding="utf-8")
        print(json.dumps(ausgabe, ensure_ascii=False, indent=2))
        return 0

    ergebnis = urteil(zeilen)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    return 0 if ergebnis["bestanden"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
