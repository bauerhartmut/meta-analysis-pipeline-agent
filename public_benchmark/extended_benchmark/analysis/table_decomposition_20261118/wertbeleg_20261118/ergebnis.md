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

* **Zelle**: die Spalte, deren Zelle das Feld traegt - gespiegelt sind beide
  Produktionszweige, `row_fields` (Spaltenfeld, Rolle aus dem Zeilenlabel,
  Arm-als-Zeile, zweiter Wert einer Verbundzelle) und `reachable_fields`
  (`secondary_role` der Spalte, also der Streuungswert aus `-0.38 (0.37)`).
* **Kopfangabe**: die Kopfzeile, deren Arm das Feld `*_group_size` belegt.
* Verglichen wird mit `_zelltreffer` aus `diagnose_spaltenzeitpunkte.py`
  (Dezimalkomma, Unicode-Minus, Verbundzelle, Null nur als Ganzzahl).

Zusaetzlich wird die ganze belegte Zeile geprueft (steht der Wert in irgendeiner
Messzelle dieser Zeile?) und die Tabelle nach dem Wert durchsucht (Rumpf,
Kopfbaender, Fussnoten), damit "nicht gedruckt" nicht mit "am erwarteten Ort
nicht gedruckt" verwechselt wird.

## 2. Ergebnis ueber alle 62 erreichbaren Goldfelder

| Kennzahl | Anzahl |
| --- | --- |
| Goldzellen der Auswahl | 278 |
| davon erreichbar | **62** |
| Wert steht an einer **belegenden Stelle** | **32** (26 Kopfangabe, 6 Zelle) |
| Wert steht in der **belegten Zeile** (irgendeine Messzelle) | 34 |
| Wert steht an keiner belegenden Stelle | **30** |

Von den 62 kommen **37** ueber eine Kopfangabe und **25** ueber eine Zelle
(Zwei Felder in `PMC3475525:T2` sind ueber beide Wege erreichbar.) Nur **4**
Felder haengen an einer p-Wert-belegten Zeile - die vier neuen Felder aus
`yun2024:390` -, und alle vier stehen woertlich in der belegenden Zelle:
`-0.38`/`0.37` in `r3/c7`, `-0.04` in `r3/c8`, `0.11` in `r3/c4` und `r3/c8`.

### Die 30 Felder ohne Wert an der belegenden Stelle

Nach Feldart: 22 `*_group_size`, 5 `*_mean`, 3 `*_standard_deviation`.

**9 Felder: Wert steht nur anderswo im Kopf oder in einer Fussnote**

| Record | Tabelle | Feld | gedruckt als | Fundstelle |
| --- | --- | --- | --- | --- |
| yun2024:15, :16 | PMC2667135:T4 | intervention_group_size 103 | `CoPAT (n = 103)` | Kopfband + Fussnote |
| yun2024:275 | PMC3654355:T1 | intervention_group_size 71 | `ILI (n = 71)` | Kopfband |
| yun2024:282 | PMC3654355:T2 | intervention_group_size 71 | `(n = 71)` | Kopfband |
| yun2024:335, :336 | PMC5617873:T2 | intervention_group_size 45 | `Placebo (n = 45)` | Kopfband, aber Arm `Placebo` |
| yun2024:662 | PMC4987981:T1 | comparator_group_size 23 | `Placebo (n = 23)` | Kopfband |
| yun2024:678, :682 | PMC5777419:T2 | intervention_group_size 16 | `(n = 16)` | Kopfband |

**3 Felder: Wert steht anderswo im Rumpf**

| Record | Tabelle | Feld | Fundstelle |
| --- | --- | --- | --- |
| yun2024:266 | PMC2430617:T1 | intervention_group_size 80 | `r5/c1` |
| yun2024:445 | PMC4140238:T2 | intervention_mean 1.2 | `r8/c2` (belegte Zeile, andere Spalte) |
| yun2024:445 | PMC4140238:T2 | comparator_mean 2.1 | `r5/c1`, `r8/c1` (belegte Zeile, andere Spalte) |

Bei `yun2024:445` steht der Wert also in der belegten Zeile, aber nicht in der
Spalte, die das Feld traegt; bei `yun2024:335`/`:336` bindet der Kopf die
gedruckte 45 an den Arm `Placebo`, waehrend das Gold sie als
`intervention_group_size` fuehrt - die Stelle ist gedruckt, die Armzuordnung
passt nicht.

**18 Felder: Wert steht nirgends in der Tabelle**

`yun2024:194` (169/167), `yun2024:196` (24/24), `yun2024:265` (83/79),
`yun2024:266` (79), `yun2024:426` (44), `yun2024:78`/`:79` (30),
`yun2024:421` (mean 0.83, sd 0.22), `yun2024:494` (630),
`yun2024:662` (37), `yun2024:665` (mean 103.4/97.6, sd 28.9/20.8).

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

## 4. A-E nach der Messung (unveraendert)

| Kennzahl | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| erreichbare Goldfelder | 62 | 62 | 62 | 62 | 62 |
| strukturell komplett | 60/60 | 60/60 | 60/60 | 60/60 | 60/60 |
| Strukturfehler | 0 | 0 | 0 | 0 | 0 |
| erwartete Zellen | 1687 | 1261 | 1687 | 1687 | 1674 |
| Einheiten | 60 | 159 | 329 | 442 | 273 |
| Warnungen | 137 | 101 | 237 | 318 | 253 |

## 5. Grenzen

* Der Wertabgleich prueft **Woertlichkeit**, nicht Bedeutung: steht die Zahl in
  der Zelle, gilt sie als gedruckt - auch wenn sie dort eine andere Groesse
  meint. Das ist die bewusst schwache, aber pruefbare Aussage.
* Die Zuordnung "welche Zelle traegt das Feld" spiegelt `row_fields` und
  `reachable_fields`; aendert sich die Produktion, muss der Spiegel mit.
* "Nirgends in der Tabelle" heisst: nicht im geparsten Rumpf, in den
  Kopfbaendern und Fussnoten dieser Tabelle. Ein Wert kann im Fliesstext oder
  in einer anderen Tabelle des Dokuments stehen; das wird hier nicht behauptet
  und nicht geprueft.

## 6. Empfehlung fuer den naechsten Schritt

Die 22 `*_group_size`-Felder sind der groesste Block ohne gedruckten Wert an
der belegenden Stelle (15 ueber Kopfangaben, 7 ueber Zeilen). Als naechstes
dort ansetzen: die 4 Faelle, in denen der Wert **im Kopf steht, aber an einen
anderen Arm gebunden ist** (`yun2024:335`/`:336` Placebo/45, `yun2024:662`
Placebo/23, `yun2024:15`/`:16` CoPAT/103) sind mit dem vorhandenen
Armbeleg vergleichbar und ohne Netzlauf pruefbar. Die 18 "nirgends"-Felder
zuerst **nicht** angehen: dort ist die Tabelle nicht die Quelle des Goldwerts.
