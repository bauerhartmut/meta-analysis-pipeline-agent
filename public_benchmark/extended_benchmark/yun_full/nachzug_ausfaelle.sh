#!/bin/bash
# Nachzug der Length-Ausfaelle, sobald der Hauptlauf beendet ist.
#
# Warum warten: `--retry-failed` liest die Fehlzeilen aus den eigenen
# predictions.jsonl. Laeuft der Hauptlauf noch, wuerden zwei Prozesse in
# dieselbe Datei schreiben (Vorfall vom 16.11. vormittags: verschenkte
# Zeilen, Duplikate, zerrissene Logzeilen).
#
# Aufruf:  bash nachzug_ausfaelle.sh [--jetzt]
#          --jetzt ueberspringt die Wartephase (nur wenn sicher fertig).
#
# Ergebnis: runs/<run>/konsole_nachzug.log, runs/<run>/nachzug_zusammenfassung.txt
set -u
cd /d/daswu/AIResearch || exit 1
export PYTHONIOENCODING=utf-8

R=public_benchmark/extended_benchmark/runs
RUN=yun699_8000_alle_20261117
LOG=$R/$RUN/konsole.log
NLOG=$R/$RUN/konsole_nachzug.log
LOCK=$R/$RUN/nachzug.lock
MAXWARTE=${MAXWARTE:-480}   # 480 x 60 s = 8 h

# --- Doppelstart-Schutz -----------------------------------------------------
if [ -f "$LOCK" ]; then
  # kill -0 taugt unter Git Bash nicht fuer Windows-PIDs, deshalb zusaetzlich
  # das Alter: eine Sperre juenger als 90 Minuten gilt als aktiv.
  if [ -n "$(find "$LOCK" -mmin -90 2>/dev/null)" ]; then
    echo "Nachzug laeuft bereits (Sperre juenger als 90 min), Abbruch."
    exit 0
  fi
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# --- Warten auf das Ende des Hauptlaufs -------------------------------------
if [ "${1:-}" != "--jetzt" ]; then
  echo "Warte auf 'fertig:' in $LOG (max ${MAXWARTE} min)"
  for i in $(seq 1 "$MAXWARTE"); do
    if grep -q "^fertig:" "$LOG" 2>/dev/null; then
      echo "Hauptlauf beendet nach ${i} Minuten."
      break
    fi
    sleep 60
  done
  if ! grep -q "^fertig:" "$LOG" 2>/dev/null; then
    echo "FEHLER: Hauptlauf nach ${MAXWARTE} Minuten nicht beendet, kein Nachzug gestartet."
    exit 1
  fi
  sleep 30
fi

# --- Ausgangsstand sichern --------------------------------------------------
cp -f "$R/$RUN/predictions.jsonl" "$R/$RUN/predictions.vor_nachzug.jsonl"
vorher=$(.venv/bin/python -c "
import json
n=0
for l in open('$R/$RUN/predictions.jsonl', encoding='utf-8'):
    if not l.strip(): continue
    r=json.loads(l)
    if r.get('fehlerklasse')=='length_ohne_ergebnis' and r['model']=='glm': n+=1
print(n)
")
echo "GLM-Ausfaelle vor dem Nachzug: $vorher"

# --- Nachzug ----------------------------------------------------------------
nohup .venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
  --split "" --max-tokens 8000 --cell-timepoint --cache-buster \
  --workers 1 --retry-failed \
  --run-id "$RUN" --quelle v7_nachzug \
  > "$NLOG" 2>&1 &
NPID=$!
echo "Nachzug gestartet, PID $NPID"

# --- Auf den Nachzug warten -------------------------------------------------
for i in $(seq 1 240); do
  if grep -q "^fertig:" "$NLOG" 2>/dev/null; then break; fi
  sleep 30
done
if ! grep -q "^fertig:" "$NLOG" 2>/dev/null; then
  echo "FEHLER: Nachzug nicht abgeschlossen, Dedupe unterlassen."
  exit 1
fi

# --- Dedupe und Zaehlung ----------------------------------------------------
.venv/bin/python public_benchmark/extended_benchmark/yun_full/dedupe_predictions.py \
  --run "$RUN" --write

.venv/bin/python - "$R" "$RUN" "$vorher" <<'PY' > "$R/$RUN/nachzug_zusammenfassung.txt"
import json, sys
from pathlib import Path
runs, run, vorher = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])

def lade(p):
    d = {}
    for l in p.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r["model"] != "glm":
            continue
        d[r["record_id"]] = r.get("fehlerklasse") or ("leer" if not r["rows"] else "ok")
    return d

alt = lade(runs / run / "predictions.vor_nachzug.jsonl")
neu = lade(runs / run / "predictions.jsonl")
ausfaelle = [k for k, v in alt.items() if v == "length_ohne_ergebnis"]
jetzt = [k for k in ausfaelle if neu.get(k) == "length_ohne_ergebnis"]
gerettet = [k for k in ausfaelle if k not in jetzt]
print(f"GLM-Ausfaelle vor dem Nachzug:      {vorher}")
print(f"im Nachzug erfolgreich:             {len(gerettet)}")
print(f"im Nachzug erneut length:           {len(jetzt)}")
print(f"stabil gescheitert (Anteil):        {len(jetzt) / max(vorher, 1) * 100:.0f} %")
PY
cat "$R/$RUN/nachzug_zusammenfassung.txt"
