# Zeilenbindung mit Zeilengruppen-Achse (21.11.2026)

Die Regel ist aus yun2024:30 abgeleitet, goldfrei und ohne Netzaufruf. Neu
gegenueber der ersten Fassung sind vier Punkte:

1. Zeilengruppe als eigene Achse: die kurze Ueberschrift ueber der Datenzeile
   (`PCS`, `MCS`, `Physical Functioning`) wird gelesen und gegen die
   Outcome-Worte geprueft.
2. Spaltenraster als Filter vor der Auswahl: nur Zeilen, ueber denen eine
   Armzeile mit genau so vielen Spalten wie Wertepaare steht. Fortsetzungs-
   zeilen wie `+ MTX` und Groessenzeilen `(n = ...)` sind keine Armzeile.
3. Armnamen mit Alias: `Control` im Record trifft `PBO`/`placebo` in der
   Tabelle; `Certolizumab 200 mg` trifft `CZP 200 mg` ueber die Dosis.
4. Zeitpunkt: nennt der Record eine Regel statt eines Datums, gilt der letzte
   Wochenblock - so steht es in der Zeitpunktregel selbst.

Zwei Varianten des Stichentscheids: `streng` verweigert, wenn mehrere Zeilen
gleich gut passen; `erstes` nimmt die erste bindungsfaehige Zeile in
Dokumentreihenfolge, also die erste Gruppe der Tabelle.

## Record 30: trifft die Regel die Goldzellen?

| Variante | gebunden | Zeile | Gruppe | Block | Zellen | Goldtreffer |
|---|---|---:|---|---:|---:|---:|
| streng | nein | - | - | - | 0 | 0/6 |
| erstes | ja | 70 | PCS | 2 | 6 | 6/6 |

Variante `erstes` liefert 6 von 6 Goldzellen:
Mittelwert, Streuung und Gruppengroessen beider Arme, Woche 52, Gruppe PCS.
Blockbegruendung: letzter Block laut Zeitpunktregel.
`streng` verweigert hier, weil der Kontext weder PCS noch MCS nennt - die
Gruppenachse loest den Fall also nur mit dem Reihenfolge-Stichentscheid.

## Messung auf den 41 schweren Records

| Gruppenmodus | Anwendung | gebunden | neue TP | davon erreichbar | davon `fp_gebunden` | davon `fn_wert_ersetzt` | FP-Delta | TP-Verlust |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| streng | additiv | 1 | 1 | 0 | 0 | 0 | +5 | -1 |
| streng | ersetzen | 1 | 1 | 0 | 0 | 0 | +5 | -1 |
| erstes | additiv | 3 | 7 | 0 | 0 | 0 | +11 | -7 |
| erstes | ersetzen | 3 | 7 | 0 | 0 | 0 | +11 | -7 |


### Wohin die Aenderungen fallen (Gruppenmodus erstes, additiv)

- `yun2024:30`: 6 Zellen gebunden, davon 6 neu richtig; Phase-1-Klassen: fn_leer: 6
- `yun2024:446`: 6 Zellen gebunden, davon 1 neu richtig; Phase-1-Klassen: fn_leer: 6
- `yun2024:451`: 6 Zellen gebunden, davon 0 neu richtig; Phase-1-Klassen: fn_leer: 6

Der Zugewinn liegt ausschliesslich in `fn_leer`-Zellen: Record 30 mit 6 von 6
Zellen und eine Zelle in 446. Die erreichbaren `fp_gebunden`- und
`fn_wert_ersetzt`-Zellen bleiben unberuehrt, weil sie in Records liegen, die
die Regel nicht bindet. Der Gewinn ist also echt, aber nicht der gesuchte.

Erreichbar sind 26 der 33 Fehlerzellen der
Auswahl (24 mit Wert und Wort in einer Zeile,
2 mit dem Wort in den zehn Zeilen darueber,
7 ohne Outcome-Bezug).

## Je Record (Gruppenmodus erstes, additiv)

| Record | gebunden | Gruppe | Label bzw. Grund | TP/FP/FN vorher | TP/FP/FN nachher | Aenderungen |
|---|---|---|---|---|---|---:|
| `yun2024:30` | ja | PCS | Mean score (SD) | 0/0/6 | 6/0/0 | 6 |
| `yun2024:52` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:119` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/4 | 0/0/4 | 0 |
| `yun2024:128` | nein | - | Weight (kg) | 0/0/4 | 0/0/4 | 0 |
| `yun2024:152` | nein | - | Female | 0/0/4 | 0/0/4 | 0 |
| `yun2024:159` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:164` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:171` | nein | - | GAD antibody positivity[?]( ) [ n (% | 0/0/4 | 0/0/4 | 0 |
| `yun2024:173` | nein | - | GAD antibody positivity[?]( ) [ n (% | 0/0/4 | 0/0/4 | 0 |
| `yun2024:204` | nein | - | ? Na?ve (%) | 0/0/2 | 0/0/2 | 0 |
| `yun2024:251` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/4 | 0/0/4 | 0 |
| `yun2024:252` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:273` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:304` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/4 | 0/0/4 | 0 |
| `yun2024:356` | nein | - | Caucasian/White | 0/0/2 | 0/0/2 | 0 |
| `yun2024:420` | nein | - | Cervicothoracic spine | 0/0/6 | 0/0/6 | 0 |
| `yun2024:421` | nein | - | Thoracolumbar spine | 0/0/6 | 0/0/6 | 0 |
| `yun2024:446` | ja | - | Waist circumference (cm) | 0/0/6 | 1/5/5 | 6 |
| `yun2024:451` | ja | Health and demograph | Age (years) | 0/0/6 | 0/6/6 | 6 |
| `yun2024:523` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:525` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:557` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:559` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:582` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:624` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:625` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:671` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:672` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:673` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:674` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/6 | 0/0/6 | 0 |
| `yun2024:678` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:685` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:687` | nein | - | keine Zeile mit Zahlenpaaren | 0/0/2 | 0/0/2 | 0 |
| `yun2024:113` | nein | - | Basic | 0/4/6 | 0/4/6 | 0 |
| `yun2024:357` | nein | - | Caucasian/White | 0/4/2 | 0/4/2 | 0 |
| `yun2024:362` | nein | - | keine Zeile mit Zahlenpaaren | 0/2/4 | 0/2/4 | 0 |
| `yun2024:533` | nein | - | keine Zeile mit Zahlenpaaren | 0/2/2 | 0/2/2 | 0 |
| `yun2024:615` | nein | - | keine Zeile mit Zahlenpaaren | 0/2/4 | 0/2/4 | 0 |
| `yun2024:616` | nein | - | keine Zeile mit Zahlenpaaren | 0/2/4 | 0/2/4 | 0 |
| `yun2024:626` | nein | - | keine Zeile mit Zahlenpaaren | 0/2/2 | 0/2/2 | 0 |
| `yun2024:686` | nein | - | keine Zeile mit Zahlenpaaren | 0/6/2 | 0/6/2 | 0 |

## Grenzen

- Der Stichentscheid `erstes` ist eine Annahme, keine Ableitung: wenn der
  Kontext keine Gruppe nennt, gewinnt die erste Gruppe der Tabelle. Auf
  Record 30 ist das PCS und trifft das Gold, weil Gold dort PCS nutzt; bei
  einem Record mit MCS-Gold waere dieselbe Regel falsch.
- Die 41 Records sind die schweren Faelle, nicht die Gesamtmenge: von den
  Fehlerzellen liegen nur 33 hier, davon 26 erreichbar.
- Die Regel bindet keinen Zeitpunkt in der Zelle und keine Gruppengroesse
  ausserhalb einer `(n = ...)`-Kopfzeile.
- Der Modus `ersetzen` kann TPs kosten; er ist getrennt ausgewiesen.
