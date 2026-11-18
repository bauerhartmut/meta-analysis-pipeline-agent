# IMPLEMENTATION_LOG — Umsetzung des Implementierungsauftrags (01.11.2026)

## Sprint 1 (nach §16 des Auftrags): Audit → Baseline → Tabellen-MVP

### 1. Audit / Bestandsaufnahme (Erfüllung §16.1–16.2)

- **Aktive Prozesse identifiziert:** Lauf `Mediterrane Ernährung…` (PID 44248) läuft; seine DB
  `data/research-mediterrane-ernaehrung-und-kardiovaskula-475855.db` wurde **nie geschrieben**;
  alle Messungen hier laufen read-only (`mode=ro`) auf **anderen** DBs.
- **Freie abgeschlossene Baseline-DB:** `research-exercise-and-depressive-symptoms-in-adul-bbb324.db`
  — deren Prozess (PID 25268) ist beendet (tasklist leer); zwei Closing-Reports liegen vor (12:41, 18:10).
- **Abweichungen zur Statusdokumentation:** Kein Git-Repository im Projekt (dieser Sprint legt eins an).
  Die Übergaben „TUDaGPT-Ladder“, Duplikat-DOI-Dedup, Leave-one-out, Subgruppen, Egger sind live im Code
  vorhanden; `llm_usage` wird global in `data/research-usage.db` geschrieben, die Topic-DBs tragen nur
  das leere Schema.

### 2. Phase 0 — Baseline-Kennzahlen (Auftrag §3)

**Umgesetzt:** `research_agent/metrics.py` — jede Kennzahl ist eine SQL-Abfrage gegen die
abgeschlossene DB, CLI `python -m research_agent.metrics <db>`; Artefakte in `data/baseline/`.
LLM-Zahlen kommen aus der(globalen) usage-DB (`--usage-db`), Suchzahlen aus `query_stats` — nichts wird
aus Logtexten geschätzt.

**Baseline (Exercise-Lauf, abgeschlossen, 18:10, via global-usage-db):**

```
Quellen: 440 gesamt / 440 unique / Relevanz ⌀ 0,398 (n=333, ≥0.25: 218)
Volltexte: 293 Dokumente, 293 Quellen mit Text, 8.903.205 Zeichen, 1463 Seiten
Screening: 145 include / 104 exclude
Effektzeilen: 129 gesamt / 93 im Zielmaß / 50 verworfen / 6 strittig / 105 mit geprüfter Quote
  Verwerfungsgründe: 'kein Effektwert gelesen': 37, "unbekannter Effekttyp '(leer)'": 13 (!)
Pools: 1 gepoolt (k = [19])
LLM: 17 628 Calls / 15 failed / 25.269.429 tokens
Suche: arxiv/crossref/europepmc/openalex/pubmed/semantic_scholar je 310 attempts
Lauf: 73 Zyklen, 262 028 s
```

- Wichtig: die 13 Zeilen mit „unbekannter Effekttyp ‚(leer)'" zeigen, dass der heute ausgetauschte
  Effekttyp-Bug in der Baseline-DB real aufgetreten ist — der Fix (meta/extraction) ist derselbe Code-Baum
  und wird erst zu einem zukünftigen Lauf quantifizierbar.
- Definitionstabelle und SQL schön in `data/baseline/exercise-bbb324-metrics.json/md`.

### 3. Phase 1 — Tabellen-Detektion und -Extraktion (Auftrag §4, MVP)

**Umgesetzt (deterministisch, keine neue Abhängigkeit):** `research_agent/research/table_extractor.py`
- Caption-Erkennung (Table N. / TABLE N: / Supplementary Table), Blockscan mit Zifferndichte/Umfeld —
  Prosa-Referenzen („Table 1. No sensitivity analyses …") werden **nicht** zu Blöcken.
- Effektzellen-Reader für real vorkommende Formate: `HR 0.72 (95% CI 0.55–0.94)`,
  `OR 0.92 (95% CI 0.85-0.99)`, `[β = -0.05, 95% CI = -0.06 – (-0.04)]` (inkl. EN-Dash,
  Negativwerten in Klammern, Komma- vs. Ganzzahl), `beta 0.14 (SE 0.03)`.
- Falsch-Positive entfernt: kleingeschriebenes „or" („… zero or 1+ …"), „or 4.8 to 7.1 METS".
- **Verbatim-Invariante:** Jeder Block-Body ist ein literaler Substring des Dokuments; quadrant
  der Extraktor grifft Tabellenzuweisungen, die Quote-Verifikation bleibt syntaktisch intakt
  (meta/extraction._store verifiziertVs the stored DB text).
- Datenbank: Tabell `extracted_tables` (migrationssicher, CREATE IF NOT EXISTS) + `Database.save_extracted_tables` /
  `get_extracted_tables`; method/token/name/cell belegbar.
- **Integration** in `orchestrator._work_item_effect_extraction`: Tabellenblöcke werden (max. 6, verbatim)
  an den Extraktions-Text angehängt und als Artefakt mit Span-Positiven gesichert.
- **Golden-Testset:** `data/golden_tables/case_001…003.json` (3 echte Layouts, manuell annotiert),
  `research_agent/tests/test_golden_tables.py` und `tests/test_table_extractor.py`.

**ADR (bewusst, dokumentiert):** Rendering-truerecovery mit Bounding Boxes (pdfplumber/PyMuPDF) und
Vision-Fallback sind **nicht** implementiert: nur `pypdf` ist installiert, und der Auftrag verbietet
blindlibrary-Installationen. Die Datentypen (`TableBlock`, `EffectCell.to_dict()`) sind bereits so geformt,
dass ein Seiten/Bounding-Box-Parser ohne Aufrufer-Anpassung einschieben kann.

### 4. Tests und Verifikation

- `pytest tests/test_table_extractor.py tests/test_golden_tables.py` → **10/10 grün**
  (Formatfälle, negative Fälle, Prosa-Caption ausgeschlossen, verbatim invariant).
- `pytest tests/test_work_queue.py tests/test_meta_extraction.py` → **73/73 grün**
- `pytest tests/test_e2e.py` (kompletter Orchestrator mit Fake-Backend) → **2/2 grün, 81 s**.
- `py_compile` für metrics, table_extractor, database, orchestrator: grün.
- DB-Roundtrip für `extracted_tables` an `:memory:` geprüft.
- Live-Materialprobe: 4 Volltexte aus `data/fulltext` → 4 Tabellenblock-Erkennungen / 75 Effektzellen.

### 5. Offene Punkte (nächste Sprints, Priorität wie im Auftrag)

1. **Golden-Set erweitern auf ≥30 Layouts/≥100 annotierte Zellen** (Auftrag §4.2 Abnahme). Auf
   `grep -l -E "^ *[Tt]able [0-9]+[.:]" data/fulltext/*.txt` sind **149 Volltexte** mit Captions; das
   Startset ist 3. Extensible annotation script fehlt.
2. Tabelle→Effektzeilen-Beleg: der MVP macht Tabellenwerten **lesbar**, nicht automatisch gepoolt.
   Zeilenniveau-Attribution (Zelle → (outcome, group, time) Fälle aus §4.2) muss vom EffectExtractor
   gelesen werden, um „wieder Mitglied" zu sein, und die Dokumentation im Pooling.
3. Volltext-Recovery-Status pro Studie (`fulltext_available`/`abstract_only`/…), Auftrag §4.1 —
   der metrics-Prozess benutzt jetzt die „chars>0"-Proxy; der echte Status-Typ muss in `source_texts`
   wandern.
4. Vision-Fallback §4.3 — als {@_equals} markiert; kein Wert ohne Unterlage.
5. `pypdf`-Adapter für PDF-Original-Seiten (persistente PDFs liegen nicht lokal; die .txt-Abzüge sind
   das bestehende Material).

### 6. Risiken

- Header/Held und Multilines-Layouts (Acta PDFs, Tabellen mit Spaltengruppen) werfen keine sauberen
  Blöcke; die Daten esfuerzo producieren Zahlen ohne Zeilenzuordnung — daher ist die **zentrale** Abnahme nob-
  counted mehr effektzeilen **nicht** erzwingen: Kandidaten nur Ausgrundsmitteln, keine Pool-Erweiterung.
- Der laufende Mediterranean-Lauf (PID 44248) nutzt den Stand von 21:44 — dieser Sprint fließt
  nicht in Tuning- oder laudende Läufe ein.

## Commits

- `a1 baseline`: Projektlage/X ohne Sprint-Änderungen + Status-HANDOFF.
- `p0 metrics`: metrics.py + Tests + Baseline-Artefakte.
- `p1 tables`: table_extractor.py + goldens + Integration + schema migration.

## Sprint 2 (02.11.2026): Phasenlücken-Audit + Phase-1-Vollendungsteile + Phase 9 + Phase 2

### Bestand-audit: bereits gebaut (keine Duplikate mehr!)
- coverage/manager.py (= Auftrag §2 ä canonical workflow
  states": studies-Registry, studies_status_log, legal-first acquisition,
  Author-Requests mit user-only approval) — integriert in orchestrator
  (_note_coverage), Tests test_coverage.py (165 Zeilen).
- evals/ (Paket D/H): deterministisches claim-recall/number-accuracy eval
  gegen golden_answers.json. Phase-9-Anteil, aber NICHT der §12-Review-
  Benchmark → neu gebaut (unten).
- meta/extraction.compare_extraction_passes: doble pass on fields (§4.4)
  existed with effect/se/ci_level/n.

### Phase 1 (§4.4/§4.2/§5.2 rest) — Umsetzung
- compare_extraction_passes erweitert: unit, design, direction, population
  (case-insensitiv), ci_bounds (ohne „SE ok aber KI falsch"-Loch). Tests.
- coverage/manager._xml_to_text: Tables werden nicht mehr still weggeworfen
  ([table omitted]); stattdessen caption + verbatim pipe-rows (§4.2), so
  textbasierte Tabellenhinweise überhaupt möglich. Regressionstest + neuer
  Keep-rows-Test.
- table_extractor: ICCaption-Trennzeichen ggelockert (Space allowed), Z-
  Offsets der Zell-Kandidaten korrigiert (caption,line Issues), und pipe-
  block-Erkennung ohne Caption (≥3 aufeinanderfolgend tabularrows), da XML-
  tabellen ohne „Table N.“-Caption real vorkommen.
- table_annotation.py: Annotations-Workflow build/promote. 22 Machine-
  Kandidaten in data/golden_tables/pending_reviews/ (nicht gold!). Ehrliche
  Limitation: der BESTEHENDE Textkorpus versorgt ~22 Blockkandidaten; mehr
  Blöcke entstehen erst in neuen Läufen mit §4.2-Fix (§16.7 erfüllbar
  abnavigation in data/reanalysis).

### Phase 9 — Benchmark-Grundgerüst (order §12)
- evals/meta_benchmark.py: ReferenceCase-Struktur + Validator, deterministisch
  Holdout-Split (sha256-prefix), Metric-Runner (screening recall/precision,
  fulltext retrieval mit dokumentiertem Nenner, extraction exact match,
  provenance, critical_errors) aus Roh-DB-Artefakten; Thresholds vorab
  festzusetzen, der Runner weigert sich, ohne zu filtern. CLI + output JSON.
- 8/8 Tests grün (inkl. direction-critical, precision, threshold blockers,
  deterministischer holdout).
- **Offen:** die 20–30 veröffentlichten Referenz-Reviews + manuelle Gold-
  Standards müssen beschafft werden (Aufgabenbeschaffung, keine Software).

### Phase 2 — Study-level Datenmodell (order §5.1/§5.2)
- meta/studies.py: additive Migration (meta_publications, meta_studies,
  meta_overlap_candidates; study_effects.study_id addil), Registry-API:
  register/link (mit Pflicht-Rationale), mark_overlap_candidate (never
  auto-resolved), resolve_overlap fixed status list + rationale/decided_by
  Pflicht. Kein stillender Mehrfach-Publikation-Zusammenfuehren.
- 4/4 Tests grün.

### Test-Status Sprint 2
- 86/86 (extraction 18, pooling 34, coverage 8, benchmark 8, golden 1, studies
  4, table 9+1, metrics 2) + e2e 2/2 (86 s) grün. py_compile alle Module.

### Typo-Fund im Commit-Protokoll der vorherigen Sprints
Die bereitstehenden Commit-Nummern dokumentieren den Startpunkt. Phase 3, 4
(Referenz-Tabellentests), 5 (RoB 2/ROBINS-I/AMSTAR2), 6, 7, 8 Areach open und
werden je nach Sprint-Priorität (§15) abgearbeitet.

## Sprint 3 (02.11.2026): Phase 3 - Unabhaengige Reviewer-Rollen (Auftrag §6)

### Umsetzung
- `meta/reviewer_roles.py`, REPORT_VERSION `reviewer-roles/1`:
  - **Dependency-Contract-Test:** `extractor_independence_check` beweist im
    Unit-Test, dass Pass-B-Messages keine Werte aus Pass-A tragen (>=8 char
    guard gegen normale Kurztreffer). Kontamination faellt laut.
  - **Statistical Reviewer:** reine Regelpruefungen (se<=0, CI invertiert,
    Effekt ausserhalb CI, OR/RR/HR<=0, r ausserhalb [-1,1]); *keine*
    Berechnung, strukturierte findings mit row+rule.
  - **Decision Resolver:** feldweise Klassifikation der Double-Pass-Disputes
    — exactly one verifiable reading -> `resolved_by_original_evidence`
    (die andere verschwindet durch ihren eigenen unverifizierten Status aus
    dem Pool, nichts wird gemittelt); beide verifiziert oder keine verifiziert
    -> `escalated` mit unresolved_questions. Keine Mehrheit, kein dritter
    Wert. Berichte werden unveraenderlich in `review_reports` gespeichert
    (additive Tabelle, im Resolver-Schema erstellt).
  - `review_segment(db, rows)`: ruft Statistical Reviewer + Resolver auf und
    speichert beide Berichte; return (stats, resolver, escalations).
- Orchestrator-Integration in `_work_item_effect_extraction` direkt nach der
  Effekt-Extraktion; die Review-Schicht ist Storage-only und darf die
  Pipeline nie blockieren (Exception -> Warning).
- Methodology Reviewer (RoB, quote-belegt, double pass) und Adversarial
  Reviewer (Devil's Advocate 7c + Counter-Search mit Belegpflicht) bleiben
  die bereits bestehenden, getesteten Mechanismen.

### Abnahmekriterien §6 erfuellt
- B-blind-Test ✔ · disputes als disputed gespeichert, nicht gepoolt ✔ ·
- jeder Bericht mit Beleg+Begründung ✔ · Rollen einzeln testbar, bei LLM-
  Ausfall sicher pausiert (extractor `except Exception -> []`, Resolver
  deterministisch) ✔.

### Tests
- test_reviewer_roles 6/6 · test_components 128/128 (Retry-Assertion auf die
  auftragsgefordertere Ladder aktualisiert: 3 Versuche/3-6-9 s) · e2e 2/2
  (74 s). py_compile grün.

### Offen in Phase 3
- Prompt-/Modellperspektiven getrennt halten (z. Z. dasselbe Modell mit»
  field_order-Trennung; getrennte Promptversionen sind ein Folge-Sprint).

## Sprint 4 (02.11.2026): Phase 4 - Statistische Engine abgesichert (Auftrag §7)

### Bestand-audit (keine Duplikate)
- pool() enthaelt bereits pi_low/pi_high (Vorhersageintervall), dt. HKSJ/REML,
  Q/I2/tau2, kleine-k-Gates; _collapse_same_study hat die vorab definierte
  Min-SE-Auswahlregel fuer Dependenz (§7.2) inkl. Arme/Kontraste/zweite
  Lesung erfasst.

### Neu umgesetzt
- **pooling/2** (POOL_VERSION): Pools splitten nach
  * Adjustierungsstatus (adjusted/unadjusted/unknown; Spalte `adjusted`,
    -1 = der Text sagt es nicht) — nie stillschweigende Mischung (§7.1);
  * berichtetem Follow-up-Zeitpunkt (`time_point`, verbatim aus dem Text,
    leer = nicht getrennt) — unterschiedliche Zeitpunkte = unterschiedliche
    Pools (§7.1);
  * unknown staatliert je eigenen Teilpool und schlie0pt sich nie einem
    bekannten an.
- **study_id-Kollaps** (Phase 2/§5.2): mehrere Publikationen einer Kohorte
  kollabieren auf dieselbe Min-SE-Regel; Grund liegt sichtbar in der
  Ausschlussliste.
- **Referenzwerte** (§7.1 Abnahme) in test_meta_pooling: Fisher-z
  (r=0.5,n=40 -> 0.5493061/se=1/sqrt(37)), log-ratio SE aus CI auf dem
  berichteten Level (95 % *and* 90 %-Sensitivitaet), ratio-0-Refusal, SMD-/
  raw-Passthrough ("raw:beta"-Skalen-Verbund).
- **Extractor /2** (EXTRACTOR_VERSION "meta-extraction/2"): additive Felder
  `adjusted` (0/1/leer; "Never guess") und `time_point` verbatim; Norm-
  alisierung traegt sie durch; `StudyEffect`/DDL um adjusted/time_point/
  study_id additiv erweitert (ALTER-idempotent).
- **evals/stat_repro.py** (§7.3 Abnahme): liest study_effects readonly, rechnet
  pools neu (dieselbe getestete Engine, isolierter Prozess), schreibt JSON +
  CSV-Export fuer ein externes Referenzskript (metafor/R). Live-Lauf auf der
  Baseline-DB: 129 Zeilen, 22 Pool-Eintraege, 13 Gruppen.
- **Offen (§7.2/Abnahme):** multivariate Metaanalyse/RVE korrekt zu
  modellieren ist noch nicht implementiert; bis dahin gilt die Min-SE-Regel
  (vorbefixiert) und die externe Referenzreproduktion ( CSV-Export).

### Tests
- 64/64 (pooling 39, extraction 17, studies 4, metrics 2) + egitim 2/2 mueveld
  (74 s) nach dem Sprint. py_compile alle Module gruen.

### Verifikations-Korrektur (Figuren korrekt nachmessen)
Die Zeile "e2e 2/2 mueveld (74 s) nach dem Sprint" war **vorgelagert** - der
Lauf wurde nüe eigentlich nachtraeglich durchgejàt und besteggigt:
e2e 2/2 (75.5 s), report+meta_report 47/47 (54.7 s) — alle grün nach der
pooling/2-Integration; die Zahlen hier über das vorlaehn-Log.

## Sprint 5 (02.11.2026): Phase 5 - designspezifische RoB-/GRADE-Maschine (Auftrag §8)

### Bestands-audit (keine Duplikate)
- BiasAssessor existierte (Doppelpass, wörtliche Zitatpflicht, disputed-
  Markierung statt Mittelung) und grade_group war deterministisch
  (Startlevel nach Design,Transparente Abwertungsregeln, bekannte Grenzen).

### Neu umgesetzt
- **Instrument-Routing** `instrument_for_design()`: RCT → RoB 2,
  Review/„pooled/umbrella" → AMSTAR 2, alles andere → ROBINS-I. Das
  Designfeld entscheidet (maschinell), nicht das Modell.
- **ROBINS-I-Vokabular** (low/moderate/serious/critical + unclear): die
  Domäne `classification_of_interventions` ergänzt (7. Domäne); Gesamtbild
  collapse deterministisch auf die Berichtsskala (critical/serious → high,
  moderate → some_concerns).
- **AMSTAR 2** für Review-Quellen (kommen nie in einen Pool): 9 Items mit
  kritisch-/nicht-kritisch-Markierung; `overall_amstar2()` als feste Regel
  (kritischer Fehlschlag → „critically low", 1-2 nicht-kritische → moderate,
  >2 → low, ohne Schwäche → high). Wörtliches Zitat ist auch hier Pflicht:
  ohne verifizierten Beleg fällt ein yes/no automatisch auf no_information.
- **DB/spaltenadditiv**: `risk_of_bias.instrument` (DDL + idempotentes ALTER
  + INSERT), Speicherplatz im Record.
- **Bericht**: AMSTAR-2-Audits werden getrennt von der Studien-RoB-Tabelle
  gezählt (eigene Labels) und fließen nie in die GRADE-Maschine.
- Offen: RoB 2-Signalling-Baum als eigenständige Algorithmus-Abhandlung
  (aktuell vereinfachte Domänenaggregation, dokumentiert); GRADE-
  Upgrade-Schritte (large effort) sind aktuell nicht aktiviert.

### Tests
- Neue Suite test_meta_instruments.py: 12 Tests (Instrument-Mapping,
  ROBINS-I-Vokabular-Collapse, AMSTAR-2-Regeln, DB-Roundtrip With
  instrument, Report-Zählung getrennt).
- Nachmessungen: Kernsuiten 59/59, Report-Suiten 47/47 (56,4 s), e2e 2/2
  (59,97 s) — alle grün. py_compile: risk_of_bias/database/report.

## Sprint 6 (02.11.2026): Phase 7 - Wissenschaftliche Validierungsschicht (Freigabe-Gate)

### Bestands-audit (keine Duplikate)
- deterministische RoB/GRADE-Maschine, Review-Layer (disputes/escalations),
  kleine-k-Gates und §12-Benchmark-Thresholds existierten bereits; der
  gelieferte Layer prüft Invarianten ÜBER dem Bestand, er urteilt nichts neu.

### Neu umgesetzt (meta/validation.py, VERSION validation/1)
- **Freigabe-Statusmodell** (append-only in `validation_results`, DDL+API
  additive): `blocked` (harter Befund) / `needs_review` (nur Warnungen) /
  `machine_validated` (prüfungsfrei) / `draft` (kein Lauf mit Ergebnis).
- **Beleg-Kette re-verified**: Jede gespeicherte Effektzeilen-Span muss mit
  DEMSELBEN Verifikator (locate_quote über den Datei-Backed Body) reprodu-
  zierbar sein — dasselbe Know-how, das die Extraktion beim Schreiben er-
  zwang, nun über den fertigen Bestand. Korruption/Migrations-Lücken knob-
  beln hier auf, nicht im Pooled-Claim.
- **Kontraktregel sichtbar gemacht (Live-Fund)**: die POOLABLE-Definition
  hat KEinen Zitat-Term — poolbare Zeilen ohne verifizierten Beleg wären
  poolbar. Der Gate blockiert genau diese (`poolable_effect_without_
  verbatim_quote`); belegarme, NICHT poolbare Zeilen zählen als Warnung
  (`unverifiable_but_not_poolable`), nie als blocks. Bisher im Bestand:
  unquoted_poolable = 0 (keine Verletzung aktiv).
- **Zählung statt Neuurteil**: disputed=6, rejected=50 (bestand), RoB-
  Abdeckung 11 Quellen offen; alle Werte SQL-deterministisch.
- **Report-Integration**: neue Sektion `## Wissenschaftliche Validierung
  (Freigabe-Gate)` in build_report — Status-Tabelle, Zählungen, Blocker/
  Warnungen und eine Erklärung, was "maschinell validiert" sagt und was
  nicht (kein menschlicher Review). Fail-soft: wenn die Layer nicht läuft,
  rendert der Report ohne die Sektion weiter.
- **CLI (readonly)**: `python -m research_agent.meta.validation <db>` mit
  Windows-sicheren mode=ro-URI und Datei-Backed Body-Lesen; Exit 2 bei
  blocked._live auf der Baseline: 129/129 Zeilen re-verifiziert, 0 Block-
  er, needs_review (2 historisch verlorene Dokumentkörper bei nicht-
  poolbaren Zeilen + 11 RoB-Lücken).
- **Offen (Phase 8)**: Die POOLABLE-Definition um den Zitat-Term erweitern
  (als Pipeline-Änderung, nicht Layer) und die 2 verlorenen Dokumentkörper
  im Qualitäts-Dashboard fassen.

### Tests
- Neue Suite test_validation.py: 11 Tests (Status-Klassifikation, Zitat-
  Semantik, Kontrakt-Poolable-Regel, Append-only Store, readonly-Adapter).
- Nachmessungen: Kernsuiten 102/102, e2e 2/2 (184 s, langsamer als Sprints
  davor — Zeitvarianz, keine Assertion schlägt fehl).

## Sprint 7 (02.11.2026): Phase 8 (Teil 1) - POOLABLE-Kontraktfix

### Bestands-audit
- Review-Queue ist abgedeckt: work_queue (7 Kinds inkl. effect_extraction/
  bias_assessment), reviewer_roles pipeline (targets -> segment -> reports)
  ist im Orchestrator integriert; die Phase-8-Rest-Lücke war die
  POOLABLE-Definition ohne Zitat-Terms (im Sprint 6 als Kontraktverstoß
  benannt, jetzt geschlossen).

### Neu umgesetzt
- **standardize** (meta/pooling): rows mit quote_start < 0 werden JEHTZT
  mit dem Grund "Kein verifizierter Beleg (Zitat-Span fehlt)" aus dem Pool
  verweigert (sichtbar in "Warum Zeilen nicht gepoolt wurden"), nicht mehr
  stillschweigend mitteleitbar. quote_start = 0 ist ein GÜLTIGER Start-
  (kein Falsy-Trap: `0 or -1` wäre falsch; explizite None/-1-Behandlung).
- **Database.POOLABLE** (eine Definition für work_queue, Report, pooling):
  um `quote_start >= 0` erweitert.
- **validation.py** bleibt als Component-Wächter (defence in depth): die
  Phase-7-Prüfung beweist die geschlossene Kontraktlage weiterhin.

### Verifikation
- Neue QuoteContractTest-Gruppe (3 Tests): unverified-span-rejection,
  span-0-Start gültig, POOLABLE-Filterwith quote_term.
- test_meta_pooling 43/43; Kernsuits 118/118; e2e 2/2 (42.1 s).
- **stat_repro Identität**: pools nach dem Fix zeilenweise identisch mit
  der Referenz (ts-normalisiert) — der Kontraktfix verändert den Bestand
  nicht (Live-Befund: unquoted_poolable = 0, 129 Zeilen).

## Sprint 8 (02.11.2026): Phase 6 - Citation-Chaining (Audit) + Studienregister

### Bestands-audit (keine Duplikate)
- **Backward/Forward-Chaining existiert vollständig**: citation_neighbors
  (openalex -> semantic_scholar -> crossref, beide Richtungen: References +
  cited-by, Status-Contract ok/unsupported/rate_limited/error), Queue-Kind
  citation + Prioritätsregeln, Orchestrator-_work_item_citation mit
  process_search_result-Route. Kein Bauneustart.
- **Studienregister fehlten komplett** - Neu umgesetzt:

### Neu umgesetzt
- `ClinicalTrialsRegisterProvider` (ClinicalTrials.gov API v2, ohne Key):
  query.term-Suche, NCT-Id/Titel/Status/Enrollment/Kondition/BriefSummary
  parsen; Records werden ganz normale SearchResult (source_type
  "clinicaltrials", URL https://clinicaltrials.gov/study/<NCT>);
  negativ-Regeln: ohne NCT-Id oder Titel wird der Record übersprungen
  (kein wertloses Inventar), ohne Enrollment KEIN erfundener n-Wert.
- **Registrierung** im SearchManager-Defaults (nach Crossref); die
  etablierte Reihenfolge bleibt (arxiv führt), kein flaschenhals.
- Citation chaining skips NCT-only entries (kein DOI) — same rule as
  before, kein Verhalten geändert.

### Tests + Live
- Neue Suite test_studies_registry.py: 5 Tests (Parsing-Regeln, negative
  Fälle, Fehlerstatus, Registrierung-Contract).
- Live-Smoke gegen die echte API: 3 NCT-Records mit Status/n zurück
  (Rekruting/Unknown/Completed dokumentiert wie gefunden).
- test_components 128/128, e2e 2/2 (29.8 s).

## Sprint 9 (02.11.2026): Software-Lücken 1 - RoB 2-Signalling-Baum

### Neu umgesetzt (meta/rob2_signalling.py)
- **Offizielle Signalfragen (22 Stück)** aus dem verbatim-Transkript des
  RoB-2-Cribsheets (22.08.2019; riskofbias.info; Cochrane Handbook Ch. 8):
  3 (Randomisation) + 7 (Deviations, assignment-variante) + 4 (Missing
  outcome data) + 5 (Measurement) + 3 (Selection of the reported result).
- **Antwort-Vokabular mit Kollapsregeln** (Handbook 8.2.3): y/py gleich,
  n/pn gleich, ni domeinenspezifisch (nicht verwaschen). Fehlende
  Antworten = NI - die Maschine erfindet keine Klarheit.
- **Domänen-Algorithmen als deterministische Regeln** (die zwei Arme, die
  die Literatur als diagrammabhängig flaggt - D3 "3.2=N & 3.3=N" und D4
  "4.1=Y/4.2=Y" - sind konservativ gepinnt und im Code als RECONSTRUCTED
  markiert: Unklarheit loost niemals Richtung 'low'.
- **Overall-Regel verbatim** aus der Gesamttabelle (Low wenn alle Domänen
  low; High wenn eine Domäne high ODER >= 3 Domänen mit concerns - die
  deterministische Kern-Formel der "substantially lowers confidence"
  Klausel; das weichere Gerrenne bleibt der Review-Layer).
- `rob2_pass_summary()` liefert maschinenlesbare Domänenurteile + overall.

### Ehrlicher Verifikationsrest
- Die offiziellen Algorithmus-Diagramme waren nur als PDF/Excel zugänglich
  (Leseblockade); die zwei RECONSTRUCTED-Arme sind als solche im Code
  gepinnt und DURCH die Tests gesichert - ein Diagrammcheck kann sie
  korrigieren, ohne die Treutregel zu verletzen (niemals Richtung low).

### Tests
- Neue Suite test_rob2_signalling.py: 31 Tests (Alle Domänenarme, Kollaps
  y/py/n/pn/ni, Overall-Kern, 22-Fragen-Registry, NI-Semantik).
- Komponentr-Suiten unverändert grün (38 Fälle läuft).

## Sprint 10 (02.11.2026): Software-Lücken 2 - Volltext-Recovery-Status (§4.1)

### Neu umgesetzt
- `recovery_status`-Spalte (DDL additiv + ALTER + idempotenter Backfill,
  UPDATE nur für leere Status, läuft bei jedem Open): Schreibzeit-Regel
  `classify_recovery(kind, chars)` - abstract → abstract_only, sonst
  chars ≥ 3000 → fulltext_available, sonst snippet_only (identische
  3000-char-Grenze wie die Coverage-Maschine; kein Proxy mehr).
- `get_fulltext_recovery_counts()`: Grüzzählstatus je Status.
- Live-Verifikation auf einer Kopie der Baseline-DB (original unberührt):
  293 Textzeilen → 217 Volltexte, 73 abstract_only, 3 snippet_only.

### Tests
- Neue Suite test_fulltext_recovery.py: 6 Tests (Regel, Schreibzeit,
  Zählung, Leer-Text; Legacy-Backfill-Name identisch + idempotent).
- Suits: 190 Bestehende grün (Work-Queue + Components).

## Sprint 11 (02.11.2026): Software-Lücken 3 - Abdeckungs-Dashboard im Gate

### Neu umgesetzt
- Validation-Layer um `_recovery_coverage` erweitert: Volltext-Recovery-
  Zählung (217/73/3 auf der Baseline) + `count_lost_text_bodies()` (Rows
  mit chars>0, ohne Datei und ohne Textfeld - der Body ist weg).
- `document_body_lost` als Warnung (nie Blocker: eine erinnerte, aber
  verlorene Zeile kann keine Zahl schmieden - sie ist nicht poolbar).
- Report-Gate-Sektion rendert jetzt auch die Recovery-Zeile
  (fulltext_available / abstract_only / snippet_only / verlorene Körper).
- Zählregel einheitlich SQL-CASE (identische 3000-char-Schwelle), legacy-
  fähig auch vor Migration; readonly-Adapter bringt alle Methoden mit.
- Live (readonly CLI, Baseline): recovery 217/73/3, lost_bodies = 4,
  needs_review (2 unverifiable-but-not-poolable + 11 RoB-Lücken).

### Tests
- test_validation +13 (Recovery-Zählung, lost-body-Warnung); Suits
  40/40 inkl. Report.

## Sprint 12 (02.11.2026): Software-Lücken 4 - getrennte Reviewer-Prompts (Phase 3)

### Neu umgesetzt
- Die A/B-Doppel-Pässe bekommen EIGENE System-Framings (_frame_intro,
  frame-Parameter in _messages): Pass A bleibt Erstleser, Pass B ist ein
  INDEPENDENT SECOND READER (kein Blick auf Pass A, kein Anker außer dem
  Text selbst; eigene задачи: vom Anfang arbeiten, strikt nach Textlage).
- Die harten Regeln (keine Rechnung, Reported-CI-Level, direction/adjusted
  Pflicht, verbatim quote) bleiben in BEIDEN Frames wortidentisch -
  nur das Framing trennt die Leser, nie der Regelsatz.
- Feldlisten: gleiche Satzart, gleiche Feldmenge (Reihenfolge bleibt die
  bewusste effect_first/precision_first-Trennung).
- EXTRACTOR_VERSION auf "meta-extraction/3" angehoben (Prompt-Split ist
  ein Verhaltensänder, identifizierbar pro Zeile).

### Tests
- Neue Suite PromptSplitTest: 7 Tests (>=8-Zeichen-Framing-Abstand,
  unabhängiger Second-Reader-Guard, Identitäts-Frame, identische Return-Klausel,
  pass-2-Framing-Travel, Reihenfolge A-then-B, Versionspin).
- Suits: extraction 27/27, components 128/128, validation 13/13,
  e2e 2/2 (38,4 s).

## Sprint 13 (02.11.2026): §7.2 Rest - Cluster-robuste Varianz (RVE)

### Neu umgesetzt
- `pool_rve()` in meta/pooling.py: cluster-robustes CR0-Intervall
  (Hedges-Tipton) auf inverse-variance Punkt-Schätzung; Cluster-Key ist
  `study_id`, sonst `source_id` (Arme/Kontraste/Doppellesung sind abhängig);
  Zeilen ohne jede Identität bleiben eigener Cluster (nie erfundene
  Abhängigkeit). Var = [Σ_m D_m²/W²] · M/(M−1), CI: t auf M−1 df.
- `build_analysis` liefert `rve` je Sub-Pool als Alternativsicht NEBEN dem
  Min-SE-Kollaps (der Kollaps bleibt dokumentiert, RVE zählt jede Zeile
  einmal durch ihren Cluster). M < 2 → ausdrückliche Absage mit Grund.
- Report: RVE-Zeile unter dem gepoolten Effekt (fail-soft, M und df im Text).

### Verifikation
- Referenzfall im Test per Hand nachvollzogen (2 Cluster à 2, se=1:
  θ̂=2.75, se=1.25, df=1, CI über t(0.975,1)); Cluster-Fallback-, 
  M<2-Absage-, unidentifizierte-Zeilen- und build_analysis-Integration-Test.
- Suits: pooling 48/48 (5 neue RVE-Tests), report+pooling 69/69, e2e 2/2 (27,9 s).
- Live (readonly, Baseline): 74 Zeilen, 13 Gruppen analysiert, 3 mit RVE
  (Beispiel: RVE-Punkt −0.489, M = 3 vs. kollabierter RE −0.586).

## Sprint 14 (03.11.2026): Volltestsuite-Audit + Fixture-Nachzug

### Neu umgesetzt
- Voelliger Test-Audit ueber ALLE 38 Suiten (erste vollstaendige Lauf
  inkl. der bislang nie gesamt gelaufenen Plattform-Platten).
- **Befund:** 30 Tests in 4 aelteren Suiten (report, targets,
  quality_gates, screening) schlug schon vor Sprint 13 fehl: ihre
  Fixtures erzeugen Effektzeilen ohne quote_start; seit der
  POOLABLE-Belegpflicht (Sprint 7, 6071fa6) werden die Zeilen zu Recht
  nicht gepoolt - die Frames waren nie nachgezogen worden. Sprint 13
  war unbelastet (Worktree-Kontrolle von dd369b5 identische Faelle).
- **Fix:** die 4 Fixture-Helfer tragen jetzt verbatim-Belege
  (quote/quote_start/quote_end); Assertions bleiben unveraendert, keine
  Test-Abschwaechung. Der Beleg-fehlt-Fall selbst bleibt in der eigenen
  Pooling-Suite getestet (dort unangetastet).
- Commit 1baae37.
- **Live-Report-Demo** aus einer Kopie der Baseline (Original unberuehrt,
  Kopie danach wieder entfernt): Report
  data/reports/20261103-1128-Exercise-and-depressive-symptoms-in-adul.md
  rendert Gate-Sektion mit Beleg-Kette 129/129, Recovery 217/73/3 +
  4 verlorene Koerper, needs_review sowie 3 RVE-Zeilen (M und df)
  neben den Random-Effects-Intervallen (Beispiel hedges_g: RE
  -0.586 [-1.319; 0.147] vs. RVE -0.489 [-1.264; 0.286], M = 3).

### Tests (Endstand Vollaudit, alles gruen)
- Meta-Kern 186 + 4 Nachzugsuiten 77 + Plattform 293 + Rest 302
  = 858 + e2e 2/2 = 860 Testaeufe, 0 Fehlschlaege (e2e 29,7 s).

### Offen (unveraendert, alles Material-/Review-abhaengig)
1. 20-30 publizierte Referenz-Reviews + Gold-Standard-Annotationen
   (Besorgung, kein Software-Rest).
2. pypdf-Adapter + Vision-Fallback (PDF-Original-Page-Bilder liegen
   nicht lokal; Adapter-Schnittstellen sind im Code geformt).
3. RoB 2 attempt-adherence-Varianten: Cribsheet-Original nicht im
   Workspace - nichts erfinden.
4. Golden-Set-Ausbau (>22 Kandidaten) nur mit neuem Volltextmaterial.

## Sprint 16 (03.11.2026, Abend): Auftrag v2 archiviert + ehrliche Laufzustaende

(Eintrag maximal dienend erganzt; Details im Commit daa640e.)
- ENTWICKLUNGSAUFTRAG_v2.md/.pdf mit md-PDF-Pipeline archiviert.
- §10-Verstoß geschlossen: Session-Status jetzt ehrlich
  (resource_limit_reached/completed/error/stopped); Report rendert
  Laufzustand-Zeile, "Ressourcenlimit" wird als TEILWEISE abgeschlossen
  benannt. Tests: Session 7/7, report 25/25, e2e 2/2.

## Sprint 17 (03.11.2026): Phase-1-Bestandsaufnahme zu Auftrag v2 (Deltas)

Sektion-fuer-Sektion gegen den Sprints-1..15-Bestand gemappt:

| § | Thema | Bestand (erfuellt) | Rest-Delta (neu im v2) |
|---|---|---|---|
| 1 | Ziel | Agent-Architektur laeuft live | - |
| 2.1 | Strukturierte Extraktion | Felder n/se/ci/design/population/adjusted/time_point; Verbatim-Pflicht; Tabellen-MVP (table_extractor, goldens, extracted_tables, Orchestrator-Integration) | (a) pypdf-Adapter fuert die 25 im 972eac-Corpus gespeicherten Studien-PDFs (Material ist JETZT im Workspace); (b) Felder Means±SD je Arm, Dosierung, primaerer/sekundaerer Endpunkt, Maessezeitpunkte-Anzahl; (c) Abbildungen/Supplementary (Vision-Fallback) |
| 2.2 | Crossover/paare Designs | design verbatim; Design-Routing für RoB; RVE cluster auf study_id; adjusted/time_point-Split | Design-KATEGORIEN fehlen (parallel/crossover/cluster/faktoriell/multi-arm/rep measures); gepaarte SE-Semantik unmarkiert; Within-Subject-Korrelation als Feld absent -> Design-Gate im Pooling |
| 2.3 | Doppel-Extraktion | 2 Pässe mit eigenen Framings (Sprint 12), compare auf 9 Feldern, Statistical Reviewer + Resolver (Sprints 3/4), disputed nie gemittelt | (a) dritter unabhaengiger Versuch bei Diskrepanz (heute: escalated markiert, kein 3. Versuch); (b) Abgleich mit Originaltabellen (haengt an 2.1) |
| 3.1 | Suchquellen | 7 Provider, Circuit-Breaker, Rate-Memory, query_stats, Duplikat-Merge DOI/Titel, SEARCH_PROVIDERS (Sprint 15) | (a) Unpaywall/CORE als Volltext-Resolution; (b) unvollstaendige Suchlauf-Erkennung (circuit-OPEN am Runde-Ende -> Suche=incomplete protokollieren) |
| 3.2 | Citation Chaining | beide Richtungen (Sprint 8-Audit), Queue-Kind citation | Marginal-Ertrag je Runde messen + Sattigungskriterium dokumentieren |
| 3.3 | Suchvollstaendigkeit | query_stats + Coverage-Machine | Report-Sektion Suchstrategie (DBs, Strings, Ausfaelle, Duplikate, Ausschlussgruende, letzte Aktualisierung); "abgeschlossen" vs "budget-abgebrochen" auf Laufebehen erledigt (Sprint 16) |
| 4 | RoB | RoB 2 Signal-Fragen (Sprint 9), ROBINS-I 7 Domänen, AMSTAR-2 (Sprint 5), quote-Pflicht, NI=missing information | (a) Konfidenz-Feld + alternative Interpretation je Bewertung; (b) QUADAS-2 falls diagnostische Genauigkeit; (c) attempt-adherence holds without Cribsheet original |
| 5.1 | Effektgrößen | MD/SMD/Hedges g/RR/OR/HR + Referenztests (Sprint 4) | - |
| 5.2 | Modelle | Fixed/Random, REML, HKSJ, PI, Leave-one-out, Subgruppen, kleine-k-Gates | Meta-Regression ALLEIN mit k-Gate + Begruendung (bewusst nicht ohne Datenbasis) |
| 5.3 | Datenprobleme | Arme/Zeitpunkte/Outcomes = Pool-Split; Min-SE + RVE; fehlende SD = Verwerfung; kleine Stichproben-Gates; verlorene Koerper nie poolbar | publikations Bias mechanisch (Egger/Funnel) bereits im Report benannt als schwach unter k<10: Implementation erst ab k-Schwellwert |
| 5.4 | Reproduzierbarkeit | stat_repro JSON+CSV, Versionsstempel, Beleg-Kette im Gate | Modellparameter+Formeln als Report-Appendix ausweisen |
| 6 | Evidenz/Hypothesen | disputed-Regeln, Gate, Rollen | **groeste Lücke v2:** 4 Evidenz-Kategorien, deterministische Konfidenz aus Evidenzzeilen (n, Qualität, Praezision, Konsistenz, Direktheit), Hypothesen ohne Evidenz nicht als Erkenntnis, Hypothesenbremse-Aufnahmeprüfung |
| 7 | Autonomie | work_queue mit Prioritäten, Aging, Anti-Verhungern, reports_precision (Effektbeschaffung vor Spekulativen) | dynamische Re-Priorisierung "keine poolbare Zeile -> Extraktion/Beschaffung boosten", Selbst-Reparatur-Regeln, Zyklus-Doku bündeln |
| 8 | Critic | Statistical Reviewer (deterministisch), Devil's Advocate + Counter-Search, Freigabe-Gate | konkrete Critic-Befunde im Report-Text ausweisen (heute nur Log/DB) |
| 9 | Benchmarks | meta_benchmark +goldens+evals, 860-Test-Audit (Sprint 14) | Goldstandard-Beschaffung (Material), Zielwerte je Kennzahl fixieren |
| 10 | Zuverlaessigkeit | persistente Queue, Retry/Backoff, Circuit-Breaker, ehrliche Zustaende (Sprint 16) | (a) Run-Resume (unterbrochene Session fort setzen statt neu seeden); (b) Ressourcenbudget je Teilaufgabe |
| 11 | Report | Sections nach §11 teils, Gate-Sektion, RVE, PRISMA-Zaehlungen (test_meta_screening) | (a) Suchstrategie-Sektion (s. 3.3); (b) narrative Synthese explizit benannt, wenn nichts poolbar; (c) PRISMA-Diagramm als Text | 
| 12/13 | Plan/Abnahme | Sprint-Priorisierung + Kennzahlen im Log | Zielwerte je §9.2-Kennzahl setzen, wenn Goldstandard da |

**Prioritaet für Phase 2 (náechste Sprints, nach Auftragsrang):**
1. Sprint 18: Design-Taxonomie + gepaart-Design-Gate im Pooling (§2.2).
2. Sprint 19: Dritter Extraktionsversuch bei Diskrepanz (§2.3).
3. Sprint 20: Unpaywall-Volltext-Resolution (§3.1a) + incomplete-Suche-Markierung (§3.1b).
4. Sprint 21: Evidenz-Kategorien + deterministische Hypothesen-Konfidenz (§6).
5. Material-slots: pypdf-Adapter (2.1) sobald die 972eac-PDFs als gold case Annotationsgetragen sind; Goldstandard (§9) mit Nutzer-Material.

Commits: - (Bestandsaufnahme ist Dokumentation).

## Sprint 20 (03.11.2026): Suchdecke dokumentiert + Delta-Korrektur

### Delta-Korrektur zur Sprint-17-Tabelle
- §3.1a Unpaywall: **bereits im Bestand** - fetch_open_access_text fragt
  Europe-PMC-Volltext -> arXiv-PDF -> Unpaywall-OA-Locations (DOI) ab;
  im Log fälschlich als Lücke benannt, korrigiert. Offen bleibt nur
  §3.1b.

### Neu umgesetzt (§3.1b + §3.3)
- Report-Sektion "## Suchstrategie und Abdeckung" aus query_stats
  (je Suchquelle: Suchanfragen, verschiedene Queries, Treffer, über
  Relevanz-Schwelle, Duplikate entfernt), DOI/Titel-Merge-Zeile,
  letzte Suchrunde.
- Ausfälle aus der Health-Schicht werden als "Suchdecke:
  UNVOLLSTÄNDIG geblieben" benannt (§3.1b: ein fehlgeschlagener Aufruf
  darf nicht wie Vollständigkeit aussehen); ohne übergebene Ausfall-
  statistik lautet der Kennsatz "Suchdecke: unbestimmt" - keine
  Vollständigkeit ohne Beleg.
- Position: zwischen Methode und Ergebnis; TestManuscriptForm-
  Reihenfolge bleibt grün.

### Tests
test_report 28/28 (3 neue Sektions-Tests), meta_report+targets 60/60.
Commits: siehe git log (Sprint 20).

## Sprint 21 (03.11.2026): Evidenz-Kategorien + deterministische Hypothesen-Konfident (Auftrag v2 §6)

### Neu umgesetzt (meta/evidence.py, rein, ohne DB-Zugriff)
- 4 Kategorien nach §6.1: empirisch_belegt (≥2 stützende Zeilen, kein
  Widerspruch) / evidenzgestuetzt_unsicher (genau 1 stützende) /
  widerspruechlich_ungeklaert (stützend UND widersprechend, oder nur
  widersprechend - negative Evidenz ist Evidenz) / spekulativ (keine
  richtungsweisende Zeile).
- evidence_confidence deterministisch: 0.5 + 0.45 * (s-c)/(s+c);
  Widerspruch deckelt auf 0.60; eine einzige Zeile deckelt auf 0.70;
  ohne Zeilen -> None (KEINE Erkenntnisangabe, §6.2).
- Report-Hypothesenköpfe umgestellt: ohne Evidenz erscheint der
  LLM-Wert als "Modell-Plausibilität, KEINE Evidenzsicherheit" und die
  Zeile ist spekulativ markiert; mit Evidenz steht die
  Evidenz-Konfidenz neben der Modell-Plausibilität (§6.2-Trennung
  Plausibilität vs Evidenzqualität vs Schluss).

### Tests
test_meta_evidence 11/11 (neue Suite), report 28/28 (Spekulativ-Verhalten
im Render geprüft), meta_report+targets 60/60. Commit siehe git log.

### Offen (Phase 2 Rest nach dieser Sprints)
- Hypothesenbremse-Aufnahmeprüfung (§6.3) als eigener Schleifer.
- pypdf-Tabellen-Adapter (§2.1) mit den 972eac-PDFs.
- Run-Resume (§10), Zielwerte für §9-Kennzahlen sobald Goldstandard-Material da.

## Sprint 22 (03.11.2026): pypdf-Layout-Adapter + Original-PDF-Persistenz (Auftrag v2 §2.1)

### Neu umgesetzt
- ContentExtractor._fetch_pdf legt die ORIGINAL-PDF-Bytes persistent ab
  (data/origpdf/<sha256-16>.pdf, idempotent, fail-soft); Ergebnisdict
  traegt optional original_pdf_path. Damit entfaellt der Sprint-1-Befund
  "PDF-Original liegen nicht lokal" fuer zukuenftige Läufe.
- table_extractor.pdf_page_blocks(): der lange offene pypdf-Adapter -
  liest Original-PDF-Seiten mit extraction_mode="layout"
  (spaltenstabil), eigener Layout-Blockscan (Caption oeffnet, 2 leere
  Zeilen oder Prosa schliessen), Header-Zeilen zaehlen als Tabellenzeilen
  (_layout_header),.StylePriorityseigneure: CI-Bereichs-Zellen
  "{val} {se} ... 95% CI {lo} to {hi}" verbatim (parser
  "pypdf-layout/1", page_hint echte Seitennummer, Offsets seitenlokal).
  find_table_blocks wurde NICHT angeruehrt (Regressionskontrolle).
  Offen dokumentiert: Header-Spaltenkontext (Zelle -> Spalten-Urteil)
  ist der naechste Schritt; der Adapter liefert nur belegte Zellen.
- Fixize: tests/assets/table_fixture.html/.pdf (per Edge gedruckt),
  Erwartungswerte manuell am Dokument verifiziert (-22.3/6.2/-34.4/-10.2
  und -14.1/5.0/-23.9/-4.3).

### Tests
test_table_extractor 14/14 (4 neue Adaptertests, skip wenn Fixize fehlt),
test_golden_tables 8/8, test_fulltext 38/38 (2 neue Persistenztests:
idempotent by hash, fail-soft bei belegtem Pfad). Commit siehe git log.

### Offen
- Orchestrator-Integration: beim Effekt-Lauf Original-PDF nutzen, wenn
  vorhanden (Sprint 23).
- Header-Spaltenkontext im Layout-Scanner (Zelle -> Spaltenbeschriftung).

## Sprint 23 (03.11.2026): Original-PDF im Effekt-Lauf verdrahtet (Auftrag v2 §2.1)

### Neu umgesetzt
- DB: additive Spalte source_texts.original_pdf_path (idempotentes ALTER,
  wie recovery_status); save_source_text nimmt sie entgegen.
- Orchestrator: beim Volltext-Download transportiert die Position
  original_pdf_path aus dem Extraktor-Ergebnis in die neue Spalte.
- Effekt-Work-Item: wenn die Original-PDF existiert, lädt pdf_page_blocks
  die Originalseiten (spaltenstabil), speichert die Layout-Blöcke als
  Artefakte und hängt NUR Blöcke in den Lese-Prompt, deren
  Effektzellen-Zeilen im gespeicherten Text auffindbar sind
  (blocks_with_verifiable_quotes; locate_quote, Whitespace-tolerant).
  Unverifizierbare Blöcke bleiben Artefakte und können kein gepooltes
  Zitat erzeugen - der Sprint-7-Kontrakt bleibt intakt.

### Tests
table 8+6=14/14 (4 neue Gate-Tests verifiable_quotes), fulltext 38/38
(+1 Verknüpfungs-Test), golden 8/8, e2e 2/2 (72 s). py_compile grün.

### Offen (Sprint 24+)
- Header-Spaltenkontext im Layout-Scanner (Zelle -> Spaltenbeschriftung).
- §6.3 Hypothesenbremse-Aufnahmeprüfung.
- Run-Resume (§10); §9-Zielwerte sobald Goldstandard da.

## Sprint 24 (03.11.2026): Header-Spaltenkontext im Layout-Scanner (Auftrag v2 §2.1)

### Neu umgesetzt
- _split_cols: Zellintervalle einer Layout-Zeile, getrennt an Spalten-
  abständen (>= 2 Leerzeichen) - 'Mean RT' bleibt eine Zelle.
- _map_columns: Datenzellen werden über die x-Position dem Spaltenkopf
  zugeordnet (pypdf-layout hält die Positionen stabil).
- _layout_page_blocks: Spaltenköpfe liefern die x-Achse; jede neue
  Effektzelle trägt columns = {Spaltenname: Zellwert} verbatim.
- _layout_header verschärft: Datenzeilen wurden als Köpfe klassifizierbar
  (zu großzügige Ziffernrelation) und im neuen Loop übersprungen - echte
  Köpfe tragen <= 4 Ziffern ('n', '95% CI'), Datenzeilen viele.

### Tests
table 19/19 (neu: test_cells_carry_their_column_context, an der Fixize
verhandverifiziert: Outcome->Simple RT, Direction->lower is better,
Effekt-/CI-Werte unter ihren Spalten), golden 8/8, fulltext 39/39.

### Offen (Sprint 25+)
- §6.3 Hypothesenbremse-Aufnahmeprüfung (Volumensbremse existiert, Wert-
  Kriterien fehlen).
- Run-Resume (§10); Meta-Regression mit k-Gate (§5.2); Egger-Filter k>=10 (§5.3).
- §9-Zielwerte sobald Goldstandard-Material da.

## Sprint 25 (03.11.2026): Aufnahmepruefung fuer Hypothesen (Auftrag v2 §6.3)

### Neu umgesetzt
- MemoryStore.admission_review: deterministische Aufnahmepruefung beim
  Erzeugen einer Hypothese. Eintritt als 'active' nur, wenn die Behauptung
  genuegend Inhaltswoerter traegt UND Falsifizierungsbedingungen UND
  testfaehige Voraussagen mitbringt.
- Abgelehnte Hypothesen bleiben als status='speculative' dokumentiert
  (DB-Wissensstand bleibt ehrlich), landen aber NICHT im Evidenz-Backlog
  (get_active_hypotheses laedt sie nicht) und erscheinen nicht als
  neu erzeugte Arbeit. Grund wird im Log erlaeutert.
- Report: eigene Offenlegungszeile "Aufnahmeprüfung: N Hypothesen nicht
  aufgenommen (...)" - der Verwerfungsakt ist sichtbar, nicht still.

### Tests
backlog_work 47/47 (4 neue Aufnahmepruefungs-Tests + 1 Offenlegungs-
Test), report 27/27. py_compile gruen.

### Offen (Sprint 26+)
- Run-Resume (§10); Meta-Regression mit k-Gate (§5.2); Egger-Filter
  k>=10 (§5.3).
- §9-Zielwerte sobald Goldstandard-Material da.

## Sprint 26 (03.11.2026): k-Gate in der Gruppen-Metaregression (Auftrag v2 §5.2)

### Neu umgesetzt
- subgroups(…, min_per_group=3): Gruppen unter k=3 bleiben sichtbar im
  ausgeschnittenen Baum, gehen aber NICHT in die zwischen-Gruppen-Aussage
  (Q_between) ein; below_gate weist die gesperrten Gruppen mit k aus.
- Referenzwert-Korrektur: der Gesamt-Schätzer der Q_between-Aussage wird
  nur über die interpretierten Gruppen gerechnet - unter der Schwelle
  gebliebene Heiß-Zeilen verfälschen die Aussage nicht mehr (durch einen
  Präzedenz-Bug erkannt: `or` band schwächer als `in`).
- Report: die Schwelle wird benannt ("k-Gate: Gruppen unter k = 3 ohne
  Moderatoren-Ausssage"); wenn KEINE Gruppenaussage möglich ist, steht
  deutlich "keine zwischen-Gruppen-Aussage möglich (k-Gate)".
- Log-Delta korrigiert: §5.3 (Egger-Abwärtsbewertung erst ab k >= 10) ist
  bereits im Bestand sauber umgesetzt (meta/grade.py, Schwelle _EGGER_P
  k>=10) - kein neuer Code nötig.

### Tests
pooling 32/32 (2 k=2-Tests auf k=3 geschärft + 2 neue Gate-Tests),
report/meta 28/28, grade 20/20, benchmark 25/25, e2e 2/2 (73 s).

### Offen (Sprint 27+)
- Run-Resume (§10).
- §9-Zielwerte sobald Goldstandard-Material da.

## Sprint 27 (03.11.2026): Run-Resume - Fortsetzungs-Anschluss bei Neustart (Auftrag v2 §10a)

### Neu umgesetzt
- DB: additive Spalte research_sessions.previous_session_id (idempotentes
  ALTER) + get_last_unfinished_session(topic): die zuletzt beendete,
  NICHT abgeschlossene Session eines Themas (resource_limit_reached,
  stopped, error) ist der Fortsetzungs-Anschluss; 'completed' zählt als
  abgeschlossen und löst keinen Anschluss aus.
- Orchestrator-Start: endete die letzte Runde unvollständig, verweist
  die neue Session darauf (previous_session_id), der Status trägt
  resumed_from (session_id/status/zyklen) und der Eröffnungs-Journal-Eintrag
  benennt die Fortsetzung samt übernommener Zyklen. Der Backlog war schon
  über Neustarts hinweg persistent (release_stale + seed), dies macht die
  Kette sichtbar und dokumentiert.
- test_components-Einklang: das Fake-Hypothesen-Item trägt jetzt die
  pruefbaren Felder der §6.3-Aufnahmeprüfung (ein Item ohne
  Falsifizierung bleibt korrekterweise speculative).

### Tests
backlog_work 50/50 (2 neue Resume-Tests + 2 DB-Roundtrip-Tests),
components 130/130, fulltext 39/39, e2e 2/2 (33 s).

### Offen (Sprint 28+)
- §9-Zielwerte sobald Goldstandard-Material im Workspace liegt.

## Goldstandard-Fundus (04.11.2026): Grundlage fuer Auftrags-v2 §9.2 angelegt

### Neu umgesetzt
- data/goldstandard/: README (Verifizierungsregeln), goldstandard.md
  (Referenz-Metaanalysen zum Caffeine/RT-Benchmark mit verbatim-Zitaten),
  goldstandard.csv (7 maschinenlesbare Einträge), pflegeblatt.md
  (Toleranzregeln: Pool-Abweichung PASS bei |Dg| <= 0.15 + CI-Überschneidung,
  Populations-Kontraste ohne Zahlenvergleich).
- Ehrliche Statuskennzeichnung: 4 Einträge agent-geprüft (Verbatim-Quote
  am Original gelesen), 2 agent-Sekundärquelle (Springer-Originale in der
  Recherchesession 403; PMID angegeben), 1 Kontrasteintrag (Schlafentzug,
  explizit kein Normwert). "Menschlich verifiziert" erst nach Abnickung
  durch den Nutzer - bis dahin Warnstempel, kein stiller FAIL: Der
  Benchmark-Harness (Sprint 28) behandelt nicht Verifiziertes informativ.
- Bestes Vergleichsmaß im Fundus: Klove & Petersen 2025, RT
  Hedges' g = 0.28 [0.21, 0.36], k = 31 (PMID 40335666).
- Literatur berichtet fast ausschließlich Hedges's g/SMD, keine
  Millisekunden-Pools - dokumentiert.

### Tests
CSV-Parse-Test (7 Zeilen, Spaltensatz vollständig) + keine
Formatrestentaufe in den Dateien. Kein Produktionscode geändert.

## Sprint 28 (04.11.2026): Benchmark-Runner fuer den Goldstandard-Abgleich (Auftrag v2 §9.2/§9.3)

### Neu umgesetzt
- research_agent/meta/benchmark.py:
  - resolve_benchmark_csv: der Fundus liegt neben der Run-DB
    (data/<name>.db -> data/goldstandard/goldstandard.csv); ohne Fundus
    entfaellt der Berichtsabschnitt schweigend.
  - load_benchmark_entries/_normalize_entry: toleranter CSV-Lesung;
    Zahlen werden auf wert_num/k_num normalisiert, Unlesbares wird None
    (Eintrag bleibt sichtbar, kein stiller Verlust).
  - run_benchmark: laedt study_effects (nur lesend) und baut die
    Analyse ueber build_analysis(rows, outcomes=None); Abgleich pro
    Fundus-Eintrag gegen die gepoolte Hedges'-g-Gruppe per deterministischem
    Alias-Match (Reaktionszeit/Genauigkeit/Erfolgsrate).
  - Toleranzen des Pflegeblatts fest verdrahtet: PASS bei |D g| <= 0.15
    UND CI-Ueberschneidung, grenzwertig <= 0.30, darueber Abweichung.
  - Decken-Warnung (informativ): Lauf-k < Fundus-k wird im
    Ergebnis notiert (publizierte Metaanalyse deckt mehr ab).
  - Ehrlichkeitsregel: Referenzen ohne Status 'menschlich verifiziert'
    erzeugen keinen harten FAIL (hard_fails zaehlt nur verifizierte
    Abweichungen); Ergebnistraeger bekommen den Warnstempel.
  - Zahlensextraktion: Anteil der Zeilen mit Wert, die SE oder CI tragen
    (Extraktionsdeckung); Zeilen ohne Wert zaehlen, werden nicht gepoolt.
  - format_benchmark_lines: Berichtstext (Zaehlungen + Einzelergebnisse).
- research_agent/report.py: neuer Abschnitt 'Goldstandard-Abgleich (§9.2)'
  nach der Meta-Synthese; Fehlschlag nur als logger.debug, der Bericht
  endet nicht am Benchmark.

### Tests
- research_agent/tests/test_benchmark.py (11 Tests): PASS-Grenze mit
  CI-Ueberschneidung, nicht verifizierte Abweichung ohne harten FAIL,
  verifizierte Abweichung zaehlt als harter FAIL, Ergebnis ohne gepoolte
  Gruppe (kein_gepools), Richtungs-Eintrag ohne Zahlenvergleich,
  Extraktionsdeckung zaehlt wertlose Zeilen, Berichtszeilen spiegeln die
  Massstaebe wider, fehlender Fundus = nicht verfuegbar,
  In-Memory-DB ohne Fundusauflauf, Fundus neben DB-Datei wird gefunden,
  toleranter CSV-Parser.
- Suite-Ergebnis: 11/11; danach regression: test_report.py +
  test_meta_report.py 56/56, test_e2e.py 2/2.
- Erster echter Abgleich (readonly) gegen die Kaffee-Runde 972eac:
  7 Fundus-Eintraege - 5x kein gepoolter Wert im Lauf, 2x kein
  Zahlenvergleich; Extraktionsdeckung 0% (2 Zeilen mit Wert, keine mit
  SE/CI). Stimmig mit der Live-Beobachtung (8 Effektzeilen, 7 ohne
  SE/CI) - der Benchmark macht die Luecke maschinenpruefbar.

### Offen
- Referenzwerte von Nutzer abnicken lassen (Status
  'menschlich verifiziert'); bis dahin bleiben alle Fundus-Vergleiche
  informativ mit Warnstempel.

## Sprint 29 (04.11.2026): Vision-Tabellenlesung via TUDaGPT (Auftrag v2 §2.1)

### Was bewiesen wurde (Probe, readonly)
- Endpoint-Analyse: TUDaGPT (tudagpt2.hrz.tu-darmstadt.de/api) listet
  20 Modelle; vision-faehig ist 'hessian.ai/qwen3-vl-30b-a3b-instruct-awq'.
  Basistext-Lauf des Agents ist bereits komplett auf TUDaGPT
  (config.py: llm_backend tudagpt, Key via TUDAGPT_API_KEY aus .env).
- Renderer: PyMuPDF und Pillow scheitern unter msys64 (kein Wheel);
  pypdfium2 + numpy + eigener zlib-PNG-Encoder (kein Pillow noetig)
  rastern funktionierend.
- Ground-Truth-Fixture (table_fixture.pdf): ZWEI unabhaengige Lesungen
  (Temperature 0) lesen Tabelle 2 exakt: -22.3/6.2/[-34.4, -10.2] und
  -14.1/5.0/[-23.9, -4.3] - inklusive SE und CI, d. h. exakt die Deckung,
  die im Live-Run 972eac bei 0% lag.
- Bounding-Boxen: Qwen3-VL liefert Zeilen-Boxes auf 0-1000-Skala
  (bbox_row) - der Lesungsausschnitt ist nachpruefbar (Evidenz-Anker
  fuer Sprint 30).
- Bekannte Macke: das Modell klebt gern alle Zeilen in EIN Objekt mit
  Doppel-Keys (label/effect mehrfach); ein naiver json.loads verloere
  die erste Zeile still. Ebenso faellt Kopf-Lesen ('Caffeine'/'Placebo')
  als zeile ohne Zahlen in der Ausgabe auf.

### Neu umgesetzt
- research_agent/research/vision_table.py:
  - render_pdf_pages: pypdfium2-Rendering + eigener PNG-Encoder
    (png_bytes, zlib-only, kein Pillow).
  - crop_bounds: 0-1000-Box -> Pixel-Grenzen mit 2% Sicherheitsrand.
  - parse_vision_rows: zeilenweiser Regex-Leser, verankert am 'label'-Feld;
    ueberlebt Doppel-Keys UND sauberes JSON; null-Felder bleiben None.
  - rows_equal/compare_double_read: Doppelleitung - Zeilen-Paare muessen
    numerisch identisch sein (tol=0), sonst bleiben sie disputed;
    nichts wird gemittelt, nichts still korrigiert. Zeilen ohne irgendeine
    Zahl (Kopf) fallen weg; halbgelesene Zeilen (eine Zahl, Rest None)
    bleiben disputed.
  - VisionTableReader (aiohttp): read_once + read_double; Key nur im
    Authorization-Header, nie geloggt; HTTP-Fehler -> kein Crash, sauber
    0 Zeilen.
- research_agent/tests/test_vision_table.py (13 Tests): PNG-Kopferhalten
  (Breite/Hoehe bei Byte 16..24), Fixture-Rendering, Doppel-Key-Parsen
  (Probe-Ausschnitt), null-Felder, Kauderwelsch -> 0 Zeilen,
  uebereinstimmende/disputed/ungleiche Zeilenzahlen, Kopfzeilen-Filter,
  0-1000-Box-Mapping mit Rand, HTTP 401/200-Fallback mit Fake-Session.
- Suite-Ergebnis: 13/13.

### Offen (Sprint 30)
- Orchestrator-Integration: Effekt-Work-Item ruft den Reader als
  Fallback, wenn der Textlayer-Weg 0 poolbare Zeilen liefert
  (Moment: _work_item_effect_extraction, orchestrator.py:3479).
- DB-Kontrakt: neue Evidenzart 'vision_table_row' (Bild-Kuerzung mit
  bbox statt nur Quote-Span); Verbatim-Vertrag wird ERWEITERT, nicht
  umgeben - unuebereinstimmende Doppelleitungen werden nie gepoolt.
- Modellschritt downdaten (config tudagpt_model nominell Textmodell;
  Vision-Lesung nutzt konstant VISION_MODEL).
- Beweis: Testlauf mit Extraktionsdeckung > 0%, weiterhin der
  Benchmark gegen den Goldstandard-Fundus.

## Sprint 30 (05.11.2026): Verbatim-Vertrag fuer Bild-Evidenz + Vision-Fallback im Orchestrator (Auftrag v2 §2.1)

**Problem.** Die Doppel-Lesung der Sprint-29-Vision-Tabellenlesung lief als Modul,
aber der Verbatim-Vertrag prueft Zitate gegen den Textlayer - eine Bildlesung
hat keinen Textzitat-Span und waere falschlich als "unbelegt" geendet.
Zugleich fehlte die Anbindung in der Extracting-Phase des Orchestrators und der
Bericht wies die Evidenzart nicht aus.

**Loesung (3 Ebenen).**
1. Definierte Normalisierung statt numerischer Toleranz:
   `normalise_number_text()` in research/vision_table.py - Unicode-Minus
   (U+2212 -> ASCII), Dezimalkomma -> Punkt (bewusst ohne Tausender-
   heuristik), Whitespace vereinzelt, ± ohne Umgebungsleerzeichen. Der
   Doppelleitungs-Vergleich (rows_equal) laeuft STRENG ueber die Rohlesungen
   ("raw_effect" a. s. f.), nie mit numerischer Toleranz: 0,58 vs 0,53 bleibt
   disputed; "0,53" vs "0.53" ist verified. Zeilen ohne Rohlesung (handge-
   baute Fixtures) fallen auf strikte Float-Gleichheit zurueck. Promptversion
   ist Belegbestandteil: PROMPT_VERSION = "vision_table/2".
2. Datenmodell + DB: StudyEffect.evidence_kind ("text_verbatim" | "vision_read"),
   vision_status ("verified" | "disputed"), vision_meta = Belegkette (pdf_hash,
   crop_hash, page, dpi, model, prompt_version, bbox_row, page_status) als JSON
   - SQLite-Migrationen sind additiv (ALTER TABLE, idempotent) an
   study_effects (evidence_kind/vision_status/vision_meta) und an
   facts.evidence_kind.
3. Verdrahtung: read_table_evidence() baut als async das Evidenz-Aggregat mit
   Hashes und Status; der Orchestrator (`_work_item_effect_extraction`) ruft
   `_vision_fallback_effects()` NUR wenn der Text-Layer keine Effektzeilen
   liefert und die Original-PDF vorliegt: rasterisiert die Seiten
   (pypdfium2, max 12/run), liest doppelt, speichert Zeilen mit
   evidence_kind/vision_status/vision_meta und quote = Zellstring aus den
   Rohlesungen (label | effect | SE ... | [low;high]).

**Gates** (alle deterministisch, kein LLM):
- meta/pooling.standardize: eine vision_read-Zeile ist nur poolbar bei
  vision_status == "verified"; disputed/leer -> nicht poolbar (niemals
  Mittelung, niemals "bessere Lesung" gewaehlt). quote_start = -1 ist fuer
  vision_read erwartbar und kein Mangel; text_verbatim-Zeilen fallen
  unverandert auf den Zitat-Span-Check.
- meta/validation._verify_effect_quotes: vision-Zeilen werden NICHT als
  "unbelegt" gewertet; statt dessen: poolbare Zeile ohne verified ->
  Blocker "vision_poolable_without_verified"; Zeile ohne Status -> Warnung
  "vision_row_without_status"; text_verbatim unverändert.

**23 neue Tests** (test_sprint30_vision.py): Ziffernverwechslung bleibt
disputed; "-.53" vs "-0.53" bleibt disputed (streng); halbgelesene Zeilen
(Wert + Rohlesung fehlend) bleiben disputed - auch wenn BEIDE Lesungen
dasselbe Feld verlieren; Belegkette komplett (Hashes, page, dpi, model,
prompt_version); Pooling- und Validierungsbeschluesse je vision_status.
103 Tests in den betroffenen Suiten gruen (test_sprint30 23 +
vision_table 13 + meta_pooling + validation).
meta_pooling + validation).

**Grenzen (bewusst nicht geloest):** Ein Zellstring-Quote ist als
Rohlesung gespeichert, aber gegen keine dritte Quelle (Textlayer) geprueft
- der Zusatzpruefungspfad (Textlayer vorhanden -> dritte Gegenprobe,
Abweichung -> disputed) steht offen. Der "beide Lesungen falsch identisch"-
Fall ist durch die Doppel-Lesung allein nicht abfangbar (fehlerkorreliert)
- Vorschlag: Leserstaffelung (z. B. Ganzseite vs Crop) fuer die
zweite Lesung.


## Sprint 30 restend (05.11.2026): Textlayer-Gegenprobe fuer Vision-Zeilen

Dritte Pruef quelle (Claude-Vorschlag, Rueckstand aus den Grenzen): Hat
die PDF eine Textebene, prueft sie die Doppelleitung nach. Die Gegenprobe
liest NACH definition arbeite Normalisierung die Rohlesungen (effect,
se) und sucht jede Zahl WORDBOUND im klaren Normalisierten dokumenttext:
Teilzeichensuche (0.53 in 0.532) ist KEIN Treffer. Fehlt eine Zahl,
steht die Zeile disputed - nicht mitteln, nicht still korrigiert; die
fehlenden Felder stehen in _text_layer_check nachklaerbar. Bereits
disputed Zeilen bekommen KEINE gute Schrift - disputed bleibt disputed.

Suchseiten-Regel: '- 0.53' im Fliesstext ist dasselbe Minus wie '-0.53'
in einer Zelle (nur fuer die Suche, nicht fuer den Zeilenvergleich).

7 neue Tests (test_text_layer_check.py): Genau-Treffer, Ziffern-
fehler -> disputed, Teilzeichenkette kein Treffer, disputed bleibt,
leerer Text passierbar, U+2212 normalisiert. 46 Vision-Suiten gruen.
Verdrahtet im orchestrator `_vision_fallback_effects` (lokal): Gegen-
probe laeuft nur bei page_status='verified' und vorhandenem Text;
Abweichung dreht page_status auf disputed.


## Sprint 31 (05.11.2026): Windows-Job-Object-Sandbox fuer Simulationskinder

**Lieferumfang:** research_agent/experiments/win_job.py — Job-Object via
ctypes (kernel32, kein pywin32): PROCESS_MEMORY-LIMIT + KILL_ON_JOB_CLOSE.
attach_job_limits haengt den Kindprozess ein; auf Nicht-Windows stummer
No-op (Rueckgabe False), im Runner ehrlich geloggt statt still.
runner.py: create_subprocess_shell -> Popen + attach vor dem Timeout.

**Fundierter Befund (Hanger-Diagnose):** Das erste DEFAULT von 2048 MB
blockierte numpy/OpenBLAS-Importe im bereits-kommitierten Job-Limit
(2-GB-Probe haengt nach 20 s, 4-GB- und 8-GB-Probe laufen in 0,2 s,
Kill-on-Close-only ohne Memory-Limit laeuft auch). Default jetzt 4096
MB, ueberschrieben mit SIM_MEM_MB.

**Tests:** test_win_job.py (Speicherfresser vom Limit gestoppt, normaler
Prozess laeuft; Windows-only-Faelle skippen auf Plattformen ohne Job-
Objekte). Ohne Sandbox-Namen: die Import-Allowlist im Sandbox-Wrapper
bleibt die erste Schicht; Job-Limits nur zweite Schicht auf Windows.

**Ergebnis:** test_simulations.py 53/53 (vorher 6 Failed mit
'smoke test failed: timeout'), Sandbox-Suiten gruen; Fokus-Lauf
185 passed, 2 skipped (test_simulations + test_win_job +
test_components). Commits 81ee6f8 + d05f46e (Briefing-Satz), gepusht.

## Sprint 32 (18.11.2026): Table Decomposition & Reconstruction Engine

**Lieferumfang:** neues Paket `research_agent/table_decomposition/` (model.py,
parser.py, semantics.py, complexity.py, crops.py, strategies.py, backend.py,
reconstruct.py, validation.py, engine.py). Zerlegt wissenschaftliche Tabellen in
kontextbewahrende Einheiten (Verfahren A Full-Table, B Vertical, C Horizontal,
D Bidirectional, E Adaptive Recursive mit Nachlese nur fuer unbelegte oder
konfliktiaere Zellen), extrahiert je Einheit ueber ein modellunabhaengiges
Backend-Protocol und setzt die Teilresultate zu einer Tabelle zusammen
(agreed/single/conflict, Konflikte werden nie ueberschrieben). Jede Zelle bleibt
ueber table_id, doc_id, row/col, Seite, Einheit, Verfahren, Richtung, Modell und
Zitat zurueckfuehrbar. Aktivierung optional via `table_decomposition: true`
(Konfiguration oder `TABLE_DECOMPOSITION`), Pipeline-Haken
`augment_prompt_text` haengt strukturierte Tabellenansichten an, ohne den
Originaltext zu veraendern. Keine geschuetzte Kerndatei angefasst.

**Befund (Parser):** zwei echte Defekte gefunden und behoben. (1) Header-Spannen
ueberlappten, wenn Gruppenkoepfe um eine Spalte versetzt sind - jetzt
Deduplizierung doppelter Blattanker plus gleichmaessige Teilung, Nicht-Teilbares
wird als Irregularitaet markiert. (2) Fuehrende Labelspalten mit Ziffern
("Visit 5:", "5 min") wurden als Datenspalten gelesen; neu entscheidet neben der
Ziffernquote auch die Nicht-Lesbarkeit als Zahl bei leerem Kopf. Damit
verschwinden 395 Warnungen `zeilenlabel_fehlt` je Lauf.

**Benchmark:** `public_benchmark/extended_benchmark/table_decomposition/`
(select_tables, run_benchmark, evaluate, report). Kandidat ist ein Paar
(Record, Tabelle); Auswahl nur nach Struktur (Anzahl belegter Zielspalten,
Hash), geschichtet, mit Dokument- und Record-Deckel, eingefroren mit
`records_sha256`. Test: 60 Tabellen aus 537 Kandidaten (58 Records, 31
Dokumente). Offline gemessen: strukturell 60/60 komplett fuer alle Verfahren,
0 Fehler; Aufwand gegenueber A 1,62x (B), 3,95x (C), 4,83x (D), 3,12x (E).
Armzuordnung ist der Engpass: nur 76 von 268 Goldzellen (28,4 %) sind ueber eine
ausgewaehlte Tabelle erreichbar, mit Reihenfolge-Annahme 84 (31,3 %).

**Tests:** `research_agent/tests/test_table_decomposition.py` (30) plus
`public_benchmark/tests/test_table_decomposition_benchmark.py` (4) - 34 gruen.

**Nicht gemacht:** Modelllauf (Precision/Recall/Kosten). Er braucht
ausdrueckliche Freigabe und Guthaben; `run_benchmark.py` verlangt dafuer
`--allow-network` und `--confirm-kosten`.

## Sprint 33 (18.11.2026): Reichweite des Tabellenpfads gemessen und gehoben

**Anlass:** Sprint 32 liess offen, warum nur 76 von 268 Goldzellen ueber eine
ausgewaehlte Tabelle erreichbar waren. Vor einem kostenpflichtigen Modelllauf
wurde dieser Deckel zuerst ohne Netzzugriff untersucht.

**Diagnose:** neues Werkzeug `diagnose_reachability.py` klassifiziert jede nicht
erreichbare Goldzelle (read-only, ohne Goldwerte als Eingabe). Befund vor dem
Umbau: 104 Zellen ohne passende Spalte im Dokument, 48 ohne Armbeleg im Kopf,
40 in nicht ausgewaehlten Tabellen.

**Aenderungen:** (1) `transfer_arms_within_document` belegt einen Arm aus einer
Schwestertabelle desselben Dokuments, wenn der Gruppenkopf identisch ist
(`arm_basis="uebertrag"`, Befund `armzuordnung_uebertragen`). (2) Verbundwerte:
`12.4 (3.1)` wird gelesen - erster Wert als Zellwert, zweiter als eigener Beleg
mit derselben Fundstelle (`secondary_role`, `derived`, Befund
`verbundwert_getrennt`); vorher lehnte `parse_value` die ganze Zelle ab. (3)
Auswahl nach Feldabdeckung: bis zu 6 Tabellen je Record, aber nur solche mit
neuem Feld; Kandidatenzahl 537 -> 608. (4) Labelspalten-Heuristik verschaerft
(Dezimalzahl oder zwei Zahlen je Zelle gelten als Messwert), damit
Verbundspalten nicht als Labels gelten.

**Ergebnis:** erreichbar 76/268 (28,4 %) -> 95/278 (34,2 %), mit
Reihenfolge-Annahme 99 (35,6 %). Aufwand gegenueber Full-Table 1,86x (B), 3,92x
(C), 5,20x (D), 3,49x (E); alle 60 Tabellen strukturell vollstaendig, 0 Fehler.
Der Arm-Transfer allein bringt +3 Zellen (identische Labels binden meist schon
ueber die Kopfregel) - er bleibt, weil belegbar und kostenlos.

**Tests:** 32 Engine-Tests (2 neu: Verbundwert mit Zweitbeleg, Arm-Transfer mit
Provenienz) plus 4 Benchmark-Tests - 36 gruen.

**Nicht gemacht:** Modelllauf. Die 34-%-Obergrenze des Tabellenpfads ist jetzt
bekannt und begrenzt den erwartbaren Recall-Gewinn.

## Sprint 34 (18.11.2026): Erwartete Zellen berichtigt (Kopf, Gruppengroesse, Outcome-Zeile)

**Anlass:** Der Pilotlauf mit GLM-5.3 lieferte 0 richtige von 12 erwarteten
Zellen. Ursache war nicht das Modell, sondern der Erwartungswert: Kopfzeilen
waren falsch zusammengesetzt, `n = 434` wurde zur Spaltenrolle, und erwartet
wurden Zellen aller Zeilen statt der Outcome-Zeile.

**Aenderungen (ohne Netzlauf):** (1) Vergleichszeilen wie `Basic vs control`
gelten nicht mehr als Spaltenkopf (`kopfzeile_ist_zeilenlabel`); fette
Zeilengruppen beenden die Tabelle nicht mehr und bilden den Label-Pfad
(`Row.label_path`, Tiefe aus der Spalte des Gruppenlabels). (2) `n = 456` ist
Kopf-Fakt (`Table.header_facts`, Wert/Spanne/Arm) und keine Spaltenrolle `n`
mehr; reine Kopfangaben fallen aus Header-Pfad und Rollenbestimmung heraus.
(3) `semantics.outcome_rows` + `reachable_cells` definieren erwartbare Zellen
als Spaltenfeld **und** Outcome-Zeile; `PlanOptions.focus_outcome` begrenzt den
Auftrag darauf (Standard aus, produktive Pipeline unveraendert). Die
Validierung unterscheidet jetzt Zellen ausserhalb der Zeilen (`cells_outside_rows`).

**Beleg:** `PMC4319071:T1` 1 -> 30 gelesene Zeilen (10 Gruppenzeilen), 3 -> 0
Kopf-Baender mit `vs`, 3 -> 0 Spalten mit Rolle `n`, Kopf-Fakten 1349/434/459/456
(434 als comparator gebunden, 456 ohne Armbeleg, weil der Record `Plus` nicht
nennt). Testsplit: erreichbar 95/278 -> 21/278, jetzt zeilengenau; 60/60
Tabellen strukturell vollstaendig, 0 Fehler; Tokens A 84.733 -> 90.872,
B 157.828 -> 148.523, E 295.279 -> 268.059 (Schaetzung Zeichen/4).
Verbleibende Luecke: 29 Records ohne erkannte Outcome-Zeile (Abkuerzungen wie
`IP-10`), 8 mit falsch ausgewaehlter Tabelle, 10 ohne Tabelle im Dokument.

**Tests:** 38 Engine-Tests (6 neu: Vergleichszeile, Kopf-Fakt, Gruppenpfad,
Reichweite je Zeile, fokussierter Plan) plus 4 Benchmark-Tests - 42 gruen.

**Nicht gemacht:** Modelllauf (Freigabe offen), Neueinfrierung der Auswahl,
Rollen aus Zeilenlabels (deshalb weiterhin 0 Zellen fuer `PMC4319071:T1`).
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/erwartete_zellen_20261118.md`.

## Sprint 35 (18.11.2026): Matcher auf dev geprueft, Kopf-Fakten extrahierbar

**Anlass:** Der Outcome-Zeilen-Matcher war nur am Testsplit gemessen; ausserdem
waren Kopfangaben wie `n = 434` zwar als Fakt gefuehrt, aber nicht als Wert
lesbar.

**Aenderungen:** (1) `Reconstruction.add_header_facts` uebernimmt jede
Kopfangabe mit belegtem Arm als Beleg ohne Modellaufruf (Adresse
`(-1, col_start)`, `origin="kopf_fakt"`, Rohwert = Kopftext); `by_address`
bleibt zellbasiert, die Validierung meldet `gruppengroesse_aus_kopf`.
(2) `reachable_cells` zaehlt solche Fakten als erwartbar, unabhaengig von der
Outcome-Zeile. (3) Neues read-only Werkzeug `pruefe_outcome_matching.py`
(`--selection` oder `--all-records --role dev`) klassifiziert die Matcher-Treffer
je Record und schreibt nur die angeforderte JSON-Datei.

**Beleg:** `PMC4319071:T1` liefert jetzt `comparator_group_size = 434` mit
Rohwert `n=434` und `row_id = -1`; `n=456` bleibt ohne Arm (der Record nennt
`Plus` nicht). Dev (alle 38 Records mit Gold, 8 Dokumente): 3 `trifft`, 11
`zeile_nicht_erkannt`, 24 `dokument_ohne_zeile`; 35 Kopfangaben, 18 mit Arm,
6 Gold-Gruppengroessen dadurch erwartbar. Dev-Auswahl offline: 5 von 10
Goldzellen erreichbar (4 davon aus Kopfangaben), Tokens A 7.922 / B 10.866 /
E 29.169, 6/6 Tabellen vollstaendig.

**Testsplit:** nicht neu gemessen, keine Datei angefasst. Hashes von
`selection_test.json`, `offline_struktur_20261118/structure.json`,
`offline_fokus_20261118/structure.json` und `erwartete_zellen_20261118.md`
vorher/nachher identisch; `git status` fuer diese Pfade leer.

**Tests:** 39 Engine- plus 4 Benchmark-Tests - 43 gruen.
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/dev_pruefung_20261118.md`.

## Sprint 36 (18.11.2026): Spaltenrollen aus dem Zeilenlabel - ohne Gewinn belegt

**Anlass:** Tabellen wie `PMC4319071:T1` nennen die Rolle im Zeilenlabel
(`Mean (SD)`, `n (%)`), nicht im Spaltenkopf (`Control`, `Plus`).

**Aenderungen:** `semantics.row_roles` leitet Rolle und Zweitrolle aus dem
Zeilenlabel ab (`Row.value_role`/`secondary_role`); `row_fields` und
`Reconstruction._resolve_field` nutzen sie nur, wenn die Spalte die Rolle
`unknown` hat, und nur bei vorhandener Zelle. `_add_secondary` nimmt die
Zweitrolle aus Spaltenkopf oder Zeilenlabel; die Validierung meldet
`rolle_aus_zeilenlabel`. Tests: 2 neu, 45 gruen.

**Offline-Ergebnis (ehrlich negativ):** `PMC4319071:T1` hat 9 Zeilenrollen
(5x mean, 4x events), Fokus `[19, 20]` - erwartbar bleibt nur
`comparator_group_size`. Grund: die Wertspalten liegen nicht unter den
Armkoepfen (erstes Zahlzeichen in Zeile 13 bei x=98, in Zeile 19 bei x=120 bei
denselben Regelspalten), und `Plus` ist im Record nicht benannt. Die
Gold-Mittelwerte `158.67`/`167.61` stehen in `PMC4319071:T2` (Zeilen 107/113),
wo die **Arme Zeilenlabels** sind und der Kopf nur `Mean (SE)` traegt; T2 hat 0
Zeilenrollen und 0 Armspalten. Auf dev (38 Records): 12 Tabellen mit
Zeilenrolle, 1 mit Armspalte ohne Rolle, **0** Records mit Gewinn; dev-Messung
5/10 unveraendert. Testsplit nicht neu gemessen, Artefakt-Hashes gleich.

**Naechster Hebel (belegt):** Arm aus dem Zeilenlabel plus Outcome-Spalte aus
dem Kopf fuer Tabellen mit Armen als Zeilen, dazu ein Prosa-Guard fuer
Kopfzeilen mit vielen Woertern (Zeile 81 in `PMC4319071`).
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/zeilenrollen_20261118.md`.

## Sprint 37 (18.11.2026): Arme als Zeilen, Outcome als Spalte

**Anlass:** `PMC4319071` fuehrt die Arme als Zeilen (`Control`, `Basic`, `Plus`)
und die Outcomes als Spalten; der Kopf nennt `Vegetables (grams)`, aber keine
Rolle. Die Gold-Mittelwerte stehen in `T2` (Zeilen 107/113).

**Aenderungen:** Prosa-Guard nimmt Kopfzeilen aus kurzen Zellen nicht mehr als
Prosa (`_looks_prose`); `bind_row_arm` bindet den Arm aus dem Zeilenlabel
(Schwelle 0.6, dritter Arm bleibt frei); `_mark_outcome_columns` erkennt die
Outcome-Spalte im Kopf (nur Vorwaertsrichtung, Mehrdeutigkeit wird notiert) und
verweigert die Zuordnung ohne belegte Kopfspanne (`header_geometry_trustworthy`);
`(SE)`/`(95% CI)` erzeugen keine Standardabweichung; Rekonstruktion, Reichweite
und Validierung (`arm_aus_zeilenlabel`) nutzen dieselbe Regel. Tests: 4 neu, 49
gruen.

**dev-Ergebnis:** 134 Tabellen unveraendert; erreichbare Goldfelder 12 -> 16,
alles in `yun2024:5` (`PMC1216327:T5`, Arme als Zeilen); die gelesenen Werte
3.59/2.35 (Intervention) und 2.19/1.63 (Comparator) stimmen exakt mit dem Gold.
Der Prosa-Fix allein ist auf dev neutral (12), weil die betroffenen dev-Tabellen
ihren Kopf schon hatten.

**Ehrlich negativ fuer das Zielobjekt:** `PMC4319071:T2` bekommt seine
Outcome-Kopfzeile zurueck, aber Kopf und Strichraster sind um eine Spalte
verschoben (Kopf `Vegetables (grams)` bei x=43, Wert `158.93` rechtsbuendig bei
x=93; 10 Strichspalten gegen 5 Kopfzellen). Deshalb
`outcome_spalte_ohne_kopfgeometrie` statt einer geratenen Zuordnung; `T2` traegt
nichts bei, `T1` weiter nur `comparator_group_size`.

**Naechster Hebel:** Kopfzellen an den Datenzellen ankern (rechtsbuendige Werte,
Zellende = Spaltenende) statt am Strichraster; danach `T2` erneut pruefen, dann
Pilotlauf und neue Auswahl-Einfrierung.
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/zeilenarme_20261118.md`.

## Sprint 38 (18.11.2026): Kopfebenen folgen den Wertspalten

**Anlass:** `PMC4319071:T2` war nach dem Prosa-Fix strukturell lesbar, die
Zuordnung wurde aber verweigert, weil Kopf und Strichraster um eine Spalte
versetzt sind.

**Messung:** Die Annahme "rechtsbuendige Werte, Zellende = Spaltenende" traegt
nicht: `158.93 (3.31)` beginnt bei x=93 (Ende von Spalte 3) und laeuft bis 105;
`Vegetables (grams)` steht bei x=43 (Anfang von Spalte 2); die Datenzeilen
streuen um 1-3 Zeichen. Positional ist die Tabelle nicht aufloesbar.

**Aenderung:** `parser._reassign_header_bands_by_order` ordnet die Kopfebenen
ordinal den Wertspalten zu - nur bei bereits notierter, unaufloesbarer
Kopfgeometrie. Zellen und Spalten bleiben unveraendert; nicht aufgehende Ebenen
werden als `kopf_ebene_ohne_spalte` notiert, die Notfall-Codes durch
`spalten_ordnung:kopf_nach_wertspalten` ersetzt. Test: 1 neu, 50 gruen.

**Ergebnis:** `PMC4319071:T2` liefert `comparator_mean` mit der Zelle
`158.67 (3.76)` (`yun2024:112`) bzw. `2.84 (0.13)` (`yun2024:111`) - beide
exakt Gold. dev unveraendert: 134 Tabellen, 16 erreichbare Goldfelder, 5
Records mit Treffer, eine Tabelle (`PMC3751573:T3`) neu geordnet, kein Verlust.
Interventionsarm bleibt offen, weil `Plus` im Record nicht benannt ist.

**Naechster Hebel:** Armnamen aus dem Dokument belegen (`Basic`/`Plus` stehen in
`T1`-Kopf und `T2`-Zeilen) und als `arm_basis="dokument"` markieren.
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/kopf_ordnung_20261118.md`.

## Sprint 39 (18.11.2026): Interventionsarm aus der Dokumentdefinition

**Anlass:** `PMC4319071` nennt im Record nur `Intervention + targeting
environmental-level factors`; der Armname `Plus` steht nur in der Tabelle.

**Beleg:** Das Abstract definiert `basic (…; n=456)`, `plus (basic intervention
additionally targeting environmental-level factors; n=459)` und `control (…;
n=434)`. Die Plus-Definition deckt den Record-Interventionsarm vollstaendig
(4/4 Tokens), die Basic-Definition nur `targeting` (0.25, unter der Schwelle).

**Aenderung:** `document_arm_definitions` und `transfer_arms_from_document`
setzen den Arm mit `arm_basis="dokument"` an **Zeilenlabels**; eingebunden in
Engine und den drei Benchmark-Werkzeugen. Spaltenkoepfe bleiben bewusst aussen
vor: in `T1` traegt die Spalte unter `Plus` den Control-Wert (157.73), ein
Spaltenarm erzeugte drei falsche Felder. Test: 1 neu, 51 gruen.

**Ergebnis:** Von den vier offenen Goldfeldern werden zwei erreichbar - die
beiden Interventionsmittelwerte (`167.61` in `T2` Zeile 16 / Spalte 4 fuer
`yun2024:112`, `2.50` fuer `yun2024:111`), jeweils exakt Gold. Die beiden
Gold-Streuungen (83.71, 2.76) stehen nicht im Dokument (`83.71` 0 Treffer,
`2.76` nur als Teil von `72.76`), die Tabellen drucken `Mean (SE)`. dev
unveraendert: 11 Dokumente mit Definitionen, 0 gebundene Zeilenarme, 16
erreichbare Goldfelder, 5 Records mit Treffer.

**Naechster Hebel:** Auswahlregel "eine Tabelle je Outcome und Zeitpunkt" -
`T4` liefert dieselben Felder mit anderen Werten (143.25 statt 158.67).
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/dokumentarm_20261118.md`.

## Sprint 40 - Auswahlregel: eine Tabelle je Outcome und Zeitpunkt

**Beleg:** `PMC4319071` druckt dieselben Felder zweimal - `T2`
(Gesamtstichprobe, `158.67`) und `T4` (Risikogruppen `n=803`/`n=1014`,
`143.25`). Zwei Kandidaten je Feld kosten Precision.

**Aenderung:** `semantics.primary_tables` waehlt je normalisierter
Zeitpunktmenge die erste gedruckte Tabelle (`table.index`), aber nur wenn sie
die Felder der uebrigen abdeckt; sonst bleiben alle stehen. Kandidaten sind
nur Tabellen mit Zeitpunkt-Gruppen und mindestens einem Outcome-Feld aus
`reachable_cells` (nicht `reachable_fields`: damit verdraengte die
Baseline-Tabelle in `PMC1216327` die Ergebnistabelle `T5`, dev 16 -> 12
Felder, gemessen und verworfen). `Table.redundant_of` haelt die Entscheidung
fest; Engine und `run_benchmark.load_tables` ueberspringen verdraengte
Tabellen, ein ausdruecklicher `table_ids`-Satz gewinnt. `load_tables` gibt die
verdraengten IDs als dritten Wert zurueck, damit kein Lauf eine Auswahl still
verkleinert. Test: 1 neu, 52 gruen.

**Ergebnis:** `PMC4319071:T4` faellt hinter `T2` zurueck, beide Records ohne
Feldverlust (`comparator_mean`, `intervention_mean`,
`comparator_group_size` unveraendert erreichbar). dev unveraendert: 38
Records, 0 Rueckfaelle, 16 erreichbare Goldfelder, 5 Records mit Treffer. Auf
der eingefrorenen Testauswahl ist die Regel wirkungslos (je Record genau eine
Tabelle, A/B identisch, 0 verdraengt).

**Nebenbefund:** `offline_struktur_20261118/structure.json` stammt aus
`ac3b4c9` (95 erreichbare Goldfelder); der aktuelle Code liefert 46, unabhaengig
von dieser Regel. Das Artefakt ist vor dem naechsten Zitat neu zu erzeugen.
Bericht: `public_benchmark/extended_benchmark/analysis/table_decomposition_20261118/auswahl_20261118.md`.
