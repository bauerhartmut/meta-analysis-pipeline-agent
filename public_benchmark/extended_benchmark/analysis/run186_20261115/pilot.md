# Pilotlauf über 3 Records (15.11.2026)

Freigabe: Pilot über 3 Records aus dem eingefrorenen 186er-Teilsatz, gleiche
Flags wie im Plan, eigene `--run-id`. Kein Vollauf.

## Befehl

```bash
cd D:/daswu/AIResearch
export PYTHONIOENCODING=utf-8
IDS="yun2024:35,yun2024:67,yun2024:68"

.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --records public_benchmark/extended_benchmark/records/yun_test186.jsonl \
  --split test --models glm --workers 3 --ids "$IDS" --target-fallback \
  --run-id yun_test186_pilot_20261115 \
  > public_benchmark/extended_benchmark/runs/test186_pilot.log 2>&1
```

Ausgabe: `runs/yun_test186_pilot_20261115/predictions.jsonl`, Log
`runs/test186_pilot.log`. Exit-Code 0.

## Ergebnis

| Record | Ziel im Record | prompt_version | Zellen | Zeitpunkt an jeder Zelle | Tokens | Dauer |
|---|---|---|---|---|---|---|
| `yun2024:35` | `baseline` | `v6_target_fallback` | 6 | ja (alle `baseline`) | 4.581 | 17,7 s |
| `yun2024:68` | `baseline` | `v6_target_fallback` | 2 | ja | 4.438 | 20,8 s |
| `yun2024:67` | `baseline` | `v6_target_fallback` | 2 | ja | 6.461 | 29,7 s |

* **Etikett:** alle drei Zeilen `prompt_version = v6_target_fallback` (ohne
  `_cb`, weil ohne `--cache-buster` gelaufen — so vorgesehen).
* **Zeitpunkt an den Zellen:** 10 von 10 Zellen tragen `timepoint`; bei
  `yun2024:35` mit `chosen = baseline` und `discarded = ['week 1', 'week 52']`,
  d. h. das Modell nennt den gewählten Zeitpunkt und die verworfenen.
* **Technisch sauber:** `http_status = 200`, `finish_reason = stop`,
  `parse_error` leer, `retried = False` bei allen drei.
* Gold blieb unverändert (der Lauf schreibt nur in `runs/`).

## Hochrechnung auf 186 Records (aus diesen 3 Messpunkten)

| Größe | Pilot | Hochrechnung |
|---|---|---|
| Completion-Tokens je Record | 5.160 (Mittel) | 186 × 5.160 ≈ **0,96 Mio** |
| Dauer je Aufruf | 17,7–29,7 s | bei 3 Threads ≈ **23–24 min** |

Die Tokens bestätigen die Obergrenze aus dem Plan (0,70–1,05 Mio). Die
Laufzeitschätzung ist mit n=3 grob; der langsamste Aufruf (`yun2024:67`,
29,7 s) hatte die meisten Tokens.

## Grenzen

* Alle drei Pilot-Records haben `baseline` als Ziel und **keine** Mittelwerte
  außer bei `yun2024:35` — der Rückfallpfad (`rueckfall`) und die Zeitpunktregel
  bei abweichenden Zielen sind damit **nicht** getestet.
* Drei Records sind kein Beleg für die Fehlerquote des Vollaufs; sie zeigen nur,
  dass Etikett, Rückgabeschema und Zeitpunktfeld funktionieren.
* Kein Cache-Treffer (`suspected_cache`) zu prüfen, weil der erste Lauf dieser
  Records.
