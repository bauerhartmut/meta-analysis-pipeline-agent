# Was der GLM-Reparaturlauf bringen kann (Schätzung)

Grundlage: Lesekopie `runs/_lesekopie_20261118/predictions.jsonl`, Modell glm. 104 Ausfälle, davon 103 `length_ohne_ergebnis` und 1 `json_kaputt`. Diese Records tragen 427 Goldzellen; alle zählen heute als fehlend.

Bestand: 699 Records, 2773 Goldzellen, richtig 1840, falsch 281, fehlend 652, Precision 0.8675, Recall 0.6635, F1 0.7519.

Die Quote der Reparatur ist **nicht gemessen**: Im Bestand gibt es keine Zeile mit `pfad=repair`. Die Szenarien spannen deshalb den plausiblen Bereich auf; alle Zahlen darin sind Schätzungen, keine Messungen. Die Precision bleibt konstant angenommen, weil neue Zellen dieselbe Treffsicherheit wie der Bestand haben dürften.

| Szenario | richtige Zellen dazu | richtig | Recall | Precision | F1 | F1-Delta |
|---|---:|---:|---:|---:|---:|---:|
| konservativ (40 % Erfolg, 60 % Zelltreffer) | +102 | 1942 | 0.7003 | 0.8674 | 0.7749 | +0.0230 |
| mittel (60 % Erfolg, 78 % Zelltreffer) | +200 | 2040 | 0.7357 | 0.8673 | 0.7961 | +0.0442 |
| Anker wie die brauchbaren Zeilen (3,09 richtige Zellen je Record) | +322 | 2162 | 0.7797 | 0.8676 | 0.8213 | +0.0694 |

Orientierung: Ein Recall-Punkt sind 28 Zellen. Selbst das optimistische Szenario hebt den Recall um +11.6 Punkte, das mittlere um +7.2.

Nicht enthalten: die 36 leeren Antworten ohne Ausfallklasse. Sie sind ein eigener Block (`retry_leer_ids.txt`) und laufen nicht in diesem Reparaturlauf mit.
