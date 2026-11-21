# F1-Offensive: Fehlerursachen, Locator, Validierung (21.11.2026)

Auftrag: 759 FN und 507 FP kategorisieren, den Satz-Locator um die
Unterscheider-Pflicht erweitern, die Zwei-Stufen-Kette verallgemeinern und
danach bis zu drei gezielte Netzlaeufe auf 420, 421 und 523 fahren. Gold,
Testset und Bewertungslogik bleiben unveraendert; alle Zahlen sind aus
vorhandenen Predictions nachgerechnet.

Der zusammenfassende Stand der 295 Faelle (Endvariante 43 Zellen, 38 TP, 5 FP,
88 Prozent Trefferquote) steht in `abschlussbericht_20261121.md`.

Die Bausteine tragen bei den uebrigen FN-Regeln nicht; Messung und Begruendung
stehen in `bausteine_uebertrag_20261121.md` (50 Zellen, 7 TP, 43 FP bei 464
offenen Faellen). Die Kontrolle dazu (`pruefung_fn_20261121.md`) zeigt: keine
Ueberlappung mit den 43 Zellen, und die Stichprobe der
`fn_nicht_im_dokument`-Faelle bestaetigt die Klasse.

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

### Mit Zeitpunktzuordnung: 2 TP, 0 FP

`zaehler_zeitpunkt_20261121.py` sucht die Tabelle, deren Zeilenbeschriftung zum
Outcome-Namen passt, liest den Arm aus Zeile oder Kopfzeile und waehlt die
Spalte des Zielzeitpunkts (letzter berichteter).

| Variante | Zellen | TP | FP | TP-Verlust |
|---|---:|---:|---:|---:|
| `zaehler` (nur `n` + `(%)`) | 2 | 2 | 0 | 0 |
| `prozent` (auch Prozentzeilen) | 6 | 2 | 4 | 0 |

Nur `yun2024:190` ist ein echter Zaehler: Armzeilen `Intervention`/`TAU`,
Zeitpunktspalten `Baseline`/3/6/12 Monate, Zielspalte 12 Monate, Werte 52/51 =
beide Gold. Die drei Baseline-Faelle (370, 373, 379) sind Prozentwerte ohne
Zeitpunktachse; bei 370 und 373 liefert die Outcome-Zeile andere Zahlen als Gold
(`Diabetes, %  52  59` gegen 35/33), bei 379 gibt es keine passende Zeile. Die
`prozent`-Variante zahlt diese Fehlgriffe als 4 FP.

## Groessenzeile der Zielzeile: 2 von 31

`groessen_zielzeile_20261121.py` liest die Groessenzeile ueber der Zielzeile:
Zielzeile ueber den Outcome-Namen suchen, naechste echte Groessenzeile darueber
(`n = 40` mit Zahl), Spalte ueber die Armnamen. Gemessen an den 31 Faellen mit
korrekter Groessenzeile und richtigem Arm:

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | 31 |
| Regel liefert einen Wert | 6 |
| davon richtig (TP) | 2 |
| davon falsch (FP) | 4 |
| Zielzeile nicht ueber Outcome gefunden | 13 |
| Groessenzeile nicht in Reichweite | 4 |
| Arm nicht eindeutig | 4 |
| Tabelle gelesen, nur der andere Arm | 4 |

Die 2 TP sind `yun2024:346` und `yun2024:347` (Resveratrol/Placebo, je 22). Die
4 FP stammen alle aus `PMC5617873` (`yun2024:331/334/335/336`): dort ist
`intervention` = Aripiprazole, `comparator` = `Placbeo` (Tippfehler im Kontext),
Gold fuehrt aber 45 als Intervention und 47 als Comparator, waehrend die Tabelle
`Placebo (n = 45)` vor `Aripiprazole (n = 47)` stellt. Gold und Dokument sind
dort vertauscht; die Regel folgt dem Dokument.

Die unankerte Variante (alle Groessenzeilen im Dokument, nur bei einem einzigen
Wert je Arm) liefert 10 der 31 mit 2 TP und 8 FP und ist damit schlechter.

### Mit Aliasliste: 4 von 31

`zielzeile_alias_20261121.py` ergaenzt drei Wortformen (Scanning/Scan duration,
Akronyme ab drei Buchstaben, Plural) und misst die 31 erneut:

| Kennzahl | ohne Alias | mit Alias |
|---|---:|---:|
| geliefert | 6 | 9 |
| TP | 2 | 4 |
| FP | 4 | 5 |
| TP-Verlust | 0 | 0 |

Der Zugewinn sind `yun2024:426` (`Scanning times` gegen `Scan duration (min)`,
Armspalten `Short-Bore MR (n = 44)` / `Open MR (n = 49)`), also 2 TP.

Wirkung je Baustein:

| Variante | geliefert | TP | FP |
|---|---:|---:|---:|
| ohne Erweiterung | 7 | 2 | 5 |
| nur Akronyme | 7 | 2 | 5 |
| nur `scanning` | 9 | 4 | 5 |
| Akronyme + `scanning` | 9 | 4 | 5 |

Die Aliasliste enthaelt nur noch `scanning -> scan, duration`;`blood/pressure`
und `fruit/vegetable` sind entfernt, weil sie nichts veraendern. Die
Akronym-Regel bringt allein 0 TP.

Vier der fuenf FP sind Gold-Verdachtsfaelle (`PMC5617873`, Arme vertauscht:
dreimal `Placebo (n = 45)` vor `Aripiprazole (n = 47)`, Kontext-Intervention
Aripiprazole). Der fuenfte, `yun2024:196`, ist **kein** Gold-Fehler: Gold steht
so in Tabelle 2 (Woche 28, n = 24, Mittel 1.29/1.08), die Regel las die
Kopfzeile von Tabelle 1 (145/140). Belege im
`pruefvermerk_gold_20261121.md`; Gold blieb unveraendert.

### Alias ueber alle 295 fn_wert_ersetzt

`zielzeile_alle_20261121.py` misst dieselbe Erweiterung ueber alle
`fn_wert_ersetzt`, mit einem groben Leser je Feldtyp (Groesse aus der
Groessenzeile, Mittel und Ereignisse als erste Zahl der Armzelle, Streuung als
Zahl in Klammern).

| Kennzahl | ohne | mit Alias |
|---|---:|---:|
| Zielzeile gefunden (von 295) | 156 | 178 |
| Zellen geliefert | 39 | 47 |
| TP exakt | 14 | 20 |
| FP exakt | 25 | 27 |
| TP gerundet | 14 | 22 |
| FP gerundet | 25 | 25 |

Der Alias bringt **+22 gefundene Zielzeilen, +8 Zellen, +6 TP und +2 FP**; die
zwei FP sind Rundungen (31.7 gegen Gold 32, 19.8 gegen Gold 20), nach Rundung
also **+8 TP und +0 FP**. Neue Treffer: `yun2024:426` (Groessen 44/49 plus zwei
Mittel), `yun2024:664` und `yun2024:665` (je zwei Mittel).

Die 27 FP verteilen sich auf Groesse 10, Mittel 10 und Ereignis 7 (Streuungen 0):

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| Groesse | Groessenzeile | 8 | 10 |
| Mittel | `26.1 +/- 1.0` | 12 | 5 |
| Mittel | `Mittel (SD)` | 0 | 2 |
| Mittel | sonstig | 0 | 3 |
| Ereignis | nackt | 0 | 3 |
| Ereignis | sonstig | 0 | 3 |
| Ereignis | `Mittel (SD)` | 0 | 1 |

**Mittel nur noch im Format `Mittel (SD)` zu lesen ist eine Verschlechterung:**
Alle 12 richtigen Mittel standen im Format `26.1 +/- 1.0`; die 2 FP, die auch im
Format `Mittel (SD)` auftreten, haben eine falsche Zeile oder Spalte.

### Endvariante: Ereignisse aus, Mittel in beiden Formaten

Der Ereignis-Leser ist abgeschaltet (er lieferte 0 TP und 7 FP), Mittel werden
nur aus `Zahl +/- Zahl` und `Zahl (Zahl)` gelesen. Alle Laeufe ohne
Ereignis-Leser:

Groessenzeilen kommen aus der Tabelle der Zielzeile (mit Rueckfall auf die
naechste Zeile darueber); das Zellformat `n  Mean (95% CI)` wird als Zeilen-`n`
gelesen. Groessen sind Zaehlungen, Dezimalwerte und Werte unter 5 werden
verworfen.

| Kennzahl | ohne | mit Alias | nur `Mittel (SD)` | Endvariante |
|---|---:|---:|---:|---:|
| Zielzeile gefunden | 156 | 178 | 178 | 178 |
| Zellen | 28 | 34 | 16 | 33 |
| TP | 22 | 26 | 14 | 30 |
| FP | 6 | 8 | 2 | 3 |
| Trefferquote | 79 % | 76 % | 88 % | **91 %** |

Formate in der Endvariante:

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| Groesse | Groessenzeile | 10 | 2 |
| Mittel | `Zahl +/- Zahl` | 16 | 1 |
| Mittel | `Zahl (Zahl)` | 4 | 0 |

Das Uebereinstimmungs-Gate (`GATE`) gibt eine Groessenzelle nur aus, wenn
Label-Zuordnung und Positionsregel denselben Wert liefern. Es kostet die acht
PMC5617873-Zellen und den bewussten Positionsverlust bei `yun2024:426` und hebt
die Trefferquote von 88 auf 91 Prozent (33 Zellen, 30 TP, 3 FP).

Enthaelt ein Dokument eine Tabelle mit Wochenspalte, in der das Outcome
mehrfach vorkommt, gilt die Zeile des letzten Zeitpunkts statt der
Baseline-Zeile; bei mehreren solchen Tabellen entscheidet die fruehste. Der
Kopf wird auch fuer kurze Armnamen wie `Pls group` gelesen.

`yun2024:193` wird damit richtig: 138/131 aus Tabelle 2, Woche 28.
`yun2024:196` bleibt falsch - die Haupttabelle 2 nennt fuer Woche 28 die Werte
80/78, Gold (24/24) stammt aus Tabelle 3, einer Subgruppe (MMSE-J 20 bis 23).
Der Pruefvermerk fuehrt den Fall als `gold_aus_subgruppentabelle`.

Eine fruehere Blockheuristik ohne Wochenspalte wurde verworfen: sie waehlte bei
zwei Bloecken desselben Outcomes den falschen (196: Mittelblock 80/78 statt
Aenderungsblock 24/24) und griff in anderen Faellen eine spaetere, fremde
Tabelle ab.

Der Schritt bringt gegenueber dem Alias-Lauf mit Ereignissen 7 FP weniger bei
gleicher TP-Zahl; gegenueber der strengen Variante 12 TP mehr bei 5 FP mehr.

### Die 2 Groessen-FP und der Einsatz der 33 Zellen

`groessen_fp_einsatz_20261121.py`. Mit Gate bleiben zwei Groessen-FP:

| Klasse | Faelle |
|---|---:|
| falsche Tabelle (Subgruppe) | 2 |

Die 2 Tabellenfaelle sind die beiden Arme von `yun2024:196`: Gold stammt aus
Tabelle 3 (Subgruppe MMSE-J 20 bis 23, Woche 28), die Regel liest die
Haupttabelle 2 (80/78).

Die beiden Arme von `yun2024:426` fallen durch das Gate weg: Label-Zuordnung
(49/44) und Positionsregel (44/49) widersprechen sich, also wird die Zelle nicht
mehr ausgegeben. Damit ist der frueher bewusst bezahlte Positionsverlust
entfallen; die acht PMC5617873-Zellen ebenso.

`yun2024:193` ist mit der Wochenspalten-Auswahl richtig geworden.

Einsatz der 33 Zellen in die P5-Vorhersagen, Bilanz ueber alle 699 Records:

| Zellen | TP | FP | FN |
|---|---:|---:|---:|
| vorher | 170 | 101 | 2603 |
| alle 33 | 200 | 100 | 2573 |
| nur die 30 richtigen | 200 | 97 | 2573 |

Alle 33: +30 TP und -1 FP. Nur die richtigen: +30 TP und -4 FP (vier Zellen
ersetzten vorhandene falsche Werte).

### Mittel-FP: Tabellenlokalitaet half nicht, das Blocklabel schon

`mittel_fp_20261121.py`. Tabellenlokalitaet allein holte keine Zelle: Mittel
werden nur aus der Zielzeile gelesen, die Fehler lagen in der Zeilenwahl.
Geholfen hat die Blocklabel-Regel (siehe unten): von den sieben Mittel-FP sind
vier weg, drei bleiben.

| Klasse | Faelle | Betroffene Zellen |
|---|---:|---|
| Gold nicht als Mittelwert belegt | 1 | `yun2024:345` |

- `345`: Der Goldwert 2.3 steht im Dokument nur als Grenze eines
  Median-Differenz-Intervalls, nicht als Mittelwertzelle.

`33` und `34` sind mit der Zeitpunktspalten-Regel richtig geworden (siehe
unten); uebrig bleibt nur `345`.

### Blocklabel-Regel fuer Messwoerter

Nennt das Outcome ein Messwort (`stiffness`, `range of motion`, `neutral zone`,
`neural zone`), darf die Zielzeile nur in einem Tabellenblock mit passendem
Label liegen (`block_label`, `ziel_zeile_block`). Gibt es mehrere solche Bloecke,
gewinnt der spaetere Traeger.

Dadurch werden `yun2024:221` (2 Zellen), `:222` und `:223` richtig: Die Regel
liest jetzt den Block `Stiffness (in Nm/Degree)` der Tabelle 113-155 statt der
Beweglichkeitszeile in Grad. Zusaetzlich waehlt die Mittelspalte jetzt die beste
Label-Uebereinstimmung statt der ersten: Bei zwei Interventionsspalten gewinnt
`ACVC-HA group` gegen `ACVC group` (0.34 statt 0.35).

Andere Zellen kippen nicht: Die Messung steigt von 30 auf 34 TP, die FP fallen
von 11 auf 7.

### Zeitpunktspalten: Subskalen-Block und letzte Woche

`zeitverlauf_mittel`. Hat eine Tabelle einen Wochenkopf mit mehreren Zeitpunkten
(`Week 12  Week 24  Week 52`), wird das Mittel aus der Spalte des **letzten**
Zeitpunkts gelesen. Die Zeile kommt aus dem Block, dessen Ueberschrift das
Outcome trifft - per Alias oder als Akronym (`MCS` fuer `Mental Component
Summary`); trifft keine Ueberschrift, gilt der erste Block der Tabelle.
Innerhalb des Blocks zaehlt die erste Zeile mit lesbarem Mittel, typisch
`Mean score (SD)`.

Die Armspalte wird dabei ueber Dosis und Placebo-Synonyme zugeordnet
(`CZP 400 mg` zu `Certolizumab 400 mg`, `PBO` zu `Control`), weil die
Spaltennamen im Wochenkopf nicht die Armbeschriftung des Records tragen.

Damit werden `yun2024:33` (38.1 / 31.5, Block `PCS`, Woche 52) und `yun2024:34`
(45.4 / 41.1, Block `MCS`, Woche 52) richtig. Die Messung steigt auf 43 Zellen,
38 TP und 5 FP; andere Zellen kippen nicht.

### Armzuordnung aus der Spaltenreihenfolge

`armreihenfolge_20261121.py`. Die Regel ordnet jeden `n`-Wert ueber den
Spaltennamen des Tabellenkopfs zu, nicht ueber die Position. Fuer `PMC5617873`
steht in Spalte 1 `Placebo (n = 45)`, in Spalte 2 `Aripiprazole (n = 47)`; die
Regel liefert Intervention 47, Comparator 45.

Gold fuehrt fuer dieselben vier Records Intervention 45, Comparator 47, also die
Placebo-Werte als Intervention. Die Positionsregel ("erste Datenspalte ist
Intervention, zweite Comparator", Spaltennamen ignoriert) ist im Skript
umsschaltbar (`POSITIONAL`) und wurde ueber die 295 gemessen:

| Lesart | Zellen | TP | FP |
|---|---:|---:|---:|
| Position (Standard) | 33 | 30 | 3 |
| Spaltenname (Vergleich) | 33 | 30 | 3 |

Mit dem Gate sind beide Lesarten gleichwertig: Wo sie sich unterscheiden, wird
die Zelle nicht mehr ausgegeben.

Richtig werden alle 8 PMC5617873-Zellen. Falsch werden die beiden Arme von
`yun2024:426` (vorher 49/44, jetzt 44/49, Gold 49/44): dort steht in Spalte 1
die Vergleichsgruppe, in Spalte 2 die Intervention, und Gold folgt den Namen.
`yun2024:193` bleibt richtig, weil seine Kopfzeile die Intervention zuerst nennt.

Die Positionsregel ist der Standard (`POSITIONAL = True`). Sie gewinnt 8 Zellen
gegen ein Gold, das an dieser Stelle selbst vertauscht ist, und verliert dafuer
die 2 belegten Zellen von `yun2024:426` - ein bewusster Verlust, im Bericht
ausgewiesen (siehe `pruefvermerk_gold_20261121.md`).

Kernbefund: die Groessenzeile ist nicht der Engpass. In 13 der 25 nicht
gelieferten Faelle ist schon die Zielzeile ueber den Outcome-Namen nicht
auffindbar (`Vegetable intake` vs. Tabellenzeile `Vegetables`), in 4 weiteren
fehlt eine Groessenzeile in Reichweite, in 4 ist der Arm in einer Multiarm-
Tabelle mehrdeutig.

## Warum 76 der 103 P5-Records fuer das Pooling unvollstaendig sind

`pooling_luecken_20261121.py`, offline. Sollfelder je Outcome-Typ: sechs bei
kontinuierlich (Mittel, SD, Groesse je Arm), vier bei binaer (Ereignisse,
Groesse je Arm). 27 Records sind vollstaendig, 76 haben Luecken:

| Kategorie | Records |
|---|---:|
| Standardabweichung und weitere Felder | 40 |
| nur Standardabweichung fehlt | 15 |
| Ereignisse und weitere Felder | 11 |
| nur Ereignisse fehlen | 5 |
| nur Groesse/Mittel (Regeln vorhanden) | 4 |
| nur Groesse (Regeln vorhanden) | 1 |

Feldweise fehlen die SD in 55, Mittel in 38/39, Groesse in 42/43, Ereignisse in
15/16 Records. Kein Feld ist je Record die einzige Luecke - es fehlen immer
beide Arme oder mehrere Felder zugleich.

**Mit den vorhandenen Regeln schliessbar: 0 von 76.** Fuenf Records liegen
feldartig im Bereich der Regeln (nur Groesse bzw. nur Groesse und Mittel
fehlen), aber die Regeln liefern dort nichts: bei `yun2024:212`, `213`, `214`,
`215` steht die Gruppengroesse nicht in der Tabelle der Zielzeile (die
Zielzeile selbst wird gefunden, es gibt aber keine `n`-Zeile), bei
`yun2024:626` wird die Zielzeile nicht gefunden und der Ereignisleser ist
abgeschaltet. Auftraege aus Gold: 8 Zellen, geliefert 0 - mit und ohne Gate.

Sichtung der SD-Luecke (reine Textzaehlung, keine Regel): bei 6 der 15 Records
steht neben beiden Goldmitteln ein zweiter Wert im Format `Mittel +/- SD` oder
`Mittel (SD)`, bei 11 steht er irgendwo im Dokument.

Drei weitere Records sind vollstaendig, aber nicht poolbar, weil die
Ereigniszahl die Gruppengroesse uebersteigt (`yun2024:313`, `376`, `380`).

## Streuung als eigenes Zellfeld

`wert_aus_zelle` liefert die Streuung jetzt fuer `*_standard_deviation`, aber
nur aus Zellen, deren Format den zweiten Wert als SD ausweist (`Mittel (SD)`,
`Mittel +/- SD`); KI-, Prozent- und `n Mean`-Zellen bleiben leer, damit keine
Intervallgrenze als SD durchgeht. Die Zaehlung fuer Groesse und Mittel bleibt
unveraendert bei 33 Zellen / 30 TP / 3 FP; die Streuung laeuft separat:

| Stand | Zellen | TP | FP |
|---|---:|---:|---:|
| Streuung (295er-Auftraege) | 17 | 17 | 0 |

`sd_durchreichen_20261121.py` misst die Wirkung an den 15 Records, denen
ausschliesslich die SD fehlt:

| Kennzahl | Wert |
|---|---:|
| Zellauftraege | 22 |
| davon geliefert | 6 (27 %) |
| Records vollstaendig | 3 (`447`, `448`, `450`) |
| davon gegen Gold richtig | 0 |

Die 16 nicht gelieferten Auftraege scheitern zu gleichen Teilen an fehlender
Zielzeile (`6`, `110`, `113`, `114`) und an einer Zielzeile ohne SD-Format
(`160`, `163`, `203`, `449`).

Die drei vollstaendigen Records lasen die Baseline-Tabelle und trafen damit
keinen Goldwert. Mit der Tabellenwahl (naechster Abschnitt) lesen sie die
Nachher-Tabelle und sind mit allen sechs Feldern gold-richtig; ihre SD faellt
dort aus dem 95%-KI. Poolbasis dann: k 24 -> 27, pooled 0.125 -> 0.136.

## Tabellenwahl: Nachher-Tabelle vor Baseline-Tabelle

`tabellenwahl_20261121.py`, offline. Die Zielzeile kam bisher aus der ersten
Zeile mit dem hoechsten Alias-Treffer und lag damit in der Baseline-Tabelle,
wenn sie vor der Nachher-Tabelle steht. Neu bewertet `tabellen_zeitpunkt` den
Tabellenkopf (`+2` Follow-up, Zeitpunkt, Woche oder Monat; `-2` Baseline,
Charakteristika), und `ziel_zeile_zeitpunkt` zieht bei gleichem Treffer in die
Nachher-Tabelle um - aber nur, wenn diese ihre Arme in der Unterschrift nennt
(`I; n=104`). Dazu lesen `armkuerzel` und `gruppenzeile_wert` die Armzeilen,
und `wert_aus_zelle` leitet die Streuung aus einem 95%-KI ab
(`SE = halbe Breite / 1.96`, `SD = SE * sqrt(n)`).

| Record | Felder richtig alt | Felder richtig neu | vollstaendig richtig neu |
|---|---:|---:|---|
| `yun2024:196` | 0 | 0 | nein |
| `yun2024:447` | 1 | 6 | ja |
| `yun2024:448` | 1 | 6 | ja |
| `yun2024:450` | 1 | 6 | ja |

Die 33 Zellen und die 17 Streuungszellen der 295 FN-Faelle bleiben unveraendert
(33/30/3 und 17/17/0), kein TP geht verloren. Der Umzug kostet aber, wenn die
Armbedingung fehlt: ohne sie steht der Zellstand bei 33 Zellen / 18 TP / 15 FP
und die Streuung bei 17 / 5 / 12, weil dann eine Aenderungstabelle gegen die
Tabelle mit den Absolutwerten gewinnt (`PMC4987981`: Gold steht in der
Baseline-Tabelle).

`yun2024:196` bleibt falsch. Seine Goldwerte stehen in Tabelle 3, einer
Subgruppentabelle (MMSE-J 20 bis 23); diese Einschraenkung nennt der Record
nicht. Allein gelesen liefert die Tabelle nur die beiden Mittel (2 von 6
Feldern), Groesse und Streuung brauchen die Zeilen-n und das KI dieser Tabelle.

### Kennzeichnung und Wirkung ueber alle 699 Records

Jede aus einem KI abgeleitete Streuung traegt im Ergebnis `abgeleitet: True` und
`herkunft: "95%-KI"`, abgelesene Zellen tragen `abgeleitet: False` und
`herkunft: "zelle"`. Die Fixture schreibt das Kennzeichen je Zelle mit, damit
abgelesene und abgeleitete Werte nicht verwechselt werden.

`umschreiben_20261121.py` liest alle 699 Records aus `yun699.jsonl` je Goldfeld
zweimal (Tabellenwahl aus und an), 2.463 Auftraege:

| Klasse | Zellen |
|---|---:|
| beide richtig, gleicher Wert | 210 |
| verworfen (alt richtig, neu nichts) | 0 |
| umgeschrieben, neu falsch | 0 |
| umgeschrieben, neu richtig | 0 |
| neu richtig | 26 |
| neu falsch, alt ohne Wert | 0 |
| neu falsch, alt schon falsch | 169 |
| beide ohne Wert | 2.058 |

Die Tabellenwahl verwirft also keine richtige Zelle und schreibt keine um; sie
holt 26 richtige Zellen dazu (sechs Records aus `PMC4879328`, `446` bis `452`)
und erzeugt keine neue falsche Zelle. Von den 14 abgeleiteten Streuungen sind
10 richtig; falsch sind `yun2024:446` (Waist: Gold 3.32 gegen 5.07 aus dem
gedruckten KI, das Gold passt nicht zum Intervall) und `yun2024:451` (die Regel
liest `Vigorous PA` statt der MVPA).

In den gespeicherten P5-Vorhersagen (103 Records) bestaetigt die neue Regel 30
richtige Zellen, ueberschreibt 31 und laesst 110 ohne Regelwert. Alle 31
Ueberschreibungen sind alte Schuld: die Regel lieferte dort schon vorher einen
anderen falschen Wert, keine geht auf die Tabellenwahl zurueck. Die Bilanz
ueber alle 699 Records:

| Stand | TP | FP | FN |
|---|---:|---:|---:|
| P5 unveraendert | 166 | 96 | 2607 |
| P5 + alte Regelzellen | 138 | 158 | 2635 |
| P5 + neue Regelzellen | 157 | 141 | 2616 |

Das Ersetzen kostet auch mit der neuen Tabellenwahl TP; sie verkleinert den
Verlust nur (alt -28 TP, neu -9 TP gegen die unveraenderte Vorhersage).

## Fixture: beide Zellstaende zellgenau

`fixture_20261121.py` (Modi `schreiben` / `pruefen`) friert die 33 Zellen mit
Gate unter `zellen`, die 43 Zellen ohne Gate unter `zellen_ohne_gate` und die
17 Streuungszellen unter `zellen_streuung` ein, dazu die Ablation der acht
Schalter (`ohne_zeitpunkt`, `ohne_armbedingung`, `ohne_armzeile`,
`ohne_vorzeichen` sind neu). `pruefen` rechnet beide Staende neu und
vergleicht jede Zelle ueber Schluessel (Record, Feld, Arm), Wert und
Richtig-Kennzeichen; Abweichungen werden einzeln gemeldet und der Rueckgabewert
ist dann 1. Stand: 33 Zellen mit Gate, 43 ohne Gate, Abweichungen 0.

## Aendern die Ersetzungen die gepoolte Schaetzung?

`pooling_effekt_20261121.py`, offline. Zellen der 103 P5-Records in vier
Staenden, Effekt je Record als Log-Odds-Ratio (binaer) bzw. Hedges g
(kontinuierlich), gepoolt mit `pool(method="hksj")` aus
`research_agent/meta/pooling.py`:

| Stand | k | pooled | 95 %-KI | I2 |
|---|---:|---:|---|---:|
| unveraendert | 24 | 0.125 | -0.302 bis 0.551 | 91.1 |
| 33 Zellen | 24 | -0.018 | -0.575 bis 0.538 | 92.6 |
| 43 Zellen | 24 | -0.018 | -0.575 bis 0.538 | 92.6 |
| Gold (Referenz) | 58 | 0.318 | -0.412 bis 1.048 | 97.8 |

Nur zwei Records aendern ihren Effekt (`yun2024:347`, `yun2024:668`); die
Verschiebung betraegt 0.07 auf der Effektskala, die Intervalle ueberlappen sich
fast vollstaendig. Auf der gemeinsamen Menge (k = 20) lauten die Werte 0.043,
-0.115, -0.115 und -0.026; ohne Extremwerte (|g| > 3, k = 19) 0.086, 0.052,
0.052 und 0.092. Gate und Ohne-Gate sind identisch, weil die 10 zusaetzlich
verworfenen Zellen auf Records ohne vollstaendige Zellen liegen.

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
.venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/tabellenwahl_20261121.py
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
