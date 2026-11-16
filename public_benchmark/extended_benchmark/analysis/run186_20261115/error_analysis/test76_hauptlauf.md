# Hauptlauf auf der Testbasis, alle 76 Records (16.11.2026)

Run-ID `test76_hauptlauf_20261116`, Modell `glm` (`gwdg/glm-5.3`), Datei
`records/yun_test76_ziel.jsonl` (SHA-256 `06fea97c…`, 76 Records, 243 Zellen),
`--split test --cell-timepoint --target-fallback --group-size-mode aus --repair
--max-tokens 19000 --workers 3`.

Kosten: **552.552 Completion-Tokens** (531.767 primär, 20.785 Reparatur) für 76
Records, 7.268 je Record; 4.657 Sekunden Rechenzeit summiert über die Records,
Wanduhr rund 40 Minuten. 12 Records liefen über den Reparaturpfad.

## 1. Gesamtkennzahlen

| Kennzahl | Wert |
|---|---|
| Zell-F1 | 0,5351 |
| Recall | 0,4239 |
| Precision | 0,7254 |
| MAE | 30,0929 |
| MAE ohne `yun2024:479` | **0,5853** auf 128 statt 130 Zellen |
| Abdeckung | 0,535 (130/243) |
| exakte Records | 16/76 |

**Die MAE ist kein Modellbefund.** Die beiden Gruppengrößen von `yun2024:479`
tragen 3.837,16 der insgesamt 3.912,08 absoluten Abweichung. Ohne diesen einen
Record liegt die MAE bei 0,5853. Details in Abschnitt 5.

## 2. Zellklassen

| Klasse | Zellen | richtig | falsch | ohne Gold | Precision |
|---|---:|---:|---:|---:|---:|
| `zieltreu` | 76 | 55 | 11 | 10 | 0,8333 |
| `rueckfall` | 48 | 32 | 16 | 0 | 0,6667 |
| `gruppengroesse_ohne_zeitpunkt` | 4 | 4 | 0 | 0 | 1,0 |
| `ohne_zeitpunkt` / `ohne_ziel` | 0 | – | – | – | – |

Belegstufen der Zeitpunktlabels: `gedruckt` 120, `artikel` 8, `ziel` 2,
`unklar` 8. Treffer mit belegter Einheit 91, Treffer allein aus dem Ziel 2.
Rückfallquote-Intervall 0,3913–0,4493 (unklar einmal nicht, einmal mitgezählt).

`unsichere_ziele`: **4 Records, 10 Zellen, 10 richtig, 0 falsch.** Die vier
abgeleiteten Ziele (`63`, `71`, `693`, `694`) sind also im Lauf vollständig
richtig getroffen — der Block zählt jetzt auch die Zellen mit, die als `unklar`
oder `rueckfall` enden.

## 3. Ausfälle und leere Antworten

34 Records liefern keine Zelle: 5 technische Ausfälle und 29 leere Antworten.
Von den 34 hat 31 ein Gold ohne Mittelwerte (leer ist dort erwartet), 3 ein Gold
mit Mittelwerten.

Technische Ausfälle:

| Record | Art | Tokens | Reparatur |
|---|---|---:|---|
| `yun2024:53` | `length_ohne_ergebnis` | 19.000 | 6.000 Tokens, wieder `length` |
| `yun2024:148` | `length_ohne_ergebnis` | 19.000 | 6.000 Tokens, wieder `length` |
| `yun2024:671` | `length_ohne_ergebnis` | 19.000 | 507 Tokens, `stop`, aber keine Zelle |
| `yun2024:52` | Read-Timeout (300 s), 0 Tokens | – | Retry lief, wieder Timeout |
| `yun2024:51` | Read-Timeout (300 s), 0 Tokens | – | Retry lief, wieder Timeout |

Beide Timeout-Records hatten ihren zweiten Versuch schon; `53` und `148` haben
19.000 plus 6.000 Tokens zweimal erfolglos verbrannt. Ein weiterer Versuch wäre
blinde Wiederholung, deshalb keiner.

## 4. Auslassungen konzentrieren sich auf Gruppengrößen

125 Auslassungen (Quote 0,5144): `intervention_group_size` 45,
`comparator_group_size` 45, `*_standard_deviation` 8+7, `*_mean` 7+6,
`*_events` 3+3. Die 31 folgenlosen Records sind genau die, deren Gold nur
Gruppengrößen enthält — dort sind die Gruppengrößen die einzige Information,
und das Modell liefert sie nicht, weil es ohne Zeitpunktbezug antwortet.

## 5. Gold-Fehler-Kandidat `yun2024:479`

Gold: `intervention_group_size` 1,919 · `comparator_group_size` 1,922 ·
`intervention_events` 1,078 · `comparator_events` 976. Gruppengrößen von 1,9
Personen sind unmöglich. Der Artikel (PMC4144850) druckt eine Tabelle:

```
Anemic: Hb<110 g/l   1,922  0.508   1,919  0.562   0.050 [-0.011 to 0.110] …
```

Das sind **1.922 und 1.919 Personen** mit Tausendertrennzeichen, nicht 1,922
Personen. Das Gold hat das Komma als Dezimaltrennzeichen gelesen. Das Modell
antwortete 1919/1922 und hatte damit recht — es wird hier für einen Gold-Fehler
bestraft, und zwar mit 3.837 der 3.912 absoluten Abweichung des ganzen Laufs.

Die Datei ist eingefroren und wurde **nicht** geändert. Eine Korrektur braucht
eine neue Version samt neuem Hash und einem neuen Bericht.

## 6. Systematischer Fehler bei „post (after 4-week training)“

Sechs Records derselben Studie (`289`, `290`, `291`, `292`, `294`, `295`) liegen
beim `comparator_mean` um 2,0 bis 8,7 zu niedrig (39,5 statt 48,2; 33,6 statt
41,3; 44,6 statt 50,8; 42,8 statt 46,5; 39,3 statt 42,8; 44,5 statt 46,5).
Der Zeitpunkt ist jeweils richtig (`Post` bzw. das volle Label), nur der Wert
stammt offenbar aus der falschen Spalte oder Zeile. Das ist der größte
inhaltliche Fehlerblock des Laufs: 6 von 27 falschen Zellen.

Weitere falsche Zellen: `yun2024:365` Komparator-Gruppengröße 20 statt 45;
`yun2024:445` 68 statt 70; `yun2024:291` SD 12,8 statt 9,8.

## 7. Überzählige Zellen

10 Zellen ohne Gold: `*_events` 5, `*_mean` 4, `*_standard_deviation` 1,
Gruppengrößen 2. Die Precision 0,7254 der Gesamtrechnung enthält diese Zellen
als Fehler; in der Klassentabelle tauchen sie als `ohne Gold` auf.

## 8. Grenzen

- Ein Modell, ein Lauf, kein Vergleichslauf auf denselben 76 Records.
- Die 243 Zellen sind die Testbasis, nicht die Trainingsmenge; ein Teil der
  Auslassungen ist Gold-Eigenschaft (Gruppengrößen ohne Zeitpunktbezug).
- `MAE` und `Precision` sind durch `yun2024:479` bzw. die überzähligen Zellen
  verzerrt; beide Zahlen ohne diese Störungen stehen oben daneben.
- Die zwei Timeout-Records sind nicht bewertet; ihre Zellen fehlen in jeder
  Kennzahl dieses Berichts.
