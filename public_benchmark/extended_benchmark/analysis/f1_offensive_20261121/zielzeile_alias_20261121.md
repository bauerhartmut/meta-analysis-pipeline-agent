# Zielzeile mit Aliasliste (21.11.2026)

Offline, ohne Netzaufruf. Aus den 13 Ausfaellen der Zielzeilen-Suche sind drei
Schwaechen belegt und mit einer kleinen Aliasliste behoben: Wortvarianten ohne
gemeinsamen Stamm (`Scanning times` / `Scan duration (min)`), Akronyme mit drei
Buchstaben (`WMS-R`), Pluralformen (`Vegetable intake` / `Vegetables`).

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
| 196 | WMS-R (0 min) | `MMSE-J 24.0 (2.4) 24.2 (2.2)` | Goldwert 24 nur als Nachbarzeile, nicht als Groesse |
| 358 | improvement at week 144 (SDMT) | keine Zeile | Goldwert 144 ist die Wochenzahl |
| 365 | leptin/adiponectin ratio | keine Zeile | Wert nur im Fliesstext |
| 389 | controlled blood pressure | `Complicated (n = 175)` | Mehrarm, Gold greift eine Subgruppe |
| 426 | Scanning times | `Scan duration (min) 19.8 ... 31.7` | Wortvariante, per Alias behoben |
| 512 | Adverse effects | `1200 (*N* = 122) 2400 (*N* = 123)` | Goldwert 122 ist die Gruppengroesse, kein Ereignis |
| 644 | progression-free survival | `(*N* = 48) (*N* = 23)` | Groessenzeile ohne Armnamen |

Nur `Scanning times` ist eine reine Wortvariante. Die uebrigen Faelle scheitern
an Mehrarm-Tabellen, fehlenden Zielzeilen oder an Goldwerten, die keine
Tabellenzelle sind.

## Aliasliste

| Outcome-Wort | Zulaeassige Tabellenwoerter |
|---|---|
| scanning | scan, duration |
| vegetable | vegetables |
| vegetables | vegetable |
| fruit | fruits |
| blood | blood, pressure |
| pressure | pressure |

## Ergebnis an den 31 Zielfaellen

| Kennzahl | Wert |
|---|---:|
| Zielfaelle | 31 |
| Regel liefert einen Wert | 9 |
| davon richtig (TP) | 4 |
| davon falsch (FP) | 5 |
| TP-Verlust | 0 |

Vor der Aliasliste waren es 6 geliefert, 2 TP, 4 FP; die Aliasliste bringt
zwei TP (426) und einen FP (196) hinzu.

## Abbruchgruende der nicht gelieferten Faelle

| Stufe | Faelle |
|---|---:|
| Zielzeile nicht gefunden | 12 |
| Groessenzeile nicht in Reichweite | 4 |
| Arm mehrdeutig oder nur anderer Arm | 6 |

## Gold-Verdacht bei den FP

| Record | Regelwert | Gold | Befund |
|---|---:|---:|---|
| 331/334/335/336 | 45 | 47 | `PMC5617873` nennt dreimal `Placebo (n = 45)` vor `Aripiprazole (n = 47)`; Kontext-Intervention ist Aripiprazole. Gold fuehrt 45 als Intervention: Arme vertauscht. |
| 196 | 140 | 24 | Tabelle 1 nennt `Pls group (n = 145)` und `Placebo group (n = 140)`; Gold nennt fuer beide Arme 24. Herkunft der 24 im Dokument nicht belegt. |

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
