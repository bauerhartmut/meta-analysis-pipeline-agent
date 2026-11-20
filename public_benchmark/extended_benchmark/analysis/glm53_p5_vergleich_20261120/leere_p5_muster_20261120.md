# Die 33 leeren P5-Records: Zeigen sie das Muster von yun2024:523? (20.11.2026)

Rein lesende Auswertung. Quelle: `runs/yun699_p5_24000_20261118/predictions.jsonl`
(33 Zeilen mit `content_chars = 0`), der Gold-Datensatz und die Dokumenttexte.
Kein Modellaufruf, keine Prediction geschrieben, kein Gold veraendert. Skript:
`leere_p5_muster_20261120.py`, Rohdaten: `leere_p5_muster_20261120.json`.

## Frage

Auf `yun2024:523` hat Stufe 1 das Budget im Reasoning verbraucht, weil das erste
Wertepaar in einem Satz mit mehreren Paaren steht und es dort kein Zeilenlabel
zum Zitieren gibt. Zeigen die 33 leeren P5-Records dieselbe Textlage?

## Messung

Je Record und je Goldwert wird geprueft, wo der Wert im Dokumenttext steht:

- **Tabellenzeile**: der Wert steht in einer Zeile, die als Pipe-Zeile beginnt.
- **Prosa, mehrere Paare**: der Wert steht in einem Satz mit mindestens zwei
  „+-“ oder mindestens vier Zahlen (zwei Werte je Arm) - dann gibt es keine
  eindeutige Zeile, sondern eine Kommaliste.
- **Prosa, ein Paar**: der Wert steht in einem Satz mit genau einem Wertepaar.
- **fehlt im Text**: kein Goldwert des Records steht im Text.

## Ergebnis

| Klasse | Records |
|---|---:|
| Prosa, mehrere Paare (Muster von 523) | **17** |
| fehlt im Text (kein Goldwert im Text) | **16** |
| Tabellenzeile | 0 |
| Prosa, ein Paar | 0 |
| Records mit mindestens einem fehlenden Goldwert | 30 |

Dazu eine harte Strukturtatsache: **in allen 33 Dokumenten gibt es keine einzige
Pipe-Zeile** (0 von 33). Der Markdown-Text, den die Pipeline dem Modell gibt,
enthaelt also nirgends ein Tabellengitter, an dem sich Zeile und Spalte
festmachen liessen - auch dort nicht, wo der Parser eine Tabelle erkennt
(Trenner sind Leerzeichen, nicht Pipes).

**Antwort auf die Frage: Ja, aber nur fuer die Haelfte der Faelle - und zwar
lueckenlos fuer die Haelfte, in der die Werte ueberhaupt im Text stehen.** Von
den 17 Records, in denen mindestens ein Goldwert im Text gedruckt ist, zeigen
**17 von 17** das 523-Muster: der Wert steht in einem Satz mit mehreren
Wertepaaren, nie in einer eigenen Tabellenzeile. Die anderen 16 haben gar keinen
Goldwert im Text (Werte nur in Bild-Tabellen oder Anhaengen, die die Extraktion
nicht mitnimmt); dort ist die Ursache eine andere, und ein Satz-Locator wuerde
dort `found: false` liefern muessen statt zu suchen.

Die 17 im Einzelnen: `30`, `52`, `119`, `159`, `173`, `204`, `251`, `420`,
`421`, `446`, `451`, `523`, `525`, `671`, `672`, `673`, `674`.

Damit ist die Hypothese H-A aus `p5_budgetdiagnose_20261120.md` („kein
Tabellenanker im kurzen Text“) praezisiert: Der fehlende Anker hat zwei Formen.
Entweder steht der Wert in einer Kommaliste ohne Zeilenlabel (17 Faelle, das
523-Muster) oder er steht ueberhaupt nicht im Text (16 Faelle). Ein Prompt, der
ein Zeilenlabel verlangt, hat in beiden Formen nichts zu zitieren.

## Grenzen

- Die Einordnung ist eine Heuristik auf Zeilen und Saetzen, keine Sichtpruefung
  jedes Falls. „Mehrere Paare“ heisst: mindestens zwei „+-“ oder mindestens vier
  Zahlen im selben Satz; ein Satz mit vier Zahlen, die keine Wertepaare sind,
  wuerde falsch eingeordnet.
- Die Tabellenzeilen-Pruefung kann in diesen Dokumenten nie anschlagen, weil
  keine Pipe-Zeilen existieren. „0 Tabellenzeilen“ heisst daher nicht, dass die
  Originaldokumente keine Tabellen haben - nur, dass der extrahierte Text kein
  Gitter enthaelt.
- Die 33 sind keine Zufallsstichprobe: es sind genau die Records, die im P5-Lauf
  ohne Inhalt endeten. Ueber die 666 uebrigen Records sagt die Auswertung
  nichts.
- Der Zusammenhang ist beschreibend, und die Kausalitaet ist praeziser als hier
  zuerst formuliert: Nicht der fehlende Anker allein loest den Abbruch aus,
  sondern das Abwaegen darueber. Auf 523 antwortet die **alte** Zeilenlabel-Fassung
  in 3.318 Tokens, sobald der Zusatz „Answer without weighing alternative
  readings.“ im Prompt steht; ohne ihn verbrannte sie 16.632. Die fehlende
  Zeilenlabel-Struktur ist also der Ausloeser der Denkschleife, nicht ihre
  Ursache im engeren Sinn. Siehe `zweistufig_lauf_20261120/satz_523_ergebnis_20261120.md`.
- Die Zuordnung der 17 Records zum Muster beruht auf Textlage, nicht auf einem
  Aufruf je Record; ob sie ohne Zusatz wirklich abbrechen wuerden, ist für keinen
  dieser 17 ausser 523 und 525 gemessen.
