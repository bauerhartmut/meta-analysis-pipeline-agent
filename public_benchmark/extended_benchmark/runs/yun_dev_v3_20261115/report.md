# Yun-Dev-Lauf mit absoluten Ereigniszahlen (15.11.2026)

Fünfter Lauf auf denselben 43 Dev-Records, glm-5.3, frische Generierung
(`--cache-buster`, Version **`v3_abs_count_cb`**). Neu gegenüber
`v2_timepoint` ist eine Prompt-Zeile:

> „Report event counts as absolute numbers of events, never as percentages or
> rates."

Zeitpunktvorgabe, Zellformat und Record-Schema blieben unverändert. 43 Aufrufe,
alle HTTP 200, keine leer gelaufenen Retries; Median 3,06 s, Maximum 110 s.

## Vergleich mit dem letzten Lauf (v2b, frisch)

| Kennzahl | `v2b_cachebuster` | `v3_abs_count_cb` |
|---|---|---|
| **Zellen-F1** | 0,945 | **0,919** |
| **MAE** | 0,405 | **0,431** |
| **mae_coverage** | 0,988 (168/170) | **0,929 (158/170)** |
| Zellen-Recall | 0,959 | 0,900 |
| Zellen-Precision | 0,931 | 0,939 |
| exakte Records | 35/43 | 33/43 |
| vorhergesagte Zellen | 175 | 163 |
| Armvertauschung | 0/84 | 0/79 |

Der Lauf ist in allen drei berichteten Kennzahlen **schlechter** als der
vorherige. Die Precision steigt leicht, weil weniger Zellen geliefert werden —
das ist keine Verbesserung.

## Die Prompt-Zeile hat die Ereigniszahlen nicht verändert

Die drei Fälle, die als Prozentverwechslung klassifiziert waren, sind
zeichengleich geblieben:

| Record | Feld | Gold | v2b | v3 |
|---|---|---|---|---|
| yun2024:190 | intervention_events | 52 | 64 | 64 |
| yun2024:190 | comparator_events | 51 | 73 | 73 |
| yun2024:191 | intervention_events | 49 | 31 | 31 |
| yun2024:191 | comparator_events | 64 | 48 | 48 |

Auch die Feldkennzahlen sind unverändert: Recall 0,75 für beide
Ereignisfelder, MAE 3,75 bzw. 4,75. Die Zeile hat also **nichts** bewirkt, was
die Ereigniszahlen betrifft. Die frühere Deutung „48 ist die Rate 64/133 = 48,1
Prozent" beschreibt zwar die Zahl, aber das Modell hat sie nicht als Rate
verstanden und auf die Anweisung hin auch nicht korrigiert.

## Woher der Rückgang kommt

Nur 7 der 43 Records haben sich überhaupt geändert: `yun2024:1`, `:2`, `:17`,
`:18`, `:230`, `:232`, `:235`. Vier davon (`1`, `2`, `17`, `18`) haben
**0 Gold-Zellen**; dort liefert v3 weniger Zellen, was die Precision hebt und
den Recall nicht berührt.

Der eigentliche Verlust ist ein neuer Ausfall: `yun2024:232` liefert in v3
**keine Antwort** (in v2b 6 Zellen). Dieser eine Record kostet 6 der 170
Gold-Zellen und erklärt den größten Teil des Abstands in `mae_coverage`
(168 → 158 gepaarte Zellen).

Damit ist der Unterschied zwischen 0,945 und 0,919 **nicht** als systematische
Wirkung der Prompt-Zeile belegbar: Ein einzelner ausgefallener Aufruf und
weniger Zellen auf Records ohne Gold reichen aus. Für einen belastbaren
Vergleich bräuchte es mehrere frische Läufe je Version.

## Regelbasierte Prüfung

`validate_predictions.py` prüft je Lauf, ob Ereignisse die Gruppengröße
übersteigen oder negativ sind, und **markiert nur** — die Vorhersagen bleiben
unverändert.

Ergebnis für diesen Lauf: **0 Markierungen**. Auch für alle vier früheren Läufe
ergibt die Prüfung 0 Markierungen (nachträglich ausgeführt, ohne Netzlauf).

Das ist kein Fehler der Regel, sondern eine Eigenschaft der Daten: Die
Prozentverwechslungen erzeugen Werte **unter** der Gruppengröße (48 bei 133),
die Regel greift nur bei unmöglichen Werten. Sie ist damit ein billiger Schutz
gegen grobe Fehler, aber kein Detektor für das Problem, das wir haben. Auf
synthetischen Fällen ist sie getestet (4 Tests); in diesem Datensatz ist sie
inert.

## Einordnung

- Die Prompt-Zeile ist umgesetzt und dokumentiert, aber **nicht validiert als
  Verbesserung**. Sie bleibt als eigene Version getrennt; `v2_timepoint` bleibt
  die Referenz mit den besten gemessenen Zahlen.
- Der Rückgang ist überwiegend ein technischer Ausfall (`yun2024:232`), kein
  inhaltlicher Rückschritt. Beides getrennt zu halten war der Zweck der
  technischen Kennzahlen und funktioniert hier.
- 43 Records bleiben Pilotgröße; ein Unterschied von 0,026 F1 ist bei einem
  einzigen ausgefallenen Record nicht interpretierbar.

Rohdaten: `predictions.jsonl` (43 Zeilen, `prompt_version = v3_abs_count_cb`),
`eval/glm.jsonl`, `eval/glm.metrics.json`, `validation.json`.
