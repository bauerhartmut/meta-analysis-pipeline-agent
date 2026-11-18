# Table Decomposition & Reconstruction: Benchmarkbericht

Erzeugt am 2026-11-18 10:00 UTC aus den unten genannten Artefakten. Alle Zahlen sind aus diesen Dateien gelesen, keine ist geschaetzt.

## Auswahl

| Feld | Wert |
|---|---|
| Split | test |
| Tabellen | 60 |
| Records | 59 |
| Dokumente | 31 |
| Kandidaten | 608 |
| Gold erreichbar (Summe je Tabelle) | 95 |
| Records-Hash | c22ed3fb42dbaaff |
| eingefroren | ja |

| Schicht | Tabellen |
|---|---|
| mehrzeitpunkt | 37 |
| mehrstufiger_kopf | 36 |
| fussnoten | 35 |
| mittel | 19 |
| sehr_komplex | 19 |
| einfach | 14 |
| komplex | 8 |
| komplexe_pdf | 8 |
| mehrarm | 8 |

## Struktur- und Aufwandsvergleich (ohne Modellaufruf)

| Var | Verfahren | Records | Tabellen | Einheiten/Record | Zeichen/Record | Zeichen/Einheit | Tokens ges. (Sch.) | Gold erreichbar (Vereinigung) | strukturell komplett | Prueffeheler | Warnungen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Full-Table Extraction | 59 | 60 | 1,0 | 5744,6 | 5648,9 | 84.733 | 95 | 60/60 | 0 | 79 |
| B | Vertical Decomposition | 59 | 60 | 2,8 | 10700,2 | 3803,1 | 157.828 | 95 | 60/60 | 0 | 41 |
| C | Horizontal Decomposition | 59 | 60 | 6,3 | 22529,3 | 3554,1 | 332.307 | 95 | 60/60 | 0 | 125 |
| D | Bidirectional Decomposition | 59 | 60 | 8,5 | 29876,4 | 3504,4 | 440.677 | 95 | 60/60 | 0 | 166 |
| E | Adaptive Recursive Decomposition | 59 | 60 | 5,0 | 20018,9 | 4044,9 | 295.279 | 95 | 60/60 | 0 | 161 |

`Tok. (Sch.)` ist eine Schaetzung aus Prompt-Zeichen / 4 und als solche markiert; sie ersetzt keine gemessene Tokenzahl.

## Modellvergleich

Kein Modelllauf vorhanden. Precision, Recall, F1, Exact Match und Kosten pro richtiger Zelle sind daher **nicht gemessen**; der Strukturvergleich oben belegt nur, dass die Zerlegung den Kontext vollstaendig mitfuehrt und wie viele Aufrufe sie kostet.

## Grenzen

- Ein Modellkonsens zwischen Zeilen- und Spaltenlesung ist ein Hinweis, kein Beweis; die Pruefung gegen die Quelle bleibt menschlich.
- `gold_reachable` ist die Obergrenze des Tabellenpfads, keine Modellleistung: Goldzellen, deren Feld eine Spalte der Tabelle traegt.
- Der Weg von der Zelle zum Arm ist eine deterministische Header- und Kontextzuordnung. Wo sie keinen Arm belegt, bleibt die Spalte ohne Feld und geht nicht in die Bewertung ein.
