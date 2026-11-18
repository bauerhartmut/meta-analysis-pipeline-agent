# Benchmark: Table Decomposition auf Yun-699

Vier Werkzeuge, ein eingefrorener Testdatensatz, ein Ergebnisordner:

| Datei | Aufgabe |
|---|---|
| `select_tables.py` | Auswahl der Tabellen (nur Strukturkriterien, goldwertfrei), friert sie ein |
| `run_benchmark.py` | Offline-Strukturlauf oder Modelllauf (A–E) |
| `evaluate.py` | Zellabgleich gegen Gold, Precision/Recall/F1, Kosten |
| `report.py` | Markdown-Bericht aus `structure.json` und `evaluation.json` |

Ergebnisordner:
`../analysis/table_decomposition_20261118/` (Auswahl, Läufe, Berichte).

## Datengrundlage

`../yun_full/records/yun699.jsonl` — 699 Records, 2.773 Goldzellen aus 120
Dokumenten (111 mit `table-wrap`, 92 mit Strichregel). Goldzellen tragen Feld,
Arm und Wert; Outcome und Zeitpunkt stehen nur im Record-Kontext, deshalb sind
diese beiden Kennzahlen im Benchmark **nicht messbar** und werden im Bericht
ausdrücklich als nicht gemessen geführt.

Dokumenttexte:
`public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/no_attributes_markdown_files/<PMCID>.md`

## Auswahl (eingefroren, goldwertfrei)

- Kandidat ist ein Paar **(Record, Tabelle)** im jeweiligen Split
  (`record.document.split`), nicht eine Tabelle allein: derselbe Tabellentext
  kann für mehrere Records gelten, und die Armzuordnung hängt am Record-Kontext.
- Kandidat wird nur, wessen Tabelle nach `enrich_table` mindestens eine Spalte
  mit Zielfeld trägt (`--include-unbound` hebt das auf).
- Sortiert wird nach `n_target_columns` (mehr belegte Zielspalten zuerst),
  dann nach Tabellen-ID-Hash — kein Goldwert, kein Modellurteil.
- Geschichtet nach Komplexität und Merkmalen (mehrarm, mehrzeitpunkt,
  mehrstufiger_kopf, fussnoten, komplexe_pdf), round-robin, mit
  `--max-per-document` (Standard 2) und `--max-per-record` (Standard 3) gegen
  Klumpenbildung.
- Der Split-Hash der Records steht als `records_sha256` in der Auswahl;
  `frozen` dokumentiert den Stand.

```
python public_benchmark/extended_benchmark/table_decomposition/select_tables.py \
    --role test --target 60 --write
python public_benchmark/extended_benchmark/table_decomposition/select_tables.py \
    --role dev --target 40 --write
```

Entwicklungs- (`dev`) und Testsplit (`test`) sind getrennt; jede Optimierung
gehört auf `dev`.

## Offline-Lauf (ohne Netz, ohne Kosten)

```
python public_benchmark/extended_benchmark/table_decomposition/run_benchmark.py \
    --offline --run-id offline_struktur_20261118
```

Misst je Record und Verfahren: Einheiten, Prompt-Zeichen, geschätzte Tokens
(Zeichen / 4, als Schätzung markiert), erwartete Zellen, Zellen im Ausschnitt,
Goldzellen erreichbar und den Validierungsstatus. Kein Modellaufruf, keine
Precision/Recall.

„Goldzelle erreichbar“ heißt seit dem 18.11.2026: das Feld trägt eine Spalte
**und** die Zelle steht in der Outcome-Zeile des Records (`focus_rows`). Eine
Spalte mit dem Feld in irgendeiner Zeile zählt nicht mehr. Gruppengrößen aus
dem Kopf (`n = 434`) sind Kopf-Fakten und zählen nicht als gelesener Zellwert.
Der Auftrag ist entsprechend auf die Outcome-Zeile begrenzt; `--all-rows`
misst zum Vergleich weiter die ganze Tabelle.

## Modelllauf (kostenpflichtig, nur mit Freigabe)

```
python public_benchmark/extended_benchmark/table_decomposition/run_benchmark.py \
    --model gwdg/glm-5.3 --strategies A B E --max-tokens 24000 \
    --allow-network --confirm-kosten --run-id modell_glm53_abe_20261118
```

Ohne **beide** Flags bricht das Werkzeug ab. Der Lauf schreibt
`predictions.jsonl` **zeilenweise** (jede fertige Record-Zeile sofort, damit ein
Abbruch keine bezahlten Ergebnisse verliert) und `run.json` mit Modell,
Strategien und `max_tokens` — nichts wird überschrieben, jede `run-id` ist ein
eigener Ordner.

`--max-tokens` (Standard 24000) gilt für alle Verfahren gleich. Bei 8000 endet
GLM-5.3 auf großen Tabellen mit `finish_reason=length` und leerem Inhalt, also
ohne verwertbare Antwort — gemessen im Smoke-Lauf vom 18.11.2026.

## Auswertung

```
python public_benchmark/extended_benchmark/table_decomposition/evaluate.py \
    --run-dir <run>
# schreibt <run>/evaluation.json

python public_benchmark/extended_benchmark/table_decomposition/report.py \
    --structure <offline-run>/structure.json --evaluation <run>/evaluation.json \
    --selection ../analysis/table_decomposition_20261118/selection_test.json \
    --out <run>/bericht.md
```

`evaluate.py` zählt je Record: `richtig` (Wert innerhalb der Zelltoleranz und
gleiches Feld), `falsch`, `fehlend`, `ohne_gold`; daraus Precision, Recall, F1,
Exact Match (Record vollständig richtig), Arm-Tausch, technische Ausfälle,
Tokens, Laufzeit, Kosten und Kosten pro 100 richtige Zellen. Zusätzlich
Aufschlüsselung nach Komplexität, Fehlerklassen, Validierungsbefunde und
Kontextabdeckung (Anteil Zellen mit Zitat, Zeilenlabel, Seite).

Preise sind Parameter (`--preis-in-pro-1k`, `--preis-out-pro-1k`), damit
derselbe Lauf mit anderen Annahmen nachgerechnet werden kann, ohne neu zu
extrahieren. Ohne Preise bleibt `kosten` leer — es wird keine Zahl erfunden.

## Regeln

- Goldannotationen werden nie verändert; `evaluate.py` liest sie nur.
- Keine Optimierung auf `test`; Auswahl und Schwellen werden auf `dev`
  eingestellt.
- Der Modelllauf braucht ausdrückliche Freigabe (Kosten, Rate-Limits) und
  vorher die Telemetrie des letzten Laufs.
- Ergebnisse ohne Modelllauf sind Strukturaussagen, keine Qualitätsaussagen.
