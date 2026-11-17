# Suche: Goldstandard mit Volltexten und Goldzellen

Stand: 2026-11-17
Frage: Gibt es einen öffentlich zugänglichen Datensatz, der (a) die Volltexte der
RCT-Publikationen mitliefert, (b) Gold-Zellen auf Armebene enthält und (c) für
uns ohne Verhandlung nutzbar ist?

## Kurzantwort

**Nein, nicht in dieser Kombination.** Kein geprüfter Datensatz erfüllt alle drei
Bedingungen gleichzeitig. Der einzige, der Text *und* Armzellen *und* eine
freizügige Lizenz verbindet, ist **Yun et al. 2024** — und der ist bei uns
bereits vollständig eingebunden (120 Artikel, 699 Records, 2.773 Goldzellen).
Alles andere scheitert an genau einem der drei Punkte: Text fehlt, Zellen
fehlen, oder die Lizenz verbietet die Nutzung.

## Übersicht der geprüften Quellen

| Quelle | Volltext mitgeliefert | Goldzellen (Armebene) | Lizenz | Urteil |
|---|---|---|---|---|
| Yun et al. 2024 (`hyesunyun/llm-meta-analysis`) | nein, aber Abstract + Results als XML/Markdown für alle 120 Artikel | ja (2×2, Mittelwert/SD/n) | Apache-2.0 (Repo) | **verwendbar, bereits vollständig eingebunden** |
| Cochrane-Datenpakete (Reviews ab 26.04.2023) | nein (nur Review-Daten) | ja (`events1/total1`, `mean1/sd1`) | Review-Lizenz (grün/gold) **plus** explizite KI-Klausel | **blockiert ohne Genehmigung** |
| Li et al. 2026, „What level of automation" (RSM) | ja, 58 Volltext-PDFs (aber nicht verteilt) | ja, JSON mit Statistik, RoB, Studienmerkmalen | Paper CC BY; Daten „upon reasonable request" | **nur per Anfrage** |
| MedSR-Bench | nein (nur PMIDs) | ja (2.144 Gruppen) | apache-2.0 des Uploaders, Rechte Dritter offen | Lizenzklärung offen (bereits dokumentiert) |
| European Urology / Yisha et al. | nein (Volltext nur teilweise OA) | ja (104 Records) | keine Lizenzdatei | zu klein (bereits dokumentiert) |
| GLASS / TrialReviewBench | nein | ja (81 Zeilen) | Labels MIT, Artikelrechte bei Verlagen | erschöpft (bereits dokumentiert) |
| Evidence Inference 2.0 | Snippets + Volltextbezug, kein Volltext | nein, nur Richtung des Effekts | CC BY-SA (HF-Kopie) | **Zellen fehlen** |
| ExaCT (Kiritchenko et al. 2010) | ja, 1.000 RCT-Volltexte (HTML) | nein, 21 Studienmerkmale | keine öffentliche Korpus-Auslieferung gefunden | **Zellen fehlen, Korpus nicht abrufbar** |
| RoBuster (JMIR Form Res 2026) | ja, 41 RCT-PDFs, nur CC-BY-Artikel | nein, nur RoB-2-Spans | CC BY (Artikel) | **Zellen fehlen** |
| PICO-Corpus / EBM-NLP / EvidenceOutcomes | nein (nur Abstracts) | nein bzw. ohne Outcome-Bezug | keine Lizenzdatei | ungeeignet |
| AACT / ClinicalTrials.gov | nein (Registerdaten) | ja | Public Domain | anderer Extraktionsgegenstand |

## Befunde im Einzelnen

### 1. Yun et al. 2024 — der einzige vollständig nutzbare Fall

`https://github.com/hyesunyun/llm-meta-analysis` (Commit `1bc768d`, Apache-2.0)

Das Repository liefert laut `evaluation/data/DATASET.md` **alle Textversionen**
der 120 eingeschlossenen RCTs mit: `abstract_and_results_xml_files`,
`no_attributes_xml_files`, `no_attributes_markdown_files` (die Modell-Eingabe).
Es sind Abstract **und Results-Section**, nicht das ganze PDF — genau die Teile,
in denen die Zahlen stehen.

Die Gold-Tabelle `annotated_rct_dataset.csv` führt je Record:

- `pmcid`, `outcome`, `intervention`, `comparator`, `outcome_type`
- `intervention_events`, `intervention_group_size`, `comparator_events`,
  `comparator_group_size`
- `intervention_mean`, `intervention_standard_deviation`, `comparator_mean`,
  `comparator_standard_deviation`
- `notes`, dazu drei Herkunftsflags: `is_data_in_figure_graphics`,
  `is_relevant_data_in_table`, `is_table_in_graphic_format`

Damit ist das der einzige öffentliche Datensatz, der Zellen **und** einen
Hinweis auf den Fundort (Tabelle / Grafik / Text) mitliefert. Was fehlt:
Seitenzahl, Abschnittsname, Zellposition, Zeitpunkt. Also genau die Lücke, die
wir mit eigener Annotation schließen wollten.

Status bei uns: `public_benchmark/extended_benchmark/yun_full/` — 120 Texte,
699 Records, 2.773 Goldzellen, Manifest mit SHA-256, Adapter, Auswertung.

### 2. Cochrane-Datenpakete — technisch ideal, rechtlich versperrt

`https://www.cochranelibrary.com/data` (Stand 25.04.2023): Für Reviews, die
**nach dem 25. April 2023** erschienen sind, gibt es ein vollständiges
Datenpaket (CSV/RIS) mit Studiendaten, RoB-Bewertungen, Analysedaten und
Referenzen, „under the same license as the associated review ('green' or
'gold')". Für ältere Reviews gibt es die Analysedaten als RevMan-5-Datei mit
Konverter. Die Analysedaten enthalten die Armzahlen (`events1`, `total1`,
`mean1`, `sd1`, …).

Die Nutzungsbedingungen (`https://www.cochranelibrary.com/about/data-download`,
Abschnitt 3) sind eindeutig und gelten auch für Open-Access-Reviews:

> „AI developers and companies must obtain authorization before using Cochrane
> content … for AI development, training, or implementation. No implied
> permission exists absent a proper licence."

und weiter, ausdrücklich als Untersagung ohne Erlaubnis:

> „Use or enable artificial intelligence technologies or tools to ingest, train,
> analyze, process, copy, distribute, or generate output based on the Cochrane
> Library, the Data, or any material included therein".

Die CC-BY-Option im Lizenzabschnitt hilft nicht: Abschnitt 3 stellt klar, dass
„[u]se rights are determined solely by the applicable licence terms" und dass
öffentlich zugängliche Inhalte urheberrechtlich geschützt bleiben. Eine
Evaluierung, bei der ein Modell Cochrane-Daten liest, ist genau der untersagte
Fall. Ohne schriftliche Genehmigung nicht verwendbar — auch nicht für eine
reine Messung.

### 3. Li et al. 2026 — 58 Volltexte mit Armzellen, aber nicht veröffentlicht

„What level of automation is 'good enough'?" *Research Synthesis Methods* 17(4),
671–692, DOI `10.1017/rsm.2025.10066`, PMCID `PMC13311339`, CC BY 4.0.

Die Autoren haben sechs Metaanalysen (Hypertension, Diabetes, Orthopädie)
aufgelöst, **58 RCT-Volltexte als PDF** von den Modellen lesen lassen und dazu
ein Ground-Truth-JSON mit Statistiken (Stichproben, Mittelwerte, SD, Effekte,
KI, p-Werte, unerwünschte Ereignisse, Dropouts), RoB-Domänen und
Studienmerkmalen von zwei Personen unabhängig prüfen lassen. Das ist
strukturell **genau das, was wir brauchen**: Volltext-PDF als Eingabe,
Armzellen als Gold, unabhängig geprüft.

Die Datenverfügbarkeitsangabe lautet jedoch: „All data analyzed in this study
were extracted from published sources and are available in the article or
supplementary material. Additional information is available from the
corresponding author upon reasonable request." Das JSON selbst ist nicht
abgelegt. Das Supplement enthält die Prompts, nicht die Gold-Tabelle.

### 4. Was an den übrigen Kandidaten fehlt

- **Evidence Inference 2.0** (`evidence-inference.ebm-nlp.com`): Volltextbezug
  und Evidenz-Snippets, aber nur die Richtung des Effekts (gestiegen /
  gefallen / kein signifikanter Effekt) — keine Zahlen. Grundlage des
  Yun-Datensatzes.
- **ExaCT** (Kiritchenko et al., BMC Med Inform Decis Mak 2010;10:56): 1.000
  RCT-Volltexte in HTML, 21 Studienmerkmale annotiert. Keine Armzahlen, und
  eine öffentliche Korpus-Auslieferung war nicht auffindbar (nur das Paper).
- **RoBuster** (JMIR Form Res 2026;10:e55127): 41 RCT-Volltexte, bewusst nur
  CC-BY-Artikel, RoB-2-Spans annotiert, Datensatz im Supplement. Sauber
  lizenziert, aber falscher Gegenstand — keine Ergebniszahlen.
- **TrialBench** (Sci Data 2025): Register- und Prognosedaten, keine
  Publikationsvolltexte, keine Armzellen.
- **PubMed 20k RCT / EBM-NLP / PICO-Corpus / EvidenceOutcomes**: nur Abstracts,
  keine Armzahlen bzw. ohne Outcome-Zuordnung.

## Konsequenz

Es gibt keinen frei verfügbaren Datensatz, der unsere Provenienzfrage
(Seite/Tabelle/Zelle) mit Volltexten und Armzellen beantwortet. Die drei
realistischen Wege, in dieser Reihenfolge:

1. **Anfrage an Li, Mathrani & Susnjak** (Massey University, Korrespondenz
   `l.li5@massey.ac.nz`): Bitte um das Ground-Truth-JSON der 58 RCTs. Ein Brief,
   potenziell 58 Volltexte mit Armzellen und unabhängiger Zweitprüfung. Der
   Datensatz ist mit CC BY publiziert, die Autoren haben die Weitergabe
   ausdrücklich angeboten („upon reasonable request").
2. **Cochrane-Genehmigung** (bereits als Stufe 2 im Maßnahmenplan): ohne
   schriftliche Erlaubnis bleibt der CDSR-Datenbestand gesperrt.
3. **Yun bleibt die Basis** und die eigene Annotation der 25 Artikel liefert die
   Provenienzfelder. Das ist der Stand, der ohne fremde Zusage trägt.

## Grenzen dieser Suche

- Geprüft wurden öffentlich indexierte Quellen (Paper, Repos, Cochrane-Seiten,
  HF, OSF, Zenodo). Nicht geprüft: kostenpflichtige Korpora (DistillerSR,
  EPPI-Reviewer-Bestände), Verlagsdatenbanken, sowie Datensätze, die nur in
  Supplementen einzelner Reviews liegen.
- Die Lizenzbewertung ist eine Textauslegung der zitierten Bedingungen, keine
  Rechtsberatung.
- Ob die 58 RCTs von Li et al. tatsächlich als PDFs weitergegeben werden dürfen,
  hängt an den Verlagsrechten der sechs Metaanalysen; das ist Teil der Anfrage.
