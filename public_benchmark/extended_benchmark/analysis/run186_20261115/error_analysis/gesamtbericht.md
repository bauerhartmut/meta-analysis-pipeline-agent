# Gesamtbericht: Fehleranalyse der 47 v7-Records (15.11.2026)

Erstellt ohne einen einzigen API-Aufruf aus den vorhandenen Läufen
(`yun_test186_v6_20261115`, `yun_test186_v7_folgelauf_20261116`,
`yun_test186_kombiniert_20261116`), den Golddaten und den Artikeltexten.
Erzeugendes Skript: `analysiere_47.py`; Rohdaten je Record:
`fehlerklassifikation_47_records.csv` (47 Zeilen, 30 Spalten), Aggregate:
`kennzahlen.json`.

## 1. Datenlage

| Status des v7-Versuchs | Records | Goldzellen | Tokens v7 |
|---|---:|---:|---:|
| Antwort mit Zellen | 23 | 75 | 268.540 |
| gültiges JSON, 0 Zellen | 6 | 12 | — |
| `length` ohne jede Ausgabe | 18 | 46 | 342.000 |
| **gesamt** | **47** | **133** | **610.540** |

Zellbilanz über alle 133 Goldzellen:

| Ausgang | Zellen | Anteil |
|---|---:|---:|
| richtig | 48 | 36,1 % |
| falscher Wert | 16 | 12,0 % |
| Auslassung in beantworteten Records | 11 | 8,3 % |
| Goldzelle nie bearbeitet (18 + 6 Records ohne Antwort) | 58 | 43,6 % |
| überzählige Zellen (nicht im Gold) | 15 | – |

Precision 0,6076, Recall 0,3609. Zeitpunkte: 48 zieltreu, 12 Rückfall, 4 unklar.

## 2. Die sieben Fragen

### 2.1 Was ist der größte Engpass?

**Die technische Nicht-Ausgabe.** In 24 von 47 Records (51 %) kommt keine
verwertbare Antwort: 18-mal endet die Generierung nach 19.000 Tokens mit
`content_len = 0`, 6-mal mit leerer Zellenliste. Diese 24 Records enthalten
**58 der 133 Goldzellen (43,6 %)**. Erst danach kommen inhaltliche Fehler:
16 falsche Werte, 11 echte Auslassungen, 12 Rückfall-Zeitpunkte.

### 2.2 Wie verteilen sich technische, inhaltliche und goldbedingte Fehler?

| Ursache | Records | Goldzellen betroffen |
|---|---:|---:|
| technisch (Length 18, leere Antwort 6) | 24 (51,1 %) | 58 |
| inhaltlich (falscher Wert, Auslassung, Zeitpunkt, überzählig) | 16 Records mit Zellfehlern | 39 (16 + 11 + 12 Rückfallzellen) |
| Gold (bestätigter Konflikt) | **0** | 0 |

Die 7 Records mit überzähligen Zellen sind inzwischen am Text geprüft (siehe
`ueberzaehlige_zellen.md`): **7 der 15 Zellen sind korrekt und fehlen nur im
Gold**, 2 gehören zu einem falschen Outcome, 4 sind bei Drei-Arm-Studien in der
Armzuordnung mehrdeutig, 2 sind ohne Tabellenblick nicht belegbar. Die
Precision liegt damit zwischen 0,61 (alle 15 als Fehler) und 0,70 (7 als richtig
gezählt); das Gold bleibt unverändert.

Nachtrag 15.11.2026: Schritt 1 und 2 des Entwicklungsplans sind umgesetzt
(`--repair` mit 6.000-Token-Deckel; `*_group_size` ohne Zeitpunktpflicht samt
eigener Auswertklasse).

Nachtrag 16.11.2026: Die 76 Records der zweiten Kohorte sind mit Zielzeitpunkten
eingefroren (`records/yun_test76_ziel.jsonl`, 243 Goldzellen, SHA-256
`9051c64be53aec818c77a20c13eea81bf0b8d3ed932dfa15388b8faec6daa31a`); Details
in `teststrategie.md` und `test76_annotation.md`.

Nachtrag 16.11.2026: Drei Pilotläufe über dieselben 12 Records zeigen, dass die
Gruppengrößen-Zeile im Prompt die Primärausfälle von 2 auf 6 (lang) bzw. 5
(kurz) hebt. Sie ist deshalb **opt-in** (`--group-size-mode`, Standard `aus`);
die Auswert-Ausnahme bleibt. Keine der drei Fassungen erreicht die
Length-Schwelle von 10 %. Details in `pilot_repair.md`, `pilot_gegenprobe.md`
und `pilot_kurzregel.md`.

### 2.3 Wie viele der 18 Length-Ausfälle sind erklärbar?

* **Technisch vollständig charakterisiert: 18 von 18.** Alle mit
  `finish_reason = length`, `content_len = 0`, `completion_tokens = 19000`,
  `parse_error = kein_json`. Kein abgeschnittenes JSON, keine Teilausgabe.
* **Kausal belegt: 0 von 18.** Reasoning-Tokens und Rohantwort wurden nicht
  gespeichert (`--save-content` war aus); die Schleife im Reasoning-Kanal ist
  eine begründete Schlussfolgerung, kein Messwert.
* **Als Input-Problem widerlegt: 18 von 18.** Die Ausfälle verteilen sich auf
  12 Dokumente (max. 2 je Dokument), die Textgröße korreliert nicht (25 % / 41 %
  / 42 % / 0 % in vier Größenklassen), und der kleinste Ausfall hatte nur 4.648
  Zeichen Prompt.

### 2.4 Ist eine mehrstufige Architektur besser?

**Teilweise belegt, nicht insgesamt.** Belegt ist, dass die aktuellen Fehler an
zwei getrennten Entscheidungen hängen: Wertsuche (16 falsche Werte, benachbarte
Zeile/Spalte) und Zeitpunkt (12 Rückfälle, 4 unklar). Eine Trennung beider
Schritte (Variante B) greift genau dort. Für die Length-Ausfälle gibt es
**keinen Beleg**, dass eine Pipeline hilft — die Ausfälle haben null Ausgabe,
also ist die Ausgabelänge nicht die Ursache; sie kann nur indirekt wirken, wenn
kleinere Aufträge das Modell aus der Schleife holen.

### 2.5 Welche Änderung bringt den größten Qualitätsgewinn pro Token?

**Die Schema-Lücke bei Gruppengrößen (Variante A, Schritt 2).** Sie erklärt 6
von 6 leeren Antworten (alle Goldzellen sind `intervention_group_size` /
`comparator_group_size`, fünf Ziele sind `baseline`), kostet **null zusätzliche
Aufrufe** und erschließt 12 Goldzellen. An zweiter Stelle: der gedeckelte
Reparaturaufruf (Variante D), der je Ausfall 19.000 auf höchstens 6.000 Tokens
senkt und damit die 638.000 verschwendeten Tokens der 18 Fälle halbiert.

### 2.6 Welche drei Maßnahmen zuerst?

1. **Reparaturaufruf mit 6.000-Token-Budget** für Length-Ausfälle.
2. **Schemafeld für armbezogene Angaben ohne Zeitpunkt** (Gruppengrößen).
3. **Gruppengrößen-Regel** („N der analysierten Population") plus manuelle
   Stichprobe der 15 überzähligen Zellen.

### 2.7 Welche Ergebnisse müssen vor einem neuen kostenpflichtigen Lauf vorliegen?

1. Tests grün inklusive der neuen Tests für Reparatur und Schema-Ausnahme.
2. Pilot über 12 Records (3 Length, 3 leer, 3 armgemischt, 3 normal) mit
   Length-Quote ≤ 10 %, leeren Antworten ≤ 5 %, Precision ≥ 0,70.
3. Eingefrorene TEST-Datei der zweiten Kohorte (76 Records, 243 Zellen) mit
   Zielzeitpunkten und Hash im Bericht, plus Testlauf-Register.
4. Beziffertes Budget (bei 12.000 Tokens/Record und 76 Records ≈ 0,91 Mio).

## 3. Kurzfazit

Der v7-Folgelauf hat 23 Records gerettet und den Recall von 0,618 auf 0,703
gehoben, aber die Hälfte der Fehlzeilen bleibt ohne Antwort, und die geretteten
Zellen sind ungenauer (Precision 0,61 gegen 0,92 im v6-Anteil). Die Ursachen
sind klar trennbar: technische Nicht-Ausgabe (58 Goldzellen), Wertfehler in 16
Zellen, Zeitpunktfehler in 12 Zellen, Gold-Konflikte in **keinem** der 47
Records. Die nächste Iteration sollte die billigen, strukturellen Fixes zuerst
machen und erst danach über eine Pipeline-Architektur entscheiden.

## 4. Dateien dieses Pakets

| Datei | Inhalt |
|---|---|
| `fehlerklassifikation_47_records.csv` | je Record: Status v6/v7, Tokens, Zellen, Gold, Treffer, Fehlwerte, Precision/Recall/F1, Kategorien |
| `kennzahlen.json` | alle Aggregate inklusive Length-Details |
| `analysiere_47.py` | Erzeuger (read-only, ohne API) |
| `length_analysis.md` | die 18 Ausfälle mit Belegen und Hypothesenrangfolge |
| `fehlerursachen.md` | quantitative und qualitative Ursachenanalyse |
| `architekturvergleich.md` | Varianten A–D im Vergleich |
| `teststrategie.md` | DEV/TEST-Split und Pilotdesign |
| `entwicklungsplan.md` | priorisierte Schritte mit Schwellenwerten |
