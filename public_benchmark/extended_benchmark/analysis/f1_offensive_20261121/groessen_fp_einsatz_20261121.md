# Groessen-FP und Einsatz der Zellen (21.11.2026)

Offline, ohne Netzaufruf.

## Teil A: die 2 Groessen-FP

| Record | Feld | Regelwert | Gold | Klasse | Zeile Regel | Zeile Gold |
|---|---|---:|---:|---|---:|---|
| `yun2024:196` | intervention_group_size | 80.0 | 24.0 | falsche_tabelle | 47 | 1 |
| `yun2024:196` | comparator_group_size | 78.0 | 24.0 | falsche_tabelle | 47 | 1 |

Klassen: {'falsche_tabelle': 2}

## Teil B: 33 Zellen in P5 eingesetzt

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 200 | +30 |
| FP | 101 | 100 | -1 |
| FN | 2603 | 2573 | -30 |

Betroffene Records: 19 von 699.

## Teil C: nur die richtigen Zellen

Setzt man nur die 30 richtigen Zellen ein
(ohne die 3 falschen), dann:

| Kennzahl | vorher | nachher | Delta |
|---|---:|---:|---:|
| TP | 170 | 200 | +30 |
| FP | 101 | 97 | -4 |
| FN | 2603 | 2573 | -30 |

Das ist die Obergrenze: 26 Zellen waren neu, 4 ersetzten
einen vorhandenen falschen Wert.
