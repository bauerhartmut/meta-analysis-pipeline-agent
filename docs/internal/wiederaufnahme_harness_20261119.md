# Wiederaufnahme im Harness und Nachzug der P5-Fehlzeilen, 19.11.2026

Anlass: Der P5-Lauf hat um 10:14 nach 7 von 103 Records abgebrochen, weil
`gwdg/glm-5.3` mit 503 ("all instances at max capacity"), 429 und Timeout
antwortete und keinen Token ausgab. Der Harness hatte jeden dieser Records
endgueltig als Ausfall verbucht. Waere er durchgelaufen, haette er 103
Fehlerzeilen geschrieben und danach einen Bericht erzeugt, der die Startwache
gegen jeden spaeteren Lauf sperrt.

## 1. Was der Harness vorher tat

| Ebene | Verhalten |
|---|---|
| HTTP-Retry (`retry_manager`) | hoechstens 3 Versuche, Backoff 2 s, Faktor 2, Deckel 60 s, `Retry-After` beachtet |
| Auftragsebene | **keine** Wiederholung: nach dem dritten Fehlversuch entstand sofort die Fehlerzeile, das Journal schrieb `failed` |
| Folge | ein Anbieterausfall von mehr als etwa 10 Sekunden kostet den ganzen Auftrag |

Gemessen am 19.11.: 7 Records, 0 Tokens, Fehlerklassen 4 x `server_fehler`,
2 x `timeout`, 1 x `rate_limit`. Die 503-Meldung nennt ausdruecklich einen
Zustand, der Minuten bis Stunden dauert ("Try again later"), nicht einen Fehler
des Aufrufs.

## 2. Wiederaufnahme auf Auftragsebene

Neues Modul `yun_full/wiederaufnahme.py` (ohne Netz und Dateien testbar):

- `noetig(diagnose, bisher, max_versuche, frist_ok)` — wahr nur fuer die
  temporaeren Klassen aus `fehlerklassen.KLASSEN`: `server_fehler`,
  `rate_limit`, `timeout`, `verbindungsfehler`. `auth`, `anfrage_ungueltig` und
  `budget_im_reasoning` bleiben endgueltig, weil derselbe Aufruf mit denselben
  Mitteln reproduzierbar scheitert. Unbekannte Klassen (etwa
  `length_ohne_ergebnis` aus der alten Strategie) gelten als nicht wiederholbar.
- `wartezeit(nummer, basis_s)` — Backoff des Retry-Managers mit Jitter, Deckel
  600 s. `Retry-After` wird bewusst **nicht** verwendet: ein 429 mit "Retry
  after 1 seconds" ist eine Drossel je Aufruf, keine Aussage ueber die
  Kapazitaet des Anbieters.

Im Harness (`run_extended_extraction.py`):

- drei neue Optionen: `--wiederaufnahme-versuche` (Standard 4, `0` stellt das
  alte Verhalten her), `--wiederaufnahme-basis` (Standard 30 s),
  `--wiederaufnahme-frist` (Standard 90 min ab Laufstart).
- greift nur unter `--retry-strategie neu`, weil nur dort eine zentrale
  `diagnose` vorliegt.
- Wirkung: statt die Zeile zu schreiben, wartet der Thread die Backoff-Zeit und
  der Auftrag wird erneut eingereiht. Das Journal bleibt auf `running`, es
  entsteht **keine** Zwischenzeile. Erst nach der letzten Wiederaufnahme oder
  abgelaufener Frist wird die Fehlerzeile geschrieben; sie traegt dann
  `wiederaufnahmen: n`.
- die Auftragsschleife nutzt jetzt `wait(..., FIRST_COMPLETED)` statt
  `as_completed`, weil die Schlange waehrend des Laufs wachsen muss.
- Abschlusszeile nennt die Zahl der Wiederaufnahmen, die Fehlermeldung sagt
  `endgueltig` statt `kein Retry`.

Wartezeiten bei Basis 30 s und vier Wiederaufnahmen: rund 30, 60, 120, 240 s,
zusammen etwa 7,5 Minuten je Auftrag. Ein Anbieterausfall von einer Viertelstunde
kostet damit keinen Record mehr, ein Ausfall von Stunden laeuft nach der Frist in
die normale Fehlerzeile.

## 3. Geltung fuer den laufenden P5-Lauf

Der Lauf `yun699_p5_24000_20261118` (PID 19324, gestartet 10:27:05) hat die
alte Fassung bereits geladen; die Aenderung wirkt erst fuer Prozesse, die nach
diesem Commit starten. Fuer die Reproduzierbarkeit dieses Laufs gilt deshalb:
seine Zeilen tragen kein Feld `wiederaufnahmen`, und einzelne 503 bleiben dort
Ausfaelle.

## 4. Nachzug der Fehlzeilen

`yun_full/nachzug_p5_7.py` bereitet den Nachzug vor und startet nichts von
selbst:

- `--pruefen` (Standard) zeigt Fehlzeilen, Sperrlage und den vollstaendigen
  Befehl, aendert nichts.
- `--starten` bricht mit Exitcode 3 ab, solange die Startwache oder der Harness
  lebt (`jobs._lebt` ueber `OpenProcess`), sichert vorher die
  `predictions.jsonl`, haengt die neuen Zeilen an dieselbe Datei (damit die
  Auswertung alle 103 ids sieht) und ruft danach `dedupe_predictions.py` ohne
  `--write` auf. Ob Doppelzeilen bereinigt werden, bleibt eine bewusste
  Einzelentscheidung, weil `--write` die Datei umschreibt.

Stand 10:41 (`--pruefen`):

```
Fehlzeilen: 8
  yun2024:6: HTTP 429 rate_limit, 0 Tokens
  yun2024:30: HTTP 503 server_fehler, 0 Tokens
  yun2024:32: HTTP 0 timeout, 0 Tokens
  yun2024:54: HTTP 503 server_fehler, 0 Tokens
  yun2024:68: HTTP 503 server_fehler, 0 Tokens
  yun2024:52: HTTP 0 timeout, 0 Tokens
  yun2024:85: HTTP 503 server_fehler, 0 Tokens
  yun2024:110: HTTP 503 server_fehler, 0 Tokens
Sperrlage: Harness laeuft (PID 19324, harness.lock)
```

Acht statt sieben, weil `yun2024:110` erst im Neustart um 10:31 gescheitert ist.
Das Skript liest die Fehlzeilen dynamisch und erfasst damit auch spaetere
Ausfaelle; es muss deshalb erst nach dem Abschluss des Laufs laufen.

## 5. Pruefung

- `py_compile` auf allen vier geaenderten bzw. neuen Dateien.
- `pytest public_benchmark/tests/test_wiederaufnahme.py test_retry_manager.py
  test_fehlerklassen.py test_jobs.py test_dedupe_predictions.py` — 57 passed.
- `run_extended_extraction.py --dry-run` mit zwei ids: Auswahl korrekt, kein
  Verzeichnis angelegt, keine Anfrage gesendet.
- `nachzug_p5_7.py --pruefen`: Exitcode 0, Sperrlage erkannt, nichts geschrieben.

Nicht geprueft: ein echter Lauf mit Wiederaufnahme gegen den Anbieter. Das
kostet Guthaben und ist erst nach dem Abschluss des laufenden P5 sinnvoll.
