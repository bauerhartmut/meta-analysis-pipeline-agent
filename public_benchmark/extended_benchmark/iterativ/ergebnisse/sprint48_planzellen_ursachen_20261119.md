# Sprint 48: Ursachen der 26 wertabweichenden Planzellen

Grundlage: `pruefe_armbindung_sprint48.py` (Plan-Auswahl ueber `load_tables`),
Stand `offline_struktur_20261118b/structure.json`. Rein lesend, keine
Netzaufrufe. Die 26 Zellen sind die Kopftreffer, deren Wert nicht zum Goldwert
passt; **68 von 94** Feldtreffern bleiben damit nicht widerlegt (Obergrenze,
Zeilenzellen und Messwerte ungeprueft).

## 1. Aufteilung

| Ursache | Zellen | Records |
|---|---:|---|
| Untergruppe oder geteilter Arm im selben Tableau | 17 | 78, 79, 172, 174, 265, 266, 426, 531, 532, 645, 647 |
| Goldwert steht in einer anderen Tabelle (andere Population) | 5 | 185, 194, 196 |
| Arm-/Spaltenfehlbindung | 4 | 335, 336, 678, 682 |
| **Summe** | **26** | 18 Records |

Die Ursachenpruefung deckt keine der 26 Zellen auf; die Zahl 68 bleibt
unveraendert. Das nachgezogene Skript weist 44 Kopftreffer mit Wert und Arm,
4 mit dem Wert des anderen Arms (`arm_vertauscht`: 335, 336, 678, 682) und 22
mit abweichendem Wert aus; die Bandpruefung aller 114 Kopfangaben ergibt 110
ok, 0 gemischt, 0 falsch und 4 ohne Arm. Die falschen Spaltenarme (426, 678)
sitzen in der Spaltenzuordnung selbst und sind damit nicht ueber die
Bandkonsistenz auffindbar. Die Aufteilung aendert aber die Diagnose: es sind nicht
26 gleichartige "Untergruppenfaelle", sondern 5 armfalsche Zellen und 5
Zellen, deren Beleg in einem anderen Tableau steht.

## 2. Alle 26 Zellen

| Record | Feld | Gold | Plan-Tabelle | gedruckt | Ursache |
|---|---|---:|---|---|---|
| `yun2024:78` | intervention | 30 | T4 | Palmvitee n = 3 / 19 / 8 (Perioden S1-S3) | Untergruppe je Periode; 30 ist die randomisierte Zahl, nicht im Kopf |
| `yun2024:79` | intervention | 30 | T4 | wie 78 | dito |
| `yun2024:172` | intervention | 33 | T1 | Metformin 17, Sitagliptin 16 | Interventionsarm geteilt; Summe 33 nicht gedruckt |
| `yun2024:174` | intervention | 33 | T1 | wie 172 | dito |
| `yun2024:185` | comparator | 28 | T1 | Placebo 33 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:194` | intervention | 169 | T1 | Pls 145 | analysierte vs randomisierte Kohorte; 169 steht in T6 |
| `yun2024:194` | comparator | 167 | T1 | Placebo 140 | dito |
| `yun2024:196` | intervention | 24 | T6 | Pls 169 | Gold aus T3/T5 (Mittel 1,29); T6 ist die Baseline-Kohorte |
| `yun2024:196` | comparator | 24 | T6 | Placebo 167 | dito |
| `yun2024:265` | intervention | 83 | T1 | 30 ug 81, 60 ug 78 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:265` | comparator | 79 | T1 | Placebo 78 | dito |
| `yun2024:266` | intervention | 80 | T1 | 30 ug 81, 60 ug 78 | dito |
| `yun2024:266` | comparator | 79 | T1 | Placebo 78 | dito |
| `yun2024:335` | intervention | 45 | T2 | Aripiprazol 47 -> intervention | Arme gegen Gold vertauscht: Gold fuehrt 45 als intervention (Placebo), 47 als comparator |
| `yun2024:336` | intervention | 45 | T2 | wie 335 | dito |
| `yun2024:426` | comparator | 44 | T4 | n = 18, n = 30 -> comparator | Untergruppen 18/21/30/34; die P-Wert-Spalte steht zusaetzlich falsch auf comparator |
| `yun2024:531` | intervention | 289 | T3 | 298 / 307 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:531` | comparator | 204 | T3 | 214 | dito |
| `yun2024:532` | intervention | 283 | T1 | 298 / 307 | dito |
| `yun2024:532` | comparator | 204 | T1 | 214 | dito |
| `yun2024:645` | intervention | 27 | T1 | Iodine 29 | Wert nicht im Kopf; Population weicht ab (nicht belegt) |
| `yun2024:645` | comparator | 26 | T1 | Placebo 30 | dito |
| `yun2024:647` | intervention | 27 | T1 | Iodine 29 | dito |
| `yun2024:647` | comparator | 26 | T1 | Placebo 30 | dito |
| `yun2024:678` | intervention | 16 | T2 | n = 15 -> intervention | Spaltenarm falsch: 15 steht ueber Antibiotic, Gold will 15 als comparator |
| `yun2024:682` | intervention | 16 | T2 | n = 15 -> intervention | dito |

## 3. Der Verdacht zu yun2024:196

`yun2024:196` ist **kein** Fall wie 678. In T6 sind die Spalten korrekt den
Armen zugeordnet (intervention, comparator) und die Kopfangaben `n = 169` /
`n = 167` passen zu diesen Spalten; T6 ist eine Baseline-/Ereignistabelle der
Gesamtkohorte (Zeilen u. a. Karzinomarten mit 0/1). Der Goldwert 24/24 und die
Mittelwerte 1,29 / 1,08 stehen in T3 bzw. T5, nicht in T6. Die Zelle ist damit
eine **Tabellen-/Populationsverwechslung**: der Plan liest die Kohortengroesse
aus dem falschen Tableau, nicht einen falsch gebundenen Arm.

Bei `yun2024:194` ist es dasselbe Muster: T1 traegt die analysierten 145/140,
Gold nutzt die randomisierten 169/167 aus T6.

## 4. Skript-Review (frischer Blick, Zahlen unveraendert)

Gelesen: `public_benchmark/extended_benchmark/yun_full/pruefe_armbindung_sprint48.py`,
304 Zeilen. Keine Zahl und kein Ergebnis geaendert. Befunde:

1. **Bandpruefung fehlt.** Der Docstring verspricht "sitzt das Kopfband ueber
   Spalten desselben Arms?", aber `band_arme()` wird nur in `details` abgelegt
   und nie ausgewertet. Zwei falsche Spaltenarme (426, 678) blieben deshalb
   unentdeckt.
2. **"wertgedeckt" ist zu stark.** Die 68 zaehlen Zeilenzellen und alle
   Nicht-Gruppenfelder ungeprueft mit; korrekt waere "nicht durch eine
   wertabweichende Kopfangabe widerlegt".
3. **Armvertauschung wird als Wertabweichung verbucht.** `wert_ohne_arm` prueft
   nur Zellen, deren Wert schon passt; 335/336 (47 auf intervention statt
   comparator) erscheinen als `wert_abweichend`. Eine Klasse "Arm vertauscht"
   fehlt.
4. **Keine Abstimmung mit dem Artefakt.** Es fehlt die Zusicherung
   `summe['feldtreffer_gesamt'] == structure['gold_reachable']` (94). Wird
   `structure.json` neu erzeugt, aendert sich die Bezugsgroesse still.
5. **Absoluter Auswahlpfad.** `struktur['selection']` ist ein absoluter Pfad;
   auf einem anderen Rechner oder Checkout bricht das Skript ab.
6. **Tautologie in Abschnitt 3.** `Feld erreichbar = z['field'] in {...}` ist
   immer wahr, weil `z` aus derselben Liste stammt.
7. **Sortierung und Casts.** `sorted(records)` sortiert lexikografisch (`682`
   vor `78`); `int(z['value'])` schneidet nicht-ganzzahlige Groessen ab.
8. **Leere Auswahl wird stillschweigend hingenommen.** Ein Record ohne
   Auswahlzeile traegt 0 bei, ohne Warnung.

Punkte 1, 3 und 4 sind inzwischen umgesetzt: das Skript weist je Kopfangabe
einen Bandstatus aus, fuehrt die Klasse `arm_vertauscht` und bricht ab, wenn die
Summe nicht zu `gold_reachable` passt. Die Bezugsgroesse (94) ist unveraendert.

Hinweis: Wo "Population weicht ab (nicht belegt)" steht, ist die Zuordnung
(randomisiert vs analysiert) aus dem Markdown nicht sicher belegbar; belegt ist
nur, dass der Goldwert nicht im Kopf der gewaehlten Tabelle steht. Die
Summenprobe belegt dagegen 78 (3+19+8 = 30) und 172/174 (17+16 = 33).

## 5. Spaltenzuordnung 426 und 678: was der Tabellenkopf belegt

Geprueft rein offline aus den Plan-Tabellen und dem Record-Kontext
(`intervention` / `comparator`), ohne Umbau des Artefakts.

### yun2024:678 (und 682, gleiche Tabelle)

| Quelle | Beleg |
|---|---|
| Kontext | intervention = **antibiotic**, comparator = **placebo** |
| Kopf | `Probiotic group` (Spalten 1-5) traegt zweimal `(n=16)`; `Antibiotic group` (6-10) traegt `(n=15)`; `Placebo group` (11-15) traegt **kein** n |
| Plan-Arme | Antibiotic -> intervention, Placebo -> comparator (kontexttreu) |
| Gold | 16 intervention, 15 comparator |
| Kopf + Gold | Probiotic = intervention (16), Antibiotic = comparator (15) |

Der Kopf stuetzt also das **Gold**, nicht die Plan-Bindung: die 16 steht ueber
der Probiotic-Gruppe, die 15 ueber der Antibiotic-Gruppe. Der Plan folgt dem
Kontext und bindet die 15 an intervention. Das ist ein **Kontext-gegen-Gold-
Konflikt**, keine Fehlbindung des Parsers: ohne Gold sagt der Kopf nicht, welche
Gruppe intervention ist. Wird der gedruckte n-Vorrang ueber den Kontext gestellt,
werden `:678` und `:682` mit je 16/intervention wertrichtig (**2 der 5 Zellen**);
zusaetzlich werden die bisher nicht erreichbaren 15/comparator-Zellen
erreichbar und wertgleich (2 weitere, nicht unter den 5).

### yun2024:426

| Quelle | Beleg |
|---|---|
| Kontext | intervention = **open MR**, comparator = **short-bore MR** |
| Kopf | `Short-Bore MR Imaging` Spalte 1: `n = 18`; Spalte 4: `n = 30`. `Open MR Imaging` Spalte 2: `n = 21`; Spalte 5: `n = 34`. `P Value` Spalte 3 |
| Plan-Arme | Short-Bore -> comparator (korrekt), Open -> **kein Arm**, P-Wert -> comparator (falsch) |
| Gold | 49 intervention, 44 comparator |

Short-Bore als comparator ist damit **richtig**; falsch sind nur die fehlende
Zuordnung der Open-Spalten und der P-Wert als comparator. Die Goldwerte 49/44
stehen in T4 nirgends (auch nicht als Summe der Untergruppen 18+30 = 48 und
21+34 = 55). Kopf-treu bleibt es bei **0 wertrichtigen Zellen**.

### yun2024:335 (und 336), zum Vergleich

Kopf: `Placebo (n = 45)` Spalten 0-1, `Aripiprazole (n = 47)` Spalten 2-3;
Kontext: intervention = Aripiprazole, comparator = Placebo. Kopf und Kontext
stimmen hier ueberein, das **Gold** ist umgekehrt (45 intervention, 47
comparator). Aus dem Kopf laesst sich die Umkehrung nicht begruenden:
**0 der 5 Zellen** werden dadurch wertrichtig.

**Ergebnis:** Kopf-treu werden **2 der 5** armfalschen Zellen wertrichtig
(678 und 682), und zwar nur unter der Regel "gedrucktes n schlaegt Kontext".
Bleibt der Kontext massgeblich, sind es **0 von 5**. Die 68 im Hauptskript
bleiben in beiden Faellen unveraendert, weil dort nichts umgebaut wird.

## 6. Zweiter Skript-Review (keine Zahl geaendert)

1. **Bandstatus prueft nur die eigene Spannweite.** Bei 678 steht das Band
   `(n=15)` ueber Spalten, die der Plan selbst als intervention fuehrt, also
   "ok" - obwohl die Gruppenbezeichnung Antibiotic dem Kontext widerspricht.
   Bandkonsistenz kann eine falsche Armidentitaet prinzipiell nicht finden.
2. **`arm_vertauscht` ist goldgetrieben, kein Kopfbeleg.** Ein Untergruppen-n,
   das zufaellig dem Goldwert des anderen Arms entspricht, wuerde als
   Vertauschung gemeldet.
3. **`gold_werte` ist nach Arm geschluesselt.** Records mit nur einer
   Gruppengroesse (kein Gegenstueck) koennen keine Vertauschung erkennen.
4. **Bandzaehlung ist pro Vorkommen, nicht pro Angabe.** Records mit zwei
   Tabellen zaehlen dieselbe Angabe doppelt in die 114.
5. **`details` behaelt zwei Kandidaten.** Bei 78 mit drei Perioden-n fehlt der
   dritte im JSON.
6. **Abgleich nur als Summe.** Ein +1/-1 zwischen zwei Records bliebe
   unbemerkt; ein Abgleich je Record fehlt.
7. **Absoluter Auswahlpfad** in `structure.json`; auf fremdem Checkout bricht
   das Skript ab.
8. **`int()` in der MD-Ausgabe** schneidet nicht-ganzzahlige Groessen ab;
   `float(gold['value'])` hat keinen None-Schutz.
9. **Sortierung** bleibt lexikografisch (682 vor 78).
