#!/usr/bin/env python
"""Abdeckung der 33 leeren P5-Records: P5-Prompt gegen 6.000er-Locator-Fenster.

Fuer jeden Record zwei Ausschnitte, beide offline nachgerechnet:

* **P5**: was der P5-Lauf wirklich gesehen hat. `run_extended_extraction.build_prompt`
  setzt den Text als `text[:limit]` mit `limit=45000` ein, und `main()` liest das
  Dokument vollstaendig - also Anfang des Dokuments, Grenze 45.000 Zeichen.
* **Fenster**: `waehle_ausschnitt(text, stichworte, BREITE=6000, SCHRITT=500)` aus
  `zweistufig_trocken_20261120.py`, das Fenster mit den meisten Outcome-Treffern.

Gemeldet wird je Ausschnitt, wie viele Goldwerte darin gedruckt sind. Das ist die
Tabelle aus `p5_ausschnitt_vergleich_20261120.md`; sie ist mit diesem Skript
nachrechenbar (Spalten `p5_im_prompt` und `im_ausschnitt` im JSON).

Anlass: `baue_fall` meldet `goldwerte_im_volltext`; das ist die Zahl fuer das
ganze Dokument. Wer sie als Ausschnitt-Abdeckung liest, waehlt Records als Probe,
deren Zielwerte im Fenster gar nicht stehen (674). Umgekehrt beschreibt die
Fenster-Abdeckung nicht den P5-Lauf, weil P5 ein anderes Fenster benutzt.

Aufruf:
    .venv/bin/python .../ausschnitt_abdeckung_20261120.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402
from zweistufig_trocken_20261120 import baue_fall  # noqa: E402

MUSTER = HIER / "leere_p5_muster_20261120.json"
AUS = HIER / "ausschnitt_abdeckung_20261120.json"
#: Textgrenze des P5-Prompts (`build_prompt(..., limit=45000)`), keine Schaetzung.
P5_LIMIT = 45000


def main() -> int:
    faelle = json.loads(MUSTER.read_text(encoding="utf-8"))["faelle"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    zeilen = []
    for rid, muster in faelle.items():
        record = records[rid]
        fall = baue_fall(rid, record)
        werte = {round(float(z["value"]), 6) for z in (record.get("gold") or {}).get("cells") or []}

        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        p5_prompt = text[:P5_LIMIT]
        p5_zahlen, _, _ = zahlen_im_text(p5_prompt)
        p5_gefunden = sorted(w for w in werte if p5_zahlen.get(w))

        im_ausschnitt, _, _ = zahlen_im_text(fall["ausschnitt_text"])
        gefunden = sorted(w for w in werte if im_ausschnitt.get(w))
        zeilen.append({
            "record_id": rid,
            "klasse": muster["klasse"],
            "dokument": fall["dokument"],
            "text_zeichen": len(text),
            "goldzellen": len(fall["gold"]),
            "goldwerte": len(werte),
            "im_ausschnitt": len(gefunden),
            "fehlend": sorted(w for w in werte if not im_ausschnitt.get(w)),
            "pipe_zeilen_ausschnitt": sum(1 for z in fall["ausschnitt_text"].splitlines()
                                          if z.count("|") >= 2),
            "p5_prompt_zeichen": len(p5_prompt),
            "p5_gekuerzt": len(text) > P5_LIMIT,
            "p5_im_prompt": len(p5_gefunden),
            "p5_fehlend": sorted(w for w in werte if not p5_zahlen.get(w)),
            "p5_reasoning": muster["reasoning"],
        })
    zeilen.sort(key=lambda z: (-z["im_ausschnitt"], z["record_id"]))
    fair = [z for z in zeilen if z["im_ausschnitt"] == z["goldwerte"] and z["goldwerte"] >= 4]
    p5_voll = [z["record_id"] for z in zeilen if z["p5_im_prompt"] == z["goldwerte"]]
    ergebnis = {
        "quelle": str(MUSTER.relative_to(ROOT.parent)).replace("\\", "/"),
        "n": len(zeilen),
        "ausschnitt_zeichen": 6000,
        "p5_limit": P5_LIMIT,
        "p5_herkunft": "run_extended_extraction.build_prompt(..., limit=45000): text[:limit], "
                       "main() liest das Dokument vollstaendig",
        "faelle": zeilen,
        "fair": [z["record_id"] for z in fair],
        "ohne_vollstaendige_abdeckung": len(zeilen) - len(fair),
        "ohne_jeden_goldwert": sum(1 for z in zeilen if z["im_ausschnitt"] == 0),
        "p5_alle_goldwerte": p5_voll,
        "p5_ohne_vollstaendige_abdeckung": len(zeilen) - len(p5_voll),
        "p5_gekuerzt": sum(1 for z in zeilen if z["p5_gekuerzt"]),
        "p5_und_fenster_verschieden": [z["record_id"] for z in zeilen
                                       if z["p5_im_prompt"] != z["im_ausschnitt"]],
    }
    AUS.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{len(zeilen)} Records; P5 = Anfang des Dokuments bis {P5_LIMIT} Zeichen, "
          f"Fenster = 6.000 Zeichen um die meisten Outcome-Treffer")
    print(f"  {'Record':<14} {'Klasse':<20} {'P5':>7} {'Fenster':>9} {'Dokument':>9}")
    for z in zeilen:
        print(f"  {z['record_id']:<14} {z['klasse']:<20} "
              f"{z['p5_im_prompt']:>4}/{z['goldwerte']:<2} "
              f"{z['im_ausschnitt']:>6}/{z['goldwerte']:<2} "
              f"{z['text_zeichen']:>9}"
              + ("  (P5 gekuerzt)" if z["p5_gekuerzt"] else ""))
    print(f"\nP5: alle Goldwerte im Prompt bei {len(p5_voll)}/{len(zeilen)}; "
          f"ohne vollstaendige Abdeckung {ergebnis['p5_ohne_vollstaendige_abdeckung']}/{len(zeilen)}; "
          f"gekuerzt {ergebnis['p5_gekuerzt']}/{len(zeilen)}")
    print(f"Fenster: alle Goldwerte bei {len(fair)}/{len(zeilen)}; "
          f"ohne vollstaendige Abdeckung {ergebnis['ohne_vollstaendige_abdeckung']}/{len(zeilen)}")
    print(f"Abdeckung P5 != Fenster: {len(ergebnis['p5_und_fenster_verschieden'])}/{len(zeilen)} "
          f"{ergebnis['p5_und_fenster_verschieden']}")
    print(f"\nfaire Proben (alle Goldwerte im Ausschnitt, >=4 Werte): {ergebnis['fair']}")
    print(f"ohne jeden Goldwert im Ausschnitt: {ergebnis['ohne_jeden_goldwert']}/{len(zeilen)}")
    print("geschrieben:", AUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
