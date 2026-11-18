# Aufloesbarkeit der Ausfaelle

Quelle: `D:/daswu/AIResearch/public_benchmark/extended_benchmark/runs/_lesekopie_20261118/predictions.jsonl` / glm. Records-Verzeichnis: ebm_nlp.jsonl, evidence_inference.jsonl, yun.jsonl, yun_dev.jsonl, yun_kandidaten.jsonl, yun_test186.jsonl, yun_test76_ohne_ziel.jsonl, yun_test76_ziel.jsonl.

| Gruppe | Zeilen | in `records/` | nur Ersatzquelle | nicht gefunden | ohne Dokument | ohne Gold | Goldzellen |
|---|---|---|---|---|---|---|---|
| Ausfall | 104 | 81 | 23 | 0 | 0 | 1 | 427 |
| Erfolg | 595 | 369 | 226 | 0 | 0 | 30 | 2346 |

## Ersatzquellen

- `D:/daswu/AIResearch/public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl`: vorhanden=True, versioniert=True
- `D:/daswu/AIResearch/handoff_20261116/daten/yun699.jsonl`: vorhanden=True, versioniert=False
- `D:/daswu/AIResearch/benchmark_analysis_handoff_20261116/goldstandard/yun699.jsonl`: vorhanden=True, versioniert=False

Nur über die Ersatzquelle erreichbar: yun2024:128, yun2024:130, yun2024:133, yun2024:152, yun2024:212, yun2024:213, yun2024:214, yun2024:215, yun2024:251, yun2024:30

Ohne Goldzellen (nicht bewertbar): yun2024:653
