# Satz-Locator auf yun2024:523: der Abbruch hing am Schema (20.11.2026)

Ein freigegebener Aufruf. Modell `gwdg/glm-5.3`, Budget 16.632, Temperatur 0,
gleicher Ausschnitt wie zuvor (6.000 von 6.811 Zeichen), Prompt 7.265 Zeichen.
Unterschied zur vorigen Fassung ist nur das Locator-Schema: verlangt wird der
berichtende Satz woertlich statt eines Zeilenlabels. Rohdaten:
`predictions_satz_523_16632.jsonl`, Skript `../zweistufig_satz_20261120.py`.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **2.342** von 16.632 |
| Reasoning-Zeichen | 8.262 |
| Inhalt | 610 Zeichen, 2 Locators |
| Dauer | 150,2 s |

Beide Locators enthalten denselben Satz, woertlich und im Ausschnitt
nachgewiesen (`satz_im_ausschnitt = True`), Zeitpunkt `first evaluation`,
`found = true`:

> Mean scores of first and second evaluations were 10.24 +- 0.77, 17.73 +- 0.46
> in feedback receivers and 9.73 +- 0.77 and 12.13 +- 0.47 in others (p < 0.001).

Der Satz enthaelt die gesuchten Werte 10,24 und 9,73 sowie die SD 0,77; die
Pruefung findet 0,77, 9,73 und 10,24 im Satz.

## Der Vergleich, der die Frage beantwortet

Derselbe Record, derselbe Ausschnitt, dasselbe Budget, nur das Schema geaendert:

| Fassung | Ergebnis | Tokens | Inhalt |
|---|---|---:|---|
| Zeilenlabel (`stage1_ankerlos`) | abgebrochen, `length` | 16.632 (voll) | 0 Zeichen, 0 Locators |
| Satz-Locator (`stage1_satz`) | ok, `stop` | 2.342 | 610 Zeichen, 2 Locators |

**Ja, der Abbruch hing am Schema.** Bei einem Budget, das zuvor vollstaendig im
Reasoning verschwand, antwortet dasselbe Modell auf demselben Material in 2.342
Tokens, sobald es den Satz zitieren darf statt eine Zeile zu benennen, die es im
Text nicht gibt.

## Was der Satz-Locator nicht leistet

Der zurueckgegebene Satz enthaelt **beide** Wertepaare: erstes (10,24 / 9,73)
und zweites (17,73 / 12,13) Evaluation. Stufe 1 hat die Stelle also gefunden,
aber die Ambiguitaet nicht aufgeloest - die liegt jetzt bei Stufe 2, die aus
diesem Satz das erste Paar waehlen muss. Fuer 525 war die Lage einfacher, weil
das dritte Paar einen eigenen Satz hat; dort las Stufe 2 vier von vier Zellen
richtig.

Damit ist die Kette fuer 523 noch nicht bis zum TP gemessen: Es gibt Locators,
aber noch keine Zellen. Der naechste Schritt waere Stufe 2 mit diesem Satz und
der Auflage, das **erste** Wertepaar zu lesen (Armzuordnung: intervention =
feedback receivers, comparator = others). Erwartung: 4 Zellen (Mittelwert und SD
je Arm), davon 4 TP, wenn die Paarwahl stimmt; die Gruppengroessen 15/15 bleiben
FN, weil sie im Text nicht gedruckt sind.

## Grenzen

- **n = 1** Record, ein Dokument. Der Satz-Locator ist auf 525 nicht in dieser
  Fassung gemessen (dort lief die Zeilenlabel-Fassung), also gibt es keinen
  zweiten Messpunkt fuer das neue Schema.
- Der Vergleich Zeilenlabel gegen Satz ist confounded mit dem Zusatzsatz
  „Answer without weighing alternative readings.“ im neuen Prompt. Der Satz
  steht im Prompt, um langes Abwaegen zu unterbinden; ob der Erfolg am Schema
  oder an dieser Anweisung haengt, ist mit einem Aufruf nicht getrennt.
- Tokens sind keine Kostenwahrheit: 2.342 Completion-Tokens sind gemessen, der
  Prompt hat 7.265 Zeichen (Eingabetokens nicht budgetiert).
