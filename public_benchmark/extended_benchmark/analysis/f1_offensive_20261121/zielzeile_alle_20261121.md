# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
295 `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias | nur `Mittel (SD)` | Ereignisse aus, Mittel beide Formate |
|---|---:|---:|---:|---:|
| Zielzeile gefunden | 156 | 178 | 178 | 178 |
| Zellen geliefert | 36 | 44 | 24 | 41 |
| TP (exakt) | 18 | 24 | 12 | 24 |
| FP (exakt) | 18 | 20 | 12 | 17 |
| TP (auf ganze Zahl gerundet) | 18 | 26 | 12 | 24 |
| FP (auf ganze Zahl gerundet) | 18 | 18 | 12 | 17 |

## FP nach Feldtyp (Alias-Lauf vor der Umstellung, 20 FP)

| Feldtyp | FP |
|---|---:|
| groesse | 10 |
| mittel | 10 |

## Formate der gelieferten Zellen (Endvariante)

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| groesse | groessenzeile | 12 | 10 |
| mittel | mittel_sd | 0 | 2 |
| mittel | plus_minus | 12 | 5 |

## FP nach Zellformat

| Feldtyp | Zellformat | FP |
|---|---|---:|
| groesse | groessenzeile | 10 |
| mittel | plus_minus | 5 |
| mittel | sonstig | 3 |
| mittel | mittel_sd | 2 |


Nur durch den Alias neu geliefert: 8 Zellen, davon
6 exakt richtig und
8 nach Rundung richtig.
Die zwei exakten FP sind Rundungen: 31.7 gegen Gold 32 und 19.8 gegen Gold 20.

## Neue Zellen

| Record | Feld | Regelwert | Gold | richtig |
|---|---|---:|---:|---|
| `yun2024:426` | intervention_group_size | 49.0 | 49.0 | ja |
| `yun2024:426` | intervention_mean | 31.7 | 32.0 | nein |
| `yun2024:426` | comparator_group_size | 44.0 | 44.0 | ja |
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

In der Endvariante stellen sich die 17 FP so:

* Groesse 10, davon 10 richtig (siehe Format-Tabelle).
* Mittel 5 im Format `+/-`, 12 richtig.
* Mittel 2 im Format `Mittel (SD)`, 0 richtig - dort ist die Zeile oder Spalte
  falsch, nicht das Format.

Enthaelt ein Dokument eine Tabelle mit Wochenspalte, in der das Outcome
mehrfach vorkommt, gilt die Zeile des letzten Zeitpunkts statt der
Baseline-Zeile; bei mehreren solchen Tabellen entscheidet die fruehste (die
Haupttabelle steht vor den Subgruppentabellen).

`yun2024:193` wird damit richtig (138/131 aus Tabelle 2, Woche 28).
`yun2024:196` bleibt falsch: die Haupttabelle 2 nennt fuer Woche 28 die Werte
80/78, Gold (24/24) stammt aus Tabelle 3, einer Subgruppe (MMSE-J 20 bis 23).

Die Armzuordnung der Groessen folgt den Spaltennamen (`POSITIONAL = False`). Die
Positionsregel (erste Datenspalte = Intervention) ist umschaltbar und in
`armreihenfolge_20261121.md` gemessen: sie holt die acht PMC5617873-Zellen und
macht dafuer die beiden Arme von `yun2024:426` falsch.

Trefferquote: 24 von 41 Zellen, also
58 Prozent. Ereignisse tragen
nichts bei, Groessen und Mittel teilen sich die Treffer. Die Umstellung von der
ersten Zahl auf zwei erlaubte Formate kostet 3 weitere Zellen des Formats
`sonstig`, alle drei waren falsch.
