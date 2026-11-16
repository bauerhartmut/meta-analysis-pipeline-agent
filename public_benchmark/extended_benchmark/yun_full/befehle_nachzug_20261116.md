# Befehlsfolge fuer den Lauf `yun699_8000_alle_20261117`

Stand: 16.11.2026. Der Lauf laeuft; diese Datei beschreibt nur, was **nach**
seinem Ende zu tun ist. Nichts hier greift in einen laufenden Prozess ein.

## Vorher: Split-Falle

Harness und Auswertung haben unterschiedliche Standardwerte:

| Werkzeug | Standard fuer `--split` | Wirkung |
|---|---|---|
| `run_extended_extraction.py` | `dev` | laedt nur 43 von 699 Records |
| `auswerte_yun699.py` | `None` | kein Filter, wertet alle Zeilen der Datei aus |

Der laufende Lauf wurde mit `--split ""` gestartet und enthaelt daher alle 699
Records. Wer das Harness kuenftig ohne `--split ""` startet, bekommt 43 Records
und wuerde bei der Auswertung eine Metrik ueber 43 Records erhalten, die wie ein
voller Lauf aussieht. Deshalb: **beim Start immer `--split ""`, beim Auswerten
ohne `--split`.**

## 1. Status pruefen

```bash
cd /d/daswu/AIResearch
export PYTHONIOENCODING=utf-8
.venv/bin/python public_benchmark/extended_benchmark/yun_full/lauf_status.py \
  --run yun699_8000_alle_20261117 --erwartet 2094
```

Erwartet am Ende: `Prozesse: 0`, `2094/2094`, `0 Duplikate`, Exit-Code 0.
Exit-Code 1 heisst: mehrere Prozesse oder Duplikate, dann erst klaeren.

## 2. Fehlzeilen nachziehen

Nur ausfuehren, wenn oben `Prozesse: 0` steht. `--retry-failed` findet die
Fehlzeilen selbst, es muss keine Zahl eingetragen werden.

```bash
.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm qwen qwen30 \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
  --split "" --max-tokens 8000 --cell-timepoint --cache-buster --workers 3 \
  --run-id yun699_8000_alle_20261117 --quelle v7_nachzug --retry-failed
```

Option `--repair` ergaenzen, wenn die Wiederholungen mit 8000 Tokens erneut in
`length` laufen: dann wird einmal mit 24000 Tokens nachgefasst. Das ist eine
andere Bedingung; die Zeilen tragen `quelle=v7_nachzug` und sind in der
Auswertung getrennt erkennbar.

## 3. Duplikate entfernen

Pflichtschritt: `--retry-failed` haengt neue Zeilen an und laesst die alten
Fehlzeilen stehen. `auswerte_yun699.py` dedupliziert nicht (Zeile 76), jeder
wiederholte Record ginge sonst doppelt in die Metrik ein.

```bash
.venv/bin/python public_benchmark/extended_benchmark/yun_full/dedupe_predictions.py \
  --run yun699_8000_alle_20261117 --write
```

Regel: je `(record_id, model)` gewinnt die letzte nicht fehlgeschlagene Zeile;
gibt es keine, bleibt die letzte Fehlzeile als Ausfall sichtbar. Gesichert wird
vorher nach `predictions.jsonl.bak`.

## 4. Auswerten

```bash
.venv/bin/python public_benchmark/extended_benchmark/yun_full/auswerte_yun699.py \
  --run yun699_8000_alle_20261117 \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl
```

Danach je Modell getrennt pruefen, ob die Zahl der ausgewerteten Records der
Zahl der erfolgreichen Zeilen entspricht. Weichen sie ab, ist die Dedupe
schiefgelaufen.

## Erwartete Groessenordnung

Aus dem Zwischenstand bei 97 GLM-Records: 8,2 % technische Ausfaelle
(`length`), 4,1 % leere Antworten. Hochgerechnet auf 699 sind das rund 57
technische Ausfaelle pro Modell. Fuer Qwen 397B und Qwen 30B lagen zum
Zeitpunkt dieses Zwischenstands noch keine eigenen Werte vor.
