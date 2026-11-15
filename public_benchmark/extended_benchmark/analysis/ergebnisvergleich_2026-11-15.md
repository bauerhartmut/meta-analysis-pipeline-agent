# Benchmark-Ergebnisse und Verbesserungsbewertung

Stand: 15.11.2026  
Grundlage: vorhandene, abgeschlossene Läufe und Auswertungen. Kein neuer Modell- oder Netzaufruf.

## 1. Kurzfazit

Auf dem Yun-Benchmark gibt es eine belegte Verbesserung bei Abdeckung und Recall. Ein allgemeiner Qualitätsfortschritt über alle Benchmarks ist daraus aber nicht ableitbar.

| Benchmark | Früher | Aktuell | Bewertung |
|---|---:|---:|---|
| Yun-Dev, GLM | v1: F1 **0,708** | v6: **0,944 bis 0,965** | Deutlich verbessert, aber der Dev-Satz wurde für die Prompt-Entwicklung mehrfach verwendet |
| Yun-186, v6 | F1 **0,6548** | — | Ausgangsbasis für den großen Test |
| Yun-186, kombiniert v6+v7 | F1 **0,6548** | F1 **0,6934** | Beobachtete Verbesserung, aber selektive Reparatur von 47 Fehlzeilen |
| v7-Pilot | — | 5/6 formal, nur **4/6 mit Zellen** | Kriterium wegen Median **8.951 > 6.000 Tokens** nicht bestanden |
| GLASS, 54 Records | 13.11. | kein neuer Lauf | Keine Evidenz für eine Verbesserung in diesem Benchmark |

## 2. Yun-186: Was sich verändert hat

Der kombinierte Lauf aus v6 und dem v7-Folgelauf zeigt:

| Kennzahl | v6 | kombiniert v6+v7 | Veränderung |
|---|---:|---:|---:|
| Zell-F1 | 0,6548 | **0,6934** | **+3,9 Prozentpunkte** |
| Recall | 0,6184 | **0,7032** | **+8,5 Prozentpunkte** |
| Precision | 0,6958 | 0,6838 | **−1,2 Prozentpunkte** |
| exakte Records | 73 von 186 | 79 von 186 | **+6 Records** |
| Auslassungen | 197 | 137 | **−60** |
| MAE | 0,3796 | 1,6303 | deutlich höher |
| MAE-Coverage | 0,6731 | 0,7862 | **+11,3 Prozentpunkte** |

Die Verbesserung kommt überwiegend daher, dass vorher fehlende Records jetzt Zellen liefern. Die Genauigkeit der gelieferten Zellen ist nicht besser geworden: Die Precision sinkt leicht, und die MAE steigt deutlich.

Der MAE-Anstieg ist teilweise ein Skaleneffekt: Die neu gewonnenen Records enthalten große Outcome-Werte, darunter einen Einzelfehler von 305. Der kombinierte MAE ist deshalb nicht direkt mit dem v6-MAE vergleichbar.

Hinweis zu den F1-Werten: Der Hauptwert in `fallback_eval_kombiniert.json` ist `gesamt.cell_f1 = 0,6934`. Der abweichende Wert `zell_f1_aus_klassen = 0,6784` ist eine klassenbasierte Nebenrechnung und sollte nicht als Hauptwert verwendet werden.

## 3. Der wichtigste Vorbehalt

Das ist **kein sauberer v7-Gesamtlauf**:

- Der v7-Folgelauf lief nur über die 47 Records, die bei v6 wegen `length` gescheitert waren.
- 18 dieser 47 Records scheiterten auch mit v7; 23 lieferten Zellen, 6 lieferten gültiges JSON ohne Zellen.
- In der kombinierten Datei kommen 157 Zeilen aus v6 und 29 aus v7. Die 18 verbliebenen v7-Fehler bleiben als v6-Zeilen stehen.
- Die 186er-Menge ist für v7 kein unberührter Holdout mehr, weil v7 genau an ihren Fehlzeilen entwickelt und getestet wurde.
- Der v7-Pilot war mit **5/6 formalen Erfolgen**, aber nur **4/6 mit Zellen**, optimistisch. Im vollständigen Folgelauf blieben **18 von 47 = 38,3 Prozent** Length-Ausfälle.

Der kombinierte F1 von 0,6934 ist damit eine **selektive Reparaturquote**, keine allgemeine Aussage „v7 ist besser als v6“.

## 4. Yun-Dev und GLASS

Auf dem 43-Record-Dev-Satz war die Entwicklung deutlich:

| Lauf | Prompt | F1 |
|---|---|---:|
| v1 | ohne Zeitpunktangabe | 0,708 |
| v2 | Zeitpunkt im Prompt | 0,876 |
| v2 frisch | Zeitpunkt im Prompt, Cache-Buster | 0,945 |
| v6 | Zielzeitpunkt mit Rückfall | 0,944 bis 0,965 |

Das ist ein großer Fortschritt, aber der Dev-Satz wurde für die Prompt-Entwicklung mehrfach verwendet. Die 0,96er-Werte sind deshalb eher ein Entwicklungsergebnis als ein unabhängiger Testwert.

Bei GLASS gibt es seit dem 13.11. keinen neuen Lauf. Dort lag der beste F1 bei **0,539** (Qwen 3.5 397B); die Unterschiede zwischen den Modellen waren statistisch nicht belastbar. Für GLASS wurde also **keine neue Verbesserung gemessen**.

## 5. Bewertung

**Ja, wir haben uns verbessert — aber nur auf dem Yun-Benchmark und vor allem bei der Abdeckung.** Konkret: mehr gefundene Zellen, weniger Auslassungen, mehr exakte Records und ein höherer Recall.

**Nein, wir haben noch keinen belastbaren allgemeinen Qualitätsfortschritt nachgewiesen**, weil:

1. v7 nur auf den v6-Fehlzeilen lief,
2. Precision und MAE nicht besser wurden,
3. 38 Prozent der v7-Folgezeilen weiterhin Length-Ausfälle sind,
4. die 186er-Menge für v7 nicht mehr unberührt ist,
5. für GLASS und die anderen Benchmarks kein neuer Vergleichslauf vorliegt.

## 6. Empfehlung

Den kombinierten Wert als „Selektive v7-Reparatur: F1 0,6548 → 0,6934 bei 29 ersetzten Zeilen“ berichten, nicht als neuen Modellbenchmark.

Vor dem nächsten API-Lauf zuerst die 18 verbliebenen Fehlzeilen und die Gold-Konflikte prüfen und einen unberührten Holdout festlegen. Das ist der größere Hebel als ein weiterer Lauf über dieselben 47 Records; ein Netzlauf kostet zusätzlich Guthaben, ohne die Selektionsverzerrung zu beheben.

## 7. Quelldateien

- `public_benchmark/extended_benchmark/analysis/run186_20261115/fallback_eval.json`
- `public_benchmark/extended_benchmark/analysis/run186_20261115/fallback_eval_kombiniert.json`
- `public_benchmark/extended_benchmark/analysis/run186_20261115/fallback_eval_v7.json`
- `public_benchmark/extended_benchmark/analysis/run186_20261115/auswertung186.md`
- `public_benchmark/extended_benchmark/analysis/run186_20261115/folgelauf_v7_und_goldkonflikte.md`
- `public_benchmark/extended_benchmark/runs/ergebnisse_yun_dev.md`
- `public_benchmark/evaluation/multi_model_cross_validation/ergebnisse_gesamt.md`
