# qwen30 gegen glm auf Yun-699 (Lesekopie)

Quelle: `runs/_lesekopie_20261118/predictions.jsonl` (Lesekopie der laufenden Datei), Gold: `records/yun699.jsonl`. Beide Modelle mit 699 Records, 2773 Goldzellen. Alle Zahlen aus `qwen30_lesekopie.json`, `glm_lesekopie.json` und `vergleich.json` in diesem Ordner.

## Gesamtkennzahlen

| Kennzahl | qwen30 | glm | Differenz |
|---|---:|---:|---:|
| richtig | 1026 | 1840 | -814 |
| falsch | 348 | 281 | +67 |
| fehlend | 1399 | 652 | +747 |
| Zellen ohne Gold | 542 | 115 | +427 |
| Precision | 0.7467 | 0.8675 | -0.1208 |
| Recall | 0.3700 | 0.6635 | -0.2935 |
| F1 | 0.4948 | 0.7519 | -0.2571 |
| MAE | 21.5365 | 5.0573 | +16.4792 |
| Records exakt (strict) | 62 | 346 | -284 |
| technische Ausfaelle | 0 | 104 | -104 |
| leere Antworten | 57 | 36 | +21 |
| Tokens | 75671 | 1934079 | -1858408 |

Bezugsgroesse Precision: 1374 bewertbare Meldungen von qwen30, 2121 von glm.

## Woher die fehlenden Zellen kommen

| Ursache | Zellen |
|---|---:|
| leere Antwort (57 Records) | 168 |
| geantwortet, Feld nicht gemeldet | 1231 |
| Summe | 1399 |

Zellstatus von qwen30, getrennt nach Gruppenfeldern (N je Arm):

| Feldgruppe | richtig | falsch | fehlend |
|---|---:|---:|---:|
| Gruppengroesse | 190 | 30 | 1066 |
| Mittelwerte, SD, Events | 836 | 318 | 333 |

Einstellung `group_size_mode` je Modell: qwen30: {'aus': 699}, glm: {'aus': 699}

## Feldebene

| Feld | qwen30 richtig | qwen30 falsch | qwen30 fehlend | glm richtig | glm fehlend |
|---|---:|---:|---:|---:|---:|
| comparator_events | 86 | 32 | 40 | 92 | 38 |
| comparator_group_size | 100 | 15 | 528 | 456 | 154 |
| comparator_mean | 195 | 77 | 38 | 194 | 64 |
| comparator_standard_deviation | 129 | 56 | 90 | 160 | 80 |
| intervention_events | 78 | 28 | 46 | 94 | 31 |
| intervention_group_size | 90 | 15 | 538 | 465 | 146 |
| intervention_mean | 212 | 73 | 31 | 208 | 64 |
| intervention_standard_deviation | 136 | 52 | 88 | 171 | 75 |

## Nach Outcome-Typ

| Typ | qwen30 richtig | qwen30 fehlend | glm richtig | glm fehlend |
|---|---:|---:|---:|---:|
| binary | 312 | 249 | 449 | 127 |
| continuous | 714 | 1150 | 1391 | 525 |

## Record-Ebene

| Lage | Records |
|---|---:|
| beide vollstaendig exakt | 58 |
| nur qwen30 vollstaendig exakt | 15 |
| nur glm vollstaendig exakt | 310 |
| keiner vollstaendig exakt | 316 |

Records, in denen nur qwen30 mindestens eine richtige Zelle hat: 54. Records, in denen nur glm mindestens eine richtige Zelle hat: 212.

Leere Antworten: qwen30 57, glm 36, in beiden leer: 11.

## Kosten je richtiger Zelle

| Modell | Tokens | richtige Zellen | Tokens je richtige Zelle |
|---|---:|---:|---:|
| qwen30 | 75671 | 1026 | 73.8 |
| glm | 1934079 | 1840 | 1051.1 |

Faktor: glm kostet je richtiger Zelle das 14.3-fache von qwen30.
