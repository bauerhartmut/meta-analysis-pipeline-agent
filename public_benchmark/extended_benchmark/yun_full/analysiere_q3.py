"""Was unterscheidet die Length-Ausfaelle im Abschnitt Q3 von den Erfolgen dort?

Vergleicht innerhalb eines Record-Bereichs die Records mit
`length_ohne_ergebnis` gegen die erfolgreichen: Textlaenge, Tabellendichte,
Spaltenzahl, Zellenzahl, Outcome-Typ und eine grobe Themenzuordnung.

Das Fachgebiet ist im Datensatz NICHT annotiert. Die Themenzuordnung ist eine
Stichwort-Heuristik auf dem Dokumenttext und darf hoechstens als Hinweis
gelesen werden, nicht als Messung.

Aufruf:
    python analysiere_q3.py --run yun699_8000_alle_20261117 --von 109 --bis 162
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent          # extended_benchmark
REPO = HERE.parents[2]       # Projektwurzel: yun_full -> extended_benchmark -> public_benchmark -> Repo
RUNS = BENCH / "runs"
STANDARD_RECORDS = HERE / "records" / "yun699.jsonl"

THEMEN = {
    "Ernaehrung": ["nutrition", "diet", "food", "snack", "calorie", "obesity", "weight"],
    "Psyche": ["depress", "anxiety", "mental", "stress", "psycholog", "cbt", "counsel"],
    "Schmerz": ["pain", "analges", "opioid", "morphine"],
    "Kardiovaskulaer": ["cardiovascular", "blood pressure", "hypertens", "myocardial", "statin"],
    "Onkologie": ["cancer", "tumor", "chemotherapy", "oncolog"],
    "Infektion": ["infection", "vaccin", "antibiotic", "covid", "hiv"],
    "Bewegung": ["exercise", "physical activity", "walking", "training"],
    "Diabetes": ["diabetes", "glycemic", "insulin", "hba1c"],
    "Atemwege": ["asthma", "copd", "respiratory", "smoking"],
    "Paediatrie": ["child", "infant", "pediatric", "adolescent"],
}


def lies(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def merkmale(text: str) -> dict[str, float]:
    zeilen = [z for z in text.splitlines() if z.strip()]
    tabellen = [z for z in zeilen if z.count("|") >= 2]
    spalten = max((z.count("|") - 1 for z in tabellen), default=0)
    return {
        "text_chars": float(len(text)),
        "zeilen": float(len(zeilen)),
        "tabellenzeilen": float(len(tabellen)),
        "tabellenanteil": len(tabellen) / len(zeilen) if zeilen else 0.0,
        "max_spalten": float(spalten),
        "zahlenzeilen": float(sum(1 for z in zeilen if re.search(r"\d", z))),
        "woerter": float(len(text.split())),
    }


def thema(text: str) -> str:
    klein = text.lower()
    treffer = {name: sum(klein.count(w) for w in worte) for name, worte in THEMEN.items()}
    bestes = max(treffer, key=treffer.get)
    return bestes if treffer[bestes] >= 3 else "unklar"


def kennzahlen(werte: list[float], einheit: str = "") -> str:
    if not werte:
        return "-"
    return f"{statistics.median(werte):.0f}{einheit} (n={len(werte)})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--records", type=Path, default=STANDARD_RECORDS)
    ap.add_argument("--modell", default="glm")
    ap.add_argument("--von", type=int, required=True, help="erste laufende Nummer, z. B. 109")
    ap.add_argument("--bis", type=int, required=True, help="letzte laufende Nummer, z. B. 162")
    args = ap.parse_args()

    records = lies(args.records)
    rows = [r for r in lies(RUNS / args.run / "predictions.jsonl") if r["model"] == args.modell]
    nach_id = {r["record_id"]: r for r in rows}

    ausfall, erfolg, fehlt = [], [], []
    for nummer in range(args.von, args.bis + 1):
        rid = f"yun2024:{nummer}"
        record = next((r for r in records if r["record_id"] == rid), None)
        if record is None:
            continue
        row = nach_id.get(rid)
        if row is None:
            fehlt.append(rid)
            continue
        if row["fehlerklasse"] == "length_ohne_ergebnis":
            ausfall.append(record)
        elif not row["failed"]:
            erfolg.append(record)

    print(f"Abschnitt yun2024:{args.von}..{args.bis} ({args.modell}): "
          f"{len(ausfall)} Ausfaelle, {len(erfolg)} Erfolge, {len(fehlt)} noch nicht gelaufen")

    daten: dict[str, list[dict]] = {"Ausfall": [], "Erfolg": []}
    for name, gruppe in (("Ausfall", ausfall), ("Erfolg", erfolg)):
        for record in gruppe:
            datei = REPO / record["document"]["path"]
            text = datei.read_text(encoding="utf-8", errors="replace") if datei.exists() else ""
            m = merkmale(text)
            m["gold_zellen"] = float(len((record.get("gold") or {}).get("cells") or []))
            m["thema"] = thema(text)
            m["record_id"] = record["record_id"]
            m["outcome_type"] = (record.get("context") or {}).get("outcome_type") or "?"
            daten[name].append(m)

    print(f"\n{'Merkmal':18} {'Ausfall':>22} {'Erfolg':>22}")
    for feld in ("text_chars", "woerter", "zeilen", "tabellenzeilen", "zahlenzeilen",
                 "max_spalten", "gold_zellen"):
        a = [d[feld] for d in daten["Ausfall"]]
        e = [d[feld] for d in daten["Erfolg"]]
        print(f"{feld:18} {kennzahlen(a):>22} {kennzahlen(e):>22}")
    anteil_a = [d["tabellenanteil"] for d in daten["Ausfall"]]
    anteil_e = [d["tabellenanteil"] for d in daten["Erfolg"]]
    med_a = statistics.median(anteil_a) * 100 if anteil_a else 0.0
    med_e = statistics.median(anteil_e) * 100 if anteil_e else 0.0
    print(f"{'Tabellenanteil':18} {med_a:20.1f} % {med_e:20.1f} %")
    print()
    for name in ("Ausfall", "Erfolg"):
        typen = collections.Counter(d["outcome_type"] for d in daten[name])
        print(f"{name:8} Outcome-Typen: {dict(typen)}")
    print()
    for name in ("Ausfall", "Erfolg"):
        themen = collections.Counter(d["thema"] for d in daten[name])
        print(f"{name:8} Themen (Heuristik): {themen.most_common()}")
    # Scheitern Records dokumentweise oder einzeln? Wenn innerhalb desselben
    # Dokuments manche Arme scheitern und andere nicht, kann die Textlaenge die
    # Ursache nicht sein - der Text ist fuer alle Records desselben Dokuments gleich.
    nach_dok: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for name, gruppe in (("Ausfall", ausfall), ("Erfolg", erfolg)):
        for record in gruppe:
            nach_dok[record["document"]["id"]].append((record["record_id"], name))
    gemischt = {d: v for d, v in nach_dok.items() if len({n for _, n in v}) > 1}
    print(f"\nDokumente im Abschnitt: {len(nach_dok)}")
    print(f"  gemischt (teils Ausfall, teils Erfolg): {len(gemischt)} Dokumente, "
          f"{sum(len(v) for v in gemischt.values())} Records")
    for dok, eintraege in sorted(gemischt.items(), key=lambda x: -len(x[1]))[:5]:
        faelle = sum(1 for _, n in eintraege if n == "Ausfall")
        print(f"    {dok}: {faelle} von {len(eintraege)} Ausfall")

    # Reproduzierbarkeit: Laufen dieselben Records in frueheren Laeufen anders
    # aus? Ein Record, der frueher mit gleichen Bedingungen durchlief und jetzt
    # in length laeuft, ist ein Fall von Nichtdeterminismus, keine
    # Record-Eigenschaft.
    abschnitt = {r["record_id"] for r in ausfall + erfolg}
    frueher: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for pfad in RUNS.glob("*/predictions.jsonl"):
        if pfad.parent.name == args.run:
            continue
        for row in lies(pfad):
            if row.get("model") != args.modell:
                continue
            if row.get("record_id") not in abschnitt:
                continue
            ergebnis = row.get("fehlerklasse") or ("leer" if not row.get("rows") else "ok")
            frueher[row["record_id"]][pfad.parent.name] = ergebnis

    jetzt_ausfall = {r["record_id"] for r in ausfall}
    umstritten = [
        rid for rid, laeufe in frueher.items()
        if "ok" in laeufe.values()
        and (rid in jetzt_ausfall or "length_ohne_ergebnis" in laeufe.values())
    ]
    print(f"\nReproduzierbarkeit: {len(frueher)} Records des Abschnitts kommen in "
          f"frueheren Laeufen vor")
    print(f"  mit gemischten Ergebnissen (einmal ok, einmal length): {len(umstritten)}")
    stabil = [rid for rid in jetzt_ausfall
              if frueher.get(rid) and all(v == "length_ohne_ergebnis" for v in frueher[rid].values())]
    print(f"  Ausfaelle, die in ALLEN frueheren Laeufen ebenfalls Ausfall waren: {len(stabil)}")

    print("\nEinzelrecords:")
    for name in ("Ausfall", "Erfolg"):
        for d in daten[name][:6]:
            print(f"  {name:8} {d['record_id']:>12} text={d['text_chars']:6.0f} "
                  f"tab={d['tabellenzeilen']:3.0f} spalten={d['max_spalten']:2.0f} "
                  f"zellen={d['gold_zellen']:2.0f} {d['outcome_type']:10} {d['thema']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
