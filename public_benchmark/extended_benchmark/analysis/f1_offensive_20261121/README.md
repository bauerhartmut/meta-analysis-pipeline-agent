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
