#!/usr/bin/env python3
"""Koennen 20 der 295 `fn_wert_ersetzt` durch Zeilenbenennung im Prompt geloest werden?

Offline, ohne Netzaufruf, ohne Gold-Aenderung. Systematische Stichprobe: jeder
15. Fall der 295 in der Reihenfolge von `fehlerursachen_20261121.json`, also
20 Faelle ueber die ganze Liste verteilt.

Je Fall wird geprueft, ob der Goldwert im Dokument in einer Zeile steht, deren
Label oder Zeilengruppe den Outcome benennt:

* `eindeutig_benannt`  genau eine solche Zeile - eine Prompt-Zeilenangabe kann
  den Fall loesen.
* `mehrdeutig_benannt` mehrere solche Zeilen - der Prompt braucht zusaetzlich
  Gruppe oder Zeitpunkt.
* `ohne_outcome_bezug` Wert steht im Text, aber keine Zeile nennt den Outcome.
* `wert_nicht_im_dokument` der Wert fehlt in der Markdown-Fassung.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zeilenbenennung_20261121.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
import re
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
from satz_locator_20261121 import unterscheider  # noqa: E402
from zahlabgleich_20261121 import zahl_positionen  # noqa: E402
from zeilenbindung_20261121 import PAAR, binde, gruppe_von, label_von  # noqa: E402

SCHRITT = 15
ANZAHL = 20


ZAEHLFELDER = {"intervention_group_size", "comparator_group_size",
               "intervention_events", "comparator_events", "intervention_total", "comparator_total"}


def benenne(record: dict[str, Any], text: str, wert: float, feld: str) -> dict[str, Any]:
    kern = [w.lower() for w in unterscheider(record.get("context") or {})]
    zeilen = text.splitlines()
    fundstellen = [i for i, l in enumerate(zeilen) if zahl_positionen(wert, l)]
    if not fundstellen:
        return {"klasse": "wert_nicht_im_dokument", "zeilen": 0, "belege": []}
    benannt: list[dict[str, Any]] = []
    tabellenzeilen = 0
    for i in fundstellen:
        treffer = PAAR.search(zeilen[i])
        # Tabellenzeilen tragen ein Wertepaar `Wert (SD)`, ein `+/-` oder `n = X`.
        ist_zeile = bool(treffer) or "\u00b1" in zeilen[i] or bool(re.search(r"n\s*=\s*\d", zeilen[i]))
        if not ist_zeile or len(zeilen[i].strip()) > 120:
            continue
        tabellenzeilen += 1
        label = label_von(zeilen[i], treffer.start()) if treffer else zeilen[i].strip()[:60]
        if len(label) > 80:
            continue
        gruppe, _ = gruppe_von(i, zeilen)
        nennt = any(w[: max(6, len(w) - 3)] in label.lower() for w in kern) or (
            bool(gruppe) and any(w[: max(6, len(w) - 3)] in gruppe.lower() for w in kern)
        )
        if nennt:
            benannt.append({"zeile": i + 1, "label": label[:60], "gruppe": gruppe,
                            "hat_paar": bool(treffer)})
    if not tabellenzeilen:
        return {"klasse": "wert_nur_im_fliessetext", "zeilen": len(fundstellen), "belege": []}
    if len(benannt) == 1:
        klasse = "eindeutig_benannt"
    elif benannt:
        klasse = "mehrdeutig_benannt"
    else:
        klasse = "ohne_outcome_bezug"
        # Zaehlfelder stehen in Kopfzeilen, die den Outcome nie nennen; dort
        # identifiziert die Kaption die Tabelle.
        # Nur wenn der Wert wirklich in einer kurzen Zeile mit `n =` steht,
        # identifiziert die Kaption die Tabelle; Prosa-Zeilen zaehlen nicht.
        groessenzeile = any(
            zahl_positionen(wert, zeilen[i]) and len(zeilen[i].strip()) <= 120
            and ("n =" in zeilen[i] or "\u00b1" in zeilen[i])
            for i in fundstellen
        )
        if feld in ZAEHLFELDER and groessenzeile:
            fenster = " ".join(" ".join(zeilen[max(0, i - 10) : i + 1]) for i in fundstellen).lower()
            if any(w[: max(6, len(w) - 3)] in fenster for w in kern):
                klasse = "kaption_benannt"
    return {"klasse": klasse, "zeilen": len(fundstellen), "belege": benannt[:4]}


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    stichprobe = faelle[::SCHRITT][:ANZAHL]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte: dict[str, str] = {}

    ergebnisse: list[dict[str, Any]] = []
    for f in stichprobe:
        rid = f["record_id"]
        record = records[rid]
        if rid not in texte:
            texte[rid] = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        text = texte[rid]
        befund = benenne(record, text, f["wert"], f["feld"])
        bindung = binde(record, text, "streng")
        gold = {(str(z.get("field") or ""), v.arm_von(z)): v.zahl(z.get("value"))
                for z in (record.get("gold") or {}).get("cells") or []}
        ergebnisse.append(
            {
                "record_id": rid,
                "feld": f["feld"],
                "arm": f["arm"],
                "wert": f["wert"],
                "feldgruppe": "zaehlung" if f["feld"] in ZAEHLFELDER else ("streuung" if "standard_deviation" in f["feld"] else "mittelwert"),
                "outcome": (record.get("context") or {}).get("outcome"),
                "klasse": befund["klasse"],
                "zeilen_mit_wert": befund["zeilen"],
                "belege": befund["belege"],
                "regel_bindet_record": bool(bindung.get("zellen")),
                "regel_grund": bindung.get("grund"),
                "gold_wert_am_schluessel": gold.get((f["feld"], f["arm"])) == f["wert"],
            }
        )

    verteilung = Counter(e["klasse"] for e in ergebnisse)
    nach_feld = Counter(e["feldgruppe"] for e in ergebnisse)
    feld_gesamt = Counter(
        "zaehlung" if f["feld"] in ZAEHLFELDER else ("streuung" if "standard_deviation" in f["feld"] else "mittelwert")
        for f in faelle
    )
    loesbar = verteilung["eindeutig_benannt"]
    teilweise = verteilung["mehrdeutig_benannt"]
    ergebnis = {
        "stand": "2026-11-21",
        "grundgesamtheit": len(faelle),
        "stichprobe": len(ergebnisse),
        "verfahren": f"jeder {SCHRITT}. Fall der Liste",
        "verteilung": dict(verteilung),
        "feldgruppen_stichprobe": dict(nach_feld),
        "feldgruppen_gesamt": dict(feld_gesamt),
        "loesbar_durch_zeilenbenennung": loesbar,
        "teilweise_loesbar": teilweise,
        "faelle": ergebnisse,
    }
    (HIER / "zeilenbenennung_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld'].replace('_', ' ')} | {e['arm']} | {e['wert']} | "
        f"{e['klasse']} | {e['zeilen_mit_wert']} | "
        f"{(e['belege'][0]['gruppe'] + ' / ' if e['belege'] and e['belege'][0]['gruppe'] else '').encode('ascii', 'replace').decode()}"
        f"{(e['belege'][0]['label'] if e['belege'] else '-')[:40].encode('ascii', 'replace').decode()} | "
        f"{'ja' if e['regel_bindet_record'] else 'nein'} |"
        for e in ergebnisse
    )
    bericht = f"""# Zeilenbenennung im Prompt gegen `fn_wert_ersetzt` (21.11.2026)

Offline, ohne Netzaufruf. Stichprobe: jeder {SCHRITT}. der {len(faelle)} Faelle
(`fn_wert_ersetzt`), also {len(ergebnisse)} Faelle ueber die ganze Liste verteilt.

Geprueft wird nur die Voraussetzung, die ein Prompt erfuellen muesste: steht der
Goldwert im Dokument in einer Zeile, deren Label oder Zeilengruppe den Outcome
benennt? Ist das eindeutig, kann eine explizite Zeilenangabe den Fall loesen.

## Verteilung

| Klasse | Faelle |
|---|---:|
| eindeutig benannt | {verteilung['eindeutig_benannt']} |
| Tabelle ueber Kaption benannt (Zaehlfelder) | {verteilung['kaption_benannt']} |
| mehrdeutig benannt | {verteilung['mehrdeutig_benannt']} |
| Wert ohne Outcome-Bezug | {verteilung['ohne_outcome_bezug']} |
| Wert nur im Fliesstext, keine Tabellenzeile | {verteilung['wert_nur_im_fliessetext']} |
| Wert nicht im Dokument | {verteilung['wert_nicht_im_dokument']} |

## Faelle

| Record | Feld | Arm | Wert | Klasse | Zeilen mit Wert | Gruppe / Label | Regel bindet Record |
|---|---|---|---|---:|---|---|---|
{tab}

## Antwort

Eine explizite Zeilenbenennung im Prompt erreicht hoechstens 4 der 20 Faelle:
eine eindeutig benannte Zeile, eine mehrdeutige (Zusatzangabe noetig) und zwei
Zaehlfelder, deren Tabelle die Kaption benennt. Bei `yun2024:389` ist der Wert
175 allerdings die Groesse einer Untergruppe (`Complicated (n = 175)`), nicht
die Armgroesse; nach Sichtpruefung bleiben 3 belastbare Faelle. Die anderen 16
sind so nicht loesbar: 14 Werte stehen nur im Fliesstext, 2 in Zeilen ohne
Outcome-Bezug.

## Lesart

`eindeutig benannt` heisst: der Prompt koennte die Zeile nennen, und die Zeile
ist ohne Zusatzwissen eindeutig. `mehrdeutig benannt` heisst: mehrere Zeilen
nennen den Outcome, es braucht zusaetzlich Gruppe oder Zeitpunkt. Die beiden
restlichen Klassen kann eine Zeilenbenennung nicht erreichen, weil der Wert
nicht in einer benannten Zeile steht.
"""
    (HIER / "zeilenbenennung_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")
    print(f"Stichprobe {len(ergebnisse)} von {len(faelle)}: {dict(verteilung)}")
    for e in ergebnisse:
        print(f"{e['record_id']:14s} {e['feld']:28s} {e['wert']:>7} | {e['klasse']:22s} | "
              f"Zeilen {e['zeilen_mit_wert']} | Regel bindet: {'ja' if e['regel_bindet_record'] else 'nein'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
