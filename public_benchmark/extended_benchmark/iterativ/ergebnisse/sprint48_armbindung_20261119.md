# Sprint 48: Arm- und Wertpruefung auf der Plan-Auswahl

Massgeblich ist die Tabelle, die `load_tables` je Record auswaehlt (dieselbe Pipeline wie `run_benchmark.py --offline`), nicht das ganze Dokument. Rein lesend: keine Netzaufrufe, keine Predictions geschrieben.

## 1. Befund

- **94 Goldzellen** sind im Plan ueber ihr Feld erreichbar (`gold_reachable`, Sollwert 94); davon 80 mit Gruppengroesse: 10 ueber die Outcome-Zeile, 70 nur ueber eine Kopfangabe.
- Von den 70 Feldtreffern ueber Kopfangaben tragen **44** Wert **und** Arm, **4** tragen den Wert des anderen Arms (Arm vertauscht), **22** einen anderen Wert.
- Damit sind **68 von 94** Feldtreffern nicht durch eine wertabweichende Kopfangabe widerlegt. Das ist eine **Obergrenze**: Zeilenzellen und Messwertzellen sind nicht wertgeprueft, und verifiziert ist nur der Abgleich gegen Gold, nicht die Spaltenarm-Zuordnung selbst.
- Bandpruefung aller 114 Kopfangaben der Plan-Tabellen: 110 ok, 0 gemischt, 0 falsch, 4 ohne Arm. Ein Band ueber gemischten oder fremden Armen wird als Befund ausgewiesen, aendert die Wertzaehlung aber nicht.
- Abgleich: Summe 94 = Sollwert 94 aus `structure.json`.

## 2. Records mit Feldtreffer ohne passenden Wert/Arm

| Record | Tabelle(n) | Feld | Gold | Klasse | Band | gedruckte Kandidaten |
|---|---|---|---:|---|---|---|
| `yun2024:172` | PMC5079604:T1 | `intervention_group_size` | 33 (intervention) | wert_abweichend | ok | "Metformin (*n* = 17)" -> intervention (17); "Sitagliptin (*n* = 16)" -> intervention (16) |
| `yun2024:174` | PMC5079604:T1 | `intervention_group_size` | 33 (intervention) | wert_abweichend | ok | "Metformin (*n* = 17)" -> intervention (17); "Sitagliptin (*n* = 16)" -> intervention (16) |
| `yun2024:185` | PMC5122613:T1 | `comparator_group_size` | 28 (comparator) | wert_abweichend | ok | "Placebo (*n* = 33)" -> comparator (33) |
| `yun2024:194` | PMC5360580:T1 | `intervention_group_size` | 169 (intervention) | wert_abweichend | ok | "Pls group (n = 145)" -> intervention (145) |
| `yun2024:194` | PMC5360580:T1 | `comparator_group_size` | 167 (comparator) | wert_abweichend | ok | "Placebo group (n = 140)" -> comparator (140) |
| `yun2024:196` | PMC5360580:T6 | `intervention_group_size` | 24 (intervention) | wert_abweichend | ok | "Pls group (n = 169)" -> intervention (169) |
| `yun2024:196` | PMC5360580:T6 | `comparator_group_size` | 24 (comparator) | wert_abweichend | ok | "Placebo group (n = 167)" -> comparator (167) |
| `yun2024:265` | PMC2430617:T1 | `intervention_group_size` | 83 (intervention) | wert_abweichend | ok | "30 µg YIC group (N = 81)" -> intervention (81); "60 µg YIC group (N = 78)" -> intervention (78) |
| `yun2024:265` | PMC2430617:T1 | `comparator_group_size` | 79 (comparator) | wert_abweichend | ok | "Placebo group (N = 78)" -> comparator (78) |
| `yun2024:266` | PMC2430617:T1 | `intervention_group_size` | 80 (intervention) | wert_abweichend | ok | "30 µg YIC group (N = 81)" -> intervention (81); "60 µg YIC group (N = 78)" -> intervention (78) |
| `yun2024:266` | PMC2430617:T1 | `comparator_group_size` | 79 (comparator) | wert_abweichend | ok | "Placebo group (N = 78)" -> comparator (78) |
| `yun2024:335` | PMC5617873:T2 | `intervention_group_size` | 45 (intervention) | arm_vertauscht | ok | "Aripiprazole (n = 47)" -> intervention (47) |
| `yun2024:336` | PMC5617873:T2 | `intervention_group_size` | 45 (intervention) | arm_vertauscht | ok | "Aripiprazole (n = 47)" -> intervention (47) |
| `yun2024:426` | PMC3877023:T4 | `comparator_group_size` | 44 (comparator) | wert_abweichend | ok | "n = 18" -> comparator (18); "n = 30" -> comparator (30) |
| `yun2024:531` | PMC4230312:T3 | `intervention_group_size` | 289 (intervention) | wert_abweichend | ok | "Quetiapine 300 mg/day (***n*** = 298)" -> intervention (298); "Quetiapine 600 mg/day (***n*** = 307)" -> intervention (307) |
| `yun2024:531` | PMC4230312:T3 | `comparator_group_size` | 204 (comparator) | wert_abweichend | ok | "Placebo (***n*** = 214)" -> comparator (214) |
| `yun2024:532` | PMC4230312:T1 | `intervention_group_size` | 283 (intervention) | wert_abweichend | ok | "Quetiapine 300 mg/day ( ***n*** = 298)" -> intervention (298); "Quetiapine 600 mg/day ( ***n*** = 307)" -> intervention (307) |
| `yun2024:532` | PMC4230312:T1 | `comparator_group_size` | 204 (comparator) | wert_abweichend | ok | "Placebo (***n*** = 214)" -> comparator (214) |
| `yun2024:645` | PMC4675066:T1 | `intervention_group_size` | 27 (intervention) | wert_abweichend | ok | "Iodine (*n* = 29)" -> intervention (29) |
| `yun2024:645` | PMC4675066:T1 | `comparator_group_size` | 26 (comparator) | wert_abweichend | ok | "Placebo (*n* = 30)" -> comparator (30) |
| `yun2024:647` | PMC4675066:T1 | `intervention_group_size` | 27 (intervention) | wert_abweichend | ok | "Iodine (*n* = 29)" -> intervention (29) |
| `yun2024:647` | PMC4675066:T1 | `comparator_group_size` | 26 (comparator) | wert_abweichend | ok | "Placebo (*n* = 30)" -> comparator (30) |
| `yun2024:678` | PMC5777419:T2 | `intervention_group_size` | 16 (intervention) | arm_vertauscht | ok | "(n=15)" -> intervention (15) |
| `yun2024:682` | PMC5777419:T2 | `intervention_group_size` | 16 (intervention) | arm_vertauscht | ok | "(n=15)" -> intervention (15) |
| `yun2024:78` | PMC3546023:T4 | `intervention_group_size` | 30 (intervention) | wert_abweichend | ok | "**Palmvitee, n = 3**" -> intervention (3); "**Palmvitee,n = 19**" -> intervention (19); "**Palmvitee,n = 8**" -> intervention (8) |
| `yun2024:79` | PMC3546023:T4 | `intervention_group_size` | 30 (intervention) | wert_abweichend | ok | "**Palmvitee, n = 3**" -> intervention (3); "**Palmvitee,n = 19**" -> intervention (19); "**Palmvitee,n = 8**" -> intervention (8) |

## 3. Der Fall yun2024:678

- Plan-Tabelle: `PMC5777419:T2`
- Gold `intervention_group_size` = 16 (intervention): Klasse `arm_vertauscht`, Band `ok`
- Kopfangabe `(n=15)` -> intervention (Wert 15), Band ueber ['intervention'] (ok)

Die Tabelle bindet `n = 15` an **intervention**, Gold verlangt 16/intervention und 15/comparator. Die 15 steht ueber der Antibiotic-Gruppe (Spalten 6-10), die der Plan als intervention fuehrt; die 16 der Probiotic-Gruppe traegt keinen Arm. Der Planwert 1 ist damit ein Feldtreffer ohne passenden Wert - und am falschen Arm; wertgeprueft bleibt 0.

## 4. Grenzen

- Zeilenzellen und Messwerte werden als Feldtreffer gezaehlt, aber nicht wertgeprueft; die Zahl der nicht widerlegten Feldtreffer ist deshalb eine Obergrenze.
- Die Bandpruefung nutzt die Spaltenarme des Plans. Eine bereits dort falsche Zuordnung (426) erkennt sie nicht; sie findet nur Baender, die ueber gemischten oder fremden Armen sitzen.
- `arm_vertauscht` prueft, ob eine Kopfangabe den Goldwert des anderen Arms traegt; sie erkennt keine Vertauschung, deren Wert in der Tabelle gar nicht vorkommt.
