# Satz-Locator auf yun2024:420: Abbruch auch ohne Zeilenlabel-Entscheidung (20.11.2026)

Ein freigegebener Aufruf. Modell `gwdg/glm-5.3`, Satz-Locator (`stage1_satz`),
Budget 16.632, Temperatur 0, gleicher Ausschnitt wie in allen 420-Laeufen
(6.000 Zeichen, Start 15.500 von 26.274). Prompt 7.313 Zeichen (Ausschnitt 6.000,
Regelteil 1.313). Rohdaten: `predictions_satz_420_16632.jsonl`, Skript
`../zweistufig_satz_20261120.py`.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **abgebrochen** (`finish_reason = length`) |
| Completion-Tokens | **16.632** (Budget vollstaendig verbraucht) |
| Reasoning-Zeichen | **66.006** |
| Inhalt | **0 Zeichen**, 0 Locators (`parse_fehler = leer`) |
| Dauer | 57,73 s |
| Goldwerte im Ausschnitt | **6/6** |
| Prompt-SHA256 | `f7bc1167...b5b2` |

Kein zweiter Versuch; das Abbruchkriterium (`content_chars == 0 oder
finish_reason == "length"`) ist erfuellt.

## Was der Aufruf beantworten sollte

Bei 420 steht die Zielzahl in einem Satz mit zwei gleichberechtigten
Schnittstellen (0,95/0,24 gegen 1,43/0,48 und 0,83/0,22 gegen 1,32/0,51), ohne
gedrucktes Zeilenlabel. Die Hypothese war: der Zeilenlabel-Zwang
(„ein Label je Arm“) erzeugt die Denkschleife, ein Satz-Zitat beendet sie, weil
der Satz beide Kandidaten enthaelt.

**Diese Hypothese ist fuer 420 widerlegt.** Der Satz-Locator bricht genauso ab
wie die Zeilenlabel-Fassung mit Zusatzsatz - gleiches Budget, gleiches
Abbruchkriterium, gleiche Reasoning-Groessenordnung:

| Fassung auf 420 | Tokens | Reasoning-Zeichen | Ergebnis |
|---|---:|---:|---|
| Zeilenlabel + Zusatzsatz | 16.632 (voll) | 69.175 | abgebrochen, 0 Zeichen |
| **Satz-Locator** | **16.632 (voll)** | **66.006** | **abgebrochen, 0 Zeichen** |

## Was der Vergleich mit 523 sagt

Derselbe Satz-Locator, derselbe Regelteil, gleiches Budget, Erfolg auf 523:
2.342 Tokens, 2 Locators, Satz woertlich im Ausschnitt. Der Unterschied liegt
damit nicht im Schema, sondern im Record:

| Record | Goldzellen | Goldwerte im Ausschnitt | Pipe-Zeilen | Satz-Locator |
|---|---:|---:|---:|---|
| 523 | 4 | 3/4 | 0 | ok, 2.342 Tokens |
| 420 | 6 | 6/6 | 0 | abgebrochen, 16.632 Tokens |

Der Prompt unterscheidet sich nur um 48 Zeichen (7.265 gegen 7.313). Die
Abdeckung ist bei 420 besser (6/6 gegen 3/4), trotzdem bricht er ab. Die
Kandidaten-Hypothese in der Form „das Schema muss sich zwischen zwei
gleichberechtigten Kandidaten entscheiden“ traegt nicht: 420 scheitert auch,
wenn das Schema die Entscheidung gar nicht verlangt.

Damit stehen fuer 420 drei Messungen mit demselben Ausschnitt und demselben
Budget: Zeilenlabel ohne Zusatz, Zeilenlabel mit Zusatz, Satz-Locator - alle drei
verbrauchen das volle Budget ohne einen Zeichen Inhalt. Fuer 523 trennt dagegen
genau der Zusatzsatz zwischen Abbruch und Antwort. Der Unterschied ist
record-spezifisch und mit den vorhandenen Messungen nicht erklaert.

**Nachtrag 20.11.2026:** Der Befund ist mit demselben Prompt (identischer
SHA256 `f7bc1167...b5b2`) und `qwen3.5-397b` aufgeloest - der Abbruch ist
modellspezifisch, nicht recordspezifisch. qwen liefert zwei Locators und den
Satz mit allen vier erreichbaren Goldwerten; siehe
`qwen_420_ergebnis_20261120.md`.

## Kosten

Gemessene Completion-Tokens dieser Reihe: 26.121 + 268 + 3.318 + 1.038 + 16.632 +
16.632 + 16.632 = **80.641** (Summe der in den Predictions gespeicherten
`completion_tokens`, auf ganze Tokens gerundet wie dort). Eingabetokens sind
nicht budgetiert und hier nicht enthalten.

## Grenzen

- **n = 1** Aufruf je Zelle; eine Wiederholung koennte anders ausgehen (der
  P5-Lauf zeigt diese Varianz: 5 von 13 Abbruechen lieferten im Nachzug Zellen).
- Der Abbruch ist nur an Tokens, Reasoning-Zeichen und `finish_reason`
  gemessen. Das Modell liefert keinen Text, die Inhalte der Denkschleife sind
  nicht einsehbar - „record-spezifisch“ ist eine Beschreibung, keine Ursache.
- Die beiden Records kommen aus verschiedenen Publikationen (420/421 aus
  PMC3877023, 523/525 aus PMC5325897); ein Vergleich ueber Dokumente hinweg
  kontrolliert weder Abschnittslaenge noch Tabellenlage.
