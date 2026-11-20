# Zwei Aufrufe mit Ankerfassung 2: Ergebnis (20.11.2026)

Zwei freigegebene Aufrufe auf `yun2024:559` und `yun2024:615`, Modell und Budget wie
zuvor (`gwdg/glm-5.3`, 24.000 Completion-Tokens, Temperatur 0). Prompt =
`build_prompt` (`v2_timepoint`) plus Ankerfassung 2 (1.393 Zeichen, SHA256
`9c422225abfa...`), Label `v2_timepoint_anker2`. Abbruchkriterium unveraendert:
`content_chars == 0` oder `finish_reason == "length"`. Rohdaten:
`predictions_anker2.jsonl`.

## Ergebnis aller drei Fassungen

| Record | Fassung | Status | Completion-Tokens | Reasoning-Zeichen | Inhalt | Zellen | TP | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:559` | P5 (ohne Anker) | `length` | 24.000 | 89.528 | 0 | 0 | 0 | 0 | 6 |
| `yun2024:559` | Anker 1 | ok (`stop`) | 16.632 | 67.322 | 340 | 2 | 0 | 2 | 6 |
| `yun2024:559` | **Anker 2** | **`length`** | 24.000 | 98.896 | 0 | 0 | 0 | 0 | 6 |
| `yun2024:615` | P5 (ohne Anker) | ok | 17.518 | 70.114 | — | 2 | 0 | 2 | 4 |
| `yun2024:615` | Anker 1 | `length` | 24.000 | 98.472 | 0 | 0 | 0 | 0 | 4 |
| `yun2024:615` | **Anker 2** | **`length`** | 24.000 | 96.344 | 0 | 0 | 0 | 0 | 4 |

Kosten dieser Runde: 48.000 Completion-Tokens. Kosten der Ankerspur insgesamt
(Fassung 1 und 2): 88.632 Completion-Tokens, Gewinn an Treffern: 0.

## Antwort auf die beiden Fragen

**`yun2024:559` antwortet nicht leer, sondern gar nicht.** Der Record endet mit
`finish_reason = length`, 0 Zeichen Inhalt und 24.000 verbrauchten Tokens. Es gibt
also keine geprüfte Leerantwort mit `chosen_timepoint` und `discarded_timepoints`,
sondern einen Abbruch. Die Zellenzahl ist zwar 0, aber der Status ist `abgebrochen`,
nicht `ok`. Gegenueber Fassung 1 ist das eine Verschlechterung: die lieferte eine
Antwort (falsche Tabelle, 2 falsche Zellen), jetzt kommt keine.

**`yun2024:615` bricht erneut ab**, mit 96.344 statt 98.472 Reasoning-Zeichen. Die
Pruefregel hat den Reasoning-Bedarf nicht erkennbar gesenkt.

## Was das ueber den Anker sagt

- Die neue Pruefregel greift nicht: statt bei fehlender Verankerung eine leere Liste
  zurueckzugeben, sucht das Modell weiter und laeuft ins Budget. Auf `559` stieg das
  Reasoning von 67.322 auf 98.896 Zeichen.
- Eine zusaetzliche Pflicht im Prompt ohne Verkleinerung des Suchraums erhoeht den
  Reasoning-Bedarf. Das ist die plausibelste Erklaerung fuer beide Abbrueche; belegt
  ist nur die Zahlenlage, nicht die Ursache.
- Der Anker ist damit fuer diese zwei Records gescheitert, in beiden Fassungen und in
  beide Richtungen (falsche Tabelle bzw. kein Ergebnis). Weitere Anker-Varianten auf
  demselben Einzelaufruf versprechen nach dieser Messung keinen Gewinn.

## Naechster Schritt

Die Abbruchstelle ist ein Reasoning-Problem, kein Schema- und kein Formulierungsproblem.
Sinnvoll ist deshalb nur ein Verfahren, das den Suchraum vor dem Aufruf verkleinert —
also die echte Zweistufigkeit: erst Zeile und Arm in einem kurzen Aufruf bestimmen
(eng begrenzter Ausschnitt, kleines Budget), dann die Zellen aus dieser einen Zeile
lesen. Alles andere wiederholt die Messung von heute.

Bewertung wie in `vergleiche_20261120.py` (Schluessel Feld + Arm, 1:1-Verbrauch). Gold
und die bestehenden Predictions sind unveraendert; geschrieben wurde nur in diesem
Verzeichnis.
