# Groessen-FP und Einsatz der Zellen (21.11.2026)

Offline, ohne Netzaufruf.

## Teil A: die 4 Groessen-FP

| Record | Feld | Regelwert | Gold | Klasse | Zeile Regel | Zeile Gold |
|---|---|---:|---:|---|---:|---|
| `yun2024:196` | intervention_group_size | 80.0 | 24.0 | falsche_tabelle | 47 | 1 |
| `yun2024:196` | comparator_group_size | 78.0 | 24.0 | falsche_tabelle | 47 | 1 |
| `yun2024:426` | intervention_group_size | 44.0 | 49.0 | falsche_spalte | 10 | 10, 122, 162 |
| `yun2024:426` | comparator_group_size | 49.0 | 44.0 | falsche_spalte | 10 | 10, 97 |

Klassen: {'falsche_tabelle': 2, 'falsche_spalte': 2}

## Teil B: 41 Zellen in P5 eingesetzt

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 204 | +34 |
| FP | 101 | 104 | +3 |
| FN | 2603 | 2569 | -34 |

Betroffene Records: 24 von 699.

## Teil C: nur die richtigen Zellen

Setzt man nur die 34 richtigen Zellen ein
(ohne die 7 falschen), dann:

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 204 | +34 |
| FP | 101 | 97 | -4 |
| FN | 2603 | 2569 | -34 |

Das ist die Obergrenze: 30 Zellen waren neu, 4 ersetzten
einen vorhandenen falschen Wert.
