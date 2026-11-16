# Uebergabe: klinische Extraktionspipeline, Yun-Benchmark (16.11.2026)

Dieser Ordner enthaelt den vollstaendigen Arbeitsstand: Rohdaten, alle Laeufe mit
Antworten, Auswertungen, Prompts, Skripte, Fehleranalyse und Dokumentation. Er ist
so gedacht, dass eine aussenstehende Person oder KI die Ergebnisse **ohne
Rueckfragen** nachrechnen und beurteilen kann.

## Aufbau

```
handoff_20261116/
  README.md                     diese Datei
  benchmark_report.md           ausfuehrlicher Bericht (Ergebnisse, Begruendungen, Entscheidungsvorlage)
  ergebnisse.md                 kompakte Ergebnistabellen (aus den Messdateien erzeugt)
  methodik.md                   Datensatz, Metrikdefinitionen, Vergleichsregeln
  offene_probleme.md            ungeloeste Punkte und naechste Experimente
  ANHANG_DATEILISTE.md          vollstaendige Dateiliste mit Groesse
  MANIFEST_SHA256.txt           SHA-256 jeder Datei (Integritaetspruefung)
  pruefung.md                   Ergebnis der Qualitaetskontrolle dieser Uebergabe

  daten/
    yun699.jsonl                699 Records inkl. Goldzellen (der Goldstandard)
    manifest.json               Aufbau des Datensatzes (Felder, Zaehlungen, Quellhash)
    official_metrics.json       offizielle Kennzahlen des Original-Benchmarks
    stichprobe60.json           60 geschichtete Records (Referenzlauf)
    stichprobe20.json           20 Records (Modellvergleich)
    vergleich_20261116.json     Kennzahlen aller Laeufe, einheitlich berechnet
    ausschluss_konflikte.json   Kennzahlen mit und ohne bestreitbare Goldannotationen
    laufkennzahlen.json         je Lauf: Treffer, Tokens, Zeit, Fehlerklassen
    texte_manifest.txt          Liste der 120 verwendeten Volltexte
    volltexte/<PMC-ID>.md       die 120 Artikelvolltexte selbst (Apache-2.0)
    README_yun_full.md          Beschreibung des Auswertungsordners im Original

  laeufe/<run-id>/              je Lauf: predictions.jsonl, lauf.log,
                                auswertung_yun.json, yun_metriken.json, ggf. validator.json

  skripte/                      Harness, Adapter, Auswertung, Validator, Export
  skripte/tests/                die beiden Testdateien des Benchmarks

  konfiguration/
    prompt_v7_zellzeitpunkt.txt     produktiver Prompt, gerendert
    prompt_v8_quellenzeile.txt      Experiment C (Quellenangabe im JSON)
    prompt_v7_gruppengroesse_kurz.txt  Experiment B
    prompt_standard_ohne_zellzeitpunkt.txt
    prompt_repair.txt               Reparaturaufruf nach Length-Ausfall
    systemprompt.txt                Systemnachricht
    modelle_und_parameter.json      Modell-IDs, Limits, Retry- und Cache-Regeln

  fehleranalyse/
    falsche_zellen.csv          jede falsch extrahierte Zelle mit Study-ID, PMC,
                                Goldwert, Modellwert, Fundstelle und Fehlerklasse

  protokolle/
    laufprotokolle.md           Anfragen, Ausfaelle, Tokens, Zeiten je Lauf
```

## Enthaltene Studien und Aufgaben

Der Datensatz besteht aus 699 Extraktionsaufgaben (Records) aus 120 Artikeln.
Jeder Record verlangt Werte fuer einen Studienarm-Vergleich: Mittelwert,
Standardabweichung und Gruppengroesse je Arm (kontinuierlich) oder Ereigniszahl
und Gruppengroesse je Arm (binaer). `daten/yun699.jsonl` enthaelt Goldwerte,
Kontext (Intervention, Comparator, Outcome, Zielzeitpunkt) und die PMC-ID.
Die Volltexte selbst liegen nicht in diesem Ordner, sind aber im Repository
unter `public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/data/no_attributes_markdown_files/`
als `<PMC-ID>.md` abgelegt (120 Dateien, Apache-2.0).

## Was hier bewusst NICHT enthalten ist

- **API-Schluessel und Zugangsdaten.** Der Harness liest sie aus der lokalen
  Konfiguration; sie sind weder in den Laeufen noch in den Skripten enthalten.
- **Kosten in Geld.** Fuer den genutzten Endpunkt liegt kein Preisaushang vor.
  Ausgewiesen sind Output-Tokens und Laufzeiten; Kosten pro Zelle waeren eine
  Schaetzung und sind deshalb nicht angegeben.
- **Start- und Endzeit je Lauf.** Der Harness protokolliert sie nicht. In
  `protokolle/laufprotokolle.md` steht der Dateizeitstempel von
  `predictions.jsonl` und die Summe der je Anfrage gemessenen `elapsed_s`.
- **Rohprompts je Anfrage.** Nur mit `--save-content` gespeichert; das ist bei
  drei Records der Fall (`laeufe/yun_v8_probe_20261116/`). Fuer alle anderen
  Laeufe sind Promptversion, Modell-ID, Limit und geparste Zellen gespeichert.

## Nachrechnen

```
# Kennzahlen aller Laeufe aus den Rohdaten
.venv/bin/python skripte/vergleich_20261116.py   # im Repository, nicht hier

# Einzelnen Lauf auswerten
.venv/bin/python public_benchmark/extended_benchmark/yun_full/auswerte_yun699.py \
    --run yun20_8000_glm_cb_20261116 --out /tmp/x.json

# Integritaet pruefen (Windows/Git Bash)
sha256sum -c MANIFEST_SHA256.txt
```

Die Datei `daten/vergleich_20261116.json` wird aus `laeufe/*/predictions.jsonl`
berechnet; sie ist also keine unabhaengige Quelle, sondern eine Zusammenfassung
mit nachvollziehbarer Rechenvorschrift (Dateikopf von `vergleich_20261116.py`).

## Belastbarkeit der Ergebnisse

- **Belastbar:** Metrikkorrektur (0,8324 statt 0,8000), Fehlerklassen mit
  Artikelbelegen, technische Ausfallquoten bei 4.000 Tokens, Git-Historie.
- **Eingeschraenkt:** 20-Record-Vergleiche (kleine Stichprobe, breite
  Konfidenzintervalle), Qwen3-30B (Cache-Anteil unklar), Experiment B.
- **Explorativ:** alle Aussagen zur zweistufigen Architektur,
  Evidenzverknuepfung und zum vollstaendigen Testsplit.

## Stand

Arbeitsstand 16.11.2026. Die Git-Historie des Repositories enthaelt die
Commits dieses Tages (`4ed869b`, `3258166`, `7b2360a`, `64b9c09` und folgende).
Der produktive Prompt v7 und die Golddatei wurden nicht veraendert.
