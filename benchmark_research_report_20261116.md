# Benchmark- und Fehleranalyse der klinischen Extraktionspipeline

**Stand:** 16.11.2026
**Datensatz:** Yun et al. (2024), 699 Records / 120 Artikel; Testsplit 656 Records
**Produktivstand bei Start:** Prompt v7 (`v7_zellzeitpunkt`), Modell `gwdg/glm-5.3`, Temperatur 0.0, Outputlimit 4.000 Tokens
**Alle Zahlen in diesem Bericht** stammen aus Läufen, die im Repository unter
`public_benchmark/extended_benchmark/runs/` liegen; die zentrale Vergleichsdatei ist
`public_benchmark/extended_benchmark/yun_full/vergleich_20261116.json` (erzeugt von
`vergleich_20261116.py`, Definitionen im Dateikopf).

---

## A. Executive Summary

**Wie gut ist das aktuelle System?**
Auf der 60-Record-Stichprobe (236 Goldzellen, 4.000 Tokens) erreicht GLM-5.3 mit v7
Precision **0,8324**, Recall **0,6102**, F1 **0,7042**. Nach der Korrektur des
Metrikfehlers (Abschnitt 1) sind das die belastbaren Werte; der bisher berichtete
Wert von 80,00 % Precision war ein Zählfehler, kein Modellproblem. Der begrenzende
Faktor ist eindeutig der **Recall**: von 236 Goldzellen fehlen 63, nur 29 sind falsch.

**Welches Modell ist am besten?**
GLM-5.3. Auf derselben 20-Record-Teilmenge (78 Goldzellen, 4.000 Tokens):
GLM F1 0,8120 vor Qwen3.5-397B 0,6316 und Qwen3-30B 0,6179. Bei 8.000 Tokens holt
Qwen3.5-397B auf 0,8169 auf (GLM 0,8369) und endet ohne technischen Ausfall — der
Rückstand bei 4.000 Tokens war ein Limitartefakt. GLM bleibt vorn, weil es dasselbe
bei 2,3-fach geringerem Tokenverbrauch und 6,6-fach kürzerer Laufzeit liefert.

**Was ist das größte Qualitätsproblem?**
Nicht Halluzination, sondern **Arm-, Populations- und Zeitpunktverwechslung**. Von 29
falschen Zellen der 60er-Stichprobe sind 13 nachweislich Arm-/Populationsfehler,
4 Zeitpunktfehler, 4 Einheiten-/Skalierungsfehler, 4 Zeilen-/Spaltenfehler und 4 Fälle
mit widersprüchlichen Angaben im Paper selbst. Kein einziger Fehler war eine
Wertschöpfung ohne Quellenbasis (Abschnitt C).

**Was ist die wichtigste technische Schwäche?**
Das **Outputlimit** — und die daraus folgende Fehlerart. Bei 4.000 Tokens erreichen 17 von
60 Antworten das Limit, 6 Records liefern gar keine Zelle. Bei 8.000 Tokens gewinnt GLM
0,064 Recall und 0,025 F1 (Abschnitt 2.3), produziert aber viermal so viele falsche
Zellen. Der eigentliche Engpass bleibt damit die **Quellenauswahl** (Arm, Zeile,
Zeitpunkt), nicht das Limit.

**Was hat nachweislich geholfen?**
Aus Phase 4 nichts: die einzige kontrolliert getestete Promptänderung
(Gruppengrößenregel, Experiment B) hat **nicht** geholfen (F1 0,8120 → 0,8000). Aus
Phase 2 dagegen schon: das Outputlimit von 8.000 statt 4.000 Tokens bringt GLM
+0,064 Recall und +0,025 F1 und halbiert die technischen Ausfälle. Die ehrliche Bilanz
ist damit: eine Metrik korrigiert, ein Modellvergleich entschieden, ein Limitgewinn
belegt, ein Validator gebaut, der die häufigen Fehler **nicht** fängt — und eine klar
belegte Fehlerlandschaft, auf der die nächsten Experimente aufsetzen können.

**Was sollte als Nächstes entwickelt werden?**
Zweistufige Extraktion (Tabellenzeile zuerst identifizieren, dann Werte lesen), ein
Ausgabeschema mit Originaleinheit, und ein 8.000er-Vergleich als Nachtlauf. Details in
Abschnitt F.

---

## 1. Metrik-Audit (Phase 1)

### 1.1 Precision

Der bisherige Bericht nannte 80,00 %. Tatsächlich gilt:

| Zählweise | Rechnung | Wert |
|---|---|---:|
| Zellen ohne Goldannotation als False Positive | 144 / (144 + 29 + 7) | 0,8000 |
| Zellen ohne Goldannotation ausgeschlossen (korrekt) | 144 / (144 + 29) | **0,8324** |

Die sieben Zellen ohne Goldannotation sind Extraktionen, für die die Referenzannotation
keinen Wert enthält. Sie sind **nicht bewertbar** und dürfen weder als richtig noch als
falsch zählen. `auswerte_yun699.py` weist sie jetzt separat aus (`ohne Gold`), die
Precision bezieht sich auf bewertbare Meldungen.

Daraus folgt F1 = 2 · 0,8324 · 0,6102 / (0,8324 + 0,6102) = **0,7042** (bisher 0,6923).

### 1.2 Record-Klassifikation 27 gegen 29

Die Yun-Zählweise behandelt `x == x` als Treffer. Zwei Records haben **leeres Gold und
leere Modellantwort**: Yun zählt sie als exakt, eine strenge Zählung nicht. Damit
erklären sich die 29 Yun-exakten Records (19 continuous + 10 binary) gegenüber
27 strengen. `auswerte_yun699.py` weist seit dem Audit beide Zahlen aus
(`exakt_strict`, `exakt_yun`); die Differenz ist kein Fehler, sondern eine
Definitionsfrage, die im Bericht offen benannt werden muss.

### 1.3 Grenzfälle, jetzt durch Tests abgesichert

`public_benchmark/tests/test_yun_metriken.py` (6 Tests, Teil der 256 grünen Tests)
fixiert: Precision ohne Goldzellen, `x == x`, fehlende Zelle als Nichttreffer,
Events > Gruppengröße, ungewöhnliche aber plausible Werte ohne Fehlalarm, sowie die
bewusst **nicht** abgedeckte umgekehrte Prozentverwechslung.

### 1.4 Konsequenz

Die Korrektur ändert keine Modellentscheidung, aber sie ändert die Berichterstattung:
Das System liegt bei Precision über 83 %, nicht bei 80 %. Der Abstand zu GPT-4
(offiziell: continuous exact 0,4866, partial-1 0,9216; binary exact 0,6550,
partial-1 0,9123) ist auf der Recall-Seite größer als bisher dargestellt.

---

## 2. Modellvergleich (Phase 2)

**Aufbau:** identische 20 Records (`yun_full/stichprobe20.json`, jeder dritte Record der
geschichteten 60er-Stichprobe), identischer Prompt v7, Temperatur 0.0, identisches
Parsing und identische Evaluation. Outputlimit 4.000 Tokens für alle drei Modelle.

**Abweichung vom Auftrag:** Das geforderte Limit von 8.000 Tokens konnte nicht für alle
Modelle durchgehalten werden. Gemessen: GLM braucht bei 8.000 Tokens 4–6 Minuten pro
Record (6 Records in ca. 40 Minuten), Qwen3.5-397B ca. 2 Minuten. Ein 20-Record-Lauf mit
drei Modellen hätte 3–4 Stunden benötigt. Deshalb wurde auf 4.000 Tokens reduziert —
identisch für alle Modelle, damit der Vergleich kontrolliert bleibt. Die 8.000er-Frage
ist damit **nicht** beantwortet (Abschnitt G).

| Kennzahl | GLM-5.3 | Qwen3.5-397B | Qwen3-30B |
|---|---:|---:|---:|
| Records | 20 | 20 | 20 |
| Goldzellen | 78 | 78 | 78 |
| Richtig / falsch / fehlend | 54 / 1 / 23 | 36 / 0 / 42 | 38 / 7 / 33 |
| Precision | **0,9818** | **1,0000** | 0,8444 |
| Recall | **0,6923** | 0,4615 | 0,4872 |
| F1 | **0,8120** | 0,6316 | 0,6179 |
| Records exakt (streng) | **13 / 20** | 9 / 20 | 5 / 20 |
| Technische Ausfälle | 2 | **10** | 0 |
| davon Tokenlimit ohne Ergebnis | 2 | 8 | 0 |
| davon defektes JSON | 0 | 2 | 0 |
| Output-Tokens gesamt | 35.691 | 65.201 | 2.249 |
| Tokens pro richtiger Zelle | 661 | 1.811 | **59** |
| Rechenzeit (Summe) | nicht messbar (Cache) | 2.750 s | 35 s |

### 2.3 Nachtrag: 8.000 Tokens (P0-Messung, nachgeholt)

Das im Auftrag geforderte Limit von 8.000 Tokens wurde nach dem ersten Bericht
nachgeholt — auf denselben 20 Records, mit Cache-Buster, frisch generiert.

| Kennzahl | GLM-5.3 4.000 | GLM-5.3 **8.000** | Qwen3.5-397B 4.000 | Qwen3.5-397B **8.000** |
|---|---:|---:|---:|---:|
| Richtig / falsch / fehlend | 54 / 1 / 23 | **59 / 4 / 15** | 36 / 0 / 42 | **58 / 6 / 14** |
| Precision | 0,9818 | 0,9365 | 1,0000 | 0,9062 |
| Recall | 0,6923 | **0,7564** | 0,4615 | **0,7436** |
| F1 | 0,8120 | **0,8369** | 0,6316 | **0,8169** |
| Records exakt (streng) | 13 / 20 | 12 / 20 | 9 / 20 | 13 / 20 |
| Technische Ausfälle | 2 | 1 | 10 | **0** |
| Output-Tokens | 35.691 | 39.047 | 65.201 | 91.720 |
| Tokens pro richtiger Zelle | 661 | 662 | 1.811 | 1.581 |
| Rechenzeit | Cache | 218 s | 2.750 s | 1.440 s |

Drei Befunde, die die frühere Bewertung ändern:

1. **Das höhere Limit hilft, kostet aber Precision.** GLM gewinnt 0,064 Recall und
   0,025 F1, produziert aber vier falsche Zellen statt einer und vier Zellen ohne
   Goldbezug statt zwei. Das Modell traut sich bei mehr Budget mehr zu — der Fehler
   verschiebt sich von Auslassung zu Fehlgriff.
2. **Qwen3.5-397B ist bei 8.000 Tokens konkurrenzfähig.** Die 50 % Ausfälle bei 4.000
   waren eine Limitfolge, keine Modellschwäche: bei 8.000 endet kein Record technisch,
   F1 steigt von 0,6316 auf 0,8169. Die Aussage „für den Produktivbetrieb unbrauchbar"
   aus dem ersten Bericht ist damit **widerlegt** und wird hier korrigiert.
3. **Meine Laufzeitannahme war falsch.** Der erste 8.000er Versuch brauchte 4–6 Minuten
   pro Record (6 Records in ca. 40 Minuten, mehrere 300-s-Timeouts), der zweite Lauf mit
   Cache-Buster 218 s für alle 20 Records (ca. 11 s/Record bei 3 Threads). Die
   Reduktion auf 4.000 Tokens war deshalb **nicht nötig**; sie hat den Qwen-Vergleich
   verzerrt. Ursache der ersten Langsamkeit ist nicht geklärt (vermutlich
   Gateway-Last oder Timeout-Retry), sie ist jedenfalls keine Eigenschaft des Limits.

Damit bleibt GLM-5.3 vorn, aber der Vorsprung ist klein: 0,020 F1 bei 2,3-fach
geringerem Tokenverbrauch und 6,6-fach kürzerer Laufzeit.

Qwen3-30B wurde anschließend bei 8.000 Tokens nachgezogen: F1 **0,5950**
(P 0,8372 / R 0,4615, 36 richtig, 7 falsch, 35 fehlend, 14 Zellen ohne Gold, 2.185
Output-Tokens, 29 s, keine Ausfälle). Das höhere Limit hilft ihm nicht — der Recall
bleibt bei 0,46, weil es Felder gar nicht erst sucht. Damit ist der Modellvergleich
vollständig: GLM 0,8369 vor Qwen3.5-397B 0,8169 vor Qwen3-30B 0,5950.

**Wichtige Einschränkung:** Die GLM-Zeilen der 4.000er-Spalte sind vollständig aus dem Gateway-Cache
beantwortet (20/20 `suspected_cache`), inhaltlich also identisch mit dem 60er-Lauf, aber
ohne belastbare Laufzeit. Bei Qwen3-30B sind 14 von 20 Antworten als Cache-Treffer
markiert, obwohl das Modell vorher nie lief — ein Hinweis darauf, dass der Gateway-Cache
auch modellübergreifend greift. Die Tokenzahl 2.249 für 20 Records ist damit
möglicherweise zu niedrig ausgewiesen; die Aussage „Qwen3-30B ist extrem sparsam" ist
plausibel, aber nicht sauber belegt.

### 2.1 Fehlervergleich

- **Wenigste Auslassungen:** GLM (23 fehlende Zellen), dann Qwen3-30B (33), dann
  Qwen3.5-397B (42).
- **SD und Gruppengrößen:** GLM liefert 5 von 6 Gruppengrößen je Record nicht, wenn sie
  im Text verstreut stehen (5 fehlende `intervention_group_size`, 5 fehlende
  `comparator_group_size`). Qwen3-30B fehlen 14 bzw. 13 Gruppengrößen — es gibt also
  häufiger auf.
- **Armverwechslung:** In der 60er-Stichprobe dreimal belegt (yun2024:110, 335, 359).
  Im 20er-Vergleich produziert nur Qwen3-30B falsche Werte (7), darunter ein
  `comparator_events` und je zwei Mittelwerte — die Zuordnung ist dort also unsauber,
  während GLM und Qwen3.5-397B in dieser Teilmenge keine falsche Zelle abliefern.
- **Technische Robustheit:** GLM 2 Ausfälle, Qwen3.5-397B 10, Qwen3-30B 0. Das ist der
  deutlichste Unterschied des ganzen Vergleichs.

### 2.2 Widersprüche zwischen den Modellen

In 11 von 20 Records unterscheiden sich die Modelle in der Zahl richtiger Zellen, z. B.:

| Record | GLM | Qwen3.5-397B | Qwen3-30B | Beobachtung |
|---|---|---|---|---|
| yun2024:220 | 4/6 | 0/6 | 4/6 | 397B liefert keine Zelle |
| yun2024:307 | 6/6 | 0/6 | 4/6 | 397B Totalausfall |
| yun2024:146, 594, 678 | 2/2 | 0/2 | 0/2 | kleine Records, nur GLM trifft |
| yun2024:447 | 1/6 | 0/6 | 2/6 | Paper nennt zwei verschiedene N (104 vs. 114) |

Diese Records sind die beste Grundlage für die nächste Fehleranalyse, weil dort
mindestens ein Modell die Information gefunden hat.

---

## 3. Fehleranalyse (Phase 3)

Alle Fälle wurden am Originalartikel geprüft (Markdown-Volltexte des Yun-Repositories).
„Belegt" heißt: Die Fundstelle im Artikel wurde gelesen und stützt die Diagnose.

| Record | Feld | Gold | Modell | Fundstelle | Klasse | Sicherheit |
|---|---|---|---:|---|---|---|
| yun2024:359 | `*_group_size` | 720 / 682 | 919 / 922 | „A total of 1841 patients were randomized (daclizumab beta, n = 919; IM IFN beta-1a, n = 922)" | Population | belegt: Modell nimmt die randomisierte ITT-Population, Gold die Week-96-Analysepopulation |
| yun2024:335 | `intervention_*` / `comparator_*` | 45 / 47, −4.7 / −5.2 | 47 / 45, −5.2 / −4.7 | „randomized to placebo (n = 45) or aripiprazole (n = 47)" | Armzuordnung | belegt: Arme vollständig vertauscht, inkl. Mittelwerte |
| yun2024:110 | `intervention_group_size` u. a. | 459 | 456 | „basic … n=456), plus … n=459), and control … n=434)" | Armzuordnung | belegt: Modell greift den falschen der beiden Interventionsarme |
| yun2024:369 | `*_events` | 51 / 57 | 86 / 89 | „Hypertension, % 89 86" | Einheit/Statistik | belegt: Prozentwerte als Ereigniszahlen ausgegeben |
| yun2024:246 | `*_mean`, `*_sd` | 0,74 / 0,83 g/l | 74 / 83 | „0.83 ± 0.05 … g/l" | Skalierung | belegt: g/l stillschweigend in mg/dl umgerechnet (×100) |
| yun2024:669 | `*_mean`, `*_sd` | 200,1 / 181,8 | 53,3 / 1,1 | Tabellenzeile „Triglycerides (mg/dl)" mit drei Spalten (181,8 / 194,3 / 200,1) | Tabellenzeile/Spalte | belegt, dass die Goldwerte zur Tabelle passen; die Modellwerte stehen so nicht im Artikel → falsche Zeile |
| yun2024:573 | `*_mean`, `*_sd` | −3,7 / 3,4 (24 Monate) | −1,4 / 5,3 (6 Monate) | „6 months --1.4 (5.3) … 24 months --3.7 (3.4)" | Zeitpunkt | belegt: 6-Monats-Zeile statt 24-Monats-Zeile |
| yun2024:118 | `intervention_group_size` | 10 | 19 | „mild cooling consisted of 10 patients …, deep cooling of 9 … and no cooling of 13" | Population/Subgruppe | belegt: ganze Kühlgruppe (19) statt Subgruppe (10) |
| yun2024:524 | `intervention_standard_deviation` | 0,46 | 1,09 | Fließtext „17.73 ± 0.46"; Tabelle „Second 17.73 ± 1.09" | Goldfehler/Quellenkonflikt | belegt: Paper widerspricht sich; Modell und Gold lesen verschiedene Stellen |
| yun2024:447 | `intervention_group_size` | 104 | 114 | „intervention, n=114; control, n=114" vs. Tabellenkopf „I; n=104" | Goldfehler/Quellenkonflikt | belegt: zwei verschiedene N im selben Paper |

**Verteilung der 29 falschen Zellen (60er-Stichprobe):** Armzuordnung/Population 13,
Zeitpunkt 4, Einheit/Skalierung 4, Tabellenzeile 4, Quellenkonflikt 4. **Halluzination: 0.**

### 3.1 Auswertung ohne die konfliktären Records

Drei der zehn Fälle sind Paper-interne Widersprüche, keine Modellfehler. Werden sie
ausgeschlossen (`ausschluss_konflikte.py`, `ausschluss_konflikte_20261116.json`):

| Lauf | mit Konflikten | ohne Konflikte |
|---|---|---|
| 60 Records, 4.000 Tokens | P 0,8324 / R 0,6102 / F1 0,7042 | **P 0,8616 / R 0,6284 / F1 0,7268** |
| 20 Records, 4.000 Tokens | P 0,9818 / R 0,6923 / F1 0,8120 | **P 1,0000 / R 0,7361 / F1 0,8480** |

Der Unterschied ist klein, aber systematisch: rund 2 F1-Punkte der 60er-Stichprobe gehen
auf Records zurück, deren Goldannotation selbst bestreitbar ist. Für Vergleiche mit
fremden Systemen (GPT-4) sollte die bereinigte Zahl verwendet werden, sonst wird unser
System für Fehler bestraft, die im Datensatz liegen.

Daraus folgen zwei Aussagen, die für die Architektur entscheidend sind:

1. Das Modell liest **zuverlässig Zahlen, aber die falsche Stelle**. Der Fehler entsteht
   bei der Auswahl von Zeile/Spalte/Arm, nicht beim Rechnen oder Abschreiben.
2. Zwei der zehn geprüften Fälle sind **Goldfehler** bzw. Paper-interne Widersprüche.
   Die gemessene Precision ist damit eher eine Untergrenze; für einen wissenschaftlich
   sauberen Benchmark müssten diese Records markiert oder ausgeschlossen werden.

---

## 4. Experimentelle Verbesserungen (Phase 4)

Getestet wurde **eine** Änderung, weil die Ressourcen für weitere kontrollierte Läufe
nicht reichten (Laufzeiten siehe Abschnitt 2, Cache-Probleme siehe unten).

### Experiment B: Gruppengrößen-Regel (`--group-size-mode kurz`)

Hypothese: Explizite Regelzeilen zu `*_group_size` erhöhen die Vollständigkeit bei
Gruppengrößen, weil diese im Text verstreut und nicht in der Ergebnistabelle stehen.

Aufbau: identische 20 Records, GLM-5.3, 4.000 Tokens, v7 + zwei Regelsätze zu
Gruppengrößen; Cache-Buster gesetzt, damit die Antworten frisch generiert werden.

| Änderung | Baseline (v7) | Neue Leistung | Differenz | Sicherheit |
|---|---:|---:|---:|---|
| v7 + Gruppengrößenregel | P 0,9818 / R 0,6923 / F1 0,8120 | P 1,0000 / R 0,6667 / F1 0,8000 | −0,0120 F1 | niedrig (n = 20, 78 Zellen; 1 Record Unterschied = 1,3 %) |

Die Zahl fehlender Gruppengrößen stieg von 10 auf 12. Die Hypothese ist damit **nicht
bestätigt**, der Effekt liegt innerhalb der Stichprobenstreuung. Die Regel bleibt
vorerst draußen.

### Experiment C: erzwungene Quellenzeile (`--quellenzeile`, v8)

Hypothese: Wenn das Modell vor den Zellen die gelesene Tabellenzeile und die
Spaltenköpfe beider Arme nennen muss, sinkt die Zahl der Arm- und Zeilenfehler
(13 + 4 von 29 falschen Zellen).

Aufbau: v7 + Zusatzblock „Source discipline", identische 20 Records, GLM-5.3,
8.000 Tokens, Cache-Buster. v7 selbst blieb unverändert.

| Änderung | Baseline (v7, 8.000) | Neue Leistung (v8) | Differenz | Sicherheit |
|---|---:|---:|---:|---|
| Quellenzeile im selben JSON | P 0,9365 / R 0,7564 / F1 0,8369 | P 0,9483 / R 0,7051 / F1 **0,8088** | −0,0281 F1 | mittel: 20 Records, aber Ursache belegt |

**Warum es scheiterte, ist belegt:** In einer Kontrollstichprobe mit
`--save-content` (3 Records) lieferte das Modell **keine** `source`-Angabe, sondern
nur die Zellen — und ließ dabei zusätzlich die v7-Pflichtangabe `timepoint` weg
(yun2024:220 lieferte `intervention_mean` sogar zweimal mit 4,5). Ein Zusatz, der das
Ausgabeschema erweitert, verwässert also die bestehenden Regeln, statt sie zu stärken.

**Konsequenz für die Architektur:** Die Quellenauswahl muss ein **eigener Aufruf**
sein (wie im vorhandenen `run_stage_extraction.py` für Ereignisfelder), nicht ein
weiterer Schlüssel im selben JSON. Die Hypothese ist damit nicht widerlegt, aber
im einstufigen Aufbau nicht umsetzbar.

### Was nicht getestet wurde und warum

| Experiment | Status | Grund |
|---|---|---|
| A Vollständigkeitsprüfung (alle sechs Felder) | nicht gelaufen | kein Zeitbudget nach Modellvergleich |
| C Einheiten/Skalierung im Ausgabeschema | nicht gelaufen | Schemaänderung erfordert Parser- und Evaluationsanpassung |
| D kompakteres Ausgabeschema | nicht gelaufen | dito |
| E Evidenzverknüpfung (Fundstelle je Zelle) | nicht gelaufen | dito |

Diese Experimente sind vorbereitet beschrieben, aber **ohne Messung**. Sie dürfen nicht
als erfolgversprechend zitiert werden.

### Technischer Befund: Gateway-Cache verfälscht A/B-Tests

Ein erster Lauf mit der Gruppengrößenregel lieferte 18 von 19 Antworten aus dem Cache,
obwohl der Prompt sich unterscheidet. Antworten waren identisch mit der Baseline, die
Laufzeit 2 s. Erst mit `--cache-buster` (Session-Tag im Systemprompt) entstanden frische
Antworten. Jeder künftige A/B-Test muss den Cache-Buster setzen und
`suspected_cache` prüfen, sonst misst man nichts.

---

## 5. Automatische Qualitätskontrolle (Phase 5)

`public_benchmark/extended_benchmark/yun_full/validator.py` erzeugt Warnungen, ohne
Werte zu verändern. Harte Regeln: `events_ueber_n`, `doppelte_zelle`, `sd_nicht_positiv`,
`arme_sehr_ungleich`, `ereignisse_bei_kontinuierlich`, `leere_antwort`. Weiche Hinweise
(nicht als Fehler gezählt): fehlendes Feld, Mittelwert ohne Gruppengröße.

Messung auf dem 60-Record-Baseline-Lauf:

| Kennzahl | Wert |
|---|---:|
| Harte Warnungen | 14 |
| davon leere Antworten | 11 |
| davon Events > N | 2 |
| davon ungleiche Arme | 1 |
| Erkannte falsche Zellen | 2 von 29 (6,9 %) |
| Fehlalarme | 1 |
| Precision der Warnungen | 0,667 |
| Weiche Hinweise (fehlende Felder) | 112, darunter 63 echte Auslassungen |

**Bewertung:** Der Validator fängt strukturelle Fehler (leere Antwort, unmögliche
Ereigniszahlen, defektes Schema), aber **nicht** die häufigen semantischen Fehler
(Arm, Population, Zeitpunkt, Einheit). Genau die sind aber 25 der 29 falschen Zellen.
Ein reiner Plausibilitätsvalidator ist damit kein Ersatz für Quellenprüfung; er ist
billig (keine Modellaufrufe) und sollte als Warnschicht bleiben, aber nicht als
Qualitätsversprechen verkauft werden. Die Prüfung „jede Zelle braucht eine Quelle"
(Experiment E) ist die eigentliche Abhilfe — und die ist ungetestet.

---

## 6. Wirtschaftlichkeit

| Modell | Limit | F1 | Output-Tokens / 20 Records | Tokens pro richtiger Zelle | Rechenzeit / 20 Records | Ausfallquote |
|---|---:|---:|---:|---:|---:|---:|
| GLM-5.3 | 4.000 | 0,8120 | 35.691 | 661 | 2 s (Cache) | 10 % |
| GLM-5.3 | 8.000 | **0,8369** | 39.047 | 662 | 218 s | 5 % |
| Qwen3.5-397B | 4.000 | 0,6316 | 65.201 | 1.811 | 46 min | 50 % |
| Qwen3.5-397B | 8.000 | 0,8169 | 91.720 | 1.581 | 24 min | 0 % |
| Qwen3-30B | 4.000 | 0,6179 | 2.249 (Cache-unsicher) | 59 | 35 s | 0 % |

Echte Preise liegen für die genutzten Endpunkte nicht vor; Kosten werden deshalb nur in
Tokens ausgewiesen. Bei gleichem Limit (8.000) ist Qwen3.5-397B **2,3-mal so teuer und
6,6-mal so langsam** wie GLM bei 0,020 F1-Punkten Rückstand. Bei 4.000 Tokens war der
Eindruck „unbrauchbar" ein Artefakt des Limits. Qwen3-30B ist um Größenordnungen
billiger, verliert aber 0,19 F1-Punkte gegenüber GLM und liefert öfter falsche Werte
statt Auslassungen.

---

## 7. Priorisierte Roadmap

| Priorität | Maßnahme | Nutzen | Aufwand | Abhängigkeit | Evidenz |
|---|---|---|---|---|---|
| ~~P0~~ | 8.000-Token-Vergleich GLM und Qwen3.5-397B | **erledigt**: GLM 0,8369 vor Qwen 0,8169 | 130 k Tokens, 30 min | keine | Abschnitt 2.3 |
| **P0** | Echte Zweistufigkeit für kontinuierliche Felder (Stufe 1 = Zeile/Arm als eigener Aufruf, Stufe 2 = Werte) | adressiert 13 der 29 falschen Zellen | 2 Tage | `stage_extraction.py` auf Mean/SD/N erweitern | einstufiger Zusatz gescheitert (Experiment C), Fehlerbild Arm/Population |
| **P1** | Ausgabeschema mit Originaleinheit und Originalwert (keine Umrechnung) | adressiert 4 der 29 falschen Zellen, verhindert stille ×100-Fehler | 1 Tag | Parser + Evaluation | yun2024:246 belegt |
| **P1** | Validator als Warnschicht ausliefern | fängt leere Antworten und unmögliche Ereigniszahlen | erledigt, nur einbinden | keine | 14 Warnungen, 11 davon leere Antworten |
| **P1** | Gold-Audit der konfliktären Records (524, 447, 669) | verhindert, dass Modellfehler Goldfehler sind | 2–3 h manuell | keine | Abschnitt 3, zwei belegte Konflikte |
| **P2** | Evidenzverknüpfung (Fundstelle je Zelle) | ermöglicht Prüfung ohne Gold | 2 Tage | P0-Architektur | ungetestet, nur Hypothese |
| **P2** | Prompt-Vollständigkeitsregel (Experiment A) | Recall | 1 Tag | Cache-Buster-Disziplin | ungetestet |

---

## 8. Entscheidungsvorlage

**1. Soll GLM-5.3 weiterhin das primäre Extraktionsmodell sein?**
Ja. Bestes F1, bester Recall, robusteste technische Bilanz (2 Ausfälle gegenüber 10 bei
Qwen3.5-397B). Die Precision von 0,98–1,00 in beiden Stichproben spricht dafür, dass die
Fehler überwiegend Auslassungen sind — und Auslassungen sind mit Architekturarbeit
adressierbar.

**2. Ist Qwen3.5-397B qualitativ besser?**
Bei 8.000 Tokens ist es **fast gleichwertig**: F1 0,8169 gegen 0,8369 für GLM, dabei
ein Record mehr exakt (13 gegen 12) und null technische Ausfälle. Bei 4.000 Tokens war
es halbiert — das war eine Limitfolge, keine Modellschwäche (frühere Aussage hier
korrigiert). Wirtschaftlich lohnt es sich trotzdem nicht: 2,3-fache Tokenmenge,
6,6-fache Laufzeit für 0,020 F1 Rückstand.

**3. Ist Qwen3-30B eine wirtschaftlich sinnvolle Alternative?**
Als Extraktor nein, auch nicht mit 8.000 Tokens: F1 0,5950 gegen 0,8369 bei GLM, also
0,24 Punkte Rückstand, davon 0,29 Recall. Die Fehler sind zudem falsche Werte statt
Auslassungen (7 falsch, 14 Zellen ohne Goldbezug) — die teurere Fehlerart, weil sie
stillschweigend in die Meta-Analyse gehen. Als Vorfilter bleibt es interessant
(59 Tokens pro richtiger Zelle), aber das ist unbelegt.

**4. Sollten wir die Extraktion in kleinere Teilaufgaben zerlegen?**
Ja, aber gezielt: nicht nach Feldern, sondern nach **Quellenauswahl**. Die Fehleranalyse
zeigt, dass das Modell Zahlen korrekt abschreibt und an der falschen Stelle sucht. Eine
vorgeschaltete Stufe „welche Tabelle, welche Zeile, welcher Arm" würde 13 von 29 Fehlern
adressieren. Eine Aufteilung in sechs Einzelaufrufe pro Record würde dagegen die
Tokenkosten versechsfachen, ohne den Kernfehler zu treffen.

**5. Welche drei Änderungen versprechen den größten Qualitätsgewinn?**
(a) 8.000-Token-Betrieb (beseitigt 17 Length-Ausfälle und 6 Totalausfälle pro 60
Records), (b) vorgeschaltete Tabellenzeilen-/Armbestimmung, (c) Ausgabeschema mit
Originaleinheit ohne Umrechnung. (a) ist gemessen (+0,025 F1). (b) ist als einstufiger Prompt-Zusatz **gescheitert**
(−0,028 F1, Experiment C) und braucht einen eigenen Aufruf. (c) ist aus der
Fehleranalyse begründet, aber nicht experimentell belegt.

**6. Welche Fehler können wir bereits jetzt automatisch verhindern?**
Leere Antworten, Events > Gruppengröße, doppelte Zellen, SD ≤ 0, extrem ungleiche Arme,
Ereigniszahlen bei kontinuierlichem Outcome. Das sind 14 Warnungen auf 60 Records, davon
11 leere Antworten — die Quote echter Fehler unter den Warnungen liegt bei 2 von 3.

**7. Welche Probleme brauchen weiterhin ein stärkeres Modell oder Menschen?**
Arm-/Populationszuordnung bei mehrarmigen Studien, Zeitpunktwahl bei mehreren
Follow-ups, Einheiten ohne explizite Angabe. Das erfordert entweder eine Architektur mit
Quellenzwang oder menschliche Prüfung; ein Plausibilitätsvalidator kann es nicht leisten.

**8. Was ist der sinnvollste nächste Benchmark?**
Ein Lauf auf dem bereinigten 20-Record-Satz (ohne 524, 447, 669) mit 8.000 Tokens für
LLM und eine echte Zweistufigkeit. Der Modellvergleich ist entschieden — Qwen3-30B holt
auch bei 8.000 Tokens nicht auf —, offen ist nur die Architekturfrage.

**9. Was ist belastbar, was explorativ?**
Belastbar: der Metrikfehler und seine Korrektur (0,8324 / 0,7042), die Fehlerklassen mit
Artikelbelegen, die Cache-Falle, die technische Ausfallquote der Modelle bei 4.000
Tokens. Belastbar zusätzlich: der 8.000er-Vergleich GLM gegen Qwen3.5-397B (frisch generiert,
keine Cache-Treffer). Explorativ: die 20-Record-Stichprobe als Ganzes (klein, breite
Konfidenzintervalle), Experiment B (kein Effekt nachweisbar) und Experiment C
(gescheitert, Ursache aber belegt).

---

## 9. Warum der vollständige Testsplit nicht lief

Der Lauf über die restlichen 596 Records mit 8.000 Tokens wurde **nicht** gestartet.
Begründung nach den im Auftrag genannten Bedingungen:

1. **Metriken geprüft:** erfüllt (Abschnitt 1).
2. **Technik geklärt:** nicht erfüllt. Bei 8.000 Tokens wurden 4–6 Minuten pro Record
   gemessen; 596 Records wären 40–60 Stunden. Bei 4.000 Tokens dauert der Lauf ca.
   2,5 Stunden, produziert aber 28 % Length-Ausfälle — die Ergebnisse wären mit dem
   bekannten Limitfehler belastet.
3. **Ressourcen für die übrigen Experimente:** nicht erfüllt; der 4.000er-Lauf hätte das
   Budget für Fehleranalyse und Bericht aufgebraucht.

Voraussetzung für den vollständigen Lauf: entweder ein schnellerer Endpunkt oder eine
Record-Aufteilung mit Wiederaufnahme (die der Harness bereits unterstützt:
`predictions.jsonl` wird inkrementell fortgesetzt).

---

## 10. Offene Fragen

1. Bringt die echte Zweistufigkeit (eigener Aufruf für Zeile/Arm) den erwarteten Gewinn?
Der einstufige Versuch zeigt nur, dass ein Schema-Zusatz nicht funktioniert.
2. Ist der Gateway-Cache modellübergreifend? 14 von 20 Qwen3-30B-Antworten waren
   Cache-Treffer, obwohl das Modell zuvor nie lief. Wenn ja, sind Token- und
   Laufzeitangaben für Cache-Treffer wertlos.
3. Wie viele der 29 falschen Zellen sind Goldfehler? Zwei sind belegt, weitere
   Kandidaten (669, 110) nicht abschließend geklärt.
4. Bringt die zweistufige Architektur tatsächlich den erwarteten Gewinn? Plausibel
   begründet, nicht gemessen; der einstufige Ersatz ist gemessen und gescheitert.
5. Wie verhält sich das System auf den 596 nicht getesteten Records? Die 60er-Stichprobe
   ist geschichtet, aber klein.

---

## 11. Artefakte dieses Tages

| Datei | Inhalt |
|---|---|
| `yun_full/vergleich_20261116.json` / `.py` | zentrale Vergleichsdatei, einheitliche Kennzahlen |
| `yun_full/validator.py` | Plausibilitätsprüfungen mit Messmodus gegen Gold |
| `yun_full/stichprobe20.json` | 20-Record-Teilmenge (jeder dritte Record der 60er) |
| `tests/test_yun_metriken.py` | 6 Tests für die Metrik-Grenzfälle |
| `runs/yun20_4000_{glm,qwen,qwen30}_20261116/` | Modellvergleich inkl. `auswertung_yun.json`, `yun_metriken.json` |
| `runs/yun20_4000_glm_gskcb_20261116/` | Experiment B (Gruppengrößenregel, frisch generiert) |
| `runs/yun20_8000_glm_20261116/` | abgebrochener erster 8.000er-Lauf (6 Records, Laufzeitbeleg) |
| `runs/yun20_8000_glm_cb_20261116/` | GLM bei 8.000 Tokens, frisch generiert |
| `runs/yun20_8000_qwen_cb_20261116/` | Qwen3.5-397B bei 8.000 Tokens, frisch generiert |
| `runs/yun20_8000_qwen30_cb_20261116/` | Qwen3-30B bei 8.000 Tokens, frisch generiert |
| `runs/yun20_8000_glm_v8_20261116/` | Experiment C: Quellenzeile im Prompt (v8) |
| `runs/yun_v8_probe_20261116/` | Kontrollstichprobe mit Rohantworten (belegt, dass `source` fehlt) |
| `yun_full/ausschluss_konflikte.py` / `.json` | Kennzahlen mit und ohne die drei konfliktären Records |
| `runs/yun699_test60_20261116/validator.json` | Validatormessung auf der 60er-Stichprobe |
