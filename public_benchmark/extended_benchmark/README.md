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
| `numeric_extraction` (Yun) | zellgenaue Precision/Recall/F1, MAE, Armvertauschung, Record-Exaktheit | Eine Zelle trifft, wenn Feld, Arm und Wert übereinstimmen (absolute und relative Toleranz einstellbar). MAE über die absoluten Abweichungen getroffener Zellen. Armvertauschung zählt, wenn beide Arme eines Feldes vertauscht geliefert werden. |
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
