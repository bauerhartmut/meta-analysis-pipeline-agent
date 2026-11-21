# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
295 `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias | Alias, Mittel nur `Mittel (SD)` |
|---|---:|---:|---:|
| Zielzeile gefunden | 156 | 178 | 178 |
| Zellen geliefert | 39 | 47 | 27 |
| TP (exakt) | 14 | 20 | 8 |
| FP (exakt) | 25 | 27 | 19 |
| TP (auf ganze Zahl gerundet) | 14 | 22 | 8 |
| FP (auf ganze Zahl gerundet) | 25 | 25 | 19 |

## FP nach Feldtyp (Alias-Lauf, 27 FP)

| Feldtyp | FP |
|---|---:|
| groesse | 10 |
| mittel | 10 |
| ereignis | 7 |

## Formate der gelieferten Zellen (Alias-Lauf)

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| ereignis | mittel_sd | 0 | 1 |
| ereignis | nackt | 0 | 3 |
| ereignis | sonstig | 0 | 3 |
| groesse | groessenzeile | 8 | 10 |
| mittel | mittel_sd | 0 | 2 |
| mittel | plus_minus | 12 | 5 |
| mittel | sonstig | 0 | 3 |

## FP nach Zellformat

| Feldtyp | Zellformat | FP |
|---|---|---:|
| groesse | groessenzeile | 10 |
| mittel | plus_minus | 5 |
| mittel | sonstig | 3 |
| ereignis | nackt | 3 |
| ereignis | sonstig | 3 |
| mittel | mittel_sd | 2 |
| ereignis | mittel_sd | 1 |


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

Gelesen wird je Feldtyp: Groessen aus der Groessenzeile, Mittel und Ereignisse
als erste Zahl der Armzelle, Streuungen als Zahl in Klammern. Der Leser ist
grob und nicht validiert; die TP/FP-Zahlen messen die Zielzeilensuche, nicht
einen fertigen Extraktor.

Die 27 FP verteilen sich auf Groesse 10, Mittel 10 und Ereignis 7; Streuungen
stellen keinen Fehler. Die Zellformate zeigen den Grund:

* Mittel stehen fast immer als `26.1 +/- 1.0` (12 richtig, 5 falsch), nicht als
  `Mittel (SD)`; `sonstig` sind 3 weitere Fehler (etwa Median mit Quartilen).
* Ereignisse liefern 0 richtige und 7 falsche Zellen - der Leser greift dort
  regelmaessig den Prozentwert oder die Nachbarspalte.
* Groessen treffen 8 von 18.

Die verlangte Umstellung auf `Mittel (SD)` kostet deshalb mehr, als sie bringt:
Zellen 47 -> 27, TP 20 -> 8, FP 27 -> 19.
Alle 12 richtigen Mittel standen im Format `+/-`; die 2 FP im Format
`Mittel (SD)` bleiben auch nach der Umstellung, weil dort Zeile oder Spalte
falsch ist, nicht das Format. Trefferquote: 43 Prozent mit weiter Fassung,
30 Prozent mit strenger.
