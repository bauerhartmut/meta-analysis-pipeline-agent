# Alle Ergebnisse: klinische Extraktion auf dem Yun-Benchmark

**Stand:** 16.11.2026  
**Datensatz:** Yun et al. (2024), 699 Records aus 120 Artikeln, Testanteil 656, Goldzellen 2.773  
**Systemstand:** Prompt v7 (`v7_zellzeitpunkt`), Modell `gwdg/glm-5.3`, Temperatur 0.0  

Alle Zahlen dieser Datei sind aus den Rohdaten gerechnet (`ergebnisse_komplett_md.py`), Quellen: `daten/vergleich_20261116.json`, `daten/ausschluss_konflikte.json`, `laeufe/*/predictions.jsonl`, `daten/yun699.jsonl`.

## 1. Kurzfassung

- Referenzlauf (60 Records, 4.000 Tokens): Precision **0,8324**, Recall **0,6102**, F1 **0,7042** (144 richtig, 29 falsch, 63 fehlend von 236 Goldzellen).
- Bestes Modell bei 8.000 Tokens: GLM (F1 0,8369), vor Qwen3.5-397B (0,8169) und Qwen3-30B (0,5950).
- Groesstes Qualitaetsproblem sind Arm-, Populations- und Zeitpunktverwechslungen (21 von 29 falschen Zellen), nicht Halluzination (0 belegte Faelle).
- Ein Prompt-Zusatz zur Quellenangabe (v8) und die Gruppengroessenregel (Experiment B) haben **nicht** geholfen; das hoehere Outputlimit (8.000) hilft (+0,025 F1 bei GLM).

## 2. Datensatz und Stichproben

| Merkmal | Wert |
|---|---:|
| Records gesamt | 699 |
| Artikel | 120 |
| Dev / Test laut Original | 43 / 656 |
| Goldzellen gesamt | 2.773 |
| Stichprobe 60 | 60 Records, 236 Goldzellen |
| Stichprobe 20 | 20 Records, 78 Goldzellen (jeder dritte Record der 60er) |

Die Stichproben sind deterministisch und geschichtet; alle Modellvergleiche nutzen identische Record-Listen.

## 3. Metrikaudit (Korrekturen am frueheren Bericht)

| Kennzahl | frueher berichtet | korrekt | Ursache |
|---|---:|---:|---|
| Precision | 0,8000 | **0,8324** | 7 Zellen ohne Goldannotation wurden als False Positive gezaehlt (144/180 statt 144/173) |
| F1 | 0,6923 | **0,7042** | Folge der Precision-Korrektur |
| Records exakt | 27 | 27 streng / **29 nach Yun** | Yun zaehlt `x == x` auch bei leerem Gold und leerer Antwort als Treffer (2 Records) |

Beide Zaehlweisen werden getrennt ausgewiesen (`exakt_strict`, `exakt_yun`). Abgesichert durch 6 Tests in `tests/test_yun_metriken.py`.

## 4. Referenzlauf: 60 Records, 4.000 Tokens (GLM-5.3, v7)

| Kennzahl | Wert |
|---|---:|
| Precision | 0,8324 |
| Recall | 0,6102 |
| F1 | 0,7042 |
| richtig / falsch / fehlend | 144 / 29 / 63 |
| Zellen ohne Goldannotation | 7 |
| Output-Tokens | 131443 |
| Records exakt (streng / Yun) | 27 / 29 |
| technische Ausfaelle | 6 (length_ohne_ergebnis=6) |

### 4.1 Kennzahlen je Feld

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

Summen: 144 richtig, 29 falsch, 63 fehlend.

## 5. Modellvergleich

### 5.1 Bei 4.000 Tokens (20 Records, erste Messung)

| Lauf | P | R | F1 | richtig/falsch/fehlend | Ausfaelle | Tokens | Zeit |
|---|---:|---:|---:|---|---:|---:|---:|
| GLM / 4k | 0,9818 | 0,6923 | 0,8120 | 54/1/23 | 2 | 35691 | 2 s |
| Qwen3.5-397B / 4k | 1,0000 | 0,4615 | 0,6316 | 36/0/42 | 10 | 65201 | 2750 s |
| Qwen3-30B / 4k | 0,8444 | 0,4872 | 0,6179 | 38/7/33 | 0 | 2249 | 35 s |

Bei 4.000 Tokens war Qwen3.5-397B durch das Limit halbiert (8 Length-Ausfaelle, 2 defektes JSON).

### 5.2 Bei 8.000 Tokens (20 Records, frische Generierung mit Cache-Buster)

| Lauf | P | R | F1 | richtig/falsch/fehlend | Ausfaelle | exakt streng | Tokens | Zeit |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| GLM / 8k | 0,9365 | 0,7564 | 0,8369 | 59/4/15 | 1 | 12/20 | 39047 | 218 s |
| Qwen3.5-397B / 8k | 0,9062 | 0,7436 | 0,8169 | 58/6/14 | 0 | 13/20 | 91720 | 1440 s |
| Qwen3-30B / 8k | 0,8372 | 0,4615 | 0,5950 | 36/7/35 | 0 | 5/20 | 2185 | 29 s |

Wirkung des Limits bei GLM: 4.000 -> 8.000 = Recall +0,064, Precision -0,045, F1 +0,025, Ausfaelle 2 -> 1. Qwen3.5-397B: Ausfaelle 10 -> 0, F1 +0,185. Qwen3-30B: F1 -0,023, holt also nicht auf.

### 5.3 Tokens pro richtiger Zelle (Wirtschaftlichkeit)

| Lauf | F1 | Tokens | Tokens je richtiger Zelle | Zeit |
|---|---:|---:|---:|---:|
| GLM / 8k | 0,8369 | 39047 | 661,8 | 218 s |
| Qwen3.5-397B / 8k | 0,8169 | 91720 | 1581,4 | 1440 s |
| Qwen3-30B / 8k | 0,5950 | 2185 | 60,7 | 29 s |

Geldkosten sind nicht angegeben: fuer den Endpunkt liegt kein Preisaushang vor.

## 6. Experimente

| Experiment | Aenderung | Baseline F1 | Variante F1 | Differenz | Ergebnis |
|---|---|---:|---:|---:|---|
| B | Gruppengroessenregel im Prompt (`--group-size-mode kurz`) | 0,8120 | 0,8000 | -0,0120 | kein Gewinn, Hypothese verworfen |
| C | Quellenangabe vor den Zellen (v8, `--quellenzeile`) | 0,8369 | 0,8088 | -0,0281 | gescheitert: Modell ignoriert den Zusatz und laesst `timepoint` weg |

Nicht gelaufen (kein Budget): Experiment A (Vollstaendigkeitsregel), D (kompakteres Schema), E (Evidenz je Zelle). Diese Ideen sind **unbelegt**.

## 7. Auswertung ohne bestreitbare Goldannotationen

Ausgeschlossen: yun2024:524 (Fliesstext gegen Tabelle), yun2024:447 (zwei verschiedene N), yun2024:669 (Modellwerte im Artikel nicht auffindbar).

| Lauf | mit Konflikten (P / R / F1) | ohne Konflikte (P / R / F1) |
|---|---|---|
| 60 Records, 4000 Tokens | 0,8324 / 0,6102 / 0,7042 | 0,8616 / 0,6284 / 0,7268 |
| 20 Records, 4000 Tokens | 0,9818 / 0,6923 / 0,8120 | 1,0000 / 0,7361 / 0,8480 |

Die bereinigte Zahl ist fuer Vergleiche mit fremden Systemen die fairere Basis.

## 8. Validator

- Datenbasis: 60 Records des Referenzlaufs.
- Harte Warnungen: 15; zusaetzlich 124 weiche Hinweise (fehlende Felder).

| Regel | Anzahl |
|---|---:|
| `weich:feld_fehlt` | 112 |
| `weich:n_fehlt` | 12 |
| `leere_antwort` | 11 |
| `events_ueber_n` | 2 |
| `arme_sehr_ungleich` | 1 |
| `sd_gegen_mittel` | 1 |

- Erkannte falsche Zellen: **2 von 29** (Quote 0,069).
- Warnungen ohne echten Fehler: 1 (Precision der Warnungen 0,6667).

Der Validator faengt damit vor allem strukturelle Probleme (leere Antwort, unmoegliche Ereigniszahlen). Die haeufigen semantischen Fehler erkennt er nicht.

## 9. Fehleranalyse der 29 falschen Zellen

| Klasse | Anzahl |
|---|---:|
| Armzuordnung / Population | 13 |
| Zeitpunkt | 4 |
| Einheit / Skalierung | 4 |
| Tabellenzeile / Spalte | 4 |
| Goldfehler / Quellenkonflikt | 4 |
| Halluzination | 0 |

### 9.1 Am Artikel geprueften Faelle (10)

| Record | PMC | Feld | Gold | Modell | Fundstelle | Klasse | Diagnose | Sicherheit |
|---|---|---|---|---|---|---|---|---|
| yun2024:359 | PMC5971365 | intervention_group_size / comparator_group_size | 720 / 682 | 919 / 922 | Results, Absatz Descriptive data: "n = 919" / "n = 922" | Population | Modell nimmt die randomisierte ITT-Population, Gold die Week-96-Analysepopulation | belegt |
| yun2024:335 | PMC5617873 | alle Armfelder | 45 / 47, -4,7 / -5,2 | 47 / 45, -5,2 / -4,7 | Abstract: "placebo (n = 45) or aripiprazole (n = 47)" | Armzuordnung | Arme vollstaendig vertauscht, inklusive Mittelwerte | belegt |
| yun2024:110 | PMC4319071 | intervention_* und comparator_* | 459 / 2,5 | 456 / 3,3 | Methods: "basic ... n=456), plus ... n=459), and control ... n=434" | Armzuordnung | Modell greift den falschen der beiden Interventionsarme | belegt |
| yun2024:369 | PMC1475568 | intervention_events / comparator_events | 51 / 57 | 86 / 89 | Baseline-Tabelle: "Hypertension, % 89 86" | Einheit/Statistik | Prozentwerte als Ereigniszahlen ausgegeben | belegt |
| yun2024:246 | PMC5571493 | Mittelwerte und SD | 0,74 / 0,83 g/l | 74 / 83 | Ergebnisabschnitt: "0.83 +- 0.05 ... g/l" | Skalierung | g/l stillschweigend in mg/dl umgerechnet (x100) | belegt |
| yun2024:669 | PMC4987981 | Mittelwerte und SD | 200,1 / 181,8 | 53,3 / 1,1 | Tabelle Triglycerides (mg/dl) mit drei Spalten 181,8 / 194,3 / 200,1 | Tabellenzeile | Gold passt zur Tabelle, Modellwerte stehen so nicht im Artikel | belegt |
| yun2024:573 | PMC5541727 | Mittelwerte und SD | -3,7 / 3,4 (24 Monate) | -1,4 / 5,3 (6 Monate) | Tabelle: "6 months --1.4 (5.3)", "24 months --3.7 (3.4)" | Zeitpunkt | 6-Monats-Zeile statt 24-Monats-Zeile | belegt |
| yun2024:118 | PMC4323894 | intervention_group_size | 10 | 19 | Methods: "mild cooling consisted of 10 patients", Kuehlgruppe insgesamt 19 | Population | ganze Kuehlgruppe statt der Subgruppe | belegt |
| yun2024:524 | PMC5325897 | intervention_standard_deviation | 0,46 | 1,09 | Fliesstext "17.73 +- 0.46" gegen Tabelle "Second 17.73 +- 1.09" | Goldfehler/Quellenkonflikt | Paper widerspricht sich; Modell und Gold lesen verschiedene Stellen | belegt |
| yun2024:447 | PMC4879328 | intervention_group_size | 104 | 114 | "intervention, n=114; control, n=114" gegen Tabellenkopf "I; n=104" | Goldfehler/Quellenkonflikt | zwei verschiedene Gruppengroessen im selben Paper | belegt |

### 9.2 Alle falschen Zellen der Vergleichslaeufe

Gold- und Modellwert je Feld; die Fundstelle ist nur bei den oben geprueften Faellen verifiziert (Spalte leer = nicht geprueft, keine Vermutung).

| Lauf | Record | PMC | Feld | Gold | Modell | Fehlerklasse |
|---|---|---|---|---:|---:|---|
| Referenz 60 Records / 4k | yun2024:110 | PMC4319071 | intervention_group_size | 459 | 456 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:110 | PMC4319071 | intervention_mean | 2.5 | 3.3 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:110 | PMC4319071 | intervention_standard_deviation | 2.79 | 2.94 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:110 | PMC4319071 | comparator_mean | 2.84 | 3.19 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:110 | PMC4319071 | comparator_standard_deviation | 2.71 | 2.74 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:118 | PMC4323894 | intervention_group_size | 10 | 19 | Population |
| Referenz 60 Records / 4k | yun2024:246 | PMC5571493 | intervention_mean | 0.74 | 74 | Skalierung |
| Referenz 60 Records / 4k | yun2024:246 | PMC5571493 | intervention_standard_deviation | 0.05 | 5 | Skalierung |
| Referenz 60 Records / 4k | yun2024:246 | PMC5571493 | comparator_mean | 0.83 | 83 | Skalierung |
| Referenz 60 Records / 4k | yun2024:246 | PMC5571493 | comparator_standard_deviation | 0.05 | 5 | Skalierung |
| Referenz 60 Records / 4k | yun2024:335 | PMC5617873 | intervention_group_size | 45 | 47 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:335 | PMC5617873 | intervention_mean | -4.7 | -5.2 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:335 | PMC5617873 | comparator_group_size | 47 | 45 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:335 | PMC5617873 | comparator_mean | -5.2 | -4.7 | Armzuordnung |
| Referenz 60 Records / 4k | yun2024:359 | PMC5971365 | intervention_group_size | 720 | 919 | Population |
| Referenz 60 Records / 4k | yun2024:359 | PMC5971365 | comparator_group_size | 682 | 922 | Population |
| Referenz 60 Records / 4k | yun2024:369 | PMC1475568 | intervention_events | 51 | 86 | Einheit/Statistik |
| Referenz 60 Records / 4k | yun2024:369 | PMC1475568 | comparator_events | 57 | 89 | Einheit/Statistik |
| Referenz 60 Records / 4k | yun2024:447 | PMC4879328 | intervention_group_size | 104 | 114 | Goldfehler/Quellenkonflikt |
| Referenz 60 Records / 4k | yun2024:524 | PMC5325897 | intervention_standard_deviation | 0.46 | 1.09 | Goldfehler/Quellenkonflikt |
| Referenz 60 Records / 4k | yun2024:524 | PMC5325897 | comparator_standard_deviation | 0.47 | 2.29 | Goldfehler/Quellenkonflikt |
| Referenz 60 Records / 4k | yun2024:573 | PMC5541727 | intervention_mean | -3.7 | -1.4 | Zeitpunkt |
| Referenz 60 Records / 4k | yun2024:573 | PMC5541727 | intervention_standard_deviation | 3.4 | 5.3 | Zeitpunkt |
| Referenz 60 Records / 4k | yun2024:573 | PMC5541727 | comparator_mean | -0.8 | -2.7 | Zeitpunkt |
| Referenz 60 Records / 4k | yun2024:573 | PMC5541727 | comparator_standard_deviation | 3.5 | 4.4 | Zeitpunkt |
| Referenz 60 Records / 4k | yun2024:669 | PMC4987981 | intervention_mean | 200.1 | 53.3 | Tabellenzeile |
| Referenz 60 Records / 4k | yun2024:669 | PMC4987981 | intervention_standard_deviation | 55.9 | 36.9 | Tabellenzeile |
| Referenz 60 Records / 4k | yun2024:669 | PMC4987981 | comparator_mean | 181.8 | 1.1 | Tabellenzeile |
| Referenz 60 Records / 4k | yun2024:669 | PMC4987981 | comparator_standard_deviation | 61.3 | 43.3 | Tabellenzeile |
| GLM / 8k | yun2024:30 | PMC3003523 | intervention_mean | 38.1 | 7.8 |  |
| GLM / 8k | yun2024:30 | PMC3003523 | intervention_standard_deviation | 9.5 | 0.4 |  |
| GLM / 8k | yun2024:30 | PMC3003523 | comparator_mean | 31.5 | 1.7 |  |
| GLM / 8k | yun2024:30 | PMC3003523 | comparator_standard_deviation | 7.4 | 0.6 |  |
| Qwen3.5-397B / 8k | yun2024:30 | PMC3003523 | intervention_mean | 38.1 | 6.4 |  |
| Qwen3.5-397B / 8k | yun2024:30 | PMC3003523 | comparator_mean | 31.5 | 2.1 |  |
| Qwen3.5-397B / 8k | yun2024:160 | PMC5056957 | intervention_mean | 0.61 | 0.55 |  |
| Qwen3.5-397B / 8k | yun2024:160 | PMC5056957 | intervention_standard_deviation | 1.8 | 1.11 |  |
| Qwen3.5-397B / 8k | yun2024:160 | PMC5056957 | comparator_mean | 0.66 | 0.61 |  |
| Qwen3.5-397B / 8k | yun2024:160 | PMC5056957 | comparator_standard_deviation | 1.69 | 1.13 |  |
| Qwen3-30B / 8k | yun2024:10 | PMC2363753 | comparator_events | 5 | 10 |  |
| Qwen3-30B / 8k | yun2024:30 | PMC3003523 | intervention_mean | 38.1 | 45.8 |  |
| Qwen3-30B / 8k | yun2024:30 | PMC3003523 | intervention_standard_deviation | 9.5 | 11.4 |  |
| Qwen3-30B / 8k | yun2024:30 | PMC3003523 | comparator_mean | 31.5 | 41.1 |  |
| Qwen3-30B / 8k | yun2024:30 | PMC3003523 | comparator_standard_deviation | 7.4 | 10.8 |  |
| Qwen3-30B / 8k | yun2024:160 | PMC5056957 | intervention_mean | 0.61 | 0.62 |  |
| Qwen3-30B / 8k | yun2024:160 | PMC5056957 | comparator_mean | 0.66 | 0.59 |  |
| GLM v8 Quellenzeile / 8k (Exp. C) | yun2024:10 | PMC2363753 | comparator_events | 5 | 25 |  |
| GLM v8 Quellenzeile / 8k (Exp. C) | yun2024:30 | PMC3003523 | intervention_mean | 38.1 | 6.4 |  |
| GLM v8 Quellenzeile / 8k (Exp. C) | yun2024:30 | PMC3003523 | comparator_mean | 31.5 | 2.1 |  |

## 10. Alle Laeufe (Historie)

Neu gerechnet aus `laeufe/*/predictions.jsonl`; die aelteren Laeufe nutzen teils andere Datensaetze (Dev-Split, 76er-Benchmark) und sind deshalb nicht direkt vergleichbar.

| Lauf | Records | richtig/falsch/fehlend | F1 | Ausfaelle | Tokens | Cache |
|---|---:|---|---:|---:|---:|---:|
| armzeile_291_295_20261116 | 5 | 14/10/6 | 0,5185 | 1 | 27822 | 0 |
| pilot_kurzregel_20261116 | 12 | 23/0/13 | 0,7797 | 2 | 153176 | 2 |
| pilot_len_b_20261116 | 6 | 10/2/9 | 0,6061 | 1 | 68166 | 0 |
| pilot_ohne_regel_20261116 | 12 | 20/0/16 | 0,7143 | 2 | 111291 | 0 |
| pilot_repair_20261116 | 12 | 23/0/13 | 0,7797 | 3 | 161691 | 2 |
| stage_20261115 | 43 | 159/5/6 | 0,9521 | 0 | k. A. | 0 |
| test76_hauptlauf_20261116 | 76 | 105/25/113 | 0,5630 | 5 | 531767 | 0 |
| trockenlauf76_20261116 | 5 | 8/4/10 | 0,4706 | 0 | 53013 | 0 |
| v3_comparator_289_295_20261116 | 7 | 38/4/0 | 0,9048 | 0 | 24768 | 0 |
| version_check_20261115 | 1 | 0/0/0 | - | 0 | 5795 | 0 |
| version_check_v3_20261115 | 1 | 0/0/0 | - | 0 | 2233 | 0 |
| yun20_4000_glm_20261116 | 20 | 54/1/23 | 0,8120 | 2 | 35691 | 20 |
| yun20_4000_glm_gsk_20261116 | 20 | 54/2/22 | 0,8060 | 2 | 32371 | 18 |
| yun20_4000_glm_gskcb_20261116 | 20 | 52/0/26 | 0,8000 | 4 | 29966 | 0 |
| yun20_4000_qwen30_20261116 | 20 | 38/7/33 | 0,6179 | 0 | 2249 | 14 |
| yun20_4000_qwen_20261116 | 20 | 36/0/42 | 0,6316 | 10 | 65201 | 0 |
| yun20_8000_glm_20261116 | 20 | 61/7/10 | 0,8356 | 0 | 51446 | 2 |
| yun20_8000_glm_cb_20261116 | 20 | 59/4/15 | 0,8369 | 1 | 39047 | 0 |
| yun20_8000_glm_v8_20261116 | 20 | 55/3/20 | 0,8088 | 2 | 46783 | 0 |
| yun20_8000_qwen30_cb_20261116 | 20 | 36/7/35 | 0,5950 | 0 | 2185 | 11 |
| yun20_8000_qwen_cb_20261116 | 20 | 58/6/14 | 0,8169 | 0 | 91720 | 0 |
| yun60_8000_glm_20261116 | 2 | 4/0/4 | 0,6667 | 0 | 8199 | 0 |
| yun699_test60_20261116 | 60 | 144/29/63 | 0,7042 | 6 | 131443 | 0 |
| yun699_trockenlauf_20261116 | 5 | 12/2/12 | 0,6000 | 1 | 21869 | 0 |
| yun_dev_20261114 | 86 | 205/93/42 | 0,6426 | 0 | 115829 | 0 |
| yun_dev_diag_20261115 | 1 | 6/0/0 | 1,0000 | 0 | 3728 | 0 |
| yun_dev_diag_24k | 1 | 0/0/6 | - | 0 | 24000 | 0 |
| yun_dev_diag_32k | 2 | 6/0/6 | 0,6667 | 0 | 37015 | 0 |
| yun_dev_fresh_20261115 | 43 | 163/5/2 | 0,9645 | 0 | 68227 | 0 |
| yun_dev_retry_20261115 | 86 | 232/51/57 | 0,7448 | 0 | 108807 | 0 |
| yun_dev_std_20261115 | 43 | 159/5/6 | 0,9521 | 0 | 75164 | 0 |
| yun_dev_tp_20261115 | 86 | 220/51/69 | 0,7201 | 0 | 148064 | 0 |
| yun_dev_v3_20261115 | 43 | 153/5/12 | 0,9329 | 0 | 103483 | 0 |
| yun_dev_v4_20261115 | 43 | 128/40/2 | 0,7574 | 0 | 121271 | 0 |
| yun_dev_v5_20261115 | 43 | 118/1/51 | 0,8166 | 0 | 149941 | 0 |
| yun_dev_v6_20261115 | 43 | 161/1/8 | 0,9699 | 0 | 209276 | 0 |
| yun_dev_v6b_20261115 | 43 | 167/1/2 | 0,9882 | 0 | 162636 | 0 |
| yun_dev_v6c_20261115 | 43 | 167/1/2 | 0,9882 | 0 | 177502 | 0 |
| yun_test186_kombiniert_20261116 | 186 | 398/47/121 | 0,7873 | 18 | 1357130 | 8 |
| yun_test186_pilot_20261115 | 3 | 6/0/0 | 1,0000 | 0 | 15480 | 0 |
| yun_test186_v6_20261115 | 186 | 350/31/185 | 0,7392 | 47 | 1584590 | 6 |
| yun_test186_v7_folgelauf_20261116 | 47 | 48/16/69 | 0,4873 | 18 | 610540 | 6 |
| yun_v8_probe_20261116 | 3 | 14/0/4 | 0,8750 | 0 | 11792 | 0 |

## 11. Belastbarkeit

| Aussage | Status |
|---|---|
| Metrikkorrektur 0,8324 / 0,7042 | belastbar (nachgerechnet, getestet) |
| Fehlerklassen mit Artikelbelegen | belastbar (10 Faelle am Volltext geprueft) |
| Modellrangfolge bei 8.000 Tokens | belastbar fuer 20 Records, breite Konfidenzintervalle |
| Technische Ausfallquoten bei 4.000 Tokens | belastbar (60 bzw. 20 Records) |
| Experiment B und C ohne Wirkung | belastbar fuer diese Stichprobe |
| Zweistufige Architektur, Evidenzverknuepfung | **unbelegt**, nur begruendete Hypothese |
| Vollstaendiger Testsplit (596 Records) | **nicht gemessen** |

## 12. Reproduktion

```
# Kennzahlen aller Laeufe
.venv/bin/python public_benchmark/extended_benchmark/yun_full/vergleich_20261116.py
# diese Datei
.venv/bin/python public_benchmark/extended_benchmark/yun_full/ergebnisse_komplett_md.py
# bereinigte Auswertung
.venv/bin/python public_benchmark/extended_benchmark/yun_full/ausschluss_konflikte.py
# Tests
.venv/bin/python -m pytest public_benchmark/tests -q
```
