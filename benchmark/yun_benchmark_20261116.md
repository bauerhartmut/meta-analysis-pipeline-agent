# Yun-2024-Benchmark mit dem aktuellen GLM-Agenten — Stand 16.11.2026

**Status: Infrastruktur fertig. Trockenlauf mit fünf Aufgaben und gestaffelter
Testlauf mit 60 geschichteten Testrecords sind gelaufen und gegen die offiziellen
Goldannotationen ausgewertet, zusätzlich in der Yun-Zählweise (Exact/Partial/
Unknown). Der Rest der 656 Testrecords ist noch nicht gelaufen** — Hochrechnung
aus dem 60er-Lauf: ~1,7 Mio. Tokens und ~2,5 Stunden für die übrigen 596 Records;
Entscheidung darüber steht aus.

Getrennt vom bisherigen 76-Record-Benchmark: eigener Datensatz, eigene
Record-Datei, eigene Auswertung, keine gemeinsamen Kennzahlen.

## 1. Herkunft und Lizenz

| | |
|---|---|
| Repository | https://github.com/hyesunyun/llm-meta-analysis |
| Commit (lokal, shallow) | `1bc768d4d098c727c9866eeff909297c38a3e84c` |
| Paper | Yun, Pogrebitskiy, Marshall, Wallace: *Automatically Extracting Numerical Results from Randomized Controlled Trials with Large Language Models*, MLHC 2024 (arXiv 2405.01686, PMC12448672) |
| Lizenz | Apache License 2.0 (`LICENSE` im Repository) |
| Lokaler Pfad | `public_benchmark/raw_data/yun_llm_meta_analysis/` (Git-Clone, unverändert) |

Der Datensatz war bereits als Klon im Projekt vorhanden; für diesen Auftrag wurde
er nicht neu geladen, sondern gegen seinen Commit und seine Hashes verifiziert.
Das Original wurde nicht verändert (kein Schreibzugriff, `git status` im Klon
sauber).

## 2. Download und SHA-256

| Datei | SHA-256 | Bytes |
|---|---|---|
| `evaluation/data/annotated_rct_dataset.json` | `d8f666fdd70a2e7f4ed9d4334cda8f949c85f9c4ef45c3c66e69ba555a4d7e9a` | 682.536 |
| `evaluation/data/annotated_rct_dataset.csv` | `5e5f660fa770ab647fa44424f002c7b9e1a2b6a3feb783ee2dc4f2438c1017f6` | 157.072 |
| `evaluation/data/meta_analysis_case_study.json` | `cb7af79795ca96c7eec9f7e0e52d304fb2e645ff3c190c2c38323a1ea6ad9fca` | 4.364 |
| `evaluation/data/DATASET.md` | `f354cc7562f1b1d057e7b3be4a28a772079281bddad40972b1094f25f8f7ff14` | 1.188 |
| Textkorpus `no_attributes_markdown_files/` (120 Dateien) | Sammelhash `09564bfd…` über `sha256  bytes  name` je Datei | 1.483.955 gesamt |

Einzelhashes aller 120 Textdateien: `yun_full/texte_manifest.txt`. Vollständiges
Manifest inklusive Zählungen und Schema-Mapping: `yun_full/manifest.json`.

## 3. Datenstruktur

Ein Record ist ein **ICO-Tripel** (Intervention, Comparator, Outcome) mit den
numerischen Feldern des jeweiligen Outcome-Typs. Am Original verifiziert:

| Kennzahl | Wert |
|---|---|
| Records gesamt | **699** (Paper: 699 ✓) |
| Artikel (PMCID) | **120** (Paper: 120 ✓) |
| Dev-Split | 43 Records aus 10 Artikeln (Paper: 43 ✓) |
| Test-Split | **656** Records aus **110** Artikeln (Paper: 656 ✓) |
| Outcome-Typen | 517 kontinuierlich, 182 binär |
| Goldzellen | **2.773** (davon Test 2.603, Dev 170) |
| Records ohne jede numerische Annotation | 31 (davon 26 im Test) |
| `is_data_complete` | 412 TRUE / 287 FALSE |
| Felder | `id, evidence_inference_prompt_id, pmcid, outcome, intervention, comparator, outcome_type, intervention_events, intervention_group_size, intervention_mean, intervention_standard_deviation, comparator_*, notes, is_data_in_figure_graphics, is_relevant_data_in_table, is_table_in_graphic_format, is_data_complete, tiktoken_*_token_num, split` |

**Text:** `abstract_and_results_xml_files` (Roh-XML), `no_attributes_xml_files`
(ohne Stil-Tags), `no_attributes_markdown_files` (Markdown, das die Autoren als
Modelleingabe nutzen). Vorhanden für **alle 120 Artikel** (Dateiname `PMC<id>.md`);
keine fehlenden Volltexte. Es sind Abstract + Results, keine Volltexte.

**Fehlend/unvollständig im Original:** kein Zeitpunktfeld; kein Quellenbeleg
(kein Satz-/Tabellenverweis) pro Zelle; keine Einzelannotationen (nur die
konsolidierte Doppelannotation); 31 Records ohne jeden Zahlenwert;
`notes` ist Freitext, keine strukturierte Begründung.

## 4. Schema-Mapping

Adapter: `yun_full/baue_yun699.py` → `yun_full/records/yun699.jsonl`
(SHA-256 `c22ed3fb…`, 699 Zeilen). Originalwerte bleiben als `raw` je Zelle
erhalten, jede Zelle trägt `source` (Originalfeldname).

| Yun-Feld | Harness-Feld |
|---|---|
| `id` | `record_id` = `yun2024:<id>`, `provenance.source_id` |
| `pmcid` | `document.id` = `PMC<pmcid>` |
| `split` (DEV/TEST) | `document.split` (`dev`/`test`) |
| `intervention` | `context.intervention` |
| `comparator` | `context.comparator` |
| `outcome` | `context.outcome` |
| `outcome_type` | `context.outcome_type` |
| `intervention_mean` / `_standard_deviation` / `_group_size` | `gold.cells` mit `field=intervention_mean` / `intervention_standard_deviation` / `intervention_group_size`, `arm=intervention` |
| `comparator_mean` / `_standard_deviation` / `_group_size` | dito mit `arm=comparator` |
| `intervention_events` / `comparator_events` | `gold.cells` mit `field=…_events` |
| `notes` | `issues[0]`, zusätzlich `provenance` |
| **Zeitpunkt** | **nicht vorhanden** → `timepoint.target` trägt die Papierregel als Text (siehe 6) |

Unterschiede, die nicht glatt aufgehen:

* **Kein Zeitpunkt.** Unser Schema erwartet `timepoint.target`; Yun hat keines.
  Der Wert ist deshalb eine Regel, kein Datum, und wird in der Auswertung nicht
  bewertet.
* **Andere Zellzählung.** Unser 76er-Benchmark annotiert ein festes
  Zell-Soll (6 bzw. 4 Felder); Yun lässt Felder leer, wenn das Paper sie nicht
  berichtet. 26 Test-Records haben gar keine Zelle — das sind gültige Aufgaben,
  aber nicht zellbewertbar.
* **Tausendertrenner.** 14 Originalwerte tragen Kommas (`1,919`, `6,032.37`).
  Sie werden nach Muster `^\d{1,3}(,\d{3})+(\.\d+)?$` normalisiert, im Record mit
  `normalisiert: true` markiert, `raw` bleibt erhalten. Ohne dieses Muster wird
  nichts geraten.
* **Sechs Zellen passen nicht zum `outcome_type`** (kontinuierliche Records mit
  `comparator_events`, u. a. `yun2024:455`–`457`). Sie sind übernommen und im
  Manifest als `feld_typ_abweichungen` gelistet, nicht korrigiert.
* **Keine Quellenstelle.** Unser Gold trägt teils `spans`; Yun hat keine. Für
  Yun-Records bleibt `spans` leer.

## 5. Verwendbare Testaufgaben

* **656 Test-Records aus 110 Artikeln**, Text für alle vorhanden.
* Davon **630 mit mindestens einer Goldzelle**, **26 ohne** (nicht zellbewertbar).
* Goldzellen im Test: **2.603**; 485 kontinuierliche, 171 binäre Records.
* Dev-Split (43 Records, 10 Artikel) bleibt strikt getrennt und wurde in diesem
  Auftrag nicht gelaufen.

Der Agent erhält ausschließlich `document`, `context` und `timepoint.target`; die
Goldzellen stehen nur in der Record-Datei, aus der die Auswertung liest. Geprüft:
Der Prompt-Kopf (alles außer dem Artikeltext) enthält für die fünf Pilotrecords
keinen Goldwert (`test_yun699.py`).

## 6. Harness-Konfiguration

```
run_extended_extraction.py --models glm --split test \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
  --ids yun2024:6,yun2024:7,yun2024:12,yun2024:10,yun2024:11 \
  --cell-timepoint --target-fallback --repair --max-tokens 19000 --workers 3 \
  --run-id yun699_trockenlauf_20261116 --quelle yun699_trocken
```

| | |
|---|---|
| Modell | `gwdg/glm-5.3` (`glm`), Temperatur 0.0 |
| Promptstand | v7 (`--cell-timepoint`), unverändert |
| Datensatzversion | `yun699.jsonl`, SHA-256 `c22ed3fb…`, Quelle `1bc768d` |
| Auswertung | `yun_full/auswerte_yun699.py` (Zellvergleich, exakt) |
| Lauf | `runs/yun699_trockenlauf_20261116/` (predictions, Log, Auswertung) |

**Abweichung von v7, die dokumentiert werden muss:** v7 bindet den Zielzeitpunkt
an einen konkreten Wert aus dem Record. Yun hat kein Zeitpunktfeld, und einen
Zeitpunkt zu erfinden wäre eine unzulässige Annahme. Deshalb steht als Vorgabe
die Regel des Papers: `primary time point of the trial (if not stated: the last
reported time point)`. Die Zellzeitpunkt-Logik (ein Zeitpunkt pro Antwort,
Header, `fallback`) läuft unverändert; der Zeitpunkt wird nur nicht bewertet,
weil es keine Goldzeitpunkte gibt.

## 7. Tokenverbrauch und Laufzeit (Trockenlauf)

| Record | Finish | Tokens | Zeit | Zellen (Gold/Modell) |
|---|---|---:|---:|---|
| `yun2024:7` | stop | 1.041 | 11 s | 6 / 2 |
| `yun2024:6` | length → Reparatur | 19.000 | 106 s | 6 / 4 |
| `yun2024:12` | stop | 953 | 7 s | 6 / 6 |
| `yun2024:10` | stop | 875 | 41 s | 4 / 2 |
| `yun2024:11` | json_kaputt | 0 | 300 s | 4 / 0 |
| **Summe** | | **24.420** | 466 s summiert | 26 / 14 |

Wanduhr: 14:25–14:37, also **rund 12 Minuten für 5 Records** mit 3 Threads.

**Hochrechnung Testsplit (656 Records):**

* sauberer Pfad: ~956 Completion-Tokens je Record → **~0,63 Mio. Tokens**
* gemessener Durchschnitt inkl. Length-Ausreißer: 4.884 → **~3,2 Mio. Tokens**
* Wanduhr bei gleichem Durchsatz: **~26 Stunden**

Beides liegt weit über dem bisherigen Hauptlauf (552.552 Tokens, 40 Minuten).
Deshalb kein vollständiger Lauf ohne ausdrückliche Freigabe.

## 8. Evaluationsmetriken (Trockenlauf, n = 5)

Ausgewertet gegen die offiziellen Goldzellen, exakter Vergleich:

| Kennzahl | Wert |
|---|---|
| Goldzellen im Lauf | 26 |
| richtig | 12 |
| falsch | 2 |
| fehlend (Gold da, Modell schweigt) | 12 |
| Zellen ohne Gold | 0 |
| Precision | **0,8571** |
| Recall | **0,4615** |
| F1 | **0,6000** |
| Abdeckung (richtig/Gold) | 0,4615 |
| MAE (über 14 verglichene Zellen) | 2,2143 |
| Records exakt | 0 / 5 |
| Records teilweise | 4 / 5 |
| technische Ausfälle | 1 |
| leere Antworten | 0 |

Aufschlüsselung:

| Feld | richtig | falsch | fehlend |
|---|---:|---:|---:|
| `intervention_mean` | 3 | 0 | 1 |
| `intervention_standard_deviation` | 0 | 1 | 2 |
| `intervention_group_size` | 2 | 0 | 3 |
| `intervention_events` | 1 | 0 | 0 |
| `comparator_mean` | 3 | 0 | 1 |
| `comparator_standard_deviation` | 1 | 0 | 2 |
| `comparator_group_size` | 2 | 0 | 3 |
| `comparator_events` | 0 | 1 | 0 |

Nach Arm: Intervention 6 richtig / 1 falsch / 6 fehlend; Comparator 6 / 1 / 6.
Nach Outcome-Typ: kontinuierlich 11 / 1 / 12 (24 Zellen), binär 1 / 1 / 0 (2 Zellen).

Die MAE wird von einer einzigen Abweichung dominiert (12,34 statt 23,34).

**Definitionen:** Zellvergleich exakt; „fehlend" ist keine falsche Extraktion;
Zellen ohne Gold zählen nicht als Fehler; technische Ausfälle (kein JSON) werden
getrennt gezählt. Diese Zählung weicht von Yun ab (siehe 9).

## 9. Vergleich mit den Originalergebnissen

Offizielle Metriken aus dem Repository (`evaluation/metrics/*_metrics.json`,
lokal gespiegelt in `yun_full/official_metrics.json`), Testsplit:

| Modell | kont. exakt | kont. teilweise | bin. exakt | bin. teilweise | Punkt-MAE (SMD / logOR) |
|---|---:|---:|---:|---:|---|
| GPT-4 | 0,4866 | 0,9216 | 0,6550 | 0,9123 | 0,290 / 0,101 |
| GPT-3.5 | 0,2804 | 0,8722 | 0,2982 | 0,7485 | 0,951 / 0,441 |
| Mistral-7B | 0,0948 | 0,7938 | 0,1637 | 0,7076 | 1,138 / 0,657 |
| Gemma-7B | 0,0866 | 0,8103 | 0,1345 | 0,6784 | 3,466 / 0,913 |

**Keine direkte Vergleichbarkeit.** Die Bedingungen unterscheiden sich in vier
Punkten:

1. **Aufgabe:** Yun wertet `continuous_outcomes` und `binary_outcomes` als
   getrennte Aufgaben mit eigenem Prompt je Modell und Modellfamilie; wir fahren
   eine einheitliche v7-Extraktion, die `outcome_type` als Kontext erhält.
2. **Metrik:** Yun zählt Exact/Partial Match über Instanzen und je Feld, dazu
   Unknown-Zählungen und Punkt-Schätzer (SMD/logOR). Unsere Precision/Recall/F1
   zählen Zellen als Einheit; unsere MAE ist eine Wertabweichung, keine
   Punkt-Schätzer-Abweichung.
3. **Stichprobe:** hier 5 Records, dort 656.
4. **Zeitpunkt:** Yun hat keine Zeitpunktvorgabe; wir setzen die Papierregel als
   Text, was Antworten verlängern kann (ein 19.000-Token-Ausreißer).

Ein Vergleich unserer Zahlen mit GPT-4 wäre deshalb irreführend. Belastbar ist
erst ein Lauf über den vollen Testsplit mit derselben Zählung wie Yun.

## 10. Häufigste Fehler im Trockenlauf

1. **Auslassungen (12 von 14 Fehlzellen).** Vor allem SD und Gruppengrößen: Das
   Modell berichtet Mittelwerte, lässt SD und N weg oder findet sie nicht.
   Dasselbe Muster wie im 76er-Benchmark (dort 90 der 125 Auslassungen
   Gruppengrößen).
2. **Ein Wertfehler mit großer Wirkung:** `yun2024:12`
   `intervention_standard_deviation` 12,34 statt 23,34 — die MAE von 2,21 geht
   fast vollständig darauf zurück. Am Artikel nicht geprüft.
3. **Ein Ereignisfehler:** `yun2024:10` `comparator_events` 25 statt 5. Ebenfalls
   nicht am Artikel geprüft.
4. **Antwortformat:** ein Lauf endete mit `json_kaputt` nach 300 s und 0 Tokens.

## 11. Technische Probleme

* **Length-Ausreißer:** `yun2024:6` lief mit 19.000 Tokens in `length`; der
  Reparaturaufruf (6.000 Tokens) brachte vier Zellen, aber keinen Abschluss. Der
  Ausreißer allein kostet so viel wie 20 normale Aufgaben.
* **`json_kaputt` bei 0 Tokens:** `yun2024:11` lieferte nach 300 s keine verwertbare
  Antwort. Kein Retry (Regel des Runners bei Formatfehlern) — bewusst nicht
  wiederholt.
* **Langsame Antworten:** 300 s und 106 s bei zwei von fünf Aufgaben; die
  Durchsatzschätzung schwankt dadurch stark.
* **Zielzeitpunkt als Regeltext** verlängert den Prompt-Kopf um ~1,8–2,0k Zeichen
  und macht die Bindung weicher als bei einem Datum. Ohne Yun-Zeitpunktfeld ist
  das nicht vermeidbar, sollte aber im vollen Lauf beobachtet werden.

## 12. Empfehlungen

1. **Freigabe für den vollen Testsplit nur mit Kostenrahmen:** 0,6–3,2 Mio.
   Tokens, 20–30 h Wanduhr. Sinnvoll ist ein gestaffelter Lauf (z. B. 60 Records
   geschichtet nach Outcome-Typ, dann der Rest), damit ein Abbruch nach dem
   ersten Drittel noch eine belastbare Teilkennzahl liefert.
2. **Length-Ausreißer vorher adressieren:** Die Kombination aus Regel-Ziel und
   langen Results-Abschnitten erzeugt 19k-Token-Antworten. Ein Token-Deckel pro
   Antwort (z. B. 4.000) würde den Ausreißer billig machen, ohne den Prompt zu
   ändern — als Laufparameter, nicht als Promptänderung.
3. **Yun-Zählung zusätzlich implementieren:** Exact/Partial Match je Instanz und
   Unknown-Zählungen, damit der Vergleich mit GPT-4 (0,4866 / 0,9216) auf
   derselben Skala steht. Ohne das bleibt jeder Vergleich unbelegt.
4. **Vor dem Lauf die 14 Tausendertrenner-Zellen und die 6 Feld/Typ-Abweichungen
   sichten** — sie sind im Manifest gelistet und betreffen 11 Records.
5. **Kein Fine-Tuning, keine Promptänderung** aufgrund dieser fünf Records: Die
   Stichprobe ist zu klein, und der Fehlerschwerpunkt (Auslassungen bei SD/N) ist
   aus dem 76er-Benchmark bereits bekannt.

## Artefakte

| Pfad | Inhalt |
|---|---|
| `public_benchmark/extended_benchmark/yun_full/baue_yun699.py` | Adapter (Quellhash geprüft, reproduzierbar) |
| `…/yun_full/records/yun699.jsonl` | 699 Records im Harness-Schema, SHA-256 `c22ed3fb…` |
| `…/yun_full/manifest.json` | Quelle, Hashes, Zählungen, Mapping, Anomalien |
| `…/yun_full/texte_manifest.txt` | SHA-256 aller 120 Textdateien |
| `…/yun_full/auswerte_yun699.py` | Auswertung gegen Goldzellen |
| `…/yun_full/official_metrics.json` | offizielle Yun-Metriken je Modell |
| `…/runs/yun699_trockenlauf_20261116/` | predictions, Lauf-Log, Auswertung |
| `public_benchmark/raw_data/yun_llm_meta_analysis/` | unveränderter Originalklon |

## 13. Gestaffelter Testlauf: 60 geschichtete Testrecords

Freigabe: erst 60 Records, Token-Deckel 4.000 je Antwort, danach Entscheidung
über den Rest.

### Auswahl (deterministisch, ohne Blick auf Ausgaben)

`yun_full/baue_stichprobe.py` → `yun_full/stichprobe60.json`. Schichten nach
`outcome_type` × Zahl der Goldzellen, proportional zur Testverteilung
(Größte-Reste-Verfahren), Auswahl mit gleichmäßigem Schritt über die nach id
sortierte Schicht:

| Schicht | Test | gewählt |
|---|---:|---:|
| continuous, 6 Zellen | 242 | 22 |
| continuous, 4 Zellen | 45 | 4 |
| continuous, 3 Zellen | 3 | 0 |
| continuous, 2 Zellen | 175 | 16 |
| continuous, 0 Zellen | 20 | 2 |
| binary, 4 Zellen | 141 | 13 |
| binary, 2 Zellen | 24 | 2 |
| binary, 0 Zellen | 6 | 1 |
| **Summe** | **656** | **60** |

### Lauf

```
run_extended_extraction.py --models glm --split test \
  --records yun_full/records/yun699.jsonl --ids <60 ids aus stichprobe60.json> \
  --cell-timepoint --target-fallback --repair --max-tokens 4000 --workers 3 \
  --run-id yun699_test60_20261116 --quelle yun699_test60
```

| | |
|---|---|
| Tokens | **173.178** (2.886 je Record) |
| Laufzeit | ~15 Minuten Wanduhr, 2.031 s summiert, Median 18,8 s je Antwort |
| Antworten | 43 × `stop`, 17 × `length` (Deckel 4.000) |
| davon `length` ohne jede Zelle | 6 (technisch gescheitert) |
| leere Antworten | 11 (5 ohne Fehlerklasse + 6 `length_ohne_ergebnis`) |
| gemeldete Zellen | 180 |

Der Deckel hat den Ausreißer aus dem Trockenlauf (19.000 Tokens) auf 4.000
gedrückt, aber **28 % der Antworten laufen in den Deckel**; bei 6 Records bleibt
danach nichts verwertbar. 4.000 ist für diesen Prompt zu knapp.

### Eigene Zellmetriken

| Kennzahl | Wert |
|---|---|
| Goldzellen | 236 |
| richtig / falsch / fehlend | **144 / 29 / 63** |
| Zellen ohne Gold | 7 |
| Precision | **0,8000** |
| Recall | **0,6102** |
| F1 | **0,6923** |
| Abdeckung | 0,6102 |
| MAE (über 173 verglichene Zellen) | 6,2058 |
| Records exakt / teilweise / ohne Treffer | 27 / 20 / 2 |
| technische Ausfälle / leere Antworten | 6 / 11 |

| Feld | richtig | falsch | fehlend |
|---|---:|---:|---:|
| `intervention_mean` | 15 | 5 | 8 |
| `intervention_standard_deviation` | 10 | 5 | 8 |
| `intervention_group_size` | 36 | 5 | 13 |
| `intervention_events` | 10 | 1 | 2 |
| `comparator_mean` | 15 | 5 | 7 |
| `comparator_standard_deviation` | 10 | 5 | 8 |
| `comparator_group_size` | 39 | 2 | 13 |
| `comparator_events` | 9 | 1 | 4 |

Armbild: Intervention 71 richtig / 16 falsch / 31 fehlend, Comparator 73 / 13 /
32. Die MAE von 6,21 wird von wenigen großen Werten getragen (Gruppengrößen,
Extremwerte), nicht von systematischer Streuung.

### Yun-Zählweise (Exact/Partial/Unknown)

`yun_full/yun_metriken.py` bildet die Zählweise aus `calculate_metrics.py` nach:
fehlende Gold- und Modellzellen gelten als `x`, `x == x` ist ein Treffer; exact =
alle Felder des Tasks stimmen; partial_k = mindestens k Treffer.

| Task | n | exact | partial_1 | model_unknowns | reference_unknowns |
|---|---:|---:|---:|---:|---:|
| continuous | 44 | **0,4318** | 0,8864 | 55 | 85 |
| binary | 16 | **0,6250** | 1,0000 | 7 | 8 |

Feldtrefferquoten continuous: `intervention_mean` 0,6364,
`intervention_standard_deviation` 0,7045, `intervention_group_size` 0,6364,
`comparator_mean` 0,6818, `comparator_standard_deviation` 0,7045,
`comparator_group_size` 0,6818. Binary: 0,8125 / 0,8125 / 0,7500 / 0,8750.

### Vergleich mit GPT-4 — jetzt auf derselben Zählweise, aber nicht derselben Stichprobe

| Metrik | GLM-5.3 (60 Records) | GPT-4 (656 Records, Yun) |
|---|---:|---:|
| continuous exact | 0,4318 | 0,4866 |
| continuous partial_1 | 0,8864 | 0,9216 |
| binary exact | 0,6250 | 0,6550 |
| binary partial_1 | 1,0000 | 0,9123 |

**Zulässig ist jetzt der Vergleich der Zählweise, nicht der Population.** Offen
bleiben vier Unterschiede: (1) 60 geschichtete statt 656 Records, (2) eine
einheitliche v7-Extraktion statt getrennter Continuous-/Binary-Prompts und
modellspezifischer Templates, (3) Zeitpunktregel als Text statt keiner Vorgabe,
(4) 4.000-Token-Deckel, der 28 % der Antworten abschneidet — GPT-4 hatte keinen
solchen Deckel. Punkt 4 drückt unser Ergebnis; Punkt 2 kann es in beide
Richtungen verschieben.

Für die Punkt-Schätzer (SMD/logOR) fehlt der Vergleich: Yun nutzt dafür
`statsmodels`, das in dieser Umgebung nicht installiert ist. Eine eigene Näherung
wäre nicht Yun-identisch und wird deshalb nicht ausgewiesen.

### Hochrechnung Rest

| | 60 Records gemessen | 596 Records übrig |
|---|---:|---:|
| Tokens | 173.178 | **~1,72 Mio.** |
| Wanduhr | ~15 min | **~2,5 h** |

Der Deckel macht den Restlauf kalkulierbar. Vor dem Start sollte er aber auf
6.000–8.000 angehoben werden: bei 4.000 scheitern 6 von 60 Records vollständig,
was den Recall künstlich senkt und den Vergleich mit GPT-4 verzerrt.

---

**Hinweis zur Reproduzierbarkeit:** Rohläufe, Vergleichsdateien und die
Auswertungsskripte, aus denen diese Zahlen stammen, sind nicht veröffentlicht.
Die Werte sind dokumentierte Messungen mit dieser Einschränkung; Schätzungen sind
im Text als solche gekennzeichnet.
