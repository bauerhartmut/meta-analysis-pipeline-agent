"""Armzuordnung der Groessenzellen: Kopfzeilen-Label gegen Spaltenreihenfolge.

Offline, ohne Netzaufruf. Vergleicht fuer die 295 `fn_wert_ersetzt`-Faelle zwei
Lesarten der Gruppengroessen:

* `label`  - jeder `n`-Wert gehoert zu dem Arm, der in seiner Spalte steht
             (Spaltenreihenfolge aus dem Tabellenkopf, Zuordnung ueber den
             Spaltennamen). Das ist die Regel im Skript.
* `position` - die erste Datenspalte gehoert immer der Intervention, egal wie
             die Spalte heisst.

Zusaetzlich werden die vier PMC5617873-Records einzeln belegt, deren Groessen-FP
als `falsche_spalte` gefuehrt sind.
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
from zaehlfelder_20261121 import segmente  # noqa: E402

PMC = ("yun2024:331", "yun2024:334", "yun2024:335", "yun2024:336")
SIZE_FELDER = ("intervention_group_size", "comparator_group_size")


def kopf_zeile(zeilen: list[str], ziel: int, context: dict[str, Any]) -> tuple[int, list[str]]:
    """Naeheste Kopfzeile ueber der Zielzeile, die beide Arme benennt."""
    a, _ = m.tabellengrenzen(zeilen, ziel)
    for j in range(ziel - 1, a - 1, -1):
        segs = segmente(zeilen[j])
        arme = [m.arm_weit(s, context) for s in segs]
        if len([a_ for a_ in arme if a_]) >= 2:
            return j, segs
    return -1, []


def belege(recs: dict[str, dict[str, Any]], texte: dict[str, str],
           detail: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kopfzeile, Spaltenreihenfolge und Gold fuer die vier PMC5617873-Records."""
    gold_map: dict[str, dict[str, Any]] = {}
    for e in detail:
        if e["feld"] in SIZE_FELDER:
            gold_map.setdefault(e["record_id"], {})[e["feld"]] = e.get("gold")
    aus: list[dict[str, Any]] = []
    for rid in PMC:
        context = recs[rid].get("context") or {}
        zeilen = texte[rid].splitlines()
        ziel = m.alias_mod.ziel_zeile_alias(
            zeilen, str(context.get("outcome") or ""), m.alias_mod.ALIAS, True)
        j, segs = kopf_zeile(zeilen, ziel, context) if ziel >= 0 else (-1, [])
        spalten = []
        for pos, seg in enumerate(segs):
            arm = m.arm_weit(seg, context)
            if arm:
                spalten.append({"spalte": pos + 1, "kopf": seg[:40], "arm": arm})
        gold = {k: gold_map.get(rid, {}).get(k) for k in SIZE_FELDER}
        aus.append({"record_id": rid, "kopfzeile": j + 1, "spalten": spalten,
                    "gold": gold, "kopf_text": (zeilen[j].strip()[:120] if j >= 0 else "")})
    return aus


def bilanz(detail: list[dict[str, Any]], tauschen: bool) -> dict[str, Any]:
    """Richtige und falsche Groessenzellen, optional mit getauschten Armen."""
    zwischen: dict[str, dict[str, dict[str, Any]]] = {}
    for e in detail:
        if e["feld"] in SIZE_FELDER and e.get("regel"):
            zwischen.setdefault(e["record_id"], {})[e["feld"]] = e
    richtig = falsch = 0
    for rid, felder in zwischen.items():
        if tauschen and len(felder) == 2:
            i, c = felder.get(SIZE_FELDER[0]), felder.get(SIZE_FELDER[1])
            if i and c:
                zwischen[rid] = {SIZE_FELDER[0]: dict(i, regel=dict(i["regel"], value=c["regel"]["value"])),
                                 SIZE_FELDER[1]: dict(c, regel=dict(c["regel"], value=i["regel"]["value"]))}
    for rid, felder in zwischen.items():
        for feld, e in felder.items():
            gold = e.get("gold")
            if gold is None:
                continue
            if float(e["regel"]["value"]) == float(gold):
                richtig += 1
            else:
                falsch += 1
    return {"richtig": richtig, "falsch": falsch, "zellen": richtig + falsch}


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in faelle}}
    res = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True,
                  mean_formate=("mittel_sd", "plus_minus"))
    detail = res["detail"]
    gesamt = {"ohne_tausch": bilanz(detail, False), "mit_tausch": bilanz(detail, True)}
    einzeln = belege(recs, texte, detail)

    zeilen = ["# Armzuordnung: Kopfzeilen-Label gegen Spaltenreihenfolge", "",
              "Offline, ohne Netzaufruf.", "",
              "## Die vier PMC5617873-Records", ""]
    for b in einzeln:
        zeilen.append(f"* `{b['record_id']}` - Kopfzeile {b['kopfzeile']}: `{b['kopf_text']}`")
        for s in b["spalten"]:
            zeilen.append(f"  * Spalte {s['spalte']}: `{s['kopf']}` -> `{s['arm']}`")
        g = b["gold"]
        zeilen.append(f"  * Gold: intervention {g['intervention_group_size']}, "
                      f"comparator {g['comparator_group_size']}")
    zeilen += ["", "## Bilanz der Groessenzellen", "",
               "| Lesart | richtig | falsch | Zellen |", "|---|---:|---:|---:|"]
    for name, wert in (("Label (Spaltenname)", gesamt["ohne_tausch"]),
                       ("Position (erste Spalte = Intervention)", gesamt["mit_tausch"])):
        zeilen.append(f"| {name} | {wert['richtig']} | {wert['falsch']} | {wert['zellen']} |")
    zeilen += ["", "## Lesart", "",
               "Die Regel ordnet jeden `n`-Wert ueber den Spaltennamen zu; das ist die",
               "Spaltenreihenfolge des Tabellenkopfs, nur ohne Annahme ueber die erste",
               "Spalte. Bei PMC5617873 steht `Placebo (n = 45)` in Spalte 1 und",
               "`Aripiprazole (n = 47)` in Spalte 2; die Regel liefert deshalb",
               "Intervention 47 und Comparator 45.", "",
               "Gold fuehrt fuer dieselben Records Intervention 45 und Comparator 47,",
               "also die Werte der Placebo-Spalte als Intervention. Ein Tausch der",
               "Regelwerte wuerde diese acht Zellen gegen Gold richtig stellen, aber",
               "dem Tabellenkopf widersprechen.", "",
               "## Was ein Tausch kostet", "",
               "Ein Tausch aller Groessenpaare stellt die acht PMC5617873-Zellen richtig,",
               "macht aber `yun2024:193` (138/131) und `yun2024:426` (49/44) falsch, also",
               "vier vorher richtige Zellen. Unterm Strich: 12 richtig / 10 falsch vorher,",
               "16 richtig / 6 falsch nachher - gegen ein Gold, das an dieser Stelle selbst",
               "vertauscht ist. Der Tabellenkopf bleibt die verlaesslichere Quelle.", ""]
    (HIER / "armreihenfolge_20261121.md").write_text("\n".join(zeilen), encoding="ascii", errors="replace")
    (HIER / "armreihenfolge_20261121.json").write_text(
        json.dumps({"gesamt": gesamt, "records": einzeln}, indent=2, ensure_ascii=True), encoding="utf-8")
    print("Faelle", len(faelle))
    for name, wert in gesamt.items():
        print(f"{name:14s} richtig {wert['richtig']} | falsch {wert['falsch']}")
    for b in einzeln:
        print(b["record_id"], [(s["spalte"], s["arm"]) for s in b["spalten"]], "gold", b["gold"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
