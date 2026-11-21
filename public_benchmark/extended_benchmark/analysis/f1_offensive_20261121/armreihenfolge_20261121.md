# Armzuordnung: Kopfzeilen-Label gegen Spaltenposition

Offline, ohne Netzaufruf.

## Die vier PMC5617873-Records

* `yun2024:331` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention None, comparator None
* `yun2024:334` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention None, comparator None
* `yun2024:335` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention None, comparator None
* `yun2024:336` - Kopfzeile 40: `Placebo (n =?45)            Aripiprazole (n =?47)   Difference or ratio (95% confidence interval) P value`
  * Spalte 1: `Placebo (n =?45)` -> `comparator`
  * Spalte 2: `Aripiprazole (n =?47)` -> `intervention`
  * Gold: intervention None, comparator None

## Lesart

`label` ordnet jeden `n`-Wert ueber den Spaltennamen zu, `position` nimmt die
erste Datenspalte als Intervention und die zweite als Comparator. Bei
PMC5617873 steht `Placebo (n = 45)` in Spalte 1 und `Aripiprazole (n = 47)`
in Spalte 2; `position` liefert dort also Intervention 45, Comparator 47 und
trifft damit das Gold, das dieselbe Zuordnung fuehrt.

## Bilanz ueber die 295

| Lesart | Zellen | TP | FP | Groessenzellen richtig | Groessenzellen falsch |
|---|---:|---:|---:|---:|---:|
| label | 33 | 30 | 3 | 10 | 2 |
| position | 33 | 30 | 3 | 10 | 2 |

Richtig geworden: 0 Zellen. Falsch geworden: 0 Zellen.

| Richtung | Record | Feld | vorher | nachher | Gold |
|---|---|---|---:|---:|---:|

## Lesart der Zahlen

Standard ist die Positionsregel (`POSITIONAL = True`). Sie holt alle acht
PMC5617873-Zellen und macht dafuer die beiden Arme von `yun2024:426`
falsch: dort steht in Spalte 1 die Vergleichsgruppe, Gold folgt dem
Spaltennamen. Dieser Verlust ist bewusst und im Bericht ausgewiesen.

Das Gold der vier PMC5617873-Records ist vertauscht (Placebo-Werte als
Intervention); die Positionsregel trifft diese Konvention, die
Spaltennamen-Lesart trifft den Tabellenkopf. Beide Zahlen stehen oben.
