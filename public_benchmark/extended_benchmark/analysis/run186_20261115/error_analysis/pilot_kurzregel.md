# Dritte Fassung: knappe Feldvorgabe statt zwei Regelsätze (15.11.2026)

Run-ID `pilot_kurzregel_20261116`, dieselben 12 Records, `glm`,
`--cell-timepoint --target-fallback --group-size-mode kurz --max-tokens 19000
--repair`. Der Prompt ist damit 132 Zeichen kürzer als die lange Fassung
(1.644 gegen 1.776) und 24 Zeichen länger als ohne Zeile (1.620).

Neu im Code: `--group-size-mode {aus,lang,kurz}`, **Standard `aus`**. Die
Auswert-Ausnahme für `*_group_size` ohne Zeitpunkt bleibt unverändert
(`evaluate_fallback.py`, Klasse `gruppengroesse_ohne_zeitpunkt`).

## 1. Drei Fassungen im Vergleich (identische 12 Records)

| Kennzahl | `lang` (zwei Regelsätze) | `aus` (keine Zeile) | `kurz` (Feldvorgabe) |
|---|---:|---:|---:|
| **Primärausfälle** | **6/12 = 50,0 %** | **2/12 = 16,7 %** | **5/12 = 41,7 %** |
| Length nach Reparatur | 3/12 = 25,0 % | 2/12 = 16,7 % | 2/12 = 16,7 % |
| leere Antworten | 0/12 | 4/12 = 33,3 % | **2/12 = 16,7 %** |
| Zellen | 23 | 24 | **27** |
| Precision | **1,0000** | 0,8333 | 0,8519 |
| Recall | 0,6389 | 0,5556 | 0,6389 |
| F1 | **0,7797** | 0,6667 | 0,7302 |
| exakte Records | 7/12 | 5/12 | 6/12 |
| Tokens standard-Pfad | 47.691 (6) | 73.291 (10) | 58.176 (7) |
| Tokens repair-Pfad | 134.806 (6) | 50.000 (2) | 111.000 (5) |
| **Tokens gesamt** | **182.497** | **123.291** | **169.176** |
| Tokens je Record | 15.208 | 10.274 | 14.098 |

## 2. Was die kurze Fassung leistet

**Sie halbiert die leeren Antworten, aber nicht die Ausfälle.** Von den vier
Gruppengrößen-Records, die ohne Zeile leer antworten, liefern mit `kurz` zwei
Zellen (`566` mit Header „week 4“, `325` mit einer Zelle); `571` und `252`
bleiben leer. Gleichzeitig laufen drei Records, die ohne Zeile normal antworten,
jetzt primär in 19.000 Tokens: `149`, `81` und `204` — alle drei werden durch
die Reparatur gerettet (1.756, 1.562, 682 Tokens).

Damit gilt: **jede Zeile zu Gruppengrößen erhöht die Schleifenneigung**, die
kurze weniger als die lange (5 statt 6 von 12), aber deutlich gegenüber keiner
Zeile (2 von 12). Der Unterschied zwischen 5 und 6 ist bei n = 12 nicht
signifikant; der zwischen 5 und 2 ist der einzige belastbare Befund dieser
Reihe.

**Precision 0,8519 kommt nicht von Fehlwerten.** 23 von 27 Zellen sind richtig,
0 falsch, 4 ohne Gold; die vier überzähligen stammen wie in der Gegenprobe aus
`580` (6 statt 2 Goldzellen). Ob sie im Artikel stehen, ist ungeprüft.

## 3. Einordnung

| Ziel | `lang` | `aus` | `kurz` |
|---|---|---|---|
| Length ≤ 10 % | nein | nein | nein |
| leer ≤ 5 % | ja | nein | nein |
| Precision ≥ 0,70 | ja | ja | ja |
| F1 ≥ 0,72 | ja | nein | ja |

Alle drei Fassungen verfehlen die Length-Schwelle; `kurz` verfehlt zusätzlich
das Leer-Ziel, `aus` verfehlt beides und den F1. **Keine der drei ist
publikationsreif.** Die Ursache ist nicht mehr die Gruppengrößen-Zeile allein:
Auch ohne sie bleiben 2 von 12 Records (`169`, `76`) im Loop, beide mit
Gold-Konflikt beziehungsweise ohne jede Ausgabe in zwei unabhängigen Läufen.

## 4. Empfehlung aus den Messungen

**Standard `aus` beibehalten (umgesetzt) und die vier Gruppengrößen-Records
getrennt behandeln, statt den Prompt weiter zu tunen.** Begründung: Die Zeile
kostet in beiden Fassungen mehr, als sie bringt (4 zusätzliche Primärausfälle,
+59.206 Tokens in `kurz` gegen `aus`), und ihr Nutzen ist auf 2 von 4 leeren
Records begrenzt. Der saubere Weg ist ein Schema-/Nachbearbeitungsschritt:
Gruppengrößen aus dem Methodenteil getrennt abfragen oder aus
`intervention_n`/`comparator_n` des Records übernehmen, wenn sie dort stehen.
Risiko: Das ist ein neuer Extraktionspfad und braucht einen eigenen Test; die
billigere Zwischenlösung ist, die 2 verbleibenden leeren Antworten als
Auslassung zu akzeptieren.
