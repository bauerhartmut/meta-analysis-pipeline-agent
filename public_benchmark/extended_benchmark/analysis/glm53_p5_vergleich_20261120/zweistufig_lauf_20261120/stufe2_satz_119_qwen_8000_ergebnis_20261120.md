# Stufe 2 auf dem 119er Satz: keine Zelle, weil der Satz Anteile und keine Mittelwerte druckt (20.11.2026)

Ein freigegebener Aufruf, die Wiederholung des Budget-Abbruchs mit 8.000 statt
4.000 Tokens. Modell `gwdg/qwen3.5-397b-a17b` (`qwen`), Stufe 2 auf dem Satz aus
`predictions_satz_119_qwen_16000.jsonl`, Prompt **byte-identisch** zum 4.000er
Lauf (7.668 Zeichen, SHA256 `0e0c102c...9291`), nur `max_tokens` geaendert.
Rohdaten: `predictions_stufe2_satz_119_qwen_8000.jsonl`.

## Vorab offline geprueft (kein Netz)

Am zitierten Satz selbst, vor dem Aufruf:

| Pruefung | Ergebnis |
|---|---|
| Arme im Satz | `mild cooling` **4x**, `no cooling` **5x**; Kontext nennt `Mild-cooling` bzw. `No cooling` |
| Zielwerte gedruckt | `70%` **1x**, `15.4%` **1x**, je woertlich |
| Zahlenform | `70` kommt nur als `70%` vor, `15.4` nur als `15.4%` |
| Gruppengroessen 10 / 13 | **nicht im Satz** (auch nicht als Ziffernfolge) |
| Bezugsgroesse | „70% of mild cooling attained good GOS … only 15.4% attained good GOS in no cooling group" |

Der Satz traegt die Arme also eindeutig und die beiden Zahlen in genau einer
Form. Was er nicht druckt, ist ein Mittelwert: er berichtet **Anteile von
Patienten** an einem binaeren Ziel („attained good GOS"). Das Gold fuehrt diese
Anteile als `intervention_mean` = 70,0 und `comparator_mean` = 15,4.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **5.899** von 8.000 |
| Reasoning-Zeichen | 22.362 |
| Inhalt | 509 Zeichen, **0 Zellen** (`parse_fehler = keine_verwertbaren_zellen`) |
| Dauer | 272,17 s |
| Bewertung | 0 TP / 0 FP / 4 FN |

Die Rohantwort ist kein Parserfehler, sondern eine **leere Zellenliste mit
vollem Zitat**:

```json
{"cells": [], "quote": "<der vollstaendige Satz, woertlich>"}
```

Das Modell hat die Belegstelle also gelesen, zugeordnet und dann ausdruecklich
keine Zelle ausgegeben. Die Auflage des Prompts war: lies je Arm „mean and
standard deviation", kopiere die Zahlen „exactly as printed", und „do not
convert, compute, round". Bei einer Prozentangabe, die einen Anteil und keinen
Mittelwert darstellt, fuehrt diese Auflage zu genau dieser Antwort: entweder
`70` als `mean` ausgeben (Umdeutung) oder umrechnen (verboten) oder nichts
ausgeben. Das Modell waehlt das Nichts - konservativ, aber ohne Treffer.

## Was der Aufruf beantwortet

**Der Satz traegt die zwei erreichbaren Zellen nicht als `mean` - nicht, weil
sie fehlen, sondern weil die Feldbezeichnung des Goldes nicht zur gedruckten
Groesse passt.** Das ist derselbe Befund, der bei 119 schon auf Stufe 1
notiert wurde (`outcome_type = continuous`, gedruckt ist ein dichotomierter
Anteil), jetzt auf Stufe 2 gemessen: Der Ort ist richtig, das Zitat ist
richtig, aber das verlangte Feld (`*_mean`) beschreibt eine andere Groesse als
die gedruckte (`%` der Patienten mit gutem GOS).

Damit ist die Kette auf 119 **technisch geschlossen und inhaltlich leer**:

| Stufe | Ergebnis |
|---|---|
| 1 (qwen, 6.236 Tokens) | ok, 2 Locators, Satz woertlich, `timepoint = "6 months post-trauma"` |
| 2 (qwen, 4.000 Tokens) | abgebrochen, 0 Zeichen (Budget) |
| 2 (qwen, 8.000 Tokens) | ok, 0 Zellen, leere Liste mit vollem Zitat |

Ein zweiter Aufruf mit mehr Budget haette hier nichts geaendert: der 8.000er
Lauf ist fertig geworden (5.899 Tokens, `stop`) und hat trotzdem keine Zelle
geliefert. Der 4.000er Abbruch war ein Budgetproblem, die fehlenden Zellen sind
keines.

## Kosten

Gemessene Completion-Tokens: 145.145 (bisherige Reihe) + 5.899 = **151.044**.
Der 4.000er Abbruch-Lauf ist darin enthalten (145.145 schloss ihn ein).
Eingabetokens sind nicht budgetiert und hier nicht enthalten.

## Grenzen

- **n = 1** Aufruf mit 8.000. Ob eine andere Formulierung des Feldes (etwa
  „percentage of patients" statt „mean") Zellen liefert, ist damit **nicht**
  gemessen; gemessen ist nur, dass der jetzige Prompt sie nicht liefert.
- Die leere Liste ist eine Interpretation der Rohantwort. Sie ist eindeutig
  (`"cells": []`), aber die Begruendung des Modells steht nur in der Denkspur
  (22.362 Zeichen), die nicht im Predictions-File liegt.
- Der Vergleich mit 420 traegt nur teilweise: dort druckt der Satz Mittelwerte
  (`0.95 [SD, 0.24]`), hier Anteile. Die beiden Records testen verschiedene
  Groessen unter demselben Feldschema.
- Der F1 ist hier nicht berechenbar (Precision `null`, weil keine Zelle
  ausgegeben wurde) - 0 TP ist nicht dasselbe wie „keine Aussage", sondern die
  Folge einer leeren Liste.
