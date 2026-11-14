# Prognose: Wie sich Modelle unter 40B Parametern mit Finetuning entwickeln würden

Stand: 2026-11-14
Grundlage: eigener Lauf mit sechs Modellen auf 54 GLASS-Records
(`tier1_scores_aligned.json`) plus veröffentlichte Finetuning-Ergebnisse.

**Wichtig zur Lesart:** Alle Zahlen in Abschnitt 4 sind **Prognosen**, keine
Messungen. Sie sind aus der gemessenen Fehlerzerlegung (Abschnitt 2) und
publizierten Finetuning-Effekten (Abschnitt 3) abgeleitet und als Bandbreiten
angegeben. Ein Nachweis entsteht erst durch den in Abschnitt 6 beschriebenen
Lauf.

## 1. Ausgangslage: gemessene Werte der Modelle unter 40B

| Modell | Parameter | Recall | Precision | exakte Records | Zeilen/Record (Mittel) | Median je Record |
|---|---|---:|---:|---:|---:|---:|
| Qwen3-30B | 30B MoE, 3B aktiv | 0,566 | 0,426 | 7 / 54 | 2,4 | 0,8 s |
| Qwen 3.6-35B | 35B MoE | 0,511 | 0,503 | 6 / 54 | 2,0 | 13,1 s |
| Qwen 3.8-27B | 27B, Reasoning | 0,566 | 0,355 | 6 / 54 | 3,1 | 110,0 s |

Zum Vergleich die großen Modelle: Recall 0,571-0,604, Precision 0,358-0,510,
exakte Records 8-9. Der Abstand zu den großen Modellen ist bei 54 Records nicht
signifikant — die kleinen Modelle liegen beim Recall nur 0,5 bis 9
Prozentpunkte darunter.

## 2. Fehlerzerlegung: woran die Modelle tatsächlich scheitern

Je Modell 182 Gold-Zellen, aus der zeilenweisen Auswertung:

| Modell | richtig | falsch | fehlend | Zusatzzellen | Anteil Zusatz an allen Ausgaben |
|---|---:|---:|---:|---:|---:|
| Qwen3-30B | 96 | 33 | 53 | 113 | 47 % |
| Qwen 3.6-35B | 93 | 16 | 73 | 76 | 41 % |
| Qwen 3.8-27B | 101 | 22 | 59 | 167 | 58 % |
| (große Modelle) | 103-108 | 12-20 | 54-66 | 88-179 | 43-58 % |

Drei Fehlerarten mit sehr unterschiedlicher Trainierbarkeit:

1. **Zusatzzellen (41-58 % aller Ausgaben).** Die Modelle liefern alle
   Subgruppen eines Papers, der Goldstandard führt eine gepoolte Zeile. Das ist
   ein **Konventionsfehler**, kein Lesefehler — genau der Typ, den
   überwachtes Lernen am direktesten korrigiert.
2. **Fehlende Zellen (29-40 % der Gold-Zellen).** Teils nicht im Volltext
   auffindbar, teils falsche Zeile gewählt. Nur teilweise trainierbar.
3. **Falsche Zellen (7-18 %).** Vorhanden, aber falsch zugeordnet (Arm,
   Zeitpunkt, Einheit) oder falsch abgelesen. Das ist der teuerste Fehler und
   der am schwersten abzustellende.

Anteil an allen gelieferten Zellen; die Spanne reicht von 41 Prozent (Qwen
3.6-35B) bis 58 Prozent (Qwen 3.8-27B). Bei den kleinen Modellen kommt ein vierter Punkt hinzu: **Formatstabilität.**
Qwen 3.8-27B lieferte bei 8000 Tokens sechs leere Antworten
(`finish_reason: length`) und einen JSON-Parsefehler. Das ist reine
Ausgabeformatierung und mit Finetuning praktisch vollständig behebbar.

## 3. Was die Literatur zu Finetuning erwartet

| Quelle | Aufgabe | Effekt |
|---|---|---|
| Wadhwa et al. 2023 (ML4H) | RCT-Interventionen/Outcomes aus Abstracts, Finetuning | ~20 Punkte absoluter F1 gegenüber vorherigem SOTA |
| PMC12633606 (ELMTEX, 60k klinische Zusammenfassungen) | strukturierte Extraktion, LoRA/QLoRA auf Llama-3.1-8B | „Fine-tuning consistently outperformed prompting alone", LoRA +10-20 Punkte, QLoRA 2-4 Punkte darunter |
| Verily 2024 (Schedule-of-Event-Tabellen) | Tabellenerkennung | Precision 59,8 → 87,3 (+27,5 pp) bei praktisch gleichem Recall 97,3 → 98,9 |
| Schema-to-JSON (EMNLP 2024) | Schema-Extraktion aus Tabellen, Finetuning mit 1.169 Beispielen | LLaMA-7B 51,3 Token-F1 vs. 13,5 ohne Finetuning; T5-11B 64,1 vs. 36,9 |
| Kumar 2026 (BioNLP) | Claim-Verifikation, QLoRA mit 1.008 Beispielen | 7B-Modell schlägt GPT-4o um bis zu 12 Punkte bei 44,5-fach geringeren Kosten |

Das Muster ist konsistent: **Finetuning verschiebt vor allem die Precision und
die Formatdisziplin, deutlich weniger den Recall.** Der Verily-Fall ist die
beste Analogie zu unserem Problem — dort wurde fast ausschließlich die
Precision von 60 auf 87 Prozent gehoben, weil das Modell vorher zu viel
markierte.

Für unsere Aufgabe heißt das: Die 41-58 Prozent Zusatzzellen sind der
angreifbare Teil, die 29-40 Prozent fehlenden Zellen der sperrige.

## 4. Prognose

Annahmen: Finetuning mit 1.000-5.000 Beispielen, die der Goldkonvention folgen
(eine Zeile je gepoolter Analyse, feste Feldliste), Holdout nach Publikation,
keine Änderung des Prompts. Zwei Szenarien.

### Szenario A: destillierte Trainingsdaten (1.000-2.000 Beispiele)

Labels aus einem starken Modell auf offenen Volltexten erzeugt, stichprobenartig
geprüft. Billig, aber die Labels tragen die Fehler des Lehrers.

| Kennzahl | Qwen3-30B heute | Prognose A | Qwen 3.6-35B heute | Prognose A | Qwen 3.8-27B heute | Prognose A |
|---|---:|---|---:|---|---:|---|
| Recall | 0,566 | 0,58-0,64 | 0,511 | 0,54-0,61 | 0,566 | 0,58-0,64 |
| Precision | 0,426 | 0,50-0,62 | 0,503 | 0,55-0,66 | 0,355 | 0,45-0,58 |
| exakte Records | 7 / 54 | 12-18 / 54 | 6 / 54 | 11-17 / 54 | 6 / 54 | 10-16 / 54 |
| leere/ungültige Ausgaben | 0 | ~0 | 0 | ~0 | 6 | ~0 |
| Zeilen/Record | 2,4 | 1,3-1,8 | 2,0 | 1,2-1,7 | 3,1 | 1,3-1,9 |

### Szenario B: menschlich geprüfte Trainingsdaten (3.000-5.000 Beispiele)

| Kennzahl | Qwen3-30B heute | Prognose B | Qwen 3.6-35B heute | Prognose B | Qwen 3.8-27B heute | Prognose B |
|---|---:|---|---:|---|---:|---|
| Recall | 0,566 | 0,62-0,70 | 0,511 | 0,58-0,67 | 0,566 | 0,62-0,70 |
| Precision | 0,426 | 0,58-0,70 | 0,503 | 0,60-0,72 | 0,355 | 0,52-0,65 |
| exakte Records | 7 / 54 | 16-24 / 54 | 6 / 54 | 15-22 / 54 | 6 / 54 | 14-20 / 54 |

### Begründung der Bandbreiten

- **Precision (+10 bis +25 pp).** Direkt aus der Fehlerzerlegung: 41-58 Prozent
  der Ausgaben sind Zusatzzeilen, die eine trainierte Konvention beseitigen
  kann. Die Literatur stützt 10-20 Punkte (LoRA) bis 27 Punkte (Verily).
  Obergrenze bewusst unter dem Verily-Wert, weil unsere Zusatzzellen teilweise
  inhaltlich korrekt sind und die Bewertung sie nur wegen der
  Goldgranularität als falsch zählt.
- **Recall (+3 bis +12 pp).** Kleiner, weil die fehlenden Zellen zur Hälfte
  nicht im Volltext stehen oder in Tabellen, die das Modell nicht linear
  liest. Finetuning verbessert die Zeilenwahl (Zuordnungsrate 0,78-0,85 →
  geschätzt 0,88-0,95), nicht die Auffindbarkeit.
- **Exakte Records (11-17 % → 25-45 %).** Folgt aus Precision und
  Formatstabilität: Ein Record ist nur exakt, wenn alle Zellen stimmen; jede
  halbierte Zusatzquote hebt diesen Anteil überproportional.
- **Formatfehler → nahe null.** Reine Ausgabekonvention, in der Literatur
  der zuverlässigste Effekt.

### Wer am meisten gewinnt

| Modell | Größter Hebel | Erwartung |
|---|---|---|
| Qwen3-30B | falsche Zellen (18 % der Gold-Zellen) und Zusatzzeilen | profitiert am stärksten, weil beides trainierbar ist |
| Qwen 3.6-35B | fehlende Zellen (40 %) | profitiert am wenigsten bei Precision (schon 0,503), am meisten bei Recall — der aber am schwersten trainierbar ist |
| Qwen 3.8-27B | Format und Überextraktion | größter Einzelsprung bei Precision, bleibt aber das langsamste Modell (Reasoning-Kosten bleiben) |

### Was Finetuning nicht löst

- **Goldgranularität.** Wenn der Goldstandard eine gepoolte Zeile führt und das
  Paper zehn Subgruppen hat, bleibt die Zuordnung mehrdeutig. Ein trainiertes
  Modell lernt die Konvention, nicht die Wahrheit.
- **Armverwechslung.** In unserem Datensatz strukturell unsichtbar (GLASS führt
  keine Armwerte). Ohne Arm-Gold kann Finetuning das nicht verbessern.
- **Domänentransfer.** Ein auf Onkologie trainierter Extraktor wird auf
  Kardiologie schlechter — der Effekt ist in der Literatur gut belegt und muss
  im Design berücksichtigt werden.
- **Obergrenze durch Datenmenge.** Mit 54 Records ist kein Finetuning möglich;
  ohne 1.000+ Beispiele bleibt jeder Effekt im Rauschen.

### Prognoseunsicherheit

Die Bandbreiten sind bewusst weit. Drei Gründe:

1. Unser Testset hat 54 Records; die kleinste nachweisbare Differenz liegt bei
   7,0 Prozentpunkten. Ein Teil der prognostizierten Effekte wäre auf dem
   heutigen Testset **nicht messbar**.
2. Die Literaturwerte stammen aus anderen Aufgaben (Abstracts statt Volltexte,
   Tabellen statt Fließtext, Klassifikation statt Zahlenextraktion).
3. Destillierte Labels (Szenario A) können die Fehler des Lehrers
   weitertragen — in dem Fall ist der Precision-Gewinn kleiner als angegeben.

## 5. Was das für die Modellwahl bedeutet

Wenn die Prognose auch nur zur Hälfte eintritt, verschiebt sich die Rangfolge:
Ein finetuntes 30B-Modell käme auf Precision 0,50-0,62 bei 0,8 s je Record und
wäre damit für Massenläufe den großen Modellen überlegen — nicht wegen besserer
Extraktion, sondern wegen Preis-Leistung. Qwen 3.6-35B bliebe die Wahl, wenn
falsche Werte teurer sind als fehlende (klinische Fragestellungen), weil es
schon heute die wenigsten Zusatzzellen liefert.

## 6. Wie man die Prognose prüft (Vorschlag)

1. **Trainingsdaten getrennt halten.** Holdout nach Publikation, nicht nach
   Record — sonst lernt das Modell die Studien auswendig. Bei 54 Records ist
   das ein Holdout von 11 Records; zu klein, deshalb zuerst Datensatz
   erweitern.
2. **Datenmenge staffeln.** 1.000 / 2.000 / 4.000 Beispiele, jeweils gleicher
   Holdout. Erwartung: Precision steigt bis 2.000, danach flach.
3. **Zwei Kontrollen mitlaufen lassen.** (a) Basismodell mit demselben Prompt,
   (b) Basismodell mit Few-Shot statt Finetuning. Ohne (b) lässt sich der
   Effekt nicht von besserer Aufgabenbeschreibung trennen.
4. **Fehlerzerlegung wiederholen**, nicht nur F1 berichten: Zusatzzellen,
   fehlende Zellen, falsche Zellen, Formatfehler. Nur so ist sichtbar, ob der
   Effekt aus der Konvention oder aus besserem Lesen kommt.
5. **Abbruchkriterium.** Wenn die Zusatzzellen nach 2.000 Beispielen nicht um
   mindestens ein Drittel sinken, ist der Ansatz für diese Aufgabe nicht
   tragfähig.

## 7. Fazit

Die Prognose ist vorsichtig optimistisch und stützt sich auf einen klaren
Mechanismus: Der größte gemessene Fehleranteil der kleinen Modelle ist ein
Konventionsfehler (41-58 Prozent Zusatzzeilen), und Konventionen sind der
trainierbarste Teil der Aufgabe. Realistisch sind **+10 bis +25 Punkte
Precision** und **+3 bis +12 Punkte Recall**, womit die kleinen Modelle die
heutigen großen bei Precision erreichen oder übertreffen könnten, bei einem
Bruchteil der Laufzeit.

Nicht erwartbar ist ein Sprung beim Recall oder eine Lösung der
Armverwechslung — beides hängt an Daten, die der Goldstandard nicht führt.

## Quellen

- Wadhwa et al., „Jointly Extracting Interventions, Outcomes, and Findings from
  RCT Reports with LLMs", ML4H 2023.
- „For clinical data extraction, QLoRA attains accuracy close to LoRA while
  requiring lower compute resources", PMC12633606.
- Verily, „Selective Fine-tuning on LLM-labeled Data", 2024 (Schedule-of-Event).
- „Schema-Driven Information Extraction from Heterogeneous Tables", EMNLP
  Findings 2024.
- Kumar, „Small LLMs for Biomedical Claim Verification", BioNLP 2026.
- Eigene Messung: `tier1_scores_aligned.json`, `runs/tier1_20261113/`.
