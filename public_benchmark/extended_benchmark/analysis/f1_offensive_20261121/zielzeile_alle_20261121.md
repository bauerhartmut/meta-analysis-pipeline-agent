# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
295 `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias |
|---|---:|---:|
| Zielzeile gefunden | 156 | 178 |
| Zellen geliefert | 39 | 47 |
| TP (exakt) | 14 | 20 |
| FP (exakt) | 25 | 27 |
| TP (auf ganze Zahl gerundet) | 14 | 22 |
| FP (auf ganze Zahl gerundet) | 25 | 25 |

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
