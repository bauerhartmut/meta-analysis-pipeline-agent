# Ereigniszaehler mit Zeitpunktzuordnung (21.11.2026)

Offline, ohne Netzaufruf. Regel: Tabelle suchen, deren Zeilenbeschriftung zum
Outcome-Namen passt, Arm aus Zeile oder Kopfzeile, Spalte des Zielzeitpunkts
(Record-Regel: letzter berichteter Zeitpunkt). Zwei Varianten, weil die drei
Baseline-Faelle keine Zaehler, sondern Prozentwerte sind.

## Ergebnis

| Variante | Zellen | TP | FP | TP-Verlust |
|---|---:|---:|---:|---:|
| `zaehler` (nur `n` + `(%)`) | 2 | 2 | 0 | 0 |
| `prozent` (auch Prozentzeilen) | 6 | 2 | 4 | 0 |

## Zellen, Variante `zaehler`

| Record | Feld | Regelwert | Quelle | Spalte | Gold | richtig |
|---|---|---:|---|---|---:|---|
| `yun2024:190` | intervention_events | 52.0 | zaehler | 12 months | 52.0 | ja |
| `yun2024:190` | comparator_events | 51.0 | zaehler | 12 months | 51.0 | ja |

## Zellen, Variante `prozent`

| Record | Feld | Regelwert | Quelle | Spalte | Gold | richtig |
|---|---|---:|---|---|---:|---|
| `yun2024:190` | intervention_events | 52.0 | zaehler | 12 months | 52.0 | ja |
| `yun2024:190` | comparator_events | 51.0 | zaehler | 12 months | 51.0 | ja |
| `yun2024:370` | comparator_events | 52.0 | prozent | Prozentzeile | 33.0 | nein |
| `yun2024:370` | intervention_events | 59.0 | prozent | Prozentzeile | 35.0 | nein |
| `yun2024:373` | comparator_events | 72.0 | prozent | Prozentzeile | 46.0 | nein |
| `yun2024:373` | intervention_events | 54.0 | prozent | Prozentzeile | 32.0 | nein |

## Lesart

Nur `yun2024:190` ist ein echter Zaehler: Arm in der Zeile (`Intervention`,
`TAU`), Zeitpunkt in der Spalte (`Baseline`, 3, 6, 12 Monate), je Zelle `n` und
`(%)`. Die Zielspalte ist der letzte Zeitpunkt, dort steht 52/51 - beide Gold.
Die drei uebrigen Faelle sind Prozentwerte aus Baseline-Tabellen ohne
Zeitpunktachse; ihre Goldpaare stehen in keiner Tabellenzeile, die
Outcome-Zeile liefert andere Zahlen (etwa `Diabetes, %  52  59` bei Gold 35/33).
Die Variante `prozent` zahlt diese Fehlgriffe als FP.
