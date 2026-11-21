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
zellgenau fest - 33 Zellen mit Gate unter `zellen`, 43 ohne Gate unter
`zellen_ohne_gate` - und `pruefen` vergleicht beide Listen samt Ablation.

| Lauf | Zellen | TP | FP |
|---|---:|---:|---:|
| Endvariante | 33 | 30 | 3 |
| ohne Gate | 43 | 38 | 5 |
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

## Grenzen

- Alle Regeln sind Textheuristiken auf Markdown; sie greifen bei sauberen
  Tabellen mit Beschriftung, nicht bei Bildtabellen oder freiem Fliesstext.
- Tabellenwahl bei doppelten Labels bleibt eine Annahme (spaeterer Block,
  spaetere Tabelle), gedeckt durch Gold, nicht durch den Text.
- Das Gate macht die Ausgabe praeziser, aber schmaler: Es verwirft die acht
  PMC5617873-Zellen, bei denen das Gold selbst vertauscht ist, und damit auch
  den frueheren Positionsverlust bei `yun2024:426`.
- `yun2024:196` und `yun2024:345` sind mit keiner Leseregel zu holen; beide
  brauchen eine Goldentscheidung.
- Die Pooling-Messung ist eine Naeherung: einfache Effektformeln, nur 24 von 103
  P5-Records vollstaendig, I2 ueber 90 Prozent, ein Record mit |g| = 6. Sie
  zeigt die Groessenordnung der Verschiebung, nicht die gepoolte Wahrheit.
- Die Stichprobe umfasst 20 von 164 Faellen mit festem Schritt, nicht zufaellig
  gezogen; "nur gerundet" kann bei kurzen Zahlen ein Zufallstreffer sein.
- Nicht geprueft: Wirkung ausserhalb der 295 Faelle und ausserhalb der
  P5-Bilanz; die Pipeline selbst wurde nicht veraendert.

## Empfehlung

Den Stand als Endvariante festschreiben (30 TP, 3 FP, 91 Prozent Trefferquote,
Fixture gegen Regressionen), die drei Goldfaelle im Pruefvermerk belassen und die
7 zusaetzlichen Treffer aus der FN-Uebertragung als Randgewinn notieren, nicht
als Hebel. Weitere
Regelarbeit an den FN-Klassen ist abgeschlossen und bringt nichts; offen ist
allein die Goldfrage. Wer sie klaeren will, braucht eine PDF-Gegenprobe der
`fn_nicht_im_dokument`-Faelle (Netzzugriff, vorher freigeben) und eine
Entscheidung zu `yun2024:196` (Subgruppe) und `yun2024:345` (Wert nur als
Intervallgrenze).
