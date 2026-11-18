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

Jetzt leiten beide Wartezeiten ihre Schrittzahl aus derselben Grenze ab:
`SCHRITTE = MAXWARTE * 60 / TAKT`, Standard `--max-warte 720 --takt 30` ergibt
1.440 Abfragen (12 h) statt 240 (2 h). `--max-warte` und `--takt` sind
Parameter, keine Konstanten im Code.

Abbruchpfad offline geprueft (`nachzug_abbruch_protokoll.txt`), mit
`NACHZUG_KINDBEFEHL` als Ersatz fuer den Harness-Aufruf:

| Fall | Erwartung | Ergebnis |
|---|---|---|
| Kind meldet nie `fertig:` | Abbruch, Exit 1, kein Dedupe, Sperre bleibt | Exit 1, keine `predictions.jsonl.bak`, Sperre liegt |
| Kind meldet `fertig:` | weiter zu Dedupe und Zusammenfassung | „fertig nach 3 Abfragen“, Dedupe lief, Sperre entfernt |
| Trockenlauf nach dem Umbau | unveraendert | 103 vorher, 2 gerettet, 101 erneut length |

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
