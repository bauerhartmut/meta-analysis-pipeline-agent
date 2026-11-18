#!/bin/bash
# Startet den P5-Lauf (103 Ausfaelle, Budget 24000) erst dann, wenn Nachtlauf und
# Nachzug wirklich fertig sind, und wertet ihn direkt mit werte_p5_aus.py aus.
#
# Warum eine Wache statt eines direkten Starts: `kill -0` taugt unter Git Bash
# nicht fuer Windows-PIDs (es meldet einen laufenden Prozess als weg), der
# Prozessstand kommt deshalb aus lauf_status.py. Zusaetzlich gilt eine
# nachzug.lock juenger als 90 Minuten als aktiver Nachzug, und gestartet wird
# erst, wenn RUHE Sekunden lang keine Zeile mehr an predictions.jsonl des
# fremden Laufs haengt. Ohne diese dritte Pruefung koennte P5 zwischen zwei
# Etappen eines mehrteiligen Laufs loslaufen.
#
# Aufruf:
#   bash yun_full/starte_p5_wenn_frei.sh
#   MAXWARTE=60 TAKT=30 RUHE=60 bash yun_full/starte_p5_wenn_frei.sh
#
# Ergebnis: runs/p5_start_20261118.log, danach zusaetzlich die Artefakte von
# werte_p5_aus.py. Bricht ohne Start ab, wenn die Frist ablaeuft.
set -u
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HIER/../../.." || exit 1
export PYTHONIOENCODING=utf-8

R=public_benchmark/extended_benchmark/runs
FREMD=yun699_8000_alle_20261117
MEIN=yun699_p5_24000_20261118
GATE="$R/p5_gate_20261118.pid"
LOG="$R/p5_start_20261118.log"
AUSWAHL=public_benchmark/extended_benchmark/iterativ/ergebnisse/p5_vorbereitung_20261118.json
MAXWARTE=${MAXWARTE:-720}   # Minuten
TAKT=${TAKT:-60}            # Sekunden zwischen zwei Pruefungen
RUHE=${RUHE:-180}           # Sekunden ohne neue Zeile gelten als Ruhe

mkdir -p "$R"
if [ -f "$GATE" ] && [ -n "$(find "$GATE" -mmin -$(( MAXWARTE + 10 )) 2>/dev/null)" ]; then
  echo "Startwache laeuft bereits (PID $(cat "$GATE" 2>/dev/null))."
  exit 0
fi
echo $$ > "$GATE"
trap 'rm -f "$GATE"' EXIT

log() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

prozess_aktiv() {
  local s
  s=$(.venv/bin/python public_benchmark/extended_benchmark/yun_full/lauf_status.py \
        --run "$FREMD" 2>/dev/null | head -1)
  case "$s" in
    "Prozesse: 0"*) return 1 ;;
    *) return 0 ;;   # unklare Ausgabe: im Zweifel noch nicht frei
  esac
}

sperre_aktiv() {
  local l="$R/$FREMD/nachzug.lock"
  [ -f "$l" ] || return 1
  [ -n "$(find "$l" -mmin -90 2>/dev/null)" ]
}

frei() { ! prozess_aktiv && ! sperre_aktiv; }

groesse() { stat -c %s "$R/$FREMD/predictions.jsonl" 2>/dev/null || echo 0; }

log "Startwache laeuft (PID $$), Frist ${MAXWARTE} min, Takt ${TAKT}s, Ruhe ${RUHE}s."
start=$SECONDS
fertig=0
while [ $(( SECONDS - start )) -lt $(( MAXWARTE * 60 )) ]; do
  if ! frei; then
    log "noch belegt (Prozess oder Sperre); naechste Pruefung in ${TAKT}s"
    sleep "$TAKT"
    continue
  fi
  vorher=$(groesse)
  sleep "$RUHE"
  if [ "$(groesse)" = "$vorher" ] && frei; then
    fertig=1
    log "frei: keine Prozesse, keine Sperre, ${RUHE}s ohne neue Zeile"
    break
  fi
  log "Bewegung waehrend der Ruhephase; warte weiter"
done

if [ "$fertig" -ne 1 ]; then
  log "ABBRUCH: nach ${MAXWARTE} min nicht frei, P5 nicht gestartet."
  exit 1
fi

IDS=$(.venv/bin/python -c "import json;print(','.join(json.load(open('$AUSWAHL',encoding='utf-8'))['ids']))")
if [ -z "$IDS" ]; then
  log "ABBRUCH: keine ids in $AUSWAHL"
  exit 1
fi

log "starte P5: 103 ids, yun699.jsonl, Budget 24000, Retry-Strategie neu"
.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
  --split "" --ids "$IDS" --models glm --workers 2 --max-tokens 24000 \
  --run-id "$MEIN" --retry-strategie neu --quelle p5_24000 >> "$LOG" 2>&1
code=$?
log "Harness beendet mit Exitcode $code"

if [ "$code" -ne 0 ]; then
  log "keine Auswertung, weil der Lauf mit $code endete"
  exit "$code"
fi

.venv/bin/python public_benchmark/extended_benchmark/yun_full/werte_p5_aus.py >> "$LOG" 2>&1
wcode=$?
log "Auswertung beendet mit Exitcode $wcode (Artefakte: iterativ/ergebnisse/p5_auswertung_20261118.{json,md})"
exit "$wcode"
