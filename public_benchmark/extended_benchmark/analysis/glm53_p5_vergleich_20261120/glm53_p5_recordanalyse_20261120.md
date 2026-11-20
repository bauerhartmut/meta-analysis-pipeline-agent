# Recordanalyse GLM-5.3 gegen P5 (20.11.2026)

Grundgesamtheit: die **103 Records** der P5-Auswahl, davon **102 bewertbar**
(`yun2024:653` hat keine Goldzellen), **423 Goldzellen**. Bewertung mit der
strengen Logik (Feld und Arm, 1:1-Verbrauch). Rein lesend, keine Prediction
verändert, kein Gold angefasst.

## Kurzfassung

- Auf dieser Auswahl hat die Referenz **null Zellen**; jeder Treffer stammt von
  P5. Ein Record-Vergleich „besser/schlechter" ist deshalb nicht möglich, nur
  eine Fehleranalyse der P5-Antworten.
- Die Fehlmenge ist **überwiegend eine Nicht-Antwort**, nicht ein Denkfehler:
  132 der 253 FN (52 %) entfallen auf die 33 Records ohne jede Antwort.
- Von den 121 FN auf beantworteten Records sind **68 falsche Werte**, **49
  fehlende Zellen** und nur **4 Armverwechslungen** (3 Records).
- Auf der Ausgabeseite stehen **80 Mehrfach-/Falschwert-Zellen** und **17
  Fremdschlüssel**; die Dublettenregel kostet 80 FP, die Yun-Logik würde sie
  ignorieren.
- 16 Records sind perfekt (F1 1,0), 44 ohne einen einzigen Treffer.

## 1. Verteilung auf Record-Ebene

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
| **Summe** | **102** |

Von den 44 Records ohne TP haben 33 keine Antwort (Budget), 3 eine Antwort ohne
Zellen (`yun2024:137` und zwei weitere) und 8 eine Antwort mit Zellen, aber
keinem richtigen Wert: `yun2024:113`, `:357`, `:362`, `:533`, `:615`, `:616`,
`:626`, `:686`.

Perfekt (F1 1,0, alle Goldzellen richtig und keine FP): `yun2024:32`, `:68`,
`:133`, `:136`, `:183`, `:228`, `:232`, `:233`, `:270`, `:344`, `:349`, `:367`,
`:405`, `:601`, `:602`, `:677`.

## 2. Fehlerkategorien

Zerlegung der 253 FN und 97 FP auf den 102 bewertbaren Records. Die Zuordnung
prüft zuerst, ob der **gespiegelte** Arm den Goldwert trägt (Armverwechslung),
dann, ob der Schlüssel mit anderem Wert vorliegt, sonst gilt die Zelle als
fehlend.

| Kategorie | Zellen | Anteil an FN bzw. FP | Erläuterung |
|---|---:|---:|---|
| Fehlende Extraktion | 181 | 71,5 % FN | Goldzelle hat keine Entsprechung; **132 davon** sind die 33 Records ohne Antwort |
| Falscher Wert | 68 | 26,9 % FN | Schlüssel steht da, Wert weicht ab |
| Armverwechslung | 4 | 1,6 % FN | Wert steht unter dem anderen Arm (3 Records: `113`, `178`, `291`) |
| Mehrfach-/Falschwert-Zelle | 80 | 82,5 % FP | Schlüssel kommt im Gold vor, Zelle ist Dublette oder trägt einen anderen Zeitpunkt-/Zeilenwert |
| Fremdschlüssel | 17 | 17,5 % FP | Feld/Arm kommt im Gold des Records nicht vor |
| Doppelte Extraktion (eigene Kategorie) | in den 80 enthalten | — | Dubletten sind nicht von Falschwerten am selben Schlüssel trennbar, ohne den Zeitpunkt zu kennen |
| Falsche Feldzuordnung | 0 | — | Ein Feldwechsel wäre ein Fremdschlüssel; die 17 sind überwiegend zusätzliche Felder, keine vertauschten |
| Nicht erkannte Tabelle | 6 Records | — | 6 der 33 Abbrüche haben im Markdown keinen Tabellentext (nur Caption und Bildplatzhalter) |
| Reasoning-Budgetabbruch | 33 Records | 132 FN | `completion_tokens` = 24.000, `content_chars` = 0 |
| Fehler durch Bewertungsregeln | 80 FP | — | Dubletten zählen hier als FP; die Yun-Logik ignoriert sie |

Die Kategorie „Armverwechslung" ist eine Verschärfung gegenüber der ersten
Zählung: `yun2024:113` liefert die Gruppengrößen 459/456, das Gold erwartet
456/459. Ohne Spiegelprüfung wäre das als zwei falsche Werte durchgegangen.
Mit ihr sind es zwei Armverwechslungen — derselbe Fehler, richtige Diagnose.

## 3. Wo die Fehlmenge herkommt

| Quelle | FN | Anteil an 253 |
|---|---:|---:|
| 33 Records ohne Antwort (132 Goldzellen) | 132 | 52,2 % |
| Beantwortet, Zelle fehlt | 49 | 19,4 % |
| Beantwortet, Wert falsch | 68 | 26,9 % |
| Beantwortet, Arm vertauscht | 4 | 1,6 % |

Damit ist die wichtigste Aussage dieser Analyse: **Die Hälfte der Fehlmenge ist
kein Extraktionsfehler, sondern eine Nicht-Antwort.** Wer P5 über die
Zellqualität beurteilt, ohne die 33 Abbrüche zu trennen, misst überwiegend die
Verfügbarkeit des Endpunkts.

Auf den 67 Records mit Zellen (423 − 132 = 291 Goldzellen) liegt die
Trefferquote je Goldzelle bei 170 von 291 — 58,4 %. Das ist die Qualität
dessen, was P5 tatsächlich ausgibt.

## 4. Zehn Records mit dem größten Abstand zur Referenz

Die Referenz hat auf allen 103 Records 0 TP; der Abstand ist deshalb
gleichbedeutend mit dem P5-Gewinn. Größte Gewinne:

| Record | Gold | P5 TP | P5 FP | P5 FN | P5 F1 |
|---|---:|---:|---:|---:|---:|
| `yun2024:183` | 6 | 6 | 0 | 0 | 1,000 |
| `yun2024:228` | 6 | 6 | 0 | 0 | 1,000 |
| `yun2024:232` | 6 | 6 | 0 | 0 | 1,000 |
| `yun2024:233` | 6 | 6 | 0 | 0 | 1,000 |
| `yun2024:32` | 6 | 6 | 0 | 0 | 1,000 |
| `yun2024:133` | 4 | 4 | 0 | 0 | 1,000 |
| `yun2024:160` | 6 | 4 | 0 | 2 | 0,800 |
| `yun2024:163` | 6 | 4 | 0 | 2 | 0,800 |
| `yun2024:203` | 6 | 4 | 0 | 2 | 0,800 |
| `yun2024:212` | 6 | 4 | 0 | 2 | 0,800 |

Die Gegenliste — Records, auf denen auch P5 nichts trifft — ist für die
Weiterarbeit wichtiger:

| Record | Gold | P5 Zellen | TP | FP | FN | Ursache |
|---|---:|---:|---:|---:|---:|---|
| `yun2024:30` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:52` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:159` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:420` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:421` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:446` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:451` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:523` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:525` | 6 | 0 | 0 | 0 | 6 | Budgetabbruch |
| `yun2024:113` | 6 | 4 | 0 | 4 | 6 | Armverwechslung plus Zeitpunktwechsel |

Die zehn Records mit den meisten falsch positiven Zellen:

| Record | Gold | P5 Zellen | TP | FP | Muster |
|---|---:|---:|---:|---:|---|
| `yun2024:686` | 2 | 6 | 0 | 6 | ganze Tabelle einer anderen Population ausgegeben |
| `yun2024:113` | 6 | 4 | 0 | 4 | Arme vertauscht, Zeitpunkt gewechselt |
| `yun2024:158` | 6 | 6 | 2 | 4 | zwei Zeitpunkte gleichzeitig geliefert |
| `yun2024:161` | 6 | 6 | 2 | 4 | zwei Zeitpunkte gleichzeitig geliefert |
| `yun2024:174` | 4 | 6 | 2 | 4 | zwei Zeitpunkte gleichzeitig geliefert |
| `yun2024:357` | 2 | 4 | 0 | 4 | andere Studienpopulation (21/20 statt 13/13) |
| `yun2024:556` | 6 | 6 | 2 | 4 | zwei Zeitpunkte gleichzeitig geliefert |
| `yun2024:558` | 6 | 6 | 2 | 4 | zwei Zeitpunkte gleichzeitig geliefert |
| `yun2024:668` | 6 | 6 | 2 | 4 | zwei Zeitpunkte gleichzeitig geliefert |
| `yun2024:110` | 6 | 4 | 1 | 3 | Werte aus fremder Zeile |

## 5. Drei Belege im Wortlaut

**Armverwechslung (`yun2024:113`).** Gold: `intervention_group_size` 456,
`comparator_group_size` 459. P5: `intervention_group_size` 459,
`comparator_group_size` 456, dazu Mittelwerte zum Zeitpunkt „1-month
follow-up". Die Zellen sind vollständig, aber seitenvertauscht.

**Falsche Population (`yun2024:686`).** Gold: beide Gruppengrößen 17. P5 gibt
für beide Arme 34 zum Zeitpunkt „during 12 week diet" und zusätzlich Mittelwert
und Streuung. 34 ist die Summe beider Arme — P5 hat die Gesamtzeile der Tabelle
gelesen, nicht die Armzeilen.

**Falscher Zeitpunkt (`yun2024:357`).** Gold: beide Gruppengrößen 13. P5 gibt
21 und 20 zum Zeitpunkt „after 4 months of dietary intervention". Die Zahlen
stehen im Dokument, gehören aber zu einer anderen Auswertungsgruppe.

Diese drei Fälle zeigen dasselbe Muster: **P5 findet Zahlen, ordnet sie aber
der falschen Zeile, dem falschen Zeitpunkt oder dem falschen Arm zu.** Das ist
ein Bindungsproblem, kein Erkennungsproblem.

## 6. Wird P5 durch die Tabellen- und Arm-Logik benachteiligt?

Gemessen auf diesen 102 Records:

| Benachteiligung | Messwert | Wirkung |
|---|---|---|
| Arm als Bewertungsschlüssel | 4 von 253 FN sind Armverwechslungen | klein (1,6 %), aber jeder Fall kostet doppelt: 2 FN und 2 FP |
| Dubletten als FP | 80 von 97 FP | groß: ohne diese Regel wäre die Precision 0,705 statt 0,637 |
| Zellen ohne Gold als FP | 17 von 97 FP | klein, aber vorhanden |
| Zeitpunkt nicht prüfbar | 0 Goldzellen mit Zeitpunkt | die Precision ist eine Obergrenze, keine Untergrenze |
| Tabellenkontext | 33 Abbrüche, davon 6 ohne Tabellentext | wirkt über die Nicht-Antwort, nicht über falsche Zellen |

Die Tabellen- und Arm-Logik bestraft P5 also **nicht** über falsche
Zellzuordnung — dort sind nur 4 Zellen betroffen. Sie bestraft P5 über die
Verfügbarkeit (33 Abbrüche, 132 FN) und über die Ausgabedisziplin (80
Mehrfachzellen). Das ist eine andere Baustelle als die Armzuordnung.

## 7. Grenzen

- Der Record-Vergleich ist einseitig: Ohne GLM-Zellen auf diesen Records gibt
  es keinen Referenz-F1 je Record, nur absolute Zahlen.
- Die Klassifikation „falscher Wert" ist eine Restmenge. Ob der Wert aus einer
  anderen Zeile, einem anderen Zeitpunkt oder einem Rechenfehler stammt, ist
  nur in den drei inspizierten Fällen belegt, nicht für alle 68.
- „Doppelte Extraktion" und „falscher Wert am selben Schlüssel" sind ohne
  Gold-Zeitpunkt nicht trennbar; die 80 FP enthalten beides.
- Die Zellzahlen stammen aus `predicted.cells`. Das Feld `rows` derselben Zeile
  wird nicht zusätzlich gezählt; beide enthalten im P5-Lauf dieselben Zellen.

## 8. Reproduktion

```
.venv/bin/python public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/vergleiche_20261120.py
```

Die Record-Tabelle mit allen 103 Zeilen steht als `records` in
`vergleich_20261120.json` (je Record Goldzellen, Zellen, TP/FP/FN, F1 und
Fehlerklassen).
