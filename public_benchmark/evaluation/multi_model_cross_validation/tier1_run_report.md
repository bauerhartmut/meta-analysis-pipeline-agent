# Laufbericht: drei Modelle auf GLASS

Stand: 2026-11-13
Datensatz: GLASS TrialReviewBench study results (81 Records, 54 mit abrufbarem Volltext)
Auswertung: [`tier1_scores_aligned.json`](tier1_scores_aligned.json), `--common --aligned`
Rohausgaben: `runs/tier1_20261113/predictions.jsonl`
Skripte: `run_tier1_extraction.py`, `score_tier1.py`

## Ergebnis: 54 Records, alle drei Modelle vollständig

182 Gold-Zellen, 54 Records, 28 Cluster. Jedes Modell hat jeden Record
beantwortet.

| Modell | Recall | 95 %-Bootstrap | Precision | Genauigkeit in gefundener Zeile | exakte Records | Zusatzzellen |
|---|---:|---|---:|---:|---:|---:|
| GLM 5.3 | **0,604** | 0,485-0,724 | 0,358 | 0,844 | 9 / 54 | 179 |
| DeepSeek V4.1 Flash | **0,577** | 0,469-0,681 | 0,383 | 0,851 | 8 / 54 | 153 |
| Qwen 3.5 397B | **0,571** | 0,471-0,670 | 0,510 | 0,897 | 9 / 54 | 88 |

Die Konfidenzintervalle überlappen vollständig. **Mit 54 Records und 28 Clustern
ist kein Unterschied zwischen den Modellen nachweisbar.** Das ist kein
Gleichstandsnachweis: die kleinste nachweisbare Differenz liegt bei dieser
Größe im Bereich von 9 bis 10 Prozentpunkten.

## Weitere Qwen-Varianten unter 40B

Nachgereicht wurden drei kleinere Modelle, alle über denselben Prompt und
dieselben 54 Records:

| Kennzahl | Qwen3-30B | Qwen 3.6-35B | Qwen 3.8-27B | Spanne der drei großen Modelle |
|---|---:|---:|---:|---|
| Recall | 0,566 | 0,511 | 0,566 | 0,571-0,604 |
| Precision | 0,426 | 0,503 | 0,355 | 0,358-0,510 |
| F1 | 0,486 | 0,507 | 0,436 | 0,450-0,539 |
| exakte Records | 7 / 54 | 6 / 54 | 6 / 54 | 8-9 / 54 |
| Zeilen zugeordnet | 0,778 | 0,778 | 0,833 | 0,815-0,852 |
| Genauigkeit in gefundener Zeile | 0,744 | 0,853 | 0,821 | 0,844-0,897 |
| Zusatzzellen | 113 | 76 | 167 | 88-179 |
| Aufrufe | 54 | 59 | 72 | 54-111 |
| leer / Fehler | 0 / 0 | 0 / 5 | 6 / 12 | 11-41 / 2-13 |
| Median je Record | 0,8 s | 13,1 s | 110,0 s | 4,2-49,6 s |

Drei Profile, gleiche Stichprobe: Qwen3-30B hält beim Recall mit, füllt
gefundene Zeilen aber am schlechtesten. Qwen 3.6-35B extrahiert vorsichtig —
niedrigster Recall, dafür die wenigsten Zusatzzellen und die zweitbeste
Genauigkeit in gefundener Zeile. Qwen 3.8-27B ist ein Reasoning-Modell: bei
8000 Tokens fünfmal `finish_reason: length` mit leerem Inhalt, deshalb 24000
Tokens; danach Median 110 s je Record und die schlechteste Precision im Feld.

Keiner der Abstände ist bei 54 Records signifikant. Das Tempo dagegen ist
deutlich: Qwen3-30B braucht 0,8 s je Record gegen 24 bis 50 s bei den großen
Modellen.

## Was die Zahlen sagen

- Alle drei Modelle finden rund 57-60 Prozent der Goldzellen; 40 Prozent fehlen
  oder weichen ab.
- Rund 85 Prozent der Goldzeilen werden überhaupt gefunden. Wenn die Zeile
  gefunden ist, stimmen 84-90 Prozent ihrer Zellen. Der Fehler liegt also
  überwiegend im Finden der richtigen Zeile, nicht in falschen Zahlen.
- Ganze Records korrekt: 8 bis 9 von 54 (rund 16 Prozent).
- Die Precision liegt mit 0,36-0,51 deutlich unter der Genauigkeit in
  gefundenen Zeilen, weil die Modelle zusätzliche Zeilen liefern, die zu keiner
  Goldzeile gehören (88-179 Zellen). Das ist echte Überextraktion gegenüber der
  Goldgranularität, kein Bewertungsartefakt.
- Qwen hat die höchste Precision und die geringste Überextraktion, GLM den
  höchsten Recall. Beides liegt innerhalb der Unsicherheit.

## Zeilenzuordnung

Die Modelle benennen ihre Zeilen anders als der Goldstandard (statt „Keller,
2016" schreibt Qwen „EBRT before vs during/after nivolumab"). Eine Zuordnung
über den Studiennnamen scheitert bei 0 von 41 geprüften Records. Der Auswerter
ordnet deshalb über die übereinstimmende Zahl zu (Anker: Effektgröße, dann
weitere numerische Zellen).

Einschränkung: Der Anker ist die Goldzahl selbst. Recall und Precision sind
deshalb leicht zugunsten des Modells verzerrt; belastbar ist vor allem die
Genauigkeit der übrigen Zellen einer gefundenen Zeile.

## Abdeckung

| Modell | beantwortet | fehlend |
|---|---:|---:|
| DeepSeek | 54 / 54 | 0 |
| Qwen | 54 / 54 | 0 |
| GLM | 54 / 54 | 0 |

Ein 55. Record mit Volltextangabe ließ sich nicht laden (Europe PMC HTTP 500);
26 weitere Records haben keinen offenen Volltext und waren nicht Teil des Laufs.

## Das Tokenbudget war die eigentliche Fehlerquelle

Beim ersten Durchlauf mit `max_tokens` 12000 blieben 48 Antworten leer:
`finish_reason: length`, `completion_tokens` exakt 12000, `content` leer. Das
Reasoning hatte das Budget verbraucht, bevor die JSON-Antwort begann — dasselbe
Muster wie in der GLM-Diagnose vom Vormittag, nur mit längeren Dokumenten.

Mit 24000 Tokens liefen alle 10 offenen GLM-Aufträge ohne einen einzigen Fehler
durch (0 leer, 0 Fehler). Qwen brauchte 16000 für den letzten offenen Record.
Die bereits erfolgreichen Läufe mit 12000 bleiben gültig, weil das Budget dort
nicht bindend war (`finish_reason: stop`).

## Laufdaten

- 3 Modelle: `gwdg/qwen3.5-397b-a17b`, `gwdg/deepseek-v4.1-flash-1017`,
  `gwdg/glm-5.3`, Temperatur 0.
- Prompt: Volltext (max. 45000 Zeichen), Outcome-Name, Feldliste; Antwort als
  JSON mit `rows`. Keine Nachbearbeitung, kein Few-Shot.
- Rund 200 protokollierte Aufrufe insgesamt, davon die letzten 10 GLM-Aufträge
  sequenziell mit 10 s Pause wegen der Ratengrenze (10 Anfragen pro 10 s).

## Grenzen

- 54 Records, 28 Cluster, 182 Zellen: für Modellvergleiche zu klein, um
  Unterschiede unter 9 Prozentpunkten zu erkennen.
- Precision strukturell benachteiligt (Subgruppenzeilen); Recall ist die
  belastbarere Zahl.
- Keine Arm-, Zeitpunkt-, Seiten- oder Tabellenprüfung, weil GLASS diese Felder
  nicht führt.
- Die Zeilenzuordnung ankert auf der Goldzahl; die Genauigkeit der übrigen
  Zellen ist die konservative Kennzahl.

## Einordnung

Der Weg funktioniert ohne neue Annotation: öffentlicher Goldstandard, Volltext
aus Europe PMC, drei Modelle, maschinelle Bewertung. Die Ergebnisse zeigen einen
klaren Befund (rund 60 Prozent der Goldzellen, 16 Prozent ganze Records) und
keinen Modellunterschied. Für eine Rangfolge braucht es mehr Records oder
mehrere Goldstandards, nicht mehr Rechenzeit.
