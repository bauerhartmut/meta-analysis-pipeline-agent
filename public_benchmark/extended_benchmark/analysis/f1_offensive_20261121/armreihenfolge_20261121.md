# Armzuordnung: Kopfzeilen-Label gegen Spaltenposition

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

## Lesart

`label` ordnet jeden `n`-Wert ueber den Spaltennamen zu, `position` nimmt die
erste Datenspalte als Intervention und die zweite als Comparator. Bei
PMC5617873 steht `Placebo (n = 45)` in Spalte 1 und `Aripiprazole (n = 47)`
in Spalte 2; `position` liefert dort also Intervention 45, Comparator 47 und
trifft damit das Gold, das dieselbe Zuordnung fuehrt.

## Bilanz ueber die 295

| Lesart | Zellen | TP | FP | Groessenzellen richtig | Groessenzellen falsch |
|---|---:|---:|---:|---:|---:|
| label | 41 | 28 | 13 | 12 | 10 |
| position | 41 | 34 | 7 | 18 | 4 |

Richtig geworden: 8 Zellen. Falsch geworden: 2 Zellen.

| Richtung | Record | Feld | vorher | nachher | Gold |
|---|---|---|---:|---:|---:|
| richtig | `yun2024:331` | comparator_group_size | 45.0 | 47.0 | 47.0 |
| richtig | `yun2024:331` | intervention_group_size | 47.0 | 45.0 | 45.0 |
| richtig | `yun2024:334` | comparator_group_size | 45.0 | 47.0 | 47.0 |
| richtig | `yun2024:334` | intervention_group_size | 47.0 | 45.0 | 45.0 |
| richtig | `yun2024:335` | comparator_group_size | 45.0 | 47.0 | 47.0 |
| richtig | `yun2024:335` | intervention_group_size | 47.0 | 45.0 | 45.0 |
| richtig | `yun2024:336` | comparator_group_size | 45.0 | 47.0 | 47.0 |
| richtig | `yun2024:336` | intervention_group_size | 47.0 | 45.0 | 45.0 |
| falsch | `yun2024:426` | comparator_group_size | 44.0 | 49.0 | 44.0 |
| falsch | `yun2024:426` | intervention_group_size | 49.0 | 44.0 | 49.0 |

## Lesart der Zahlen

Standard ist die Positionsregel (`POSITIONAL = True`). Sie holt alle acht
PMC5617873-Zellen und macht dafuer die beiden Arme von `yun2024:426`
falsch: dort steht in Spalte 1 die Vergleichsgruppe, Gold folgt dem
Spaltennamen. Dieser Verlust ist bewusst und im Bericht ausgewiesen.

Das Gold der vier PMC5617873-Records ist vertauscht (Placebo-Werte als
Intervention); die Positionsregel trifft diese Konvention, die
Spaltennamen-Lesart trifft den Tabellenkopf. Beide Zahlen stehen oben.
