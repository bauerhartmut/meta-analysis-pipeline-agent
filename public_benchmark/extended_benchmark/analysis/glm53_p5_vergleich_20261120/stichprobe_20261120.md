# Stichprobe fuer die Kette (20.11.2026)

Quelle: `D:/daswu/AIResearch/public_benchmark/extended_benchmark/runs/yun699_p5_24000_20261118/predictions.jsonl`. Leere P5-Records: **33**.

## Warum gelockert

Die strenge Fassung (Wochenlabel im Ausschnitt) trifft **0 von 33** Records. Gruende ueber alle 33: 25 ohne Score-Zeile, 30 ohne Wochenlabel, 8 mit binaerem Outcome, 3 mit nur einem Stueck. Die Kette braucht aber nur eine Zeile mit Outcome-Wert, also wird das Wochenlabel protokolliert statt verlangt.

## Kriterien

1. Record ohne Inhalt im P5-Lauf.
2. Zwei Stuecke (Prosa plus Tabellenfenster).
3. Mindestens eine Score-Zeile im Ausschnitt.
4. Outcome-Typ `continuous`.
5. Noch nicht gemessen (yun2024:30 ausgenommen).
6. Je Dokument hoechstens zwei Records.

## Auswahl

| Record | Dokument | Outcome | Score-Zeilen | Wochenlabel | Gold im Ausschnitt | Prompt |
|---|---|---|---:|---|---:|---:|
| `yun2024:420` | PMC3877023 | quantitative contour sharpness of the  | 1 mean (SD) | nein | 4/6 | 6323 |
| `yun2024:421` | PMC3877023 | quantitative contour sharpness of the  | 1 mean (SD) | nein | 4/6 | 6321 |
| `yun2024:582` | PMC3504298 | Attentional Function | 9 Mean (SD) | nein | 1/1 | 6305 |
| `yun2024:671` | PMC4550271 | Community knowledge | 3 Mean (SD) | nein | 2/2 | 6241 |
| `yun2024:672` | PMC4550271 | Community knowledge | 3 Mean (SD) | nein | 2/2 | 6261 |

## Obergrenze der Bewertung bei 420 und 421

Bei `yun2024:420` und `yun2024:421` fehlen die Gruppengroessen im Ausschnitt
(18/21 bzw. 30/34 stehen nur ausserhalb der beiden Stuecke), die Mittelwerte
und Standardabweichungen liegen drin. Von sechs Goldzellen sind dort also nur
vier erreichbar: **F1 hoechstens 0,8**, auch bei fehlerfreiem Lauf. Ein Wert
unter 0,8 misst den Lauf, ein Wert von 0,8 misst nur die Abdeckung.

## Kosten

Gemessen auf yun2024:30: 8.003 Tokens Stufe 1, 3.262 Tokens Stufe 2, zusammen 11265.
Fuenf Records: erwartet **56325** Completion-Tokens.
Obergrenze bei ausgeschoepftem Budget (16.000 + 8.000 je Record): **120000** Tokens.

Die 33 Records haben im P5-Lauf ihr Budget im Reasoning verbraucht; die Obergrenze ist deshalb der erwartbare Worst Case.

## Offen vor dem Lauf

Nur yun2024:30 traegt ein Wochenlabel. Fuer die anderen vier muss Stufe 2 ohne Wochenblock auskommen (eine Tabelle, ein Block) und der Ausschnitt je Record offline geprueft werden.

