# Fehleranalyse Yun-Dev

Datengrundlage: 43 Records, 170 Gold-Zellen, Laeufe: stage_20261115, yun_dev_20261114, yun_dev_fresh_20261115, yun_dev_retry_20261115, yun_dev_std_20261115, yun_dev_tp_20261115, yun_dev_v3_20261115, yun_dev_v4_20261115, yun_dev_v5_20261115, yun_dev_v6_20261115, yun_dev_v6b_20261115.

## Laeufe

| Lauf | Modell | Prompt | Cache-Anteil | leer | F1 | MAE | mae_coverage | Metriken identisch |
|---|---|---|---|---|---|---|---|---|
| stage_20261115 | glm | `v2_timepoint_stage2` | 0.0 | 2/43 | 0.9112 | 0.4152 | 0.9647 | ja |
| yun_dev_20261114 | glm | `v1` | 0.209 | 2/43 | 0.708 | 3.7638 | 0.9412 | ja |
| yun_dev_20261114 | qwen30 | `v1` | 0.209 | 1/43 | 0.4789 | 5.5021 | 0.8118 | ja |
| yun_dev_fresh_20261115 | glm | `v2_timepoint` | 0.0 | 2/43 | 0.9449 | 0.4054 | 0.9882 | ja |
| yun_dev_retry_20261115 | glm | `v2_timepoint` | 1.0 | 3/43 | 0.9162 | 0.4703 | 0.9294 | ja |
| yun_dev_retry_20261115 | qwen30 | `v2_timepoint` | 1.0 | 1/43 | 0.4661 | 0.9774 | 0.7353 | ja |
| yun_dev_std_20261115 | glm | `v2_timepoint` | 0.0 | 2/43 | 0.9326 | 0.4152 | 0.9647 | ja |
| yun_dev_tp_20261115 | glm | `v2_timepoint` | 0.163 | 5/43 | 0.8758 | 0.5089 | 0.8588 | ja |
| yun_dev_tp_20261115 | qwen30 | `v2_timepoint` | 0.163 | 1/43 | 0.4661 | 0.9774 | 0.7353 | ja |
| yun_dev_v3_20261115 | glm | `v3_abs_count` | 0.0 | 3/43 | 0.9189 | 0.431 | 0.9294 | ja |
| yun_dev_v4_20261115 | glm | `v4_last_timepoint` | 0.0 | 0/43 | 0.7378 | 3.6214 | 0.9882 | ja |
| yun_dev_v5_20261115 | glm | `v5_target_timepoint` | 0.0 | 9/43 | 0.7973 | 0.0008 | 0.7 | ja |
| yun_dev_v6_20261115 | glm | `v6_target_fallback` | 0.0 | 1/43 | 0.9443 | 0.0389 | 0.9529 | ja |
| yun_dev_v6b_20261115 | glm | `v6_target_fallback` | 0.0 | 1/43 | 0.9625 | 0.0006 | 0.9882 | ja |

## Fehler je Prompt-Version

Versionen werden getrennt ausgewiesen und nicht summiert: `verworfen`
bedeutet, dass die Fassung im Dev-Lauf schlechter war als die Referenz.

| Version | Status | Fehler | technisch | inhaltlich | zusätzliche Zellen | Läufe |
|---|---|---|---|---|---|---|
| `v1` | historisch | 135 | 12 | 123 | 56 | 1 |
| `v2_timepoint` | historisch | 246 | 28 | 218 | 114 | 4 |
| `v2_timepoint_stage2` | unbekannt | 11 | 0 | 11 | 15 | 1 |
| `v3_abs_count` | verworfen | 17 | 6 | 11 | 5 | 1 |
| `v4_last_timepoint` | verworfen | 42 | 0 | 42 | 9 | 1 |
| `v5_target_timepoint` | verworfen | 52 | 32 | 20 | 7 | 1 |
| `v6_target_fallback` | referenz | 12 | 6 | 6 | 18 | 2 |

### v1 (historisch)

| Klasse | Anzahl |
|---|---|
| Nicht eindeutig klassifizierbar | 83 |
| Zahl nicht extrahiert | 30 |
| Unvollstaendige Modellantwort | 12 |
| Falscher Messzeitpunkt | 8 |
| Falsche Tabellenzeile | 2 |

| Feld | Klassen |
|---|---|
| comparator_events | Unvollstaendige Modellantwort (1), Zahl nicht extrahiert (1), Nicht eindeutig klassifizierbar (1) |
| comparator_group_size | Zahl nicht extrahiert (13), Unvollstaendige Modellantwort (3), Nicht eindeutig klassifizierbar (2) |
| comparator_mean | Nicht eindeutig klassifizierbar (20), Falscher Messzeitpunkt (2), Unvollstaendige Modellantwort (1) |
| comparator_standard_deviation | Nicht eindeutig klassifizierbar (18), Falscher Messzeitpunkt (2), Unvollstaendige Modellantwort (1) |
| intervention_events | Zahl nicht extrahiert (2), Unvollstaendige Modellantwort (1), Nicht eindeutig klassifizierbar (1) |
| intervention_group_size | Zahl nicht extrahiert (14), Unvollstaendige Modellantwort (3), Nicht eindeutig klassifizierbar (1) |
| intervention_mean | Nicht eindeutig klassifizierbar (22), Falscher Messzeitpunkt (2), Unvollstaendige Modellantwort (1) |
| intervention_standard_deviation | Nicht eindeutig klassifizierbar (18), Falsche Tabellenzeile (2), Falscher Messzeitpunkt (2), Unvollstaendige Modellantwort (1) |

### v2_timepoint (historisch)

| Klasse | Anzahl |
|---|---|
| Zahl nicht extrahiert | 106 |
| Nicht eindeutig klassifizierbar | 100 |
| Unvollstaendige Modellantwort | 28 |
| Falsche Tabellenzeile | 12 |

| Feld | Klassen |
|---|---|
| comparator_events | Nicht eindeutig klassifizierbar (6), Falsche Tabellenzeile (6), Zahl nicht extrahiert (2) |
| comparator_group_size | Zahl nicht extrahiert (44), Unvollstaendige Modellantwort (6), Nicht eindeutig klassifizierbar (2) |
| comparator_mean | Nicht eindeutig klassifizierbar (22), Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (3) |
| comparator_standard_deviation | Nicht eindeutig klassifizierbar (18), Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (3) |
| intervention_events | Nicht eindeutig klassifizierbar (8), Falsche Tabellenzeile (4), Zahl nicht extrahiert (4) |
| intervention_group_size | Zahl nicht extrahiert (44), Unvollstaendige Modellantwort (6), Nicht eindeutig klassifizierbar (2) |
| intervention_mean | Nicht eindeutig klassifizierbar (24), Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (3) |
| intervention_standard_deviation | Nicht eindeutig klassifizierbar (18), Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (3), Falsche Tabellenzeile (2) |

### v2_timepoint_stage2 (unbekannt)

| Klasse | Anzahl |
|---|---|
| Zahl nicht extrahiert | 6 |
| Nicht eindeutig klassifizierbar | 3 |
| Falsche Tabellenzeile | 2 |

| Feld | Klassen |
|---|---|
| comparator_events | Nicht eindeutig klassifizierbar (1), Falsche Tabellenzeile (1) |
| comparator_group_size | Zahl nicht extrahiert (1) |
| comparator_mean | Zahl nicht extrahiert (1) |
| comparator_standard_deviation | Zahl nicht extrahiert (1) |
| intervention_events | Nicht eindeutig klassifizierbar (1), Falsche Tabellenzeile (1) |
| intervention_group_size | Zahl nicht extrahiert (1) |
| intervention_mean | Nicht eindeutig klassifizierbar (1), Zahl nicht extrahiert (1) |
| intervention_standard_deviation | Zahl nicht extrahiert (1) |

### v3_abs_count (verworfen)

| Klasse | Anzahl |
|---|---|
| Zahl nicht extrahiert | 6 |
| Unvollstaendige Modellantwort | 6 |
| Nicht eindeutig klassifizierbar | 3 |
| Falsche Tabellenzeile | 2 |

| Feld | Klassen |
|---|---|
| comparator_events | Nicht eindeutig klassifizierbar (1), Falsche Tabellenzeile (1) |
| comparator_group_size | Zahl nicht extrahiert (1), Unvollstaendige Modellantwort (1) |
| comparator_mean | Zahl nicht extrahiert (1), Unvollstaendige Modellantwort (1) |
| comparator_standard_deviation | Zahl nicht extrahiert (1), Unvollstaendige Modellantwort (1) |
| intervention_events | Nicht eindeutig klassifizierbar (1), Falsche Tabellenzeile (1) |
| intervention_group_size | Zahl nicht extrahiert (1), Unvollstaendige Modellantwort (1) |
| intervention_mean | Nicht eindeutig klassifizierbar (1), Zahl nicht extrahiert (1), Unvollstaendige Modellantwort (1) |
| intervention_standard_deviation | Zahl nicht extrahiert (1), Unvollstaendige Modellantwort (1) |

### v4_last_timepoint (verworfen)

| Klasse | Anzahl |
|---|---|
| Nicht eindeutig klassifizierbar | 35 |
| Falscher Messzeitpunkt | 4 |
| Zahl nicht extrahiert | 2 |
| Falsche Tabellenzeile | 1 |

| Feld | Klassen |
|---|---|
| comparator_group_size | Zahl nicht extrahiert (1) |
| comparator_mean | Nicht eindeutig klassifizierbar (10), Falscher Messzeitpunkt (1) |
| comparator_standard_deviation | Nicht eindeutig klassifizierbar (8), Falscher Messzeitpunkt (1) |
| intervention_group_size | Zahl nicht extrahiert (1) |
| intervention_mean | Nicht eindeutig klassifizierbar (9), Falscher Messzeitpunkt (1) |
| intervention_standard_deviation | Nicht eindeutig klassifizierbar (8), Falsche Tabellenzeile (1), Falscher Messzeitpunkt (1) |

### v5_target_timepoint (verworfen)

| Klasse | Anzahl |
|---|---|
| Unvollstaendige Modellantwort | 32 |
| Zahl nicht extrahiert | 19 |
| Nicht eindeutig klassifizierbar | 1 |

| Feld | Klassen |
|---|---|
| comparator_group_size | Unvollstaendige Modellantwort (8), Zahl nicht extrahiert (2) |
| comparator_mean | Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (4) |
| comparator_standard_deviation | Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (4) |
| intervention_group_size | Unvollstaendige Modellantwort (8), Zahl nicht extrahiert (1) |
| intervention_mean | Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (4), Nicht eindeutig klassifizierbar (1) |
| intervention_standard_deviation | Unvollstaendige Modellantwort (4), Zahl nicht extrahiert (4) |

### v6_target_fallback (referenz)

| Klasse | Anzahl |
|---|---|
| Unvollstaendige Modellantwort | 6 |
| Zahl nicht extrahiert | 4 |
| Nicht eindeutig klassifizierbar | 2 |

| Feld | Klassen |
|---|---|
| comparator_group_size | Zahl nicht extrahiert (2), Unvollstaendige Modellantwort (1) |
| comparator_mean | Nicht eindeutig klassifizierbar (1), Unvollstaendige Modellantwort (1) |
| comparator_standard_deviation | Unvollstaendige Modellantwort (1) |
| intervention_group_size | Zahl nicht extrahiert (2), Unvollstaendige Modellantwort (1) |
| intervention_mean | Unvollstaendige Modellantwort (1), Nicht eindeutig klassifizierbar (1) |
| intervention_standard_deviation | Unvollstaendige Modellantwort (1) |

## Ereigniszahlen

| Version | Lauf | Modell | Record | Feld | Arm | Gold | Vorhersage | Fehler | Klasse |
|---|---|---|---|---|---|---|---|---|---|
| `v2_timepoint_stage2` | stage_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint_stage2` | stage_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint_stage2` | stage_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Falsche Tabellenzeile |
| `v2_timepoint_stage2` | stage_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Falsche Tabellenzeile |
| `v1` | yun_dev_20261114 | glm | yun2024:120 | intervention_events | intervention | 8.0 |  |  | Unvollstaendige Modellantwort |
| `v1` | yun_dev_20261114 | glm | yun2024:120 | comparator_events | comparator | 13.0 |  |  | Unvollstaendige Modellantwort |
| `v1` | yun_dev_20261114 | qwen30 | yun2024:120 | intervention_events | intervention | 8.0 |  |  | Zahl nicht extrahiert |
| `v1` | yun_dev_20261114 | qwen30 | yun2024:120 | comparator_events | comparator | 13.0 |  |  | Zahl nicht extrahiert |
| `v1` | yun_dev_20261114 | qwen30 | yun2024:190 | intervention_events | intervention | 52.0 | 26.0 | 26.0 | Nicht eindeutig klassifizierbar |
| `v1` | yun_dev_20261114 | qwen30 | yun2024:190 | comparator_events | comparator | 51.0 | 32.0 | 19.0 | Nicht eindeutig klassifizierbar |
| `v1` | yun_dev_20261114 | qwen30 | yun2024:263 | intervention_events | intervention | 72.0 |  |  | Zahl nicht extrahiert |
| `v2_timepoint` | yun_dev_fresh_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_fresh_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_fresh_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_fresh_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_retry_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_retry_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_retry_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_retry_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:120 | intervention_events | intervention | 8.0 | 2.0 | 6.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:120 | comparator_events | comparator | 13.0 | 8.0 | 5.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:190 | intervention_events | intervention | 52.0 | 26.0 | 26.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:190 | comparator_events | comparator | 51.0 | 32.0 | 19.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:191 | intervention_events | intervention | 49.0 |  |  | Zahl nicht extrahiert |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:191 | comparator_events | comparator | 64.0 |  |  | Zahl nicht extrahiert |
| `v2_timepoint` | yun_dev_retry_20261115 | qwen30 | yun2024:263 | intervention_events | intervention | 72.0 |  |  | Zahl nicht extrahiert |
| `v2_timepoint` | yun_dev_std_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_std_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_std_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_std_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_tp_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_tp_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_tp_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_tp_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:120 | intervention_events | intervention | 8.0 | 2.0 | 6.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:120 | comparator_events | comparator | 13.0 | 8.0 | 5.0 | Falsche Tabellenzeile |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:190 | intervention_events | intervention | 52.0 | 26.0 | 26.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:190 | comparator_events | comparator | 51.0 | 32.0 | 19.0 | Nicht eindeutig klassifizierbar |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:191 | intervention_events | intervention | 49.0 |  |  | Zahl nicht extrahiert |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:191 | comparator_events | comparator | 64.0 |  |  | Zahl nicht extrahiert |
| `v2_timepoint` | yun_dev_tp_20261115 | qwen30 | yun2024:263 | intervention_events | intervention | 72.0 |  |  | Zahl nicht extrahiert |
| `v3_abs_count` | yun_dev_v3_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| `v3_abs_count` | yun_dev_v3_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| `v3_abs_count` | yun_dev_v3_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Falsche Tabellenzeile |
| `v3_abs_count` | yun_dev_v3_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Falsche Tabellenzeile |

## Gold-Pruefung

1 von 170 Gold-Zellen haben einen Pruefhinweis.

| Record | Feld | Arm | Gold | Treffer im Text | Hinweis |
|---|---|---|---|---|---|
| yun2024:3 | intervention_mean | intervention | 50.6 | 1 | Artikel nennt 50,6 und 50,7 gm fuer denselben Wert; Gold nutzt 50,6 |

## Pruefqueue

Gesamt 741 Eintraege, getrennt nach Version:

| Datei | Status | Versionen | Eintraege | Prioritaeten |
|---|---|---|---|---|
| `human_review_queue.csv` | referenz | v6_target_fallback | 52 | {2: 10, 3: 1, 4: 1, 5: 40} |
| `human_review_discarded.csv` | verworfen | v3_abs_count, v4_last_timepoint, v5_target_timepoint | 160 | - |
| `human_review_historical.csv` | historisch | v1, v2_timepoint, v2_timepoint_stage2 | 529 | - |

Nur die Referenzdatei ist zur Pruefung vorgesehen; die uebrigen
liegen vollstaendig vor, damit nichts verloren geht.
