# Yun-Dev-Pilotlauf mit Zeitpunktvorgabe (15.11.2026)

Wiederholung des Pilotlaufs vom 14.11.2026 auf denselben 43 Dev-Records
(170 Gold-Zellen). Einzige Änderung: Der Prompt nennt jetzt den Messzeitpunkt
(`PROMPT_VERSION = "v2_timepoint"`): Werte am Ende der Intervention, nicht
Baseline, nicht Follow-up. Record-Schema und Gold-Werte blieben unverändert.

- Modelle: qwen3-30b-a3b-instruct-2507 (qwen30), glm-5.3 (glm)
- 43 Aufrufe je Modell, alle HTTP 200, keine Wiederholungen
- Leere Antworten: qwen30 1 (wie zuvor), glm 5 (zuvor 2; 3 x kein JSON,
  2 x keine verwertbaren Zellen)
- Median-Laufzeit: qwen30 2,0 s, glm 3,4 s

## Vergleich mit dem Lauf ohne Zeitpunktangabe

| Modell | Kennzahl | Lauf 14.11. | Lauf 15.11. |
|---|---|---|---|
| qwen30 | Recall / Precision / F1 | 0,500 / 0,460 / 0,479 | 0,465 / 0,468 / 0,466 |
| qwen30 | MAE bei Abdeckung | 5,50 bei 138/170 = 0,81 | **0,98** bei 125/170 = **0,74** |
| qwen30 | exakte Records | 8/43 | 8/43 |
| glm | Recall / Precision / F1 | 0,706 / 0,710 / 0,708 | **0,829 / 0,928 / 0,876** |
| glm | MAE bei Abdeckung | 3,76 bei 160/170 = 0,94 | **0,51** bei 146/170 = **0,86** |
| glm | exakte Records | 24/43 | **31/43** |

Armvertauschung bleibt in beiden Läufen bei 0 (neu: 0/61 bei qwen30, 0/73 bei
glm).

Die Zeitpunktvorgabe wirkt genau dort, wo der Ausreißer saß: `intervention_mean`
und `intervention_standard_deviation` gehen bei glm von MAE 20,21 bzw. 9,76 auf
**0,00**, der Recall dieser Felder von 0,40/0,42 auf 0,80/0,79. `yun2024:229`
liefern jetzt beide Modelle exakt (487,33 und 453,57), vorher beide 854,0 und
470,0.

## Der Gewinn ist nicht gratis

- glm verliert Abdeckung: 146 statt 160 gepaarte Zellen, 5 statt 2 leere
  Antworten. Precision und F1 steigen also teilweise, weil das Modell bei
  unsicheren Records lieber schweigt. Der MAE fällt trotzdem echt, weil er auf
  den verbleibenden Zellen von 3,76 auf 0,51 geht — das ist keine
  Abdeckungsarithmetik.
- glm verliert bei den Ereigniszahlen: Recall 0,875 auf 0,75, MAE 0,00 auf 3,75
  (intervention) bzw. 4,75 (comparator), bei 8 abgedeckten Zellen. Die
  Zeitpunktformulierung hat dort offenbar die Aufmerksamkeit verschoben.
- qwen30 verliert Recall und Abdeckung (0,81 auf 0,74), gewinnt aber massiv beim
  MAE (5,50 auf 0,98). Bei 43 Records ist der Recall-Rückgang von 0,035 nicht
  belastbar.

## Nach Feld (Lauf 15.11.: Recall | MAE | abgedeckte Zellen)

| Feld | Gold | qwen30 | glm |
|---|---|---|---|
| intervention_group_size | 38 | 0,421 \| 0,59 \| 17 | 0,895 \| 0,00 \| 34 |
| comparator_group_size | 38 | 0,421 \| 0,47 \| 17 | 0,895 \| 0,00 \| 34 |
| intervention_events | 8 | 0,500 \| 5,33 \| 6 | 0,750 \| 3,75 \| 8 |
| comparator_events | 8 | 0,625 \| 3,43 \| 7 | 0,750 \| 4,75 \| 8 |
| intervention_mean | 20 | 0,450 \| 0,90 \| 20 | 0,800 \| 0,00 \| 16 |
| comparator_mean | 20 | 0,500 \| 0,30 \| 20 | 0,750 \| 0,39 \| 16 |
| intervention_standard_deviation | 19 | 0,474 \| 0,97 \| 19 | 0,789 \| 0,00 \| 15 |
| comparator_standard_deviation | 19 | 0,526 \| 0,30 \| 19 | 0,789 \| 0,00 \| 15 |

## Einordnung

- Die Zeitpunktangabe gehört in den Prompt. Sie behebt einen Fehler, der 90 der
  170 Dev-Zellen betrifft (alle 15 Records aus PMC5498715), und kostet bei glm
  Abdeckung (0,94 auf 0,86), nicht Genauigkeit.
- Die Läufe sind nur innerhalb derselben Prompt-Version vergleichbar. Der Lauf
  vom 14.11. bleibt als `v1` dokumentiert und sollte nicht mit `v2`-Zahlen
  gemischt werden.
- Offen: glm antwortet bei 5 von 43 Records leer. Vor dem Quell-Testsplit ist zu
  klären, ob das an der Promptlänge, am JSON-Zwang oder an langen Tabellen liegt.

Rohdaten: `predictions.jsonl` (86 Zeilen), `eval/*.jsonl`,
`eval/*.metrics.json`.
