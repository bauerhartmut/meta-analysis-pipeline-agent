# Yun-Dev-Lauf mit frischer Generierung (15.11.2026)

Vierter Lauf auf denselben 43 Dev-Records. Der vorherige Lauf kam aus dem
Gateway-Cache (alle Antworten unter 0,2 s). Für diesen Lauf hängt
`--cache-buster` einen zufälligen Session-Tag in den Systemprompt; das ändert
den Prompt und ist deshalb als eigene Version **`v2b_cachebuster`** deklariert.
Die Zeitpunktvorgabe aus `v2_timepoint` bleibt Wort für Wort enthalten, es kommt
nur eine Zeile `Session tag: <zufall>` hinzu.

Nachweis, dass frisch generiert wurde:

- `suspected_cache` = 0 von 43
- Laufzeit min 1,64 s, Median 3,81 s, max 50,38 s (vorher: alle unter 0,2 s)
- 37 von 43 Zellenlisten weichen trotzdem nicht ab — bei Temperatur 0 und
  identischem Text ist das erwartbar; 6 Records unterscheiden sich

## Vergleich mit dem Lauf aus dem Cache

| Kennzahl | Cache-Lauf (`yun_dev_retry`) | Frischer Lauf (`v2b`) |
|---|---|---|
| Zellen-Recall | 0,900 | **0,959** |
| Zellen-Precision | 0,933 | 0,931 |
| **Zellen-F1** | 0,916 | **0,945** |
| **MAE** | 0,470 | **0,405** |
| **mae_coverage** | 0,929 (158/170) | **0,988 (168/170)** |
| exakte Records | 33/43 | 35/43 |
| Armvertauschung | 0/79 | 0/84 |
| vorhergesagte Zellen | 164 | 175 |

Der frische Lauf ist in F1, MAE und Abdeckung besser als der Cache-Lauf. Die
Cache-Zahlen waren also keine Überschätzung, sondern eine leichte
Unterschätzung.

## Was sich geändert hat

- `yun2024:231` (musculäre Ausdauer) wurde gerettet: erster Versuch `length`,
  Wiederholung mit 32.000 Token lieferte 6 Zellen in 2.794 Token. Der Record,
  der sich vorher auch bei 32k festlief, antwortet frisch also doch.
- `yun2024:233` ebenfalls gerettet (4.160 Token, 6 Zellen).
- Zwei Records bleiben leer, beide **korrekt**: `yun2024:17` und `yun2024:18`
  haben 0 Gold-Zellen; die Antwort `{"cells": []}` ist die richtige.
- Zwei der 170 Gold-Zellen bleiben ohne Vorhersage; welche, steht nicht in
  diesem Bericht und ist noch nicht erhoben.

## Nach Feld (frischer Lauf: Recall | MAE | abgedeckte Zellen)

| Feld | Gold | glm |
|---|---|---|
| intervention_group_size | 38 | 0,974 \| 0,00 \| 37 |
| comparator_group_size | 38 | 0,974 \| 0,00 \| 37 |
| intervention_events | 8 | 0,750 \| 3,75 \| 8 |
| comparator_events | 8 | 0,750 \| 4,75 \| 8 |
| intervention_mean | 20 | 0,950 \| 0,005 \| 20 |
| comparator_mean | 20 | 1,000 \| 0,00 \| 20 |
| intervention_standard_deviation | 19 | 1,000 \| 0,00 \| 19 |
| comparator_standard_deviation | 19 | 1,000 \| 0,00 \| 19 |

Das Bild ist jetzt eindeutig: Gruppengrößen, Mittelwerte und Streuungen werden
bei glm praktisch fehlerfrei gelesen (MAE 0,00 bis 0,005). Der gesamte
verbleibende Fehler sitzt in den **Ereigniszahlen**: 4 von 16 Zellen fehlen,
4 weitere sind falsch, MAE 3,75 bzw. 4,75. Diese 8 Zellen sind der einzige
Grund, warum der Recall nicht über 0,97 liegt.

## Einordnung

- Der Prompt-Zusatz ist rein technisch (Session-Tag), nicht inhaltlich. `v2b`
  und `v2_timepoint` sollten in Vergleichen trotzdem getrennt geführt werden,
  weil die Anfragen nicht identisch sind.
- 43 Records bleiben Pilotgröße. Der Abstand zu qwen30 (F1 0,466) ist deutlich
  größer als die Änderung zwischen den glm-Läufen (0,916 auf 0,945), also
  belastbar; Unterschiede von 0,03 innerhalb von glm sind es nicht.

Rohdaten: `predictions.jsonl` (43 Zeilen, `prompt_version = v2b_cachebuster`),
`eval/glm.jsonl`, `eval/glm.metrics.json`.
