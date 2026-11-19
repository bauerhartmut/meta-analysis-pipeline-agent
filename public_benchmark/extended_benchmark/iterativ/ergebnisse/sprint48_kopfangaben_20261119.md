# Sprint 48: Kopfangaben unter den Goldzellen der 33 Budgetfaelle

Grundgesamtheit: **33** `length_ohne_ergebnis`-Records aus `yun699_p5_24000_20261118`, **132** Goldzellen. Rein lesend: keine Netzaufrufe, keine Predictions geschrieben, keine eingefrorene Eingabe beruehrt. Die Entscheidungsvorlage `sprint48_nachzug_entscheidung_20261119.md` bleibt unveraendert.

## 1. Befund

- **62 von 132 Goldzellen** sind Gruppengroessen (`intervention_group_size`, `comparator_group_size`). Nur diese koennen ueberhaupt eine Kopfangabe sein.
- **16 Goldzellen (12,1 % aller Goldzellen) stehen als `n = ...` im Tabellenkopf**: 8 mit belegtem Arm und 8 ohne Arm. Weitere 0 treffen eine Kopfangabe nur mit einem anderen Arm.
- **46 Gruppengroessen haben keine Kopfangabe** im Dokument; 70 Goldzellen sind Messwerte (Mittelwert, Streuung, Ereignisse).
- Ueber die Outcome-Zeile erreichbar sind **10 von 132** Goldzellen; **7** nur ueber eine Kopfangabe und **115** weder ueber Zeile noch Kopfangabe (Fliesstext, andere Tabelle oder im Markdown nicht enthalten).

## 2. Je Record

| Record | Dokument | Gold | Gruppenfeld | Kopf m. Arm | Kopf o. Arm | and. Arm | keine Kopfangabe | ueber Outcome-Zeile | nur Kopf (Wert) | weder/noch |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:159` | PMC5056957 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:30` | PMC3003523 | 6 | 2 | 1 | 1 | 0 | 0 | 0 | 1 | 5 |
| `yun2024:420` | PMC3877023 | 6 | 2 | 1 | 1 | 0 | 0 | 4 | 1 | 1 |
| `yun2024:421` | PMC3877023 | 6 | 2 | 1 | 1 | 0 | 0 | 4 | 1 | 1 |
| `yun2024:446` | PMC4879328 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:451` | PMC4879328 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:52` | PMC3195393 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:523` | PMC5325897 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:525` | PMC5325897 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:557` | PMC3136370 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:559` | PMC3136370 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:673` | PMC4550271 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:674` | PMC4550271 | 6 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 6 |
| `yun2024:119` | PMC4323894 | 4 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 4 |
| `yun2024:128` | PMC4493951 | 4 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 4 |
| `yun2024:152` | PMC5055753 | 4 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 4 |
| `yun2024:171` | PMC5079604 | 4 | 2 | 1 | 0 | 0 | 1 | 0 | 1 | 3 |
| `yun2024:173` | PMC5079604 | 4 | 2 | 1 | 0 | 0 | 1 | 2 | 0 | 2 |
| `yun2024:251` | PMC5614421 | 4 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 4 |
| `yun2024:304` | PMC4357072 | 4 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 4 |
| `yun2024:164` | PMC5062234 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:204` | PMC5380326 | 2 | 2 | 1 | 1 | 0 | 0 | 0 | 1 | 1 |
| `yun2024:252` | PMC5614421 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:273` | PMC3214395 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:356` | PMC5884950 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:582` | PMC3504298 | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 |
| `yun2024:624` | PMC3493722 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `yun2024:625` | PMC3493722 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `yun2024:671` | PMC4550271 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:672` | PMC4550271 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:678` | PMC5777419 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 0 |
| `yun2024:685` | PMC2836833 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| `yun2024:687` | PMC2836833 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 2 |

Spalten: `Kopf m. Arm` = Goldwert steht als `n = ...` im Kopf und der Arm ist belegt; `Kopf o. Arm` = Kopfangabe ohne belegten Arm; `and. Arm` = Wert nur mit anderem Arm; `keine Kopfangabe` = Gruppengroesse, deren Wert nicht als `n = ...` vorkommt; `ueber Outcome-Zeile` = Goldfeld kommt in `reachable_cells` mit einer echten Datenzeile vor (feldweise, wie im Benchmark); `nur Kopf (Wert)` = Wert steht als Kopfangabe mit belegtem Arm und das Feld kommt in keiner Datenzeile vor; `weder/noch` = keiner der beiden Wege fuer diesen Wert.

## 3. Was das fuer den Kopf-Fakten-Prompt bedeutet

Ein Kopf-Fakten-Prompt kann hoechstens die 16 Goldzellen mit belegter oder unbelegter Kopfangabe direkt liefern - das sind 12,1 % der 132 Goldzellen dieser 33 Faelle. Die uebrigen 116 Zellen sind 70 Messwerte und 46 Gruppengroessen ohne `n = ...` im Markdown; fuer sie aendert ein Kopf-Fakten-Prompt nichts.

In den fuenf Planfaellen aus der Diagnose sieht der Hebel so aus (6 von 18 Goldzellen sind Kopfangaben):

| Record | Gold | Gruppenfeld | Kopfangabe | mit Arm | ohne Arm |
|---|---:|---:|---:|---:|---:|
| `yun2024:30` | 6 | 2 | 2 | 1 | 1 |
| `yun2024:252` | 2 | 2 | 0 | 0 | 0 |
| `yun2024:421` | 6 | 2 | 2 | 1 | 1 |
| `yun2024:672` | 2 | 2 | 0 | 0 | 0 |
| `yun2024:678` | 2 | 2 | 2 | 2 | 0 |

Vollstaendig ueber Kopfangaben abgedeckt ist nur `yun2024:678`. Ohne jeden Kopfangaben-Treffer bleiben `yun2024:252`, `yun2024:672`: dort stehen die gesuchten Gruppengroessen nicht als `n = ...` im Markdown.

Der Hebel wirkt damit nur dort, wo die Aufgabe tatsaechlich nach Gruppengroessen fragt. Ob der Prompt das Reasoning entlastet, ist **nicht** gemessen: die Zaehlung zeigt nur die Obergrenze des Ertrags, nicht die Wirkung auf das Budget.

## 4. Grenzen

- Gezaehlt wird gegen `Table.header_facts` des vorhandenen Parsers; eine Kopfangabe, die der Parser nicht erkennt (etwa in einer Bild-Caption), fehlt hier. Die Zahl ist damit eine Untergrenze.
- Der Wertvergleich ist numerisch ueber `value`; dieselbe Zahl an anderer Stelle (etwa eine Stichprobe, die zufaellig `n` entspricht) kann einen Treffer erzeugen. Deshalb ist der Arm mit ausgewiesen.
- `nur Kopf (Wert)` prueft den Wert, nicht nur das Feld: `reachable_cells` fuehrt eine Kopfangabe mit belegtem Arm als `(-1, feld)` und wuerde sonst auch dann einen Treffer melden, wenn die Tabelle eine andere Zahl druckt (`yun2024:252`: Tabelle `*n* = 398`, Gold 402).
- Kopfangaben koennen kursiv gesetzt sein (`*n* = 398`); gezaehlt wird, was `Table.header_facts` liefert, nicht ein eigener Textabgleich.
- Gezaehlt werden **alle Tabellen des Dokuments**. Die Planwerte in `offline_struktur_20261118b/structure.json` beziehen sich auf je eine ausgewaehlte Tabelle und koennen deshalb kleiner sein (etwa `yun2024:421`: Plan 0, dokumentweit 4 Goldzellen ueber die Outcome-Zeile).
