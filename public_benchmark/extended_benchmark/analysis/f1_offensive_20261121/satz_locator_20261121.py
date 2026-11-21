#!/usr/bin/env python3
"""Phase 2: Satz-Locator mit Unterscheider-Pflicht.

Der Locator waehlt eine Textstelle nur dann, wenn sie das Outcome ueber die
Region oder ein unterscheidendes Outcome-Wort anspricht. Fehlt der
Unterscheider, wird nichts gebunden: der Fall geht als `ohne_unterscheider` und
damit an die Tabellenzeile, statt willkuerlich einen Satz zu nehmen.

Damit behebt die Regel den in `kopf_und_satzauswahl_20261120.md` belegten
Fehler: dort banden 5 von 10 Faellen ein richtiges Zahlenpaar an einen Satz,
der die Region nicht nannte (420 `Cervicothoracic`, 421 `thoracolumbar`,
523 `results`).

Rein offline: kein Modellaufruf, keine Aenderung an Gold oder Predictions.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/satz_locator_20261121.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
BENCH = ANALYSE.parent
REPO = BENCH.parent.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))

import vergleiche_20261120 as v  # noqa: E402

LAUF = ANALYSE / "glm53_p5_vergleich_20261120" / "zweistufig_lauf_20261120"
SATZ_ENDE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
STOPP = {
    "quantitative", "assessment", "comparison", "primary", "reported", "between",
    "versus", "effect", "effects", "change", "changes", "baseline", "significant",
    "significantly", "values", "value", "using", "after", "before", "group",
    "groups", "patients", "participants", "results", "result", "study", "outcome",
    "outcomes", "mean", "score", "scores", "total", "analysis", "table", "figure",
    # Funktionswoerter und Zeiteinheiten koennen kein Outcome unterscheiden.
    "according", "between", "during", "within", "without", "there", "these",
    "those", "which", "while", "month", "months", "week", "weeks", "day",
    "days", "year", "years", "hour", "hours", "minute", "minutes",
}


def unterscheider(context: dict[str, Any]) -> list[str]:
    """Woerter aus dem Outcome, die diesen Record von Nachbarn trennen."""
    worte = re.findall(r"[A-Za-z][A-Za-z-]{5,}", str((context or {}).get("outcome") or ""))
    raus = []
    for wort in worte:
        if wort.lower() in STOPP:
            continue
        if wort.lower() not in [w.lower() for w in raus]:
            raus.append(wort)
    return raus


def saetze(text: str, versatz: int = 0) -> list[dict[str, Any]]:
    """Saetze mit Position im Gesamttext."""
    raus, start = [], 0
    for stueck in SATZ_ENDE.split(text):
        raus.append({"text": stueck.strip(), "start": versatz + start})
        start += len(stueck) + 1
    return [s for s in raus if s["text"]]


def zahlen(text: str) -> set[float]:
    raus = set()
    for m in re.finditer(r"\d+(?:[.,]\d+)?", text):
        try:
            raus.add(round(float(m.group(0).replace(",", ".")), 6))
        except ValueError:
            continue
    return raus


def enthaelt_wort(satz: str, wort: str) -> bool:
    """Wort oder Wortstamm; Regionsangaben stehen oft in Zusammensetzungen."""
    stamm = wort.lower()[: max(6, len(wort) - 3)]
    return stamm in satz.lower()


def paar_vorhanden(satz: str) -> bool:
    """Mindestens zwei Zahlen im Satz, wie fuer Mittelwert und Streuung noetig."""
    return len(re.findall(r"\d+(?:[.,]\d+)?", satz)) >= 2


def waehle(region: str, context: dict[str, Any], goldpaare: set[float] | None = None) -> dict[str, Any]:
    """Waehlt eine Textstelle oder verweigert die Bindung.

    Rueckgabe: `zustand` in
      eindeutig             genau ein Satz mit Zahlen und Unterscheider
      ohne_unterscheider    Zahlen gefunden, aber kein Satz nennt das Outcome
      mehrere_kandidaten    mehrere Saetze mit Unterscheider, keine Aufloesung
      kein_satz             kein Satz mit Zahlenpaar
    """
    kern = unterscheider(context)
    kandidaten = saetze(region)
    mit_zahlen = [s for s in kandidaten if paar_vorhanden(s["text"])]
    # Pflichtbegriff ist der seltenste Outcome-Begriff: er traegt die Region
    # (Cervicothoracic gegen thoracolumbar) und trennt Nachbar-Records.
    haeufigkeit = {
        wort: sum(1 for s in kandidaten if enthaelt_wort(s["text"], wort)) for wort in kern
    }
    pflicht = sorted((w for w in kern if haeufigkeit[w]), key=lambda w: haeufigkeit[w])
    mit_kern = [
        s for s in mit_zahlen
        if pflicht and enthaelt_wort(s["text"], pflicht[0])
    ]
    if len(mit_kern) > 1:
        # Bei mehreren Kandidaten entscheidet die Zahl der getroffenen
        # Outcome-Begriffe; Gleichstand bleibt unaufgeloest.
        rang = {id(s): sum(1 for w in kern if enthaelt_wort(s["text"], w)) for s in mit_kern}
        bestes = max(rang.values())
        spitze = [s for s in mit_kern if rang[id(s)] == bestes]
        mit_kern = spitze if len(spitze) == 1 else mit_kern
    # Der Unterscheider darf auch im direkt folgenden Satz stehen: Regionsangaben
    # stehen haeufig im Satz davor, die Zahlen im Satz danach.
    erweitert = []
    for i, satz in enumerate(kandidaten):
        text = satz["text"]
        folge = kandidaten[i + 1]["text"] if i + 1 < len(kandidaten) else ""
        if paar_vorhanden(text) and any(enthaelt_wort(text + " " + folge, w) for w in kern):
            erweitert.append({"text": text, "start": satz["start"], "beleg": (text + " " + folge).strip()})
    if not kern:
        return {"zustand": "ohne_unterscheider", "satz": "", "start": None,
                "grund": "Outcome traegt kein unterscheidendes Wort", "kern": kern}
    if len(mit_kern) == 1:
        satz = mit_kern[0]
        return {"zustand": "eindeutig", "satz": satz["text"], "start": satz["start"],
                "grund": f"ein Satz mit Zahlenpaar und Pflichtbegriff '{pflicht[0]}'", "kern": kern}
    if len(mit_kern) > 1:
        return {"zustand": "mehrere_kandidaten", "satz": "", "start": None,
                "grund": f"{len(mit_kern)} Saetze mit Pflichtbegriff: "
                         + " | ".join(s["text"][:60] for s in mit_kern[:3]), "kern": kern}
    if len(erweitert) == 1:
        satz = erweitert[0]
        return {"zustand": "eindeutig", "satz": satz["text"], "start": satz["start"],
                "grund": "Unterscheider im Folgesatz", "kern": kern}
    if len(erweitert) > 1:
        return {"zustand": "mehrere_kandidaten", "satz": "", "start": None,
                "grund": f"{len(erweitert)} Saetze mit Unterscheider im Folgesatz", "kern": kern}
    if mit_zahlen:
        return {"zustand": "ohne_unterscheider", "satz": "", "start": None,
                "grund": f"{len(mit_zahlen)} Saetze mit Zahlen, keiner nennt das Outcome",
                "kern": kern}
    return {"zustand": "kein_satz", "satz": "", "start": None,
            "grund": "kein Satz mit Zahlenpaar in der Region", "kern": kern}


def fenster(text: str, position: int, breite: int = 3000) -> tuple[str, int]:
    start = max(0, position - breite // 2)
    return text[start : start + breite], start


def pruefe_gespeicherte_faelle() -> list[dict[str, Any]]:
    """Die 10 gespeicherten Stufe-1-Antworten mit der neuen Regel pruefen."""
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: list[dict[str, Any]] = []
    for pfad in sorted(LAUF.glob("*.jsonl")):
        for roh in pfad.read_text(encoding="utf-8").splitlines():
            if not roh.strip():
                continue
            zeile = json.loads(roh)
            rid = zeile.get("record_id")
            if not rid or rid not in records:
                continue
            stuecke = zeile.get("stuecke") or []
            if not stuecke:
                continue
            record = records[rid]
            text = (REPO / (record.get("document") or {}).get("path", "")).read_text(
                encoding="utf-8", errors="replace"
            )
            region = " ".join(text[s[0] : s[1]] for s in stuecke)
            locators = zeile.get("locators") or (zeile.get("stufe1") or {}).get("locators") or []
            alt = [str(l.get("satz") or "").strip() for l in locators if str(l.get("satz") or "").strip()]
            gold = sorted({
                round(float(z["value"]), 6)
                for z in (record.get("gold") or {}).get("cells") or []
                if z.get("value") is not None
            })
            entscheidung = waehle(region, record.get("context") or {})
            paar = bool(zahlen(entscheidung["satz"] or "") & set(gold)) if entscheidung["satz"] else False
            faelle.append(
                {
                    "record_id": rid,
                    "quelle": pfad.name,
                    "alter_satz": alt[0] if alt else "",
                    "alter_satz_mit_unterscheider": bool(alt) and any(
                        enthaelt_wort(alt[0], w) for w in unterscheider(record.get("context") or {})
                    ),
                    "alter_satz_mit_goldpaar": bool(alt) and bool(zahlen(alt[0]) & set(gold)),
                    "neuer_zustand": entscheidung["zustand"],
                    "neuer_satz": entscheidung["satz"],
                    "grund": entscheidung["grund"],
                    "unterscheider": entscheidung["kern"],
                    "goldpaar_im_neuen_satz": paar,
                    "goldwerte": gold,
                }
            )
    # Doppelte (Record, Satz) aus mehreren Laeufen entfernen.
    gesehen, einzig = set(), []
    for f in faelle:
        key = (f["record_id"], f["neuer_zustand"], f["neuer_satz"][:80])
        if key in gesehen:
            continue
        gesehen.add(key)
        einzig.append(f)
    return einzig


def baue_schwierige_faelle(grenze: int = 30) -> list[dict[str, Any]]:
    """20-30 schwierige Faelle: Fenster um den ersten Goldwert je Record.

    Grundlage sind die 41 schweren Records. Das Fenster ist bewusst
    deterministisch (3000 Zeichen um den ersten Goldwert) und damit keine
    Nachbildung des echten Retrievals, sondern ein reproduzierbarer Testfall.
    """
    auswahl = json.loads(
        (ANALYSE / "schwere_records_20261121" / "auswahl_20261121.json").read_text(encoding="utf-8")
    )["records"]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: list[dict[str, Any]] = []
    for eintrag in auswahl:
        rid = eintrag["record_id"]
        record = records[rid]
        text = (REPO / (record.get("document") or {}).get("path", "")).read_text(
            encoding="utf-8", errors="replace"
        )
        werte = [
            round(float(z["value"]), 6)
            for z in (record.get("gold") or {}).get("cells") or []
            if z.get("value") is not None
        ]
        if not werte:
            continue
        erster = None
        for wert in werte:
            for m in re.finditer(rf"(?<![\d.,]){re.escape(str(wert).rstrip('0').rstrip('.'))}(?![\d])", text):
                erster = m.start()
                break
            if erster is not None:
                break
        if erster is None:
            continue
        region, start = fenster(text, erster)
        entscheidung = waehle(region, record.get("context") or {})
        gold_im_fenster = sum(
            1 for w in werte
            if re.search(rf"(?<![\d.,]){re.escape(str(w).rstrip('0').rstrip('.'))}(?![\d])", region)
        )
        paar = bool(zahlen(entscheidung["satz"] or "") & set(werte)) if entscheidung["satz"] else False
        faelle.append(
            {
                "record_id": rid,
                "feld_gold": werte,
                "fenster_start": start,
                "goldwerte_im_fenster": gold_im_fenster,
                "von_goldwerten": len(werte),
                "neuer_zustand": entscheidung["zustand"],
                "neuer_satz": entscheidung["satz"],
                "grund": entscheidung["grund"],
                "unterscheider": entscheidung["kern"],
                "goldpaar_im_neuen_satz": paar,
            }
        )
        if len(faelle) >= grenze:
            break
    return faelle


def main() -> int:
    gespeichert = pruefe_gespeicherte_faelle()
    schwierig = baue_schwierige_faelle()

    def zaehlung(faelle: list[dict[str, Any]]) -> dict[str, int]:
        raus: dict[str, int] = {}
        for f in faelle:
            raus[f["neuer_zustand"]] = raus.get(f["neuer_zustand"], 0) + 1
        return raus

    ergebnis = {
        "stand": "2026-11-21",
        "regel": {
            "unterscheider_pflicht": "Satz muss ein Outcome-Wort (Stamm, mindestens 6 Zeichen) tragen, "
                                     "sonst keine Bindung",
            "folgesatz": "Unterscheider darf im direkt folgenden Satz stehen",
            "mehrdeutig": "mehrere Kandidaten werden nicht aufgeloest, der Fall faellt an die Tabellenzeile",
        },
        "gespeicherte_faelle": {
            "anzahl": len(gespeichert),
            "zustand": zaehlung(gespeichert),
            "mit_goldpaar": sum(1 for f in gespeichert if f["goldpaar_im_neuen_satz"]),
            "alter_locator_bindungen": sum(1 for f in gespeichert if f["alter_satz"]),
            "alter_locator_mit_goldpaar": sum(1 for f in gespeichert if f["alter_satz_mit_goldpaar"]),
            "faelle": gespeichert,
        },
        "schwierige_faelle": {"anzahl": len(schwierig), "zustand": zaehlung(schwierig),
                              "mit_goldpaar": sum(1 for f in schwierig if f["goldpaar_im_neuen_satz"]),
                              "faelle": schwierig},
    }
    (HIER / "satz_locator_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    zeilen_a = "\n".join(
        f"| `{f['record_id']}` | {f['quelle']} | {'ja' if f['alter_satz_mit_unterscheider'] else 'nein'} | "
        f"{f['neuer_zustand']} | {'ja' if f['goldpaar_im_neuen_satz'] else 'nein'} | {f['grund'][:70]} |"
        for f in gespeichert
    )
    zeilen_b = "\n".join(
        f"| `{f['record_id']}` | {f['goldwerte_im_fenster']}/{f['von_goldwerten']} | {f['neuer_zustand']} | "
        f"{'ja' if f['goldpaar_im_neuen_satz'] else 'nein'} | {f['grund'][:70]} |"
        for f in schwierig
    )
    bericht = (
        "# Satz-Locator mit Unterscheider-Pflicht (21.11.2026)\n\n"
        "Rein offline, kein Modellaufruf. Der Locator bindet einen Satz nur, wenn er\n"
        "mindestens zwei Zahlen und ein unterscheidendes Wort aus dem Outcome traegt\n"
        "(Wortstamm, mindestens sechs Zeichen). Der Unterscheider darf im direkt\n"
        "folgenden Satz stehen. Mehrere Kandidaten werden nicht aufgeloest; der Fall\n"
        "faellt dann an die Tabellenzeile, statt willkuerlich einen Satz zu waehlen.\n\n"
        "## A: die zehn gespeicherten Faelle\n\n"
        "| Record | Quelle | alter Satz mit Unterscheider | neuer Zustand | Goldpaar im Satz | Grund |\n"
        "|---|---|:---:|---|:---:|---|\n"
        f"{zeilen_a}\n\n"
        f"Zustaende: {zaehlung(gespeichert)}. Mit Goldpaar: "
        f"{ergebnis['gespeicherte_faelle']['mit_goldpaar']} von {len(gespeichert)}.\n\n"
        "## B: schwierige Faelle (Fenster um den ersten Goldwert)\n\n"
        "| Record | Goldwerte im Fenster | neuer Zustand | Goldpaar im Satz | Grund |\n"
        "|---|---:|---|:---:|---|\n"
        f"{zeilen_b}\n\n"
        f"Zustaende: {zaehlung(schwierig)}. Mit Goldpaar: "
        f"{ergebnis['schwierige_faelle']['mit_goldpaar']} von {len(schwierig)}.\n\n"
        "## Was sich aendert\n\n"
        "Der alte Locator band in allen Faellen mit Satz einen Satz, auch wenn er das\n"
        "Outcome nicht nannte (420, 421). Neu ist die Bindung in diesen Faellen\n"
        "ausgeschlossen: der Zustand ist `ohne_unterscheider`, die Entscheidung geht an\n"
        "die Tabellenzeile. Das kostet keine Tokens (reine Regel) und verhindert eine\n"
        "falsche Bindung, liefert aber fuer sich genommen noch keine Zelle.\n\n"
        "## Grenzen\n\n"
        "- Die 20-30 schwierigen Faelle sind Fenster um den ersten Goldwert, nicht das\n"
        "  echte Retrieval; sie pruefen die Regel, nicht die Pipeline.\n"
        "- `mehrere_kandidaten` ist eine ehrliche Verweigerung, keine Loesung: der Fall\n"
        "  braucht dann die Tabellenzeile oder einen zweiten Aufruf.\n"
        "- Der Wortstamm-Test kann zu weit greifen (`results` ist aus der Stoppliste\n"
        "  genommen, andere Generika nicht).\n"
    )
    alt_bind = ergebnis["gespeicherte_faelle"]["alter_locator_bindungen"]
    alt_paar = ergebnis["gespeicherte_faelle"]["alter_locator_mit_goldpaar"]
    neu_bind = zaehlung(gespeichert).get("eindeutig", 0)
    neu_paar = ergebnis["gespeicherte_faelle"]["mit_goldpaar"]
    verweigert = len(gespeichert) - neu_bind
    bericht += (
        "## Gemessene Wirkung auf den zehn gespeicherten Faellen\n\n"
        f"| Stand | Bindungen | davon mit Goldpaar | Verweigerungen |\n|---|---:|---:|---:|\n"
        f"| alter Locator | {alt_bind} | {alt_paar} | 0 |\n"
        f"| neuer Locator | {neu_bind} | {neu_paar} | {verweigert} |\n\n"
        "Die Pflicht zum Unterscheider entfernt falsche Bindungen: 420 und 421 werden\n"
        "nicht mehr an einen Satz ohne Regionsangabe gehaengt. Sie erzeugt aber keine\n"
        "richtigen: in den verbleibenden Bindungen steht der Pflichtbegriff, nicht das\n"
        "Goldpaar. Ein Satz allein reicht damit nicht; die Zelle muss aus der Zeile\n"
        "kommen. Das prueft Phase 3, und deshalb ist dieser Locator kein F1-Hebel fuer\n"
        "sich, sondern eine Absicherung gegen stille Fehlbindungen.\n"
    )
    (HIER / "satz_locator_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    # Die statische Passage "Was sich aendert" ist durch die Messung ueberholt:
    # der neue Locator bindet 420/421 weiterhin, nur mit falschen Zahlen.
    anfang = bericht.find("## Was sich aendert")
    ende = bericht.find("## Gemessene Wirkung")
    if anfang != -1 and ende != -1:
        bericht = bericht[:anfang] + (
            "## Was sich aendert\n\n"
            "Auf den zehn gespeicherten Faellen bindet der alte Locator fuenf Saetze,\n"
            "davon vier mit dem richtigen Zahlenpaar. Der neue Locator bindet vier Saetze\n"
            "mit Pflichtbegriff und keinem richtigen Zahlenpaar; sechs Faelle werden\n"
            "verweigert (fuenf mehrdeutig, einer ohne Unterscheider). Die Pflicht\n"
            "verschiebt die Bindung damit von der richtigen Zahl zum falschen Satz: 420\n"
            "und 421 nennen das Regionswort, tragen aber andere Zahlen. Das ist ein\n"
            "negatives Ergebnis und wird so berichtet.\n\n"
            "Die Ursache ist strukturell: ein Regionswort steht im Tabellenkopf oder in\n"
            "der Ueberschrift, das Zahlenpaar in der Zeile. Solange beides in einem Satz\n"
            "gesucht wird, konkurrieren sie. Der naechste Schritt ist deshalb keine\n"
            "weitere Satzregel, sondern die Zeilenbindung aus Phase 3.\n\n"
        ) + bericht[ende:]
    (HIER / "satz_locator_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print("Gespeicherte Faelle:", zaehlung(gespeichert),
          "| Goldpaar", ergebnis["gespeicherte_faelle"]["mit_goldpaar"])
    print("Schwierige Faelle:", zaehlung(schwierig),
          "| Goldpaar", ergebnis["schwierige_faelle"]["mit_goldpaar"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
