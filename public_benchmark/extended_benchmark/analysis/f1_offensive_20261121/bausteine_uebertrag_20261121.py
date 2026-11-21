"""Tragen die Bausteine der 295er-Auswertung auch bei den uebrigen FN-Regeln?

Offline, ohne Netzaufruf. Gemessen werden die drei uebrigen FN-Klassen aus
`fehlerursachen_20261121.json` mit derselben Regelkette wie bei den 295:

* tabellenlokale Groesse (n-Zeile, Zeilen-n),
* Positionsregel (erste Datenspalte = Intervention),
* Wochenspalte (letzter Zeitpunkt),
* Messwort-Block (stiffness, range of motion, neutral zone).

Ausgewiesen wird je Klasse und je Quelle (`zeile`, `position`, `wochenspalte`,
`zielzeile`), wie viele Zellen richtig und falsch sind; zusaetzlich derselbe
Lauf mit abgeschalteter Positionsregel.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(ANALYSE / "f1_offensive_20261121"))

import vergleiche_20261120 as v  # noqa: E402
import zielzeile_alle_20261121 as m  # noqa: E402

KLASSEN = ("fn_leer", "fn_nicht_im_dokument", "fn_nicht_ausgegeben")


def lauf(faelle: list[dict[str, Any]], recs: dict[str, dict[str, Any]],
         texte: dict[str, str]) -> dict[str, Any]:
    res = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True,
                  mean_formate=("mittel_sd", "plus_minus"))
    je_quelle: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"TP": 0, "FP": 0})
    je_feld = collections.Counter()
    for e in res["detail"]:
        quelle = (e["regel"] or {}).get("quelle") or "keine"
        je_quelle[quelle]["TP" if e["richtig"] else "FP"] += 1
        je_feld["mean" if e["feld"].endswith("_mean") else "size"] += 1
    return {"faelle": len(faelle), "zellen": res["geliefert"], "tp": res["tp"],
            "fp": res["fp"], "je_quelle": dict(je_quelle), "je_feld": dict(je_feld)}


def main() -> int:
    daten = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    alle = daten["faelle_fn"]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in alle}}

    ergebnis: dict[str, Any] = {"mit_position": {}, "ohne_position": {}}
    for name, pos in (("mit_position", True), ("ohne_position", False)):
        m.POSITIONAL = pos
        for klasse in KLASSEN:
            faelle = [f for f in alle if f["regel"] == klasse]
            ergebnis[name][klasse] = lauf(faelle, recs, texte)
    m.POSITIONAL = True

    zeilen = ["# Bausteine der 295er-Auswertung bei den uebrigen FN-Regeln", "",
              "Offline, ohne Netzaufruf.", "",
              "## Ergebnis je Klasse", "",
              "| Klasse | Faelle | Zellen | TP | FP | Trefferquote |",
              "|---|---:|---:|---:|---:|---:|"]
    for klasse in KLASSEN:
        e = ergebnis["mit_position"][klasse]
        quote = (100.0 * e["tp"] / e["zellen"]) if e["zellen"] else 0.0
        zeilen.append(f"| `{klasse}` | {e['faelle']} | {e['zellen']} | {e['tp']} | "
                      f"{e['fp']} | {quote:.0f} % |")
    gesamt_tp = sum(ergebnis["mit_position"][k]["tp"] for k in KLASSEN)
    gesamt_fp = sum(ergebnis["mit_position"][k]["fp"] for k in KLASSEN)
    gesamt_z = sum(ergebnis["mit_position"][k]["zellen"] for k in KLASSEN)
    zeilen += ["", f"Zusammen: {gesamt_z} Zellen, {gesamt_tp} TP, {gesamt_fp} FP "
                   f"({100.0 * gesamt_tp / gesamt_z:.0f} % Trefferquote)." if gesamt_z else "",
               "", "## Welcher Baustein liefert", "",
               "| Quelle | TP | FP |", "|---|---:|---:|"]
    summe: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"TP": 0, "FP": 0})
    for klasse in KLASSEN:
        for quelle, wert in ergebnis["mit_position"][klasse]["je_quelle"].items():
            summe[quelle]["TP"] += wert["TP"]
            summe[quelle]["FP"] += wert["FP"]
    for quelle, wert in sorted(summe.items(), key=lambda x: -(x[1]["TP"] + x[1]["FP"])):
        zeilen.append(f"| `{quelle}` | {wert['TP']} | {wert['FP']} |")
    zeilen += ["", "## Mit und ohne Positionsregel", "",
               "| Lauf | Zellen | TP | FP |", "|---|---:|---:|---:|"]
    for name, marke in (("mit_position", "Positionsregel an"), ("ohne_position", "Positionsregel aus")):
        z = sum(ergebnis[name][k]["zellen"] for k in KLASSEN)
        tp = sum(ergebnis[name][k]["tp"] for k in KLASSEN)
        fp = sum(ergebnis[name][k]["fp"] for k in KLASSEN)
        zeilen.append(f"| {marke} | {z} | {tp} | {fp} |")
    zeilen += ["", "## Lesart", "",
               "Die Bausteine tragen hier nicht. Von 464 offenen FN-Faellen liefert die",
               "Kette nur einen kleinen Teil, und davon ist der groesste Teil falsch. Die",
               "Wochenspalte ist der einzige Baustein mit klarem Signal (4 von 4 richtig,",
               "alle in `fn_nicht_ausgegeben`). Die Positionsregel bringt in `fn_leer`",
               "13 falsche gegen 3 richtige Zellen und ist ohne sie sogar einen TP besser.",
               "Der Mittel-Leser aus der Zielzeile liefert in allen drei Klassen fast nur",
               "Fehlgriffe.", "",
               "Das ist plausibel: Die 295er-Faelle sind solche, in denen die Pipeline",
               "einen Wert geliefert hat, der dem Gold widersprach - dort war die Zeile",
               "vorhanden und nur falsch gewaehlt. Die uebrigen FN-Faelle sind ueberwiegend",
               "Faelle ohne lesbare Zelle im Markdown (Tabellenbild, Fliesstext, anderer",
               "Zeitpunkt); bessere Zeilenwahl hilft dort nicht.", ""]
    (HIER / "bausteine_uebertrag_20261121.md").write_text("\n".join(zeilen), encoding="ascii", errors="replace")
    (HIER / "bausteine_uebertrag_20261121.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=True), encoding="utf-8")
    print("Zellen", gesamt_z, "TP", gesamt_tp, "FP", gesamt_fp)
    for quelle, wert in sorted(summe.items(), key=lambda x: -(x[1]["TP"] + x[1]["FP"])):
        print(f"  {quelle:14s} TP {wert['TP']:2d} FP {wert['FP']:2d}")
    for klasse in KLASSEN:
        e = ergebnis["mit_position"][klasse]
        print(f"  {klasse:22s} Faelle {e['faelle']:3d} Z {e['zellen']:2d} TP {e['tp']} FP {e['fp']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
