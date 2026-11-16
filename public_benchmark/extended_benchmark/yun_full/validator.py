#!/usr/bin/env python
"""Plausibilitaetspruefungen fuer Modellantworten (nur Warnungen, keine Aenderung).

Zwei Betriebsarten:

* ohne `--gegen-gold`: prueft nur die Modellausgabe (produktionstauglich, kein
  Gold im Zugriff).
* mit `--gegen-gold`: vergleicht die Warnungen mit den Goldzellen und misst,
  wie viele echte Fehler erkannt werden und wie viele Warnungen falsch sind.

Die Pruefungen sind bewusst konservativ: Sie sollen ungewoehnliche, aber korrekte
Studienwerte nicht verwerfen, sondern nur auf Verdacht melden.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
RUNS = BENCH / "runs"
RECORDS = HERE / "records" / "yun699.jsonl"

FELDER = {
    "continuous": [
        "intervention_mean",
        "intervention_standard_deviation",
        "intervention_group_size",
        "comparator_mean",
        "comparator_standard_deviation",
        "comparator_group_size",
    ],
    "binary": [
        "intervention_events",
        "intervention_group_size",
        "comparator_events",
        "comparator_group_size",
    ],
}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def pruefe(record: dict, zellen: list[dict]) -> list[dict]:
    """Liefert Warnungen `{regel, feld, text}` fuer einen Record."""
    typ = record["context"]["outcome_type"]
    werte: dict[str, float] = {}
    doppelt: set[str] = set()
    for zelle in zellen:
        feld = zelle["field"]
        if feld in werte:
            doppelt.add(feld)
        werte.setdefault(feld, zelle["value"])
    warnungen: list[dict] = []

    def melde(regel: str, feld: str, text: str) -> None:
        warnungen.append({"regel": regel, "feld": feld, "text": text})

    for feld in doppelt:
        melde("doppelte_zelle", feld, "Feld mehrfach gemeldet")

    for arm in ("intervention", "comparator"):
        n = werte.get(f"{arm}_group_size")
        e = werte.get(f"{arm}_events")
        m = werte.get(f"{arm}_mean")
        sd = werte.get(f"{arm}_standard_deviation")
        if e is not None and n is not None and e > n:
            melde("events_ueber_n", f"{arm}_events", f"{e:g} Ereignisse bei N={n:g}")
        if m is not None and n is None and typ == "continuous":
            melde("weich:n_fehlt", f"{arm}_group_size", "Mittelwert ohne Gruppengroesse")
        if m is not None and sd is not None:
            if sd <= 0:
                melde("sd_nicht_positiv", f"{arm}_standard_deviation", f"SD={sd:g}")
            elif abs(m) > 0 and sd > 5 * abs(m):
                melde("sd_gegen_mittel", f"{arm}_standard_deviation", f"SD {sd:g} bei Mittelwert {m:g}")
            if 0 < abs(m) < 1 and sd >= 1:
                melde(
                    "anteil_gegen_prozent",
                    f"{arm}_mean",
                    f"Mittelwert {m:g} (Anteil?) mit SD {sd:g} (Prozent?)",
                )
        if e is not None and typ == "continuous":
            melde("ereignisse_bei_kontinuierlich", f"{arm}_events", "Ereigniszahl bei kontinuierlichem Outcome")

    n_i = werte.get("intervention_group_size")
    n_c = werte.get("comparator_group_size")
    if n_i and n_c and max(n_i, n_c) / max(min(n_i, n_c), 1e-9) > 3:
        melde("arme_sehr_ungleich", "intervention_group_size", f"N {n_i:g} gegen {n_c:g}")

    # Vollstaendigkeit ist ohne Gold nicht bewertbar: ein nicht geliefertes Feld
    # kann korrekt sein, weil das Paper es nicht berichtet. Deshalb nur als
    # weicher Hinweis gezaehlt, nicht als Fehlerwarnung.
    for feld in FELDER[typ]:
        if feld.endswith(("mean", "standard_deviation", "events")) and feld not in werte:
            melde("weich:feld_fehlt", feld, "Feld nicht geliefert")
    if not zellen:
        melde("leere_antwort", "", "keine Zelle geliefert")
    return warnungen


HART = {
    "events_ueber_n",
    "doppelte_zelle",
    "sd_nicht_positiv",
    "arme_sehr_ungleich",
    "ereignisse_bei_kontinuierlich",
    "leere_antwort",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--gegen-gold", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = lies(RUNS / args.run / "predictions.jsonl")
    recs = {r["record_id"]: r for r in lies(args.records)}
    je_regel: Counter = Counter()
    warnungen_gesamt: list[dict] = []
    for row in rows:
        record = recs[row["record_id"]]
        for w in pruefe(record, row.get("rows") or []):
            je_regel[w["regel"]] += 1
            warnungen_gesamt.append({**w, "record_id": row["record_id"]})
    harte = [w for w in warnungen_gesamt if w["regel"] in HART]
    weiche = [w for w in warnungen_gesamt if w["regel"] not in HART]

    print(f"{args.run}: {len(rows)} Records, {len(harte)} harte Warnungen, {len(weiche)} weiche Hinweise")
    for regel, anzahl in je_regel.most_common():
        print(f"  {regel:<28} {anzahl}")

    ergebnis = {"run": args.run, "records": len(rows), "warnungen": len(warnungen_gesamt), "je_regel": dict(je_regel)}
    if args.gegen_gold:
        echt = falsch = 0
        erkannt = 0
        falsche_zellen = 0
        for row in rows:
            record = recs[row["record_id"]]
            gold = {c["field"]: c["value"] for c in record["gold"]["cells"]}
            modell: dict[str, float] = {}
            for zelle in row.get("rows") or []:
                modell.setdefault(zelle["field"], zelle["value"])
            warnungen = [w for w in pruefe(record, row.get("rows") or []) if w["regel"] in HART]
            markiert = {w["feld"] for w in warnungen if w["feld"]}
            for feld, wert in gold.items():
                m = modell.get(feld)
                if m is None:
                    continue
                if abs(m - wert) > 1e-9:
                    falsche_zellen += 1
                    if feld in markiert:
                        erkannt += 1
            for feld in markiert:
                if feld in gold and feld in modell and abs(modell[feld] - gold[feld]) > 1e-9:
                    echt += 1
                else:
                    falsch += 1
        ergebnis["gegen_gold"] = {
            "falsche_zellen": falsche_zellen,
            "erkannt": erkannt,
            "quote_erkannt": round(erkannt / falsche_zellen, 4) if falsche_zellen else None,
            "warnungen_auf_echten_fehler": echt,
            "warnungen_ohne_fehler": falsch,
            "praezision": round(echt / (echt + falsch), 4) if (echt + falsch) else None,
        }
        print(
            f"  gegen Gold: {erkannt}/{falsche_zellen} falsche Zellen markiert "
            f"({ergebnis['gegen_gold']['quote_erkannt']}), "
            f"{falsch} Fehlalarme, Praezision {ergebnis['gegen_gold']['praezision']}"
        )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
