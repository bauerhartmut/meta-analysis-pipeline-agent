# Yun-699-Benchmark (externer Datensatz, separates Benchmark)

Eigener Benchmark auf dem öffentlichen Datensatz von Yun et al. (2024), getrennt
vom 76-Record-Benchmark. Kein gemeinsames Gold, keine gemeinsamen Kennzahlen.

* Datensatz: `public_benchmark/raw_data/yun_llm_meta_analysis/` (Git-Clone,
  Commit `1bc768d`, Apache-2.0), 120 Artikel, 699 ICO-Records
  (43 dev / 656 test), 2.773 Goldzellen.
* Record-Datei: `records/yun699.jsonl` — erzeugt von `baue_yun699.py` aus
  `annotated_rct_dataset.json` (Quellhash wird geprüft).
* Manifest: `manifest.json` (Hashes, Zählungen, Schema-Mapping, Anomalien).
* Auswertung: `auswerte_yun699.py` (Zellvergleich gegen Gold, exakt).

## Bauen (verändert nichts am Original)

```bash
python public_benchmark/extended_benchmark/yun_full/baue_yun699.py --write
```

Das Skript bricht ab, wenn der SHA-256 der Quelle abweicht oder nicht 699 Records
gelesen werden.

## Trockenlauf

```bash
python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm --split test \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
  --ids yun2024:6,yun2024:7,yun2024:12,yun2024:10,yun2024:11 \
  --cell-timepoint --target-fallback --repair --max-tokens 19000 --workers 3 \
  --run-id yun699_trockenlauf_20261116 --quelle yun699_trocken
```

## Auswerten

```bash
python public_benchmark/extended_benchmark/yun_full/auswerte_yun699.py \
  --run <run-id> --split test \
  --out public_benchmark/extended_benchmark/runs/<run-id>/auswertung_yun.json
```

`--split test` zählt nur Testrecords; ohne die Angabe wird alles gezählt, was im
Lauf steckt.

## Was der Agent sieht

Nur `document`, `context` und `timepoint.target`. Die Goldzellen stehen
ausschließlich in der Record-Datei, aus der die Auswertung liest, und werden nie
in den Prompt geschrieben (`tests/test_yun699.py` prüft den Prompt-Kopf gegen die
Goldwerte der Pilotrecords).

Yun hat kein Zeitpunktfeld. `timepoint.target` trägt deshalb die Papierregel
(„primary time point of the trial, if not stated: the last reported time point")
als Text; bewertet wird der Zeitpunkt nicht. Siehe `yun_benchmark_report.md`.
