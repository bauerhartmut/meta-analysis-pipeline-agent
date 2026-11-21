# Groessen-FP und Einsatz der Zellen (21.11.2026)

Offline, ohne Netzaufruf.

## Teil A: die 10 Groessen-FP

| Record | Feld | Regelwert | Gold | Klasse | Zeile Regel | Zeile Gold |
|---|---|---:|---:|---|---:|---|
| `yun2024:196` | intervention_group_size | 80.0 | 24.0 | falsche_tabelle | 47 | 1 |
| `yun2024:196` | comparator_group_size | 78.0 | 24.0 | falsche_tabelle | 47 | 1 |
| `yun2024:331` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:331` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:334` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:334` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:335` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:335` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:336` | intervention_group_size | 47.0 | 45.0 | falsche_spalte | 40 | 1, 6, 34 |
| `yun2024:336` | comparator_group_size | 45.0 | 47.0 | falsche_spalte | 40 | 1, 6, 34 |

Klassen: {'falsche_tabelle': 2, 'falsche_spalte': 8}

## Teil B: 41 Zellen in P5 eingesetzt

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 194 | +24 |
| FP | 101 | 114 | +13 |
| FN | 2603 | 2579 | -24 |

Betroffene Records: 24 von 699.

## Teil C: nur die richtigen Zellen

Setzt man nur die 24 richtigen Zellen ein
(ohne die 17 falschen), dann:

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 194 | +24 |
| FP | 101 | 97 | -4 |
| FN | 2603 | 2579 | -24 |

Das ist die Obergrenze: 20 Zellen waren neu, 4 ersetzten
einen vorhandenen falschen Wert.
