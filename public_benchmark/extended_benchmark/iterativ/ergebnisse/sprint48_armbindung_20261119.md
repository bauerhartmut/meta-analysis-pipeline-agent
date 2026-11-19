# Sprint 48: Arm- und Wertpruefung der neu gezaehlten Kopfangaben

Stichprobe: alle **23** Records, deren `gold_reachable` sich durch die Neuerzeugung geaendert hat (Vergleich gegen `911e593^`). Rein lesend: keine Netzaufrufe, keine Predictions geschrieben.

## 1. Befund

- **38 Goldzellen** sind neu ueber Kopfangaben erreichbar; 30 davon mit **passendem Wert und Arm**, 0 mit passendem Wert aber falschem Arm.
- **8 Zellen** werden nur deshalb gezaehlt, weil das *Feld* von einer Kopfangabe belegt ist - der gedruckte Wert weicht vom Goldwert ab (Untergruppen statt Gesamtgruppe).
- Bandpruefung: 43 tragende Angaben sitzen ueber Spalten desselben Arms, 0 ueber Spalten eines anderen Arms, 6 ueber Spalten ohne Arm.

## 2. Je Record

| Record | alt -> neu | neu ueber Kopf | Wert+Arm | Wert ok, Arm falsch | Wert abweichend |
|---|---:|---:|---:|---:|---:|
| `yun2024:665` | 0 -> 6 | 0 | 0 | 0 | 0 |
| `yun2024:390` | 1 -> 6 | 2 | 2 | 0 | 0 |
| `yun2024:421` | 0 -> 3 | 2 | 1 | 0 | 1 |
| `yun2024:172` | 0 -> 2 | 2 | 1 | 0 | 1 |
| `yun2024:174` | 0 -> 2 | 2 | 1 | 0 | 1 |
| `yun2024:350` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:352` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:402` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:403` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:486` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:489` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:531` | 0 -> 2 | 2 | 0 | 0 | 2 |
| `yun2024:532` | 0 -> 2 | 2 | 0 | 0 | 2 |
| `yun2024:639` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:640` | 0 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:645` | 0 -> 2 | 0 | 0 | 0 | 0 |
| `yun2024:647` | 0 -> 2 | 0 | 0 | 0 | 0 |
| `yun2024:184` | 0 -> 1 | 1 | 1 | 0 | 0 |
| `yun2024:185` | 0 -> 1 | 1 | 0 | 0 | 1 |
| `yun2024:391` | 1 -> 2 | 2 | 2 | 0 | 0 |
| `yun2024:426` | 0 -> 1 | 2 | 2 | 0 | 0 |
| `yun2024:678` | 0 -> 1 | 2 | 2 | 0 | 0 |
| `yun2024:682` | 0 -> 1 | 2 | 2 | 0 | 0 |

## 3. Beispiele

- `yun2024:390` intervention_group_size=27: wert_und_arm_stimmig - PMC3278655:T1: "(n = 27)" -> intervention (Band ueber ['intervention']); PMC3278655:T2: "(n=30)" -> intervention (Band ueber ['intervention'])
- `yun2024:390` comparator_group_size=18: wert_und_arm_stimmig - PMC3278655:T1: "(n = 18)" -> comparator (Band ueber ['comparator']); PMC3278655:T2: "(n=24)" -> comparator (Band ueber ['comparator'])
- `yun2024:421` intervention_group_size=30: wert_und_arm_stimmig - PMC3877023:T1: "Short-Bore MR (n = 44)" -> intervention (Band ueber ['intervention']); PMC3877023:T3: "n = 18" -> intervention (Band ueber ['intervention'])
- `yun2024:421` comparator_group_size=34: feld_belegt_wert_abweichend - PMC3877023:T1: "Open MR (n = 49)" -> comparator (Band ueber ['comparator'])
- `yun2024:172` intervention_group_size=33: feld_belegt_wert_abweichend - PMC5079604:T1: "Metformin (*n* = 17)" -> intervention (Band ueber ['intervention']); PMC5079604:T1: "Sitagliptin (*n* = 16)" -> intervention (Band ueber ['intervention'])
- `yun2024:172` comparator_group_size=15: wert_und_arm_stimmig - PMC5079604:T1: "Placebo (*n* = 15)" -> comparator (Band ueber ['comparator'])
- `yun2024:174` intervention_group_size=33: feld_belegt_wert_abweichend - PMC5079604:T1: "Metformin (*n* = 17)" -> intervention (Band ueber ['intervention']); PMC5079604:T1: "Sitagliptin (*n* = 16)" -> intervention (Band ueber ['intervention'])
- `yun2024:174` comparator_group_size=15: wert_und_arm_stimmig - PMC5079604:T1: "Placebo (*n* = 15)" -> comparator (Band ueber ['comparator'])
- `yun2024:350` intervention_group_size=9: wert_und_arm_stimmig - PMC5874317:T1: "**Bilateral ( *n* = 9)**" -> intervention (Band ueber ['intervention'])
- `yun2024:350` comparator_group_size=9: wert_und_arm_stimmig - PMC5874317:T1: "**Unilateral ( *n* = 9)**" -> comparator (Band ueber ['comparator'])
- `yun2024:352` intervention_group_size=9: wert_und_arm_stimmig - PMC5874317:T1: "**Bilateral ( *n* = 9)**" -> intervention (Band ueber ['intervention'])
- `yun2024:352` comparator_group_size=9: wert_und_arm_stimmig - PMC5874317:T1: "**Unilateral ( *n* = 9)**" -> comparator (Band ueber ['comparator'])
- `yun2024:402` intervention_group_size=20: wert_und_arm_stimmig - PMC5781260:T1: "(*N* = 20 59% men, 41% women)" -> intervention (Band ueber ['intervention'])
- `yun2024:402` comparator_group_size=20: wert_und_arm_stimmig - PMC5781260:T1: "(*N* = 20 40% men, 60% women)" -> comparator (Band ueber ['comparator'])
- `yun2024:403` intervention_group_size=20: wert_und_arm_stimmig - PMC5781260:T1: "(*N* = 20 59% men, 41% women)" -> intervention (Band ueber ['intervention'])
- `yun2024:403` comparator_group_size=20: wert_und_arm_stimmig - PMC5781260:T1: "(*N* = 20 40% men, 60% women)" -> comparator (Band ueber ['comparator'])
- `yun2024:486` intervention_group_size=44: wert_und_arm_stimmig - PMC3786549:T3: "(*n* = 44)" -> intervention (Band ueber ['intervention']); PMC3786549:T3: "(*n* = 44)" -> intervention (Band ueber ['intervention'])
- `yun2024:486` comparator_group_size=44: wert_und_arm_stimmig - PMC3786549:T3: "(*n* = 44)" -> comparator (Band ueber ['comparator']); PMC3786549:T3: "(*n* = 44)" -> comparator (Band ueber ['comparator'])
- `yun2024:489` intervention_group_size=44: wert_und_arm_stimmig - PMC3786549:T3: "(*n* = 44)" -> intervention (Band ueber ['intervention']); PMC3786549:T3: "(*n* = 44)" -> intervention (Band ueber ['intervention'])
- `yun2024:489` comparator_group_size=44: wert_und_arm_stimmig - PMC3786549:T3: "(*n* = 44)" -> comparator (Band ueber ['comparator']); PMC3786549:T3: "(*n* = 44)" -> comparator (Band ueber ['comparator'])
- `yun2024:531` intervention_group_size=289: feld_belegt_wert_abweichend - PMC4230312:T1: "Quetiapine 300 mg/day ( ***n*** = 298)" -> intervention (Band ueber ['intervention']); PMC4230312:T1: "Quetiapine 600 mg/day ( ***n*** = 307)" -> intervention (Band ueber ['intervention'])
- `yun2024:531` comparator_group_size=204: feld_belegt_wert_abweichend - PMC4230312:T1: "Placebo (***n*** = 214)" -> comparator (Band ueber ['comparator']); PMC4230312:T3: "Placebo (***n*** = 214)" -> comparator (Band ueber ['comparator'])
- `yun2024:532` intervention_group_size=283: feld_belegt_wert_abweichend - PMC4230312:T1: "Quetiapine 300 mg/day ( ***n*** = 298)" -> intervention (Band ueber ['intervention']); PMC4230312:T1: "Quetiapine 600 mg/day ( ***n*** = 307)" -> intervention (Band ueber ['intervention'])
- `yun2024:532` comparator_group_size=204: feld_belegt_wert_abweichend - PMC4230312:T1: "Placebo (***n*** = 214)" -> comparator (Band ueber ['comparator']); PMC4230312:T3: "Placebo (***n*** = 214)" -> comparator (Band ueber ['comparator'])
- `yun2024:639` intervention_group_size=12: wert_und_arm_stimmig - PMC4511433:T1: "Elobixibat 2.5 mg (*N* = 12)" -> intervention (Band ueber ohne Arm); PMC4511433:T2: "A3309 - 2.5 mg (*N* = 12)" -> intervention (Band ueber ['intervention'])
- `yun2024:639` comparator_group_size=12: wert_und_arm_stimmig - PMC4511433:T1: "Placebo (*N* = 12)" -> comparator (Band ueber ohne Arm); PMC4511433:T2: "Placebo (*N* = 12)" -> comparator (Band ueber ohne Arm)
- `yun2024:640` intervention_group_size=12: wert_und_arm_stimmig - PMC4511433:T1: "Elobixibat 2.5 mg (*N* = 12)" -> intervention (Band ueber ohne Arm); PMC4511433:T2: "A3309 - 2.5 mg (*N* = 12)" -> intervention (Band ueber ['intervention'])
- `yun2024:640` comparator_group_size=12: wert_und_arm_stimmig - PMC4511433:T1: "Placebo (*N* = 12)" -> comparator (Band ueber ohne Arm); PMC4511433:T2: "Placebo (*N* = 12)" -> comparator (Band ueber ohne Arm)
- `yun2024:184` comparator_group_size=33: wert_und_arm_stimmig - PMC5122613:T1: "Placebo (*n* = 33)" -> comparator (Band ueber ['comparator'])
- `yun2024:185` comparator_group_size=28: feld_belegt_wert_abweichend - PMC5122613:T1: "Placebo (*n* = 33)" -> comparator (Band ueber ['comparator'])
- `yun2024:391` intervention_group_size=27: wert_und_arm_stimmig - PMC3278655:T1: "(n = 27)" -> intervention (Band ueber ['intervention']); PMC3278655:T2: "(n=30)" -> intervention (Band ueber ['intervention'])
- `yun2024:391` comparator_group_size=18: wert_und_arm_stimmig - PMC3278655:T1: "(n = 18)" -> comparator (Band ueber ['comparator']); PMC3278655:T2: "(n=24)" -> comparator (Band ueber ['comparator'])
- `yun2024:426` intervention_group_size=49: wert_und_arm_stimmig - PMC3877023:T1: "Open MR (n = 49)" -> intervention (Band ueber ['intervention'])
- `yun2024:426` comparator_group_size=44: wert_und_arm_stimmig - PMC3877023:T1: "Short-Bore MR (n = 44)" -> comparator (Band ueber ['comparator']); PMC3877023:T3: "n = 18" -> comparator (Band ueber ['comparator'])
- `yun2024:678` intervention_group_size=16: wert_und_arm_stimmig - PMC5777419:T1: "Antibiotic group (n=16)" -> intervention (Band ueber ['intervention']); PMC5777419:T2: "(n=15)" -> intervention (Band ueber ['intervention'])
- `yun2024:678` comparator_group_size=15: wert_und_arm_stimmig - PMC5777419:T1: "Placebo group (n=15)" -> comparator (Band ueber ['comparator']); PMC5777419:T3: "Placebo group (n=15)" -> comparator (Band ueber ['comparator'])
- `yun2024:682` intervention_group_size=16: wert_und_arm_stimmig - PMC5777419:T1: "Antibiotic group (n=16)" -> intervention (Band ueber ['intervention']); PMC5777419:T2: "(n=15)" -> intervention (Band ueber ['intervention'])
- `yun2024:682` comparator_group_size=15: wert_und_arm_stimmig - PMC5777419:T1: "Placebo group (n=15)" -> comparator (Band ueber ['comparator']); PMC5777419:T3: "Placebo group (n=15)" -> comparator (Band ueber ['comparator'])

## 4. Grenzen

- Geprueft ist die Bindung des Parsers gegen die Spaltenarme unter dem Band; eine falsche Spaltenarm-Zuordnung selbst wird nicht aufgedeckt.
- `gold_reachable` zaehlt Felder, nicht Werte. Die Zaehlung kann daher Felder als erreichbar fuehren, obwohl der gedruckte Wert ein anderer ist.
