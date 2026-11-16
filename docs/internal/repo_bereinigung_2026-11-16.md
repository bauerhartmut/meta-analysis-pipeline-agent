# Repo-Bereinigung 2026-11-16

## Ziel

Der öffentliche Stand von `origin/master` soll keine privaten Unterlagen, keine
vollständige A-Annotation, keine nicht lizenzierten Verlags- oder
Dritt-Datensätze und keine internen Binärartefakte mehr enthalten.

## Methode

Die Dateien werden mit `git rm --cached` aus dem Repository entfernt. Die
lokalen Kopien bleiben erhalten; sie werden nur nicht mehr versioniert. Die
anschließenden `.gitignore`-Regeln verhindern ein versehentliches erneutes
Hinzufügen.

## Entfernte Dateien (71)

### Private und externe Unterlagen (4)

- `docs/external/ingendahl_2026-11-16/01_projektkurzbeschreibung.md`
- `docs/external/ingendahl_2026-11-16/02_beispielannotation.md`
- `docs/external/ingendahl_2026-11-16/03_annotationsanleitung_v1.2.md`
- `docs/external/ingendahl_2026-11-16/antwortentwurf.md`

### A-Annotation (1)

- `data/golden_effects/goldstandard_A.json`

### A-Ableitungen mit konkreten Effektwerten oder Zeilenzahlen (14)

- `data/golden_effects/example_annotation.json`
- `data/golden_effects/abgleich_trockenlauf.json`
- `data/golden_effects/abgleich_pipeline.json`
- `data/golden_effects/kalibrierung_klaerung_09843.json`
- `data/golden_effects/kalibrierung_pruefpunkte.json`
- `data/golden_effects/kalibrierung_tabellenpruefung_09843_2c7ab.json`
- `data/golden_effects/probelauf_eignung.json`
- `docs/internal/kalibrierung_pruefpunkte_20261110.md`
- `docs/internal/kalibrierung_tabellenpruefung_09843_2c7ab.md`
- `docs/internal/vollannotation_abgabe_checkliste_20261110.md`
- `docs/internal/probelauf_abgabe_checkliste_20261110.md`
- `docs/internal/goldstandard_entscheidung_3790c91f96.md`
- `docs/internal/goldstandard_entscheidung_5cbf.md`
- `docs/internal/probelauf_eignung_20261110.md`

`example_annotation.json` enthält eine exakte A-Effektzeile für `203c...`
(HR 0,83, 95-%-KI, Zitat). `abgleich_trockenlauf.json` übernimmt genau diese
Zeile als `gold_effect`. Die Kalibrierungsdateien und Checklisten nennen
konkrete A-Zeilen, Effektwerte oder Zeilenzahlen pro Dokument.
`abgleich_pipeline.json` enthält aktuell nur `gold: 0`, nennt aber A als
Goldquelle und ist ein A-abgeleitetes, veraltetes Vergleichsartefakt; es wird
deshalb ebenfalls nicht weiter versioniert.

### Verlags- und Dritttexte (38)

- `scripts/sd_test.html`
- `data/bench/sol2/abstracts_b_20261108.xml`

PMC-Volltext-XML, 13 Dateien:

- `data/bench/sol/xml_fetch_ncbi/PMC10025070.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC1370968.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC1490287.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC2982730.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC3014244.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC4425994.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC4734949.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC6535156.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC7163627.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC8094738.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC8181734.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC8959415.xml`
- `data/bench/sol/xml_fetch_ncbi/PMC9554922.xml`

PMC-Volltext-XML, 23 Dateien:

- `data/bench/sol/xml_q1/PMC10024317.xml`
- `data/bench/sol/xml_q1/PMC10131443.xml`
- `data/bench/sol/xml_q1/PMC10149792.xml`
- `data/bench/sol/xml_q1/PMC10796483.xml`
- `data/bench/sol/xml_q1/PMC11123999.xml`
- `data/bench/sol/xml_q1/PMC11137944.xml`
- `data/bench/sol/xml_q1/PMC11801451.xml`
- `data/bench/sol/xml_q1/PMC12002473.xml`
- `data/bench/sol/xml_q1/PMC12394315.xml`
- `data/bench/sol/xml_q1/PMC12449008.xml`
- `data/bench/sol/xml_q1/PMC13095836.xml`
- `data/bench/sol/xml_q1/PMC13373100.xml`
- `data/bench/sol/xml_q1/PMC13454318.xml`
- `data/bench/sol/xml_q1/PMC13625438.xml`
- `data/bench/sol/xml_q1/PMC4319556.xml`
- `data/bench/sol/xml_q1/PMC5958333.xml`
- `data/bench/sol/xml_q1/PMC6302692.xml`
- `data/bench/sol/xml_q1/PMC6306655.xml`
- `data/bench/sol/xml_q1/PMC7647758.xml`
- `data/bench/sol/xml_q1/PMC8663735.xml`
- `data/bench/sol/xml_q1/PMC9456584.xml`
- `data/bench/sol/xml_q1/PMC9519126.xml`
- `data/bench/sol/xml_q1/PMC9819026.xml`

### Third-Party-Daten ohne ausreichende Lizenz (7)

- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/pico_corpus_v1/original/pico_corpus_main.zip`
- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/pico_corpus_v1/records.jsonl`
- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/eururology_v1/original/prompt1_chatgpt.xlsx`
- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/eururology_v1/original/prompt1_claude.xlsx`
- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/eururology_v1/original/prompt2_chatgpt.xlsx`
- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/eururology_v1/original/prompt2_claude.xlsx`
- `public_benchmark/evaluation/multi_model_cross_validation/goldstandard_datasets/eururology_v1/records.jsonl`

Die zugehörigen `manifest.json`-Dateien bleiben als Quellen- und
Lizenznachweis im Repository.

### Interne Binärartefakte (7)

- `ENTWICKLUNGSAUFTRAG_v2.pdf`
- `docs/briefing_modell_20261107.pdf`
- `data/bench/probleme_und_offene_fragen_20261105.pdf`
- `data/bench/sol/ergebnisstand_20261108.pdf`
- `data/bench/validierung/browser_meta_full_20261109.png`
- `data/bench/validierung/browser_meta_sichtbar_20261109.png`
- `data/bench/validierung/dashboard_gate_20261108.png`

## Bewusst nicht entfernt

- `data/golden_effects/kalibrierung_arbeitsblatt.json` und
  `data/golden_effects/vollannotation_arbeitsblaetter.json`: Arbeitsblatt-
  Metadaten und Effektstellen, keine A-Zeilen oder A-Entscheidungen.
- Statusnotizen mit aggregierten A-Zahlen (69 Zeilen, 13 Begründungen):
  Sie verraten keine per-Dokument-Antworten, bleiben aber ein Hinweis auf den
  Umfang. Bei strenger Blindheit sind auch sie zu entfernen.
- `data/golden_effects/blind_b_20261110/`: das B-Paket mit leerem B-Gerüst,
  Anleitung, Schema und Arbeitsblättern. Es enthält keine A-Annotation.
- `public_benchmark/.../glass_v1/`: Die Labels sind MIT-lizenziert; die
  Artikelrechte sind davon getrennt. Kein Roh-Volltext.
- `docs/internal/`-Textnotizen: keine vollständige A-Annotation und keine
  Zugangsdaten. Sie bleiben vorerst, sind aber weiterhin interne Arbeitsnotizen.
- `.env.example`: nur Variablennamen und Platzhalter, keine Secrets.

## Git-History

Das Entfernen aus dem aktuellen Commit löscht die Dateien **nicht** aus der
Git-History. Insbesondere `goldstandard_A.json`, die externe Korrespondenz und
die A-Beispielzeile waren bereits öffentlich. Ein echter Purge benötigt
History-Rewrite und Force-Push und ist nach den Projektregeln nicht erlaubt.
Für die B-Blindheit bleibt deshalb die wichtigste Konsequenz: Repository privat
stellen oder B neu bewerten.

## Optionen für die veröffentlichte History

1. **Repository privat stellen** — sofort wirksam, kein Rewrite, keine
   Zustimmung Dritter. Bestehende Klone, Forks und GitHub-Caches werden nicht
   bereinigt; für B ist A damit trotzdem nicht wieder blind.
2. **Neues öffentliches Repository mit sauberem Root-Commit** — alten Stand
   archivieren oder löschen, neuen Baum ohne History veröffentlichen. Kein
   Force-Push, aber die alte History bleibt bis zur Löschung des alten Repos
   öffentlich; vorhandene Klone bleiben.
3. **GitHub Support um Löschung bitten** — für sensible Daten oder
   urheberrechtlich geschützte Inhalte (ggf. DMCA). Erfolg ist nicht
   garantiert und deckt nicht automatisch die A-Annotation ab.
4. **History-Rewrite mit `git filter-repo`/BFG und Force-Push** — entfernt die
   Dateien aus zukünftigen Klonen, nicht aus vorhandenen Forks/Caches. Das
   verletzt die Projektregel „kein Force-Push, keine History-Rewrites“ und
   braucht ausdrückliche Freigabe; nicht empfohlen.

**Empfehlung:** Option 1 sofort, Option 2 nur wenn ein öffentlicher sauberer
Stand gebraucht wird. B muss ohnehin neu bewertet oder mit neuen Dokumenten
gestartet werden.

## Folgen

- Lokale Prüfskripte, die `goldstandard_A.json` als Default verwenden, laufen
  weiter, solange die lokale Kopie vorhanden ist.
- Ein frischer Clone enthält die entfernten Dateien nicht. Die betroffenen
  Benchmarks müssen ihre Rohdaten künftig über den dokumentierten Download-
  oder Freigabeweg beziehen.
- Die `.gitignore`-Regeln verhindern ein erneutes Hinzufügen über
  `git add`.
