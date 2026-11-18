# Outcome-Zeile aus der Zellform - Messung

Offline, 2026-11-18. Kein Netzlauf, kein Modelllauf, Gold und eingefrorene
Eingaben unveraendert.

## 1. Was umgesetzt ist

`semantics.consider_outcome_row_candidate` prueft die Zellform: Kandidat ist
eine **vollstaendige Datenzeile** - in jeder Messspalte (Spalte mit Feld) steht
eine Zahl. Das trennt eine Ergebniszeile von Zwischenueberschriften,
Definitions- und Leerzeilen. Die Entscheidung steht in
`Table.outcome_row_decision`:

| Entscheidung | Bedeutung |
| --- | --- |
| `original:treffer` | ein Zeilenlabel nennt das Outcome - der Name entscheidet |
| `original:mehrdeutig` | mehrere Zeilen sind vollstaendig, die Form nennt keine |
| `vorschlag:r<id>` | genau eine Zeile ist vollstaendig - Vorschlag, ohne Uebernahme |
| `original:kein_kandidat` | keine (oder zu wenige) Messspalten bzw. keine vollstaendige Zeile |

**Es wird nichts gesetzt.** Die Pruefung der Kopfbänder, Arme und Rollen
verlangt einen Gewinn an **Feldern**; durch die Zeilenwahl entsteht kein Feld.
Naehme man stattdessen erwartbare Zellen als Gewinn, waere die Pruefung
selbstbestaetigend: jede gesetzte Zeile gewinnt Zellen. Der Zwangslauf unten
zeigt, warum das hier sogar schaedlich waere.

Verteilung ueber die 60 Eintraege der Auswahl: 16 `original:treffer`,
26 `original:mehrdeutig`, 7 `vorschlag` (r0 sechsmal, r1 einmal),
11 `original:kein_kandidat`.

## 2. `PMC3278655:T2`: die Praemisse stimmt nicht

Der Record `yun2024:390` sucht `subsidence`. Gedruckt heisst die Zeile
**nicht** `Mean maximum total point motion`. Beleg aus der Tabelle selbst
(60-Monats-Spalten: TM = c7, Cemented = c8):

| Zeile | c7 | c8 |
| --- | --- | --- |
| `Mean maximum total point motion (range)` | `0.98` (r0) / `0.79` (Fortsetzung r1) | `0.79` / `0.9` |
| `Superior/inferior translation (SD)` | `--0.38 (0.37)` | `--0.04 (0.11)` |

Die Goldzellen von `yun2024:390` sind `intervention_mean = -0.38`,
`intervention_standard_deviation = 0.37`, `comparator_mean = -0.04`,
`comparator_standard_deviation = 0.11` - sie stehen woertlich in
**`Superior/inferior translation (SD)`**. Die MTPM-Zeile traegt sie nicht.

Ausserdem sind in dieser Tabelle **acht Zeilen vollstaendig** (r0 bis r7), die
Zellform nennt also keine Zeile eindeutig: Entscheidung `original:mehrdeutig`,
`outcome_zeilen` bleibt leer, erwartbare Zellen bleiben 2 (die beiden
Kopfangaben `n=27`, `n=18`).

## 3. Zwangslaeufe (offline, ohne Uebernahme)

Jede Zeile einzeln als Outcome-Zeile gesetzt, Abgleich gegen das Gold
(Feld erreichbar / Wert woertlich in der Zeile):

| Zeile | Felder erreichbar | Goldfelder (Feldebene) | Goldwerte gedruckt in der Zeile |
| --- | --- | --- | --- |
| r0 `Mean maximum total` (MTPM) | 6 | 6 von 6 | **0** |
| r3 `Superior/inferior translation (SD)` | 6 | 6 von 6 | **4** (`-0.38`, `0.37`, `-0.04`, `0.11`) |

Damit ist gemessen:

- Die **Feldebene** kann die Zeile nicht pruefen: jede vollstaendige Zeile
  macht dieselben sechs Goldfelder erreichbar (58 -> 62), auch die falsche.
  Ein Gewinn an Goldfeldern ist hier **kein Beleg** fuer die Zeile.
- Auf **Wertebene** belegt nur `Superior/inferior translation` die vier
  Goldwerte; die MTPM-Zeile belegt keinen einzigen.
- Die restlichen zwei nicht erreichbaren Goldzellen von `yun2024:391`
  (`intervention_events = 0`, `comparator_events = 2`) stehen **nicht** in
  `PMC3278655:T2`; sie sind im Text gedruckt (`0 of 27`, `2 of 18`). Keine
  Zeilenwahl dieser Tabelle kann sie erreichen.

Von sechs nicht erreichbaren Goldzellen der beiden Records wuerden mit der
richtigen Zeile vier erreichbar (Feldebene), mit der MTPM-Zeile null.

## 4. Messung A-E (eingefrorene Auswahl)

| Kennzahl | vorher | nachher |
| --- | --- | --- |
| erreichbare Goldfelder | 58 | **58** |
| strukturell komplett | 60/60 | 60/60 |
| Strukturfehler | 0 | **0** |
| erwartete Zellen | unveraendert | unveraendert |
| Warnungen | unveraendert | unveraendert |

`records` ist elementweise identisch mit dem Lauf aus `zellform_20261118`:
die Entscheidung wird gefuehrt, sie aendert keine Zelle.

## 5. Tests

`research_agent/tests/test_outcome_zeile.py` (5 Tests): eindeutige
vollstaendige Zeile ist ein Vorschlag ohne Uebernahme, zwei vollstaendige
Zeilen sind mehrdeutig (mit Vermerk), eine Zeile mit Luecke ist kein
Kandidat, ein Namenstreffer geht vor, und am echten Dokument: `mehrdeutig`,
`focus_rows` leer, 2 erwartbare Zellen, MTPM-Zeile druckt `0.79`/`0.9`,
Subsidence-Zeile `--0.38 (0.37)`.

Gesamt **85 Tests gruen** (vorher 80).

## 6. Empfehlung fuer den naechsten Schritt

Die Zeile braucht einen **gedruckten Beleg ueber die Form hinaus**. Der
naechste Kandidat liegt in der Tabelle selbst: der p-Wert. Der Record-Text sagt
`The TM components had significantly greater subsidence than the cemented
components (p = 0.001)`, und genau die Zeile `Superior/inferior translation`
traegt in der p-Wert-Spalte `0.001` - die einzige `0.001` der Tabelle. Eine
Regel "Zeile, deren p-Wert-Zelle dem p-Wert entspricht, den der Record im Satz
zum Outcome nennt" ist gedruckt belegt, studienunabhaengig und pruefbar; sie
muss nur eindeutig sein (mehrere Treffer -> keine Uebernahme). Vor jeder
Uebernahme ist der Wertabgleich zu fahren, nicht die Feldebene.
