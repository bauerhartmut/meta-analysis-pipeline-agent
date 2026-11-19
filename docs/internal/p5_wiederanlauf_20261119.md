# P5-Wiederanlauf: Betriebspruefung 19.11.2026

Artefakt zum Arbeitsauftrag "P5-Wiederanlauf und Betriebspruefung". Alle Werte
sind gemessen, nicht geschaetzt. Kein Commit erfolgt (keine Freigabe erteilt).

## Phase 1 – Bestandsaufnahme (09:59)

### Git

| Punkt | Wert |
|---|---|
| Branch | `master` |
| HEAD | `de24ecc` (Fasst alle Berichte des 18.11.2026 in einem Tagesbericht zusammen) |
| Abstand zu `origin/master` | 688 Commits voraus, 1 dahinter |
| Working Tree | 36 Eintraege (5 geaendert, 31 unversioniert), unveraendert gelassen |

### Prozesse

`ps -ef` und `ps -W` zeigen keinen Python-Prozess. Es lief weder eine Extraktion
noch ein P5-Lauf noch eine Startwache. Bedingung "keine konkurrierende
Extraktion" erfuellt.

### Gate, PID, Nonce, Marker

| Element | Befund |
|---|---|
| `runs/p5_gate_20261118.pid` | enthielt `6630`, `kill -0` tot, `ps -W` fuehrt die PID nicht |
| `runs/p5_start_20261118.log` | letzte Zeile `[18:30:54] noch belegt ...`; die Frist von 720 min lief um 04:55 ab, ohne Abschlusszeile |
| `runs/yun699_p5_24000_20261118` | existierte nicht — P5 war nie gestartet |
| `iterativ/kontrolle/p5_positivkontrolle/ok.json` | vom 18.11. 16:21, also abgelaufen (Grenze 600 s) |
| Nonce | keine gueltige vorhanden; sie wird je Auswertungslauf neu erzeugt |

### Sperrlage

`starte_p5_wenn_frei.sh --pruefen` meldete:

```
Lauf: yun699_8000_alle_20261117
Prozess: Prozesse: 0  - der Lauf steht (abgebrochen oder fertig)
Nachzug: keine Sperre
Letzte Zeile: vor 42095 s (Ruhe gilt ab 180 s)
=> frei, P5 wuerde starten
```

Es gab keine `nachzug.lock` mehr. Einzige verwaiste Sperre war die Gate-Datei mit
PID 6630.

### Predictions und Logs

Fremdlauf `runs/yun699_8000_alle_20261117` vor dem Eingriff:

```
Zeilen: 2097 roh, 2097 eindeutige Paare, 0 Duplikate, 0 unlesbar  ok
  glm      n= 699  failed  21 ( 3.0 %)  leer  37 ( 5.3 %)
  qwen     n= 699  failed  86 (12.3 %)  leer  71 (10.2 %)
  qwen30   n= 699  failed   0 ( 0.0 %)  leer  57 ( 8.2 %)
```

Additiv gesichert, ohne eine bestehende Datei zu aendern:

- `runs/yun699_8000_alle_20261117/predictions.vor_p5_20261119.jsonl`
  (md5 `0525f28776af144528130cc869d8a58e`, identisch mit `predictions.jsonl`)
- `runs/_sicherung_20261119/p5_start_20261118.log`
- `runs/_sicherung_20261119/konsole_nachzug_20261118.log`
- `runs/_sicherung_20261119/p5_gate_20261118.pid.alt` (alter Inhalt: 6630)

## Phase 2 – Wiederherstellung (09:59–10:02)

| Punkt | Befund |
|---|---|
| Verwaiste Sperre | Gate-Datei PID 6630; das Skript erkannte sie ueber `pid_lebt` als verwaist und uebernahm sie ("Alte Wache-Sperre von PID 6630 ist verwaist, uebernehme.") |
| Neue Wache | PID 959, neue Gate-Datei enthielt `959`, Prozess ueber `ps -W` bestaetigt |
| Heartbeat | Logzeile `[09:59:44] Startwache laeuft (PID 959), Frist 720 min, Takt 60s, Ruhe 180s.` und danach die Freigabemeldung |
| Gate und Nonce | Gate neu und gueltig; eine Nonce gibt es erst beim Auswertungslauf, weil `werte_p5_mit_kontrolle.sh` sie je Aufruf erzeugt und an die Marke bindet |

Um 10:02:46 meldete die Wache `frei: keine Prozesse, kein Nachzug, 180s ohne neue
Zeile` und startete den Lauf. Nur ein Lauf, keine Parallelitaet.

## Phase 3 – P5-Ausfuehrung (10:02–10:14)

Der Lauf startete korrekt: `103 Records, 103 offene Auftraege, 2 Threads`,
Verzeichnis `runs/yun699_p5_24000_20261118`, Harness-PID 1001 als Kind der Wache.

Er scheiterte vollstaendig an der Gegenseite. Nach 13 Minuten:

| Kennzahl | Wert |
|---|---|
| geschriebene Records | 7 |
| davon erfolgreich | 0 |
| verbrauchte Completion-Tokens | 0 |
| Fehlerklassen | 4 `server_fehler`, 2 `timeout`, 1 `rate_limit` |

Die Fehlertexte:

- HTTP 503: `litellm.ServiceUnavailableError: All instances of service 'glm-5.3' are at max capacity. Try again later.`
- HTTP 429: `RateLimitError: Rate limit exceeded: user 10s request limit reached (10 of 10)`
- Timeout: `TimeoutError: The read operation timed out`

Der Harness versucht je Auftrag drei HTTP-Versuche (`http_versuche: 3`, Backoff
1,6–4,8 s) und verbucht danach einen Ausfall ohne Retry auf Auftragsebene. Bei
1 Record je 2 Minuten haette der Lauf rund 3,5 Stunden gebraucht und dabei
ausschliesslich Ausfaelle geschrieben — ein wertloser Lauf, der anschliessend
ueber `werte_p5_aus.py` einen Bericht mit 103 Ausfaellen erzeugt und damit die
Wache gegen jeden spaeteren echten Lauf gesperrt haette (`grep "P5 fertig"` plus
vorhandener Bericht).

Deshalb wurde der Lauf um 10:14:09 abgebrochen. Ablauf:

| Punkt | Befund |
|---|---|
| Abbruch | `kill -TERM 1001`, Exitcode 143 |
| Wache | loggte `Harness beendet mit Exitcode 143` und `keine Auswertung, weil der Lauf mit 143 endete`, beendete sich, `trap` entfernte die Gate-Datei |
| Auswertung | nicht gestartet, `p5_auswertung_20261118.md` existiert nicht |
| Prozesse danach | 0 |
| `harness.lock` | blieb stehen, enthaelt PID 27256 (Windows). `tasklist` findet sie nicht; `RunSperre._verwaist()` erkennt sie ueber `OpenProcess` als tot und uebernimmt sie beim naechsten Start ("Hinweis: abgelaufene Sperre uebernommen") |

Gesichert vor dem Abbruch:

- `runs/_sicherung_20261119/p5_abbruch_predictions_20261119.jsonl` (7 Zeilen)
- `runs/_sicherung_20261119/p5_abbruch_jobs_20261119.jsonl`
- `runs/_sicherung_20261119/p5_start_bis_abbruch_20261119.log`

Der Lauf ist damit nicht abgeschlossen. Es wurde kein zweiter Lauf gestartet,
weil die Gegenseite (GWDG, `gwdg/glm-5.3`) zum Zeitpunkt der Pruefung keine
Kapazitaet hatte und ein Neustart ohne Freigabe nicht vorgesehen ist.

## Phase 3a – Vortest der Anbieterkapazitaet (10:20)

Neues Skript `yun_full/pruefe_glm_kapazitaet.py`: sendet genau einen Record aus
der P5-Auswahl mit denselben Harness-Parametern wie der echte Lauf
(`--split "" --models glm --retry-strategie neu`), aber kleinem Budget und eigenem
Laufverzeichnis. Erfolgskriterium ist nur, ob die Gegenseite antwortet:
HTTP 200 und mehr als 0 Completion-Tokens; ein `length`-Abschluss ist bei 1400
Tokens erwartet und kein Fehler.

Ergebnis (Lauf `p5_vortest_20261119_102008`, Record `yun2024:6`, Versuch 1 von 3):

```
HTTP 200, 1400 Tokens, Abschluss length
OK: Anbieter antwortet, P5 darf starten
```

Die Kapazitaetslage hat sich zwischen 10:14 und 10:20 erholt. Die 1400 Tokens
reichen fuer den Zellinhalt des Records nicht, der Abschluss `length_ohne_ergebnis`
ist bei diesem Budget also erwartet und kein Anbieterfehler.

## Phase 3b – Neustart nach bestandenem Vortest (10:24)

Wache neu gestartet, PID 1918. Ablauf im Log:

```
[10:24:03] Startwache laeuft (PID 1918), Frist 720 min, Takt 60s, Ruhe 180s.
[10:27:04] frei: keine Prozesse, kein Nachzug, 180s ohne neue Zeile
[10:27:05] starte P5: 103 ids, yun699.jsonl, Budget 24000, Retry-Strategie neu
103 Records, 96 offene Auftraege, 2 Threads
```

96 statt 103 offene Auftraege, weil `run_extended_extraction.py` jede vorhandene
Zeile als erledigt zaehlt, auch eine Fehlzeile (Kommentar `erledigte_paare`, Zeile
621: "Jede vorhandene Zeile gilt als erledigt — auch eine Fehlzeile"). Die 7
Ausfaelle aus dem abgebrochenen Lauf bleiben damit als Ausfaelle im Ergebnis
stehen und muessen, wenn sie ins Sample sollen, mit `--retry-failed` nachgezogen
werden.

Erste Messung nach 8 Minuten Laufzeit:

| Kennzahl | Wert |
|---|---|
| Records gesamt | 11 (7 vom Abbruch, 4 neu) |
| neu davon erfolgreich | 3 (`yun2024:84`, `yun2024:86`, `yun2024:113`, Abschluss `stop`) |
| neu davon Ausfall | 1 (`yun2024:110`, 503) |
| Completion-Tokens neu | 36.225 (16.039 / 9.112 / 11.074) |

Damit ist die Kapazitaetslage belastbar bestaetigt: echte Antworten mit
`finish_reason: stop`, nicht nur ein einzelner Vortest. Vereinzelte 503 bleiben
bestehen und werden wie vorgesehen als Ausfall verbucht.

## Phase 4 – Befund

1. **Vorgefunden:** kein Prozess, keine lebende Sperre, P5 nie gestartet, Gate-PID
   6630 verwaist, 2097 unveraenderte Predictions des Fremdlaufs.
2. **Laufende Prozesse:** keine.
3. **Wiederherstellung:** nur Neustart der Wache noetig; die verwaiste Gate-Sperre
   uebernahm das Skript selbst. Um 10:02:46 startete der Lauf korrekt.
4. **P5 gestartet und abgeschlossen:** gestartet ja, abgeschlossen nein. Abbruch
   nach 7 von 103 Records, weil der Anbieter 503/429/timeout lieferte und kein
   Record einen Token erhielt.
5. **Ergebnisorte:** Lauf `runs/yun699_p5_24000_20261118` (7 Fehlerzeilen), Log
   `runs/p5_start_20261118.log`, Sicherungen in `runs/_sicherung_20261119/`.
   Eine Auswertung gibt es nicht.
6. **Auffaelligkeiten:** Der Fremdlauf endet 21 Minuten vor dem geplanten
   P5-Start (22:17 gegen 18:30-Wartebeginn), die Wache hat ihren Abschluss aber
   nie protokolliert — sie wurde vermutlich mit der Sitzung beendet. Ferner
   verbucht der Harness 503/429 nach drei Versuchen als Ausfall, ohne den Auftrag
   spaeter erneut zu versuchen; bei einem Anbieterausfall laeuft ein Lauf damit
   vollstaendig leer, statt zu warten.
