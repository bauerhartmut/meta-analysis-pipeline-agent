# Ereigniszaehler deterministisch lesbar? (21.11.2026)

Offline, ohne Netzaufruf. Grundgesamtheit: die 29 `events`-Faelle
ohne Groessenzeile. Geprueft wird, ob der Goldwert als `N (x%)` in einer
Tabellenzeile steht und die Spalte ueber eine Kopfzeile einem Arm zuzuordnen
ist.

## Verteilung

| Klasse | Faelle |
|---|---:|
| Zaehler mit Prozentzeichen, richtiger Arm | 0 |
| Zaehler mit Prozent ohne Zeichen, richtiger Arm | 0 |
| Zaehler unter (%)-Kopfzeile, richtiger Arm | 4 |
| Zaehler im anderen Arm | 1 |
| Zaehler, Arm unklar | 14 |
| Wert ohne Prozentanteil | 10 |
| Wert nicht im Dokument | 0 |

## Faelle

| Record | Feld | Arm | Wert | Klasse | Spaltenarm | Zeile |
|---|---|---|---|---:|---|---:|
| `yun2024:127` | intervention_events | intervention | 11.0 | zaehler_arm_unklar | - | 11 |
| `yun2024:127` | comparator_events | comparator | 21.0 | zaehler_arm_unklar | - | 8 |
| `yun2024:130` | intervention_events | intervention | 11.0 | zaehler_arm_unklar | - | 11 |
| `yun2024:14` | comparator_events | comparator | 54.0 | zaehler_arm_unklar | - | 159 |
| `yun2024:153` | comparator_events | comparator | 7.0 | zaehler_arm_unklar | - | 11 |
| `yun2024:190` | intervention_events | intervention | 52.0 | zaehler_prozent_in_kopfzeile | intervention | 74 |
| `yun2024:190` | comparator_events | comparator | 51.0 | zaehler_anderer_arm | intervention | 74 |
| `yun2024:305` | intervention_events | intervention | 1.0 | wert_ohne_prozent | - | - |
| `yun2024:313` | intervention_events | intervention | 22.0 | zaehler_arm_unklar | - | 8 |
| `yun2024:313` | comparator_events | comparator | 16.0 | wert_ohne_prozent | - | - |
| `yun2024:369` | intervention_events | intervention | 51.0 | zaehler_arm_unklar | - | 22 |
| `yun2024:369` | comparator_events | comparator | 57.0 | zaehler_arm_unklar | - | 29 |
| `yun2024:370` | comparator_events | comparator | 33.0 | zaehler_prozent_in_kopfzeile | comparator | 13 |
| `yun2024:373` | comparator_events | comparator | 46.0 | zaehler_prozent_in_kopfzeile | comparator | 44 |
| `yun2024:379` | intervention_events | intervention | 25.0 | zaehler_arm_unklar | - | 28 |
| `yun2024:379` | comparator_events | comparator | 39.0 | zaehler_prozent_in_kopfzeile | comparator | 15 |
| `yun2024:380` | intervention_events | intervention | 47.0 | zaehler_arm_unklar | - | 21 |
| `yun2024:380` | comparator_events | comparator | 19.0 | zaehler_arm_unklar | - | 28 |
| `yun2024:499` | intervention_events | intervention | 27.0 | zaehler_arm_unklar | - | 35 |
| `yun2024:500` | intervention_events | intervention | 12.0 | zaehler_arm_unklar | - | 49 |
| `yun2024:501` | comparator_events | comparator | 15.0 | zaehler_arm_unklar | - | 46 |
| `yun2024:62` | intervention_events | intervention | 23.0 | wert_ohne_prozent | - | - |
| `yun2024:626` | intervention_events | intervention | 2.0 | wert_ohne_prozent | - | - |
| `yun2024:626` | comparator_events | comparator | 3.0 | wert_ohne_prozent | - | - |
| `yun2024:63` | intervention_events | intervention | 23.0 | wert_ohne_prozent | - | - |
| `yun2024:63` | comparator_events | comparator | 5.0 | wert_ohne_prozent | - | - |
| `yun2024:64` | comparator_events | comparator | 4.0 | wert_ohne_prozent | - | - |
| `yun2024:65` | comparator_events | comparator | 3.0 | wert_ohne_prozent | - | - |
| `yun2024:66` | comparator_events | comparator | 4.0 | wert_ohne_prozent | - | - |

## Antwort

Deterministisch lesbar sind 4 der 29 Faelle,
alle ueber eine Kopfzeile mit Prozentangabe und den Arm in der
Zeilenbeschriftung. In 1 Fall landet der
Zaehler in der falschen Zeile, in 14 ist der Arm
nicht bestimmbar, in 10 fehlt der Prozentbezug.
Ein Zaehler im Format `11 (12%)` mit Prozentzeichen trat in keinem Fall auf;
die Tabellen schreiben `52 (39.1)` ohne Zeichen oder stellen `No. patients (%)`
ueber nackte Zahlen.

## Lesart

`zaehler_richtiger_arm` ist die einzige Klasse, aus der eine Regel ohne Raten
einen Wert ziehen koennte. `zaehler_anderer_arm` waere ein Widerspruch zur
Goldbeschriftung, `zaehler_arm_unklar` fehlt die Kopfzeile. `wert_ohne_prozent`
bedeutet, dass die Zahl im Text steht, aber nicht als Zaehler mit Anteil.
