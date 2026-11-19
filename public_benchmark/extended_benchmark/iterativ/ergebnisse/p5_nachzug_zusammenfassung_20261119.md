# P5-Nachzug und Neubewertung, 19.11.2026

Kurzfassung: Der P5-Lauf `yun699_p5_24000_20261118` (103 Records, Modell glm,
Budget 24.000 Tokens) hatte 60 Fehlzeilen hinterlassen. Wiederholt wurden nur
die 38 echten Anbieterausfaelle (503, 429, Timeout); 24 davon wurden gerettet.
Nach dem Aufraeumen hat jeder Record genau eine Zeile. Die neu gerechnete
Auswertung nennt 67 statt 43 verwertbare Records.

## 1. Ausgangslage

Der Lauf endete am 19.11. um 13:14 mit 103 Zeilen: 43 verwertbar, 60 Ausfaelle.
Darunter waren 38 Anbieterausfaelle ohne einen einzigen ausgegebenen Token:

| Klasse | HTTP | Records | Tokens |
|---|---:|---:|---:|
| `server_fehler` | 503 | 28 | 0 |
| `timeout` | 0 | 8 | 0 |
| `rate_limit` | 429 | 2 | 0 |
| `length_ohne_ergebnis` | 200 | 20 | je 24.000 |
| Antwort ohne Zellen | 200 | 2 | 2.501 / 3.842 |

`done_keys` zaehlt jede vorhandene Zeile als erledigt, auch eine Fehlzeile;
ohne `--retry-failed` waeren die 38 Anbieterausfaelle dauerhaft im Ergebnis
geblieben.

## 2. Auswahl des Nachzugs

`yun_full/nachzug_p5.py` wiederholt nur, was `wiederholbar()` als
Anbieterausfall erkennt: `server_fehler` mit 503, `rate_limit` mit 429,
`timeout` mit Status 0 oder ohne Status. `length_ohne_ergebnis` und Antworten
ohne Zellen bleiben stehen, weil derselbe Aufruf mit demselben Budget
reproduzierbar gleich endet.

| Groesse | Wert |
|---|---:|
| Fehlzeilen gesamt | 60 |
| ausgewaehlt (wiederholen) | 38 |
| ausgelassen | 22 (20 x `length_ohne_ergebnis`, 2 x ohne Zellen) |
| Completion-Tokens in den ausgelassenen Zeilen | 486.343 |
| Kostenschaetzung Obergrenze (38 x 24.000) | 912.000 |
| Kostenschaetzung Erwartung (38 x 7.840 Mittel der Erfolge) | 297.931 |

## 3. Lauf

| Groesse | Wert |
|---|---|
| Start / Ende | 13:41:48 / 14:56:02 (74 Minuten) |
| Auftraege, Threads, Budget | 38, 2, 24.000 |
| Frist der Wiederaufnahme | 90 Minuten |
| Wiederaufnahmen (`Wiederaufnahme n/4`) | 15 |
| erfolgreich (Zellen geschrieben) | 24 |
| endgueltig gescheitert | 14 |
| Completion-Tokens | 576.082 |
| Harness-Exitcode | 0 |

Der Anbieter war in der ersten Viertelstunde weiter ueberlastet (503 und
Timeout); die Wiederaufnahme hielt die Auftraege offen, statt sie sofort als
Ausfall zu verbuchen. Danach ueberwog `ok`.

Die 14 gescheiterten Auftraege sind keine Anbieterausfaelle: 13 x
`length_ohne_ergebnis` (24.000 Tokens im Reasoning aufgebraucht) und 1 x
Antwort ohne Zellen. Die tatsaechlichen Tokens liegen mit 576.082 ueber der
Erwartung von 297.931, weil diese 14 Faelle je das volle Budget verbraucht
haben.

## 4. Genau eine Zeile je Record

`--retry-failed` haengt Zeilen an, statt die Fehlzeile zu ersetzen. Der Nachzug
raeumt deshalb selbst auf (`eindeutig_machen`, Regel aus
`dedupe_predictions.entdopple`): je (record_id, model) bleibt die letzte
brauchbare Zeile.

| Groesse | Wert |
|---|---:|
| Zeilen vor dem Aufraeumen | 141 |
| entfernte Duplikate | 38 |
| unlesbare Zeilen | 0 |
| Records ohne genau eine Zeile | **0** |
| Zeilen danach | 103 |

Sicherungen: `predictions.vor_nachzug_20261119.jsonl` (Stand 13:14) und
`predictions.jsonl.bak` (Stand vor dem Aufraeumen), beide im Laufverzeichnis.

## 5. Stand danach

| Groesse | Wert |
|---|---:|
| Zeilen (ein Paar je Record und Modell) | 103 |
| verwertbar (mindestens eine Zelle) | 67 |
| Antwort ohne Zellen | 3 |
| Ausfaelle | 36 |
| davon `length_ohne_ergebnis` | 33 |
| davon 503 / 429 / Timeout | 0 |

Der Nachzug endet mit Exitcode 4: das ist die bewusste Meldung "es bleiben
Ausfaelle", kein Fehler des Aufraeumens. Die 36 Budgetfaelle wurden nicht
erneut bezahlt.

## 6. Auswertung: 13:14 gegen 15:04

`werte_p5_mit_kontrolle.sh` auf dem neuen Stand: Positivkontrolle gruen (alle
12 Kennzahlen, 22 Klassenzahlen und 25 Werte in Bilanz und Zellprotokoll
stimmen), Auswertung Exit 0.

| Kennzahl | 13:14 | 15:04 |
|---|---:|---:|
| gerettet (Antwort mit Zellen) | 43 | **67** |
| fertig, aber ohne Zellen | 2 | 3 |
| weiter ausgefallen | 58 | **33** |
| Antwort technisch erhalten | 45 | 70 |
| Rettungsquote (102 bewertbare) | 42 (41,2 %) | **66 (64,7 %)** |
| Stufe 3 inhaltlich wertgleich | 38 | **58** |
| Zellen | 179 | **271** |
| adressiert (Feld und Arm) | 154 | 241 |
| wertgleich (Feld und Arm) | 114 | **170** |
| TP / FP / FN | 114 / 61 / 309 | 170 / 97 / 253 |
| Precision | 0,651 | 0,637 |
| Recall | 0,270 | **0,402** |
| F1 | 0,381 | **0,493** |
| Completion-Tokens | 823.476 | 1.399.558 |

## 7. Einordnung

- Der Nachzug ist der groesste Einzelhebel bisher: +24 verwertbare Records,
  +23,5 Punkte Rettungsquote, +11,2 Punkte F1, +92 Zellen.
- Die Precision sinkt leicht um 1,4 Punkte, weil die neuen Antworten mehr
  Dubletten und Fremdschluessel enthalten (`ueberzaehlig` 46 -> 80,
  `fremdschluessel` 15 -> 17). Netto ueberwiegt der Gewinn deutlich:
  TP +56 gegen FP +36.
- `weiter ausgefallen` sinkt von 58 auf 33, obwohl 14 Nachzuege scheiterten:
  diese 14 waren vorher schon als Ausfall gezaehlt. Ein Record wechselte von
  `weiter_ausfall` zu `fertig_ohne_zellen` (`yun2024:137`).
- Die 36 verbleibenden Ausfaelle sind reine Budgetgrenzen. Ein weiterer Versuch
  mit demselben Budget von 24.000 Tokens hat bei 20 bereits identisch
  gescheiterten Faellen keine Aussicht und kostet je Fall das volle Budget.

## 8. Pruefungen

- 94 Tests gruen (`test_run_extended_extraction.py`, `test_crash_recovery.py`,
  `test_nachzug_p5.py`, `test_wiederaufnahme.py`, `test_dedupe_predictions.py`,
  `test_jobs.py`, `test_fehlerklassen.py`), inklusive Auswahlfilter und
  Kostenschaetzung.
- `nachzug_p5.py --pruefen` vor dem Start: 38 von 60 ausgewaehlt, Sperrlage
  frei, nichts geschrieben.
- Laufprotokoll: `runs/nachzug_p5_20261119.log`.
- Auswertung: `iterativ/ergebnisse/p5_auswertung_20261118.{json,md}`; der
  Vergleichsstand von 13:14 liegt unter `runs/p5_auswertung_stand1314/`.

## 9. Offene Punkte

- Die 36 Budgetfaelle sind unentschieden: entweder mit hoeherem Budget erneut
  versuchen (Obergrenze 36 x neues Budget) oder im Bericht als Ausfall
  ausweisen.
- Die offizielle Bewertung (Recall, MAE) bleibt der geschuetzte
  Bewertungslauf; die Zellzaehlung hier ist eine Selbstpruefung.
- Zitierbar sind jetzt 67 verwertbare Records und 66 von 102 bewertbaren
  Records gerettet. So steht es im Handoff
  `docs/internal/wiederaufnahme_harness_20261119.md` (Abschnitt 7 und 8) und in
  der Auswertung `p5_auswertung_20261118.md` (64.7 %). Die Momentaufnahme
  `runs/p5_auswertung_stand1314/` bleibt absichtlich bei 43 und 42 von 102: sie
  belegt den Stand vor dem Nachzug und wird nicht nachgezogen.
