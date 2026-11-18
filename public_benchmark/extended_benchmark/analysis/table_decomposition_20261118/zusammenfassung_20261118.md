# Tabellenzerlegung: Stand und Ergebnisse (2026-11-18)

Zusammenfassung der Arbeit an der modellunabhaengigen `table_decomposition`-Engine
und am Yun-699-Benchmark. Alle Zahlen stammen aus Laeufen dieses Tages; die
Belege stehen im selben Verzeichnis (`*.json`, `*.md`, `bisect_20261118/`).

## 1. Ausgangslage

- Ziel: wissenschaftliche Tabellen strukturerhaltend zerlegen, gegen Yun-699
  validieren, Recall erhoehen ohne Precision zu verlieren.
- Eingefrorene Testauswahl `selection_test.json`: 59 Records, 60 Tabellen,
  fuenf Strategien (A-E), 1748 erwartete Zellen.
- dev-Split: 38 Records mit Goldzellen.
- Regel im Projekt: kein Netzlauf ohne Freigabe, keine erfundenen Werte, jede
  Zahl nachrechenbar, Gold unveraendert.

## 2. Was gebaut wurde

| Sprint | Commit | Aenderung | Wirkung (gemessen) |
| --- | --- | --- | --- |
| 36 | `dca0bb9` | Spaltenrollen aus dem Zeilenlabel (`Row.value_role`, `secondary_role`, `row_roles`) | test: 21 -> 56 erreichbare Goldfelder |
| 37 | `737142c` | Prosa-Guard, Armbindung aus dem Zeilenlabel (Schwelle 0,6), Outcome-Spalten, Kopf-Geometrie, SE-Guard | dev: 12 -> 16 Goldfelder, 5 Records mit Treffer; test neutral (56) |
| 38 | `718d291` | Kopfbaender nach Wertspalten neu geordnet (`_reassign_header_bands_by_order`) | `PMC4319071:T2` liefert `comparator_mean` = 158.67 exakt; test: 56 -> 46 und 0 -> 7 Strukturfehler |
| 39 | `79556dc` | Interventionsarm aus der Dokumentdefinition (`arm_basis="dokument"`) | `intervention_mean` 167.61 und 2.50 erreichbar; test neutral (46) |
| 40 | `38fbeea` | Auswahlregel: je Outcome und Zeitpunkt nur eine Tabelle (`primary_tables`, `Table.redundant_of`) | `PMC4319071:T4` faellt hinter `T2` zurueck, kein Feldverlust |
| 41 | `80c9948` | `primary_tables` gibt nur noch die verdraengten Tabellen zurueck; neues Struktur-Artefakt `offline_struktur_20261118b` | test: 46 Goldfelder (statt veralteter 95) |
| 42 | `8d01cb3` | Bisect der Reichweite ueber neun Staende | Ursache der Fehler zugeordnet |

Tests: **52 passed** (`research_agent/tests/test_table_decomposition.py`,
`public_benchmark/tests/test_table_decomposition_benchmark.py`).

## 3. Fachliche Kernpunkte

**Rollen und Arme nur mit Beleg.** Ohne Beleg bleibt der Arm leer; die
Begruendung steht in `arm_basis` (`header_treffer`, `reihenfolge`, `uebertrag`,
`dokument`). `(SE)` und `(95% CI)` erzeugen keine Standardabweichung.

**Kopfebenen** werden bei unaufloesbarer Kopfgeometrie ordinal den
**Wertspalten** zugeordnet, nicht ueber x-Positionen, weil Kopf und Strichraster
versetzt sind.

**Dokumentarm nur an Zeilenlabels.** Ein Spaltenarm unter `Plus` in `T1` traegt
den Control-Wert (`157.73`) und erzeugte drei falsche Felder; gemessen und
verworfen.

**Auswahlregel.** Kandidaten sind Tabellen mit Zeitpunkt-Gruppenzeilen und
mindestens einem Outcome-Feld. Je Zeitpunktmenge gewinnt die erste gedruckte
Tabelle - nur wenn sie die Felder der uebrigen abdeckt; sonst bleiben alle
stehen. Felder kommen aus `reachable_cells` (Outcome-bezogen), nicht aus
`reachable_fields`: sonst verdraengt in `PMC1216327` die Baseline-Tabelle die
Ergebnistabelle und dev faellt von 16 auf 12 Goldfelder.

## 4. Messungen

### dev (38 Records mit Gold)

| Groesse | Wert |
| --- | --- |
| erreichbare Goldfelder | 16 |
| Records mit mindestens einem Treffer | 5 |
| Rueckfaelle durch die Auswahlregel | 0 |

Systematische Gegenprobe: **kein** dev-Dokument druckt dasselbe Outcome zu
denselben Zeitpunkten in zwei Tabellen. Das einzige Dokument mit zwei
Zeitpunkttabellen (`PMC4450164`, `yun2024:120`) hat verschiedene
Zeitpunktmengen (`sonography`/`ivp` gegen `drain removal`) und keine
Zielfelder; die Regel verdraengt dort nichts. Die Verdraengung selbst ist an
`PMC4319071` (test) und im Unit-Test belegt.

### PMC4319071 (test, beide Records `yun2024:111`/`112`)

- `PMC4319071:T4` (Risikogruppen `n=803`/`n=1014`) traegt
  `redundant_of = "PMC4319071:T2"` (Gesamtstichprobe).
- Goldfelder vorher = nachher: `comparator_mean`, `intervention_mean`,
  `comparator_group_size`; kein Verlust.
- Belegte Werte bleiben die einzigen Kandidaten: `158.67` (comparator, 4 Monate,
  Vegetables) und `167.61` (intervention) fuer `yun2024:112`, `2.84` / `2.50`
  fuer `yun2024:111`. Die beiden Gold-Streuungen (`83.71`, `2.76`) stehen nicht
  im Dokument - es druckt `Mean (SE)`.

### Eingefrorene Testauswahl (aktueller Code, Strategie A)

| Groesse | Wert |
| --- | --- |
| Tabellen | 60 |
| strukturell komplett | 57/60 |
| erwartete Zellen | 1748 |
| Gold erreichbar | 46 (in allen fuenf Strategien) |
| Strukturfehler | 7 |
| Warnungen | 136 |

## 5. Bisect: woher 95 und 46 kommen

| Stufe | Commit | Gold | Zellen | komplett | Fehler |
| --- | --- | --- | --- | --- | --- |
| alter Stand | `ac3b4c9` | 95 | 2022 | 60/60 | 0 |
| vor der Zellkorrektur | `811ae9d~1` | 95 | 2022 | 60/60 | 0 |
| Zellzaehlung berichtigt | `811ae9d` | 21 | 1748 | 60/60 | 0 |
| vor den Zeilenrollen | `dca0bb9~1` | 21 | 1748 | 60/60 | 0 |
| Zeilenrollen (Sprint 36) | `dca0bb9` | 56 | 1748 | 60/60 | 0 |
| Guards (Sprint 37) | `737142c` | 56 | 1748 | 60/60 | 0 |
| Kopfbaender (Sprint 38) | `718d291` | 46 | 1748 | 57/60 | 7 |
| Dokumentarm (Sprint 39) | `79556dc` | 46 | 1748 | 57/60 | 7 |
| Auswahlregel (HEAD) | `80c9948` | 46 | 1748 | 57/60 | 7 |

Rechnung: 95 - 74 (berichtigte Zellzaehlung) + 35 (Zeilenrollen) - 10
(Kopfband-Guard) = 46.

**Befund:** Die 95 war eine Ueberzaehlung. Von den 49 Goldfeldern Differenz
gehen nur 10 auf einen Guard der abgefragten Commits zurueck, und zwar auf
`_reassign_header_bands_by_order` (`718d291`); derselbe Guard erzeugt alle 7
Strukturfehler. Gegenprobe: Funktion im Speicher auf `return False` gesetzt ->
56 Goldfelder, 60/60 komplett, 0 Fehler.

**Betroffene Tabellen:** `PMC3877023:T3/T4` (3 und 1 Goldfeld, je 3 Fehler),
`PMC4987981:T2` (4 Goldfelder), `PMC5777419:T2` (je 1 fuer zwei Records),
`PMC3654355:T1` (kein Goldverlust, ein Fehler `header_span_ueberlappt`).

## 6. Pruefungen und Grenzen

- Kein Netzlauf in dieser Sitzung; alle Messungen offline.
- Testartefakte unveraendert: `selection_test.json`,
  `offline_struktur_20261118`, `offline_fokus_20261118` (git-Status leer).
- Gold wurde nicht angefasst; Vorhersagen gibt es nur aus Modellaeufen, die
  hier nicht stattfanden.
- **Nicht gemessen:** Precision, Recall, F1. `gold_reachable` ist die
  Obergrenze des Tabellenpfads, kein Guetemass.
- Die Auswahlregel ist auf der eingefrorenen Testauswahl wirkungslos (je Record
  genau eine Tabelle); sie wirkt im Dokumentpfad ohne `table_ids`.
- Der Kopfband-Guard ist derzeit ein Nettoverlust: Er liefert in
  `PMC4319071:T2` einen exakten Wert, zerstoert aber in fuenf Tabellen Felder.
- Commits sind lokal; kein Push in dieser Sitzung.

## 7. Naechste Schritte

1. **Kopfband-Guard absichern** (groesster Hebel, offline, kein Guthaben):
   Neuordnung nur behalten, wenn sie keine ueberlappenden Baender erzeugt und
   keine Felder entfernt, sonst Tabellenstand zuruecknehmen. Erwartung:
   56 Goldfelder, 0 Fehler, `PMC4319071`-Gewinn bleibt.
2. **Auswahlregel auf Spalten-Zeitpunkte ausweiten** (mittel): `_timepoint_key`
   kennt nur Gruppenzeilen; Tabellen mit Zeitpunkten im Kopf bleiben aussen vor.
3. **Modellauflauf** (teuer, nur mit Freigabe): erst nach Schritt 1, sonst wird
   gegen eine bekannte Fehlerquelle gemessen.

## 8. Belegdateien

| Datei | Inhalt |
| --- | --- |
| `auswahl_20261118.md` | Regel, dev-Gegenprobe, PMC4319071, Struktur-Artefakt, Bisect |
| `auswahlregel_20261118.json` | dev- und PMC-Messung der Auswahlregel |
| `dev_auswahlregel_20261118.json` | Gegenprobe: dev-Dokumente mit mehreren Zeitpunkttabellen |
| `offline_struktur_20261118b/structure.json` | aktuelles Struktur-Artefakt (46 Goldfelder) |
| `bisect_20261118/bisect_20261118.json` | Stufen, Befund, Gegenprobe |
| `bisect_20261118/<stufe>/structure.json` | neun Einzellaeufe des Bisects |
| `zeilenrollen_20261118.md`, `zeilenarme_20261118.md`, `kopf_ordnung_20261118.md`, `dokumentarm_20261118.md` | Berichte der Sprints 36-39 |
| `IMPLEMENTATION_LOG.md` (Repo-Wurzel) | Sprint-Protokoll 36-42 |
