# Nachzug der GLM-Ausfälle: Startprotokoll

Gestartet am 2026-11-18 um 12:22 (Ortszeit), nach Freigabe durch den Nutzer.

## Befehl

```
bash public_benchmark/extended_benchmark/yun_full/nachzug_ausfaelle.sh --repair \
  > public_benchmark/extended_benchmark/runs/yun699_8000_alle_20261117/nachzug_steuerung.log 2>&1
```

## Zustand beim Start

| Punkt | Wert |
|---|---|
| Nachtlauf `yun699_8000_alle_20261117` | läuft, PID 3952 |
| Zeilen in `predictions.jsonl` | 1.619, 0 Duplikate, 0 unlesbar |
| glm | 699 Records, 104 failed, 36 leer |
| qwen | 221 von 699 (offen: 478) |
| qwen30 | 699, fertig |
| Steuerskript | PID 2153, Sperre `nachzug.lock` gesetzt |
| Frist für das Warten | 720 Minuten (`MAXWARTE`) |

Die erste Logzeile lautet „Warte, bis kein Extraktionsprozess mehr laeuft
(max 720 min)." Das Skript prüft dafür `lauf_status.py --run` und wartet, bis dort
`Prozesse: 0` steht; ein fremder Lauf mit anderer run-id blockiert nicht.

## Was danach automatisch passiert

1. Sicherung nach `predictions.vor_nachzug.jsonl`.
2. Zählung der GLM-Length-Ausfälle vor dem Nachzug.
3. Harness-Aufruf mit `--retry-failed --repair`, `--workers 1`, `--cache-buster`,
   24.000 Tokens und `--quelle v7_nachzug`. Die Rohantwort wird mitgeschrieben
   (`content`, bei Reparatur zusätzlich `content_primaer`), weil `--save-content`
   seit Commit `586dd18` voreingestellt ist.
4. Warten auf das Kind über `kill -0` und `wait`; ein gestorbenes Kind bricht die
   Wartephase sofort ab (Exitcode 2).
5. `dedupe_predictions.py --run ... --write` und Zusammenfassung.

## Erwartung

Laut `retry_plan_glm.md` sind es 103 repair-Records mit 423 Zellen und rund
824.000 Tokens (Schätzung aus dem Retry-Plan, nicht gemessen). Die Ausfallzahlen
der 104 failed-Records verteilen sich auf `length_ohne_ergebnis` und
`json_kaputt`; `--retry-failed` fasst beide an.

## Prüfen

```
python public_benchmark/extended_benchmark/yun_full/lauf_status.py --run yun699_8000_alle_20261117
cat public_benchmark/extended_benchmark/runs/yun699_8000_alle_20261117/nachzug_steuerung.log
tail -20 public_benchmark/extended_benchmark/runs/yun699_8000_alle_20261117/konsole_nachzug.log
```

Wenn der Nachtlauf die Frist von 720 Minuten überschreitet, bricht das Skript mit
Exit 1 ab, ohne einen Nachzug zu starten; die Sperre bleibt liegen und gilt nach
90 Minuten als abgelaufen.
