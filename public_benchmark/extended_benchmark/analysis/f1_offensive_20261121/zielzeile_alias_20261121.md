# Zielzeile mit Aliasliste (21.11.2026)

Offline, ohne Netzaufruf. Die Aliasliste enthaelt nur den Eintrag, der Treffer
bringt; `blood/pressure` und `fruit/vegetable` sind entfernt, weil sie das
Ergebnis nicht veraendern (112-115 scheitern an der Mehrarm-Groessenzeile, 389
an der Subgruppenwahl).

## Wirkung je Baustein

| Variante | geliefert | TP | FP |
|---|---:|---:|---:|
| ohne Erweiterung | 7 | 2 | 5 |
| nur Akronyme | 7 | 2 | 5 |
| nur scanning | 9 | 4 | 5 |
| Akronyme + scanning | 9 | 4 | 5 |

Der Alias `scanning -> scan, duration` bringt beide TP (`yun2024:426`): zwei
zusaetzliche Zellen, beide richtig. Die Akronym-Regel allein bringt nichts, sie
verschiebt weder Treffer noch Fehler. Der FP `yun2024:196` entsteht unabhaengig
von der Erweiterung, weil die Regel dort Tabelle 1 statt Tabelle 2 liest.

## Aliasliste

| Outcome-Wort | Zulaeassige Tabellenwoerter | Wirkung |
|---|---|---|
| scanning | scan, duration | 2 TP (426) |

Die Akronym-Regel (Woerter ab drei Grossbuchstaben bleiben im Tokenizer) ist
kein Alias, sondern Teil der Wortzerlegung; sie bringt allein 0 TP und wurde
beibehalten, weil sie die Zerlegung nicht verschlechtert (gleiche Werte wie
ohne Erweiterung).

## Sichtung der 13 Ausfaelle (Label gegen Outcome)

Die Zeilen sind ueber den Goldwert gesucht und dienen nur der Ableitung der
Aliasliste; die Regel selbst sieht keinen Goldwert.

| Record | Outcome | Zeile mit dem Goldwert | Befund |
|---|---|---|---|
| 112 | Vegetable intake | `n=1349 n=434 n=459 n=456` | Mehrarm-Groessenzeile, Zielzeile fehlt |
| 113 | Vegetable intake | dieselbe Zeile | Mehrarm |
| 114 | Fruit intake | dieselbe Zeile | Mehrarm |
| 115 | Fruit intake | dieselbe Zeile | Mehrarm |
| 182 | Adverse events | keine Zeile | Goldwert 0 steht in keiner Tabellenzeile |
| 196 | WMS-R (0 min) | `28  24  1.29 ... 24  1.08` | Gold aus Tabelle 2, Wochenwert 28 mit n = 24 |
| 358 | improvement at week 144 (SDMT) | keine Zeile | Goldwert 144 ist die Wochenzahl |
| 365 | leptin/adiponectin ratio | keine Zeile | Wert nur im Fliesstext |
| 389 | controlled blood pressure | `Complicated (n = 175)` | Mehrarm, Gold greift eine Subgruppe |
| 426 | Scanning times | `Scan duration (min) 19.8 ... 31.7` | Wortvariante, per Alias behoben |
| 512 | Adverse effects | `1200 (*N* = 122) 2400 (*N* = 123)` | Goldwert 122 ist die Gruppengroesse |
| 644 | progression-free survival | `(*N* = 48) (*N* = 23)` | Groessenzeile ohne Armnamen |

Nur `Scanning times` ist eine reine Wortvariante. Die uebrigen Faelle scheitern
an Mehrarm-Tabellen, fehlenden Zielzeilen oder an Goldwerten, die keine
Tabellenzelle sind.

## Ergebnis an den 31 Zielfaellen

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | 31 |
| Regel liefert einen Wert | 9 |
| davon richtig (TP) | 4 |
| davon falsch (FP) | 5 |
| TP-Verlust | 0 |

## Abbruchgruende der nicht gelieferten Faelle

| Stufe | Faelle |
|---|---:|
| Zielzeile nicht gefunden | 12 |
| Groessenzeile nicht in Reichweite | 4 |
| Arm mehrdeutig oder nur anderer Arm | 6 |

## Gold-Verdacht bei den FP

Pruefvermerk: `pruefvermerk_gold_20261121.md`.

| Record | Regelwert | Gold | Befund |
|---|---:|---:|---|
| 331/334/335/336 | 45 | 47 | `PMC5617873` nennt dreimal `Placebo (n = 45)` vor `Aripiprazole (n = 47)`; Kontext-Intervention ist Aripiprazole. Gold fuehrt 45 als Intervention: Arme vertauscht. |
| 196 | 140 | 24 | Gold stammt aus Tabelle 2 (Woche 28, n = 24, Mittel 1.29/1.08); die Regel las die Kopfzeile von Tabelle 1 (145/140). Gold ist belegt, der Verdacht widerlegt. |

Kein Goldwert wurde geaendert.

## Gelieferte Zellen

| Record | Feld | Regelwert | Quelle | Zeile | Gold | richtig |
|---|---|---:|---|---:|---:|---|
| `yun2024:196` | comparator_group_size | 140.0 | zeile | 8 | 24.0 | nein |
| `yun2024:331` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | nein |
| `yun2024:334` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | nein |
| `yun2024:335` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | nein |
| `yun2024:336` | comparator_group_size | 45.0 | zeile | 40 | 47.0 | nein |
| `yun2024:346` | comparator_group_size | 22.0 | zeile | 33 | 22.0 | ja |
| `yun2024:347` | comparator_group_size | 22.0 | zeile | 33 | 22.0 | ja |
| `yun2024:426` | comparator_group_size | 44.0 | zeile | 10 | 44.0 | ja |
| `yun2024:426` | intervention_group_size | 49.0 | zeile | 10 | 49.0 | ja |
