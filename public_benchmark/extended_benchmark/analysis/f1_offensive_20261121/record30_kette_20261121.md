# Record yun2024:30, Kette offline nachgerechnet (21.11.2026)

Gelesen werden die gespeicherten Antworten der Stufe 1 (Zeilenbindung) und der
Stufe 2 aus `zweistufig_lauf_20261120/`. Kein Modellaufruf.

## Stufe 1 (gespeichert)

- Arm intervention: Zeile `Mean score (SD)`, Spalte `CZP 200 mg + MTX`, Zeitpunkt `Week 52`
- Arm comparator: Zeile `Mean score (SD)`, Spalte `PBO + MTX`, Zeitpunkt `Week 52`

## Stufe 2, Zellen mit Fundstelle

| Feld | Arm | Wert | Fundstelle belegt | Zeile im Dokument |
|---|---|---:|:---:|---|
| intervention_mean | intervention | 38.1 | ja | Role Emotional            32.4 (39.1)         28.9 (38.1)         30.9 |
| intervention_standard_deviation | intervention | 9.5 | ja | Mean score (SD)       36.1 (8.9)    36.8 (8.4)    30.7 (7.1)    37.8 ( |
| intervention_group_size | intervention | 393.0 | ja | # Abstract ## Introduction The objective of this study was to assess t |
| comparator_mean | comparator | 31.5 | ja | Mean score (SD)       36.1 (8.9)    36.8 (8.4)    30.7 (7.1)    37.8 ( |
| comparator_standard_deviation | comparator | 7.4 | ja | Mean score (SD)       36.1 (8.9)    36.8 (8.4)    30.7 (7.1)    37.8 ( |
| comparator_group_size | comparator | 199.0 | ja | # Abstract ## Introduction The objective of this study was to assess t |

Fundstellen belegt: 6 von 6.

## Bilanz

| Stand | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| vorher | 6 | 0 | 0 | 1.0000 |
| nach Validierung | 6 | 0 | 0 | 1.0000 |

Verworfen: 0 Zellen.

## Was der Fall zeigt

Die Kette traegt auf diesem Record: Zeile `Mean score (SD)`, Wochenblock 52,
sechs Zellen, F1 1,0, jede Zelle im Text belegt. Die Validierung aendert nichts,
weil keine Zelle gegen eine strukturelle Regel verstoesst. Das ist die
Referenz fuer die Frage, ob eine Verallgemeinerung Regressionen erzeugt: hier
darf keine entstehen.

Grenzen: ein Record, ein Modell (qwen 3.5 397b), gespeicherte Antworten vom
20.11.2026. Die Fundstelle ist die erste Fundstelle der Zahl im Dokument, nicht
notwendig die vom Modell gelesene; bei mehrfach gedruckten Zahlen ist sie daher
nur ein Beleg, dass die Zahl im Artikel steht.
