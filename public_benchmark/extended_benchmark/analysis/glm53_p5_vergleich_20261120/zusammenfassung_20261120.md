# P5 gegen GLM-5.3: Gesamtstand 20.11.2026

Zusammenfassung aller Berichte, Offline-Auswertungen und Messlaeufe des Tages.
Quellen sind die Einzelberichte im selben Verzeichnis; jede Zahl dort ist aus
Predictions, Gold oder Dokumenttext nachgerechnet. Kein Modellaufruf fuer diese
Zusammenfassung, keine Prediction, kein Gold und kein Test veraendert.

## 1. Fragestellung und Grundgesamtheit

Der Lauf `runs/yun699_p5_24000_20261118` (`gwdg/glm-5.3`, Budget 24.000,
Prompt `v2_timepoint`) bearbeitet **103 Records** - genau die, die der
8.000er-Referenzlauf `yun699_8000_alle_20261117` mit
`length_ohne_ergebnis` verloren hatte. Ergebnis: 70 Records mit Antwort,
**33 Records ohne Inhalt** (`content_chars = 0`, `finish_reason = length`,
`http_status = 200`, `parse_error = kein_json`).

Die 33 sind also 33 von 103, nicht 33 von 699. Die 699 sind der
Gesamtdatensatz mit 2.773 Goldzellen.

## 2. Benchmark-Kennzahlen

Bewertung mit der P5-Logik (Schluessel Feld **und** Arm, 1:1-Verbrauch,
Dubletten und Fremdschluessel sind FP).

| Grundgesamtheit | System | TP | FP | FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| 699 Records | GLM 5.3 | 1.844 | 410 | 929 | 0,8181 | 0,6650 | 0,7336 |
| 596 Records (ohne P5-Auswahl) | GLM 5.3 | 1.844 | 410 | 506 | 0,8181 | 0,7847 | 0,8010 |
| 559 Zeilen mit Zellen | GLM 5.3 | 1.844 | 410 | 462 | 0,8181 | 0,7997 | **0,8088** |
| 103 Records (P5-Auswahl) | GLM 5.3 | 0 | 0 | 423 | n. def. | 0,000 | 0,000 |
| 103 Records (P5-Auswahl) | P5 | 170 | 101 | 253 | 0,6273 | 0,4019 | 0,4899 |
| 102 bewertbare Records | P5 | 170 | 97 | 253 | 0,6367 | 0,4019 | **0,4928** |
| Hybrid (596 + 102) | GLM + P5 | 2.014 | 507 | 759 | 0,7989 | 0,7263 | **0,7609** |

- `yun2024:653` hat keine Goldzellen und geht in die 102er-Zahlen nicht ein.
- Der dokumentierte Wert 0,493 entsteht aus gerundeten 0,637 und 0,402; exakt
  sind es 0,4928.
- Hybrid gegen GLM allein: **+170 TP, +97 FP, −170 FN, +6,1 Punkte Recall,
  +2,7 Punkte F1, −1,9 Punkte Precision**. Das ist der belastbare Beitrag von
  P5: es schliesst eine Luecke, in der die Referenz nichts lieferte.

### 2.1 Vier GLM-Zahlen im Umlauf

| Wert | Grundgesamtheit | Logik |
|---|---|---|
| F1 0,8088 | 559 Zeilen mit Zellen | P5 |
| F1 0,8313 | dieselben 559 | Yun-699 |
| F1 0,7519 | alle 699 | Yun-699 |
| F1 0,7336 | alle 699 | P5 |

Die Kurzform "GLM erreicht etwa 0,80" meint die guenstigste Variante: Sie
laesst 37 Zeilen ohne Zelle und die 103 Budgetabbrueche aus dem Nenner.

### 2.2 Zerlegung der Spanne 0,809 gegen 0,493

| Schritt | F1 | Aenderung | Ursache |
|---|---:|---:|---|
| Dokumentierter Referenzwert | 0,8088 | - | 559 Zeilen mit Zellen |
| gleiche Logik, alle 699 | 0,7336 | −0,0752 | 140 Zeilen ohne Antwort im Nenner |
| gleiche Logik, nur die 103 | 0,0000 | −0,7336 | GLM liefert dort keine Zelle |
| P5 auf denselben 103 | 0,4928 | +0,4928 | P5 beantwortet 67 der 103 |

Die Spanne ist damit vollstaendig erklaert; es bleibt kein Rest fuer
"GLM besser" oder "P5 schlechter". Die Record-Mengen sind disjunkt
(Schnittmenge 0).

## 3. Recordanalyse der P5-Auswahl

| F1-Bereich | Records |
|---|---:|
| 0,0 (kein TP) | 44 |
| 0,2 | 2 |
| 0,3 | 6 |
| 0,4 | 2 |
| 0,5 | 7 |
| 0,6 | 1 |
| 0,7 | 12 |
| 0,8 | 12 |
| 1,0 (perfekt) | 16 |
| Summe | 102 |

Von den 44 Records ohne TP haben 33 keine Antwort, 3 eine Antwort ohne Zellen
und 8 Zellen ohne richtigen Wert (`113`, `357`, `362`, `533`, `615`, `616`,
`626`, `686`).

### 3.1 Fehlerzerlegung

| Kategorie | Zellen | Anteil |
|---|---:|---:|
| Fehlende Extraktion (FN) | 181 | 71,5 % |
| davon 33 Records ohne Antwort | 132 | 52,2 % |
| Falscher Wert (FN) | 68 | 26,9 % |
| Armverwechslung (FN) | 4 | 1,6 % |
| Mehrfach-/Falschwertzelle (FP) | 80 | 82,5 % |
| Fremdschluessel (FP) | 17 | 17,5 % |
| Falsche Feldzuordnung (FP) | 0 | - |

Auf den 67 antwortenden Records sind 170 von 291 Goldzellen getroffen -
**58,4 %**. Das ist die Qualitaet dessen, was P5 tatsaechlich ausgibt.

### 3.2 Drei Belege im Wortlaut

- `yun2024:113`: Gold 456/459, P5 459/456 - Arme vertauscht, Zellen vollstaendig.
- `yun2024:686`: Gold 17/17, P5 34/34 - Gesamtzeile statt Armzeilen.
- `yun2024:357`: Gold 13/13, P5 21/20 - andere Auswertungsgruppe.

Gemeinsames Muster: P5 findet Zahlen und ordnet sie der falschen Zeile, dem
falschen Zeitpunkt oder dem falschen Arm zu. **Bindungsproblem, kein
Erkennungsproblem.**

## 4. Diagnose der 33 Abbrueche

### 4.1 Die 13 Faelle ohne Strukturhypothese

| Kennzahl | ohne Struktur (13) | mit Struktur (20) | Erfolge (67) |
|---|---:|---:|---:|
| Reasoning-Zeichen, Median | 93.380 | 95.202 | 31.444 |
| Prompt-Zeichen, Median | 7.811 | 26.295 | 17.103 |
| Reasoning je Textzeichen | **13,2** | 3,8 | 2,1 |
| Datenzellen, Median | 20 | 107,5 | 60 |
| ohne Tabelle mit Zielfeld | 13 | 11 | 51 |
| ohne parsebare Tabelle | 6 | 0 | 9 |

Die Gruppe mit den wenigsten Daten und dem kuerzesten Prompt verbraucht das
meiste Reasoning. "Zu viel Text" ist als Ursache ausgeschlossen, ebenso
Prompt-Redundanz (Aufschlag in allen Gruppen rund 1.010 Zeichen).

### 4.2 Nicht deterministisch

Fuenf der 13 haben in der Nachzug-Zeile des Referenzlaufs mit demselben Budget
Zellen geliefert: `128` (16.857), `356` (24.000 + 801 Repair), `557` (22.137),
`559` (14.534), `624` (12.805). Eine pauschale Budgeterhoehung verschiebt die
Grenze, nicht das Verhalten.

### 4.3 Der P5-Ausschnitt war nie zu kurz

`run_extended_extraction.py` liest das Dokument vollstaendig und setzt es als
`text[:45000]` ein. Kein Dokument der 33 ist laenger als 42.606 Zeichen
(groesstes: `671`/`672`/`673`/`674`). P5 sah also in allen 33 Faellen das
**ganze Dokument**; bei **19 von 33** standen alle Goldwerte im Prompt, und der
Lauf brach trotzdem ab. Die These "Beschneidungsproblem" ist fuer P5 widerlegt.

### 4.4 Zwei Textformen, kein Tabellengitter

| Klasse | Records |
|---|---:|
| Prosa, mehrere Wertepaare im Satz (523-Muster) | 17 |
| kein Goldwert im Text (nur Caption/Bildplatzhalter) | 16 |
| Tabellenzeile | 0 |
| Prosa, ein Paar | 0 |

In **allen 33 Dokumenten gibt es 0 Pipe-Zeilen**. Wo Werte im Text stehen,
stehen sie in Kommalisten ohne Zeilenlabel (17 von 17). Ein Prompt, der ein
Zeilenlabel verlangt, hat dort nichts zu zitieren - das Modell sucht, bis das
Budget aufgebraucht ist, statt `found: false` zu sagen.

## 5. Offline-Messungen

### 5.1 Fensterlage (6.000 Zeichen)

| Groesse | Wert |
|---|---:|
| Records | 33 |
| Goldwerte gesamt (verschieden je Record) | 118 |
| davon im Volltext auffindbar | 92 |
| davon nicht im Text | 26 |
| im aktuellen Fenster sichtbar | 67 |
| Orakel: bestes einzelnes 6.000er-Fenster | 91 |
| drei Stuecke zu 2.000 Zeichen | 72 (24 Records mit >= 2 Werten) |
| Records ohne Goldwert im Fenster | 6 (`159`, `164`, `624`, `625`, `685`, `687`) |

Der Engpass ist die Startregel, nicht die Breite: nur ein Wert passt in kein
6.000er-Fenster. Drei der sechs Records ohne Wert im Fenster (`164`, `624`,
`625`) haben gar keinen Goldwert im Text; dort hilft nur eine andere
Dokumentaufbereitung.

### 5.2 Fundstellen-Audit

| Etikette | Werte |
|---|---:|
| Ergebnisteil, Text | 64 |
| Ergebnisteil, eingeflachte Tabelle | 23 |
| Abstract | 2 |
| Diskussion | 2 |
| Zitat- oder Verweisnummer | 1 |
| nirgends | 26 |
| Summe | 118 |

- Belastbar im Ergebnisteil: **87**.
- Genau **ein** Textfund ist eine Verweisnummer: `152`, "Figure 7".
- Auf der belastbaren Menge bleibt der Abstand Fenster gegen Orakel:
  **56 gegen 85** (statt 67 gegen 91).

### 5.3 Dublettenfilter (goldfrei, 0 Tokens)

| Variante | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| unveraendert | 170 | 97 | 253 | 0,6367 | 0,4019 | 0,4928 |
| eine Zelle je Feld+Arm | 170 | 88 | 253 | 0,6589 | 0,4019 | 0,4993 |
| goldinformierte Obergrenze | 170 | 88 | 253 | 0,6589 | 0,4019 | 0,4993 |

9 Zellen in 5 Records entfernt, +0,65 Punkte F1. Mehr gibt der Filter nicht
her, weil 67 der 97 falschen Zellen einzelne Falschwerte sind.

### 5.4 Zuordnung der 67 einzelnen Falschwertzellen

| Klasse | Zellen |
|---|---:|
| reine Zuordnung (Feld/Arm) | 4 |
| Wert steht im Text, gehoert zu keinem Goldslot | 63 |
| Wert steht so nicht im Text | 0 |

Eine reine Zuordnungsregel bringt hoechstens +0,87 Punkte F1 (TP 170 -> 173).
Die 63 Textfaelle brauchen eine Zeilen- oder Zeitpunktregel, keine
Zuordnungsregel. Jede Bestaetigung traegt ihre Fundstelle im JSON.

### 5.5 Trennzeichen-Audit

6 von 7 dynamisch geprueften Zahlparsern lesen mindestens einen Teststring
falsch (`7.69` -> 769 bzw. `1.234,5` unlesbar), darunter
`gemeinsam.als_zahl`, `werte_p5_aus.zahl`, `vergleiche.zahl`,
`baue_yun699.zahl`, `precheck_gold`, `pruefe_extraktion.zahl`. Nur
`arm_level.parse_number` liest alle sieben Teststrings korrekt. 45 statische
Fundstellen im Repo sind dokumentiert. Die Zahlen dieser Analyse sind davon
nicht betroffen; der Falschwert-Bericht wurde nach der Verschaerfung neu
gerechnet, alle 63 Textbelege blieben bestaetigt.

## 6. Online-Messungen

Modell `gwdg/qwen3.5-397b`, Temperatur 0, Abbruch bei `content_chars == 0` oder
`finish_reason = length`, sofern nicht anders vermerkt.

| Spur | n | Ergebnis | Tokens |
|---|---:|---|---:|
| Tabellenanker Fassung 1 (`559`) | 1 | `ok`, falsche Tabelle, 0 TP / 2 FP | 16.632 |
| Tabellenanker Fassung 2 (`559`, `615`) | 2 | beide Budgetabbruch, 0 Zeichen | 88.632 gesamt |
| Dreifenster-Serie (`30`, `673`, `674`) | 3 | alle `ok`, 0 von 3 zitieren das Goldmittel | 21.638 |
| Tabelle+Prosa (`30`) | 1 | falsche Zeile `Mean change from BL`, 6/6 sichtbar | 8.174 |
| Gegenprobe ohne Prosa (`30`) | 1 | erneut `Mean change`, Confound ausgeraeumt | 7.589 |
| Zeilenbindungs-Regel (`30`) | 1 | richtige Zeile, Caption, `Week 52` | 8.003 |
| Stufe 2 auf dem Zeilen-Locator (`30`) | 1 | 6 Zellen, **TP 6 / FP 0 / FN 0, F1 1,0** | 3.262 |
| Kette auf 5 Records | 5 | 420 F1 0,8; 421 F1 0; 582/671/672 `found: false` | 32.162 |
| Kopf-Vorstufe auf 5 Records | 5 | 582 F1 1,0 ohne Modell; uebrige vier ohne Kopfzelle | 39.153 |
| Kopf-Modus-Versuche (`582`) | 2 | beide `found: false` | 5.030 + 5.501 |

Weitere Einzelpunkte derselben Spur:

- **523** mit glm: 2.342 + 268 Tokens, 4 Zellen, **F1 0,800**.
- **420** mit qwen: Stufe 1 7.728 Tokens, Stufe 2 2.590 Tokens, 4 Zellen,
  **F1 0,800** (Deckel: Gruppengroessen 18/21 fehlen im Ausschnitt).
- **52** mit qwen: Stufe 2 2.827 Tokens, 2 Zellen, **2 TP / 0 FP / 4 FN,
  F1 0,500**; Armrichtung aus "from 11.5% to 13.6%" korrekt.
- **421** mit qwen: 10.686 Tokens, **`found: false`** (falsches Negativ).
- **119** mit qwen: Budget 4.000 Abbruch; Budget 8.000 `ok`, **0 Zellen**
  (der Satz druckt Anteile, das Gold verlangt `mean`).

### 6.1 Was der 30er-Record zeigt

Die Kette ist dort vollstaendig: Tabellenfenster loest die Abdeckung (6/6
statt 2/6), der Zeilenbindungs-Block waehlt die Goldzeile `Mean score (SD)`,
Stufe 2 liest den Block `Week 52`, F1 1,0. Kosten 8.003 + 3.262 = 11.265
Tokens. Ohne den Regelblock waehlte dasselbe Modell zweimal die
Aenderungszeile - die falsche Zeile ist modellseitig, nicht vom Prosastueck
geprimt.

### 6.2 Warum die Kette nicht in die Breite traegt

- **421**: derselbe Satz nennt zwei Schnittstellen mit je zwei Paaren; gebunden
  wird erneut das erste Paar. Fehler bei der Bindung, nicht beim Lesen.
- **582**: Goldwert ist die Gruppengroesse (16/16) im Tabellenkopf, nicht die
  `Mean (SD)`-Zeile.
- **671/672**: Gruppengroessen nur im Abstract (Position 1.018) und in einem
  Spaltenkopf bei 5.347, beide ausserhalb des Ergebnisteils. Strukturell
  unerreichbar mit dem aktuellen Ausschnitt.
- **420**: erreicht mit 0,8 genau den Deckel des Ausschnitts.

## 7. Kopf-Parser und Satzauswahl

### 7.1 Kopf-Parser mit Arm und Untergruppe

`kopf_parser_20261120.kopf_parse` liest jede Kopfzelle einzeln, zieht die
Untergruppe aus dem Text vor der Klammer und verteilt die Zellen gleichmaessig
auf die Arme. Fuer 582:

```
Positive ABM       Neutral ABM
Faces (*n* = 16)   Words (*n* = 16)   Faces (*n* = 14)   Words (*n* = 15)   *p*
```

| Lesart | Werte | TP | FP | FN | F1 |
|---|---|---|---:|---:|---:|---:|
| `erste_zwei` | 16, 16 | 2 | 0 | 0 | **1,0** |
| `je_arm` | 16, 14 | 1 | 1 | 1 | 0,5 |
| `untergruppe` | 16, 14 | 1 | 1 | 1 | 0,5 |

Der 1,0-Wert haengt an `erste_zwei`, also an den zwei Zellen des
`Positive ABM`-Blocks. Sobald die Arme getrennt gelesen werden, steht 16 gegen
14. Warum Gold 16/16 verlangt, obwohl der Kopf vier Zellen fuer zwei Arme
druckt, ist aus dem Dokument nicht ableitbar. Alle drei Lesarten werden im
Kettenlauf und als `vorstufe_varianten_f1` im JSON ausgegeben.

### 7.2 Satzauswahl der Stufe 1 (10 gespeicherte Faelle)

| Record | Paar | fehlender Unterscheider | Urteil |
|---|---|---|---|
| `420` (2x) | ja | `Cervicothoracic` | Paar richtig, nicht eindeutig |
| `421` | ja | `thoracolumbar` | Paar richtig, nicht eindeutig |
| `523` | ja | `results` | Paar richtig, nicht eindeutig |
| `30`, `673`, `674` | nein | - | richtiger Satz lag vor, nicht genommen |
| `119`, `52` | nein | - | kein brauchbarer Satz im Ausschnitt |

Bilanz: **5** richtiges Paar ohne Unterscheider, **3** richtiger Satz nicht
gewaehlt, **2** ohne brauchbaren Satz, **0** "richtig und eindeutig".

**Korrektur einer frueheren Aussage:** 421 band nicht den falschen Satz. Der
Satz `Regarding quantitative assessment of contour sharpness ...` ist der
richtige und enthaelt alle vier Paare; es fehlt nur das Wort `thoracolumbar`,
deshalb ist er zwischen 420 und 421 nicht unterscheidbar. Die Aussage in
`kette_vorstufe_20261120.md` ist damit ueberholt.

## 8. Kosten

| Posten | Completion-Tokens |
|---|---:|
| bis Record 30 einschliesslich Ankerspur (88.632) und qwen-Spur bis 52 | 209.937 |
| Kette auf 5 Records | 32.162 |
| Kopf-Modus-Versuch 1 (`582`) | 5.030 |
| Kopf-Modus-Versuch 2 (`582`) | 5.501 |
| Kettenlauf mit Kopf-Vorstufe | 39.153 |
| **Summe der Reihe** | **291.783** |

## 9. Was belegt ist und was offen bleibt

Belegt:

- Die 0,809/0,493-Spanne ist ein Auswahl- und Grundgesamtheitsartefakt, kein
  Qualitaetsunterschied; P5 liefert dort als einziges System Treffer.
- Die 33 Abbrueche sind Nicht-Antworten, nicht Denkfehler bei der Extraktion;
  52 % der FN stammen aus ihnen.
- Der P5-Ausschnitt war nie zu kurz; der Abbruch ist eine Denkschleife ueber
  vorhandenem Material.
- Die Zeilenbindung ist per Prompt loesbar (30, F1 1,0), die Stufe 2 ist der
  billige Teil (268-3.262 Tokens).
- Kopfzahlen sind ohne Modell extrahierbar (582: 16/16 ohne Aufruf).
- Dublettenfilter und Zuordnungskorrektur sind gratis, aber klein
  (+0,65 bzw. +0,87 Punkte F1).

Offen:

- 671/672 strukturell unerreichbar (Kopfzahlen ausserhalb des Ergebnisteils).
- 421 scheitert an der `found`-Entscheidung, 119 an der
  Gold-Feldbezeichnung (`mean` gegen gedruckten Anteil).
- Der Tabellenanker ist nur an n = 2 gemessen und dort ohne Gewinn; fuer die
  uebrigen 11 der 13 Faelle unbelegt, nicht widerlegt.
- Der Kopf-Parser greift nur bei 582; 420/421/671/672 haben im Tabellenstueck
  keine Kopfzelle.
- Die Satzauswahl ist an 10 gespeicherten Faellen geprueft, nicht
  repraesentativ fuer die 33 leeren Records.

## 10. Empfehlung fuer den naechsten Schritt

1. **Satz-Locator um die Unterscheider-Pflicht erweitern**: Wird ein Satz
   gewaehlt, muss er (oder der direkt folgende) die Regions- bzw.
   Outcome-Angabe tragen, sonst ist die Zeile zu nehmen. Das adressiert 420,
   421 und 523 zugleich, kostet 0 Tokens und ist gegen die 10 gespeicherten
   Faelle offline pruefbar (`satzauswahl_20261120.py` erweitern).
2. **Erst danach** ueber einen weiteren Netzlauf entscheiden (Freigabe noetig,
   maximal 2-3 Aufrufe), vorzugsweise auf 420/421/523 mit dem neuen Locator.
3. **Berichtsregel**: Ab jetzt die 699er-Zahl mit allen Ausfaellen im Nenner
   als Headline, die 559er-Zahl nur als Diagnose, und den Hybrid getrennt
   ausweisen.

Nicht empfohlen: weitere Anker-Aufrufe vor der Zweistufigkeit, weitere
Prompt-Fassungen auf 420/421 (4 von 4 Zellen brachen ab), eine pauschale
Budgeterhoehung und eine Aenderung des Goldstandards.
