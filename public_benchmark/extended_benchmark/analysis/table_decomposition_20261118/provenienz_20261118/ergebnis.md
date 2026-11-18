# Sprint 45 - Provenienz und semantische Validierung der Gruppengroessen

Stand 18.11.2026. Offline, rein lesend: kein Modelllauf, kein Netz, Gold und
eingefrorene Eingaben unveraendert. Alle Zahlen stammen aus
`messung.json` (erzeugt von
`public_benchmark/extended_benchmark/table_decomposition/diagnose_provenienz.py`).

## 0. Kurzfassung

| Groesse | Wert |
| --- | --- |
| strukturell erreichbare Goldfelder | 94 |
| davon wertgleich an der belegten Stelle | 58 |
| nicht wertgleich | 36 |
| `exact_value` | 0 |
| `sum_of_subgroups` | 3 |
| `subgroup_vs_total` | 3 |
| `population_mismatch` | 15 |
| `timepoint_mismatch` | 6 |
| `unexplained` | 9 |

Von den 94 erreichbaren Feldern sind 49 direkt gedruckt, 41 mehrfach belegt
(mehrere Fundstellen, keine einzelne gedruckte Gruppengroesse) und 4 aus einer
Verbundzelle abgeleitet. Der Arm ist bei allen 94 eindeutig.

## 1. Reproduktion

```
python public_benchmark/extended_benchmark/table_decomposition/diagnose_provenienz.py \
    --out public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/provenienz_20261118/messung.json
```

Das Skript liest dieselbe Auswahl und dieselben Records wie die Kursiv-Messung
(`run_benchmark.DEFAULT_SELECTION`, `DEFAULT_RECORDS`), ermittelt die
erreichbaren Felder ueber `reachable_cells` und die Fundstellen ueber
`research_agent.table_decomposition.provenienz`. Die Bilanz 94/58 ist
identisch mit `kursiv_n_20261118/messung.json`; die 54 vor Sprint 44
erreichbaren Felder bleiben unveraendert.

## 2. Phase 1 - Volltextpruefung der Armkonflikte

Gelesen wurden die eingefrorenen Markdown-Dokumente
(`.../no_attributes_markdown_files/PMC5617873.md`, `PMC5777419.md`)
vollstaendig: Fließtext, alle Tabellen, Fussnoten, Methoden- und
Ergebnisabschnitt.

### PMC5617873:T2 (`yun2024:335`, `yun2024:336`)

Belege im Dokument:

* Abstract: "Ninety-two patients were randomized to placebo (n = 45) or
  aripiprazole (n = 47)."
* Ergebnisse: "92 patients were randomly assigned to receive placebo (n = 45)
  or aripiprazole (n = 47)."
* Baseline-Tabelle (T1): "Placebo (n = 45) Aripiprazole (n = 47) Total (n = 92)".
* Nebenwirkungstabelle (T3): "Placebo (n = 45) Aripiprazole (n = 47)".
* Gegenprobe: "Forty-two (93.3%) patients in the placebo group" (42/45 = 93,3 %)
  und "the last dose of placebo corresponding to aripiprazole (n = 45)".
* Methoden: "Patients received flexibly dosed aripiprazole (1--15 mg/day) or
  placebo." - die Gruppen sind dort nicht beziffert.
* Fussnoten `a`-`c` der Tabellen: "Mean (standard deviation)", IQ-Definition,
  "Ratio between aripiprazole and placebo" - keine Armzahl.

Befund: **45 = Placebo (Vergleichsarm), 47 = Aripiprazol (Interventionsarm)**,
dreifach unabhaengig belegt (Abstract, Ergebnisse, zwei Tabellen) und durch die
93,3 %-Gegenprobe gestuetzt. Der Parser bindet wie der Text: `Aripiprazole
(n = 47)` haengt an `intervention`, das Placebo-Band bleibt ohne Arm, weil der
Vergleichsarm im Record `Placbeo` heisst. Der Widerspruch sitzt im **Goldfeld**
(intervention 45, comparator 47). Keine Armumkehr.

### PMC5777419:T2 (`yun2024:678`, `yun2024:682`)

Belege im Dokument:

* Methoden: "randomly assigned to a probiotic (n=16), antibiotic (n = 16) or
  placebo (n = 15) group."
* Analyse: "Forty-seven patients, 16 in the probiotic group, 16 in the
  antibiotic group and 15 in the placebo group were analyzed."
* Baseline-Tabelle (T1): "Probiotic group (n=16) Antibiotic group (n=16)
  Placebo group (n=15)".
* Ergebnis-Tabelle (T3): "Day 0 16 (100%) 16 (100%) 15 (100%)".
* Fussnoten: nur Abkuerzungen (CAL, PPD, BOP, CFU), keine Armzahl.

Befund: **Antibiotika = 16, Placebo = 15**, das Gold (intervention 16,
comparator 15) ist richtig. Der Konflikt entsteht im Kopfband: der Rohtext
stellt die drei Groessen unter die drei Gruppen, der Parser legt `(n=15)` ueber
die Spalten 6-10 (Antibiotic) und zerlegt das Probiotic-`(n=16)` in zwei
Baender ueber c2 und c5. Die Zahl 16 ist im Dokument gedruckt (Text und T1),
nur nicht an der Adresse, die der Parser ihr gibt.

In beiden Faellen bleibt die Armzuordnung unveraendert; es gibt keine
automatische Umkehrung und keine Uebernahme aus dem Goldwert. Die vollstaendigen
Zitate stehen zusaetzlich maschinenlesbar unter `armkonflikte` in
`messung.json`.

## 3. Phase 2 - die 36 nicht wertgleichen Felder

Vergaberegel: Eine Klasse wird nur vergeben, wenn der Beleg automatisch
geprueft ist - Zitat im Dokument (ohne Auszeichnung, Leerraum normalisiert),
Summe der gedruckten Kopfangaben, oder der Wert steht an einer anderen Stelle
derselben Tabelle beziehungsweise eines anderen Tabellenzugs. Schlaegt die
Pruefung fehl, faellt das Feld auf `unexplained`. `exact_value` bleibt bei 0,
weil die Liste per Definition nur nicht wertgleiche Felder enthaelt.

| Record | Tabelle | Feld | Gold | gedruckt an der Adresse | Klasse |
| --- | --- | --- | --- | --- | --- |
| `yun2024:185` | PMC5122613:T1 | `comparator_group_size` | 28 | Placebo (*n* = 33) | population_mismatch |
| `yun2024:194` | PMC5360580:T1 | `comparator_group_size` | 167 | Placebo group (n = 140) | population_mismatch |
| `yun2024:194` | PMC5360580:T1 | `intervention_group_size` | 169 | Pls group (n = 145) | population_mismatch |
| `yun2024:265` | PMC2430617:T1 | `comparator_group_size` | 79 | Placebo group (N = 78) | population_mismatch |
| `yun2024:265` | PMC2430617:T1 | `intervention_group_size` | 83 | 30 µg YIC (N = 81), 60 µg YIC (N = 78) | population_mismatch |
| `yun2024:266` | PMC2430617:T1 | `comparator_group_size` | 79 | Placebo group (N = 78) | population_mismatch |
| `yun2024:266` | PMC2430617:T1 | `intervention_group_size` | 80 | 30 µg YIC (N = 81), 60 µg YIC (N = 78) | population_mismatch |
| `yun2024:531` | PMC4230312:T3 | `comparator_group_size` | 204 | Placebo (n = 214) | population_mismatch |
| `yun2024:531` | PMC4230312:T3 | `intervention_group_size` | 289 | Quetiapin 300 (n = 298), 600 (n = 307) | population_mismatch |
| `yun2024:532` | PMC4230312:T1 | `comparator_group_size` | 204 | Placebo (n = 214) | population_mismatch |
| `yun2024:532` | PMC4230312:T1 | `intervention_group_size` | 283 | Quetiapin 300 (n = 298), 600 (n = 307) | population_mismatch |
| `yun2024:645` | PMC4675066:T1 | `comparator_group_size` | 26 | Placebo (*n* = 30) | population_mismatch |
| `yun2024:645` | PMC4675066:T1 | `intervention_group_size` | 27 | Iodine (*n* = 29) | population_mismatch |
| `yun2024:647` | PMC4675066:T1 | `comparator_group_size` | 26 | Placebo (*n* = 30) | population_mismatch |
| `yun2024:647` | PMC4675066:T1 | `intervention_group_size` | 27 | Iodine (*n* = 29) | population_mismatch |
| `yun2024:494` | PMC5419060:T3 | `intervention_group_size` | 630 | 4 (0.68), 5 (0.05), 6 (0.15), ... | subgroup_vs_total |
| `yun2024:78` | PMC3546023:T4 | `intervention_group_size` | 30 | Palmvitee, n = 3 / 19 / 8 | subgroup_vs_total |
| `yun2024:79` | PMC3546023:T4 | `intervention_group_size` | 30 | Palmvitee, n = 3 / 19 / 8 | subgroup_vs_total |
| `yun2024:172` | PMC5079604:T1 | `intervention_group_size` | 33 | Metformin (*n* = 17), Sitagliptin (*n* = 16) | sum_of_subgroups |
| `yun2024:174` | PMC5079604:T1 | `intervention_group_size` | 33 | Metformin (*n* = 17), Sitagliptin (*n* = 16) | sum_of_subgroups |
| `yun2024:662` | PMC4987981:T1 | `intervention_group_size` | 37 | Metformin 21, Pioglitazon 16 | sum_of_subgroups |
| `yun2024:445` | PMC4140238:T2 | `comparator_mean` | 2.1 | 1.2 (68), 0.5 (70), 0.8 (64) | timepoint_mismatch |
| `yun2024:445` | PMC4140238:T2 | `intervention_mean` | 1.2 | 1.4, 1.3, 0.9 | timepoint_mismatch |
| `yun2024:665` | PMC4987981:T2 | `comparator_mean` | 97.6 | 2.2 ± 10.0 | timepoint_mismatch |
| `yun2024:665` | PMC4987981:T2 | `comparator_standard_deviation` | 20.8 | 2.2 ± 10.0 | timepoint_mismatch |
| `yun2024:665` | PMC4987981:T2 | `intervention_mean` | 103.4 | 15.2 ± 19.2 | timepoint_mismatch |
| `yun2024:665` | PMC4987981:T2 | `intervention_standard_deviation` | 28.9 | 15.2 ± 19.2 | timepoint_mismatch |
| `yun2024:196` | PMC5360580:T6 | `comparator_group_size` | 24 | Placebo group (n = 167) | unexplained |
| `yun2024:196` | PMC5360580:T6 | `intervention_group_size` | 24 | Pls group (n = 169) | unexplained |
| `yun2024:335` | PMC5617873:T2 | `intervention_group_size` | 45 | Aripiprazole (n = 47) | unexplained |
| `yun2024:336` | PMC5617873:T2 | `intervention_group_size` | 45 | Aripiprazole (n = 47) | unexplained |
| `yun2024:421` | PMC3877023:T3 | `intervention_mean` | 0.83 | 2.2 (1), .03, 1.7 (0.7) | unexplained |
| `yun2024:421` | PMC3877023:T3 | `intervention_standard_deviation` | 0.22 | 2.2 (1), 1.7 (0.7) | unexplained |
| `yun2024:426` | PMC3877023:T4 | `comparator_group_size` | 44 | n = 18, n = 30 | unexplained |
| `yun2024:678` | PMC5777419:T2 | `intervention_group_size` | 16 | (n=15) | unexplained |
| `yun2024:682` | PMC5777419:T2 | `intervention_group_size` | 16 | (n=15) | unexplained |

### Was die Klassen bedeuten

**`population_mismatch` (15 Felder, 5 Dokumente).** Die gewaehlte Tabelle
druckt eine andere Population als das Gold; die groessere Zahl steht im
Dokument.

* PMC4230312 (4 Felder): "A total of 776 (35.2%) patients ... were included in
  the ITT population (283, 289, and 204 patients ...)" gegen "The safety
  population comprised 819 patients ... (298, 307, and 214)". Die gewaehlten
  Tabellen sind Safety-Tabellen, das Gold ist ITT.
* PMC2430617 (4 Felder): 242 randomisiert (83/80/79), "Five patients ... were
  excluded from the intent-to-treat analysis"; die gewaehlte Tabelle druckt
  81/78/78.
* PMC4675066 (4 Felder): Baseline 29/30, Ergebnis-Tabelle 27/26.
* PMC5360580 (2 Felder): Tabelle 6 druckt 169/167, die gewaehlte Tabelle
  145/140; Fließtext "328 patients enrolled, 276 patients completed".
* PMC5122613 (1 Feld): "Fifty-seven subjects were assessed for CTT (placebo,
  n = 28; RMD, n = 29)" gegen Baseline 33.

**`timepoint_mismatch` (6 Felder).** Der Wert steht im Dokument, aber zu einem
anderen Zeitpunkt. PMC4987981 (4 Felder): T1 druckt den Baselinewert
103.4 (±28.9) beziehungsweise 97.6 (±20.8), die gewaehlte Tabelle die
Aenderung. PMC4140238 (2 Felder): 1.2 und 2.1 stehen in derselben Tabelle in
einer anderen Zeitpunktspalte (r6/c3, r8/c2 beziehungsweise r1/c1, r3/c2).

**`subgroup_vs_total` (3 Felder).** Das Gold ist die Gesamtgruppe, die Tabelle
druckt nur Untergruppen. PMC5419060: 630 Proben (Juli 2014, CDC D), die Tabelle
listet Ablehnungsgruende (4/630 = 0.68 %). PMC3546023: die Tabelle druckt drei
Raucherstrata (3/19/8), die Gesamtgruppe 30 steht als Kopfangabe in T1.

**`sum_of_subgroups` (3 Felder).** Das Gold ist die Summe zweier gedruckter
Untergruppen, die Summe selbst ist nirgends gedruckt. PMC5079604:
17 + 16 = 33 ("we combined the metformin and sitagliptin groups").
PMC4987981: 21 + 16 = 37 ("23, 16 and 21 patients were randomized to placebo,
pioglitazone and metformin").

**`unexplained` (9 Felder).** Keine der fuenf Klassen traegt; der Befund ist
trotzdem dokumentiert:

* `yun2024:335`/`:336`: Armvertauschung im Gold (Phase 1). Die Kategorienliste
  kennt keinen Armfall; das Feld bleibt `unexplained`, der Beleg steht im
  Befund.
* `yun2024:678`/`:682`: verschobene Kopfbaender (Phase 1).
* `yun2024:421` (2): 0.83 (SD 0.22) steht nur im Fließtext, die Tabelle druckt
  2.2 (1) / 2.7 (0.7) - andere Skala, kein Tabellenbeleg.
* `yun2024:426` (1): die gewaehlte Tabelle druckt SNR-Werte; 44/49 stammen aus
  einer anderen Tabelle (Short-Bore MR n = 44, Open MR n = 49), die Mittel
  32±22 und 20±9 aus dem Fließtext.
* `yun2024:196` (2): die gewaehlte Tabelle listet Krebsereignisse mit n =
  169/167; 24 erscheint im Dokument nur als Wochenzahl, nie als Gruppengroesse.

## 4. Phase 3 - Provenienzmodell

Neu: `research_agent/table_decomposition/provenienz.py` (nur lesend, keine
Aenderung an der Produktionslogik). Jedes Feld laesst sich je Fundstelle
beschreiben:

| Feld | Inhalt |
| --- | --- |
| `tabelle`, `zeile`, `spalten` | Tabelle, Datenzeile (-1 = Kopf), Spalten |
| `quelle` | `kopfangabe` oder `messzelle` |
| `text` | Originaltext der Fundstelle |
| `wert` | gedruckte Zahl, nur bei genau einer Zahl |
| `arm`, `arm_basis` | zugeordneter Arm und seine Herkunft |
| `zeitpunkt` | Zeitangabe aus der Kopfbeschriftung, sonst leer |
| `art` | `direkt`, `abgeleitet` oder `mehrfach` |
| `regel` | `gruppengroesse_im_kopf`, `spaltenfeld`, `rolle_aus_zeilenlabel`, `arm_als_zeile`, `zweitwert_der_spalte`, `zweitwert_der_zelle` |
| `sicherheit` | `hoch`, `mittel`, `niedrig` |

Die drei Arten sind strikt getrennt:

* **direkt**: genau eine Zahl an der Stelle (Kopfangabe oder Einzelzelle).
* **abgeleitet**: eine Verbundzelle (`2.2 (1)`, `15.2 ± 19.2`); der Wert
  entsteht erst durch die Regel, `wert` bleibt leer.
* **mehrfach**: mehrere Fundstellen. Zwei Untergruppen (`n = 17`, `n = 16`)
  ergeben `mehrfach` - **eine Summe ist damit nie eine gedruckte
  Gruppengroesse**. Genau das verlangt Phase 3; die 41 mehrfach belegten Felder
  sind der sichtbare Beleg dafuer.

`feld_arm` liefert `eindeutig`, `mehrdeutig` oder `ohne` und raet nicht: ohne
Arm bleibt es `ohne`. Tests:
`research_agent/tests/test_provenienz.py` (5 Tests) prueft die Summenregel
(17/16 -> mehrfach), die einzelne Kopfangabe (47, Arm intervention, hoch), das
verschobene Band (`(n=15)`), die Verbundzelle (abgeleitet, kein Wert) und die
Streuung aus dem Zweitwert der Spalte.

## 5. Phase 4 - Messung

1. strukturell erreichbar: **94**
2. wertgleich: **58**
3. nicht wertgleich: **36**
4. Verteilung: `population_mismatch` 15, `timepoint_mismatch` 6,
   `subgroup_vs_total` 3, `sum_of_subgroups` 3, `unexplained` 9,
   `exact_value` 0
5. direkt 49, abgeleitet 4, mehrfach 41 (Summe 94)
6. Arm eindeutig 94, mehrdeutig 0, ohne 0; Sicherheit hoch 73, mittel 21,
   niedrig 0
7. Armkonflikte: vollstaendig in Abschnitt 2 und unter `armkonflikte` in
   `messung.json`

Reproduzierbar: dieselbe Auswahl, dieselben Records, kein Zufall, keine
Netzabfrage. Die 58 wertgleichen Felder sind gegenueber Sprint 44 unveraendert.

## 6. Grenzen

* Die Klassifikation ist je Feld kuratiert (`BELEGE` im Skript); die
  **Pruefung** ist automatisiert: Zitat im Dokument, Summe der Kopfangaben oder
  Wert an anderer Stelle. Ein nicht belegter Eintrag faellt auf `unexplained`.
* Die Kategorienliste kennt keinen Armfall. `yun2024:335`/`:336` bleiben
  deshalb `unexplained`, obwohl der Beleg eindeutig ist.
* `population_mismatch` sagt nicht, welche Population die richtige ist. Das
  Gold nennt die analysierte Population, die gewaehlte Tabelle eine andere;
  welche fuer die Meta-Analyse gilt, entscheidet der Record, nicht der Parser.
* Der Zeitpunkt in der Provenienz stammt aus der Kopfbeschriftung und ist leer,
  wenn dort keine Zeitangabe steht. Er ist eine Lesehilfe, keine Zusicherung.
* Die Produktionslogik wurde nicht angefasst; die 36 Felder bleiben
  nicht wertgleich.

## 7. Empfehlung fuer Sprint 46

**Groesster Hebel: die 15 `population_mismatch`-Felder.** Sie stammen aus nur
fuenf Dokumenten und haben ein gemeinsames Muster: die gewaehlte Tabelle
druckt Safety- beziehungsweise Baseline-Zahlen, das Gold die analysierte
Population (ITT, "assessed", "analyzed"). Ein Sprint 46 sollte offline messen,
wie oft ein Dokument die passende Population in einer **anderen Tabelle
desselben Dokuments** druckt - das ist bei 10 der 15 Felder bereits der Fall
(PMC5360580 T6 mit 169/167, PMC2430617 T4-Kopf mit 79/83/80, PMC4675066 T2 mit
27/26); bei den uebrigen fuenf steht die Zahl nur im Fließtext (PMC4230312,
PMC5122613). Dann pruefen, ob eine Regel "Population aus der Kopfbeschriftung
waehlen" diese Tabelle trifft, ohne die Armzuordnung anzufassen. Kosten: null
Guthaben, rein offline.

Zweiter Hebel, kleiner: die **Bandgeometrie** bei whitespace-aufgeblaehten
Kopfzeilen (PMC5777419, 2 Felder) - die Zahl ist gedruckt, nur falsch
adressiert. Dritter Hebel: `yun2024:421`/`:426` sind Textwerte, keine
Tabellenwerte; dafuer ist die Tabellenzerlegung nicht zustaendig.
