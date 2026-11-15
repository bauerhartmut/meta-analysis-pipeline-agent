# Extraktionslauf über die 186 Records mit belegtem Zielzeitpunkt

Stand: 15.11.2026. **Noch nicht gestartet.** Dieser Plan beschreibt den Lauf
vollständig; die Freigabe fehlt.

## Ausgangslage

| Größe | Wert | Quelle |
|---|---|---|
| Kandidaten-Split | 262 Records | `records/yun_kandidaten.jsonl` |
| davon mit belegtem Ziel | **186** | `timepoint.target` nicht leer |
| Goldzellen dieser 186 | 566 (Median 2, max 6 je Record) | `gold.cells` |
| Prompt-Text (gekürzt auf 45.000 Zeichen) | 2.827.369 Zeichen ≈ 707.000 Tokens | `build_prompt(..., limit=45000)`; 5 Texte werden gekürzt |
| Referenz-Telemetrie | dev v6: 209.276 Completion-Tokens für 43 Records / 170 Zellen | `runs/yun_dev_v6_20261115/predictions.jsonl` |

Die 186 liegen alle im Split `test` und überschneiden sich nicht mit `dev`
(0 gemeinsame IDs), der Dev-Satz bleibt also unberührt.

## Vorbereitung (einmalig, vor dem Lauf)

```bash
cd D:/daswu/AIResearch

# 1) Eingefrorene Record-Datei der 186 MIT Zeitpunktannotation (gitignored)
.venv/bin/python - <<'PY'
import json
from pathlib import Path
ids = set(Path("public_benchmark/extended_benchmark/analysis/run186_20261115/ids.txt").read_text().strip().split(","))
src = Path("public_benchmark/extended_benchmark/records/yun.jsonl")
kan = Path("public_benchmark/extended_benchmark/records/yun_kandidaten.jsonl")
out = Path("public_benchmark/extended_benchmark/records/yun_test186.jsonl")
anno = {r["record_id"]: r for r in (json.loads(l) for l in kan.read_text(encoding="utf-8").splitlines() if l.strip())}
recs = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
sel = []
for r in recs:
    if r["record_id"] in ids:
        r = dict(r)
        r["timepoint"] = anno[r["record_id"]]["timepoint"]
        assert json.dumps(r["gold"], sort_keys=True) == json.dumps(anno[r["record_id"]]["gold"], sort_keys=True)
        sel.append(r)
assert len(sel) == 186, len(sel)
assert all((r.get("timepoint") or {}).get("target") for r in sel)
out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in sel) + "\n", encoding="utf-8")
print("geschrieben:", out, len(sel))
PY
```

**Wichtig — sonst still falsch:** `records/yun.jsonl` trägt die Auto-Annotation
nicht. Nur **4 der 186** haben dort einen Zeitpunkt (die vier manuellen
Einträge); die übrigen 182 liefen ohne Ziel und bekämen nach `bestimme_version()`
das Label `v2_timepoint` — der Lauf wäre dann kein v6-Lauf, ohne dass es im Log
auffällt. Deshalb die eingefrorene Datei übergeben und im Vorfeld prüfen:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'public_benchmark/extended_benchmark')
import run_extended_extraction as R
from pathlib import Path
sel = R.load_records('test', None, path=Path('public_benchmark/extended_benchmark/records/yun_test186.jsonl'))
print(len(sel), 'Records,', sum(1 for r in sel if (r.get('timepoint') or {}).get('target')), 'mit Ziel')
assert len(sel) == 186 and all((r.get('timepoint') or {}).get('target') for r in sel)
"
# Erwartung: 186 Records, 186 mit Ziel
```

`analysis/run186_20261115/ids.txt` enthält die 186 IDs als Komma-Liste
(2.219 Zeichen), `ids_ohne_ziel.txt` die 76 Gegenstücke.

## Exakter Befehl

```bash
cd D:/daswu/AIResearch
export PYTHONIOENCODING=utf-8

IDS=$(cat public_benchmark/extended_benchmark/analysis/run186_20261115/ids.txt)

.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --records public_benchmark/extended_benchmark/records/yun_test186.jsonl \
  --split test \
  --models glm \
  --workers 3 \
  --ids "$IDS" \
  --target-fallback \
  --run-id yun_test186_v6_20261115 \
  > public_benchmark/extended_benchmark/runs/test186_v6.log 2>&1
```

Warum diese Flags:

* `--records records/yun_test186.jsonl` — die eingefrorene Datei trägt die
  Zeitpunktannotation (neu hinzugefügte Option; Standard bleibt
  `records/yun.jsonl`). Ohne sie wäre der Lauf kein v6-Lauf, siehe Fallstrick
  oben.
* `--split test` — die 186 liegen im Test-Split; `--ids` schneidet daraus genau
  die belegten Records heraus. Ohne `--ids` liefen alle 407.
* `--models glm` — glm ist die Referenz aus v6 (zwei Läufe 0,944/0,963). Der
  Standard wäre `qwen30 glm`, also doppelte Kosten.
* `--target-fallback` ist bereits Standard und wird hier explizit gesetzt,
  damit der Befehl selbsterklärend bleibt; Version = `v6_target_fallback`.
* **kein `--cache-buster`** — diese Records wurden nie extrahiert, es gibt
  keinen Cache-Treffer zu umgehen. Bei einem Wiederholungslauf unbedingt
  `--cache-buster` **und** eine neue `--run-id` verwenden, sonst liefert das
  Gateway die erste Antwort erneut.
* `--run-id` explizit, weil der Standard nur das Datum ist und ein zweiter Lauf
  am selben Tag sonst in denselben Ordner schreibt (Wiederaufnahme-Logik würde
  vorhandene Zeilen überspringen und den Lauf stillschweigend verkürzen).

## Erwartete Kosten

Gemessen, nicht geschätzt, wo möglich:

| Posten | Wert | Herleitung |
|---|---|---|
| Modellaufrufe | 186 | ein Aufruf je Record |
| davon Retries | +7 % bis +16 % → **200–216 Aufrufe** | v6: 15.474/209.276; v6c: 28.075/177.502 |
| Prompt-Tokens | ≈ 0,71 Mio | 2.827.369 Zeichen / 4 (5 Texte gekürzt) |
| Completion-Tokens | **0,70–1,05 Mio** | 1.231 Tokens je Goldzelle × 566 = 0,70 Mio; 4.867 je Record × 186 = 0,91 Mio; mit Retries bis 1,05 Mio |
| Gesamt | **≈ 1,4–1,8 Mio Tokens** | Summe beider Posten |

Der Dev-Lauf über 43 Records kostete 209.276 Completion-Tokens; die 186 Records
haben 3,3-mal so viele Goldzellen (566 statt 170), daher die Skalierung über
Zellen und Records getrennt.

**Preis in Guthaben:** nicht angegeben, weil das Gateway-Preismodell nicht im
Repo dokumentiert ist und ich keinen Euro-Betrag erfinden will. Für die
Kostenrechnung zählt: 200–216 Aufrufe, 1,4–1,8 Mio Tokens. Wer den Preis pro
1.000 Tokens kennt, multipliziert ihn damit.

**Laufzeit:** in den Logs stehen keine Zeitstempel, also keine belastbare
Messung. Bei 3 Threads und 200–216 Aufrufen ist der Lauf ein Vielfaches des
Dev-Laufs (43 Aufrufe).

## Umgang mit den 76 Records ohne Ziel

* Sie sind **nicht** Teil dieses Laufs (`ids.txt` enthält nur die 186).
* Sie laufen später als **eigene Kohorte** mit `ids_ohne_ziel.txt`, gleicher
  Befehl, eigene `--run-id` (`yun_test76_v2_20261115`). Ohne Ziel setzt
  `bestimme_version()` automatisch `v2_timepoint`; die Zeilen sind also im
  Log erkennbar und nicht als v6 etikettiert.
* Auswertung strikt getrennt: die 76 gehen **nicht** in die MAE der 186 ein.
  Sie werden als Kohorte „ohne Ziel" mit `ohne_ziel`-Zellen ausgewiesen
  (`evaluate_fallback.py` trennt diese Klasse bereits).
* Grund für die Trennung: Bei ihnen ist der Zielzeitpunkt unbelegt; ein
  gemeinsamer MAE würde die Aussage der 186 verwässern.

## Abbruchkriterien

Nach jeweils 30 fertigen Aufträgen prüfen:

```bash
cd D:/daswu/AIResearch
.venv/bin/python - <<'PY'
import json
from pathlib import Path
p = Path("public_benchmark/extended_benchmark/runs/yun_test186_v6_20261115/predictions.jsonl")
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
tok = sum((r.get("completion_tokens") or 0) + (r.get("retry_tokens") or 0) for r in rows)
leer = sum(1 for r in rows if not (r.get("rows") or {}).get("cells"))
kaputt = sum(1 for r in rows if r.get("retry_grund"))
print(f"{len(rows)} Auftraege | {tok} Tokens | leer: {leer} | Retry: {kaputt}")
PY
```

**Abbrechen, wenn**

1. `FEHLER: kein API-Schluessel` im Log steht — das Skript endet dann selbst
   mit Code 2, es wird nichts geschrieben.
2. Mehr als **20 %** der ersten 30 Aufträge leer sind (keine Zellen) — das wäre
   ein Prompt- oder Formatbruch, kein Modellzufall.
3. Mehr als **30 %** der ersten 30 Aufträge einen Retry brauchen, oder
   `finish_reason = length` bei zwei Aufrufen hintereinander auftritt.
4. Fünf Rate-Limit-Antworten (HTTP 429) in Folge: 5 Minuten warten, dann einmal
   wiederholen; tritt es erneut auf, abbrechen (das Gateway ist dann der
   Engpass, nicht das Modell).
5. Die Completion-Tokens **1,2 Mio** überschreiten — dann ist die Schätzung
   gerissen und der Rest wird neu kalkuliert.
6. Der Lauf doppelt so lange braucht wie der Dev-Lauf bei gleicher Aufrufzahl.

Ein Abbruch ist billig: `predictions.jsonl` ist eine Zeile je Auftrag, ein
Neustart mit derselben `--run-id` macht genau dort weiter (bereits erledigte
Aufträge werden übersprungen). Kein Teil-Lauf wird gelöscht oder überschrieben.

## Nach dem Lauf

```bash
cd D:/daswu/AIResearch
export PYTHONIOENCODING=utf-8

.venv/bin/python public_benchmark/extended_benchmark/evaluate_fallback.py \
  --run yun_test186_v6_20261115 \
  --records public_benchmark/extended_benchmark/records/yun_test186.jsonl \
  --out public_benchmark/extended_benchmark/analysis/run186_20261115/fallback_eval.json

.venv/bin/python public_benchmark/extended_benchmark/evaluate_extended.py \
  --dataset yun \
  --records public_benchmark/extended_benchmark/records/yun_test186.jsonl \
  --predictions public_benchmark/extended_benchmark/runs/yun_test186_v6_20261115/predictions.jsonl \
  --out public_benchmark/extended_benchmark/analysis/run186_20261115/eval.json
```

Erwartete Artefakte: `runs/yun_test186_v6_20261115/predictions.jsonl`,
`runs/test186_v6.log`, dazu die beiden Auswertungen. MAE wird nur mit
`mae_coverage` berichtet (Regel des Repos), nie ohne Abdeckung.

## Risiken

* **Textkürzung:** 5 der 186 Artikel sind länger als 45.000 Zeichen und werden
  abgeschnitten; Goldzellen aus dem hinteren Teil können unerreichbar sein
  (bekannt aus den Dev-Läufen, dort ebenfalls so).
* **Ein Modell:** glm allein ist die Referenz, aber ein Modellvergleich ist mit
  diesem Lauf nicht möglich; dafür wäre ein zweiter Lauf mit `qwen30` nötig
  (doppelte Kosten).
* **Keine Vorab-Validierung der 186 Goldzellen:** Der Split ist auf wörtliche
  Belegbarkeit geprüft (84,08 % wörtlich belegt), nicht auf inhaltliche
  Richtigkeit jedes Goldwerts.
