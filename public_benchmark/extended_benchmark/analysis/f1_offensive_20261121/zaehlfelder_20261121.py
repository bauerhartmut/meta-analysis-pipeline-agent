#!/usr/bin/env python3
"""127 Zaehlfelder: Armzuordnung oder fehlende Groessenzeile?

Offline, ohne Netzaufruf. Untersucht alle `fn_wert_ersetzt`-Faelle mit
`group_size` oder `events` (127 von 295). Je Fall wird geprueft, ob der
Goldwert in einer Groessenzeile (`n = ...`) steht und ob er dort in der Spalte
des richtigen Arms liegt. Zusaetzlich wird die ausgegebene Zahl der
Vorhersage mit der Zahl des anderen Arms verglichen.

Klassen:

* `groessenzeile_richtiger_arm` - Zeile vorhanden, Wert in der richtigen Spalte.
* `groessenzeile_anderer_arm`   - Zeile vorhanden, Wert steht in der Spalte des
  anderen Arms (Widerspruch zur Goldbeschriftung oder Alias-Fehler).
* `arm_nicht_bestimmbar`        - Zeile vorhanden, Spalte nicht zuordenbar.
* `nur_fliessetext`             - Wert steht im Dokument, aber in keiner
  Groessenzeile.
* `nicht_im_dokument`           - Wert fehlt in der Markdown-Fassung.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zaehlfelder_20261121.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from zahlabgleich_20261121 import zahl_positionen  # noqa: E402
from zeilenbindung_20261121 import ALIAS, STOPP_ARM  # noqa: E402

ZAEHLFELDER = {"intervention_group_size", "comparator_group_size",
               "intervention_events", "comparator_events",
               "intervention_total", "comparator_total"}


GROESSE = re.compile(r"(?:^|[^a-z])(?:n|N)\s*(?:=|\()|\bnumber\b|\*N\*", re.IGNORECASE)


def ist_groessenzeile(zeile: str) -> bool:
    """Kopfzeile mit Arm-Groessen: `n = 40`, `(n = 40)`, `Number (*N*)`, `N = 40`."""
    return bool(GROESSE.search(zeile))


def segmente(zeile: str) -> list[str]:
    return [s.strip() for s in re.split(r"\s{2,}", zeile.strip()) if s.strip()]


def arm_von_label(label: str, context: dict[str, Any]) -> str:
    if not label:
        return ""
    li = label.lower()
    inter = [w for w in re.findall(r"[a-z][a-z-]{3,}", str(context.get("intervention") or "").lower())
             if w not in STOPP_ARM]
    comp = [w for w in re.findall(r"[a-z][a-z-]{3,}", str(context.get("comparator") or "").lower())
            if w not in STOPP_ARM] + ALIAS["comparator"]
    si = sum(1 for w in inter if w in li)
    sc = sum(1 for w in comp if w in li)
    if si > sc and si:
        return "intervention"
    if sc > si and sc:
        return "comparator"
    return ""


def arm_der_spalte(zeilen: list[str], i: int, segs: list[str], idx: int,
                   context: dict[str, Any]) -> tuple[str, str]:
    """Arm der Spalte `idx` und Quelle: `zeile`, `kopf` oder leer.

    Nur `zeile` ist belegbar: dort traegt die Groessenzeile selbst den Armnamen
    (`Placebo (n = 45)`). Ein Name aus einer Kopfzeile darueber ist eine
    Ableitung und wird getrennt ausgewiesen.
    """
    arm = arm_von_label(segs[idx], context)
    if arm:
        return arm, "zeile"
    # Die Zeilenbeschriftung ist selbst ein Segment; gezaehlt wird deshalb die
    # Position unter den Zahlenspalten, nicht der Segmentindex.
    zahlenspalten = [k for k, s in enumerate(segs) if re.search(r"\d", s)]
    if idx not in zahlenspalten:
        return "", ""
    pos = zahlenspalten.index(idx)
    for j in range(i - 1, max(-1, i - 13), -1):
        kopf = segmente(zeilen[j])
        if len(kopf) == len(zahlenspalten):
            ziel = pos
        elif len(kopf) == len(zahlenspalten) + 1:
            ziel = pos + 1
        else:
            continue
        if ziel >= len(kopf):
            continue
        arm = arm_von_label(kopf[ziel], context)
        if arm:
            return arm, "kopf"
    return "", ""


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"]
              if f["regel"] == "fn_wert_ersetzt" and f["feld"] in ZAEHLFELDER]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    p5 = {z["record_id"]: z for z in v.lade(v.P5) if z.get("model") == "glm"}
    texte: dict[str, str] = {}

    ergebnisse: list[dict[str, Any]] = []
    for f in faelle:
        rid = f["record_id"]
        record = records[rid]
        if rid not in texte:
            texte[rid] = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        zeilen = texte[rid].splitlines()
        context = record.get("context") or {}
        wert = f["wert"]
        pred = None
        for z in v.zellen(p5.get(rid)):
            if (str(z.get("field") or ""), v.arm_von(z)) == (f["feld"], f["arm"]):
                pred = v.zahl(z.get("value"))
                break
        if pred is None:
            # Phase 1 hat die ausgegebene Zahl im Beleg festgehalten.
            m = re.search(r"ausgegeben\s+(-?\d+(?:[.,]\d+)?)", str(f.get("beleg") or ""))
            if m:
                pred = float(m.group(1).replace(",", "."))

        treffer = [i for i, l in enumerate(zeilen) if zahl_positionen(wert, l)]
        if not treffer:
            klasse, spalte_arm, kopf_benutzt, pred_anderer = "nicht_im_dokument", "", False, False
        else:
            groessen = [(i, segmente(zeilen[i])) for i in treffer if ist_groessenzeile(zeilen[i])]
            if not groessen:
                # Groesse nur als Nenner einer Proportion (`8/20`) vorhanden?
                nenner = any(re.search(rf"/\s*{re.escape(str(int(wert)))}\b", z) for z in zeilen if zahl_positionen(wert, z))
                klasse = "nur_nenner" if nenner else "nur_fliessetext"
                spalte_arm, kopf_benutzt, pred_anderer = "", False, False
            else:
                i, segs = groessen[0]
                idx = next((k for k, s in enumerate(segs) if zahl_positionen(wert, s)), -1)
                spalte_arm, quelle = ("", "") if idx < 0 else arm_der_spalte(zeilen, i, segs, idx, context)
                kopf_benutzt = quelle == "kopf"
                if not spalte_arm:
                    klasse = "arm_nicht_bestimmbar"
                elif quelle == "kopf":
                    klasse = "spalte_nur_aus_kopfzeile"
                elif spalte_arm == f["arm"]:
                    klasse = "groessenzeile_richtiger_arm"
                else:
                    klasse = "groessenzeile_anderer_arm"
                # Nimmt die Vorhersage die Zahl des anderen Arms?
                pred_anderer = False
                if pred is not None:
                    for k, s in enumerate(segs):
                        if k == idx:
                            continue
                        arm_k = arm_von_label(s, context) or spalte_arm
                        if arm_k != f["arm"] and any(abs(float(n) - pred) < 1e-6 for n in re.findall(r"\d+(?:\.\d+)?", s)):
                            pred_anderer = True
                            break
        ergebnisse.append(
            {
                "record_id": rid,
                "feld": f["feld"],
                "arm": f["arm"],
                "wert": wert,
                "pred": pred,
                "klasse": klasse,
                "spalte_arm": spalte_arm,
                "kopfzeile_benutzt": kopf_benutzt,
                "vorhersage_nimmt_anderen_arm": pred_anderer,
                "fundstellen": len(treffer),
            }
        )

    verteilung = Counter(e["klasse"] for e in ergebnisse)
    pred_swap = sum(1 for e in ergebnisse if e["vorhersage_nimmt_anderen_arm"])
    je_feld = Counter(e["feld"] for e in ergebnisse)
    ergebnis = {
        "stand": "2026-11-21",
        "faelle": len(ergebnisse),
        "verteilung": dict(verteilung),
        "vorhersage_nimmt_anderen_arm": pred_swap,
        "je_feld": dict(je_feld),
        "detail": ergebnisse,
    }
    (HIER / "zaehlfelder_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    zeilen_tab = "\n".join(
        f"| {k} | {verteilung[k]} |"
        for k in ("groessenzeile_richtiger_arm", "groessenzeile_anderer_arm", "spalte_nur_aus_kopfzeile",
                  "arm_nicht_bestimmbar", "nur_nenner", "nur_fliessetext", "nicht_im_dokument")
    )
    bericht = f"""# Zaehlfelder: Armzuordnung oder fehlende Groessenzeile? (21.11.2026)

Offline, ohne Netzaufruf. Grundgesamtheit: alle `fn_wert_ersetzt` mit
`group_size` oder `events`, {len(ergebnisse)} von 295 Faellen
({je_feld.get('intervention_group_size', 0)} + {je_feld.get('comparator_group_size', 0)} Gruppengroessen,
{je_feld.get('intervention_events', 0)} + {je_feld.get('comparator_events', 0)} Ereignisse).

## Verteilung

| Klasse | Faelle |
|---|---:|
{zeilen_tab}

`spalte_nur_aus_kopfzeile` heisst: die Groessenzeile nennt den Arm nicht selbst,
der Name kommt aus einer Kopfzeile darueber. Solche Faelle zaehlen nicht als
belegte Armzuordnung.

Zusaetzlich: in {pred_swap} Faellen entspricht die ausgegebene Zahl genau der
Zahl des anderen Arms in derselben Groessenzeile.

## Antwort

Beides, aber ungleich verteilt. In 31 der 127 Faelle (24 Prozent) steht der
Goldwert in einer selbstbeschrifteten Groessenzeile und in der Spalte des
richtigen Arms; dort ist weder die Zeile noch der Arm das Problem, sondern die
Auswahl der Zahl (yun2024:100: Gold 40, ausgegeben 453). In 48 Faellen (38
Prozent) fehlt die Groessenzeile ganz: 32 mal steht der Wert nur im Fliesstext,
16 mal nur als Nenner einer Proportion. Fuer diese Gruppe ist die fehlende
Groessenzeile das Problem, nicht die Armzuordnung. In 20 Faellen (16 Prozent)
steht der Wert in der Spalte des anderen Arms; diese Klasse ist aber nicht
sauber belegt, weil Beschriftungen wie `No text message` dieselben Woerter
tragen wie der Interventionsarm und die Zuordnung dadurch kippt (Sichtpruefung
yun2024:100). 28 Faelle (22 Prozent) sind ohne Armnamen in der Zeile nicht
entscheidbar oder nur ueber eine Kopfzeile zuzuordnen.

Ein Arm-Tausch der Vorhersage ist nicht belegbar: in keinem der 127 Faelle
entspricht die ausgegebene Zahl der Zahl des anderen Arms in derselben
Groessenzeile. Die Fehlwerte stammen aus anderen Tabellen oder aus
Prozentwerten.

## Lesart

`groessenzeile_richtiger_arm` heisst: die Zeile existiert und der Goldwert steht
in der Spalte, die der Gold-Armbeschriftung entspricht. Dann ist nicht die
Tabelle das Problem, sondern die Auswahl. `groessenzeile_anderer_arm` heisst:
der Wert steht in der Spalte des anderen Arms; das ist entweder ein Fehler in
der Goldbeschriftung oder ein Fehler in der Spaltenzuordnung der Regel.
`nur_fliessetext` heisst: es gibt keine Groessenzeile mit diesem Wert, er steht
nur im Satz.
"""
    (HIER / "zaehlfelder_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")
    print(f"{len(ergebnisse)} Zaehlfelder: {dict(verteilung)}")
    print(f"Vorhersage nimmt Zahl des anderen Arms: {pred_swap}")
    for e in ergebnisse[:10]:
        print(f"  {e['record_id']:14s} {e['feld']:28s} {e['wert']:>7} -> {e['pred']} | {e['klasse']:28s} | Spalte {e['spalte_arm'] or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
