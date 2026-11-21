# Groessen-FP und Einsatz der Zellen (21.11.2026)

Offline, ohne Netzaufruf.

## Teil A: die 10 Groessen-FP

| Record | Feld | Regelwert | Gold | Klasse | Zeile Regel | Zeile Gold |
|---|---|---:|---:|---|---:|---|
| `yun2024:193` | comparator_group_size | 140.0 | 131.0 | gold_in_anderer_tabelle_ohne_groessenzeile | 8 | - |
| `yun2024:196` | comparator_group_size | 140.0 | 24.0 | falsche_tabelle | 8 | 1 |
| `yun2024:331` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:331` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:334` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:334` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:335` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:335` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:336` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:336` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |

Klassen: {'gold_in_anderer_tabelle_ohne_groessenzeile': 1, 'falsche_tabelle': 1, 'falsche_spalte': 8}

## Teil B: 37 Zellen in P5 eingesetzt

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 190 | +20 |
| FP | 101 | 114 | +13 |
| FN | 2603 | 2583 | -20 |

Betroffene Records: 23 von 699.

## Teil C: nur die richtigen Zellen

Setzt man nur die 20 richtigen Zellen ein
(ohne die 17 falschen), dann:

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 190 | +20 |
| FP | 101 | 97 | -4 |
| FN | 2603 | 2583 | -20 |

Das ist die Obergrenze: 16 Zellen waren neu, 4 ersetzten
einen vorhandenen falschen Wert.
