# Zeilenlabel mit Zusatzsatz auf yun2024:421: das 2x2 ist voll, alle vier Zellen brechen ab (20.11.2026)

Ein freigegebener Aufruf, der erst im dritten Anlauf einen Modellkontakt bekam
(siehe „Transport“). Modell `gwdg/glm-5.3`, Zeilenlabel-Fassung
(`stage1_ankerlos`) mit dem Zusatz „Answer without weighing alternative
readings.“, Budget 16.632, Temperatur 0, Lesezeit 900 s, Prompt 7.229 Zeichen.
Rohdaten: `predictions_421_zusatz_16632.jsonl`; Skript
`../zweistufig_lauf_20261120.py`.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **abgebrochen** (`finish_reason = length`) |
| Completion-Tokens | **16.632** (Budget vollstaendig verbraucht) |
| Reasoning-Zeichen | **69.403** |
| Inhalt | **0 Zeichen**, 0 Locators |
| Dauer | 318,33 s |
| Goldwerte im Ausschnitt | **6/6** |

## Das 2x2 fuer PMC3877023

Beide Records liegen auf demselben Ausschnitt (Zeichen 15.500–21.500 von
26.274), denselben 6.000 Zeichen, 6/6 Goldwerte im Prompt. Unterschiedlich ist
nur das Schema (Zeilenlabel gegen Satz-Zitat) und der Outcome-Name
(cervicothoracic gegen thoracolumbar).

| Record | Schema | Tokens | Reasoning | Dauer | Ergebnis |
|---|---|---:|---:|---:|---|
| 420 | Zeilenlabel + Zusatz | 16.632 | 69.175 | 61,19 s | abgebrochen |
| **421** | **Zeilenlabel + Zusatz** | **16.632** | **69.403** | **318,33 s** | **abgebrochen** |
| 420 | Satz-Locator | 16.632 | 66.006 | 57,73 s | abgebrochen |
| 421 | Satz-Locator | 16.632 | 69.265 | 542,86 s | abgebrochen |

**Ergebnis: 4 von 4 Zellen brechen ab, jede mit dem vollen Budget und ohne ein
Zeichen Inhalt.** Das Schema entscheidet hier nichts: weder das Zeilenlabel noch
das Satz-Zitat noch der Zusatzsatz bringen auf diesem Text eine Antwort. Damit
ist die Schema-Hypothese fuer diese Publikation erledigt; der Faktor liegt im
Text (bzw. im Modell auf diesem Text), nicht in der Anweisung.

## Der auffaellige Gleichlauf

Die vier Zellen verbrauchen zwischen 66.006 und 69.403 Reasoning-Zeichen - eine
Spanne von 5 % bei vier unabhaengigen Aufrufen, davon zwei mit anderem Schema.
Die Wanduhrzeiten streuen dagegen um Faktor 9 (57,73 s bis 542,86 s) bei
identischer Tokenzahl. Der Rechenaufwand ist also stabil, die Zustellrate des
Anbieters nicht.

Das stuetzt die Deutung „Denkschleife ueber denselben Text“: haette das Schema
die Ursache gesetzt, muesste die Reasoning-Menge zwischen Zeilenlabel und Satz
auseinanderlaufen.

## Was fuer diesen Text jetzt ausgeschlossen ist

| Ausschluss | Beleg |
|---|---|
| zu kurzer Ausschnitt | 6/6 Goldwerte im Prompt, beide Records |
| Zeilenlabel-Zwang | Satz-Locator bricht auf 420 und 421 ab |
| Abwaegen der Lesarten | Zusatzsatz vorhanden, bricht trotzdem ab |
| Record-Eigenheit | 420 und 421 verhalten sich gleich |
| volles Dokument statt Fenster | P5 brach auf 420 mit vollem Text ebenfalls ab |

Nicht ausgeschlossen und nicht gemessen: ein anderer Ausschnitt derselben
Publikation, ein anderes Modell, ein anderes Budget.

## Transport

Der Anbieter war waehrend dieser Messung gestoert; drei Anlaeufe waren noetig,
nur der letzte erreichte das Modell:

| Anlauf | Ergebnis | Tokens |
|---|---|---|
| 1 | 504, dann zweimal 503 (`ServiceUnavailableError`) | keine |
| 2 | dreimal 503 | keine |
| 3 | erster Versuch 504 nach rund 8 min, zweiter Versuch HTTP 200 und Budgetabbruch | 16.632 |

Die Anlaeufe 1 und 2 liegen als `predictions_421_zusatz_16632_fehler504_503.jsonl`
und `..._fehler503_b.jsonl` daneben und zaehlen **nicht** als Abbruch. Die
Fehlerzeilen tragen `status = fehler` und `transport_fehler = true`; das ist die
Korrektur aus `satz_421_ergebnis_20261120.md`, die hier auch im
Zeilenlabel-Runner greift. Der erste 504 kam nach acht Minuten - also vom
Gateway, nicht von meiner Lesezeit; `--timeout 900` hat den zweiten Versuch
durchgelassen, der bei 300 s abgeschnitten worden waere.

## Kosten

Gemessene Completion-Tokens: 97.273 (bisherige Reihe) + 16.632 = **113.905**.
Die sechs fehlgeschlagenen HTTP-Versuche haben keine Tokens zugerechnet
bekommen; serverseitiger Verbrauch ist nicht ablesbar.

## Grenzen

- **n = 1** je Zelle. Vier Zellen auf einem Ausschnitt einer Publikation; die
  Aussage gilt fuer diesen Text, nicht fuer alle 33 leeren P5-Records.
- Beide Records sehen denselben 6.000-Zeichen-Ausschnitt; „die Publikation“ ist
  damit nicht belegt, nur „dieser Text aus dieser Publikation“.
- Der 504 im dritten Anlauf zeigt, dass der Anbieter denselben Prompt auch
  serverseitig abbrechen kann. Ob der erfolgreiche Versuch inhaltlich dasselbe
  gerechnet hat, ist nicht pruefbar - die Denkspur ist nicht einsehbar.
