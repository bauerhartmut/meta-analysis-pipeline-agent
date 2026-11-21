# Zeilenbindung ueber alle 699 Records (21.11.2026)

Dieselbe Regel wie in der 41er-Auswahl, offline und ohne Netzaufruf, additiver
Modus. `ersetzen` bleibt aussen vor, weil es in der Auswahl zahlengleich war.

## Gesamtbild

| Gruppenmodus | Records | gebundene Records | gebundene Zellen (richtig) | TP | FP | FP-Delta | TP-Delta |
|---|---:|---:|---:|---|---|---:|---:|
| streng | 699 | 2 | 12 (2 richtig) | 170 -> 172 | 101 -> 111 | +10 | +2 |
| erstes | 699 | 22 | 126 (34 richtig) | 170 -> 198 | 101 -> 177 | +76 | +28 |

## Luecke zwischen richtigen Zellen und neuen TP

| Gruppenmodus | richtige Zellen | neu hinzugefuegt | vorher schon richtig | vorher falsch (additiv nicht ersetzt) | doppelte Goldschluessel | doppelte Bindungsschluessel |
|---|---:|---:|---:|---:|---:|---:|
| streng | 2 | 2 | 0 | 0 | 0 | 0 |
| erstes | 34 | 28 | 6 | 0 | 0 | 0 |

`neu hinzugefuegt` entspricht dem TP-Delta. Die Differenz sind Zellen, die im
Gold stehen, aber die Bilanz nicht heben, weil der Wert vorher schon richtig war
oder weil am Schluessel ein falscher Wert stand, den der additive Modus nicht
ueberschreibt. Doppelte Schluessel treten nicht auf.

### Armzuordnung der falschen Zellen

| Gruppenmodus | richtige Zellen | falsche Zellen | davon Wert falsch | davon Schluessel nicht im Gold | davon Wert unter dem anderen Arm |
|---|---:|---:|---:|---:|---:|
| streng | 2 | 10 | 10 | 0 | 0 |
| erstes | 34 | 92 | 76 | 16 | 1 |

`Wert unter dem anderen Arm` ist der einzige direkte Hinweis auf eine vertauschte
Armzuordnung; alle anderen falschen Zellen treffen eine Zeile, die im Gold gar
nicht vorkommt.

## Aufteilung

| Gruppenmodus | gebunden (41) | Zellen (richtig) | FP-Delta (41) | TP-Delta (41) |
|---|---:|---:|---:|---:|
| streng | 1 | 6 (1 richtig) | +5 | +1 |
| erstes | 3 | 18 (7 richtig) | +11 | +7 |

| Gruppenmodus | gebunden (658) | Zellen (richtig) | FP-Delta (658) | TP-Delta (658) |
|---|---:|---:|---:|---:|
| streng | 1 | 6 (1 richtig) | +5 | +1 |
| erstes | 19 | 108 (27 richtig) | +65 | +21 |

## Antwort

Die Zusatz-FP der 41 verschwinden nicht. Bei `erstes` sind es 11 der 76
Zusatz-FP; die uebrigen 65 stammen aus 19 weiteren Records, die dafuer 21 TP
liefern. `streng` liegt bei 2 TP und 10 FP. Die Regel skaliert also nicht:
22 von 699 Records werden gebunden, 34 von 126 Zellen treffen das Gold
(27 Prozent).

## Lesart

Die Zusatz-FP der 41 schweren Records verschwinden nicht, sie sind nur ein
Teil der Gesamtbilanz. Entscheidend ist das Verhaeltnis von neuen TP zu neuen
FP: gebundene Zellen, die nicht im Gold stehen, kosten eine FP, gleichgueltig
in welchem Record sie liegen. Die Tabelle zeigt dieses Verhaeltnis getrennt
fuer die Auswahl und fuer die uebrigen Records.
