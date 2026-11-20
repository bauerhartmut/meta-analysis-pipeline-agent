# Satz-Locator auf yun2024:421: der Abbruch gehoert zum Text, nicht zu 420 (20.11.2026)

Ein freigegebener Aufruf, der wegen zweier Transportfehler dreimal gestartet
werden musste (siehe „Der Weg zum Messpunkt“). Modell `gwdg/glm-5.3`,
Satz-Locator (`stage1_satz`), Budget 16.632, Temperatur 0, Lesezeit 900 s.
Rohdaten: `predictions_satz_421_16632.jsonl` (Messpunkt) und
`predictions_satz_421_16632_503_fehler.jsonl` (erster Versuch).

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **abgebrochen** (`finish_reason = length`) |
| Completion-Tokens | **16.632** (Budget vollstaendig verbraucht) |
| Reasoning-Zeichen | **69.265** |
| Inhalt | **0 Zeichen**, 0 Locators |
| Dauer | 542,86 s |
| Prompt | 7.311 Zeichen (Ausschnitt 6.000, Regeln 1.311) |
| Goldwerte im Ausschnitt | **6/6** |

## Die Gegenueberstellung, die die Frage beantwortet

| Record | Outcome | Prompt | Ausschnitt | Tokens | Reasoning | Dauer | Ergebnis |
|---|---|---|---:|---:|---:|---:|---|
| 420 | contour sharpness, **cervicothoracic** spine | 7.313 | 15.500–21.500 | 16.632 | 66.006 | 57,73 s | abgebrochen |
| **421** | contour sharpness, **thoracolumbar** spine | 7.311 | 15.500–21.500 | 16.632 | 69.265 | 542,86 s | **abgebrochen** |

Beide Records stammen aus **PMC3877023** (26.274 Zeichen), und die Fensterwahl
greift bei beiden auf **denselben Ausschnitt** zu: Zeichen 15.500 bis 21.500,
39 bzw. 40 Outcome-Treffer, 0 Pipe-Zeilen, je 6/6 Goldwerte im Ausschnitt. Das
Modell hat also zweimal **denselben Text** gesehen; unterschiedlich waren nur die
Kontextzeilen (Intervention, Comparator, Outcome) und damit der Name der
Wirbelsaeulenregion.

**Antwort auf die Frage: Der Abbruch ist keine Eigenheit von 420.** Er tritt bei
421 mit derselben Fassung, demselben Budget und demselben Ausschnitt genauso auf.
Mit zwei Records aus einer Publikation ist das Ausmass aber genau das: der
Abbruch haengt an **diesem Ausschnitt** (und an diesem Modell), nicht am
einzelnen Record. Ob die ganze Publikation betroffen ist, ist damit nicht
gemessen - beide Proben teilen sich denselben Text, eine dritte Stelle des
Dokuments wurde nicht geprueft.

## Was jetzt ausgeschlossen ist

Auf dem Text 15.500–21.500 von PMC3877023 sind drei Fassungen mit Budget 16.632
gemessen, alle ohne einen Zeichen Inhalt:

| Fassung | Record | Tokens | Ergebnis |
|---|---|---:|---|
| Zeilenlabel + Zusatzsatz | 420 | 16.632 | abgebrochen |
| Satz-Locator | 420 | 16.632 | abgebrochen |
| Satz-Locator | 421 | 16.632 | abgebrochen |

Damit sind fuer diesen Text ausgeschlossen: zu kurzer Ausschnitt (6/6 Werte
gedruckt), Schema-Zwang zur Zeilenlabel-Entscheidung (Satz-Fassung bricht auch
ab) und Record-Eigenheit (421 bricht auch ab). Der P5-Lauf mit dem **vollen
Dokument** brach auf 420 ebenfalls ab; die volle Laenge hilft dort also auch
nicht.

## Der Weg zum Messpunkt

Drei Starts, ein Messpunkt - das gehoert zum Ergebnis, weil zwei davon
Transportfehler waren und nicht als Abbruch zaehlen duerfen:

| Versuch | Ergebnis | Tokens | Dauer |
|---|---|---:|---:|
| 1 | dreimal HTTP **503**, keine Antwort | keine (`null`) | 4,75 s je Versuch |
| 2 | **TimeoutError** der Socket-Lesezeit nach 300 s | keine (`null`) | 300,08 s |
| 3 (Lesezeit 900 s) | abgebrochen, `finish_reason = length` | 16.632 | 542,86 s |

Versuch 2 zeigt eine Grenze des Runners, nicht des Modells: `rx._call_once`
liest mit fester Lesezeit von 300 s. Derselbe Aufruf brauchte im dritten Versuch
542,86 s bis zum Budget - mit 300 s waere er nie zu einem Ergebnis gekommen.
Zwei Aenderungen am Analyse-Skript `zweistufig_satz_20261120.py` sind daraus
geworden:

1. `--timeout` setzt die Lesezeit je Versuch (Default bleibt 300 s).
2. Ein Aufruf ohne Modellkontakt (HTTP-Fehler oder `completion_tokens = null`)
   wird als `status = fehler` mit `transport_fehler = true` geschrieben, nicht
   als `abgebrochen`. Sonst zaehlt ein 503 als Abbruch am Tokenlimit und die
   Messreihe wird still verfaelscht.

Der erste Versuch liegt deshalb getrennt in `predictions_satz_421_16632_503_fehler.jsonl`.

## Kosten

Gemessene Completion-Tokens: 80.641 (bisherige Reihe) + 16.632 = **97.273**.
Die Versuche 1 und 2 haben keine Tokens zugerechnet bekommen; ob der Anbieter
serverseitig gerechnet hat, ist aus den Antworten nicht ablesbar.

## Grenzen

- **n = 1** Messpunkt je Zelle; die Dauer unterscheidet sich zwischen 420 und 421
  um Faktor 9 (57,73 s gegen 542,86 s) bei identischer Tokenzahl - die
  Wanduhrzeit ist offensichtlich kein Mass fuer den Rechenaufwand.
- Beide Proben liegen auf **demselben Ausschnitt**; „Publikation“ ist damit
  nicht belegt, nur „dieser Text“. Ein anderer Ausschnitt aus PMC3877023 wurde
  nicht gemessen.
- Der Abbruch ist an Tokens, Reasoning-Zeichen und `finish_reason` gemessen. Die
  Denkschleife selbst ist nicht einsehbar.
