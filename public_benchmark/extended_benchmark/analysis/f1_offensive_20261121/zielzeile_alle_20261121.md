# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
227 `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias | nur `Mittel (SD)` | Ereignisse aus, Mittel beide Formate |
|---|---:|---:|---:|---:|
| Zielzeile gefunden | 116 | 129 | 129 | 129 |
| Zellen geliefert | 28 | 34 | 16 | 33 |
| TP (exakt) | 22 | 26 | 14 | 30 |
| FP (exakt) | 6 | 8 | 2 | 3 |
| TP (auf ganze Zahl gerundet) | 22 | 28 | 14 | 30 |
| FP (auf ganze Zahl gerundet) | 6 | 6 | 2 | 3 |

## FP nach Feldtyp (Alias-Lauf vor der Umstellung, 8 FP)

| Feldtyp | FP |
|---|---:|
| mittel | 6 |
| groesse | 2 |

## Formate der gelieferten Zellen (Endvariante)

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| groesse | groessenzeile | 10 | 2 |
| mittel | mittel_sd | 4 | 0 |
| mittel | plus_minus | 16 | 1 |

## FP nach Zellformat

| Feldtyp | Zellformat | FP |
|---|---|---:|
| mittel | sonstig | 3 |
| groesse | groessenzeile | 2 |
| mittel | mittel_sd | 2 |
| mittel | plus_minus | 1 |


## Streuung als eigenes Feld

Auftraege aus den `fn_wert_ersetzt`-Faellen mit Feld `*_standard_deviation`:
68. Geliefert 17, davon richtig
17 und falsch 0. Gelesen wird die Streuung aus
Zellen im Format `Mittel (SD)` oder `Mittel +/- SD`. Druckt die Nachher-Tabelle
keine SD, sondern ein 95%-KI, leitet `wert_aus_zelle` sie ab
(`SD = halbe Intervallbreite / 1.96 * sqrt(n)`); solche Zellen tragen
`abgeleitet: True` und `herkunft: 95%-KI` und sind damit von abgelesenen
Streuungen unterscheidbar (hier 0 Zellen).

Nur durch den Alias neu geliefert: 6 Zellen, davon
4 exakt richtig und
6 nach Rundung richtig.
Die zwei exakten FP sind Rundungen: 31.7 gegen Gold 32 und 19.8 gegen Gold 20.

## Neue Zellen

| Record | Feld | Regelwert | Gold | richtig |
|---|---|---:|---:|---|
| `yun2024:426` | intervention_mean | 31.7 | 32.0 | nein |
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

In der Endvariante stellen sich die 3 FP so:

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

Neu bewertet `tabellen_zeitpunkt` den Tabellenkopf (`+2` Follow-up, Zeitpunkt,
Woche, Monat; `-2` Baseline, Charakteristika). Bei gleichem Alias-Treffer zieht
`ziel_zeile_zeitpunkt` in die Nachher-Tabelle um, aber nur wenn sie ihre Arme in
der Unterschrift nennt (`I; n=104`); `armkuerzel` und `gruppenzeile_wert` lesen
dann die Armzeilen, die Gruppengroesse kommt aus der Unterschrift. Auf den
227 Faellen aendert das keine Zelle (33/30/3 und 17/17/0); die drei
Records aus `PMC4879328` werden damit gold-richtig, siehe
`tabellenwahl_20261121.md`.

`yun2024:193` wird damit richtig (138/131 aus Tabelle 2, Woche 28).
`yun2024:196` bleibt falsch: die Haupttabelle 2 nennt fuer Woche 28 die Werte
80/78, Gold (24/24) stammt aus Tabelle 3, einer Subgruppe (MMSE-J 20 bis 23).

Die Armzuordnung der Groessen folgt der Spaltenposition (`POSITIONAL = True`):
Die erste Datenspalte ist die Intervention, die zweite der Comparator. Sie holt
die acht PMC5617873-Zellen und macht dafuer die beiden Arme von `yun2024:426`
falsch; dieser Verlust ist bewusst (Gold folgt dort den Spaltennamen, siehe
`armreihenfolge_20261121.md`).

Trefferquote: 30 von 33 Zellen, also
90 Prozent. Ereignisse tragen
nichts bei, Groessen und Mittel teilen sich die Treffer. Die Umstellung von der
ersten Zahl auf zwei erlaubte Formate kostet 3 weitere Zellen des Formats
`sonstig`, alle drei waren falsch.
