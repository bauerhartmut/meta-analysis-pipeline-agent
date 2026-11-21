"""Aendern die Ersetzungen die gepoolte Effektschaetzung in P5?

Offline, ohne Netzaufruf. Gebaut werden vier Zellstaende fuer die 103
P5-Records:

* `p5`      - Vorhersagen unveraendert,
* `gate`    - die 33 Zellen der Endvariante ersetzt,
* `ohne_gate` - die 43 Zellen der Variante ohne Gate ersetzt,
* `gold`    - alle Zellen durch Gold ersetzt (Referenz).

Je Record wird ein Effekt abgeleitet, sobald die Zellen vollstaendig sind:

* binaer: Log-Odds-Ratio mit 0.5-Korrektur, SE = sqrt(1/a+1/b+1/c+1/d),
* kontinuierlich: Hedges g aus Mittelwerten und Standardabweichungen,
  SE = sqrt((n1+n2)/(n1*n2) + g^2/(2*(n1+n2))).

Gepoolt wird mit `research_agent/meta/pooling.pool(method="hksj")`. Ausgewiesen
werden alle vollstaendigen Records sowie - fuer den direkten Vergleich - die
Records, die in allen vier Staenden vollstaendig sind (gemeinsame Menge).

Hinweis: Die Effektbildung ist eine einfache, hier dokumentierte Ableitung, nicht
die Effektpipeline des Projekts; sie dient allein dem Vergleich der Zellstaende.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(ANALYSE / "f1_offensive_20261121"))
sys.path.insert(0, str(REPO))

import vergleiche_20261120 as v  # noqa: E402
import zielzeile_alle_20261121 as m  # noqa: E402
from research_agent.meta import pooling  # noqa: E402

FORMATE = ("mittel_sd", "plus_minus")
CONT = ("intervention_mean", "comparator_mean", "intervention_standard_deviation",
        "comparator_standard_deviation", "intervention_group_size", "comparator_group_size")
BIN = ("intervention_events", "comparator_events", "intervention_group_size",
       "comparator_group_size")


def p5_zellen(zeile: dict[str, Any]) -> dict[str, float]:
    aus: dict[str, float] = {}
    for zelle in ((zeile.get("predicted") or {}).get("cells") or []):
        wert = zelle.get("value")
        if wert is None:
            continue
        try:
            aus[str(zelle.get("field"))] = float(wert)
        except (TypeError, ValueError):
            continue
    return aus


def gold_zellen(record: dict[str, Any]) -> dict[str, float]:
    aus: dict[str, float] = {}
    for zelle in (record.get("gold") or {}).get("cells") or []:
        wert = zelle.get("value")
        if wert is None:
            continue
        try:
            aus[str(zelle.get("field"))] = float(wert)
        except (TypeError, ValueError):
            continue
    return aus


def effekt(zellen: dict[str, float], typ: str) -> tuple[float, float] | None:
    """(estimate, se) je Record, oder None wenn unvollstaendig."""
    if typ == "continuous":
        if any(zellen.get(k) is None for k in CONT):
            return None
        n1, n2 = zellen["intervention_group_size"], zellen["comparator_group_size"]
        m1, m2 = zellen["intervention_mean"], zellen["comparator_mean"]
        s1, s2 = zellen["intervention_standard_deviation"], zellen["comparator_standard_deviation"]
        if n1 < 2 or n2 < 2 or s1 <= 0 or s2 <= 0:
            return None
        sp = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
        if sp <= 0:
            return None
        d = (m1 - m2) / sp
        j = 1 - 3 / (4 * (n1 + n2) - 9)
        g = d * j
        var = (n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2))
        return g, math.sqrt(var)
    if any(zellen.get(k) is None for k in BIN):
        return None
    n1, n2 = zellen["intervention_group_size"], zellen["comparator_group_size"]
    a, c = zellen["intervention_events"], zellen["comparator_events"]
    if n1 < 1 or n2 < 1 or a < 0 or c < 0 or a > n1 or c > n2:
        return None
    a2, c2 = a + 0.5, c + 0.5
    b2, d2 = n1 - a + 0.5, n2 - c + 0.5
    est = math.log((a2 * d2) / (b2 * c2))
    se = math.sqrt(1 / a2 + 1 / b2 + 1 / c2 + 1 / d2)
    return est, se


def pool_stand(zellen_map: dict[str, dict[str, float]], typen: dict[str, str],
               nur: set[str] | None = None, max_abs: float | None = None) -> dict[str, Any]:
    effekte = []
    for rid, zellen in zellen_map.items():
        if nur is not None and rid not in nur:
            continue
        e = effekt(zellen, typen.get(rid, ""))
        if not e:
            continue
        if max_abs is not None and abs(e[0]) > max_abs:
            continue
        effekte.append({"est": e[0], "se": e[1], "label": rid})
    erg = pooling.pool(effekte, method="hksj")
    return {"k": erg["k"], "pooled": erg["pooled"], "ci": (erg["ci_low"], erg["ci_high"]),
            "i2": erg["i2"], "tau2": erg["tau2"], "records": {e["label"] for e in effekte}}


def main() -> int:
    daten = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in daten["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in faelle}}
    p5 = v.lade(v.P5)
    typen = {z["record_id"]: str((recs[z["record_id"]].get("context") or {}).get("outcome_type") or "")
             for z in p5}

    staende: dict[str, dict[str, dict[str, float]]] = {
        "p5": {z["record_id"]: p5_zellen(z) for z in p5},
        "gold": {z["record_id"]: gold_zellen(recs[z["record_id"]]) for z in p5},
    }
    ersetzungen: dict[str, dict[str, float]] = {}
    for name, gate in (("gate", True), ("ohne_gate", False)):
        m.GATE = gate
        res = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True, mean_formate=FORMATE)
        m.GATE = True
        werte: dict[str, float] = {}
        for e in res["detail"]:
            if e.get("regel"):
                werte.setdefault(e["record_id"], {})[e["feld"]] = e["regel"]["value"]
        ersetzungen[name] = werte
        staende[name] = {z["record_id"]: {**p5_zellen(z), **werte.get(z["record_id"], {})}
                         for z in p5}

    ergebnis: dict[str, Any] = {}
    for name, karte in staende.items():
        ergebnis[name] = pool_stand(karte, typen)
    gemeinsam = set.intersection(*(ergebnis[n]["records"] for n in staende))
    ergebnis_gemeinsam = {name: pool_stand(karte, typen, nur=gemeinsam)
                          for name, karte in staende.items()}
    # Extremwerte (|g| > 3) sind Zellartefakte, keine Effekte; ohne sie zeigt
    # sich, ob das Vorzeichen der Schaetzung von zwei Records abhaengt.
    robust = {name: pool_stand(karte, typen, nur=gemeinsam, max_abs=3.0)
              for name, karte in staende.items()}
    richtung: dict[str, tuple[int, int]] = {}
    for name in ("p5", "gate", "ohne_gate", "gold"):
        unten = oben = 0
        for rid in gemeinsam:
            e = effekt(staende[name][rid], typen[rid])
            if not e:
                continue
            if e[0] < 0:
                unten += 1
            else:
                oben += 1
        richtung[name] = (unten, oben)

    # Welche Records tragen die Ersetzungen ueberhaupt in den Pool?
    betroffen = {"gate": sorted(ersetzungen["gate"]), "ohne_gate": sorted(ersetzungen["ohne_gate"])}
    beruehrt: dict[str, list[str]] = {}
    for name in ("gate", "ohne_gate"):
        im_pool = [rid for rid in betroffen[name] if rid in ergebnis[name]["records"]]
        ausserhalb = [rid for rid in betroffen[name] if rid not in ergebnis[name]["records"]]
        beruehrt[name] = im_pool
        print(f"{name:10s} ersetzte Records={len(betroffen[name])} davon im Pool={len(im_pool)} "
              f"ausserhalb (unvollstaendig)={len(ausserhalb)}")
    delta_gate = [rid for rid in beruehrt["gate"]
                  if abs(effekt(staende["gate"][rid], typen[rid])[0]
                         - effekt(staende["p5"][rid], typen[rid])[0]) > 1e-9]
    delta_ohne = [rid for rid in beruehrt["ohne_gate"]
                  if abs(effekt(staende["ohne_gate"][rid], typen[rid])[0]
                         - effekt(staende["p5"][rid], typen[rid])[0]) > 1e-9]
    print("Effekt geaendert: gate", len(delta_gate), "| ohne_gate", len(delta_ohne))

    zeilen = ["# Gepoolte Effektschaetzung in P5 mit und ohne Ersetzungen", "",
              "Offline, ohne Netzaufruf. Effektableitung: Log-Odds-Ratio (binaer) bzw.",
              "Hedges g (kontinuierlich), gepoolt mit `pool(method=\"hksj\")` aus",
              "`research_agent/meta/pooling.py`. Die Ableitung ist eine einfache,",
              "hier dokumentierte Naeherung, nicht die Effektpipeline des Projekts.", "",
              "## Alle vollstaendigen Records je Stand", "",
              "| Stand | Zellen ersetzt | k | pooled | 95 %-KI | I2 | tau2 |",
              "|---|---:|---:|---:|---|---:|---:|"]
    for name, label in (("p5", "unveraendert"), ("gate", "33 Zellen"),
                        ("ohne_gate", "43 Zellen"), ("gold", "Gold (Referenz)")):
        e = ergebnis[name]
        zeilen.append(f"| {label} | {0 if name in ('p5', 'gold') else (33 if name == 'gate' else 43)} | "
                      f"{e['k']} | {e['pooled']:.3f} | {e['ci'][0]:.3f} bis {e['ci'][1]:.3f} | "
                      f"{(e['i2'] or 0):.1f} | {(e['tau2'] or 0):.4f} |")
    wechsel = []
    for rid in sorted(set(delta_gate) | set(delta_ohne)):
        e0 = effekt(staende["p5"][rid], typen[rid])
        e1 = effekt(staende["gate"][rid], typen[rid])
        e2 = effekt(staende["gold"][rid], typen[rid])
        wechsel.append((rid, typen[rid], e0[0], e1[0], None if not e2 else e2[0]))

    zeilen += ["", "## Records, deren Effekt sich aendert", "",
               "| Record | Typ | P5 | mit Ersetzung | Gold |", "|---|---|---:|---:|---:|"]
    for rid, typ, vor, nach, gold in wechsel:
        g = "-" if gold is None else f"{gold:.3f}"
        zeilen.append(f"| `{rid}` | {typ} | {vor:.3f} | {nach:.3f} | {g} |")
    zeilen += ["", "## Sensitivitaet ohne Extremwerte (|g| <= 3, gemeinsame Menge)", "",
               "| Stand | k | pooled | 95 %-KI | I2 | negativ / positiv |",
               "|---|---:|---:|---|---:|---:|"]
    for name, label in (("p5", "unveraendert"), ("gate", "33 Zellen"),
                        ("ohne_gate", "43 Zellen"), ("gold", "Gold (Referenz)")):
        e = robust[name]
        zeilen.append(f"| {label} | {e['k']} | {e['pooled']:.3f} | {e['ci'][0]:.3f} bis "
                      f"{e['ci'][1]:.3f} | {(e['i2'] or 0):.1f} | "
                      f"{richtung[name][0]} / {richtung[name][1]} |")
    zeilen += ["", "## Wo die Ersetzungen den Pool beruehren", "",
               "| Stand | ersetzte Records | davon vollstaendig (im Pool) | Effekt geaendert |",
               "|---|---:|---:|---:|"]
    for name, label, delta in (("gate", "33 Zellen", delta_gate),
                              ("ohne_gate", "43 Zellen", delta_ohne)):
        zeilen.append(f"| {label} | {len(betroffen[name])} | {len(beruehrt[name])} | {len(delta)} |")
    zeilen += ["", "Die 10 Zellen, die das Gate zusaetzlich verwirft, liegen auf Records, die",
               "im P5-Pool nicht vollstaendig sind; deshalb sind beide Staende gepoolt gleich.",
               "", f"## Gemeinsame Menge (k = {len(gemeinsam)})", "",
               "| Stand | k | pooled | 95 %-KI | I2 | tau2 |",
               "|---|---:|---:|---|---:|---:|"]
    for name, label in (("p5", "unveraendert"), ("gate", "33 Zellen"),
                        ("ohne_gate", "43 Zellen"), ("gold", "Gold (Referenz)")):
        e = ergebnis_gemeinsam[name]
        zeilen.append(f"| {label} | {e['k']} | {e['pooled']:.3f} | {e['ci'][0]:.3f} bis "
                      f"{e['ci'][1]:.3f} | {(e['i2'] or 0):.1f} | {(e['tau2'] or 0):.4f} |")
    (HIER / "pooling_effekt_20261121.md").write_text("\n".join(zeilen) + "\n",
                                                     encoding="ascii", errors="replace")
    (HIER / "pooling_effekt_20261121.json").write_text(json.dumps(
        {"alle": ergebnis, "gemeinsam": {"k": len(gemeinsam), "werte": ergebnis_gemeinsam},
         "robust": robust, "richtung": richtung, "wechsel": wechsel},
        indent=2, ensure_ascii=True, default=list), encoding="utf-8")
    for name in ("p5", "gate", "ohne_gate", "gold"):
        e = ergebnis[name]
        g = ergebnis_gemeinsam[name]
        print(f"{name:10s} alle k={e['k']:3d} pooled={e['pooled']:.3f} "
              f"[{e['ci'][0]:.3f}; {e['ci'][1]:.3f}] | gemeinsam k={g['k']:2d} "
              f"pooled={g['pooled']:.3f} [{g['ci'][0]:.3f}; {g['ci'][1]:.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
