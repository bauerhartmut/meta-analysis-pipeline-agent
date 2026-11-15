# Auswertung des 186er-Laufs (15.11.2026)

Run-ID `yun_test186_v6_20261115`, Modell `glm`, Prompt `v6_target_fallback`,
`--workers 3`. Drei Abschnitte in einer Ergebnisdatei: 18 Zeilen aus dem ersten
Anlauf (vor dem Schema-Zusatz), 10 Zeilen aus der Fortsetzung mit 24.000 Token,
158 Zeilen mit `--max-tokens 16000`. Rohdaten:
`runs/yun_test186_v6_20261115/predictions.jsonl` (186 Zeilen),
`analysis/run186_20261115/fallback_eval.json`.

## 1. Lauf und Kosten

| Abschnitt | Records | Tokens | je Record |
|---|---|---|---|
| 1 (Altlauf, ohne `fehlerklasse`) | 18 | 347.204 | 19.289 |
| 2 (Fortsetzung, 24.000 max) | 10 | 145.364 | 14.536 |
| 3 (Fortsetzung, 16.000 max) | 158 | 1.220.571 | 7.726 |
| **gesamt** | **186** | **1.713.139** | **9.210** |

Damit ist der Lauf bei 143 % der ursprünglich gesetzten 1,2-Mio-Grenze. Die
Umstellung auf 16.000 Token senkte die Kosten je Record um 47 % gegenüber
Abschnitt 2 (14.536 → 7.726).

## 2. Fehlerquote

| Klasse | Zeilen | Anteil an 186 |
|---|---|---|
| `ok` (Zellen vorhanden) | 131 | 70,4 % |
| `ok`, aber `keine_verwertbaren_zellen` | 8 | 4,3 % |
| `length_ohne_ergebnis` | **47** | **25,3 %** |
| `json_kaputt` | **0** | 0 % |

Auf die 168 Zeilen mit dem neuen Schema bezogen: **47 von 168 = 28,0 %**
Length-Fehler, kein JSON-Fehler. Die drei leeren Zeilen des Altlaufs
(`yun2024:159`, `79`, `114`) sind 159/79/114 aus Abschnitt 1 und tragen kein
`fehlerklasse`-Feld; sie fehlen in der Zählung oben nicht, weil sie zusätzlich
zur Klasse „ok ohne Zellen" zählen — sie sind in Wahrheit Length-Ausfälle mit
24.000 + 32.000 Tokens.

Length-Retries gibt es seit dem Fix **keine mehr**: In den 168 Zeilen mit neuem
Schema ist `retried` nirgends gesetzt. Die zwei Retries mit `retry_grund =
"length"` in der Datei (`yun2024:75`, `yun2024:111`) stammen aus dem Altlauf und
haben damals noch funktioniert (6 Zellen nach 14.323 bzw. 18.226 Tokens).

## 3. Length-Fehler im Detail

* **Textlänge ist nicht die Ursache:** 23 von 98 Records mit Text unter 15.000
  Zeichen scheitern, 24 von 88 mit 15.000 Zeichen und mehr. Die kürzeste
  Fehlzeile hat 2.999 Zeichen.
* **Kostenanteil:** 46 % aller Completion-Tokens gingen in Length-Fehlzeilen
  (Abschnitt 3: 42 × 16.000 = 672.000 von 1.220.571).
* **Goldverlust:** In den 47 Fehlzeilen liegen **133 von 566 Goldzellen (23,5 %)**.
* **Textkürzung bei 45.000 Zeichen** betrifft 5 Texte und ist damit nicht die
  Erklärung.

## 4. Zeitpunkte: zieltreu, Rückfall, unklar

| Klasse | Zellen | richtig | falsch | ohne Goldwert | Precision |
|---|---|---|---|---|---|
| zieltreu | 352 | 263 | 11 | 78 | **0,9599** |
| Rückfall | 139 | 77 | 18 | 44 | **0,8105** |
| unklar (kein belegbarer Zeitpunkt) | 12 | – | – | – | – |
| ohne Zeitpunkt / ohne Ziel | 0 | – | – | – | – |
| **Summe** | **503** | | | | |

**491 von 503 Zellen (97,6 %) tragen einen belegten Zeitpunkt**, nur 12 bleiben
unklar (2,1 %) — gegenüber 66 von 78 (84,6 %) in der Teilmenge von 28 Zeilen.
Die Normalisierung greift also über den ganzen Lauf.

Die Rückfallzellen sind mehrheitlich richtig (77 von 95 bewertbaren), aber
messbar schlechter als die zieltreuen (0,81 gegen 0,96). Die Zeitdistanz der
Rückfälle liegt im Median bei 2,76 Monaten (nur 6 Fälle bestimmbar).

## 5. Metriken (`evaluate_fallback.py`, Zellen gegen Gold)

| Kennzahl | Wert | Bezug |
|---|---|---|
| Zell-F1 | **0,6548** | 350 Treffer von 566 Gold- und 503 vorhergesagten Zellen |
| Recall | 0,6184 | 350 / 566 |
| Precision | 0,6958 | 350 / 503 |
| MAE | **0,3796** | bei `mae_coverage = 0,6731` (381 von 566 Paaren) |
| exakte Records | 73 von 186 | 39,25 % |
| Auslassungen | 197 Zellen | 34,81 % |

Der Recall ist der schwächste Wert und fast vollständig eine Folge der
Length-Ausfälle: Ohne die 47 Fehlzeilen blieben 433 bewertbare Goldzellen, von
denen 350 getroffen sind (**80,8 %**). Precision und MAE sind davon unberührt.

Verzerrung: 133 der 197 Auslassungen stammen aus Fehlzeilen; die restlichen 64
sind echte Auslassungen in bearbeiteten Records.

Je Feld: Gruppengrößen werden zuverlässig gefunden, wenn die Zelle kommt
(Precision 0,93–0,97), aber nur zu 63–64 % (Recall). Mittelwerte und
Streuungen liegen bei Recall 0,52–0,63 und Precision 0,45–0,46 — dort schlägt
die Rückfallregel durch: Eine Zelle am falschen Zeitpunkt zählt als
Fehlvorhersage, auch wenn die Zahl stimmt.

## 6. Studienarme

| Kennzahl | Wert |
|---|---|
| Records mit unterschiedlichen Zeitpunkten je Arm (`arme_gemischt`) | **7** |
| davon `yun2024:75`, `76`, `78`, `80`, `81`, `149`, `150` | |
| Records mit vertauschten Armen (`arm_swap`) | 4 von 188 bewertbaren (2,13 %) |

Die sieben gemischten Records liegen auffällig gehäuft: fünf davon stammen aus
derselben Studie (`75`, `76`, `78`, `80`, `81`), zwei aus einer zweiten
(`149`, `150`). Das ist kein Streufehler über den Korpus, sondern ein
Tabellenmuster: In diesen Artikeln steht der Komparator in einem eigenen Block,
und die Rückfallregel greift dann je Feld unterschiedlich.

`yun2024:75` ist zusätzlich ein **Gold-Konflikt** und ab jetzt in
`analyze_errors.GEPRUEFTE_FAELLE` als Klasse 5 eingetragen
(`analysis/yun2024_75_gold_conflict.md`): Gold paart palmvitee-Baseline (11,97)
mit palmvitee-Woche-24 (13,72) und führt die palmvitee-Gruppe (n = 29) als
Komparator, obwohl der Placebo-Arm (n = 27) bei Woche 24 den Wert 11,00 trägt.
Seine vier Zellen sind unter den 12 `unklar`-Fällen.

## 7. Bewertung

* **Stabilisierung wirkt:** Kein Length-Retry mehr, kein JSON-Fehler, 97,6 %
  belegte Zeitpunkte, Fortsetzen ohne Doppelverarbeitung.
* **Der Ausfall selbst bleibt:** 28 % der Records liefern nichts, und das trifft
  ein Viertel aller Goldzellen. Die 16.000-Token-Grenze hat das nur verbilligt.
* **Der Lauf ist damit vollständig, aber nicht kosteneffizient:** Die 131 Zeilen
  mit Zellen kosteten 729.543 Token und lieferten alle 350 Treffer; die 55 Zeilen
  ohne Zellen kosteten 983.596 Token und lieferten keinen.
* **Armzuordnung ist systematisch auffällig**, nicht zufällig: sieben Records,
  zwei Studien, ein Gold-Konflikt.

## 8. Grenzen

* Die 18 Altzeilen haben kein `fehlerklasse`-Feld; Fehlerzahlen sind deshalb
  zusätzlich auf die 168 neuen Zeilen bezogen.
* `mae_coverage` 0,6731 heißt: MAE gilt für zwei Drittel der Goldzellen, nicht
  für den ganzen Teilsatz.
* `arm_swap` (4 Records) und `arme_gemischt` (7 Records) messen Verschiedenes:
  Tausch der Werte zwischen den Armen gegenüber abweichenden Zeitpunkten.
* Ein Record ohne Zellen kann im Artikel trotzdem korrekt „nicht berichtet"
  sein (`keine_verwertbaren_zellen`, 8 Fälle); die sind nicht geprüft.

## 9. Empfehlung

**Vor der zweiten Kohorte den Length-Ausfall angehen, nicht die Kosten.**
Konkret: einen Testlauf über die 20 kürzesten Fehlzeilen mit dem Zusatz „return
the JSON object first, no reasoning" in einer eigenen Run-ID. Begründung: Der
Ausfall kostet 23,5 % der Goldzellen und ist die einzige Ursache, die Recall
(0,62 gegen 0,81 ohne Fehlzeilen) und exakte Records (39 %) dominiert; die
Kostenfrage ist mit 7.726 Tokens je Record bereits gelöst. Die 76 Records der
zweiten Kohorte sollten erst starten, wenn die Fehlerquote unter 10 % liegt.
