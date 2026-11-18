# Table Decomposition & Reconstruction Engine — Ergebnisse

Stand: 18.11.2026. Testsplit des Yun-699-Korpus, eingefrorene Auswahl, **ohne
Modellaufruf**. Alle Zahlen sind aus den genannten JSON-Artefakten gelesen;
Tokenzahlen sind als Schätzung aus Prompt-Zeichen / 4 markiert. Precision,
Recall, F1 und Kosten pro richtiger Zelle sind **nicht gemessen** (siehe
Abschnitt 8).

## 1. Kurzfassung

| Frage | Antwort |
|---|---|
| Bleibt die Tabellenstruktur rekonstruierbar? | Ja. 60 von 60 Tabellen strukturell vollständig, 0 Fehler, für alle fünf Verfahren. |
| Gehen Header-Informationen verloren? | Nein. Jede Einheit führt den vollen Header-Pfad, das Zeilenlabel und die relevanten Fußnoten mit; die Validierung prüft es je Einheit. |
| Sind Teilresultate auf die Originalstelle zurückführbar? | Ja. Tabelle, Dokument, Zeile/Spalte, Seite, Einheit, Verfahren, Richtung, Modell und Zitat stehen an jedem Beleg. |
| Sind die fünf Verfahren unabhängig benchmarkbar? | Ja. Gemeinsame Auswahl, gemeinsame Goldzellen, ein Lauf je Verfahren. |
| Zeigt die adaptive Zerlegung einen Vorteil? | Auf dem Tabellenpfad **nicht messbar**: die erreichbare Goldmenge ist für A–E identisch (95 Zellen), weil sie von der Auswahl und der Armzuordnung abhängt, nicht vom Zerlegeverfahren. E kostet 3,49× Eingabe von A. Ob E die 95 Zellen besser trifft, entscheidet erst der Modelllauf. |
| Wie viel Gold ist über Tabellen überhaupt erreichbar? | 95 von 278 Zellen (34,2 %), mit Reihenfolge-Annahme 99 (35,6 %). Das ist die Obergrenze des Tabellenpfads, keine Modellleistung. |

## 2. Datensatz und Auswahl

Korpus: `yun699.jsonl` — 699 Records, 2.773 Goldzellen, 120 Dokumente (111 mit
`table-wrap`, 92 mit Strichregel). Auswahlkriterium ist reine Struktur (Anzahl
Spalten mit belegtem Zielfeld, Tabellen-ID-Hash), kein Goldwert, kein Modell.
Kandidat ist ein Paar (Record, Tabelle); je Record höchstens 6 Tabellen, je
Dokument höchstens 2, und nur Tabellen, die mindestens ein neues Feld beisteuern.

| Feld | Wert |
|---|---|
| Split | `test` |
| Tabellen | 60 |
| Records | 59 |
| Dokumente | 31 |
| Kandidaten (Record, Tabelle) | 608 |
| Goldzellen der 59 Records | 278 |
| davon erreichbar | **95 (34,2 %)** |
| `records_sha256` | `c22ed3fb42dbaaff7051a89cdb327c4b250a134db0a62a19d3877d5ba311c0b1` |

Schichtverteilung der 60 Tabellen: mehrzeitpunkt 37, mehrstufiger_kopf 36,
fussnoten 35, mittel 19, sehr_komplex 19, einfach 14, komplex 8, komplexe_pdf 8,
mehrarm 8.

Devsplit: 26 Kandidaten, mit `--target 40` wurden 6 ausgewählt — zu klein für
Schwellenoptimierung. Das ist ein Befund, kein Versehen.

## 3. Struktur und Aufwand je Verfahren

Standardkonfiguration, 59 Records, 60 Tabellen, ohne Modellaufruf:

| Var | Verfahren | Einheiten/Record | Zeichen/Record | Zeichen/Einheit | Tokens ges. (Sch.) | Faktor zu A | Gold erreichbar | strukturell komplett | Fehler | Warnungen |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Full-Table Extraction | 1,02 | 5.744,6 | 5.648,9 | 84.733 | 1,00 | 95 | 60/60 | 0 | 79 |
| B | Vertical Decomposition | 2,81 | 10.700,2 | 3.803,1 | 157.828 | 1,86 | 95 | 60/60 | 0 | 41 |
| C | Horizontal Decomposition | 6,34 | 22.529,3 | 3.554,1 | 332.307 | 3,92 | 95 | 60/60 | 0 | 125 |
| D | Bidirectional Decomposition | 8,53 | 29.876,4 | 3.504,4 | 440.677 | 5,20 | 95 | 60/60 | 0 | 166 |
| E | Adaptive Recursive | 4,95 | 20.018,9 | 4.044,9 | 295.279 | 3,49 | 95 | 60/60 | 0 | 161 |

Mit Reihenfolge-Annahme (`--arm-order-fallback`, dieselbe Auswahl):

| Var | Einheiten/Record | Zeichen/Record | Tokens ges. (Sch.) | Gold erreichbar |
|---|---|---|---|---|
| A | 1,02 | 5.745,7 | 84.749 | 99 |
| B | 2,92 | 11.087,9 | 163.546 | 99 |
| C | 6,34 | 22.534,7 | 332.387 | 99 |
| D | 8,63 | 30.269,5 | 446.475 | 99 |
| E | 5,02 | 20.291,8 | 299.304 | 99 |

Beobachtungen:

- **Kontexterhalt kostet Platz, nicht Genauigkeit.** Zerlegte Einheiten sind
  kürzer (3.500–4.000 Zeichen) als die volle Tabelle (5.649), aber es gibt mehr
  davon: C liest jede Zeile mit allen Köpfen und braucht deshalb 3,92×
  Eingabe, D durch die doppelte Leserichtung 5,20×.
- **B ist der günstigste Zerlegungspfad** (1,86×): jede Spalte führt ihren Kopf
  nur einmal mit.
- **E bleibt unter D** (3,49×), weil die Nachlese nur unbelegte oder konfliktäre
  Zellen anfasst.
- Alle Verfahren decken dieselben 95 Goldzellen ab — die Abdeckung hängt an
  Auswahl und Armzuordnung (Abschnitt 4), nicht am Verfahren.

## 4. Reichweite des Tabellenpfads

Ausgangspunkt war 76 von 268 Goldzellen (28,4 %). Drei deterministische
Mechanismen kamen hinzu:

| Mechanismus | Wirkung | Markierung |
|---|---|---|
| Dokumentweiter Arm-Transfer: belegter Gruppenkopf gilt in Schwestertabellen desselben Dokuments | 18 Spalten in 215 Tabellen, +3 Goldzellen | `arm_basis="uebertrag"`, Befund `armzuordnung_uebertragen` |
| Verbundwerte `12.4 (3.1)`: erster Wert = Messwert, zweiter Wert = eigener Beleg mit derselben Fundstelle | ohne diesen Fix blieben diese Zellen wertlos | `secondary_role`, `evidence.derived`, Befund `verbundwert_getrennt` |
| Auswahl nach Feldabdeckung statt Tabellenzahl | Kandidaten 537 → 608, mehr Felder je Record | `--max-per-record 6`, „nur mit neuem Feld“ |

Ergebnis: **95 von 278 Zellen (34,2 %)**, mit Reihenfolge-Annahme 99 (35,6 %).

Die verbleibenden 183 Zellen sind klassifiziert
(`diagnose_erreichbarkeit_20261118.json`):

| Grund | Zellen | Bedeutung |
|---|---|---|
| `feld_fehlt_im_dokument` | 100 | keine Tabelle des Dokuments hat eine Spalte dieser Rolle |
| `arm_nicht_gebunden_ohne_namensrest` | 40 | Spalte existiert, der Kopf nennt den Arm aber nicht (Kontextname ist Langtext, Kopf sagt „IG“) |
| `spalte_nicht_ausgewaehlt` / `…_mit_arm` | 42 | die Tabelle mit der Spalte ist nicht in der Auswahl |
| `arm_nicht_gebunden` | 1 | Ambiguität zwischen zwei Armnamen |

Nach Rolle: mean 60, sd 58, n 39, events 26. Nach Arm: comparator 96,
intervention 87 — die Lücke ist symmetrisch, also kein einseitiger Bindungsfehler.

**Konsequenz:** Ein fehlerfreies Modell kann auf diesem Pfad höchstens ~34 % des
Goldes liefern. Die Zerlegung hebt diesen Deckel nicht; sie sorgt dafür, dass die
erreichbaren Zellen vollständig kontextualisiert sind.

## 5. Fehleranalyse

Befunde der Strukturprüfung (Summe über die 59 Record-Läufe; eine Tabelle kann in
mehreren Records gezählt werden):

| Code | A | B | C | D | E | Bedeutung |
|---|---|---|---|---|---|---|
| `zeilenlabel_fehlt` | 62 | 41 | 62 | 103 | 98 | Zeile ohne Label (Gruppen-Zwischenzeile) |
| `spaltenkopf_fehlt` | 17 | 0 | 63 | 63 | 63 | Spalte ohne Header-Pfad (leere Eckzelle) |
| `verbundwert_getrennt` | 8 | 8 | 8 | 8 | 8 | Spalte mit zwei Zahlen je Zelle, zweiter Wert belegt |
| `armzuordnung_uebertragen` | 6 | 6 | 6 | 6 | 6 | Arm aus Schwestertabelle |
| `zelle_ausserhalb_scope` | 0 | 47 | 0 | 0 | 0 | Spalteneinheit liest nur ihre Spalte |

Während der Arbeit gefundene und behobene Parser-Defekte:

1. **Überlappende Header-Spannen** bei um eine Spalte versetzten Gruppenköpfen →
   Deduplizierung doppelter Blattanker plus gleichmäßige Teilung; Nicht-Teilbares
   wird als Irregularität markiert, nie geraten.
2. **Labelspalten mit Ziffern** (`Visit 5:`, `5 min`) wurden als Datenspalten
   gelesen → 395 Warnungen je Lauf. Jetzt entscheidet zusätzlich, ob sich die
   Zellen als Zahl lesen lassen.
3. **Verbundzellen** (`12.4 (3.1)`) wurden von `parse_value` komplett abgelehnt →
   der ganze Zellwert fehlte.

`zelle_ausserhalb_scope` bei B ist erwartbar und kein Fehler: jede Zelle wird von
genau einer Spalteneinheit gelesen, die Abdeckung ist vollständig.

## 6. Token- und Kostenvergleich

Gemessen sind nur Prompt-Zeichen; die Tokenspalte ist Zeichen / 4 und als
Schätzung markiert. Gemessene Tokens, Laufzeit und Kosten entstehen im
Modelllauf; `evaluate.py` rechnet dann aus `prompt_tokens`/`completion_tokens`
und `--preis-in`/`--preis-out`:

```
kosten = prompt_tokens/1000 * preis_in + completion_tokens/1000 * preis_out
kosten_pro_100_richtige_zellen = kosten / richtig * 100
```

Eine Euro-Zahl ohne Modelllauf wäre erfunden und steht deshalb hier nicht.
Relativ ist die Aussage belastbar: B 1,86×, E 3,49×, C 3,92×, D 5,20× von A.

## 7. Was geliefert ist

| Lieferziel | Ort |
|---|---|
| Architekturbericht der bestehenden Pipeline | `docs/table_decomposition_architektur.md` |
| Modul | `research_agent/table_decomposition/` |
| Schnittstellen-Dokumentation | `research_agent/table_decomposition/README.md` |
| Tests für alle fünf Verfahren | `research_agent/tests/test_table_decomposition.py` (32), `public_benchmark/tests/test_table_decomposition_benchmark.py` (4) |
| Reproduzierbarer Benchmark | `public_benchmark/extended_benchmark/table_decomposition/` |
| Vergleichstabellen | dieses Dokument, Abschnitte 3–6 |
| Fehleranalyse | Abschnitt 5 und `diagnose_erreichbarkeit_20261118.json` |
| Token-/Kostenvergleich | Abschnitt 6 |
| Integrationsempfehlung | Abschnitt 9 |
| Maschinell erzeugter Bericht | `strukturbericht_20261118.md` |
| Einordnung und Entscheidungen | `einordnung_20261118.md` |

## 8. Was nicht gemessen ist

- **Zell-Precision, Zell-Recall, Zell-F1, Exact Match**: brauchen einen
  Modelllauf (extrahiert gegen Gold), nicht freigegeben.
- **Korrekte Arm-/Outcome-/Zeitpunktzuordnung**: Armzuordnung ist im Gold
  zellweise vorhanden und wird im Modelllauf über Feld+Arm mitgezählt; Outcome
  und Zeitpunkt sind im Gold **nicht** zellweise annotiert und bleiben nicht
  messbar (`evaluate.py` weist das aus).
- **Technische Ausfallquote, Laufzeit, gemessene Tokens, Kosten pro 100 richtige
  Zellen**: entstehen erst im Modelllauf.

Der Modelllauf startet nur mit `--allow-network --confirm-kosten`; ohne beide
Flags bricht das Werkzeug ab.

## 9. Empfehlung für die produktive Integration

1. **A bleibt Baseline, B wird Standard für den Tabellenpfad**: 1,86× Aufwand,
   vollständiger Kontexterhalt, gleiche Abdeckung. C und D nur, wenn der
   Modelllauf einen Recall-Vorteil zeigt, der 4–5× Eingabe trägt.
2. **E mit Nachlese-Budget**, eingestellt auf `dev`; die Nachlese greift nur bei
   unbelegten oder konfliktären Zellen.
3. **Aktivierung über `table_decomposition: true`** (Konfiguration oder
   `TABLE_DECOMPOSITION`); der Pipeline-Haken `augment_prompt_text` hängt die
   strukturierte Tabellenansicht an, ohne den Originaltext zu verändern, sodass
   die Zitatprüfung intakt bleibt. Noch nicht in `orchestrator.py` verdrahtet —
   bewusst erst nach dem Modelllauf.
4. **Reihenfolge-Annahme aus lassen** (billig, +4 Zellen, prüfpflichtig); im
   Benchmark mitführen, um den Effekt zu kennen.
5. **Nächster Hebel: Rollen-Vokabular.** Von 100 Zellen ohne passende Spalte
   entfallen 60 auf Mittelwerte — vermutlich Köpfe wie „Change“, „Post“,
   „Follow-up“, die `role_for_header` nicht als Mittelwert liest. Ohne
   Netzkosten messbar; jede Ergänzung mit Test und Gegenprobe.
6. **Danach der Modelllauf** A/B/E auf `test` (C/D nur bei Bedarf), mit
   vorheriger Telemetrie des letzten Laufs und ausdrücklicher Freigabe.

## 10. Reproduzierbarkeit

```bash
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

python public_benchmark/extended_benchmark/table_decomposition/select_tables.py \
    --role test --target 60 --write
python public_benchmark/extended_benchmark/table_decomposition/run_benchmark.py \
    --offline --run-id offline_struktur_20261118
python public_benchmark/extended_benchmark/table_decomposition/run_benchmark.py \
    --offline --arm-order-fallback --run-id offline_struktur_reihenfolge_20261118
python public_benchmark/extended_benchmark/table_decomposition/diagnose_reachability.py \
    --selection …/selection_test.json \
    --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
    --out …/diagnose_erreichbarkeit_20261118.json
python public_benchmark/extended_benchmark/table_decomposition/report.py \
    --structure …/offline_struktur_20261118/structure.json \
    --selection …/selection_test.json --out …/strukturbericht_20261118.md
```

Prüfstand: `pytest research_agent/tests/test_table_decomposition.py
public_benchmark/tests/test_table_decomposition_benchmark.py -q` → 36 Tests
grün (Stand 18.11.2026).

## 11. Grenzen

- Der Strukturvergleich sagt nichts über Extraktionsqualität.
- `gold_reachable` ist die Obergrenze des Tabellenpfads, keine Modellleistung.
- Die Diagnose klassifiziert per Header-Text, nicht per Modell; sie priorisiert,
  sie beweist nicht.
- Der Devsplit ist mit 26 Kandidaten zu klein für Schwellenoptimierung.
- Goldannotationen wurden nicht verändert; die Auswahl verwendet keine Goldwerte
  als Eingabe.

## 12. Artefakte

| Datei | Inhalt |
|---|---|
| `selection_test.json` | eingefrorene Auswahl (60 Tabellen, 608 Kandidaten, Hash) |
| `selection_dev.json` | Devauswahl (6 Tabellen aus 26 Kandidaten) |
| `offline_struktur_20261118/structure.json` | Struktur, Aufwand, Reichweite A–E |
| `offline_struktur_reihenfolge_20261118/structure.json` | dasselbe mit Reihenfolge-Annahme |
| `diagnose_erreichbarkeit_20261118.json` | Klassifikation jeder nicht erreichbaren Goldzelle |
| `strukturbericht_20261118.md` | maschinell erzeugter Bericht |
| `einordnung_20261118.md` | Einordnung, Entscheidungen, Begründungen |
| `ergebnisbericht_20261118.md` | dieses Dokument |
