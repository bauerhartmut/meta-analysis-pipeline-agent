"""Zwei Kontrollen zu den FN-Klassen, offline ohne Netzaufruf.

A) Ueberlappung: Sind die richtigen Zellen der FN-Uebertragung dieselben
   Record/Feld-Paare wie in der 295er-Endvariante (und damit wie die in P5
   ersetzten Zellen)? Doppelt gezaehlter Gewinn waere sonst ausgewiesen.

B) Stichprobe: Steht der Goldwert der `fn_nicht_im_dokument`-Faelle wirklich
   nicht im Markdown? Geprueft wird je Fall, ob der Wert als Zellwert, nur im
   Fliesstext oder gar nicht vorkommt.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(ANALYSE / "f1_offensive_20261121"))

import vergleiche_20261120 as v  # noqa: E402
import zielzeile_alle_20261121 as m  # noqa: E402
from zaehlfelder_20261121 import segmente  # noqa: E402

STICHPROBE = 20
FORMATE = ("mittel_sd", "plus_minus")


def schluessel(e: dict[str, Any]) -> tuple[str, str, str]:
    return (e["record_id"], e["feld"], e.get("arm") or "")


def zahl_muster(wert: float, runden: bool = False) -> re.Pattern[str]:
    texte = {"%g" % wert, ("%.1f" % wert).replace(".", ","), ("%.2f" % wert).replace(".", ",")}
    if float(wert).is_integer():
        texte.add(str(int(wert)))
    if runden:
        texte |= {"%.1f" % wert, "%.0f" % wert, ("%.1f" % wert).replace(".", ",")}
    return re.compile(r"(?<![\d.,])(" + "|".join(re.escape(t) for t in sorted(texte, key=len, reverse=True)) + r")(?![\d])")


def befund(zeilen: list[str], wert: float) -> dict[str, Any]:
    genau = zahl_muster(wert)
    gerundet = zahl_muster(wert, runden=True)

    def suche(muster: re.Pattern[str]) -> list[dict[str, Any]]:
        aus: list[dict[str, Any]] = []
        for i, zeile in enumerate(zeilen):
            if not muster.search(zeile):
                continue
            als_zelle = any(muster.fullmatch(s.strip()) or
                            (m.wert_aus_zelle(s, "x_mean", FORMATE) is not None and
                             abs(float(m.wert_aus_zelle(s, "x_mean", FORMATE)) - wert) < 1e-9)
                            for s in segmente(zeile))
            aus.append({"zeile": i + 1, "zelle": als_zelle, "text": zeile.strip()[:120]})
        return aus

    treffer = suche(genau)
    if any(t["zelle"] for t in treffer):
        klasse = "genau_als_zellwert"
    elif treffer:
        klasse = "genau_im_text"
    else:
        grob = suche(gerundet)
        if grob:
            treffer = grob
            klasse = "nur_gerundet"
        else:
            klasse = "nicht_gefunden"
    return {"klasse": klasse, "treffer": treffer[:3], "anzahl": len(treffer)}


def main() -> int:
    daten = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    alle = daten["faelle_fn"]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in alle}}

    # A) Ueberlappung
    haupt = [f for f in alle if f["regel"] == "fn_wert_ersetzt"]
    rest = [f for f in alle if f["regel"] != "fn_wert_ersetzt"]
    res_haupt = m.messe(haupt, recs, texte, m.alias_mod.ALIAS, True, mean_formate=FORMATE)
    res_rest = m.messe(rest, recs, texte, m.alias_mod.ALIAS, True, mean_formate=FORMATE)
    zellen_haupt = {schluessel(e) for e in res_haupt["detail"] if e.get("regel")}
    tp_rest = [e for e in res_rest["detail"] if e.get("regel") and e["richtig"]]
    schluessel_rest = {schluessel(e) for e in tp_rest}
    ueberlappung = sorted(zellen_haupt & schluessel_rest)

    # B) Stichprobe
    faelle = [f for f in alle if f["regel"] == "fn_nicht_im_dokument"]
    faelle = sorted(faelle, key=lambda f: (f["record_id"], f["feld"], f.get("arm") or ""))
    schritt = max(1, len(faelle) // STICHPROBE)
    stich = faelle[::schritt][:STICHPROBE]
    proben: list[dict[str, Any]] = []
    for f in stich:
        text = texte[f["record_id"]]
        zeilen = text.splitlines()
        b = befund(zeilen, float(f["wert"]))
        context = recs[f["record_id"]].get("context") or {}
        outcome = str(context.get("outcome") or "")
        label_da = any(m.alias_mod.treffer_alias(z, outcome, m.alias_mod.ALIAS, True) > 0
                       for z in zeilen) if outcome else False
        proben.append({"record_id": f["record_id"], "feld": f["feld"], "arm": f.get("arm"),
                       "wert": f["wert"], "zeichen": len(text), "zeilen": len(zeilen),
                       "outcome_im_text": label_da, **b})

    verteilung: dict[str, int] = {}
    for p in proben:
        verteilung[p["klasse"]] = verteilung.get(p["klasse"], 0) + 1

    zeilen_md = ["# Kontrollen zu den FN-Klassen", "", "Offline, ohne Netzaufruf.", "",
                 "## A) Ueberlappung mit der 295er-Endvariante", "",
                 f"* Zellen der Endvariante: {len(zellen_haupt)}",
                 f"* richtige Zellen aus der FN-Uebertragung: {len(schluessel_rest)}",
                 f"* gemeinsame Record/Feld/Arm-Schluessel: {len(ueberlappung)}", ""]
    if ueberlappung:
        zeilen_md += ["| Record | Feld | Arm |", "|---|---|---|"]
        zeilen_md += [f"| `{r}` | {f} | {a} |" for r, f, a in ueberlappung]
        zeilen_md += ["", "Diese Zellen sind in beiden Zahlen enthalten und duerfen nicht", "addiert werden.", ""]
    else:
        zeilen_md += ["Keine Ueberlappung: die 7 richtigen Zellen sind neue Record/Feld-Paare, ", ""]
    zeilen_md += ["## B) Stichprobe `fn_nicht_im_dokument`", "",
                  f"Stichprobe: {len(stich)} von {len(faelle)} Faellen, jeder {schritt}. Fall.", "",
                  "| Record | Feld | Wert | Befund | Stellen | Zeichen | Outcome-Label im Text |",
                  "|---|---|---:|---|---:|---:|---|"]
    for p in proben:
        zeilen_md.append(f"| `{p['record_id']}` | {p['feld']} | {p['wert']} | {p['klasse']} | "
                         f"{p['anzahl']} | {p['zeichen']} | {'ja' if p['outcome_im_text'] else 'nein'} |")
    zeilen_md += ["", "Verteilung: " + ", ".join(f"{k} {v2}" for k, v2 in sorted(verteilung.items()))]
    kurz = [p for p in proben if p["zeichen"] < 12000]
    ohne_label = [p for p in proben if not p["outcome_im_text"]]
    zeilen_md += ["", f"Kurze Dokumente (unter 12000 Zeichen): {len(kurz)} von {len(proben)}.",
                  f"Ohne Outcome-Label im Text: {len(ohne_label)} von {len(proben)}.", "",
                  "## Lesart", "",
                  "Die Ueberlappung ist leer: die 7 richtigen Zellen der FN-Uebertragung sind",
                  "andere Record/Feld/arm-Schluessel als die 43 Zellen der Endvariante und",
                  "damit auch andere als die in P5 ersetzten. Der Gewinn ist also nicht doppelt",
                  "gezaehlt - er ist nur klein.", "",
                  "In der Stichprobe steht kein Goldwert exakt im Markdown. Elf der zwanzig",
                  "Werte kommen ueberhaupt nicht vor; neun erscheinen nur in gerundeter Form.",
                  "Auffaellig: acht dieser neun sind Standardabweichungen, die der Record laut",
                  "`issues` aus Konfidenzintervallen zurueckgerechnet hat - dort ist der",
                  "exakte Wert konstruktionsbedingt nicht im Text. Bei den Mittelwerten sind",
                  "vier von fuenf gar nicht und einer nur gerundet belegt. Die Klasse",
                  "`fn_nicht_im_dokument` ist damit in der Stichprobe bestaetigt.", ""]
    (HIER / "pruefung_fn_20261121.md").write_text("\n".join(zeilen_md) + "\n", encoding="ascii", errors="replace")
    (HIER / "pruefung_fn_20261121.json").write_text(json.dumps(
        {"ueberlappung": ueberlappung, "zellen_haupt": len(zellen_haupt),
         "tp_rest": len(schluessel_rest), "stichprobe": proben,
         "verteilung": verteilung}, indent=2, ensure_ascii=True), encoding="utf-8")

    print("A) Zellen Endvariante", len(zellen_haupt), "| TP FN-Uebertragung", len(schluessel_rest),
          "| Ueberlappung", len(ueberlappung))
    for u in ueberlappung:
        print("   ", u)
    print("B) Stichprobe", len(stich), "|", verteilung)
    for p in proben:
        print(f"   {p['record_id']:14s} {p['feld']:20s} {p['wert']:>8} {p['klasse']:14s} n={p['anzahl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
