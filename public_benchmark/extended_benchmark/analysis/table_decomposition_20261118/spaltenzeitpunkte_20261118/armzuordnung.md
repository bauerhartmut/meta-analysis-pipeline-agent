# Armzuordnung aus gedruckter Abkuerzung (`TM`), Messung

Offline, 2026-11-18. Kein Netzlauf, kein Modelllauf, Gold und eingefrorene
Eingaben unveraendert.

**Ursache.** In `PMC3278655:T2` trennen die Kopfteile `TM` und `Cemented` die
Arme. `Cemented` steht woertlich in der Comparator-Bezeichnung
(`cemented component.`) und wurde gebunden. `TM` ist zwei Zeichen lang: die
Tokenregel verwirft kurze Tokens, und der Namensvergleich entfernt
Klammerzusaetze - die Abkuerzung `(TM)` aus
`The trabecular metal tibial monoblock component (TM)` war damit unsichtbar.
Folge: vier Interventions-Stichproben (`(n=30)`, `(n=29)`, `(n=28)`,
`(n=27)`) standen ohne Arm, `intervention_group_size` fehlte.

**Loesung (allgemein, ohne Studienname).** `consider_arm_candidate` schlaegt
einen Arm nur vor, wenn der Kopfteil genau eine im Dokument gedruckte
Klammerabkuerzung eines Arms ist (`TM` -> intervention). Wie bei den
Kopfbändern entscheidet die Validierung an einer Kopie: gefuellt werden nur
leere Arme, kein Feld darf verloren gehen, und mindestens ein Feld muss
gewonnen werden - sonst `original:...`. Die Entscheidung steht als
`Table.arm_decision`. Zusatz: eine Kopfangabe (`(n=27)`), deren Arm sich aus
dem Bandpfad nicht belegen laesst, erbt den Arm der Spalten unter dem Band,
wenn dort genau einer steht (`arm_basis="spalte"`).

## 1. Wirkung auf `PMC3278655:T2`

| Band | Spalte | Arm vorher | Arm nachher | Feld |
| --- | --- | --- | --- | --- |
| `(n=30)` | c1 (`TM`, 6 months) | leer | `intervention` (`spalte`) | `intervention_group_size` 30 |
| `(n=24)` | c2 (`Cemented`, 12 months) | `comparator` | `comparator` (`header_treffer`) | `comparator_group_size` 24 |
| `(n=29)` | c3 (`TM`, 24 months) | leer | `intervention` (`spalte`) | `intervention_group_size` 29 |
| `(n=23)` | c4 (`Cemented`, 60 months) | `comparator` | `comparator` | `comparator_group_size` 23 |
| `(n=28)` | c5 (`TM`, p-Wert-Spalte) | leer | `intervention` (`spalte`) | `intervention_group_size` 28 |
| `(n=21)` | c6 (`Cemented`) | `comparator` | `comparator` | `comparator_group_size` 21 |
| `(n=27)` | c7 (`TM`) | leer | `intervention` (`spalte`) | `intervention_group_size` 27 |
| `(n=18)` | c8 (`Cemented`) | `comparator` | `comparator` | `comparator_group_size` 18 |

Spaltenarme: c1/c3/c5/c7 = `intervention` mit `arm_basis="abkuerzung"`
(`arm_decision` = `kandidat:uebernommen:c1,c3,c5,c7`), c2/c4/c6/c8 bleiben
`comparator` aus dem Kopftreffer.

**Ergebnis der Messung** (`messung_nach_armzuordnung.json`):

| Paar | Felder vorher | Felder nachher | Goldzellen mit erreichbarem Feld |
| --- | --- | --- | --- |
| `PMC3278655:T2` / `390` | `comparator_group_size` | + `intervention_group_size` | 2 von 6 (vorher 1) |
| `PMC3278655:T2` / `391` | `comparator_group_size` | + `intervention_group_size` | 2 von 4 (vorher 1) |
| `PMC5777419:T2` / `678`, `/682` | `intervention_group_size` | unveraendert | unveraendert |

Die vier `(n=…)`-Baender sind damit **erreichbar**: Gold 27 (intervention) und
18 (comparator) treffen zu, weil die Kopfangaben jetzt den richtigen Arm
tragen. Nur die *Anzahl* der Felder waechst - die Zahl der erreichbaren
Goldzellen steigt entsprechend, weil `gold_reachable` feldfeldweise zaehlt.

## 2. Wirkung auf die eingefrorene Auswahl (A-E)

| Kennzahl | vorher | nachher |
| --- | --- | --- |
| erreichbare Goldfelder | 56 | **58** |
| strukturell komplett | 60/60 | 60/60 |
| Strukturfehler | 0 | 0 |
| erwartete Zellen | 1748 | 1748 |
| Warnungen (A) | 137 | 137 |

Gleich in A, B, C, D, E (`structure_nach_armzuordnung.json`).

**Reichweite der Regel:** von 60 Auswahl-Eintraegen uebernehmen genau **2**
einen Armkandidaten (die beiden `PMC3278655:T2`-Records); die uebrigen 58
haben keine gedruckte Klammerabkuerzung im Spaltenkopf und bleiben bei
`original:kein_kandidat`. Die Regel greift also nicht breit, sondern nur wo
ein Beleg dasteht.

## 3. Was weiterhin fehlt

- **Rollen:** die `TM`/`Cemented`-Spalten bleiben `role=unknown`; Mittel und
  Streuung (`--0.38 (0.37)`) werden deshalb nicht zu Feldern. Der Arm allein
  erzeugt keine Rolle.
- **Outcome-Zeile:** `subsidence` ist in `T2` nicht als Zeile erkannt
  (`outcome_zeilen: []`), die Goldwerte stehen in `Superior/inferior
  translation`.
- **Zeitpunktauswahl:** unveraendert wirkungslos - je Zeitpunkt 0 Felder, keine
  Verdraengung (Abschnitt 2 der ersten Messung gilt weiter).

## 4. Tests

Neu: `research_agent/tests/test_armabkuerzung.py` (5 Tests):

| Test | prueft |
| --- | --- |
| `test_printed_abbreviation_binds_the_arm` | `TM` -> intervention, `arm_basis="abkuerzung"`, Fakt `(n=27)` mit Arm `spalte` |
| `test_abbreviation_needs_the_printed_brackets` | ohne `(TM)` im Armnamen kein Kandidat, Arm bleibt leer |
| `test_abbreviation_without_field_gain_is_refused` | ohne `(n=…)` kein Gewinn -> `original:kein_gewinn` |
| `test_abbreviation_keeps_an_existing_arm` | `Cemented`-Spalte behaelt `comparator`, nur die leere Spalte wird gefuellt |
| `test_tm_table_reaches_all_four_group_sizes` | echtes Dokument: c1/c3/c5/c7 = intervention, vier Fakten mit Arm, beide Gruppengroessen erreichbar |

Gesamt **74 Tests gruen** (vorher 69).

## 5. Empfehlung fuer den naechsten Schritt

Jetzt die **Rolle** der `TM`/`Cemented`-Spalten angehen: der Kopfteil nennt
keine Rolle, die Zellen tragen `Mittel (Streuung)` und die Zeile heisst
`Superior/inferior translation (SD)`. Ein Rollenkandidat aus der Zellform
(`--0.38 (0.37)` -> mean + sd) mit derselben Validierung (kein Feldverlust,
Gewinn noetig) wuerde `intervention_mean`/`-standard_deviation` und die
Comparator-Werte liefern - acht Goldzellen, die heute gedruckt, aber
unerreichbar sind. Offline pruefbar, kein Guthaben.
