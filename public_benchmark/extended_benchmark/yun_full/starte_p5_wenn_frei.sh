#!/bin/bash
# Startet den P5-Lauf (103 Ausfaelle, Budget 24000) erst dann, wenn Nachtlauf und
# Nachzug wirklich fertig sind, und wertet ihn direkt mit werte_p5_aus.py aus.
#
# Woran "fertig" erkannt wird:
#   1. kein Extraktionsprozess fuer den fremden Lauf (lauf_status.py, "Prozesse: 0");
#      `kill -0` taugt unter Git Bash nicht, es meldet einen laufenden
#      Windows-Prozess als beendet (am 18.11. fuer die Windows-PID 3952 gesehen).
#   2. der Nachzug lebt nicht mehr. Geprueft wird der PROZESS aus der Sperre
#      (nachzug.lock enthaelt die PID), nicht das Alter der Sperre: die Steuerung
#      wartet bis zu 720 Minuten, eine Sperre gilt aber schon nach 90 Minuten als
#      alt. Eine Alterspruefung allein wuerde P5 also starten, waehrend der
#      Nachzug noch lebt und sein Kind erst startet.
#   3. RUHE Sekunden keine neue Zeile an predictions.jsonl des fremden Laufs,
#      damit P5 nicht in der Pause zwischen zwei Etappen eines mehrteiligen
#      Laufs loslaeuft.
#
# Aufruf:
#   bash yun_full/starte_p5_wenn_frei.sh              # warten und dann starten
#   bash yun_full/starte_p5_wenn_frei.sh --pruefen    # nur Lagebild, kein Start
#   MAXWARTE=60 TAKT=30 RUHE=60 bash yun_full/starte_p5_wenn_frei.sh
#
# Ergebnis: runs/p5_start_20261118.log, danach zusaetzlich die Artefakte von
# werte_p5_aus.py. Bricht ohne Start ab, wenn die Frist ablaeuft.
set -u
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HIER/../../.." || exit 1
export PYTHONIOENCODING=utf-8

# Ueberschreibbar, damit die Erkennung ohne echten Lauf geprueft werden kann.
R=${R:-public_benchmark/extended_benchmark/runs}
FREMD=${FREMD:-yun699_8000_alle_20261117}
MEIN=${MEIN:-yun699_p5_24000_20261118}
GATE=${GATE:-$R/p5_gate_20261118.pid}
LOG=${LOG:-$R/p5_start_20261118.log}
AUSWAHL=${AUSWAHL:-public_benchmark/extended_benchmark/iterativ/ergebnisse/p5_vorbereitung_20261118.json}
MAXWARTE=${MAXWARTE:-720}   # Minuten
TAKT=${TAKT:-60}            # Sekunden zwischen zwei Pruefungen
RUHE=${RUHE:-180}           # Sekunden ohne neue Zeile gelten als Ruhe
SPERRE_MAX=${SPERRE_MAX:-10} # Minuten, in denen eine Sperre ohne sichtbaren Prozess noch gilt

for name in MAXWARTE TAKT RUHE SPERRE_MAX; do
  wert=$(eval "printf '%s' \"\${$name}\"")
  case "$wert" in
    ''|*[!0-9]*) echo "FEHLER: $name braucht eine Zahl, nicht '$wert'."; exit 2 ;;
  esac
done

PRUEFEN=0
case "${1:-}" in
  --pruefen) PRUEFEN=1 ;;
  '') ;;
  *) echo "Unbekannter Parameter: $1"; exit 2 ;;
esac

log() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

# PID-Lebendpruefung ohne kill -0: ps -W listet msys- und Windows-PID, die Sperre
# enthaelt die msys-PID. Beide Spalten werden geprueft, damit die Zuordnung nicht
# von der msys-Version abhaengt.
pid_lebt() {
  case "${1:-}" in ''|*[!0-9]*) return 1 ;; esac
  ps -W 2>/dev/null | awk -v p="$1" '$1==p || $4==p {f=1} END{exit f?0:1}'
}

prozess_status() {
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/lauf_status.py \
    --run "$FREMD" 2>/dev/null | head -1
}

prozess_aktiv() {
  case "$(prozess_status)" in
    "Prozesse: 0"*) return 1 ;;
    *) return 0 ;;   # unklare Ausgabe: im Zweifel noch nicht frei
  esac
}

# Setzt SPERRTEXT und meldet 0, wenn der Nachzug noch als aktiv gilt.
sperre_stand() {
  local l="$R/$FREMD/nachzug.lock" p
  if [ ! -f "$l" ]; then
    SPERRTEXT="keine Sperre"
    return 1
  fi
  p=$(head -1 "$l" 2>/dev/null | tr -d '[:space:]')
  if pid_lebt "$p"; then
    SPERRTEXT="Sperre PID $p lebt weiter"
    return 0
  fi
  if [ -n "$(find "$l" -mmin -"$SPERRE_MAX" 2>/dev/null)" ]; then
    SPERRTEXT="Sperre PID $p nicht sichtbar, aber juenger als ${SPERRE_MAX} min"
    return 0
  fi
  SPERRTEXT="Sperre PID $p ist verwaist"
  return 1
}

frei() { ! prozess_aktiv && ! sperre_stand; }

groesse() { stat -c %s "$R/$FREMD/predictions.jsonl" 2>/dev/null || echo 0; }

ruhe_sekunden() {
  local f="$R/$FREMD/predictions.jsonl" m
  [ -f "$f" ] || { echo "keine Datei"; return; }
  m=$(stat -c %Y "$f" 2>/dev/null || echo 0)
  echo "vor $(( $(date +%s) - m )) s"
}

if [ "$PRUEFEN" -eq 1 ]; then
  echo "Lauf: $FREMD"
  echo "Prozess: $(prozess_status)"
  sperre_stand
  echo "Nachzug: $SPERRTEXT"
  echo "Letzte Zeile: $(ruhe_sekunden) (Ruhe gilt ab ${RUHE} s)"
  if prozess_aktiv || sperre_stand; then
    echo "=> belegt, P5 wuerde warten"
    exit 1
  fi
  echo "=> frei, P5 wuerde starten"
  exit 0
fi

mkdir -p "$R"

# Eine liegen gebliebene Sperre einer harten Beendigung (SIGKILL, kein trap)
# darf einen Neustart nicht fuer die ganze Frist blockieren: entscheidend ist,
# ob der eingetragene Prozess noch lebt.
if [ -f "$GATE" ]; then
  gp=$(head -1 "$GATE" 2>/dev/null | tr -d '[:space:]')
  if pid_lebt "$gp"; then
    echo "Startwache laeuft bereits (PID $gp)."
    exit 0
  fi
  echo "Alte Wache-Sperre von PID $gp ist verwaist, uebernehme."
  rm -f "$GATE"
fi

if grep -q "^\[.*\] P5 fertig" "$LOG" 2>/dev/null; then
  echo "P5 ist laut $LOG bereits durch; kein zweiter Lauf."
  exit 0
fi

echo $$ > "$GATE"
trap 'rm -f "$GATE"' EXIT

log "Startwache laeuft (PID $$), Frist ${MAXWARTE} min, Takt ${TAKT}s, Ruhe ${RUHE}s."
start=$SECONDS
fertig=0
while [ $(( SECONDS - start )) -lt $(( MAXWARTE * 60 )) ]; do
  if prozess_aktiv; then
    log "noch belegt (Extraktion fuer $FREMD laeuft); naechste Pruefung in ${TAKT}s"
    sleep "$TAKT"
    continue
  fi
  if sperre_stand; then
    log "noch belegt ($SPERRTEXT); naechste Pruefung in ${TAKT}s"
    sleep "$TAKT"
    continue
  fi
  vorher=$(groesse)
  sleep "$RUHE"
  if [ "$(groesse)" = "$vorher" ] && ! prozess_aktiv && ! sperre_stand; then
    fertig=1
    log "frei: keine Prozesse, kein Nachzug, ${RUHE}s ohne neue Zeile"
    break
  fi
  log "Bewegung waehrend der Ruhephase; warte weiter"
done

if [ "$fertig" -ne 1 ]; then
  log "ABBRUCH: nach ${MAXWARTE} min nicht frei, P5 nicht gestartet."
  exit 1
fi

IDS=$(.venv/bin/python -c "import json;print(','.join(json.load(open('$AUSWAHL',encoding='utf-8'))['ids']))" 2>>"$LOG")
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
log "P5 fertig"
exit "$wcode"
