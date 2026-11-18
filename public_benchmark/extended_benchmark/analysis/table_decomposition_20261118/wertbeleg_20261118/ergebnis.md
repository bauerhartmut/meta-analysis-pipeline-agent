# Wertabgleich je Goldfeld und Einheiten-Rueckgang - Messung

Offline, 2026-11-18. Kein Netzlauf, kein Modelllauf, Gold und eingefrorene
Eingaben unveraendert. Werkzeug:
`public_benchmark/extended_benchmark/table_decomposition/diagnose_wertbeleg.py`,
Rohdaten: `messung.json` (daneben).

## 1. Was gemessen wird

Die Feldebene ist bei der Outcome-Zeile zu grosszuegig: der Zwangslauf aus
`outcome_zeile_20261118` zeigte, dass **jede** vollstaendige Zeile dieselben
Goldfelder erreichbar macht. Deshalb wird je erreichbarer Goldzelle die Stelle
gesucht, die das Feld tatsaechlich belegt, und dort der gedruckte Wert
verglichen:

* **Messzelle**: die Spalte, deren Zelle das Feld traegt - gespiegelt sind
  beide Produktionszweige, `row_fields` (Spaltenfeld, Rolle aus dem Zeilenlabel,
  Arm-als-Zeile, zweiter Wert einer Verbundzelle) und `reachable_fields`
  (`secondary_role` der Spalte, also der Streuungswert aus `-0.38 (0.37)`).
* **Kopfangabe**: die Kopfzeile, deren Arm das Feld `*_group_size` belegt.
* Verglichen wird mit `_zelltreffer` aus `diagnose_spaltenzeitpunkte.py`
  (Dezimalkomma, Unicode-Minus, Verbundzelle, Null nur als Ganzzahl).

**Getrennt gezaehlt** werden drei verschiedene Dinge, die vorher in einer Zahl
steckten:

1. **belegende Kopfangabe** - der Wert steht in der Kopfzeile, die das Feld
   traegt (Kopfangaben haengen an keiner Zeile),
2. **belegende Messzelle** - der Wert steht in der Zelle, die das Feld traegt,
3. **Messzelle der belegten Zeile, falsche Spalte** - der Wert steht in einer
   Messzelle der belegten Zeile, aber nicht in der Spalte des Feldes.

Die Kategorien sind disjunkt (Messzelle vor Kopfangabe vor falscher Spalte), und
"in belegter Zeile" zaehlt **keine** Kopfangabe mehr mit. Zusaetzlich wird die
Tabelle nach dem Wert durchsucht (Rumpf, Kopfbaender, Fussnoten), damit "nicht
gedruckt" nicht mit "am erwarteten Ort nicht gedruckt" verwechselt wird.

## 2. Ergebnis ueber alle 62 erreichbaren Goldfelder

| Kennzahl | Anzahl |
| --- | --- |
| Goldzellen der Auswahl | 278 |
| davon erreichbar | **62** |
| Wert in der **belegenden Kopfangabe** | **26** |
| Wert in der **belegenden Messzelle** | **6** |
| Wert an einer belegenden Stelle (Kopf oder Zelle) | **32** |
| Wert in einer **Messzelle der belegten Zeile, falsche Spalte** | **2** |
| Wert nur anderswo gedruckt (Kopf/Fussnote/Rumpf) | **10** |
| Wert nirgends in der Tabelle | **18** |

In **Messzellen der belegten Zeile** steht der Wert damit bei **8** Feldern -
6 in der belegenden Zelle plus 2 in der falschen Spalte. Die frueher gemeldeten
34 waren zu hoch: sie zaehlten die 26 Kopffelder mit, obwohl eine Kopfangabe an
keiner Zeile haengt.

Nach Weg der Erreichbarkeit: **37** Felder kommen ueber eine Kopfangabe (22
davon drucken den Wert dort, 15 nicht), **25** ueber eine Zelle (6 drucken ihn
dort, 19 nicht). Vier dieser 25 sind zusaetzlich ueber den Kopf erreichbar
(`PMC3475525:T2`, `PMC4140238:T1`). Nur **4** Felder haengen an einer
p-Wert-belegten Zeile - die vier neuen aus `yun2024:390` -, und alle vier stehen
woertlich in der belegenden Messzelle: `-0.38`/`0.37` in `r3/c7`, `-0.04` in
`r3/c8`, `0.11` in `r3/c4` und `r3/c8`.

### Die 30 Felder ohne Wert an der belegenden Stelle

Nach Feldart: 22 `*_group_size`, 5 `*_mean`, 3 `*_standard_deviation`.

**10 Felder: Wert nur anderswo gedruckt**

| Record | Tabelle | Feld | gedruckt als | Fundstelle |
| --- | --- | --- | --- | --- |
| yun2024:15, :16 | PMC2667135:T4 | intervention_group_size 103 | `CoPAT (n = 103)` | Kopfband + Fussnote |
| yun2024:266 | PMC2430617:T1 | intervention_group_size 80 | - | `r5/c1` |
| yun2024:275 | PMC3654355:T1 | intervention_group_size 71 | `ILI (n = 71)` | Kopfband |
| yun2024:282 | PMC3654355:T2 | intervention_group_size 71 | `(n = 71)` | Kopfband |
| yun2024:335, :336 | PMC5617873:T2 | intervention_group_size 45 | `Placebo (n = 45)` | Kopfband, Arm leer |
| yun2024:662 | PMC4987981:T1 | comparator_group_size 23 | `Placebo (n = 23)` | Kopfband, kein Fakt |
| yun2024:678, :682 | PMC5777419:T2 | intervention_group_size 16 | `(n=16)` | Kopfband, Arm leer |

**2 Felder: belegte Zeile, falsche Spalte** - `yun2024:445`
(`PMC4140238:T2`): `intervention_mean 1.2` steht in `r8/c2`,
`comparator_mean 2.1` in `r5/c1` und `r8/c1`; die belegende Spalte traegt die
Werte nicht.

**18 Felder: Wert steht nirgends in der Tabelle**

`yun2024:194` (169/167), `yun2024:196` (24/24), `yun2024:265` (83/79),
`yun2024:266` (79), `yun2024:426` (44), `yun2024:494` (630),
`yun2024:78`/`:79` (30), `yun2024:421` (mean 0.83, sd 0.22), `yun2024:662`
(37), `yun2024:665` (mean 103.4/97.6, sd 28.9/20.8).

Beispiele geprueft: `PMC4987981:T2` druckt fuer FPG die **Aenderungen**
`2.2 ± 10.0`, `15.2 ± 19.2`, `20.5 ± 17.4` - die Goldwerte 103.4/97.6 stehen
dort nicht (auch nicht in Kopf oder Fussnote). `PMC3877023:T3` druckt
`2.2 (1)`/`2.9 (0.9)`, nicht 0.83/0.22. `PMC3546023:T4` druckt drei
Palmvitee-Gruppen mit `n = 3`/`19`/`8`, nicht die Goldsumme 30.

## 3. Trifft der Einheiten-Rueckgang bei `yun2024:390` nur unbelegte Messzeilen?

Verglichen wird derselbe Record-Satz mit und ohne p-Wert-Korroboration
(Monkeypatch der Produktionsfunktion, kein zweiter Codepfad). Einziger Record
mit Unterschied ist `yun2024:390`; alle anderen Records bleiben in allen
Verfahren gleich.

**Ursache:** vor der Korroboration ist `focus_rows` leer (`[]`) - der Plan
liest die **ganze Tabelle** (8 Zeilen). Nach der Korroboration ist
`focus_rows = [3]` und `corroborated_row = {subsidence: 3}`.

| Verfahren | Einheiten vorher | nachher | Goldabdeckung vorher | nachher |
| --- | --- | --- | --- | --- |
| C (zeilenweise) | 8 | 1 | 4 Felder | 4 Felder |
| D (beidseitig) | 15 | 8 | 4 Felder | 4 Felder |
| E (adaptiv) | 15 | 8 | 4 Felder | 4 Felder |

**Die 7 entfernten Zeileneinheiten (C, D, E):** `Mean maximum total`,
`point motion (range)`, `Lateral/medial translation (SD)`,
`Anterior/posterior translation (SD)`, `Anterior/posterior tilt (SD)`,
`Internal/external rotation (SD)`, `Varus/valgus tilt (SD)`. In keiner dieser
Zeilen steht ein Goldwert: **7 von 7 sind unbelegte Messzeilen**, und keine
davon ist die belegte Zeile r3.

**Die 8 entfernten Spalteneinheiten (nur D und E):** 5 tragen keinen Goldwert.
3 tragen Goldwerte (`comparator sd 0.11` in c4; `intervention mean -0.38` und
`sd 0.37` in c7; `comparator mean -0.04` und `sd 0.11` in c8), werden aber
durch schmalere Spalteneinheiten ueber **nur r3** ersetzt - die Goldabdeckung
bleibt deshalb bei 4 von 4 Feldern. Es geht also kein belegter Wert verloren;
der Auftrag wird auf die belegte Zeile zugeschnitten.

**Fazit:** Ja fuer die Zeileneinheiten - der Rueckgang trifft ausschliesslich
Zeilen ohne gedruckten Goldwert (vorher die Ganztabellen-Streuung, nicht
erkannte Outcome-Zeilen). Fuer D/E kommen Spalteneinheiten hinzu, die auf die
belegte Zeile verengt werden; die vier gedruckten Goldwerte bleiben in jedem
Verfahren abgedeckt.

## 4. Pruefung der vier Kopfangaben mit Armkonflikt

Geprueft sind die vier Faelle aus der Empfehlung des letzten Schritts: die
Kopfangaben, deren gedruckter Wert nicht am Goldfeld ankommt. Je Band sind
Beschriftung, gebundener Arm (`header_facts`) und Goldfeld gegenuebergestellt.

| Fall | Kopfangabe | gedruckt | Arm laut Produktion | Goldfeld | Urteil |
| --- | --- | --- | --- | --- | --- |
| `yun2024:335`, `:336` | `Placebo (n = 45)` | 45 | **leer** (`kein_treffer`) | intervention_group_size 45 | gedruckt, aber ohne Arm; Beschriftung Placebo = Vergleichsarm |
| `yun2024:335`, `:336` | `Aripiprazole (n = 47)` | 47 | intervention (`header_treffer`) | comparator_group_size 47 | **an den anderen Arm gebunden** |
| `yun2024:678`, `:682` | `(n=15)` (Spalten 6-10) | 15 | intervention (`header_treffer`) | comparator_group_size 15 | **an den anderen Arm gebunden** |
| `yun2024:678`, `:682` | `(n=16)` (Spalten 2 und 5) | 16 | **leer** (`kein_treffer`) | intervention_group_size 16 | gedruckt, aber ohne Arm |
| `yun2024:15`, `:16` | `CoPAT^a^ (*n* = 103)` | 103 | **kein Fakt** | intervention_group_size 103 | gleicher Arm (CoPAT = intervention); Band wird nicht als Kopfangabe erkannt |
| `yun2024:662` | `Placebo (*n* = 23)` | 23 | **kein Fakt** | comparator_group_size 23 | gleicher Arm (Placebo = comparator); Band wird nicht als Kopfangabe erkannt |

**Die Korrektur:** von den vier genannten Faellen sind nur **zwei** wirklich an
einen anderen Arm gebunden - `Aripiprazole (n = 47)` und `(n=15)`. Die beiden
anderen sind **keine Kopfangaben der Produktion**: `CoPAT (*n* = 103)` und
`Placebo (*n* = 23)` scheitern an der Kursiv-Auszeichnung `*n*`, weder
`group_size_declaration` noch `_GROUP_SIZE_ANY_RE` treffen, deshalb gibt es fuer
diese Baender keinen `header_fact`. Ihre Beschriftung stimmt mit dem Goldarm
ueberein (CoPAT = intervention, Placebo = comparator).

Zwei weitere Beobachtungen aus den Baendern, ohne Annahme ueber die Ursache:

* In `PMC5617873:T2` stehen die beiden gedruckten Werte unter den
  **entgegengesetzten Armnamen**: Placebo 45 (Gold: intervention 45),
  Aripiprazole 47 (Gold: comparator 47). Der Vergleichsarm heisst im Record
  `Placbeo`, das Band `Placebo` - deshalb bleibt der Placebo-Fakt ohne Arm.
* In `PMC4987981:T1` druckt der Kopf `Metformin (n = 21)` und
  `Pioglitazone (n = 16)`; das Goldfeld `intervention_group_size` ist 37, also
  die Summe der beiden gedruckten Gruppen. In `PMC2667135:T4` passen beide
  Baender (`CoPAT` 103, `IPAT` 97) zu den Goldwerten, sie werden nur nicht
  extrahiert.

## 5. A-E nach der Messung (unveraendert)

| Kennzahl | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| erreichbare Goldfelder | 62 | 62 | 62 | 62 | 62 |
| strukturell komplett | 60/60 | 60/60 | 60/60 | 60/60 | 60/60 |
| Strukturfehler | 0 | 0 | 0 | 0 | 0 |
| erwartete Zellen | 1687 | 1261 | 1687 | 1687 | 1674 |
| Einheiten | 60 | 159 | 329 | 442 | 273 |
| Warnungen | 137 | 101 | 237 | 318 | 253 |

## 6. Grenzen

* Der Wertabgleich prueft **Woertlichkeit**, nicht Bedeutung: steht die Zahl in
  der Zelle, gilt sie als gedruckt - auch wenn sie dort eine andere Groesse
  meint. Das ist die bewusst schwache, aber pruefbare Aussage.
* Die Zuordnung "welche Zelle traegt das Feld" spiegelt `row_fields` und
  `reachable_fields`; aendert sich die Produktion, muss der Spiegel mit.
* "Nirgends in der Tabelle" heisst: nicht im geparsten Rumpf, in den
  Kopfbaendern und Fussnoten dieser Tabelle. Ein Wert kann im Fliesstext oder
  in einer anderen Tabelle des Dokuments stehen; das wird hier nicht behauptet
  und nicht geprueft.

## 7. Empfehlung fuer den naechsten Schritt

Zwei Hebel, in dieser Reihenfolge:

1. **Kursiv-`*n*` in Kopfbaendern** (`PMC2667135:T4`, `PMC4987981:T1`, dazu
   `PMC3654355:T1/T2` mit `( *n* = 71)`): vier Records, deren Wert woertlich im
   Kopf steht und deren Beschriftung zum Goldarm passt, die aber keinen
   `header_fact` erzeugen. Das ist eine reine Parser-/Regex-Frage, offline
   pruefbar, und bringt Felder ohne jede Zuordnungsannahme.
2. **Armkonflikt `PMC5777419:T2` und `PMC5617873:T2`**: dort muesste die
   Armzuordnung entschieden werden (gedruckte Beschriftung gegen Goldarm).
   Riskant, weil ohne Beleg im Text nicht entscheidbar - erst nach (1) und nur
   mit einer Messung, die den Feldgewinn gegen den Feldverlust stellt.
