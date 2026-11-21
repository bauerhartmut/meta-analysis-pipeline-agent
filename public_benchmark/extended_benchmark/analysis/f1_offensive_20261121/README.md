# F1-Offensive: Fehlerursachen, Locator, Validierung (21.11.2026)

Auftrag: 759 FN und 507 FP kategorisieren, den Satz-Locator um die
Unterscheider-Pflicht erweitern, die Zwei-Stufen-Kette verallgemeinern und
danach bis zu drei gezielte Netzlaeufe auf 420, 421 und 523 fahren. Gold,
Testset und Bewertungslogik bleiben unveraendert; alle Zahlen sind aus
vorhandenen Predictions nachgerechnet.

| Datei | Inhalt |
|---|---|
| `zahlabgleich_20261121.py` | gemeinsamer Zahlabgleich fuer Fehleranalyse und Validierung |
| `fehlerursachen_20261121.py` / `.md` / `.json` | Phase 1: Kategorisierung der FN und FP |
| `satz_locator_20261121.py` / `.md` / `.json` | Phase 2: Locator mit Unterscheider-Pflicht, 10 Regressionfaelle + 30 schwere Faelle |
| `validiere_zellen_20261121.py` / `validierung_20261121.md` / `.json` | Phase 3: goldfreie Zellvalidierung, am 699-Hybrid gemessen |
| `record30_kette_20261121.py` / `.md` / `.json` | Phase 3: Record 30 offline nachgerechnet, Fundstelle je Zelle |
| `zeilenbindung_20261121.py` / `.md` / `.json` | Zeilenbindung als Regel, gemessen an allen 41 schweren Records |

## Zahlabgleich: eine Fassung fuer beide Skripte

Fehleranalyse und Zellvalidierung hatten zwei verschiedene Fassungen. Die
Fehleranalyse verwarf `14.2` in `14.20`, `48` in `48.0` und `48` in `48.` am
Satzende und zaehlte dadurch zu viele Werte als "nicht im Text". Beide nutzen
jetzt `zahlabgleich_20261121.zahl_positionen`:

- Punkt oder Komma als Dezimaltrenner,
- nachlaufende Nullen erlaubt (14.2 passt auf 14.20),
- ganzzahlige Zelle passt auf 48.0, nicht auf 48.5,
- keine angrenzenden Ziffern (48 passt nicht auf 148),
- Satzpunkt ist kein Zahlbestandteil.

Zusaetzlich trennt die Fehleranalyse jetzt "steht im Dokument nicht" von "steht
erst hinter der 45.000-Zeichen-Grenze". Gemessen: **0 Faelle** liegen nur hinter
der Grenze; die Kuerzung ist fuer diese Kategorien also kein Faktor.

## Phase 1: Fehlerursachen (neu gerechnet)

Basis 699 Records, 2.014 Goldzellen, Hybrid wie in `vergleiche_20261120.py`
(GLM auf 596, P5 auf 102). Die Bilanz ist unveraendert: TP 2.014, FP 507, FN 759.
Jede FN und jede FP traegt genau eine Kategorie mit Regelkennung und Beleg
(Position im Text, Vergleichszelle); das Skript bricht ab, wenn die Summen nicht
exakt 759/507 treffen.

| FN-Kategorie | Anzahl | Anteil |
|---|---:|---:|
| Wert erkannt, falsch gebunden (anderer Wert ausgegeben) | 295 | 38,9 % |
| leere Modellausgabe | 182 | 24,0 % |
| Wert steht im Dokument nicht (Abdeckung) | 164 | 21,6 % |
| Wert im Prompt, nicht ausgegeben | 118 | 15,6 % |
| Gold-Mehrdeutigkeit | 0 | 0 % |

| FP-Kategorie | Anzahl | Anteil |
|---|---:|---:|
| Wert erkannt, falsch gebunden | 270 | 53,3 % |
| falsches Outcome | 160 | 31,6 % |
| falsche Einheit (Faktor oder Rate als Anzahl) | 40 | 7,9 % |
| falscher Zeitpunkt (Baseline- oder Aenderungswert) | 22 | 4,3 % |
| Zahl steht nirgends im Dokument | 10 | 2,0 % |
| doppelte Zelle | 4 | 0,8 % |
| falsches Feld | 1 | 0,2 % |
| falscher Arm | 0 | 0 % |
| Zahl erst hinter der Prompt-Grenze | 0 | 0 % |
| Zeitpunktfehler aus anderer Zeile | 0 | 0 % |

### Verschiebung gegenueber der ersten Fassung

| Kategorie | vorher | nachher | Differenz |
|---|---:|---:|---:|
| FN Wert erkannt, falsch gebunden | 286 | 295 | +9 |
| FN Wert nicht im Prompt | 173 | 164 | -9 |
| FN leere Ausgabe / nicht ausgegeben | 182 / 118 | 182 / 118 | 0 |
| FP falsch gebunden | 264 | 270 | +6 |
| FP falsches Outcome | 157 | 160 | +3 |
| FP falscher Zeitpunkt | 19 | 22 | +3 |
| FP Halluzination | 22 | 10 | -12 |
| FP Einheit / Dublette / Feld | 40 / 4 / 1 | 40 / 4 / 1 | 0 |

Damit sind 21 FN und 12 FP anders zugeordnet; die Gesamtzahlen bleiben, weil nur
die Zuordnung innerhalb der 759 und 507 wechselt. Belastbar sind jetzt vor
allem die beiden Zahlen, die vorher zu hoch waren: **12 der 22 "Halluzinationen"
standen im Dokument** und sind gebundene Fremdzahlen, und **9 der 173
"nicht im Prompt"** wurden mit dem korrigierten Abgleich im Text gefunden und
sind jetzt als "anderer Wert ausgegeben" eingeordnet.

Zwei inhaltliche Befunde bleiben:

- **Armfehler als exakter Werttausch existieren nicht** (0 Faelle). Was wie ein
  Armfehler aussieht, ist ein Populations- oder Zeilenfehler: der Wert ist
  Goldwert eines anderen Records derselben Publikation (`fp_outcome`, 160) oder
  steht im selben Dokument an anderer Stelle (`fp_gebunden`, 270).
- **Gold-Mehrdeutigkeit im definierten Sinn gibt es nicht** (0): kein Record
  traegt fuer denselben Schluessel zwei Werte, kein Wert steht in beiden Armen.

## Phase 2: Satz-Locator mit Unterscheider-Pflicht

Der Locator bindet einen Satz nur, wenn er ein Zahlenpaar und den seltensten
Outcome-Begriff traegt (der Pflichtbegriff ist die Region: `Cervicothoracic`
gegen `thoracolumbar`). Der Begriff darf im direkt folgenden Satz stehen.
Mehrere Kandidaten werden nicht aufgeloest, sondern verweigert.

| Fallgruppe | alt: Bindungen | alt: mit Goldpaar | neu: Bindungen | neu: mit Goldpaar | Verweigerungen |
|---|---:|---:|---:|---:|---:|
| 10 gespeicherte Faelle | 5 | 4 | 4 | 0 | 6 |
| 30 schwere Faelle | nicht erhoben | - | 12 | 5 | 18 |

Ergebnis ohne Beschoenigung: Der alte Locator band fuenf Saetze, vier davon mit
dem richtigen Zahlenpaar. Der neue bindet vier Saetze mit Pflichtbegriff und
keinem richtigen Zahlenpaar und verweigert sechs Faelle. Die Pflicht verschiebt
die Bindung damit von der richtigen Zahl zum falschen Satz: 420 und 421 nennen
das Regionswort, tragen aber andere Zahlen. Ursache ist strukturell - das
Regionswort steht im Tabellenkopf oder in der Ueberschrift, das Zahlenpaar in
der Zeile; solange beides in einem Satz gesucht wird, konkurrieren sie. Der
Locator ist in dieser Fassung also ein Riegel gegen stille Fehlbindungen, aber
kein F1-Hebel.

## Phase 3: Zwei-Stufen-Kette und Validierung

- **Record 30 (PoC)**: gespeicherte Stufe 1 waehlt die Zeile `Mean score (SD)`,
  Block `Week 52`; Stufe 2 liefert sechs Zellen, jede mit Fundstelle im
  Dokument belegt, F1 1,0 vor und nach der Validierung. Keine Regression.
- **Goldfreie Validierung am 699-Hybrid**: 48 Zellen verworfen, davon 31
  nicht-ganzzahlige Ereignis- oder Gruppenzahlen und 17 Ereigniszahlen groesser
  als die eigene Gruppengroesse. TP unveraendert 2.014, FP 507 auf 459, F1
  **0,7609 auf 0,7678**.
- **Nicht verwerfend, nur gemeldet**: der Textabgleich (87 Zellen) und die
  Prozentpruefung (10). Ein Verwerfen haette 76 richtige Zellen geloescht, weil
  der gespeicherte Dokumenttext bei einigen Records die Goldwerte nicht
  enthaelt. Das ist ein Befund zur Dokumentfassung, kein Zellfehler.

## Zeilenbindung mit Zeilengruppen-Achse (Nachtrag 21.11.2026)

Regel ohne Gold: Datenzeile mit `Wert (SD)`-Paaren, Spaltenraster aus Arm- und
Wochenzeile als Filter vor der Auswahl, Zeilengruppen-Ueberschrift (PCS/MCS)
als zweite Achse, Armwahl ueber Spaltenlabels inklusive Dosis und
Comparator-Alias (`Control` trifft `PBO`), Zeitpunkt aus dem Record oder - bei
reiner Zeitpunktregel - der letzte Wochenblock.

Record 30 gegen seine 6 Goldzellen (38.1/9.5 und 31.5/7.4, n = 393/199, Woche
52, Gruppe PCS):

| Variante | gebunden | Gruppe | Block | Goldtreffer |
|---|---|---|---:|---:|
| streng | nein (3 gleich gute Zeilen) | - | - | 0/6 |
| erstes | ja | PCS | 52 | 6/6 |

Messung auf allen 41 schweren Records (`TP-Verlust` negativ = Gewinn). Die
`ersetzen`-Laeufe waren zahlengleich zu `additiv` und sind nicht ausgewiesen:

| Gruppenmodus | gebunden | neue TP | davon erreichbar | FP-Delta | TP-Verlust |
|---|---:|---:|---:|---:|---:|
| streng | 1 | 1 | 0 | +5 | -1 |
| erstes | 3 | 7 | 0 | +11 | -7 |

Ergebnis: **0 der 24 erreichbaren `fp_gebunden`/`fn_wert_ersetzt`-Zellen**
(26 mit Kaption-Bezug) werden neu gebunden. Der Zugewinn von 7 TP liegt
ausschliesslich in `fn_leer`-Zellen: Record 30 mit 6 von 6 und eine Zelle in
`yun2024:446`. Von 18 gebundenen Zellen sind 7 richtig; `yun2024:451`
(`Age (years)`) ist ein Fehlgriff des Stichentscheids (0/6).

Grenze des Verfahrens: `streng` verweigert Record 30, weil der Kontext weder
PCS noch MCS nennt; `erstes` trifft PCS nur, weil PCS die erste Gruppe der
Tabelle ist. Bei einem Record mit MCS-Gold waere dieselbe Regel falsch.

## Gegenprobe: alle 699 Records (offline)

Dieselbe Regel, additiver Modus, alle 699 Records mit Gold und P5-Zellen
(`zeilenbindung_gesamt_20261121.py`):

| Gruppenmodus | gebunden | Zellen (richtig) | TP | FP | FP-Delta | TP-Delta |
|---|---:|---:|---:|---:|---:|---:|
| streng | 2 | 12 (2) | 172 | 111 | +10 | +2 |
| erstes | 22 | 126 (34) | 198 | 177 | +76 | +28 |

Die Zusatz-FP der 41 verschwinden nicht, sie sind nur ein kleiner Teil: 11 der
76 bei `erstes`. Die uebrigen 658 Records steuern +65 FP bei +21 TP bei, das
Verhaeltnis wird also schlechter, nicht besser. `streng` bleibt bei 2 TP zu
10 FP. Die Regel bindet 22 von 699 Records (3 Prozent) und trifft in deren
126 Zellen zu 34 (27 Prozent) das Gold.

### Luecke 34 richtige Zellen zu 28 neuen TP

Belegt, nicht geschaetzt: von den 34 richtigen Zellen kamen 28 neu hinzu (das
ist genau das TP-Delta), 6 standen vorher schon richtig am Schluessel.
Doppelte Gold- oder Bindungsschluessel gibt es nicht (0/0). Von den 92 falschen
Zellen entfallen 76 auf einen falschen Wert an einem echten Goldschluessel, 16
auf Schluessel, die im Gold gar nicht vorkommen, und genau 1 auf einen Wert,
der unter dem anderen Arm im Gold steht. Eine vertauschte Armzuordnung ist
als Ursache damit fast ausgeschlossen.

## Zeilenbenennung im Prompt: 20 von 295 Faellen

Systematische Stichprobe (jeder 15. Fall der 295 `fn_wert_ersetzt`), offline
(`zeilenbenennung_20261121.py`):

| Klasse | Faelle |
|---|---:|
| Zeile eindeutig benannt | 1 |
| Zeile mehrdeutig benannt | 1 |
| Zaehlfeld ueber Kaption/Tabelle benannt | 2 |
| Wert nur im Fliesstext | 14 |
| Wert in Zeile ohne Outcome-Bezug | 2 |

Getrennt nach Feldgruppe, damit die Zaehlfelder die Aussage nicht verwaessern:

| Feldgruppe | Faelle | eindeutig | mehrdeutig | Kaption | Fliesstext | ohne Bezug |
|---|---:|---:|---:|---:|---:|---:|
| Mittelwerte | 6 | 1 | 0 | 0 | 5 | 0 |
| Streuungen | 4 | 0 | 1 | 0 | 3 | 0 |
| Zaehlfelder | 10 | 0 | 0 | 2 | 6 | 2 |

Fuer Mittelwerte und Streuungen (10 Faelle) bleiben damit 2 durch Zeilen-
benennung erreichbar, 8 nicht. Bei den Zaehlfeldern sind 2 ueber die Kaption
auffindbar, 6 stehen nur im Fliesstext, 2 in Zeilen ohne Outcome-Bezug. In der
Gesamtmenge der 295 sind 127 Zaehlfelder, 100 Mittelwerte, 68 Streuungen.

## Zaehlfelder: fehlende Groessenzeile oder Armzuordnung?

Alle 127 `fn_wert_ersetzt` mit `group_size` oder `events`, offline
(`zaehlfelder_20261121.py`):

| Klasse | Faelle |
|---|---:|
| Groessenzeile vorhanden, Wert im richtigen Arm | 31 |
| Groessenzeile vorhanden, Wert im anderen Arm | 20 |
| Arm nur ueber Kopfzeile zugeordnet | 6 |
| Arm nicht bestimmbar | 22 |
| Groesse nur als Nenner (8/20) | 16 |
| Groesse nur im Fliesstext | 32 |

Damit ist die fehlende Groessenzeile der groessere Block: 48 von 127 (38
Prozent) haben keine Zeile, in der die Groesse als eigene Zelle steht. Die
Armzuordnung ist hoechstens in 20 Faellen (16 Prozent) betroffen, und diese
Klasse ist nicht sauber belegt: Beschriftungen wie `No text message` tragen
dieselben Woerter wie der Interventionsarm, wodurch die Zuordnung kippt
(Sichtpruefung `yun2024:100`). 28 Faelle sind ohne Armnamen nicht entscheidbar,
31 sind in Ordnung (dort ist die Auswahl der Zahl das Problem). Ein Arm-Tausch
der Vorhersage ist in keinem Fall belegbar: die ausgegebene Zahl stimmt nie mit
der Zahl des anderen Arms in derselben Groessenzeile ueberein.

## Nachregel fuer Gruppengroessen: 0 von 48

`groessen_regel_20261121.py` liest Gruppengroessen nur noch aus Nennern
(`k/n`), und zwar ausschliesslich dann, wenn die Kopfzeile die Groessen selbst
nennt (`n = ...`) und jede Spalte einem Arm zugeordnet ist. Die Satzquelle
(`N patients were randomized ...`) ist entfernt: sie las ausschliesslich
Gesamtzahlen und lieferte fuenf Werte, alle falsch. Gemessen an den 48
Zaehlfeldern ohne Groessenzeile:

| Kennzahl | Wert |
|---|---:|
| Ziel-Faelle | 48 |
| Regel liefert einen Wert | 0 |
| davon richtig | 0 |
| verweigert | 48 |
| FP (additiv) | 0 |
| TP-Verlust | 0 |

Die 48 bestehen aus 29 Ereignis-Feldern (keine Groesse, kein Nenner) und 19
Groessenfaellen. In den Groessenfaellen steht der Goldwert zwar oft als Nenner
(16 Faelle), aber in Tabellen anderer Subgruppen (`yun2024:120`: Nenner 30/52,
Gold 20/44) oder als Kompletter-Zahl (`yun2024:547`: `68 of 72`). Ohne die
Satzquelle bleibt es daher bei Verweigerung und 0 FP.

## Ereigniszaehler: 4 von 29 lesbar

`ereignisse_20261121.py` prueft die 29 `events`-Faelle ohne Groessenzeile, ob
der Goldwert als Zaehler mit Prozentanteil in einer Zeile mit Armspalte steht:

| Klasse | Faelle |
|---|---:|
| Zaehler mit Prozentzeichen, richtiger Arm | 0 |
| Zaehler mit Prozent ohne Zeichen, richtiger Arm | 0 |
| Zaehler unter (%)-Kopfzeile, richtiger Arm | 4 |
| Zaehler im anderen Arm | 1 |
| Zaehler, Arm unklar | 14 |
| Wert ohne Prozentanteil | 10 |

Das Format `11 (12%)` kommt in keinem Fall vor; die Tabellen schreiben
`52 (39.1)` ohne Zeichen oder setzen `No. patients (%)` ueber nackte Zahlen. Nur
4 der 29 sind ueber eine (%)-Kopfzeile und den Arm in der Zeilenbeschriftung
deterministisch lesbar; 14 mal fehlt die Armzuordnung, 10 mal der Prozentbezug.

## Phase 4: Netzlaeufe 420, 421, 523 - nicht gestartet

Die Bedingung des Auftrags war "nach erfolgreichen Offline-Tests". Die
Offline-Ergebnisse erfuellen sie nicht:

- Der Locator erzeugt 0 richtige Bindungen (4 Bindungen, keine mit Goldpaar).
- Der einzige belastbare Gewinn ist der Nachfilter mit +0,0069 F1; er braucht
  keinen Netzlauf, weil er auf gespeicherten Predictions rechnet.
- Drei Records koennen die geforderte Bedingung "keine Verschlechterung der
  699-Record-Baseline" grundsaetzlich nicht zeigen.

Ein Lauf auf 420, 421 und 523 wuerde damit rund 30.000 bis 40.000
Completion-Tokens kosten (Schaetzung aus 8.003 + 3.262 je Record) und die
Ursache der 270 gebundenen Fehlzellen nicht adressieren. Die Entscheidung ist
deshalb: erst die Zeilenbindung fuer die `fp_gebunden`-Gruppe bauen, dann
laufen. Der fertige Befehl und die Kosten stehen in `zweistufig_lauf_20261120.py`
und in `tabelle_prosa_30_ergebnis_20261120.md`.

## Reproduktion

```
.venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/fehlerursachen_20261121.py
.venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/satz_locator_20261121.py
.venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/validiere_zellen_20261121.py
.venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/record30_kette_20261121.py
```

Alle vier Skripte sind lesend: kein Modellaufruf, keine geschriebene Prediction,
kein Gold angefasst.

## Grenzen

- Die Kategorien in Phase 1 sind exklusive Text- und Zahlenheuristiken, keine
  Rekonstruktion der Modellabsicht. `fp_zeitpunkt` erkennt Baseline- und
  Aenderungswerte nur ueber Schluesselwoerter im Umfeld.
- `fn_nicht_im_dokument` heisst: die Zahl steht in der gespeicherten
  Markdown-Fassung des Artikels nicht. Bei Bildtabellen und Anhaengen ist das
  eine Grenze der Aufbereitung, nicht der Extraktion.
- Die 30 schweren Faelle in Phase 2 sind Fenster um den ersten Goldwert, nicht
  das echte Retrieval.
- Der Nachfilter kann keine Zelle erzeugen und keinen Wert berichtigen; die
  270 gebundenen Fehlzellen bleiben.
- Alle Zahlen gelten fuer den Hybrid aus GLM und P5, nicht fuer eine neue
  Pipeline.
