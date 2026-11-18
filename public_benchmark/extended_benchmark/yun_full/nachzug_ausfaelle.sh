#!/bin/bash
# Nachzug der Ausfaelle, sobald kein Extraktionsprozess mehr laeuft.
#
# Warum nicht auf "fertig:" warten: Der Lauf kann in mehreren Etappen gelaufen
# sein (Fortsetzung nach einem Abbruch), und dann steht "fertig:" in einer
# anderen Datei als der, die dieses Skript beobachtet. Beobachtet wird deshalb
# der Prozessstand ueber lauf_status.py ("Prozesse: 0"), das Log dient nur der
# Protokollierung und ist als Parameter waehlbar.
#
# Aufruf:
#   bash nachzug_ausfaelle.sh [--log PFAD] [--run NAME] [--repair] [--jetzt]
#
#   --log PFAD    Logdatei des Hauptlaufs (Standard: runs/$RUN/konsole.log)
#   --run NAME    Run-Verzeichnis (Standard: yun699_8000_alle_20261117)
#   --repair      Reparaturaufruf fuer Length-Faelle aktivieren (6.000 Tokens)
#   --jetzt       nicht warten, sofort starten (nur wenn sicher kein Prozess laeuft)
#   --dry-run     Durchgriff ohne Netzlauf: sichert, zeigt die Auswahl, haengt
#                 Ersatzzeilen an, dedupliziert und rechnet die Zusammenfassung.
#                 Nur auf einer Kopie des Run-Verzeichnisses zulaessig.
#   --max-warte MIN  Wartezeit-Grenze in Minuten (Standard 720 = 12 h), gilt fuer
#                 das Warten auf den Hauptlauf UND fuer das Warten auf den Nachzug.
#   --takt SEK    Abfrageintervall in Sekunden (Standard 30).
#
# Nur fuer die offline-Uebung des Abbruchpfads: NACHZUG_KINDBEFEHL ersetzt den
# Harness-Aufruf durch einen beliebigen Befehl (erzeugt keine Anfrage).
#
# Ergebnis: runs/$RUN/konsole_nachzug.log, runs/$RUN/nachzug_zusammenfassung.txt
set -u
# Projektwurzel aus dem Skriptort ableiten (dieses Skript liegt in
# public_benchmark/extended_benchmark/yun_full), damit kein privater
# Absolutpfad im Repo steht.
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HIER/../../.." || exit 1
export PYTHONIOENCODING=utf-8

R=public_benchmark/extended_benchmark/runs
RUN=yun699_8000_alle_20261117
LOG=""
REPAIR=""
JETZT=0
TROCKEN=0
ECHT="yun699_8000_alle_20261117"
MAXWARTE=${MAXWARTE:-720}   # Minuten; gilt fuer das Warten auf den Hauptlauf und auf den Nachzug
TAKT=${TAKT:-30}            # Sekunden zwischen zwei Abfragen

while [ $# -gt 0 ]; do
  case "$1" in
    --log) LOG="${2:-}"; shift 2 ;;
    --run) RUN="${2:-}"; shift 2 ;;
    --repair) REPAIR="--repair"; shift ;;
    --jetzt) JETZT=1; shift ;;
    --dry-run) TROCKEN=1; JETZT=1; shift ;;
    --max-warte) MAXWARTE="${2:-}"; shift 2 ;;
    --takt) TAKT="${2:-}"; shift 2 ;;
    *) echo "Unbekannter Parameter: $1"; exit 2 ;;
  esac
done
[ -n "$LOG" ] || LOG="$R/$RUN/konsole.log"

case "$MAXWARTE" in ''|*[!0-9]*) echo "FEHLER: --max-warte braucht eine Minutenzahl, nicht '$MAXWARTE'."; exit 2 ;; esac
case "$TAKT" in ''|*[!0-9]*) echo "FEHLER: --takt braucht eine Sekundenzahl, nicht '$TAKT'."; exit 2 ;; esac
if [ "$TAKT" -lt 1 ]; then
  echo "FEHLER: --takt muss mindestens 1 Sekunde sein."
  exit 2
fi
GRENZE=$(( MAXWARTE * 60 ))   # Sekunden; beide Wartephasen messen damit dieselbe Frist

if [ "$TROCKEN" -eq 1 ] && [ "$RUN" = "$ECHT" ]; then
  echo "FEHLER: --dry-run nur auf einer Kopie (--run <kopie>) ausfuehren."
  exit 2
fi
NLOG="$R/$RUN/konsole_nachzug.log"
LOCK="$R/$RUN/nachzug.lock"

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

if [ ! -f "$R/$RUN/predictions.jsonl" ]; then
  echo "FEHLER: $R/$RUN/predictions.jsonl fehlt, nichts zu nachzuziehen."
  exit 1
fi

# --- Warten, bis kein Extraktionsprozess mehr laeuft ------------------------
# lauf_status.py prueft den Prozessstand unabhaengig davon, in welche Datei
# der Lauf schreibt, und zwar nur fuer DIESE run-id: Ein fremder Lauf mit
# anderer run-id wird als "Fremde Laeufe" gemeldet und blockiert nicht.
# "Prozesse: 0" ist die Bedingung, nicht ein Logtext.
laeuft_noch() {
  local status
  status=$(.venv/bin/python public_benchmark/extended_benchmark/yun_full/lauf_status.py \
             --run "$RUN" 2>/dev/null | head -1)
  case "$status" in
    "Prozesse: 0"*) return 1 ;;
    "Prozesse: "*) return 0 ;;
    *) return 0 ;;   # unklare Ausgabe: im Zweifel weiter warten
  esac
}

if [ "$JETZT" -eq 0 ]; then
  echo "Warte, bis kein Extraktionsprozess mehr laeuft (max ${MAXWARTE} min)."
  echo "Log (nur zur Information): $LOG"
  start=$SECONDS
  while [ $(( SECONDS - start )) -lt "$GRENZE" ]; do
    if ! laeuft_noch; then
      echo "Kein Prozess mehr aktiv nach $(( (SECONDS - start) / 60 )) Minuten."
      break
    fi
    sleep 60
  done
  if laeuft_noch; then
    echo "FEHLER: nach ${MAXWARTE} Minuten laeuft noch ein Prozess, kein Nachzug gestartet."
    exit 1
  fi
  sleep 30
else
  if laeuft_noch; then
    echo "FEHLER: --jetzt gesetzt, aber es laeuft noch ein Prozess. Abbruch."
    exit 1
  fi
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
KINDBEFEHL=(
  .venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py
  --models glm
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl
  --split "" --max-tokens 24000 --cell-timepoint --cache-buster
  --workers 1 --retry-failed $REPAIR
  --run-id "$RUN" --quelle v7_nachzug
)

if [ "$TROCKEN" -eq 1 ]; then
  echo "=== TROCKENLAUF: kein Netzlauf, keine Anfrage ==="
  echo "Sicherung: $R/$RUN/predictions.vor_nachzug.jsonl"
  echo "Auswahl, die ein echter Lauf anfassen wuerde:"
  # Der Trockenlauf des Harness prueft die Auswahl gegen die Kopie.
  .venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
    --models glm \
    --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
    --split "" --max-tokens 24000 --cell-timepoint --cache-buster \
    --workers 1 --retry-failed $REPAIR \
    --run-id "$RUN" --quelle v7_nachzug --dry-run
  # Ersatzzeilen, damit Dedupe und Zusammenfassung echten Stoff haben.
  .venv/bin/python public_benchmark/extended_benchmark/yun_full/nachzug_trocken_schreibe.py \
    --run-verzeichnis "$R/$RUN" --anzahl 2
else
  if [ -n "${NACHZUG_KINDBEFEHL:-}" ]; then
    nohup bash -c "$NACHZUG_KINDBEFEHL" > "$NLOG" 2>&1 &
  else
    nohup "${KINDBEFEHL[@]}" > "$NLOG" 2>&1 &
  fi
  NPID=$!
  echo "Nachzug gestartet, PID $NPID (Log: $NLOG)"

  # --- Auf den Nachzug warten -----------------------------------------------
  # Dieselbe Frist wie beim Warten auf den Hauptlauf (MAXWARTE Minuten),
  # gemessen in echter Zeit: Ein Schlafintervall dauert auf einem belasteten
  # Rechner laenger als angefordert, eine Schrittzaehlung wuerde die Frist
  # dadurch still ueberschreiten.
  zeilen_anzahl() {
    if [ -f "$R/$RUN/predictions.jsonl" ]; then
      wc -l < "$R/$RUN/predictions.jsonl" | tr -d '[:space:]'
    else
      echo 0
    fi
  }
  zeilen_start=$(zeilen_anzahl)
  log_stand=$(stat -c %s "$NLOG" 2>/dev/null || echo 0)
  letzte_aenderung=""

  echo "Warte auf den Nachzug (max ${MAXWARTE} min, Takt ${TAKT} s)."
  start=$SECONDS
  while [ $(( SECONDS - start )) -lt "$GRENZE" ]; do
    if grep -q "^fertig:" "$NLOG" 2>/dev/null; then break; fi
    # Ein gestorbenes Kind nicht bis zum Ablauf der Frist beobachten.
    if ! kill -0 "$NPID" 2>/dev/null; then break; fi
    sleep "$TAKT"
    groesse=$(stat -c %s "$NLOG" 2>/dev/null || echo 0)
    if [ "$groesse" != "$log_stand" ]; then
      log_stand=$groesse
      letzte_aenderung=$SECONDS
    fi
  done

  if ! grep -q "^fertig:" "$NLOG" 2>/dev/null; then
    neu=$(( $(zeilen_anzahl) - zeilen_start ))
    if [ -n "$letzte_aenderung" ]; then
      still=$(( SECONDS - letzte_aenderung ))
    else
      still=$(( SECONDS - start ))
    fi
    if kill -0 "$NPID" 2>/dev/null; then
      # Kind lebt: nicht beenden (ein Abbruch braucht Freigabe), aber den
      # Zustand belegen und den Rest von Hand nachholbar machen.
      echo "FEHLER: Nachzug nach ${MAXWARTE} Minuten noch nicht fertig."
      echo "Kind laeuft weiter (PID $NPID): ${neu} neue Zeilen, letzte Logaenderung vor ${still} s."
      echo "Dedupe unterlassen, damit kein halber Stand als Ergebnis gilt."
      echo "Das Kind wird nicht beendet; es schreibt weiter in $R/$RUN/predictions.jsonl."
      echo "Sperre $LOCK bleibt liegen (gilt nach 90 Minuten als abgelaufen)."
      echo "PID notiert in $R/$RUN/nachzug_kind.pid."
      echo "$NPID" > "$R/$RUN/nachzug_kind.pid"
      echo "Wenn es von selbst endet, den Rest von Hand:"
      echo "  .venv/bin/python public_benchmark/extended_benchmark/yun_full/dedupe_predictions.py --run $RUN --write"
      trap - EXIT
      exit 1
    fi
    wait "$NPID"
    code=$?
    echo "FEHLER: Nachzug endete ohne Abschlusszeile (Exitcode $code, ${neu} neue Zeilen)."
    echo "Letzte Zeilen aus $NLOG:"
    tail -n 15 "$NLOG" 2>/dev/null | sed 's/^/  /'
    echo "Dedupe unterlassen."
    if [ "$code" -eq 0 ]; then
      echo "Exitcode 0: moeglicherweise fertig, aber ohne 'fertig:'-Zeile. Stand pruefen, dann von Hand deduplizieren."
    fi
    trap - EXIT
    exit 2
  fi
  echo "Nachzug fertig nach $(( SECONDS - start )) s ($(( $(zeilen_anzahl) - zeilen_start )) neue Zeilen)."
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
