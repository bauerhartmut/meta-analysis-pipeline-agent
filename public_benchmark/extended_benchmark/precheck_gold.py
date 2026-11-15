"""Gold-Vorpruefung ohne Modellaufrufe.

Zwei Muster, die im Dev-Satz nur durch Textvergleich auffielen:

1. **Doppelangabe** — derselbe Sachverhalt steht an zwei Stellen mit
   unterschiedlichen Zahlen (PMC1216327: 50,7/-0,7 in der Kurzfassung gegen
   50,6/-7,0 im Ergebnisteil).
2. **Standort statt Arm** — eine als Gruppengroesse annotierte Zahl ist im
   Artikel eine Standort- oder Zentrumszahl (PMC3580751: 940/1831 sind
   "unit A"/"unit B", nicht die Studienarme).

Erkennung ohne Sprachmodell:

* Doppelangabe: zwei Zahlen an weit auseinanderliegenden Stellen, die sich nur
  in einer Nachkommastelle oder um Faktor 10 unterscheiden ("fast dieselbe
  Zahl"), und deren Saetze ein gemeinsames Ankerwort tragen (Einheit oder
  Outcome-Begriff). Ein Satzvergleich ueber Wortgleichheit scheitert hier, weil
  Abstract und Ergebnisteil denselben Wert anders formulieren.
* Standortzahl: die Zahl steht in einem Satz mit Standortbezug in der Naehe
  ("hospitalised in unit A", "940 (34 %)") und das Ankerwort steht hoechstens
  80 Zeichen entfernt.

Das Werkzeug liest nur; es schreibt weder Gold noch Predictions und ruft kein
Modell auf.

Aufruf:
    python public_benchmark/extended_benchmark/precheck_gold.py \
        --out public_benchmark/extended_benchmark/analysis/gold_precheck_20261115
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECORDS = HERE / "records" / "yun.jsonl"

STANDORT = re.compile(
    r"\b(?:unit|centre|center|site|hospital|ward|clinic|department|institute|location)s?\b",
    re.IGNORECASE,
)
ORTSPHASE = re.compile(
    r"\b(?:in|at|from|across|to)\s+(?:the\s+)?(?:\w+\s+){0,3}"
    r"(?:unit|centre|center|hospital|site|ward|clinic|department|institute|location)\b",
    re.IGNORECASE,
)
BEREICH = re.compile(r"##\s+(Results|Methods|Materials and Methods|Patients and Methods)\b")
ZAHL = re.compile(r"(?<![\w.])-?\s?\d+(?:[.,]\d+)?")


def saetze(text: str) -> list[tuple[int, str]]:
    """Satzliste mit Startposition."""
    out: list[tuple[int, str]] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+", text):
        teil = text[start : match.start()]
        if teil.strip():
            out.append((start, teil.strip()))
        start = match.end()
    if text[start:].strip():
        out.append((start, text[start:].strip()))
    return out


def zahlen_mit_position(satz: str) -> list[tuple[int, float, bool]]:
    """Zahlen mit Position und der Angabe, ob sie mit Dezimalstelle stehen."""
    werte = []
    for treffer in ZAHL.finditer(satz):
        roh = treffer.group(0).replace(" ", "").replace(",", ".")
        try:
            werte.append((treffer.start(), float(roh), "." in roh))
        except ValueError:
            continue
    return werte


def teile(text: str) -> int | None:
    """Position, an der der Hauptteil beginnt (Ende der Kurzfassung)."""
    treffer = BEREICH.search(text)
    return treffer.start() if treffer else None


def region(position: int, grenze: int | None) -> str:
    if grenze is None:
        return "unbestimmt"
    return "Kurzfassung" if position < grenze else "Hauptteil"


def beziehung(a: float, b: float, *, dezimal_a: bool = True, dezimal_b: bool = True) -> str:
    """Zwei Schreibweisen derselben Zahl?

    Eng gefasst, weil sonst jedes Zahlenpaar eines Artikels passt: beide Zahlen
    muessen mit Dezimalstelle geschrieben sein ("7.0" zaehlt als Dezimalzahl,
    auch wenn der Wert ganzzahlig ist), Nachkommastelle heisst hoechstens 0,5
    Prozent Abstand, Zehnerstelle heisst exakter Faktor 10.
    """
    if not (dezimal_a and dezimal_b) or a == b or a == 0 or b == 0:
        return ""
    if abs(abs(a) / abs(b) - 10) < 0.005 or abs(abs(b) / abs(a) - 10) < 0.005:
        return "Faktor 10 (Zehnerstelle)"
    if abs(a - b) <= 0.005 * max(abs(a), abs(b)):
        return "Nachkommastelle"
    return ""


def ist_prosa(satz: str) -> bool:
    """Tabellenblaetter ausschliessen: dort stehen zu viele Zahlen dicht."""
    if "|" in satz or "::::" in satz or "table-wrap" in satz or "caption" in satz:
        return False
    if satz.count("\n") > 2:
        return False
    return len(zahlen_mit_position(satz)) <= 6


def zahlpaare(
    text: str,
    outcome: str,
    cells: list[dict[str, Any]],
    *,
    mindestabstand: int = 1000,
    nur_prosa: bool = True,
    braucht_outcome: bool = True,
) -> list[dict[str, Any]]:
    """Gold-Wert und fast gleiche Zahl an anderer Stelle, beide beim Outcome.

    Verankert an den Goldzellen statt an allen Zahlen eines Artikels: gesucht
    wird eine zweite Schreibweise des annotierten Werts (Nachkommastelle oder
    Faktor 10) in einem Satz mit demselben Outcome-Begriff.

    Die Stufe ist einstellbar (`nur_prosa`, `braucht_outcome`,
    `mindestabstand`). Die gelockerte Stufe dient nur der Messung, ob ein
    Nullergebnis an der Regel oder an den Daten liegt; als Befund zaehlt sie
    nicht.
    """
    grenze = teile(text)
    begriffe = [w for w in re.findall(r"[a-z]{5,}", outcome.lower())]
    if braucht_outcome and not begriffe:
        return []
    prosa = [
        (pos, satz, zahlen_mit_position(satz))
        for pos, satz in saetze(text)
        if (ist_prosa(satz) or not nur_prosa)
        and (not braucht_outcome or any(w in satz.lower() for w in begriffe))
    ]
    treffer: list[dict[str, Any]] = []
    for cell in cells:
        gold = float(cell["value"])
        for pos_a, satz_a, zahlen_a in prosa:
            for _, wert_a, dez_a in zahlen_a:
                if wert_a != gold or not dez_a:
                    continue
                for pos_b, satz_b, zahlen_b in prosa:
                    if abs(pos_b - pos_a) < mindestabstand:
                        continue
                    for _, wert_b, dez_b in zahlen_b:
                        art = beziehung(gold, wert_b, dezimal_a=dez_a, dezimal_b=dez_b)
                        if not art:
                            continue
                        gemeinsam = sorted(
                            ({w for w in begriffe if w in satz_a.lower()}
                             & {w for w in begriffe if w in satz_b.lower()})
                        )
                        if braucht_outcome and not gemeinsam:
                            continue
                        treffer.append(
                            {
                                "art": "doppelangabe",
                                "beziehung": art,
                                "field": cell["field"],
                                "arm": cell.get("arm"),
                                "gold": gold,
                                "wert_a": wert_a,
                                "wert_b": wert_b,
                                "anker": gemeinsam,
                                "position_a": pos_a,
                                "position_b": pos_b,
                                "abstand": pos_b - pos_a,
                                "region_a": region(pos_a, grenze),
                                "region_b": region(pos_b, grenze),
                                "satz_a": satz_a[:400],
                                "satz_b": satz_b[:400],
                            }
                        )
    gesehen: set[tuple[float, float, int, int]] = set()
    eindeutig = []
    for eintrag in treffer:
        schluessel = (eintrag["wert_a"], eintrag["wert_b"], eintrag["position_a"], eintrag["position_b"])
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        eindeutig.append(eintrag)
    eindeutig.sort(key=lambda t: (-t["abstand"], t["position_a"]))
    return eindeutig


def standortzahlen(text: str, cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gruppengroessen, deren Zahl im Artikel eine Standortzahl ist."""
    treffer: list[dict[str, Any]] = []
    for cell in cells:
        if not cell["field"].endswith("group_size"):
            continue
        wert = cell["value"]
        roh = f"{wert:.0f}" if float(wert).is_integer() else f"{wert}"
        muster = re.compile(rf"(?<![\d.,]){re.escape(roh)}(?![\d.,])")
        for pos, satz in saetze(text):
            treffer_zahl = muster.search(satz)
            if not treffer_zahl or not ist_prosa(satz):
                continue
            umgebung = satz[max(0, treffer_zahl.start() - 80) : treffer_zahl.end() + 80]
            # Nur eine Ortsangabe, die an die Zahl gebunden ist, zaehlt:
            # "hospitalised in unit A" oder eine Prozentangabe direkt danach.
            ort = ORTSPHASE.search(umgebung)
            if ort and "[" in umgebung[:30]:
                # Tabellenspalte "unit" ist keine Ortsangabe.
                ort = None
            prozent = re.match(r"\s*\(?\d{1,3}(?:\.\d+)?\s?%", satz[treffer_zahl.end() : treffer_zahl.end() + 12])
            if not ort and not (prozent and STANDORT.search(umgebung)):
                continue
            treffer.append(
                {
                    "art": "standortzahl",
                    "field": cell["field"],
                    "arm": cell.get("arm"),
                    "gold": wert,
                    "position": pos,
                    "ortswort": (STANDORT.search(umgebung) or ORTSPHASE.search(umgebung)).group(0),
                    "satz": satz[:400],
                }
            )
            break
    return treffer


def pruefe_record(record: dict[str, Any], *, weit: str = "eng") -> list[dict[str, Any]]:
    pfad = REPO / (record["document"].get("path") or "")
    if not pfad.exists():
        return []
    text = pfad.read_text(encoding="utf-8", errors="replace")
    outcome = (record.get("context") or {}).get("outcome", "")
    cells = record["gold"]["cells"]
    kopf = {
        "record_id": record["record_id"],
        "document": record["document"]["id"],
        "outcome": outcome,
        "gold_zellen": "; ".join(
            f"{c['field']}={c['value']:g}" for c in cells
        ),
    }
    if weit == "weit":
        paare = zahlpaare(
            text, outcome, cells, mindestabstand=0, nur_prosa=False, braucht_outcome=False
        )
    elif weit == "mittel":
        paare = zahlpaare(text, outcome, cells, mindestabstand=0)
    else:
        paare = zahlpaare(text, outcome, cells)
    ereignisse = [{**kopf, **t} for t in paare]
    ereignisse += [{**kopf, **t} for t in standortzahlen(text, cells)]
    return ereignisse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=RECORDS)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--nur-split", default="", help="nur Records dieses Splits pruefen")
    parser.add_argument("--ohne-split", default="dev", help="Records dieses Splits auslassen")
    parser.add_argument(
        "--stufe",
        choices=("eng", "mittel", "weit"),
        default="eng",
        help=(
            "eng = Befundstufe; mittel = ohne Abstandsfilter; weit = ohne Prosa-, "
            "Outcome- und Abstandsfilter (mittel/weit nur zur Messung)"
        ),
    )
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

    alle: list[dict[str, Any]] = []
    for record in records:
        alle.extend(pruefe_record(record, weit=args.stufe))
    if args.stufe != "eng":
        gesehen: set[tuple[Any, ...]] = set()
        gefiltert = []
        for eintrag in alle:
            schluessel = (eintrag["record_id"], eintrag.get("field"), eintrag.get("arm"), eintrag.get("wert_b"))
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            gefiltert.append(eintrag)
        alle = gefiltert

    args.out.mkdir(parents=True, exist_ok=True)
    felder = [
        "art", "record_id", "document", "outcome", "gold_zellen", "beziehung",
        "wert_a", "wert_b", "anker", "region_a", "region_b", "abstand",
        "position_a", "position_b", "field", "arm", "gold", "ortswort",
        "satz_a", "satz_b", "satz",
    ]
    with (args.out / "hits.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=felder, extrasaction="ignore")
        writer.writeheader()
        for eintrag in alle:
            zeile = {**eintrag}
            for schluessel in ("anker",):
                if schluessel in zeile:
                    zeile[schluessel] = "|".join(zeile[schluessel])
            writer.writerow(zeile)
    (args.out / "summary.json").write_text(
        json.dumps(
            {
                "records_geprueft": len(records),
                "stufe": args.stufe,
                "treffer": len(alle),
                "doppelangaben": sum(1 for e in alle if e["art"] == "doppelangabe"),
                "standortzahlen": sum(1 for e in alle if e["art"] == "standortzahl"),
                "records_mit_treffer": len({e["record_id"] for e in alle}),
                "dokumente_mit_treffer": len({e["document"] for e in alle}),
                "module_aufrufe": 0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"geprueft: {len(records)} Records, Treffer: {len(alle)} "
        f"({sum(1 for e in alle if e['art'] == 'doppelangabe')} Doppelangaben, "
        f"{sum(1 for e in alle if e['art'] == 'standortzahl')} Standortzahlen) "
        f"in {len({e['document'] for e in alle})} Dokumenten"
    )
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
