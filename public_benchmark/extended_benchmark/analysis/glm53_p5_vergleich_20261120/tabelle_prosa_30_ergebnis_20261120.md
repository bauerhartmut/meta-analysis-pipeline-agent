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

## Zeilenbindung im Prompt (20.11.2026)

Dritter Aufruf, gleicher Ausschnitt wie im ersten (Prosastueck 5.391–7.391,
Tabellenfenster 7.641–9.641), aber mit einem bindenden Regelblock vor
`PROMPT_REGELN`: die Zeile muss den Outcome-Wert selbst tragen (Beispiel
`Mean score (SD)`, `Mean (SD)`, `Median (IQR)`, `n`), Aenderungszeilen
(`Mean change from BL`, `change`, `delta`, `difference`) sind als `zeilenlabel`
ausgeschlossen, und der Zeitpunktblock ist ueber seinen Spaltenkopf zu benennen.

Prompt 6.260 Zeichen, SHA256 `7ff0a5d60543f2e5…`. Offline vor dem Aufruf:

- Goldwerte im Ausschnitt **6/6**, alle im Tabellenstueck.
- Score-Zeile `Mean score (SD)` **3 Treffer**, alle im Tabellenstueck
  (Positionen 8.279, 8.857, 9.435 — PCS, MCS und die dritte Blockzeile).
- Zeitpunktlabel im Prosastueck: `Week 12`, `Week 24`, `Week 52` sowie die
  Caption `Improvements in health-related quality of life at weeks 12, 24 and 52`.

`ok`, `finish_reason = stop`, **8.003** Completion-Tokens, 223,76 s, 625 Zeichen,
2 Locators.

| Arm | Zeilenlabel | Spaltenkopf | Caption | Timepoint |
|---|---|---|---|---|
| intervention | `Mean score (SD)` | `CZP 200 mg + MTX` | `Improvements in health-related quality of life at weeks 12, 24 and 52 (ITT population, LOCF)*` | `Week 52` |
| comparator | `Mean score (SD)` | `PBO + MTX` | dieselbe | `Week 52` |

Die gewaehlte Zeile ist die Goldzeile: sie steht bei 8.279 und enthaelt
`38.1 (9.5)` und `31.5 (7.4)`; die Gruppengroessen `393` und `199` stehen in den
Spaltenkoepfen desselben Tabellenkopfs. Die Bindung greift also — nach zwei
Laeufen mit `Mean change from BL` waehlt das Modell dieselbe Tabelle nun in der
Score-Zeile, mit richtiger Caption und richtigem Zeitpunkt.

Offen bleibt die Spaltenblock-Zuordnung: der Spaltenkopf nennt nur den Arm,
nicht die Woche. In der Zeile stehen neun Werte (drei Bloecke zu je drei
Armen); das Gold liegt im dritten Block. Das ist Aufgabe der Stufe 2 und ohne
Extraktion hier nicht geprueft.

## Stufe 2 auf dem Zeilen-Locator (20.11.2026)

Der Stufe-1-Runner prueft das Zeilenlabel jetzt gegen die Stuecke; Tabellen-
Locators tragen damit `stueck = 2` statt `None` (nachgeprueft an der
gespeicherten Zeile mit `--pruefe-prediction`, ohne Netzaufruf).

Stufe 2 (`zweistufig_stufe2_zeile_20261120.py`) liest aus der benannten Zeile
nur den Block des Zielzeitpunkts: je Arm Mittelwert, Standardabweichung und
Gruppengroesse, sechs Zellen. Ausschnitt 514 Zeichen (Wochenzeile, Spaltenkopf,
Zeile), Prompt 1.885 Zeichen, Budget 8.000.

Offline nachgerechnet, bevor der Aufruf startete (`wochenblock`): die Zeile hat
neun Wertepaare, drei Bloecke zu drei Armen.

| Block | CZP 200 mg + MTX | CZP 400 mg + MTX | PBO + MTX |
|---|---|---|---|
| Week 12 | 36.1 (8.9) | 36.8 (8.4) | 30.7 (7.1) |
| Week 24 | 37.8 (9.5) | 38.4 (8.8) | 31.4 (7.3) |
| Week 52 | **38.1 (9.5)** | 38.9 (8.9) | **31.5 (7.4)** |

Beide Goldmittel liegen in `Week 52` (CZP 200 mg bzw. PBO), die Zuordnung ist
also eindeutig und nicht geschaetzt.

`ok`, `finish_reason = stop`, **3.262** Completion-Tokens, 814 Zeichen, 6 Zellen,
gelesener Block `Week 52`.

| Feld | Wert | im Ausschnitt gedruckt |
|---|---|---|
| intervention_mean | 38.1 | ja |
| intervention_standard_deviation | 9.5 | ja |
| intervention_group_size | 393 | ja |
| comparator_mean | 31.5 | ja |
| comparator_standard_deviation | 7.4 | ja |
| comparator_group_size | 199 | ja |

Bewertung gegen Gold: **TP 6, FP 0, FN 0, P 1.0, R 1.0, F1 1.0**. Das ist der
erste Record der Reihe, der die Kette bis zum Wert durchlaeuft, und der erste
mit vollstaendigem F1. Die 8.000 Tokens waren nicht ausgeschoepft (3.262).

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
- Mit dem bindenden Regelblock waehlt dasselbe Modell dieselbe Tabelle in der
  Goldzeile (`Mean score (SD)`, 3. Lauf). Damit ist die Zeilenbindung per
  Prompt geloest.
- Stufe 2 loest auch die Wochenspalte: Block `Week 52` gelesen, sechs Zellen,
  F1 1.0. Die Kette (Fenster, Zeile, Zeitpunkt, Wert) ist auf diesem Record
  vollstaendig und kostet 8.003 + 3.262 Tokens.

## Kosten

8.174 Completion-Tokens, 235,88 s fuer Tabellenfenster plus Prosastueck; 7.589
Tokens, 397,03 s fuer das Tabellenfenster allein; 8.003 Tokens, 223,76 s mit
Zeilenbindung; 3.262 Tokens, 87,8 s fuer Stufe 2. Gesamtstand der
Reihe: 161.271 (bis 52) + 21.638 (Dreifenster-Serie) + 8.174 + 7.589 + 8.003 +
3.262 = **209.937** Completion-Tokens.

## Empfehlung

Die Kette ist auf diesem Record geschlossen (F1 1.0, 11.265 Tokens fuer beide
Stufen). Naechster Hebel ist die Generalisierung: dieselbe Kette auf eine
kleine Stichprobe der 33 Records, nicht auf alle. Schaetzung (nicht gemessen):
bei rund 11.300 Tokens je Record kosten 5 Records etwa 57.000 Completion-Tokens,
alle 33 etwa 373.000. Fuenf Records zeigen, ob Zeilenbindung und Wochenblock
uebertragen; die volle Serie lohnt erst, wenn die Trefferquote der Stichprobe
steht.
