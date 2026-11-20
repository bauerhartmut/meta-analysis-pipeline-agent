# Empfehlungen aus dem GLM-5.3/P5-Vergleich (20.11.2026)

Grundlage sind die drei Berichte im selben Verzeichnis:
`glm53_p5_vergleich_20261120.md`, `glm53_p5_recordanalyse_20261120.md`,
`p5_budgetdiagnose_20261120.md`. Alle Zahlen dort sind aus vorhandenen
Predictions nachgerechnet; die Wirkungserwartungen hier sind **Szenarien** und
als solche markiert.

## Vorab: eine Voraussetzung, keine Maßnahme

Bevor eine technische Maßnahme greift, muss der Bewertungsstandard stimmen.
Der Wert „F1 etwa 0,80" ist auf den 559 Erfolgszeilen gemessen, nicht auf dem
Datensatz. Auf allen 699 Zeilen sind es 0,7336 (Logik dieser Analyse) bzw.
0,7519 (Yun-Logik). Solange beide Zahlen als „GLM-Qualität" zitiert werden,
wird jede Verbesserung an der falschen Größe gemessen.

**Empfehlung:** Ab jetzt zwei Kennzahlen berichten — (a) Gesamtdatensatz mit
allen Ausfällen im Nenner, (b) Hybrid aus Referenz plus Nachzug. Die
Erfolgszeilen-Zahl bleibt als Diagnose, nicht als Headline.

## Die fünf Maßnahmen

| # | Maßnahme | Zielgröße | Aufwand | Risiko | Tokens | Isoliert prüfbar |
|---|---|---|---|---|---|---|
| 1 | Tabellenanker statt Volltext | Recall | mittel | mittel | neutral bis niedriger | ja, trocken + 1 Aufruf |
| 2 | Antwortgerüst vor dem Reasoning | Recall, Verfügbarkeit | klein | niedrig | neutral | ja |
| 3 | Dubletten- und Fremdschlüsselfilter | Precision | klein | niedrig | **0** | ja, sofort |
| 4 | Zwei-Schritt: Zeile/Zeitpunkt, dann Zellen | Precision, Recall | hoch | mittel | höher | ja, 8–10 Records |
| 5 | Zerlegung B/E für die 5 Fälle mit Strukturplan | Recall | hoch | mittel | 2 Aufrufe je Fall | ja, 5 Records |

### 1. Tabellenanker statt Volltext

> **Nachtrag 20.11.2026: gebaut, an zwei Records gemessen, dort ohne Gewinn (n = 2).** Zwei Fassungen des
> Ankers, je ein Aufruf auf `yun2024:559` und `yun2024:615`, 24.000 Tokens,
> Abbruch bei `content_chars == 0` oder `finish_reason = length`. Fassung 1
> (884 Zeichen) beantwortet 559 mit 16.632 Tokens, nennt aber eine
> Separationsanalyse-Tabelle und liefert −1,92/−5,12 statt −4,0/−8,0: 0 TP,
> 2 FP. Fassung 2 (1.393 Zeichen, Quelle muss Zielzeitpunkt und Feld tragen,
> `chosen_timepoint`/`discarded_timepoints` bleiben) laesst **beide** Records
> ins Budget laufen (559: 98.896, 615: 96.344 Reasoning-Zeichen, je 0 Zeichen
> Inhalt). Kosten der Ankerspur 88.632 Completion-Tokens, Gewinn 0 TP. Details:
> `anker_lauf_20261120/ergebnis_20261120.md` und `ergebnis_anker2_20261120.md`.
> Die Erwartung unten (+29 TP) ist damit fuer diese zwei Records nicht eingetreten;
> fuer die uebrigen 11 der 13 Faelle ist sie offen und ungemessen. Die Zahl bleibt
> als damalige Schaetzung stehen.

**Was:** Wo der Parser eine Tabelle mit Zielfeld findet, nur diese Tabelle samt
Kopfzeilen und Fußnoten senden. Wo er keine findet, einen eigenen
Fließtext-Pfad verwenden statt den Volltext mit der Bitte, eine Tabelle zu
finden.

**Warum:** Die 13 Fälle ohne Strukturhypothese haben den kleinsten Prompt und
die höchste Reasoning-Dichte (13,2 Zeichen Reasoning je Zeichen Text). 13 von
13 haben keine Tabelle mit Zielfeld, 6 gar keinen Tabellentext. Das Modell
sucht, was nicht da ist.

**Erwartete Wirkung (Szenario, keine Messung):** Die 13 Records tragen 50
Goldzellen. Würden sie mit der Trefferquote der bereits beantworteten Records
(170 von 291 = 58,4 %) beantwortet, wären das rund **+29 TP und +6,9 Punkte
Recall** auf der P5-Auswahl (0,402 → 0,470). Die Precision bliebe näherungsweise
gleich, weil die neuen Zellen dasselbe Dublettenmuster tragen.

**Aufwand:** Prompt-Bau und Auswahl der Tabelle; kein Modellaufruf zum Testen.
**Risiko:** Fälle, in denen die Zahlen nur im Fließtext stehen, verlieren ihren
Kontext — deshalb der zweite Pfad. **Tokens:** eher weniger, weil der Prompt
kleiner wird. **Isoliert:** Strukturplan und Prompt können ohne Netz geprüft
werden; ein einzelner Aufruf (`yun2024:30`) zeigt, ob das Reasoning fällt.

### 2. Antwortgerüst vor dem Reasoning

**Was:** Das Modell gibt zuerst das JSON-Gerüst mit den erwarteten
Feld-/Arm-Schlüsseln aus und füllt es anschließend. Alternativ eine kurze
Antwortpflicht vor der Begründung.

**Warum:** Alle 33 Abbrüche enden mit 24.000 Tokens Reasoning und **null**
Zeichen Inhalt. Ein Gerüst macht den Abbruch wenigstens teilweise verwertbar
und zwingt zur Struktur, bevor die Suche beginnt.

**Erwartete Wirkung:** Deckt sich mit Maßnahme 1 bei den 13 Fällen und wirkt
zusätzlich bei den 20 strukturellen Abbrüchen. **Nicht additiv zu 1 zählen.**
Für sich genommen ist der Gewinn offen; er hängt daran, ob das Modell das
Gerüst wirklich vor dem Reasoning ausgibt.

**Aufwand:** klein (Prompt-Ergänzung, Parser für das Gerüst).
**Risiko:** niedrig — im schlechtesten Fall ändert sich nichts.
**Tokens:** neutral, das Budget bleibt. **Isoliert:** ja, ein Aufruf auf einem
der 33 Records.

### 3. Dubletten- und Fremdschlüsselfilter

**Was:** Je Record und (Feld, Arm) höchstens eine Zelle ausgeben; Zellen mit
Schlüsseln, die im Gold des Records nicht vorkommen, nur behalten, wenn sie
belegt sind.

**Warum:** Von 97 FP sind 80 Mehrfach- oder Falschwert-Zellen am selben
Schlüssel und 17 Fremdschlüssel.

**Gemessene Wirkung (kein Szenario):** Nur eine Zelle je Schlüssel behalten
hebt auf den 102 Records die Precision von **0,6367 auf 0,6589** und F1 von
**0,4928 auf 0,4993** — bei unverändertem Recall. Mehr ist es nicht, weil die
meisten „überzähligen" Zellen keine wörtlichen Dubletten sind, sondern Werte
zu einem anderen Zeitpunkt oder aus einer anderen Zeile. Der Filter ist
trotzdem gratis.

**Aufwand:** klein, reine Nachbearbeitung. **Risiko:** niedrig; die Auswahl
„erste Zelle gewinnt" ist willkürlich, die Alternative „beste Zelle gewinnt"
liefert dasselbe Ergebnis (gemessen). **Tokens:** 0. **Isoliert:** sofort auf
vorhandenen Predictions.

### 4. Zwei-Schritt-Extraktion: erst Zeile und Zeitpunkt, dann Zellen

**Was:** Aufruf 1 wählt anhand von Tabelle und Kopf die Zeile (Population,
Zeitpunkt, Armzuordnung). Aufruf 2 liest nur die Zellen dieser Zeile.

**Warum:** Auf den beantworteten Records sind 72 der 121 FN falsche Werte oder
Armverwechslungen, und die inspizierten Fälle zeigen dasselbe Muster: P5 findet
Zahlen und ordnet sie der falschen Zeile zu (`yun2024:686`: 34 statt 17;
`yun2024:113`: Arme vertauscht; `yun2024:357`: andere Population). Das ist ein
Bindungsproblem, kein Erkennungsproblem.

**Erwartete Wirkung (Szenario):** Würde die Hälfte der 72 Binde-Fehler zu
Treffern, wären das **+36 TP und +8,5 Punkte Recall** auf der Auswahl.
**Aufwand:** hoch — neuer Aufrufpfad, neue Auswertung.
**Risiko:** mittel — zwei Aufrufe können sich widersprechen; der zweite Aufruf
kann die Zeile des ersten nicht mehr korrigieren.
**Tokens:** höher (zwei Aufrufe je Record), aber je Aufruf kleiner.
**Isoliert:** ja, auf 8–10 Records mit bekannten Bindefehlern.

### 5. Zerlegung B/E für die 5 Fälle mit Strukturplan

**Was:** Die vertikale (B) und die adaptive (E) Zerlegung real extrahieren für
die fünf Records, für die ein Strukturplan vorliegt.

**Warum:** Die Zerlegung ist bisher **nur als Plan** geprüft, nie als
Modelllauf. Sie ist der einzige vorhandene Mechanismus, der den Kontext
kleiner macht, ohne die Aufgabe zu ändern.

**Erwartete Wirkung:** offen — es gibt keine Messung. Das ist der Grund, sie
nicht vor 1 und 2 zu setzen.
**Aufwand:** hoch. **Risiko:** mittel (mehr Aufrufe, kleinere Ausschnitte).
**Tokens:** bis 2 × 24.000 je Fall. **Isoliert:** ja, fünf Records,
`yun2024:30` zuerst.

## Priorisierung (Stand 20.11.2026, nach den Anker-Messungen)

1. **Maßnahme 3 ist erledigt** — Dublettenfilter gemessen: Precision 0,6367 →
   0,6589, F1 0,4928 → 0,4993, Recall unverändert. Mehr gibt der Filter nicht
   her, weil 67 der 97 falschen Zellen einzelne Falschwerte sind.
2. **Maßnahme 1 ist an zwei Records gemessen und dort ohne Gewinn (n = 2)** —
   beide Ankerfassungen ohne Treffer, 88.632 Tokens verbraucht. Die übrigen 11 der
   13 Fälle sind nicht getestet; der Anker ist dort unbelegt, nicht widerlegt.
   Vor einem weiteren Anker-Aufruf hat die Zweistufigkeit Vorrang.
3. **Maßnahme 4 (Zweistufigkeit) ist gebaut, auf vier Records gemessen und auf
   zwei davon vollständig geschlossen.** Mit `glm-5.3` ist die Kette nur auf
   `yun2024:523` vollständig (Stufe 1: 2.342 Tokens, Stufe 2: 268 Tokens,
   4 TP / 0 FP / 2 FN, F1 0,800); auf 420 und 421 bricht dieselbe Stufe 1 in
   jeder geprüften Prompt-Fassung ab (4 von 4 Zellen, je volles Budget,
   0 Zeichen). Mit `qwen3.5-397b` antwortet Stufe 1 auf allen drei gemessenen
   Records: Treffer auf 420 und 119, falsches Negativ auf 421. Auf 420 ist auch
   Stufe 2 gelaufen (2.590 Tokens von 4.000, 4 Zellen): **4 TP / 0 FP / 2 FN,
   F1 0,800**, das erste Schnittstellenpaar korrekt gewählt. Auf 119 antwortet
   Stufe 2 nach einer Budgetkorrektur (8.000) mit einer **leeren Zellenliste**
   und vollem Zitat: der Satz druckt Anteile („70% … attained good GOS") und
   keine Mittelwerte, und das Modell weigert sich, sie als `mean` auszugeben.
   Auf 52, einem der 33 Abbrüche aus einer fremden Publikation, trägt die Kette
   ebenfalls: 2 Zellen, richtig zugeordnet, 0 FP (F1 0,500 bei nur 2 von 6
   erreichbaren Werten). Die Zweistufigkeit trägt damit auf drei Records
   vollständig (523 mit glm; 420 und 52 mit qwen), scheitert auf 421 an der
   `found`-Entscheidung und auf 119 an der Feldbezeichnung des Goldes. Details
   im Nachtrag unten.
4. **Maßnahme 2** — billig, aber sie ändert an der Bindung nichts; erst nach
   Maßnahme 4 sinnvoll, wenn ein Aufruf überhaupt zuverlässig Inhalt liefert.
5. **Maßnahme 5** — zuletzt, weil sie am meisten kostet und am wenigsten belegt
   ist.

## Was nicht empfohlen wird

- **Budget pauschal erhöhen.** 24.000 war das Budget, 33 Fälle haben es
  vollständig im Reasoning verbraucht; 5 davon hatten bei gleichem Budget schon
  einmal Zellen. Mehr Budget verschiebt die Grenze, nicht das Verhalten.
- **Goldstandard anpassen.** Die Fehler liegen in der Bindung, nicht in der
  Annotation. Eine Goldänderung würde das Problem verdecken.
- **Predictions überschreiben.** Die drei inspizierten Fälle sind nur deshalb
  nachvollziehbar, weil die Rohantworten unverändert vorliegen.
- ~~**Ein weiteres Modell als Referenz.** Der Vergleich ist kein Modellproblem:
  Beide Läufe nutzen `gwdg/glm-5.3` mit derselben Prompt-Fassung.~~
  **Widerlegt am 20.11.2026 (n = 2 Records).** Auf demselben Prompt bricht
  `glm-5.3` auf `yun2024:421` mit vollem Budget und 0 Zeichen ab, `qwen3.5-397b`
  antwortet in 10.686 Tokens mit `stop`; auf `yun2024:119` antwortet qwen in
  6.236 Tokens und trifft. Das Modell ist ein Faktor, nicht nur die Prompt-Fassung.
  Siehe Nachtrag unten.

## Nachtrag 20.11.2026, abends: Schema, Anweisung und Modell getrennt

Die alte Fassung dieser Empfehlung führte die 33 Abbrüche auf ein Schema- und
Strukturproblem zurück (Maßnahme 1/2). Seitdem sind elf Aufrufe der Stufe 1 auf
fünf Records gelaufen, alle mit demselben 6.000-Zeichen-Ausschnitt, Temperatur
0 und je einem Aufruf pro Zelle. Das Bild hat sich verschoben.

| Record | Modell | Prompt-Fassung | Budget | Tokens | Ergebnis |
|---|---|---|---:|---:|---|
| 523 | `glm-5.3` | Zeilenlabel, ohne Zusatz | 16.632 | 16.632 | **Abbruch**, 0 Zeichen |
| 523 | `glm-5.3` | Zeilenlabel + Zusatz | 16.632 | 3.318 | ok, 2 Locators |
| 523 | `glm-5.3` | Satz-Locator + Zusatz | 16.632 | 2.342 | ok, 2 Locators → Stufe 2: 4 TP/0 FP/2 FN, F1 0,800 |
| 420 | `glm-5.3` | Zeilenlabel + Zusatz | 16.632 | 16.632 | **Abbruch**, 0 Zeichen |
| 420 | `glm-5.3` | Satz-Locator | 16.632 | 16.632 | **Abbruch**, 0 Zeichen |
| 420 | `qwen3.5-397b` | Satz-Locator (identischer Prompt) | 16.000 | 7.728 | ok, 2 Locators, **Treffer** (4/6 Werte im Satz) |
| 52 | `qwen3.5-397b` | Satz-Locator | 16.000 | 7.400 | ok, 2 Locators, **Treffer** (11,5/13,6, Armrichtung korrekt) |
| 421 | `glm-5.3` | Satz-Locator | 16.632 | 16.632 | **Abbruch**, 0 Zeichen |
| 421 | `glm-5.3` | Zeilenlabel + Zusatz | 16.632 | 16.632 | **Abbruch**, 0 Zeichen |
| 421 | `qwen3.5-397b` | Satz-Locator | 16.000 | 10.686 | ok, **`found: false`** (falsches Negativ) |
| 119 | `qwen3.5-397b` | Satz-Locator | 16.000 | 6.236 | ok, 2 Locators, **Treffer** |

Berichte: `zweistufig_lauf_20261120/satz_523_ergebnis_20261120.md`,
`satz_420_ergebnis_20261120.md`, `satz_421_ergebnis_20261120.md`,
`zusatz_421_ergebnis_20261120.md`, `qwen_421_ergebnis_20261120.md`,
`qwen_119_ergebnis_20261120.md`, `qwen_420_ergebnis_20261120.md`,
`qwen_52_ergebnis_20261120.md`.

**Stufe 2, nachgetragen:** `yun2024:523` mit `glm-5.3` — 268 Tokens, 4 Zellen,
4 TP / 0 FP / 2 FN, F1 0,800. `yun2024:420` mit `qwen3.5-397b` auf dem oben
zitierten Satz — 2.590 Tokens von 4.000, 4 Zellen, **4 TP / 0 FP / 2 FN,
F1 0,800**, Dauer 124,12 s, gelesen wird `0.95 [SD, 0.24]` gegen
`1.43 [SD, 0.48]` (das erste Schnittstellenpaar, wie das Gold). Die zwei FN
sind die Gruppengrößen 18 und 21, die nur im Kopf der qualitativen Tabelle
stehen und nicht in der Belegstelle. Bericht:
`zweistufig_lauf_20261120/stufe2_satz_420_qwen_ergebnis_20261120.md`.
`yun2024:119` mit `qwen3.5-397b`, Budget 4.000 — **abgebrochen**
(`finish_reason = length`), 4.000 Tokens, 15.994 Reasoning-Zeichen, 0 Zeichen
Inhalt, also keine Aussage über den Satz. Bericht:
`stufe2_satz_119_qwen_4000_ergebnis_20261120.md`.
`yun2024:119` mit `qwen3.5-397b`, Budget 8.000 (byte-identischer Prompt) — **ok,
0 Zellen**: 5.899 Tokens, 22.362 Reasoning-Zeichen, Antwort
`{"cells": [], "quote": …}`. Offline vorab geprüft: die Arme stehen im Satz
(`mild cooling` 4×, `no cooling` 5×), `70%` und `15.4%` je einmal wörtlich, die
Gruppengrößen 10/13 gar nicht. Bericht:
`stufe2_satz_119_qwen_8000_ergebnis_20261120.md`.
`yun2024:52` mit `qwen3.5-397b`, Budget 8.000, `--paare 1` (der Satz berichtet je
Arm **einen** Wert) — **ok, 2 Zellen**: 2.827 Tokens, 10.082
Reasoning-Zeichen, `intervention_mean` = 13,6 und `comparator_mean` = 11,5,
beide richtig zugeordnet, **2 TP / 0 FP / 4 FN** (P 1,00, R 0,333, F1 0,500).
Die Armrichtung steckt nur in „from 11.5% to 13.6% … postintervention"; der
Prompt nennt sie nicht. Die Vorgabeprompts für 523 und 420 sind byte-gleich
geblieben (SHA `f6753fd3…` und `977e817a…`). Bericht:
`stufe2_satz_52_qwen_8000_ergebnis_20261120.md`.

**Befund 1 — das Schema ist nicht die Ursache.** Auf 420 brechen *zwei*
verschiedene Fassungen ab (Zeilenlabel mit Zusatz und Satz-Locator), auf 421
ebenso. 4 von 4 Zellen, je volles Budget, je 0 Zeichen Inhalt, bei 6 von 6
Goldwerten im Ausschnitt. Wer das Schema weiter ändert, ändert an diesen beiden
Records nichts.

**Befund 2 — die Anweisung wirkt, aber nicht überall.** „Answer without weighing
alternative readings." trennt auf 523 zwischen Abbruch (16.632) und Antwort
(3.318, bzw. 2.342 mit Satz-Schema). Auf 420 und 421 trennt sie nichts. Der
Effekt ist record-abhängig und mit den vorhandenen Messungen nicht erklärt.

**Befund 3 — das Modell ist ein Faktor.** Auf demselben Prompt und demselben
Ausschnitt antwortet `qwen3.5-397b`, wo `glm-5.3` das Budget verbrennt (420, 421,
119). Auf 420 ist der Prompt byte-identisch (7.313 Zeichen, gleicher SHA256),
also ist der Abbruch dort nachweislich modell- und nicht recordspezifisch. Der
Preis ist ungleich: auf 421 ist die Antwort ein falsches Negativ, auf 420 ein
Treffer mit 4 der 6 Goldwerte im zitierten Satz, auf 119 ein Treffer am
richtigen Zeitpunkt mit wörtlich belegtem Satz.

**Der Effekt trägt über PMC3877023 hinaus (n = 2 fremde Dokumente).** Auf
`yun2024:52` (PMC3195393), einem der 33 P5-Abbrüche aus einem unberührten
Dokument, antwortet qwen in 7.400 Tokens mit dem richtigen Satz und ordnet die
Arme über die Richtung („from 11.5% to 13.6% … postintervention") korrekt zu:
intervention = 13,6 mit `timepoint = postintervention`, comparator = 11,5 mit
`pre-intervention`. Derselbe Record ist im P5-Lauf mit `glm-5.3` nach 95.546
Reasoning-Zeichen ohne Inhalt abgebrochen. Die qwen-Stufe-1-Bilanz steht damit
bei 3 Treffern in 4 Aufrufen, und das einzige falsche Negativ (421) liegt
**innerhalb** von PMC3877023. Ein
Modellwechsel allein ist damit **keine** Lösung: für die P5-Bilanz sind Abbruch
und `found: false` gleich, weil `bilanz_p5` jedes Goldfeld ohne passende
Vorhersagezelle als FN zählt, ob die Antwort leer blieb oder nicht. Der
Unterschied ist, dass ein antwortendes Modell diagnostizierbar ist und auf 119
in einen Treffer kippt; ob es auf weiteren Records kippt, ist die offene Frage.
Wer den Modellwechsel vorschlägt, muss also den Treffer auf 119 zeigen, nicht
die bloße Verfügbarkeit.

**Befund 4 — die Annotation trägt einen Bezeichnungsfehler, der Recall kostet.**
Auf 119 sind von 4 Goldzellen nur 2 aus dem Ausschnitt erreichbar: die
Gruppengrößen 10 und 13 stehen nicht im Text. Zusätzlich deklariert der Kontext
`outcome_type = continuous`, während gedruckt ein dichotomierter Anteil steht
(„70 % attained good GOS"), den das Gold als `mean` führt. Auch bei perfektem
Locator ist dieser Record nicht 4/4. Das Gold bleibt unverändert; die Zahl
gehört aber in jede Bewertung des Records.

**Was daraus für die Maßnahmenliste folgt:** Maßnahme 1 (Anker) bleibt an zwei
Records ohne Gewinn, Maßnahme 3 ist erledigt, Maßnahme 4 ist gebaut und gemischt
gemessen, Maßnahme 2 (Antwortgerüst) ist mit Befund 1 und 3 nicht mehr die
naheliegende nächste Größe — sie ändert nichts an einem Modell, das ohne
Ausgabe das Budget verbraucht, und nichts an einem Satz, der zitiert wird.

## Nächster Schritt

Die Kette auf 52 ist geschlossen (2 TP / 0 FP, Armrichtung korrekt). Die
Fensterwahl ist offline nachgemessen (`fensterlage_20261120.py`,
`p5_fensterlage_20261120.md`; 33 Abbrüche, 118 verschiedene Goldwerte):

| Goldwerte im 6.000er-Fenster | Abbrüche (von 33) |
|---|---:|
| 0 | 6 |
| 1 | 6 |
| 2 und mehr | 21 |

Die frühere Tabelle war falsch etikettiert: 21 ist die Zahl der Records mit
**mindestens zwei** Werten im Fenster, nicht mit null. Ohne jeden Wert im
Fenster sind 6 (159, 164, 624, 625, 685, 687), mit genau einem 6.

Von den 118 Goldwerten stehen 92 im Dokumenttext, 26 nicht (Bildtabelle, nur
Caption). Das aktuelle Fenster zeigt 67, also 25 im Text stehende Werte nicht.
Das beste einzelne 6.000er-Fenster käme auf 91; nur ein Wert passt in kein
Fenster dieser Breite. Der Engpass ist die Startregel, nicht die Breite: drei
2.000er-Stücke erreichen 72 Werte und 24 Records mit mindestens zwei Werten
(gegenüber 67 und 21 beim Einzelfenster). Drei der sechs Records ohne Wert im
Fenster (164, 624, 625) haben gar keinen Goldwert im Text; dort hilft keine
Regel, nur eine andere Dokumentaufbereitung.

Nachgeprüft am 20.11.2026 (`fundstellen_20261120.py`): Von den 92 im Text
gefundenen Werten ist genau **einer** eine reine Zitat- oder Verweisnummer
(152: 7.0 ist "Figure 7"). **75** stehen im Ergebnisteil, davon 19 nur in
eingeflachtem Tabellentext; 2 stehen nur im Abstract, 2 nur in der Diskussion,
12 in vier Dokumenten ohne Body-Überschrift (52, 152, 557, 559; auf 52 stehen
sie sichtbar in der Ergebnistabelle). Auf der belastbaren Menge bleibt der
Abstand zwischen Orakel und Fenster erhalten: **74 gegen 48** (mit den
Unbekannten 85 gegen 56). Die 91/67 sind also nicht durch Zufallstreffer
getragen; wer nur den Ergebnisteil zählt, nennt 74/48.

Für eine qwen-Serie heißt das: über alle 33 würde sie zu 51 von 118 Werten
(43 %) die Fensterwahl bzw. die Dokumentaufbereitung messen. Das Modell messbar
ist sie auf den 21 Records mit mindestens zwei Werten im Fenster; 159 und
446/451 gewinnen mit drei 2.000er-Stücken, 685/687 nur mit einem Fenster, das
bis an die Tabellenzeile reicht.

1. **Erledigt:** Fensterlage offline geprüft (0 Tokens), Ergebnis oben und in
   `p5_fensterlage_20261120.md`.
2. **Nächster Aufruf:** qwen-Serie nur auf den 21 Records mit mindestens zwei
   Werten im Fenster (Budget 16.000 je Record, gemessener Verbrauch
   6.236–7.728); 164, 624, 625 bleiben außen vor, bis die Bildtabellen
   maschinenlesbar sind.

Nicht empfohlen bleibt: weitere Stufe-2-Aufrufe auf 119 (Feldbezeichnung offen),
weitere Prompt-Fassungen auf 420/421 (Befund 1), eine Budgeterhöhung als
Strategie und eine Änderung des Goldstandards.
