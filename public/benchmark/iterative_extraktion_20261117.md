# Iterative High-Recall-Extraktion: Fehleranalyse, Architektur, Messungen

Stand 18.11.2026. Grundlage ist der vollstaendige GLM-5.3-Lauf auf Yun-699
(`runs/yun699_8000_alle_20261117`): 2.773 Goldzellen, 1.840 richtig, 281 falsch,
652 fehlend, Precision 0,8675, Recall 0,6635, F1 0,7519.

Alle Skripte liegen in `public_benchmark/extended_benchmark/iterativ/`, alle
Ergebnisse in `.../iterativ/ergebnisse/`. Bestehende Laeufe, Rohdaten und
Goldannotationen wurden nicht veraendert.

**Wichtige Einschraenkung vorab:** Der Netzversuch (Variante B/C/D) konnte in
dieser Nacht **nicht** gefahren werden. Das Gateway antwortet seit etwa 00:15
auf jede neue Anfrage mit `401 {"detail":"Not authenticated"}` und gibt nur
gecachte Kurzanfragen frei; gemessen wurde eine Durchsatzrate von einer Anfrage
pro vier Minuten. Die Ursache ist eine serverseitige Drosselung, kein Fehler im
Code: derselbe Aufruf gelingt nach einer Pause und scheitert unter Last wieder
(Belege im Abschnitt 5). Die ohne Netz messbaren Teile sind vollstaendig erhoben.

## 1. Fehleranalyse der 652 fehlenden Zellen

Verfahren: `fehleranalyse_zellen.py` sucht die jeweilige Goldzahl im gelieferten
Auszug, bestimmt den Blocktyp (Tabelle, Fliesstext, Abbildungsunterschrift),
prueft die Naehe zu den Armnamen, die Anzahl der Zeitangaben im Umfeld und bei
Event-Zellen, ob nur ein Prozentwert dasteht. Fehlt die Zahl im Auszug, wird
zusaetzlich das Volltext-XML durchsucht. Die Zuordnung ist **lexikalisch und
automatisch**, keine menschliche Annotation.

| Kategorie | Zellen | Anteil |
|---|---|---|
| technischer Ausfall (Record mit Fehlerklasse) | 427 | 65,5 % |
| nicht auffindbar (weder Auszug noch XML) | 71 | 10,9 % |
| leere Antwort (Record ohne Zellen) | 40 | 6,1 % |
| Zeitpunkt-Mehrdeutigkeit | 39 | 6,0 % |
| Tabelle | 30 | 4,6 % |
| Armkonflikt (Zahl nur beim anderen Arm) | 20 | 3,1 % |
| Prozent statt absoluter Anzahl | 13 | 2,0 % |
| Fliesstext | 12 | 1,8 % |
| Abbildung | 0 | 0,0 % |
| nur im Volltext, nicht im Auszug | 0 | 0,0 % |

### Befund 1: Fast drei Viertel sind Record-Ausfaelle, keine Suchprobleme

427 + 40 = **467 Zellen (71,6 %)** haengen an 140 Records, die entweder mit
`length_ohne_ergebnis` abgebrochen sind oder leer geantwortet haben. Diese Zellen
sind durch bessere Suche **nicht** zu gewinnen, sondern nur durch einen
Record-Nachzug (`--retry-failed`, bei erneutem `length` mit `--repair`).

### Befund 2: Der Korpus ist ein Auszug, nicht das Paper

Die 71 „nicht auffindbaren" Zellen stehen auch im Volltext-XML nicht: Die
mitgelieferten XML-Dateien enthalten denselben Abstract-plus-Results-Auszug wie
die Markdown-Dateien (Median der Dokumentlaenge in der Stichprobe: 13.663
Zeichen). Die Kategorie `nur_volltext` ist deshalb leer. Ein Teil der
Goldannotation stammt offensichtlich aus Teilen des Papers, die im Korpus fehlen
(Methoden, Tabellen des Volltexts). Das ist eine **Obergrenze fuer jede
Retrieval-Variante**, keine Modellschwaeche.

### Befund 3: Die restlichen Ausfaelle sind inhaltlich klar verteilt

Von den 185 inhaltlichen Auslassungen entfallen 39 auf Zeitpunkt-Mehrdeutigkeit,
30 auf Tabellen, 20 auf Armkonflikte, 13 auf Prozent-statt-Anzahl und 12 auf
Fliesstext. Genau diese 114 Zellen sind mit belegbarer Fundstelle adressierbar.

Je Feld (Auszug):

| Feld | technisch | leer | nicht auffindbar | Zeitpunkt | Tabelle | Arm | Prozent | Text |
|---|---|---|---|---|---|---|---|---|
| intervention_group_size | 100 | 14 | 10 | 12 | 1 | 5 | – | 4 |
| comparator_group_size | 100 | 14 | 8 | 14 | 5 | 9 | – | 4 |
| intervention_mean | 51 | 6 | 2 | – | 2 | 1 | – | 2 |
| comparator_mean | 52 | – | 3 | 4 | 3 | – | – | 2 |
| intervention_standard_deviation | 42 | – | 25 | 1 | 7 | – | – | – |
| comparator_standard_deviation | 42 | – | 22 | 5 | 8 | 3 | – | – |
| intervention_events | 20 | – | 1 | – | 2 | 2 | 6 | – |
| comparator_events | 20 | 6 | – | 3 | 2 | – | 7 | – |

Auffaellig: Die Standardabweichungen sind der groesste Bestand an „nicht
auffindbaren" Zellen (47 von 71). Sie stehen haeufig in Tabellen des Volltexts,
die im Auszug fehlen.

## 2. Architektur: Cell-Level-Retrieval mit Evidenzzwang

```
Record + fehlende Zelle (Feld, Arm, Outcome, Zeitpunkt)
        │
        ├─ 1. Suche       zerlegt den Auszug in Absaetze und Tabellenzeilen,
        │                 bewertet sie lexikalisch (Outcome, Armnamen,
        │                 Feldsynonyme) und waehlt die besten 9 Ausschnitte
        │                 (max. 7.000 Zeichen)
        │
        ├─ 2. Extraktion  ein Auftrag je Zelle; das Modell muss Wert **und**
        │                 woertliches Zitat, Zeilen- und Spaltenlabel nennen
        │
        ├─ 3. Belegpruefung  Zitat muss woertlich im Dokument stehen und den
        │                 Wert enthalten; sonst faellt die Antwort weg
        │
        ├─ 4. Evidenzaufloesung  bei zwei Modellen: nur belegte Antworten,
        │                 bei Gleichstand entscheidet der Armbezug im Zitat,
        │                 sonst Enthaltung (kein Mehrheitsentscheid)
        │
        └─ 5. Pruefregeln  Ereignisse gegen N, Prozent gegen Anzahl,
                          SD-Plausibilitaet, Outcome- und Zeitpunktbezug
```

Dateien und Zweck:

| Datei | Zeilen | Aufgabe |
|---|---|---|
| `gemeinsam.py` | 234 | Record-/Dokumentzugriff, Blockzerlegung, Zahlensuche, Armnamen |
| `fehleranalyse_zellen.py` | 223 | Kategorisierung der fehlenden Zellen |
| `zell_retrieval.py` | 302 | Suchauftrag, Prompt, Modellaufruf, Zitatpruefung |
| `zell_pruefung.py` | 120 | sechs Pruefgruppen, harte und weiche Regeln |
| `pruefung_offline.py` | 170 | Wirksamkeit der Regeln ohne Netzzugriff |
| `experiment.py` | 283 | Stichprobe, Varianten A–D, Precision/Recall/F1 |

Warum Evidenzzwang statt Mehrheitsentscheid: Ein Mehrheitsentscheid kann bei
zwei Modellen ohnehin nicht greifen, und bei drei entscheidet er nach
Modellstimmen statt nach Quellenlage. Das Zitatkriterium ist strenger und
pruefbar: Es akzeptiert nur Werte, die woertlich im Auszug stehen. Ein Modell,
das eine Tabellenzeile falsch liest, faellt damit durch, auch wenn zwei andere
dasselbe behaupten.

## 3. Implementierungsaufwand

Gemessen: 1.332 Zeilen Python in sechs Dateien, ohne Abhaengigkeiten ausser der
Standardbibliothek und dem bestehenden Harness (`_call_once`, `MODELS`).
Geschaetzter Aufwand fuer den hier gebauten Stand: ein Arbeitstag. Nicht
enthalten: OCR/PDF-Anbindung, UI, Parallelbetrieb mehrerer Laeufe.

## 4. Tokenverbrauch und Kosten (gemessen, nicht geschaetzt)

Fuer die 65 Zellen der Experiment-Stichprobe:

| Groesse | Wert |
|---|---|
| Prompt-Zeichen gesamt | 419.083 |
| Prompt-Tokens, Naeherung (Zeichen/4) | 104.770 |
| Median je Zelle | 6.657 Zeichen |
| Ausschnitte je Zelle (Median) | 3 |
| Anfragen bei zwei Modellen | 130 |

Hochgerechnet auf alle 652 fehlenden Zellen: rund **1,05 Mio. Prompt-Tokens je
Modell**, bei zwei Modellen 2,1 Mio. Dazu kommen kurze Antworten (JSON, rund
100–200 Tokens je Zelle). Zum Vergleich: Der GLM-Hauptlauf verbrauchte
1.934.079 Completion-Tokens fuer 699 Records.

Monetaere Kosten lassen sich fuer dieses interne Hochschul-Gateway nicht
ableiten; es gibt keinen oeffentlichen Preis pro Token. Belastbar sind Tokens
und Laufzeit.

## 5. Experiment A–D: vorbereitet, nicht gelaufen

Aufbau (`experiment.py --plan`, Seed 20261117): 20 Records, stratifiziert je 10
mit technischem Ausfall und 10 mit echter Auslassung, 75 Goldzellen, 65 fehlende
Zellen. Geplant waren 130 Anfragen (GLM + Qwen3 30B).

**Abbruchgrund.** Ab etwa 00:15 lieferte das Gateway auf jede neue Anfrage
`HTTP 401 {"detail":"Not authenticated"}`, auch auf Anfragen, die Minuten vorher
mit 200 beantwortet worden waren. Belege:

- derselbe Aufruf mit kurzem Prompt: 200 in 0,4 s, danach identischer Aufruf: 401 in 0,0 s,
- sechs Anfragen im Abstand von 12 s: 200 (aus dem Cache, 0,1 s),
- vier Anfragen im Abstand von 8 s: alle 401,
- der Lauf schaffte in vier Minuten eine einzige Anfrage.

Ein Auth-Problem des Schluessels ist ausgeschlossen (die Modellliste und
einzelne Kurzanfragen gingen durch); es ist eine serverseitige Drosselung. Der
Nachtlauf auf dem vollen Datensatz ist an derselben Ursache bei 1.485/2.094
stehen geblieben.

**Was trotzdem gemessen wurde (ohne API):**

- **Auffindbarkeit:** In 54 der 65 Stichprobenzellen (83,1 %) steht die Goldzahl
  woertlich im gelieferten Auszug. Nur diese Zellen kann ein Retrieval
  gewinnen — die Obergrenze fuer Variante B/C/D liegt damit bei 83 % der
  fehlenden Zellen, nicht bei 100 %.
- **Wirksamkeit der Pruefregeln** (Auftragspunkt 4) gegen den bestehenden Lauf,
  also gegen 2.121 bewertbare Zellen:

| Gate | markiert | davon falsch | davon richtig | erkennt von 281 falschen | verwirft von 1.840 richtigen | Precision danach |
|---|---|---|---|---|---|---|
| alle Regeln | 117 | 50 | 67 | 17,8 % | 3,6 % | 0,8847 |
| nur harte Regeln | 27 | 26 | 1 | 9,2 % | 0,1 % | 0,8782 |

Je Regel:

| Regel | markiert | davon richtig | Bewertung |
|---|---|---|---|
| `anteil_statt_mittelwert` | 55 | 41 | unbrauchbar, zu viele Fehlalarme |
| `sd_gegen_mittelwert` | 19 | 11 | schwach |
| `ereignisse_ueber_gruppengroesse` | 16 | 0 | **praezise** |
| `ereignis_nicht_ganzzahlig` | 16 | 0 | **praezise** |
| `arme_sehr_ungleich` | 16 | 14 | unbrauchbar |
| `sd_nicht_positiv` | 1 | 1 | neutral |

Damit ist belegt: Nur die Konsistenzregeln (Ereignisse ≤ N, ganzzahlige
Ereignisse) trennen zuverlaessig. Die „weichen" Regeln markieren ueberwiegend
korrekte Zellen und duerfen hoechstens warnen, nicht verwerfen. `zell_pruefung.py`
setzt das jetzt ueber `HARTE_REGELN` um; dazu gehoert auch
`gruppengroesse_nicht_positiv`, das erst der Synthetiktest als Luecke zeigte
(eine negative Gruppengroesse war zuvor von keiner Regel erfasst).

### Auswertungspfad A–D geprueft (synthetisch, ohne Netz)

`synthetik_test.py` schreibt 130 gezielt konstruierte Antworten auf die 65
Stichprobenzellen (Faelle: beide richtig, Streit mit Armbezug, nur ein Modell
belegt, Streit ohne Armbezug, beide gleich falsch, harter Verstoss) und laesst
denselben Auswertungscode laufen. Ergebnis:

| Variante | richtig | falsch | fehlend | Precision | Recall | F1 | hinzugefuegt |
|---|---|---|---|---|---|---|---|
| A | 10 | 0 | 65 | 1,000 | 0,133 | 0,235 | 0 |
| B | 41 | 24 | 10 | 0,631 | 0,547 | 0,586 | 55 |
| C | 51 | 13 | 11 | 0,797 | 0,680 | 0,734 | 54 |
| D | 50 | 10 | 15 | 0,833 | 0,667 | 0,741 | 50 |

Alle neun Pruefungen bestanden: A ergaenzt nichts, B nur belegte Antworten, C
ist nicht schlechter als B, C enthaelt sich beim Streit ohne Armbezug, D
verwirft genau die Zellen mit hartem Verstoss (2 negative Ereignisse, 2
Ereignisse bei kontinuierlichem Outcome) und wird dadurch nicht schlechter als
A.

Zusaetzlich sind drei Dateizustaende belegt (17 von 17 Pruefungen bestanden):
**unvollstaendig** (jede dritte Zeile fehlt) laeuft ohne Fehler und gewinnt
hoechstens so viel wie die vollstaendige Datei, **doppelt** (jede Zeile zweimal)
wird auf die letzte Zeile je Zelle reduziert und liefert exakt dieselben
Metriken, **leer** laesst B, C und D gleich A. Dabei fiel ein echter Fehler auf:
Die Zahl der eingelesenen Antwortzeilen wurde von einer gleichnamigen Variablen
in der Auffindbarkeits-Schleife ueberschrieben und stand bei 4 statt 0.

Die Zahlen sind **kein Modellergebnis**: Die Antworten sind erfunden, geprueft
wurde ausschliesslich, dass jede Verzweigung des Auswertungscodes laeuft und
plausible Werte liefert. Die echte Stichprobe unter `ergebnisse/exp1` bleibt
unberuehrt.

## 6. Empfehlung fuer den produktiven Einsatz

1. **Zuerst Record-Nachzug, nicht Zell-Retrieval.** 467 der 652 fehlenden Zellen
   (71,6 %) haengen an 140 Records mit technischem Ausfall oder leerer Antwort.
   Die Telemetrie beziffert den Block: 103 Length-Records tragen 423 fehlende
   Zellen und haben 824.000 Tokens ohne Ergebnis verbraucht; 36 leere Antworten
   tragen 40 Zellen bei nur 55.011 Tokens. Alle 139 Ausfaelle haben Reasoning
   produziert, aber nichts Verwertbares geliefert. Ein `--retry-failed` mit
   `--repair` wirkt auf alle Zellen eines Records gleichzeitig; Einzelheiten und
   fertige Befehle: `public_benchmark/extended_benchmark/iterativ/ergebnisse/retry_plan_glm.md`.
2. **Zell-Retrieval nur fuer die 114 inhaltlich klaren Auslassungen** (Tabelle,
   Zeitpunkt, Armkonflikt, Prozent-statt-Anzahl, Fliesstext). Das sind die
   Faelle mit belegbarer Fundstelle.
3. **Evidenzzwang ist Pflicht, Mehrheitsentscheid unzulaessig.** Ein Zitat, das
   woertlich im Auszug steht und den Wert enthaelt, ist die einzige Bedingung,
   die eine Zelle ohne Gold pruefbar macht.
4. **Nur harte Pruefregeln verwerfen.** Weiche Regeln nur als Warnung fuehren;
   sie markieren in der Messung 55 bzw. 16 Zellen, davon ueberwiegend korrekte.
5. **Korpus vor Modell erweitern.** 71 Zellen sind im gelieferten Auszug nicht
   enthalten. Bevor weitere Modellaufrufe in diese Zellen gehen, sollte der
   Volltext (Methoden und Tabellen) beschafft werden; sonst wird eine
   Obergrenze optimiert, die nicht im Modell liegt.

## 7. Reproduktion

```bash
cd public_benchmark/extended_benchmark/iterativ

# Fehleranalyse (ohne API)
../../../.venv/bin/python fehleranalyse_zellen.py \
    --out ergebnisse/fehleranalyse_glm699.json

# Pruefregeln und Auffindbarkeit (ohne API)
../../../.venv/bin/python pruefung_offline.py \
    --out ergebnisse/pruefung_offline.json

# Auswertungspfad ohne Netz pruefen (synthetische Antworten)
../../../.venv/bin/python synthetik_test.py --quelle ergebnisse/exp1 \
    --out-dir ergebnisse/exp1_synthetisch

# Experiment: Stichprobe, dann Netzphase, dann Auswertung
../../../.venv/bin/python experiment.py --plan --n-records 20 --seed 20261117 \
    --out-dir ergebnisse/exp1
../../../.venv/bin/python zell_retrieval.py --zellen ergebnisse/exp1/zellen.json \
    --modelle glm qwen30 --out ergebnisse/exp1/antworten.jsonl --workers 1 --pause 8
../../../.venv/bin/python experiment.py --auswerten --out-dir ergebnisse/exp1
```

Die Netzphase erzeugt `ergebnisse/exp1/antworten.jsonl` (eine Zeile je Zelle und
Modell, mit Wert, Zitat, Verifikationsflag, Tokens und Laufzeit) und
`ergebnis.json` (Varianten A–D mit Precision, Recall, F1, Verwerfungen und
Tokenverbrauch). Beides ist noch nicht erzeugt.

## 8. Grenzen dieser Auswertung

- Die Fehlerkategorien sind lexikalisch, nicht annotiert. Die Kategorie
  „Armkonflikt" bedeutet nur, dass die Zahl ausschliesslich im Umfeld des
  anderen Arms steht; sie beweist keinen Denkfehler des Modells.
- Die Auffindbarkeit prueft, ob die Zahl als Zeichenfolge im Auszug steht, nicht
  ob sie an der richtigen Stelle steht. 83,1 % ist deshalb eine Obergrenze.
- Die Messung der Pruefregeln nutzt die Modellzellen als Bezugsgroesse fuer N.
  Fehlt N in einer Antwort, greifen die N-abhaengigen Regeln nicht.
- Variante B/C/D ist auf echten Modellantworten ungemessen. Der Auswertungspfad
  ist synthetisch belegt (9/9 Pruefungen), aber ohne Netzmessung ist keine
  Aussage ueber den tatsaechlichen Recall-Gewinn moeglich; die Zahlen oben sind
  Obergrenzen und Regelguete, keine Ergebnisse des Experiments.
- GPT-6 Astra steht auf dem Gateway nicht zur Verfuegung (27 Modelle, u. a.
  `gwdg/glm-5.3`, `gwdg/qwen3.5-397b-a17b`, `gwdg/qwen3-30b-a3b-instruct-2507`,
  `gwdg/qwen3.6-35b-a3b`). Die dritte Modellstimme muesste ersetzt werden.
