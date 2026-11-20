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

## Priorisierung

1. **Maßnahme 3 sofort** — kostet nichts, ist auf vorhandenen Predictions
   gemessen und verbessert die Precision. Sie löst das Problem nicht, aber sie
   ist der einzige Schritt ohne Risiko.
2. **Maßnahme 1 als Nächstes** — der größte erwartete Hebel bei den 13 Fällen,
   und der einzige, der ohne Netzlauf vorbereitet werden kann.
3. **Maßnahme 2** — billig, überschneidet sich mit 1, deshalb danach.
4. **Maßnahme 4** — der sauberste Angriff auf die Bindefehler, aber teuer und
   erst sinnvoll, wenn 1 und 2 die Verfügbarkeit gehoben haben.
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
- **Ein weiteres Modell als Referenz.** Der Vergleich ist kein Modellproblem:
  Beide Läufe nutzen `gwdg/glm-5.3` mit derselben Prompt-Fassung.

## Nächster Schritt

Der einzige Schritt ohne Kosten und ohne Freigabebedarf ist Maßnahme 3 auf den
vorhandenen 103 Predictions plus der trockene Prompt-Bau für Maßnahme 1. Beides
lässt sich in einem Offline-Lauf erledigen und liefert die Entscheidungsgrundlage
für den ersten Netlauf.
