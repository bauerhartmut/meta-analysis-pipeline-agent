# TrialSieve (2025): Was der Datensatz ist und ob er zu unserer Aufgabe passt

Stand 21.11.2026. Externe Prüfung des publizierten Datensatzes; im Repo gibt es
keinen TrialSieve-Bestand (Suche nach `TrialSieve`/`trial_sieve`: 0 Treffer,
keine Datei). Kein Modellaufruf, keine Änderung an Gold, Predictions oder Tests.

Quellen:

- Paper: Kartchner et al., *TrialSieve: A Comprehensive Biomedical Information
  Extraction Framework for PICO, Meta-Analysis, and Drug Repurposing*,
  Bioengineering 2025, 12(5), 486, doi 10.3390/bioengineering12050486,
  PMC12109152.
- Daten und Code: https://github.com/pathology-dynamics/trialsieve_final
  (CC0-1.0, Rolling Updates, 33 Commits, keine Releases).
- Preprint-Seite: https://davidkartchner.com/papers/trialsieve

## 1. Kurzbild

| Punkt | Wert |
|---|---|
| Einheit | PubMed-Abstracts (Titel und Abstract annotiert) |
| Umfang | **1.609 Abstracts**, 443.695 Wörter |
| Annotationen | 170.557 Entity-Annotationen, 15.854 QC-Annotationen |
| Spans | 97.004 verschiedene, **52.638 finale** Spans |
| Labels | **20 Entity-Typen** plus Relations-/Baumstruktur |
| Auswahl | aus BioSift (10.000 Abstracts, 7 Einschlusskriterien), dazu < 100 expertenrelevante |
| Annotatoren | 72 Studierende, 3+ je Abstract, 10 QC-Manager, Mehrheitsvotum je Zeichen |
| Split | 70/15/15 je Abstract, Abstracts > 500 Tokens satzweise geteilt |
| Lizenz | Datensatz CC0-1.0, Artikel CC BY |

## 2. Aufbau

Die 20 Labels (README des Repos, Definitionsliste): Disease/Condition of
Interest, Dosage, Drug Intervention, Follow-up period, Group Characteristic,
Group Name, Group Population/Sample Size, Intervention Administration,
Intervention Duration, Intervention Frequency, Non-Pharmaceutical Intervention,
Non-Study Drug, Outcome (Study Endpoint), Qualitative Side Effects,
Quantitative Measurement, Statistical Significance, Study Duration, Study
Years, Type of Quant. Measure, Units.

Die Besonderheit ist die **Baumstruktur** statt flacher PICO-Tags: Wurzel ist
ein `group`-Pseudo-Knoten, an dem Gruppengröße und Populationsmerkmale hängen;
Interventionen (mit Dosis, Applikation, Frequenz, Dauer) und Outcomes (mit
quantitativer Messung, Messtyp und Signifikanz) hängen an diesem Knoten. Pro
Studie gibt es **einen Baum je Patientengruppe**. Ein Comparator wird bewusst
**nicht** ausgezeichnet: jede Gruppe hat dieselbe Struktur, damit niemand (und
kein Algorithmus) bei mehreren Armen einen Comparator wählen muss.

## 3. Veröffentlichte Ergebnisse (Table 2, Span-Ebene)

| Modell | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| BioLinkBERT | **0,875** | 0,599 | **0,679** | 0,637 |
| BioBERT | 0,808 | 0,468 | 0,574 | 0,516 |
| KRISSBERT | 0,872 | 0,607 | 0,658 | 0,632 |
| PubMedBERT | 0,874 | **0,614** | 0,666 | **0,639** |
| GPT-4o | 0,837 | 0,563 | 0,459 | 0,506 |

Einzelne Labels in Table 3 (Auszug): `Quantitative Measurement` F1 0,747
(BioLinkBERT) bzw. 0,758 (PubMedBERT), `Statistical Significance` 0,918 bzw.
0,889, `Disease/Condition` höchstens 0,538. Fehleranalyse auf 237 Abstracts:
BioLinkBERT 71,48 % korrekt, menschliche Annotation 50,35 %; Menschen deckten
20 % weniger Spans ab.

Zwei Auffälligkeiten im Paper, die bei einer Zitierung zu prüfen sind:

- Die Zahl der Relationsannotationen ist mit 443.695 **identisch zur Wortzahl**.
  Plausibel wäre eine Relation je Token, belegt ist es nicht.
- Der Abstract nennt die Annotatoren-Umfrage mit `n = 39`, die Methoden mit 38
  von 72 vollständig ausgefüllten Fragebögen.

## 4. Vergleich mit unserer Aufgabe (yun699 / P5)

| Dimension | TrialSieve | yun699 / P5 |
|---|---|---|
| Einheit der Bewertung | Text-Span mit Label | Zelle `(Feld, Arm)` mit exaktem Zahlenwert |
| Textbasis | nur Abstract | Volltext mit eingeflachten Tabellen |
| Zeitpunkt | kein Label (nur Follow-up-Periode, Studiendauer) | Ziel-Zeitpunkt entscheidet über Treffer |
| Arme | ein Baum je Gruppe, **kein** Comparator-Label | `intervention_*` / `comparator_*` ist Pflicht |
| Gruppengröße | eigenes Label `Group Population / Sample Size` | unser Fehlerherd (582, 671/672) |
| Metrik | Span-Precision/Recall/F1, Teilwort-Treffer | Zell-F1, exakter Wert, 1:1-Verbrauch |
| Umfang | 1.609 Abstracts, 52.638 Spans | 699 Records, 2.773 Goldzellen |
| Gold-Qualität | Studierende, Re-Check 50,35 % korrekt | kuratiertes Gold, unverändert |

**Konsequenz:** Die 0,639 von PubMedBERT sind **nicht** mit unseren 0,7336
(699 Records, P5-Logik) oder 0,8088 (559 Zeilen) vergleichbar. Es sind
verschiedene Aufgaben (Span-Erkennung gegen Zellbindung), verschiedene
Textbasen (Abstract gegen Volltext) und verschiedene Gold-Güten. Wer die
Zahlen nebeneinander stellt, ohne das zu sagen, wiederholt genau den Fehler,
der beim GLM-Referenzwert schon korrigiert wurde.

## 5. Wofür der Datensatz brauchbar ist

1. **Externe Prüfung der Arm- und Kopf-Bindung.** Genau die Stelle, an der
   unsere Kette scheitert (Kopfzahlen, Untergruppen, mehrere Arme), ist hier
   annotiert: Gruppengröße je Gruppe, Gruppenname, Gruppenbaum. Ein Teilset
   mit mindestens zwei Gruppen, Gruppengröße und quantitativer Messung ist ein
   unabhängiger Test für `kopf_parser_20261120.py` außerhalb von PMC3877023
   und PMC3504298.
2. **Zusatz-Evaluierung des Nenner-Problems.** Die 33 Abbrüche kosten uns
   52 % der FN. TrialSieve trennt "Span vorhanden" von "Wert gebunden", also
   lässt sich dort messen, ob ein Modell die Zahl überhaupt findet, bevor die
   Bindung geprüft wird - ohne Volltextaufwand.
3. **Few-Shot- und Vortrainingsmaterial.** CC0, 1.609 Abstracts, 20 Labels,
   sauber dokumentierte Fehleranalyse; als Beispielmaterial für Prompts
   verwendbar, ohne Lizenzfrage.
4. **Vergleichspunkt für LLM-Extraktion.** GPT-4o erreicht dort 0,506 F1 auf
   Span-Ebene; das ist eine publizierte Hausnummer für dieselbe Modellklasse,
   die wir einsetzen - allerdings auf einer anderen Aufgabe.

## 6. Was der Datensatz nicht leistet

- **Kein Ersatz für den P5-Benchmark.** Es gibt keine normalisierten
  Zahlenwerte je Feld und Arm, keine Zeitpunkte, keine Tabellenzeilen und
  keine Gruppengrößen-Zuordnung im Sinne unserer Zellen.
- **Keine Volltext-Abdeckung.** Die Autoren nennen das selbst als Limitation:
  quantitative Ergebnisse stehen oft nur im Volltext. Unser Kernproblem
  (Tabellenzeile vs. Änderungszeile) existiert im Abstract nicht.
- **Kein Comparator.** Die bewusste Designentscheidung ist für Meta-Analyse
  richtig, für unsere Intervention/Comparator-Zuordnung aber unbrauchbar.
- **Rauschiges Gold.** 50,35 % menschliche Korrektheit im Re-Check heißt: ein
  Teilset ist als Zielgröße nur begrenzt belastbar; es taugt für
  Generalisierungsindizien, nicht für harte Prozentpunkte.

## 7. Empfehlung

**Nicht** als Benchmark-Ersatz oder als neue Headline-Zahl einführen. Wenn
externe Validierung gewünscht ist, dann als **kleines, getrennt ausgewiesenes
Teilset**: 50-100 Abstracts mit mindestens zwei Gruppen, Gruppengröße und
quantitativer Messung, dazu ein Konverter von Spans auf `(Feld, Arm)`-Zellen.
Aufwand offline, 0 Tokens; Nutzen: prüft, ob der Kopf-Parser und die
Armzuordnung außerhalb unserer fünf Dokumente tragen. Das ist ein
Diagnosewerkzeug, keine Benchmark-Zahl.

Priorität bleibt unverändert: erst die Unterscheider-Pflicht im Satz-Locator
offline gegen die 10 gespeicherten Fälle prüfen (0 Tokens), danach über einen
Netzlauf entscheiden.
