# Pilot v7 auf sechs gescheiterten Records (15.11.2026)

Freigabe: „mach das" auf die Empfehlung, den Pilot nach Abschnitt 4.4 des
Konzepts zu starten. Run-ID `pilot_len_b_20261116`, Modell `glm`,
`--cell-timepoint --target-fallback --max-tokens 19000 --workers 2`.

## 1. Auswahl

`pilot_len.py --waehlen` nimmt die 47 Length-Fehlzeilen des v6-Laufs und wählt
sechs deterministisch, gleichmäßig über die sortierte Artikellänge verteilt
(2.999 bis 49.917 Zeichen):

`yun2024:325`, `yun2024:117`, `yun2024:580`, `yun2024:161`, `yun2024:685`,
`yun2024:115`.

## 2. Ergebnis

| Record | Ziel | Zellen (v7) | Goldzellen | v6 vorher | Header | Prüfung |
|---|---|---|---|---|---|---|
| `yun2024:115` | month 4 | 4 | 6 | leer (24.000 Tokens) | „4-month follow-up" | belegt, fallback stimmig |
| `yun2024:117` | month 6 | 3 | 3 | leer (24.000 Tokens) | „6 months" | belegt, fallback stimmig |
| `yun2024:580` | follow-up | 2 | 2 | leer | „1-month follow-up" | belegt, fallback stimmig |
| `yun2024:161` | month 24 | 4 | 6 | leer | „24 m" | belegt, fallback stimmig |
| `yun2024:325` | baseline | 0 | 2 | leer | – | leere Zellenliste, gültiges JSON |
| `yun2024:685` | baseline | 0 | 2 | leer | – | erneut `length`, 19.000 Tokens |

**5 von 6** liefern parsebares JSON mit `finish_reason = stop`, zusammen 13
Zellen für 17 der 21 Goldzellen dieser Records. Header sind in allen vier
Fällen wörtlich im Artikel belegt, `fallback` ist überall stimmig (`false` =
Zielzeitpunkt).

## 3. Kontrolle: der Prompt ist der Hebel, nicht das Limit

`yun2024:115` und `yun2024:117` sind unter v6 **bei 24.000 Tokens** gescheitert
(erster Lauf, Abschnitt 2) und liefern unter v7 bei **19.000** Zellen. Ein
höheres Limit kann die Verbesserung also nicht erklären; die Änderung ist
Schema und Regel.

## 4. Urteil nach den vorab festgelegten Kriterien

| Kriterium | Vorgabe | gemessen | erfüllt |
|---|---|---|---|
| Erfolge | mindestens 5 von 6 | 5 von 6 (83,3 %) | **ja** |
| Median Tokens | ≤ 6.000 | 8.951 | **nein** |

Damit ist `pilot_urteil.bestanden = false` — nicht wegen der Form, sondern wegen
der Kosten. Die Antworten sind unter v7 im Median etwa doppelt so teuer wie die
gültigen v6-Antworten (4.425).

Variante A (v6 + Reasoning-Parameter) ist **nicht gelaufen**: Der Client sendet
nur `max_tokens` und `temperature`, ein Reasoning-Budget kennt er nicht. Die
Entscheidungstabelle des Konzepts ist damit nur auf B anwendbar; B ist formal
bestanden.

## 5. Kosten

| Posten | Tokens |
|---|---|
| Pilot gesamt (6 Records) | 58.166 |
| davon der eine Ausfall | 19.000 |
| Median Erfolg | 8.951 |

Projektion Vollauf v7 über 186 Records **[Schätzung]**: 0,833 × 8.951 +
0,167 × 19.000 = 10.630 je Record, also ≈ 1,98 Mio Completion-Tokens — mehr als
die 1,71 Mio von v6, aber bei 83 % statt 75 % Abdeckung.

Projektion nur für die 47 Fehlzeilen **[Schätzung]**: ≈ 500.000 Tokens. Das ist
der billigere Weg zu vollständiger Abdeckung (Konzept, Rang 3).

## 6. Grenzen

* Sechs Records, alle vorher gescheitert: der Pilot zeigt, dass v7 diese Fälle
  löst, er schätzt nicht die Ausfallquote des Gesamtlaufs.
* `yun2024:325` liefert gültiges JSON, aber keine Zellen. Ob der Artikel dort
  wirklich nichts berichtet (Ziel `baseline`), ist nicht geprüft.
* `yun2024:685` bleibt ein Ausfall; ein Muster ist bei n = 1 nicht ableitbar.
* Die Trefferqualität der neuen Zellen ist nicht bewertet — das Urteil war
  bewusst auf die Form beschränkt.

## 7. Empfehlung

**v7 nur für die 47 Fehlzeilen laufen lassen und mit den v6-Zeilen
zusammenführen, statt 186 Records neu zu extrahieren.** Begründung: Der Pilot
zeigt 5 von 6 geretteten Records bei ≈ 58.000 Tokens; hochgerechnet auf die 47
Fehlzeilen sind das ≈ 0,5 Mio statt ≈ 2,0 Mio für einen Vollauf, bei gleicher
Abdeckung. Risiko: zwei Prompt-Fassungen in einem Datensatz — deshalb braucht
jede Zeile ein `quelle`-Feld und der Bericht eine getrennte Ansicht, wie im
Konzept vorgesehen.
