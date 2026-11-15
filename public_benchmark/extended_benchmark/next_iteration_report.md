# Nächste Iteration: Fehleranalyse und Fahrplan

Stand: 15.11.2026. Grundlage sind alle Yun-Dev-Läufe unter
`public_benchmark/extended_benchmark/runs/`, ausgewertet von
`analyze_errors.py`. Die Rohausgaben liegen in
`analysis/v1_20261115/` (`error_analysis.json`, `error_analysis.md`,
`error_cases.csv`, `human_review_queue.csv`).

Alle Zahlen dieses Berichts stammen aus diesen Dateien; keine ist von Hand
eingetragen. Die Metriken wurden beim Lauf neu berechnet und stimmen mit den
gespeicherten `eval/*.metrics.json` überein (`metriken_identisch: true` in
allen sieben Läufen).

## 1. Zusammenfassung der Fehler

Die Fehler werden **je kanonischer Prompt-Version getrennt** ausgewiesen und
nicht summiert. `v3_abs_count` ist als **verworfen** markiert: Die Fassung lag
im Dev-Lauf unter der Referenz (F1 0,919 statt 0,945) und ist kein Standard
mehr. Die Zuordnung und der Status stehen in `versions.py`.

| Version | Status | Fehler | technisch | inhaltlich | zusätzliche Zellen | Läufe |
|---|---|---|---|---|---|---|
| `v2_timepoint` | Referenz | 235 | 28 | 207 | 107 | 3 |
| `v3_abs_count` | **verworfen** | 17 | 6 | 11 | 5 | 1 |
| `v1` | historisch | 135 | 12 | 123 | 56 | 1 |

Für die Referenz `v2_timepoint` (235 Fehler, 28 davon technisch):

| Klasse | Anzahl | Anteil |
|---|---|---|
| Nicht eindeutig klassifizierbar | 100 | 43 % |
| Zahl nicht extrahiert | 100 | 43 % |
| Unvollständige Modellantwort | 28 | 12 % |
| Falsche Tabellenzeile | 4 | 2 % |
| Prozentwert statt absoluter Zahl | 3 | 1 % |
| Falscher Messzeitpunkt | 0 | – |
| Halluzinierter Wert | 0 | – |
| Gruppenverwechslung | 0 | – |
| Ereignisse/Teilnehmer verwechselt | 0 | – |
| Parser-/Formatfehler | 0 | – |

`v3_abs_count` (verworfen) hat 17 Fehler: 6 nicht extrahiert, 6 unvollständig,
4 nicht eindeutig, 1 Prozentwert. Die Ereigniszahlen sind darin unverändert
gegenüber der Referenz; die Fassung wird ab hier nur noch nachrichtlich geführt.

Drei Befunde sind wichtiger als die Verteilung:

1. **Die Klassen „Gruppenverwechslung“ und „Ereignisse/Teilnehmer“ sind
   leer.** Die in der Aufgabe vermuteten Fehlerarten treten in diesem Datensatz
   nicht auf. Wer sie im Prompt adressiert, bekämpft ein Problem, das die Daten
   nicht zeigen.
2. **Der größte Block ist „nicht extrahiert“** (100 Zellen), nicht „falsch
   gelesen“. Das ist ein Abdeckungs-, kein Genauigkeitsproblem.
3. **Knapp die Hälfte der Fehler ist nicht eindeutig klassifizierbar**, weil die
   Zahl zwar wörtlich im Artikel steht, die Zuordnung zu Zeile, Spalte oder
   Zeitpunkt aus den vorhandenen Daten aber nicht belegbar ist. Diese Fälle
   sind der Kern der menschlichen Prüfung, nicht der Prompt-Arbeit.

## 2. Fehlerverteilung nach Modell

Nur Referenzversion `v2_timepoint`:

| Klasse | glm-5.3 | qwen3-30b |
|---|---|---|
| Nicht eindeutig | 12 | 88 |
| Zahl nicht extrahiert | 14 | 86 |
| Unvollständige Antwort | 24 | 4 |
| Falsche Tabellenzeile | 0 | 4 |
| Prozentwert statt absolut | 3 | 0 |
| Falscher Messzeitpunkt | 0 | 0 |
| Halluzinierter Wert | 0 | 0 |

Die Profile sind gegensätzlich. glm liest fast alles, was es findet, richtig,
bricht aber bei schwierigen Tabellen ganz ab (Reasoning-Schleife, 24 Zellen
ohne jede Antwort). qwen3-30b antwortet fast immer, lässt aber ein Drittel der
Zellen weg und liefert viele Werte, die zwar im Artikel stehen, aber nicht zur
gesuchten Zeile gehören (88 nicht eindeutig).

Ein technisches Detail: In der Referenzversion gibt es **107 zusätzliche Zellen
ohne Gold-Pendant**, davon 88 von qwen3-30b — überwiegend für die 5 Records, in
denen der Annotator keine Zahlen gefunden hat. Das drückt die Precision, ist aber
inhaltlich ungeklärt: Ob dort wirklich keine Zahlen stehen oder der Gold-Stand
unvollständig ist, kann nur eine Sichtprüfung entscheiden.

## 3. Fehlerverteilung nach Feld

| Feld | häufigste Klassen |
|---|---|
| intervention_group_size | nicht extrahiert (43), unvollständig (6) |
| comparator_group_size | nicht extrahiert (43), unvollständig (6) |
| intervention_mean | nicht eindeutig (23), unvollständig (4) |
| intervention_standard_deviation | nicht eindeutig (18), unvollständig (4), Tabellenzeile (2) |
| comparator_mean | nicht eindeutig (22), unvollständig (4) |
| comparator_standard_deviation | nicht eindeutig (18), unvollständig (4) |
| intervention_events | nicht eindeutig (10), nicht extrahiert (4) |
| comparator_events | nicht eindeutig (5), Prozent (3), Tabellenzeile (2) |

Die Gruppengrößen sind der größte Einzelposten — aber ausschließlich als
**fehlende** Zellen (86 fehlende Gruppengrößen-Zellen in der
Referenzversion), nicht als falsche. Werden sie geliefert, sind sie fast immer
richtig. Bei Mittelwerten und
Streuungen ist es umgekehrt: Sie werden geliefert, aber häufig aus der falschen
Zeile.

## 4. Ereigniszahlen im Detail

In der Referenzversion sind 26 Ereigniszellen fehlerhaft. Aufgeschlüsselt:

| Ursache | Anzahl | Beleg |
|---|---|---|
| nicht extrahiert / keine Antwort | 6 | Feld fehlt in der Antwort |
| Prozentwert statt absoluter Zahl | 3 | Ereignisrate stimmt auf 0,1 Prozent |
| falsche Tabellenzeile | 2 | Wert entspricht einer anderen Outcome-Zeile |
| nicht eindeutig (Wert steht im Text) | 15 | Zeile/Spalte nicht belegbar |

**Die vermuteten Hauptursachen bestätigen sich nicht:**

- *Ereignisse mit Teilnehmerzahl verwechselt:* 0 Fälle. In keinem Fall
  entspricht die Vorhersage einer Gruppengröße.
- *Arme verwechselt:* 0 Fälle über alle Läufe.
- *ITT vs. Per-Protocol:* nicht prüfbar, weil die Records keine
  Populationangabe tragen; kein Fall zeigt zwei konkurrierende
  Populationsgrößen.
- *Mehrere Ereignisdefinitionen:* in den geprüften Fällen nicht erkennbar.

**Was sich belegen lässt:**

- In `yun2024:191` sagt der Artikel 64 von 133 Kontrollteilnehmern; glm
  antwortet 48 — genau 48,1 %, also die Rate. Dasselbe Muster in zwei weiteren
  Zellen. Das ist ein echter Prompt-Fix-Kandidat („Zahlen als absolute Anzahl,
  nicht als Prozent").
- In `yun2024:190` liefert glm 64/73 statt 52/51 (Gruppen 125/133). Die
  Vorhersagen stehen wörtlich im Artikel, gehören aber zu einer anderen Zeile
  oder einem anderen Zeitpunkt; das ist ohne Tabellenkontext nicht
  entscheidbar.
- qwen3-30b liefert in `yun2024:120` für die Kontrolle 8 statt 13; die 8 ist die
  Interventions-Ereigniszahl derselben Zeile — ein Zeilen-/Spaltenversatz
  innerhalb derselben Tabelle.

Der Restfehler bei glm (Recall 0,75 auf Ereignissen) ist damit **nicht** ein
Verständnisproblem der Begriffe, sondern ein Zuordnungsproblem bei mehrzeiligen
Tabellen — plus ein Prozentproblem, das sich billig beheben lässt.

## 5. Gold-Datenqualität

Geprüft wurden alle 170 Gold-Zellen gegen den Artikeltext: wörtliches Vorkommen
(inklusive Dezimalkomma, Tausendertrennzeichen und Unicode-Minus),
Plausibilität (Ereignisse ≤ Gruppengröße) und offensichtliche Mehrdeutigkeit.

Ergebnis: **169 von 170 Zellen sind wörtlich im Artikel belegt.** Eine Zelle
braucht eine menschliche Entscheidung:

| Record | Feld | Gold | Befund |
|---|---|---|---|
| `yun2024:3` | intervention_mean | 50,6 | Artikel nennt an einer Stelle 50,6 gm, an einer anderen 50,7 gm für denselben Wert. Gold nutzt 50,6; glm antwortet 50,7 und wird dafür als Fehler gezählt. |

Der Fall `comparator_mean` = −0,7 im selben Record war zunächst auffällig, weil
der Artikel „− 0,7 gm" mit Leerzeichen schreibt; nach Normalisierung (Unicode-
Minus, Leerzeichen, Dezimalkomma) ist der Wert belegt und unauffällig. Genau
dafür prüft das Modul mehrere Schreibweisen.

Die 50,6/50,7-Dopplung ist ein Selbstwiderspruch des Artikels, kein
Annotationsfehler — der Annotator hat eine der beiden Stellen gewählt. Solche
Fälle sind für den Benchmark wichtig, weil sie die Obergrenze der erreichbaren
Genauigkeit senken und bei der Bewertung als Modellfehler erscheinen.

Nicht geprüft werden konnte: Zeitpunkt-, Populations- und Armangaben, weil die
Records diese Metadaten nicht führen (`zeitpunkt`/`population` stehen in
`error_cases.csv` deshalb als „nicht erfasst"). Diese Lücke ist selbst ein
Befund: Ohne Zeitpunkt im Datensatz ist die Annotation für Dritte nicht
nachvollziehbar.

## 6. Technische Probleme

1. **Gateway-Cache.** Ein Lauf lieferte 86 Antworten in unter 0,2 s, davon 84
   zeichengleich mit dem vorherigen Lauf. Solche Läufe sind keine Messpunkte,
   werden aber als `suspected_cache` markiert und im Bericht getrennt geführt.
   `--cache-buster` erzwingt frische Generierung (eigene Prompt-Version).
2. **Reasoning-Schleifen.** glm verbraucht bei großen Tabellen das gesamte
   Tokenbudget ohne Inhalt (`finish_reason = "length"`, bis 138.000 Zeichen
   Reasoning). Ein Retry mit 32.000 Token rettet zwei von drei Fällen; der
   dritte widersetzt sich auch dort.
3. **Leere Antworten sind nicht gleich Fehler.** Zwei Records haben 0
   Gold-Zellen; die leere Antwort ist dort korrekt. Technische Ausfälle (40
   Zellen) sind von inhaltlichen Fehlern getrennt ausgewiesen.
4. **Fehlende Zeitpunkt-/Populationsmetadaten** in den Records (siehe oben).
5. **Kein Parserfehler**: Alle nicht-leeren Antworten waren maschinell lesbar.
6. **Uneinheitliche Versionsnamen.** Dieselbe Prompt-Fassung hieß je nach Lauf
   `v2_timepoint`, `v2b_cachebuster` oder `v2_timepoint_cb`. `versions.py`
   bildet alle Schreibweisen auf drei kanonische Versionen ab (`v1`,
   `v2_timepoint`, `v3_abs_count`); Analysen und Übersichten nutzen diese
   Zuordnung, die Rohdaten der Läufe bleiben unverändert.

## 7. Menschlich zu prüfende Fälle

`human_review_queue.csv` enthält 505 Einträge mit Prüfstatus `offen` und einer
Spalte `prompt_version`, damit Referenz- und verworfene Fälle getrennt geprüft
werden können:

| Priorität | Anzahl | Inhalt |
|---|---|---|
| 1 | 26 | falsche Ereigniszahlen |
| 2 | 182 | fehlende Zellen |
| 3 | 24 | große Abweichungen (≥ 5 absolut) |
| 4 | 155 | mehrdeutige Zuordnung / sonstige Fehler |
| 5 | 118 | zufällige korrekte Kontrollfälle |

Jeder Eintrag enthält Record, Feld, Arm, Gold, Vorhersage, Quelle (PMCID und
Dateipfad), Fehlerhypothese und Prüfstatus. Wichtig: Die Prüfung dient der
Qualitätssicherung, **nicht** dem Anpassen der Gold-Daten an Modellantworten.
Ergänzend sind die 5 Records ohne Gold-Zellen zu prüfen, in denen qwen3-30b
Werte liefert.

## 8. Priorisierte Verbesserungsmaßnahmen

| Rang | Maßnahme | erwartete Wirkung | Aufwand |
|---|---|---|---|
| 1 | Prompt: „Ereignisse als absolute Anzahl, nicht als Prozent" | behebt belegte 3 Fälle, verhindert die Klasse | Minuten |
| 2 | Prompt: Tabellenzeile explizit benennen lassen (Outcome-Name aus dem Record) und in der Antwort mitliefern | adressiert 15 mehrdeutige Ereigniszellen und 100 mehrdeutige Zellen der Referenzversion | Stunden |
| 3 | Retry-Regel beibehalten (32.000 Token) | +12 Zellen Abdeckung bei glm, belegt | erledigt |
| 4 | Zeitpunkt- und Populationsfeld in die Records aufnehmen | macht Annotation prüfbar, verhindert Zeitpunktfehler strukturell | Stunden + Nachannotation |
| 5 | Technische Validierung: Ereignisse ≤ Gruppengröße, Prozentwerte erkennen | fängt 3–5 Fehler automatisch, ohne Modell | Stunden |
| 6 | Tabellen separat übergeben statt Volltext | größter Hebel bei mehrzeiligen Tabellen, aber größter Umbau | Tage |

## 9. Konzept für die nächste Benchmark-Iteration

### Bewertung der Ansätze

**A. Bessere Prompts (Zeitpunkt, Population, Arm).** Zeitpunkt ist belegt
wirksam (MAE 3,76 → 0,41 bei glm, F1 0,708 → 0,945). Population ist in den
Daten nicht vorhanden, ein Prompt-Zusatz daher wirkungslos, solange die Records
sie nicht führen. Armangabe ist bereits im Prompt und die Verwechslungsrate 0.
Erwartung: kleiner Zusatzgewinn (Prozentregel), sonst ausgeschöpft.
Aufwand: Minuten. Risiko: gering, aber jede Änderung braucht eine neue
Prompt-Version, sonst sind Läufe nicht vergleichbar.

**B. Strukturierte Tabellenübergabe.** Die Fehler konzentrieren sich auf
mehrzeilige Tabellen (PMC5498715, `yun2024:190`). Wenn Zeilen und Spalten als
Markdown mit Kopfzeile übergeben werden, verschwindet ein Teil der
Zuordnungsfehler. Erwartung: hoch für Tabellenrecords, aber der Anteil solcher
Records im Dev-Satz ist klein (1 Artikel mit 15 Records). Aufwand: mittel bis
hoch (Tabellenextraktion aus Markdown/XHTML, Spaltenzuordnung).
Risiko: neue Fehler durch falsch geparste Tabellen; ohne Vergleichslauf nicht
abschätzbar.

**C. Mehrstufige Extraktion (Tabelle → Zeile/Spalte → Zahl → Prüfung).**
Passend zum Befund: Der Fehler ist die Zuordnung, nicht das Lesen. Ein
zweiter Schritt („welche Zeile, welche Spalte, welcher Zeitpunkt?") macht die
Entscheidung explizit und prüfbar. Erwartung: höchster inhaltlicher Hebel,
insbesondere für die 100 mehrdeutigen Zellen der Referenzversion. Aufwand: hoch (mehrere Aufrufe
pro Record, Verdrahtung, Auswertung). Rechenaufwand: 2–3× pro Record.
Risiko: Fehlerfortpflanzung zwischen Stufen; Zwischenergebnisse müssen
mitgespeichert und separat bewertet werden.

**D. Fine-Tuning.** Siehe Abschnitt 10: derzeit nicht sinnvoll.

**E. Regelbasierte Validierung.** Ereignisse ≤ Gruppengröße, Rate statt
Absolutzahl erkennen, Mittelwert/Streuung vertauscht erkennen. Erwartung:
fängt einen kleinen, klar benannten Teil der Fehler (3–8 Zellen), verhindert
aber, dass sie als Modellfehler durchgehen. Aufwand: gering. Risiko: gering,
solange die Validierung nur markiert und nicht korrigiert.

### Vorschlag für die Reihenfolge

1. Prompt-Regel „absolute Anzahl" + Validierung (E) — ein Nachmittag, belegter
   Nutzen, keine Strukturänderung.
2. Mehrstufige Extraktion (C) auf dem bestehenden Dev-Satz prototypisch, mit
   Zwischenergebnissen im Predictions-Format.
3. Erst danach Tabellenübergabe (B) — sie ist nur sinnvoll, wenn C zeigt, dass
   die Zeilenwahl das Problem ist und nicht das Tabellenformat.

## 10. Datenerweiterung und Fine-Tuning

### Datensatz (Aufgabe G)

Der Dev-Satz hat 43 Records, 38 davon mit Zahlen, und stammt aus einem Artikel
zu 40 %. Für belastbare Aussagen braucht es mehrere hundert Records.

Vorschlag:

- **Quelle**: PMC Open Access über den vorhandenen Downloader
  (`download_pmc_oa.py`, S3-Bucket `pmc-oa-opendata`, Lizenzfilter CC BY /
  CC BY-NC). Kein neuer Anbieter, keine neue Rechtsgrundlage.
- **Umfang**: 400–600 Records aus 200–300 Artikeln, Ziel 1500–2000 Zellen.
- **Schichtung**: randomisiert vs. quasi-experimentell, binär vs. kontinuierlich,
  ein vs. mehrere Arme, Tabelle vs. Fließtext, ein vs. mehrere Zeitpunkte.
  Diese Schichten sind genau die Fehlerdimensionen aus Abschnitt 4.
- **Annotation**: zwei unabhängige Annotatoren für 15 % der Records, Cohen's
  Kappa als Gütekriterium; Konflikte werden aufgelöst, nicht gemittelt.
  Pflichtfelder je Zelle: Zeitpunkt, Population, Arm, Quelle (Tabelle/Seite).
- **Trennung**: Der Dev-Satz bleibt reine Evaluation. Trainings- und
  Few-Shot-Beispiele kommen ausschließlich aus einem neuen Trainingssplit
  anderer Artikel. Der eingefrorene Satz (249 Records) und der Quell-Testsplit
  (407 Records) bleiben gesperrt.
- **Reihenfolge**: erst 50 Records als Pilot annotieren, Kappa messen, dann
  skalieren — sonst wird ein Annotationsschema skaliert, das nicht trägt.

### Fine-Tuning (Aufgabe D)

**Derzeit nicht sinnvoll.** Begründung aus den Daten:

- Die Fehler sind überwiegend Zuordnungs- und Abdeckungsfehler, keine
  Formulierungsfehler. Fine-Tuning verbessert die Formulierung, nicht das
  Tabellenverständnis.
- Mit 38 Records mit Zahlen ist jede Fine-Tuning-Abschätzung Rauschen.
- Ein fine-getuntes Modell auf dem Dev-Satz würde genau die 38 Records
  optimieren, auf denen wir messen — der Erfolg wäre nicht auf ungesehene
  Records übertragbar, und genau das verlangt die Arbeitsregel.

Sinnvoll wird es frühestens bei 300+ annotierten Records aus dem neuen
Trainingssplit, mit einem echten Holdout und einem Vergleich gegen den
Prompt-Stand, nicht gegen den Ausgangspunkt. Bis dahin gilt: Prompt und
mehrstufige Extraktion zuerst, Fine-Tuning als letzte Stufe.

## Technische Umsetzung

- `analyze_errors.py` liest nur; es schreibt ausschließlich nach `analysis/`.
  Bestehende Läufe und Metriken werden nicht verändert.
- Die Metriken werden beim Lauf neu berechnet und gegen `eval/*.metrics.json`
  geprüft; Abweichungen würden den Lauf mit `metriken_identisch: false`
  markieren (aktuell in allen Läufen `true`).
- Tests: `public_benchmark/tests/test_analyze_errors.py` (13 Tests) deckt
  Zahlenvarianten, Unicode-Minus, Tausendertrennzeichen, alle
  Klassifikationsregeln, die Trennung technisch/inhaltlich, die Gold-Prüfung
  und die Priorisierung der Prüfqueue ab.
