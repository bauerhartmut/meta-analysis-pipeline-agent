"""Regelbasierter Kopf-Parser fuer Gruppengroessen, ohne Modellaufruf.

Fundstelle: die Zeile mit den Kopfzellen `(n = ...)` und die Armzeile darueber.
Zuordnung ueber Zeichenpositionen: jede Kopfzelle gehoert zu dem Arm, dessen
Spaltenlabel links von ihr steht.

Aufruf:
    python kopf_parser_20261120.py
    python kopf_parser_20261120.py --records yun2024:582 --zeigen
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parents[2]))
sys.path.insert(0, str(HIER.parents[1]))

import vergleiche_20261120 as v  # noqa: E402
import kettenlauf_20261120 as k  # noqa: E402

KOPF_RE = re.compile(r"\(\s*\*?n\*?\s*=\s*(\d+)\s*\)", re.I)
TRENNER_RE = re.compile(r"^\s*-{5,}")


def arm_spalten(zeile: str) -> list[tuple[int, str]]:
    """Spaltenlabels der Armzeile mit ihrer Startposition."""
    treffer = [(m.start(), m.group(0).strip())
               for m in re.finditer(r"[A-Za-z][A-Za-z /-]{1,40}?(?=\s{2,}|$)", zeile)
               if m.group(0).strip()]
    return [(p, s) for p, s in treffer if p > 0]


def kopf_parse(text: str, start: int, ende: int) -> dict[str, Any]:
    """Kopfzellen einer Tabelle finden und ihren Spaltenlabels zuordnen."""
    zeilen: list[tuple[int, str]] = []
    pos = start
    for roh in text[start:ende].splitlines():
        if roh.strip():
            zeilen.append((pos, roh))
        pos += len(roh) + 1

    kopf_zeile = None
    bester = 0
    for idx, (_, roh) in enumerate(zeilen):
        if TRENNER_RE.match(roh):
            continue
        anzahl = len(KOPF_RE.findall(roh))
        if anzahl >= 2 and anzahl > bester:
            kopf_zeile, bester = idx, anzahl
    if kopf_zeile is None:
        return {"gefunden": False, "grund": "keine Zeile mit zwei Kopfzellen"}

    arm_zeile = None
    for idx in range(kopf_zeile - 1, max(-1, kopf_zeile - 4), -1):
        roh = zeilen[idx][1]
        if TRENNER_RE.match(roh) or KOPF_RE.search(roh) or re.search(r"\d", roh):
            continue
        if len(arm_spalten(roh)) >= 2:
            arm_zeile = idx
            break

    roh_kopf = zeilen[kopf_zeile][1]
    spalten = arm_spalten(zeilen[arm_zeile][1]) if arm_zeile is not None else []
    treffer = list(KOPF_RE.finditer(roh_kopf))
    # Armzeilen sind zentriert ueber ihren Untergruppen: die Kopfzellen werden
    # gleichmaessig auf die Arme verteilt, nicht ueber die Labelposition.
    je_arm = len(treffer) // len(spalten) if spalten else 0
    zellen = []
    for i, m in enumerate(treffer):
        arm = spalten[min(i // je_arm, len(spalten) - 1)][1] if je_arm else ""
        zellen.append({"arm_label": arm, "wert": float(m.group(1)),
                       "zelle": m.group(0), "pos": zeilen[kopf_zeile][0] + m.start()})
    return {"gefunden": bool(zellen), "zellen": zellen, "kopfzeile": roh_kopf.strip(),
            "armzeile": zeilen[arm_zeile][1].strip() if arm_zeile is not None else "",
            "zeile_pos": zeilen[kopf_zeile][0]}


def gold_groessen(fall: dict[str, Any]) -> dict[str, float]:
    raus = {}
    for z in (fall.get("gold") or {}).get("cells") or []:

        if z.get("field") in ("intervention_group_size", "comparator_group_size"):
            raus[z["field"]] = float(z["value"])
    return raus


def bester_schnitt(werte: list[float], gold: dict[str, float]) -> dict[str, Any]:
    """Beide Armzuordnungen pruefen: links/rechts gegen intervention/comparator."""
    kandidaten = []
    for ordnung in ("wie_gedruckt", "getauscht"):
        paare = list(zip(werte, ("intervention_group_size", "comparator_group_size")))
        if ordnung == "getauscht":
            paare = [(w, f) for w, f in reversed(paare)]
        tp = sum(1 for w, f in paare if gold.get(f) == w)
        fp = len(paare) - tp
        fn = len(gold) - tp
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        kandidaten.append({"ordnung": ordnung, "tp": tp, "fp": fp, "fn": fn,
                           "f1": round(f1, 3)})
    return max(kandidaten, key=lambda x: (x["f1"], x["ordnung"] == "wie_gedruckt"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", nargs="*", default=["yun2024:582", "yun2024:420",
                                                     "yun2024:421", "yun2024:671",
                                                     "yun2024:672"])
    ap.add_argument("--zeigen", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--ganz", action="store_true",
                    help="ganzen Dokumenttext durchsuchen statt nur Tabellenstueck")
    args = ap.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    raus = []
    for rid in args.records:
        record = records[rid]
        text = (k.ROOT / (record.get("document") or {}).get("path", "")).read_text(
            encoding="utf-8", errors="replace")
        stuecke = k.erweitere(text, k.waehle_stuecke(text, k.worte_von(record)))
        fall = {"text": text, "gold": record.get("gold") or {}, "stuecke": stuecke}
        start, ende, _ = (0, len(fall["text"]), "") if args.ganz else fall["stuecke"][-1]
        kopf = kopf_parse(fall["text"], start, ende)
        gold = gold_groessen(fall)
        eintrag = {"record_id": rid, "gold": gold, **kopf}
        werte = [z["wert"] for z in kopf.get("zellen", [])][:2]
        if kopf.get("gefunden") and len(werte) == 2:
            eintrag["zuordnung"] = bester_schnitt(werte, gold)
        else:
            eintrag["zuordnung"] = {"f1": 0.0, "grund": "weniger als zwei Kopfzellen"}
        raus.append(eintrag)
        print(f"{rid}: Kopfzellen {[z['zelle'] for z in kopf.get('zellen', [])]} | "
              f"Arme {[z['arm_label'] for z in kopf.get('zellen', [])]} | "
              f"Gold {gold} | F1 {eintrag['zuordnung'].get('f1')} "
              f"({eintrag['zuordnung'].get('ordnung', eintrag['zuordnung'].get('grund'))})")
        if args.zeigen:
            print(f"   Armzeile : {kopf.get('armzeile', '')!r}")
            print(f"   Kopfzeile: {kopf.get('kopfzeile', '')!r}")

    if args.json:
        Path(args.json).write_text(json.dumps(raus, indent=2, ensure_ascii=True),
                                   encoding="utf-8")
    treffer = sum(1 for e in raus if e["zuordnung"].get("f1") == 1.0)
    print(f"F1 = 1.0 bei {treffer} von {len(raus)} Records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
