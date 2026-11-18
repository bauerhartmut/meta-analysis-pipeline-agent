# Table Decomposition & Reconstruction: Architekturbericht

Stand 18.11.2026. Beschreibt die bestehende Extraktionspipeline, die Stellen, an
denen die neue Engine andockt, und die Gründe für ihre Bauform. Zahlen aus
Messläufen stehen im Ergebnisteil
(`public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/`).

## 1. Auftrag

Die Extraktion mit GLM 5.3 auf Yun-699 erreicht Precision 86,75 %, Recall
66,35 % (1.840 richtig, 281 falsch, 652 fehlend bei 2.773 Goldzellen). Ein
vermuteter Fehlerherd sind komplexe Tabellen: mehrstufige Köpfe, Zellverbünde,
viele Arme und Messzeitpunkte, Fußnoten, durch PDF-Parsing zerstörte Struktur.

Die Engine zerlegt Tabellen in kontextbewahrende Einheiten, extrahiert sie
einzeln und setzt sie zu einer Tabelle zusammen. Sie ist modellunabhängig und
lässt die bestehende Pipeline unverändert funktionieren.

## 2. Ist-Zustand der Pipeline

| Baustein | Datei | Rolle |
|---|---|---|
| Tabellenerkennung im Text | `research_agent/research/table_extractor.py` | `find_table_blocks` / `find_effect_cells` erkennen Tabellenblöcke und Effektzeilen im Markdown-/Text-Layer; `pdf_page_blocks` liest Seitenlayouts, `blocks_with_verifiable_quotes` filtert Blöcke ohne belegbares Zitat, `augment_document_text` hängt die Blockansicht an den Extraktionstext |
| JATS | `research_agent/research/jats_tables.py` | `parse_jats_text`, `blocks_from_jats`, `stat_rich_candidates`; nutzt `colspan`/`rowspan` und Kopfzeilen aus XML |
| Vision | `research_agent/research/vision_table.py` | `render_pdf_pages`, `crop_bounds`, `png_bytes`, `normalise_number_text`; Seitenrendering und Bildausschnitte |
| LLM-Zugriff | `research_agent/llm/engine.py`, `research_agent/config.py` | Modellaufrufe, Konfiguration (geschützt) |
| Orchestrierung | `research_agent/orchestrator.py` | Zeile ~3583 `augment_document_text(text)` → `text_for_llm`; ~3673 Vision-Fallback; ~1170 JATS-Pfad |
| Auswertung | `public_benchmark/extended_benchmark/run_extended_extraction.py`, `evaluate_extended.py`, `yun_full/auswerte_yun699.py` | Extraktionsläufe, Zellvergleich gegen Gold, Yun-699-Kennzahlen |

Gemeinsam ist allen Pfaden: die Tabelle erreicht das Modell als **Text**
(Markdown, Layout-Text oder JATS-Pipe-Tabelle), teils zusätzlich als Bild. Eine
strukturierte Zwischenrepräsentation mit Header-Hierarchie, Spannen, Rollen und
Armzuordnung gibt es bisher nicht; die Zuordnung von Zelle zu Arm und Feld
leistet das Modell im Prompt.

## 3. Warum ein eigenes Paket

- `table_extractor.py` erkennt Blöcke und Effektzeilen, segmentiert aber nicht
  nach Spalten/Zeilen und führt keine Header-Hierarchie.
- `jats_tables.py` liefert Spannen, aber nur für JATS-XML.
- `vision_table.py` liefert Bilder und Boxen, keine Semantik.
- Die Kerndateien sind geschützt (`.gitignore`-Sektion „Kernbausteine“).

Deshalb liegt die Engine als eigenes Paket `research_agent/table_decomposition/`
vor. Sie liest dieselben Quellen (Markdown/Text, optional Seitenlayout), fasst
aber nichts Bestehendes an und wird von der Pipeline nur optional aufgerufen.

## 4. Datenfluss der Engine

```
Dokumenttext
   │  parser.parse_document            (Strichregel-, Pipe-, Whitespace-Tabellen)
   ▼
DocumentTables ── Table(rows, columns, header_bands, footnotes, spans)
   │  semantics.enrich_table           (Header-Pfade, Rollen, Arme, Zielfelder)
   ▼
angereicherte Table
   │  complexity.assess                (Score + Klasse + Treiber)
   │  strategies.plan                  (A–E → ExtractionUnits mit vollem Kontext)
   ▼
ExtractionUnit[] ── prompt, expected_cells, crop, depth
   │  backend.ExtractionBackend.extract (beliebiges Modell, JSON-Vertrag)
   ▼
UnitResult[] ── Zellen mit row/col/value/raw/quote
   │  reconstruct.Reconstruction        (Belege sammeln, deduplizieren, Konflikte)
   ▼
ReconstructionResult ── cells, conflicts, stats
   │  validation.validate               (Struktur + Inhalt, getrennt ausgewiesen)
   ▼
ValidationReport + TableRun/EngineResult (to_dict für Persistenz und Benchmark)
```

Verfahren E (adaptiv) läuft zusätzlich durch `strategies.refinement_units`: nur
unbelegte oder konfliktäre Adressen werden nachgelesen, gedeckelt durch
`max_depth` und `max_calls_per_table`.

## 5. Datenmodell

`model.py` hält die Repräsentation, die der Auftrag verlangt:

| Objekt | Inhalt |
|---|---|
| `Table` | `table_id`, `doc_id`, `index`, `caption`, `label`, `page`, `line_start/line_end`, `char_start/char_end`, `caption_char_span`, `rows`, `columns`, `header_bands`, `footnotes`, `irregularities`, `complexity`, `context` |
| `Column` | `col_id`, `header`, `header_path`, `role`, `arm`, `arm_basis`, `field`, `unit`, `col_span` |
| `Row` | `row_id`, `label`, `cells`, `line`, `irregular` |
| `Cell` | `row_id`, `col_id`, `text`, `value`, `line`, `col_span`, `mapping`, `inherited_from_row` |
| `HeaderBand` | `text`, `level`, `col_start`, `col_end`, `span`, `source` |
| `Footnote` | `marker`, `text`, `line`, `char_span` |

`crops.py` ergänzt die Fundstelle: Zeichen- und Zeilenspanne, normalisierte
Box (`text-layout/1000`), Seitennummer nur wenn belegt. Die Yun-Markdown-Dateien
tragen keine Seitenkoordinaten; dort bleibt `page` leer und `image.available`
steht auf `false` — es wird keine Koordinate erfunden.

## 6. Schnittstellen

Vollständig in `research_agent/table_decomposition/README.md`. Die drei
Einstiegspunkte:

```python
from research_agent.table_decomposition.engine import (
    TableDecompositionEngine, TableDecompositionConfig, augment_prompt_text,
)
from research_agent.table_decomposition.parser import parse_document
```

- `TableDecompositionConfig` — `enabled`, `strategy`, Budgets, `include_footnotes`,
  `include_verbatim`, `arm_order_fallback`, `model_name`; ladbar aus bool, String,
  Mapping, `TABLE_DECOMPOSITION` oder der Agentenkonfiguration.
- `TableDecompositionEngine(backend, config)` — `plan(table)`,
  `run_table(table, text)`, `run_document(text, doc_id, context=…, table_ids=…)`.
- `augment_prompt_text(text, doc_id, context, config)` — Pipeline-Haken: hängt
  strukturierte Tabellenansichten an den Extraktionstext an, ohne den
  Originaltext zu verändern (die Zitatprüfung bleibt damit intakt).

## 7. Integrationspunkte

1. **Konfigurationsschalter** `table_decomposition: true` (auch `"A"`…`"E"` oder
   Mapping). Gelesen von `TableDecompositionConfig.from_agent_config()`; fällt
   auf die Umgebungsvariable `TABLE_DECOMPOSITION` zurück. Ohne Schalter bleibt
   jede bestehende Funktion unverändert.
2. **Prompt-Anreicherung** über `augment_prompt_text` an der Stelle, an der
   `orchestrator.py` heute `augment_document_text` aufruft. Rückgabe enthält
   `enabled`, `tables`, `appended_chars` und die Tabellenliste für Telemetrie.
3. **Eigenständiger Lauf** über `TableDecompositionEngine.run_document` mit
   eigenem Backend — so laufen Benchmark und spätere Produktion ohne Änderung
   am Orchestrator.

Keine geschützte Datei wurde verändert. Der Haken ist vorbereitet, aber noch
nicht in `orchestrator.py` verdrahtet (bewusst: erst nach Modellvergleich).

## 8. Bewusste Entscheidungen

- **Markdown/Text zuerst, Bild als Zusatz.** Die Yun-Quellen sind Markdown mit
  Strichregel; Bild-Crops ohne Struktur würden genau den Kontext verlieren, den
  der Auftrag verlangt. `TableCrop.image` trägt die Seitenreferenz für spätere
  PDF-Pfade.
- **Header-Spannen über die Wiederholungsperiode der Blattköpfe**, nicht
  geometrisch: Gruppenköpfe sind in den Yun-Tabellen teils um eine Spalte
  versetzt. Passt die Periode nicht auf die Spaltenzahl, wird die Spanne
  gleichmäßig geteilt und als Irregularität markiert — nie geraten.
- **Armzuordnung deterministisch** über Header-Treffer, normalisierten
  Namensvergleich und Token-Überlappung mit Mindestvorsprung. Ohne Beleg bleibt
  `arm = None` und die Spalte bekommt kein Feld; sie geht dann nicht in die
  Bewertung ein, statt einen Wert falsch zuzuordnen.
- **Optionale Reihenfolge-Annahme** (`arm_order_fallback`): bei genau zwei
  Armspalten und nur einem benannten Arm wird der andere aus der Leserichtung
  gesetzt — sichtbar als `arm_basis="reihenfolge"` und als Validierungsbefund
  `armzuordnung_angenommen`. Standard ist aus.
- **Konflikte werden nicht überschrieben.** Widersprüchliche Werte bleiben als
  Kandidatenliste stehen (`status="conflict"`) und sind aus
  `prediction_cells()` ausgeschlossen.
- **Strukturelle Vollständigkeit getrennt von inhaltlicher Richtigkeit.**
  `ValidationReport.structural` beantwortet „wurde jede Zelle, jeder Kopf, jede
  Fußnote mitgeführt?“; Inhaltsregeln prüfen Werte gegen die Quellzelle und
  Plausibilität. Ein Konsens zweier Leserichtungen ist ein Hinweis, kein Beweis.

## 9. Grenzen

- Der Parser versteht die real vorliegenden Markdown-Tabellen des Korpus; für
  PDF-Layouts ohne Strichregel bleibt der Whitespace-Fallback, dessen
  Spaltengrenzen bei mehrzeiligen Zellen unsicher sind.
- Die Armzuordnung ist der Engpass: nur ein Teil der Tabellen trägt den
  Studienarm im Kopf, sodass je Record im Schnitt 1,3 der 4,6 Goldzellen über
  eine ausgewählte Tabelle erreichbar sind (Messung siehe Ergebnisteil).
- Ohne Modelllauf gibt es keine Precision/Recall-Aussage; der Strukturvergleich
  belegt Kontexterhalt und Aufwand, nicht Extraktionsqualität.

## 10. Prüfstand

```
python -m pytest research_agent/tests/test_table_decomposition.py -q
python -m pytest public_benchmark/tests/test_table_decomposition_benchmark.py -q
```

34 Tests: Parser (Strichregel, Pipe, Whitespace, Spannen, Labelspalten mit
Ziffern), Rollen und Armbindung, Verfahren A–E, Budget-Chunking, Crops,
Rekonstruktion (agreed/single/conflict), adaptive Nachlese, Backend-Ausfall,
Validierungsregeln, Konfiguration, Pipeline-Haken sowie Zellabgleich und
Berichtsformat des Benchmarks.
