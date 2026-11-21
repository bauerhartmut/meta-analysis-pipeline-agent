# Zeilenbenennung im Prompt gegen `fn_wert_ersetzt` (21.11.2026)

Offline, ohne Netzaufruf. Stichprobe: jeder 15. der 295 Faelle
(`fn_wert_ersetzt`), also 20 Faelle ueber die ganze Liste verteilt.

Geprueft wird nur die Voraussetzung, die ein Prompt erfuellen muesste: steht der
Goldwert im Dokument in einer Zeile, deren Label oder Zeilengruppe den Outcome
benennt? Ist das eindeutig, kann eine explizite Zeilenangabe den Fall loesen.

## Verteilung

| Klasse | Faelle |
|---|---:|
| eindeutig benannt | 1 |
| Tabelle ueber Kaption benannt (Zaehlfelder) | 2 |
| mehrdeutig benannt | 1 |
| Wert ohne Outcome-Bezug | 2 |
| Wert nur im Fliesstext, keine Tabellenzeile | 14 |
| Wert nicht im Dokument | 0 |

## Faelle

| Record | Feld | Arm | Wert | Klasse | Zeilen mit Wert | Gruppe / Label | Regel bindet Record |
|---|---|---|---|---:|---|---|---|
| `yun2024:100` | intervention group size | intervention | 40.0 | wert_nur_im_fliessetext | 6 | - | nein |
| `yun2024:114` | intervention group size | intervention | 456.0 | ohne_outcome_bezug | 3 | - | nein |
| `yun2024:14` | comparator events | comparator | 54.0 | wert_nur_im_fliessetext | 5 | - | nein |
| `yun2024:193` | intervention group size | intervention | 138.0 | wert_nur_im_fliessetext | 2 | - | nein |
| `yun2024:222` | comparator mean | comparator | 2.67 | eindeutig_benannt | 1 | Lateral bending                0.15?0.04 | nein |
| `yun2024:242` | comparator standard deviation | comparator | 0.9 | wert_nur_im_fliessetext | 2 | - | nein |
| `yun2024:290` | comparator mean | comparator | 41.3 | wert_nur_im_fliessetext | 1 | - | nein |
| `yun2024:303` | intervention mean | intervention | 1.0 | wert_nur_im_fliessetext | 3 | - | nein |
| `yun2024:334` | intervention group size | intervention | 45.0 | kaption_benannt | 5 | - | nein |
| `yun2024:355` | comparator mean | comparator | 5.7 | wert_nur_im_fliessetext | 3 | - | nein |
| `yun2024:389` | comparator events | comparator | 175.0 | kaption_benannt | 3 | - | nein |
| `yun2024:445` | comparator group size | comparator | 70.0 | ohne_outcome_bezug | 16 | - | nein |
| `yun2024:522` | comparator group size | comparator | 30.0 | wert_nur_im_fliessetext | 2 | - | nein |
| `yun2024:572` | intervention standard deviation | intervention | 4.2 | mehrdeutig_benannt | 3 | Medial tibial plateau / months | nein |
| `yun2024:617` | comparator group size | comparator | 656.0 | wert_nur_im_fliessetext | 1 | - | nein |
| `yun2024:643` | intervention group size | intervention | 48.0 | wert_nur_im_fliessetext | 2 | - | nein |
| `yun2024:665` | intervention standard deviation | intervention | 28.9 | wert_nur_im_fliessetext | 1 | - | nein |
| `yun2024:669` | intervention mean | intervention | 200.1 | wert_nur_im_fliessetext | 1 | - | nein |
| `yun2024:681` | comparator standard deviation | comparator | 13.0 | wert_nur_im_fliessetext | 2 | - | nein |
| `yun2024:75` | comparator mean | comparator | 13.72 | wert_nur_im_fliessetext | 1 | - | nein |

## Antwort

Eine explizite Zeilenbenennung im Prompt erreicht hoechstens 4 der 20 Faelle:
eine eindeutig benannte Zeile, eine mehrdeutige (Zusatzangabe noetig) und zwei
Zaehlfelder, deren Tabelle die Kaption benennt. Bei `yun2024:389` ist der Wert
175 allerdings die Groesse einer Untergruppe (`Complicated (n = 175)`), nicht
die Armgroesse; nach Sichtpruefung bleiben 3 belastbare Faelle. Die anderen 16
sind so nicht loesbar: 14 Werte stehen nur im Fliesstext, 2 in Zeilen ohne
Outcome-Bezug.

## Lesart

`eindeutig benannt` heisst: der Prompt koennte die Zeile nennen, und die Zeile
ist ohne Zusatzwissen eindeutig. `mehrdeutig benannt` heisst: mehrere Zeilen
nennen den Outcome, es braucht zusaetzlich Gruppe oder Zeitpunkt. Die beiden
restlichen Klassen kann eine Zeilenbenennung nicht erreichen, weil der Wert
nicht in einer benannten Zeile steht.
