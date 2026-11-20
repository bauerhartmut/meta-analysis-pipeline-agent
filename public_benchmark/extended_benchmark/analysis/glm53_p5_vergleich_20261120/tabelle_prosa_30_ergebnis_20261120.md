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
liegt damit nicht am Ausschnitt — die richtige Zeile war sichtbar, Caption und
Zeitpunkt stimmen —, ist aber noch nicht allein der Zeilenwahl zuzuordnen.

## Confound: das Prosastueck enthaelt Aenderungswerte

Das Prosastueck (5.391–7.391) enthaelt den MCS-Satz mit `6.4, 6.4 and 2.1`
(Week 52). Das sind Veraenderungswerte, keine Score-Werte: sie stehen in der
Quelle als mittlere Aenderung gegenueber Baseline, nicht als Mittelwert der
Skala. Das Modell hat diese Zahlen also im Prompt gesehen, bevor es die Zeile
waehlte, und die gewaehlte Zeile heisst genau `Mean change from BL`. Damit sind
zwei Erklaerungen nicht trennbar:

1. Das Modell waehlt aus der Tabelle heraus die falsche Zeile.
2. Das Prosastueck hat die Aenderungszeile geprimt, weil es Aenderungswerte
   zeigt und der Score dort nicht vorkommt.

Die Aussage „Zeilenwahl statt Ausschnitt" gilt fuer die Abdeckung (6/6, alle
Werte sichtbar), nicht fuer die Ursache der falschen Zeile. Die Gegenprobe
unten (Tabellenfenster ohne Prosastueck) entscheidet, ob das Prosastueck die
Zeile geprimt hat.

## Gegenprobe: Tabellenfenster ohne Prosastueck

Zweiter Aufruf, gleiche Parameter (Budget 16.000, Modell qwen), Ausschnitt nur
7.641–9.641 (`table region`), Prompt 3.420 Zeichen, SHA256 `1c0cb7c203187286…`.
Offline geprueft: **6 von 6** Goldwerten im Ausschnitt, alle im Tabellenfenster;
`393` und `199` stehen dort in den Spaltenkoepfen.

`ok`, `finish_reason = stop`, **7.589** Completion-Tokens, 397,03 s, 459 Zeichen,
2 Locators.

| Arm | Zeilenlabel | Spaltenkopf | Caption | Timepoint |
|---|---|---|---|---|
| intervention | `Mean change from BL` | `CZP 200 mg + MTX (n = 393)` | — | — |
| comparator | `Mean change from BL` | `PBO + MTX (n = 199)` | — | — |

Damit ist der Confound ausgeraeumt: die Aenderungszeile wird auch ohne
Prosastueck gewaehlt, sie ist also nicht durch die Zahlen `6.4, 6.4 and 2.1`
geprimt, sondern Ergebnis der Zeilenwahl aus der Tabelle. Zugleich zeigt der
Lauf den Preis des Verzichts: ohne Prosastueck fehlen Caption und
Zeitpunktangabe (`timepoint` leer), weil die Wochenlabels nicht im Fenster
liegen. Eine Stufe 2 muesste den Zeitpunkt dann raten.

## Was das fuer die Kette heisst

- Das Tabellenfenster loest die Abdeckung: 6/6 statt 2/6 im Prosafenster.
- Der Locator findet Tabelle, Zeitpunkt und Arme, waehlt aber die falsche Zeile
  (`change` statt `score`). Eine Stufe 2 auf dieser Antwort wuerde 7,8 und 1,7
  extrahieren, also 0 von 6 Treffern bei 2 falschen Zellen.
- Fuer die Bewertung heisst das: der Record ist mit diesem Prompt nicht
  metrisch besser. Der Fehler ist lokalisiert (Tabelle gefunden, Zeile falsch),
  aber wegen des Confounds noch nicht kausal der Zeilenwahl zuzuschreiben.
- Die Gegenprobe verschiebt die Zuordnung: die falsche Zeile ist modellseitig
  (2 von 2 Laeufen mit Aenderungszeile, einer davon ohne Prosastueck). Das
  Prosastueck bleibt trotzdem noetig, weil nur dort Caption und Zeitpunkt
  stehen.

## Kosten

8.174 Completion-Tokens, 235,88 s fuer Tabellenfenster plus Prosastueck; 7.589
Tokens, 397,03 s fuer das Tabellenfenster allein. Gesamtstand der Reihe: 161.271
(bis 52) + 21.638 (Dreifenster-Serie) + 8.174 + 7.589 = **198.672**
Completion-Tokens.

## Empfehlung

Das Prosastueck bleibt im Prompt (Caption und Zeitpunkt), das Tabellenfenster
auch. Dazu die Zeile binden: ausdruecklich verlangen, dass die Zeile den
Outcome-Wert selbst traegt (Score/Mittelwert), und `Mean change` ausschliessen.
Offline ist nur pruefbar, dass die Score-Zeile im Ausschnitt steht; ob das
Modell sie waehlt, entscheidet ein Aufruf. Falls die Bindung per Prompt nicht
greift, ist die Alternative eine Stufe 2 mit zwei Zeilenkandidaten (Score vs.
Change), die den Zeitpunkt aus der Caption nimmt.
