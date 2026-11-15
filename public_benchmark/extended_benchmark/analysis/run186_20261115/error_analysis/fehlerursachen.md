# Fehlerursachen der 47 v7-Records (15.11.2026)

Quelle: `fehlerklassifikation_47_records.csv` (je Record) und `kennzahlen.json`
(Aggregate), erzeugt von `analysiere_47.py` aus den vorhandenen Läufen. Kein
Modellaufruf, keine Gold-Änderung.

## 1. Verteilung

| Status v7 | Records | Zellen | Tokens v7 |
|---|---:|---:|---:|
| Antwort mit Zellen | 23 | 79 | 268.540 |
| gültiges JSON ohne Zellen | 6 | 0 | — |
| `length` ohne Ausgabe | 18 | 0 | 342.000 |
| **gesamt** | **47** | **79** | **610.540** |

Zellmetriken dieser 47 Records: Goldzellen 133, extrahiert 79, Treffer 48,
falscher Wert 16, überzählige Zelle 15, Auslassung 69. Precision **0,6076**,
Recall **0,3609**. Zeitpunkte: zieltreu 48, Rückfall 12, unklar 4.

## 2. Kategorien (Mehrfachnennung, nur belegte Zuordnungen)

| Kategorie | Records |
|---|---:|
| A: `length`-Abbruch ohne Ausgabe | 18 |
| A: leere Antwort (gültiges JSON, 0 Zellen) | 6 |
| B: falscher Zahlenwert | 8 |
| B: überzählige Zelle (Feld nicht im Gold) | 7 |
| B: Auslassung | 6 |
| B: Rückfall-Zeitpunkt | 5 |
| B: Zeitpunkt unklar | 2 |
| C: bestätigter Gold-Konflikt | **0** |
| C: Komparator nur als Baseline berichtet | **0** (149/150 liegen nicht in den 47) |

Wichtig: Unter den 47 Records ist **kein** bestätigter Gold-Konflikt. Die
Gold-Diskussion der letzten Runde (`yun2024:75, 76, 78, 80, 81`) betrifft
Records, die im v6-Lauf Zellen geliefert haben, nicht die Fehlzeilen.

## 3. Die sechs leeren Antworten sind systematisch, nicht zufällig

Alle sechs haben dieselbe Goldstruktur: **zwei Zellen, beide Gruppengrößen**.

| Record | Dokument | Ziel | Goldzellen |
|---|---|---|---|
| `yun2024:252` | PMC5614421 | baseline | intervention/comparator_group_size |
| `yun2024:325` | PMC5559992 | baseline | dito |
| `yun2024:403` | PMC5781260 | baseline | dito |
| `yun2024:571` | PMC5541727 | week 4 | dito |
| `yun2024:613` | PMC115849 | baseline | dito |
| `yun2024:687` | PMC2836833 | baseline | dito |

Das v7-Schema verlangt einen **Outcome-Zeitpunkt für beide Arme** und lässt
Zellen weg, die das Paper nicht berichtet. Gruppengrößen sind aber
Arm-Eigenschaften, keine zeitpunktgebundenen Outcome-Werte; fünf der sechs Ziele
sind `baseline`, wo es keinen Follow-up-Zeitpunkt gibt. Die leere Antwort ist
damit die logische Folge des Schemas **[Hypothese, gestützt durch 6 von 6
gleiche Struktur]**. Es fehlt ein Feldpfad für armbezogene Angaben ohne
Zeitpunkt.

## 4. Die acht Records mit falschen Werten

**a) Gruppengrößen: andere Population oder vertauschte Arme** (12 der 16
Fehlwerte)

| Record | Feld | Modell | Gold | Deutung |
|---|---|---|---|---|
| `yun2024:115` | intervention_group_size | 459 | 456 | Arme vertauscht (Komparator = 456 im Modell) |
| `yun2024:196` | intervention/comparator_group_size | 140 / 135 | 24 / 24 | andere Population (Analysiert vs. randomisiert) **[Hypothese]** |
| `yun2024:357` | intervention/comparator_group_size | 21 / 20 | 13 / 13 | dito |
| `yun2024:483` | intervention/comparator_group_size | 50 / 49 | 59 / 55 | dito |
| `yun2024:533` | intervention/comparator_group_size | 34 / 30 | 37 / 35 | dito |

**b) Mittelwerte und Streuungen aus benachbarter Zeile/Spalte** (4 Fehlwerte)

| Record | Feld | Modell | Gold |
|---|---|---|---|
| `yun2024:151` | intervention_mean | 12.202 | 11.897 |
| `yun2024:196` | intervention/comparator_mean | 1,41 / 1,39 | 1,29 / 1,08 |
| `yun2024:345` | intervention_mean | 3,2 | 2,3 |
| `yun2024:162` | intervention/comparator_standard_deviation | 4,06 / 4,33 | 6,22 / 5,68 |

Diese Fälle sind ohne Blick in die Tabelle nicht eindeutig einer Ursache
zuzuordnen; die Klassifikation im CSV nennt deshalb nur „falscher Wert".

## 5. Überzählige Zellen und Auslassungen

* **15 überzählige Zellen** in 7 Records: Mittelwerte und Ereigniszahlen, die
  nicht im Gold stehen (`yun2024:384` 80/71, `yun2024:465` 3/4, `yun2024:597`
  12,5, `yun2024:117` comparator_events 2, `yun2024:170` 5/4). Ohne manuelle
  Prüfung ist nicht entscheidbar, ob es korrekte, im Gold fehlende Werte sind
  oder falsche Outcome-Zuordnungen — beides ist plausibel, deshalb **keine
  Zuordnung** im CSV.
* **69 Auslassungen** bei 133 Goldzellen; davon sind 10 fehlende
  Standardabweichungen (5 intervention, 5 comparator) und 1 fehlender
  Komparator-Mittelwert. Der Rest entfällt auf Records ohne jede Antwort
  (18 Length + 6 leer = 24 Records).

## 6. Zeitpunkte

48 Zellen sind zieltreu, 12 Rückfall, 4 unklar. Die Rückfälle sind mehrheitlich
richtig (in der Gesamtauswertung Precision 0,83), aber sie zeigen, dass die
v7-Regel „beide Arme am selben Zeitpunkt" in 5 Records zu einem Zeitpunkt
führte, der nicht das Ziel ist.

## 7. Was Gold beiträgt — und was nicht

* **0 der 47 Records** sind bestätigte Gold-Konflikte.
* **0** haben den Komparator-nur-Baseline-Fall.
* Die 6 leeren Antworten entstehen an einer Schema-Lücke, nicht an falschem
  Gold: Das Gold verlangt Gruppengrößen, der Prompt fragt nach
  Outcome-Zeitpunkten.
* Damit ist der Einfluss der Golddaten auf diese 47 Records **gering** — anders
  als in der v6-Gesamtauswertung, wo 5 Records als Gold-Konflikt eingetragen
  sind.
