# Sprint 48 - Gedruckter Zeitpunkt als Fundstellen-Filter

Stand 18.11.2026, zweite Fassung: Zeilenlabels als gedruckte Quelle. Offline,
rein lesend: kein Modelllauf, kein Netz, Gold und eingefrorene Auswahl
unveraendert. Zahlen aus `messung.json` (`diagnose_zeitpunkt.py`).

## Frage

Lassen sich die sechs `timepoint_mismatch`-Felder aufloesen, wenn eine
Fundstelle nur dann an einen Zeitpunkt gebunden wird, wenn der Zielzeitpunkt
**gedruckt** ist - im Outcome und an der Fundstelle selbst?

## Regel (`research_agent/table_decomposition/zeitpunkt.py`)

Gedruckte Quellen an der Fundstelle:

* **Spaltenkopf** - Beschriftungskette der Spalte (`week 8`, `baseline`).
* **Zeilenlabel** - das eigene Label der Zeile (`7 min`); druckt es keinen
  Zeitpunkt, tritt die naechste Gruppenzeile darueber ein
  (`Visit 3B: 16-hour persistence of action` -> `visit 3b`).
* **Gruppe** - nennt das Outcome auch die Gruppe und druckt eine der
  Fundstellen sie, bleiben nur die Fundstellen mit passender Gruppe uebrig
  (noetig, weil `7 min` in mehreren Visiten steht).

Gebunden wird nur bei Gleichheit normalisierter, gedruckter Angaben; die
Fundstelle traegt danach `arm_basis = zeitpunkt:<zeitpunkt>`. Kein Rat aus
Spaltenposition, Tabelle oder Goldwert.

## Ergebnis: 0 von 6 entschieden

| Groesse | Wert |
| --- | --- |
| Stellen der Auswahl | 194 |
| davon mit gedrucktem Zeitpunkt im Spaltenkopf | 12 |
| Felder, die die Regel bindet | 3 (alle in `:445`) |
| `timepoint_mismatch`-Felder | 6 |
| davon mit gedrucktem Zielzeitpunkt im Outcome | 2 |
| davon mit Zeitpunkt im Spaltenkopf | 0 |
| davon mit Zeitpunkt im Zeilenlabel | **2** |
| davon entschieden | **0** |

Das Zeilenlabel bringt die Bindung also naeher heran als der Spaltenkopf -
entschieden ist trotzdem keines der beiden Felder.

## `yun2024:445`: Zeile getroffen, Wert verschoben

Die Bindung funktioniert: das Outcome nennt `visit 3B at 7 min`, die Tabelle
`PMC4140238:T2` druckt genau das, und die Regel engt auf **eine** Zeile ein
(`Visit 3B`, Zeile `7 min`). Trotzdem ist das Feld nicht entschieden:

* `comparator_mean`: die gebundenen Zellen sind Verbundzellen (`2.1 (69)`), aus
  denen die Fundstelle keinen Einzelwert bildet - `werte_zeile = []`.
* `intervention_mean`: die Regel liefert genau **einen** Wert, **0.9** - aber
  das Gold ist **1.2**.

Der Grund steht in der Tabelle selbst. Die Spaltenkoepfe sind

```
c1 Time of itching grading post-CAC | c2 Placebo mean score (n)
c3 BBOS 1.5% mean score (n)         | c4 Difference in mean itching score
```

die Datenzeilen tragen ihre Zellen aber eine Spalte weiter links:

```
r6 (Visit 3B)     cells: {0: "3 min", 1: "2.0 (70)", 2: "1.2 (68)", 3: "0.8"}
r8 (Visit 3B/7 min) cells: {0: "7 min", 1: "2.1 (69)", 2: "1.2 (68)", 3: "0.9"}
```

Damit landet der BBOS-Mittelwert (1.2) in der Placebo-Spalte und die Differenz
(0.9) in der BBOS-Spalte. Dass die letzte Zelle die Differenz ist, rechnet sich
nach: 2.1 − 1.2 = 0.9, 1.9 − 0.4 = 1.5, 2.0 − 1.2 = 0.8. Die Zeile ist um eine
Spalte versetzt, weil die Gruppenzeile (`Visit 3B: ...`) eine Zelle mehr hat
als die Datenzeilen.

**Folge: `timepoint_mismatch` war fuer `:445` eine Fehldiagnose.** Nicht der
Zeitpunkt war falsch, sondern die Spaltenzuordnung der Datenzeilen. Die
Zeitpunkt-Regel hat das aufgedeckt, weil sie die richtige Zeile festnagelt und
der Wert daneben liegt.

## `yun2024:665`: unveraendert offen

Das Outcome `FPG` druckt keinen Zeitpunkt; der Zeitpunkt des Records ist eine
Regel (`quelle: "regel"`). Zeilenlabels drucken hier keinen Zeitpunkt
(`zeilen = []`), also bindet die Regel nichts. Der Goldwert ist der
Baseline-Wert aus T1, waehrend T2 die Aenderung druckt - das bleibt eine
Annotationsfrage.

## Grenzen

* Die Regel bildet keinen Wert aus Verbundzellen; wo die Fundstelle nur den
  Zelltext traegt (`2.1 (69)`), bleibt `wert` leer.
* Zeilenlabels decken nur Tabellen ab, die den Zeitpunkt als Zeile fuehren; bei
  Spaltentabellen bleibt es beim Kopf.
* Der Spaltenversatz ist ein Problem des Tabellenpfads, nicht dieser Regel - er
  betrifft jede Auswertung dieser Tabelle, unabhaengig vom Zeitpunkt.

## Empfehlung

**Naechster Hebel: den Zeilenversatz der Tabelle pruefen und beheben.** Eine
Datenzeile mit weniger Zellen als Spalten (hier vier statt fuenf) wird derzeit
von links gefuellt; sie muss an der Zeit- beziehungsweise Labelspalte
ausgerichtet werden, sonst wandert jeder Wert eine Spalte nach links. Das
betrifft alle Tabellen mit einer breiteren Gruppenzeile und ist damit groesser
als die Zeitpunktfrage: es kann andere Felder still verfaelschen. Kosten: eine
Parser-Aenderung mit Gegenprobe auf allen 59 Records; Risiko mittel, deshalb
mit Vorher/Nachher-Bilanz (94/68, 101/83, 46, 55) als Leitplanke.
