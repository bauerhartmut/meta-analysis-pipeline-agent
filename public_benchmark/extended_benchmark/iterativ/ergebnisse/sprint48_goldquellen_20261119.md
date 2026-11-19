# Sprint 48: Herkunft der neun Goldwerte ohne Fundstelle

Grundgesamtheit: die **9** Goldzellen aus den 33 Budgetfaellen, deren Wert weder als `n = ...`-Kopfangabe noch im Fliesstext, in einer Caption oder einer Tabellenzelle mit Gruppen-Kontext vorkommt (`sprint48_kopfangaben_20261119.json`, Herkunft `nicht_gefunden`). Rein lesend: keine Netzaufrufe, keine Predictions geschrieben.

## 1. Befund

- Das `source`-Feld der Goldzelle traegt **nur den Feldnamen** (`intervention_group_size`, `comparator_group_size`), in allen 9 Faellen identisch mit `field`. Eine Fundstelle (Tabelle, Zeile, Seite) steht dort nicht.
- Die Herkunft steht in den Rohdaten (`annotated_rct_dataset.json`, `provenance.source_id`): vier Flags und eine Notiz je Record.
- **5 der 9 Zellen** gehoeren zu Records, die die Rohdaten selbst als Grafik-Tabelle, Abbildung oder unvollstaendig markieren (164, 171, 173, 273).
- **4 der 9 Zellen** (523, 525) sind als vollstaendig markiert, ihr Wert `15` steht aber nur als `0.15` im Markdown - auch dort liefert kein Textpfad den Wert.

## 2. Je Zelle

| Record | Dokument | Feld | Wert | `source` | Grafik-Tabelle | Daten in Abbildung | vollstaendig | Notiz | Urteil |
|---|---|---|---:|---|---|---|---|---|---|
| `yun2024:164` | PMC5062234 | `intervention_group_size` | 21 | `intervention_group_size` | TRUE | FALSE | FALSE | Data found in table in graphic format. | Tabelle nur als Grafik - Textpfad ausgeschlossen |
| `yun2024:164` | PMC5062234 | `comparator_group_size` | 21 | `comparator_group_size` | TRUE | FALSE | FALSE | Data found in table in graphic format. | Tabelle nur als Grafik - Textpfad ausgeschlossen |
| `yun2024:171` | PMC5079604 | `intervention_group_size` | 33 | `intervention_group_size` | FALSE | FALSE | FALSE | SD is not given. | Datensatz unvollstaendig - Wert fehlt im Markdown |
| `yun2024:173` | PMC5079604 | `intervention_group_size` | 33 | `intervention_group_size` | FALSE | TRUE | TRUE | Used percentage to calculate events as binary outcome. | Daten in einer Abbildung - Textpfad ausgeschlossen |
| `yun2024:273` | PMC3214395 | `comparator_group_size` | 30 | `comparator_group_size` | TRUE | FALSE | FALSE | mean and std not given for group 1 and 2 combined | Tabelle nur als Grafik - Textpfad ausgeschlossen |
| `yun2024:523` | PMC5325897 | `intervention_group_size` | 15 | `intervention_group_size` | FALSE | FALSE | TRUE | - | Wert fehlt im Markdown, obwohl der Datensatz vollstaendig ist |
| `yun2024:523` | PMC5325897 | `comparator_group_size` | 15 | `comparator_group_size` | FALSE | FALSE | TRUE | - | Wert fehlt im Markdown, obwohl der Datensatz vollstaendig ist |
| `yun2024:525` | PMC5325897 | `intervention_group_size` | 15 | `intervention_group_size` | FALSE | FALSE | TRUE | - | Wert fehlt im Markdown, obwohl der Datensatz vollstaendig ist |
| `yun2024:525` | PMC5325897 | `comparator_group_size` | 15 | `comparator_group_size` | FALSE | FALSE | TRUE | - | Wert fehlt im Markdown, obwohl der Datensatz vollstaendig ist |

## 3. Einordnung

Fuer **jede** dieser neun Zellen ist ein Textpfad ausgeschlossen: der Wert steht nicht im Markdown, und die Rohdaten begruenden das fuer 164, 173 und 273 mit einer Grafik-Tabelle bzw. einer Abbildung. Bei 171 fehlt die Bezugsgroesse, der Datensatz ist als unvollstaendig markiert. Bei 523 und 525 ist der Datensatz vollstaendig, die `15` fehlt aber trotzdem - das ist ein Befund zur Datenquelle (PDF-Layout oder Markdown-Verlust), nicht zum Prompt.

Fuer die Entscheidung heisst das: Diese neun Zellen senken die Obergrenze jeder Prompt-Variante und duerfen nicht als Prompt-Luecke gezaehlt werden. Die betroffenen Records bleiben Ausfall, ohne dass ein Nachzug sie heilen kann.

## 4. Warum die 15 bei 523/525 fehlt

Beide Records teilen das Dokument `PMC5325897`. Die 15 steht nirgends gedruckt; sie ist aus dem Text und der Baseline-Tabelle ableitbar:

- Text: "30 emergency medicine residents with the mean age of 36.63 ± 30.30 years were allocated to two equal groups (56.7% male)"
- Tabelle 1, Male: 9 und 8
- Tabelle 1, Female: 6 und 7
- Summe je Gruppe: 15 und 15; 30 / 2 = 15

Die Prozentwerte in der Tabelle (60/40 und 53,3/46,7) bestaetigen den Nenner 15. Ein Textpfad muesste die Groesse also rechnen (Summe der Geschlechter oder 30/2), nicht lesen; deshalb fehlt sie im Markdown, obwohl der Datensatz als vollstaendig markiert ist.

## 5. Grenzen

- Die Flags sind Selbstauskuenfte des Datensatzes, keine Nachpruefung am PDF. `is_data_complete = TRUE` schliesst einen Markdown-Verlust nicht aus (523/525).
- Geprueft ist das Markdown, das der P5-Prompt liest; eine andere Quelle fuer Tabelleninhalt (PDF, XML) ist damit nicht ausgeschlossen, aber nicht Teil dieses Pfads.
