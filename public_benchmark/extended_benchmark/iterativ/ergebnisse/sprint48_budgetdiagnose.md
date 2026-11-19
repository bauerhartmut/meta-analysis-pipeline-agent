# Sprint 48: Diagnose der P5-Budgetabbrueche

Grundgesamtheit: **33** `length_ohne_ergebnis`-Zeilen und **67** verwertbare Zeilen aus `yun699_p5_24000_20261118`; 3 weitere Zeilen ohne Zellen bleiben im Vergleich aussen vor. Rein lesende Auswertung: keine Netzaufrufe, keine geaenderten Predictions, kein Gold, keine eingefrorene Eingabe beruehrt.

**Befund in einem Satz:** Die Budgetabbrueche sind nicht ueberwiegend durch Tabellenkomplexitaet oder Zellenzahl erklaerbar. Die Ausfaelle haben im Median weniger Tabellen und weniger Datenzellen als die Erfolge; der scharfe Kontrast ist der Reasoning-Umfang (Median 95.071 gegen 31.444 Zeichen). Am haeufigsten greift H1 (Komplexitaet): 51,5 % der Ausfaelle gegen 35,8 % der Erfolge; am spezifischsten H3 (mehrstufige Koepfe): 27,3 % gegen 13,4 %.

## 1. Uebersicht der 33 Budgetfaelle

| Record | Dokument | Tab. | Zeilen max | Spalten max | Datenzellen | Kopfebenen | Komplexitaet | Prompt-Zeichen | Reasoning-Zeichen | Gold | Diagnosen | Hypothesen |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|
| `yun2024:30` | PMC3003523 | 3 | 5 | 12 | 56 | 2 | komplex | 26.854 | 89.370 | 6 | TPSD- | H1, H4, H6 |
| `yun2024:52` | PMC3195393 | 6 | 12 | 11 | 153 | 2 | sehr_komplex | 25.950 | 95.546 | 6 | ----- | H1, H2, H4 |
| `yun2024:119` | PMC4323894 | 0 | 0 | 0 | 0 | 0 | unbekannt | 11.045 | 98.142 | 4 | ----- | H4, H7 |
| `yun2024:128` | PMC4493951 | 2 | 7 | 4 | 37 | 2 | mittel | 8.970 | 90.927 | 4 | ----- | H4, H7 |
| `yun2024:152` | PMC5055753 | 1 | 8 | 3 | 20 | 1 | einfach | 8.788 | 99.665 | 4 | ----- | H4, H7 |
| `yun2024:159` | PMC5056957 | 2 | 22 | 13 | 184 | 1 | mittel | 17.100 | 88.346 | 6 | ----- | H2, H4 |
| `yun2024:164` | PMC5062234 | 0 | 0 | 0 | 0 | 0 | unbekannt | 4.897 | 99.794 | 2 | ----- | H4, H7 |
| `yun2024:171` | PMC5079604 | 2 | 4 | 4 | 19 | 1 | mittel | 21.446 | 97.231 | 4 | ----- | H6 |
| `yun2024:173` | PMC5079604 | 2 | 4 | 4 | 19 | 1 | mittel | 21.416 | 93.443 | 4 | ----- | H6 |
| `yun2024:204` | PMC5380326 | 3 | 17 | 6 | 169 | 2 | sehr_komplex | 15.580 | 89.548 | 2 | ----- | H1, H2, H6 |
| `yun2024:251` | PMC5614421 | 3 | 13 | 6 | 100 | 1 | komplex | 41.153 | 97.921 | 4 | ----- | H1, H4, H6 |
| `yun2024:252` | PMC5614421 | 3 | 13 | 6 | 100 | 1 | komplex | 41.138 | 99.829 | 2 | TP-D- | H1, H4, H6 |
| `yun2024:273` | PMC3214395 | 0 | 0 | 0 | 0 | 0 | unbekannt | 4.436 | 101.270 | 2 | ----- | H4, H7 |
| `yun2024:304` | PMC4357072 | 0 | 0 | 0 | 0 | 0 | unbekannt | 6.540 | 95.635 | 4 | ----- | H4, H7 |
| `yun2024:356` | PMC5884950 | 2 | 15 | 3 | 48 | 1 | mittel | 20.650 | 96.159 | 2 | ----- | H4, H7 |
| `yun2024:420` | PMC3877023 | 4 | 5 | 6 | 49 | 4 | sehr_komplex | 27.322 | 86.878 | 6 | ----- | H1, H3, H4, H6 |
| `yun2024:421` | PMC3877023 | 4 | 5 | 6 | 49 | 4 | sehr_komplex | 27.320 | 84.549 | 6 | TPSD- | H1, H3, H4, H6 |
| `yun2024:446` | PMC4879328 | 3 | 4 | 5 | 15 | 3 | sehr_komplex | 26.270 | 95.071 | 6 | ----- | H1, H3, H4 |
| `yun2024:451` | PMC4879328 | 3 | 4 | 5 | 15 | 3 | sehr_komplex | 26.319 | 95.333 | 6 | ----- | H1, H3, H4 |
| `yun2024:523` | PMC5325897 | 2 | 16 | 3 | 51 | 1 | mittel | 7.811 | 89.661 | 6 | ----- | H4, H7 |
| `yun2024:525` | PMC5325897 | 2 | 16 | 3 | 51 | 1 | mittel | 7.811 | 89.708 | 6 | ----- | H4, H7 |
| `yun2024:557` | PMC3136370 | 1 | 6 | 7 | 42 | 1 | mittel | 14.124 | 93.380 | 6 | ----- | H4, H7 |
| `yun2024:559` | PMC3136370 | 1 | 6 | 7 | 42 | 1 | mittel | 14.139 | 89.528 | 6 | ----- | H4, H7 |
| `yun2024:582` | PMC3504298 | 1 | 11 | 5 | 55 | 2 | komplex | 13.869 | 99.406 | 2 | ----- | H1, H4 |
| `yun2024:624` | PMC3493722 | 0 | 0 | 0 | 0 | 0 | unbekannt | 6.268 | 87.507 | 2 | ----- | H4, H7 |
| `yun2024:625` | PMC3493722 | 0 | 0 | 0 | 0 | 0 | unbekannt | 6.268 | 82.625 | 2 | ----- | H4, H7 |
| `yun2024:671` | PMC4550271 | 5 | 36 | 9 | 467 | 3 | sehr_komplex | 43.571 | 100.255 | 2 | ----- | H1, H2, H3, H4 |
| `yun2024:672` | PMC4550271 | 5 | 36 | 9 | 467 | 3 | sehr_komplex | 43.591 | 100.367 | 2 | TP-D- | H1, H2, H3, H4 |
| `yun2024:674` | PMC4550271 | 5 | 36 | 9 | 467 | 3 | sehr_komplex | 43.605 | 93.674 | 6 | ----- | H1, H2, H3, H4 |
| `yun2024:673` | PMC4550271 | 5 | 36 | 9 | 467 | 3 | sehr_komplex | 43.585 | 93.498 | 6 | ----- | H1, H2, H3, H4 |
| `yun2024:685` | PMC2836833 | 7 | 6 | 7 | 117 | 2 | komplex | 19.903 | 88.956 | 2 | ----- | H1, H4 |
| `yun2024:678` | PMC5777419 | 3 | 7 | 15 | 115 | 3 | sehr_komplex | 13.328 | 97.070 | 2 | TP-D- | H1, H3, H6 |
| `yun2024:687` | PMC2836833 | 7 | 6 | 7 | 117 | 2 | komplex | 19.900 | 95.376 | 2 | ----- | H1, H4 |

Spalten: `Tab.` zaehlt **alle** Tabellen des Dokuments, `Zeilen max` und `Spalten max` sind das Maximum je Tabelle, `Datenzellen` die Summe nicht-leerer Datenzellen (ohne Labelspalten), `Kopfebenen` die hoechste Zahl von Header-Baendern. Diagnosen: T = eingefrorene Testauswahl, P = Strukturplan A-E, S = Kopfband-Diagnose (Sprint 43), D = Gruppenkopf-/Fliesstext-Diagnose, M = Modelllauf A/B/E, `-` = kein Artefakt. Zur **Publikation** traegt der Record nur Dokument-ID und Dokumentpfad; Titel, Journal und DOI stehen nicht in den Daten und sind im JSON als nicht verfuegbar gekennzeichnet.

Alle 33 Zeilen: `completion_tokens = 24000` (genau das Budget), `content_chars = 0`, `finish_reason = length`, `http_status = 200`, Version `v2_timepoint`. Jede `record_id` kommt genau einmal vor.

## 2. Haeufigkeit der strukturellen Merkmale

| Merkmal | Ausfaelle Median | Erfolge Median | Ausfaelle Q75 | Erfolge Q75 |
|---|---:|---:|---:|---:|
| `tabellen` | 2 | 3 | 4 | 4 |
| `tabellen_mit_zielfeld` | 0 | 0 | 1 | 0 |
| `zeilen_max` | 6 | 8 | 15 | 18 |
| `datenzellen_summe` | 49 | 60 | 117 | 153 |
| `datenzellen_zielfeld` | 0 | 0 | 4 | 0 |
| `datenspalten_max` | 6 | 4 | 7 | 6 |
| `kopfebenen_max` | 1 | 1 | 3 | 2 |
| `gruppenkopf_zellen` | 0 | 0 | 4 | 0 |
| `komplexe_tabellen` | 1 | 0 | 2 | 1 |
| `komplexitaet_score_max` | 0,5 | 0,4 | 0,8 | 0,6 |
| `prompt_zeichen` | 19.900 | 17.103 | 26.854 | 21.966 |
| `text_zeichen` | 18.929 | 16.081 | 25.866 | 20.888 |
| `fussnoten_summe` | 0 | 0 | 3 | 4 |
| `unregelmaessige_zeilen` | 1 | 0 | 5 | 2 |

Schwellen aus allen 103 Zeilen (Q75): `datenzellen_summe` 121, `datenzellen_zielfeld` 0, `prompt_zeichen` 22.671, `komplexitaet_score_max` 0,6. Die Schwellen stammen aus beiden Gruppen zusammen, damit kein Merkmal allein durch die Auswahl auffaellt.

## 3. Gruppierung nach Fehlerhypothesen

| Hypothese | Ausfaelle | Anteil | Erfolge | Anteil | Differenz |
|---|---:|---:|---:|---:|---:|
| H1 Zu hohe Tabellenkomplexitaet | 17 / 33 | 51,5 % | 24 / 67 | 35,8 % | 15,7 Pp |
| H2 Zu viele Tabellenzellen | 7 / 33 | 21,2 % | 19 / 67 | 28,4 % | -7,2 Pp |
| H3 Mehrstufige Ueberschriften | 9 / 33 | 27,3 % | 9 / 67 | 13,4 % | 13,9 Pp |
| H4 Ungeeignete Promptstruktur | 29 / 33 | 87,9 % | 55 / 67 | 82,1 % | 5,8 Pp |
| H5 Zu aufwendige Reasoning-Schritte | 33 / 33 | 100 % | 0 / 67 | 0 % | 100 Pp |
| H6 Zu umfangreiche Ausgabe | 9 / 33 | 27,3 % | 16 / 67 | 23,9 % | 3,4 Pp |
| H7 Sonstige bzw. nicht eindeutig klassifizierbar | 13 / 33 | 39,4 % | 30 / 67 | 44,8 % | -5,4 Pp |

H5 ist ein **Mechanismus, keine Ursache**: jede Ausfallzeile hat das Budget im Reasoning verbraucht, weil kein Inhalt ausgegeben wurde. H5 unterscheidet daher nichts und steht nur als Befund in der Tabelle. H7 markiert Faelle, bei denen **keine strukturelle** Hypothese (H1, H2, H3, H6) greift; H4 bleibt dabei aussen vor, weil "keine Tabelle mit Zielfeld" in beiden Gruppen fast ueberall zutrifft.

Beobachtung und Vermutung sind getrennt: die Anteile sind Beobachtung; dass ein Merkmal die Ursache ist, waere eine Vermutung. Aussagekraft hat nur ein Merkmal, das bei den Ausfaellen deutlich haeufiger auftritt als bei den Erfolgen.

## 4. Vergleich mit den 67 erfolgreichen Records

| Kennzahl | Ausfaelle | Erfolge |
|---|---:|---:|
| reasoning_zeichen: Median | 95.071 | 31.444 |
| reasoning_zeichen: Spanne | 82.625-101.270 | 3.147-88.771 |
| completion_tokens: Median | 24.000 | 8.388 |
| completion_tokens: Spanne | 24.000-24.000 | 787-22.823 |
| dauer_s: Median | 191,5 | 76,2 |
| dauer_s: Spanne | 0,1-300 | 0,1-298,4 |

Struktureller Kontrast: 6 der 33 Ausfaelle haben im Dokument **keine parsebare Tabelle**, 24 haben keine Tabelle, der der Parser ein Zielfeld zuordnen kann. Bei den Erfolgen betraegt der Median der Datenzellen 60, bei den Ausfaellen 49; die Ausfaelle sind strukturell also **nicht** die groesseren Tabellen. Auch die Zahl der Tabellen ist bei ihnen kleiner (2 gegen 3 im Median).

Fruehere Laeufe derselben Records bei 8.000 Tokens (vorhandene Predictions, Modell glm): 73 x `length_ohne_ergebnis`, 7 x `ok` Beobachtungen. Auf Record-Ebene: 33 der 33 haben mindestens eine 8000er-Zeile, davon 3 mit mindestens einem Erfolg. Die Mehrheit war also schon bei 8.000 ein Budgetabbruch; mehr Budget allein hat die Klasse nicht gedreht.

Die Dauerangabe ist nur eingeschraenkt brauchbar: mindestens eine Zeile nennt 0,14 s bei 89.370 Reasoning-Zeichen. Sie wird deshalb nicht als Merkmal verwendet.

## 5. Bereits getestete Zerlegungsverfahren

Die Zerlegung liegt als `table_decomposition`-Engine mit fuenf Strategien vor (A Full-Table, B Vertical, C Horizontal, D Bidirectional, E Adaptive Recursive); zeilen- und spaltenweise Zerlegung sind Einheiten innerhalb von B und C. Fuer die 33 Faelle ist die Abdeckung:

| Verfahren | Records der 33 mit vorhandenem Artefakt |
|---|---:|
| A (Strukturplan, offline) | 5 |
| B (Strukturplan, offline) | 5 |
| C (Strukturplan, offline) | 5 |
| D (Strukturplan, offline) | 5 |
| E (Strukturplan, offline) | 5 |
| Modelllauf A/B/E (echte Zellen) | 0 |
| Kopfband-Diagnose (Sprint 43) | 2 |
| Gruppenkopf-/Fliesstext-Diagnose | 5 |
| in eingefrorener Testauswahl | 5 |
| in eingefrorener dev-Auswahl | 0 |

Damit ist die Zerlegung fuer **keinen** der 33 Faelle mit einem Modell gemessen: die fuenf Strategien liegen nur als Strukturplan fuer 5 Records vor, und der Modelllauf A/B/E enthaelt keine Zeile dieser Auswahl. Zeilen- und spaltenweise Zerlegung wurden also nur als Plan, nicht als Extraktion geprueft.

## 6. Fuenf interessanteste Testfaelle

- `yun2024:273` (PMC3214395): Dokument ohne parsebare Tabelle, trotzdem 101.270 Reasoning-Zeichen: prueft, ob der Volltext-Prompt ohne Tabellenanker das Reasoning treibt.
- `yun2024:671` (PMC4550271): groesste Datenzellenzahl der Ausfaelle (467): Testfall fuer H2/H6.
- `yun2024:30` (PMC3003523): liegt in der eingefrorenen Auswahl und hat einen Strukturplan fuer A-E (5 Strategien): einziger Falltyp, bei dem eine Zerlegung ohne neue Auswahl direkt gegen den Budgetabbruch geprueft werden kann.
- `yun2024:171` (PMC5079604): teilt das Dokument PMC5079604 mit 1 weiteren Ausfall (yun2024:173): trennt Dokumenteffekt von Recordeffekt.
- `yun2024:119` (PMC4323894): bei 19.000 Tokens erfolgreich, bei 24.000 `length`: Dosis-Wirkung ohne Strukturaenderung, starkes Indiz gegen reine Budgetknappheit.

## 7. Empfehlungen fuer den naechsten Experimentierschritt

1. **Zerlegung vor Budget.** Fuer die 5 Faelle mit vorhandenem Strukturplan die vertikale (B) Zerlegung real extrahieren, danach die adaptive (E); beide sind bisher nur als Plan geprueft, nie als Modelllauf. Erwartung: kleinerer Ausschnitt je Aufruf, weniger Reasoning. Kosten: je Fall zwei Aufrufe, im schlimmsten Fall 2 x 24.000 Tokens.
2. **Tabellenausschnitt statt Volltext.** Der P5-Prompt sendet den ganzen Artikelauszug (bis 45.000 Zeichen) ohne Zielzeitpunkt-Bindung; der Median liegt bei 19.900 Zeichen. Ein Prompt mit genau der Tabelle und ihrem Kopf ist der naechste zu testende Unterschied, nicht ein hoeheres Budget.
3. **Prosa-Faelle trennen.** Records ohne Tabelle brauchen einen eigenen Pfad (Ergebnisse im Fliesstext), sonst sucht das Modell eine Tabelle, die es nicht gibt.
4. **Kein Budgetaufschlag ohne Aenderung.** 24.000 loest die Faelle nicht, die bei 8.000 schon `length` waren; die Dosis-Wirkung aus `budget_hypothese_20261118.md` zeigt Rettungen nur bei geaenderter Aufgabe, nicht bei mehr Budget allein.

## 8. Fazit

Auf die Ausgangsfrage, ob die Abbrueche ueberwiegend durch Tabellenkomplexitaet, Promptstruktur, Reasoning-Aufwand oder Ausgabeumfang erklaerbar sind:

- **Tabellenkomplexitaet und Zellenzahl: nein.** H1 trennt mit 15,7 Pp, H2 mit -7,2 Pp; die Ausfaelle haben im Median sogar weniger Datenzellen und weniger Tabellen als die Erfolge.
- **Mehrstufige Ueberschriften: teilweise.** H3 trifft 9 von 33 Ausfaellen gegenueber 9 von 67 Erfolgen (13,9 Pp). Das ist der spezifischste Strukturtrenner (selten bei Erfolgen), erklaert aber nur gut ein Viertel der Faelle.
- **Promptstruktur: nur schwach trennend.** H4 trifft 29 der 33 Ausfaelle und 55 der 67 Erfolge. Der Grund: der Volltext-Prompt mit hoechstens 45.000 Zeichen gilt fuer alle Records, und bei den meisten liegt keine Tabelle mit zugeordnetem Zielfeld vor - das trifft Erfolge wie Ausfaelle.
- **Ausgabeumfang: nein.** H6 trennt mit 3,4 Pp.
- **Reasoning-Aufwand: als Mechanismus bestaetigt, als Ursache offen.** Alle Ausfaelle enden mit 24.000 Tokens und 0 Zeichen Inhalt; der Reasoning-Umfang ist rund dreimal so hoch wie bei den Erfolgen. Warum er so hoch ist, zeigt die Struktur nicht.
- **13 der 33 Ausfaelle haben keine strukturelle Hypothese**: bei ihnen bleibt nur der Prompt-/Reasoning-Pfad als Erklaerung.

Gesichert ist damit nur der Mechanismus (Budget im Reasoning, kein Inhalt) und die Tatsache, dass die Ausfaelle strukturell nicht schwieriger sind als die Erfolge. Nicht gesichert ist eine einzelne Ursache; die Daten stuetzen am ehesten die Kombination aus Volltext-Prompt und aufwendiger Reasoning-Kette.

## 9. Grenzen

- Reasoning-Tokens stehen nicht in den Predictions; angegeben sind Zeichen. Die Umrechnung Zeichen/Token ist eine Schaetzung (Median 4,0 aus 390 abgeschnittenen Zeilen, `budget_hypothese_20261118.md`).
- Strukturmerkmale kommen aus dem vorhandenen Parser und der vorhandenen Komplexitaetsbewertung. Wo der Parser keine Tabelle erkennt, steht 0 - das ist ein Parserbefund, keine Aussage ueber das PDF.
- Zusammenhange sind beobachtet, nicht kausal belegt. Der Bericht nennt keine Ursache als gesichert.
