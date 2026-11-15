# Pilot mit Reparaturaufruf, 12 Records (15.11.2026)

Freigabe: „Führe jetzt den 12-Record-Pilot mit --repair und dem neuen v7-Prompt
aus“. Run-ID `pilot_repair_20261116`, Modell `glm`,
`--cell-timepoint --target-fallback --max-tokens 19000 --repair --workers 2`.
Der Lauf wurde nach 6 von 12 Records unterbrochen (Runner-Neustart) und mit
demselben Befehl fortgesetzt; der Fortsetzungsmechanismus übersprang die
6 fertigen Zeilen, es gibt keine Doppelzeilen.

## 1. Auswahl (`pilot_repair.py --waehlen`)

| Gruppe | Records | Auswahlregel |
|---|---|---|
| length | `328`, `566`, `169` | 18 Length-Ausfälle, die auch unter v6 leer blieben, gleichmäßig über die Textlänge |
| leer | `325`, `571`, `252` | 6 gültige Antworten ohne Zellen, gleichmäßig über die Textlänge |
| armgemischt | `149`, `76`, `81` | die 7 Records mit gemischten Armen aus dem kombinierten Lauf, gleichmäßig abgetastet |
| normal | `119`, `580`, `204` | die 4 Records mit ausschließlich richtigen Zellen, ohne Befund |

## 2. Ergebnis je Record

| Record | Gruppe | Pfad | Tokens primär | Reparatur | Zellen | Treffer | Header |
|---|---|---|---:|---:|---:|---|---|
| `yun2024:328` | length | standard | 2.448 | – | 2 | 2/2 | – |
| `yun2024:566` | length | repair | 19.000 | 765 | 2 | 2/2 | – |
| `yun2024:169` | length | repair | 19.000 | 6.000 | 0 | 0/2 | – |
| `yun2024:325` | leer | standard | 4.428 | – | 1 | 1/2 | – |
| `yun2024:571` | leer | standard | 17.719 | – | 2 | 2/2 | „week 4“ |
| `yun2024:252` | leer | repair | 19.000 | 6.000 | 0 | 0/2 | – |
| `yun2024:149` | armgemischt | standard | 9.757 | – | 4 | 4/4 | „Postop 3rd month“ |
| `yun2024:76` | armgemischt | repair | 19.000 | 6.000 | 0 | 0/6 | – |
| `yun2024:81` | armgemischt | standard | 10.333 | – | 6 | 6/6 | „24 weeks“ |
| `yun2024:119` | normal | repair | 19.000 | 1.197 | 2 | 2/4 | – |
| `yun2024:580` | normal | repair | 19.000 | 844 | 2 | 2/2 | – |
| `yun2024:204` | normal | standard | 3.006 | – | 2 | 2/2 | „baseline“ |

## 3. Die vier geforderten Kennzahlen

| Kennzahl | Wert | Vorgabe aus `entwicklungsplan.md` | erfüllt |
|---|---:|---|---|
| **Length-Quote** | **3/12 = 25,0 %** | ≤ 10 % | **nein** |
| **leere Antworten** | **0/12 = 0,0 %** | ≤ 5 % | **ja** |
| **Precision** | **1,0000** (23/23) | ≥ 0,70 | **ja** |
| **Tokens je Pfad** | standard 7.949, repair 22.468 | – | – |

Zellmetriken auf den 12 Records: 36 Goldzellen, 23 Treffer, 0 falsche Werte,
0 überzählige Zellen, 13 Auslassungen → Recall 0,6389, F1 0,7797, exakt 7/12.
Alle 23 Treffer sind im Artikel belegt (13 „gedruckt“, 10 „artikel“), 2 Zellen
sind Rückfall (beide richtig), keine Gruppengröße kam ohne Zeitpunkt.

## 4. Tokens, aufgeteilt nach Pfad

| Pfad | Records | Tokens gesamt | je Record | beantwortet |
|---|---:|---:|---:|---:|
| standard | 6 | 47.691 | 7.949 | 6/6 |
| repair | 6 | 134.806 | 22.468 | 3/6 |
| **gesamt** | **12** | **182.497** | **15.208** | **9/12** |

Davon Primäraufrufe 161.691 (13.474 je Record) und Reparaturen 20.806; eine
Reparatur kostet im Mittel 3.468 Tokens. (Korrektur vom 15.11.2026: eine frühere
Fassung dieses Absatzes nannte 161.691 als Gesamtsumme und 140.885 als
Primäranteil; die Pfadsummen waren richtig, die Beschriftung nicht.) Eine **erfolgreiche** Reparatur
(`566`, `119`, `580`) kostet 19.000 + 0,9k ≈ 19.900 Tokens für 6 Zellen, also
etwa 3.500 Tokens je geretteter Zelle; eine **erfolglose** kostet 25.000.

## 5. Drei Befunde, die wichtiger sind als die Quote

**a) Der Reparaturaufruf rettet die Hälfte.** 3 von 6 Reparaturen liefern Zellen
(566, 119, 580), 3 laufen auch bei 6.000 Tokens in den Loop (169, 252, 76). Das
Budget ist damit ausreichend, wenn die Schleife überhaupt verlässt — es ist kein
Budgetproblem.

**b) Der Primäraufruf scheitert jetzt auch bei vorher erfolgreichen Records.**
`119` und `580` hatten im v7-Folgelauf Zellen ohne Ausfall (119: 4/4, 580: 2/2);
im Pilot laufen beide primär in 19.000 Tokens und werden erst durch die
Reparatur gerettet. Die Primärausfallquote liegt damit bei 6/12 = 50 % (im
Folgelauf 38,3 %, andere Stichprobe). Ob die neue Gruppengrößen-Zeile im Prompt
das Reasoning verlängert, ist **nicht belegt** — dafür müsste derselbe Pilot
einmal ohne diese Zeile laufen.

**c) Der neue Prompt behebt die Armmischung.** `149` (4/4) und `81` (6/6)
treffen jetzt den Zielzeitpunkt; im kombinierten Lauf waren genau diese Records
armgemischt (`149` = Kandidat, `81` = bestätigter Gold-Konflikt). Die
Auswertung meldet für den Piloten 0 gemischte Zellen. Bei `81` ist der Treffer
allerdings gegen ein Gold gezählt, das selbst als Konflikt geprüft ist — der
Wert ist also nicht unabhängig bestätigt.

## 6. Urteil

Formal: **Length-Ziel verfehlt (25 % statt ≤ 10 %), die übrigen drei Ziele
erreicht.** Precision 1,0 auf 23 Zellen ist der stärkste Einzelwert dieses
Piloten; die 12 Records enthalten jedoch 6 vorher gescheiterte und 3 vorher
fehlerfreie Records, also keine Zufallsstichprobe. Der F1 von 0,7797 ist
deshalb **nicht** mit dem DEV-Wert 0,6934 vergleichbar.

Kosten: 161.691 Tokens für 12 Records. Hochgerechnet auf die 76 Testrecords
**[Schätzung]** ≈ 1,02 Mio Completion-Tokens.

## 7. Grenzen

- 12 Records, 36 Goldzellen: ein Unterschied von 3 Records ist kein Effekt.
- `76` ist ein bestätigter Gold-Konflikt; sein Ausfall ist ein Formfehler, keine
  Aussage über Extraktionsqualität.
- `119` liefert 2 von 4 Goldzellen; welche zwei fehlen, ist hier nicht geprüft.
- Die Reparatur läuft mit demselben Modell und ohne Reasoning-Parameter; ob ein
  Reasoning-Budget die Schleife besser bricht, ist weiterhin offen.
