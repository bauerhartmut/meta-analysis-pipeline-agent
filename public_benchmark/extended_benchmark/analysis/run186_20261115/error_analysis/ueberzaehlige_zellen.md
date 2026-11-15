# Die 15 überzähligen Zellen am Artikeltext geprüft (15.11.2026)

Frage: Stehen die Werte im Artikel und gehören sie zum Outcome, oder hat das
Modell sie falsch zugeordnet? Grundlage: `ueberzaehlige_kontext.txt` (erzeugt
von `pruefe_ueberzaehlige.py`, Zitatfenster von ±180 Zeichen). Kein Modellaufruf.

## Ergebnis

| Urteil | Zellen | Records |
|---|---:|---|
| **korrekt, im Gold nicht erfasst** | **7** | 117, 384, 640 |
| falsches Outcome | 2 | 170 |
| Armzuordnung bei drei Armen mehrdeutig | 4 | 597, 606 |
| nicht belegbar (Zahl nicht im Outcome-Kontext) | 2 | 465 |

## Belege je Record

**yun2024:117 — comparator_events = 2 @ 6 months (korrekt)**
„There were 63.2% of patients (12 patients) in cooling group attained good GOS
at 6 months compared with only 15.4% in non-cooling group (2 patients).“
2 von 13 Komparatorpatienten, Gold führt nur `comparator_mean = 15.4`. Die Zelle
ist richtig, das Gold ist unvollständig.

**yun2024:384 — intervention_mean = 80, comparator_mean = 71 @ Final Visit (korrekt)**
„patients in the 'phone calls' group (80%) had better blood pressure control
than those in the 'no phone calls' group (71%)“; Tabelle bestätigt 80/33 und
71/27 bei „Controlled blood pressure“. Outcome ist genau dieser Anteil. Gold
führt nur die Gruppengrößen (60/119).

**yun2024:640 — mean/SD beider Arme @ baseline (korrekt)**
„LDL-Cholesterol (mmol/L) Mean (SD) 4.29 (0.71) 4.61 (0.63) 4,78 (0.65)“ —
Komparator 4,29 (SD 0,71), Intervention 4,61 (SD 0,63) bei Baseline. Alle vier
Zellen sind Textwerte des Outcomes; Gold führt nur die Gruppengrößen.

**yun2024:170 — intervention_events = 5, comparator_events = 4 (falsches Outcome)**
Die Zahlen stammen aus „Hyperglycemia relapse (*n*) 5 4 11“, einer
Verträglichkeitszeile der drei Studienarme. Das Outcome des Records ist
„Cox proportional hazards of failure-free survival“. Falsches Outcome, nicht
fehlendes Gold.

**yun2024:597 und :606 — 12.5 / 10.5 gegen 25.2 @ 12 weeks (mehrdeutig)**
„more patients discontinued due to lack of efficacy in the placebo group than
in the etoricoxib and naproxen group (25.2%, 12.5%, 10.5%, respectively)“.
Alle drei Werte sind Textwerte des Outcomes, aber die Studie hat **drei** Arme:
welcher der beiden Wirkstoffe der „Intervention“-Arm ist, sagt der Record nicht.
Die Werte sind belegt, die Armzuordnung ist nicht entscheidbar.

**yun2024:465 — 3 und 4 @ 24 (nicht belegbar)**
Im Zitatfenster stehen nur Baseline-Werte (CD4, Kalzium, Vitamin D); ein
Triglyceridwert 3 oder 4 zu Woche 24 ist an den Fundstellen nicht zu sehen. Ohne
Tabellenblick bleibt offen, ob die Zahl aus einer Nachbarzeile stammt.

## Was das für die Kennzahlen bedeutet

Bisher wurden alle 15 Zellen als falsch gezählt. Korrigiert man nur die belegten
Fälle, ergibt sich als **Obergrenze** der Genauigkeit:

* Precision ohne die 7 belegten Zellen: 48 / 79 = 0,6076
* Precision, wenn die 7 als richtig zählen: 55 / 79 = **0,6962**

Die 4 mehrdeutigen und 2 nicht belegbaren Zellen bleiben als Fehler gezählt, die
2 falschen ebenso. Der wahre Wert liegt damit zwischen 0,61 und 0,70 — die
bisherige Precision unterschätzt die Extraktionsqualität um bis zu 9 Punkte.

Wichtig: **Das Gold wird nicht geändert.** Die 7 Zellen sind ein Befund für die
nächste Goldpflege, keine stille Korrektur. Ein Gold-Nachtrag würde die
bestehenden Ergebnisse verschieben und ist nur mit neuer, versionierter
Golddatei zulässig.

## Konsequenz für den Entwicklungsplan

Die überzähligen Zellen sind **kein Prioritätsfall** mehr: 7 von 15 sind
korrekt, 2 falsch, 4 strukturell mehrdeutig (Drei-Arm-Studien), 2 offen. Der
Prompt braucht keine „keine zusätzlichen Zellen“-Regel, die hätte 7 richtige
Zellen unterdrückt. Stattdessen gehört die Drei-Arm-Mehrdeutigkeit als
Datenmodellfrage in die Goldpflege: Records mit mehr als zwei Studienarmen
brauchen eine Armzuordnung im Record, nicht im Prompt.
