# Tabellenanker-Prompt fuer die 13 Budgetfaelle (20.11.2026)

Trockenbau, kein Modellaufruf. Basis ist der echte Prompt-Bauer des Harness (`build_prompt`, Version `v2_timepoint`) mit demselben Markdown, das der P5-Lauf gelesen hat. Der Ankerblock wird angehaengt; der bestehende Prompt bleibt Zeichen fuer Zeichen erhalten.

## Ankerblock (884 Zeichen)

```text
Table anchor (binding, before any cell):
1. Name the one place that reports this outcome: the table caption (table number and title) or, if the outcome is reported only in prose, the sentence. Copy it character for character.
2. Add "anchor" as the first key: {"source": "<caption or sentence>", "row": "<row label exactly as printed>", "intervention_column": "<column head of the intervention arm>", "comparator_column": "<column head of the comparator arm>"}.
3. Every cell must come from this one row and this one time point. Never combine two rows, two populations or two tables.
4. If that row reports the target time point, answer immediately and do not search another candidate.
5. If it does not report the target time point, return an empty cell list and name its label in "discarded_timepoints"; never substitute another time point.
Do not describe tables you did not use.
```

## Prompt-Laenge je Record

| Record | Dokument | Typ | Gold | Text | Prompt alt | Prompt neu | Delta | Delta % | Tabelle | Pipe-Zeilen |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:119` | PMC4323894 | continuous | 4 | 10032 | 11045 | 11929 | +884 | +8.0 | 0 | 0 |
| `yun2024:128` | PMC4493951 | binary | 4 | 7954 | 8970 | 9854 | +884 | +9.86 | 2 | 0 |
| `yun2024:152` | PMC5055753 | binary | 4 | 7782 | 8788 | 9672 | +884 | +10.06 | 1 | 0 |
| `yun2024:164` | PMC5062234 | continuous | 2 | 3808 | 4897 | 5781 | +884 | +18.05 | 0 | 0 |
| `yun2024:273` | PMC3214395 | continuous | 2 | 3360 | 4436 | 5320 | +884 | +19.93 | 0 | 0 |
| `yun2024:304` | PMC4357072 | binary | 4 | 5515 | 6540 | 7424 | +884 | +13.52 | 0 | 0 |
| `yun2024:356` | PMC5884950 | continuous | 2 | 19352 | 20650 | 21534 | +884 | +4.28 | 2 | 0 |
| `yun2024:523` | PMC5325897 | continuous | 6 | 6811 | 7811 | 8695 | +884 | +11.32 | 2 | 0 |
| `yun2024:525` | PMC5325897 | continuous | 6 | 6811 | 7811 | 8695 | +884 | +11.32 | 2 | 0 |
| `yun2024:557` | PMC3136370 | continuous | 6 | 13122 | 14124 | 15008 | +884 | +6.26 | 1 | 0 |
| `yun2024:559` | PMC3136370 | continuous | 6 | 13122 | 14139 | 15023 | +884 | +6.25 | 1 | 0 |
| `yun2024:624` | PMC3493722 | binary | 2 | 5258 | 6268 | 7152 | +884 | +14.1 | 0 | 0 |
| `yun2024:625` | PMC3493722 | binary | 2 | 5258 | 6268 | 7152 | +884 | +14.1 | 0 | 0 |

Summe: 121747 -> 133239 Zeichen (+11492). Der Anker kostet 884 Zeichen je Aufruf, also rund 9.4 Prozent eines durchschnittlichen Prompts dieser Gruppe.

## Was der Anker aendert und was nicht

- Er aendert nur die Prompt-Oberflaeche: Quelle, Zeilenlabel und beide Spaltenkoepfe muessen vor den Zellen benannt werden, alle Zellen stammen aus dieser einen Zeile, und die Suche endet am Anker. Die Extraktionsregeln, die Feldliste und der Zeitpunktzwang bleiben unveraendert; der Anker uebernimmt die v2-Regel, bei fehlendem Zielzeitpunkt Zellen wegzulassen statt einen anderen Zeitpunkt einzusetzen.
- Er beantwortet nicht die Frage, ob der Anker den Reasoning-Verbrauch senkt. Das ist eine Hypothese; ohne Aufruf ist die Wirkung nicht gemessen. Gemessen ist nur die Prompt-Laenge.
- Fuer die sechs Records ohne Tabellentext im Markdown greift Regel 1 auf den Satz zurueck; der Anker verlangt dort keine Tabelle, die es nicht gibt.
- Die Laenge ist fuer die kurzen Dokumente der Gruppe der groesste relative Eingriff (bis +21,8 Prozent), fuer die langen der kleinste (+4,7 Prozent). Absolut ist der Zuwachs in allen 13 Faellen identisch.
- Ein spaeterer Lauf braucht genau eine freigegebene Aenderung: den Ankerblock im Prompt. Das Abbruchkriterium bleibt `content_chars > 0` und `finish_reason = stop`.

Die SHA256-Summen je Prompt stehen in `tabellenanker_20261120.json`; damit ist nachpruefbar, dass nur der Anker hinzugekommen ist.
