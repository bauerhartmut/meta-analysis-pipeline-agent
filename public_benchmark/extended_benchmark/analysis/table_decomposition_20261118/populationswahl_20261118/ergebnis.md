# Sprint 46 - Populationswahl aus der Kopfbeschriftung

Stand 18.11.2026. Offline, rein lesend: kein Modelllauf, kein Netz, Gold und
eingefrorene Auswahl unveraendert. Zahlen aus `messung.json` (Skript
`diagnose_populationswahl.py`).

## Frage

Werden die 15 `population_mismatch`-Felder aus Sprint 45 wertgleich, wenn die
Tabelle nicht aus der eingefrorenen Auswahl, sondern aus dem Dokument gewaehlt
wird - und bleibt die Armzuordnung unveraendert?

## Regel

`research_agent/table_decomposition/tabellenwahl.py`, drei Stufen:

1. Traegt eine der aktuellen Tabellen eine Zeile zum Outcome, bleibt es bei
   ihr - auch wenn die Kopfbeschriftung nach Baseline klingt.
2. Sonst bleibt es ebenfalls bei der aktuellen Tabelle, wenn sie keine
   Baseline-Tabelle ist.
3. Ist sie eine Baseline-Tabelle (Caption oder Kopfband nennt "baseline",
   "demographic" oder "characteristics") und hat keine Outcome-Zeile, gewinnt
   die Tabelle mit den meisten Outcome-Zeilen, die selbst keine Baseline ist.

Die Arme werden nicht angefasst: die gewaehlte Tabelle wird mit demselben
`enrich_table` und denselben Transfers gelesen. Kein Goldwert steuert die Wahl.

## Ergebnis

| Groesse | vorher | nachher |
| --- | --- | --- |
| erreichbare Goldfelder | 94 | 94 |
| wertgleich | 58 | **62** |
| nicht wertgleich | 36 | 32 |

* Tabellenwechsel: **4** von 48 Records.
* neu wertgleich: **4** Felder, neu nicht wertgleich: **0**.
* Armwechsel: **0**.
* Von den 15 `population_mismatch`-Feldern werden **4** wertgleich, nicht 10.

Die vier Felder sind die Gruppengroessen von `yun2024:645` und `yun2024:647`
(Bayley-III): die Auswahl nahm die Baseline-Tabelle mit 29/30, die
Outcome-Tabelle druckt 27/26. Beide Records wechseln von `PMC4675066:T1` nach
`PMC4675066:T2`, die Arme der Kopfangaben bleiben `intervention` und
`comparator`.

## Warum nur 4 von 15

| Dokument | Felder | Befund |
| --- | --- | --- |
| PMC4675066 | 4 | Baseline 29/30 gegen Outcome 27/26 - Regel greift. |
| PMC5360580 | 2 | Die Auswahl heisst "Table 1" und traegt keine Baseline-Beschriftung; die Regel wechselt nicht. T6 druckt 169/167. |
| PMC2430617 | 4 | T1 ist als Baseline erkannt, aber die AE-Tabelle T4 traegt keine Outcome-Zeile zum Outcome "adverse events" (ihre Gruppenkoepfe stehen in einer Datenzeile, nicht in einem Kopfband). Kein Ziel, kein Wechsel. |
| PMC4230312 | 4 | T1/T3 sind ausdruecklich "(safety population)"; die ITT-Zahlen 283/289/204 stehen nur im Fließtext, in keiner Tabelle. |
| PMC5122613 | 1 | T2 traegt CTT-Zeilen, druckt aber kein n; 28 steht nur im Fließtext. |

Von den 10 Feldern, deren Zahl in einer anderen Tabelle gedruckt steht, sind
also nur die vier aus PMC4675066 mit einer reinen Kopfbeschriftungs-Regel
erreichbar. Die anderen sechs scheitern an der fehlenden Population in der
Beschriftung (PMC5360580) oder an der fehlenden Outcome-Zeile im Ziel
(PMC2430617).

## Nebenwirkungen

Zwei weitere Records wechseln, ohne die 94 Felder zu veraendern:
`yun2024:672` (`PMC4550271:T1` -> `:T4`) und `yun2024:675`
(`PMC4550271:T1` -> `:T2`). Ihre Goldfelder waren schon vorher nicht
erreichbar; der Wechsel kostet dort nichts, zeigt aber, dass die Regel auch
ausserhalb der 15 Felder feuert.

## Grenzen

* Die Regel waehlt nur Tabellen; sie aendert keine Rolle, keinen Arm und keine
  Spalte.
* Sie erkennt Baseline nur an der Beschriftung. Eine Tabelle mit Caption
  "Table 1", deren Zeilen Alters- und Geschlechtsangaben sind, erkennt sie
  nicht (PMC5360580).
* Ein Gruppenkopf in einer Datenzeile (PMC2430617:T4) ist fuer die
  Kopfangaben-Erkennung unsichtbar; das ist ein Parser-Thema, nicht die
  Tabellenwahl.
* Die Messung ist offline und deterministisch; die 94/58 davor sind identisch
  mit Sprint 45.

## Empfehlung fuer Sprint 47

**Die Tabellenwahl ist als Produktionsregel noch nicht reif, aber der Kern
traegt.** Naechster Hebel mit dem besten Verhaeltnis: die zwei verbleibenden
Parser-Luecken, die zusammen 6 Felder kosten - (a) Gruppenkoepfe in einer
Datenzeile als Kopfangabe lesen (PMC2430617, 4 Felder), (b) Baseline ueber
Zeilenlabels statt nur ueber die Caption erkennen (PMC5360580, 2 Felder).
Beides offline messbar, ohne Armzuordnung und ohne Gold zur Steuerung. Erst
wenn diese beiden Luecken geschlossen sind, lohnt es, die Tabellenwahl in die
Produktion zu heben; bis dahin bleibt sie ein Messwerkzeug mit +4 Feldern.
