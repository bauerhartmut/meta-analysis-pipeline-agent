# Dublettenfilter auf den P5-Predictions (20.11.2026)

Reine Nachbearbeitung, kein Modellaufruf. Bewertet auf den 102 bewertbaren Records der P5-Auswahl mit der Logik aus `vergleiche_20261120.py` (Schluessel Feld + Arm, 1:1-Verbrauch). Gold und `predictions.jsonl` bleiben unveraendert; die SHA256-Summen vor und nach der Rechnung sind identisch.

## Kennzahlen vorher/nachher

| Variante | TP | FP | FN | Precision | Recall | F1 | entfernte Zellen | Records veraendert |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| unveraendert (Referenz) | 170 | 97 | 253 | 0.6367 | 0.4019 | 0.4928 | 0 | 0 |
| Dublettenfilter, erste Zelle je Feld+Arm | 170 | 88 | 253 | 0.6589 | 0.4019 | 0.4993 | 9 | 5 |
| Dublettenfilter, haeufigster Wert je Feld+Arm | 170 | 88 | 253 | 0.6589 | 0.4019 | 0.4993 | 9 | 5 |
| Obergrenze (goldinformiert, nicht anwendbar) | 170 | 88 | 253 | 0.6589 | 0.4019 | 0.4993 | 9 | 5 |

## Was der Filter tut und was nicht

- Der goldfreie Filter entfernt 9 Zellen in 5 von 102 Records. Der Recall bleibt mit 0.4019 unveraendert, weil je (Feld, Arm) immer eine Zelle stehen bleibt und der 1:1-Verbrauch ohnehin nur eine Trefferzelle je Goldzelle zulaesst.
- Precision 0.6367 -> 0.6589, F1 0.4928 -> 0.4993 (+0.65 Prozentpunkte).
- Die Mehrheitsvariante liegt bei F1 0.4993; sie ist gegenueber der ersten Zelle nicht besser, weil sich bei wiederholten Zellen meist derselbe Wert wiederholt.
- Die goldinformierte Obergrenze liegt bei F1 0.4993; die Differenz zu `erste_zelle` ist der Preis dafuer, dass der Filter den richtigen Wert nicht kennen kann.

## Grenze des Verfahrens

- Von den 97 falschen Zellen der Basis sind 13 Mehrfachzellen im selben (Feld, Arm), 67 einzelne Zellen mit falschem Wert auf einem Gold-Schluessel und 17 Fremdschluessel. Nur die Mehrfachzellen sind goldfrei entfernbar.
- Dass 13 Mehrfachzellen erkannt werden, aber nur 9 Zellen verschwinden, liegt an den Gruppen ohne Treffer: steht im selben (Feld, Arm) keine goldpassende Zelle, bleibt nach dem Filter genau eine falsche Zelle stehen.
- Weil alle drei Varianten dasselbe Ergebnis liefern, sind die entfernten Zellen exakte Wertwiederholungen: die Auswahlregel (erste, haeufigste, goldpassende) ist dann gleichgueltig.
- Fremdschluessel sind goldfrei nicht entfernbar: `intervention_events` und `comparator_mean` sind in anderen Records korrekte Zielfelder. Eine Loeschung waere nur mit Goldwissen oder einer record-spezifischen Feldauswahl moeglich.
- Der Filter aendert die Ausgabedisziplin nicht. Er verschiebt nur, welche der mehrfach genannten Zellen zaehlt.

## Records, bei denen der goldfreie Filter wirkt

| Record | Goldzellen | Zellen | TP vorher | TP nachher | FP vorher | FP nachher | entfernt |
|---|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:151` | 4 | 6 | 3 | 3 | 3 | 1 | 2 |
| `yun2024:174` | 4 | 6 | 2 | 2 | 4 | 2 | 2 |
| `yun2024:214` | 6 | 6 | 4 | 4 | 2 | 0 | 2 |
| `yun2024:215` | 6 | 6 | 4 | 4 | 2 | 0 | 2 |
| `yun2024:662` | 2 | 3 | 1 | 1 | 2 | 1 | 1 |

