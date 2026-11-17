# MedSR-Bench: Anschlussfähigkeit an `study_effects`

Erzeugt von `public_benchmark/scripts/goldstandard/analyse_medsr_bench.py`.
Alle Zahlen sind aus den 100 Review-JSONs gezählt, keine Schätzung.

**Lizenzstand:** Der Datensatz ist aus der Cochrane Library abgeleitet.
Cochrane verlangt für KI-Nutzung eine ausdrückliche Genehmigung; die
Apache-2.0-Angabe des Uploaders klärt das nicht. Rohdaten sind gitignored.

Dateien: 100, 8264765 Bytes.

## Zählungen

| Kennzahl | Wert |
|---|---:|
| Reviews | 100 |
| Trials gesamt | 1297 |
| davon `include` | 1297 |
| Analyse-Gruppen | 2144 |
| Gruppennummern mehrfach vergeben | 301 |
| Studienzeilen | 8810 |
| Gruppen mit mindestens 2 Studien | 2004 |
| Gruppen, deren Zeilen alle Effekt + KI tragen | 2000 |
| Gruppen poolbar (k >= 2, alle Zeilen mit Effekt + KI) | 2000 |
| Gruppen ohne eine einzige vollstaendige Armzeile | 20 |
| Studienzeilen mit Effekt + KI | 7574 |
| Armzeilen vollstaendig, kontinuierlich | 2273 |
| Armzeilen vollstaendig, binaer | 5305 |
| Gruppen mit Zielkonklusion | 1908 |
| Studiennamen in `data_studies` | 7570 |
| davon ohne passenden Studienblock | 0 |

## Verteilungen

**Trials nach `relation_type`**

| Wert | Gruppen |
|---|---:|
| include | 1297 |

**Datentyp**

| Wert | Gruppen |
|---|---:|
| Dichotomous | 1501 |
| Continuous | 643 |

**Effektmaß**

| Wert | Gruppen |
|---|---:|
| Risk Ratio | 1377 |
| Mean Difference | 539 |
| Std. Mean Difference | 104 |
| Odds Ratio | 93 |
| Risk Difference | 18 |
| Peto Odds Ratio | 13 |

**Zielkonklusion**

| Wert | Gruppen |
|---|---:|
| not significant | 1317 |
| favor comparison | 329 |
| favor Intervention | 262 |

## KI-Konsistenz

Für Mittelwertdifferenzen lässt sich der Standardfehler unabhängig aus
beiden Quellen rechnen: aus dem berichteten KI und aus den Arm-SDs.
Stimmen beide, ist das KI ein 95-%-KI.

- geprüfte Zeilen: 1865
- Median von (KI-Breite / Arm-SE): 3.9199 (erwartet 3.9199)
- Anteil im Fenster 3,6 bis 4,2: 1.0

## Provenienz

Keine Felder mit Seiten-, Tabellen-, Zell- oder Zitatbezug gefunden.
Der Verbatim-Kontrakt des Projekts lässt sich auf diesem Datensatz
nicht prüfen.

## Volltextverfügbarkeit (Stichprobe)

Geprüft: 40 PMIDs über Europe PMC.

| Status | PMIDs |
|---|---:|
| paywall | 30 |
| oa | 7 |
| pmc_no_oa | 3 |

`oa` = offene Lizenz, `pmc_no_oa` = in PMC lesbar ohne OA-Lizenz,
`paywall` = kein PMC-Volltext, `notfound` = kein Treffer.

## Lesart

Die Zahlen sagen, wie viel des Benchmarks überhaupt in die Struktur passt.
Sie sagen nichts über die Qualität der Werte und nichts über die Lizenz.

