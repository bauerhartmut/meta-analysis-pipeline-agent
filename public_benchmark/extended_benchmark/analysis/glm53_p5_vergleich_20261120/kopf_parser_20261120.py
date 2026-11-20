"""Regelbasierter Kopf-Parser fuer Gruppengroessen, ohne Modellaufruf.

Struktur, die gelesen wird:

    Positive ABM       Neutral ABM
    Faces (*n* = 16)   Words (*n* = 16)   Faces (*n* = 14)   Words (*n* = 15)

Die Armzeile traegt die Arme, jede Kopfzelle traegt ihre Untergruppe
(`Faces`, `Words`) und ihren Wert. Die Arme werden gleichmaessig auf die
Kopfzellen verteilt, weil die Armnamen ueber ihren Untergruppen zentriert
stehen.

Drei Lesarten stehen zur Verfuegung, damit klar ist, worauf ein F1-Wert beruht:

- `erste_zwei`   : die ersten zwei gedruckten Kopfzellen
- `je_arm`       : die erste Zelle jedes Arms
- `untergruppe`  : je Arm die Untergruppe, die zum Kontextnamen passt
                   (`Word-based` -> `Words`, `Face-based` -> `Faces`)

Aufruf:
    python kopf_parser_20261120.py
    python kopf_parser_20261120.py --ganz --zeigen
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
FELD_RE = re.compile(r"\s{2,}")


def arm_spalten(zeile: str) -> list[tuple[int, str]]:
    """Spaltenlabels der Armzeile mit ihrer Startposition."""
    treffer = [(m.start(), m.group(0).strip())
               for m in re.finditer(r"[A-Za-z][A-Za-z /-]{1,40}?(?=\s{2,}|$)", zeile)
               if m.group(0).strip()]
    return [(p, s) for p, s in treffer if p > 0]


def kopf_parse(text: str, start: int, ende: int) -> dict[str, Any]:
    """Kopfzellen finden und Arm sowie Untergruppe zuordnen."""
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
        return {"gefunden": False, "grund": "keine Zeile mit zwei Kopfzellen", "zellen": []}

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
    felder = [f for f in FELD_RE.split(roh_kopf.strip()) if f.strip()]
    roh_zellen = [f for f in felder if KOPF_RE.search(f)]
    je_arm = len(roh_zellen) // len(spalten) if spalten else 0
    zellen = []
    for i, feld in enumerate(roh_zellen):
        m = KOPF_RE.search(feld)
        untergruppe = feld[:m.start()].strip(" *:|")
        arm = spalten[min(i // je_arm, len(spalten) - 1)][1] if je_arm else ""
        zellen.append({"arm_label": arm, "untergruppe": untergruppe,
                       "wert": float(m.group(1)), "zelle": m.group(0),
                       "pos": zeilen[kopf_zeile][0]})
    return {"gefunden": bool(zellen), "zellen": zellen, "kopfzeile": roh_kopf.strip(),
            "armzeile": zeilen[arm_zeile][1].strip() if arm_zeile is not None else "",
            "zeile_pos": zeilen[kopf_zeile][0]}


def _waehle(zellen: list[dict[str, Any]], arm: str, untergruppe: str) -> float | None:
    for z in zellen:
        if z["arm_label"] == arm and untergruppe and untergruppe in z["untergruppe"].lower():
            return z["wert"]
    return None


def varianten(zellen: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, list[float]]:
    """Drei Lesarten der Kopfzellen als [Intervention, Komparator]."""
    werte = [z["wert"] for z in zellen]
    raus: dict[str, list[float]] = {}
    if len(werte) >= 2:
        raus["erste_zwei"] = werte[:2]

    arme = []
    for z in zellen:
        if z["arm_label"] not in arme:
            arme.append(z["arm_label"])
    if len(arme) >= 2:
        je = []
        for arm in arme[:2]:
            je.append(next(z["wert"] for z in zellen if z["arm_label"] == arm))
        raus["je_arm"] = je

        iv = str(context.get("intervention") or "").lower()
        cv = str(context.get("comparator") or "").lower()
        ug_i = "words" if "word" in iv else ("faces" if "face" in iv else "")
        ug_c = "faces" if "face" in cv else ("words" if "word" in cv else "")
        wi = _waehle(zellen, arme[0], ug_i)
        wc = _waehle(zellen, arme[1], ug_c)
        if wi is not None and wc is not None:
            raus["untergruppe"] = [wi, wc]
    return raus


def gold_groessen(fall: dict[str, Any]) -> dict[str, float]:
    raus = {}
    for z in (fall.get("gold") or {}).get("cells") or []:
        if z.get("field") in ("intervention_group_size", "comparator_group_size"):
            raus[z["field"]] = float(z["value"])
    return raus


def f1_von(werte: list[float], gold: dict[str, float]) -> dict[str, Any]:
    """Beide Armordnungen pruefen, beste melden."""
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
    ap.add_argument("--ganz", action="store_true",
                    help="ganzen Dokumenttext durchsuchen statt nur Tabellenstueck")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    raus = []
    for rid in args.records:
        record = records[rid]
        text = (k.ROOT / (record.get("document") or {}).get("path", "")).read_text(
            encoding="utf-8", errors="replace")
        stuecke = k.erweitere(text, k.waehle_stuecke(text, k.worte_von(record)))
        start, ende, _ = (0, len(text), "") if args.ganz else stuecke[-1]
        kopf = kopf_parse(text, start, ende)
        gold = gold_groessen({"gold": record.get("gold") or {}})
        eintrag: dict[str, Any] = {"record_id": rid, "gold": gold,
                                   "kopfzeile": kopf.get("kopfzeile", ""),
                                   "armzeile": kopf.get("armzeile", ""),
                                   "zellen": kopf.get("zellen", []),
                                   "varianten": {}}
        for name, werte in varianten(kopf.get("zellen", []),
                                     record.get("context") or {}).items():
            eintrag["varianten"][name] = {"werte": werte, **f1_von(werte, gold)}
        raus.append(eintrag)
        zellen_txt = [(z["arm_label"], z["untergruppe"], z["wert"])
                      for z in eintrag["zellen"]]
        print(f"{rid}: Zellen {zellen_txt} | Gold {gold}")
        for name, daten in eintrag["varianten"].items():
            print(f"   {name:11s} {daten['werte']} -> TP {daten['tp']} FP {daten['fp']} "
                  f"FN {daten['fn']} F1 {daten['f1']} ({daten['ordnung']})")
        if args.zeigen:
            print(f"   Armzeile : {eintrag['armzeile']!r}")
            print(f"   Kopfzeile: {eintrag['kopfzeile']!r}")

    if args.json:
        Path(args.json).write_text(json.dumps(raus, indent=2, ensure_ascii=True),
                                   encoding="utf-8")
    mit = sum(1 for e in raus if e["varianten"].get("erste_zwei", {}).get("f1") == 1.0)
    print(f"F1 = 1.0 (erste_zwei) bei {mit} von {len(raus)} Records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
