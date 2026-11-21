# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
295 `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias | nur `Mittel (SD)` | Ereignisse aus, Mittel beide Formate |
|---|---:|---:|---:|---:|
| Zielzeile gefunden | 156 | 178 | 178 | 178 |
| Zellen geliefert | 36 | 44 | 26 | 43 |
| TP (exakt) | 30 | 34 | 22 | 38 |
| FP (exakt) | 6 | 10 | 4 | 5 |
| TP (auf ganze Zahl gerundet) | 30 | 36 | 22 | 38 |
| FP (auf ganze Zahl gerundet) | 6 | 8 | 4 | 5 |

## FP nach Feldtyp (Alias-Lauf vor der Umstellung, 10 FP)

| Feldtyp | FP |
|---|---:|
| mittel | 6 |
| groesse | 4 |

## Formate der gelieferten Zellen (Endvariante)

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| groesse | groessenzeile | 18 | 4 |
| mittel | mittel_sd | 4 | 0 |
| mittel | plus_minus | 16 | 1 |

## FP nach Zellformat

| Feldtyp | Zellformat | FP |
|---|---|---:|
| groesse | groessenzeile | 4 |
| mittel | sonstig | 3 |
| mittel | mittel_sd | 2 |
| mittel | plus_minus | 1 |


Nur durch den Alias neu geliefert: 8 Zellen, davon
4 exakt richtig und
6 nach Rundung richtig.
Die zwei exakten FP sind Rundungen: 31.7 gegen Gold 32 und 19.8 gegen Gold 20.

## Neue Zellen

| Record | Feld | Regelwert | Gold | richtig |
|---|---|---:|---:|---|
| `yun2024:426` | intervention_group_size | 44.0 | 49.0 | nein |
| `yun2024:426` | intervention_mean | 31.7 | 32.0 | nein |
| `yun2024:426` | comparator_group_size | 49.0 | 44.0 | nein |
| `yun2024:426` | comparator_mean | 19.8 | 20.0 | nein |
| `yun2024:664` | intervention_mean | 101.9 | 101.9 | ja |
| `yun2024:664` | comparator_mean | 97.6 | 97.6 | ja |
| `yun2024:665` | intervention_mean | 103.4 | 103.4 | ja |
| `yun2024:665` | comparator_mean | 97.6 | 97.6 | ja |

## Lesart

Gelesen wird je Feldtyp: Groessen aus der Groessenzeile, Mittel nur in den
Formaten `Zahl +/- Zahl` und `Zahl (Zahl)`, Streuungen als Zahl in Klammern.
Der Ereignis-Leser ist in allen Laeufen abgeschaltet (vorher 0 TP, 7 FP).

Groessenzeilen kommen aus der Tabelle der Zielzeile; erst wenn dort keine
Groessenzeile steht, gilt der Rueckfall auf die naechste Zeile darueber. Das
Zellformat `n  Mean (95% CI)` einer Zeitverlaufstabelle wird als Zeilen-`n`
gelesen (n nach der Wochenzahl, zweites n nach dem ersten Klammerblock).

In der Endvariante stellen sich die 5 FP so:

* Groesse 4 (196 Subgruppe, 426 Positionsverlust).
* Mittel 1 im Format `+/-` (345: Gold steht nur als Intervallgrenze).

Hat eine Tabelle mehrere Wochenspalten, gilt die Spalte des letzten Zeitpunkts
und der Block, dessen Ueberschrift das Outcome trifft (Alias oder Akronym wie
`MCS`); ohne Treffer der erste Block. Damit sind 33 und 34 richtig.

Nennt das Outcome ein Messwort (`stiffness`, `range of motion`, `neutral zone`,
`neural zone`), gilt nur eine Zielzeile in einem Block mit passendem Label; bei
mehreren solchen Bloecken gewinnt der spaetere. Das holt 221 bis 223 und waehlt
bei mehreren Spalten desselben Arms das genauere Label (ACVC-HA statt ACVC).

Enthaelt ein Dokument eine Tabelle mit Wochenspalte, in der das Outcome
mehrfach vorkommt, gilt die Zeile des letzten Zeitpunkts statt der
Baseline-Zeile; bei mehreren solchen Tabellen entscheidet die fruehste (die
Haupttabelle steht vor den Subgruppentabellen).

`yun2024:193` wird damit richtig (138/131 aus Tabelle 2, Woche 28).
`yun2024:196` bleibt falsch: die Haupttabelle 2 nennt fuer Woche 28 die Werte
80/78, Gold (24/24) stammt aus Tabelle 3, einer Subgruppe (MMSE-J 20 bis 23).

Die Armzuordnung der Groessen folgt der Spaltenposition (`POSITIONAL = True`):
Die erste Datenspalte ist die Intervention, die zweite der Comparator. Sie holt
die acht PMC5617873-Zellen und macht dafuer die beiden Arme von `yun2024:426`
falsch; dieser Verlust ist bewusst (Gold folgt dort den Spaltennamen, siehe
`armreihenfolge_20261121.md`).

Trefferquote: 38 von 43 Zellen, also
88 Prozent. Ereignisse tragen
nichts bei, Groessen und Mittel teilen sich die Treffer. Die Umstellung von der
ersten Zahl auf zwei erlaubte Formate kostet 3 weitere Zellen des Formats
`sonstig`, alle drei waren falsch.
