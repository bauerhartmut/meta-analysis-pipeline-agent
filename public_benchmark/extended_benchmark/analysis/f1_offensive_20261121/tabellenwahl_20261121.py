#!/usr/bin/env python3
"""Tabellenwahl: Nachher-/Follow-up-Tabelle vor der Baseline-Tabelle.

Offline, ohne Netzaufruf. Die Regel nahm bisher die erste Zeile mit dem
hoechsten Alias-Treffer und damit die Baseline-Tabelle, wenn sie vor der
Nachher-Tabelle steht. Neu ist ein Kriterium auf dem Tabellenkopf:

* `tabellen_zeitpunkt` bewertet eine Tabelle mit +2 (Follow-up, Zeitpunkt,
  Woche/Monat), -2 (Baseline, Charakteristika) oder 0.
* `ziel_zeile_zeitpunkt` waehlt bei gleichem Alias-Treffer die Nachher-Tabelle,
  aber nur wenn sie ihre Arme selbst benennt (`I; n=104`). Ohne diese Bedingung
  gewaenne eine Aenderungstabelle gegen die Tabelle mit den Absolutwerten
  (PMC4987981: Gold steht in der Baseline-Tabelle).
* `armkuerzel` und `gruppenzeile_wert` lesen die Nachher-Tabelle: Armkuerzel in
  der Zeile, Gruppengroesse in der Unterschrift, Mittel als nackte Zahl.
* `wert_aus_zelle` leitet die Streuung aus einem 95%-KI ab, wenn keine SD
  gedruckt ist: SE = halbe Intervallbreite / 1.96, SD = SE * sqrt(n).

Gemessen werden die vier Records, an denen die Baseline- bzw. Haupttabelle
griff (`yun2024:196`, `447`, `448`, `450`), die 33 Zellen der Endvariante und
der P5-Pool.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/tabellenwahl_20261121.py
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
FELDER = {"intervention_group_size": "intervention",
          "comparator_group_size": "comparator",
          "intervention_mean": "intervention",
          "comparator_mean": "comparator",
          "intervention_standard_deviation": "intervention",
          "comparator_standard_deviation": "comparator"}
VIER = ("yun2024:196", "yun2024:447", "yun2024:448", "yun2024:450")


def schalter(**werte: bool) -> None:
    m.ZEITPUNKT_TABELLE = werte.get("zeitpunkt", True)
    m.TABELLE_ARMBEDINGUNG = werte.get("armbedingung", True)
    m.ARMZEILE = werte.get("armzeile", True)
    m.VORZEICHEN = werte.get("vorzeichen", True)
    m.SD_AUS_KI = werte.get("sd_ki", True)
    m.POSITIONAL = True
    m.GATE = True
    m.WOCHENSPALTE = True
    m.MESSWORT_BLOCK = True
    m.TABELLENLOKAL = True


def alt_stand() -> None:
    schalter(zeitpunkt=False, armzeile=False, vorzeichen=False, sd_ki=False)


def gold_zelle(record: dict[str, Any], feld: str) -> float | None:
    for zelle in (record.get("gold") or {}).get("cells") or []:
        if str(zelle.get("field")) == feld and zelle.get("value") is not None:
            return float(zelle["value"])
    return None


def felder_lesen(record: dict[str, Any], text: str) -> dict[str, dict[str, Any]]:
    aus: dict[str, dict[str, Any]] = {}
    for feld, arm in FELDER.items():
        gold = gold_zelle(record, feld)
        if gold is None:
            continue
        info = m.lies(record, text, feld, arm, m.alias_mod.ALIAS, True, FORMATE)
        aus[feld] = {"wert": None if info is None else info["value"],
                     "zeile": None if info is None else info.get("zeile"),
                     "quelle": None if info is None else info.get("quelle"),
                     "abgeleitet": bool((info or {}).get("abgeleitet")),
                     "herkunft": (info or {}).get("herkunft", "zelle"),
                     "gold": gold,
                     "richtig": info is not None and abs(info["value"] - gold) < 1e-6}
    return aus


def tabellen(zeilen: list[str]) -> list[tuple[int, int]]:
    """Grenzen aller Tabellen (jede Unterschrift beginnt eine neue)."""
    grenzen: list[tuple[int, int]] = []
    start = 0
    for i, zeile in enumerate(zeilen):
        if m.KAPITION.search(zeile):
            if i > start:
                grenzen.append((start, i))
            start = i
    grenzen.append((start, len(zeilen)))
    return grenzen


def sicht_je_tabelle(record: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """Was die Regel liest, wenn nur eine Tabelle des Dokuments sichtbar ist."""
    zeilen = text.splitlines()
    aus: list[dict[str, Any]] = []
    for a, b in tabellen(zeilen):
        kopf = " ".join(z for z in zeilen[a:min(b, a + 3)] if z.strip())
        kopf = " ".join(kopf.replace(":::", " ").split())[:90]
        teil = "\n".join(zeilen[a:b])
        werte = felder_lesen(record, teil)
        aus.append({"start": a + 1, "ende": b, "kopf": kopf,
                    "zeitpunkt": m.tabellen_zeitpunkt(zeilen, a, b),
                    "felder": werte,
                    "richtig": sum(1 for w in werte.values() if w["richtig"])})
    return aus


def pool_karte(zellen: dict[str, dict[str, float]], vier: dict[str, Any]) -> dict[str, Any]:
    """P5-Zellen plus die richtigen Zellen der vier Records."""
    karte = {rid: dict(c) for rid, c in zellen.items()}
    for rid, felder in vier.items():
        for feld, wert in felder.items():
            if wert["richtig"]:
                karte[rid][feld] = wert["wert"]
    return karte


def main() -> int:
    daten = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    alle = [f for f in daten["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    faelle = [f for f in alle if not f["feld"].endswith("standard_deviation")]
    streuung = [f for f in alle if f["feld"].endswith("standard_deviation")]
    recs = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = v.lade(v.P5)
    texte = {rid: (m.REPO / recs[rid]["document"]["path"]).read_text(encoding="utf-8",
                                                                     errors="replace")
             for rid in set(VIER) | {f["record_id"] for f in alle}}

    # 1. Die vier Records, vorher und nachher.
    alt_stand()
    alt = {rid: felder_lesen(recs[rid], texte[rid]) for rid in VIER}
    schalter()
    neu = {rid: felder_lesen(recs[rid], texte[rid]) for rid in VIER}

    def bilanz(stand: dict[str, dict[str, Any]], rid: str) -> dict[str, int]:
        werte = stand[rid]
        return {"felder": len(werte),
                "richtig": sum(1 for w in werte.values() if w["richtig"]),
                "geliefert": sum(1 for w in werte.values() if w["wert"] is not None),
                "vollstaendig_richtig": int(all(w["richtig"] for w in werte.values()))}

    vier: dict[str, Any] = {}
    for rid in VIER:
        vier[rid] = {"outcome": str((recs[rid].get("context") or {}).get("outcome") or ""),
                     "alt": alt[rid], "neu": neu[rid],
                     "bilanz_alt": bilanz(alt, rid), "bilanz_neu": bilanz(neu, rid)}

    # 2. Tabellen des jeweiligen Dokuments, einzeln gelesen.
    sichten = {rid: sicht_je_tabelle(recs[rid], texte[rid]) for rid in VIER}

    # 3. Die 295 Faelle: Zellstand und Streuung, je Schalter.
    staende: dict[str, Any] = {}
    for name, kw in (("neu", {}), ("ohne_zeitpunkt", {"zeitpunkt": False}),
                     ("ohne_armbedingung", {"armbedingung": False}),
                     ("ohne_armzeile", {"armzeile": False}),
                     ("ohne_vorzeichen", {"vorzeichen": False}),
                     ("ohne_sd_ki", {"sd_ki": False})):
        schalter(**kw)
        zell = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True, FORMATE)
        sd = m.messe(streuung, recs, texte, m.alias_mod.ALIAS, True, FORMATE)
        staende[name] = {"zellen": zell["geliefert"], "tp": zell["tp"], "fp": zell["fp"],
                         "streuung": {"zellen": sd["geliefert"], "tp": sd["tp"], "fp": sd["fp"]},
                         "detail": zell["detail"], "streuung_detail": sd["detail"]}
    alt_stand()
    zell_alt = m.messe(faelle, recs, texte, m.alias_mod.ALIAS, True, FORMATE)
    sd_alt = m.messe(streuung, recs, texte, m.alias_mod.ALIAS, True, FORMATE)
    staende["alt"] = {"zellen": zell_alt["geliefert"], "tp": zell_alt["tp"], "fp": zell_alt["fp"],
                      "streuung": {"zellen": sd_alt["geliefert"], "tp": sd_alt["tp"],
                                   "fp": sd_alt["fp"]},
                      "detail": zell_alt["detail"], "streuung_detail": sd_alt["detail"]}
    schalter()

    def schluessel(e: dict[str, Any]) -> tuple[str, str, str]:
        return (e["record_id"], e["feld"], e.get("arm") or "")

    alt_z = {schluessel(e): e for e in staende["alt"]["detail"]}
    neu_z = {schluessel(e): e for e in staende["neu"]["detail"]}
    zell_diff = {
        "hinzu": [{"key": list(k), "wert": neu_z[k]["regel"]["value"], "gold": neu_z[k]["gold"],
                   "richtig": neu_z[k]["richtig"]} for k in sorted(set(neu_z) - set(alt_z))],
        "entfaellt": [{"key": list(k), "wert": alt_z[k]["regel"]["value"], "gold": alt_z[k]["gold"],
                       "richtig": alt_z[k]["richtig"]} for k in sorted(set(alt_z) - set(neu_z))],
        "kippt": [{"key": list(k), "alt": alt_z[k]["regel"]["value"],
                   "neu": neu_z[k]["regel"]["value"], "gold": alt_z[k]["gold"]}
                  for k in sorted(set(alt_z) & set(neu_z))
                  if alt_z[k]["richtig"] != neu_z[k]["richtig"]],
    }
    sd_alt_d = {schluessel(e): e for e in staende["alt"]["streuung_detail"]}
    sd_neu_d = {schluessel(e): e for e in staende["neu"]["streuung_detail"]}
    sd_diff = {"hinzu": [list(k) for k in sorted(set(sd_neu_d) - set(sd_alt_d))],
               "entfaellt": [list(k) for k in sorted(set(sd_alt_d) - set(sd_neu_d))],
               "kippt": [list(k) for k in sorted(set(sd_alt_d) & set(sd_neu_d))
                         if sd_alt_d[k]["richtig"] != sd_neu_d[k]["richtig"]]}

    # 4. P5-Pool: unveraendert, mit den Feldern der alten und der neuen Regel.
    typen = {z["record_id"]: str((recs[z["record_id"]].get("context") or {}).get("outcome_type")
                                 or "") for z in p5}
    basis = {z["record_id"]: pe.p5_zellen(z) for z in p5}
    pool = {}
    for name, vier_stand in (("alt", alt), ("neu", neu)):
        karte = pool_karte(basis, vier_stand)
        e = pe.pool_stand(karte, typen)
        pool[name] = {"k": e["k"], "pooled": e["pooled"], "ci": list(e["ci"]),
                      "i2": e["i2"], "records": sorted(e["records"])}
    e0 = pe.pool_stand({rid: dict(c) for rid, c in basis.items()}, typen)
    pool["p5"] = {"k": e0["k"], "pooled": e0["pooled"], "ci": list(e0["ci"]), "i2": e0["i2"],
                  "records": sorted(e0["records"])}

    ergebnis = {"stand": "2026-11-21", "vier": vier, "sichten": sichten,
                "staende": {k: {"zellen": w["zellen"], "tp": w["tp"], "fp": w["fp"],
                                "streuung": w["streuung"]} for k, w in staende.items()},
                "zell_diff": zell_diff, "streuung_diff": sd_diff, "pool": pool}
    (HIER / "tabellenwahl_20261121.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=True), encoding="utf-8")

    # 5. Bericht.
    md = ["# Tabellenwahl: Nachher-Tabelle vor Baseline-Tabelle (21.11.2026)", "",
          "Offline, ohne Netzaufruf. `tabellenwahl_20261121.py`. Die Regel bewertet",
          "Tabellenkoepfe (`+2` Follow-up/Zeitpunkt, `-2` Baseline) und zieht bei",
          "gleichem Alias-Treffer in die Nachher-Tabelle um - aber nur, wenn diese",
          "ihre Arme in der Unterschrift nennt (`I; n=104`).", "",
          "## Die vier Records", "",
          "| Record | Outcome | Felder | richtig alt | richtig neu | vollstaendig richtig neu |",
          "|---|---|---:|---:|---:|---|"]
    for rid in VIER:
        e = vier[rid]
        md.append(f"| `{rid}` | {e['outcome']} | {e['bilanz_neu']['felder']} | "
                  f"{e['bilanz_alt']['richtig']} | {e['bilanz_neu']['richtig']} | "
                  f"{'ja' if e['bilanz_neu']['vollstaendig_richtig'] else 'nein'} |")
    md += ["", "### Zellen im Vergleich", "",
           "| Record | Feld | alt | neu | Gold | neu richtig | abgeleitet | Quelle neu |",
           "|---|---|---:|---:|---:|---|---|---|"]
    for rid in VIER:
        for feld, w in vier[rid]["neu"].items():
            a = vier[rid]["alt"][feld]
            md.append(f"| `{rid}` | {feld} | {'-' if a['wert'] is None else a['wert']} | "
                      f"{'-' if w['wert'] is None else w['wert']} | {w['gold']} | "
                      f"{'ja' if w['richtig'] else 'nein'} | "
                      f"{'ja' if w['abgeleitet'] else 'nein'} | "
                      f"{w['quelle'] or '-'} / Zeile {w['zeile'] or '-'} |")
    abgeleitet = [(rid, feld) for rid in VIER for feld, w in vier[rid]["neu"].items()
                  if w["abgeleitet"]]
    md += ["", f"Abgeleitet statt abgelesen sind {len(abgeleitet)} Zellen; gedruckt ist ",
           "keine davon, sie stammen aus dem 95%-KI der Nachher-Tabelle.",
           ""]
    md += ["", "## Tabellen der Dokumente, einzeln gelesen", "",
           "Jede Tabelle allein an die Regel gegeben; so wird sichtbar, welche Werte",
           "in welcher Tabelle stehen.", ""]
    for rid in VIER:
        md += [f"### `{rid}`", "", "| Zeile | Zeitpunkt | richtig | Tabellenkopf |",
               "|---:|---:|---:|---|"]
        for s in sichten[rid]:
            md.append(f"| {s['start']} | {s['zeitpunkt']} | {s['richtig']} | {s['kopf']} |")
        md.append("")
    md += ["## Zellstand der 295 Faelle", "",
           "| Stand | Zellen | TP | FP | Streuung Zellen | Streuung TP | Streuung FP |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for name in ("alt", "neu", "ohne_zeitpunkt", "ohne_armbedingung", "ohne_armzeile",
                 "ohne_vorzeichen", "ohne_sd_ki"):
        s = staende[name]
        md.append(f"| {name} | {s['zellen']} | {s['tp']} | {s['fp']} | "
                  f"{s['streuung']['zellen']} | {s['streuung']['tp']} | "
                  f"{s['streuung']['fp']} |")
    md += ["", f"Zellunterschiede: {len(zell_diff['hinzu'])} hinzu, "
           f"{len(zell_diff['entfaellt'])} entfallen, {len(zell_diff['kippt'])} kippen. "
           f"Streuung: {len(sd_diff['hinzu'])} hinzu, {len(sd_diff['entfaellt'])} entfaellt, "
           f"{len(sd_diff['kippt'])} kippen.", "",
           "## P5-Pool", "",
           "| Stand | k | pooled | 95 %-KI | I2 |", "|---|---:|---:|---|---:|"]
    for name in ("p5", "alt", "neu"):
        p = pool[name]
        md.append(f"| {name} | {p['k']} | {p['pooled']:.3f} | "
                  f"{p['ci'][0]:.3f} bis {p['ci'][1]:.3f} | {(p['i2'] or 0):.1f} |")
    ohne_bedingung = staende["ohne_armbedingung"]
    md += ["", "## Grenzen", "",
           "- Die Streuung der drei Records ist nicht gedruckt. Sie faellt aus dem",
           "  95%-KI (`SE = halbe Breite / 1.96`, `SD = SE * sqrt(n)`) und ist damit",
           "  eine Ableitung, kein abgelesener Wert.",
           f"- Das Kriterium zieht nur in eine Nachher-Tabelle um, die ihre Arme selbst",
           f"  benennt. Ohne diese Bedingung steht der Zellstand bei "
           f"{ohne_bedingung['zellen']} Zellen / {ohne_bedingung['tp']} TP / "
           f"{ohne_bedingung['fp']} FP und die Streuung bei "
           f"{ohne_bedingung['streuung']['zellen']} Zellen / "
           f"{ohne_bedingung['streuung']['tp']} TP: der Umzug gewinnt dann eine",
           "  Aenderungstabelle gegen die Tabelle mit den Absolutwerten",
           "  (`PMC4987981`: Gold steht in der Baseline-Tabelle).",
           "- `yun2024:196` bleibt falsch: die Tabelle mit den Goldwerten ist eine",
           "  Subgruppentabelle (MMSE-J 20 bis 23), und diese Einschraenkung steht",
           "  nicht im Record-Kontext. Auch allein gelesen liefert sie nur die beiden",
           "  Mittel (2 von 6 Feldern); Groesse und Streuung brauchen die Zeilen-n",
           "  und das KI dieser Tabelle."]
    (HIER / "tabellenwahl_20261121.md").write_text("\n".join(md) + "\n", encoding="ascii",
                                                   errors="replace")

    for rid in VIER:
        b = vier[rid]["bilanz_neu"]
        print(f"{rid:14s} richtig alt {vier[rid]['bilanz_alt']['richtig']}/{b['felder']} -> "
              f"neu {b['richtig']}/{b['felder']} | vollstaendig richtig "
              f"{'ja' if b['vollstaendig_richtig'] else 'nein'}")
    for name in ("alt", "neu"):
        s = staende[name]
        print(f"{name:5s} Zellen {s['zellen']:3d} TP {s['tp']:3d} FP {s['fp']:3d} | "
              f"Streuung {s['streuung']['zellen']}/{s['streuung']['tp']}/{s['streuung']['fp']}")
    print(f"Zellunterschiede: hinzu {len(zell_diff['hinzu'])} entfaellt "
          f"{len(zell_diff['entfaellt'])} kippt {len(zell_diff['kippt'])}")
    for name in ("p5", "alt", "neu"):
        p = pool[name]
        print(f"Pool {name:5s} k={p['k']:3d} pooled={p['pooled']:.3f} "
              f"[{p['ci'][0]:.3f}; {p['ci'][1]:.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
