# Kandidaten-Split der Datenerweiterung (15.11.2026)

Reine Textprüfung, **keine Modellaufrufe**, keine Änderung an Gold, Records oder
Predictions. Werkzeug: `candidate_split.py`.

## Was geprüft wird

Für jede Goldzelle der 407 noch nicht verwendeten Records wird gesucht, ob die
Zahl **wörtlich** im Artikeltext steht — in deutscher und englischer
Schreibweise (Komma/Punkt), mit Minus und Leerzeichen („- 0.7"), mit
Tausendertrennzeichen („1,831") und in den Rundungen 2/1/0 Nachkommastellen.
Ausgegeben werden Variante, Zeichenposition, Region (Kurzfassung/Hauptteil) und
ein Textfenster von 90 Zeichen. Findet sich nichts Wörtliches, prüft das
Werkzeug, ob die Zahl **gerundet** dasteht (eine Nachkommastelle oder Ganzzahl).

## Gegenprobe am Dev-Satz

**170 von 170 Zellen wörtlich belegt**, alle 38 Records mit Goldzellen komplett
(`dev_validation/`; fünf Dev-Records führen keine Zellen). Das deckt sich mit der früheren Sichtprüfung, die 169 von
170 Zellen als wörtlich belegt und eine Zelle (50,6/50,7) als Doppelangabe
geführt hatte: 50,6 steht wörtlich im Ergebnisteil.

## Ergebnis auf den 407 Records

| Kennzahl | Wert |
|---|---|
| Records | 407 |
| Goldzellen | 1.294 |
| wörtlich belegt | 1.088 (**84,1 %**) |
| ohne wörtlichen Beleg | 206 |
| Records vollständig belegt | **262** |
| Records mit Lücke | 145 |
| Records ohne Goldzellen | 26 |

Korrektur gegenüber der ersten Fassung: Dort standen 288 – gezählt wurden
auch die 26 Records ohne Goldzellen, die formal „alles belegt" haben, aber
nichts zu extrahieren enthalten. Der Kandidaten-Split umfasst daher **262**
Records (`zeitpunkte.md`).

Nach Feld:

| Feld | Zellen | belegt | Quote |
|---|---|---|---|
| intervention_group_size | 356 | 326 | 91,6 % |
| comparator_group_size | 356 | 327 | 91,9 % |
| intervention_mean | 139 | 99 | 71,2 % |
| comparator_mean | 134 | 103 | 76,9 % |
| intervention_standard_deviation | 101 | 89 | 88,1 % |
| comparator_standard_deviation | 100 | 88 | 88,0 % |
| intervention_events | 51 | 25 | 49,0 % |
| comparator_events | 57 | 31 | 54,4 % |

## Wo die Lücken liegen

* **57 der 206** fehlenden Zellen stehen in Kurztexten unter 5.000 Zeichen —
  dort liefert der Markdown nur die Kurzfassung, Tabellenwerte fehlen
  strukturell.
* **149** stehen in längeren Texten; dort ist die Zahl entweder anders
  geschrieben, gerundet oder aus einer Tabelle, die der Markdown nicht
  enthält.
* Nur **2** der 206 finden sich gerundet (eine Nachkommastelle oder Ganzzahl);
  bei **204** gibt es keine verwandte Schreibweise im Text.

Die schwächsten Felder sind die Ereigniszahlen (49–54 %). Das ist plausibel:
Ereignisse stehen meist in Tabellen oder im Fließtext als „n (%)"-Konstrukt,
seltener als reine Zahl.

## Was das für den Split heißt

* **262 Records** sind vollständig wörtlich belegt und taugen ohne weitere
  Prüfung als Kandidaten (eingefroren als `records/yun_kandidaten.jsonl`, Liste
  und Zeitpunkte in `zeitpunkte.md`).
* **145 Records** haben mindestens eine Zelle ohne Beleg; sie brauchen einen
  Blick in den Text, bevor sie in den Benchmark gehen.
* **26 Records** führen keine Goldzellen und fallen für die Extraktion aus.

Der Split selbst liegt als `kandidaten.jsonl` (Record-Kennung, Dokument,
Outcome, Zeitpunkt, Zellen mit Belegstatus) neben dieser Auswertung; die
Einzelprüfung mit Textfenster steht in `zellen.csv`.

## Grenzen

* Geprüft wird nur, **ob** die Zahl im Text steht — nicht, ob sie zum richtigen
  Arm, Zeitpunkt oder Outcome gehört. Dafür sind `precheck_gold.py` und die
  Sichtprüfung da.
* „Nicht wörtlich" heißt nicht „falsch": Der Markdown ist eine
  Textrepräsentation; Werte aus Bildern und nicht übertragenen Tabellen fehlen.
* Zahlen unter 1 werden nicht als „gerundet auf Ganzzahl" geprüft (eine „0"
  findet sich in jedem Text und sagt nichts).
