# Groessenzeile der Zielzeile (21.11.2026)

Offline, ohne Netzaufruf. Die Regel nutzt keinen Goldwert: sie sucht die
Zielzeile ueber den Outcome-Namen, nimmt die naechste Groessenzeile darueber und
liest dort die Spalte des Arms. Mehrdeutige Spalten (Multiarm mit gleichem
Armnamen) werden verweigert.

## Ergebnis an den 31 Zielfaellen

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | 31 |
| Regel liefert einen Wert | 6 |
| davon richtig (TP) | 2 |
| davon falsch (FP) | 4 |

| Record | Feld | Regelwert | Quelle | Zeile | Gold | Vorhersage | richtig |
|---|---|---:|---|---:|---:|---:|---|
| `yun2024:331` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | None | nein |
| `yun2024:334` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | None | nein |
| `yun2024:335` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | None | nein |
| `yun2024:336` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | None | nein |
| `yun2024:346` | comparator_group_size | 22.0 | zeile | 33 | 22.0 | None | ja |
| `yun2024:347` | comparator_group_size | 22.0 | zeile | 33 | 22.0 | 5.0 | ja |

## Abbruchgruende

| Stufe | Faelle |
|---|---:|
| geliefert | 6 |
| Zielzeile nicht ueber Outcome gefunden | 13 |
| Groessenzeile nicht in Reichweite | 4 |
| Arm nicht eindeutig zugeordnet | 4 |
| Tabelle gelesen, aber nur der andere Arm | 4 |

## Variante ohne Zielzeilen-Anker

Dieselbe Regel ohne Outcome-Anker - alle Groessenzeilen im Dokument, geliefert
nur bei einem einzigen Wert je Arm:

| Kennzahl | Wert |
|---|---:|
| geliefert | 10 |
| TP | 2 |
| FP | 8 |

Die ankerlose Variante liefert Werte, obwohl jedes Dokument mehrere
Groessenzeilen mit verschiedenen Werten enthaelt (Subgruppen, mehrere
Tabellen). Sie trifft zwei Faelle und erzeugt acht FP; die verankerte Variante
ist mit 2 TP und 4 FP besser, weil sie nur die Groessenzeile ueber der
Zielzeile liest.

## Bilanz ueber alle 24 gelieferten Zellen (`ersetzen`)

| Kennzahl | Wert |
|---|---:|
| TP (ersetzt falschen Wert durch Gold) | 2 |
| FP (bleibt falsch) | 13 |
| TP-Verlust (ersetzt richtigen Wert durch falschen) | 0 |

Zusaetzlich liefert die Regel 18 Zellen ausserhalb der 31 Zielfaelle.

## Lesart

Ein Treffer verlangt drei Dinge zugleich: die Zielzeile muss ueber den
Outcome-Namen auffindbar sein, die Groessenzeile muss in Reichweite liegen, und
die Armspalte muss eindeutig sein. Die 31 Zielfaelle erfuellen laut
`zaehlfelder_20261121` die dritte Bedingung; die ersten beiden prueft diese
Regel.
