#!/usr/bin/env python3
"""Baut Aufgaben- und Loesungsordner fuer die schwersten Records (Stand 21.11.2026).

Auswahl, reproduzierbar aus vorhandenen Artefakten:
  A) alle Records, bei denen der P5-Lauf keinen Inhalt geliefert hat
     (content_chars == 0, 33 Records),
  B) alle Records, bei denen P5 Zellen geliefert hat, aber keinen Treffer
     (p5.zellen > 0, p5.tp == 0, Goldzellen > 0, 8 Records).

yun2024:653 faellt aus B heraus: der Record hat keine Goldzellen.

Erzeugt:
  aufgaben/ANLEITUNG.md        gemeinsame Extraktionsanleitung
  aufgaben/<record>_aufgabe.md Kontext + Volltext
  loesungen/<record>_loesung.json  Goldzellen + P5-Bilanz
  loesungen/INDEX.md           Auswahltabelle und Kennzahlen
  auswahl_20261121.json        Maschinenlesbare Auswahl

Kein Modellaufruf, keine Aenderung an Gold oder Predictions.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BASE = REPO / "public_benchmark" / "extended_benchmark"
ANALYSE = BASE / "analysis" / "glm53_p5_vergleich_20261120"
VERGLEICH = ANALYSE / "vergleich_20261120.json"
GOLD = BASE / "yun_full" / "records" / "yun699.jsonl"
PRED = BASE / "runs" / "yun699_p5_24000_20261118" / "predictions.jsonl"
MUSTER = ANALYSE / "leere_p5_muster_20261120.json"

HIER = Path(__file__).resolve().parent
AUFGABEN = HIER / "aufgaben"
LOESUNGEN = HIER / "loesungen"

FELDER = (
    "intervention_group_size",
    "intervention_events",
    "intervention_mean",
    "intervention_standard_deviation",
    "comparator_group_size",
    "comparator_events",
    "comparator_mean",
    "comparator_standard_deviation",
)


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def dateiname(record_id: str) -> str:
    return record_id.replace(":", "_").replace("/", "_")





ANLEITUNG = """# Extraktionsanleitung

Diese Anleitung gilt fuer alle Aufgaben im Ordner `aufgaben/`. Ziel ist eine
Liste von Zellen, die sich maschinell gegen einen Goldstandard pruefen laesst.

## Auftrag

Lies den Dokumenttext der Aufgabe und extrahiere die numerischen Ergebnisse,
die zu **Intervention**, **Comparator** und **Outcome** im Aufgabenkopf gehoeren.
Gib genau ein JSON-Objekt zurueck, ohne Kommentar, ohne Markdown.

## Felder

Erlaubt sind genau diese acht Feldnamen:

`intervention_group_size`, `intervention_events`, `intervention_mean`,
`intervention_standard_deviation`, `comparator_group_size`,
`comparator_events`, `comparator_mean`, `comparator_standard_deviation`.

Je `(field, arm)` hoechstens eine Zelle. `arm` ist `intervention` oder
`comparator`.

## Regeln

1. **Nur aus dem Dokument.** Kein Vorwissen, keine Umrechnung, kein Runden,
   kein Schaetzen. Den Wert so uebernehmen, wie er gedruckt ist.
2. **Zeitpunkt.** Nimm den primaeren Zeitpunkt des Trials; ist keiner genannt,
   den zuletzt berichteten. Keine Baseline-Werte, ausser der Zielzeitpunkt ist
   die Baseline. Mische nie zwei Zeitpunkte in einer Zelle und trage das
   gedruckte Zeitpunktlabel in `timepoint` ein.
3. **Zeile.** Die Zeile muss den Outcome-Wert selbst tragen (`Mean (SD)`,
   `Median (IQR)`, `n`, `events`). Aenderungszeilen (`Mean change from BL`,
   `change`, `delta`, `difference`) sind nur zulaessig, wenn das Dokument
   keinen absoluten Wert zum Zielzeitpunkt berichtet.
4. **Kopfzahlen sind erlaubt.** Gruppengroessen duerfen aus dem Tabellenkopf
   oder der Armzeile stammen, auch wenn sie in keiner Ergebniszeile stehen
   (Beispiel: `Faces (n = 16)`).
5. **Armzuordnung.** `intervention` ist der Experimentalarm, `comparator` die
   Kontrolle. Gibt es je Arm mehrere Untergruppen, nimm die Untergruppe, die
   zur berichteten Population des Outcomes gehoert. Ist das nicht aufloesbar,
   lass die Zelle weg und begruende es in `unklar`.
6. **Fehlende Werte.** Berichtet das Dokument einen Wert nicht, lass die Zelle
   weg. Nicht raten, nicht aus einer anderen Population, Zeile oder einem
   anderen Zeitpunkt ersetzen. Ist keine einzige Zelle belegt, antworte
   `"found": false`.
7. **Anteile und Ereignisse.** Prozente und Anteile nicht als `mean` ausgeben.
   Ereignisse als absolute Zahl in `events`, nicht als Rate.
8. **Ein Beleg je Zelle.** `quote` enthaelt die Textstelle (maximal 300
   Zeichen), aus der der Wert stammt.

## Ausgabeschema

```json
{
  "found": true,
  "cells": [
    {
      "field": "intervention_mean",
      "arm": "intervention",
      "value": 38.1,
      "timepoint": "Week 52",
      "quote": "Mean score (SD) ... 38.1 (9.5)"
    }
  ],
  "unklar": ""
}
```

`timepoint` und `quote` werden nicht bewertet, helfen aber bei der Nachpruefung.
`unklar` bleibt leer, wenn nichts offen ist.

## Bewertung

Eine Zelle ist ein Treffer, wenn `(field, arm)` uebereinstimmt und der Wert
innerhalb von `1e-6` gleich ist. Daraus folgen TP, FP, FN sowie Precision,
Recall und F1 je Aufgabe. Zusaetzliche Zellen zaehlen als FP; fehlende als FN.
"""


def baue_aufgabe(record: dict, text: str) -> str:
    context = record.get("context") or {}
    ziel = (record.get("timepoint") or {}).get("target") or ""
    doc = record.get("document") or {}
    schema = (
        '{"found": true, "cells": [{"field": "<field>", "arm": "intervention" | "comparator", '
        '"value": <number>, "timepoint": "<label as printed>", "quote": "<Textstelle>"}], "unklar": ""}'
    )
    return (
        f"# Aufgabe {record['record_id']}\n\n"
        "## Kontext\n\n"
        f"- Intervention: {context.get('intervention') or 'nicht genannt'}\n"
        f"- Comparator: {context.get('comparator') or 'nicht genannt'}\n"
        f"- Outcome: {context.get('outcome') or 'nicht genannt'}\n"
        f"- Outcome-Typ: {context.get('outcome_type') or 'unbekannt'}\n"
        f"- Zielzeitpunkt (Regel): {ziel or 'nicht genannt'}\n"
        f"- Dokument: {doc.get('id') or 'unbekannt'} ({doc.get('text_chars') or len(text)} Zeichen)\n\n"
        "## Auftrag\n\n"
        "Extrahiere die acht Felder gemaess `ANLEITUNG.md` und antworte mit genau einem\n"
        "JSON-Objekt in diesem Schema:\n\n"
        f"`{schema}`\n\n"
        "## Dokument\n\n"
        "----- DOKUMENTANFANG -----\n"
        f"{text}\n"
        "----- DOKUMENTENDE -----\n"
    )


def main() -> None:
    vergleich = json.loads(VERGLEICH.read_text(encoding="utf-8"))
    bilanz = vergleich["records"]
    records = {r["record_id"]: r for r in lies_jsonl(GOLD)}
    predictions = {z["record_id"]: z for z in lies_jsonl(PRED)}
    muster = json.loads(MUSTER.read_text(encoding="utf-8"))["faelle"]

    abbrueche = sorted(
        (rid for rid, z in predictions.items() if not z.get("content_chars")),
        key=lambda r: int(r.split(":")[1]),
    )
    ohne_treffer = sorted(
        (
            rid
            for rid, v in bilanz.items()
            if v["p5"]["zellen"] > 0 and v["p5"]["tp"] == 0 and v["goldzellen"] > 0
        ),
        key=lambda r: int(r.split(":")[1]),
    )

    if len(abbrueche) != 33:
        raise SystemExit(f"erwartet 33 Abbrueche, gefunden {len(abbrueche)}")
    if len(ohne_treffer) != 8:
        raise SystemExit(f"erwartet 8 Records ohne Treffer, gefunden {len(ohne_treffer)}")

    for ordner in (AUFGABEN, LOESUNGEN):
        ordner.mkdir(parents=True, exist_ok=True)
        for alt in ordner.glob("*"):
            if alt.is_file():
                alt.unlink()

    (AUFGABEN / "ANLEITUNG.md").write_text(ANLEITUNG, encoding="utf-8", newline="\n")

    zeilen = []
    auswahl = {"stand": "2026-11-21", "kriterien": {}, "records": []}
    auswahl["kriterien"] = {
        "A_keine_antwort": "content_chars == 0 im P5-Lauf (33 Records)",
        "B_zellen_ohne_treffer": "p5.zellen > 0, p5.tp == 0, goldzellen > 0 (8 Records)",
        "ausgeschlossen": {"yun2024:653": "keine Goldzellen"},
    }

    for klasse, ids in (("A_keine_antwort", abbrueche), ("B_zellen_ohne_treffer", ohne_treffer)):
        for rid in ids:
            record = records[rid]
            text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
            gold = record["gold"]["cells"]
            if klasse == "A_keine_antwort" and rid in muster:
                gefunden_anzahl = int(muster[rid]["werte_gefunden"])
                fehlend = list(muster[rid]["werte_fehlend"])
                status = "nein" if muster[rid]["klasse"] == "fehlt_im_text" else "ja"
                methode = "Satz- und Tabellenkontext (leere_p5_muster_20261120.json)"
            else:
                gefunden_anzahl = None
                fehlend = []
                status = "nicht ausgewertet"
                methode = "nicht ausgewertet"
            v = bilanz[rid]["p5"]

            (AUFGABEN / f"{dateiname(rid)}_aufgabe.md").write_text(
                baue_aufgabe(record, text), encoding="utf-8", newline="\n"
            )
            loesung = {
                "record_id": rid,
                "dokument": {
                    "pmcid": record["document"].get("id"),
                    "pfad": record["document"]["path"],
                    "text_zeichen": len(text),
                },
                "klasse": klasse,
                "kontext": record.get("context"),
                "zielzeitpunkt_regel": (record.get("timepoint") or {}).get("target"),
                "gold_summe": len(gold),
                "gold_zellen": [
                    {
                        "field": c["field"],
                        "arm": c.get("arm"),
                        "value": c["value"],
                        "raw": c.get("raw"),
                        "timepoint": c.get("timepoint"),
                    }
                    for c in gold
                ],
                "goldwerte_im_text": {
                    "status": status,
                    "gefunden": gefunden_anzahl,
                    "von": len(gold),
                    "ohne_fund": fehlend,
                    "methode": methode,
                },
                "p5_lauf": {
                    "zellen": v["zellen"],
                    "tp": v["tp"],
                    "fp": v["fp"],
                    "fn": v["fn"],
                    "f1": v["f1"],
                    "fehlerklasse": v.get("fehlerklasse") or "",
                },
            }
            (LOESUNGEN / f"{dateiname(rid)}_loesung.json").write_text(
                json.dumps(loesung, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
            )

            f1_text = "-" if v["f1"] is None else f"{v['f1']:.3f}"
            text_status = {"ja": "ja", "nein": "nein"}.get(status, "-")
            zeilen.append(
                f"| `{rid}` | {klasse.split('_')[0]} | {record['document'].get('id')} | "
                f"{len(gold)} | {v['zellen']} | {v['tp']} | {f1_text} | {text_status} |"
            )
            auswahl["records"].append(
                {
                    "record_id": rid,
                    "klasse": klasse,
                    "pmcid": record["document"].get("id"),
                    "goldzellen": len(gold),
                    "p5_zellen": v["zellen"],
                    "p5_tp": v["tp"],
                    "gold_im_text": status,
                }
            )

    (HIER / "auswahl_20261121.json").write_text(
        json.dumps(auswahl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    ohne_text = [
        a for a in auswahl["records"] if a["gold_im_text"] == "nein"
    ]
    index = (
        "# Loesungen und Auswahl (Stand 21.11.2026)\n\n"
        f"{len(auswahl['records'])} Records: {len(abbrueche)} ohne Antwort im P5-Lauf, "
        f"{len(ohne_treffer)} mit Zellen, aber ohne Treffer. Eine Loesungsdatei je Record, "
        "Dateiname wie in `aufgaben/` (Doppelpunkt als Unterstrich).\n\n"
        "| Record | Klasse | Dokument | Goldzellen | P5-Zellen | P5-TP | P5-F1 | Gold im Text |\n"
        "|---|---|---|---:|---:|---:|---:|:---:|\n"
        + "\n".join(zeilen)
        + "\n\n"
        "Klasse A = `content_chars == 0` im P5-Lauf, Klasse B = Zellen ohne Treffer.\n"
        "`Gold im Text` ist fuer Klasse A die Einordnung aus `leere_p5_muster_20261120.md` "
        "(nein = kein Goldwert im Dokumenttext, Antwort muss leer bleiben); fuer Klasse B "
        "nicht ausgewertet.\n\n"
        f"Records der Klasse A ohne jeden Goldwert im Text: {len(ohne_text)} "
        f"({', '.join('`' + a['record_id'] + '`' for a in ohne_text) if ohne_text else 'keine'}). "
        "Dort ist die richtige Antwort eine leere Zellenliste; die Goldwerte stehen trotzdem in "
        "der Loesungsdatei.\n\n"
        "`yun2024:653` ist nicht enthalten: der Record hat keine Goldzellen.\n"
    )
    (LOESUNGEN / "INDEX.md").write_text(index, encoding="utf-8", newline="\n")

    print(f"Aufgaben: {len(abbrueche) + len(ohne_treffer)}")
    print(f"Loesungen: {len(list(LOESUNGEN.glob('*_loesung.json')))}")
    print(f"Klasse A ohne Goldwert im Text: {len(ohne_text)}")


if __name__ == "__main__":
    main()
