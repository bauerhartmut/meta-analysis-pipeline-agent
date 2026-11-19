# Sprint 48: Ursachen der 26 wertabweichenden Planzellen

Grundlage: `pruefe_armbindung_sprint48.py` (Plan-Auswahl ueber `load_tables`),
Stand `offline_struktur_20261118b/structure.json`. Rein lesend, keine
Netzaufrufe. Die 26 Zellen sind die Kopftreffer, deren Wert nicht zum Goldwert
passt; die Wertabdeckung bleibt damit **68 von 94**.

## 1. Aufteilung

| Ursache | Zellen | Records |
|---|---:|---|
| Untergruppe oder geteilter Arm im selben Tableau | 16 | 78, 79, 172, 174, 265, 266, 531, 532, 645, 647 |
| Goldwert steht in einer anderen Tabelle (andere Population) | 5 | 185, 194, 196 |
| Arm-/Spaltenfehlbindung | 5 | 335, 336, 426, 678, 682 |
| **Summe** | **26** | 18 Records |

Keine der 26 Zellen wird durch die Ursachenpruefung wertgedeckt; die Zahl 68
bleibt unveraendert. Die Aufteilung aendert aber die Diagnose: es sind nicht
26 gleichartige "Untergruppenfaelle", sondern 5 armfalsche Zellen und 5
Zellen, deren Beleg in einem anderen Tableau steht.

## 2. Alle 26 Zellen

| Record | Feld | Gold | Plan-Tabelle | gedruckt | Ursache |
|---|---|---:|---|---|---|
| `yun2024:78` | intervention | 30 | T4 | Palmvitee n = 3 / 19 / 8 (Perioden S1-S3) | Untergruppe je Periode; 30 ist die randomisierte Zahl, nicht im Kopf |
| `yun2024:79` | intervention | 30 | T4 | wie 78 | dito |
| `yun2024:172` | intervention | 33 | T1 | Metformin 17, Sitagliptin 16 | Interventionsarm geteilt; Summe 33 nicht gedruckt |
| `yun2024:174` | intervention | 33 | T1 | wie 172 | dito |
| `yun2024:185` | comparator | 28 | T1 | Placebo 33 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:194` | intervention | 169 | T1 | Pls 145 | analysierte vs randomisierte Kohorte; 169 steht in T6 |
| `yun2024:194` | comparator | 167 | T1 | Placebo 140 | dito |
| `yun2024:196` | intervention | 24 | T6 | Pls 169 | Gold aus T3/T5 (Mittel 1,29); T6 ist die Baseline-Kohorte |
| `yun2024:196` | comparator | 24 | T6 | Placebo 167 | dito |
| `yun2024:265` | intervention | 83 | T1 | 30 ug 81, 60 ug 78 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:265` | comparator | 79 | T1 | Placebo 78 | dito |
| `yun2024:266` | intervention | 80 | T1 | 30 ug 81, 60 ug 78 | dito |
| `yun2024:266` | comparator | 79 | T1 | Placebo 78 | dito |
| `yun2024:335` | intervention | 45 | T2 | Aripiprazol 47 -> intervention | Arme gegen Gold vertauscht: Gold fuehrt 45 als intervention (Placebo), 47 als comparator |
| `yun2024:336` | intervention | 45 | T2 | wie 335 | dito |
| `yun2024:426` | comparator | 44 | T4 | n = 18, n = 30 -> comparator | Untergruppen 18/21/30/34 plus falsche Spaltenarme (Short-Bore und P-Wert als comparator) |
| `yun2024:531` | intervention | 289 | T3 | 298 / 307 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:531` | comparator | 204 | T3 | 214 | dito |
| `yun2024:532` | intervention | 283 | T1 | 298 / 307 | dito |
| `yun2024:532` | comparator | 204 | T1 | 214 | dito |
| `yun2024:645` | intervention | 27 | T1 | Iodine 29 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:645` | comparator | 26 | T1 | Placebo 30 | dito |
| `yun2024:647` | intervention | 27 | T1 | Iodine 29 | dito |
| `yun2024:647` | comparator | 26 | T1 | Placebo 30 | dito |
| `yun2024:678` | intervention | 16 | T2 | n = 15 -> intervention | Spaltenarm falsch: 15 steht ueber Antibiotic, Gold will 15 als comparator |
| `yun2024:682` | intervention | 16 | T2 | n = 15 -> intervention | dito |

## 3. Der Verdacht zu yun2024:196

`yun2024:196` ist **kein** Fall wie 678. In T6 sind die Spalten korrekt den
Armen zugeordnet (intervention, comparator) und die Kopfangaben `n = 169` /
`n = 167` passen zu diesen Spalten; T6 ist eine Baseline-/Ereignistabelle der
Gesamtkohorte (Zeilen u. a. Karzinomarten mit 0/1). Der Goldwert 24/24 und die
Mittelwerte 1,29 / 1,08 stehen in T3 bzw. T5, nicht in T6. Die Zelle ist damit
eine **Tabellen-/Populationsverwechslung**: der Plan liest die Kohortengroesse
aus dem falschen Tableau, nicht einen falsch gebundenen Arm.

Bei `yun2024:194` ist es dasselbe Muster: T1 traegt die analysierten 145/140,
Gold nutzt die randomisierten 169/167 aus T6.

## 4. Skript-Review (frischer Blick, Zahlen unveraendert)

Gelesen: `public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py`,
304 Zeilen. Keine Zahl und kein Ergebnis geaendert. Befunde:

1. **Bandpruefung fehlt.** Der Docstring verspricht "sitzt das Kopfband ueber
   Spalten desselben Arms?", aber `band_arme()` wird nur in `details` abgelegt
   und nie ausgewertet. Zwei falsche Spaltenarme (426, 678) blieben deshalb
   unentdeckt.
2. **"wertgedeckt" ist zu stark.** Die 68 zaehlen Zeilenzellen und alle
   Nicht-Gruppenfelder ungeprueft mit; korrekt waere "nicht durch eine
   wertabweichende Kopfangabe widerlegt".
3. **Armvertauschung wird als Wertabweichung verbucht.** `wert_ohne_arm` prueft
   nur Zellen, deren Wert schon passt; 335/336 (47 auf intervention statt
   comparator) erscheinen als `wert_abweichend`. Eine Klasse "Arm vertauscht"
   fehlt.
4. **Keine Abstimmung mit dem Artefakt.** Es fehlt die Zusicherung
   `summe['feldtreffer_gesamt'] == structure['gold_reachable']` (94). Wird
   `structure.json` neu erzeugt, aendert sich die Bezugsgroesse still.
5. **Absoluter Auswahlpfad.** `struktur['selection']` ist ein absoluter Pfad;
   auf einem anderen Rechner oder Checkout bricht das Skript ab.
6. **Tautologie in Abschnitt 3.** `Feld erreichbar = z['field'] in {...}` ist
   immer wahr, weil `z` aus derselben Liste stammt.
7. **Sortierung und Casts.** `sorted(records)` sortiert lexikografisch (`682`
   vor `78`); `int(z['value'])` schneidet nicht-ganzzahlige Groessen ab.
8. **Leere Auswahl wird stillschweigend hingenommen.** Ein Record ohne
   Auswahlzeile traegt 0 bei, ohne Warnung.

Empfehlung: Punkte 1, 3 und 4 vor dem naechsten Lauf beheben (Bandarm-Auswertung,
Klasse "Arm vertauscht", Soll-Ist-Abgleich), ohne die Bezugsgroesse zu aendern.

Hinweis: Wo "Population weicht ab (nicht belegt)" steht, ist die Zuordnung
(randomisiert vs analysiert) aus dem Markdown nicht sicher belegbar; belegt ist
nur, dass der Goldwert nicht im Kopf der gewaehlten Tabelle steht. Die
Summenprobe belegt dagegen 78 (3+19+8 = 30) und 172/174 (17+16 = 33).
