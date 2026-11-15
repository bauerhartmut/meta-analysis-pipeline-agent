# Ergebnisse: Yun-Dev-Pilotlaeufe (numerische Extraktion)

Automatisch erzeugt aus den Laufdaten von `run_extended_extraction.py` und
`evaluate_extended.py`. Datengrundlage: die 43 Dev-Records aus
`records/yun_dev.jsonl` mit 170 Gold-Zellen aus 38 Records mit Inhalt.
Der Quell-Testsplit (407 Records) und die 249 eingefrorenen Records wurden
nicht verwendet.

Der MAE steht in jeder Tabelle neben `mae_coverage`, damit ein niedriger
Fehler bei duenner Abdeckung nicht als gut durchgeht.

## Ueberblick

| Lauf | Prompt | Modell | Recall | Precision | F1 | MAE | mae_coverage | exakt | Vertauschung | leer | Antworten < 1 s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Lauf 1: ohne Zeitpunktangabe | `v1` | qwen3-30b-a3b | 0,500 | 0,460 | 0,479 | 5,502 | 0,812 (138/170) | 8/43 | 0/68 | 1/43 | 18/43 |
| Lauf 1: ohne Zeitpunktangabe | `v1` | glm-5.3 | 0,706 | 0,710 | 0,708 | 3,764 | 0,941 (160/170) | 24/43 | 0/80 | 2/43 | 0/43 |
| Lauf 2: Zeitpunkt im Prompt | `v2_timepoint` | qwen3-30b-a3b | 0,465 | 0,468 | 0,466 | 0,977 | 0,735 (125/170) | 8/43 | 0/61 | 1/43 | 13/43 |
| Lauf 2: Zeitpunkt im Prompt | `v2_timepoint` | glm-5.3 | 0,829 | 0,928 | 0,876 | 0,509 | 0,859 (146/170) | 31/43 | 0/73 | 5/43 | 1/43 |
| Lauf 3: mit Retry (Cache-Treffer) | `v2_timepoint` | qwen3-30b-a3b | 0,465 | 0,468 | 0,466 | 0,977 | 0,735 (125/170) | 8/43 | 0/61 | 1/43 | 43/43 |
| Lauf 3: mit Retry (Cache-Treffer) | `v2_timepoint` | glm-5.3 | 0,900 | 0,933 | 0,916 | 0,470 | 0,929 (158/170) | 33/43 | 0/79 | 3/43 | 43/43 |
| Lauf 4: frisch, Cache-Buster | `v2_timepoint` | glm-5.3 | 0,959 | 0,931 | 0,945 | 0,405 | 0,988 (168/170) | 35/43 | 0/84 | 2/43 | 0/43 |
| Lauf 5: absolute Ereigniszahlen | `v3_abs_count` | glm-5.3 | 0,900 | 0,939 | 0,919 | 0,431 | 0,929 (158/170) | 33/43 | 0/79 | 3/43 | 0/43 |
| Lauf 6: Standardprompt frisch | `v2_timepoint` | glm-5.3 | 0,935 | 0,930 | 0,933 | 0,415 | 0,965 (164/170) | 34/43 | 0/82 | 2/43 | 0/43 |
| Lauf 7: letzter Messzeitpunkt | `v4_last_timepoint` | glm-5.3 | 0,753 | 0,723 | 0,738 | 3,621 | 0,988 (168/170) | 25/43 | 0/84 | 0/43 | 0/43 |
| Lauf 8: Zielzeitpunkt je Record | `v5_target_timepoint` | glm-5.3 | 0,694 | 0,936 | 0,797 | 0,001 | 0,700 (119/170) | 24/43 | 0/59 | 9/43 | 0/43 |
| Lauf 9: Zielzeitpunkt mit Rueckfall | `v6_target_fallback` | glm-5.3 | 0,947 | 0,942 | 0,944 | 0,039 | 0,953 (162/170) | 34/43 | 0/81 | 1/43 | 0/43 |
| Lauf 10: Rueckfall wiederholt | `v6_target_fallback` | glm-5.3 | 0,982 | 0,944 | 0,963 | 0,001 | 0,988 (168/170) | 35/43 | 0/84 | 1/43 | 0/43 |
| Lauf 11: JSON-Retry, Standard v6 | `v6_target_fallback` | glm-5.3 | 0,982 | 0,949 | 0,965 | 0,037 | 0,988 (168/170) | 36/43 | 0/84 | 1/43 | 0/43 |

Prompt-Versionen kanonisch: `v2b_cachebuster`, `v2_timepoint` und
`v2_timepoint_cb` sind dieselbe Fassung (`v2_timepoint`), der Cache-Zusatz
`_cb` ist nur eine Generierungsvariante (siehe `versions.py`).

Antworten unter einer Sekunde sind ein Cache-Verdacht, kein Beweis: bei
qwen3-30b sind sie auch normale Geschwindigkeit. Aussagekraeftig ist das
Vollbild: Lauf 3 hat 43 von 43 in unter 0,2 s, Lauf 4 keine einzige.

## Letzter Lauf je Modell nach Feld

qwen3-30b: Lauf 3, glm: Lauf 4 (beide kanonisch `v2_timepoint`).
Werte als Recall | MAE | abgedeckte Zellen.

| Feld | Gold | qwen3-30b | glm-5.3 |
|---|---|---|---|
| intervention_group_size | 38 | 0,421 \| 0,59 \| 17 | 0,974 \| 0,00 \| 37 |
| comparator_group_size | 38 | 0,421 \| 0,47 \| 17 | 0,974 \| 0,00 \| 37 |
| intervention_events | 8 | 0,500 \| 5,33 \| 6 | 0,750 \| 3,75 \| 8 |
| comparator_events | 8 | 0,625 \| 3,43 \| 7 | 0,750 \| 4,75 \| 8 |
| intervention_mean | 20 | 0,450 \| 0,90 \| 20 | 0,950 \| 0,01 \| 20 |
| comparator_mean | 20 | 0,500 \| 0,30 \| 20 | 1,000 \| 0,00 \| 20 |
| intervention_standard_deviation | 19 | 0,474 \| 0,97 \| 19 | 1,000 \| 0,00 \| 19 |
| comparator_standard_deviation | 19 | 0,526 \| 0,30 \| 19 | 1,000 \| 0,00 \| 19 |

## Fehlerverteilung der letzten Laeufe

| Lauf | Modell | gepaarte Zellen | Median | p90 | Maximum |
|---|---|---|---|---|---|
| Lauf 3: mit Retry (Cache-Treffer) | qwen3-30b-a3b | 125 | 0,000 | 2,700 | 26,000 |
| Lauf 3: mit Retry (Cache-Treffer) | glm-5.3 | 158 | 0,000 | 0,000 | 22,000 |
| Lauf 4: frisch, Cache-Buster | glm-5.3 | 168 | 0,000 | 0,000 | 22,000 |

## Befunde

- Der Zeitpunkt im Prompt (`v2`) behebt den groessten Einzelfehler:
  `yun2024:229` wurde vorher von beiden Modellen mit 854,0 statt 487,33
  beantwortet (Follow-up-Spalte statt Post-test).
- Die Wiederholung bei `finish_reason = "length"` rettet zwei von drei
  Ausfaellen; frisch generiert gelingt auch der dritte.
- Bei glm sitzt der gesamte Restfehler in den Ereigniszahlen: Recall 0,75,
  MAE 3,75 bis 4,75 bei je 8 Gold-Zellen. Gruppengroessen, Mittelwerte und
  Streuungen liegen bei MAE 0,00 bis 0,005.
- Armvertauschung trat in keinem Lauf auf.
- Lauf 3 kam aus dem Gateway-Cache (alle Antworten unter 0,2 s, 84 von 86
  Zellenlisten zeichengleich); Lauf 4 ist die belastbare Messung.

## Grenzen

- 43 Records sind Pilotgroesse; Unterschiede unter etwa 0,03 F1 sind nicht
  belastbar, der Abstand zwischen den Modellen schon.
- Vergleiche nur innerhalb derselben Prompt-Version; `v2b_cachebuster`
  enthaelt zusaetzlich einen technischen Session-Tag.
- Keine Sichtpruefung der Modellantworten, nur Parser und Metriken.
- Zwei Records (`yun2024:17`, `yun2024:18`) haben 0 Gold-Zellen; leere
  Antworten dort sind korrekt.

## Quelldaten

- `yun_dev_20261114/`: Lauf 1: ohne Zeitpunktangabe, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_tp_20261115/`: Lauf 2: Zeitpunkt im Prompt, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_retry_20261115/`: Lauf 3: mit Retry (Cache-Treffer), `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_fresh_20261115/`: Lauf 4: frisch, Cache-Buster, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_v3_20261115/`: Lauf 5: absolute Ereigniszahlen, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_std_20261115/`: Lauf 6: Standardprompt frisch, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_v4_20261115/`: Lauf 7: letzter Messzeitpunkt, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_v5_20261115/`: Lauf 8: Zielzeitpunkt je Record, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_v6_20261115/`: Lauf 9: Zielzeitpunkt mit Rueckfall, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_v6b_20261115/`: Lauf 10: Rueckfall wiederholt, `predictions.jsonl`, `eval/*.metrics.json`
- `yun_dev_v6c_20261115/`: Lauf 11: JSON-Retry, Standard v6, `predictions.jsonl`, `eval/*.metrics.json`
- Erzeugt von `runs/build_results_md.py`.
