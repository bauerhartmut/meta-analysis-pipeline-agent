"""Satzauswahl der Stufe 1 offline pruefen, ohne Aufruf.

Liest alle gespeicherten Stufe-1-Antworten im Laufverzeichnis und im
Kettenlauf, nimmt die Locators mit nicht leerem `satz` und prueft je Fall:

- traegt der gebundene Satz Goldwerte (`richtig`),
- lag im Ausschnitt ueberhaupt ein Satz mit Goldwerten (`falsch, richtiger
  Satz lag vor` oder `falsch, kein richtiger Satz im Ausschnitt`).

Aufruf:
    python satzauswahl_20261120.py
    python satzauswahl_20261120.py --json satzauswahl_20261120.json
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

LAUF = HIER / "zweistufig_lauf_20261120"
KETTE = LAUF / "predictions_kette_stichprobe_20261120.jsonl"
SATZ_ENDE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
STOPP = {"quantitative", "assessment", "comparison", "primary", "reported", "between",
         "versus", "versus", "effect", "effects", "change", "changes", "baseline",
         "significant", "significantly", "values", "value", "using", "after", "before"}


def unterscheider(context: dict[str, Any]) -> list[str]:
    """Woerter, die das Outcome dieses Records von Nachbar-Records trennen."""
    worte = re.findall(r"[A-Za-z][A-Za-z-]{5,}", str(context.get("outcome") or ""))
    return [w for w in worte if w.lower() not in STOPP]


def saetze(text: str) -> list[str]:
    return [s.strip() for s in SATZ_ENDE.split(text) if s.strip()]


def zahlen(satz: str) -> set[float]:
    raus = set()
    for m in re.finditer(r"\d+(?:[.,]\d+)?", satz):
        try:
            raus.add(round(float(m.group(0).replace(",", ".")), 6))
        except ValueError:
            continue
    return raus


def locators_von(zeile: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(zeile.get("locators"), list):
        return zeile["locators"]
    stufe1 = zeile.get("stufe1") or {}
    if isinstance(stufe1.get("locators"), list):
        return stufe1["locators"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte: dict[str, str] = {}
    quellen = sorted(LAUF.glob("*.jsonl"))
    if KETTE.exists() and KETTE not in quellen:
        quellen.append(KETTE)

    faelle: list[dict[str, Any]] = []
    for pfad in quellen:
        for roh in pfad.read_text(encoding="utf-8").splitlines():
            if not roh.strip():
                continue
            zeile = json.loads(roh)
            rid = zeile.get("record_id")
            if not rid or rid not in records:
                continue
            if rid not in texte:
                texte[rid] = (k.ROOT / (records[rid].get("document") or {}).get("path", "")
                              ).read_text(encoding="utf-8", errors="replace")
            roh_gold = zeile.get("goldwerte")
            if isinstance(roh_gold, list):
                gold = sorted({round(float(w), 6) for w in roh_gold})
            else:
                gold = sorted({round(float(z["value"]), 6)
                               for z in (records[rid].get("gold") or {}).get("cells") or []
                               if z.get("value") is not None})
            zellen = (records[rid].get("gold") or {}).get("cells") or []
            mittel = {round(float(z["value"]), 6) for z in zellen
                      if str(z.get("field")).endswith("_mean")}
            streuung = {round(float(z["value"]), 6) for z in zellen
                        if str(z.get("field")).endswith("standard_deviation")}
            kern = unterscheider(records[rid].get("context") or {})
            ausschnitt = " ".join(texte[rid][s[0]:s[1]]
                                   for s in zeile.get("stuecke") or [])
            mit_gold = [s for s in saetze(ausschnitt) if zahlen(s) & set(gold)]
            for loc in locators_von(zeile):
                satz = str(loc.get("satz") or "").strip()
                if not satz:
                    continue
                nummern = zahlen(satz)
                treffer = sorted(nummern & set(gold))
                paar = (bool(nummern & mittel) and bool(nummern & streuung))
                drin = [w for w in kern if w.lower() in satz.lower()]
                vollstaendig = bool(kern) and len(drin) == len(kern)
                if paar and vollstaendig:
                    urteil = "richtig und eindeutig"
                elif paar:
                    urteil = ("Paar richtig, Unterscheider fehlt: "
                              + ", ".join(w for w in kern if w not in drin))
                elif mit_gold:
                    urteil = "Paar fehlt, richtiger Satz lag vor"
                else:
                    urteil = "Paar fehlt, kein richtiger Satz im Ausschnitt"
                faelle.append({"record_id": rid, "quelle": pfad.name,
                               "arm": loc.get("arm"), "satz": satz,
                               "goldwerte_im_satz": treffer, "paar_vollstaendig": paar,
                               "unterscheider_im_satz": drin, "unterscheider": kern,
                               "saetze_mit_gold_im_ausschnitt": len(mit_gold),
                               "urteil": urteil,
                               "tokens": zeile.get("completion_tokens")})
                print(f"{rid:14s} {urteil:52s} Paar {str(paar):5s} "
                      f"| {pfad.name[:26]:26s} | {satz[:45]!r}")

    zaehl: dict[str, int] = {}
    for f in faelle:
        zaehl[f["urteil"]] = zaehl.get(f["urteil"], 0) + 1
    print("Summe Locators mit Satz:", zaehl, "| Faelle", len(faelle))
    einzig = {(f["record_id"], f["quelle"], f["satz"]) for f in faelle}
    print("ohne Doppelzaehlung je Quelle:", len(einzig))
    print("Records betroffen:", sorted({f["record_id"] for f in faelle}))
    if args.json:
        Path(args.json).write_text(json.dumps({"zaehlung": zaehl, "faelle": faelle},
                                              indent=2, ensure_ascii=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
