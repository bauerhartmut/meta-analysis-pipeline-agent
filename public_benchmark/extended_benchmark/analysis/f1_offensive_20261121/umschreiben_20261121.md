# Verwirft oder ueberschreibt die Tabellenwahl richtige Zellen? (21.11.2026)

Offline, ohne Netzaufruf. `umschreiben_20261121.py`. Alle 699 Records aus `yun699.jsonl`, je Goldfeld einmal mit
ausgeschalteter (`alt`) und einmal mit eingeschalteter (`neu`)
Tabellenwahl gelesen. Ereignisfelder sind ausgenommen, weil der
Ereignisleser in beiden Staenden abgeschaltet ist.

## Klassen je Zelle

| Klasse | Zellen |
|---|---:|
| gleich | 210 |
| verworfen | 0 |
| umgeschrieben_falsch | 0 |
| umgeschrieben_richtig | 0 |
| neu_richtig | 26 |
| neu_falsch_ohne_alt | 0 |
| neu_falsch_mit_alt | 169 |
| keine | 2058 |

| Feldart | gleich | verworfen | umgeschrieben_falsch | umgeschrieben_richtig | neu_richtig | neu_falsch_ohne_alt | neu_falsch_mit_alt | keine |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| groesse | 90 | 0 | 0 | 0 | 6 | 0 | 65 | 1125 |
| mittel | 60 | 0 | 0 | 0 | 10 | 0 | 53 | 503 |
| streuung | 60 | 0 | 0 | 0 | 10 | 0 | 51 | 430 |

## Beispiele

### verworfen (0 gezeigt)

keine

### umgeschrieben_falsch (0 gezeigt)

keine

### umgeschrieben_richtig (0 gezeigt)

keine

## Abgeleitete Streuungen

14 Zellen der neuen Regel stammen aus einem 95%-KI; davon richtig 10.

| Record | Feld | Arm | Wert | Gold | richtig |
|---|---|---|---:|---:|---|
| `yun2024:446` | intervention_standard_deviation | intervention | 5.07 | 3.32 | nein |
| `yun2024:446` | comparator_standard_deviation | comparator | 6.24 | 3.54 | nein |
| `yun2024:447` | intervention_standard_deviation | intervention | 2.29 | 2.29 | ja |
| `yun2024:447` | comparator_standard_deviation | comparator | 3.84 | 3.84 | ja |
| `yun2024:448` | intervention_standard_deviation | intervention | 1.56 | 1.56 | ja |
| `yun2024:448` | comparator_standard_deviation | comparator | 2.48 | 2.48 | ja |
| `yun2024:449` | intervention_standard_deviation | intervention | 0.26 | 0.26 | ja |
| `yun2024:449` | comparator_standard_deviation | comparator | 0.33 | 0.33 | ja |
| `yun2024:450` | intervention_standard_deviation | intervention | 1.82 | 1.82 | ja |
| `yun2024:450` | comparator_standard_deviation | comparator | 2.32 | 2.32 | ja |
| `yun2024:451` | intervention_standard_deviation | intervention | 1.56 | 66.12 | nein |
| `yun2024:451` | comparator_standard_deviation | comparator | 2.48 | 66.25 | nein |
| `yun2024:452` | intervention_standard_deviation | intervention | 3.33 | 3.33 | ja |
| `yun2024:452` | comparator_standard_deviation | comparator | 3.54 | 3.54 | ja |

## P5-Vorhersagen

- richtige Vorhersagezellen von der neuen Regel bestaetigt: 30
- richtige Vorhersagezellen mit anderem Wert ueberschrieben: 31
  - davon die alte Regel ohne Wert: 0
  - davon die alte Regel mit demselben falschen Wert: 31
  - davon die alte Regel richtig, neu falsch: 0
- richtige Vorhersagezellen, zu denen die neue Regel nichts liefert: 110

| Stand | TP | FP | FN |
|---|---:|---:|---:|
| p5 | 166 | 96 | 2607 |
| p5_plus_alt | 138 | 158 | 2635 |
| p5_plus_neu | 157 | 141 | 2616 |

| Record | Feld | Arm | Vorhersage | Gold | Regel neu | abgeleitet |
|---|---|---|---:|---:|---:|---|
| `yun2024:32` | intervention_mean | intervention | 53.9 | 53.9 | 38.9 | nein |
| `yun2024:32` | intervention_standard_deviation | intervention | 22.2 | 22.2 | 8.9 | nein |
| `yun2024:32` | comparator_group_size | comparator | 199.0 | 199.0 | 36.0 | nein |
| `yun2024:32` | comparator_mean | comparator | 34.0 | 34.0 | 31.5 | nein |
| `yun2024:32` | comparator_standard_deviation | comparator | 20.1 | 20.1 | 7.4 | nein |
| `yun2024:86` | comparator_group_size | comparator | 6885.0 | 6885.0 | 5122.0 | nein |
| `yun2024:158` | intervention_group_size | intervention | 592.0 | 592.0 | 24.0 | nein |
| `yun2024:160` | intervention_group_size | intervention | 592.0 | 592.0 | 24.0 | nein |
| `yun2024:161` | intervention_group_size | intervention | 560.0 | 560.0 | 24.0 | nein |
| `yun2024:162` | intervention_group_size | intervention | 560.0 | 560.0 | 24.0 | nein |
| `yun2024:163` | intervention_group_size | intervention | 560.0 | 560.0 | 24.0 | nein |
| `yun2024:212` | intervention_mean | intervention | 9.2 | 9.2 | 5.8 | nein |
| `yun2024:212` | intervention_standard_deviation | intervention | 0.9 | 0.9 | 0.5 | nein |
| `yun2024:212` | comparator_mean | comparator | 9.6 | 9.6 | 5.9 | nein |
| `yun2024:212` | comparator_standard_deviation | comparator | 1.1 | 1.1 | 0.7 | nein |
| `yun2024:215` | intervention_mean | intervention | 2.2 | 2.2 | 5.8 | nein |
| `yun2024:215` | intervention_standard_deviation | intervention | 0.4 | 0.4 | 0.5 | nein |
| `yun2024:215` | comparator_mean | comparator | 2.0 | 2.0 | 5.9 | nein |
| `yun2024:215` | comparator_standard_deviation | comparator | 0.3 | 0.3 | 0.7 | nein |
| `yun2024:214` | intervention_mean | intervention | 2.0 | 2.0 | 5.8 | nein |
| `yun2024:214` | intervention_standard_deviation | intervention | 0.4 | 0.4 | 0.5 | nein |
| `yun2024:214` | intervention_mean | intervention | 2.0 | 2.0 | 5.8 | nein |
| `yun2024:214` | comparator_mean | comparator | 1.8 | 1.8 | 5.9 | nein |
| `yun2024:214` | comparator_standard_deviation | comparator | 0.2 | 0.2 | 0.7 | nein |
| `yun2024:232` | comparator_mean | comparator | 13.8 | 13.8 | 20.06 | nein |
| `yun2024:232` | comparator_standard_deviation | comparator | 1.14 | 1.14 | 8.04 | nein |
| `yun2024:367` | comparator_mean | comparator | 57.0 | 57.0 | 7.0 | nein |
| `yun2024:427` | intervention_mean | intervention | 17.97 | 17.97 | 16.9 | nein |
| `yun2024:427` | intervention_standard_deviation | intervention | 6.58 | 6.58 | 3.4 | nein |
| `yun2024:427` | comparator_mean | comparator | 11.28 | 11.28 | 9.23 | nein |
| `yun2024:427` | comparator_standard_deviation | comparator | 4.35 | 4.35 | 2.1 | nein |
