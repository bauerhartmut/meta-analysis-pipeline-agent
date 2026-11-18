# Sprint 48 - Gedruckter Zeitpunkt als Fundstellen-Filter

Stand 18.11.2026. Offline, rein lesend: kein Modelllauf, kein Netz, Gold und
eingefrorene Auswahl unveraendert. Zahlen aus `messung.json`
(`diagnose_zeitpunkt.py`).

## Frage

Lassen sich die sechs `timepoint_mismatch`-Felder aufloesen, wenn eine
Fundstelle nur dann an einen Zeitpunkt gebunden wird, wenn **beides gedruckt**
ist - der Zielzeitpunkt im Outcome-Text und derselbe Zeitpunkt in der
Spaltenbeschriftung?

## Regel (`research_agent/table_decomposition/zeitpunkt.py`)

* Zielzeitpunkt aus dem Outcome: `7 min`, `week 8`, `baseline`, `visit 3B`.
* Zeitpunkt im Spaltenkopf: dieselben Formen, gelesen aus der
  Beschriftungskette der Spalte.
* Gebunden wird nur bei Gleichheit der normalisierten Form; die Fundstelle
  traegt danach `arm_basis = zeitpunkt:<zeitpunkt>`. Fehlt eine Seite, bleibt
  es bei keiner Bindung - kein Rat aus Spaltenposition, Tabelle oder Goldwert.

## Ergebnis: 0 von 6 entschieden

| Groesse | Wert |
| --- | --- |
| Stellen der Auswahl | 194 |
| davon mit gedrucktem Zeitpunkt im Spaltenkopf | 12 |
| Felder, die die Regel bindet | 0 |
| `timepoint_mismatch`-Felder | 6 |
| davon mit gedrucktem Zielzeitpunkt im Outcome | 2 |
| davon mit gedrucktem Zeitpunkt im Spaltenkopf | 0 |
| davon entschieden | **0** |

Die Regel greift also nirgends in dieser Auswahl: die zwoelf Stellen mit
Kopfzeitpunkt gehoeren zu Dokumenten, deren Outcome keinen Zeitpunkt druckt.
Das ist kein Fehler der Regel, sondern die Lage im Korpus.

## Warum, je Feld

**`yun2024:445` comparator_mean (2.1) und intervention_mean (1.2).** Das Outcome
druckt den Zeitpunkt (`ocular itching for visit 3B at 7 min`), die gewaehlte
Tabelle `PMC4140238:T2` druckt ihn aber in den **Zeilenlabels**, nicht in den
Spaltenkoepfen:

```
r6: "Visit 3B: 16-hour persistence of action"   3 min   2.0 (70)  1.2 (68)  0.8
r7:                                              5 min   2.3 (70)  1.3 (67)  1.0
r8:                                              7 min   2.1 (69)  1.2 (68)  0.9
```

Die Spaltenkoepfe lauten `Placebo mean score (n)` und `BBOS 1.5% mean score
(n)` - kein Zeitpunkt. Beide Felder bleiben damit offen; **nicht** umgesetzt
(Vorschau, mit Gold geprueft): eine Regel, die auch Zeilenlabels als gedruckten
Zeitpunkt zulaesst, wuerde beide binden - der Goldwert steht in Zeile `7 min`
unter `Visit 3B`.

**`yun2024:665` comparator/intervention mean und Standardabweichung.** Das
Outcome ist `FPG` und druckt keinen Zeitpunkt. Der Zeitpunkt des Records ist
keine gedruckte Angabe, sondern eine Regel:

```
target: "primary time point of the trial (if not stated: the last reported time point)"
quelle: "regel", status: "Regel (Yun kennt kein Zeitpunktfeld)"
```

Gedruckt sind nur Richtungen: `PMC4987981:T1` traegt `Baseline
characteristics`, `T2` traegt `Mean change [Mean ± SD]`. Der Goldwert
(103.4 ± 28.9) ist der **Baseline**-Wert aus T1. Eine Regel, die dem gedruckten
Ziel folgt, muesste also die Aenderungstabelle nehmen - und laege gegen die
Annotation. Das Feld ist damit nicht durch einen gedruckten Zeitpunkt zu
entscheiden, sondern nur durch eine Annahme darueber, welcher Zeitpunkt gilt.

## Was daraus folgt

* Fuer die zwei Felder aus `:445` fehlt nicht der gedruckte Zeitpunkt, sondern
  seine **Position**: er steht im Zeilenlabel. Das ist die naechste zulaessige
  Quelle - gedruckt, im selben Tabellenblock, ohne Gold.
* Fuer die vier Felder aus `:665` fehlt der gedruckte Zielzeitpunkt ganz. Hier
  hilft keine Regel, die nur druckt, was dasteht; noetig waere eine
  dokumentierte Annahme (Baseline gegen Aenderung), und die ist eine
  fachliche Entscheidung, keine Messung.

## Grenzen

* Die Regel liest nur die Beschriftungskette der Spalte, nicht Zeilenlabels und
  nicht Tabellenueberschriften.
* `zeitpunkt` an der Fundstelle ist bei Kopfangaben leer; die Regel kann dort
  nichts binden.
* Keine Aussage darueber, ob die Zeitpunktangabe im Paper richtig ist - nur
  darueber, ob sie gedruckt und auffindbar ist.

## Empfehlung

**Naechster Hebel: Zeilenlabel als gedruckte Zeitpunktquelle zulassen** (eng:
Labelzelle der Zeile plus Gruppenzeile darueber, gleiche Normalisierung). Das
schliesst die zwei Felder aus `:445` ohne Gold und ohne Annahme; Kosten: ein
Messlauf offline, Risiko gering, weil die Bindung dieselbe bleibt (Gleichheit
zweier gedruckter Zeitpunkte). Die vier Felder aus `:665` sollten als
Annotationsfrage offen ausgewiesen bleiben, nicht stillschweigend geloest
werden.
