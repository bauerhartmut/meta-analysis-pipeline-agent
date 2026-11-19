# Sprint 48: Planwerte neu erzeugt (structure.json)

Der Lauf `offline_struktur_20261119` erzeugt die Planwerte mit dem aktuellen Code neu
(gleiche eingefrorene Auswahl, fuenf Strategien, Outcome-Zeile, kein `assume_order`).
Die Datei `offline_struktur_20261118b/structure.json` ist durch diesen Lauf ersetzt;
der separate Ordner `offline_struktur_20261119/` bleibt als Beleg stehen.

- Auswahl-SHA256: `c22ed3fb42dbaaff7051a89cdb327c4b250a134db0a62a19d3877d5ba311c0b1` (unveraendert)
- erzeugt: 2026-11-19T20:09:31+00:00 (vorher 2026-11-18T11:41:50+00:00)
- Befehl: `python public_benchmark/extended_benchmark/table_decomposition/run_benchmark.py --offline --run-id offline_struktur_20261119 --out public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/offline_struktur_20261119`

## 1. Kennzahlen je Strategie

| Strategie | Gold erreichbar alt -> neu | komplett alt -> neu | Fehler alt -> neu | expected_cells alt -> neu |
|---|---|---|---|---|
| A | 46 -> 94 | 57/60 -> 60/60 | 7 -> 0 | 1748 -> 1687 |
| B | 46 -> 94 | 57/60 -> 60/60 | 7 -> 0 | 1358 -> 1266 |
| C | 46 -> 94 | 57/60 -> 60/60 | 7 -> 0 | 1748 -> 1687 |
| D | 46 -> 94 | 57/60 -> 60/60 | 7 -> 0 | 1748 -> 1687 |
| E | 46 -> 94 | 57/60 -> 60/60 | 7 -> 0 | 1735 -> 1674 |

## 2. Was sich aendert

- **23 von 59 Records** aendern die Reichweite (Summe 46 -> 94). Mit der
  kuratierten Alias-Zuordnung (Control -> PBO, Definition -> IPAT) kommen
  15, 16 und 30 je eine Zelle hinzu: 94 -> 97.
- **29 Records** aendern Einheiten oder Prompt-Zeichen.
- Strukturfehler fallen von 7 auf 0; komplett von 57/60 auf 60/60.
- Die Ursache ist die Kopfangaben-Zaehlung aus Sprint 44 (`reachable_cells` fuehrt `n = ...` als `(-1, feld)`), nicht die Auswahl: die SHA256 ist identisch.

Beispiele fuer geaenderte Reichweite (Strategie A):

| Record | alt | neu |
|---|---:|---:|
| `yun2024:172` | 0 | 2 |
| `yun2024:174` | 0 | 2 |
| `yun2024:184` | 0 | 1 |
| `yun2024:185` | 0 | 1 |
| `yun2024:350` | 0 | 2 |
| `yun2024:352` | 0 | 2 |
| `yun2024:390` | 1 | 6 |
| `yun2024:391` | 1 | 2 |
| `yun2024:402` | 0 | 2 |
| `yun2024:403` | 0 | 2 |

## 3. Die fuenf Planfaelle

| Record | Strategie | Einheiten alt -> neu | Zeichen alt -> neu | Gold alt -> neu |
|---|---|---|---|---|
| `yun2024:30` | A | 1 -> 1 | 3515 -> 3515 | 1 -> 1 |
| `yun2024:30` | B | 1 -> 1 | 2398 -> 2398 | 1 -> 1 |
| `yun2024:252` | A | 1 -> 1 | 5318 -> 5318 | 0 -> 0 |
| `yun2024:252` | B | 1 -> 1 | 5318 -> 5318 | 0 -> 0 |
| `yun2024:421` | A | 1 -> 1 | 5489 -> 5398 | 0 -> 3 |
| `yun2024:421` | B | 1 -> 3 | 5489 -> 11272 | 0 -> 3 |
| `yun2024:672` | A | 1 -> 1 | 8234 -> 8370 | 0 -> 0 |
| `yun2024:672` | B | 3 -> 3 | 11612 -> 11759 | 0 -> 0 |
| `yun2024:678` | A | 1 -> 1 | 6461 -> 6753 | 0 -> 1 |
| `yun2024:678` | B | 1 -> 1 | 6461 -> 6753 | 0 -> 1 |

Damit sind die reproduzierten Feldtreffer: 30 -> 2, 252 -> 0, 421 -> 3, 672 -> 0,
678 -> 1. Bei 421 und 678 stammen die Treffer aus den Kopfangaben (421 zusaetzlich
zwei Zellen aus der Outcome-Zeile), bei 30 aus `n = 393`. **Wertgeprueft** ist
678 jedoch 0: die Kopfangabe `(n=15)` sitzt ueber der Antibiotic-Gruppe
(`intervention`), Gold verlangt 16/intervention und 15/comparator; in der
Entscheidungsvorlage steht deshalb 0 (`sprint48_armbindung_20261119.md`).
