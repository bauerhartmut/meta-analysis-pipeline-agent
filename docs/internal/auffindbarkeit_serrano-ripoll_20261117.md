# Auffindbarkeit und Extraktionstauglichkeit der Serrano-Ripoll-Referenzstudien

Datum: 17.11.2026
Prüfskript: `scripts/pruefe_serrano_referenzen.py`
Rohdaten: `data/reviews/serrano_referenzen_20261117.json`,
Laufprotokoll: `data/reviews/serrano_referenzen_20261117.log`

Read-only gegen öffentliche APIs (Europe PMC, PubMed E-utilities, Crossref,
OpenAlex, Semantic Scholar). Kein Modellaufruf, keine Datenbank, keine
Änderung am Agenten.

## Fragestellung

Vor dem ersten Netzlauf der Reproduktion war zu klären:

1. Sind die 12 eingeschlossenen RCTs über die Provider des Agenten
   erreichbar, obwohl Embase, PsycINFO, CINAHL und CENTRAL fehlen?
2. Lassen sich Mittelwerte und SD der 10 Trials mit PMC-Volltext ziehen?

## Referenzliste (verifiziert über PMID, nicht über die gedruckte Nummer)

| # | Studie | PMID | DOI | PMC | CC BY |
|---|---|---|---|---|---|
| 33 | Arean 2016 | 27998876 | 10.2196/jmir.6482 | PMC5209607 | ja |
| 34 | Birney 2016 | 26813737 | 10.2196/mhealth.4231 | PMC4748138 | ja |
| 35 | Dahne 2019 | 31208690 | 10.1016/j.beth.2018.12.003 | PMC6582985 | nein (Author Manuscript) |
| 36 | Ham 2019 (HARUToday) | 31402881 | 10.3389/fpsyg.2019.01592 | PMC6669916 | ja |
| 37 | Lüdtke 2018 | 30273901 | 10.1016/j.psychres.2018.08.113 | – | nein |
| 38 | Mantani 2017 | 29101095 | 10.2196/jmir.8602 | PMC5695656 | ja |
| 39 | Moberg 2019 | 31199319 | 10.2196/12556 | PMC6592477 | ja |
| 40 | Pratap 2018 | 30093372 | 10.2196/10130 | PMC6107735 | ja |
| 41 | Roepke 2015 | 26182069 | 10.1089/g4h.2014.0046 | – | nein |
| 42 | Tighe 2017 | 28132007 | 10.1136/bmjopen-2016-013518 | PMC5278278 | ja |
| 43 | Graham 2020 | 32432695 | 10.1001/jamapsychiatry.2020.1011 | PMC7240649 | nein (Author Manuscript) |
| 44 | Guo 2020 | 32044751 | 10.2196/16715 | PMC7058168 | ja |

Damit: 8 von 12 CC BY, 10 von 12 mit PMC-Volltext, 2 geschlossen
(Lüdtke, Roepke).

Korrektur zu einer früheren Notiz: Die gedruckte Nummerierung [33]–[44]
stimmt mit Tabelle 2 des Reviews überein. Es ist der `citedOrder` des
Europe-PMC-References-Endpunkts, der davon abweicht (er sortiert die
Referenzen anders); maßgeblich ist die gedruckte Liste.

Nebenbefund: Die App "HARUToday" ist über ihren Namen nicht suchbar
(Europe PMC liefert zu `HARUToday` nur Fremdtreffer). Die Studie ist nur
über Autor/Titel zu finden - ein Beleg dafür, dass App-Namen als
Suchbegriff unbrauchbar sind.

## Befund 1: Identifier-Ebene - 12 von 12 überall vorhanden

Jede der 12 Studien ist in allen fünf Providern nachweisbar
(DOI-Abfrage bei Europe PMC, PubMed, Crossref, OpenAlex, Semantic Scholar):
12/12, keine Lücke.

**Folgerung:** Das Fehlen von Embase, PsycINFO, CINAHL und CENTRAL ist für
diese Referenzliste kein Hindernis. Alle 12 Trials stehen in MEDLINE
und/oder Crossref. Die Datenbanklücke betrifft die Vollständigkeit der
Suche, nicht die Erreichbarkeit der Referenz.

## Befund 2: Such-Ebene - eine Stichwortabfrage findet sie nicht

Eine realistische Abfrage
(`("smartphone app" OR "mobile app") AND depression AND randomized controlled trial`),
ein Lauf je Provider:

| Provider | Treffer in den ersten 100 | Treffer im Fenster 1000 | Ränge der Gefundenen |
|---|---|---|---|
| Europe PMC | 0/12 (hitCount 500) | 3/12 | Mantani #387, Guo #412, Birney #490 |
| PubMed | 2/12 (hitCount 349) | 4/12 | Graham #78, Dahne #136, Moberg #144, Mantani #231 |
| OpenAlex | 6/12 | nicht gemessen | – |
| Crossref | 1/12 | nicht gemessen | – |
| Semantic Scholar | 0/12 (0 Rückläufer) | – | nicht belastbar |

**Folgerung:** Der Referenzbestand ist über eine Einzelabfrage praktisch
nicht erreichbar; Europe PMC vergräbt die Studien bis Rang 490. Recall
entsteht erst aus mehreren Konzeptabfragen, nicht aus einer breiten.
Die Semantic-Scholar-Zeile ist wertlos (Rate-Limit, 0 Rückläufer) und
darf nicht als Negativbefund gelesen werden.

## Befund 3: Zitationspfad reicht allein nicht

Referenzlisten einschlägiger Reviews, geprüft über OpenAlex
`referenced_works`:

- Linardon 2019 (World Psychiatry, 81 Referenzen): 5/12
- Firth 2017 (World Psychiatry, 70 Referenzen): 4/12

**Folgerung:** Rückwärts-Zitation über ein Review deckt höchstens die
Hälfte ab. Der Pfad ist nützlich, aber kein Ersatz für die Suche.

## Befund 4: Volltextzugang

- 10 von 12 haben einen PMC-Volltext.
- 8 von 10 liefern `fullTextXML` (Arean, Birney, Ham, Mantani, Moberg,
  Pratap, Tighe, Guo).
- 2 von 10 antworten mit HTTP 500 (Dahne, Graham): Author Manuscripts
  ohne XML. Für sie bleibt nur die PMC-HTML-Seite oder das PDF.

## Befund 5: Arm-Statistiken - gemischt, nicht einheitlich ziehbar

Geprüft über Tabellenüberschriften und `mean (SD)`-Marker im Volltext:

| Studie | Berichtsform | Arm-Mittelwert + SD direkt? |
|---|---|---|
| Ham 2019 | Tab. 4: Prä-Post-Vergleich je Fragebogen | ja |
| Mantani 2017 | Tab. 3/4: Outcomes Woche 9 und 17 | ja |
| Tighe 2017 | Tab. 2: beobachtete Mittelwerte T1/T2 | ja |
| Guo 2020 | Tab. 2: primäres Outcome CES-D | ja |
| Arean 2016 | Tab. 3: Haupteffekte auf Veränderung | nein (Modellschätzer, Baseline-SD in Tab. 1) |
| Birney 2016 | Tab. 2: ANCOVA-Ergebnisse | nein (adjustierte Differenzen) |
| Moberg 2019 | Tab. 3/4: Gruppen-Zeit-Interaktion, Change-Scores | nein |
| Pratap 2018 | Tab. 4: wöchentliche Veränderung PHQ-9 | nein |
| Dahne 2019 | kein XML | offen |
| Graham 2020 | kein XML | offen |

**Folgerung:** Eine vollständige Neuberechnung aller 10 SMD aus
Arm-Mittelwerten und SD ist mit den offenen Texten **nicht** möglich.
Vier Studien berichten modellbasiert oder als Change-Score; bei ihnen
braucht es Baseline-SD plus Veränderungsschätzer, also eine
Herleitung mit dokumentierten Annahmen.

## Konsequenzen für die Benchmark-Definition

1. Suchtoleranz: "11 von 12 gefunden" ist mit einer Abfrage nicht
   erreichbar und als Einzelabfrage-Kriterium falsch gesetzt. Sinnvoll ist
   Recall über den gesamten Lauf (mehrere Konzeptabfragen plus
   Zitationspfad) mit dokumentierter Abfrageliste.
2. Pooling: Der SMD-Abgleich läuft auf der extrahierbaren Teilmenge
   (derzeit 4 direkt, 4 mit Herleitung, 2 ohne XML). Die Toleranz gilt für
   diese Teilmenge, nicht für alle 10.
3. Die zwei Author-Manuscript-Studien (Dahne, Graham) brauchen einen
   zweiten Abrufweg; ohne ihn fehlt eine Studie, die den
   Heterogenitätstreiber Dahne enthält.
4. App-Namen sind kein Suchbegriff (HARUToday-Befund).

## Nachtrag: systematische Suche nach einem vollständig offenen Review

Skript: `scripts/suche_volltext_review.py`. Es sucht Metaanalysen mit
Volltext in Europe PMC, zieht aus dem Volltext-XML die im Results-Teil und
in der Einschlusstabelle zitierten Studien (Hintergrundliteratur steht in
Einleitung und Diskussion) und prüft für diese den OA-Status.

Geprüft wurden vier Themenfelder (digital/mHealth, COVID-19, Telemedizin,
Studierende) mit 176 bzw. 177 Kandidaten; auswertbar waren 11 bzw. 6
Reviews, weil bei vielen der Results-Teil keine Referenzanker trägt.

**Ergebnis: kein Review mit 100 % CC BY.** Bester Wert im
Interventionsbereich: 17 von 19 Primärstudien frei in PMC (89,5 %),
14 davon CC BY (`10.2196`-Reihe, PMID 42243497). Im COVID-Feld erreicht
ein Review 12 von 12 frei in PMC (100 %), aber nur 10 CC BY (83 %)
(PMID 42666214) - und es ist eine Risikofaktor-Analyse, keine
Interventionsstudie. Der Spitzenwert über alle Felder (85,6 % CC BY) ist
eine Cochrane-Diagnostik-Übersicht mit k=146 und damit unbrauchbar.

**Die entscheidende Unterscheidung:** CC BY (Weiterverwendung) und
"frei in PMC lesbar" (Text-Mining für nicht-kommerzielle Forschung
erlaubt) sind nicht dasselbe. Meine frühere Fassung des Kriteriums
"alle Volltexte offen" hat CC BY verlangt und damit systematisch zu
streng gemessen. Auf der Ebene "lesbar in PMC" existieren Reviews mit
vollständiger Abdeckung; für Interventionen liegt der gemessene Bestwert
bei 89 %.

## Grenzen dieser Prüfung

- Befund 5 stützt sich auf Tabellenüberschriften und Marker, nicht auf
  eine manuelle Vollextraktion. Die Einordnung "nein" heißt "nicht
  direkt", nicht "unmöglich".
- Semantic Scholar lieferte keine Ergebnisse; die Provider-Zeile ist
  nicht belastbar.
- Crossref und OpenAlex wurden nur bei Tiefe 100 geprüft.
- Der Zitationspfad wurde nur für zwei Reviews gemessen.
