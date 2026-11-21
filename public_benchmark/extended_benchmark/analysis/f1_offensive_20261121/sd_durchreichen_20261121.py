"""SD als eigenes Zellfeld: wie viele der 15 Records werden vollstaendig?

Offline, ohne Netzaufruf. Der plus_minus-Leser hat die Streuung immer schon
gesehen, sie wurde nur nicht als Feld ausgegeben. `wert_aus_zelle` liefert sie
jetzt fuer `*_standard_deviation`, aber nur aus Zellen, deren Format den zweiten
Wert als SD ausweist (`Mittel (SD)`, `Mittel +/- SD`).

Gemessen wird an den 15 P5-Records, denen ausschliesslich die SD fehlt:

1. Liefert die Regel den Wert, und stimmt er gegen Gold?
2. Wird der Record dadurch vollstaendig, und aendert sich die Poolbasis?

Die Goldwerte dienen nur als Auftrag und Pruefmass; gelesen wird aus dem
Dokument.
"""

from __future__ import annotations

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
import pooling_effekt_20261121 as pe  # noqa: E402

FORMATE = ("mittel_sd", "plus_minus")
ARME = {"intervention_standard_deviation": "intervention",
        "comparator_standard_deviation": "comparator"}


def main() -> int:
    luecken = json.loads((HIER / "pooling_luecken_20261121.json").read_text(encoding="utf-8"))
    ids = [z["record_id"] for z in luecken["je_record"] if z["typ"] == "continuous"
           and z["fehlt"] and set(z["fehlt"]) <= set(ARME)]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = v.lade(v.P5)
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8",
                                                                        errors="replace")
             for rid in ids}

    auftraege = []
    for rid in ids:
        gold = pe.gold_zellen(recs[rid])
        for feld in ARME:
            if feld in pe.p5_zellen(next(z for z in p5 if z["record_id"] == rid)):
                continue
            if feld in gold:
                auftraege.append({"record_id": rid, "feld": feld, "arm": ARME[feld],
                                  "wert": gold[feld]})
    ergebnis = m.messe(auftraege, recs, texte, m.alias_mod.ALIAS, True, mean_formate=FORMATE)

    # Grund je nicht geliefertem Auftrag: Zielzeile fehlt oder Zellformat passt nicht.
    gruende: dict[tuple[str, str], str] = {}
    for f in auftraege:
        if any(e["record_id"] == f["record_id"] and e["feld"] == f["feld"]
               for e in ergebnis["detail"]):
            continue
        rec = recs[f["record_id"]]
        zeilen = texte[f["record_id"]].splitlines()
        outcome = str((rec.get("context") or {}).get("outcome") or "")
        ziel = m.ziel_zeile_block(zeilen, outcome, m.alias_mod.ALIAS, True)
        if ziel < 0:
            gruende[(f["record_id"], f["feld"])] = "keine Zielzeile"
        else:
            gruende[(f["record_id"], f["feld"])] = "Zielzeile ohne SD-Format"

    geliefert: dict[str, dict[str, dict[str, Any]]] = {rid: {} for rid in ids}
    for e in ergebnis["detail"]:
        geliefert[e["record_id"]][e["feld"]] = e
    je: dict[str, dict[str, Any]] = {}
    vollstaendig = richtig = 0
    for rid in ids:
        braucht = [f for f in ARME
                   if f not in pe.p5_zellen(next(z for z in p5 if z["record_id"] == rid))]
        da = [f for f in braucht if f in geliefert[rid]]
        stimmt = all(geliefert[rid][f]["richtig"] for f in da)
        je[rid] = {"braucht": braucht, "geliefert": da,
                   "richtig": sum(1 for f in da if geliefert[rid][f]["richtig"]),
                   "vollstaendig": len(da) == len(braucht),
                   "ganz_richtig": len(da) == len(braucht) and stimmt}
        vollstaendig += len(da) == len(braucht)
        richtig += je[rid]["ganz_richtig"]

    # Poolbasis: P5 plus die gelieferten SD (alle) bzw. nur die richtigen.
    typen = {z["record_id"]: str((recs[z["record_id"]].get("context") or {}).get("outcome_type")
                                 or "") for z in p5}
    basis = {z["record_id"]: pe.p5_zellen(z) for z in p5}
    alle_sd = {rid: dict(basis[rid]) for rid in basis}
    gute_sd = {rid: dict(basis[rid]) for rid in basis}
    for rid, felder in geliefert.items():
        for feld, e in felder.items():
            alle_sd[rid][feld] = e["regel"]["value"]
            if e["richtig"]:
                gute_sd[rid][feld] = e["regel"]["value"]
    p_alle = pe.pool_stand(alle_sd, typen)
    p_gut = pe.pool_stand(gute_sd, typen)
    p_basis = pe.pool_stand(basis, typen)

    daten = {"records": len(ids), "auftraege": len(auftraege),
             "geliefert": ergebnis["geliefert"], "richtig": ergebnis["tp"],
             "falsch": ergebnis["fp"],
             "records_vollstaendig": vollstaendig, "records_ganz_richtig": richtig,
             "je_record": je,
             "gruende": {f"{a}|{b}": c for (a, b), c in gruende.items()},
             "pool": {"basis": {"k": p_basis["k"], "pooled": p_basis["pooled"]},
                      "mit_alle_sd": {"k": p_alle["k"], "pooled": p_alle["pooled"]},
                      "mit_richtigen_sd": {"k": p_gut["k"], "pooled": p_gut["pooled"]}}}
    (HIER / "sd_durchreichen_20261121.json").write_text(
        json.dumps(daten, indent=2, ensure_ascii=True), encoding="utf-8")

    md = ["# SD als eigenes Zellfeld: Wirkung an den 15 Records", "",
          "Offline, ohne Netzaufruf. `sd_durchreichen_20261121.py`. `wert_aus_zelle`",
          "liefert die Streuung jetzt fuer `*_standard_deviation`, aber nur aus Zellen",
          "im Format `Mittel (SD)` oder `Mittel +/- SD`; alles andere bleibt leer.", "",
          f"- Records mit ausschliesslich fehlender SD: {len(ids)}",
          f"- Zellauftraege: {len(auftraege)}, geliefert {ergebnis['geliefert']}, "
          f"richtig {ergebnis['tp']}, falsch {ergebnis['fp']}",
          f"- Records vollstaendig: {vollstaendig}, davon gegen Gold ganz richtig: {richtig}",
          "", "| Record | fehlende Felder | geliefert | richtig | vollstaendig |",
          "|---|---|---:|---:|---|"]
    for rid in ids:
        e = je[rid]
        md.append(f"| `{rid}` | {', '.join(f.replace('_standard_deviation', '') for f in e['braucht'])} | "
                  f"{len(e['geliefert'])} | {e['richtig']} | "
                  f"{'ja' if e['vollstaendig'] else 'nein'} |")
    md += ["", "## Nicht gelieferte Auftraege", "", "| Record | Feld | Grund |",
           "|---|---|---|"]
    for (rid, feld), grund in sorted(gruende.items()):
        md.append(f"| `{rid}` | {feld.replace('_standard_deviation', '')} | {grund} |")
    md += ["", "## Poolbasis", "",
           "| Stand | k | pooled |", "|---|---:|---:|",
           f"| P5 unveraendert | {p_basis['k']} | {p_basis['pooled']:.3f} |",
           f"| mit allen gelieferten SD | {p_alle['k']} | {p_alle['pooled']:.3f} |",
           f"| mit den richtigen SD | {p_gut['k']} | {p_gut['pooled']:.3f} |",
           "", "Die Poolbasis waechst nur um Records, deren uebrige Zellen schon",
           "vollstaendig waren; fehlt weiter ein anderes Feld, bleibt der Record draussen.",
           "", "## Grenzen", "",
           "- Goldmittel dienen als Auftrag: die Regel muss die Zielzeile aus dem",
           "  Goldoutcome finden, nicht aus dem P5-Ergebnis.",
           "- Ein Treffer misst nur den SD-Wert der Zielzeile; die Zuordnung Arm/Spalte",
           "  folgt derselben Label-Logik wie beim Mittel."]
    (HIER / "sd_durchreichen_20261121.md").write_text("\n".join(md) + "\n",
                                                      encoding="ascii", errors="replace")
    print(f"Records {len(ids)} | Auftraege {len(auftraege)} | geliefert "
          f"{ergebnis['geliefert']} richtig {ergebnis['tp']} falsch {ergebnis['fp']}")
    print(f"vollstaendig {vollstaendig} | ganz richtig {richtig}")
    for rid in ids:
        e = je[rid]
        print(f"  {rid}: braucht {len(e['braucht'])} geliefert {len(e['geliefert'])} "
              f"richtig {e['richtig']} vollstaendig {e['vollstaendig']}")
    print(f"Pool: k {p_basis['k']} -> {p_alle['k']} / {p_gut['k']} | pooled "
          f"{p_basis['pooled']:.3f} -> {p_alle['pooled']:.3f} / {p_gut['pooled']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
