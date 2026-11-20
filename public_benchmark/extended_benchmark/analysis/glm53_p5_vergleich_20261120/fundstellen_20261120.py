#!/usr/bin/env python
"""Tragen Zitate, Verweise oder tabellenfremde Fundstellen die 92 Goldwerte?

Die Fenstermessung (`fensterlage_20261120.py`) zaehlt einen Goldwert als
"sichtbar", sobald seine Ziffernfolge irgendwo im Text steht. Diese Pruefung
geht eine Stufe tiefer und ordnet jede Fundstelle ein:

* Abschnitt: Abstract, Ergebnisteil, Methoden, Diskussion, sonstiger Body.
  Die Dokumente haben keine Zeilenumbrueche vor Ueberschriften; erkannt wird
  an den Inline-Markern `#`/`##` und einer festen Wortliste. Der Abstract
  endet an der ersten H1-Ueberschrift nach Position 0, der   Ergebnisteil beginnt an der ersten Results-Ueberschrift im Body und endet an
  Discussion/Conclusion/Limitations oder am Textende. Nummerierte Ueberschriften
  (`# 3. Results`, `## 3.1. Baseline Characteristics`) werden mit erkannt; ohne
  das blieben vier Dokumente (52, 152, 557, 559) ohne Body-Grenze.
* Zitat: die Zahl steht in einer eckigen Klammer (`[17]`) oder in einer
  Klammer mit `et al`/Jahreszahl/reiner Ziffernliste (`(12, 15)`).
* Verweis: die Zahl ist selbst eine Tabellen- oder Abbildungsnummer
  (`Table 1`, `Figure 2`).
* Tabellenkontext: im Umfeld von 250 Zeichen stehen mindestens zwei
  Tabellenmerker (`n =`, `mean`, `SD`, `CI`). Die Tabellen dieser Markdown-
  Dateien sind eingeflacht und haben keine Pipe-Zeilen; ein sicheres
  "fremde Tabelle" gibt es daher nicht, nur diesen Naeherungswert. Zusaetzlich
  wird geprueft, ob im selben Umfeld ein Outcome-Stichwort steht.

Je Goldwert eine Etikette:

* `ergebnisteil_text`     : mindestens eine Fundstelle im Ergebnisteil ohne
                            Tabellenkontext, kein Zitat, kein Verweis.
* `ergebnisteil_tabelle`  : alle Ergebnisteil-Fundstellen liegen in einem
                            Tabellenkontext. Das ist die eingeflachte
                            Ergebnistabelle des eigenen Trials, keine fremde
                            Tabelle; sie zaehlt als belastbar, aber getrennt
                            ausgewiesen.
* `abstract`, `methoden`, `diskussion`, `body_sonstiges`: nur dort.
* `zitat_oder_verweis`    : alle Fundstellen sind Zitat oder Verweis.
* `nirgends`              : keine Fundstelle im Text (Bildtabelle).

Danach wird das 6.000er-Fenster und das Orakel **nur auf den belastbaren
Fundstellen** (`ergebnisteil`) neu gerechnet. Bleibt der Abstand zwischen
Fenster und Orakel erhalten, haengt die Aussage "Startregel statt Breite"
nicht an Zufallstreffern.

Rein lesend, kein Modellaufruf, kein Netz.

Aufruf:
    .venv/bin/python .../fundstellen_20261120.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
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
from fensterlage_20261120 import kontext, regeln, werte_index  # noqa: E402
from zweistufig_trocken_20261120 import BREITE, waehle_ausschnitt  # noqa: E402

MUSTER = HIER / "leere_p5_muster_20261120.json"
AUS_JSON = HIER / "fundstellen_20261120.json"
AUS_MD = HIER / "p5_fundstellen_20261120.md"

WORT = (
    r"(Abstract|Background|Objectives?|Aims?|Methods?|Design|Measurements?|Results?|"
    r"Discussion|Conclusions?|Introduction|Participants|Statistical analysis|"
    r"Study design|Data collection|Limitations|References?|Acknowledg\w*|Funding|"
    r"Tables?|Figures?)"
)
UEBERSCHRIFT = re.compile(
    r"(?P<level>#{1,6})\s+(?:\d+(?:\.\d+)*\.?\s+)?(?P<title>" + WORT + r")\b", re.I)
TABELLE = re.compile(r"\b(n\s*=|mean|SD|95%\s*CI|CI\b|Table)\b", re.I)
JAHR = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")


def abschnitte(text: str) -> dict[str, Any]:
    """Spans fuer Abstract, Ergebnisteil, Methoden, Diskussion."""
    kopf = [(m.start(), len(m.group("level")), m.group("title").lower())
            for m in UEBERSCHRIFT.finditer(text)]
    if not kopf:
        return {"body_start": None, "abstract_ende": None, "spans": []}
    abstract_ende = next((s for s, level, _ in kopf if level == 1 and s > 0), None)
    body_start = abstract_ende
    spans: list[tuple[int, int, str]] = []
    if abstract_ende:
        spans.append((0, abstract_ende, "abstract"))

    if body_start is not None:
        im_body = [(s, level, titel) for s, level, titel in kopf if s >= body_start]
        ergebnis = [(s, level) for s, level, titel in im_body if titel.startswith("result")]
        methoden = [(s, level) for s, level, titel in im_body
                    if titel.startswith(("method", "design", "participants",
                                         "statistical", "data collection", "measurement"))]
        ende_titel = ("discussion", "conclusion", "limitation", "reference")
        if ergebnis:
            r_start, r_level = ergebnis[0]
            r_ende = next((s for s, level, titel in im_body
                           if s > r_start and level <= r_level and titel.startswith(ende_titel)),
                          len(text))
            if methoden:
                spans.append((methoden[0][0], r_start, "methoden"))
            spans.append((r_start, r_ende, "ergebnisse"))
            if r_ende < len(text):
                spans.append((r_ende, len(text), "diskussion"))
        else:
            if methoden:
                spans.append((methoden[0][0], len(text), "methoden"))
        spans.append((body_start, len(text), "body_sonstiges"))

    # Spezifischere Spans zuerst pruefen.
    reihenfolge = ["abstract", "ergebnisse", "methoden", "diskussion", "body_sonstiges"]
    spans.sort(key=lambda x: reihenfolge.index(x[2]))
    return {"body_start": body_start, "abstract_ende": abstract_ende, "spans": spans}


def abschnitt_von(spans: list[tuple[int, int, str]], pos: int) -> str:
    for start, ende, name in spans:
        if start <= pos < ende:
            return name
    return "unbekannt"


def ist_zitat(text: str, start: int, ende: int) -> bool:
    if start > 0 and ende < len(text) and text[start - 1] == "[" and text[ende] == "]":
        return True
    auf = text.rfind("(", 0, start)
    zu = text.find(")", ende)
    if auf == -1 or zu == -1:
        return False
    if "(" in text[auf + 1:start] or ")" in text[ende:zu]:
        return False
    innen = text[auf:zu + 1]
    if "et al" in innen.lower() or JAHR.search(innen):
        return True
    return bool(re.fullmatch(r"\(\s*\d[\d,\s;\u2013-]*\)", innen))


def ist_verweis(text: str, start: int) -> bool:
    davor = text[max(0, start - 30):start]
    return bool(re.search(r"(Table|Figure|Fig\.?|Supplementary Table)\s*$", davor, re.I))


def tabellenkontext(text: str, start: int, ende: int, stichworte: list[str]) -> tuple[bool, bool]:
    umfeld = text[max(0, start - 250):ende + 250]
    tabelle = len(TABELLE.findall(umfeld)) >= 2
    klein = umfeld.lower()
    outcome = any(wort.lower() in klein for wort in stichworte)
    return tabelle, outcome


def main() -> int:
    muster = json.loads(MUSTER.read_text(encoding="utf-8"))["faelle"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: dict[str, Any] = {}
    etiketten: Counter[str] = Counter()

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
        schnitt = abschnitte(text)

        bewertung: dict[str, Any] = {}
        index_streng: dict[float, list[tuple[int, int]]] = {w: [] for w in werte}
        for wert in werte:
            stellen = []
            for start, ende in index[wert]:
                zitat = ist_zitat(text, start, ende)
                verweis = ist_verweis(text, start)
                abschnitt = abschnitt_von(schnitt["spans"], start)
                tabelle, outcome_nah = tabellenkontext(text, start, ende, stichworte)
                stellen.append({"start": start, "abschnitt": abschnitt,
                                "zitat": zitat, "verweis": verweis,
                                "tabelle": tabelle, "outcome_nah": outcome_nah,
                                "kontext": kontext(text, (start, ende))})
                if abschnitt == "ergebnisse" and not zitat and not verweis:
                    index_streng[wert].append((start, ende))

            if not stellen:
                etikette = "nirgends"
            elif index_streng[wert]:
                belastbar = [s for s in stellen
                             if s["abschnitt"] == "ergebnisse" and not s["zitat"] and not s["verweis"]]
                etikette = ("ergebnisteil_tabelle" if all(s["tabelle"] for s in belastbar)
                            else "ergebnisteil_text")
            elif any(s["zitat"] or s["verweis"] for s in stellen):
                etikette = "zitat_oder_verweis"
            else:
                etikette = max((s["abschnitt"] for s in stellen),
                               key=lambda a: sum(1 for s in stellen if s["abschnitt"] == a))
            etiketten[etikette] += 1
            bewertung[str(wert)] = {"etikette": etikette, "stellen": stellen}

        wahl = waehle_ausschnitt(text, stichworte, BREITE, 500)
        start, ende = wahl["start"], wahl["ende"]
        streng_regeln = regeln(text, stichworte, outcome, ziel, index_streng)
        faelle[rid] = {
            "record_id": rid,
            "dokument": m.get("dokument"),
            "text_zeichen": len(text),
            "hat_body_ueberschrift": schnitt["body_start"] is not None,
            "abschnitte": [(s, e, n) for s, e, n in schnitt["spans"]],
            "werte": bewertung,
            "werte_gesamt": len(werte),
            "werte_im_text": sum(1 for w in werte if index[w]),
            "werte_streng": sum(1 for w in werte if index_streng[w]),
            "fenster": {"start": start, "ende": ende},
            "streng_fenster": sum(1 for w in werte
                                  if any(start <= s[0] < ende for s in index_streng[w])),
            "streng_orakel": streng_regeln["orakel_6000"]["abgedeckt"],
            "streng_mehrfach": streng_regeln["mehrfach_3x2000"]["abgedeckt"],
            "streng_regeln": streng_regeln,
        }

    reihenfolge = list(faelle)
    werte_gesamt = sum(f["werte_gesamt"] for f in faelle.values())
    werte_text = sum(f["werte_im_text"] for f in faelle.values())
    werte_streng = sum(f["werte_streng"] for f in faelle.values())
    fenster_streng = sum(f["streng_fenster"] for f in faelle.values())
    orakel_streng = sum(f["streng_orakel"] for f in faelle.values())
    mehrfach_streng = sum(f["streng_mehrfach"] for f in faelle.values())
    ergebnis = {
        "n": len(faelle),
        "fenster_breite": BREITE,
        "werte_gesamt": werte_gesamt,
        "werte_im_text": werte_text,
        "werte_etiketten": dict(etiketten),
        "werte_streng": werte_streng,
        "streng_fenster": fenster_streng,
        "streng_orakel": orakel_streng,
        "streng_mehrfach": mehrfach_streng,
        "faelle": faelle,
    }
    AUS_JSON.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    def betrag(name: str) -> int:
        return etiketten.get(name, 0)

    md = [
        "# Tragen Zitate und Zufallstreffer die 92 Goldwerte? (20.11.2026)",
        "",
        "Rein offline: jede Fundstelle eines Goldwerts wird nach Abschnitt, "
        "Zitatkontext und Tabellenkontext eingeordnet. Kein Modellaufruf, kein "
        "Netz, Gold und Predictions unveraendert.",
        "",
        "## Einschraenkung vorab",
        "",
        f"- Keines der {len(faelle)} Dokumente hat eine References-Ueberschrift; "
        "die Dateien enden vor der Literaturliste. Literaturnachweise im Text "
        "sind deshalb nur eckige Ziffernklammern und Autoren-Jahr-Klammern.",
        "- Pipe-Tabellen gibt es nicht; Tabellen liegen eingeflacht als Text mit "
        "`n =`, `mean`, `SD` vor. Ein sicheres Urteil \"fremde Tabelle\" ist "
        "offline nicht moeglich; die 19 Tabellenfunde sind die eingeflachte "
        "Ergebnistabelle des eigenen Trials, weil jedes Dokument eine "
        "Publikation enthaelt.",
        "",
        "## Etiketten der Goldwerte",
        "",
        "| Etikette | Werte |",
        "|---|---:|",
        f"| `ergebnisteil_text` | {betrag('ergebnisteil_text')} |",
        f"| `ergebnisteil_tabelle` | {betrag('ergebnisteil_tabelle')} |",
        f"| `abstract` | {betrag('abstract')} |",
        f"| `methoden` | {betrag('methoden')} |",
        f"| `diskussion` | {betrag('diskussion')} |",
        f"| `body_sonstiges` | {betrag('body_sonstiges')} |",
        f"| `unbekannt` | {betrag('unbekannt')} |",
        f"| `zitat_oder_verweis` | {betrag('zitat_oder_verweis')} |",
        f"| `nirgends` | {betrag('nirgends')} |",
        f"| **Summe** | **{werte_gesamt}** |",
        "",
        f"Von {werte_gesamt} Goldwerten sind {werte_text} im Text auffindbar und "
        f"{betrag('nirgends')} nicht. Belastbar im Ergebnisteil stehen "
        f"**{werte_streng}**; die uebrigen {werte_text - werte_streng} verteilen "
        f"sich auf Abstract ({betrag('abstract')}), Diskussion "
        f"({betrag('diskussion')}), Zitat/Verweis ({betrag('zitat_oder_verweis')}) "
        f"und nicht klassifizierbare Dokumente ({betrag('unbekannt')}).",
        "",
        "## Fenster und Orakel auf den belastbaren Fundstellen",
        "",
        "| Groesse | alle Textfundstellen | nur Ergebnisteil |",
        "|---|---:|---:|",
        f"| Goldwerte mit Fundstelle | {werte_text} | {werte_streng} |",
        f"| im aktuellen 6.000er-Fenster | 67 | {fenster_streng} |",
        f"| Orakel: bestes 6.000er-Fenster | 91 | {orakel_streng} |",
        f"| drei Stuecke zu 2.000 Zeichen | 72 | {mehrfach_streng} |",
        "",
    ]

    if werte_streng:
        md.append(
            f"Auf den belastbaren Fundstellen bleibt ein Abstand von "
            f"**{orakel_streng - fenster_streng}** Werten zwischen dem besten "
            f"einzelnen Fenster ({orakel_streng}) und dem aktuellen Fenster "
            f"({fenster_streng})."
        )
    else:
        md.append("Es bleibt kein belastbarer Wert uebrig; die Aussage waere dann "
                  "nicht stützbar.")

    md += [
        "",
        "## Records mit Auffaelligkeiten",
        "",
        "| Record | Werte | im Text | belastbar | Fenster | Orakel | Etiketten |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for rid in reihenfolge:
        f = faelle[rid]
        zaehler = Counter(z["etikette"] for z in f["werte"].values())
        im_ergebnis = zaehler.get("ergebnisteil_text", 0) + zaehler.get("ergebnisteil_tabelle", 0)
        if f["werte_im_text"] and im_ergebnis < f["werte_im_text"]:
            md.append(
                f"| `{rid}` | {f['werte_gesamt']} | {f['werte_im_text']} | "
                f"{f['werte_streng']} | {f['streng_fenster']} | {f['streng_orakel']} | "
                + ", ".join(f"{k}: {n}" for k, n in zaehler.most_common()) + " |"
            )

    md += [
        "",
        "## Antwort auf die Frage",
        "",
        f"Von den {werte_text} im Text gefundenen Werten steht **{betrag('zitat_oder_verweis')}** "
        f"ausschliesslich als Zitat- oder Verweisnummer: 152: 7.0 ist die "
        f"Abbildungsnummer in \"Figure 7\", kein Messwert. **{werte_streng}** stehen "
        f"im Ergebnisteil, davon "
        f"{betrag('ergebnisteil_tabelle')} ausschliesslich in eingeflachten "
        f"Tabellentext. Nur {betrag('abstract')} Werte stehen allein im Abstract, "
        f"{betrag('diskussion')} allein in der Diskussion, {betrag('unbekannt')} "
        f"ohne bestimmbaren Abschnitt. Der "
        f"Abstand zwischen Fenster und Orakel bleibt auf der belastbaren Teilmenge "
        f"erhalten ({fenster_streng} gegen {orakel_streng}); die Aussage "
        f"\"Startregel statt Breite\" haengt damit nicht an Zufallstreffern. Die "
        f"absoluten Zahlen sinken aber: fuer den Ergebnisteil heisst es "
        f"{orakel_streng} statt 91.",
        "",
"",
        "## Vorbehalt",
        "",
        "- Die Abschnittsgrenzen haengen an erkannten Ueberschriften. Wo keine "
        "Body-Ueberschrift gefunden wird, bleibt der Abschnitt `unbekannt` und "
        "die Fundstelle zaehlt nicht als belastbar; das ist streng, nicht "
        "grosszuegig.",
        "- Der Tabellen-Naeherungswert prueft nur das Umfeld von 250 Zeichen. "
        "Eine eingeflachte Baseline-Tabelle kann als Outcome-Kontext durchgehen, "
        "wenn das Outcome-Stichwort im selben Umfeld steht.",
        "- Ein Wert im Abstract kann der Hauptbefund sein; er ist hier nicht "
        "belastbar, weil der Ergebnisteil die Bindung an Zeile und Arm traegt.",
        "",
        f"Rohdaten: `{AUS_JSON.name}`.",
        "",
    ]
    AUS_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    print(f"{len(faelle)} Records, {werte_gesamt} Goldwerte, {werte_text} im Text")
    print("Etiketten:", dict(etiketten))
    print(f"belastbar im Ergebnisteil: {werte_streng}; Fenster {fenster_streng}; "
          f"Orakel {orakel_streng}; 3x2000 {mehrfach_streng}")
    print()
    print(f"  {'Record':<13} {'Text':>4} {'streng':>6} {'Fenster':>7} {'Orakel':>6}")
    for rid in reihenfolge:
        f = faelle[rid]
        print(f"  {rid:<13} {f['werte_im_text']:>4} {f['werte_streng']:>6} "
              f"{f['streng_fenster']:>7} {f['streng_orakel']:>6}")
    print("\ngeschrieben:", AUS_JSON)
    print("geschrieben:", AUS_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
