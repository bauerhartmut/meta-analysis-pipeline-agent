# Table Decomposition & Reconstruction Engine

Modellunabhängige Engine, die wissenschaftliche Tabellen in kontextbewahrende
Einheiten zerlegt, jede Einheit separat extrahieren lässt und die Teilresultate
zu einer konsistenten Tabelle zusammensetzt. Jede Zelle bleibt auf ihre
Originalstelle zurückführbar.

Architektur und Integrationspunkte: [`docs/table_decomposition_architektur.md`](../../docs/table_decomposition_architektur.md).
Benchmark: [`public_benchmark/extended_benchmark/table_decomposition/README.md`](../../public_benchmark/extended_benchmark/table_decomposition/README.md).

## Schnellstart

```python
from research_agent.table_decomposition.engine import (
    TableDecompositionConfig, TableDecompositionEngine,
)
from research_agent.table_decomposition.backend import ScriptedBackend

config = TableDecompositionConfig(enabled=True, strategy="E", model_name="mein-modell")
engine = TableDecompositionEngine(backend=ScriptedBackend(...), config=config)

text = open("dokument.md", encoding="utf-8").read()
result = engine.run_document(
    text, "PMC1234567",
    context={"intervention": "Verum", "comparator": "Placebo",
             "outcome": "HbA1c", "timepoint_target": "12 weeks"},
    table_ids=["PMC1234567:T2"],      # optional: nur diese Tabellen
)

result.prediction_cells()   # Zellen mit Feld, Arm, Wert, Zitat, Seite
result.conflicts()          # Widersprüche, unverändert als Kandidaten
result.validation_summary() # Struktur- und Inhaltsbefunde
result.to_dict()            # vollständige Provenienz für Persistenz
```

Ohne Backend plant und prüft die Engine nur (`dry_run`): `engine.plan(table)`
liefert die Einheiten samt Prompts, `validate` die Strukturbefunde. Das genügt
für Strukturanalysen und Kostenvergleiche ohne Netzzugriff.

## Öffentliche Schnittstellen

### `parser.parse_document(text, doc_id) -> DocumentTables`

Erkennt Tabellen in drei Formen: Pandoc-`::::table-wrap`-Blöcke mit
Strichregel (Yun-Korpus), Pipe-Tabellen, Whitespace-Spalten. Liefert
`DocumentTables.tables`, `unresolved_blocks` und je Tabelle `Table` mit Zeilen,
Spalten, Header-Bändern, Fußnoten und Irregularitäten.

Zellwerte liest `parser.parse_value(text)` (deutsche und englische
Dezimaltrennzeichen, `±`, `%`, Klammerwerte, `<`/`>`).

### `semantics.enrich_table(table, context, assume_order=False) -> Table`

Schreibt Header-Pfade, Rollen (`label`, `n`, `mean`, `sd`, `events`, `p`,
`unknown`), Arm, `arm_basis` und Zielfeld (`intervention_mean`,
`comparator_sd`, …) in die Spalten. Idempotent.

- `role_for_header(path)` — Rolle aus dem Header-Pfad.
- `bind_arm(path, intervention, comparator) -> ArmBinding` — Arm aus
  Header-Treffer, normalisiertem Namensvergleich, Token-Überlappung; ohne Beleg
  `arm=None`, `basis` sagt warum (`kein_treffer`, `ambiguous`).
- `assume_order` — Reihenfolge-Annahme bei genau zwei Armspalten, markiert als
  `arm_basis="reihenfolge"` (Standard aus; im Benchmark separat gemessen).

### `complexity.assess(table) -> ComplexityScore`

Score, Klasse (`einfach`, `mittel`, `komplex`, `sehr_komplex`) und benannte
Treiber aus Header-Ebenen, Gruppenköpfen, Spalten, Zeilen, Fußnoten,
irregulären Zeilen, Zeitpunktspalten und nicht zuordenbaren Spalten. Rein
strukturell, ohne Modell.

### `strategies.plan(table, strategy, options, document_text) -> DecompositionPlan`

| Var | Verfahren | Einheiten | Kontext jeder Einheit |
|---|---|---|---|
| A | Full-Table Extraction | 1 (ggf. Budget-Chunks) | ganze Tabelle, Köpfe, Fußnoten, optional Originaltext |
| B | Vertical Decomposition | je Spalte | vollständiger Header-Pfad, Arm, Einheit, alle Zeilenlabels, Fußnoten |
| C | Horizontal Decomposition | je Zeile | Zeilenlabel, alle Spaltenköpfe mit Pfad, Fußnoten |
| D | Bidirectional Decomposition | B + C | beide Richtungen; Überlappungen sind als Crops verzeichnet |
| E | Adaptive Recursive Decomposition | nach Komplexität | einfache Tabelle ganz, komplexe zerlegt, Nachlese nur für unbelegte/konfliktäre Zellen |

`ExtractionUnit` trägt `unit_id`, `table_id`, `doc_id`, `row_ids`, `col_ids`,
`context_row_ids`, `context_col_ids`, `expected_cells`, `prompt`, `crop`,
`depth`, `parent_unit_id`, `notes`. `PlanOptions` begrenzt
`max_units_per_table`, `min_columns_for_split`, `max_refinement_units`,
`include_footnotes`, `include_verbatim`.

Der Prompt jeder Einheit enthält: Studienkontext (Intervention, Komparator,
Outcome, Zielzeitpunkt), Tabellenkopf mit Legende, Gruppenkopf-Zeilen, die
Zeilen- und Spaltenköpfe **im vollen Pfad**, die Werte des Ausschnitts, die
relevanten Fußnoten, optional den Originaltext-Ausschnitt und die Arbeitsanweisung
mit JSON-Schema.

### `backend.ExtractionBackend` (Protocol)

```python
class ExtractionBackend(Protocol):
    def extract(self, prompt: str, unit: ExtractionUnit) -> UnitResult: ...
```

`UnitResult` trägt `unit_id`, `cells: list[PredictedCell]`, `raw_text`, `model`,
`prompt_tokens`, `completion_tokens`, `runtime_s`, `error`.
`PredictedCell` hat `row_id`, `col_id`, `value`, `raw`, `quote`.

Antwortvertrag (JSON, in Codeblöcken erlaubt):

```json
{"cells": [{"row": 3, "column": 2, "value": 12.4, "raw": "12.4 (3.1)",
            "quote": "12.4 (3.1)"}]}
```

`parse_cells(text)` liest diese Antwort und meldet `leere_antwort`, `kein_json`,
`kein_zellenfeld`, `zellen_keine_liste`, `zellen_unlesbar`. Mitgeliefert:
`ScriptedBackend` (Tests, feste Antworten) und `CallableBackend` (eigene
Funktion, z. B. Gateway-Aufruf).

### `reconstruct.Reconstruction`

Sammelt Belege je Adresse (Zeile, Spalte) und entscheidet:

| Status | Bedeutung |
|---|---|
| `agreed` | mindestens zwei Einheiten, gleicher Wert |
| `single` | genau eine Einheit |
| `conflict` | abweichende Werte; Kandidatenliste, kein Wert, aus `prediction_cells()` ausgeschlossen |

Belege tragen `table_id`, `doc_id`, `page`, `unit_id`, `strategy`, `direction`,
`model`, `crop_id`, `depth`, `row_label`, `header_path`, `quote`,
`source_value`, `source_present`.

### `validation.validate(table, units, reconstruction) -> ValidationReport`

Status `strukturell_vollstaendig` oder `strukturell_luecken`, Befunde mit
Schweregrad `error`/`warning`/`info` und Code:

| Gruppe | Codes |
|---|---|
| Abdeckung | `zelle_nicht_abgedeckt`, `zelle_nicht_abgedeckt_sammel`, `zelle_ausserhalb_scope`, `einheit_id_doppelt` |
| Kopf und Kontext | `caption_fehlt`, `fussnote_fehlt`, `spalte_unbekannt`, `header_kontext_fehlt`, `spaltenkopf_fehlt`, `zeilenlabel_fehlt`, `header_span_ueberlappt`, `mehrere_zeitpunkte_im_kopf`, `spalte_ohne_feld` |
| Crops | `crop_fehlt`, `crop_spanne_unbelegt`, `crop_ohne_caption` |
| Inhalt | `ohne_rohwert`, `beleg_nicht_im_ausschnitt`, `abweichend_von_quellzelle`, `ereignisse_ueber_gruppengroesse`, `sd_gegen_mittel`, `einheit_inkonsistent`, `konflikt` |
| Zuordnung | `armzuordnung_angenommen` |

`beleg_nicht_im_ausschnitt` ist hart: das `quote` einer Zelle muss wörtlich im
Prompt der Einheit stehen, sonst gilt der Beleg als nicht prüfbar.

### `engine.augment_prompt_text(text, doc_id, context, config, max_tables=4)`

Pipeline-Haken für `table_decomposition: true`: hängt strukturierte
Tabellenansichten (Header-Hierarchie, Zeilenlabels, Werte, Fußnoten) als
Appendix an den Extraktionstext. Der Originaltext bleibt unverändert, damit die
Zitatprüfung weiter greift. Rückgabe: `(text, {"enabled", "tables",
"appended_chars", …})`.

## Konfiguration

| Feld | Standard | Wirkung |
|---|---|---|
| `enabled` | `False` | Schalter der Pipeline |
| `strategy` | `"A"` | Verfahren A–E |
| `max_units_per_table` | 24 | Obergrenze der Einheiten je Tabelle |
| `max_calls_per_table` | 32 | Obergrenze der Aufrufe inklusive Nachlese |
| `max_depth` | 2 | Rekursionstiefe der adaptiven Nachlese |
| `max_refinement_units` | 8 | Nachlese-Einheiten je Runde |
| `min_columns_for_split` | 3 | darunter wird nicht spaltenweise zerlegt |
| `include_footnotes` | `True` | Fußnoten im Prompt |
| `include_verbatim` | `True` | Originaltext-Ausschnitt im Prompt |
| `arm_order_fallback` | `False` | Arm aus der Leserichtung annehmen (markiert) |
| `model_name` | `""` | Kennung für die Provenienz |

Gelesen aus bool, String (`"true"`, `"E"`), Mapping, Umgebungsvariable
`TABLE_DECOMPOSITION` (+ `TABLE_DECOMPOSITION_STRATEGY`) oder der
Agentenkonfiguration.

## Tests

```
python -m pytest research_agent/tests/test_table_decomposition.py -q
```

Deckt Parser (Strichregel, Pipe, Whitespace, Spannen, Labelspalten mit Ziffern),
Rollen und Armbindung, alle fünf Verfahren, Budget-Chunking, Crops,
Rekonstruktion, adaptive Nachlese, Backend-Ausfall, Validierungsregeln,
Konfiguration und den Pipeline-Haken ab.
