# Tabellenanker-Prompt fuer die 13 Budgetfaelle (20.11.2026)

Trockenbau, kein Modellaufruf. Basis ist der echte Prompt-Bauer des Harness (`build_prompt`, Version `v2_timepoint`) mit demselben Markdown, das der P5-Lauf gelesen hat. Der Ankerblock wird angehaengt; der bestehende Prompt bleibt Zeichen fuer Zeichen erhalten.

## Ankerblock (1393 Zeichen)

```text
Table anchor (binding, before any cell):
1. Name the one place that reports this outcome at the target time point: the table caption (table number and title) or, if the outcome is reported only in prose, the sentence. Copy it character for character.
2. Add "anchor" as the first key: {"source": "<caption or sentence, copied verbatim>", "row": "<row label exactly as printed>", "intervention_column": "<column head of the intervention arm>", "comparator_column": "<column head of the comparator arm>"}.
3. Check the anchor before you answer: the quoted source must, as printed, name the target time point and carry a value for the field of every cell you emit. A cell whose field or time point is not printed in that one row is not anchored: omit it.
4. Never combine two rows, two populations, two tables or two time points. If no single row prints the target time point and the field, return an empty cell list instead of the nearest other row.
5. After "anchor", always return the two keys the schema requires: "chosen_timepoint" (the label you used, copied exactly as printed) and "discarded_timepoints" (the other labels of this outcome you skipped, copied exactly as printed). Both are required even when the cell list is empty; use "not applicable" if only one time point is reported and "running text" if the outcome is printed only in prose.
Do not describe tables you did not use.
```

## Prompt-Laenge je Record

| Record | Dokument | Typ | Gold | Text | Prompt alt | Prompt neu | Delta | Delta % | Tabelle | Pipe-Zeilen |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:119` | PMC4323894 | continuous | 4 | 10032 | 11045 | 12438 | +1393 | +12.61 | 0 | 0 |
| `yun2024:128` | PMC4493951 | binary | 4 | 7954 | 8970 | 10363 | +1393 | +15.53 | 2 | 0 |
| `yun2024:152` | PMC5055753 | binary | 4 | 7782 | 8788 | 10181 | +1393 | +15.85 | 1 | 0 |
| `yun2024:164` | PMC5062234 | continuous | 2 | 3808 | 4897 | 6290 | +1393 | +28.45 | 0 | 0 |
| `yun2024:273` | PMC3214395 | continuous | 2 | 3360 | 4436 | 5829 | +1393 | +31.4 | 0 | 0 |
| `yun2024:304` | PMC4357072 | binary | 4 | 5515 | 6540 | 7933 | +1393 | +21.3 | 0 | 0 |
| `yun2024:356` | PMC5884950 | continuous | 2 | 19352 | 20650 | 22043 | +1393 | +6.75 | 2 | 0 |
| `yun2024:523` | PMC5325897 | continuous | 6 | 6811 | 7811 | 9204 | +1393 | +17.83 | 2 | 0 |
| `yun2024:525` | PMC5325897 | continuous | 6 | 6811 | 7811 | 9204 | +1393 | +17.83 | 2 | 0 |
| `yun2024:557` | PMC3136370 | continuous | 6 | 13122 | 14124 | 15517 | +1393 | +9.86 | 1 | 0 |
| `yun2024:559` | PMC3136370 | continuous | 6 | 13122 | 14139 | 15532 | +1393 | +9.85 | 1 | 0 |
| `yun2024:624` | PMC3493722 | binary | 2 | 5258 | 6268 | 7661 | +1393 | +22.22 | 0 | 0 |
| `yun2024:625` | PMC3493722 | binary | 2 | 5258 | 6268 | 7661 | +1393 | +22.22 | 0 | 0 |

Summe: 121747 -> 139856 Zeichen (+18109). Der Anker kostet 1393 Zeichen je Aufruf, also rund 14.9 Prozent eines durchschnittlichen Prompts dieser Gruppe; gegenueber der ersten Fassung (884 Zeichen) sind das +509 Zeichen je Aufruf.

## Was der Anker aendert und was nicht

- Er aendert nur die Prompt-Oberflaeche: Quelle, Zeilenlabel und beide Spaltenkoepfe muessen vor den Zellen benannt werden, alle Zellen stammen aus dieser einen Zeile, und die Suche endet am Anker. Die Extraktionsregeln, die Feldliste und der Zeitpunktzwang bleiben unveraendert; der Anker uebernimmt die v2-Regel, bei fehlendem Zielzeitpunkt Zellen wegzulassen statt einen anderen Zeitpunkt einzusetzen.
- Neu ist die Pruefung vor der Antwort: der genannte Quelltext muss den Zielzeitpunkt nennen und fuer jede Zelle deren Feld drucken; sonst bleibt die Zelle weg, statt die naechstbeste Zeile zu nehmen. Das haette im Aufruf vom 20.11. auf `yun2024:559` die Zellen aus der Separationsanalyse-Tabelle verhindert.
- Neu ist ausserdem, dass `chosen_timepoint` und `discarded_timepoints` ausdruecklich verlangt werden, auch bei leerer Zellenliste. Der erste Anker hatte sie verdraengt.
- Er beantwortet nicht die Frage, ob der Anker den Reasoning-Verbrauch senkt. Das ist eine Hypothese; ohne Aufruf ist die Wirkung nicht gemessen. Gemessen ist nur die Prompt-Laenge.
- Fuer die sechs Records ohne Tabellentext im Markdown greift Regel 1 auf den Satz zurueck; der Anker verlangt dort keine Tabelle, die es nicht gibt.
- Die Laenge ist fuer die kurzen Dokumente der Gruppe der groesste relative Eingriff (bis +21,8 Prozent), fuer die langen der kleinste (+4,7 Prozent). Absolut ist der Zuwachs in allen 13 Faellen identisch.
- Ein spaeterer Lauf braucht genau eine freigegebene Aenderung: den Ankerblock im Prompt. Das Abbruchkriterium bleibt `content_chars > 0` und `finish_reason = stop`.

Die SHA256-Summen je Prompt stehen in `tabellenanker_20261120.json`; damit ist nachpruefbar, dass nur der Anker hinzugekommen ist.
