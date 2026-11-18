# Armvererbung abgesichert, Rolle aus der Zellform

Offline, 2026-11-18. Kein Netzlauf, kein Modelllauf, Gold und eingefrorene
Eingaben unveraendert.

## 1. Armvererbung der Kopfangaben abgesichert

Eine Kopfangabe (`(n=27)`) erbt den Arm der Spalten unter ihrem Band - bisher
aus **jeder** gesetzten Spalte. Damit konnte ein Arm, der nur aus der
Spaltenreihenfolge stammt (`arm_basis="reihenfolge"`, eine Annahme, kein
Nachweis), eine Stichprobengroesse belegen und ein Feld tragen.

**Aenderung:** geerbt wird nur noch aus belegten Zuordnungen
(`header_treffer`, `abkuerzung`, `uebertrag`, `dokument`). Zusaetzlich muss
unter dem Band **genau ein** Arm gesetzt sein; stehen dort mehrere Arme -
belegt oder nicht -, bleibt die Angabe ohne Arm, weil sie dann fuer keine
Gruppe eindeutig gilt.

In der eingefrorenen Auswahl gab es keinen Fall, in dem ein reiner
Reihenfolge-Arm tatsaechlich eine Kopfangabe trug; die Regel schliesst den Weg
also vorbeugend, und zwei Tests halten ihn geschlossen:

| Test | prueft |
| --- | --- |
| `test_order_based_arm_does_not_prove_a_group_size` | Arm nur aus der Reihenfolge (`arm_basis="reihenfolge"`), Band `(n=27)`: Fakt bleibt ohne Arm, kein `intervention_group_size` |
| `test_mixed_arms_under_a_group_size_band_leave_the_arm_empty` | Band ueber zwei Spalten mit `comparator` und `intervention` (beide `header_treffer`): Fakt ohne Arm |

## 2. Rollenerkennung aus der Zellform

`PMC3278655:T2` nennt im Kopf keine Rolle (`TM`, `Cemented`), die Zellen tragen
aber `Mittel (Streuung)` (`--0.38 (0.37)`). Neu: `consider_role_candidate`
schlaegt `role="mean"` vor, wenn

1. die Spalte noch keine Rolle hat und einen **belegten Arm** traegt (ohne Arm
   entstuende kein Feld),
2. mindestens zwei Zellen gefuellt sind und **60 Prozent** genau `Zahl (Zahl)`
   zeigen (Fussnotenzeichen, Unicode-Minus und doppeltes Minus normalisiert),
3. weder Kopf noch Zeilenlabel nach Ereignis oder Prozent aussehen
   (`n (%)`, `%`, `events`, `p-value`) - `12 (34)` sieht sonst wie ein Mittel
   mit Streuung aus.

Uebernommen wird nur nach derselben Validierung wie bei Kopfbändern und Armen:
an einer Kopie rechnen, kein Feld verlustig, mindestens ein Feldgewinn. Die
Streuung setzt danach die vorhandene Regel `_detect_combined_columns`
(`secondary_role="sd"`). Entscheidung: `Table.role_decision`.

**Wirkung in der Auswahl:** 3 von 60 Eintraegen uebernehmen einen
Rollenkandidaten, die uebrigen 57 haben keinen:

| Tabelle / Record | Spalten | Felder danach |
| --- | --- | --- |
| `PMC3278655:T2` / `yun2024:390` | c1, c2, c3, c4, c6, c7, c8 | `intervention_mean`, `intervention_standard_deviation`, `comparator_mean`, `comparator_standard_deviation` |
| `PMC3278655:T2` / `yun2024:391` | dieselben | dieselben |
| `PMC3877023:T3` / `yun2024:421` | c4 | `intervention_mean`, `intervention_standard_deviation` |

## 3. Messung (eingefrorene Auswahl, A-E)

| Kennzahl | vorher | nachher |
| --- | --- | --- |
| erreichbare Goldfelder | 58 | **58** |
| strukturell komplett | 60/60 | 60/60 |
| Strukturfehler | 0 | 0 |
| Warnungen A / C | 137 / 244 | 137 / 244 |
| Warnungen B | 103 | 101 |
| erwartete Zellen A / C / D / E | 1748 / 1748 / 1748 / 1735 | unveraendert |
| erwartete Zellen B | 1335 | 1310 |

Die Goldfelder sinken nicht; die Zahlen verschieben sich nur dort, wo die neuen
Felder jetzt geplant werden (Strategien mit Spalteneinheiten). Je Record, alles
andere unveraendert:

| Strategie | Record | Einheiten | erwartete Zellen | Warnungen |
| --- | --- | --- | --- | --- |
| B | `yun2024:390`, `:391` | 1 -> 7 | 70 -> 56 | 1 -> 0 |
| B | `yun2024:421` | 1 -> 3 | 1 -> 3 | 0 |
| B | `yun2024:426` | 1 -> 2 | 1 -> 2 | 0 |
| D, E | `yun2024:390`, `:391` | 8 -> 15 | 70 | 8 |
| D, E | `yun2024:421` | 2 -> 4 | 6 | 0 |
| D, E | `yun2024:426` | 2 -> 3 | 6 | 0 |

**Warum die Goldfelder trotzdem bei 58 bleiben:** `gold_reachable` zaehlt nur
Zellen der **Outcome-Zeile**. In `PMC3278655:T2` ist `subsidence` weiterhin
keine erkannte Zeile (`outcome_zeilen: []`); die neuen Felder sind strukturell
zuordenbar (`reachable_fields`), aber noch an keiner Zeile belegt. Die Messung
in `spaltenzeitpunkte_20261118/messung_nach_armzuordnung.json` zeigt das
unveraendert: die Goldwerte stehen in `Superior/inferior translation`.

## 4. Tests

Neu in `research_agent/tests/test_armabkuerzung.py` (2) und
`research_agent/tests/test_zellform_rolle.py` (4):

| Test | prueft |
| --- | --- |
| `test_cell_form_makes_mean_and_sd` | echtes Dokument: c1/c2/c3/c4/c6/c7/c8 = `mean` mit `sd`, vier Felder erreichbar |
| `test_cell_form_without_arm_stays_unknown` | ohne Arm kein Kandidat, Rolle bleibt `unknown` |
| `test_event_cells_are_not_read_as_mean` | `12 (34)` unter `Not complying, n (%)` wird nicht Mittel |
| `test_plain_values_are_not_read_as_mean` | einfache Zahlen ohne Klammer werden nicht Mittel |

Gesamt **80 Tests gruen** (vorher 74).

## 5. Empfehlung fuer den naechsten Schritt

Die **Outcome-Zeile** angehen: in `PMC3278655:T2` heisst die gesuchte Zeile
`Mean maximum total point motion` und das Record-Outcome `subsidence` - eine
Umschreibung, die `_outcome_match_score` nicht verbindet. Ein Kandidat aus der
Zellform der Zeile (erste Datenzeile mit Zahlen in allen Messspalten) waere
wieder ueber die Validierung zu pruefen: kein Feldverlust, Gewinn noetig. Das
wuerde die jetzt zuordenbaren Felder (8 Goldzellen) tatsaechlich als
erreichbar zaehlen - der groesste Hebel ohne Guthaben.
