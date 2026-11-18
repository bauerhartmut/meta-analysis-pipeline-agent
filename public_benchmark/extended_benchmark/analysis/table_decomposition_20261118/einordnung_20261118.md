# Table Decomposition: Ergebnisteil und Einordnung (18.11.2026)

Alle Zahlen stammen aus den unten genannten Artefakten; keine ist geschätzt,
außer der Tokenzahl, die als Zeichen/4 markiert ist. Der maschinell erzeugte
Tabellenteil liegt in `strukturbericht_20261118.md`, die Rohdaten in
`offline_struktur_20261118/structure.json`,
`offline_struktur_reihenfolge_20261118/structure.json` und
`diagnose_erreichbarkeit_20261118.json`.

## Was gemessen wurde — und was nicht

**Gemessen:** Struktur (Abdeckung, Kontexterhalt, Validierungsbefunde), Aufwand
(Einheiten, Prompt-Zeichen, geschätzte Tokens) und die **Reichweite des
Tabellenpfads** (`gold_reachable`) für die Verfahren A–E auf einem eingefrorenen
Testdatensatz, ohne Modellaufruf.

**Nicht gemessen:** Precision, Recall, F1, Exact Match, Arm-/Outcome-/
Zeitpunktzuordnung, technische Ausfallquote, Laufzeit und Kosten pro 100
richtige Zellen. Diese Kennzahlen brauchen einen Modelllauf; er ist ohne
ausdrückliche Freigabe und Gateway-Guthaben nicht gestartet worden.

## Datensatz

| Feld | Wert |
|---|---|
| Split | `test` |
| Tabellen | 60 |
| Records | 59 |
| Dokumente | 31 |
| Kandidaten (Record, Tabelle) | 608 |
| Goldzellen der 59 Records | 278 |
| davon über die ausgewählten Tabellen erreichbar | 95 (34,2 %) |
| mit Reihenfolge-Annahme | 99 (35,6 %) |

Der Devsplit hat nach derselben Prozedur nur 26 Kandidaten; mit `--target 40`
wurden 6 ausgewählt. Für Schwellenoptimierung ist er zu klein — ein Befund, kein
Versehen.

## Struktur- und Aufwandsvergleich (Test, 59 Records, 60 Tabellen)

Standardkonfiguration (`arm_order_fallback` aus):

| Var | Verfahren | Einheiten/Record | Zeichen/Record | Tokens ges. (Sch.) | Faktor zu A | Gold erreichbar | strukturell komplett | Fehler |
|---|---|---|---|---|---|---|---|---|
| A | Full-Table | 1,02 | 5.744,6 | 84.733 | 1,00 | 95 | 60/60 | 0 |
| B | Vertical | 2,81 | 10.700,2 | 157.828 | 1,86 | 95 | 60/60 | 0 |
| C | Horizontal | 6,34 | 22.529,3 | 332.307 | 3,92 | 95 | 60/60 | 0 |
| D | Bidirectional | 8,53 | 29.876,4 | 440.677 | 5,20 | 95 | 60/60 | 0 |
| E | Adaptive | 4,95 | 20.018,9 | 295.279 | 3,49 | 95 | 60/60 | 0 |

Mit Reihenfolge-Annahme (`--arm-order-fallback`, dieselbe Auswahl): erreichbar
99, Tokens 84.749 / 163.546 / 332.387 / 446.475 / 299.304.

Lesart:

- **Kontexterhalt ist belegt.** Alle 60 Tabellen sind für alle fünf Verfahren
  strukturell vollständig, ohne einen Fehler: jede Datenzelle gehört zu genau
  einer Einheit, jeder Spaltenpfad und jedes Zeilenlabel wird mitgeführt,
  Fußnoten sind im Ausschnitt.
- **B bleibt der günstigste Zerlegungspfad** (1,86×), D der teuerste (5,20×),
  E liegt mit 3,49× dazwischen, weil die Nachlese nur unbelegte oder
  konfliktäre Zellen anfasst.

## Der Reachability-Hebel: was gebaut wurde und was er bringt

Ausgangspunkt war, dass nur 76 von 268 Goldzellen (28,4 %) über eine
ausgewählte Tabelle erreichbar waren. Drei deterministische Mechanismen sind
seitdem drin:

1. **Dokumentweiter Arm-Transfer** (`transfer_arms_within_document`): Trägt eine
   Tabelle den Gruppenkopf `Verum` belegt, gilt derselbe Kopf in der
   Schwestertabelle desselben Dokuments als belegt. Markiert als
   `arm_basis="uebertrag"`, gezählt als `armzuordnung_uebertragen`.
   Wirkung: 18 Spalten in 215 Tabellen, aber nur +3 Goldzellen — wo ein Label
   identisch ist, bindet die Kopfregel meist schon selbst. Der Mechanismus
   bleibt, weil er belegbar ist und nichts kostet.
2. **Verbundwerte** (`secondary_role`): Zellen wie `12.4 (3.1)` tragen Mittelwert
   und Streuung. Der erste Wert ist der Zellwert, der zweite wird als eigener
   Beleg mit derselben Fundstelle geführt (`derived`), markiert als
   `verbundwert_getrennt`. Vorher blieb die ganze Zelle wertlos, weil
   `parse_value` den Verbund nicht las. Wirkung: 8 Spalten in der Auswahl, ohne
   diesen Fix wären es 0.
3. **Auswahl nach Feldabdeckung**: Kandidaten sind Paare (Record, Tabelle); je
   Record werden bis zu 6 Tabellen aufgenommen, aber nur solche, die mindestens
   ein neues Feld beisteuern. Kein Goldwert, kein Modellurteil.

Ergebnis: **95 von 278 Goldzellen erreichbar (34,2 %)** gegenüber 28,4 % vor dem
Schritt. Der Zuwachs ist real, aber klein — und der Grund ist jetzt gemessen,
nicht vermutet:

| Grund (von 183 nicht erreichbaren Zellen) | Zellen | Bedeutung |
|---|---|---|
| `feld_fehlt_im_dokument` | 100 | keine Tabelle des Dokuments hat eine Spalte dieser Rolle (mean 60, sd 58, events 26 über alle Gründe) |
| `arm_nicht_gebunden_ohne_namensrest` | 40 | Spalte existiert, aber der Kopf nennt den Arm nicht (Kontextnamen sind Langtext wie „Individual cognition and self-regulation processes intervention“, der Kopf sagt „IG“) |
| `spalte_nicht_ausgewaehlt` (+ mit Arm im Kopf) | 42 | die Tabelle mit der Spalte ist nicht in der Auswahl |
| `arm_nicht_gebunden` | 1 | Ambiguität zwischen zwei Armnamen |

Damit ist die Obergrenze des Tabellenpfads für Recall bekannt: **rund 34 %** der
Goldzellen dieses Splits sind überhaupt aus Tabellen holbar, wenn die
Armzuordnung so bleibt. Selbst ein fehlerfreies Modell kann auf diesem Pfad
nicht mehr liefern. Die Zerlegung hebt diesen Deckel nicht — sie sorgt dafür,
dass die erreichbaren Zellen korrekt und vollständig kontextualisiert sind.

## Fehleranalyse der Strukturbefunde

| Code | A | B | C | D | E | Bedeutung |
|---|---|---|---|---|---|---|
| `zeilenlabel_fehlt` | 62 | 41 | 62 | 103 | 98 | Zeile ohne Label (Gruppen-Zwischenzeilen) |
| `spaltenkopf_fehlt` | 17 | 0 | 63 | 63 | 63 | Spalte ohne Header-Pfad (leere Eckzelle) |
| `verbundwert_getrennt` | 8 | 8 | 8 | 8 | 8 | Spalten mit zwei Zahlen je Zelle, zweiter Wert belegt |
| `armzuordnung_uebertragen` | 6 | 6 | 6 | 6 | 6 | Arm aus Schwestertabelle desselben Dokuments |
| `zelle_ausserhalb_scope` | 0 | 47 | 0 | 0 | 0 | Spalteneinheit liest nur ihre Spalte |

- `zelle_ausserhalb_scope` bei B ist erwartbar und kein Fehler: jede Zelle wird
  von genau einer Spalteneinheit gelesen, die Abdeckung ist vollständig.
- `spaltenkopf_fehlt` betrifft Spalten mit leerer Kopfzelle. Der Prompt führt sie
  als `col n: (ohne Kopf)`; das Modell sieht die Spalte, kann sie aber nur über
  die Nachbarpfade einordnen. Im Modelllauf gezielt zu prüfen.
- `zeilenlabel_fehlt` ist nach dem Labelspalten-Fix von 395 auf 62 gefallen; die
  verbleibenden Fälle sind Gruppen-Zwischenzeilen, die tatsächlich kein eigenes
  Label tragen.

## Token- und Kostenvergleich

Tokens sind aus Prompt-Zeichen / 4 geschätzt (markiert). Gemessene Tokens,
Laufzeit und Kosten entstehen erst im Modelllauf; `evaluate.py` rechnet dann aus
`prompt_tokens`/`completion_tokens` und `--preis-in`/`--preis-out` Kosten und
Kosten pro 100 richtige Zellen. Eine Euro-Zahl ohne Modelllauf wäre erfunden und
steht deshalb hier nicht.

Relativ: B kostet das 1,86-Fache von A an Eingabe, E das 3,49-Fache, C das
3,92-Fache, D das 5,20-Fache. Ob der Recall-Gewinn das rechtfertigt, entscheidet
der Modelllauf.

## Empfehlung für die produktive Integration

1. **A bleibt Baseline, B wird der Standard für den Tabellenpfad** (1,86×
   Aufwand, vollständiger Kontexterhalt, gleiche Abdeckung). C und D nur, wenn
   der Modelllauf einen Recall-Vorteil zeigt, der 4–5× Eingabetokens trägt.
2. **E mit Nachlese-Budget**, eingestellt auf `dev`; die Nachlese greift nur bei
   unbelegten oder konfliktären Zellen.
3. **Nächster Hebel: Rollen-Vokabular.** Von 100 Zellen ohne passende Spalte
   entfallen 60 auf Mittelwerte — vermutlich Spalten mit Köpfen wie „Change“,
   „Post“, „Follow-up“, die `role_for_header` nicht als Mittelwert liest. Das
   ist ohne Modellkosten messbar und würde die Reichweite direkt erhöhen; jede
   Ergänzung gehört mit Test und Gegenprobe in `semantics.role_for_header`.
4. **Danach der Modelllauf** (A/B/E auf `test`, C/D nur bei Bedarf), mit
   vorheriger Telemetrie und ausdrücklicher Freigabe. Erwartung: der messbare
   Recall-Gewinn ist durch die 34-%-Obergrenze begrenzt; die interessante Frage
   ist, ob B/E diese 95 Zellen vollständiger und präziser holen als A.
5. **Reihenfolge-Annahme aus lassen** (billig, +4 Zellen, prüfpflichtig); im
   Benchmark mitführen, um den Effekt zu kennen.

## Artefakte

| Datei | Inhalt |
|---|---|
| `selection_test.json` | eingefrorene Auswahl (60 Tabellen, 608 Kandidaten, Hash) |
| `selection_dev.json` | Devauswahl (6 Tabellen aus 26 Kandidaten) |
| `offline_struktur_20261118/structure.json` | Struktur/Aufwand/Reichweite A–E |
| `offline_struktur_reihenfolge_20261118/structure.json` | dasselbe mit Reihenfolge-Annahme |
| `diagnose_erreichbarkeit_20261118.json` | Klassifikation jeder nicht erreichbaren Goldzelle |
| `strukturbericht_20261118.md` | maschinell erzeugter Bericht |
| `einordnung_20261118.md` | dieser Text |
| `ergebnisbericht_20261118.md` | konsolidierter Ergebnisbericht (Tabellen, Diagnose, Reproduzierbarkeit) |

## Grenzen

- Der Strukturvergleich sagt nichts über Extraktionsqualität. Precision/Recall
  bleiben offen, bis ein Modelllauf freigegeben ist.
- `gold_reachable` ist eine Obergrenze des Tabellenpfads, keine Modellleistung.
- Die Diagnose klassifiziert per Header-Text, nicht per Modell; sie priorisiert,
  sie beweist nicht.
- Outcome- und Zeitpunktzuordnung sind im Gold nicht zellweise annotiert und
  bleiben nicht messbar; `evaluate.py` weist das aus.
