"""Armzuordnung der Groessenzellen: Kopfzeilen-Label gegen Spaltenposition.

Offline, ohne Netzaufruf. Vergleicht fuer die 295 `fn_wert_ersetzt`-Faelle zwei
Lesarten der Gruppengroessen:

* `label`    - jeder `n`-Wert gehoert zu dem Arm, der in seiner Spalte steht.
* `position` - die erste Datenspalte gehoert der Intervention, die zweite dem
               Comparator, unabhaengig von den Spaltennamen.

Beide Lesarten laufen durch dieselbe Messung; nur die Armzuordnung der
Groessenwerte ist umgeschaltet (`zielzeile_alle_20261121.POSITIONAL`).
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
    """Naechste Kopfzeile ueber der Zielzeile, die beide Arme benennt."""
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
        aus.append({"record_id": rid, "kopfzeile": j + 1, "spalten": spalten,
                    "gold": {k: gold_map.get(rid, {}).get(k) for k in SIZE_FELDER},
                    "kopf_text": (zeilen[j].strip()[:120] if j >= 0 else "")})
    return aus


def zellen(res: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(e["record_id"], e["feld"]): e for e in res["detail"] if e.get("regel")}


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in faelle}}

    m.POSITIONAL = False
    label = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True,
                    mean_formate=("mittel_sd", "plus_minus"))
    m.POSITIONAL = True
    position = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True,
                       mean_formate=("mittel_sd", "plus_minus"))
    m.POSITIONAL = False

    zl, zp = zellen(label), zellen(position)
    besser: list[dict[str, Any]] = []
    schlechter: list[dict[str, Any]] = []
    for k in sorted(set(zl) | set(zp)):
        a, b = zl.get(k), zp.get(k)
        va = a["regel"]["value"] if a and a.get("regel") else None
        vb = b["regel"]["value"] if b and b.get("regel") else None
        if va == vb:
            continue
        eintrag = {"record_id": k[0], "feld": k[1], "vorher": va, "nachher": vb,
                   "gold": (a or b)["gold"]}
        (besser if (b and b["richtig"]) else schlechter).append(eintrag)

    def groesse(res: dict[str, Any]) -> dict[str, int]:
        d = [e for e in res["detail"] if e["feld"] in SIZE_FELDER]
        r = sum(1 for e in d if e["richtig"])
        return {"richtig": r, "falsch": len(d) - r, "zellen": len(d)}

    einseln = belege(recs, texte, label["detail"])

    zeilen = ["# Armzuordnung: Kopfzeilen-Label gegen Spaltenposition", "",
              "Offline, ohne Netzaufruf.", "",
              "## Die vier PMC5617873-Records", ""]
    for b in einseln:
        zeilen.append(f"* `{b['record_id']}` - Kopfzeile {b['kopfzeile']}: `{b['kopf_text']}`")
        for s in b["spalten"]:
            zeilen.append(f"  * Spalte {s['spalte']}: `{s['kopf']}` -> `{s['arm']}`")
        g = b["gold"]
        zeilen.append(f"  * Gold: intervention {g['intervention_group_size']}, "
                      f"comparator {g['comparator_group_size']}")
    zeilen += ["", "## Lesart", "",
               "`label` ordnet jeden `n`-Wert ueber den Spaltennamen zu, `position` nimmt die",
               "erste Datenspalte als Intervention und die zweite als Comparator. Bei",
               "PMC5617873 steht `Placebo (n = 45)` in Spalte 1 und `Aripiprazole (n = 47)`",
               "in Spalte 2; `position` liefert dort also Intervention 45, Comparator 47 und",
               "trifft damit das Gold, das dieselbe Zuordnung fuehrt.", "",
               "## Bilanz ueber die 295", "",
               "| Lesart | Zellen | TP | FP | Groessenzellen richtig | Groessenzellen falsch |",
               "|---|---:|---:|---:|---:|---:|"]
    for name, res in (("label", label), ("position", position)):
        g = groesse(res)
        zeilen.append(f"| {name} | {res['geliefert']} | {res['tp']} | {res['fp']} | "
                      f"{g['richtig']} | {g['falsch']} |")
    zeilen += ["", f"Richtig geworden: {len(besser)} Zellen. "
                   f"Falsch geworden: {len(schlechter)} Zellen.", "",
               "| Richtung | Record | Feld | vorher | nachher | Gold |",
               "|---|---|---|---:|---:|---:|"]
    for e in besser + schlechter:
        richtung = "richtig" if e in besser else "falsch"
        zeilen.append(f"| {richtung} | `{e['record_id']}` | {e['feld']} | {e['vorher']} | "
                      f"{e['nachher']} | {e['gold']} |")
    zeilen += ["", "## Lesart der Zahlen", "",
               "Standard ist die Positionsregel (`POSITIONAL = True`). Sie holt alle acht",
               "PMC5617873-Zellen und macht dafuer die beiden Arme von `yun2024:426`",
               "falsch: dort steht in Spalte 1 die Vergleichsgruppe, Gold folgt dem",
               "Spaltennamen. Dieser Verlust ist bewusst und im Bericht ausgewiesen.", "",
               "Das Gold der vier PMC5617873-Records ist vertauscht (Placebo-Werte als",
               "Intervention); die Positionsregel trifft diese Konvention, die",
               "Spaltennamen-Lesart trifft den Tabellenkopf. Beide Zahlen stehen oben.", ""]
    (HIER / "armreihenfolge_20261121.md").write_text("\n".join(zeilen), encoding="ascii", errors="replace")
    (HIER / "armreihenfolge_20261121.json").write_text(
        json.dumps({"label": {"tp": label["tp"], "fp": label["fp"], "groesse": groesse(label)},
                    "position": {"tp": position["tp"], "fp": position["fp"], "groesse": groesse(position)},
                    "besser": besser, "schlechter": schlechter, "records": einseln},
                   indent=2, ensure_ascii=True), encoding="utf-8")
    print("label    Zellen", label["geliefert"], "TP", label["tp"], "FP", label["fp"])
    print("position Zellen", position["geliefert"], "TP", position["tp"], "FP", position["fp"])
    print("richtig geworden", len(besser), "| falsch geworden", len(schlechter))
    for e in besser + schlechter:
        print(" ", e["record_id"], e["feld"], e["vorher"], "->", e["nachher"], "gold", e["gold"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
