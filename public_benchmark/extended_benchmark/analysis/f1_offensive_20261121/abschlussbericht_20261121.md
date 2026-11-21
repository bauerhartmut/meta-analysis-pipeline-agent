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
5. **Mittel**: Wert aus der Zielzeile im Format `Zahl +/- Zahl` oder
   `Zahl (Zahl)`; Armspalte ueber Label, Dosis und Placebo-Synonyme.
6. **Ereignisse**: Leser abgeschaltet (0 TP, 7 FP in der Vormessung).

## Ergebnis

| Kennzahl | ohne Alias | mit Alias | nur `Mittel (SD)` | Endvariante |
|---|---:|---:|---:|---:|
| Faelle | 295 | 295 | 295 | 295 |
| Zielzeile gefunden | 156 | 178 | 178 | 178 |
| gelieferte Zellen | 36 | 44 | 26 | 43 |
| TP | 30 | 34 | 22 | 38 |
| FP | 6 | 10 | 4 | 5 |
| Trefferquote | 83 % | 77 % | 85 % | **88 %** |

Zellformate in der Endvariante:

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
| Groesse | Groessenzeile | 18 | 4 |
| Mittel | `Zahl +/- Zahl` | 16 | 1 |
| Mittel | `Zahl (Zahl)` | 4 | 0 |

## Die fuenf verbleibenden FP

| Record | Feld | Regel | Gold | Ursache |
|---|---|---:|---:|---|
| `yun2024:196` | intervention_group_size | 80 | 24 | Gold aus Subgruppentabelle (MMSE-J 20-23), siehe Pruefvermerk |
| `yun2024:196` | comparator_group_size | 78 | 24 | dito |
| `yun2024:426` | intervention_group_size | 44 | 49 | bewusster Positionsverlust (Spalte 1 ist die Vergleichsgruppe) |
| `yun2024:426` | comparator_group_size | 49 | 44 | dito |
| `yun2024:345` | intervention_mean | 5.4 | 2.3 | Gold nicht als Zellwert belegt (nur Intervallgrenze), siehe Pruefvermerk |

Damit sind drei der fuenf FP Gold- oder Konventionsfragen, zwei sind der bewusst
in Kauf genommene Preis der Positionsregel.

## Einsatz in den P5-Vorhersagen

Bilanz ueber alle 699 Records, nur die 43 gelesenen Zellen ersetzt:

| Zellen | TP | FP | FN |
|---|---:|---:|---:|
| vorher | 170 | 101 | 2603 |
| alle 43 | 208 | 102 | 2565 |
| nur die 38 richtigen | 208 | 97 | 2565 |

Alle 43: +38 TP und +1 FP. Nur die richtigen: +38 TP und -4 FP, weil vier
Zellen vorhandene falsche Werte ersetzen.

## Grenzen

- Alle Regeln sind Textheuristiken auf Markdown; sie greifen bei sauberen
  Tabellen mit Beschriftung, nicht bei Bildtabellen oder freiem Fliesstext.
- Tabellenwahl bei doppelten Labels bleibt eine Annahme (spaeterer Block,
  spaetere Tabelle), gedeckt durch Gold, nicht durch den Text.
- Die Positionsregel liest die erste Datenspalte als Intervention. Sie gewinnt
  acht PMC5617873-Zellen gegen ein dort vertauschtes Gold und verliert dafuer
  zwei belegte Zellen bei `yun2024:426`.
- `yun2024:196` und `yun2024:345` sind mit keiner Leseregel zu holen; beide
  brauchen eine Goldentscheidung.
- Nicht geprueft: Wirkung ausserhalb der 295 Faelle und ausserhalb der
  P5-Bilanz; die Pipeline selbst wurde nicht veraendert.

## Empfehlung

Den Stand als Endvariante festschreiben (38 TP, 5 FP, 88 Prozent Trefferquote)
und die beiden Goldfaelle im Pruefvermerk belassen. Der naechste sinnvolle
Schritt ist keine weitere Regel, sondern die Uebertragung der Groessen- und
Mittelregel auf die uebrigen Regeln des Fehlerbildes (`fehlerursachen_20261121`),
um zu sehen, ob dieselben Bausteine dort ebenfalls tragen; das kostet nur
Offline-Zeit und kein Guthaben.
