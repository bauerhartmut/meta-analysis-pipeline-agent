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
- die Auftragsschleife liegt als `wiederaufnahme.abwickeln(auftraege, arbeit,
  threads=...)` im Modul, nicht mehr im `main` des Harness; `main` behaelt
  nur `try/finally` um die Prozesssperre. `wait(..., FIRST_COMPLETED)`
  statt `as_completed`, weil die Schlange waehrend des Laufs wachsen muss.
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

`yun_full/nachzug_p5.py` bereitet den Nachzug vor und startet nichts von
selbst:

- `--pruefen` (Standard) zeigt Fehlzeilen, Sperrlage und den vollstaendigen
  Befehl, aendert nichts.
- `--starten` bricht mit Exitcode 3 ab, solange die Startwache oder der Harness
  lebt (`jobs._lebt` ueber `OpenProcess`), sichert vorher die
  `predictions.jsonl` und haengt die neuen Zeilen an dieselbe Datei (damit
  die Auswertung alle 103 ids sieht).
- danach raeumt es selbst auf: `eindeutig_machen` laesst je
  (record_id, model) genau eine Zeile stehen, die letzte brauchbare. Ohne
  diesen Schritt stuende jedes wiederholte Paar zweimal in der Datei und
  `auswerte_yun699.py` zaehlte den Record doppelt. Gesichert wird nach
  `predictions.jsonl.bak`, geschrieben ueber eine Zwischendatei; ist danach
  ein Record nicht eindeutig oder seine einzige Zeile weiterhin ein Ausfall,
  endet das Skript mit Exitcode 4.

Stand beim Schreiben (`--pruefen`, P5 bei 96 Zeilen): **55**
Fehlzeilen — 28 x `server_fehler` (503),
8 x `timeout`, 2 x `rate_limit`
(429), 15 x `length_ohne_ergebnis` mit
24.000 Tokens und 2 Antworten ohne Zellen. Die
Eindeutigkeit ist unauffaellig: 96 Zeilen, 0 Duplikate.

Die Liste waechst mit dem Lauf und enthaelt damit nicht nur Anbieterausfaelle,
sondern auch Budget- und Formatgrenzen. Ein Nachzug ueber alle Zeilen kostet
je `length`-Fall erneut das volle Budget von 24.000 Tokens. Vor `--starten`
ist deshalb eine Auswahl noetig; das Skript filtert bewusst nicht selbst,
damit die Entscheidung sichtbar bleibt.

## 5. Genau eine Zeile je Record

`--retry-failed` haengt an, statt zu ersetzen: nach dem Nachzug stuende jedes
wiederholte Paar zweimal in `predictions.jsonl`, und `auswerte_yun699.py`
zaehlt den Record doppelt. Der Nachzug raeumt deshalb nach dem Harness-Lauf
selbst auf (Abschnitt 4) und prueft danach jede id. `tests/test_nachzug_p5.py`
deckt beides offline ab:

- `test_temporaerer_ausfall_schreibt_keine_zwischenzeile`: zwei Ausfaelle,
  dann Erfolg; waehrend der Ausfaelle ist die Datei leer, am Ende steht genau
  eine Zeile.
- `test_nachzug_hinterlaesst_genau_eine_zeile_je_record`: sechs Zeilen, drei
  Paare, drei Duplikate; danach drei Zeilen, die erfolgreiche gewinnt, ein
  weiterhin fehlgeschlagener Record bleibt einmal sichtbar, die fehlende id
  wird gemeldet.
- `test_schleife_reiht_nur_wiederaufnahmen_erneut_ein`,
  `test_ausnahme_beendet_die_schleife_nicht`,
  `test_aufraeumen_ist_wiederholbar`.

## 6. Pruefung

- `py_compile` auf Harness, `wiederaufnahme.py`, `nachzug_p5.py` und dem neuen
  Test.
- `pytest test_run_extended_extraction.py test_crash_recovery.py
  test_nachzug_p5.py test_wiederaufnahme.py test_dedupe_predictions.py
  test_jobs.py test_fehlerklassen.py` — 91 passed (1,5 s).
- `run_extended_extraction.py --dry-run` mit zwei ids: Auswahl korrekt, kein
  Verzeichnis angelegt, keine Anfrage gesendet.
- `nachzug_p5.py --pruefen`: Exitcode 0, Sperrlage erkannt, nichts geschrieben.

Der Testhelfer `_auftrag` in `test_run_extended_extraction.py` setzt jetzt
`--wiederaufnahme-versuche 0`: mit dem Standard von 4 schlief der
Timeout-Test bis zu 7,5 Minuten, und der Lauf hing genau dort.

Nicht geprueft: ein echter Lauf mit Wiederaufnahme gegen den Anbieter. Das
kostet Guthaben und ist erst nach dem Abschluss des laufenden P5 sinnvoll.
