# Fehleranalyse Yun-Dev

Datengrundlage: 43 Records, 170 Gold-Zellen, Laeufe: yun_dev_20261114, yun_dev_fresh_20261115, yun_dev_retry_20261115, yun_dev_tp_20261115, yun_dev_v3_20261115.

## Laeufe

| Lauf | Modell | Prompt | Cache-Anteil | leer | F1 | MAE | mae_coverage | Metriken identisch |
|---|---|---|---|---|---|---|---|---|
| yun_dev_20261114 | glm | `v1` | 0.209 | 2/43 | 0.708 | 3.7638 | 0.9412 | ja |
| yun_dev_20261114 | qwen30 | `v1` | 0.209 | 1/43 | 0.4789 | 5.5021 | 0.8118 | ja |
| yun_dev_fresh_20261115 | glm | `v2_timepoint` | 0.0 | 2/43 | 0.9449 | 0.4054 | 0.9882 | ja |
| yun_dev_retry_20261115 | glm | `v2_timepoint` | 1.0 | 3/43 | 0.9162 | 0.4703 | 0.9294 | ja |
| yun_dev_retry_20261115 | qwen30 | `v2_timepoint` | 1.0 | 1/43 | 0.4661 | 0.9774 | 0.7353 | ja |
| yun_dev_tp_20261115 | glm | `v2_timepoint` | 0.163 | 5/43 | 0.8758 | 0.5089 | 0.8588 | ja |
| yun_dev_tp_20261115 | qwen30 | `v2_timepoint` | 0.163 | 1/43 | 0.4661 | 0.9774 | 0.7353 | ja |
| yun_dev_v3_20261115 | glm | `v3_abs_count` | 0.0 | 3/43 | 0.9189 | 0.431 | 0.9294 | ja |

## Fehler nach Klasse

| Klasse | Anzahl |
|---|---|
| Nicht eindeutig klassifizierbar | 187 |
| Zahl nicht extrahiert | 136 |
| Unvollstaendige Modellantwort | 46 |
| Falscher Messzeitpunkt | 8 |
| Falsche Tabellenzeile | 6 |
| Prozentwert und absolute Zahl verwechselt | 4 |

## Fehler nach Feld

| Feld | Klassen |
|---|---|
| comparator_events | Nicht eindeutig klassifizierbar (7), Prozentwert und absolute Zahl verwechselt (4), Zahl nicht extrahiert (3), Falsche Tabellenzeile (2), Unvollstaendige Modellantwort (1) |
| comparator_group_size | Zahl nicht extrahiert (57), Unvollstaendige Modellantwort (10), Nicht eindeutig klassifizierbar (4) |
| comparator_mean | Nicht eindeutig klassifizierbar (42), Unvollstaendige Modellantwort (6), Zahl nicht extrahiert (3), Falscher Messzeitpunkt (2) |
| comparator_standard_deviation | Nicht eindeutig klassifizierbar (36), Unvollstaendige Modellantwort (6), Zahl nicht extrahiert (3), Falscher Messzeitpunkt (2) |
| intervention_events | Nicht eindeutig klassifizierbar (13), Zahl nicht extrahiert (6), Unvollstaendige Modellantwort (1) |
| intervention_group_size | Zahl nicht extrahiert (58), Unvollstaendige Modellantwort (10), Nicht eindeutig klassifizierbar (3) |
| intervention_mean | Nicht eindeutig klassifizierbar (46), Unvollstaendige Modellantwort (6), Zahl nicht extrahiert (3), Falscher Messzeitpunkt (2) |
| intervention_standard_deviation | Nicht eindeutig klassifizierbar (36), Unvollstaendige Modellantwort (6), Falsche Tabellenzeile (4), Zahl nicht extrahiert (3), Falscher Messzeitpunkt (2) |

## Ereigniszahlen

| Lauf | Modell | Record | Feld | Arm | Gold | Vorhersage | Fehler | Klasse |
|---|---|---|---|---|---|---|---|---|
| yun_dev_20261114 | glm | yun2024:120 | intervention_events | intervention | 8.0 |  |  | Unvollstaendige Modellantwort |
| yun_dev_20261114 | glm | yun2024:120 | comparator_events | comparator | 13.0 |  |  | Unvollstaendige Modellantwort |
| yun_dev_20261114 | qwen30 | yun2024:120 | intervention_events | intervention | 8.0 |  |  | Zahl nicht extrahiert |
| yun_dev_20261114 | qwen30 | yun2024:120 | comparator_events | comparator | 13.0 |  |  | Zahl nicht extrahiert |
| yun_dev_20261114 | qwen30 | yun2024:190 | intervention_events | intervention | 52.0 | 26.0 | 26.0 | Nicht eindeutig klassifizierbar |
| yun_dev_20261114 | qwen30 | yun2024:190 | comparator_events | comparator | 51.0 | 32.0 | 19.0 | Nicht eindeutig klassifizierbar |
| yun_dev_20261114 | qwen30 | yun2024:263 | intervention_events | intervention | 72.0 |  |  | Zahl nicht extrahiert |
| yun_dev_fresh_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| yun_dev_fresh_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| yun_dev_fresh_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Nicht eindeutig klassifizierbar |
| yun_dev_fresh_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Prozentwert und absolute Zahl verwechselt |
| yun_dev_retry_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| yun_dev_retry_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| yun_dev_retry_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Nicht eindeutig klassifizierbar |
| yun_dev_retry_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Prozentwert und absolute Zahl verwechselt |
| yun_dev_retry_20261115 | qwen30 | yun2024:120 | intervention_events | intervention | 8.0 | 2.0 | 6.0 | Nicht eindeutig klassifizierbar |
| yun_dev_retry_20261115 | qwen30 | yun2024:120 | comparator_events | comparator | 13.0 | 8.0 | 5.0 | Falsche Tabellenzeile |
| yun_dev_retry_20261115 | qwen30 | yun2024:190 | intervention_events | intervention | 52.0 | 26.0 | 26.0 | Nicht eindeutig klassifizierbar |
| yun_dev_retry_20261115 | qwen30 | yun2024:190 | comparator_events | comparator | 51.0 | 32.0 | 19.0 | Nicht eindeutig klassifizierbar |
| yun_dev_retry_20261115 | qwen30 | yun2024:191 | intervention_events | intervention | 49.0 |  |  | Zahl nicht extrahiert |
| yun_dev_retry_20261115 | qwen30 | yun2024:191 | comparator_events | comparator | 64.0 |  |  | Zahl nicht extrahiert |
| yun_dev_retry_20261115 | qwen30 | yun2024:263 | intervention_events | intervention | 72.0 |  |  | Zahl nicht extrahiert |
| yun_dev_tp_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| yun_dev_tp_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| yun_dev_tp_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Nicht eindeutig klassifizierbar |
| yun_dev_tp_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Prozentwert und absolute Zahl verwechselt |
| yun_dev_tp_20261115 | qwen30 | yun2024:120 | intervention_events | intervention | 8.0 | 2.0 | 6.0 | Nicht eindeutig klassifizierbar |
| yun_dev_tp_20261115 | qwen30 | yun2024:120 | comparator_events | comparator | 13.0 | 8.0 | 5.0 | Falsche Tabellenzeile |
| yun_dev_tp_20261115 | qwen30 | yun2024:190 | intervention_events | intervention | 52.0 | 26.0 | 26.0 | Nicht eindeutig klassifizierbar |
| yun_dev_tp_20261115 | qwen30 | yun2024:190 | comparator_events | comparator | 51.0 | 32.0 | 19.0 | Nicht eindeutig klassifizierbar |
| yun_dev_tp_20261115 | qwen30 | yun2024:191 | intervention_events | intervention | 49.0 |  |  | Zahl nicht extrahiert |
| yun_dev_tp_20261115 | qwen30 | yun2024:191 | comparator_events | comparator | 64.0 |  |  | Zahl nicht extrahiert |
| yun_dev_tp_20261115 | qwen30 | yun2024:263 | intervention_events | intervention | 72.0 |  |  | Zahl nicht extrahiert |
| yun_dev_v3_20261115 | glm | yun2024:190 | intervention_events | intervention | 52.0 | 64.0 | 12.0 | Nicht eindeutig klassifizierbar |
| yun_dev_v3_20261115 | glm | yun2024:190 | comparator_events | comparator | 51.0 | 73.0 | 22.0 | Nicht eindeutig klassifizierbar |
| yun_dev_v3_20261115 | glm | yun2024:191 | intervention_events | intervention | 49.0 | 31.0 | 18.0 | Nicht eindeutig klassifizierbar |
| yun_dev_v3_20261115 | glm | yun2024:191 | comparator_events | comparator | 64.0 | 48.0 | 16.0 | Prozentwert und absolute Zahl verwechselt |

## Gold-Pruefung

1 von 170 Gold-Zellen haben einen Pruefhinweis.

| Record | Feld | Arm | Gold | Treffer im Text | Hinweis |
|---|---|---|---|---|---|
| yun2024:3 | intervention_mean | intervention | 50.6 | 1 | Artikel nennt 50,6 und 50,7 gm fuer denselben Wert; Gold nutzt 50,6 |

## Pruefqueue

505 Eintraege, Prioritaeten: {1: 26, 2: 182, 3: 24, 4: 155, 5: 118}.
