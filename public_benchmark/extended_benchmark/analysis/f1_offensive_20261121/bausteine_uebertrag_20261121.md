# Bausteine der 295er-Auswertung bei den uebrigen FN-Regeln

Offline, ohne Netzaufruf.

## Ergebnis je Klasse

| Klasse | Faelle | Zellen | TP | FP | Trefferquote |
|---|---:|---:|---:|---:|---:|
| `fn_leer` | 182 | 31 | 3 | 28 | 10 % |
| `fn_nicht_im_dokument` | 164 | 10 | 0 | 10 | 0 % |
| `fn_nicht_ausgegeben` | 118 | 9 | 4 | 5 | 44 % |

Zusammen: 50 Zellen, 7 TP, 43 FP (14 % Trefferquote).

## Welcher Baustein liefert

| Quelle | TP | FP |
|---|---:|---:|
| `zielzeile` | 0 | 25 |
| `position` | 3 | 14 |
| `zeile` | 0 | 4 |
| `wochenspalte` | 4 | 0 |

## Mit und ohne Positionsregel

| Lauf | Zellen | TP | FP |
|---|---:|---:|---:|
| Positionsregel an | 50 | 7 | 43 |
| Positionsregel aus | 50 | 8 | 42 |

## Lesart

Die Bausteine tragen hier nicht. Von 464 offenen FN-Faellen liefert die
Kette nur einen kleinen Teil, und davon ist der groesste Teil falsch. Die
Wochenspalte ist der einzige Baustein mit klarem Signal (4 von 4 richtig,
alle in `fn_nicht_ausgegeben`). Die Positionsregel bringt in `fn_leer`
13 falsche gegen 3 richtige Zellen und ist ohne sie sogar einen TP besser.
Der Mittel-Leser aus der Zielzeile liefert in allen drei Klassen fast nur
Fehlgriffe.

Das ist plausibel: Die 295er-Faelle sind solche, in denen die Pipeline
einen Wert geliefert hat, der dem Gold widersprach - dort war die Zeile
vorhanden und nur falsch gewaehlt. Die uebrigen FN-Faelle sind ueberwiegend
Faelle ohne lesbare Zelle im Markdown (Tabellenbild, Fliesstext, anderer
Zeitpunkt); bessere Zeilenwahl hilft dort nicht.
