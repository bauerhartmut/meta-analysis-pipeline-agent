# Table Decomposition & Reconstruction: Benchmarkbericht

Erzeugt am 2026-11-18 09:50 UTC aus den unten genannten Artefakten. Alle Zahlen sind aus diesen Dateien gelesen, keine ist geschaetzt.

## Auswahl

| Feld | Wert |
|---|---|
| Split | test |
| Tabellen | 60 |
| Records | 58 |
| Dokumente | 31 |
| Kandidaten | 537 |
| Gold erreichbar (Summe je Tabelle) | 79 |
| Records-Hash | c22ed3fb42dbaaff |
| eingefroren | ja |

| Schicht | Tabellen |
|---|---|
| mehrstufiger_kopf | 34 |
| mehrzeitpunkt | 32 |
| fussnoten | 32 |
| mittel | 19 |
| sehr_komplex | 19 |
| einfach | 17 |
| komplexe_pdf | 9 |
| mehrarm | 8 |
| komplex | 5 |

## Struktur- und Aufwandsvergleich (ohne Modellaufruf)

| Var | Verfahren | Records | Tabellen | Einheiten/Record | Zeichen/Record | Zeichen/Einheit | Tokens ges. (Sch.) | Gold erreichbar (Vereinigung) | strukturell komplett | Prueffeheler | Warnungen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Full-Table Extraction | 58 | 60 | 1,0 | 5598,0 | 5411,4 | 81.171 | 76 | 60/60 | 0 | 21 |
| B | Vertical Decomposition | 58 | 60 | 2,4 | 9056,9 | 3779,1 | 131.325 | 76 | 60/60 | 0 | 0 |
| C | Horizontal Decomposition | 58 | 60 | 6,6 | 22127,6 | 3350,9 | 320.851 | 76 | 60/60 | 0 | 67 |
| D | Bidirectional Decomposition | 58 | 60 | 7,8 | 27041,7 | 3447,1 | 392.104 | 76 | 60/60 | 0 | 67 |
| E | Adaptive Recursive Decomposition | 58 | 60 | 4,3 | 17462,2 | 4083,9 | 253.202 | 76 | 60/60 | 0 | 59 |

`Tok. (Sch.)` ist eine Schaetzung aus Prompt-Zeichen / 4 und als solche markiert; sie ersetzt keine gemessene Tokenzahl.

## Modellvergleich

Kein Modelllauf vorhanden. Precision, Recall, F1, Exact Match und Kosten pro richtiger Zelle sind daher **nicht gemessen**; der Strukturvergleich oben belegt nur, dass die Zerlegung den Kontext vollstaendig mitfuehrt und wie viele Aufrufe sie kostet.

## Grenzen

- Ein Modellkonsens zwischen Zeilen- und Spaltenlesung ist ein Hinweis, kein Beweis; die Pruefung gegen die Quelle bleibt menschlich.
- `gold_reachable` ist die Obergrenze des Tabellenpfads, keine Modellleistung: Goldzellen, deren Feld eine Spalte der Tabelle traegt.
- Der Weg von der Zelle zum Arm ist eine deterministische Header- und Kontextzuordnung. Wo sie keinen Arm belegt, bleibt die Spalte ohne Feld und geht nicht in die Bewertung ein.
