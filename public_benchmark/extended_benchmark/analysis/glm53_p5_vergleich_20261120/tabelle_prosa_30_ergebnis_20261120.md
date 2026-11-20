# Tabellenfenster plus Prosa-Stueck auf yun2024:30 (20.11.2026)

Ein Aufruf der Stufe 1, Modell `gwdg/qwen3.5-397b`, Budget 16.000, Lesezeit
420 s. Ausschnitt: zwei Stuecke zu 2.000 Zeichen, blind gewaehlt.

| Stueck | Zeichen | Art | Inhalt |
|---|---|---|---|
| 1 | 5.391–7.391 | prose region | MCS-Satz mit `6.4, 6.4 and 2.1` (Week 52) und Caption der Tabelle |
| 2 | 7.641–9.641 | table region | eingeflachte Tabelle: `Mean score (SD)`, `Mean change from BL`, `% MCID` |

Prompt 5.563 Zeichen, SHA256 `3b725be37cae64c9…`. Vorab offline geprueft:
**6 von 6** Goldwerten liegen im Ausschnitt, alle im Tabellenfenster
(7.4, 9.5, 31.5, 38.1, 199.0, 393.0).

## Ergebnis

`ok`, `finish_reason = stop`, **8.174** Completion-Tokens, 235,88 s, 633 Zeichen
Inhalt, 2 Locators.

| Arm | Zeilenlabel | Spaltenkopf | Caption | Timepoint |
|---|---|---|---|---|
| intervention | `Mean change from BL` | `CZP 200 mg + MTX` | `Improvements in health-related quality of life at weeks 12, 24 and 52 (ITT population, LOCF)*` | `Week 52` |
| comparator | `Mean change from BL` | `PBO + MTX` | dieselbe | `Week 52` |

Woertlichkeitspruefung:

- Zeilenlabel `Mean change from BL` steht im Tabellenstueck (Position 8.428).
- Caption steht woertlich im Prosastueck (Position 7.043).
- Die Spaltenkoepfe sind im eingeflachten Text zellenweise umbrochen
  (`CZP 200 mg` / `+ MTX` / `PBO`); das Modell hat sie korrekt zusammengesetzt,
  aber nicht als zusammenhaengende Zeichenkette zitiert.

## Die gewaehlte Zeile ist nicht die Goldzeile

Im selben Tabellenstueck stehen zwei Zeilen untereinander:

```
Mean score (SD)      36.1 (8.9) … 38.1 (9.5) 38.9 (8.9) 31.5 (7.4)
Mean change from BL  5.8 (0.5)† 6.4 (0.6)† 0.7 (0.6) 7.7 (0.4)† 8.3 (0.4)† 1.8 (0.6) 7.8 (0.4)† 8.6 (0.4)† 1.7 (0.6)
```

Das Gold verlangt `38.1 (9.5)` fuer die Intervention und `31.5 (7.4)` fuer den
Comparator, also die Zeile **Mean score (SD)**. Das Modell nennt
**Mean change from BL** und damit die Zeile darunter (`7.8 / 1.7`). Der Fehler
ist damit erstmals eindeutig der Zeilenwahl zuzuordnen, nicht dem Ausschnitt:
die richtige Zeile war sichtbar, die Caption und der Zeitpunkt stimmen.

## Was das fuer die Kette heisst

- Das Tabellenfenster loest die Abdeckung: 6/6 statt 2/6 im Prosafenster.
- Der Locator findet Tabelle, Zeitpunkt und Arme, waehlt aber die falsche Zeile
  (`change` statt `score`). Eine Stufe 2 auf dieser Antwort wuerde 7,8 und 1,7
  extrahieren, also 0 von 6 Treffern bei 2 falschen Zellen.
- Fuer die Bewertung heisst das: der Record ist mit diesem Prompt nicht
  metrisch besser, aber der Fehler ist jetzt benannt und isoliert.

## Kosten

8.174 Completion-Tokens, 235,88 s. Gesamtstand der Reihe: 161.271 (bis 52) +
21.638 (Dreifenster-Serie) + 8.174 = **191.083** Completion-Tokens.

## Empfehlung

Die Zeilenwahl im Prompt binden: ausdruecklich verlangen, dass die Zeile den
Outcome-Wert selbst traegt (Score/Mittelwert) und nicht die Veraenderung, und
`Mean change` als eigene Zeile ausschliessen. Offline pruefbar ist nur, ob die
Zeile im Ausschnitt steht; ob das Modell sie waehlt, entscheidet ein Aufruf.
Vor einem weiteren Aufruf sollte die Frage gestellt werden, ob die
Zeilenbindung ueberhaupt per Prompt loesbar ist oder eine Stufe 2 mit
Zeilenkandidaten (Score vs. Change) noetig ist.
