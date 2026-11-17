# Externe Quellen für Extraktion und Screening: Stand und Prüfung

**Stand:** 17.11.2026
**Anlass:** Drei externe Arbeiten wurden gesichtet, auf Anschlussfähigkeit geprüft
und — soweit ohne Lizenzklärung möglich — ausgemessen: LEADS (Nature
Communications 2025), Yisha et al. (BMC Med Res Methodol 2026) und MedSR-Bench
(medRxiv-Preprint 2026).
**Regel:** Jede Zahl in dieser Notiz stammt aus einer der unten genannten Dateien
oder aus einer dokumentierten Abfrage. Es wurde nichts geschätzt und nichts
ergänzt.

---

## 1. Kurzfassung

1. **Keine der drei Quellen schließt die Validierungslücke des Projekts.** Alle
   drei liefern Zahlen ohne Belegstelle (Seite, Tabelle, Zelle, Zitat). Der
   Verbatim-Kontrakt lässt sich auf keiner von ihnen prüfen.
2. **MedSR-Bench ist der beste Kandidat.** 2.000 von 2.144 Analyse-Gruppen sind
   poolbar, der Standardfehler ist doppelt unabhängig herleitbar, und die
   Studiennamen passen zu 100 Prozent zu den Analyse-Gruppen.
3. **Yisha et al. ist als Datensatz zu klein.** Veröffentlicht sind 20 statt der
   im Artikel genannten 105 Trials, und nur für 34 von 104 Records ist ein
   Volltext beschaffbar.
4. **LEADS ist kein Datensatz, sondern ein Modell plus Benchmark-Verfahren.**
   Nützlich sind die Aufgabenzerlegung und die Metriken, nicht die Daten. Die
   Studie ist methodisch schwach belegt (Stichprobengröße, keine Randomisierung,
   inkonsistente Teilnehmerzahlen).
5. **Die Lizenzfrage entscheidet, nicht die Datenlage.** MedSR-Bench ist aus der
   Cochrane Library abgeleitet; Cochrane verlangt für KI-Nutzung eine
   ausdrückliche Genehmigung. Die Apache-2.0-Angabe des Uploaders klärt das
   nicht.

---

## 2. Die drei Quellen im Vergleich

| Merkmal | LEADS (2025) | Yisha et al. (2026) | MedSR-Bench (2026) |
|---|---|---|---|
| Art | Feingetuntes Modell (Mistral-7B) + Aufgaben | Proof-of-Concept-Studie | Benchmark + Agentensystem |
| Status | peer-reviewed (Nat Commun 16:8361) | peer-reviewed (BMC 26:33, PMID 41535766) | Preprint (medRxiv), nicht begutachtet |
| Umfang | 21.335 Reviews, 453.625 Zitationen | 105 Trials beansprucht, 20 veröffentlicht | 100 Reviews, 1.297 RCTs, 2.144 Gruppen |
| Armwerte mit Lösungen | nein (Extraktion aus Publikationen) | ja, 104 Records / 486 Zellen | ja, 8.810 Studienzeilen |
| Belegstelle im Dokument | nein | nein | nein |
| Volltexte enthalten | nein | nein | nein |
| Lizenz | Publikation | **keine** im OSF-Projekt | Apache-2.0 erklärt, Inhalt aus Cochrane |
| Für das Projekt brauchbar | als Referenz und Metrikvorlage | nur mit Autorentabellen | strukturell ja, Lizenz offen |

---

## 3. LEADS — Nature Communications 16, 8361 (2025)

**Was es ist.** Auf Mistral-7B-Instruct-v0.3 feingetuntes Modell, das
Literatur-Mining in sechs Subtasks zerlegt: Suchanfragen-Generierung,
Eligibility-Bewertung und vier Extraktionsaufgaben (Studiencharakteristika,
Arm-Design, Teilnehmerstatistik, Trial-Ergebnisse). Trainingsdaten aus 21.335
systematischen Reviews mit 453.625 Zitationen und 8.485 Reviews, die über
NCT-IDs mit 27.015 Trial-Records verknüpft sind; LEADSInstruct umfasst 633.759
Instruktionsdatenpunkte.

**Ergebnisse.** Recall@3000 für die Suche; Recall@K für Screening auf 400.000
Review-Zitations-Paaren; „Accuracy" für Extraktion mit Cosinus-Ähnlichkeit
≥ 0,75. Pseudo-prospektiv: 31 Reviews nach 2025. Nutzerstudie: Screening-Recall
0,81 gegen 0,78, Zeit 580 s gegen 449 s; Extraktion 0,85 gegen 0,80, Zeit 113,9 s
gegen 83,3 s.

**Was daran schwach ist.**

- Der Screening-Effekt von 0,03 auf 10 Themen mit je bis zu 10 Auswahlen aus 30
  Kandidaten entspricht rund drei Studien; ein KI oder ein Test für diese
  Differenz wird nicht berichtet.
- Die berichteten 20,8 Prozent Zeitersparnis passen nicht zu 580 auf 449 s
  (das wären 22,6 Prozent). Bei der Extraktion stimmt die Rechnung exakt.
- Die Teilnehmerzahl ist inkonsistent: Abstract 16 aus 14 Institutionen,
  Methoden 15 Kliniker plus 2 Forscher (17), die Aufzählungen ergeben je 14.
- Die Extraktions-Nutzerstudie beruht auf zwei Personen.
- Keine Randomisierung, keine Verblindung — steht so in der eigenen
  Statistik-Sektion.

**Konsequenz für das Projekt.** LEADS ist Referenzpunkt und Wettbewerber, nicht
Datenquelle. Die Zahlen sind mit den eigenen nicht vergleichbar: Cosinus ≥ 0,75
ist deutlich weicher als der Exakt-Feld-Abgleich. Der Unterschied des Projekts
liegt im Beleg-Kontrakt, in der Doppellesung und in der deterministischen
Statistik.

---

## 4. Yisha et al. — BMC Med Res Methodol 2026;26:33

**Was es ist.** Zwei validierte Reviews aus *European Urology* (41 binäre Trials
mit 9 Outcomes, 64 kontinuierliche mit 12 Outcomes). Prompts über die
Web-Oberfläche von ChatGPT-4 und Claude 3 Opus, drei Läufe je Prompt, nur der
erste Output wird gewertet. Metrik `Pacc` = Anteil Trials mit korrekt
extrahiertem Item.

**Ergebnisse.** Binär: Gruppengröße 91–94 Prozent, Ereigniszahlen 57–71 Prozent.
Kontinuierlich: Gruppengröße 59–69 Prozent, Mittelwert und SD 24–56 Prozent.
Test-Retest-Kappa 0,67–0,96.

**Verfügbarkeit.**

- OSF-Projekt `8fzps` enthält **genau vier** Arbeitsmappen, keine PDFs, keine
  Lizenz. Die Lösungen sind die `*_rct`-Spalten; die `*_AI`-Spalten sind
  Modellausgaben.
- Veröffentlicht sind nur die Trials, die in die gepoolten Analysen eingegangen
  sind: 104 Records aus 20 Trials, 17 Publikationen, 486 Zellen.
- Volltexte: zwei Publikationen mit OA-Lizenz (20 Records), zwei weitere in PMC
  ohne OA-Lizenz (14 Records), der Rest Paywall. Ein Record gehört zu einem
  Kongressabstract ohne Artikel.

**Status im Repo.** Adapter, Manifest mit Hashes und die Records liegen unter
`goldstandard_datasets/eururology_v1/`, Teil des Tier-1-Sets (185 Records, 744
Zellen zusammen mit GLASS). Im Modelllauf vom 13.11. nicht verwendet, weil nur
zwei Publikationen offenen Volltext haben.

**Konsequenz.** Ohne die Autorentabellen (die im Artikel genannten 105 Trials
mit Belegspalte) bleibt der Datensatz bei etwa zwei Clustern. Die Anfrage ist
vorbereitet (`anfrage_eururology_autoren.md`), ein Versand- oder Antwortstand ist
im Repo nicht dokumentiert.

---

## 5. MedSR-Bench — medRxiv-Preprint 2026

**Was es ist.** Benchmark zu MedSR-Copilot, einem PRISMA-orientierten
Multi-Agenten-System. 100 Cochrane-Reviews aus 24 Domänen, alle nach 2023 und
offen zugänglich. Enthalten sind PICOS-Protokolle mit Ein- und
Ausschlusskriterien, Include-Listen, Analyse-Gruppen mit Armwerten und
dreiklassiger Zielkonklusion sowie ein separater RoB-Datensatz.

**Systemzahlen des Papers.** 63,6 Prozent menschenkonforme Endkonklusionen gegen
45,3 (Gemini 3 Flash), 34,8 (TrialMindSLR), 31,0 (DeepSeek-v4-flash) und 29,4
Prozent (GPT-5.4-Mini). Auf Yun Bench 97,6 Prozent Gruppen-Recall und 63,4
Prozent Data-Item-Accuracy. In der Mensch-KI-Studie 16,7 auf 44,1 Prozent bei 23
Analyse-Gruppen und 64,9 Prozent weniger Zeit.

**Eigene Messung** (`analyse_medsr_bench.py`, Commit `88ded17`):

| Kennzahl | Wert |
|---|---:|
| Reviews / Trials | 100 / 1.297 |
| Analyse-Gruppen | 2.144 |
| Gruppen mit k ≥ 2 | 2.004 |
| vollständig poolbar | 2.000 |
| Studienzeilen | 8.810 |
| Zeilen mit Effekt und KI | 7.574 (Paper: 7.570 Samples) |
| Armzeilen vollständig, kontinuierlich / binär | 2.273 / 5.305 |
| Gruppen mit Zielkonklusion | 1.908 |
| Gruppennummern mehrfach vergeben | 301 |
| Studiennamen ohne passenden Block | 0 von 7.570 |

**Der stärkste Befund.** Für 1.865 Mittelwertdifferenz-Zeilen wurde der
Standardfehler zweimal unabhängig gerechnet — aus dem berichteten KI und aus den
Arm-SDs mit Gruppengrößen. Der Median von KI-Breite zu Arm-SE ist 3,9199, also
exakt 2 × 1,96, und 100 Prozent der Zeilen liegen im Fenster 3,6 bis 4,2. Damit
sind alle KIs 95-%-KIs, und `se` ist nicht geraten, sondern reproduzierbar.

**Der wichtigste Gegenbefund.** Alle 1.297 Trials tragen `relation_type:
include`; es gibt keine Negativbeispiele im Release. Screening ist damit nur als
Recall messbar, nicht als Precision — die im Paper beschriebenen
2.000er-Kandidatenpools sind nicht veröffentlicht.

**Weitere Grenzen.**

- Effektmaße sind heterogen: Risk Ratio 1.377, Mean Difference 539, Std. Mean
  Difference 104, Odds Ratio 93, Risk Difference 18, Peto Odds Ratio 13. Ohne
  definierte Konversion darf nicht gemischt werden.
- Kein einziges Feld mit Seiten-, Tabellen-, Zell- oder Zitatbezug.
- 20 Analyse-Gruppen ohne eine einzige vollständige Armzeile, sieben Reviews mit
  verwaisten Gruppen.
- Volltextstichprobe über 40 PMIDs: 7 mit OA-Lizenz, 3 in PMC ohne OA, 30
  Paywall — also 17,5 Prozent offen.

**Verfügbarkeit.** Hugging Face `halfmorepiece/MedSR-Bench`, 100 JSON-Dateien
(8,26 MB) plus Parquet für den RoB-Teil, nicht gegated; Code unter
`MAGIC-AI4Med/MedSR-Copilot`, Apache-2.0.

---

## 6. Was das für das Projekt bedeutet

1. **Screening** ist erstmals mit einer echten Include-Liste messbar (1.297
   RCTs), aber nur als Recall. Für Precision braucht es eigene Negativlabels
   oder die nicht veröffentlichten Kandidatenpools.
2. **`study_effects`** lässt sich strukturell füllen: Effekt, KI, n,
   Gruppengröße, Ereigniszahlen, Outcome, Vergleich, Design und Effektmaß sind
   vorhanden. Was fehlt, ist der Beleg — also genau das Feld, das den
   Verbatim-Kontrakt trägt.
3. **Risk-of-Bias** bekommt erstmals eine Datenbasis (1.204 gelabelte Samples,
   955 Training / 249 Test).
4. **Die Validierungslücke bleibt.** Keine der drei Quellen ersetzt die
   Referenzannotation, weil keine Seite, Tabelle oder Zelle mitgeliefert wird.

---

## 7. Lizenzstand und offene Fragen

- **MedSR-Bench:** Inhalt aus der Cochrane Library. Cochrane verlangt vor
  KI-Nutzung eine ausdrückliche Genehmigung; „no implied permission exists
  without a licence". Die Apache-2.0-Angabe des Uploaders hebt fremde Rechte
  nicht auf. Rohdaten sind deshalb gitignored, versioniert sind nur Manifest und
  Aggregate.
- **Yisha et al.:** kein Lizenztext im OSF-Projekt. Nutzung für Forschung ist
  üblich, ausdrücklich erlaubt ist nichts.
- **Offene Fragen:** Erlaubt Cochrane die Nutzung eines Cochrane-abgeleiteten
  Drittbenchmarks? Auf welcher Grundlage steht die Apache-2.0-Angabe? Kommt das
  Volltext-Pool von MedSR-Copilot? Liefern die European-Urology-Autoren die
  Tabellen der 105 Trials mit Belegspalte?

---

## 8. Nächste Schritte

1. Cochrane-Anfrage um den Punkt „Nutzung eines Cochrane-abgeleiteten
   Drittbenchmarks" ergänzen und abschicken.
2. Kurze Anfrage an die MedSR-Autoren zur Rechtsgrundlage und zum Volltext-Pool.
3. European-Urology-Autorenanfrage abschicken (bereits vorbereitet).
4. Bis zu den Antworten ausschließlich Strukturarbeit: Importregel für die 301
   doppelten Gruppennummern und die 20 unvollständigen Gruppen, Konversionstabelle
   für die sechs Effektmaße.
5. **Kein Pooling- oder Extraktionslauf** auf MedSR-Bench vor der
   Lizenzklärung.

---

## 9. Belege

| Aussage | Datei |
|---|---|
| Yisha-Daten, 104 Records, 486 Zellen | `goldstandard_datasets/eururology_v1/manifest.json` |
| Yisha im Tier-1-Set | `tier1_validation_set_v1.json` |
| Datensatzprüfung, Power-Rechnung | `public_goldstandard_dataset_review.md`, `second_goldstandard_feasibility.md` |
| MedSR-Zählungen | `goldstandard_datasets/medsr_bench_v1/mapping_report.json` |
| MedSR-Hashes und Lizenzhinweis | `goldstandard_datasets/medsr_bench_v1/manifest.json` |
| MedSR-Volltextstichprobe | `goldstandard_datasets/medsr_bench_v1/fulltext_availability.json` |
| Lesbare Fassung der MedSR-Messung | `medsr_bench_mapping.md` |
| Skript | `public_benchmark/scripts/goldstandard/analyse_medsr_bench.py` |
