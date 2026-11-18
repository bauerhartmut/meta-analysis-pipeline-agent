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
- `bind_row_arm(label)` / `Row.arm` — Arm aus dem Zeilenlabel, wenn die
  Tabelle die Arme als Zeilen fuehrt (`Control`, `White Grape Juice`). Schwelle
  0.6, weil Zeilenlabels kurz sind; ein dritter Arm (`Apple Juice`) bleibt ohne
  Arm. Zusammen mit `Column.is_outcome` (Outcome-Name im Spaltenkopf) entsteht
  das Feld: Arm aus der Zeile, Rolle aus dem Kopf.
- `header_geometry_trustworthy(table)` — ohne belegte Kopfspanne
  (`header_gruppe_nicht_teilbar` usw.) wird keine Spalte zum Outcome erklaert;
  das verhindert Felder auf der falschen Spalte (belegt: `PMC4319071:T2`).
- `row_roles(label)` / `Row.value_role` — Rolle aus dem Zeilenlabel
  (`Mean (SD)` → mean + sd, `Not complying, n (%)` → events). Sie greift nur,
  wenn der Spaltenkopf keine Rolle trägt; ein Spaltenfeld hat Vorrang, und ohne
  Zellwert entsteht kein Feld. Auf dem eingefrorenen Material derzeit ohne
  messbaren Gewinn: bei den betroffenen Tabellen liegen die Wertspalten nicht
  unter den Armköpfen bzw. sind die Arme Zeilen (`PMC4319071:T2`).

Zwei weitere Mechanismen laufen dokumentweit bzw. zellgenau:

- `transfer_arms_within_document(tables, context)` — trägt der Gruppenkopf
  `Verum` in einer Tabelle einen belegten Arm, gilt derselbe Kopf in der
  Schwestertabelle desselben Dokuments als belegt (`arm_basis="uebertrag"`).
  Ohne identisches Label wird nichts übertragen.
- `reachable_fields(table)` — Felder, die eine Tabelle hergibt: Spaltenfeld plus
  der zweite Wert einer Verbundzelle. Diese Menge ist die Obergrenze des
  Tabellenpfads, keine Modellleistung.
- `outcome_rows(table, outcome)` — Zeilen, deren Label-Pfad das Outcome nennt
  (Gruppenlabels plus eigenes Label, z. B. `Dietary intake` > `Vegetable
  intake (grams)` > `Mean (SD)`). Beidseitiger Token-Abgleich mit einfacher
  Pluralnormalisierung; ohne Treffer bleibt die Liste leer.
- `reachable_cells(table, context)` — erwartbare Zellen: Spaltenfeld **und**
  Outcome-Zeile. Nur diese Menge zählt als erwartbar; Felder in anderen Zeilen
  sind für den Record kein Wert.
- `group_size_declaration(text)` / `Table.header_facts` — feste Gruppengrößen
  aus dem Kopf (`n = 456`) werden als Kopf-Fakt mit Wert und (falls belegbar)
  Arm geführt, **nicht** als Spaltenrolle `n`. Sonst liest der Extraktor
  Zeilenwerte als Gruppengröße (belegt: `PMC4319071:T1`).
  `Reconstruction.add_header_facts(table)` macht daraus ohne Modellaufruf einen
  Beleg (Adresse `(-1, col_start)`, `origin="kopf_fakt"`, Rohwert = Kopftext);
  ein Fakt ohne belegten Arm erzeugt kein Feld.

Fette Zeilengruppen (`**Dietary intake**`) sind Zeilenlabels, keine Kopfzeilen:
 sie beenden die Tabelle nicht, sondern bilden den Label-Pfad. Kopfzeilen, die
in Wahrheit Zeilenlabels tragen (Vergleichszeilen wie `Basic vs control`),
werden nicht als Spaltenkopf gelesen und als `kopfzeile_ist_zeilenlabel`
notiert.

`PlanOptions.focus_outcome=True` beschränkt den Auftrag auf die Outcome-Zeile
(übrige Zeilen laufen als Kontext mit); Standard ist `False`, damit die
produktive Pipeline unverändert bleibt.

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
| Zuordnung | `armzuordnung_angenommen`, `armzuordnung_uebertragen`, `verbundwert_getrennt` |

`beleg_nicht_im_ausschnitt` ist hart: das `quote` einer Zelle muss wörtlich im
Prompt der Einheit stehen, sonst gilt der Beleg als nicht prüfbar.

### Verbundwerte (`12.4 (3.1)`)

Viele Tabellen drucken die Streuung in Klammern hinter dem Mittelwert. Trägt
mindestens 60 % der gefüllten Zellen einer Mittelwertspalte zwei Zahlen, setzt
`semantics` `column.secondary_role = "sd"`. Der erste Wert ist der Zellwert, der
zweite wird beim Rekonstruieren als **eigener Beleg mit derselben Fundstelle**
geführt (`evidence.derived = true`, `cell.derived = true`) und erscheint in
`prediction_cells()` als `*_standard_deviation`. Der Wert wird aus dem Zitat des
Modells gelesen, nicht geschätzt; ohne zweite Zahl entsteht kein Beleg.
Der Befund `verbundwert_getrennt` zählt diese Spalten.

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
| `arm_transfer` | `True` | Arm aus einer Schwestertabelle desselben Dokuments belegen (markiert) |
| `arm_order_fallback` | `False` | Arm aus der Leserichtung annehmen (markiert) |
| `model_name` | `""` | Kennung für die Provenienz |

Gelesen aus bool, String (`"true"`, `"E"`), Mapping, Umgebungsvariable
`TABLE_DECOMPOSITION` (+ `TABLE_DECOMPOSITION_STRATEGY`) oder der
Agentenkonfiguration.

## Tests

```
python -m pytest research_agent/tests/test_table_decomposition.py -q
```

32 Tests: Parser (Strichregel, Pipe, Whitespace, Spannen, Labelspalten mit
Ziffern), Rollen und Armbindung, Arm-Transfer, Verbundwerte, alle fünf
Verfahren, Budget-Chunking, Crops, Rekonstruktion (agreed/single/conflict),
adaptive Nachlese, Backend-Ausfall, Validierungsregeln, Konfiguration und den
Pipeline-Haken.
