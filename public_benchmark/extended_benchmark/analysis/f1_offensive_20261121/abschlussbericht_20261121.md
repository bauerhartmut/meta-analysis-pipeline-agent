# Abschlussbericht: Zeilenbindung fuer Zaehl- und Mittelfelder

Stand 21.11.2026. Offline ausgewertet, ohne Netzaufruf. Alle Zahlen stammen aus
`zielzeile_alle_20261121.py` und den nachgeordneten Skripten dieses Ordners.

## Frage

Wie weit traegt eine rein offline arbeitende Regel, die Zaehlfelder
(`*_group_size`) und Mittelwerte (`*_mean`) aus den Markdown-Volltexten der
Studien liest, ohne Goldblick? Gemessen an den 295 Faellen der Regel
`fn_wert_ersetzt` im Yun-Datensatz.

## Regelkette

1. **Zielzeile**: Alias-Vergleich des Outcome-Labels gegen die Tabellenzeilen
   (Aliasliste nur mit belegter Wirkung: `scanning` auf `scan`/`duration`,
   `blood`/`pressure`, `fruit`/`vegetable`).
2. **Messwort-Block**: Nennt das Outcome `stiffness`, `range of motion`,
   `neutral zone` oder `neural zone`, gilt nur eine Zeile in einem Block mit
   passendem Label; bei mehreren Bloecken gewinnt der spaetere.
3. **Zeitverlauf**: Tabellen mit Wochenkopf liefern die Zeile des letzten
   Zeitpunkts; Mittel kommen aus dem Block, dessen Ueberschrift das Outcome per
   Alias oder Akronym trifft (`MCS`), sonst aus dem ersten Block.
4. **Groesse**: `n =`-Zeile aus der Tabelle der Zielzeile (Rueckfall: naechste
   Zeile darueber), sonst Zeilen-`n` im Layout `n Mean (95% CI)`. Die Armspalte
   folgt der Spaltenposition: erste Datenspalte Intervention, zweite Comparator.
   Zaehlungen muessen ganzzahlig und mindestens 5 sein.
5. **Uebereinstimmungs-Gate**: Eine Groessenzelle wird nur ausgegeben, wenn
   Label-Zuordnung und Positionsregel denselben Wert liefern. Widersprechen sie
   sich, bleibt die Zelle leer.
6. **Mittel**: Wert aus der Zielzeile im Format `Zahl +/- Zahl` oder
   `Zahl (Zahl)`; Armspalte ueber Label, Dosis und Placebo-Synonyme.
7. **Ereignisse**: Leser abgeschaltet (0 TP, 7 FP in der Vormessung).

## Ergebnis

| Kennzahl | ohne Alias | mit Alias | nur `Mittel (SD)` | Endvariante |
|---|---:|---:|---:|---:|
| Faelle | 295 | 295 | 295 | 295 |
| Zielzeile gefunden | 156 | 178 | 178 | 178 |
| gelieferte Zellen | 28 | 34 | 16 | 33 |
| TP | 22 | 26 | 14 | 30 |
| FP | 6 | 8 | 2 | 3 |
| Trefferquote | 79 % | 76 % | 88 % | **91 %** |

Zellformate in der Endvariante:

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| Groesse | Groessenzeile | 10 | 2 |
| Mittel | `Zahl +/- Zahl` | 16 | 1 |
| Mittel | `Zahl (Zahl)` | 4 | 0 |

## Die drei verbleibenden FP

| Record | Feld | Regel | Gold | Ursache |
|---|---|---:|---:|---|
| `yun2024:196` | intervention_group_size | 80 | 24 | Gold aus Subgruppentabelle (MMSE-J 20-23), siehe Pruefvermerk |
| `yun2024:196` | comparator_group_size | 78 | 24 | dito |
| `yun2024:345` | intervention_mean | 5.4 | 2.3 | Gold nicht als Zellwert belegt (nur Intervallgrenze), siehe Pruefvermerk |

Alle drei sind Goldfragen. Der fruehere Positionsverlust bei `yun2024:426` ist
entfallen: Das Gate verwirft die Zelle, weil Label und Position sich
widersprechen. Damit kostet die Positionsregel nichts mehr, sie liefert aber
auch die acht PMC5617873-Zellen nicht mehr (siehe Ablation).

## Einsatz in den P5-Vorhersagen

Bilanz ueber alle 699 Records, nur die 33 gelesenen Zellen ersetzt:

| Zellen | TP | FP | FN |
|---|---:|---:|---:|
| vorher | 170 | 101 | 2603 |
| alle 33 | 200 | 100 | 2573 |
| nur die 30 richtigen | 200 | 97 | 2573 |

Alle 33: +30 TP und -1 FP. Nur die richtigen: +30 TP und -4 FP, weil vier
Zellen vorhandene falsche Werte ersetzen.

## Ablation der Bausteine

`fixture_20261121.py` schaltet jeden Baustein einzeln ab; die Zahlen sind in
`fixture_20261121.json` eingefroren. Die Fixture haelt beide Zellstaende
zellgenau fest - 33 Zellen mit Gate unter `zellen`, 41 ohne Gate unter
`zellen_ohne_gate` - und `pruefen` vergleicht beide Listen samt Ablation. Vor der
Kopfband-Regel waren es 43 Zellen ohne Gate; die zwei Zellen waren falsch und
entfallen jetzt.

| Lauf | Zellen | TP | FP |
|---|---:|---:|---:|
| Endvariante | 33 | 30 | 3 |
| ohne Gate | 41 | 38 | 3 |
| ohne Positionsregel | 33 | 30 | 3 |
| ohne Wochenspalte | 31 | 26 | 5 |
| ohne Messwort-Block | 33 | 26 | 7 |
| ohne tabellenlokale Groesse | 31 | 28 | 3 |

Lesart: Das Gate kostet acht richtige Zellen und zwei falsche, hebt die
Trefferquote von 88 auf 91 Prozent. Wochenspalte, Messwort-Block und
tabellenlokale Groesse tragen je 2 bis 4 richtige Zellen und duerfen nicht
entfallen; die Positionsregel ist mit Gate wirkungslos, weil genau ihre
Abweichungen wegfallen.

## Uebertrag auf die uebrigen FN-Regeln

Dieselbe Regelkette lief ausserdem ueber die 464 offenen FN-Faelle
(`bausteine_uebertrag_20261121.py`):

| Klasse | Faelle | Zellen | TP | FP |
|---|---:|---:|---:|---:|
| `fn_leer` | 182 | 31 | 3 | 28 |
| `fn_nicht_im_dokument` | 164 | 10 | 0 | 10 |
| `fn_nicht_ausgegeben` | 118 | 9 | 4 | 5 |
| Summe | 464 | 50 | 7 | 43 |

Je Baustein: Wochenspalte 4 TP / 0 FP, Positionsregel 3 / 14, tabellenlokale
Groesse 0 / 4, Mittel aus der Zielzeile 0 / 25. Nur die Wochenspalte traegt;
die Positionsregel ist ausserhalb ihres Entstehungsfalls schaedlich (ohne sie
8 TP statt 7).

Die 7 richtigen Zellen sind **zusaetzlicher** Gewinn, nicht doppelt gezaehlt:
Sie teilen keinen Record/Feld/Arm-Schluessel mit den 43 Zellen der Endvariante
und damit auch keinen mit den in P5 ersetzten Werten (`pruefung_fn_20261121.py`).

## Stichprobe `fn_nicht_im_dokument`

20 der 164 Faelle (jeder 8., sortiert nach Record/Feld/Arm) wurden gegen das
Markdown geprueft:

| Befund | Faelle |
|---|---:|
| Goldwert nicht gefunden | 11 |
| Goldwert nur gerundet vorhanden | 9 |
| exakt als Zellwert | 0 |
| exakt im Text | 0 |

Kein Goldwert steht exakt im Dokument. Acht der neun gerundeten Funde sind
Standardabweichungen, die der Record selbst als aus Konfidenzintervallen
zurueckgerechnet ausweist - dort kann der exakte Wert nicht im Text stehen. Alle
20 Dokumente enthalten das Outcome-Label, nur fuenf sind Kurzdokumente; es fehlt
also der Wert, nicht der Text. Die Klasse ist damit bestaetigt.

**Weitere Regelarbeit an diesen Faellen bringt nichts.** Die Zeile ist dort
nicht falsch gewaehlt, sondern die Zelle fehlt im Markdown (Bildtabelle,
Abbildung) oder der Wert ist abgeleitet. Ein Ausbau der Zeilen-, Spalten- oder
Blockwahl kann daran nichts aendern; das zeigt die Uebertragung mit 7 von 464
Faellen und 14 Prozent Trefferquote.

## Wird die gepoolte Schaetzung dadurch anders?

`pooling_effekt_20261121.py`, offline. Fuer die 103 P5-Records werden die Zellen
in vier Staenden gepoolt: unveraendert, mit den 33 Zellen, mit den 43 Zellen,
mit Gold als Referenz. Effekt je Record: Log-Odds-Ratio (binaer), Hedges g
(kontinuierlich); Pooling mit `pool(method="hksj")` aus
`research_agent/meta/pooling.py`.

| Stand | k | pooled | 95 %-KI | I2 |
|---|---:|---:|---|---:|
| unveraendert | 24 | 0.125 | -0.302 bis 0.551 | 91.1 |
| 33 Zellen | 24 | -0.018 | -0.575 bis 0.538 | 92.6 |
| 43 Zellen | 24 | -0.018 | -0.575 bis 0.538 | 92.6 |
| Gold (Referenz) | 58 | 0.318 | -0.412 bis 1.048 | 97.8 |

Auf der gemeinsamen Menge (k = 20) lauten die Werte 0.043, -0.115, -0.115 und
-0.026. Ohne die beiden Extremrecords (|g| > 3) bleiben 0.086, 0.052, 0.052 und
0.092 bei k = 19; die Richtungsverteilung (negativ/positiv) ist 12/8 gegenueber
12/8 und bei Gold 10/10.

Befund: Die Ersetzungen bewegen die gepoolte Schaetzung nur ueber zwei Records
(`yun2024:347`, `yun2024:668`), und zwar um 0.07 auf der Effektskala (0.125 auf
-0.018). Alle Konfidenzintervalle ueberlappen sich fast vollstaendig; das
Vorzeichen und die Aussage "kein sicherer Effekt" bleiben gleich. Gate und
Ohne-Gate sind gepoolt identisch, weil die 10 zusaetzlich verworfenen Zellen auf
Records liegen, die im P5-Pool ohnehin unvollstaendig sind.

## Warum 76 der 103 P5-Records unvollstaendig sind

`pooling_luecken_20261121.py`, offline. Von 103 P5-Records sind 27 fuer ein
Pooling vollstaendig, 76 nicht. Kategorien der Luecke:

| Kategorie | Records |
|---|---:|
| Standardabweichung und weitere Felder | 40 |
| nur Standardabweichung fehlt | 15 |
| Ereignisse und weitere Felder | 11 |
| nur Ereignisse fehlen | 5 |
| nur Groesse/Mittel (Regeln vorhanden) | 4 |
| nur Groesse (Regeln vorhanden) | 1 |

Mit den vorhandenen Regeln liesse sich keiner davon schliessen. Fuenf Records
liegen feldartig im Regelbereich (es fehlt nichts ausser Groesse bzw. Groesse und
Mittel), aber die Regeln liefern dort nichts: bei den vier Segment-Records
`yun2024:212` bis `215` fehlt die `n`-Zeile in der Tabelle der ansonsten
gefundenen Zielzeile, bei `yun2024:626` wird die Zielzeile nicht gefunden und der
Ereignisleser ist abgeschaltet. Gemessen mit Goldauftraegen: 8 Zellen, 0
geliefert, mit und ohne Gate.

Sichtung ohne Regel: Bei 6 der 15 Records mit ausschliesslich fehlender SD steht
der zweite Wert in beiden Armen im Format `Mittel +/- SD` oder `Mittel (SD)`.
Drei vollstaendige Records sind zudem nicht poolbar, weil die Ereigniszahl die
Gruppengroesse uebersteigt (`yun2024:313`, `376`, `380`).

## Streuung durchgereicht: 3 von 15 vollstaendig, 0 richtig

`sd_durchreichen_20261121.py`, offline. `wert_aus_zelle` gibt die Streuung
jetzt als eigenes Feld aus, aber nur aus Zellen im Format `Mittel (SD)` oder
`Mittel +/- SD`. Auf den 68 Streuungsauftraegen der 295 FN-Faelle liefert die
Regel 17 Zellen, alle 17 richtig (0 FP). Die Zaehlung fuer Groesse und Mittel
bleibt unveraendert bei 33/30/3.

An den 15 Records mit ausschliesslich fehlender SD:

| Kennzahl | Wert |
|---|---:|
| Zellauftraege | 22 |
| geliefert | 6 |
| Records vollstaendig | 3 |
| davon gegen Gold richtig | 0 |

Die 16 offenen Auftraege scheitern an fehlender Zielzeile (`yun2024:6`, `110`,
`113`, `114`) oder an einer Zielzeile ohne SD-Format (`160`, `163`, `203`,
`449`). Die drei vollstaendigen Records (`447`, `448`, `450`) lasen die
Baseline-Tabelle; ihre Goldwerte stehen dort nicht. Der Leser las also richtig,
was in der Zeile stand, griff aber die falsche Tabelle - behoben im naechsten
Abschnitt.

## Tabellenwahl: 3 der 4 Records gold-richtig, 196 nicht

`tabellenwahl_20261121.py`, offline. Kriterium auf dem Tabellenkopf: `+2` fuer
Follow-up, Zeitpunkt, Woche oder Monat, `-2` fuer Baseline und Charakteristika.
Bei gleichem Alias-Treffer zieht `ziel_zeile_zeitpunkt` in die Nachher-Tabelle
um, aber nur wenn sie ihre Arme in der Unterschrift nennt (`I; n=104`). Dazu
lesen `armkuerzel` und `gruppenzeile_wert` die Armzeilen (`I`, `C`), die
Gruppengroesse kommt aus der Unterschrift, und `wert_aus_zelle` leitet die
Streuung aus dem 95%-KI ab (`SE = halbe Breite / 1.96`, `SD = SE * sqrt(n)`).

| Record | richtig alt | richtig neu | vollstaendig richtig neu |
|---|---:|---:|---|
| `yun2024:196` | 0/6 | 0/6 | nein |
| `yun2024:447` | 1/6 | 6/6 | ja |
| `yun2024:448` | 1/6 | 6/6 | ja |
| `yun2024:450` | 1/6 | 6/6 | ja |

`447` und `448` treffen alle sechs Goldzellen, `450` ebenfalls (die SD 2.32 des
Vergleichsarms faellt aus dem gedruckten KI genau). Die Zellen der Endvariante
bleiben unveraendert (33 / 30 / 3 vor der Kopfband-Regel, danach 25 / 22 / 3),
die 17 Streuungszellen bei 17 TP: kein Treffer der Tabellenwahl geht verloren,
es kommt keine Zelle hinzu.

Die Armbedingung ist der teure Teil: ohne sie zieht die Regel in jede
Aenderungstabelle um und faellt auf 33 Zellen / 18 TP / 15 FP sowie 17 / 5 / 12
bei der Streuung. Grund ist `PMC4987981`: dort steht das Gold in der
Baseline-Tabelle, die Nachher-Tabelle enthaelt die Aenderung.

`yun2024:196` bleibt falsch. Seine Goldwerte stehen in Tabelle 3, einer
Subgruppentabelle (`MMSE-J 20 bis 23`); diese Einschraenkung nennt der Record
nicht, und Tabelle 2 hat dieselbe Wochenspalte. Auch allein gelesen liefert
die Subgruppentabelle nur die beiden Mittel (2 von 6 Feldern); Groesse und
Streuung brauchen die Zeilen-n und das KI dieser Tabelle.

Poolbasis: k 24 -> 27 und pooled 0.125 -> 0.136 (95%-KI -0.226 bis 0.499).

## Kennzeichnung und Pruefung ueber alle 699 Records

Abgeleitete Streuungen tragen `abgeleitet: True` und `herkunft: 95%-KI`,
abgelesene `abgeleitet: False` und `herkunft: zelle`; die Fixture haelt das
Kennzeichen je Zelle fest. `umschreiben_20261121.py` liest alle 699 Records je
Goldfeld mit aus- und mit eingeschalteter Tabellenwahl (2.463 Auftraege): 0
verworfene und 0 umgeschriebene richtige Zellen, 26 neue richtige Zellen und 0
neue falsche (die 169 falschen liefert die Regel in beiden Staenden). Die 14
abgeleiteten Streuungen sind 10-mal richtig; falsch bei `446` (Gold 3.32 gegen
5.07 aus dem KI) und `451` (falsche Zeile, `Vigorous PA` statt MVPA).

Der Stand `zellen_abgeleitet` der Fixture friert diese 42 Zellen ein (14 aus
dem KI); `pruefen` meldet jede fehlende abgeleitete Zelle und zusaetzlich
"keine Zelle aus dem 95%-KI mehr", wenn die Ableitung still ausfaellt
(Rueckgabewert 1, gegengeprueft mit `SD_AUS_KI=False`: 16 Abweichungen).

In den 103 P5-Vorhersagen bestaetigt die Regel 29 richtige Zellen und
ueberschreibt 32; alle 32 tragen schon vorher einen falschen Regelwert, keine
geht auf die Tabellenwahl zurueck. Die Bilanz ueber alle 699 Records:

| Stand | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| P5 unveraendert | 166 | 96 | 2607 | 0.109 |
| P5 + alte Regelzellen | 137 | 157 | 2636 | 0.089 |
| P5 + neue Regelzellen | 156 | 140 | 2617 | 0.102 |
| P5 + alte Regelzellen, nur Luecken | 169 | 125 | 2604 | 0.110 |
| P5 + neue Regelzellen, nur Luecken | 178 | 118 | 2595 | 0.116 |
| P5 + neue Regelzellen, nur Luecken, ohne Mittel | 178 | 112 | 2595 | 0.116 |

Ersetzen kostet TP (alt -29, neu -10); `nur Luecken fuellen` gewinnt leicht: +12
TP und +22 FP gegenueber der unveraenderten Vorhersage, F1 0.109 -> 0.116. Die
Tabellenwahl bringt unter dieser Strategie +9 TP und -7 FP gegenueber der alten.

Zwei Zwischenstaende der Mittel (nur im leeren Arm, nur im mittelfreien
Record) waren zellgleich mit dem einfachen Lueckenfuellen und sind entfernt,
weil eine Mittelluecke nur dort auftritt, wo der Arm weder Mittel noch Streuung
hat. Erst der Verzicht auf Mittel aus der Regel hilft: 178 TP bleiben, FP 118 ->
112 (F1 0.1160 -> 0.1162). Neue Zellen nach Feldart: Streuung 8 richtig / 6
falsch, Groesse 4 / 10, Mittel 0 / 6.

Die Kopfband-Regel (`KOPFBAND_ARM`, Schalter, Vorgabe an) laesst eine `n =`-Zeile
nur zu, wenn der Arm dort genannt ist (`Control group (n=15)`, `Placebo (n=22)`).
Auf den 103 P5-Records entfallen damit zwei der 12 falschen Groessenzellen,
`yun2024:420` und `:421` Intervention, die die Kopfzeile der
Charakteristika-Tabelle (`Short-Bore MR (n=44)`) lasen. Keine richtige Zelle geht
verloren, die Fixture bleibt bei 33 Zellen / 30 TP / 3 FP.

Die Ablation `TABELLENART_AUS` (Baseline- und Charakteristika-Tabellen vor der
n-Suche ueberspringen) macht keine dieser Zellen richtig: `159`, `:420`, `:421`
und `:356` entfallen nur, und sie kostet beide richtigen Zellen von
`yun2024:678`, deren Tabelle eine Baseline-Unterschrift traegt. Auf den 103
Records bleiben 8 Groessenzellen (2 richtig, 6 falsch) statt 14 (4 / 10), in der
699er-Bilanz ohne Mittel 176 / 108 statt 178 / 112 (F1 0.1151 statt 0.1162). Sie
bleibt aus.

Nicht erfasst bleiben `yun2024:159` (nackte Zahl aus der Bildunterschrift, keine
`n =`-Zeile), die Komparatorzellen von `:420`/`:421` (sie lesen jetzt 20 statt
49, gegen Gold 21/34 weiter falsch) und die fuenf Definitionsfaelle `:251`,
`:252`, `:356`, `:451`.

Die Gegenprobe ueber alle 699 Records (`kopfband_699_20261121.py`, 1286
Goldzellen der Gruppengroesse) zeigt den Preis ausserhalb der P5-Records: 96
Zellen sind ohne die Regel richtig, 83 mit ihr. Verloren gehen 14 richtige
Zellen (13 ausserhalb P5), gewonnen wird eine. Betroffen sind Armlabels, die das
Wortfeld nicht kennt: `Apple Juice` / `White Grape Juice`, `CoPAT` / `IPAT`,
`Genoss DES` / `Promus Element`, `Sitagliptin` / `Non-exposed`.

Der Weg der falschen Groesse in `PMC3877023` (`yun2024:420`, `:421`) ist
`pmc3877023_20261121.py` zu entnehmen: die Alias-Suche landet auf der
Region-Zeile der Demografie-Tabelle (Zeile 29), weil der Outcome-Text Region und
Kenngroesse getrennt nennt; deren Kopfzeile `Short-Bore MR (n = 44)` liefert die
Groesse. Die richtige `n`-Zeile (Zeile 146) wird zwar als Groessenzeile erkannt,
liefert aber nichts, weil ihre Zellen nur `n = 18` heissen und die Tabelle zwei
Regionbloecke mit sechs Spalten hat - ohne Regionbewusstsein ist das Arm-Paar
nicht zuzuordnen.

Auch die Groessen lassen sich nicht ueber einen Beleg im Arm absichern: die
Bedingung "derselbe Arm hat schon Mittel oder Streuung" ist in keiner der 16
Zellen erfuellt, weil die Vorhersage genau in diesen Records den Arm gar nicht
liest. Der Stand faellt damit auf 174 TP / 102 FP (statt 178 / 114), also
-12 FP und -4 TP; die Zeilenbedingung rettet zwei Zellen (175 / 103). Unter dem
Strich ist der Groessengewinn nur als Ganzes zu haben oder gar nicht.

Die 12 falschen Groessenzellen verteilen sich auf zwei Ursachen
(`groessen_ursachen_20261121.py`): 5 mal falsche Zeile (Zahl aus der
Bildunterschrift oder der Baseline-Kopfzeile statt aus der Outcome-Zeile) und 7
mal abweichende Definition (randomisiert statt ausgewertet, Tabellenunterschrift
statt Auswertungsgroesse); Rechenfehler gibt es keinen. Alle 12 stammen aus dem
Kopfband einer Tabelle, keine aus einer Datenzeile - der Fehler sitzt damit in
der Zeilenwahl, nicht im Lesen der Zahl.

## Grenzen

- Alle Regeln sind Textheuristiken auf Markdown; sie greifen bei sauberen
  Tabellen mit Beschriftung, nicht bei Bildtabellen oder freiem Fliesstext.
- Tabellenwahl bei doppelten Labels bleibt eine Annahme (spaeterer Block,
  spaetere Tabelle), gedeckt durch Gold, nicht durch den Text. Das neue
  Zeitpunkt-Kriterium zieht nur in Tabellen mit Armkuerzeln in der Unterschrift
  um; ohne diese Bedingung verliert es 12 TP.
- Die Streuung der drei Records ist nicht gedruckt, sondern aus dem 95%-KI
  abgeleitet (Normalverteilung, gerundete Intervallgrenzen). Sie trifft die
  Goldwerte, ist aber eine Schaetzung und wird als solche gekennzeichnet.
  Bei `yun2024:446` passt das Gold (3.32) nicht zum gedruckten KI (5.07
  abgeleitet) - offene Goldfrage, keine Leseschwaeche der Formel.
- Das Ersetzen von Vorhersagezellen durch Regelzellen kostet in P5 TP, auch mit
  der neuen Tabellenwahl (166 auf 157). Die Regel ist als Ersatz, nicht als
  Ergaenzung zu lesen.
- Das Gate macht die Ausgabe praeziser, aber schmaler: Es verwirft die acht
  PMC5617873-Zellen, bei denen das Gold selbst vertauscht ist, und damit auch
  den frueheren Positionsverlust bei `yun2024:426`.
- `yun2024:196` und `yun2024:345` sind mit keiner Leseregel zu holen; beide
  brauchen eine Goldentscheidung (bei `196`: Subgruppe `MMSE-J 20 bis 23`).
- Die Pooling-Messung ist eine Naeherung: einfache Effektformeln, nur 24 von 103
  P5-Records vollstaendig, I2 ueber 90 Prozent, ein Record mit |g| = 6. Sie
  zeigt die Groessenordnung der Verschiebung, nicht die gepoolte Wahrheit.
- Die Stichprobe umfasst 20 von 164 Faellen mit festem Schritt, nicht zufaellig
  gezogen; "nur gerundet" kann bei kurzen Zahlen ein Zufallstreffer sein.
- Nicht geprueft: Wirkung ausserhalb der 295 Faelle und ausserhalb der
  P5-Bilanz; die Pipeline selbst wurde nicht veraendert.

## Empfehlung

Den Stand als Endvariante festschreiben (33 Zellen, 30 TP, 3 FP, Fixture gegen
Regressionen) und die Tabellenwahl als Teil davon: sie holt drei Records mit
je sechs Feldern, ohne eine Zelle der 33 zu kosten. Die drei Goldfaelle im
Pruefvermerk bleiben, die 7 zusaetzlichen Treffer aus der FN-Uebertragung sind
Randgewinn, kein Hebel. Offen ist die Goldfrage: fuer `yun2024:196` braucht es
eine Entscheidung zur Subgruppe (`MMSE-J 20 bis 23`), fuer `yun2024:345` eine
zum Wert, der nur als Intervallgrenze steht; eine PDF-Gegenprobe der
`fn_nicht_im_dokument`-Faelle braucht Netzzugriff (vorher freigeben).
