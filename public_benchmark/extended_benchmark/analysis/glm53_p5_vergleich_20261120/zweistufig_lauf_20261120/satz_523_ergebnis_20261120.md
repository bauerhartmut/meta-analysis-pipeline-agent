# Satz-Locator auf yun2024:523: der Abbruch hing an der Anweisung, nicht am Schema (20.11.2026)

> Korrigiert am 20.11.2026: Die erste Fassung dieses Berichts schrieb den Erfolg dem
> neuen Schema zu. Die Kontrolle mit dem Zusatzsatz in der alten Zeilenlabel-Fassung
> widerlegt das; beide Schemata funktionieren mit dem Zusatz. Siehe Abschnitte
> „Dreiwegvergleich“ und „Kette 523 vollstaendig“ unten.

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

Auf diesem Material antwortet das Modell in 2.342 Tokens, sobald es den Satz
zitieren darf statt eine Zeile zu benennen. Ob das am Schema oder am Zusatzsatz
liegt, klaert der Dreiwegvergleich unten - die Antwort ist: am Zusatzsatz.

## Dreiwegvergleich: Schema oder Anweisung?

Gleicher Record, gleicher Ausschnitt (6.000 Zeichen), gleiches Budget 16.632,
jeweils ein Aufruf. Unterschiede nur im Prompt:

| Prompt | Tokens | Ergebnis | Locator / Zellen |
|---|---:|---|---|
| Zeilenlabel, ohne Zusatz | 16.632 (voll) | abgebrochen, `length` | 0 Locators |
| Zeilenlabel, mit Zusatz | **3.318** | ok, `stop` | 2 Locators, Zeile `Mean scores of first and second evaluations`, Spalten `feedback receivers` / `others`, Zeitpunkt `first`, Zielwerte 10,24 / 9,73 / 0,77 in der Umgebung |
| Satz-Locator, mit Zusatz | **2.342** | ok, `stop` | 2 Locators, berichtender Satz woertlich |

**Ergebnis: Der Abbruch hing an der Anweisung, nicht am Schema.** Dieselbe
alte Zeilenlabel-Fassung, die zuvor das ganze Budget verbrauchte, antwortet in
3.318 Tokens, sobald der Satz „Answer without weighing alternative readings.“
am Ende steht - und findet dabei ein Zeilenlabel, das vorher nicht existierte
(„Mean scores of first and second evaluations“). Das Modell konnte die Stelle
also; ohne die Anweisung hat es sich im Abwaegen verfangen.

Der Satz-Locator ist trotzdem die bessere Fassung: 976 Tokens billiger (2.342
gegen 3.318) und ohne die Behauptung, es gaebe eine Tabellenzeile, die es im
Abstract nicht gibt.

Offen bleibt, ob der **Wortlaut** oder nur die **Laenge** des Zusatzes wirkt -
gemessen ist genau dieser eine Satz an genau dieser Stelle, n = 1 je Zelle.

## Kette 523 vollstaendig: 4 TP aus dem Satz

Stufe 2 mit dem Satz und der Auflage, nur die **erste** Evaluation zu lesen
(`predictions_stufe2_satz_523_16632.jsonl`):

| Groesse | Wert |
|---|---|
| Status | ok (`finish_reason = stop`) |
| Completion-Tokens | **268** |
| Inhalt | 478 Zeichen, 4 Zellen |
| TP / FP / FN | **4 / 0 / 2** |
| P / R / F1 | 1,000 / 0,667 / 0,800 |

Gelesen: intervention_mean 10,24, intervention_sd 0,77, comparator_mean 9,73,
comparator_sd 0,77 - alle vier im Ausschnitt gedruckt, alle vier richtig. Die
FN sind die Gruppengroessen 15/15, die der Text nicht nennt.

Damit ist der Fall vollstaendig: 2.342 (Stufe 1) + 268 (Stufe 2) = **2.610
Tokens** fuer 4 TP auf einem Record, dessen Stufe-1-Aufruf zuvor 16.632 Tokens
ohne Ergebnis verbrannte. Die Ambiguitaet im Satz (zwei Evaluationen je Arm) hat
Stufe 2 mit der Auflage „erstes Paar“ aufgeloest.

## Grenzen

- **n = 1** Record, ein Dokument. Der Satz-Locator ist auf 525 nicht in dieser
  Fassung gemessen (dort lief die Zeilenlabel-Fassung), also gibt es keinen
  zweiten Messpunkt fuer das neue Schema.
- Der Dreiwegvergleich ist mit je einem Aufruf pro Zelle gemessen; n = 1. Eine
  Wiederholung koennte anders ausgehen, der P5-Lauf zeigt genau diese Varianz
  (5 der 13 Abbrueche lieferten im Nachzug Zellen).
- Armzuordnung in Stufe 2 (intervention = feedback receivers, comparator =
  others) stand im Prompt; sie folgt aus dem Kontext, ist aber von mir gesetzt
  und nicht vom Modell erschlossen.
- Tokens sind keine Kostenwahrheit: 2.342 Completion-Tokens sind gemessen, der
  Prompt hat 7.265 Zeichen (Eingabetokens nicht budgetiert).
