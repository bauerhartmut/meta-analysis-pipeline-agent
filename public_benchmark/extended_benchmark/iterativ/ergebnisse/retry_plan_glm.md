# Retry-Plan GLM 5.3 (Yun-699): Stand aus der Telemetrie

Erzeugt mit `yun_full/retry_liste_glm.py` aus `runs/yun699_8000_alle_20261117`
(read-only, waehrend der Nachtlauf weiterlief). Rohdaten:
`retry_liste_glm.json`, ID-Listen: `retry_repair_ids.txt`,
`retry_leer_ids.txt`, `retry_json_kaputt_ids.txt`.

## Ausfaelle

| Gruppe | Records | fehlende Goldzellen | verbrauchte Tokens | Median Tokens | Median Textzeichen | mit Reasoning |
|---|---|---|---|---|---|---|
| `repair` (length) | 103 | **423** | 824.000 | 8.000 | 16.433 | 103 |
| `leer` (Antwort ohne Zellen) | 36 | 40 | 55.011 | 922 | 6.146 | 36 |
| `json_kaputt` | 1 | 4 | 0 | – | 40.352 | 0 |
| Summe | 140 | **467** | 879.011 | – | – | 139 |

Zum Vergleich: 559 verwertbare Records, Median 1.337 Completion-Tokens und
14.179 Textzeichen.

## Was die Zahlen sagen

- **Alle 139 Ausfaelle haben Reasoning produziert**, aber keinen verwertbaren
  Inhalt. Bei den 103 Length-Faellen sind im Median genau 8.000 Tokens
  verbraucht — das Budget war voll ausgeschoepft, das Modell hat im Denken
  aufgehoert. Ein zweiter Aufruf mit demselben Budget wiederholt das Muster.
  Deshalb `--repair`: 6.000 Tokens, Text auf 15.000 Zeichen gekuerzt.
- Die 36 leeren Antworten verbrauchen mit 922 Tokens nur ein Achtel und
  bearbeiten kuerzere Texte (Median 6.146 statt 14.179 Zeichen). Das ist kein
  Budgetproblem, sondern ein Ausgabeproblem; hier hilft die reine Wiederholung.
- Die 103 Length-Records tragen **423 der 467 fehlenden Zellen** und haben
  824.000 Tokens ohne Ergebnis gekostet — der teuerste und zugleich
  ergiebigste Block.
- 4 Zellen des `json_kaputt`-Records sind bereits automatisch wiederholt
  worden; Prioritaet niedrig.

## Befehle (erst nach Ende des Nachtlaufs)

Vorher pruefen: `lauf_status.py --run yun699_8000_alle_20261117 --erwartet 2094`
muss `Prozesse: 0` zeigen. Zwei Prozesse auf derselben `predictions.jsonl`
erzeugen Duplikate und zerrissene Zeilen (Vorfall vom 16.11.).

```bash
R=public_benchmark/extended_benchmark
RUN=yun699_8000_alle_20261117

# Block 1: 103 Length-Faelle, mit Reparaturaufruf
.venv/bin/python $R/run_extended_extraction.py --models glm \
  --records $R/yun_full/records/yun699.jsonl --split "" --max-tokens 24000 \
  --cell-timepoint --cache-buster --workers 3 --run-id $RUN --quelle v7_alle699 \
  --retry-failed --repair \
  --ids "$(cat $R/iterativ/ergebnisse/retry_repair_ids.txt)"

# Block 2: 36 leere Antworten, ohne Reparatur
.venv/bin/python $R/run_extended_extraction.py --models glm \
  --records $R/yun_full/records/yun699.jsonl --split "" --max-tokens 24000 \
  --cell-timepoint --cache-buster --workers 3 --run-id $RUN --quelle v7_alle699 \
  --retry-failed \
  --ids "$(cat $R/iterativ/ergebnisse/retry_leer_ids.txt)"

# Danach: Duplikate entfernen und neu auswerten
.venv/bin/python $R/yun_full/dedupe_predictions.py --run $RUN --write
.venv/bin/python $R/yun_full/auswerte_yun699.py --run $RUN
```

## Zwei Fallen

1. **`nachzug_ausfaelle.sh` wartet auf das falsche Log.** Das Skript sucht
   `^fertig:` in `runs/$RUN/konsole.log`; der fortgesetzte Lauf schreibt nach
   `konsole_fortsetzung2.log`. Ohne Anpassung wartet es acht Stunden und bricht
   dann ab. Entweder `LOG=` auf die Fortsetzungsdatei zeigen lassen oder nach
   `Prozesse: 0` mit `--jetzt` starten.
2. **`--retry-failed` ersetzt keine Zeilen, es haengt an.** Die alten
   Fehlzeilen bleiben stehen; erst `dedupe_predictions.py --write` macht die
   Auswertung eindeutig. Bis dahin zeigen `lauf_status.py` und
   `auswerte_yun699.py` beide Fassungen.
