# Was der GLM-Reparaturlauf bringen kann (Schätzung)

Grundlage: Lesekopie `runs/_lesekopie_20261118/predictions.jsonl`, Modell glm. 104 Ausfallzeilen (103 `length_ohne_ergebnis`, 1 `json_kaputt`) mit 427 Goldzellen, davon 0 schon richtig; die Zeilen liefern 0 Zellen, also ist alles Gewinnbare noch offen (427 Zellen).

Bestand: 699 Records, 2773 Goldzellen, richtig 1840, falsch 281, fehlend 652, Precision 0.8675, Recall 0.6635, F1 0.7519.

**Gemessen** ist der Anker: brauchbare Zeilen treffen im Mittel 3.09 Goldzellen, im Median 2; 11.3% der brauchbaren Zeilen trifft gar nichts. **Geschätzt** ist allein die Reparaturquote — im Bestand gibt es keine Zeile mit `pfad=repair`. Die Szenarien variieren deshalb nur diesen einen Parameter.

| Szenario | Zellen dazu | richtig | Recall | Precision | F1 | F1-Delta |
|---|---:|---:|---:|---:|---:|---:|
| zurueckhaltend: 50 % der 104 Records brauchbar, je 2 richtige Zellen | +104 | 1944 | 0.7010 | 0.8675 | 0.7754 | +0.0235 |
| mittel: 75 % brauchbar, je 2 richtige Zellen | +156 | 1996 | 0.7198 | 0.8674 | 0.7868 | +0.0349 |
| optimistisch: alle brauchbar, je 3.09 richtige Zellen | +322 | 2162 | 0.7797 | 0.8676 | 0.8213 | +0.0694 |
| Obergrenze: alle Goldzellen der Ausfaelle (427 gewinnbar) | +427 | 2267 | 0.8175 | 0.8676 | 0.8418 | +0.0899 |

Orientierung: Ein Recall-Punkt sind 28 Zellen. Das mittlere Szenario hebt den Recall um +5.6 Punkte, das optimistische um +11.6.

Annahmen und Grenzen:

- Die Precision bleibt konstant; fallen die Reparaturantworten schlechter aus, sinkt sie.
- Der Anker stammt aus normalen Laeufen. Reparaturantworten entstehen aus gekuerztem Text und 6.000 statt 24.000 Tokens und duerften deshalb schwaecher sein; das spricht gegen die optimistischen Szenarien, nicht gegen die Obergrenze.
- Die Obergrenze verlangt in jeder Ausfallzeile jede Goldzelle richtig, im Mittel 4.11 je Record. Der Reparatur-Prompt erlaubt bis zu sechs Zellen ("at most six cells"), schliesst sie also nicht aus, macht sie aber unwahrscheinlich.
- Nicht enthalten sind die leeren Antworten ohne Ausfallklasse; sie laufen in einem eigenen Block (`retry_leer_ids.txt`), nicht in diesem Reparaturlauf.
- Bei `json_kaputt` greift kein Reparaturaufruf, sondern der einfache Retry.
