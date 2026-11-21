# Zeilenbindung als Regel, offline gemessen (21.11.2026)

Die Regel ist aus dem Aufbau von yun2024:30 abgeleitet, goldfrei und ohne
Netzaufruf. Sie arbeitet in vier Schritten:

1. Datenzeile: eine Zeile mit Wertepaaren `Wert (SD)` und einem Zeilenlabel,
   das ein Outcome-Stammwort traegt. Aenderungszeilen (`mean change`,
   `delta`, `difference`) sind ausgeschlossen.
2. Spaltenraster: ueber der Zeile muss eine Armzeile mit genau so vielen
   Spaltenlabels stehen wie die Zeile Wertepaare hat, und eine Wochenzeile mit
   den Zeitpunktlabels. Das ist das Muster von Record 30 (`Week 12/24/52` ueber
   je drei Armen).
3. Block und Arm: der Zielzeitpunkt des Records waehlt den Wochenblock, die
   Spaltenlabels waehlen je Arm genau eine Spalte (Zahlen zaehlen mit, sonst
   waeren `CZP 200 mg` und `CZP 400 mg` nicht zu trennen).
4. Verweigerung: fehlt ein Raster, ist ein Arm nicht eindeutig oder gibt es
   zwei gleich gute Zeilen, wird nichts gebunden.

Geprueft auf 41 der 41 schweren Records. In dieser Auswahl
liegen 17 der 270 `fp_gebunden` und 16 der 295 `fn_wert_ersetzt`.

## Ergebnis

| Modus | gebunden | TP vorher | FP vorher | FN vorher | TP nachher | FP nachher | FN nachher | TP-Verlust |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| additiv | 0 | 0 | 24 | 158 | 0 | 24 | 158 | 0 |
| ersetzen | 0 | 0 | 24 | 158 | 0 | 24 | 158 | 0 |

Korrigiert wurden in der Auswahl:

| Modus | `fn_wert_ersetzt` richtig gebunden | `fp_gebunden` richtig gebunden |
|---|---:|---:|
| additiv | 0 | 0 |
| ersetzen | 0 | 0 |

Zwischenstand der Entwicklung, damit die Zahl einordenbar ist: eine erste,
lockere Fassung ohne Spaltenraster band 3 Records, davon 0 mit richtigem Wert,
und erzeugte 12 zusaetzliche FP. Die strenge Fassung bindet keinen. Beide
Ergebnisse sagen dasselbe: der Textabgleich findet Zeilen, aber nicht die
richtige Zelle.

## Obergrenze jeder Textzeilen-Bindung

Von den 33 Fehlerzellen der Auswahl liegen 24 in einer Zeile, die den Wert und ein Outcome-Wort traegt, 2 nur mit dem Wort in den zehn Zeilen darueber, 7 ohne Outcome-Bezug. Mehr als 26 Zellen kann eine textbasierte Zeilenbindung also grundsaetzlich nicht erreichen.

Erreicht hat die Regel 0. Der Grund ist nicht die Obergrenze, sondern die
Eindeutigkeit: dieselbe Tabelle enthaelt mehrere Zeilen mit demselben Label
(`Mean score (SD)` fuer PCS und MCS), und die Unterscheidung steht in einer
Zeilengruppen-Ueberschrift, die der Textabgleich nicht als eigene Achse liest.
Genau daran scheitert auch Record 30 selbst: das Label nennt den Outcome nicht
(der steht in der Caption), und die Goldzeile ist eine von zwei gleich
beschrifteten Zeilen.

## Je Record (Modus additiv)

| Record | gebunden | Zeilenlabel | TP/FP/FN vorher | TP/FP/FN nachher | Aenderungen |
|---|---|---|---|---|---:|
| `yun2024:30` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:52` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:119` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:128` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:152` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:159` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:164` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:171` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:173` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:204` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:251` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:252` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:273` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:304` | nein | - | 0/0/4 | 0/0/4 | 0 |
| `yun2024:356` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:420` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:421` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:446` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:451` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:523` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:525` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:557` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:559` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:582` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:624` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:625` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:671` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:672` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:673` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:674` | nein | - | 0/0/6 | 0/0/6 | 0 |
| `yun2024:678` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:685` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:687` | nein | - | 0/0/2 | 0/0/2 | 0 |
| `yun2024:113` | nein | - | 0/4/6 | 0/4/6 | 0 |
| `yun2024:357` | nein | - | 0/4/2 | 0/4/2 | 0 |
| `yun2024:362` | nein | Abstract Background: Cognitive impairmen | 0/2/4 | 0/2/4 | 0 |
| `yun2024:533` | nein | - | 0/2/2 | 0/2/2 | 0 |
| `yun2024:615` | nein | - | 0/2/4 | 0/2/4 | 0 |
| `yun2024:616` | nein | - | 0/2/4 | 0/2/4 | 0 |
| `yun2024:626` | nein | - | 0/2/2 | 0/2/2 | 0 |
| `yun2024:686` | nein | - | 0/6/2 | 0/6/2 | 0 |

## Was die Regel kann und was nicht

- Sie bindet nur, wenn Tabellenraster und Armspalten eindeutig sind. Das ist
  bewusst streng: eine falsche Bindung kostet eine Zelle und erzeugt eine FP,
  eine Verweigerung kostet nur den Versuch.
- Der Modus `ersetzen` kann TPs kosten; er ist deshalb nicht Standard. In
  dieser Auswahl trat der Fall nicht ein, weil nichts gebunden wurde.
- Die Regel ersetzt keine Modellentscheidung. Auf Record 30 hat das Modell die
  Zeile gewaehlt; die deterministische Regel muesste dieselbe Wahl ohne
  Semantik treffen und verweigert stattdessen.

## Grenzen

- Die Auswahl ist nicht repraesentativ fuer die 699 Records: es sind die
  schweren Faelle, in denen P5 leer blieb oder nichts traf. Von den 270
  `fp_gebunden` und 295 `fn_wert_ersetzt` liegen nur 17 und 16 hier.
- Die Zaehlung `richtig gebunden` prueft nur den Schluessel, nicht die
  Fundstelle; eine Zeile kann den Wert an der richtigen Stelle nennen und
  trotzdem die falsche Population sein.
- Kein Zeitpunkt in der Zelle: die Regel bindet keine `timepoint`-Angabe.
