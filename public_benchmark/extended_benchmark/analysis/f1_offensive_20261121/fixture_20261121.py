"""Fixture und Ablation der Endvariante (295 Faelle), offline ohne Netzaufruf.

Zwei Modi:

* `schreiben` - rechnet die Endvariante, schreibt die Zellen und die Ablation
  der vier Bausteine nach `fixture_20261121.json`.
* `pruefen`   - rechnet erneut und vergleicht mit der Fixture; jede Abweichung
  wird gemeldet, der Rueckgabewert ist dann 1.

Die Fixture haelt je Zelle Record, Feld, Arm, Wert, Gold, Zeile und Quelle fest.
Damit kann eine spaetere Aenderung an den Bausteinen keine Treffer still
kosten.
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

FIXTURE = HIER / "fixture_20261121.json"
FORMATE = ("mittel_sd", "plus_minus")


def schalter(**werte: bool) -> None:
    m.POSITIONAL = werte.get("positional", True)
    m.GATE = werte.get("gate", True)
    m.WOCHENSPALTE = werte.get("wochenspalte", True)
    m.MESSWORT_BLOCK = werte.get("messwort", True)
    m.TABELLENLOKAL = werte.get("tabellenlokal", True)
    m.ZEITPUNKT_TABELLE = werte.get("zeitpunkt", True)
    m.TABELLE_ARMBEDINGUNG = werte.get("armbedingung", True)
    m.ARMZEILE = werte.get("armzeile", True)
    m.VORZEICHEN = werte.get("vorzeichen", True)
    m.SD_AUS_KI = werte.get("sd_ki", True)


def lauf(faelle: list[dict[str, Any]], recs: dict[str, dict[str, Any]],
         texte: dict[str, str]) -> dict[str, Any]:
    return m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True, mean_formate=FORMATE)


def zellen(res: dict[str, Any]) -> list[dict[str, Any]]:
    aus: list[dict[str, Any]] = []
    for e in res["detail"]:
        if not e.get("regel"):
            continue
        aus.append({"record_id": e["record_id"], "feld": e["feld"], "arm": e.get("arm"),
                    "wert": e["regel"]["value"], "gold": e["gold"], "richtig": e["richtig"],
                    "zeile": e["regel"].get("zeile"), "quelle": e["regel"].get("quelle")})
    return sorted(aus, key=lambda x: (x["record_id"], x["feld"], x["arm"] or ""))


def kennzahlen(res: dict[str, Any]) -> dict[str, int]:
    return {"zellen": res["geliefert"], "tp": res["tp"], "fp": res["fp"]}


def main(argv: list[str]) -> int:
    modus = argv[1] if len(argv) > 1 else "schreiben"
    daten = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    alle_faelle = [f for f in daten["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    faelle = [f for f in alle_faelle if not f["feld"].endswith("standard_deviation")]
    streuung_faelle = [f for f in alle_faelle if f["feld"].endswith("standard_deviation")]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte = {rid: (Path(".") / recs[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")
             for rid in {f["record_id"] for f in alle_faelle}}

    ablation: dict[str, dict[str, int]] = {}
    schalter()
    basis = lauf(faelle, recs, texte)
    ablation["endvariante"] = kennzahlen(basis)
    basis_zellen = zellen(basis)
    # Zweiter Stand: ohne Gate, damit der Pruefmodus beide Varianten
    # zellgenau vergleicht.
    schalter(gate=False)
    ohne_gate = lauf(faelle, recs, texte)
    ohne_gate_zellen = zellen(ohne_gate)
    # Streuung als eigenes Feld: eigener Stand, eigener Vergleich.
    streuung = lauf(streuung_faelle, recs, texte)
    streuung_zellen = zellen(streuung)
    ablation["streuung"] = kennzahlen(streuung)
    schalter()
    for name, kwargs in (("ohne_gate", {"gate": False}),
                         ("ohne_positionsregel", {"positional": False}),
                         ("ohne_wochenspalte", {"wochenspalte": False}),
                         ("ohne_messwort_block", {"messwort": False}),
                         ("ohne_tabellenlokal", {"tabellenlokal": False}),
                         ("ohne_zeitpunkt", {"zeitpunkt": False}),
                         ("ohne_armbedingung", {"armbedingung": False}),
                         ("ohne_armzeile", {"armzeile": False}),
                         ("ohne_vorzeichen", {"vorzeichen": False})):
        schalter(**kwargs)
        ablation[name] = kennzahlen(lauf(faelle, recs, texte))
    schalter()

    if modus == "pruefen":
        if not FIXTURE.exists():
            print("keine Fixture vorhanden:", FIXTURE)
            return 1
        alt = json.loads(FIXTURE.read_text(encoding="utf-8"))
        probleme = 0
        if alt["ablation"] != ablation:
            probleme += 1
            print("Ablation weicht ab:")
            for name in sorted(set(alt["ablation"]) | set(ablation)):
                vorher = alt["ablation"].get(name)
                jetzt = ablation.get(name)
                if vorher != jetzt:
                    print(f"  {name}: {vorher} -> {jetzt}")
        for stand, alt_liste, neu_liste in (("gate", alt["zellen"], basis_zellen),
                                            ("ohne_gate", alt.get("zellen_ohne_gate", []),
                                             ohne_gate_zellen),
                                            ("streuung", alt.get("zellen_streuung", []),
                                             streuung_zellen)):
            alt_schluessel = {(z["record_id"], z["feld"], z["arm"]): z for z in alt_liste}
            neu_schluessel = {(z["record_id"], z["feld"], z["arm"]): z for z in neu_liste}
            fehlend = sorted(set(alt_schluessel) - set(neu_schluessel))
            neu = sorted(set(neu_schluessel) - set(alt_schluessel))
            geaendert = [k for k in set(alt_schluessel) & set(neu_schluessel)
                         if alt_schluessel[k]["wert"] != neu_schluessel[k]["wert"]
                         or alt_schluessel[k]["richtig"] != neu_schluessel[k]["richtig"]]
            for k in fehlend:
                probleme += 1
                print(f"  [{stand}] fehlt:", k)
            for k in neu:
                probleme += 1
                print(f"  [{stand}] neu:", k)
            for k in sorted(geaendert):
                probleme += 1
                print(f"  [{stand}] geaendert: {k} {alt_schluessel[k]['wert']} -> "
                      f"{neu_schluessel[k]['wert']} (richtig {alt_schluessel[k]['richtig']} -> "
                      f"{neu_schluessel[k]['richtig']})")
        print(f"Fixture {FIXTURE.name}: {len(alt['zellen'])} Zellen mit Gate, "
              f"{len(alt.get('zellen_ohne_gate', []))} ohne Gate | Abweichungen {probleme}")
        return 1 if probleme else 0

    inhalt = {"stand": "2026-11-21", "faelle": len(faelle), "ablation": ablation,
              "zellen": basis_zellen, "zellen_ohne_gate": ohne_gate_zellen,
              "zellen_streuung": streuung_zellen}
    FIXTURE.write_text(json.dumps(inhalt, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"geschrieben: {FIXTURE.name} | Zellen {len(basis_zellen)} mit Gate, "
          f"{len(ohne_gate_zellen)} ohne Gate")
    for name, k in ablation.items():
        print(f"  {name:22s} Zellen {k['zellen']:3d} TP {k['tp']:3d} FP {k['fp']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
