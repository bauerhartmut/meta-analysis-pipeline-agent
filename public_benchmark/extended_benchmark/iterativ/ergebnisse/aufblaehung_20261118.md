# Aufblähung der Feld/Arm-Zählung (Lesekopie, 559 erfolgreiche Zeilen)

Offline gemessen an 559 erfolgreichen `glm`-Zeilen mit Zellen. Großzügig heißt: Feld und Arm genügen. Streng heißt: derselbe Feld/Arm-Schlüssel darf nur einen Zeitpunkt nennen.

| Größe | Wert |
|---|---|
| Zeilen | 559 |
| Goldzellen | 2306 |
| adressiert, großzügig | 2121 |
| adressiert, streng | 2103 |
| **Aufblähung** | **18** (0.8% der großzügig adressierten) |
| wertgleich, großzügig | 1844 |
| wertgleich, streng | 1826 |
| Aufblähung wertgleich | 18 |
| betroffene Zeilen | 4 von 559 |
| Zellen insgesamt | 2254 |
| davon eindeutig (Feld, Arm, Zeitpunkt) | 2254 |
| Zellen mit Zeitpunkt | 1649 |
| Feld/Arm-Gruppen mit mehreren Zeitpunkten | 18 |

## Verteilung der Aufblähung je Zeile

| Aufblähung | Zeilen |
|---|---|
| 0 | 555 |
| 4 | 3 |
| 6 | 1 |

## Zeilen mit der größten Aufblähung

| Record | Goldzellen | adressiert | streng | Aufblähung | Zellen |
|---|---|---|---|---|---|
| `yun2024:419` | 6 | 6 | 0 | 6 | 12 |
| `yun2024:121` | 4 | 4 | 0 | 4 | 8 |
| `yun2024:418` | 6 | 6 | 2 | 4 | 10 |
| `yun2024:586` | 6 | 6 | 2 | 4 | 10 |

## Grenze dieser Zahl

Die Aufblähung ist eine **Untergrenze**, keine Obergrenze: geprüft wird nur, ob eine Vorhersage denselben Feld/Arm-Schlüssel über mehrere Zeitpunkte streut. Ob der genannte Zeitpunkt der richtige ist, lässt sich am Gold nicht prüfen, weil keine Goldzelle einen trägt. Eine Vorhersage, die den falschen Zeitpunkt nennt, aber nur einen, zählt hier als Treffer; 1649 von 2254 Zellen nennen überhaupt einen Zeitpunkt. Die tatsächliche Aufblähung kann also größer sein, nicht kleiner.

14 erfolgreiche Zeilen haben keine Goldzellen und können nichts adressieren; sie stehen in den Summen mit 0.
