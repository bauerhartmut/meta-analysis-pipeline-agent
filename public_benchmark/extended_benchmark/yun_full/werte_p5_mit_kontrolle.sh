#!/bin/bash
# Fuehrt die Positivkontrolle aus und nur bei Erfolg die echte P5-Auswertung.
#
# Fail-closed: jeder unklare Ausgang blockiert die Auswertung. Es gibt keinen
# Schalter, der sie trotzdem startet — auch eine fehlende Marke, ein nicht
# startbarer Interpreter oder ein Absturz der Kontrolle enden vor der Auswertung.
#
# Aufruf (so nutzt es die Startwache):
#   bash yun_full/werte_p5_mit_kontrolle.sh [Argumente fuer werte_p5_aus.py]
#
# Exitcodes:
#   0  Kontrolle und Auswertung erfolgreich
#   3  Auswertung verweigert den Bericht (Marke ungueltig)
#   4  Positivkontrolle fehlgeschlagen, Auswertung unterbunden
#   *  Exitcode der Auswertung, unveraendert durchgereicht
set -u
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HIER/../../.." || exit 1
export PYTHONIOENCODING=utf-8

PYTHON=${PYTHON:-.venv/bin/python}
KONTROLLE=${KONTROLLE:-public_benchmark/extended_benchmark/yun_full/positivkontrolle_p5.py}
AUSWERTUNG=${AUSWERTUNG:-public_benchmark/extended_benchmark/yun_full/werte_p5_aus.py}
MARKE=${MARKE:-public_benchmark/extended_benchmark/iterativ/kontrolle/p5_positivkontrolle/ok.json}
MAX_ALTER=${MAX_ALTER:-600}

# Nonce bindet Marke und Auswertung an genau diesen Durchlauf: eine Marke aus
# einem frueheren oder fremden Lauf kann keine Auswertung autorisieren.
NONCE="$(date +%s)-$$-${RANDOM:-0}"

# Eine alte Marke aus einem frueheren Lauf darf eine gescheiterte Kontrolle nicht
# ueberdecken.
rm -f "$MARKE"

echo "=== Positivkontrolle: $KONTROLLE"
"$PYTHON" "$KONTROLLE" --marke "$MARKE" --nonce "$NONCE"
kcode=$?
if [ "$kcode" -ne 0 ]; then
  echo "ABBRUCH: Positivkontrolle Exit $kcode; Auswertung nicht gestartet."
  rm -f "$MARKE"
  exit 4
fi

if [ ! -s "$MARKE" ]; then
  echo "ABBRUCH: Positivkontrolle lieferte keine Erfolgsmarke; Auswertung nicht gestartet."
  exit 4
fi

echo "=== Auswertung: $AUSWERTUNG"
"$PYTHON" "$AUSWERTUNG" --kontrolle-marke "$MARKE" --kontrolle-max-alter "$MAX_ALTER" \
  --kontrolle-nonce "$NONCE" "$@"
wcode=$?
if [ "$wcode" -eq 0 ]; then
  echo "=== Auswertung erfolgreich."
else
  echo "ABBRUCH: Auswertung Exit $wcode."
fi
exit "$wcode"
