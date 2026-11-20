# GLM-5.3-Referenz gegen P5: Herkunft, Vergleichbarkeit, Kennzahlen

Stand 20.11.2026. Rein lesende Auswertung vorhandener Predictions. Kein
Modellaufruf, keine Prediction geschrieben, kein Gold und keine eingefrorene
Eingabe verändert.

## Kurzfassung

1. **Der Wert von etwa 0,80 ist kein Gesamtdatensatz-Wert.** Er entsteht auf den
   **559 von 699** Zeilen, die bei GLM 5.3 überhaupt Zellen geliefert haben
   (F1 **0,8088**). Auf allen 699 Zeilen sind es **0,7336** (Logik dieser
   Analyse) bzw. **0,7519** (Logik von `auswerte_yun699.py`).
2. **0,809 und 0,493 sind nicht vergleichbar.** Sie stehen auf **disjunkten**
   Record-Mengen: die 559 Erfolgszeilen und die 103 Records, die bei GLM
   sämtlich mit `length_ohne_ergebnis` abbrachen. Auf den 103 Records hat GLM
   **0 Zellen** und damit 0 TP; P5 hat dort 170 TP.
3. **Der Prompt ist kein Unterschied.** Beide Läufe nutzen dieselbe Fassung
   `v2_timepoint`; das `_cb` im Referenzlauf ist nur ein Cache-Buster
   (`versions.normalisiere_version`).
4. **Die Bewertungslogik erklärt einen kleinen Teil.** Auf identischen
   Predictions liefert die P5-Logik (Feld und Arm, 1:1, Dubletten sind FP)
   F1 0,7336, die Yun-Logik 0,7519 — 1,8 Punkte.
5. **Der eigentliche Hebel ist die Record-Auswahl.** Auf derselben
   Grundgesamtheit ist P5 der Referenz nicht unterlegen, sondern die einzige
   Quelle von Treffern. Der Preis dafür ist eine deutlich niedrigere Precision
   (0,637 gegen 0,818 im Referenzlauf), weil P5 auf schwierigen Records mehr
   Fremd- und Mehrfachzellen liefert.

## 1. Herkunft der Referenzwerte

Im Repository kursieren vier verschiedene GLM-5.3-Zahlen. Sie stammen aus
verschiedenen Läufen und Bewertungsgrundlagen; nur eine davon ist ein
Gesamtdatensatz-Wert.

| Wert | Grundgesamtheit | Budget | Logik | Quelle |
|---|---|---:|---|---|
| **F1 0,8088** (P 0,8181 / R 0,7997) | 559 Zeilen **mit Zellen** von 699 | 8.000 | P5 (Feld+Arm, 1:1) | `p5_wartephase_audit_20261118.md`, `status_20261118.md`, hier exakt nachgerechnet |
| F1 0,8313 (P 0,8675 / R 0,7979) | dieselben 559 Zeilen | 8.000 | Yun-699 | hier nachgerechnet |
| **F1 0,7519** (P 0,8675 / R 0,6635) | **alle 699** | 8.000 | Yun-699 | `glm_699_ergebnis_20261117.md`, `yun699_test_20261117.md` |
| F1 0,7336 (P 0,8181 / R 0,6650) | alle 699 | 8.000 | P5 | hier nachgerechnet |
| F1 0,8369 | 20 Records | 8.000 | Laufbericht | `README.md`, `ergebnisse_komplett_20261116.md` |
| F1 0,7042 | 60 Records | 4.000 | Laufbericht | `public/README.md` |

Die verbreitete Kurzform „GLM erreicht etwa 0,80" bezieht sich auf die erste
Zeile. Sie ist die **günstigste** der vier 699er-Varianten: Sie lässt 37 Zeilen
ohne jede Zelle (36 leere Antworten, 1 kaputtes JSON) und die 103
Budgetabbrüche aus dem Nenner. Das ist dieselbe Auswahl, die auch den
Architekturbericht prägt, dort aber mit anderer Rechnung: „Precision 86,75 %,
Recall 66,35 %" (`docs/table_decomposition_architektur.md`, Abschnitt 1) ist
die **Gesamtdatensatz-Zahl** 1.840 / 281 / 652 auf 2.773 Goldzellen.

## 2. Der Referenzlauf im Detail

| Punkt | Wert |
|---|---|
| Lauf | `public_benchmark/extended_benchmark/runs/yun699_8000_alle_20261117` |
| Auswertungskopie | `runs/glm_auswertung_20261117/predictions.jsonl` (Stand 17.11., 23:13) |
| Zeilen | 699 (ein Modell) |
| Modell | `gwdg/glm-5.3`, Temperatur 0.0 |
| Tokenbudget | 8.000 je Anfrage |
| Prompt | `v2_timepoint` (als `v2_timepoint_cb` protokolliert, Cache-Buster) |
| Gold | 2.773 Zellen aus `yun_full/records/yun699.jsonl` |
| Testmenge | alle 699 Records, kein Split-Filter |
| Bewertung | `yun_full/auswerte_yun699.py`, exakter Zellvergleich ohne Toleranz |
| Code-Stand | letzter Commit davor `8978673` (17.11., 20:55); Ergebnis festgehalten mit `fd83563` (17.11., 23:14) |
| Fehlerbild | 595 `ok`, 103 `length_ohne_ergebnis`, 1 `json_kaputt`; 559 Zeilen mit Zellen |

Der P5-Lauf ist dagegen:

| Punkt | Wert |
|---|---|
| Lauf | `runs/yun699_p5_24000_20261118` |
| Zeilen | 103, eine je Record |
| Modell | `gwdg/glm-5.3`, Temperatur 0.0 |
| Tokenbudget | 24.000 je Anfrage |
| Prompt | `v2_timepoint` (**identische Fassung**) |
| Gold | dieselbe Datei, 423 Zellen auf den 103 Records |
| Testmenge | die 103 Records, die im Referenzlauf `length_ohne_ergebnis` waren |
| Bewertung | `yun_full/werte_p5_aus.py` (Feld+Arm, 1:1) |
| Code-Stand | `f05928a` (18.11., 16:22), Start 19.11. 10:02 |
| Fehlerbild | 70 `ok`, 3 leer, 33 `length_ohne_ergebnis` (Stand nach Nachzug 15:04) |

Damit ist die Testmenge **nicht** dieselbe, und genau das ist der Kern des
Vergleichsproblems: P5 bearbeitet ausschließlich die Records, an denen die
Referenz gescheitert ist.

## 3. Bewertungslogik beider Seiten

Beide Seiten vergleichen Zellen gegen Gold, definieren TP/FP/FN aber
unterschiedlich.

| Regel | `auswerte_yun699.py` (Referenz) | `werte_p5_aus.py` (P5) |
|---|---|---|
| Schlüssel | nur `field` | `field` **und** `arm` |
| Mehrere Zellen je Schlüssel | erste gewinnt, weitere werden ignoriert | erste passende verbraucht, weitere sind **FP** |
| Zellen ohne Goldannotation | separat (`ohne_gold`), **nicht** in der Precision | **FP** (`fremdschluessel`) |
| Wertvergleich | `< 1e-9` | `< 1e-6` |
| Precision-Nenner | richtig + falsch | TP + FP |
| Records ohne Gold | zählen im Nenner mit | ausgenommen |

Der Arm steckt in beiden Läufen schon im Feldnamen (`intervention_*`,
`comparator_*`); die P5-Prüfung auf `arm` ist deshalb eine zusätzliche
Konsistenzprüfung, kein anderer Zellbegriff.

**Gemessene Wirkung der Logik auf identischen Predictions:**

| Grundgesamtheit | Logik | TP | FP | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| 699 Records (GLM) | P5 | 1.844 | 410 | 929 | 0,8181 | 0,6650 | 0,7336 |
| 699 Records (GLM) | Yun-699 | 1.840 | 281 | 933 | 0,8675 | 0,6635 | 0,7519 |
| 103 Records (P5) | P5 | 170 | 101 | 253 | 0,6273 | 0,4019 | 0,4899 |
| 103 Records (P5) | Yun-699 | 170 | 71 | 253 | 0,7054 | 0,4019 | 0,5120 |

Der Unterschied ist systematisch: Die Yun-Logik ignoriert 115 Zellen ohne
Goldannotation und alle Dubletten und hebt damit die Precision um 4,9 Punkte
(699) bzw. 7,8 Punkte (103). Für einen fairen Vergleich muss dieselbe Logik
auf beiden Seiten laufen — im Folgenden die P5-Logik, weil sie die strengere
und die für P5 dokumentierte ist.

## 4. Vergleichbarkeit

| Frage | Befund |
|---|---|
| Beruhen beide Ergebnisse auf denselben 103 Records? | **Nein.** Die 103 sind die Auswahl von P5; der Referenzwert 0,809 steht auf den 559 übrigen Zeilen. Schnittmenge: 0 Records. |
| Existieren Predictions für dieselben Records? | **Ja**, aber ohne Inhalt: GLM hat auf allen 103 Records 0 Zellen (`length_ohne_ergebnis`). |
| Derselbe Goldstandard? | **Ja**, `yun_full/records/yun699.jsonl`, identische SHA-256 in beiden Auswertungen. |
| Dieselbe Zellvergleichslogik? | **Nein**, siehe Abschnitt 3; hier vereinheitlicht. |
| Derselbe Prompt? | **Ja**, `v2_timepoint`; `_cb` ist nur der Cache-Buster. |
| Dasselbe Budget? | **Nein**, 8.000 gegen 24.000. Das ist Teil der behandlung, nicht der Messung. |

Ein fairer Vergleich ist auf drei Weisen möglich, alle ohne neuen Modellaufruf:

1. **Gleiche Records, gleiche Logik** (103 Records): Referenz 0 TP, P5 170 TP.
2. **Gleiche Records, gleiche Logik, volle Menge** (699): Referenz 0,7336;
   P5 allein deckt nur 103 Records ab und ist dort nicht als
   Gesamtdatensatz-Kennzahl interpretierbar.
3. **Pipeline-Sicht** (Hybrid): Referenz auf den 596 übrigen Records plus P5
   auf den 102 bewertbaren der Auswahl.

## 5. Kennzahlen auf identischer Grundgesamtheit

Die vom Auftrag verlangte Tabelle, gerechnet auf den **103 Records der
P5-Auswahl**, gleiche Logik (Feld+Arm, 1:1), gleiches Gold. `yun2024:653` hat
keine Goldzellen und geht in keine der beiden Zahlen ein.

| Kennzahl | GLM 5.3 | P5 | Differenz |
|---|---:|---:|---:|
| Records | 103 | 103 | 0 |
| Goldzellen | 423 | 423 | 0 |
| TP | 0 | 170 | +170 |
| FP | 0 | 101 | +101 |
| FN | 423 | 253 | −170 |
| Precision | nicht definiert | 0,627 | — |
| Recall | 0,000 | 0,402 | +0,402 |
| F1 | nicht definiert (als 0,000 geführt) | 0,490 | +0,490 |

Ohne den Record ohne Gold (`yun2024:653`, 4 Zellen) sind es für P5
170 / 97 / 253 → Precision **0,6367**, Recall **0,4019**, F1 **0,4928**. Der
dokumentierte Wert 0,493 entsteht aus den gerundeten 0,637 und 0,402; die
exakte Rechnung ergibt 0,4928.

Zur Einordnung die Gesamtmengen:

| Grundgesamtheit | System | TP | FP | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| 699 Records | GLM | 1.844 | 410 | 929 | 0,8181 | 0,6650 | 0,7336 |
| 596 Records (Rest) | GLM | 1.844 | 410 | 506 | 0,8181 | 0,7847 | 0,8010 |
| 559 Zeilen mit Zellen | GLM | 1.844 | 410 | 462 | 0,8181 | 0,7997 | **0,8088** |
| 102 Records (Auswahl) | P5 | 170 | 97 | 253 | 0,6367 | 0,4019 | 0,4928 |

## 6. Zerlegung der Differenz 0,809 gegen 0,493

| Schritt | F1 | Änderung | Ursache |
|---|---:|---:|---|
| Dokumentierter Referenzwert | 0,8088 | — | 559 Zeilen mit Zellen |
| dieselbe Logik, alle 699 | 0,7336 | −0,0752 | 140 Zeilen ohne Antwort fallen in den Nenner |
| dieselbe Logik, nur die 103 | 0,0000 | −0,7336 | GLM liefert dort keine Zelle |
| P5 auf denselben 103 | 0,4928 | +0,4928 | P5 beantwortet 67 der 103 |

Damit ist die Spanne von 0,316 **vollständig** erklärt, ohne eine Aussage über
unterschiedliche Modellqualität: 0,075 stammen aus der Erfolgszeilen-Auswahl,
0,241 aus dem Vergleich auf disjunkten Record-Mengen. Es bleibt kein Rest, der
sich als „GLM ist besser" oder „P5 ist schlechter" lesen ließe.

## 7. Was P5 für die Gesamtpipeline bringt

Hybrid, rein rechnerisch: GLM-Predictions auf den 596 Records außerhalb der
Auswahl plus P5-Predictions auf den 102 bewertbaren Records der Auswahl.
`yun2024:653` bleibt außen vor (keine Goldzellen).

| Variante | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| GLM allein (699) | 1.844 | 410 | 929 | 0,8181 | 0,6650 | 0,7336 |
| Hybrid (596 + 102) | 2.014 | 507 | 759 | 0,7989 | 0,7263 | **0,7609** |
| Differenz | +170 | +97 | −170 | −0,019 | +0,061 | **+0,027** |

Das ist der belastbare Beitrag des P5-Laufs: **+6,1 Punkte Recall und
+2,7 Punkte F1** auf dem Gesamtdatensatz, bezahlt mit 1,9 Punkten Precision.
P5 ersetzt keine funktionierende Extraktion, sondern schließt eine Lücke, in
der die Referenz nichts lieferte.

## 8. Einschränkungen

- Alle Zahlen sind aus vorhandenen Predictions nachgerechnet, nicht aus einem
  neuen Lauf. Die offizielle Bewertung bleibt der geschützte Bewertungslauf.
- Das Gold trägt je Zelle keinen Zeitpunkt. Ein Treffer auf den falschen
  Zeitpunkt ist nicht erkennbar; die Precision ist damit eine **Obergrenze**.
- Der Hybrid ist eine Rechnung, keine Messung: Er unterstellt, dass beide
  Systeme auf ihrer jeweiligen Teilmenge dasselbe leisten wie im Lauf.
- Die 559er-Zahl ist nicht falsch, sondern eng definiert. Sie als
  Gesamtdatensatz-Kennzahl zu zitieren, ist der Fehler.
- Der P5-Lauf hat 33 Records ohne Antwort. Deren 132 Goldzellen sind in jedem
  Recall-Vergleich als FN enthalten; sie sind der größte Einzelposten der
  Fehlmenge (siehe `glm53_p5_recordanalyse_20261120.md`).

## 9. Reproduktion

```
.venv/bin/python public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/vergleiche_20261120.py
```

Quellen der Rechnung: `runs/glm_auswertung_20261117/predictions.jsonl`,
`runs/_lesekopie_20261118/predictions.jsonl` (Gegenprobe, identische Zahlen),
`runs/yun699_p5_24000_20261118/predictions.jsonl`,
`yun_full/records/yun699.jsonl`, `iterativ/ergebnisse/p5_vorbereitung_20261118.json`.
Ergebnis: `vergleich_20261120.json` neben diesem Bericht.
