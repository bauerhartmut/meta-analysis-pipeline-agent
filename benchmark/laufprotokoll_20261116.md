# Yun-Benchmark: Ergebnisse (Stand 16.11.2026)

Gemessen mit dem produktiven Extraktions-Harness (Promptstand v7, Modell
`gwdg/glm-5.3`, Temperatur 0.0) auf dem öffentlichen Yun-Datensatz
(120 RCTs, 699 ICO-Records, 656 Testrecords). Getrennt vom 76-Record-Benchmark;
keine gemeinsamen Kennzahlen. Methodik und Datenherkunft: `yun_benchmark_20261116.md`.

## Was gelaufen ist

| Lauf | Records | Deckel | Tokens | Wanduhr |
|---|---|---:|---:|---:|
| Trockenlauf `yun699_trockenlauf_20261116` | 5 | 19.000 | 24.420 | ~12 min |
| Gestaffelter Testlauf `yun699_test60_20261116` | 60 (geschichtet) | 4.000 | 173.178 | ~15 min |

Die 60 Records sind eine deterministische Stichprobe des Testsplits, geschichtet
nach `outcome_type` × Goldzellenzahl (22 × kontinuierlich-voll, 16 ×
kontinuierlich-2-Zellen, 4 × kontinuierlich-4, 2 × ohne Zelle, 13 × binär-voll,
2 × binär-2, 1 × binär ohne Zelle). Auswahl vor dem Lauf, ohne Blick auf Ausgaben.

## Zellmetriken (60 Records, exakter Vergleich)

| Kennzahl | Wert |
|---|---|
| Goldzellen | 236 |
| richtig | **144** |
| falsch | 29 |
| fehlend (Gold da, Modell schweigt) | 63 |
| Zellen ohne Gold | 7 |
| **Precision** | **0,8000** |
| **Recall** | **0,6102** |
| **F1** | **0,6923** |
| Abdeckung (richtig / Gold) | 0,6102 |
| MAE (173 verglichene Zellen) | 6,2058 |
| Records exakt | 27 / 60 |
| Records teilweise | 20 / 60 |
| Records ohne Treffer | 2 / 60 |
| technische Ausfälle | 6 |
| leere Antworten | 11 |

Zellen ohne Gold zählen nicht als Fehler. Fehlende Extraktionen sind von falschen
getrennt; der Recall ist deshalb die ehrliche Kennzahl für „wie viel der
Annotation holt der Agent überhaupt".

## Yun-Zählweise (Exact / Partial / Unknown)

Nachgebaut nach `evaluation/calculate_metrics.py` des Originalrepos: fehlende
Gold- und Modellzellen gelten als `x`, `x == x` ist ein Treffer; exact = alle
Felder des Tasks stimmen (6 kontinuierlich, 4 binär); partial_k = mindestens k
Treffer.

| Task | n | exact | partial_1 | partial_2 | model_unknowns | reference_unknowns |
|---|---:|---:|---:|---:|---:|---:|
| continuous | 44 | **0,4318** | 0,8864 | 0,8409 | 55 | 85 |
| binary | 16 | **0,6250** | 1,0000 | 0,9375 | 7 | 8 |

Feldtrefferquoten kontinuierlich: `intervention_mean` 0,6364,
`intervention_standard_deviation` 0,7045, `intervention_group_size` 0,6364,
`comparator_mean` 0,6818, `comparator_standard_deviation` 0,7045,
`comparator_group_size` 0,6818. Binär: `intervention_events` 0,8125,
`intervention_group_size` 0,8125, `comparator_events` 0,7500,
`comparator_group_size` 0,8750.

## Vergleich mit den Originalergebnissen

| Metrik | GLM-5.3 (60 Records) | GPT-4 (656 Records) | GPT-3.5 (656) |
|---|---:|---:|---:|
| continuous exact | 0,4318 | 0,4866 | 0,2804 |
| continuous partial_1 | 0,8864 | 0,9216 | 0,8722 |
| binary exact | 0,6250 | 0,6550 | 0,2982 |
| binary partial_1 | 1,0000 | 0,9123 | 0,7485 |

Die Zählweise ist jetzt identisch, die Population nicht: 60 geschichtete statt
656 Records, eine einheitliche v7-Extraktion statt getrennter Task-Prompts und
modellspezifischer Templates, Zeitpunktregel als Text statt keiner Vorgabe, und
ein 4.000-Token-Deckel, den GPT-4 nicht hatte (28 % der Antworten wurden
abgeschnitten). Punkt-Schätzer (SMD/logOR) sind nicht verglichen: dafür bräuchte
es `statsmodels` wie im Original; eine eigene Formel wäre nicht Yun-identisch.

**Lesart:** Auf gleicher Skala liegt GLM-5.3 knapp unter GPT-4 bei
kontinuierlichen Outcomes (Differenz 0,055 exact) und praktisch gleichauf bei
binären (0,030). Der Deckel drückt unser Ergebnis, die Aufgabenstellung kann es in
beide Richtungen verschieben — ein belastbarer Vergleich braucht den vollen
Testsplit ohne Deckel.

## Fehlerbild (29 falsche Zellen)

Schwerpunkt sind **Auslassungen**, nicht Fehlgriffe: 63 fehlende gegen 29 falsche
Zellen.

| Feld | richtig | falsch | fehlend |
|---|---:|---:|---:|
| `intervention_mean` | 15 | 5 | 8 |
| `intervention_standard_deviation` | 10 | 5 | 8 |
| `intervention_group_size` | 36 | 5 | 13 |
| `intervention_events` | 10 | 1 | 2 |
| `comparator_mean` | 15 | 5 | 7 |
| `comparator_standard_deviation` | 10 | 5 | 8 |
| `comparator_group_size` | 39 | 2 | 13 |
| `comparator_events` | 9 | 1 | 4 |

Nach Arm: Intervention 71 richtig / 16 falsch / 31 fehlend, Comparator 73 / 13 /
32 — kein Armunterschied. Nach Typ: kontinuierlich 98 / 26 / 56, binär 46 / 3 / 7;
die Auslassungslast liegt klar bei den kontinuierlichen Outcomes (SD und N).

**Die fünf größten Abweichungen** (MAE 6,21 wird von ihnen getragen):

| Record | Feld | Gold | Modell | Muster |
|---|---|---:|---:|---|
| `yun2024:359` | `comparator_group_size` | 682 | 922 | falsche Kohorte/Gesamtzahl |
| `yun2024:359` | `intervention_group_size` | 720 | 919 | dito |
| `yun2024:669` | `comparator_mean` | 181,8 | 1,1 | Einheiten (mg/dl gegen mmol/l) |
| `yun2024:669` | `intervention_mean` | 200,1 | 53,3 | dito |
| `yun2024:246` | `comparator_mean` | 0,83 | 83 | Skala (Anteil gegen Prozent) |

Zwei Muster, beide aus dem 76er-Benchmark bekannt: Skalen- und
Einheitenverwechslung bei Laborwerten, und Armgrößen aus der falschen Zeile. Am
Artikel nicht nachgeprüft — es sind Kandidaten für eine Quellenprüfung, keine
belegten Goldfehler.

## Technische Ausfälle und Deckel

| | |
|---|---|
| Antworten mit `stop` | 43 / 60 |
| Antworten mit `length` (4.000er Deckel) | 17 / 60 (28 %) |
| davon ohne jede Zelle | 6 |
| leer ohne Fehlerklasse | 5 |
| Median-Antwortzeit | 18,8 s |

Der Deckel hat den 19.000-Token-Ausreißer des Trockenlaufs auf 4.000 gedrückt —
Kostenkontrolle funktioniert —, kostet aber 6 Records vollständig und schneidet
bei 11 weiteren Zellen ab. 4.000 ist für diesen Prompt zu knapp.

## Kosten

| | 60 Records | 596 Records (Hochrechnung) |
|---|---:|---:|
| Tokens | 173.178 | ~1,72 Mio. |
| Wanduhr | ~15 min | ~2,5 h |

Mit 8.000er Deckel: ~2,4 Mio. Tokens, ~3,5 h.

## Grenzen

* 60 von 656 Testrecords, geschichtet — die Kennzahlen sind eine Stichprobe, keine
  Gesamtkennzahl.
* Der 4.000er Deckel verzerrt Recall und Exact-Match nach unten; wie stark, ist
  ohne denselben Lauf mit höherem Deckel nicht bezifferbar.
* Kein Punkt-Schätzer-Vergleich (SMD/logOR), also kein Vergleich der
  meta-analytischen Endpunkte.
* Yun hat kein Zeitpunktfeld; die v7-Zeitpunktvorgabe ist eine Regel, keine
  Annotation, und wird nicht bewertet.
* Fehlende Zellen im Gold sind als `x` behandelt (Yun-Zählweise) — das belohnt
  Übereinstimmung im Schweigen. Die eigene Zählung weist das getrennt aus.

## Nächster Schritt

**Restliche 596 Testrecords mit `--max-tokens 8000` laufen lassen und die
60er-Stichprobe separat ausweisen.** Begründung: Der Deckel ist der einzige
Störfaktor, der sich ohne Methodendiskussion beheben lässt, und er trifft genau
die Kennzahl, die mit GPT-4 verglichen werden soll. Kosten ~2,4 Mio. Tokens in
~3,5 h — kalkulierbar, und danach steht erstmals eine Gesamtkennzahl auf
Yun-Zählweise, die man dem Paper gegenüberstellen kann.

## Artefakte

| Pfad | Inhalt |
|---|---|
| `yun_benchmark_20261116.md` | vollständiger Bericht (Herkunft, Schema, Methodik, alle Läufe) |
| `public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl` | 699 Records, SHA-256 `c22ed3fb…` |
| `…/yun_full/manifest.json` | Quelle, Hashes, Zählungen, Mapping, Anomalien |
| `…/yun_full/stichprobe60.json` | Stichprobe und Schichtung |
| `…/runs/yun699_test60_20261116/predictions.jsonl` | Modellausgaben |
| `…/runs/yun699_test60_20261116/auswertung_yun.json` | Zellmetriken inkl. aller Abweichungen |
| `…/runs/yun699_test60_20261116/yun_metriken.json` | Exact/Partial/Unknown |
| `…/runs/yun699_trockenlauf_20261116/` | Trockenlauf mit fünf Records |

---

**Hinweis zur Reproduzierbarkeit:** Rohläufe, Vergleichsdateien und die
Auswertungsskripte, aus denen diese Zahlen stammen, sind nicht veröffentlicht.
Die Werte sind dokumentierte Messungen mit dieser Einschränkung; Schätzungen sind
im Text als solche gekennzeichnet.
