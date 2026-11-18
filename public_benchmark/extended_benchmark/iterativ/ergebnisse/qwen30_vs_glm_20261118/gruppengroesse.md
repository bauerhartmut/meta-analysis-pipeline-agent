# Gruppengrößen bei qwen30: Modell oder Parser?

qwen30 meldet in nur 190 von 1.286 Gold-Gruppen-Zellen einen Wert, 1.066 fehlen.
Nennt das Modell die Größe nicht, oder verwirft der Parser sie?

## Methode

Rohantworten speichert der Lauf nicht (`predictions.jsonl` enthält nur die
geparsten Zellen sowie `content_chars`). Ein Blick in den Modelltext ist offline
also nicht möglich. Deshalb zwei Messungen:

1. **Parsertest:** Der echte Parser (`run_extended_extraction.parse_cells`) wird
   mit zehn Schreibweisen einer Gruppengröße gefüttert.
2. **Längenvergleich mit Baseline:** Die 699 Records zerfallen in 643 mit und 56
   ohne Gold-Gruppengröße. Wo nichts zu melden ist, zeigt sich, wie viele Zeichen
   das Modell je gelieferter Zelle ohnehin braucht. Weicht die erste Gruppe davon
   ab, steckt Text in der Antwort, der beim Parsen verloren ging.

Aufruf:

```
python public_benchmark/extended_benchmark/yun_full/pruefe_gruppengroesse_qwen30.py \
    --run _lesekopie_20261118 \
    --out public_benchmark/extended_benchmark/iterativ/ergebnisse/qwen30_vs_glm_20261118/gruppengroesse.json
```

## Parsertest

| Schreibweise | kommt durch |
|---|---|
| `intervention_group_size` / Arm `intervention` / `120` | ja |
| `comparator_group_size` / Arm `comparator` / `118` | ja |
| Wert `"120,5"` (Komma) | ja |
| Wert `"120"` (String-Zahl) | ja |
| Wert `"120 patients"` | **nein** |
| Feld `n` | **nein** |
| Feld `intervention_n` | **nein** |
| Feld `group_size` | **nein** |
| Arm `control` statt `comparator` | **nein** |
| Arm fehlt | **nein** |

Der Parser ist nicht gruppenblind: Er akzeptiert Gruppenfelder wie jedes andere
Feld. Verloren gingen nur Zellen mit abweichendem Feldnamen, falschem Arm oder
Text im Wert.

## Längenvergleich

| Modell | Gruppe | Records | Zellen | Zeichen | Zeichen je Zelle (gesamt) | je Zelle (Median) | Quartile |
|---|---|---:|---:|---:|---:|---:|---|
| qwen30 | mit Gold-N | 643 | 1.968 | 211.840 | 107,6 | 102,5 | 98,8 / 102,5 / 109,3 |
| qwen30 | ohne Gold-N | 56 | 142 | 14.946 | 105,3 | 103,5 | 99,5 / 103,5 / 107,0 |
| glm | mit Gold-N | 643 | 2.154 | 210.983 | 97,9 | 98,5 | 92,8 / 98,5 / 103,5 |
| glm | ohne Gold-N | 56 | 100 | 9.806 | 98,1 | 99,5 | 77,8 / 99,5 / 103,3 |

**Der Median liegt in der Gruppe mit Gold-N sogar niedriger** (102,5 gegen 103,5)
und die Quartile überlappen fast vollständig. Rechnet man aus dem Zeichenbestand
zurück, wie viele Zellen zur Baseline passen würden, ergibt sich für qwen30 eine
Spanne von **44 (Gesamtquotient) bis 79 (Median-Baseline)** zusätzlichen Zellen,
für GLM −3 bis −34.

## Antwortmuster

| Kennzahl (643 Records mit Gold-N) | qwen30 | glm |
|---|---:|---:|
| Records, die überhaupt ein N melden | 119 (18,5 %) | 497 (77,3 %) |
| Gruppen-Zellen | 224 | 990 |
| davon mit Zeitpunkt | 224 (100 %) | 675 (68,2 %) |
| übrige Zellen | 1.744 | 1.164 |
| davon mit Zeitpunkt | 1.744 (100 %) | 912 (78,4 %) |

## Befund

**Die Schlussfolgerung hält, aber sie trägt nicht der Längentest allein.**

Der Längentest ist schwach: Eine Gruppen-Zelle kostet im JSON rund 75 Zeichen
und liegt damit nahe am Durchschnitt von etwa 105. Selbst wenn qwen30 sie
vollständig verworfen hätte, verschöbe das die Kennzahl nur um wenige Prozent —
und die Baseline stützt sich auf 56 Records. Er taugt deshalb als **Schranke,
nicht als Beweis**: Höchstens einige Dutzend Zellen (≤ 8 % der 1.066 fehlenden)
ließen sich mit verworfenem Text erklären.

Belastbar sind die beiden anderen Beobachtungen:

1. **Der Parser lässt korrekt benannte N durch** (vier Formen, darunter
   String-Zahlen und Komma) — und GLM bringt durch denselben Parser 990
   Gruppen-Zellen.
2. **Bei identischem Prompt und identischer Einstellung** `group_size_mode=aus`
   meldet qwen30 nur in 18,5 % der Records ein N, GLM in 77,3 %. Wenn qwen30
   meldet, dann immer mit Zeitpunkt (224 von 224), GLM nur zu 68 %.

Das Muster ist eine Auslassung des Modells, kein Filterverlust. Die Restlücke
bleibt: Ein Teil der N könnte als `n`, `group_size` oder Arm `control` formuliert
und still verworfen worden sein. Endgültig klären ließe sich das nur mit
gespeichertem Modelltext.
