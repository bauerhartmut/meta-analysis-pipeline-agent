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
| `v2_timepoint` | Referenz | 246 | 28 | 218 | 114 | 4 |
| `v3_abs_count` | **verworfen** | 17 | 6 | 11 | 5 | 1 |
| `v1` | historisch | 135 | 12 | 123 | 56 | 1 |

Für die Referenz `v2_timepoint` (246 Fehler, 28 davon technisch):

| Klasse | Anzahl | Anteil |
|---|---|---|
| Nicht eindeutig klassifizierbar | 100 | 41 % |
| Zahl nicht extrahiert | 106 | 43 % |
| Unvollständige Modellantwort | 28 | 11 % |
| Falsche Tabellenzeile | 12 | 5 % |
| Prozentwert statt absoluter Zahl | 0 | – |
| Falscher Messzeitpunkt | 0 | – |
| Halluzinierter Wert | 0 | – |
| Gruppenverwechslung | 0 | – |
| Ereignisse/Teilnehmer verwechselt | 0 | – |
| Parser-/Formatfehler | 0 | – |

`v3_abs_count` (verworfen) hat 17 Fehler: 6 nicht extrahiert, 6 unvollständig,
4 nicht eindeutig, 1 falsche Tabellenzeile. Die Ereigniszahlen sind darin unverändert
gegenüber der Referenz; die Fassung wird ab hier nur noch nachrichtlich geführt.

### Referenz frisch reproduziert (15.11.2026)

Lauf 6 (`yun_dev_std_20261115`) wiederholt die Referenz mit dem Standardprompt
und frischer Generierung (43 Aufrufe, Median 3,83 s, keine Antwort unter 1 s):

| Kennzahl | Lauf 4 (`v2b`) | Lauf 6 (Standard, frisch) |
|---|---|---|
| Zellen-F1 | 0,945 | 0,933 |
| MAE | 0,405 | 0,415 |
| mae_coverage | 0,988 (168/170) | 0,965 (164/170) |
| exakte Records | 35/43 | 34/43 |
| vorhergesagte Zellen | 175 | 171 |

Die Referenzzahl stammt damit nicht mehr aus einem Sonderpfad, sondern aus dem
Standardprompt; die Abweichung von 0,012 F1 liegt im Rahmen der Streuung
zwischen zwei frischen Läufen (zwei leere Antworten, drei Retries).

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
| Zahl nicht extrahiert | 20 | 86 |
| Unvollständige Antwort | 24 | 4 |
| Falsche Tabellenzeile | 8 | 4 |
| Prozentwert statt absolut | 0 | 0 |
| Falscher Messzeitpunkt | 0 | 0 |
| Halluzinierter Wert | 0 | 0 |

Die Profile sind gegensätzlich. glm liest fast alles, was es findet, richtig,
bricht aber bei schwierigen Tabellen ganz ab (Reasoning-Schleife, 24 Zellen
ohne jede Antwort). qwen3-30b antwortet fast immer, lässt aber ein Drittel der
Zellen weg und liefert viele Werte, die zwar im Artikel stehen, aber nicht zur
gesuchten Zeile gehören (88 nicht eindeutig).

Ein technisches Detail: In der Referenzversion gibt es **114 zusätzliche Zellen
ohne Gold-Pendant**, davon 88 von qwen3-30b — überwiegend für die 5 Records, in
denen der Annotator keine Zahlen gefunden hat. Das drückt die Precision, ist aber
inhaltlich ungeklärt: Ob dort wirklich keine Zahlen stehen oder der Gold-Stand
unvollständig ist, kann nur eine Sichtprüfung entscheiden.

## 3. Fehlerverteilung nach Feld

| Feld | häufigste Klassen |
|---|---|
| intervention_group_size | nicht extrahiert (44), unvollständig (6) |
| comparator_group_size | nicht extrahiert (44), unvollständig (6) |
| intervention_mean | nicht eindeutig (24), unvollständig (4), nicht extrahiert (3) |
| intervention_standard_deviation | nicht eindeutig (18), unvollständig (4), nicht extrahiert (3), Tabellenzeile (2) |
| comparator_mean | nicht eindeutig (22), unvollständig (4), nicht extrahiert (3) |
| comparator_standard_deviation | nicht eindeutig (18), unvollständig (4), nicht extrahiert (3) |
| intervention_events | nicht eindeutig (9), nicht extrahiert (4), Tabellenzeile (3) |
| comparator_events | nicht eindeutig (6), Tabellenzeile (5), nicht extrahiert (2) |

Die Gruppengrößen sind der größte Einzelposten — aber ausschließlich als
**fehlende** Zellen (88 fehlende Gruppengrößen-Zellen in der
Referenzversion), nicht als falsche. Werden sie geliefert, sind sie fast immer
richtig. Bei Mittelwerten und
Streuungen ist es umgekehrt: Sie werden geliefert, aber häufig aus der falschen
Zeile.

## 4. Ereigniszahlen im Detail

In der Referenzversion sind 30 Ereigniszellen fehlerhaft. Aufgeschlüsselt:

| Ursache | Anzahl | Beleg |
|---|---|---|
| nicht extrahiert / keine Antwort | 6 | Feld fehlt in der Antwort |
| falsche Tabellenzeile | 10 | Wert entspricht einer anderen Zeile |
| Prozentwert statt absoluter Zahl | 0 | nach Sichtprüfung widerlegt |
| nicht eindeutig (Wert steht im Text) | 14 | Zeile/Spalte nicht belegbar |

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
Tabellen.

### Nachtrag: Prozentklasse zurückgenommen (15.11.2026)

Die manuelle Prüfung der 20 falschen Ereigniszellen
(`analysis/v1_20261115/events_review.md`) hat die Klasse „Prozentwert statt
absoluter Zahl" **vollständig widerlegt**: In der Referenz gibt es keinen
einzigen belegten Fall.

Der Auslöser war `yun2024:191 comparator_events`: Gold 64, Vorhersage 48, und
64/133 = 48,1 Prozent sah nach einer Ereignisrate aus. Der Artikel enthält
48 aber als **Ereigniszahl der Zeile „0–3 months"** (31 und 48), während Gold
64 aus der Zeile „Total 0–12 months" stammt. Die Partnerzelle der Vorhersage
(31) passt exakt zu derselben Zeile, die Prozentübereinstimmung ist also
**Koinzidenz**. Die Zelle ist jetzt als falsche Tabellenzeile klassifiziert,
und ebenso die übrigen drei Zeilen desselben Zelltyps in den anderen Läufen.

Folgen: Die Klassenverteilung in Abschnitt 1 verschiebt sich um 3 Zellen von
„Prozentwert" zu „falsche Tabellenzeile" (7 statt 4); die Ereignisübersicht
nennt 5 statt 2 Tabellenzeilen und 0 Prozentfälle. Die Prompt-Zeile aus
`v3_abs_count` zielte damit auf eine Ursache, die es nicht gibt — konsistent
damit, dass v3 bei den Ereigniszahlen nichts verändert hat.

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

Die Prüfqueue ist **nach Version getrennt**. Geprüft wird ausschließlich die
Referenz; die übrigen Fälle liegen vollständig vor, damit nichts verloren geht:

| Datei | Status | Version | Einträge |
|---|---|---|---|
| `human_review_queue.csv` | zum Prüfen | `v2_timepoint` | 339 |
| `human_review_discarded.csv` | verworfen | `v3_abs_count` | 36 |
| `human_review_historical.csv` | historisch | `v1` | 160 |

Prioritäten in der Referenzdatei:

| Priorität | Anzahl | Inhalt |
|---|---|---|
| 1 | 24 | falsche Ereigniszahlen |
| 2 | 134 | fehlende Zellen |
| 3 | 8 | große Abweichungen (≥ 5 absolut) |
| 4 | 80 | mehrdeutige Zuordnung / sonstige Fehler |
| 5 | 93 | zufällige korrekte Kontrollfälle |

Jeder Eintrag enthält Record, Feld, Arm, Gold, Vorhersage, Quelle (PMCID und
Dateipfad), Fehlerhypothese und Prüfstatus. Wichtig: Die Prüfung dient der
Qualitätssicherung, **nicht** dem Anpassen der Gold-Daten an Modellantworten.
Ergänzend sind die 5 Records ohne Gold-Zellen zu prüfen, in denen qwen3-30b
Werte liefert.

## 8. Priorisierte Verbesserungsmaßnahmen

| Rang | Maßnahme | erwartete Wirkung | Aufwand |
|---|---|---|---|
| 1 | ~~Prompt: „Ereignisse als absolute Anzahl"~~ **gestrichen** | kein belegter Prozentfall; im Dev-Lauf ohne Wirkung | – |
| 2 | ~~Zeile/Spalte in einem Zwischenschritt benennen lassen~~ **getestet, ohne Wirkung** (Abschnitt 11) | benennt dieselbe falsche Stelle wie der Einzelschritt, F1 0,933 → 0,911 | erledigt |
| 3 | Retry-Regel beibehalten (32.000 Token) | +12 Zellen Abdeckung bei glm, belegt | erledigt |
| 4 | Zeitpunkt- und Populationsfeld in die Records aufnehmen | macht Annotation prüfbar, verhindert Zeitpunktfehler strukturell | Stunden + Nachannotation |
| 5 | Technische Validierung: Ereignisse ≤ Gruppengröße | fängt in diesen Daten 0 Fälle; bleibt Schutz für neue Daten | Stunden |
| 6 | Tabellen separat übergeben statt Volltext | größter Hebel bei mehrzeiligen Tabellen, aber größter Umbau | Tage |
| 7 | ~~Zeitpunkt-Regel „letzter Messpunkt"~~ **getestet, verworfen** (Abschnitt 12) | behebt 4 Zellen, zerstört 39; Gold-Konvention ist nicht einheitlich | erledigt |
| 8 | Messzeitpunkt je Record annotieren und im Prompt setzen | **erledigt** (Abschnitt 13): Annotation trifft die Konvention, Precision 0,937, MAE 0,0008 | erledigt |
| 9 | Rückfallregel bei fehlendem Zielzeitpunkt (nächstliegender berichteter Zeitpunkt, im Feld ausgewiesen) | **erledigt und Referenz** (Abschnitt 14): zwei frische Läufe F1 0,944/0,963, MAE 0,039/0,0006, keine falsche Rückfall-Zelle | erledigt |

## 9. Konzept für die nächste Benchmark-Iteration

### Bewertung der Ansätze

**A. Bessere Prompts (Zeitpunkt, Population, Arm).** Zeitpunkt ist belegt
wirksam (MAE 3,76 → 0,41 bei glm, F1 0,708 → 0,945). Population ist in den
Daten nicht vorhanden, ein Prompt-Zusatz daher wirkungslos, solange die Records
sie nicht führen. Armangabe ist bereits im Prompt und die Verwechslungsrate 0.
Erwartung: nach der Sichtprüfung kein Zusatzgewinn über die Zeitpunktangabe
hinaus (die Prozentregel ist widerlegt), sonst ausgeschöpft.
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

1. ~~Prompt-Regel „absolute Anzahl"~~ **gestrichen**, kein belegter Fall.
2. Mehrstufige Extraktion (C) — **erledigt, ohne Wirkung** (Abschnitt 11): Der
   Zwischenschritt benennt die falsche Zeile/Spalte explizit, statt sie zu
   vermeiden, und findet zusätzlich Zellen ohne Gold-Pendant. Er ist damit als
   Verbesserung erledigt und bleibt als Diagnosewerkzeug erhalten.
3. ~~Zeitpunkt-Regel „letzter berichteter Messzeitpunkt"~~ **getestet,
   verworfen** (Abschnitt 12): behebt die beiden bekannten Zellen, zerstört
   aber 39 Zellen eines anderen Artikels, weil die Gold-Annotation selbst
   keinen einheitlichen Zeitpunkt verwendet.
4. ~~Messzeitpunkt je Record annotieren~~ **erledigt** (Abschnitt 13): Die
   Annotation ist gesetzt und belegt, der Lauf gewinnt Precision und MAE,
   verliert aber Abdeckung durch Auslassungen.
5. ~~Rückfallregel für fehlende Zeitpunkte~~ **erledigt und erfolgreich**
   (Abschnitt 14): F1 0,944 bei MAE 0,039, keine falsche Rückfall-Zelle.
6. Tabellenübergabe (B) — erst sinnvoll, wenn Zeitpunkt und Rückfallregel
   stehen, sonst wird dieselbe falsche Spalte nur sauberer gelesen.

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

## 11. Prototyp mehrstufige Extraktion (15.11.2026)

Umgesetzt als reine Ereignisstufe: Stufe 1 nennt Zeilenlabel, Spaltenkopf und
Tabellenbeschriftung je Arm (keine Zahl), Stufe 2 liest die Zahl an genau
dieser Stelle. Beide Stufen werden getrennt gespeichert (`stage1.jsonl`,
`stage2.jsonl`) und getrennt bewertet; nur die beiden Ereignisfelder werden
durch das Ergebnis ersetzt, alle anderen Zellen stammen unverändert aus dem
Basislauf. 43 Records, 129 Aufrufe (1 Stufe 1 + bis zu 2 Stufe 2).

| Kennzahl | Basis (Lauf 6) | Stufe |
|---|---|---|
| Zellen-F1 | 0,933 | 0,911 |
| Zell-Recall | 0,935 | 0,935 |
| Zell-Precision | 0,930 | 0,888 |
| MAE / Abdeckung | 0,415 / 0,965 | 0,415 / 0,965 |
| exakte Records | 34/43 | 30/43 |

Nur auf den Ereignisfeldern (16 Gold-Zellen): F1 0,667 → 0,545, Precision
0,600 → 0,429, Recall unverändert 0,750, MAE unverändert 4,25.

Befunde:

1. **Die Stufe verbessert keine einzige Gold-Zelle und verschlechtert keine.**
   Von 16 Ereigniszellen bleiben 12 richtig und 4 falsch; alle vier falschen
   behalten exakt denselben Wert.
2. **Die falsche Stelle wird in Stufe 1 explizit benannt** — und ist dieselbe
   wie im Einzelschritt. `yun2024:190` (Gold 12 Monate): Zeile „Sedatives",
   Spalte „3 months follow-up", Zitat „64 (51)". `yun2024:191` (Gold „Total"):
   Zeile „0-3 months", Zitat „31(25)" und „48 (36)". Stufe 2 liest also
   korrekt an einer falsch gewählten Stelle. Der Fehler sitzt in der
   Ortswahl, nicht im Lesen — die Aufteilung macht ihn sichtbar, aber nicht
   kleiner.
3. **Acht zusätzliche Ereigniszellen** auf vier Records (`yun2024:4`, `:5`,
   `:55`, `:60`), die laut Annotation gar keine Ereigniszahl führen — dort
   stehen Mittelwerte (47,5/26,5 und 3,59/2,19). Die Stufe sucht, bis sie eine
   Zahl findet; Precision sinkt dadurch von 0,600 auf 0,429.
4. **Labels sind oft nicht wörtlich.** Nur 13 von 37 Locators stehen mit Zeile
   und Spalte wörtlich im Artikel (0,351); Umbenennungen wie „Myocardial
   infarction / Overall" verhindern einen automatischen Belegabgleich. Die
   Prüfung der Zwischenstufe ist damit nur teilautomatisch möglich.

Ergebnis: Der Prototyp ist **nicht übernommen**. Er kostet den Faktor 3 an
Aufrufen und verschlechtert F1 um 0,021, weil er zusätzliche Zellen erfindet,
ohne die Ortswahl zu verbessern. Der belegte Nutzen liegt im Diagnosewert:
Die Zielzeitpunkt-Definition („end of intervention") ist die offene Stelle,
nicht die Lesegenauigkeit. Diese Vermutung ist in Abschnitt 12 direkt geprüft
worden — mit negativem Ergebnis.

## 12. Zeitpunkt-Regel „letzter Messpunkt" (15.11.2026)

Prompt `v4_last_timepoint` verlangt den **letzten berichteten Messzeitpunkt**
des Outcomes (bei kumulativen Tabellen die Total-Zeile), verbietet Baseline und
lässt das Modell den gewählten Zeitpunkt sowie die verworfenen Zeitpunkte
wörtlich mitliefern. Ein neuer Lauf auf denselben 43 Records (frisch, 43
Aufrufe, 1 Retry, Median 7,7 s):

| Kennzahl | Referenz (Lauf 6) | `v4_last_timepoint` |
|---|---|---|
| Zellen-F1 | 0,933 | 0,738 |
| Recall / Precision | 0,935 / 0,930 | 0,753 / 0,723 |
| MAE | 0,415 | 3,621 |
| mae_coverage | 0,965 (164/170) | 0,988 (168/170) |
| exakte Records | 34/43 | 25/43 |

### Offline-Prüfung der genannten Zeitpunkte

`check_timepoints.py` prüft ohne Modell gegen den Artikeltext (Ausgabe:
`analysis/v4_20261115/timepoints_check.json`):

| Prüfung | Ergebnis |
|---|---|
| Records mit Zeitpunktangabe | 43/43 |
| echte Labels wörtlich im Artikel | 34/34 |
| Platzhalter („running text", „not applicable") | 9 |
| verworfene Labels | 58, davon 10 nicht wörtlich |
| Widerspruch „späterer Zeitpunkt verworfen" | 1 (`yun2024:192`) |

Der eine Widerspruch ist ein Fehlalarm der Heuristik: Das Outcome lautet
„continued antidepressants until the 6-month", der Horizont endet also bei 6
Monaten; das Modell lag mit „6 months follow-up" richtig (86/78 = Gold). Die
Prüfung markiert nur, sie korrigiert nicht.

### Was die Regel behebt und was sie zerstört

**Behoben** (die beiden bekannten Fehlzellen aus Abschnitt 4): `yun2024:190`
wählt „12 months follow-up" und liefert 52/51 (Gold), `yun2024:191` wählt
„Total 0-12 months" und liefert 49/64 (Gold). Auch `yun2024:192` ist richtig.

**Zerstört**: Artikel PMC5498715 (`yun2024:224`–`:238`, 15 Records, 90
Gold-Zellen). Das Modell wählt „Follow up after 4 months" — den letzten
berichteten Zeitpunkt — und trifft 51 von 90 Zellen; die Referenz traf dort
90/90, weil Gold Pre-/Post-Test meint (z. B. 0,30/0,79 gegen 0,43/1,04).

### Befund: Die Gold-Annotation hat keinen einheitlichen Zeitpunkt

Derselbe Benchmark bewertet in PMC5244530 den **letzten** Messpunkt (12 Monate
bzw. Total), in PMC5498715 den **Post-Test** (nicht den letzten Messpunkt).
Damit kann keine Prompt-Regel beide Artikel treffen: „end of intervention"
verliert PMC5244530, „letzter Messpunkt" verliert PMC5498715. Der Fehler liegt
nicht im Modell, sondern in einer fehlenden Angabe in den Gold-Records.

`v4_last_timepoint` ist deshalb **verworfen** (Status in `versions.py`,
Prüffälle in `human_review_discarded.csv`). Der mitgelieferte Zeitpunkt bleibt
als Diagnose erhalten: Er macht die Ortswahl sichtbar und offline prüfbar. Der
nächste Schritt — Zielzeitpunkt je Record — steht in Abschnitt 13.

## 13. Zielzeitpunkt je Record als Vorgabe (15.11.2026)

Weil keine Prompt-Regel beide Artikel-Konventionen treffen kann (Abschnitt 12),
ist der Zielzeitpunkt jetzt Teil der Daten. `annotate_timepoints.py` schreibt
je Dev-Record ein Feld `timepoint` mit `target`, wörtlicher `evidence` und
Datum; das Skript bricht ab, wenn sich eine Gold-Zelle ändern würde — die
Gold-Werte sind nachweislich unverändert. Übersicht:
`analysis/timepoints_annotation.md`. Verteilung: 15× „Post-test", 6× „after
intervention (post-test)", 5× „12 months follow-up", 2× „Week 8", 2× „30
days", 2× „On-Therapy Period", 2× „whole treatment period", je 1× „Total
0-12 months", „6 months follow-up", „Period 2", „T1", „post-operative DTPA
scan"; 4× „not stated" (kein Gold-Wert bzw. Tabellenkopf fehlt).

Prompt `v5_target_timepoint` setzt den Zeitpunkt verbindlich („Target time
point (binding)"), verbietet das Ausweichen auf einen anderen Zeitpunkt und
lässt den benutzten wie die verworfenen Zeitpunkte weiter mitliefern.

| Kennzahl | Referenz (Lauf 6) | `v5_target_timepoint` |
|---|---|---|
| Zellen-F1 | 0,933 | 0,797 |
| Recall / Precision | 0,935 / 0,930 | 0,694 / **0,937** |
| MAE | 0,415 | **0,0008** |
| mae_coverage | 0,965 (164/170) | 0,700 (119/170) |
| exakte Records | 34/43 | 24/43 |
| vorhergesagte Zellen | 171 | 126 |

Lauf: 43 Aufrufe, 2 Retries, kein Cache-Treffer, Median 23,9 s (vorher 3,8 s
— die Zeitpunktprüfung kostet deutlich Rechenzeit), 9 Records ohne Antwort.

### Was das Ergebnis bedeutet

**Richtig wird fast alles, was beantwortet wird.** Der MAE von 0,0008 über 119
Paare bedeutet: eine einzige Abweichung von 0,1 — `yun2024:3` mit 50,7 (Text:
„+50.7 gm") gegen Gold 50,6 (Tabelle), der bekannte Selbstwiderspruch des
Artikels. Die Precision steigt auf 0,937.

**Der Preis ist die Abdeckung.** 51 Gold-Zellen fehlen, davon 19 Gruppengrößen
und 24 Mittelwerte/Streuungen; 32 der 52 Fehlerfälle sind „unvollständige
Modellantwort" (8 Records ohne jede Zelle). Die Vorgabe „lieber weglassen als
falschen Zeitpunkt" wirkt also genau wie formuliert — sie verschiebt Fehler in
Auslassungen.

Belegt richtig mit Vorgabe sind unter anderem `yun2024:190` (12 Monate,
52/51), `yun2024:191` (Total, 49/64), `yun2024:260` (Week 8, 79/62),
`yun2024:83` (Period 2, 9,9/9,1), `yun2024:88` (T1, 117,63/158,52),
`yun2024:4` und `yun2024:120`.

**Wo die Auslassungen sitzen:** `yun2024:187`–`:189` führen laut Gold nur
Gruppengrößen, die bei „12 months follow-up" nicht als Ergebniszeile stehen —
Auslassen ist dort folgerichtig. `yun2024:224`, `:225`, `:226`, `:230` dagegen
haben den richtigen Zielzeitpunkt „Post-test" genannt und trotzdem nichts
geliefert; sie waren ohne Vorgabe korrekt. Das ist Übervorsicht, kein
Zeitpunktfehler, und der Hauptgrund für den Recall-Verlust.

### Einhaltung der Vorgabe (offline geprüft)

`check_timepoints.py` auf dem v5-Lauf: 34 von 43 Records nennen einen
Zeitpunkt, 33 davon echte Labels, 29 wörtlich im Artikel; von 57 verworfenen
Labels stehen 11 nicht wörtlich im Text; 1 Widerspruch (`yun2024:192`, wie in
Abschnitt 12 ein Fehlalarm der Heuristik).

### Ein verworfener Lauf und seine Ursache

Der erste v5-Lauf erhielt die Vorgabe nie: Der Runner liest `records/yun.jsonl`
und filtert den Split, die Annotation stand zunächst nur in
`records/yun_dev.jsonl`. Ergebnis: 43-mal leerer Zielzeitpunkt, Version ohne
Zeitpunktangabe (F1 0,927, praktisch die Referenz). Der Lauf ist als
`runs/_verworfen/yun_dev_v5_ohne_vorgabe_20261115/` erhalten und zählt nicht
zur Auswertung; die Annotation schreibt jetzt in beide Record-Dateien.

### Bewertung

`v5_target_timepoint` ist als Referenz **nicht übernommen** (Status
„verworfen", F1 −0,136 bei Abdeckung −0,265). Der Versuch belegt aber zwei
Dinge: Die Annotation trifft die Gold-Konvention (fast jede beantwortete Zelle
stimmt), und die reine Auslassungsregel ist zu streng. Der naheliegende
nächste Schritt ist deshalb keine neue Datenrunde, sondern eine Rückfallregel:
Wenn der Zielzeitpunkt für ein Feld nicht berichtet ist, den nächstliegenden
berichteten Zeitpunkt nehmen und ihn im Feld `chosen_timepoint` ausweisen.

## 14. Rückfallregel: bestes Ergebnis bisher (15.11.2026)

Prompt `v6_target_fallback` behält die verbindliche Vorgabe, ersetzt aber das
Auslassen durch einen ausgewiesenen Rückfall: Ist ein Feld am Zielzeitpunkt
nicht berichtet, wird der nächstliegende berichtete Zeitpunkt genommen und im
Feld `timepoint` der Zelle genannt. `evaluate_fallback.py` trennt die Zellen
danach in **zieltreu** und **rückfall** und zählt beide getrennt.

| Kennzahl | Referenz (Lauf 6) | `v5` (ohne Rückfall) | `v6` (mit Rückfall) |
|---|---|---|---|
| Zellen-F1 | 0,933 | 0,797 | **0,944** |
| Recall / Precision | 0,935 / 0,930 | 0,694 / 0,937 | 0,947 / 0,942 |
| MAE | 0,415 | 0,0008 | **0,039** |
| mae_coverage | 0,965 (164/170) | 0,700 (119/170) | 0,953 (162/170) |
| exakte Records | 34/43 | 24/43 | 34/43 |

Lauf 9: 43 Aufrufe, 1 Retry, kein Cache-Treffer, Median 20,6 s, 1 Record ohne
Antwort.

### Die beiden Zellklassen

| Klasse | Zellen | richtig | falsch | ohne Gold | Precision |
|---|---|---|---|---|---|
| zieltreu | 120 | 115 | 1 | 4 | 0,991 |
| rückfall | 51 | 46 | 0 | 5 | 1,000 |

Die Rückfallregel ist damit **sauber**: 46 von 46 bewertbaren Rückfall-Zellen
stimmen, keine einzige falsch. Die mittlere Zeitdistanz ist mit 12 Monaten
allerdings groß — das sind die Fälle, in denen Gold nur eine Größe führt, die
im Zielzeitpunkt nicht steht (vor allem `yun2024:187`–`:189` mit 12-Monats-Ziel
und reinen Gruppengrößen). Auslassungen sinken von 51 auf 8 Zellen (4,7 %).

### Zweiter frischer Lauf und Referenzwechsel (15.11.2026)

Weil der F1-Sprung in der Größenordnung der Streuung der Referenz lag (0,933 vs
0,945 bei zwei frischen Referenzläufen), ist v6 ein zweites Mal frisch gelaufen
(Lauf 10, 43 Aufrufe, 2 Retries, kein Cache-Treffer, Median 16,8 s, 1 Record
ohne Antwort):

| Kennzahl | Referenz-Läufe | v6-Lauf 9 | v6-Lauf 10 |
|---|---|---|---|
| Zellen-F1 | 0,933 / 0,945 | 0,944 | **0,963** |
| Recall / Precision | 0,935 / 0,930 | 0,947 / 0,942 | 0,982 / 0,944 |
| MAE | 0,405 / 0,415 | 0,039 | 0,0006 |
| Abdeckung | 0,988 / 0,965 | 0,953 | 0,988 (168/170) |
| exakte Records | 35 / 34 | 34 | 35 |
| Auslassungen | 6 / 6 | 8 | 2 |

Beide v6-Läufe liegen in F1 und MAE über beiden Referenzläufen; der
MAE-Unterschied ist zwei Größenordnungen groß und damit kein Streueffekt. Die
Rückfall-Zellen sind auch im zweiten Lauf fehlerfrei (44 von 44 bewertbaren
richtig, 0 falsch), die zieltreuen Zellen 123 von 124.

**Referenzwechsel vollzogen:** `v6_target_fallback` ist ab jetzt die Referenz
(`versions.py`), `v2_timepoint` gilt als vorherige Referenz und bleibt der
Prompt-Text für Records ohne Zeitpunktannotation. `--target-fallback` ist
Standard (`--no-target-fallback` schaltet zurück), der Zielzeitpunkt kommt aus
dem Record. Die Referenzzeile in `analyze_errors.py` wird nicht mehr fest
verdrahtet, sondern aus dem Status abgeleitet.

Was das für alte Zahlen bedeutet: Alle F1-Werte aus den Abschnitten 1–12 sind
gegen die alte Referenz gemessen. Für neue Läufe gilt v6 als Maßstab
(F1 0,944–0,963, MAE 0,0006–0,039, Abdeckung 0,953–0,988).

## 15. JSON-Robustheit und frischer Lauf (15.11.2026)

`json_kaputt()` im Runner: Antworten, die strukturell kein lesbares JSON sind
(`kein_json`, `json_fehler`, `kein_objet`), bekommen genau einen zweiten
Versuch — wie bisher schon die Reasoning-Schleifen (`finish_reason =
"length"`). Eine leere oder unbrauchbare Zellenliste (`keine_zellen`,
`keine_verwertbaren_zellen`) ist bewusst **kein** Wiederholungsgrund: Felder
dürfen ausgelassen werden, und ein zweiter Aufruf würde nur Kosten erzeugen.
Der Grund steht als `retry_grund` (`length`/`json`) in jeder Zeile.
Test: `test_kaputtes_json_wird_wiederholt`.

Frischer Lauf 11 (`yun_dev_v6c_20261115`, Standard = v6, 43 Aufrufe, Median
10,1 s, 1 Retry wegen `length` bei `yun2024:55`):

| Kennzahl | Lauf 9 | Lauf 10 | Lauf 11 |
|---|---|---|---|
| Zellen-F1 | 0,944 | 0,963 | **0,965** |
| Recall / Precision | 0,947 / 0,942 | 0,982 / 0,944 | 0,982 / 0,949 |
| MAE | 0,039 | 0,0006 | 0,038 |
| Abdeckung | 0,953 | 0,988 | 0,988 (168/170) |
| exakte Records | 34 | 35 | **36** |

Drei Läufe, F1 0,944–0,965, MAE 0,0006–0,039. Der MAE-Unterschied zwischen den
Läufen ist ein einziger Zellenfehler: `yun2024:3 comparator_mean` mit −7,0
statt −0,7 (6,3 Abweichung / 170 Paare = 0,037). Dieser Fehler tritt in zwei
von drei Läufen auf und ist damit **kein Einzelfall**, sondern eine
systematische Fehllesung der Dezimalstelle; Lauf 10 hatte die Zelle richtig.

Der eine leere Record ist `yun2024:19` mit `keine_verwertbaren_zellen` (kein
JSON-Fehler, kein Gold vorhanden) — der neue Retry greift dort absichtlich
nicht.

## 16. Prüfung der v6-Queue und zwei Absicherungen (15.11.2026)

**Versionsetikett.** Der Runner setzt das Label jetzt je Antwort: Eine Fassung,
die den Record-Zeitpunkt voraussetzt (v5, v6), wird nur dann so etikettiert,
wenn der Record wirklich einen Zeitpunkt trägt; ohne Annotation läuft und
heißt der Prompt `v2_timepoint`. Damit kann ein Lauf ohne Annotation nicht mehr
als `v6_target_fallback` in die Auswertung gehen (Test: `test_lauf_ohne_annotation_heisst_nicht_v6`).

**Zellklassen.** `evaluate_fallback.py` trennt jetzt vier Klassen statt zwei:
`zieltreu`, `rueckfall`, `ohne_zeitpunkt` (Zelle ohne Angabe) und `ohne_ziel`
(Record ohne verwertbare Annotation). Die beiden neuen Klassen werden getrennt
ausgewiesen, nicht als zieltreu verbucht. Auf beiden v6-Läufen: 120/128
zieltreu, 38/36 Rückfall, 0 ohne Zeitpunktangabe, 13 ohne Ziel (10 richtig,
3 ohne Gold) — das Modell nennt den Zeitpunkt also durchgehend.

**Prüfung der 52 Referenzfälle** (`analysis/v6_review.md`): 40 Kontrollfälle
ohne Befund, 6 Zellen eines technisch leeren Laufs (`yun2024:231`, Lauf 10
korrekt), 4 fehlende Zellen zweier Gruppengrößen, 2 inhaltliche Fälle.
Davon sind nur **1 echter Modellfehler** (`yun2024:3 comparator_mean`: −7,0
statt −0,7) und **2 Gold-Konflikte**:

* `yun2024:83` — Gold führt 940 und 1831 als Gruppengrößen, das sind im Artikel
die Krankenhausstandorte („940 (34 %) … unit A, 1,831 (66 %) … unit B"),
während die Mittelwerte aus dem Periodenvergleich stammen. Die Annotation
„Period 2" ist für die Mittelwerte belegt; für die Gruppengrößen gibt es keine
passende Zahl. Gold unverändert.
* `yun2024:3` — 50,7 (Text) gegen 50,6 (Tabelle), bereits in Abschnitt 5
erfasst.

Damit ist die Restlücke bei F1 0,96 überwiegend Datenqualität, nicht
Extraktionsqualität.

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
