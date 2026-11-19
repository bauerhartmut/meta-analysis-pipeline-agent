# Sprint 48: Arm- und Wertpruefung auf der Plan-Auswahl

Massgeblich ist die Tabelle, die `load_tables` je Record auswaehlt (dieselbe Pipeline wie `run_benchmark.py --offline`), nicht das ganze Dokument. Rein lesend: keine Netzaufrufe, keine Predictions geschrieben.

## 1. Befund

- **94 Goldzellen** sind im Plan ueber ihr Feld erreichbar (`gold_reachable`), davon 80 mit Gruppengroesse: 10 ueber die Outcome-Zeile, 70 nur ueber eine Kopfangabe.
- Von den 70 Feldtreffern ueber Kopfangaben tragen **44** den passenden Wert **und** Arm; **0** den passenden Wert, aber einen anderen Arm; **26** einen abweichenden Wert.
- Damit sind **68 von 94** Feldtreffern wert- und armgedeckt; die Zeilenzellen sind dabei nicht wertgeprueft.
- Die 0 unter "passender Wert, anderer Arm" zaehlt nur Zellen, deren Wert passt. Zusaetzlich zeigt `yun2024:678` eine Arm-Fehlbindung auf Spaltenebene: die 15 (Gold: comparator) sitzt ueber der als `intervention` gefuehrten Antibiotic-Gruppe, die 16 der Probiotic-Gruppe traegt keinen Arm.

## 2. Records mit Feldtreffer ohne passenden Wert/Arm

| Record | Tabelle(n) | Feld | Gold | Klasse | gedruckte Kandidaten |
|---|---|---|---:|---|---|
| `yun2024:172` | PMC5079604:T1 | `intervention_group_size` | 33 (intervention) | wert_abweichend | "Metformin (*n* = 17)" -> intervention (17); "Sitagliptin (*n* = 16)" -> intervention (16) |
| `yun2024:174` | PMC5079604:T1 | `intervention_group_size` | 33 (intervention) | wert_abweichend | "Metformin (*n* = 17)" -> intervention (17); "Sitagliptin (*n* = 16)" -> intervention (16) |
| `yun2024:185` | PMC5122613:T1 | `comparator_group_size` | 28 (comparator) | wert_abweichend | "Placebo (*n* = 33)" -> comparator (33) |
| `yun2024:194` | PMC5360580:T1 | `intervention_group_size` | 169 (intervention) | wert_abweichend | "Pls group (n = 145)" -> intervention (145) |
| `yun2024:194` | PMC5360580:T1 | `comparator_group_size` | 167 (comparator) | wert_abweichend | "Placebo group (n = 140)" -> comparator (140) |
| `yun2024:196` | PMC5360580:T6 | `intervention_group_size` | 24 (intervention) | wert_abweichend | "Pls group (n = 169)" -> intervention (169) |
| `yun2024:196` | PMC5360580:T6 | `comparator_group_size` | 24 (comparator) | wert_abweichend | "Placebo group (n = 167)" -> comparator (167) |
| `yun2024:265` | PMC2430617:T1 | `intervention_group_size` | 83 (intervention) | wert_abweichend | "30 µg YIC group (N = 81)" -> intervention (81); "60 µg YIC group (N = 78)" -> intervention (78) |
| `yun2024:265` | PMC2430617:T1 | `comparator_group_size` | 79 (comparator) | wert_abweichend | "Placebo group (N = 78)" -> comparator (78) |
| `yun2024:266` | PMC2430617:T1 | `intervention_group_size` | 80 (intervention) | wert_abweichend | "30 µg YIC group (N = 81)" -> intervention (81); "60 µg YIC group (N = 78)" -> intervention (78) |
| `yun2024:266` | PMC2430617:T1 | `comparator_group_size` | 79 (comparator) | wert_abweichend | "Placebo group (N = 78)" -> comparator (78) |
| `yun2024:335` | PMC5617873:T2 | `intervention_group_size` | 45 (intervention) | wert_abweichend | "Aripiprazole (n = 47)" -> intervention (47) |
| `yun2024:336` | PMC5617873:T2 | `intervention_group_size` | 45 (intervention) | wert_abweichend | "Aripiprazole (n = 47)" -> intervention (47) |
| `yun2024:426` | PMC3877023:T4 | `comparator_group_size` | 44 (comparator) | wert_abweichend | "n = 18" -> comparator (18); "n = 30" -> comparator (30) |
| `yun2024:531` | PMC4230312:T3 | `intervention_group_size` | 289 (intervention) | wert_abweichend | "Quetiapine 300 mg/day (***n*** = 298)" -> intervention (298); "Quetiapine 600 mg/day (***n*** = 307)" -> intervention (307) |
| `yun2024:531` | PMC4230312:T3 | `comparator_group_size` | 204 (comparator) | wert_abweichend | "Placebo (***n*** = 214)" -> comparator (214) |
| `yun2024:532` | PMC4230312:T1 | `intervention_group_size` | 283 (intervention) | wert_abweichend | "Quetiapine 300 mg/day ( ***n*** = 298)" -> intervention (298); "Quetiapine 600 mg/day ( ***n*** = 307)" -> intervention (307) |
| `yun2024:532` | PMC4230312:T1 | `comparator_group_size` | 204 (comparator) | wert_abweichend | "Placebo (***n*** = 214)" -> comparator (214) |
| `yun2024:645` | PMC4675066:T1 | `intervention_group_size` | 27 (intervention) | wert_abweichend | "Iodine (*n* = 29)" -> intervention (29) |
| `yun2024:645` | PMC4675066:T1 | `comparator_group_size` | 26 (comparator) | wert_abweichend | "Placebo (*n* = 30)" -> comparator (30) |
| `yun2024:647` | PMC4675066:T1 | `intervention_group_size` | 27 (intervention) | wert_abweichend | "Iodine (*n* = 29)" -> intervention (29) |
| `yun2024:647` | PMC4675066:T1 | `comparator_group_size` | 26 (comparator) | wert_abweichend | "Placebo (*n* = 30)" -> comparator (30) |
| `yun2024:678` | PMC5777419:T2 | `intervention_group_size` | 16 (intervention) | wert_abweichend | "(n=15)" -> intervention (15) |
| `yun2024:682` | PMC5777419:T2 | `intervention_group_size` | 16 (intervention) | wert_abweichend | "(n=15)" -> intervention (15) |
| `yun2024:78` | PMC3546023:T4 | `intervention_group_size` | 30 (intervention) | wert_abweichend | "**Palmvitee, n = 3**" -> intervention (3); "**Palmvitee,n = 19**" -> intervention (19); "**Palmvitee,n = 8**" -> intervention (8) |
| `yun2024:79` | PMC3546023:T4 | `intervention_group_size` | 30 (intervention) | wert_abweichend | "**Palmvitee, n = 3**" -> intervention (3); "**Palmvitee,n = 19**" -> intervention (19); "**Palmvitee,n = 8**" -> intervention (8) |

## 3. Der Fall yun2024:678

- Plan-Tabelle: `PMC5777419:T2`
- Gold `intervention_group_size` = 16 (intervention): Feld erreichbar = True, Klasse `wert_abweichend`
- Kopfangabe `(n=15)` -> intervention (Wert 15), Band ueber ['intervention']

Die Tabelle bindet `n = 15` an **intervention**, Gold verlangt 16/intervention und 15/comparator. Die 15 steht ueber der Antibiotic-Gruppe (Spalten 6-10), die der Plan als intervention fuehrt; die 16 der Probiotic-Gruppe traegt keinen Arm. Der Planwert 1 ist damit ein Feldtreffer ohne passenden Wert - und am falschen Arm; wertgeprueft bleibt 0.

## 4. Grenzen

- Zeilenzellen werden als Feldtreffer gezaehlt, aber nicht wertgeprueft; die 68 sind deshalb eine Obergrenze.
- Geprueft ist die Bindung gegen Gold und die Spaltenarme unter dem Band; eine falsche Spaltenarm-Zuordnung selbst deckt die Pruefung nicht auf.
