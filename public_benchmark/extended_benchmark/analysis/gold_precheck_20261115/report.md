# Gold-Vorprüfung der Datenerweiterung (15.11.2026)

Reine Textprüfung, **keine Modellaufrufe**, keine Änderung an Gold, Records oder
Predictions. Werkzeug: `precheck_gold.py`.

## Was geprüft wird

| Muster | Regel | Anlass |
|---|---|---|
| Doppelangabe | Der annotierte Wert (Goldzelle) steht mit Dezimalstelle im Text, und an anderer Stelle (≥ 1.000 Zeichen entfernt) steht eine **fast gleiche** Zahl — Abstand ≤ 0,5 Prozent (Nachkommastelle) oder exakter Faktor 10 (Zehnerstelle) — in einem Satz mit demselben Outcome-Begriff | `yun2024:3`: 50,7/−0,7 in der Kurzfassung gegen 50,6/−7,0 im Ergebnisteil |
| Standortzahl | Eine als Gruppengröße annotierte Zahl steht in einem Satz, in dem eine Ortsangabe an die Zahl gebunden ist („hospitalised in unit A", Prozentangabe direkt dahinter) | `yun2024:83`: 940/1831 sind „unit A"/„unit B", nicht die Studienarme |

Beide Regeln arbeiten auf Prosa-Sätzen; Tabellenblöcke (`|`, `::::`, `caption`,
mehr als zwei Zeilenumbrüche, mehr als sechs Zahlen) werden ausgeschlossen,
weil sie die Trefferliste sonst fluten (siehe „Grenzen").

## Validierung am Dev-Satz (43 Records)

Drei Treffer, und alle drei sind die bekannten Fälle:

| Record | Art | Befund |
|---|---|---|
| `yun2024:3` | Doppelangabe | 50,6 (Gold) gegen 50,7, Abstand 7.836 Zeichen |
| `yun2024:3` | Doppelangabe | −0,7 (Gold) gegen −7,0, Faktor 10 |
| `yun2024:83` | Standortzahl | 940 mit „hospitalised in unit A" |

Keine Fehltreffer am Dev-Satz, also 3 von 3 richtig.

## Ergebnis auf den 407 noch nicht verwendeten Records

**0 Treffer** — weder Doppelangaben noch Standortzahlen (`hits.csv`,
`summary.json`). Das heißt nicht, dass dort keine Probleme stehen, sondern dass
die enge Regel dort nichts findet: Sie braucht eine zweite, fast gleiche Zahl
in der Nähe desselben Outcome-Begriffs. Der Dev-Satz zeigt, dass dieses Muster
selten ist (2 Zellen in 170).

## Grenzen (gemessen, nicht geschätzt)

* Eine weite Fassung (alle Satzpaare mit ähnlicher Zahl, ohne Gold-Anker)
  lieferte auf denselben 407 Records **1.500 Treffer**, fast alle aus Tabellen —
  unbrauchbar. Deshalb der Gold-Anker und der Prosa-Filter.
* Zwei- oder dreistellige Ganzzahlen ohne Dezimalstelle werden nicht geprüft
  (dort ist „fast gleich" nicht von „andere Zeile" zu trennen).
* Regionale Zuordnung „Kurzfassung/Hauptteil" gelingt nur, wenn der Artikel eine
  `## Results`/`## Methods`-Überschrift hat (93 von 120 Dokumenten). Fehlt sie,
  steht „unbestimmt"; die Treffer bleiben über Position und Abstand belegbar.
* Standortzahlen werden nur erkannt, wenn die Ortsangabe an die Zahl gebunden
  ist. Ein Artikel, der nur „Unit A" in einer Tabellenspalte führt, fällt durch.

## Folge für die Erweiterung

Die Prüfung ist als Vorlauf brauchbar (drei von drei bekannten Fällen, keine
Fehltreffer), ersetzt aber keinen Blick in den Text: Sie findet nur die
Musterfamilie, die im Dev-Satz belegt ist. Für die neuen Records bleibt eine
Sichtprüfung der Goldzellen nötig — die Prüfung sagt, wo sie zuerst hinsehen
soll, nicht, dass alles andere sauber ist.
