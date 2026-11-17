# Zweitannotation B — Briefing (Stand 17.11.2026)

> **Vor dem Versand ausfüllen:** `[Zeitfenster]`, `[Startdatum]`, Name, Einrichtung, E-Mail, Telefon.
> Die Anleitung v1.2 ist als **Anhang A** unverändert enthalten und maßgeblich.

## 1. Zweck dieses Dokuments

Dieses Briefing fasst zusammen, worum es im Projekt geht, warum eine unabhängige
Zweitannotation gebraucht wird, was Sie erhalten und wie die Annotation
abläuft. Die Regeln selbst stehen in **Anhang A (Annotationsanleitung v1.2)**;
bei Widersprüchen gilt die Anleitung.

## 2. Das Projekt in Kürze

Wir entwickeln einen autonomen KI-gestützten Forschungsagenten, der
wissenschaftliche Literatur zu einer medizinischen Fragestellung recherchiert,
Volltexte beschafft und auswertet, relevante Effektgrößen extrahiert, die
Evidenz kritisch prüft und die Ergebnisse anschließend statistisch
zusammenführt. Langfristiges Ziel ist ein System, das große Teile eines
systematischen Reviews einschließlich der quantitativen Evidenzsynthese
eigenständig durchführen kann.

Das Projekt ist als Python-Anwendung implementiert und umfasst unter anderem:

- **Literaturrecherche:** automatisierte Suche über mehrere Literaturdatenbanken
  und Quellen.
- **Volltextanalyse:** Beschaffung und Verarbeitung wissenschaftlicher
  PDF-Volltexte.
- **Datenextraktion:** Extraktion von Effektgrößen und statistischen Kennzahlen
  mit wortgetreuen Originalzitaten; jede Zahl soll auf eine konkrete Textstelle
  zurückführbar sein.
- **Tabellenanalyse:** zusätzliche KI-gestützte Auswertung komplexer Tabellen und
  Abbildungen; zwei unabhängige Lesedurchläufe sollen Abweichungen erkennen,
  statt widersprüchliche Werte zu mitteln.
- **Evidenzbewertung:** Prüfung der Studienqualität, Erkennung von Widersprüchen,
  adversariale Überprüfung.
- **Statistische Auswertung:** Metaanalysen und Metaregressionen über
  deterministischen Python-Code. Die Berechnung erfolgt ausdrücklich nicht
  durch ein Sprachmodell, sondern reproduzierbar und überprüfbar.

Code, statistische Komponenten, Tests, Dokumentation und Benchmark-Grundlagen
sind öffentlich dokumentiert. Der Anspruch ist nicht, möglichst viele
Informationen zusammenfassen zu lassen, sondern wissenschaftlich
nachvollziehbare und überprüfbare Ergebnisse zu erzeugen.

## 3. Warum eine unabhängige menschliche Validierung nötig ist

Der aktuelle Engpass ist die zuverlässige Extraktion quantitativer
Studiendaten. Deshalb steht derzeit nicht ein weiterer Modelllauf im
Vordergrund, sondern ein belastbarer menschlicher Goldstandard.

Die bisherige Modellprüfung stützt diese Notwendigkeit: Der aktuelle Kandidat
erreicht **75,8 Prozent exakt extrahierte Felder** und **59,4 Prozent
vollständig exakte Records**. Halluzinationen wurden keine gefunden, die
Freigabegates sind aber nicht bestanden; eine autonome Nutzung ist deshalb
ausgeschlossen.

Ohne unabhängige menschliche Annotation bleibt zudem offen, ob die
Erstannotation systematisch anders liest als eine zweite Person.

## 4. Stand der Annotation

Grundlage sind 30 verblindete Volltexte aus einem gemischten Methodensample:

| Schicht | Dokumente |
|---|---|
| randomisierte Studien (`rct`) | 6 |
| Crossover-Studien (`crossover`) | 3 |
| Kohorten (`cohort`) | 7 |
| Querschnittsstudien (`cross_sectional`) | 5 |
| Übersichtsarbeiten (`aggregate`) | 4 |
| Negativkontrollen (`negative_control`) | 5 |
| **gesamt** | **30** |

- **Erstannotation A:** abgeschlossen, 69 Effektzeilen und 13 Begründungen, warum
  ein Dokument keine Effektzeile enthält; 30 Dokumente, keine offenen. A ist
  eingefroren (SHA-256 dokumentiert) und für Sie nicht einsehbar.
- **Zweitannotation B:** liegt noch nicht vor.
- Es gibt daher weder Konsens noch Kappa; Aussagen zur Inter-Rater-Reliabilität
  sind derzeit nicht möglich.

## 5. Was Sie erhalten

Ein paketiertes Blind-Paket (`blind_b_20261110.zip`) mit:

- den 30 Volltexten (`data/fulltext/<document_id>.txt`),
- dem leeren B-Gerüst `data/golden_effects/goldstandard_B.json` (30 Dokumente,
  0 Zeilen, alle offen),
- der Anleitung v1.2 und dem Schema (`docs/internal/goldstandard_schema.json`),
- 30 Arbeitsblättern mit Tabellen- und Textfundstellen,
- `manifest.json` und `SHA256SUMS.txt`,
- dem Prüfskript `scripts/pruefe_goldstandard.py` (nur Standardbibliothek).

Das Paket ist nicht zur Weitergabe an Dritte bestimmt. Die Erstannotation A,
Modellausgaben und Datenbankeinträge bleiben bis zur Abgabe nicht einsehbar.

## 6. Ablauf

1. ZIP entpacken, im Ordner `blind_b_20261110/` arbeiten.
2. Optional die Prüfsummen kontrollieren:

       sha256sum -c SHA256SUMS.txt

   Unter Windows PowerShell alternativ mit `Get-FileHash` arbeiten.
3. Zuerst die **12 Kalibrierungsdokumente** bearbeiten (die ersten 12 in der
   Reihenfolge des Gerüsts), danach die **13 übrigen Ergänzungen**, zuletzt die
   **5 Negativkontrollen**.
4. Pro Dokument alle relevanten Effekte erfassen oder das Dokument begründet als
   effektlos abschließen.
5. Nach jedem Dokument den Entwurfsprüfer laufen lassen:

       python scripts/pruefe_goldstandard.py --entwurf data/golden_effects/goldstandard_B.json

   Erwartung am Anfang: 0 Fehler, 30 offen. Nach der vollständigen Annotation
   ohne `--entwurf` prüfen; der Lauf muss mit 0 Fehlern und 0 offenen Dokumenten
   enden.
6. SHA-256 der fertigen Datei bilden:

       sha256sum data/golden_effects/goldstandard_B.json

   Unter Windows PowerShell:

       Get-FileHash data/golden_effects/goldstandard_B.json -Algorithm SHA256

7. Datei nach dem Hash nicht mehr ändern.

**Rückgabe:** `data/golden_effects/goldstandard_B.json`, deren SHA-256 und eine
kurze Bestätigung, dass alle 30 Dokumente abgeschlossen sind. Keine anderen
Dateien verändern, keine Teilstände zurücksenden.

Nach der Rückgabe wird das Paket gegen das Gerüst geprüft, danach der Hash
eingefroren und erst dann A geöffnet. Konflikte zwischen A und B werden
dokumentiert und bei Bedarf durch eine dritte Stimme entschieden; die Schwelle
für den Zeilen-Kappa liegt bei 0,80.

## 7. Rahmenbedingungen

- Die Zweitannotation erfolgt **unabhängig**: kein Austausch über Inhalte,
  kein Blick in A, keine Modellausgaben, keine Datenbankeinträge. Gearbeitet
  wird ausschließlich mit Volltext, Anleitung, Schema und dem eigenen
  Arbeitsblatt.
- Alle 30 Dokumente sind vollständig zu bearbeiten; eine Datei mit Teilstand
  wird nicht eingefroren.
- Jede Zeile braucht ein **exaktes Zitat** mit Zeichenposition
  (`quote_start`/`quote_end`).
- Zahlen werden **nicht umgerechnet und nicht gerundet**.
- Jedes Dokument hat entweder Effektzeilen oder eine Begründung
  (`no_effect_reason`), nie beides.
- Rückfragen nur zur Anleitung, zum Schema oder zur Technik. Fragen zu
  A-Entscheidungen oder ein Vergleich mit A sind während der Annotation nicht
  zulässig.

## 8. Format einer vollständigen Effektzeile

**Aus Blindheitsgründen enthält dieses Briefing keinen Auszug aus A.** Ein
Beispiel aus der Erstannotation würde Ihnen die unabhängige Lesung nehmen.
Stattdessen zeigt **Anhang A, Abschnitte A.1 bis A.4** den Aufbau einer
abgabefähigen Zeile:

- **A.1** die 14 Pflichtfelder einer Effektzeile mit Regelverweis,
- **A.2** ein Gerüst zum Abschreiben (alle Werte als Platzhalter),
- **A.3** den Prüfweg für `quote_start`/`quote_end`,
- **A.4** die häufigen Fehler, die der Prüfer meldet.

Die Platzhalter sind keine Datenwerte. Maßgeblich sind immer der Volltext und
die Anleitung.

## 9. Zeitplan

Die Annotation ist in zwei Tranchen gedacht: zuerst die zwölf
Kalibrierungsdokumente, danach die 13 Ergänzungen; die fünf Negativkontrollen
werden zuletzt bearbeitet. Zwischen den Tranchen prüfen wir kurz, ob die
Anleitung an den Grenzfällen trägt, ohne Inhalte auszutauschen.

- Zeitfenster: `[Zeitfenster]`
- Start: `[Startdatum]`

Beides ist noch nicht festgelegt und wird vor Beginn abgestimmt. Eine
belastbare Stundenschätzung für die 30 Dokumente liegt noch nicht vor; nach den
ersten drei Dokumenten können wir den tatsächlichen Aufwand gemeinsam
einschätzen, ohne während der Annotation Inhalte auszutauschen.

## 10. Kontakt

`[Name]`
`[Projekt oder Einrichtung]`
`[E-Mail-Adresse]`
`[Telefonnummer, optional]`

Rückfragen zur Anleitung, zum Schema oder zur Technik sind jederzeit möglich.

---

# Anhang A: Annotationsanleitung v1.2 (Regeln 1–9 unverändert, mit Format-Anhang vom 17.11.2026)

## Annotationsanleitung Goldstandard — Effektzeilen (v1.2, 2026-11-10)

Ziel: Ein unabhängiger, wiederholbarer Maßstab für die Effektgrößen-Extraktion.
Zwei Personen annotieren **dieselben 30 Dokumente getrennt**. Gemessen wird
gegen den Konsens, nicht gegen die Datenbank. v1.1 ergänzt den Grenzfall 5.11
(Spannweite über Zeitpunkte); v1.2 präzisiert 5.9 für Dosis-Wirkungs-Peaks und
Sensitivitätsanalysen.

Das JSON-Schema steht in `docs/internal/goldstandard_schema.json`. Ein
öffentliches Beispiel wird aus Blindheitsgründen nicht bereitgestellt; der
Formatprüfer ist `scripts/pruefe_goldstandard.py`.

---

### 1. Rollen und Blindheit

- **Annotator A** und **Annotator B** arbeiten unabhängig, ohne Austausch
  während der Annotation.
- **Blindheit:** Keine Einsicht in `study_effects`, Modellausgaben, frühere
  Extraktionen oder die Datei des anderen. Nur der Volltext, diese Anleitung
  und das Schema.
- **Konsens:** Nach Abschluss vergleicht eine dritte Person (oder A und B
  gemeinsam, erst nach Abgabe) Zeile für Zeile. Einigung wird dokumentiert;
  bleibt ein Konflikt, entscheidet ein dritter Annotator. Konflikte werden
  gezählt, nicht stillschweigend geglättet.
- **Einfrieren:** Nach der Abgabe wird die Datei per SHA-256 eingefroren
  (Ausgabe des Prüfskripts), committed und nicht mehr geändert. Korrekturen
  erzeugen eine neue Version mit neuem Datum.

---

### 2. Ablauf

1. Dokument im Volltext vollständig lesen (nicht nur Abstract).
2. Alle Stellen markieren, die einen **quantifizierten Effekt mit
   Unsicherheit** berichten — Fließtext, Tabelle, Abbildungsunterschrift.
3. Jede Stelle als eine Effektzeile erfassen (Definition unten).
4. Quote exakt kopieren und `quote_start`/`quote_end` bestimmen (die
   Prüfskript-Ausgabe zeigt die Abweichung, wenn der Span nicht passt).
5. Dokument abschließen: entweder Zeilen oder `no_effect_reason`.
6. Datei abgeben, Hash notieren, erst danach vergleichen.

**Regel gegen Optimierung:** Nicht raten, nicht ergänzen, nicht aus anderen
Tabellen rechnen. Was nicht dasteht, ist keine Zeile. Eine fehlende Zeile ist
ein echter Befund, keine Lücke, die man schließen muss.

---

### 3. Was ist eine Effektzeile?

Eine Zeile = **eine geschätzte Effektgröße** für genau eine Kombination aus:

- Outcome,
- Vergleich (Intervention vs. Kontrolle, Expositionsgruppe vs. Referenz),
- Zeitpunkt,
- Adjustierung (adjustiert vs. unadjustiert),
- Analysepopulation (Gesamt oder stratifiziert).

**Getrennte Zeilen** entstehen bei:

- mehreren Outcomes (Rezidiv, Mortalität, Fatigue),
- mehreren Kontrasten (hoch vs. niedrig, mittel vs. niedrig),
- mehreren Zeitpunkten (6 Monate, 12 Monate),
- mehreren Adjustierungsmodellen, wenn beide berichtet werden,
- mehreren Studienarmen (Dosis A, Dosis B), sofern je Arm ein eigener Effekt
  mit Unsicherheit steht,
- Subgruppen (Männer/Frauen), sofern getrennt berichtet.

**Keine eigene Zeile** sind:

- derselbe Effekt in zwei Darstellungen (Text und Tabelle) — einmal erfassen,
  die klarere Stelle als Quote wählen und in `notes` auf die Dopplung
  hinweisen,
- ein p-Wert ohne Effekt und ohne Unsicherheit,
- eine reine Beschreibung ohne Zahl,
- ein Review-Aggregat, das als solches erkannt wird: **eine** Zeile mit
  `is_primary: false` und `design_category: aggregate` (siehe 5.8).

---

### 4. Feldregeln

| Feld | Regel |
|---|---|
| `document_id` | Dateistamm des Volltexts ohne `.txt` |
| `title` | Titel wie im Dokument, nicht gekürzt |
| `year` | Erscheinungsjahr aus dem Dokument; `null`, wenn nicht erkennbar |
| `design_verbatim` | Designbezeichnung **wörtlich** aus dem Dokument |
| `design_category` | Zuordnung nach 5.1 |
| `stratum` | Auswahlschicht, aus der das Dokument stammt |
| `has_text_layer` | `true`, wenn der Text durchsuchbar ist; `false` bei reiner Bild-PDF |
| `effect_id` | `<document_id>-01`, `-02`, … in Lesereihenfolge |
| `outcome_verbatim` | Outcome **wörtlich** aus der Quelle |
| `outcome_normalized` | Vereinheitlicht (z. B. „Depressive symptoms", „Sleep onset latency") |
| `comparison_verbatim` | Vergleichsgruppe wörtlich |
| `effect_type` | `or`, `rr`, `hr`, `md`, `smd`, `g`, `beta`, `r`, `z`, `other` |
| `effect` | Zahl **wie berichtet**, nicht umgerechnet, nicht gerundet |
| `se` | Standardfehler, falls berichtet; sonst `null` |
| `ci_low`, `ci_high` | Grenzen wie berichtet; sonst `null` |
| `ci_level` | 0,95, wenn nicht anders angegeben; sonst der berichtete Wert |
| `n` | analysierte Stichprobe der Zeile, falls berichtet |
| `adjusted` | `true`/`false`, wenn erkennbar; `null` bei unklarer Angabe |
| `quote` | **exakter** Textausschnitt, der Effekt und Unsicherheit enthält |
| `quote_start`, `quote_end` | Zeichenpositionen im Volltext, `quote_end` exklusiv |
| `certainty` | `high` (Zahl und Unsicherheit eindeutig), `medium` (eine Angabe muss interpretiert werden), `low` (unklar, aber belegt) |
| `is_primary` | `false` nur für gepoolte Schätzer aus Übersichtsarbeiten |
| `notes` | Nur Beobachtungen zum Beleg, keine Bewertung |

**Nie umrechnen.** Kein Logarithmieren, kein Standardisieren, kein
Zusammenfassen. Umgerechnet wird später im Code, nachvollziehbar.

---

### 5. Entscheidungsregeln für Grenzfälle

#### 5.1 Designzuordnung

| `design_category` | Erkennungsmerkmal |
|---|---|
| `parallel_rct` | randomisiert, parallele Gruppen |
| `crossover_rct` | randomisiert, within-subject, Crossover, repeated measures |
| `cluster_rct` | Randomisierung auf Cluster-Ebene |
| `quasi_experimental` | nicht randomisiert, Pretest-Posttest, natürliche Gruppe |
| `observational` | Kohorte, Fall-Kontroll, Querschnitt, Register |
| `aggregate` | Metaanalyse, systematische Übersicht, gepoolter Schätzer |
| `unknown` | Design nicht erkennbar |

Bei mehreren Merkmalen gilt das spezifischste (Crossover vor RCT, Cluster vor
RCT). Ein RCT, der über sich selbst berichtet, ist `parallel_rct`; eine
Metaanalyse über RCTs ist `aggregate`.

#### 5.2 Ratio-Maße (OR, RR, HR)

- `effect` ist der berichtete Wert (z. B. 0,83), nicht der Logarithmus.
- `ci_low`/`ci_high` sind die berichteten Grenzen (0,70/0,99).
- `se` nur übernehmen, wenn sie **explizit** dasteht. Nicht aus dem KI
  ableiten — das macht der Code, und zwar dokumentiert.

#### 5.3 Mittelwertsdifferenzen und standardisierte Maße

- `md` für Differenzen in Originaleinheiten (z. B. Punkte auf einer Skala).
- `smd`/`g` für standardisierte Differenzen; `g` nur, wenn Hedges g explizit
  genannt ist, sonst `smd`.
- Einheit in `notes` festhalten (z. B. „Punkte, PHQ-9").

#### 5.4 Regressionskoeffizienten (`beta`)

- `beta` mit SE oder KI erfassen, Einheit und Skala in `notes`.
- Standardisierte und unstandardisierte Koeffizienten sind verschiedene
  Zeilen, wenn beide berichtet werden.

#### 5.5 Korrelationen (`r`) und Fisher-z (`z`)

- `r` nur, wenn die Korrelation selbst berichtet ist; `z` nur, wenn
  Fisher-z dasteht.
- Ein KI auf r-Skala bleibt auf r-Skala. Nicht in z umrechnen.
- Nennt der Text eine Spannweite über Zeitpunkte (z. B. `rs=[a, b]`), gilt 5.11.

#### 5.6 Median und Interquartilsabstand

Wenn nur Median und IQR berichtet sind und kein Mittelwert/SE: **keine
Effektzeile**, sondern `no_effect_reason` mit dem Hinweis „nur Median/IQR".
Die Umrechnung ist eine Modellannahme, keine Extraktion. (Falls das Projekt
sie später erlaubt, wird sie als eigene, markierte Zeile geführt.)

#### 5.7 p-Wert ohne Effektgröße

Keine Zeile. `no_effect_reason`: „nur p-Wert, keine Effektgröße".

#### 5.8 Übersichtsarbeiten

- Der gepoolte Schätzer ist **eine** Zeile mit `is_primary: false`,
  `design_category: aggregate`.
- Einzelstudien-Ergebnisse, die die Übersicht zitiert, werden **nicht**
  übernommen — sie gehören zur Primärstudie, nicht zu diesem Dokument.
- Wird die Übersicht selbst extrahiert (Kalibrierungsfall), ist die Zeile
  trotzdem korrekt annotiert; das Gate im Code entscheidet über den Pool.

#### 5.9 Mehrere Arme und Dosis

Je Arm eine Zeile, wenn ein eigener Effekt mit Unsicherheit berichtet wird.
Ist nur ein gemeinsamer Effekt über Arme berichtet, ist es **eine** Zeile mit
`notes`: „gepoolt über Arme".

- Ein **Dosis-Wirkungs-Peak** oder ein Punkt der Dosis-Wirkungs-Kurve ist
  **keine** eigene Zeile: Die Dosis ist kein Zeilenkriterium (Abschnitt 3);
  der Peak ist ein Punkt derselben Kurve, kein eigener Vergleich. Der
  gepoolte Hauptschätzer bleibt die Zeile; Peak, Dosis und Kurvenform stehen
  in `notes`.
- Eine **Sensitivitätsanalyse** ist **keine** eigene Zeile, wenn sie dieselbe
  Kombination aus Outcome, Vergleich, Zeitpunkt, Adjustierung und Population
  betrifft; sie steht in `notes` mit dem berichteten Wert.

#### 5.10 Negativkontrolle

Dokumente der Schicht `negative_control` haben keine erwartete Effektzeile.
`effects: []` und `no_effect_reason` mit Begründung (z. B. „nur deskriptive
Statistik", „Review ohne eigene Zahl", „nur p-Werte"). Eine trotzdem
gefundene Zeile wird erfasst — dann ist die Erwartung falsch, nicht die
Annotation.

#### 5.11 Spannweite über Zeitpunkte

Nennt der Fließtext eine Spannweite über Zeitpunkte ("rs=[−0.150, −0.206]",
"range across T1-T3"), ist das **keine** einzelne Effektzeile: Die Einheit
verlangt einen Zeitpunkt (Abschnitt 3).

- **Tabelle oder Abbildung ist die Quelle**, wenn sie die Werte je Zeitpunkt
  auflöst. Je Zeitpunkt eine Zeile, mit `time_point` und Tabellenzitat.
- **Keine Tabelle und keine Auflösung:** keine Zeile raten.
  `no_effect_reason` mit "Spannweite ohne Zeitpunktauflösung"; die Spanne in
  `notes` nennen.
- Eine Spanne ist **kein KI**. `ci_low`/`ci_high` bleiben den berichteten
  Konfidenzgrenzen vorbehalten; Min/Max über Zeitpunkte gehören nicht hinein.
- Bei Korrelationen nennt `notes` das Zeitpunktpaar (z. B. "T3-PA × T1-EDS"),
  weil eine Korrelationsmatrix auch Kreuzkorrelationen enthält.
- Ist nur ein Zeitpunkt genannt und zusätzlich eine Spanne, gilt der genannte
  Zeitpunkt; die Spanne steht in `notes`.

**Beispiel `3790c91f96`:** Der Satz nennt PA × emotionale Symptome
`rs=[−0.150, −0.206]` und PA × körperliche Symptome `rs=[−0.225, −0.266]`.
Tabelle 2 löst auf: emotional T1 −0,17, T2 −0,206, T3 −0,199; körperlich
T1 −0,248, T2 −0,265, T3 −0,266. Das sind sechs Zeilen, nicht zwei. Die
Pipeline speicherte zwei emotionale Zeilen ohne `time_point` und keine
körperliche Zeile; der Abgleich wertet das als Recall-Lücke, nicht als
Matching-Fehler; der Fall ist intern dokumentiert, aber nicht öffentlich
versioniert.

---

### 6. Quote und Positionen

- `quote` ist ein **exakter** Ausschnitt des Volltexts, keine Paraphrase,
  keine Auslassung mit „…".
- Der Ausschnitt muss Effekt **und** Unsicherheit enthalten, wenn beide
  dastehen. Bei Tabellenzeilen genügt die Zelle mit Effekt und KI/SE, sofern
  Outcome und Vergleich aus der Zeilenbeschriftung hervorgehen — beides in
  `notes` festhalten.
- `quote_start`/`quote_end` beziehen sich auf den gespeicherten Text
  (`data/fulltext/<id>.txt`), nicht auf das PDF.
- Das Prüfskript vergleicht `text[start:end] == quote` und meldet jede
  Abweichung. Ein fehlgeschlagener Vergleich ist ein Fehler, keine Warnung.

---

### 7. Qualitätskontrolle

1. Jede Datei läuft durch `scripts/pruefe_goldstandard.py` (Exit 0).
2. Der Prüfer meldet: fehlende Pflichtfelder, unbekannte Enum-Werte,
   Quote-Abweichung, Effekt außerhalb des KI, doppelte `effect_id`,
   Dokument ohne Zeile **und** ohne Begründung.
3. Nach der Vollannotation: Precision/Recall je Dokument und je Schicht;
   Kappa zwischen A und B. Unter **0,80** wird die Anleitung geschärft und
   die betroffene Schicht neu annotiert, bevor der Goldstandard gilt.
4. Der Konsens wird aus A und B gebildet, Konflikte mit dritter Stimme. Die
   Konsensdatei hat `annotator: "consensus"`.

---

### 8. Abgabe

**Probelauf (Format- und Ablauftest):** `scripts/erzeuge_annotationsgeruest.py`
legt die leeren Dateien an (drei Dokumente mit `probelauf: true`). Nach dem
Ausfüllen prüft `scripts/pruefe_probelauf_abgabe.py` Pflichtfelder, Quotes und
Design (Exit 0); eine Kappa-Zahl entsteht dabei nicht. Der Zeilen-Kappa wird
erst nach der Vollannotation aller 30 Dokumente mit
`scripts/werte_kappa_probe.py` (ohne `--probelauf`) gemessen; Schwelle 0,80.

- Dateinamen: `data/golden_effects/goldstandard_A.json`,
  `goldstandard_B.json`, `goldstandard_consensus.json`.
- Eine Datei enthält alle Dokumente des jeweiligen Annotators.
- Nach Abgabe: Hash notieren (`pruefe_goldstandard.py` gibt ihn aus), Datei
  committen, nicht mehr ändern.

---

### 9. Kurzcheck vor der Abgabe

- [ ] Jedes Dokument hat entweder Zeilen oder eine Begründung.
- [ ] Kein Effekt umgerechnet, keine Zahl gerundet.
- [ ] Jede Quote exakt, inklusive Bindestrichen und Gedankenstrichen.
- [ ] Ratio-Werte positiv, KI plausibel (`ci_low < effect < ci_high`).
- [ ] `is_primary: false` nur bei Übersichtsarbeiten.
- [ ] `design_category` nach 5.1, nicht nach Bauchgefühl.
- [ ] Spannweite über Zeitpunkte: je Zeitpunkt eine Zeile aus der Tabelle,
      `time_point` gesetzt (5.11).
- [ ] Prüfskript Exit 0, Hash notiert.

---

### Anhang: Beispiel einer vollständigen Effektzeile (2026-11-17)

**Nicht Bestandteil von v1.2.** Die Regeln der Abschnitte 1–9 bleiben
unverändert; dieser Anhang zeigt nur, wie eine abgabefähige Zeile aufgebaut
ist. Er enthält bewusst **keine echten Werte und kein Zitat aus einem der 30
Dokumente**: Aus Blindheitsgründen (§1) wird kein Beispiel aus einer
abgeschlossenen Annotation bereitgestellt. Alles in spitzen Klammern ist ein
Platzhalter, kein Datenwert.

#### A.1 Die 14 Pflichtfelder einer Effektzeile

| # | Feld | Eintrag | Regel |
|---|---|---|---|
| 1 | `effect_id` | `<document_id>-01`, `-02`, … | Lesereihenfolge (§4) |
| 2 | `outcome_verbatim` | Outcome **wörtlich** aus der Quelle | nicht kürzen (§4) |
| 3 | `outcome_normalized` | vereinheitlichte Bezeichnung | z. B. „Depressive symptoms“ (§4) |
| 4 | `comparison_verbatim` | Vergleichsgruppe wörtlich | Intervention vs. Kontrolle (§4) |
| 5 | `effect_type` | `or`, `rr`, `hr`, `md`, `smd`, `g`, `beta`, `r`, `z`, `other` | nach 5.2–5.5 |
| 6 | `effect` | Zahl **wie berichtet** | nicht umrechnen, nicht runden (§4) |
| 7 | `ci_low` | untere Grenze wie berichtet | `null`, wenn nicht berichtet |
| 8 | `ci_high` | obere Grenze wie berichtet | `null`, wenn nicht berichtet |
| 9 | `quote` | exakter Ausschnitt mit Effekt **und** Unsicherheit | keine Paraphrase (§6) |
| 10 | `quote_start` | Zeichenposition des ersten Zeichens | 0-basiert im gespeicherten Text (§6) |
| 11 | `quote_end` | Position **hinter** dem letzten Zeichen | exklusiv (§6) |
| 12 | `design_verbatim` | Designbezeichnung wörtlich | aus dem Dokument, nicht aus dem Titel |
| 13 | `certainty` | `high`, `medium`, `low` | nach §4 |
| 14 | `is_primary` | `true`; `false` nur für gepoolte Schätzer | nach 5.8 |

Zusätzliche Felder sind freiwillig, aber erlaubt: `se`, `ci_level`, `p_value`,
`n`, `adjusted`, `time_point`, `population`, `section`, `page`,
`source_table`, `notes`.

#### A.2 Gerüst zum Abschreiben (Platzhalter, keine Werte)

```json
{
  "effect_id": "<document_id>-01",
  "outcome_verbatim": "<Outcome wörtlich aus der Quelle>",
  "outcome_normalized": "<vereinheitlichte Bezeichnung>",
  "comparison_verbatim": "<Vergleichsgruppe wörtlich>",
  "effect_type": "<or|rr|hr|md|smd|g|beta|r|z|other>",
  "effect": "<Zahl wie berichtet>",
  "se": null,
  "ci_low": "<untere Grenze wie berichtet>",
  "ci_high": "<obere Grenze wie berichtet>",
  "quote": "<exakter Ausschnitt mit Effekt und Unsicherheit>",
  "quote_start": "<Position des ersten Zeichens>",
  "quote_end": "<Position hinter dem letzten Zeichen>",
  "design_verbatim": "<Designbezeichnung wörtlich>",
  "certainty": "<high|medium|low>",
  "is_primary": true,
  "notes": "<nur Beobachtungen zum Beleg>"
}
```

Die spitzen Klammern sind ersetzt zu füllen; die JSON-Anführungszeichen um
`effect`, `quote_start` und `quote_end` fallen dabei weg, weil dort Zahlen
stehen. `certainty` ist `high` nur, wenn Zahl **und** Unsicherheit eindeutig
dastehen.

#### A.3 Quote und Positionen: der Prüfweg

Das Prüfskript vergleicht `text[quote_start:quote_end] == quote`. Der
Zusammenhang, schematisch und ohne Bezug zu einem Dokument:

```
Text:   A A A   B B B   C C C
Index:  0 1 2 3 4 5 6 7 8 9 10
quote = "BBB"   ->  quote_start = 4, quote_end = 7
```

`quote_end` zeigt auf das Zeichen **hinter** dem Ausschnitt. Ein Ausschnitt,
der Effekt und Unsicherheit nicht beide enthält, ist unvollständig (§6) –
bei Tabellenzeilen genügt die Zelle mit Effekt und KI, wenn Outcome und
Vergleich aus der Zeilenbeschriftung hervorgehen und in `notes` stehen.

#### A.4 Häufige Fehler, die der Prüfer meldet

- Anführungszeichen, Bindestriche oder Gedankenstriche im `quote` weichen vom
  Volltext ab → Exit ≠ 0, keine Warnung (§6).
- `effect` außerhalb von `ci_low`/`ci_high`, oder Ratio-Werte ≤ 0.
- `is_primary: false` bei einer Primärstudie (nur 5.8 erlaubt das).
- Dokument ohne Zeile **und** ohne `no_effect_reason` (oder beides zugleich).
- Zwei Zeilen für denselben Effekt in Text und Tabelle statt einer Zeile mit
  Hinweis in `notes` (§3).
