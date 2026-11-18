# Gruppengrößen bei qwen30: Modell oder Parser?

Frage aus dem Vergleich: qwen30 meldet in nur 190 von 1.286 Gold-Zellen eine
Gruppengröße. Nennt das Modell sie nicht, oder verwirft der Parser sie?

## Methode

Rohantworten speichert der Lauf nicht (`predictions.jsonl` enthält nur die
geparsten Zellen, `content_chars` und `content_len`). Ein direkter Blick in den
Modelltext ist offline also nicht möglich. Deshalb zwei Messungen, die zusammen
die Frage entscheiden:

1. **Parsertest:** Der echte Parser (`run_extended_extraction.parse_cells`) wird
   mit zehn Schreibweisen einer Gruppengröße gefüttert. Damit steht fest, welche
   Formen durchkommen und welche stillschweigend verschwinden.
2. **Antwortmuster auf der Lesekopie:** Für alle 643 Records, deren Gold eine
   Gruppengröße trägt, wird gezählt, wie oft ein Modell eine meldet, wie viele
   Zellen je Antwort kommen, wie viele Zeichen je Zelle anfallen und ob die
   Gruppen-Zellen einen Zeitpunkt tragen.

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

Der Parser ist also nicht gruppenblind: Er akzeptiert Gruppenfelder wie jedes
andere Feld. Verloren gingen nur Zellen mit abweichendem Feldnamen, falschem
Arm oder Text im Wert.

## Antwortmuster (643 Records mit Gold-Gruppengröße)

| Kennzahl | qwen30 | glm |
|---|---:|---:|
| Records, die überhaupt ein N melden | 119 (18,5 %) | 497 (77,3 %) |
| Zellen je Antwort (Median) | 4 | 4 |
| Zeichen je gelieferter Zelle (Median) | 102,5 | 98,5 |
| Gruppen-Zellen gesamt | 224 | 990 |
| davon mit Zeitpunkt | 224 (100 %) | 675 (68,2 %) |
| übrige Zellen gesamt | 1.744 | 1.164 |
| davon mit Zeitpunkt | 1.744 (100 %) | 912 (78,4 %) |

## Befund

**Der Parser ist nicht die Ursache.** Er gibt korrekt benannte Gruppengrößen
unverändert weiter — belegt durch die vier „ja"-Fälle und durch GLM, das durch
denselben Parser 990 Gruppen-Zellen bringt.

**Für ein massenhaftes stilles Verwerfen gibt es kein Längen-Signal.** Würden
qwen30s N-Zellen am Parser scheitern, stünden sie trotzdem in der Antwort: Die
Zeichen je *gelieferter* Zelle müssten dann deutlich über GLMs 98,5 liegen.
Tatsächlich liegen sie mit 102,5 fast gleich, bei identischem Median von vier
Zellen je Antwort. Die Antworten sind also nicht länger als das, was übrig
bleibt.

**Das Muster passt zur Auslassung, nicht zum Fehler.** qwen30 meldet nur in
18,5 % der Records ein N gegenüber 77,3 % bei GLM, obwohl beide denselben
Prompt und dieselbe Einstellung `group_size_mode=aus` hatten; wenn es meldet,
dann mit Zeitpunkt (224 von 224).

## Grenze der Aussage

Ohne Rohantworten lässt sich nicht zu 100 % ausschließen, dass ein Teil der
N-Zellen als `n`, `group_size` oder Arm `control` formuliert und dann verworfen
wurde. Der Parsertest zeigt genau diese Lücke, und die Längenmessung spricht
dagegen. Sicher wäre die Gegenprobe nur mit gespeichertem Modelltext; der
nächste Lauf sollte `content` mitschreiben, damit diese Frage künftig direkt
beantwortbar ist.
