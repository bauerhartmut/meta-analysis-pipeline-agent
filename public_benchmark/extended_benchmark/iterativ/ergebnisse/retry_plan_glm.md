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

## Auswahl geprueft (ohne Netzlauf)

Der Harness hat jetzt `--dry-run`: Er zeigt die Auswahl und beendet, ohne eine
Anfrage zu senden oder eine Zeile zu schreiben. Damit ist der Repair-Befehl
gegen den laufenden Lauf geprueft:

| Pruefung | Ergebnis |
|---|---|
| Auswahl mit `--retry-failed --ids <Liste>` | 103 Records, 103 Auftraege |
| Setvergleich mit `retry_repair_ids.txt` | identisch (103 = 103, keine Abweichung) |
| Deckung mit den aktuellen GLM-Length-Records | 103 von 103 |
| Gegenprobe ohne `--retry-failed` | 103 Records, **0** Auftraege |
| `predictions.jsonl` vor/nach | gleiche MD5, gleiche Zeilenzahl (1.497) |

## Trockenlauf des Nachzugs (ohne Netzlauf)

`nachzug_ausfaelle.sh --dry-run` fuehrt den ganzen Ablauf aus, laesst nur den
Start weg: Sicherung, Auswahlpruefung, Ersatzzeilen statt Modellantworten,
Dedupe und Zusammenfassung. Er verweigert die echte run-id und laeuft nur auf
einer Kopie. Protokoll: `nachzug_trocken_protokoll.txt`.

Geprueft gegen eine Kopie von `yun699_8000_alle_20261117` (1.507 Zeilen):

| Schritt | Ergebnis |
|---|---|
| Sicherung | `predictions.vor_nachzug.jsonl` angelegt, 103 Length-Ausfaelle |
| Auswahl im Harness | 140 offene Auftraege (103 length + 36 leer + 1 json_kaputt) |
| Ersatzzeilen | 2 angehaengt, als `dry_run` markiert |
| Dedupe | 1.509 roh → 1.507 eindeutig, 2 Duplikate, 0 unlesbar |
| Zusammenfassung | 103 vorher, 2 gerettet, 101 erneut length (98 %) |
| Duplikate danach | 0 |
| Prozess gestartet | keiner |
| echte Datei | unveraendert (die neue Zeile dort ist eine qwen-Zeile des laufenden Nachtlaufs) |

Die 98 % sind **kein Messwert**: Die Ersatzzeilen sind konstruiert. Geprueft ist
der Ablauf, nicht die Rettungsquote.

## Eine Grenze fuer beide Wartezeiten

Die Warteschleife auf den Nachzug war auf 240 Abfragen a 30 s festgenagelt
(2 h), waehrend das Warten auf den Hauptlauf 720 min (12 h) erlaubte. Fuer 140
Auftraege mit Reparaturaufruf war das zu kurz: Der Nachzug waere abgeschnitten
worden, waehrend er noch schrieb, und der Dedupe waere unterblieben.

Jetzt messen beide Wartezeiten dieselbe Frist in echter Zeit
(`GRENZE = MAXWARTE * 60` Sekunden gegen `$SECONDS`), Standard 720 Minuten.
Eine Schrittzaehlung waere hier falsch: `sleep 30` dauert auf einem belasteten
Rechner laenger, 1.440 Schritte waeren dann mehr als 12 h. `--max-warte` und
`--takt` sind Parameter, keine Konstanten im Code.

Abbruchpfad offline geprueft, mit `NACHZUG_KINDBEFEHL` als Ersatz fuer den
Harness-Aufruf (Protokolle `nachzug_abbruch_protokoll.txt`,
`nachzug_lebt_protokoll.txt`, `nachzug_stirbt_protokoll.txt`):

| Fall | Erwartung | Ergebnis |
|---|---|---|
| Kind laeuft ueber die Frist hinaus (`sleep`-Schleife, 100 s) | Exit 1, kein Dedupe, Sperre bleibt, Kind lebt weiter | Exit 1, PID 1263 notiert und nachweislich am Leben, 13 Log-Zeilen waehrend der Frist, keine `predictions.jsonl.bak`, Sperre liegt |
| Kind stirbt ohne `fertig:` (Exit 7 nach 2 s, Frist 5 min) | sofortiger Abbruch mit Exitcode und Logrest, Exit 2 | nach **3 s** statt 300 s, Exit 2, Exitcode 7 und letzte Logzeilen im Protokoll, kein Dedupe |
| Kind meldet `fertig:` | weiter zu Dedupe und Zusammenfassung | „fertig nach 2 s“, Dedupe lief, Sperre entfernt |
| Warten auf den Hauptlauf ohne Prozess | sofort weiter | „Kein Prozess mehr aktiv nach 0 Minuten“ |
| Trockenlauf nach dem Umbau | unveraendert | 103 vorher, 2 gerettet, 101 erneut length |

Was der Abbruch jetzt anders macht: Er **raet nicht mehr**, ob das Kind noch
laeuft, sondern prueft es mit `kill -0` und holt sich bei einem toten Kind mit
`wait` den Exitcode. Ein lebendes Kind wird nicht beendet — ein Abbruch
braucht Freigabe — sondern mit PID-Datei, Fortschrittszahl und dem genauen
Dedupe-Befehl fuer danach hinterlassen, damit die Arbeit nicht verloren geht.
Ein gestorbenes Kind bricht die Wartephase sofort ab, statt die Frist
abzusitzen: Ein Absturz nach zehn Minuten haette sonst zwoelf Stunden gewartet.

Die Sperre bleibt im Abbruchfall absichtlich liegen: Das Kind schreibt
moeglicherweise noch in dieselbe Datei, ein zweiter Nachzug wuerde parallel
laufen. Nach 90 Minuten gilt sie von selbst als abgelaufen.

## Zwei Fallen

1. **`nachzug_ausfaelle.sh` ist angepasst.** Es wartet nicht mehr auf
   `^fertig:` in einer fest verdrahteten Datei, sondern fragt den Prozessstand
   ueber `lauf_status.py` ab (`Prozesse: 0`) und nimmt den Logpfad als
   Parameter (`--log`). `--jetzt` bricht jetzt ab, wenn doch noch ein Prozess
   laeuft. Die Prozessabfrage ist **run-spezifisch**: Gezaehlt werden nur
   Prozesse mit `--run-id yun699_8000_alle_20261117`; ein fremder Lauf wird als
   "Fremde Laeufe" gemeldet und blockiert den Nachzug nicht. Fehlt
   `predictions.jsonl`, bricht das Skript sofort ab, statt zu warten.
2. **`--retry-failed` ersetzt keine Zeilen, es haengt an.** Die alten
   Fehlzeilen bleiben stehen; erst `dedupe_predictions.py --write` macht die
   Auswertung eindeutig. Bis dahin zeigen `lauf_status.py` und
   `auswerte_yun699.py` beide Fassungen.
