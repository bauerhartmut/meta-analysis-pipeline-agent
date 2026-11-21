"""Die sieben verbleibenden Mittel-FP: holt sie die Tabellenlokalitaet?

Offline, ohne Netzaufruf. Fuer jede falsche Mittelzelle wird gezeigt:

* die Zielzeile, die die Regel benutzt (Zeile, Text, Tabelle),
* wo der Goldwert im Dokument steht (Zeile, Text, Tabelle),
* ob der Goldwert in der Regelzeile selbst vorkommt.

Zusaetzlich laeuft die Messung ueber die 295 mit tabellenlokaler Kopfzeilensuche
(Standard seit dieser Aenderung) und die Zahl der geaenderten Zellen wird
ausgegeben.
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

FELDER = ("intervention_mean", "comparator_mean")


FORMATE = ("mittel_sd", "plus_minus")


def stelle(zeilen: list[str], wert: float, feld: str) -> list[int]:
    """Zeilen, in denen der Wert als Mittelwert einer Zelle lesbar ist."""
    aus: list[int] = []
    for i, z in enumerate(zeilen):
        for seg in segmente(z):
            try:
                if m.wert_aus_zelle(seg, feld, FORMATE) is not None and \
                        abs(float(m.wert_aus_zelle(seg, feld, FORMATE)) - wert) < 1e-9:
                    aus.append(i)
                    break
            except (TypeError, ValueError):
                continue
    return aus


def klasse(zeilen: list[str], outcome: str, regel_tabelle: tuple[int, int],
           gold_zeilen: list[int]) -> str:
    if not gold_zeilen:
        return "gold_nicht_belegt"
    beschriftet = []
    for z in gold_zeilen:
        umfeld = " ".join(zeilen[max(0, z - 2):z + 1])
        if m.alias_mod.treffer_alias(umfeld, outcome, m.alias_mod.ALIAS, True) > 0:
            beschriftet.append(z)
    if not beschriftet:
        return "gold_anderer_abschnitt"
    if all(m.tabellengrenzen(zeilen, z) != regel_tabelle for z in beschriftet):
        return "falsche_tabelle"
    return "falsche_zeile"


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in faelle}}
    res = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True,
                  mean_formate=("mittel_sd", "plus_minus"))

    zeilen_md = ["# Die sieben Mittel-FP und die Tabellenlokalitaet", "",
                 "Offline, ohne Netzaufruf.", "",
                 "## Einzelfaelle", ""]
    faelle_md: list[dict[str, Any]] = []
    for e in res["detail"]:
        if not e["feld"].endswith("_mean") or e["richtig"]:
            continue
        rid = e["record_id"]
        zeilen = texte[rid].splitlines()
        regel_zeile = int(e["regel"]["zeile"]) - 1
        tabelle = m.tabellengrenzen(zeilen, regel_zeile)
        gold = float(e["gold"])
        gold_zeilen = stelle(zeilen, gold, e["feld"])
        gold_tabellen = [m.tabellengrenzen(zeilen, z) for z in gold_zeilen]
        k = klasse(zeilen, str((recs[rid].get("context") or {}).get("outcome") or ""),
                   tabelle, gold_zeilen)
        in_regelzeile = bool(re.search(r"(?<![\d.])" + re.escape("%g" % gold) + r"(?![\d])",
                                       zeilen[regel_zeile]))
        faelle_md.append({"record_id": rid, "feld": e["feld"], "regel": e["regel"]["value"],
                          "gold": gold, "regel_zeile": regel_zeile + 1,
                          "regel_tabelle": [tabelle[0] + 1, tabelle[1] + 1], "klasse": k,
                          "gold_in_regelzeile": in_regelzeile,
                          "gold_zeilen": [z + 1 for z in gold_zeilen],
                          "gold_tabellen": [[a + 1, b + 1] for a, b in gold_tabellen]})
    for f in faelle_md:
        zeilen_md.append(f"* `{f['record_id']}` {f['feld']}: Regel {f['regel']} (Zeile "
                         f"{f['regel_zeile']}, Tabelle {f['regel_tabelle'][0]}-{f['regel_tabelle'][1]}), "
                         f"Gold {f['gold']} (Zeilen {f['gold_zeilen']}, Tabellen "
                         f"{f['gold_tabellen']}), Klasse `{f['klasse']}`, "
                         f"Gold in der Regelzeile: {'ja' if f['gold_in_regelzeile'] else 'nein'}")
    klassen: dict[str, int] = {}
    for f in faelle_md:
        klassen[f["klasse"]] = klassen.get(f["klasse"], 0) + 1
    zeilen_md += ["", "## Klassen", "", "| Klasse | Faelle |", "|---|---:|"]
    for k, n in sorted(klassen.items()):
        zeilen_md.append(f"| {k} | {n} |")
    zeilen_md += ["", "## Messung ueber die 295", "",
                  "| Kennzahl | Wert |", "|---|---:|",
                  f"| Zellen | {res['geliefert']} |", f"| TP | {res['tp']} |",
                  f"| FP | {res['fp']} |", "",
                  "Die Kopfzeilensuche fuer Mittelspalten ist auf die Tabelle der Zielzeile",
                  "begrenzt; dadurch aendert sich keine Zelle. Mittel werden ohnehin nur aus",
                  "der Zielzeile selbst gelesen, nie aus einer Nachbarzeile oder einer",
                  "anderen Tabelle. Tabellenlokalitaet holt die sieben Zellen also nicht.", ""]
    (HIER / "mittel_fp_20261121.md").write_text("\n".join(zeilen_md), encoding="ascii", errors="replace")
    (HIER / "mittel_fp_20261121.json").write_text(
        json.dumps({"faelle": faelle_md, "klassen": klassen,
                    "messung": {"zellen": res["geliefert"], "tp": res["tp"], "fp": res["fp"]}},
                   indent=2, ensure_ascii=True), encoding="utf-8")
    print("Mittel-FP", len(faelle_md), "| Zellen", res["geliefert"], "TP", res["tp"], "FP", res["fp"])
    for f in faelle_md:
        print(f"  {f['record_id']:14s} {f['feld']:18s} {f['regel']:>6} vs {f['gold']:>6} "
              f"| {f['klasse']:20s} | Zeile {f['regel_zeile']} Tab {f['regel_tabelle']} "
              f"| Gold {f['gold_zeilen']} {f['gold_tabellen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
