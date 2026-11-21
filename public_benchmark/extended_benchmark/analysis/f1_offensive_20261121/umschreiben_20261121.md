# Verwirft oder ueberschreibt die Tabellenwahl richtige Zellen? (21.11.2026)

Offline, ohne Netzaufruf. `umschreiben_20261121.py`. Alle 699 Records aus `yun699.jsonl`, je Goldfeld einmal mit
ausgeschalteter (`alt`) und einmal mit eingeschalteter (`neu`)
Tabellenwahl gelesen. Ereignisfelder sind ausgenommen, weil der
Ereignisleser in beiden Staenden abgeschaltet ist.

## Klassen je Zelle

| Klasse | Zellen |
|---|---:|
| gleich | 197 |
| verworfen | 0 |
| umgeschrieben_falsch | 0 |
| umgeschrieben_richtig | 0 |
| neu_richtig | 26 |
| neu_falsch_ohne_alt | 0 |
| neu_falsch_mit_alt | 161 |
| keine | 2079 |

| Feldart | gleich | verworfen | umgeschrieben_falsch | umgeschrieben_richtig | neu_richtig | neu_falsch_ohne_alt | neu_falsch_mit_alt | keine |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| groesse | 77 | 0 | 0 | 0 | 6 | 0 | 57 | 1146 |
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

- richtige Vorhersagezellen von der neuen Regel bestaetigt: 29
- richtige Vorhersagezellen mit anderem Wert ueberschrieben: 32
  - davon die alte Regel ohne Wert: 0
  - davon die alte Regel mit demselben falschen Wert: 32
  - davon die alte Regel richtig, neu falsch: 0
- richtige Vorhersagezellen, zu denen die neue Regel nichts liefert: 110

| Stand | TP | FP | FN | F1 | Feld schon belegt | Mittel zurueckgehalten |
|---|---:|---:|---:|---:|---:|---:|
| p5 | 166 | 96 | 2607 | 0.109 | 0 | 0 |
| p5_plus_alt | 137 | 157 | 2636 | 0.089 | 0 | 0 |
| p5_plus_neu | 156 | 140 | 2617 | 0.102 | 0 | 0 |
| p5_plus_alt_luecken | 169 | 125 | 2604 | 0.110 | 64 | 0 |
| p5_plus_neu_luecken | 178 | 118 | 2595 | 0.116 | 66 | 0 |
| p5_plus_neu_ohne_mittel | 178 | 112 | 2595 | 0.116 | 66 | 6 |
| p5_plus_neu_groesse_arm | 174 | 102 | 2599 | 0.114 | 66 | 6 |
| p5_plus_neu_groesse_zeile | 175 | 103 | 2598 | 0.115 | 66 | 6 |
| p5_plus_neu_groesse_beides | 174 | 102 | 2599 | 0.114 | 66 | 6 |

Lesart: Ersetzen kostet TP, weil 31 richtige Vorhersagezellen durch einen
falschen Regelwert ersetzt werden. `nur Luecken fuellen` laesst diese Zellen
stehen: +12 TP und +22 FP gegenueber der unveraenderten Vorhersage (F1 0.109 -> 0.116). Mit der alten Tabellenwahl waere es +3 TP / +29 FP; die neue Wahl bringt unter dieser Strategie +9 TP und -7 FP.


## Feldprioritaet der Mittel

Streuung und Groesse werden immer gefuellt. Fuer die Mittel gibt es
zwei Staende: `alle` fuellt jede Luecke, `nie` schaltet die Mittel der
Regel ganz ab. Zwei geprueffte Zwischenstufen (Mittel nur im leeren Arm,
Mittel nur im mittelfreien Record) waren zellgleich mit `alle` und sind
entfernt.

| Stand | Feldart | neu richtig | neu falsch |
|---|---|---:|---:|
| p5_plus_neu_luecken | groesse | 4 | 10 |
| p5_plus_neu_luecken | mittel | 0 | 6 |
| p5_plus_neu_luecken | streuung | 8 | 6 |
| p5_plus_neu_ohne_mittel | groesse | 4 | 10 |
| p5_plus_neu_ohne_mittel | streuung | 8 | 6 |
| p5_plus_neu_groesse_arm | streuung | 8 | 6 |
| p5_plus_neu_groesse_zeile | groesse | 1 | 1 |
| p5_plus_neu_groesse_zeile | streuung | 8 | 6 |
| p5_plus_neu_groesse_beides | streuung | 8 | 6 |

| Stand | TP gegen P5 | FP gegen P5 | F1 |
|---|---:|---:|---:|
| Mittel in jeder Luecke | +12 | +22 | 0.1160 |
| keine Mittel aus der Regel | +12 | +16 | 0.1162 |

## Groesse nur mit Beleg im Arm

Bezug ist das Lueckenfuellen ohne Mittel (178 TP / 114 FP). `arm`:
die Vorhersage hat fuer denselben Arm schon Mittel oder Streuung.
`zeile`: die Regel liest fuer denselben Arm aus derselben Zeile ein
Mittel oder eine Streuung. Die Vorhersage traegt keine Zeilenangabe,
der Zeilenteil ist deshalb nur gegen die Regel-eigene Lesung pruefbar.

| Stand | TP | FP | FN | F1 | Groessen richtig | Groessen falsch | Groessen zurueckgehalten |
|---|---:|---:|---:|---:|---:|---:|---:|
| ohne Bedingung | 178 | 112 | 2595 | 0.1162 | 4 | 10 | 0 |
| nur mit Wert im Arm | 174 | 102 | 2599 | 0.1141 | 0 | 0 | 14 |
| nur aus derselben Zeile | 175 | 103 | 2598 | 0.1147 | 1 | 1 | 12 |
| Arm und Zeile | 174 | 102 | 2599 | 0.1141 | 0 | 0 | 14 |

14 Groessenzellen fuellt die Regel neu (4 richtig, 10 falsch).

| Record | Feld | Arm | Zeile | Wert | Gold | richtig | Arm hat Wert | Zeile passt |
|---|---|---|---|---:|---:|---|---|---|
| `yun2024:159` | intervention_group_size | intervention | 1 | 24.0 | 592.0 | nein | nein | nein |
| `yun2024:251` | intervention_group_size | intervention | 60 | 406.0 | 402.0 | nein | nein | nein |
| `yun2024:251` | comparator_group_size | comparator | 60 | 393.0 | 388.0 | nein | nein | nein |
| `yun2024:252` | intervention_group_size | intervention | 10 | 398.0 | 402.0 | nein | nein | nein |
| `yun2024:252` | comparator_group_size | comparator | 10 | 389.0 | 388.0 | nein | nein | nein |
| `yun2024:356` | comparator_group_size | comparator | 6 | 15.0 | 13.0 | nein | nein | nein |
| `yun2024:420` | comparator_group_size | comparator | 1 | 20.0 | 21.0 | nein | nein | nein |
| `yun2024:421` | comparator_group_size | comparator | 1 | 20.0 | 34.0 | nein | nein | nein |
| `yun2024:446` | intervention_group_size | intervention | 111 | 104.0 | 104.0 | ja | nein | ja |
| `yun2024:446` | comparator_group_size | comparator | 111 | 114.0 | 114.0 | ja | nein | nein |
| `yun2024:451` | intervention_group_size | intervention | 117 | 104.0 | 99.0 | nein | nein | ja |
| `yun2024:451` | comparator_group_size | comparator | 117 | 114.0 | 108.0 | nein | nein | nein |
| `yun2024:678` | intervention_group_size | intervention | 8 | 16.0 | 16.0 | ja | nein | nein |
| `yun2024:678` | comparator_group_size | comparator | 8 | 15.0 | 15.0 | ja | nein | nein |

Lesart: von den 10 falschen Groessen erfuellen 0 die Arm-Bedingung und 1 die Zeilenbedingung; von den 4 richtigen sind es 0 und 1. Die Arm-Bedingung ist in keiner der 16 Zellen erfuellt (die Vorhersage hat dort in dem Arm weder Mittel noch Streuung), sie wirkt deshalb wie ein Verzicht auf Groessen. Die Zeilenbedingung laesst zwei Zellen stehen: `yun2024:446` Intervention (richtig) und `yun2024:451` Intervention (falsch).


| Record | Feld | Arm | Vorhersage | Gold | Regel neu | abgeleitet |
|---|---|---|---:|---:|---:|---|
| `yun2024:32` | intervention_mean | intervention | 53.9 | 53.9 | 38.9 | nein |
| `yun2024:32` | intervention_standard_deviation | intervention | 22.2 | 22.2 | 8.9 | nein |
| `yun2024:32` | comparator_group_size | comparator | 199.0 | 199.0 | 36.0 | nein |
| `yun2024:32` | comparator_mean | comparator | 34.0 | 34.0 | 31.5 | nein |
| `yun2024:32` | comparator_standard_deviation | comparator | 20.1 | 20.1 | 7.4 | nein |
| `yun2024:84` | comparator_group_size | comparator | 6885.0 | 6885.0 | 39.0 | nein |
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
