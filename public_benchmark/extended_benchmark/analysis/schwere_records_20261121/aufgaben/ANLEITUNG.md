# Extraktionsanleitung

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
