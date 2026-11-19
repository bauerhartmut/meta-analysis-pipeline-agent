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

Stand nach Abschluss des Laufs (103 Zeilen): **60** Fehlzeilen — 28 x
`server_fehler` (503), 8 x `timeout` (0), 2 x `rate_limit` (429), 20 x
`length_ohne_ergebnis` (HTTP 200, je 24.000 Tokens) und 2 Antworten ohne Zellen.
Die Eindeutigkeit ist unauffaellig: 103 Zeilen, 0 Duplikate.

`--retry-failed` wiederholt nur Anbieterausfaelle. `wiederholbar` prueft Klasse
**und** HTTP-Code: 503 bei `server_fehler`, 429 bei `rate_limit`, 0 oder kein
Status bei `timeout`. Alles andere bleibt stehen, insbesondere
`length_ohne_ergebnis`: derselbe Aufruf mit demselben Budget endet
reproduzierbar gleich und kostet erneut 24.000 Tokens. `--pruefen` markiert
jede Zeile mit `wiederholen` oder `ausgelassen` und nennt die
Kostenschaetzung: Obergrenze `Auswahl x 24.000` Completion-Tokens,
Erwartungswert aus dem Mittel der erfolgreichen Zeilen. Geldbetraege nennt das
Skript nicht, weil fuer den Endpunkt kein Preisaushang vorliegt.

Am 19.11.2026 nach Abschluss: 38 von 60 Zeilen ausgewaehlt (912.000 Tokens
Obergrenze, rund 298.000 erwartbar beim Mittel von 7.840 Tokens), 22
ausgelassen mit 486.343 bereits verbrauchten Completion-Tokens.

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
  `test_aufraeumen_ist_wiederholbar`,
  `test_auswahl_nimmt_nur_503_429_und_timeout`,
  `test_kostenschaetzung_nutzt_budget_und_mittel`,
  `test_pruefen_zeigt_auswahl_und_kosten` (fuehrt `main --pruefen` gegen eine
  temporaere Datei aus und prueft, dass der Befehl nur die Auswahl enthaelt).

## 6. Pruefung

- `py_compile` auf Harness, `wiederaufnahme.py`, `nachzug_p5.py` und dem neuen
  Test.
- `pytest test_run_extended_extraction.py test_crash_recovery.py
  test_nachzug_p5.py test_wiederaufnahme.py test_dedupe_predictions.py
  test_jobs.py test_fehlerklassen.py` — 94 passed (1,4 s).
- `run_extended_extraction.py --dry-run` mit zwei ids: Auswahl korrekt, kein
  Verzeichnis angelegt, keine Anfrage gesendet.
- `nachzug_p5.py --pruefen` gegen den abgeschlossenen Lauf: Exitcode 0, 60
  Fehlzeilen, davon 38 ausgewaehlt und 22 ausgelassen, 103 Zeilen ohne Duplikat,
  Sperrlage frei, nichts geschrieben.

Der Testhelfer `_auftrag` in `test_run_extended_extraction.py` setzt jetzt
`--wiederaufnahme-versuche 0`: mit dem Standard von 4 schlief der
Timeout-Test bis zu 7,5 Minuten, und der Lauf hing genau dort.

Der echte Lauf mit Wiederaufnahme gegen den Anbieter steht seit dem Nachzug
(Abschnitt 7) aus; die 15 Wiederaufnahmen belegen, dass die Schleife unter 503
greift.

## 7. Nachzug am 19.11.2026: Ergebnis

Gestartet 13:41:48 mit `--starten` (38 ausgewaehlte Records, 2 Threads, Budget
24.000, Frist 90 Minuten), Ende 14:56:02 nach 74 Minuten. Der Anbieter war in
der ersten Viertelstunde weiter ueberlastet (503/Timeout), danach ueberwog `ok`.

| Groesse | Wert |
|---|---|
| Auftraege | 38 |
| Wiederaufnahmen | 15 |
| erfolgreich (Zellen geschrieben) | 24 |
| endgueltig gescheitert | 14 |
| Completion-Tokens im Nachzug | 576.082 (Obergrenze 912.000, Erwartung 297.931) |

Die 14 Ausfaelle sind keine Anbieterausfaelle mehr: 13 x
`length_ohne_ergebnis` (24.000 Tokens im Reasoning aufgebraucht) und 1 x
Antwort ohne Zellen. Genau dieses Muster war der Grund fuer den Filter: waeren
die 20 alten `length`-Zeilen mitgelaufen, haette derselbe Effekt 20 weitere
volle Budgets gekostet.

Aufraeumen (`eindeutig_machen`): 141 Zeilen gelesen, 38 Duplikate entfernt,
0 unlesbar, **0 Records ohne genau eine Zeile**. Danach hat die Datei 103
Zeilen, ein Paar je (record_id, model), keine Doppel. Sicherungen:
`predictions.vor_nachzug_20261119.jsonl` (Stand 13:14) und
`predictions.jsonl.bak` (Stand vor dem Aufraeumen).

Stand danach: **67** brauchbare Zeilen und **36** Ausfaelle — 33 x
`length_ohne_ergebnis`, 3 x ohne Zellen, keine 503/429/Timeout mehr. Der
Nachzug endet mit Exitcode 4, weil Ausfaelle verbleiben.

Die Auswertung `iterativ/ergebnisse/p5_auswertung_20261118.{json,md}` wurde
danach neu erzeugt (Abschnitt 8).

## 8. Neuberechnung der Auswertung, 15:04

`werte_p5_mit_kontrolle.sh` lief auf dem neuen Stand: Positivkontrolle gruen
(alle 12 Kennzahlen, 22 Klassenzahlen und 25 Werte in Bilanz und Zellprotokoll
stimmen), Auswertung Exit 0. Gegenueber dem Bericht von 13:14:

| Kennzahl | 13:14 | 15:04 |
|---|---:|---:|
| gerettet (Antwort mit Zellen) | 43 | 67 |
| fertig, aber ohne Zellen | 2 | 3 |
| weiter ausgefallen | 58 | 33 |
| Antwort technisch erhalten | 45 | 70 |
| Rettungsquote (102 bewertbare) | 42 (41,2 %) | 66 (64,7 %) |
| Stufe 3 wertgleich | 38 | 58 |
| Zellen | 179 | 271 |
| adressiert (Feld und Arm) | 154 | 241 |
| wertgleich (Feld und Arm) | 114 | 170 |
| TP / FP / FN | 114 / 61 / 309 | 170 / 97 / 253 |
| Precision | 0,651 | 0,637 |
| Recall | 0,270 | 0,402 |
| F1 | 0,381 | 0,493 |
| Completion-Tokens | 823.476 | 1.399.558 |

Die 24 geretteten Records bringen 92 Zellen, 56 wertgleiche Zellen und 11 Punkte
F1; die Precision sinkt um 1,4 Punkte, weil die neuen Antworten mehr Dubletten
und Fremdschluessel enthalten (`ueberzaehlig` 46 -> 80, `fremdschluessel`
15 -> 17). Die 36 Ausfaelle sind unveraendert 33 x `length_ohne_ergebnis` und
3 x ohne Zellen; die Differenz bei `weiter ausgefallen` (58 -> 33) erklaert sich
aus 24 geretteten Records und einem Record, der von `weiter_ausfall` zu
`fertig_ohne_zellen` wechselte (`yun2024:137`).
