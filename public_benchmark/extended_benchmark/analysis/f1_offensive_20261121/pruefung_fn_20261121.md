# Kontrollen zu den FN-Klassen

Offline, ohne Netzaufruf.

## A) Ueberlappung mit der 295er-Endvariante

* Zellen der Endvariante: 43
* richtige Zellen aus der FN-Uebertragung: 7
* gemeinsame Record/Feld/Arm-Schluessel: 0

Keine Ueberlappung: die 7 richtigen Zellen sind neue Record/Feld-Paare, 

## B) Stichprobe `fn_nicht_im_dokument`

Stichprobe: 20 von 164 Faellen, jeder 8. Fall.

| Record | Feld | Wert | Befund | Stellen | Zeichen | Outcome-Label im Text |
|---|---|---:|---|---:|---:|---|
| `yun2024:10` | comparator_group_size | 20.0 | nicht_gefunden | 0 | 2872 | ja |
| `yun2024:112` | comparator_standard_deviation | 78.33 | nur_gerundet | 1 | 49917 | ja |
| `yun2024:134` | comparator_standard_deviation | 24.79 | nur_gerundet | 3 | 21577 | ja |
| `yun2024:158` | intervention_standard_deviation | 15.64 | nur_gerundet | 2 | 16081 | ja |
| `yun2024:163` | intervention_standard_deviation | 1.81 | nur_gerundet | 5 | 16081 | ja |
| `yun2024:193` | intervention_mean | -0.59 | nicht_gefunden | 0 | 20669 | ja |
| `yun2024:205` | comparator_standard_deviation | 103.03 | nicht_gefunden | 0 | 14600 | ja |
| `yun2024:302` | intervention_mean | 0.2 | nur_gerundet | 3 | 5515 | ja |
| `yun2024:335` | intervention_mean | -4.7 | nicht_gefunden | 0 | 17138 | ja |
| `yun2024:361` | comparator_events | 169.0 | nicht_gefunden | 0 | 6842 | ja |
| `yun2024:370` | intervention_events | 35.0 | nicht_gefunden | 0 | 11667 | ja |
| `yun2024:398` | intervention_standard_deviation | 4.09 | nur_gerundet | 12 | 18987 | ja |
| `yun2024:452` | intervention_standard_deviation | 3.33 | nur_gerundet | 8 | 25267 | ja |
| `yun2024:477` | intervention_events | 1279.0 | nicht_gefunden | 0 | 41467 | ja |
| `yun2024:504` | intervention_standard_deviation | 1.37 | nur_gerundet | 17 | 16710 | ja |
| `yun2024:531` | intervention_standard_deviation | 10.54 | nur_gerundet | 3 | 15368 | ja |
| `yun2024:558` | comparator_mean | -8.0 | nicht_gefunden | 0 | 13122 | ja |
| `yun2024:61` | intervention_events | 20.0 | nicht_gefunden | 0 | 4109 | ja |
| `yun2024:620` | intervention_mean | 5639.0 | nicht_gefunden | 0 | 12441 | ja |
| `yun2024:84` | comparator_events | 124.0 | nicht_gefunden | 0 | 39597 | ja |

Verteilung: nicht_gefunden 11, nur_gerundet 9

Kurze Dokumente (unter 12000 Zeichen): 5 von 20.
Ohne Outcome-Label im Text: 0 von 20.

## Lesart

Die Ueberlappung ist leer: die 7 richtigen Zellen der FN-Uebertragung sind
andere Record/Feld/arm-Schluessel als die 43 Zellen der Endvariante und
damit auch andere als die in P5 ersetzten. Der Gewinn ist also nicht doppelt
gezaehlt - er ist nur klein.

In der Stichprobe steht kein Goldwert exakt im Markdown. Elf der zwanzig
Werte kommen ueberhaupt nicht vor; neun erscheinen nur in gerundeter Form.
Auffaellig: acht dieser neun sind Standardabweichungen, die der Record laut
`issues` aus Konfidenzintervallen zurueckgerechnet hat - dort ist der
exakte Wert konstruktionsbedingt nicht im Text. Bei den Mittelwerten sind
vier von fuenf gar nicht und einer nur gerundet belegt. Die Klasse
`fn_nicht_im_dokument` ist damit in der Stichprobe bestaetigt.

