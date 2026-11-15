# Entwicklungsplan (15.11.2026)

Abgeleitet aus `fehlerursachen.md`, `length_analysis.md` und
`architekturvergleich.md`. Alle Schritte sind ohne API-Aufruf umsetzbar; der
erste Netzlauf steht am Ende.

## 1. Priorisierung

| Problem | Betroffene Records | Ursache | Lösung | Priorität |
|---|---:|---|---|---|
| Length-Abbruch ohne jede Ausgabe | 18 (638.000 Tokens ohne Zelle) | modellseitige Generierung bis zum Limit; Budget vor dem ersten Zeichen verbraucht | Reparaturaufruf mit kleinem Budget (Variante D) + Reasoning-Parameter prüfen | **1** |
| Leere Antwort bei Gruppengrößen-Gold | 6 (12 Goldzellen) | v7-Schema verlangt Zeitpunkt für alle Zellen; Gruppengrößen sind Arm-Eigenschaften | Schemafeld für armbezogene Angaben ohne Zeitpunkt (Variante A) | **2** |
| Falsche Gruppengrößen (Population) | 5 Records, 10 Zellen | Analysiert- vs. randomisiert-N, teils Arme vertauscht | Prompt-Regel „N der Auswertung, nicht der Randomisierung" + Prüfung | **3** |
| Zeitpunkt-Rückfall | 5 Records, 12 Zellen | Rückfallregel je Antwort, Ziel nicht am Wert belegt | Zeitpunkt separat bestimmen (Variante B, Pilot) | 4 |
| Falsche Mittelwerte/Streuungen | 4 Records, 6 Zellen | benachbarte Zeile/Spalte | Lokalisieren mit Zitatstelle (Variante B) | 5 |
| Überzählige Zellen ohne Gold | 7 Records, 15 Zellen | unklar, ob korrekt oder falsches Outcome | Stichprobe von 15 Zellen manuell prüfen | 6 |
| Fehlende Standardabweichungen | 10 Zellen | Modell lässt SD weg | Prompt-Zeile „SD mit ausgeben, wenn berichtet" | 6 |
| Neue Testbasis | – | 186 ist verbraucht | DEV/TEST-Split nach `teststrategie.md` | 7 |

## 2. Schritte mit Dateien, Funktionen und Tests

### Schritt 1 — Reparaturaufruf für Length (Variante D)

* Dateien: `run_extended_extraction.py` (neues Flag `--repair`, Funktion
  `_prompt_repair()`, Feld `pfad` je Zeile), `evaluate_fallback.py` (Zählung
  `pfad`).
* Tests: Reparatur läuft nur für Fehlzeilen; Budget des Reparaturaufrufs ist
  gedeckelt; eine Reparaturzeile ersetzt keine vorhandenen Zellen; ein
  Reparatur-Fehlschlag wird als solcher gezählt.
* Erfolg: Length-Ausfälle nach Reparatur ≤ 10 % (heute 38,3 % im Folgelauf),
  Reparaturkosten ≤ 6.000 Tokens je Ausfall (heute 19.000).

### Schritt 2 — Schema-Lücke Gruppengrößen (Variante A)

* Dateien: `run_extended_extraction.py` (`_prompt_v7`, Schema:
  `cells[].timepoint` optional für `*_group_size`), `evaluate_fallback.py`
  (`belegstufe`: Gruppengrößen ohne Zeitpunkt sind zulässig),
  `pruefe_v7_zeile()` (Ausnahme für Gruppengrößen).
* Tests: leere Antwort bei reinem Gruppengrößen-Gold wird als Fehler erkannt;
  Gruppengröße ohne Zeitpunkt ist kein Schemafehler; Zeitpunktzellen brauchen
  weiterhin einen Zeitpunkt.
* Erfolg: leere Antworten ≤ 5 % (heute 12,8 % der 47), ohne Rückgang der
  Precision.

### Schritt 3 — Gruppengrößen-Regel

* Datei: `_prompt_v7` (eine Zeile: N der analysierten Population, nicht der
  randomisierten; bei Abweichung beide nennen).
* Test: Prompt enthält die Regel; ohne Modelllauf nicht mehr prüfbar.
* Erfolg: falsche Gruppengrößen von 5 auf ≤ 2 Records (Pilot).

### Schritt 4 — Pipeline B als Experiment (Lokalisieren → Werte → Zeitpunkt)

* Dateien: neues Modul `extract_pipeline.py` (drei Stufen, je Stufe ein
  `quelle`/`pfad`-Feld), `run_extended_extraction.py` (Flag `--pipeline`),
  `evaluate_fallback.py` (gleiche Auswertung, Pfad getrennt).
* Tests: jede Stufe einzeln mockbar; Zusammenführung ordnet Zitate dem richtigen
  Record zu; fehlende Stufe → keine erfundene Zelle.
* Erfolg im Pilot: Precision ≥ 0,70 bei Recall ≥ 0,65 auf denselben 12 Records.

### Schritt 5 — Testbasis herstellen

* Dateien: `records/yun_test76_ziel.jsonl` (neu, eingefroren),
  `error_analysis/testlaeufe.md` (Register), Hash im Bericht.
* Tests: Hash-Test für DEV/TEST wie bei Gold (`test_gold_unveraendert`).
* Erfolg: TEST ist eingefroren, DEV enthält alle 60 harten Fälle.

### Schritt 6 — Pilot über 12 Records

* Ausführung erst nach Schritt 1–5, Freigabe vorausgesetzt.
* Erfolg: mindestens eine Variante erreicht die Schwellen aus Abschnitt 3.

## 2a. Umsetzungsstand 15.11.2026 (ohne API-Aufruf)

**Schritt 1 umgesetzt.** `run_extended_extraction.py` hat `--repair`; nach einem
`length_ohne_ergebnis` folgt genau ein Aufruf mit `REPAIR_MAX_TOKENS = 6000`,
gekürztem Artikeltext (15.000 Zeichen) und der Aufforderung, das JSON ohne
Voranalyse auszugeben. Die Zeile trägt `pfad`, `repair_tokens`,
`repair_finish_reason`, `repair_fehlerklasse`; Zellen ersetzt die Reparatur nur
bei Erfolg, das Originalbudget bleibt unverändert. Fünf Tests decken ab: nur
nach Length, nur mit Flag, Budget 6.000, Erfolg ersetzt Zellen, Fehlschlag
bleibt Fehlzeile.

**Schritt 2 umgesetzt.** Der v7-Prompt nimmt `*_group_size` von der
Zeitpunktpflicht aus („arm characteristics … exempt from the one-time-point
rule“), der Reparaturprompt ebenso. `evaluate_fallback.py` führt solche Zellen
in der eigenen Klasse `gruppengroesse_ohne_zeitpunkt` (mit richtig/falsch/ohne
Gold) und zählt sie nicht mehr als `ohne_zeitpunkt`; an den bestehenden Läufen
ändert das nichts, weil dort jede Gruppengröße einen Zeitpunkt trägt (0 Zellen
in der Klasse, nachgerechnet). `pruefe_v7_zeile` behandelt sie ebenfalls nicht
als Zeitpunktverstoß.

**Schritt 6 gelaufen** (`pilot_repair_20261116`, 12 Records, 182.497 Tokens):
Length 25,0 % (Ziel ≤ 10 % verfehlt), leere Antworten 0 %, Precision 1,0000,
Recall 0,6389. Der Reparaturaufruf rettet 3 von 6 Fällen; zwei vorher fehlerfreie
Records (`119`, `580`) scheiterten jetzt primär. Einzelheiten in
`pilot_repair.md`.

**Gegenprobe gelaufen** (`pilot_ohne_regel_20261116`): ohne die
Gruppengrößen-Zeile nur 2 statt 6 Primärausfälle und 123.291 statt 182.497
Tokens, dafür 4 leere Antworten statt 0. Die Zeile verursacht die Ausfälle,
behebt aber die leere Antwort. Beide Fassungen verfehlen mindestens ein Ziel;
Details in `pilot_gegenprobe.md`.

## 3. Messbare Erfolgskriterien

Bezogen auf die bestehende Verteilung (v6 0,6548 / kombiniert 0,6934 F1;
Length 25,3 % gesamt, 38,3 % im Folgelauf; leere Antworten 12,8 %):

| Kennzahl | heute | Ziel | Begründung der Schwelle |
|---|---:|---:|---|
| Length-Quote | 25,3 % (38,3 % im Folgelauf) | **≤ 10 %** | Reparatur deckelt den Schaden; 10 % ist die Hälfte des v6-Werts |
| leere Antworten | 12,8 % der Fehlzeilen | **≤ 5 %** | Schema-Lücke erklärt 6 von 6 Fällen |
| Zell-F1 (DEV) | 0,6934 | **≥ 0,72** | +0,03 absolut, oberhalb der Rundungs- und Klassifikationsunschärfe |
| Precision | 0,6838 | **≥ 0,70** | darf nicht schlechter werden; B zielt auf Zeitpunktfehler |
| Recall | 0,7032 | **≥ 0,72** | Reparatur soll Zellen zurückbringen |
| MAE-Coverage | 0,7862 | **≥ 0,80** | mehr Zellen, gleiche Prüfbasis |
| exakte Records | 79/186 (42,5 %) | **≥ 46 %** | +3,5 Punkte, entspricht 6–7 Records |

Die Schwellen sind Zielwerte, keine statistisch abgesicherten Effektgrößen; bei
76 Testrecords ist ein Unterschied unter 5 Prozentpunkten nicht belegbar
(Wilson-Intervall).

## 4. Wann sich ein großer Modelllauf lohnt

Erst wenn **alle** Bedingungen erfüllt sind:

1. alle Tests grün (aktuell 226) und die neuen Tests aus Schritt 1–2 dabei,
2. Pilot über 12 Records zeigt die Schwellen aus Abschnitt 3 bei einer Variante,
3. TEST ist eingefroren und im Register eingetragen,
4. das Tokenbudget ist vorab beziffert (bei erwarteten 12.000 Tokens/Record und
   76 Testrecords ≈ 0,91 Mio Completion-Tokens **[Schätzung]**).

Vorher ist jeder Vollauf eine Wiederholung der 638.000 Tokens, die die 18
Length-Ausfälle bereits gekostet haben.
