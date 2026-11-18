# Nachtrag: getrennte Zaehlung und Armpruefung der Kopfangaben

Offline, 2026-11-18. Fortschreibung zu `ergebnis.md` im selben Ordner. Kein
Netzlauf, kein Modelllauf; Gold und eingefrorene Eingaben unveraendert.

## 1. Anlass

`ergebnis.md` meldete **34** Goldfelder mit "Wert in der belegten Zeile". Diese
Zahl war zu hoch: `gedruckt_in_zeile` war als `bool(in_zeile) or gedruckt`
gebaut, und `gedruckt` schloss die Kopfangabe ein. Eine Kopfangabe (`n = 456`)
haengt aber an keiner Zeile - sie darf in einer Zeilenaussage nicht mitzaehlen.

## 2. Aenderung im Messwerkzeug

`diagnose_wertbeleg.py` fuehrt jetzt je Goldfeld **genau eine** Kategorie:

| Kategorie | Bedeutung |
| --- | --- |
| `belegende_zelle` | Wert steht in der Messzelle, die das Feld traegt |
| `belegende_kopfangabe` | Wert steht in der Kopfzeile, die das Feld traegt |
| `zeile_andere_spalte` | Wert steht in einer Messzelle der belegten Zeile, aber nicht in der Spalte des Feldes |
| `nur_anderswo` | Wert steht nur an anderer Stelle der Tabelle (Kopf, Fussnote, Rumpf) |
| `nirgends` | Wert steht nirgends in der Tabelle |

Reihenfolge der Pruefung: Zelle vor Kopfangabe vor falscher Spalte. Zusaetzlich
gibt es `gedruckt_in_messzelle_der_zeile` (nur echte Messzellen der belegten
Zeile) und `je_quelle.gedruckt_dort` (Treffer an genau diesem Weg statt
"irgendwo belegend").

## 3. Neue Zahlen fuer die 62 erreichbaren Goldfelder

| Kennzahl | vorher gemeldet | korrigiert |
| --- | --- | --- |
| erreichbar | 62 | 62 |
| Wert in belegender Kopfangabe | (in 34 enthalten) | **26** |
| Wert in belegender Messzelle | 32 gemeinsam | **6** |
| an belegender Stelle (Kopf oder Zelle) | 32 | **32** |
| Messzelle der belegten Zeile, falsche Spalte | (in 34 enthalten) | **2** (`yun2024:445`) |
| Wert in Messzellen der belegten Zeile | **34** | **8** |
| nur anderswo gedruckt | 9 + 3 getrennt | **10** |
| nirgends in der Tabelle | 18 | **18** |

Nach Weg der Erreichbarkeit: 37 Felder ueber eine Kopfangabe (22 drucken den
Wert dort, 15 nicht), 25 ueber eine Zelle (6 drucken ihn dort, 19 nicht); vier
dieser 25 sind zusaetzlich ueber den Kopf erreichbar (`PMC3475525:T2`,
`PMC4140238:T1`).

Unveraendert gilt: nur 4 Felder haengen an einer p-Wert-belegten Zeile
(`yun2024:390`), und alle vier stehen woertlich in der belegenden Messzelle
(`-0.38`/`0.37` in `r3/c7`, `-0.04` in `r3/c8`, `0.11` in `r3/c4` und `r3/c8`).

Die vollstaendigen Feldlisten stehen in `ergebnis.md`, Abschnitt 2.

## 4. Pruefung der vier Kopfangaben mit Armkonflikt

Geprueft wurde je Band: Beschriftung, gebundener Arm (`header_facts`) und das
Goldfeld, dessen Wert dort gedruckt steht.

| Fall | Kopfangabe | gedruckt | Arm laut Produktion | Goldfeld | Urteil |
| --- | --- | --- | --- | --- | --- |
| `yun2024:335`, `:336` | `Aripiprazole (n = 47)` | 47 | intervention (`header_treffer`) | comparator 47 | **an den anderen Arm gebunden** |
| `yun2024:678`, `:682` | `(n=15)` (Spalten 6-10) | 15 | intervention (`header_treffer`) | comparator 15 | **an den anderen Arm gebunden** |
| `yun2024:335`, `:336` | `Placebo (n = 45)` | 45 | leer (`kein_treffer`) | intervention 45 | gedruckt, aber ohne Arm |
| `yun2024:678`, `:682` | `(n=16)` (Spalten 2 und 5) | 16 | leer (`kein_treffer`) | intervention 16 | gedruckt, aber ohne Arm |
| `yun2024:15`, `:16` | `CoPAT (*n* = 103)` | 103 | **kein Fakt** | intervention 103 | gleicher Arm, Band nicht erkannt |
| `yun2024:662` | `Placebo (*n* = 23)` | 23 | **kein Fakt** | comparator 23 | gleicher Arm, Band nicht erkannt |

**Ergebnis:** Von den vier genannten Faellen sind nur **zwei** wirklich an einen
anderen Arm gebunden (`Aripiprazole (n = 47)`, `(n=15)`). Die beiden anderen
sind keine Kopfangaben der Produktion: `*n*` in Kursivschrift trifft weder
`group_size_declaration` noch `_GROUP_SIZE_ANY_RE`, deshalb entsteht kein
`header_fact`. Ihre Beschriftung stimmt mit dem Goldarm ueberein
(CoPAT = intervention, Placebo = comparator).

Weitere Beobachtungen aus den Baendern, ohne Annahme ueber die Ursache:

* `PMC5617873:T2`: die gedruckten Werte stehen unter den entgegengesetzten
  Armnamen (Placebo 45 bei Gold-intervention 45, Aripiprazole 47 bei
  Gold-comparator 47). Der Vergleichsarm heisst im Record `Placbeo`, das Band
  `Placebo`.
* `PMC4987981:T1`: der Kopf druckt `Metformin (n = 21)` und
  `Pioglitazone (n = 16)`; das Goldfeld `intervention_group_size` ist 37, also
  die Summe der beiden gedruckten Gruppen.
* `PMC2667135:T4`: beide Baender (`CoPAT` 103, `IPAT` 97) passen zu den
  Goldwerten, sie werden nur nicht extrahiert.

## 5. Einheiten-Rueckgang `yun2024:390` (unveraendert)

Der Rueckgang trifft in C ausschliesslich die 7 Zeilen ohne gedruckten Goldwert
(vorher war `focus_rows` leer, der Plan las die ganze Tabelle). In D/E kommen 8
Spalteneinheiten hinzu: 5 ohne Goldwert, 3 mit Goldwert werden auf nur r3
verengt; die Goldabdeckung bleibt 4 von 4 Feldern.

## 6. Pruefungen

* Messung neu gelaufen, `messung.json` mit `kategorien` und `je_quelle`.
* 92 Tests gruen (keine Produktionsdatei geaendert, nur das Messwerkzeug).
* A-E in diesem Schritt nicht neu gerechnet, weil die Produktion unveraendert
  ist; die Zahlen 62 Goldfelder / 0 Strukturfehler / 60 von 60 Tabellen stammen
  aus dem Lauf des vorigen Schritts.
* Commit `cf3d236`. Kein Push: der Branch ist hinter dem Remote (`behind 1`),
  Force-Push ist nicht erlaubt.

## 7. Empfehlung fuer den naechsten Schritt

Zuerst die Kursiv-`*n*`-Baender (`PMC2667135:T4`, `PMC4987981:T1`,
`PMC3654355:T1/T2` mit `( *n* = 71)`): Wert woertlich im Kopf, Beschriftung
passt zum Goldarm, reine Parser-/Regex-Frage, offline pruefbar und ohne
Armzuordnungs-Annahme. Danach die zwei echten Armkonflikte
(`PMC5777419:T2`, `PMC5617873:T2`), weil dort ohne Textbeleg nicht entscheidbar
ist, welche Seite recht hat - und nur mit einer Messung, die Feldgewinn gegen
Feldverlust stellt.
