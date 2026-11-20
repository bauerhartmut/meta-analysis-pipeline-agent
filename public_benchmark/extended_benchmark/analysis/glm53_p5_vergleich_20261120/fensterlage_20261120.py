#!/usr/bin/env python
"""Wo liegen die Goldwerte der 33 P5-Abbrueche relativ zum 6.000er-Fenster?

Rein lesend, kein Modellaufruf, kein Netz. Beantwortet drei Fragen:

1. Wie viele der 33 Abbrueche haben *null* Goldwerte im 6.000er-Fenster, und
   steht der Goldwert dann ueberhaupt im Dokument (oder nur in einer
   Bildtabelle, die im Markdown als Caption steht)?
2. Liegt ein Wert im Dokument, aber ausserhalb des Fensters: wie weit weg, und
   schliesst ihn eine andere *blinde* Startregel ein?
3. Wie viele Werte sind mit *keinem* 6.000er-Fenster erreichbar, weil sie im
   Dokument weit auseinander stehen? Das ist die Obergrenze fuer jede
   Fensterheuristik.

Fensterdefinition und Bewertung sind aus `zweistufig_trocken_20261120.py`
uebernommen (BREITE 6.000, Schritt 500, 3 x Outcome-Treffer + 2 x
Tabellenzeilen + Ziffern/100). Die Zahlenlesart ist die aus
`falschwert_20261120.py` (Trennzeichen nur als Tausendergruppen), damit
"13,6" und "13.6" gleich behandelt werden.

Blinde Startregeln (kein Goldwissen, nur Text, Outcome und Zielzeitpunkt):

* `score`          : das Fenster aus `waehle_ausschnitt`.
* `outcome_erste`  : Mitte auf das erste Vorkommen des Outcome-Ausdrucks.
* `outcome_letzte` : Mitte auf das letzte Vorkommen.
* `tabelle_mitte`  : Mitte auf den Schwerpunkt der Tabellenzeilen.
* `zeitpunkt`      : Mitte auf den Zielzeitpunkt, wie er gedruckt ist.
* `anker_max`      : Kandidaten an jedem Outcome-Vorkommen und jeder
                     Tabellenzeile, je als Mitte, linke und rechte Kante;
                     gewaehlt wird der beste Score. Damit ist diese Regel
                     mindestens so gut wie `score` und prueft, ob die
                     Fensterlage oder die Bewertungsfunktion das Problem ist.
* `mehrfach_3x2000`: drei disjunkte Fenster zu 2.000 Zeichen, gierig nach
                     Score. Prueft, ob mehrere kleine Ausschnitte mehr Werte
                     abdecken als ein grosses Fenster.

`orakel_6000` ist keine Regel, sondern die Obergrenze: das 6.000er-Fenster,
das die meisten Goldwerte enthaelt (Kandidaten alle 100 Zeichen plus jede
Wertstelle als Mitte und als rechte Kante). Was dort fehlt, ist mit einem
einzelnen Fenster dieser Breite nicht erreichbar.

Abdeckung heisst: der Wert steht irgendwo im Fenster. Ob er dort zur richtigen
Zeile und zum richtigen Arm gehoert, prueft diese Messung nicht; sie ist eine
Obergrenze, keine Trefferquote.

Aufruf:
    .venv/bin/python .../fensterlage_20261120.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from falschwert_20261120 import TOKEN, lesarten  # noqa: E402
from zweistufig_trocken_20261120 import (  # noqa: E402
    BREITE,
    SCHRITT,
    zaehle,
    tabellenzeilen,
    waehle_ausschnitt,
)

MUSTER = HIER / "leere_p5_muster_20261120.json"
AUS_JSON = HIER / "fensterlage_20261120.json"
AUS_MD = HIER / "p5_fensterlage_20261120.md"
STUECK = 2000
STUECKE = 3
NAMEN = ["score", "outcome_erste", "outcome_letzte", "tabelle_mitte", "zeitpunkt",
         "anker_max", "mehrfach_3x2000", "orakel_6000"]


def bewertung(fenster: str, stichworte: list[str]) -> float:
    return (3 * zaehle(fenster, stichworte)
            + 2 * tabellenzeilen(fenster)
            + len(re.findall(r"\d", fenster)) / 100)


def werte_index(text: str, werte: list[float]) -> dict[float, list[tuple[int, int]]]:
    """Alle Stellen je Goldwert unter der Zahlenlesart aus falschwert_*.py."""
    index: dict[float, list[tuple[int, int]]] = {w: [] for w in werte}
    if not werte:
        return index
    for treffer in TOKEN.finditer(text):
        for zahl in lesarten(treffer.group(0)):
            schluessel = round(zahl, 6)
            if schluessel in index:
                index[schluessel].append((treffer.start(), treffer.end()))
    return index


def kontext(text: str, stelle: tuple[int, int]) -> str:
    von = max(0, stelle[0] - 40)
    return " ".join(text[von:stelle[1] + 25].split())


def start_um(text: str, mitte: float) -> int:
    if len(text) <= BREITE:
        return 0
    return max(0, min(len(text) - BREITE, int(mitte) - BREITE // 2))


def start_score(text: str, stichworte: list[str]) -> int:
    return waehle_ausschnitt(text, stichworte, BREITE, SCHRITT)["start"]


def outcome_stellen(text: str, outcome: str, stichworte: list[str]) -> list[int]:
    klein = text.lower()
    stellen: list[int] = []
    phrase = (outcome or "").strip().lower()
    if phrase:
        stellen += [m.start() for m in re.finditer(re.escape(phrase), klein)]
    if not stellen:
        for wort in stichworte:
            stellen += [m.start() for m in re.finditer(re.escape(wort.lower()), klein)]
    return sorted(set(stellen))


def tabellen_stellen(text: str) -> list[int]:
    stellen = []
    offset = 0
    for zeile in text.splitlines(keepends=True):
        if zeile.lstrip().startswith("|") or zeile.count("|") >= 2:
            stellen.append(offset)
        offset += len(zeile)
    return stellen


def abgedeckt(index: dict[float, list[tuple[int, int]]], start: int, ende: int) -> int:
    return sum(1 for stellen in index.values()
               if any(start <= s[0] < ende for s in stellen))


def regeln(text: str, stichworte: list[str], outcome: str,
           zielzeitpunkt: str, index: dict[float, list[tuple[int, int]]]) -> dict[str, Any]:
    """Blinde Startregeln plus Orakel; je Regel Start, Ende und Abdeckung."""
    if len(text) <= BREITE:
        ganz = {"start": 0, "ende": len(text), "abgedeckt": abgedeckt(index, 0, len(text))}
        return {name: dict(ganz) for name in NAMEN} | {"ganzer_text": dict(ganz)}
    base = start_score(text, stichworte)
    ergebnis: dict[str, Any] = {
        "score": {"start": base, "ende": base + BREITE,
                  "abgedeckt": abgedeckt(index, base, base + BREITE)},
    }

    pos_outcome = outcome_stellen(text, outcome, stichworte)
    for name, pos in (("outcome_erste", pos_outcome[:1]),
                      ("outcome_letzte", pos_outcome[-1:])):
        if pos:
            start = start_um(text, pos[0])
            ergebnis[name] = {"start": start, "ende": start + BREITE,
                              "abgedeckt": abgedeckt(index, start, start + BREITE)}

    pos_tabelle = tabellen_stellen(text)
    if pos_tabelle:
        start = start_um(text, sum(pos_tabelle) / len(pos_tabelle))
        ergebnis["tabelle_mitte"] = {"start": start, "ende": start + BREITE,
                                     "abgedeckt": abgedeckt(index, start, start + BREITE)}

    ziel = (zielzeitpunkt or "").strip()
    if ziel:
        stellen = [m.start() for m in re.finditer(re.escape(ziel.lower()), text.lower())]
        if stellen:
            start = start_um(text, stellen[0])
            ergebnis["zeitpunkt"] = {"start": start, "ende": start + BREITE,
                                     "abgedeckt": abgedeckt(index, start, start + BREITE)}

    kandidaten = {base}
    for pos in pos_outcome + pos_tabelle:
        kandidaten.update({start_um(text, pos), max(0, min(len(text) - BREITE, pos)),
                           max(0, min(len(text) - BREITE, pos - BREITE + 1))})
    bestes = max(kandidaten, key=lambda s: (bewertung(text[s:s + BREITE], stichworte), -s))
    ergebnis["anker_max"] = {"start": bestes, "ende": bestes + BREITE,
                             "abgedeckt": abgedeckt(index, bestes, bestes + BREITE)}

    # Drei disjunkte Stuecke zu 2.000 Zeichen, gierig nach Score.
    frei = [True] * (len(text) // 250 + 2)
    stuecke = []
    for _ in range(STUECKE):
        bestes_stueck = None
        for start in range(0, len(text) - STUECK + 1, 250):
            if not all(frei[start // 250:(start + STUECK) // 250 + 1]):
                continue
            note = bewertung(text[start:start + STUECK], stichworte)
            if bestes_stueck is None or note > bestes_stueck[0]:
                bestes_stueck = (note, start)
        if bestes_stueck is None:
            break
        _, start = bestes_stueck
        stuecke.append((start, start + STUECK))
        for i in range(start // 250, (start + STUECK) // 250 + 1):
            if i < len(frei):
                frei[i] = False
    ergebnis["mehrfach_3x2000"] = {
        "stuecke": stuecke,
        "abgedeckt": sum(1 for stellen in index.values()
                         if any(s[0] < ende and s[1] > start
                                for start, ende in stuecke for s in stellen)),
    }

    # Orakel: bestes 6.000er-Fenster fuer die Goldwerte selbst.
    kandidaten = set(range(0, max(1, len(text) - BREITE + 1), 100))
    for stellen in index.values():
        for s in stellen:
            kandidaten.add(max(0, min(len(text) - BREITE, s[0] - BREITE // 2)))
            kandidaten.add(max(0, min(len(text) - BREITE, s[0] - BREITE + 1)))
    orakel = max(kandidaten,
                 key=lambda s: (abgedeckt(index, s, s + BREITE), -s))
    ergebnis["orakel_6000"] = {"start": orakel, "ende": orakel + BREITE,
                               "abgedeckt": abgedeckt(index, orakel, orakel + BREITE)}
    return ergebnis


def main() -> int:
    muster = json.loads(MUSTER.read_text(encoding="utf-8"))["faelle"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: dict[str, Any] = {}

    for rid, m in muster.items():
        if "klasse" not in m or rid not in records:
            continue
        record = records[rid]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        context = record.get("context") or {}
        outcome = str(context.get("outcome") or "")
        ziel = str((record.get("timepoint") or {}).get("target") or "")
        stichworte = [w for w in re.split(r"[\s/,()-]+", outcome) if len(w) >= 4]
        if not stichworte and outcome:
            stichworte = [outcome]

        zellen = (record.get("gold") or {}).get("cells") or []
        werte = sorted({round(float(z["value"]), 6) for z in zellen
                        if z.get("value") is not None})
        index = werte_index(text, werte)

        wahl = waehle_ausschnitt(text, stichworte, BREITE, SCHRITT)
        start, ende = wahl["start"], wahl["ende"]
        im_fenster = [w for w in werte if any(start <= s[0] < ende for s in index[w])]
        im_text = [w for w in werte if index[w]]
        ausserhalb = []
        for wert in werte:
            if wert in im_fenster or not index[wert]:
                continue
            abst = min(min(abs(s[0] - start), abs(s[0] - ende)) for s in index[wert])
            richtung = ("davor" if all(s[0] < start for s in index[wert])
                        else "danach" if all(s[0] >= ende for s in index[wert])
                        else "teils davor, teils danach")
            ausserhalb.append({
                "wert": wert,
                "stellen": len(index[wert]),
                "abstand_zeichen": abst,
                "richtung": richtung,
                "kontext": [kontext(text, s) for s in index[wert][:3]],
            })

        regelwerte = regeln(text, stichworte, outcome, ziel, index)
        for name, r in regelwerte.items():
            intervalle = r.get("stuecke") or [(r["start"], r["ende"])]
            r["zellen_abgedeckt"] = sum(
                1 for z in zellen
                if z.get("value") is not None
                and any(a <= s[0] < b for a, b in intervalle
                        for s in index.get(round(float(z["value"]), 6), []))
            )

        faelle[rid] = {
            "record_id": rid,
            "dokument": m.get("dokument"),
            "klasse": m["klasse"],
            "outcome": outcome,
            "zielzeitpunkt": ziel,
            "text_zeichen": len(text),
            "goldzellen": len(zellen),
            "werte_gesamt": len(werte),
            "werte_im_text": len(im_text),
            "werte_im_fenster": len(im_fenster),
            "werte_ausserhalb": len(ausserhalb),
            "werte_nirgends": len(werte) - len(im_text),
            "fenster": {"start": start, "ende": ende, "zeichen": wahl["ende"] - wahl["start"],
                        "outcome_treffer": wahl["outcome_treffer"],
                        "tabellenzeilen": wahl["tabellenzeilen"],
                        "bewertung": round(wahl["bewertung"], 2) if wahl["bewertung"] is not None else None},
            "ausserhalb_details": ausserhalb,
            "regeln": regelwerte,
        }

    reihenfolge = list(faelle)
    null_fenster = [r for r in reihenfolge if faelle[r]["werte_im_fenster"] == 0]
    namen = NAMEN
    regeln_summe: dict[str, Any] = {}
    for name in namen:
        mit = [r for r in reihenfolge if name in faelle[r]["regeln"]]
        regeln_summe[name] = {
            "records": len(mit),
            "mindestens_ein_wert": sum(1 for r in mit if faelle[r]["regeln"][name]["abgedeckt"] >= 1),
            "mindestens_zwei_werte": sum(1 for r in mit if faelle[r]["regeln"][name]["abgedeckt"] >= 2),
            "werte": sum(faelle[r]["regeln"][name]["abgedeckt"] for r in mit),
            "zellen": sum(faelle[r]["regeln"][name]["zellen_abgedeckt"] for r in mit),
        }

    orakel_werte = sum(faelle[r]["regeln"]["orakel_6000"]["abgedeckt"] for r in reihenfolge)
    werte_gesamt = sum(faelle[r]["werte_gesamt"] for r in reihenfolge)
    werte_im_text = sum(faelle[r]["werte_im_text"] for r in reihenfolge)
    ergebnis = {
        "n": len(faelle),
        "fenster_breite": BREITE,
        "schritt": SCHRITT,
        "werte_gesamt": werte_gesamt,
        "werte_im_text": werte_im_text,
        "werte_nirgends": werte_gesamt - werte_im_text,
        "null_im_fenster": null_fenster,
        "regeln": regeln_summe,
        "orakel_werte": orakel_werte,
        "orakel_nicht_erreichbar": werte_im_text - orakel_werte,
        "faelle": faelle,
    }
    AUS_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    def pct(a: int, b: int) -> str:
        return f"{100 * a / b:.1f} %" if b else "-"

    md = [
        f"# Fensterlage der 33 P5-Abbrueche (20.11.2026)",
        "",
        "Rein offline: Goldwerte gegen Dokumenttext und gegen das 6.000er-Fenster "
        "aus `zweistufig_trocken_20261120.py`. Kein Modellaufruf, kein Netz, Gold "
        "und Predictions unveraendert.",
        "",
        "## Zahlpruefung vorab",
        "",
        f"- Records: **{len(faelle)}** (die 33 Abbrueche mit `content_chars = 0`).",
        f"- Records mit **null** Goldwerten im 6.000er-Fenster: **{len(null_fenster)}** "
        f"({', '.join(null_fenster) if null_fenster else 'keine'}).",
        f"- Records mit **mindestens zwei** Goldwerten im Fenster: "
        f"**{sum(1 for r in reihenfolge if faelle[r]['werte_im_fenster'] >= 2)}**.",
        f"- Goldwerte gesamt (verschiedene Werte je Record): {werte_gesamt}; davon im "
        f"Volltext auffindbar: {werte_im_text}, nicht auffindbar: "
        f"{werte_gesamt - werte_im_text}.",
        f"- Im 6.000er-Fenster sichtbar: "
        f"**{sum(f['werte_im_fenster'] for f in faelle.values())}** von {werte_gesamt}; "
        f"im Text, aber ausserhalb des Fensters: "
        f"{werte_im_text - sum(f['werte_im_fenster'] for f in faelle.values())}.",
        "",
        "Die frueher notierte Zahl 21 ist damit **nicht** die Zahl der Records ohne "
        "Goldwert im Fenster: sie ist die Zahl der Records mit mindestens zwei Werten "
        "im Fenster. Die Zahl der Records ohne jeden Wert im Fenster ist "
        f"{len(null_fenster)}.",
        "",
        "## Die Records ohne Goldwert im Fenster",
        "",
        "| Record | Dokument | Goldwerte | davon im Volltext | Werte ausserhalb des Fensters | bester blinder Treffer | Orakel |",
        "|---|---|---:|---:|---|---:|---:|",
    ]
    for rid in null_fenster:
        f = faelle[rid]
        ausser = ", ".join(f"{d['wert']} ({d['abstand_zeichen']} Zeichen, {d['richtung']})"
                           for d in f["ausserhalb_details"]) or "-"
        beste = max((f["regeln"][n]["abgedeckt"] for n in namen
                     if n != "orakel_6000" and n in f["regeln"]), default=0)
        md.append(f"| `{rid}` | {f['dokument']} | {f['werte_gesamt']} | {f['werte_im_text']} | "
                  f"{ausser} | {beste} | {f['regeln']['orakel_6000']['abgedeckt']} |")

    md += [
        "",
        "## Alle 33 im Ueberblick",
        "",
        "| Record | Goldwerte | im Text | im Fenster (`score`) | bester blinder Treffer | Orakel 6.000 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for rid in reihenfolge:
        f = faelle[rid]
        beste = max((f["regeln"][n]["abgedeckt"] for n in namen
                     if n != "orakel_6000" and n in f["regeln"]), default=0)
        md.append(f"| `{rid}` | {f['werte_gesamt']} | {f['werte_im_text']} | "
                  f"{f['werte_im_fenster']} | {beste} | "
                  f"{f['regeln']['orakel_6000']['abgedeckt']} |")

    md += [
        "",
        "## Startregeln im Vergleich",
        "",
        "| Regel | Records mit >= 1 Wert | Records mit >= 2 Werten | abgedeckte Werte | abgedeckte Goldzellen |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in namen:
        s = regeln_summe[name]
        md.append(f"| `{name}` | {s['mindestens_ein_wert']} | {s['mindestens_zwei_werte']} | "
                  f"{s['werte']} | {s['zellen']} |")
    md += [
        "",
        f"Abdeckung ist eine Obergrenze: gezaehlt wird, ob der Wert irgendwo im Fenster "
        f"steht, nicht ob er dort zur richtigen Zeile und zum richtigen Arm gehoert. "
        f"Zum Vergleich: von {werte_im_text} im Text auffindbaren Werten erreicht das "
        f"beste einzelne 6.000er-Fenster {orakel_werte}; "
        f"{('1 Wert liegt' if werte_im_text - orakel_werte == 1 else str(werte_im_text - orakel_werte) + ' Werte liegen')} "
        f"weiter auseinander, als ein Fenster dieser Breite fassen kann.",
        "",
        "## Was das fuer eine qwen-Serie heisst",
        "",
    ]

    sichtbar = sum(f["werte_im_fenster"] for f in faelle.values())
    md.append(
        f"Von {werte_gesamt} Goldwerten zeigt das aktuelle Fenster {sichtbar}; "
        f"{werte_gesamt - sichtbar} sind unsichtbar, davon {werte_gesamt - werte_im_text} "
        f"gar nicht im Dokumenttext und {werte_im_text - sichtbar} im Text, aber "
        f"ausserhalb des Fensters. Das beste einzelne 6.000er-Fenster kaeme auf "
        f"{orakel_werte}; nur "
        f"{('1 Wert passt' if werte_im_text - orakel_werte == 1 else str(werte_im_text - orakel_werte) + ' Werte passen')} "
        f"in kein Fenster dieser Breite. Die Breite ist damit nicht der Engpass, sondern die "
        f"Startregel. Eine qwen-Serie auf allen 33 wuerde zu {werte_gesamt - sichtbar} "
        f"von {werte_gesamt} Werten die Fensterwahl bzw. die Dokumentaufbereitung "
        f"messen, nicht das Modell."
    )

    if not null_fenster:
        md.append("Kein Record hat null Goldwerte im Fenster; die Frage nach der "
                  "Fensterlage betrifft dann nur die Records mit teilweiser Abdeckung.")
    else:
        ohne_text = [r for r in null_fenster if faelle[r]["werte_im_text"] == 0]
        md.append(
            f"Von den {len(null_fenster)} Records ohne Goldwert im Fenster haben "
            f"{len(ohne_text)} **keinen einzigen** Goldwert im Dokumenttext "
            f"({', '.join(ohne_text) if ohne_text else 'keiner'}). Dort kann keine "
            f"Startregel etwas gewinnen: der Wert existiert im Markdown nicht, weil "
            f"die Tabelle nur als Caption mit Bildplatzhalter steht. Eine Serie auf "
            f"diesen Records misst die Dokumentaufbereitung, nicht das Modell und "
            f"nicht das Fenster."
        )
        rest = [r for r in null_fenster if faelle[r]["werte_im_text"] > 0]
        if rest:
            teile = []
            for rid in rest:
                hilfen = [n for n in namen if n != "orakel_6000"
                          and faelle[rid]["regeln"].get(n, {}).get("abgedeckt", 0) > 0]
                teile.append(f"`{rid}` (" + (", ".join(hilfen) if hilfen
                              else "keine getestete blinde Regel, nur das Orakelfenster") + ")")
            md.append(
                "Bei " + ", ".join(teile) + " steht mindestens ein Wert im Dokument, "
                "aber keiner im Fenster; dort ist die Startregel der Engpass. In "
                "Klammern stehen die getesteten blinden Regeln, die einen Wert erreichen."
            )
        else:
            md.append(
                "Bei keinem dieser Records steht ein Goldwert ausserhalb des Fensters "
                "im Dokument. Eine andere Startregel kann diese Gruppe daher nicht "
                "retten."
            )

    md += [
        "",
        "## Vorbehalt",
        "",
        "- Die Zahlenlesart ist bewusst grosszuegig (Trennzeichen als Tausendergruppen, "
        "beide Lesarten). Ein Treffer heisst nur, dass die Ziffernfolge im Text steht; "
        "ein Zitat, ein Literaturverweis oder eine andere Tabelle zaehlt mit.",
        "- Die Abdeckung prueft keine Zeile und keinen Arm. Sie sagt, ob ein Modell den "
        "Wert ueberhaupt sehen konnte, nicht ob es ihn richtig bindet.",
        "- Die Startregeln sind blind, benutzen aber Outcome-Ausdruck und Zielzeitpunkt "
        "aus dem Record-Kontext, also dieselbe Information, die auch der Prompt traegt.",
        "",
        f"Rohdaten: `{AUS_JSON.name}`.",
        "",
    ]
    AUS_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"{len(faelle)} Records, {werte_gesamt} Goldwerte, davon {werte_im_text} im Text")
    print(f"null Goldwerte im Fenster: {len(null_fenster)} {null_fenster}")
    print(f"mindestens zwei im Fenster: "
          f"{sum(1 for r in reihenfolge if faelle[r]['werte_im_fenster'] >= 2)}")
    print(f"sichtbar im Fenster {sum(f['werte_im_fenster'] for f in faelle.values())}"
          f" von {werte_gesamt}; im Text {werte_im_text}; Orakel {orakel_werte}")
    print(f"Orakel 6.000: {orakel_werte} von {werte_im_text} erreichbaren Werten; "
          f"{werte_im_text - orakel_werte} nicht in einem Fenster")
    print()
    print(f"  {'Record':<13} {'Werte':>5} {'Text':>4} {'Fenster':>7} {'Orakel':>6} {'anker':>5} {'3x2000':>6}")
    for rid in reihenfolge:
        f = faelle[rid]
        print(f"  {rid:<13} {f['werte_gesamt']:>5} {f['werte_im_text']:>4} "
              f"{f['werte_im_fenster']:>7} {f['regeln']['orakel_6000']['abgedeckt']:>6} "
              f"{f['regeln'].get('anker_max', {}).get('abgedeckt', 0):>5} "
              f"{f['regeln'].get('mehrfach_3x2000', {}).get('abgedeckt', 0):>6}")
    print()
    for name in namen:
        s = regeln_summe[name]
        print(f"  {name:<16} >=1: {s['mindestens_ein_wert']:>2}  >=2: "
              f"{s['mindestens_zwei_werte']:>2}  Werte: {s['werte']:>3}  Zellen: {s['zellen']:>3}")
    print("\ngeschrieben:", AUS_JSON)
    print("geschrieben:", AUS_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
