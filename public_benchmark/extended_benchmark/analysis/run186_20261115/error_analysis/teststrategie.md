# Teststrategie für die nächste Iteration (15.11.2026)

## 1. Ausgangslage: die 186 Records sind kein Holdout mehr

Die 186 Records waren Grundlage für: Zeitpunktannotation, v6-Prompt, Rückfallregel,
Length-Diagnose, v7-Pilot und Folgelauf. Jede Schema- und Promptentscheidung
wurde an ihnen getroffen. Sie sind damit **Entwicklungsdaten**, auch wenn die
Goldzellen unverändert sind. Ein F1-Wert auf diesen 186 ist ab jetzt eine
Entwicklungs- und keine Testzahl.

Verfügbare Daten **[belegt aus den Record-Dateien]**:

| Bestand | Records | Goldzellen | Status |
|---|---:|---:|---|
| Kandidaten-Split gesamt | 262 | 809 | annotiert mit Zielzeitpunkt |
| davon 186er-Lauf | 186 | 566 | **verbraucht** (Prompt- und Schemaarbeit) |
| davon zweite Kohorte | 76 | 243 | **unberührt**, noch nie einem Modell gezeigt |
| Dev-Split (historisch) | 43 | 170 | verbraucht (v1–v11) |
| Yun-Test-Rest (unkuratiert) | 407 | – | nicht kuratiert, nur als Reserve |

## 2. Vorschlag: DEV / TEST / Reserve

**DEV (Entwicklung, 110 Records aus den 186)**

* alle 47 Length-Ausfälle,
* alle 6 leeren Antworten,
* alle 7 armgemischten Records (5 davon sind Gold-Konflikte),
* 50 zufällig gezogene Normalrecords (Seed dokumentieren),
* Überlappungen zusammengezählt, nicht doppelt.

Damit enthält DEV die schwierigen Fälle gezielt und ist für Promptarbeit
gedacht. Die übrigen ≈ 76 Records der 186 bleiben als **alte Reserve** liegen;
sie zählen nicht als Test, weil sie schon in Auswertungen sichtbar waren.

**TEST (76 Records der zweiten Kohorte, 243 Goldzellen)**

Voraussetzungen, bevor TEST das erste Mal läuft:

1. Zielzeitpunkte annotieren (Heuristik plus manuelle Stichprobe von 15 Fällen,
   Vorgehen wie `zeitpunkt_stichprobe.md`).
2. Einfrieren als `records/yun_test76_ziel.jsonl` mit SHA-256 im Bericht.
3. Festlegen, welcher Prompt/Schema-Stand der **eine** Testlauf ist.

**Eingefroren am 16.11.2026:** `records/yun_test76_ziel.jsonl`, 76 Records,
243 Goldzellen, 0 Records ohne Zielzeitpunkt.

```
SHA-256  74fd0c057356c22831fae45d71644d8b7640a8a109fb48a60cc7782cfb1db704
         (Version 2, 16.11.2026; Version 1 war 06fea97c…, siehe
         `korrektur_yun2024_479.md`)
Bytes    111699
```

Der Hash wird von `tests/test_test76_ziel.py` geprüft; jede Änderung an Gold,
Ziel oder Reihenfolge bricht den Test und braucht eine neue Version mit
aktualisiertem Hash.

**Vier Zielzeitpunkte sind als `unsicher` markiert** — `yun2024:63` (MRI
assessment), `yun2024:71` (at admission), `yun2024:693` und `yun2024:694`
(24 h postoperativ). Sie stehen nicht wörtlich im Abstract, sondern sind aus
dem Messaufbau abgeleitet. `evaluate_fallback.py` führt sie im Block
`unsichere_ziele` (Records, Zellen, richtig, falsch, IDs) getrennt; die
Hauptmetriken enthalten sie weiterhin.

Annotation: 44 Records mit ausschließlich Gruppengrößen → `baseline` (Regel),
32 Records manuell nach Abstract (`annotate_test76.py`, Tabelle in
`test76_annotation.md`, unsichere Ziele dort fett markiert). Verteilung: 44 baseline, 7 „post (after 4-week
training)“, 4 „postintervention phase“, 4 „post-training“, 2 „intraoperative
(onset)“, 2 „24 h postoperatively“, je 1 „at admission“, „postintervention“,
„during the operation“, „at birth (cord blood)“, „end of follow-up“,
„MRI assessment (timepoint not stated)“. Der Gold-Hash der 76 Records ist vor
und nach der Annotation identisch.

Ohne Zielzeitpunkt wäre TEST eine andere Aufgabe (Rückfall ohne Vorgabe) und
nicht mit DEV vergleichbar.

## 3. Regeln gegen Leckage

* Prompt-, Schema- und Schwellenwertänderungen nur auf DEV.
* TEST höchstens **einmal je Architekturentscheidung**, insgesamt höchstens zwei
  Mal in dieser Iteration.
* Jeder TEST-Lauf wird in `error_analysis/testlaeufe.md` mit Run-ID, Datum und
  Fragestellung eingetragen; nachträgliche Änderungen am Prompt nach einem
  TEST-Lauf machen den Lauf ungültig.
* Keine recordweise Nachbesserung auf TEST: Wenn ein einzelner TEST-Record
  angepasst wird, gilt der Lauf als verbraucht.
* Alle Varianten laufen auf **denselben** TEST-Records und mit demselben
  `max_tokens`.

## 4. Kennzahlen, die getrennt berichtet werden

1. Zell-F1 (Hauptwert, `gesamt.cell_f1`).
2. Precision und Recall getrennt.
3. MAE **nur mit** `mae_coverage` und zusätzlich Median-Fehler (die MAE ist
   skalenabhängig, siehe `folgelauf_v7_und_goldkonflikte.md`).
4. exakte Records.
5. Length-Quote und leere Antworten getrennt (nicht als „Ausfälle" summiert).
6. Aufrufe und Tokens je Record, aufgeschlüsselt nach Pfad (`quelle`/`pfad`).

Für Anteile werden Wilson-Intervalle angegeben; bei 76 Records ist die
Unsicherheit groß (bei 30 % Anteil etwa ±10 Prozentpunkte), Unterschiede unter
5 Prozentpunkten sind mit diesem TEST nicht belegbar.

## 5. Kostengünstiger Pilot zum Variantenvergleich

**12 Records, alle vier Varianten, dieselbe Stichprobe:**

| Gruppe | Records | Warum |
|---|---:|---|
| Length-Ausfälle | 3 | prüft Variante D und B |
| leere Antworten (nur Gruppengrößen) | 3 | prüft die Schema-Lücke aus A |
| armgemischt / Gold-Konflikt | 3 | prüft, ob B die Arme trennt |
| normale Records mit Zellen | 3 | prüft, ob Precision erhalten bleibt |

Kostenrahmen **[Schätzung]**: A ≈ 12 × 12.000 = 144.000; B ≈ 12 × 3 Aufrufe
× 3.500 = 126.000; D ≈ 12 × 15.000 = 180.000; zusammen unter 500.000 Tokens.
Gemessen wird zuerst die Form (Length-Quote, leere Antworten, parsebares JSON),
dann die Zellmetriken auf denselben 12 Records.

Abbruchregel: Eine Variante wird nach 4 von 12 Ausfällen gestoppt.

## 6. Was diese Strategie nicht leistet

* 76 Records und 243 Zellen sind klein: Ein F1-Unterschied von 0,02 ist damit
  nicht belegbar.
* Die zweite Kohorte stammt aus demselben Kandidaten-Split; ein Domänenwechsel
  (andere Zeitschriften) ist nicht abgedeckt.
* Ohne unabhängige Zweitannotation bleibt Gold der Maßstab, auch wo es
  nachweislich Konflikte enthält (5 bestätigte Fälle, alle außerhalb der 47).
