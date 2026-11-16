#!/usr/bin/env python3
"""Read-only: Goldzellen auf verlesene Tausendertrenner pruefen.

Verdacht wie bei `yun2024:479`: Der Artikel druckt einen Zaehlwert mit
Tausendertrenner ("1,922"), das Gold hat ihn als Dezimalzahl gelesen (1,922).

Geprueft werden alle Goldzellen der Felder `*_group_size` und `*_events`:

* der Wert liegt unter 1000,
* Wert mal 1000 ist (bis auf Rundung) eine ganze Zahl,
* und der Artikel enthaelt diese Zahl mit Komma ("1,922") oder ohne
  Trennzeichen ("1922").

Ausgabe je Kandidat: Goldwert, gefundene Schreibweisen, Belegstelle, und ob die
Dezimalschreibweise ("1.922") ebenfalls im Text steht. Die eingefrorene Datei
wird nicht geaendert.

    python pruefe_tausendertrenner.py            # Tabelle auf der Konsole
    python pruefe_tausendertrenner.py --json ...  # Kandidaten als JSON
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2]
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent))

from candidate_split import REPO  # noqa: E402

RECORDS = BENCH / "records" / "yun_test76_ziel.jsonl"
ZAEHLFELDER = ("group_size", "events")


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def beleg(text: str, muster: str) -> list[str]:
    """Textausschnitte um jede Fundstelle des Musters."""
    stellen = []
    for treffer in re.finditer(re.escape(muster), text):
        ausschnitt = " ".join(text[max(0, treffer.start() - 70) : treffer.start() + 40].split())
        stellen.append(ausschnitt[-110:])
    return stellen


def pruefe(record: dict, text: str) -> list[dict]:
    kandidaten = []
    for cell in record["gold"]["cells"]:
        if not any(cell["field"].endswith(feld) for feld in ZAEHLFELDER):
            continue
        wert = float(cell["value"])
        # Klasse B: Zaehlwerte sind ganzzahlig. Ein Bruchteil verletzt die
        # Invariante und ist der staerkste Hinweis auf einen Trennzeichenfehler
        # (so sah yun2024:479 mit 1,922 Personen aus).
        if wert != round(wert):
            kandidaten.append(
                {
                    "record_id": record["record_id"],
                    "field": cell["field"],
                    "gold": wert,
                    "verdacht": float(round(wert * 1000)),
                    "klasse": "B: Zaehlwert nicht ganzzahlig",
                    "schreibweise_mit_komma": len(beleg(text, f"{round(wert * 1000):,}")),
                    "schreibweise_ohne_trenner": len(beleg(text, f"{round(wert * 1000)}")),
                    "schreibweise_dezimal": len(re.findall(re.escape(f"{wert:g}"), text)),
                    "beleg_mit_komma": beleg(text, f"{round(wert * 1000):,}")[:2],
                    "beleg_ohne_trenner": beleg(text, f"{round(wert * 1000)}")[:2],
                }
            )
            continue
        if wert >= 1000 or wert < 1:
            continue
        ganz = round(wert * 1000)
        if abs(wert * 1000 - ganz) > 0.01:
            continue
        mit_komma = f"{ganz:,}"
        ohne_trenner = f"{ganz}"
        dezimal = f"{wert:g}"
        komma_stellen = beleg(text, mit_komma)
        zahl_stellen = beleg(text, ohne_trenner)
        if not komma_stellen and not zahl_stellen:
            continue
        kandidaten.append(
            {
                "record_id": record["record_id"],
                "field": cell["field"],
                "gold": wert,
                "verdacht": float(ganz),
                "klasse": "A: Komma-Schreibweise im Text",
                "schreibweise_mit_komma": len(komma_stellen),
                "schreibweise_ohne_trenner": len(zahl_stellen),
                "schreibweise_dezimal": len(re.findall(re.escape(dezimal), text)),
                "beleg_mit_komma": komma_stellen[:2],
                "beleg_ohne_trenner": zahl_stellen[:2],
            }
        )
    return kandidaten


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None, help="Kandidaten hierhin schreiben")
    args = parser.parse_args()

    records = lies(RECORDS)
    texte: dict[str, str] = {}
    alle: list[dict] = []
    for record in records:
        pfad = REPO / (record["document"].get("path") or "")
        text = texte.setdefault(str(pfad), pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else "")
        alle += pruefe(record, text)

    print(f"{len(records)} Records, {sum(len(r['gold']['cells']) for r in records)} Goldzellen geprueft")
    print(f"Kandidaten: {len(alle)}")
    for k in alle:
        print(
            f"  [{k['klasse'][0]}] {k['record_id']:<14} {k['field']:<26} Gold {k['gold']:>8g}"
            f"  Verdacht {k['verdacht']:>6g}  Komma {k['schreibweise_mit_komma']}"
            f" / Zahl {k['schreibweise_ohne_trenner']} / Dezimal {k['schreibweise_dezimal']}"
        )
        for beleg_text in (k["beleg_mit_komma"] or k["beleg_ohne_trenner"])[:1]:
            print(f"      Beleg: …{beleg_text}")

    if args.json:
        args.json.write_text(json.dumps(alle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
