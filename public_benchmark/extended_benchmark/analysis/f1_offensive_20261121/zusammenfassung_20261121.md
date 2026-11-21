# Zwischenstand: Regelwerk zur Zellextraktion und seine Wirkung (21.11.2026)

Alles hier ist offline gemessen, ohne Netzaufruf, auf denselben Daten:

- 699 Records aus `yun699.jsonl` (Goldzellen aus den Markdown-Volltexten),
- 103 P5-Records mit gespeicherten Vorhersagen
  (`yun699_p5_24000_20261118/predictions.jsonl`),
- 243 Streuungsableitungen aus dem gedruckten 95%-KI.

Die Skripte liegen in
`public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/`.
Jede Zahl unten stammt aus einem Lauf dieser Skripte und steht in der jeweils
genannten JSON-Datei.

## 1. Kurzfassung

| Frage | Antwort |
|---|---|
| Bringt die neue Tabellenwahl Zellen? | Ja: `yun2024:447/448/450` je 6/6 statt 1/6, P5-Pool k 24 -> 27 |
| Soll die Regel Vorhersagen ersetzen? | Nein: Ersetzen kostet TP (166 -> 156) |
| Soll sie nur Luecken fuellen? | Ja: 178 TP / 118 FP statt 166 / 96 |
| Sollen Mittel mitkommen? | Nein: Mittel treffen 0 von 6 Zellen, ohne sie 178 / 112 |
| Ist die Kopfband-Regel ein Gewinn? | Nur in P5 (2 falsche Zellen weg), ueber alle 699 netto -13 richtige |
| Ist der Tabellenart-Ausschluss ein Gewinn? | Nein: macht keine Zelle richtig, kostet 2 richtige |
| Warum scheitert `PMC3877023`? | Zielzeile in der Demografie-Tabelle; die richtige `n`-Zeile ist nicht parsebar |

## 2. Was die Regel liest und wie sie geprueft wird

Kern: `zielzeile_alle_20261121.py`. Fuer jede Goldzelle wird eine Zielzeile
gesucht (Alias-Treffer, Zeitpunkt-Tabelle, Armzeile, Wochenspalte, Messwort-Block)
und der Wert aus der passenden Spalte gelesen. Schalter (alle einzeln abschaltbar):

| Schalter | Wirkung | Vorgabe |
|---|---|---|
| `POSITIONAL` | Spaltenreihenfolge statt Spaltennamen | an |
| `GATE` | Armnamen und Positionspruefung muessen uebereinstimmen | an |
| `WOCHENSPALTE` | Zeitpunkt-Spalte bei mehreren Messungen | an |
| `MESSWORT_BLOCK` | Wert nur aus dem Block des Messworts | an |
| `TABELLENLOKAL` | Suche nur in der Tabelle der Zielzeile | an |
| `ZEITPUNKT_TABELLE` | Nachher-Tabelle vor Baseline-Tabelle | an |
| `TABELLE_ARMBEDINGUNG` | Umzug nur, wenn die Tabelle ihre Arme nennt | an |
| `ARMZEILE` | Armzeilen ueber das Kuerzel der Unterschrift | an |
| `VORZEICHEN` | Minuszeichen in Werten | an |
| `SD_AUS_KI` | Streuung aus dem 95%-KI ableiten | an |
| `KOPFBAND_ARM` | `n =`-Zeile im Kopfband nur mit Armbezeichnung | an |
| `TABELLENART_AUS` | Baseline-/Charakteristika-Tabellen vor der n-Suche ueberspringen | **aus** |

Die Fixture (`fixture_20261121.py`, Modus `schreiben` / `pruefen`) friert die
Zellstaende zellgenau ein; `pruefen` meldet jede Abweichung und schlaegt fehl,
wenn eine abgeleitete Streuung still auf das Ablesen zurueckfaellt:

| Stand | Zellen | TP | FP |
|---|---:|---:|---:|
| `zellen` (Endvariante) | 33 | 30 | 3 |
| `zellen_ohne_gate` | 41 | 38 | 3 |
| `zellen_streuung` | 17 | 17 | 0 |
| `zellen_abgeleitet` | 42 | 32 | 10 (14 aus dem KI) |

Ablation der Bausteine (gleicher Lauf):

| Lauf | Zellen | TP | FP |
|---|---:|---:|---:|
| Endvariante | 33 | 30 | 3 |
| ohne Gate | 41 | 38 | 3 |
| ohne Positionsregel | 33 | 30 | 3 |
| ohne Wochenspalte | 31 | 26 | 5 |
| ohne Messwort-Block | 33 | 26 | 7 |
| ohne tabellenlokale Groesse | 31 | 28 | 3 |
| ohne Zeitpunkt-Tabelle | 33 | 30 | 3 |
| ohne Armbedingung | 33 | 18 | 15 |
| ohne Armzeile | 33 | 30 | 3 |
| ohne Vorzeichen | 33 | 30 | 3 |

## 3. Tabellenwahl (Nachher-Tabelle vor Baseline)

`tabellenwahl_20261121.py`: Bei gleichem Alias-Treffer zieht die Zielzeile in die
Nachher-Tabelle um, aber nur wenn diese ihre Arme in der Unterschrift nennt
(`I; n=104`).

| Record | richtig alt | richtig neu | vollstaendig neu |
|---|---:|---:|---|
| `yun2024:196` | 0 | 0 | nein (Gold aus Subgruppe MMSE-J 20-23) |
| `yun2024:447` | 1 | 6 | ja |
| `yun2024:448` | 1 | 6 | ja |
| `yun2024:450` | 1 | 6 | ja |

Wirkung auf den P5-Pool: k 24 -> 27, gepoolt 0.125 -> 0.136. Ohne die
Armbedingung kostet der Umzug Zellen (`PMC4987981`: Gold in der Baseline-Tabelle).

## 4. Ersetzen oder nur Luecken fuellen? (699 Records)

`umschreiben_20261121.py`, Stand mit allen Vorgaben:

| Stand | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| P5 unveraendert | 166 | 96 | 2607 | 0.109 |
| P5 + alte Regelzellen | 137 | 157 | 2636 | 0.089 |
| P5 + neue Regelzellen | 156 | 140 | 2617 | 0.102 |
| P5 + alte, nur Luecken | 169 | 125 | 2604 | 0.110 |
| P5 + neue, nur Luecken | 178 | 118 | 2595 | 0.116 |
| **P5 + neue, nur Luecken, ohne Mittel** | **178** | **112** | **2595** | **0.1162** |

- Ersetzen kostet TP, weil 32 richtige Vorhersagezellen einen falschen
  Regelwert bekommen; deren alter Regelwert war in allen 32 Faellen schon falsch
  (Ursache `alt_falsch`), also alte Schuld und nicht die Tabellenwahl.
- Luecken fuellen dreht das Vorzeichen: +12 TP und +22 FP gegenueber der
  unveraenderten Vorhersage.
- Von den 103 P5-Records bestaetigt die Regel 29 Zellen, ueberschreibt 32 und
  liefert zu 110 nichts.

Feldarten der neu gefuellten Zellen (Vorgabestand):

| Feldart | richtig | falsch |
|---|---:|---:|
| Streuung | 8 | 6 |
| Groesse | 4 | 10 |
| Mittel | 0 | 6 |

Mittel aus der Regel zu nehmen ist der beste Einzelhebel: 178 / 112 statt
178 / 118. Zwei Zwischenstaende (Mittel nur im leeren Arm, nur im mittelfreien
Record) waren zellgleich mit dem einfachen Lueckenfuellen und sind entfernt.

## 5. Die falschen Groessenzellen und ihre Ursachen

`groessen_ursachen_20261121.py`, 103 P5-Records, Lueckenfuellen ohne Mittel.
Ohne Regel werden 16 Groessenzellen neu gefuellt (4 richtig, 12 falsch).

| Ursache | Zellen | Beispiele |
|---|---:|---|
| falsche Zeile | 5 | `159` (24 aus "12 and 24 months"), `420`/`421` je 2 (Baseline-Kopfzeile 44/49 statt Outcome-Zeile 18/21 und 30/34) |
| abweichende Definition | 7 | `251`/`252` (randomisiert 406/393 bzw. 398/389 gegen Outcome 402/388), `356` (15 gegen 13 abgeschlossene), `451` (Unterschrift 104/114 gegen MVPA 99/108) |
| Rechenfehler | 0 | die gelesenen Zahlen sind im Dokument jeweils korrekt gedruckt |

Alle 12 stammen aus dem Kopfband einer Tabelle (Unterschrift, Spaltenkopf oder
Trennlinie), keine aus einer Datenzeile. Belegzeilen stehen im JSON/MD des
Skripts; `yun2024:451` liest die 104/114 aus der Unterschrift in **Zeile 96**
(nicht aus der Tabellenzeile 117), `yun2024:159` die 24 aus der Unterschrift in
Zeile 3.

## 6. Kopfband-Regel

`KOPFBAND_ARM` (Schalter, Vorgabe an): eine `n =`-Zeile im Kopfband gilt nur,
wenn dort eine Armbezeichnung steht (`Control group (n=15)`, `Placebo (n=22)`),
nicht bei `Short-Bore MR (n = 44)`.

| Stand (103 P5) | Groessenzellen | richtig | falsch |
|---|---:|---:|---:|
| ohne Regel | 16 | 4 | 12 |
| Kopfband (Vorgabe) | 14 | 4 | 10 |
| Tabellenart | 8 | 2 | 6 |
| beides | 8 | 2 | 6 |

In P5 kostet die Regel keine richtige Zelle. **Ausserhalb der P5-Records aber
schon** (`kopfband_699_20261121.py`, alle 699 Records, 1286 Goldzellen der
Groesse):

| Kennzahl | Wert |
|---|---:|
| richtig ohne Regel | 96 |
| richtig mit Regel | 83 |
| Zellen verloren | 14 (13 ausserhalb P5) |
| Zellen gewonnen | 1 |

Verloren gehen Armlabels, die das Wortfeld nicht kennt: `Apple Juice` /
`White Grape Juice` (`yun2024:4`), `CoPAT` / `IPAT` (`:13`), `Genoss DES` /
`Promus Element` (`:255`, `257`, `258`, `259`), `Sitagliptin` / `Non-exposed`
(`:84`). Gewonnen wird eine Zelle in `yun2024:75` (vorher Subgruppe 56 statt
Armzeile 29). **Netto also -13 richtige Groessenzellen.**

## 7. Tabellenart-Ausschluss (Ablation, bleibt aus)

`TABELLENART_AUS`: Tabellen mit Baseline- oder Charakteristika-Unterschrift
werden vor der n-Suche uebersprungen (Unterschrift aus dem `::: caption`-Block,
nicht aus Fliesstext).

Ergebnis: **keine der drei Zielzellen wird richtig.** `159`, `420` und `421`
(Intervention) sowie `356` entfallen nur, und es gehen beide richtigen Zellen von
`yun2024:678` verloren (deren Tabelle traegt eine Baseline-Unterschrift). In der
699er-Bilanz 176 / 108 statt 178 / 112 (F1 0.1151 statt 0.1162). Schalter bleibt
aus.

## 8. Warum `PMC3877023` (`yun2024:420`, `:421`) falsch liest

`pmc3877023_20261121.py` zeigt die Kette:

1. **Falsche Zielzeile.** Der Outcome nennt Region und Kenngroesse getrennt
   ("quantitative contour sharpness of the Cervicothoracic Spine"). Die Region
   steht in der Demografie-Tabelle (Zeile 29: `Cervicothoracic spine 14 (31.8)
   15 (30.6)`), die Kenngroesse nur als Blockzeile. Alle Suchfunktionen landen auf
   der Region-Zeile (`zeitverlauf_ziel` -1, `ziel_zeile_zeitpunkt` 28,
   `ziel_zeile_alias` 28); deren Tabelle liefert `Short-Bore MR (n = 44)` /
   `Open MR (n = 49)`.
2. **Die richtige `n`-Zeile wird erkannt, aber nicht geparst.** Zeile 146
   (`**T2w sagittal**  n = 18  n = 21  n = 30  n = 34`): `ist_groessenzeile` und
   `STRENGE` greifen, `aus_groessenzeile` gibt `{}` zurueck - die Zellen sind
   weder armbeschriftet noch nackte Zahlen (`n = 18` mit schmalen Leerzeichen).
3. **Der Parser allein reicht nicht.** Zwei Regionbloecke nebeneinander
   (Gruppenzeile 141, darunter je Short-Bore, Open, P-Wert = 6 Spalten), die
   `n`-Zeile nur 5 Segmente. Ohne Regionbewusstsein ist das Arm-Paar nicht
   zuzuordnen - genau das trennt Gold 420 (18/21) von 421 (30/34).

## 9. Grenzen

- Die Bilanzen messen exakte Zellgleichheit; "FP" heisst auch: richtiges Feld,
  abweichende Nachkommastelle.
- Die Vorhersagezellen tragen keine Zeilenangabe; "aus derselben Zeile" ist nur
  gegen die Regel-eigene Lesung pruefbar.
- Die Ursachenzuordnung der 12 Groessenzellen ist manuell, aber je Zelle mit
  Belegzeile und Text im Artefakt hinterlegt.
- `yun2024:451` ist nicht entscheidbar aus dem Dokument: Gold 99/108 steht nicht
  als `n` im Text.
- Fixture und Bilanz decken nur Records mit Goldzellen ab; Aussagen ueber die
  Pipeline insgesamt sind damit nicht belegt.

## 10. Empfehlungen (nach Hebel)

1. **Kopfband-Regel ausschalten oder Wortfeld erweitern.** Sie kostet netto 13
   richtige Groessenzellen (Substanz- und Geraetenamen fehlen im Wortfeld).
   Aufwand: eine Zeile oder eine Liste, ein Lauf ueber 699 Records (Sekunden).
2. **Zielzeile ueber den Blockkopf qualifizieren.** In `PMC3877023` genuegt es,
   die Blockzeile (`Contour sharpness`) als Teil des Zeilenlabels zu lesen; damit
   landen 420/421 erstmals im richtigen Tabellenbereich. Danach bleibt die
   Spaltenzuordnung der zwei Regionbloecke als zweiter, teurerer Schritt.
3. **Auslieferung: Luecken fuellen ohne Mittel** (178 / 112). Das ist der beste
   Stand und kostet keine richtige Vorhersagezelle.
4. **Offene Goldfragen** (brauchen eine Entscheidung, keinen Lauf):
   `yun2024:446` (Gold 3.32 gegen 5.07 aus dem gedruckten KI) und `yun2024:196`
   (Gold aus einer Subgruppentabelle, die der Record nicht nennt).

## 11. Dateien

| Datei | Inhalt |
|---|---|
| `zielzeile_alle_20261121.py` | Regelwerk und Schalter |
| `fixture_20261121.py` / `.json` | eingefrorene Zellstaende, `pruefen` |
| `umschreiben_20261121.py` / `.json` / `.md` | 699er-Bilanz, Ersetzungsstrategien |
| `groessen_ursachen_20261121.py` / `.json` / `.md` | Ursachen der 12 falschen Groessenzellen, vier Schalterstaende |
| `kopfband_699_20261121.py` / `.json` / `.md` | Gegenprobe der Kopfband-Regel ueber alle 699 Records |
| `tabellenwahl_20261121.py` / `.json` / `.md` | Vier-Record-Messung der Tabellenwahl |
| `pmc3877023_20261121.py` / `.json` / `.md` | Diagnose der falschen Zielzeile |
| `README.md`, `abschlussbericht_20261121.md` | ausfuehrliche Dokumentation |

## 12. Reproduktion

```bash
cd /d/daswu/AIResearch
P=.venv/bin/python
D=public_benchmark/extended_benchmark/analysis/f1_offensive_20261121
PYTHONIOENCODING=utf-8 $P $D/fixture_20261121.py pruefen
PYTHONIOENCODING=utf-8 $P $D/groessen_ursachen_20261121.py
PYTHONIOENCODING=utf-8 $P $D/kopfband_699_20261121.py
PYTHONIOENCODING=utf-8 $P $D/umschreiben_20261121.py
PYTHONIOENCODING=utf-8 $P $D/pmc3877023_20261121.py
```

`umschreiben_20261121.py --tabellenart` misst den Tabellenart-Ausschluss;
`fixture_20261121.py schreiben` schreibt die Fixture neu (nur nach bewusster
Regelaenderung).
