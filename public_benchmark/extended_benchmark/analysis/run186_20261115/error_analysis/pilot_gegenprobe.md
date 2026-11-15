# Gegenprobe: derselbe Pilot ohne die Gruppengrößen-Zeile (15.11.2026)

Run-ID `pilot_ohne_regel_20261116`, Modell `glm`, dieselben 12 Records,
dieselben Flags wie `pilot_repair_20261116`, zusätzlich `--no-group-size-rule`.
Der Prompt ist damit 156 Zeichen kürzer (1.776 gegen 1.620 Zeichen), sonst
identisch. Neu: `--no-group-size-rule` und `--repair` unverändert; die Zeile
`group_size_rule` steht in jeder Ergebniszeile, damit die Läufe unterscheidbar
bleiben.

## 1. Vergleich

| Kennzahl | mit Regel | ohne Regel | Differenz |
|---|---:|---:|---:|
| **Primärausfälle** (erster Aufruf am Limit) | **6/12 = 50,0 %** | **2/12 = 16,7 %** | −4 |
| **Length-Quote** (nach Reparatur) | **3/12 = 25,0 %** | **2/12 = 16,7 %** | −1 |
| leere Antworten | 0/12 | **4/12 = 33,3 %** | +4 |
| extrahierte Zellen | 23 | 24 | +1 |
| Precision | 1,0000 | 0,8333 | −0,167 |
| Recall | 0,6389 | 0,5556 | −0,083 |
| F1 | 0,7797 | 0,6667 | −0,113 |
| exakte Records | 7/12 | 5/12 | −2 |
| Tokens Primäraufrufe | 161.691 | 111.291 | −50.400 |
| Tokens Reparatur | 20.806 | 12.000 | −8.806 |
| **Tokens gesamt** | **182.497** | **123.291** | **−59.206 (−32,4 %)** |

Tokens je Pfad:

| Pfad | mit Regel | ohne Regel |
|---|---:|---:|
| standard | 6 Records, 47.691 (7.949 je Record) | 10 Records, 73.291 (7.329 je Record) |
| repair | 6 Records, 134.806 (22.468 je Record) | 2 Records, 50.000 (25.000 je Record) |

## 2. Die vier Records, die kippen

| Record | mit Regel | ohne Regel |
|---|---|---|
| `yun2024:119` | primär 19.000, Reparatur 1.197 → 2 Zellen | **11.261, 4 Zellen, 4/4 richtig** |
| `yun2024:580` | primär 19.000, Reparatur 844 → 2 Zellen | **18.631, 6 Zellen (4 ohne Gold)** |
| `yun2024:566` | primär 19.000, Reparatur 765 → 2 Zellen | **5.641, leer** |
| `yun2024:571` | 17.719, 2 Zellen | **5.987, leer** |
| `yun2024:325` | 4.428, 1 Zelle | **3.881, leer** |
| `yun2024:252` | primär 19.000 + Reparatur 6.000 → 0 | **3.269, leer** |

Unverändert: `328` (2 Zellen), `149` (4/4), `81` (6/6), `204` (2/2), `169` und
`76` (beide auch ohne Regel Length).

## 3. Was das belegt

**Die Zeile löst die Length-Ausfälle aus, nicht die Stichprobe.** Bei
identischen 12 Records und 156 Zeichen Unterschied scheitern mit Regel
6 Primäraufrufe, ohne Regel 2. Zwei Records, die vorher fehlerfrei antworteten
(`119`, `580`), laufen mit der Zeile in 19.000 Tokens und liefern ohne sie 4
beziehungsweise 6 Zellen. Das ist ein Prompt-Effekt, kein Sampling-Effekt.

**Ohne die Zeile fallen die Gruppengrößen-Records leer aus.** Genau die vier
Records (`566`, `571`, `325`, `252`), deren Gold ausschließlich
`*_group_size` enthält, antworten gültig mit leerer Zellenliste — die
Schema-Lücke, die die Zeile adressieren sollte. Die Zeile behebt also das
richtige Problem, aber mit dem falschen Mittel: +4 Records Ausgabe gegen
+4 Primärausfälle und zwei unvollständige Antworten.

**Precision sinkt ohne die Zeile auf 0,8333.** Die 4 Zellen ohne Gold stammen
alle aus `580`, das plötzlich 6 statt 2 Zellen liefert; ob sie im Artikel stehen,
ist nicht geprüft (gleiche Frage wie bei den 15 überzähligen Zellen).

**Die Reparatur bleibt in beiden Läufen nötig**, rettet aber ohne Regel nur noch
0 von 2 Fällen (`169`, `76`), weil die anderen Records gar nicht mehr ausfallen.

## 4. Korrektur am ersten Pilotbericht

`pilot_repair.md` nennt 161.691 Tokens „gesamt“ und 140.885 „primär“. Richtig
ist: **161.691 sind die Primäraufrufe**, 20.806 die Reparaturen, **182.497
gesamt** (15.208 je Record). Die Pfadsummen (47.691 + 134.806) waren korrekt;
nur die Beschriftung war falsch. `pilot_repair.py` summiert in `tokens.gesamt`
nur `completion_tokens` und trennt `repair.tokens` daneben — die Addition muss
beim Lesen erfolgen.

## 5. Urteil

| Kriterium | mit Regel | ohne Regel |
|---|---|---|
| Length ≤ 10 % | nein (25 %) | nein (16,7 %) |
| leer ≤ 5 % | **ja (0 %)** | nein (33,3 %) |
| Precision ≥ 0,70 | **ja (1,0)** | **ja (0,833)** |
| F1 ≥ 0,72 | **ja (0,780)** | nein (0,667) |

Keine der beiden Fassungen erfüllt alle Ziele. Die Regel gewinnt bei den
leeren Antworten und beim F1, verliert aber bei den Kosten (−32 % ohne Regel)
und bei der Length-Quote nach Reparatur nur knapp.

## 6. Empfehlung

**Die Zeile nicht so lassen, sondern durch eine knappe Feldvorgabe ersetzen**
(z. B. eine Zeile „Group sizes: report as `intervention_group_size` /
`comparator_group_size` with no timepoint“) und diese Fassung mit denselben
12 Records prüfen. Begründung: Die jetzige Zeile erklärt zwei Regeln
(„arm characteristics, not outcome values“ + Ausnahme von der Zeitpunktregel)
und provoziert bei 6 von 12 Records einen langen Reasoning-Lauf; die Wirkung
auf die leeren Antworten ist aber belegt (0 statt 4). Risiko: eine dritte
12-Record-Runde kostet ≈ 120.000–180.000 Tokens, und bei n = 12 ist der
Unterschied zwischen 2 und 3 Ausfällen nicht signifikant.
