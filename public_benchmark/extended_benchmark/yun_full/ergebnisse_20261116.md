# Yun-Benchmark: Ergebnisse vom 16.11.2026
Alle Zahlen sind aus `vergleich_20261116.json` erzeugt (Skript `ergebnisse_md.py`),
die Rohdaten liegen unter `../runs/<run-id>/predictions.jsonl`. Der ausfuehrliche
Bericht mit Begruendungen steht in `benchmark_research_report_20261116.md`.

## 1. Alle Laeufe im Ueberblick
| Lauf | Records | P | R | F1 | richtig/falsch/fehlend | Ausfaelle |
|---|---:|---:|---:|---:|---:|---:|
| 60 Records / 4k | 60 | 0,8324 | 0,6102 | 0,7042 | 144/29/63 | 6 |
| GLM / 4k | 20 | 0,9818 | 0,6923 | 0,8120 | 54/1/23 | 2 |
| Qwen397B / 4k | 20 | 1,0000 | 0,4615 | 0,6316 | 36/0/42 | 10 |
| Qwen30 / 4k | 20 | 0,8444 | 0,4872 | 0,6179 | 38/7/33 | 0 |
| GLM+Gruppengroesse / 4k | 20 | 1,0000 | 0,6667 | 0,8000 | 52/0/26 | 4 |
| GLM / 8k | 20 | 0,9365 | 0,7564 | 0,8369 | 59/4/15 | 1 |
| Qwen397B / 8k | 20 | 0,9062 | 0,7436 | 0,8169 | 58/6/14 | 0 |
| Qwen30 / 8k | 20 | 0,8372 | 0,4615 | 0,5950 | 36/7/35 | 0 |
| GLM v8 Quellenzeile / 8k | 20 | 0,9483 | 0,7051 | 0,8088 | 55/3/20 | 2 |

Legende der Laufnamen:
- `yun699_test60_20261116`: Referenzlauf: 60 geschichtete Records, 4.000 Tokens
- `yun20_4000_glm_20261116`: 20-Record-Teilmenge, GLM, 4.000
- `yun20_4000_qwen_20261116`: 20-Record-Teilmenge, Qwen3.5-397B, 4.000
- `yun20_4000_qwen30_20261116`: 20-Record-Teilmenge, Qwen3-30B, 4.000
- `yun20_4000_glm_gskcb_20261116`: Experiment B: Gruppengroessenregel, GLM, 4.000
- `yun20_8000_glm_cb_20261116`: GLM, 8.000, frisch generiert
- `yun20_8000_qwen_cb_20261116`: Qwen3.5-397B, 8.000, frisch generiert
- `yun20_8000_qwen30_cb_20261116`: Qwen3-30B, 8.000, frisch generiert
- `yun20_8000_glm_v8_20261116`: Experiment C: Quellenzeile im Prompt (v8), GLM, 8.000

## 2. Metrikaudit
- Precision vorher 0,8000, weil 7 Zellen ohne Goldannotation als False Positive zaehlten.
- Precision korrekt **0,8324** (144 / 173), F1 **0,7042** statt 0,6923.
- Records exakt: 27 streng gegen 29 nach Yun-Zaehlweise; Ursache sind 2 Records mit
  leerem Gold und leerer Antwort, die Yun als `x == x` als Treffer zaehlt.

## 3. Modellvergleich bei 8.000 Tokens
Gleiche 20 Records, Prompt v7, Temperatur 0, frisch generiert (Cache-Buster).

| Modell | P | R | F1 | exakt streng | Ausfaelle | Tokens | Zeit |
|---|---:|---:|---:|---:|---:|---:|---:|
| GLM | 0,9365 | 0,7564 | 0,8369 | 12/20 | 1 | 39047 | 218 s |
| Qwen397B | 0,9062 | 0,7436 | 0,8169 | 13/20 | 0 | 91720 | 1440 s |
| Qwen30 | 0,8372 | 0,4615 | 0,5950 | 5/20 | 0 | 2185 | 29 s |

Das Limit 8.000 hilft GLM gegenueber 4.000 um +0,025 F1 (Recall +0,064, Precision -0,045).
Qwen3.5-397B war bei 4.000 durch das Limit halbiert (10 Ausfaelle) und ist bei 8.000
konkurrenzfaehig; Qwen3-30B holt auch bei 8.000 nicht auf.

## 4. Experimente
| Experiment | Baseline | Variante | Differenz F1 | Ergebnis |
|---|---:|---:|---:|---:|
| B: Gruppengroessenregel | F1 0,8120 | F1 0,8000 | -0,0120 | kein Gewinn, Hypothese verworfen |
| C: Quellenzeile im Prompt (v8) | F1 0,8369 | F1 0,8088 | -0,0281 | gescheitert; Modell ignoriert den Zusatz |

## 5. Auswertung ohne bestreitbare Goldannotationen
Ausgeschlossen: yun2024:524 (Fliesstext gegen Tabelle), yun2024:447 (zwei verschiedene N),
yun2024:669 (Modellwert im Artikel nicht auffindbar).

| Lauf | mit Konflikten | ohne Konflikte |
|---|---:|---:|
| 60 Records, 4000 Tokens | P 0,8324 / R 0,6102 / F1 0,7042 | P 0,8616 / R 0,6284 / F1 0,7268 |
| 20 Records, 4000 Tokens | P 0,9818 / R 0,6923 / F1 0,8120 | P 1,0000 / R 0,7361 / F1 0,8480 |

## 6. Validator (60-Referenzlauf)
- Harte Warnungen: 15 bei 60 Records, zusaetzlich 124 weiche Hinweise (fehlende Felder, nicht als Fehler gezaehlt)
- `weich:feld_fehlt`: 112
- `weich:n_fehlt`: 12
- `leere_antwort`: 11
- `events_ueber_n`: 2
- `arme_sehr_ungleich`: 1
- `sd_gegen_mittel`: 1
- Erkannte falsche Zellen: 2 von 29 (Quote 0,069), Fehlalarme 1

## 7. Fehlerklassen der 29 falschen Zellen (60 Records)
| Klasse | Anzahl | Belegter Fall |
|---|---:|---:|
| Armzuordnung / Population | 13 | yun2024:335 Arme vertauscht; yun2024:359 ITT statt Week-96-Population |
| Zeitpunkt | 4 | yun2024:573 6-Monats- statt 24-Monats-Zeile |
| Einheit / Skalierung | 4 | yun2024:246 g/l stillschweigend x100; yun2024:369 Prozent als Ereigniszahl |
| Tabellenzeile / Spalte | 4 | yun2024:669 falsche Zeile, Goldwerte passen zur Tabelle |
| Goldfehler / Quellenkonflikt | 4 | yun2024:524 Text gegen Tabelle; yun2024:447 zwei N |
| Halluzination | 0 | kein Fall belegt |

## 8. Kennzahlen je Feld (Referenzlauf 60 Records)
| Feld | richtig | falsch | fehlend |
|---|---:|---:|---:|
| intervention_mean | 15 | 5 | 8 |
| intervention_standard_deviation | 10 | 5 | 8 |
| intervention_group_size | 36 | 5 | 13 |
| comparator_mean | 15 | 5 | 7 |
| comparator_standard_deviation | 10 | 5 | 8 |
| comparator_group_size | 39 | 2 | 13 |
| intervention_events | 10 | 1 | 2 |
| comparator_events | 9 | 1 | 4 |

## 9. Was das fuer die Entscheidung bedeutet
1. GLM-5.3 bleibt das primaere Modell (F1 0,8369 bei 8.000 Tokens, beste Bilanz aus
   Qualitaet, Tokens und Laufzeit).
2. Qwen3.5-397B ist bei 8.000 Tokens fast gleichwertig, aber 2,3-mal teurer und
   6,6-mal langsamer; kein Wechselgrund.
3. Qwen3-30B ist als Extraktor nicht ausreichend (F1 0,5950).
4. Kein Prompt-Zusatz hat bisher geholfen. Der naechste Hebel ist die echte
   Zweistufigkeit (Zeile/Arm als eigener Aufruf), nicht ein weiterer Satz im Prompt.
5. Vor Vergleichen mit fremden Systemen die bereinigte Auswertung ohne die drei
   konfliktaeren Records verwenden.
