# Yun-Dev-Lauf mit Wiederholung bei Tokenlimit (15.11.2026)

Dritter Lauf auf denselben 43 Dev-Records (170 Gold-Zellen). Prompt unverändert
(`v2_timepoint`), neu ist nur die Wiederholungsregel im Runner: Antworten mit
`finish_reason = "length"` bekommen genau einen zweiten Versuch mit 32.000
Token.

## Ergebnis

| Modell | Recall | Precision | F1 | MAE | MAE-Abdeckung | exakte Records | Vertauschung |
|---|---|---|---|---|---|---|---|
| qwen30 | 0,465 | 0,468 | 0,466 | 0,98 | 125/170 = 0,74 | 8/43 | 0/61 |
| glm | 0,900 | 0,933 | **0,916** | **0,47** | **158/170 = 0,93** | 33/43 | 0/79 |

Gegenüber dem Lauf ohne Wiederholung (`yun_dev_tp_20261115`):

| Modell | Kennzahl | ohne Retry | mit Retry |
|---|---|---|---|
| glm | Recall / Precision / F1 | 0,829 / 0,928 / 0,876 | 0,900 / 0,933 / 0,916 |
| glm | MAE bei Abdeckung | 0,51 bei 0,86 | 0,47 bei 0,93 |
| glm | exakte Records | 31/43 | 33/43 |
| qwen30 | alle Kennzahlen | unverändert | unverändert |

qwen30 hatte keinen `length`-Ausfall, die Regel greift dort nicht.

## Was die Wiederholung gebracht hat

Drei glm-Zeilen wurden wiederholt, zwei davon gerettet:

| Record | Erster Versuch | Wiederholung | Zellen |
|---|---|---|---|
| yun2024:228 | `length`, 24.000 Token | `stop`, 3.728 Token | 6 (gerettet) |
| yun2024:233 | `length`, 24.000 Token | `stop`, 5.015 Token | 6 (gerettet) |
| yun2024:231 | `length`, 24.000 Token | `length`, 32.000 Token | 0 (bleibt aus) |

Die Abdeckung steigt damit von 146 auf 158 gepaarte Zellen, der Recall von 0,829
auf 0,900, die Zahl exakter Records von 31 auf 33. Ein Record (231, musculäre
Ausdauer) widersetzt sich auch bei 32.000 Token; das ist die zuvor
dokumentierte Reasoning-Schleife und bleibt eine echte Lücke von 6 Zellen.

## Einschränkung: der Lauf kam aus dem Cache

Alle 86 Antworten kamen in **unter 0,2 Sekunden** zurück (Median 0,12 s bei
qwen30, 0,09 s bei glm), und 84 der 86 Zellenlisten sind zeichengleich mit dem
Lauf `yun_dev_tp_20261115`. Auch die beiden geretteten Zeilen tragen die
Tokenzahlen der Diagnoseläufe (3.728 und 5.015). Das Gateway hat also frühere
Antworten erneut ausgeliefert, darunter auch die 32.000er-Versuche aus
`yun_dev_diag_32k`.

Konsequenz für die Lesart: Die Zahlen sind eine korrekte Auswertung der so
zustande gekommenen Vorhersagen, aber **keine unabhängige Stichprobe**. Der
Unterschied zum vorherigen Lauf stammt ausschließlich aus der
Wiederholungsregel, nicht aus einer neuen Generierung. Für belastbare
Modellvergleiche braucht es einen Lauf ohne Cache-Treffer; der Runner markiert
Laufzeiten unter einer Sekunde jetzt als `suspected_cache`.

## Nach Feld (mit Retry: Recall | MAE | abgedeckte Zellen)

| Feld | Gold | qwen30 | glm |
|---|---|---|---|
| intervention_group_size | 38 | 0,421 \| 0,59 \| 17 | 0,947 \| 0,00 \| 36 |
| comparator_group_size | 38 | 0,421 \| 0,47 \| 17 | 0,947 \| 0,00 \| 36 |
| intervention_events | 8 | 0,500 \| 5,33 \| 6 | 0,750 \| 3,75 \| 8 |
| comparator_events | 8 | 0,625 \| 3,43 \| 7 | 0,750 \| 4,75 \| 8 |
| intervention_mean | 20 | 0,450 \| 0,90 \| 20 | 0,900 \| 0,00 \| 18 |
| comparator_mean | 20 | 0,500 \| 0,30 \| 20 | 0,850 \| 0,35 \| 18 |
| intervention_standard_deviation | 19 | 0,474 \| 0,97 \| 19 | 0,895 \| 0,00 \| 17 |
| comparator_standard_deviation | 19 | 0,526 \| 0,30 \| 19 | 0,895 \| 0,00 \| 17 |

Mittelwerte und Streuungen sind bei glm jetzt das stärkste Feld (Recall 0,85 bis
0,90, MAE 0,00 bis 0,35). Schwach bleiben die Ereigniszahlen (Recall 0,75, MAE
3,75 bis 4,75 bei nur 8 Zellen) und die Gruppengrößen bei qwen30.

Rohdaten: `predictions.jsonl` (86 Zeilen inklusive `retried` und
`suspected_cache`), `eval/*.jsonl`, `eval/*.metrics.json`.
