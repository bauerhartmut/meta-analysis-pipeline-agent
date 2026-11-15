# Architekturvarianten im Vergleich (15.11.2026)

Grundlage: gemessene Werte des v7-Folgelaufs (47 Records, 610.540 Tokens,
23 mit Zellen, 18 Length) und der Length-Diagnose. Alle Kosten für Varianten,
die noch nicht gelaufen sind, sind **[Schätzung]** aus diesen Messwerten, keine
Messung.

## 1. Ausgangsdaten für jede Rechnung

| Größe | Wert | Quelle |
|---|---:|---|
| Tokens je Record, v6 gesamt (186) | 9.210 | `auswertung186.md` |
| Tokens je Record, v7-Folgelauf | 12.990 | `kennzahlen.json` |
| Tokens je Record **mit** Zellen (v7) | 10.244 | dito |
| Tokens je gerettetem Record (v7) | 26.545 | dito |
| Length-Quote v7-Folgelauf | 38,3 % (18/47) | dito |
| Length-Quote v6 gesamt | 25,3 % (47/186) | `auswertung186.md` |
| Median gültiger v6-Antworten | 4.425 Tokens | `laenge_diagnose.md` |
| Precision v7-Zellen | 0,6076 | `kennzahlen.json` |
| Precision v6-Zellen | 0,9214 | `fallback_eval_kombiniert.json` |

Der wichtigste Befund für alle Varianten: Die 18 Ausfälle liefern **null
Zeichen** Inhalt. Jede Variante, die nur den Prompt kürzt oder das Limit erhöht,
ändert daran nichts (Belege in `length_analysis.md`).

## 2. Die vier Varianten

### A — Prompt schlank halten (bestehende Architektur)

Redundante Anweisungen entfernen, Ausgabefelder knapp halten, Schema-Lücke für
Gruppengrößen ohne Zeitpunkt schließen.

* Extraktion in **einem** Aufruf, ein Zeitpunkt je Antwort (v7 bleibt).
* Erwartete Length-Quote: unverändert bis leicht besser **[Hypothese]** — die
  Promptgröße ist als Ursache widerlegt, der Effekt käme nur daher, dass weniger
  Text zu durchsuchen ist.
* Kosten: gleich bis −10 % (≈ 11.700 Tokens/Record).
* Aufwand: klein (eine Funktion, Tests). Risiko: keines bei der
  Zusammenführung, weil keine.
* Precision: unverändert.

### B — Mehrstufige Extraktion (Lokalisieren → Extrahieren → Zeitpunkt)

1. Abschnitt/Zeile lokalisieren (`locate`): kurzer Prompt, kleine Ausgabe,
   liefert Zitatstellen.
2. Werte aus der Stelle extrahieren (ohne Zeitpunktfrage).
3. Zeitpunkt aus derselben Stelle bestimmen (`timepoint_header` + `fallback`).
4. Zusammenführen im Runner.

* Aufrufe: 3 je Record (bei Bedarf 4).
* Kosten **[Schätzung]**: Lokalisieren ≈ 3.000 Tokens, Extrahieren ≈ 5.000,
  Zeitpunkt ≈ 2.000 → ≈ 10.000 Tokens/Record plus 3 Aufrufe Overhead. Bei 186
  Records ≈ 1,9 Mio — in derselben Größenordnung wie v7 heute, aber mit
  verteiltem Risiko.
* Length-Quote **[Hypothese]**: deutlich niedriger, weil jede Stufe eine kleine
  Ausgabe hat; belegen lässt sich das erst mit einem Pilot.
* Precision: **wahrscheinlich besser**, weil Zeitpunkt und Wert getrennt
  entschieden werden; genau dort liegen die aktuellen Fehler (Rückfall 12
  Zellen, Zeitpunkt unklar 4).
* Aufwand: mittel bis hoch (drei Prompts, Parser, Zusammenführung, neue Tests).
* Risiko: Zusammenführungsfehler (falsche Stelle zu falschem Record), deshalb
  braucht jede Stufe eine Belegstelle im Ergebnis.

### C — Adaptiv (A für einfache, B für schwierige Records)

Vorschaltung ohne Modell: Komplexität aus Record und Text schätzen (Zahl der
Tabellen, Goldzellenzahl, Promptlänge, Zieltyp). Einfache Records → A,
schwierige → B.

* Aufrufe: 1 oder 3.
* Kosten **[Schätzung]**: 60 % A (≈ 11.700) + 40 % B (≈ 10.000 plus Overhead)
  ergibt ≈ 10.500–12.000 Tokens/Record.
* Length-Quote: zwischen A und B.
* Aufwand: mittel (Heuristik plus beide Pfade), aber die Heuristik selbst muss
  validiert werden — sonst routet sie falsch.
* Risiko: zwei Pfade in einem Datensatz; braucht ein Feld `pfad` je Zeile, wie
  bei `quelle`.

### D — Gezielte Reparatur nach Ausfall

Erster Aufruf wie A. Schlägt er fehl (Length oder leer), folgt **ein** kurzer
Reparaturaufruf mit reduziertem Auftrag: nur fehlende Felder, kurzer Textausschnitt,
Ausgabe als flache Liste statt Objekt.

* Aufrufe: 1; bei Ausfall 2.
* Kosten **[Schätzung]**: 12.990 + 0,38 × 4.000 ≈ 14.500 Tokens/Record — teurer
  als A, aber nur dort, wo es nötig ist.
* Length-Quote: unbekannt; der Reparaturaufruf hat ein kleines Budget
  (≈ 6.000), ein erneuter Loop kostet also höchstens 6.000 statt 19.000.
* Aufwand: klein bis mittel (Flag, kürzerer Prompt, Merge der Reparaturzellen).
* Precision: unverändert; Recall steigt nur, wenn die Reparatur Zellen liefert.

## 3. Vergleichstabelle

| Kriterium | A (Prompt) | B (Pipeline) | C (adaptiv) | D (Reparatur) |
|---|---|---|---|---|
| erwartete Extraktionsqualität | gleich | **höher** (Zeitpunkt getrennt) | wie B bei harten Fällen | gleich |
| erwartete Length-Quote | 30–38 % | **niedrig** | mittel | 30 % + Teilrettung |
| Modellaufrufe je Record | 1 | 3–4 | 1–4 | 1–2 |
| Tokens je Record **[Schätzung]** | ≈ 11.700 | ≈ 10.000 + Overhead | ≈ 11.000 | ≈ 14.500 (nur bei Ausfall) |
| Implementierungsaufwand | klein | hoch | mittel | klein–mittel |
| Risiko bei der Zusammenführung | keines | **hoch** | mittel | niedrig |
| Precision-Hebel | keiner | **hoch** | hoch | keiner |

## 4. Empfehlung

**A und D zuerst, B als Experiment, C vorerst nicht.**

Begründung aus den Daten:

1. A ist der einzige Hebel, der die 6 leeren Antworten strukturell erklärt: Sie
   kommen in 6 von 6 Fällen von Records, deren Gold nur Gruppengrößen enthält.
   Ein Schemafeld für armbezogene Angaben ohne Zeitpunkt behebt das ohne
   zusätzliche Aufrufe.
2. D begrenzt den Schaden der 18 Length-Ausfälle auf 6.000 statt 19.000 Tokens
   und ist der einzige Weg, die 638.000 verschwendeten Tokens künftig zu senken,
   ohne die Architektur umzubauen.
3. B verbessert am ehesten die Precision, kostet aber drei Aufrufe und bringt
   Zusammenführungsrisiko. Dafür ist ein Pilot über dieselben 12 Records nötig,
   bevor über 186 Records entschieden wird.
4. C ist ohne validierte Komplexitätsheuristik nur ein dritter Pfad im
   Datensatz.

Für die Precision ist B der einzige aussichtsreiche Ansatz: Der aktuelle
Fehleranteil liegt bei Zeitpunkt und Zuordnung (12 Rückfall-Zellen, 4 unklare),
und genau diese Entscheidung wird in B von der Wertsuche getrennt.
