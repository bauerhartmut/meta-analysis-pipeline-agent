# v7-Folgelauf über die 47 Length-Fehlzeilen und Aufnahme der Gold-Konflikte

Datum 15.11.2026. Run-ID Folgelauf `yun_test186_v7_folgelauf_20261116`,
zusammengeführt als `yun_test186_kombiniert_20261116`. Modell `glm`,
`--cell-timepoint --target-fallback --max-tokens 19000 --quelle v7_folgelauf`,
drei Threads, 47 Aufträge.

## 1. Folgelauf

| Kennzahl | Wert |
|---|---|
| Records | 47 (genau die `length_ohne_ergebnis` des v6-Laufs) |
| Tokens | **610.540** (12.990 je Record) |
| gültig mit Zellen | 23 |
| gültig, aber leere Zellenliste | 6 |
| erneut `length` | **18** (38,3 %) |
| Zellen | 79 |
| Header wörtlich belegt | 22 von 23 Antworten mit Zellen |
| `fallback = true` | 6 |

Erwartet waren nach dem Pilot ≈ 17 % Ausfälle; tatsächlich blieben 38,3 %. Der
Pilot über sechs Records war also optimistisch — er bestand aus den *kürzesten*
und *längsten* Artikeln und nicht aus einer Zufallsstichprobe.

## 2. Kombinierte Auswertung (186 Records, beide Quellen getrennt)

Regel der Zusammenführung: Der v6-Lauf bleibt die Grundlage; ein Folgelauf-Record
ersetzt ihn nur, wenn er Zellen liefert oder gültiges JSON ohne Ausfall. 29
Records kamen aus dem Folgelauf, 18 Folgelauf-Ausfälle wurden verworfen.

| Kennzahl | v6 allein | kombiniert |
|---|---|---|
| Cell-F1 | 0,6548 | **0,6934** |
| Recall | 0,6184 | **0,7032** |
| Precision | 0,6958 | 0,6838 |
| MAE (bei Coverage) | 0,3796 (0,6731) | **1,6303 (0,7862)** |
| Paare in der MAE | 381 von 566 | **445 von 566** |
| exakte Records | 73 (39,3 %) | **79 (42,5 %)** |
| Auslassungen | 197 (34,8 %) | **137 (24,2 %)** |

Je Quelle:

| Quelle | Records | Zellen | richtig | falsch | Precision | Auslassungen |
|---|---|---|---|---|---|---|
| `v6_hauptlauf` | 157 | 491 | 340 | 29 | **0,9214** | 110 |
| `v7_folgelauf` | 29 | 75 | 44 | 16 | **0,7333** | 27 |

Die 18 verworfenen Folgelauf-Ausfälle zählen in der zweiten Zeile als
`v6_hauptlauf`, weil dort die ursprüngliche Fehlzeile steht — deshalb 157 statt
168 Records in dieser Quelle.

## 3. Warum die MAE steigt, ohne dass die Extraktion schlechter wird

Die MAE über alle Quellen mischt Skalen: Ein einziges Paar dominiert.

| Quelle | Paare | exakt | MAE | Median-Fehler | größter Fehler |
|---|---|---|---|---|---|
| `v6_hauptlauf` | 381 | 350 | 0,380 | 0,53 | 35,0 |
| `v7_folgelauf` | 64 | 48 | 9,076 | 4,00 | **305,0** |

Der größte Einzelfehler ist `yun2024:151 intervention_mean`: Modell 12.202 gegen
Gold 11.897 (Differenz 305). Allein dieses Paar trägt 4,77 der 9,08 MAE der
Folgelauf-Zellen. Die neu gewonnenen Records enthalten also großskalige
Outcomes, für die eine absolute MAE nicht vergleichbar ist. Aussagekräftiger
ist der Median-Fehler: 0,53 gegen 4,00 — die v7-Zellen sind ungenauer, aber sie
existieren, wo vorher nichts war.

## 4. Zeitpunkte und Arme

* Belegstufen kombiniert: `gedruckt` 520, `artikel` 46, `unklar` 16 Zellen;
  Treffer belegt 384, kein Treffer stützt sich allein auf das Ziel.
* Rückfallquote als Intervall: **28,4 % bis 31,1 %** (v6 allein: 27,6–30,0 %).
* Arme: `arm_konsistent` 179, `arm_gemischt_gold_bestaetigt` **5**,
  `arm_gemischt_gold_kandidat` 1, `arm_gemischt_modell` 1.
* Alle 47 Folgelauf-Antworten sind armkonsistent — das v7-Schema mit einem
  Zeitpunkt je Antwort verhindert die Mischung strukturell, nicht durch Prompt.

## 5. Gold-Konflikte: vier weitere Records aufgenommen

`yun2024:76`, `:78`, `:80` und `:81` zeigen dasselbe Muster wie `:75`: Gold
paart Baseline und Woche 24 **derselben Spalte** der Tabelle in PMC3546023 und
führt im Komparator dieselbe Gruppengröße wie im Interventionsarm (n = 29 bzw.
n = 30, Placebo wäre 27 bzw. 28). Je Record sind Mittelwert und Streuung beider
Arme als Klasse 5 mit Zeilenangabe eingetragen (`analyze_errors.GEPRUEFTE_FAELLE`,
jetzt 28 Einträge). **Gold bleibt unverändert**; die vier Records zählen damit
in der Armtriage als bestätigte Konflikte statt als Modellfehler.

`yun2024:149` bleibt Kandidat (Goldzahlen in einer Zeile, Komparator nur
präoperativ berichtet), `yun2024:150` bleibt Modellfall.

## 6. Grenzen

* Der Folgelauf lief nur über die 47 Fehlzeilen; 18 davon bleiben ohne Ergebnis.
  Die kombinierte Abdeckung ist 154 von 186 Records mit Zellen.
* Zwei Prompt-Fassungen in einem Datensatz: getrennt über `quelle`, aber jede
  Gesamtzahl über beide Quellen ist eine Mischung.
* Die MAE ist über die Quellen hinweg nicht vergleichbar (Abschnitt 3);
  berichtet werden beide Ansichten.
* Die v7-Zellen sind nicht am Artikel nachgeprüft; die Precision 0,7333 stammt
  aus dem Goldvergleich.

## 7. Empfehlung

**Die 18 verbliebenen Fehlzeilen nicht mit v7 wiederholen, sondern die
Gold-Konflikte und die 18 Ausfälle vor der zweiten Kohorte klären.** Begründung:
Der Folgelauf hat 23 Records für 610.000 Tokens gerettet (26.500 je gerettetem
Record) und dabei 16 Fehlpaare mit Median-Fehler 4,0 produziert; ein zweiter
Durchlauf über die 18 Ausfälle würde nach Pilotbefund höchstens ein Drittel
retten und weitere ≈ 340.000 Tokens kosten. Größerer Hebel: die 18 Ausfälle sind
zur Hälfte Records mit Ziel `baseline` und leerer Tabelle — dort ist die
Goldzelle selbst fraglich.
