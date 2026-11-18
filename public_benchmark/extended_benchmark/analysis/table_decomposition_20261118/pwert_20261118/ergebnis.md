# p-Wert-Korroboration der Outcome-Zeile - Messung

Offline, 2026-11-18. Kein Netzlauf, kein Modelllauf, Gold und eingefrorene
Eingaben unveraendert.

## 1. Tote Schleife im Messwerkzeug entfernt

`diagnose_outcome_zeile.py::_zellen_mit_zeile` enthielt eine Schleife ueber alle
Spalten, die nur Zellen pruefte und nichts tat (kein `continue`-Ziel, kein
Zuweisen). Sie ist weg. Die Messung ist danach **elementweise identisch**:
`messung.json` (vor der Aenderung) == `messung_ohne_tote_schleife.json`
(`{"identisch": true}`), Entscheidungen unveraendert
(11 ohne Kandidat, 26 mehrdeutig, 16 Treffer, 7 Vorschlaege).

## 2. p-Wert als gedruckter Beleg

`semantics.corroborate_outcome_row_from_document(tables, context, text)` prueft
drei Dinge, bevor eine Zeile gesetzt wird:

1. **Derselbe Satz**: der p-Wert steht im Satz, der das Outcome nennt. Satzgrenze
   ist `.`/`!`/`?` **inklusive folgender Klammern** (`([Table 2](#)).`), und es
   muessen mindestens **50 Prozent der unterscheidenden Outcome-Woerter** im Satz
   stehen. Ein gemeinsames `5`/`year` reicht nicht.
2. **Genau ein Treffer**: genau eine Zeile der Tabelle druckt diesen p-Wert in
   einer Spalte **ohne Feld** (die p-Wert-Spalte kann ohne Kopfgeometrie sein,
   wie in `PMC3278655:T2`, wo c9 keinen Kopf hat) und die Zelle ist eine
   Einzelzahl. Mehrere Zeilen -> keine Uebernahme (`p_wert:mehrdeutig`).
3. **Wertabgleich**: jede Messspalte dieser Zeile traegt einen gedruckten,
   normalisierten Wert; eine reine Klammerzelle (`(0.07--3.11)`) ist eine Spanne
   und zaehlt nicht (`p_wert:kein_wert:r<id>`).

Danach steht die Zeile in `focus_rows` **und** in
`Table.corroborated_row[outcome]`; `reachable_cells` liest sie nur fuer genau
dieses Outcome, damit ein anderer Kontext nicht die Zeile eines fremden
Outcomes erbt.

**Ein Fehlversuch ist dokumentiert:** die erste Fassung nahm den Satz nur bis
zum naechsten `. ` - Saetze, die mit `).` enden, endeten dadurch nicht, und
`yun2024:391` (`The proportion of "at risk" ...`) bekam `p = 0.001` aus dem
Subsidence-Satz. Mit Klammergrenze und der 50-Prozent-Regel bleibt
`{0.2}` uebrig, und 0.2 steht in keiner Zeile dieser Tabelle.

## 3. Ergebnis in der Auswahl

| Entscheidung | Anzahl |
| --- | --- |
| `p_wert:uebernommen` | **1** (`PMC3278655:T2`, `yun2024:390`, r3) |
| `p_wert:kein_treffer` | 8 |
| `p_wert:mehrdeutig` | 2 (`PMC3546023:T4`, zwei Zeilen mit demselben p-Wert) |
| unveraendert (`treffer`/`mehrdeutig`/`vorschlag`/`kein_kandidat`) | 49 |

`yun2024:390` (`subsidence`): Text `... greater subsidence ... (p = 0.001)`,
Zeile `Superior/inferior translation (SD)` druckt `0.001`; Wertabgleich besteht
fuer c1-c4, c6-c8 (`--0.38 (0.37)` usw.).

## 4. Messung A-E

| Kennzahl | vorher | nachher |
| --- | --- | --- |
| erreichbare Goldfelder | 58 | **62** |
| strukturell komplett | 60/60 | 60/60 |
| Strukturfehler | 0 | **0** |
| erwartete Zellen A / B / C / D / E | 1748 / 1310 / 1748 / 1748 / 1735 | 1687 / 1261 / 1687 / 1687 / 1674 |
| Einheiten A / B | 60 / 159 | 60 / 159 |
| Einheiten C / D / E | 336 / 449 / 280 | 329 / 442 / 273 |
| Warnungen A / B / C / D / E | 137 / 101 / 244 / 325 / 260 | 137 / 101 / 237 / 318 / 253 |

Nur **ein** Record aendert sich, `yun2024:390`: Goldfelder 2 -> 6, Einheiten
C 8 -> 1, D/E 15 -> 8, erwartete Zellen 70 -> 9, Warnungen 8 -> 1. Die vier
neuen Goldfelder sind genau die vier Werte, die in der belegten Zeile gedruckt
stehen (`-0.38`, `0.37`, `-0.04`, `0.11`). Die zwei uebrigen Goldzellen von
`yun2024:391` (Ereignisse `0`/`2`, im Text als `0 of 27`/`2 of 18`) bleiben
unerreichbar - diese Tabelle druckt sie nicht.

## 5. Tests

`research_agent/tests/test_pwert_korroboration.py` (7 Tests): Auswahl der Zeile
ueber den p-Wert, zwei Zeilen mit gleichem p-Wert werden abgelehnt, Satz ohne
Outcome ist kein Beleg, Satzgrenze mit Klammer verhindert das Durchreichen eines
fremden p-Werts, ein geteiltes `5-year` bindet den Satz nicht, eine Spanne
scheitert am Wertabgleich, und am echten Dokument: `p_wert:uebernommen:r3` mit
den vier Feldern.

Gesamt **92 Tests gruen** (vorher 85).

## 6. Empfehlung fuer den naechsten Schritt

Die Feldebene ist bei diesem Hebel zu grosszuegig: der Zwangslauf aus
`outcome_zeile_20261118` zeigte, dass **jede** vollstaendige Zeile dieselben
Goldfelder erreichbar macht. Deshalb als naechstes den vorhandenen
Wertabgleich (`_zahle_paare`/`_zelltreffer` aus
`diagnose_spaltenzeitpunkte.py`) ueber alle 62 Felder fahren und je Feld
festhalten, ob der Goldwert in der belegten Zeile gedruckt steht. Das kostet
kein Guthaben, misst den neuen Beleg ehrlich und zeigt, welche der 62 Felder nur
auf der Feldebene halten. Erst danach lohnt der naechste Strukturhebel.
