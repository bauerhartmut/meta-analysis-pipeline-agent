#!/usr/bin/env python3
"""Ordnet die falschen Groessenzellen der Lueckenfuellung nach Ursache.

Offline, ohne Netzaufruf. Grundlage ist derselbe Lauf wie
`umschreiben_20261121.py`: alle 699 Records, Goldfelder ohne Ereignisse, neue
Tabellenwahl an, Lueckenfuellung ohne Mittel. Fuer jede Groessenzelle, die die
Regel neu liefert, wird die Zeile mitgedruckt, in der die gelesene Zahl
tatsaechlich steht. Die Ursache ist eine manuelle Zuordnung anhand dieser Zeile
und des Goldwerts; sie steht als Tabelle `URSACHE` im Skript.

Gelesen wird dreimal (Schalter `KOPFBAND_ARM`):

* `aus`     - jede `n =`-Zeile im Kopfband zaehlt (Stand vor der Regel),
* `kuerzel` - nur ein Armkuerzel mit n (`I; n=104`),
* `arm`     - nur wenn im Kopfband eine Armbezeichnung steht (intervention,
              control, placebo, treatment, comparison).

Kategorien:

* `falsche_zeile` - die Zahl steht in einer anderen Zeile als der Goldwert
  (Bildunterschrift, Baseline-Kopfzeile statt Outcome-Zeile),
* `abweichende_definition` - die Zeile ist richtig, aber sie zaehlt eine andere
  Population (randomisiert statt ausgewertet, Charakteristika statt Outcome),
* `rechenfehler` - die gelesene Zahl passt nicht zur gedruckten Arithmetik.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/groessen_ursachen_20261121.py
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

FORMATE = ("mittel_sd", "plus_minus")
FELDART = {"group_size": "groesse", "mean": "mittel",
           "standard_deviation": "streuung", "events": "ereignis"}
STAENDE = ("aus", "kuerzel", "arm")

# Zuordnung je Zelle: (Ursache, Begruendung). Grundlage sind die gedruckten
# Zeilen der jeweiligen Tabelle, siehe `beleg` im Ergebnis.
URSACHE: dict[tuple[str, str, str], tuple[str, str]] = {
    ("yun2024:159", "intervention_group_size", "intervention"): (
        "falsche_zeile",
        "Die 24 stammt aus der Bildunterschrift 'at baseline, 12 and 24 months'; "
        "Gold 592 steht in der Armzeile 'Intervention (n=592)' der 12-Monats-Spalte."),
    ("yun2024:251", "intervention_group_size", "intervention"): (
        "abweichende_definition",
        "Kopfzeile nennt randomisiert n=406, die Outcome-Zeile rechnet mit 42/402; "
        "Gold nimmt die 402."),
    ("yun2024:251", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Kopfzeile nennt randomisiert n=393, die Outcome-Zeile rechnet mit 41/388; "
        "Gold nimmt die 388."),
    ("yun2024:252", "intervention_group_size", "intervention"): (
        "abweichende_definition",
        "Charakteristika-Tabelle nennt randomisiert n=398, Gold 402 ist der Nenner "
        "der Outcome-Zeilen."),
    ("yun2024:252", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Charakteristika-Tabelle nennt randomisiert n=389, Gold 388 ist der Nenner "
        "der Outcome-Zeilen."),
    ("yun2024:356", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Baseline-Kopfzeile nennt randomisiert n=15, Gold 13 ist die Haelfte der 26 "
        "Kinder, die die Studie abgeschlossen haben."),
    ("yun2024:420", "intervention_group_size", "intervention"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=44; Gold 18 steht als n=18 in der "
        "Outcome-Zeile 'T2w sagittal' der Bildqualitaetstabelle."),
    ("yun2024:420", "comparator_group_size", "comparator"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=49; Gold 21 steht als n=21 in "
        "derselben Outcome-Zeile."),
    ("yun2024:421", "intervention_group_size", "intervention"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=44; Gold 30 steht als n=30 in der "
        "Outcome-Zeile fuer die Brustwirbelsaeule."),
    ("yun2024:421", "comparator_group_size", "comparator"): (
        "falsche_zeile",
        "Kopfzeile der Baseline-Tabelle nennt n=49; Gold 34 steht als n=34 in "
        "derselben Outcome-Zeile."),
    ("yun2024:451", "intervention_group_size", "intervention"): (
        "abweichende_definition",
        "Die Tabellenunterschrift in Zeile 96 nennt 'I; n=104' (randomisiert), Gold 99 "
        "ist die Auswertungsgroesse der MVPA-Zeile; sie steht nicht als n im Dokument."),
    ("yun2024:451", "comparator_group_size", "comparator"): (
        "abweichende_definition",
        "Die Tabellenunterschrift in Zeile 96 nennt 'C; n=114' (randomisiert), Gold 108 "
        "ist die Auswertungsgroesse der MVPA-Zeile; sie steht nicht als n im Dokument."),
}


def art(feld: str) -> str:
    for ende, name in FELDART.items():
        if feld.endswith(ende):
            return name
    return "sonstig"


def beleg_ort(zeilen: list[str], zeile: int, wert: float,
              quelle: str) -> tuple[int | None, str, str]:
    """Zeile, in der die gelesene Zahl steht, und wie sie dort erkannt wurde.

    Gesucht wird nahe der Tabellenzeile, zuerst nach der Form `n = <zahl>`, dann
    nach einer Ueberschrift mit der Zahl, dann nach der Zahl allein. Bei
    `quelle == "unterschrift_n"` steht die Zahl in der Bildunterschrift ueber der
    Tabelle, nicht in der Tabellenzeile selbst.
    """
    zahl = str(int(wert)) if float(wert).is_integer() else str(wert)
    # `n = 104`, `*n* = 406` und `(n = 44)` sind dieselbe Form.
    muster_n = re.compile(r"\*{0,2}n\*{0,2}\s*=\s*" + re.escape(zahl))
    muster = re.compile(r"(?<![\d.])" + re.escape(zahl) + r"(?![\d])")
    if zeile < 0:
        return None, "keine", ""
    for abstand in range(0, 41):
        nah = [j for j in (zeile - abstand, zeile + abstand) if 0 <= j < len(zeilen)]
        for j in nah:
            if muster_n.search(zeilen[j]):
                return j + 1, "n-form", zeilen[j].strip()[:160]
        for j in nah:
            # Ueberschrift vor Fliesstext: die Zahl stammt aus dem Kopfband.
            if zeilen[j].lstrip().startswith("######") and muster.search(zeilen[j]):
                return j + 1, "unterschrift", zeilen[j].strip()[:160]
        if quelle != "unterschrift_n":
            for j in nah:
                if muster.search(zeilen[j]):
                    return j + 1, "zahl", zeilen[j].strip()[:160]
    return None, "keine", ""


def zellen(records: dict[str, Any], p5: dict[str, Any],
           texte: dict[str, str], texte_zeilen: dict[str, list[str]],
           kopfband_arm: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Neue Groessenzellen der Regel, je (Record, Feld, Arm)."""
    m.KOPFBAND_ARM = kopfband_arm
    aus: dict[tuple[str, str, str], dict[str, Any]] = {}
    for rid, zeile in p5.items():
        if rid not in records:
            continue
        record = records[rid]
        felder = [(str(z.get("field") or ""), v.arm_von(z), v.zahl(z.get("value")))
                  for z in (record.get("gold") or {}).get("cells") or []]
        felder = [f for f in felder if art(f[0]) == "groesse" and f[2] is not None]
        if not felder:
            continue
        text = texte[rid]
        vorher = {(str(c.get("field") or ""), v.arm_von(c)) for c in v.zellen(zeile)}
        for feld, arm, gold in felder:
            if (feld, arm) in vorher:
                continue
            neu = m.lies(record, text, feld, arm, m.alias_mod.ALIAS, True, FORMATE)
            if neu is None:
                continue
            z = neu.get("zeile")
            i = z if isinstance(z, int) else -1
            beleg_i, beleg_mode, beleg_text = beleg_ort(texte_zeilen[rid], i,
                                                        float(neu["value"]),
                                                        str(neu.get("quelle") or ""))
            aus[(rid, feld, arm)] = {
                "record_id": rid, "feld": feld, "arm": arm, "wert": neu["value"],
                "gold": gold, "richtig": abs(neu["value"] - gold) < 1e-6,
                "quelle": neu.get("quelle"), "tabellenzeile": i + 1,
                "beleg_zeile": beleg_i, "beleg_art": beleg_mode,
                "beleg_text": beleg_text,
                "gold_im_dokument": str(int(float(gold))) in text
                if float(gold).is_integer() else str(gold) in text,
            }
    return aus


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5)}
    texte: dict[str, str] = {}
    texte_zeilen: dict[str, list[str]] = {}
    for rid in p5:
        if rid not in records:
            continue
        text = (m.REPO / records[rid]["document"]["path"]).read_text(
            encoding="utf-8", errors="replace")
        texte[rid] = text
        texte_zeilen[rid] = text.splitlines()

    staende = {stand: zellen(records, p5, texte, texte_zeilen, stand)
               for stand in STAENDE}
    aus = staende["aus"]

    zellen_md: list[dict[str, Any]] = []
    for schluessel, e in aus.items():
        if e["richtig"]:
            continue
        ursache, grund = URSACHE.get(schluessel, ("offen", ""))
        eintrag = {**e, "ursache": ursache, "begruendung": grund}
        for stand in STAENDE[1:]:
            bleibt = staende[stand].get(schluessel)
            eintrag["mit_" + stand] = None if bleibt is None else {
                "wert": bleibt["wert"], "richtig": bleibt["richtig"],
                "beleg_zeile": bleibt["beleg_zeile"]}
        zellen_md.append(eintrag)

    zaehler: dict[str, int] = {}
    for e in zellen_md:
        zaehler[e["ursache"]] = zaehler.get(e["ursache"], 0) + 1
    offen = zaehler.pop("offen", 0)

    def zaehl(karte: dict[Any, dict[str, Any]]) -> dict[str, int]:
        return {"zellen": len(karte),
                "richtig": sum(1 for e in karte.values() if e["richtig"]),
                "falsch": sum(1 for e in karte.values() if not e["richtig"])}

    entfernt = {stand: {e["ursache"]: sum(1 for x in zellen_md
                                          if x["ursache"] == e["ursache"]
                                          and x["mit_" + stand] is None)
                        for e in zellen_md}
                for stand in STAENDE[1:]}
    entfernt = {stand: {k: n for k, n in z.items() if n}
                for stand, z in entfernt.items()}
    ergebnis = {"stand": "2026-11-21", "records": len(records), "p5_records": len(p5),
                "staende": {stand: zaehl(karte) for stand, karte in staende.items()},
                "ursachen": zaehler, "davon_entfernt": entfernt,
                "ohne_zuordnung": offen, "zellen": zellen_md,
                "geblieben": {stand: [e["record_id"] + "/" + e["feld"] + "/" + e["arm"]
                                      for e in zellen_md
                                      if e["mit_" + stand] is not None]
                              for stand in STAENDE[1:]}}
    (HIER / "groessen_ursachen_20261121.json").write_text(
        json.dumps(ergebnis, indent=2, ensure_ascii=True), encoding="utf-8")

    md = ["# Ursachen der falschen Groessenzellen (21.11.2026)", "",
          "Offline, ohne Netzaufruf. `groessen_ursachen_20261121.py`. Grundlage ist",
          "die Lueckenfuellung ohne Mittel ueber alle 699 Records, gemessen auf den",
          f"{len(p5)} P5-Records. Gelesen wird dreimal: ohne Kopfband-Regel (`aus`),",
          "mit Armkuerzel (`kuerzel`, z. B. `I; n=104`) und mit Armbezeichnung",
          "(`arm`, z. B. `Control group (n=15)`).", "",
          "| Stand | Groessenzellen | richtig | falsch |", "|---|---:|---:|---:|"]
    for stand in STAENDE:
        z = ergebnis["staende"][stand]
        md.append(f"| {stand} | {z['zellen']} | {z['richtig']} | {z['falsch']} |")
    md += ["", f"Von den {len(zellen_md)} falschen Zellen entfallen mit `kuerzel` "
           f"{sum(1 for e in zellen_md if e['mit_kuerzel'] is None)} und mit `arm` "
           f"{sum(1 for e in zellen_md if e['mit_arm'] is None)}.", "",
           "## Zahlen je Ursache", "", "| Ursache | Zellen | entfallen `kuerzel` "
           "| entfallen `arm` |", "|---|---:|---:|---:|"]
    for name in ("falsche_zeile", "abweichende_definition", "rechenfehler"):
        md.append(f"| {name} | {zaehler.get(name, 0)} | "
                  f"{entfernt.get('kuerzel', {}).get(name, 0)} | "
                  f"{entfernt.get('arm', {}).get(name, 0)} |")
    if offen:
        md.append(f"| offen | {offen} | - | - |")
    md += ["", "## Zellen", "",
           "| Record | Feld | Arm | Wert | Gold | Belegzeile | Beleg | Ursache "
           "| `kuerzel` | `arm` |", "|---|---|---|---:|---:|---:|---|---|---|---|"]
    for e in zellen_md:
        def stand_text(stand: str, e: dict[str, Any] = e) -> str:
            b = e["mit_" + stand]
            if b is None:
                return "entfaellt"
            return f"{b['wert']} " + ("richtig" if b["richtig"] else "falsch")

        md.append(f"| `{e['record_id']}` | {e['feld'].replace('_group_size', '')} | "
                  f"{e['arm']} | {e['wert']} | {e['gold']} | {e['beleg_zeile']} | "
                  f"{e['beleg_art']} | {e['ursache']} | {stand_text('kuerzel')} | "
                  f"{stand_text('arm')} |")
    md += ["", "## Begruendung je Zelle", ""]
    for e in zellen_md:
        md += [f"- `{e['record_id']}` {e['feld']} ({e['arm']}, Regel {e['wert']} gegen "
               f"Gold {e['gold']}): {e['begruendung']}",
               f"  Beleg Zeile {e['beleg_zeile']} ({e['beleg_art']}): "
               f"`{e['beleg_text']}`"]
    (HIER / "groessen_ursachen_20261121.md").write_text(
        "\n".join(md) + "\n", encoding="ascii", errors="replace")

    print(f"P5-Records {len(p5)}")
    for stand in STAENDE:
        print(f"  {stand:8s} {ergebnis['staende'][stand]}")
    print(f"Ursachen {zaehler} | entfallen {entfernt} | ohne Zuordnung {offen}")
    for e in zellen_md:
        print(f"  {e['record_id']:14s} {e['arm']:11s} {e['wert']:>7} gegen "
              f"{e['gold']:>7} beleg={e['beleg_zeile']} ({e['beleg_art']}) "
              f"{e['ursache']:22s} kuerzel="
              f"{'-' if e['mit_kuerzel'] is None else e['mit_kuerzel']['wert']} arm="
              f"{'-' if e['mit_arm'] is None else e['mit_arm']['wert']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
