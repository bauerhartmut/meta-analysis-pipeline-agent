# Erweiterter Cross-Model-Benchmark

Stand: 2026-11-14
Status: **Dateninfrastruktur aufgebaut; kein Modelllauf; kein Finetuning.**

Dieser Bereich ergänzt den bestehenden 54-Record-Benchmark aus GLASS um drei
öffentliche Datensätze und einen reproduzierbaren PMC-Open-Access-Downloader.
Bestehende Ergebnisse, Konfigurationen und der eingefrorene Yun-Testsplit
bleiben unangetastet.

## Was hier entsteht

| Datensatz | Aufgabe | Records | Gold-Zellen | Gold-Spannen | Quelle lokal |
|---|---|---:|---:|---:|---|
| Yun et al. 2024 | numerische Extraktion | 450 | 1.464 | – | `raw_data/yun_llm_meta_analysis` |
| Evidence Inference 2.0 | Evidenzrichtung + Beleg | 12.578 | – | 23.376 | `raw_data/evidence_inference_v2_0` |
| EBM-NLP 2.00 | PICO-Spannen | 4.985 | – | 85.845 | `raw_data/ebm_nlp` |
| PMC Open Access | Volltexte + Tabellen | nach Bedarf | – | – | Downloader |

Zählungen sind aus dem tatsächlichen Datenbestand erzeugt
(`manifest.json`), nicht aus den Papieren übernommen.

Split-Verteilung im erzeugten Bestand:

| Datensatz | train | dev | test |
|---|---:|---:|---:|
| Yun 2024 | – | 43 | 407 |
| Evidence Inference 2.0 | 10.117 | 1.237 | 1.224 |
| EBM-NLP 2.00 | 4.794 | – | 191 |

Die 407 Yun-Test-Records sind der Rest des Quell-Testsplits nach Abzug der 249
eingefrorenen C1-Records. Sie wurden nie kuratiert und nie für Prompt-Arbeit
verwendet; der eingefrorene Teil bleibt gesperrt.

## Warum diese Aufteilung

Die drei Aufgaben sind fachlich verschieden und werden getrennt bewertet:

1. **Numerische Extraktion** (Yun): N, Mean, SD, Ereignisse je Arm. Nur hier
   gibt es echte Armwerte.
2. **Evidenzrichtung** (Evidence Inference): Intervention, Comparator,
   Outcome und Richtung samt Textbeleg. Prüft Auffinden und Interpretieren,
   nicht Rechnen.
3. **PICO-Spannen** (EBM-NLP): Textspannen für Population, Intervention,
   Outcome. Prüft Segmentierung, keine Zahlen.

Ein einziger Gesamtscore über alle drei wäre irreführend; die Metriken bleiben
aufgabenspezifisch.

## Schema

`schema.json` definiert einen Record mit `document`, `context`, `gold` und
`provenance`. Regeln:

- Fehlt ein Wert, fehlt die Zelle. Es wird nichts geschätzt.
- Jede numerische Zelle nennt ihren Arm.
- `record_id` ist datensatzübergreifend eindeutig.
- Der eingefrorene Yun-Testsplit (249 Records) wird ohne `--include-frozen-yun`
  nicht aufgenommen.

## Aufbau

```
extended_benchmark/
  schema.json                  einheitliches Record-Schema
  adapters/common.py           Helfer (Zahlen, Zellen, Hashes)
  adapters/yun.py              Yun 2024 -> numeric_extraction
  adapters/evidence_inference.py  EI 2.0 -> evidence_direction
  adapters/ebm_nlp.py          EBM-NLP 2.00 -> pico_span
  predictions_schema.json     festes Format der Vorhersagedatei
  evaluate_extended.py         Bewertung je Aufgabe
  build_extended_benchmark.py  baut records/*.jsonl + manifest.json
  download_pmc_oa.py           PMC-OA-Downloader mit Tabellenparser
  records/                     erzeugte JSONL-Dateien
  manifest.json                Zählungen, Hashes, Lizenzen
```

## Ausführen

```bash
python public_benchmark/extended_benchmark/build_extended_benchmark.py
python public_benchmark/extended_benchmark/build_extended_benchmark.py --limit 20
python public_benchmark/extended_benchmark/download_pmc_oa.py --list-only
python public_benchmark/extended_benchmark/download_pmc_oa.py --pmcid PMC1216327 --limit 1 --sleep 1
python public_benchmark/extended_benchmark/download_pmc_oa.py --pmcids-file pmcids.txt --limit 50 --sleep 1
```

Der Build läuft offline auf den lokal vorhandenen Rohdaten und dauert rund
zweieinhalb Minuten (die EBM-NLP-Zuordnung ist der teuerste Teil).

## Bewertung

**Vorhersagedatei.** JSONL nach `predictions_schema.json`, eine Zeile je Record
mit `record_id`, `dataset` und `predicted`. Die Reihenfolge ist beliebig, die
Zuordnung erfolgt über `record_id`. Fehlt ein Record, zählt er als leere
Vorhersage; unbekannte IDs werden gemeldet und nicht bewertet.

```json
{"record_id": "yun2024:12", "dataset": "yun2024", "predicted": {"cells": [{"field": "intervention_group_size", "arm": "intervention", "value": 103}]}}
```

**Metriken je Aufgabe.**

| Aufgabe | Kennzahlen | Definition |
|---|---|---|
| `numeric_extraction` (Yun) | zellgenaue Precision/Recall/F1, MAE, Armvertauschung, Record-Exaktheit | Eine Zelle trifft, wenn Feld, Arm und Wert übereinstimmen (absolute und relative Toleranz einstellbar); Precision und Recall zählen tolerant. Der MAE läuft über Feld-Arm-Paare **unabhängig von der Toleranz**: Jede Gold-Zelle mit einer Vorhersage zum selben Feld und Arm zählt, auch wenn der Wert daneben liegt — sonst wäre er bei Standardtoleranz immer null. Armvertauschung zählt, wenn beide Arme eines Feldes vertauscht geliefert werden. |
| `evidence_direction` (Evidence Inference) | Label-Genauigkeit, Macro-F1, Spannen-F1 | Label wird je Record exakt verglichen. Spannen werden über IoU gematcht (Standard 0,5); Precision/Recall mikro über alle Records. |
| `pico_span` (EBM-NLP) | Token-F1 je Element, Macro-F1, Record-Exaktheit | Spannen werden als Tokenmengen je Element verglichen; Überlappung wird mikro gezählt. |

Bewusst kein gemeinsamer Gesamtscore: Die drei Aufgaben messen Verschiedenes,
und ein Mittelwert wäre nicht interpretierbar.

**Aufruf.**

```bash
python public_benchmark/extended_benchmark/evaluate_extended.py \
  --dataset yun \
  --records public_benchmark/extended_benchmark/records/yun.jsonl \
  --predictions vorhersagen.jsonl \
  --out ergebnis.json
```

Optionen: `--abs-tol` (Standard `1e-6`), `--rel-tol` (Standard `0`),
`--iou` (Standard `0.5`). Das Ergebnis-JSON enthält zusätzlich die
Feldaufschlüsselung bei Yun, die Label-Konfusionsmatrix bei Evidence Inference
und die Elementauflösung bei EBM-NLP.

## Extraktionslauf

`run_extended_extraction.py` schickt die Records eines Splits an ein Modell und
schreibt Vorhersagen im Bewertungsformat. Es wird nichts nachgebessert; ein
abgebrochener Lauf wird mit demselben Befehl fortgesetzt.

```bash
python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models qwen30 glm --split dev --workers 3 --run-id yun_dev_20261114
```

Ausgabe: `runs/<run_id>/predictions.jsonl` mit Status, Laufzeit, Parserfehler,
Prompt-Version und Zellen je (Record, Modell).

Für Diagnosen: `--ids <record_ids>` (nur diese Records), `--max-tokens`
(Budget überschreiben), `--save-content` (Rohantwort mitspeichern).

Antworten mit `finish_reason = "length"` bekommen automatisch einen zweiten
Versuch mit 32.000 Token (`RETRY_MAX_TOKENS`); `retried`, `retry_finish_reason`
und `retry_tokens` stehen in der Ausgabe. Laufzeiten unter einer Sekunde werden
als `suspected_cache` markiert: Das Gateway liefert dann offenbar eine frühere
Antwort erneut, der Lauf ist kein unabhängiger Messpunkt.

`--cache-buster` hängt einen zufälligen Session-Tag in den Systemprompt und
erzwingt damit eine neue Generierung. Der Lauf wird dann als eigene
Prompt-Version `v2b_cachebuster` geführt und nicht mit `v2_timepoint`
vermischt.

`PROMPT_VERSION` im Runner benennt die Standardfassung: **`v2_timepoint`**
(Werte am Ende der Intervention, nicht Baseline und nicht Follow-up). Sie hat
sich im Dev-Lauf als beste gemessene Fassung erwiesen.

`--absolute-counts` schaltet den Zusatz aus `v3_abs_count` ein („Ereignisse als
absolute Anzahl, nie als Prozent"). v3 lag im Dev-Lauf unter v2_timepoint
(F1 0,919 statt 0,945) und ist deshalb **nicht** Standard.

Ergebnisse unterschiedlicher Versionen sind nicht direkt vergleichbar;
`--cache-buster` hängt zusätzlich ein `_cb` an die Version.

Für Auswertungen gilt die feste Zuordnung in `versions.py`: `v2_timepoint`,
`v2b_cachebuster` und `v2_timepoint_cb` sind dieselbe Fassung (`v2_timepoint`),
`v3_abs_count[_cb]` ist `v3_abs_count`. Die Rohdaten der Läufe werden nicht
umschrieben, nur die Auswertung normalisiert.

## Fehleranalyse

`analyze_errors.py` vergleicht jede Vorhersage mit den Gold-Zellen,
klassifiziert Abweichungen nach festem Schema und schreibt vier Ausgaben:

```bash
python public_benchmark/extended_benchmark/analyze_errors.py \
  --out public_benchmark/extended_benchmark/analysis/v1_20261115
```

- `error_analysis.json`: Kennzahlen, Verteilungen nach Klasse, Modell, Feld und
  Prompt-Version, Ereignisdetails, Gold-Prüfung
- `error_analysis.md`: lesbare Fassung
- `error_cases.csv`: jede fehlerhafte, fehlende und zusätzliche Zelle
- `human_review_queue.csv`: Prüfwarteschlange mit fünf Prioritäten, **nur
  Referenzversion `v2_timepoint`**
- `human_review_discarded.csv`: Fälle der verworfenen `v3_abs_count`
- `human_review_historical.csv`: Fälle der historischen `v1`

Geprüft wird ausschließlich die Referenzdatei; die beiden anderen enthalten
dieselben Spalten mit Status `verworfen` bzw. `historisch`.

Das Modul liest nur; bestehende Läufe bleiben unverändert. Die Metriken werden
neu berechnet und gegen `eval/*.metrics.json` geprüft. Wo sich eine Ursache
nicht belegen lässt, steht "Nicht eindeutig klassifizierbar" statt einer
Vermutung. Der Abschlussbericht liegt in `next_iteration_report.md`.

## Rückfallregel `v6_target_fallback` (Referenz)

`--target-fallback` ist seit dem 15.11.2026 Standard (abschaltbar mit
`--no-target-fallback`). Es behält den Zielzeitpunkt aus dem Record als Vorgabe
und ersetzt das Auslassen: Ist ein Feld dort nicht berichtet, wird der
nächstliegende berichtete Zeitpunkt genommen und im Feld `timepoint` der Zelle
genannt. Records ohne Annotation bekommen automatisch den Text der vorherigen
Referenz `v2_timepoint`.

```bash
python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm --split dev --cache-buster --target-fallback \
  --run-id yun_dev_v6_20261115

python public_benchmark/extended_benchmark/evaluate_fallback.py \
  --run yun_dev_v6_20261115 \
  --out public_benchmark/extended_benchmark/analysis/v6_20261115/fallback_eval.json
```

`evaluate_fallback.py` trennt zieltreue Zellen und Rückfall-Zellen und weist
Auslassungen je Feld aus. Zwei frische Läufe auf den 43 Dev-Records: F1 0,944
und 0,963, MAE 0,039 und 0,0006, Abdeckung 0,953 und 0,988; Rückfall-Zellen 46
und 44 richtig, keine falsch. Bericht, Abschnitt 14. Referenz ab 15.11.2026:
`v6_target_fallback`.

## Zielzeitpunkt je Record (`v5_target_timepoint`)

`annotate_timepoints.py` pflegt den Zielmesszeitpunkt der Dev-Records als Feld
`timepoint` (`target`, `evidence`, `annotated`) in `records/yun_dev.jsonl` **und**
`records/yun.jsonl`; der Runner liest `yun.jsonl` und filtert den Split. Das
Skript bricht ab, wenn sich ein Gold-Wert ändern würde.

```bash
python public_benchmark/extended_benchmark/annotate_timepoints.py --write \
  --md public_benchmark/extended_benchmark/analysis/timepoints_annotation.md

python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm --split dev --cache-buster --target-timepoint \
  --run-id yun_dev_v5_20261115
```

`--target-timepoint` setzt den Record-Zeitpunkt als verbindliche Vorgabe und
verlangt, den benutzten wie die verworfenen Zeitpunkte zu nennen; `not stated`
im Record schaltet auf die Standardregel zurück. Ergebnis: Precision 0,937 und
MAE 0,0008, aber Abdeckung 0,700 (Auslassungen) — Bericht, Abschnitt 13.

## Zeitpunkt-Regel `v4_last_timepoint` (verworfen)

`--last-timepoint` verlangt den letzten berichteten Messzeitpunkt und lässt das
Modell den gewählten Zeitpunkt sowie die verworfenen Zeitpunkte mitliefern:

```bash
python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm --split dev --cache-buster --last-timepoint \
  --run-id yun_dev_v4_20261115

python public_benchmark/extended_benchmark/check_timepoints.py \
  --run yun_dev_v4_20261115 \
  --out public_benchmark/extended_benchmark/analysis/v4_20261115/timepoints_check.json
```

`check_timepoints.py` prüft ohne Modell, ob die genannten Labels wörtlich im
Artikel stehen, ob ein späterer Zeitpunkt verworfen wurde und wie oft die
Angabe fehlt; es korrigiert nichts. Die Fassung ist verworfen (F1 0,738 statt
0,933), weil die Gold-Annotation selbst keinen einheitlichen Zeitpunkt nutzt —
Befund in `next_iteration_report.md`, Abschnitt 12.

## Mehrstufige Ereignisextraktion (Prototyp)

`run_stage_extraction.py` ersetzt nur die beiden Ereignisfelder durch eine
zweistufige Extraktion: Stufe 1 benennt Zeilenlabel und Spaltenkopf, Stufe 2
liest die Zahl an dieser Stelle. Alle anderen Zellen kommen unverändert aus
einem Basislauf.

```bash
python public_benchmark/extended_benchmark/run_stage_extraction.py \
  --baseline-run yun_dev_std_20261115 --run-id stage_20261115 \
  --workers 3 --cache-buster

python public_benchmark/extended_benchmark/evaluate_stage_extraction.py \
  --stage-run stage_20261115 \
  --out public_benchmark/extended_benchmark/analysis/stage_20261115/stage_eval.json
```

Der Lauf schreibt `stage1.jsonl` (Locators), `stage2.jsonl` (Zahl mit Zitat)
und `predictions.jsonl` (gemergte Vorhersage, mit `staged_fields` und
`fallback_fields`). Die Bewertung weist Gesamtmetriken, Metriken nur auf den
Ereignisfeldern, den wörtlichen Belegabgleich der Zwischenstufe und die
Verschiebung je Ereigniszelle getrennt aus. Ergebnis im Bericht, Abschnitt 11:
keine Verbesserung, Prototyp nicht übernommen.

## Regelbasierte Prüfung

`validate_predictions.py` markiert unplausible Zellen (Ereignisse größer als
Gruppengröße, negative Ereigniszahlen) und **korrigiert nichts**:

```bash
python public_benchmark/extended_benchmark/validate_predictions.py \
  --run public_benchmark/extended_benchmark/runs/<run_id>
```

Ausgabe: `validation.json` im Laufverzeichnis mit Regel, Markierungen und
`korrigiert: false`. Die Prüfung läuft offline auf den gespeicherten
Vorhersagen.

## PMC-Open-Access-Downloader

Die alten FTP-Pakete (`oa_file_list.csv`, `oa_comm/`) hat NCBI im August 2026
abgeschaltet; der Bestand liegt jetzt im öffentlichen S3-Bucket
`pmc-oa-opendata` mit einem versionierten Verzeichnis je Artikel. Der
Downloader nutzt diesen Dienst: Er liest die Metadaten (inklusive
`license_code`), filtert auf Lizenzen ohne NC-/ND-Beschränkung (CC0, CC BY,
CC BY-SA) und lädt das XML des neuesten Stands.

Aus dem NXML werden erhalten:

- Titel, Abstract, Abschnitte,
- Tabellen mit `label`, `caption`, Kopfzeilen, Zeilen und Fußnoten,
- Angaben zu Supplementary Materials.

Der Zustand wird in `records/pmc_oa/state.jsonl` fortgeschrieben, ein Abbruch
ist also ohne Doppelarbeit fortsetzbar. Beispiel: `PMC1216327` (Lizenz CC BY)
liefert 6 Tabellen mit Kopfzeilen, Zeilen und Fußnoten; `PMC3298351`
(CC BY-NC-ND) wird korrekt übersprungen.

Die erzeugten Dateien unter `records/` und der Cache liegen nicht im Repo
(reproduzierbar über das Build-Skript); `manifest.json` hält Hashes und
Zählungen fest.

## Lizenzen

| Datensatz | Code/Annotationen | Texte |
|---|---|---|
| Yun 2024 | Apache-2.0 | PMC-Lizenz je Artikel |
| Evidence Inference 2.0 | MIT | PMC-Lizenz je Artikel |
| EBM-NLP 2.00 | EBM-NLP-Bedingungen | PubMed-Abstracts |
| PMC OA | – | nur CC0/CC BY/CC BY-SA heruntergeladen |

Die Rohdaten sind aus Größen- und Lizenzgründen nicht versioniert, sondern über
Commits und SHA-256 in `public_benchmark/source_registry.json` gepinnt.

## Offene Punkte

1. **Bewertungsskripte** für die drei Aufgaben (numerische Zellmetriken,
   Label-Genauigkeit, Spannen-F1) sind noch nicht gebaut.
2. **Split-Nutzung**: Evidence Inference hat offizielle Splits für 926 Artikel;
   die übrigen Annotationen haben `split: null` und dürfen nicht als Test
   verwendet werden, ohne eigene Aufteilung.
3. **Finetuning** ist ausdrücklich nicht Teil dieser Stufe; Trainingsdaten
   dürfen nicht aus den Testmengen stammen.
4. **Yun-Qualität**: 26,7 Prozent der geprüften Records hatten Befunde
   (`validation/yun_audit_30.md`). Die 450 aufgenommenen Records sind nicht
   kuratiert; die kuratierten 275 bleiben separat.

## Bezug zum bestehenden Benchmark

Der 54-Record-GLASS-Lauf bleibt unverändert gültig
(`evaluation/multi_model_cross_validation/`). Der erweiterte Benchmark ist eine
zweite, unabhängige Messung mit anderen Aufgaben und größerer Stichprobe; die
Ergebnisse werden getrennt berichtet und nicht zu einem Score verrechnet.
