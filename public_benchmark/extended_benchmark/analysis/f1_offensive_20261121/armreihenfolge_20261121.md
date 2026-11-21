# Armzuordnung: Kopfzeilen-Label gegen Spaltenreihenfolge

Offline, ohne Netzaufruf.

## Die vier PMC5617873-Records

* `yun2024:331` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention 45.0, comparator 47.0
* `yun2024:334` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention 45.0, comparator 47.0
* `yun2024:335` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention 45.0, comparator 47.0
* `yun2024:336` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention 45.0, comparator 47.0

## Bilanz der Groessenzellen

| Lesart | richtig | falsch | Zellen |
|---|---:|---:|---:|
| Label (Spaltenname) | 12 | 10 | 22 |
| Position (erste Spalte = Intervention) | 16 | 6 | 22 |

## Lesart

Die Regel ordnet jeden `n`-Wert ueber den Spaltennamen zu; das ist die
Spaltenreihenfolge des Tabellenkopfs, nur ohne Annahme ueber die erste
Spalte. Bei PMC5617873 steht `Placebo (n = 45)` in Spalte 1 und
`Aripiprazole (n = 47)` in Spalte 2; die Regel liefert deshalb
Intervention 47 und Comparator 45.

Gold fuehrt fuer dieselben Records Intervention 45 und Comparator 47,
also die Werte der Placebo-Spalte als Intervention. Ein Tausch der
Regelwerte wuerde diese acht Zellen gegen Gold richtig stellen, aber
dem Tabellenkopf widersprechen.

## Was ein Tausch kostet

Ein Tausch aller Groessenpaare stellt die acht PMC5617873-Zellen richtig,
macht aber `yun2024:193` (138/131) und `yun2024:426` (49/44) falsch, also
vier vorher richtige Zellen. Unterm Strich: 12 richtig / 10 falsch vorher,
16 richtig / 6 falsch nachher - gegen ein Gold, das an dieser Stelle selbst
vertauscht ist. Der Tabellenkopf bleibt die verlaesslichere Quelle.
