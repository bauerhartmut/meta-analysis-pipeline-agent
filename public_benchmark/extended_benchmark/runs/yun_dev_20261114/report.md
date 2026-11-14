# Yun-Dev-Pilotlauf (14.11.2026)

Erster Lauf des erweiterten Benchmarks auf der numerischen Aufgabe. Bewertet
werden ausschließlich die 43 Dev-Records (`records/yun_dev.jsonl`, 170
Gold-Zellen aus 38 Records mit Inhalt). Der Quell-Testsplit (407 Records) und
die 249 eingefrorenen Records wurden nicht angefasst.

- Modelle: `qwen3-30b-a3b-instruct-2507` (qwen30), `glm-5.3` (glm)
- Temperatur 0, ein Aufruf je Record, keine Wiederholung bei schlechter Antwort
- 43 Aufrufe je Modell, alle HTTP 200
- Leere Antworten: qwen30 1 (nicht verwertbare Zellen), glm 2 (kein JSON)
- Median-Laufzeit je Aufruf: qwen30 1,0 s, glm 3,6 s

## Gesamtergebnis

| Modell | Zellen-Recall | Zellen-Precision | F1 | MAE | MAE-Abdeckung | exakte Records | Armvertauschung |
|---|---|---|---|---|---|---|---|
| qwen30 | 0,500 | 0,460 | 0,479 | 5,50 | 138/170 = 0,81 | 8/43 | 0/68 |
| glm | 0,706 | 0,710 | 0,708 | 3,76 | 160/170 = 0,94 | 24/43 | 0/80 |

Der MAE steht hier bewusst neben der Abdeckung: qwen30 hat den schlechteren
MAE **und** die schlechtere Abdeckung, der niedrigere Fehler von glm ist also
kein Artefakt weniger, leicht zu treffender Zellen.

## MAE ist von einem Record dominiert

| Modell | n | Mittel | Median | p90 | Maximum | Mittel ohne Ausreisser |
|---|---|---|---|---|---|---|
| qwen30 | 138 | 5,50 | 0,00 | 3,60 | 366,67 | 1,71 |
| glm | 160 | 3,76 | 0,00 | 0,68 | 366,67 | 0,48 |

Der Mittelwert entsteht fast vollständig aus `yun2024:229`: Gold
`intervention_mean` 487,33, Vorhersage 854,0 (Abweichung 366,67), dazu
`intervention_standard_deviation` 111,47 gegen 271,6. Beide Modelle liegen dort
gleich falsch, was auf eine Skalen- oder Armzuordnungsfalle im Artikel
hindeutet, nicht auf Modellrauschen. Der Median von 0,0 und p90 von 0,68 bei glm
zeigen: typische Zellen werden exakt getroffen, der Fehler sitzt im Tail. Für
die Berichterstattung ist der Median deshalb die ehrlichere Kennzahl; der
Mittelwert allein wäre irreführend.

## Nach Feld (Recall | MAE | abgedeckte Zellen)

| Feld | Gold | qwen30 | glm |
|---|---|---|---|
| intervention_group_size | 38 | 0,579 \| 0,43 \| 23 | 0,947 \| 0,00 \| 36 |
| comparator_group_size | 38 | 0,579 \| 0,38 \| 24 | 0,947 \| 0,00 \| 36 |
| intervention_events | 8 | 0,625 \| 4,33 \| 6 | 0,875 \| 0,00 \| 7 |
| comparator_events | 8 | 0,750 \| 2,71 \| 7 | 0,875 \| 0,00 \| 7 |
| intervention_mean | 20 | 0,350 \| 20,38 \| 20 | 0,400 \| 20,21 \| 19 |
| comparator_mean | 20 | 0,400 \| 2,95 \| 20 | 0,450 \| 1,07 \| 19 |
| intervention_standard_deviation | 19 | 0,368 \| 9,83 \| 19 | 0,421 \| 9,76 \| 18 |
| comparator_standard_deviation | 19 | 0,421 \| 2,21 \| 19 | 0,474 \| 1,23 \| 18 |

Muster: Größen und Ereigniszahlen werden bei glm fast fehlerfrei gelesen,
sobald sie gefunden werden. Mittelwerte und Streuungen sind das Problem —
Recall 0,35 bis 0,47, und der hohe MAE dieser Felder stammt fast vollständig
aus `yun2024:229`. Die Interventionsspalte ist durchgängig schlechter als die
Kontrollspalte, was für eine Verwechslung der Armzuordnung spricht, obwohl die
formale Vertauschungsprüfung nicht anschlägt (kein Record mit beiden Armen
vertauscht).

## Einordnung

- Der Pilot beantwortet die Formatfrage: Beide Modelle liefern das geforderte
  Zellenformat, glm in 41 von 43 Fällen ohne Parserfehler. Kein Nachbessern der
  Antworten nötig, um bewertbar zu sein.
- glm ist in jeder Kennzahl besser und bei 94 % Abdeckung; qwen30 ist mit 1 s
  je Aufruf aber brauchbar für breite Läufe, wenn Abdeckung mitberichtet wird.
- 43 Records und 170 Zellen sind eine Pilotgröße. Unterschiede von 0,05 im
  Recall sind hier nicht belastbar, der Größenunterschied zwischen den Modellen
  (0,50 gegen 0,71) schon.

Rohdaten: `predictions.jsonl` (86 Zeilen), `eval/*.jsonl`, `eval/*.metrics.json`.
