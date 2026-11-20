# P5-Budgetabbrüche: die 33 Fälle, Schwerpunkt auf den 13 ohne Strukturhypothese

Stand 20.11.2026. Rein lesende Auswertung von
`iterativ/ergebnisse/sprint48_budgetdiagnose.json` (Sprint 48) und den
Predictions des P5-Laufs. Kein Modellaufruf, keine Prediction geschrieben,
kein Gold und keine eingefrorene Eingabe berührt.

Der Bericht aus Sprint 48 (`sprint48_budgetdiagnose.md`) hat die 33 Fälle
erstmals klassifiziert. Dieser Bericht beantwortet die dort offen gebliebene
Frage: **Was ist mit den 13 Fällen, für die keine strukturelle Hypothese
greift?** Die Antwort ist überraschend eindeutig und dreht die
Komplexitätsannahme um.

## Kurzfassung

1. Die 13 Fälle ohne Strukturhypothese sind **nicht** die schwierigen Tabellen.
   Sie haben den **kleinsten** Prompt (Median 7.811 Zeichen gegen 26.295 bei den
   übrigen 20 Abbrüchen und 17.103 bei den Erfolgen) und die **wenigsten**
   Datenzellen (Median 20 gegen 107,5 und 60).
2. Ihr Merkmal ist die **Reasoning-Dichte**: 93.380 Zeichen Reasoning auf 6.811
   Zeichen Text, ein Verhältnis von **13,2** — das 3,5-fache der übrigen
   Abbrüche (3,8) und das 6,3-fache der Erfolge (2,1).
3. Alle 13 haben **keine Tabelle, der der Parser das Zielfeld zuordnet**; 6
   haben überhaupt keinen Tabellentext im Markdown (nur Caption und
   Bildplatzhalter).
4. Die Abbrüche sind **nicht deterministisch**: 5 der 13 haben in einer
   Nachzug-Zeile desselben Referenzlaufs mit 24.000 Tokens Zellen geliefert.
5. Eine Budgeterhöhung ist trotzdem **keine** Lösung: 24.000 war bereits das
   Budget, und 33 Fälle haben es vollständig im Reasoning verbraucht.

## 1. Die 13 Fälle im Detail

| Record | Dokument | Typ | Gold | Reasoning | Prompt | Text | Aufschlag | R/Text | Tab. | Pipe | Dauer s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:119` | PMC4323894 | continuous | 4 | 98.142 | 11.045 | 10.032 | 1.013 | 9,8 | 0 | 0 | 237,8 |
| `yun2024:128` | PMC4493951 | binary | 4 | 90.927 | 8.970 | 7.954 | 1.016 | 11,4 | 2 | 0 | 0,1 |
| `yun2024:152` | PMC5055753 | binary | 4 | 99.665 | 8.788 | 7.782 | 1.006 | 12,8 | 1 | 0 | 0,1 |
| `yun2024:164` | PMC5062234 | continuous | 2 | 99.794 | 4.897 | 3.808 | 1.089 | 26,2 | 0 | 0 | 252,1 |
| `yun2024:273` | PMC3214395 | continuous | 2 | 101.270 | 4.436 | 3.360 | 1.076 | 30,1 | 0 | 0 | 258,6 |
| `yun2024:304` | PMC4357072 | binary | 4 | 95.635 | 6.540 | 5.515 | 1.025 | 17,3 | 0 | 0 | 286,9 |
| `yun2024:356` | PMC5884950 | continuous | 2 | 96.159 | 20.650 | 19.352 | 1.298 | 5,0 | 2 | 0 | 191,5 |
| `yun2024:523` | PMC5325897 | continuous | 6 | 89.661 | 7.811 | 6.811 | 1.000 | 13,2 | 2 | 0 | 240,1 |
| `yun2024:525` | PMC5325897 | continuous | 6 | 89.708 | 7.811 | 6.811 | 1.000 | 13,2 | 2 | 0 | 0,1 |
| `yun2024:557` | PMC3136370 | continuous | 6 | 93.380 | 14.124 | 13.122 | 1.002 | 7,1 | 1 | 0 | 178,3 |
| `yun2024:559` | PMC3136370 | continuous | 6 | 89.528 | 14.139 | 13.122 | 1.017 | 6,8 | 1 | 0 | 0,1 |
| `yun2024:624` | PMC3493722 | binary | 2 | 87.507 | 6.268 | 5.258 | 1.010 | 16,6 | 0 | 0 | 203,9 |
| `yun2024:625` | PMC3493722 | binary | 2 | 82.625 | 6.268 | 5.258 | 1.010 | 15,7 | 0 | 0 | 0,1 |

Spalten: `Tab.` = Tabellen, die der Parser im Dokument findet; `Pipe` =
Pipe-Zeilen im Markdown; `Aufschlag` = Prompt-Zeichen minus Textzeichen (was die
Pipeline dem Quelltext hinzufügt); `R/Text` = Reasoning-Zeichen je Zeichen
Quelltext. Die Dauer ist bei fünf Zeilen mit 0,1 s unbrauchbar (Telemetrie); sie
wird deshalb unten nicht als Merkmal verwendet.

## 2. Vergleich der Gruppen

| Kennzahl | ohne Struktur (13) | mit Struktur (20) | Erfolge (67) |
|---|---:|---:|---:|
| Reasoning-Zeichen, Median | **93.380** | 95.202 | 31.444 |
| Reasoning-Zeichen, Q25 | 89.661 | 89.548 | 16.809 |
| Reasoning-Zeichen, Q75 | 98.142 | 97.231 | 49.626 |
| Prompt-Zeichen, Median | **7.811** | 26.295 | 17.103 |
| Text-Zeichen, Median | **6.811** | 25.267 | 16.081 |
| Prompt-Aufschlag, Median | 1.013 | 1.005 | 1.013 |
| **Reasoning je Textzeichen** | **13,2** | 3,8 | 2,1 |
| Goldzellen, Median | 4 | 4 | 4 |
| Tabellen, Median | **1** | 3 | 3 |
| Datenzellen, Median | **20** | 107,5 | 60 |
| ohne parsebare Tabelle | 6 | 0 | 9 |
| ohne Tabelle mit Zielfeld | **13** | 11 | 51 |
| mit Gruppenkopf | 0 | 11 | 9 |
| binaeres Outcome | 5 | 3 | 19 |
| kontinuierliches Outcome | 8 | 17 | 48 |

Drei Beobachtungen:

- Der **Prompt-Aufschlag ist in allen Gruppen gleich** (rund 1.010 Zeichen).
  Die Pipeline bläht den Prompt nicht auf; Redundanz im Prompt ist als Ursache
  ausgeschlossen.
- Die 13 haben **weniger** Material als die Erfolge, verbrauchen aber **mehr**
  Reasoning je Zeichen. „Zu viel Text" kann die Ursache nicht sein.
- Der einzige durchgehende Unterschied ist das Fehlen eines Tabellenankers:
  13 von 13 ohne Tabelle mit Zielfeld, 6 von 13 ohne Tabellentext.

## 3. Was den Abbruch auslöst

Alle 33 Zeilen enden identisch: `completion_tokens` = 24.000,
`content_chars` = 0, `finish_reason` = `length`, `http_status` = 200,
`parse_error` = `kein_json`, `fehlerklasse` = `budget_im_reasoning`. Das Modell
hat das gesamte Budget im Reasoning verbraucht, ohne mit der Ausgabe zu
beginnen. Ein Zeitpunkt des Abbruchs innerhalb des Reasonings ist nicht
protokolliert; die Predictions tragen nur die Summe.

Für die 13 Fälle kommen drei Erklärungen in Frage, die sich nicht ausschließen:

### H-A: Kein Tabellenanker im kurzen Text

Der Prompt enthält den Artikeltext, aber keine Tabelle, an der sich Zeile,
Arm und Zeitpunkt festmachen lassen. Das Modell sucht im Fließtext nach einer
Struktur, die es nicht gibt, und wiederholt die Suche. Dafür spricht:

- 13 von 13 haben keine Tabelle mit Zielfeld, 6 von 13 gar keinen Tabellentext.
- Der Text ist kurz (Median 6.811 Zeichen), das Reasoning lang (93.380). Das
  Verhältnis 13,2 ist das höchste aller Gruppen.
- `yun2024:273` hat bei 3.360 Zeichen Text 101.270 Zeichen Reasoning — der
  Extremfall: fast keine Quelle, maximaler Suchaufwand.

### H-B: Dokumenteffekt, nicht Recordeffekt

Drei Dokumente stellen je zwei Records: `PMC5325897` (`523`/`525`),
`PMC3136370` (`557`/`559`), `PMC3493722` (`624`/`625`). Die Reasoning-Längen
liegen innerhalb eines Paares sehr nah beieinander (89.661/89.708;
93.380/89.528; 87.507/82.625), obwohl es verschiedene Outcomes sind. Der
Aufwand hängt also am Dokument, nicht an der Frage. Das stützt H-A: derselbe
Text erzeugt dieselbe Suche.

### H-C: Grenzvarianz, nicht harte Grenze

Fünf der 13 haben in der Nachzug-Zeile des Referenzlaufs
(`yun699_8000_alle_20261117`, 18.11.) mit 24.000 Tokens Zellen geliefert:

| Record | Completion-Tokens | Zellen |
|---|---:|---:|
| `yun2024:128` | 16.857 | 4 |
| `yun2024:356` | 24.000 + 801 Repair | 6 |
| `yun2024:557` | 22.137 | 6 |
| `yun2024:559` | 14.534 | 6 |
| `yun2024:624` | 12.805 | 4 |

Gleiches Modell, gleiche Prompt-Fassung, gleiches Budget — einmal Zellen,
einmal 24.000 Tokens Reasoning ohne Ausgabe. Der Abbruch liegt also an der
Grenze und ist nicht deterministisch. Das erklärt auch, warum eine pauschale
Budgeterhöhung nichts sichert: Sie verschiebt die Grenze, nicht das Verhalten.

## 4. Was ausgeschlossen ist

| Vermutung | Befund |
|---|---|
| Zu große Tabellen | Die 13 haben im Median 20 Datenzellen, die Erfolge 60 |
| Zu viele Tabellen | Median 1 gegen 3 bei den Erfolgen |
| Mehrstufige Köpfe / Gruppenköpfe | 0 von 13 haben Gruppenkopf-Zellen |
| Zu langer Prompt | Median 7.811 Zeichen, der kleinste aller Gruppen |
| Prompt-Redundanz | Aufschlag 1.013 Zeichen, identisch zu den Erfolgen |
| Ausgabeumfang | Es gibt keine Ausgabe; `content_chars` = 0 |
| Modell oder Prompt-Fassung | identisch zu den 67 Erfolgen (`v2_timepoint`, `gwdg/glm-5.3`) |

Damit bleibt als gemeinsamer Nenner: **kurzer Text ohne Tabellenanker, langes
Reasoning, Grenznähe.**

## 5. Ansätze zur Senkung des Reasoning-Verbrauchs

Keine pauschale Budgeterhöhung. Alle Vorschläge sind so formuliert, dass sie
ohne Netzlauf prüfbar sind (Strukturplan, Prompt-Bau, Trockenlauf).

1. **Tabellen- oder Fließtextpfad erzwingen.** Wo der Parser eine Tabelle mit
   Zielfeld findet, nur diese Tabelle plus Kopf und Fußnoten senden. Wo er keine
   findet (6 der 13), einen eigenen Fließtext-Pfad mit der Anweisung verwenden,
   die Werte aus dem Ergebnissatz zu ziehen. Erwartung: das Modell muss nicht
   suchen. Prüfbar ohne Modellaufruf an der Prompt-Länge und am Strukturplan.
2. **Antwortgerüst vor dem Reasoning.** Das Modell gibt zuerst das JSON-Gerüst
   mit den erwarteten Feld-/Arm-Schlüsseln aus und füllt es dann. Damit ist vor
   dem Reasoning klar, wie viele Zellen erwartet werden, und ein Abbruch hinter
   lässt wenigstens ein Gerüst. Prüfbar an vorhandenen Antworten: Wie viele der
   67 Erfolge hätten von einem Gerüst profitiert?
3. **Zwei kleine Aufrufe statt einem großen.** Erst Zeile/Zeitpunkt wählen
   (kurzer Prompt, kleine Antwort), dann die Zellen dieser Zeile lesen. Das
   zerlegt genau die Entscheidung, an der P5 scheitert (falsche Zeile,
   falscher Zeitpunkt, falscher Arm). Teurer in Aufrufen, billiger je Aufruf.
4. **Reasoning-Obergrenze, falls das Gateway sie anbietet.** Ein Deckel auf
   Reasoning-Tokens mit erzwungener Ausgabe. Nur mit Freigabe und nur als
   Messung, ob die Qualität hält; ohne Nachweis keine Produktivänderung.
5. **Zerlegung B/E für die 5 Fälle mit vorhandenem Strukturplan.** Der einzige
   Weg, die Zerlegung ohne neue Record-Auswahl gegen den Abbruch zu prüfen
   (`yun2024:30` und vier weitere).

## 6. Versuchsplan (nur Vorschlag, keine Freigabe)

| Schritt | Umfang | Kostenobergrenze | Abbruchkriterium |
|---|---|---|---|
| 1. Prompt-Bau trocken | 13 Records, kein Netz | 0 | Prompt enthält Tabelle + Kopf, kein Volltext |
| 2. Ein Record mit Tabellenanker | `yun2024:30` (Strukturplan vorhanden) | 1 Aufruf, 24.000 | `content_chars` > 0 und `finish_reason` = `stop` |
| 3. Fünf Records mit Tabellenanker | die 5 mit Strukturplan | 5 Aufrufe, 120.000 | mindestens 3 mit Zellen |
| 4. Nur bei Erfolg: die 13 | 13 Aufrufe | 312.000 | F1 auf den 13 ≥ 0,40 |

Schritt 1 ist kostenlos und sofort möglich. Die Schritte 2 bis 4 brauchen eine
ausdrückliche Freigabe nach der Regel „höchstens 2–3 Netläufe je
Untersuchungsfrage".

## 7. Grenzen

- Reasoning-Tokens stehen nicht in den Predictions, nur Zeichen. Die
  Umrechnung ist eine Schätzung (Median 4,0 Zeichen je Token aus 390
  abgeschnittenen Zeilen).
- Der Abbruchzeitpunkt innerhalb des Reasonings ist nicht protokolliert. „Wann"
  im Sinne von „nach wie vielen Tokens" ist nicht messbar, nur „dass".
- Die Zuordnung „ohne Strukturhypothese" stammt aus dem Sprint-48-Bericht
  (H1, H2, H3weit, H6 alle falsch, H7 wahr). Sie ist eine Klassifikation nach
  Merkmalen, keine Ursachenaussage.
- Die Dauer ist bei fünf Zeilen unbrauchbar; sie wird nicht als Merkmal
  verwendet.
- Die 5 Erfolge aus H-C stammen aus einer Nachzug-Zeile mit anderem
  Antwortpfad (Repair bei `yun2024:356`); sie belegen Varianz, nicht
  Reproduzierbarkeit.

## 8. Reproduktion

```
.venv/bin/python public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/budget_20261120.py
```

Quelle: `iterativ/ergebnisse/sprint48_budgetdiagnose.json` (103 Fälle mit
Struktur-, Lauf- und Vorlaufmerkmalen). Ergebnis: `budget_20261120.json` neben
diesem Bericht.
