# Ergebnisstand und größte Herausforderungen (16.11.2026)

Stand der Benchmark-Arbeit an der zweiten Kohorte (`yun_test76_ziel.jsonl`,
76 Records, 243 Goldzellen). Alle Zahlen stammen aus den Läufen und
Auswertungen dieses Tages; Quellen stehen am Ende.

## 1. Was gilt

| | Stand |
|---|---|
| Testbasis | **Version 3**, SHA-256 `3f811bed…` (76 Records, 243 Zellen) |
| Version 2 | `74fd0c05…` — Basis des Hauptlaufs, weiter Referenz für dessen Kennzahlen |
| Version 1 | `06fea97c…` — vor der ersten Gold-Korrektur, nur historisch |
| Modell | `glm` (`gwdg/glm-5.3`), ein Modell, kein Vergleichsmodell |
| Promptstand | v7 mit Zellzeitpunkt, Ziel-Fallback, `--repair`; ohne Armzeilen-Zusatz |
| Tests | 246 grün (`pytest public_benchmark/tests`) |

## 2. Läufe und Kosten

| Lauf | Records | Tokens | Ergebnis |
|---|---:|---:|---|
| Trockenlauf `trockenlauf76_20261116` | 5 | 57.199 | Pfad geprüft, keine Kennzahl |
| Hauptlauf `test76_hauptlauf_20261116` (V2) | 76 | **552.552** | F1 0,5455, P 0,7394, R 0,4321, MAE 0,5763 |
| Armzeilen-Prüfung `armzeile_291_295_20261116` | 5 | 27.822 | 0/10 Komparatorzellen → Zusatz verworfen |
| V3-Teillauf `v3_comparator_289_295_20261116` | 7 | **24.768** | **14/14** Komparatorzellen, 41/42 Zellen |

Der Hauptlauf brauchte 531.767 Primär- und 20.785 Reparatur-Tokens, rund 40
Minuten Wanduhr; 12 Records liefen über den Reparaturpfad. Der V3-Teillauf kam
ohne Reparatur und ohne 503-Wiederholung aus.

## 3. Kennzahlen des Hauptlaufs (Version 2)

| Kennzahl | Wert |
|---|---|
| Zell-F1 | 0,5455 |
| Precision | 0,7394 |
| Recall | 0,4321 |
| MAE | 0,5763 (Abweichungssumme 74,92 über 130 zugeordnete Zellen) |
| Abdeckung | 0,535 (130 von 243 Zellen) |
| exakt richtige Records | 16 von 76 |

| Zellklasse | Zellen | richtig | falsch | ohne Gold | Precision |
|---|---:|---:|---:|---:|---:|
| `zieltreu` | 76 | 57 | 9 | 10 | 0,8636 |
| `rueckfall` | 48 | 32 | 16 | 0 | 0,6667 |
| `gruppengroesse_ohne Zeitpunkt` | 4 | 4 | 0 | 0 | 1,0 |

Die vier als `unsicher` markierten Zielzeitpunkte (10 Zellen) sind **alle
richtig** — die Ableitung trägt.

## 4. Was die drei Korrekturen gebracht haben

**a) Gold von `yun2024:479` (Version 2).** Tausendertrenner falsch gelesen
(1,922 → 1.922 Personen). Abweichungssumme fiel von 3.912,08 auf 74,92, die
MAE von 30,09 auf 0,5763. Die Ereigniszahlen 1.078/976 meldet das Modell nicht —
die beiden Zellen bleiben Auslassungen.

**b) Comparator-Feld von 289–295 (Version 3).** Das Paper randomisiert auf FAT,
CE und TAU; ein Arm „baseline" existiert nicht, das Gold vergleicht FAT Post
gegen TAU Post. Feld heißt jetzt `treatment as usual (TAU)`.

**c) Zwei Goldzellen (Version 3).** 291: SD 14,0 statt 12,8 (das war der
Pre-SD). 294: Komparator 45,4 ± 7,7 statt der Spalte „Visual learning"
(46,5 ± 9,8).

Wirkung im direkten Vergleich, ohne neuen Hauptlauf:

| Zellen | Version 2 (Hauptlauf) | Version 3 (Teillauf) |
|---|---|---|
| 14 Komparatorzellen 289–295 | 0 richtig, 14 falsch | **14 richtig, 0 falsch** |
| alle 42 Zellen der sieben Records | – | 41 richtig, 1 falsch |
| Tokens | im Hauptlauf enthalten | 24.768 |

Damit ist belegt: Der Fehler lag in der Vorgabe, nicht im Prompt. Der extra
gebaute Armzeilen-Zusatz hätte nichts geholfen (0/10) und ist wieder entfernt.

## 5. Die größten Herausforderungen

### 5.1 Abdeckung: 34 Records liefern keine Zelle

**Befund.** 29 leere Antworten und 5 technische Ausfälle (3 × `length` trotz
Reparatur, 2 × Read-Timeout mit 0 Tokens). 31 dieser 34 haben ein Gold ohne
Mittelwerte — dort ist leer richtig. Es bleiben **3 Records mit Mittelwerten im
Gold, die das Modell nie beantwortet**, plus die 2 Timeouts, die in jeder
Kennzahl fehlen. Insgesamt 125 Auslassungen (Quote 0,5144), davon 90
Gruppengrößen.

**Warum es bremst.** Recall 0,4321 und Abdeckung 0,535 hängen fast vollständig
hier. Die Precision ist mit 0,7394 deutlich besser als der Recall — das Modell
schweigt, statt zu raten.

**Nächster Hebel.** Die 29 leeren Antworten sind kein Prompt-, sondern ein
Ausgabeproblem: prüfen, ob die Antwort abgeschnitten wird (Finish-Reason `stop`
mit leerem Inhalt) und ob ein zweiter, kürzerer Prompt nach dem Muster von
`--repair` hilft. Dazu die zwei Timeout-Records mit höherem Timeout einmalig
nachziehen. Beides ist billig (wenige zehntausend Tokens) und wirkt direkt auf
den Recall. Die drei Records mit Mittelwerten im Gold haben Priorität.

### 5.2 Vorgabe-Gold-Konflikte sind die teuerste Fehlerklasse

**Befund.** 14 der 25 falschen Zellen des Hauptlaufs waren keine Modellfehler,
sondern eine falsche Vorgabe (Comparator `baseline` statt TAU). Der Teillauf
belegt es: 14/14 richtig, sobald das Feld stimmt.

**Warum es bremst.** Derselbe Fehlertyp ist bei den übrigen Records **nicht
geprüft**. 65 Records tragen ein Comparator-Feld, das einen Arm nennt
(`Control`, `Placebo`, `P group`, Arzneimittel …) — plausibel, aber nicht gegen
die Artikelspalte verifiziert. Bei drei Goldzellen derselben Tabelle war das Gold
selbst falsch (291 SD, 294 Komparator, 295 SD). Jede solche Zelle kostet
Precision und sieht im Bericht wie ein Modellfehler aus.

**Nächster Hebel.** Eine read-only Prüfung der Armfelder gegen die Tabellenzeile,
wie sie für 289–295 gelaufen ist (`pruefe_armzeile_289_295.py`,
`analyse_mccb_armzeile.py`). Kostet keine Tokens, nur Zeit. Vor jedem weiteren
Netzlauf ist das der günstigste Schritt.

### 5.3 Das Gold selbst ist fehleranfällig bei Pre/Post-Tabellen

**Befund.** Drei Goldzellen in einer einzigen Tabelle waren falsch, alle nach
demselben Muster: Wert aus der Nachbarzeile oder Nachbarspalte (291 Pre-SD,
294 Spalte 5, 295 Pre-SD). Die Mittelwerte stimmten, nur der SD verriet es.

**Warum es bremst.** Solche Fehler sind mit Kennzahlen allein nicht sichtbar —
sie sehen wie Modellfehler aus, und das Modell wird für etwas bestraft, was es
richtig macht. Bei 295 steht die Korrektur noch aus: Gold 11,1, Artikel
`FAT Post` 39,3 ± 10,4 (Pre-Zeile: 39,3 ± 11,1).

**Nächster Hebel.** Version 4 mit der 295-Zelle und einer systematischen
Spaltenprüfung für alle Tabellen mit Pre/Post-Zeilen. Der Wert steht in der
Tabelle, der Aufwand ist Textarbeit.

### 5.4 Die Auswertung hat blinde Flecken

**Befund.** Drei Stellen verzerren die Kennzahlen:

* `_kanonisch` kennt nur Baseline-Synonyme. `klassifiziere("post (after 4-week
  training)", "Post")` ergibt `rueckfall` — alle 42 Zellen des V3-Teillaufs
  landen im Rückfall-Bucket, obwohl das Modell den Zeitpunkt korrekt meldet.
  Die sieben Records können nie „zieltreu" werden.
* 10 Zellen ohne Gold zählen in der Precision als Fehler: 105 von 142
  gemeldeten Zellen richtig (P 0,7394). Nimmt man die 10 aus der Bezugsgröße,
  sind es 105 von 132 (P 0,7955).
* Die zwei Timeout-Records fehlen in jeder Kennzahl, ohne Hinweis in der
  Kopfzeile.

**Warum es bremst.** Die Kennzahlen unterschätzen das Modell an genau den
Stellen, an denen die Datenbasis schwach ist. Wer nach F1 optimiert, optimiert
gegen Messfehler.

**Nächster Hebel.** Zielzeitpunkt-Normalisierung um „post"/„after intervention"
erweitern, Zellen ohne Gold getrennt ausweisen (wie schon bei
`unsichere_ziele`), fehlende Records in der Auswertung nennen. Reine
Auswertungsarbeit, kein Netzzugriff.

### 5.5 Jede Erkenntnis kostet einen Lauf

**Befund.** Der Hauptlauf kostet 552.552 Tokens, ein 7-Record-Teillauf 24.768 —
Faktor 22. Die Projektregel erlaubt 2–3 Läufe pro Untersuchungsfrage; der
Hauptlauf ist verbraucht, der V3-Teillauf auch.

**Warum es bremst.** Jede offene Frage (Armfelder, Abdeckung, Spaltenprüfung)
konkurriert um dasselbe knappe Gut. Blinde Wiederholungen sind ausgeschlossen,
also muss jeder Lauf vorher durch Textarbeit so weit vorbereitet sein, dass er
eine Ja/Nein-Frage beantwortet.

**Nächster Hebel.** Weiterhin Teilläufe über `--ids` statt Gesamtläufe, und
vorab festgelegte Abbruchkriterien wie bei der Armzeilen-Prüfung (das hat
funktioniert: 0/10 war ein klares Ergebnis). Ein neuer Hauptlauf erst, wenn
Version 4 steht — sonst misst er wieder die Vorgabe statt das Modell.

### 5.6 Der Prompt-Hebel ist weitgehend ausgereizt

**Befund.** Die Gruppengrößen-Zeile hat die Primärausfälle von 2 auf 6 (lang)
bzw. 5 (kurz) gehoben. Der Armzeilen-Zusatz brachte 0/10 und wurde entfernt.
Der Rückfall-Bucket bleibt mit P 0,6667 der schwächste Teil.

**Warum es bremst.** Weitere Prompt-Zusätze haben in zwei von drei Versuchen
nichts gebracht; jeder kostet einen Lauf. Die verbleibenden Fehler streuen über
viele Dokumente statt sich auf ein Muster zu konzentrieren.

**Nächster Hebel.** Keine neuen Prompt-Zusätze ohne vorherige Textdiagnose. Die
16 falschen Rückfallzellen einzeln am Artikel prüfen — erst wenn dort ein Muster
sichtbar ist, lohnt ein Prompt-Eingriff.

## 6. Was nicht geprüft ist

* Kein Vergleichslauf auf denselben 76 Records mit Version 3 — die Kennzahlen
  des Hauptlaufs sind Version-2-Zahlen und nicht mit dem V3-Teillauf mischbar.
* Keine Prüfung der Comparator-Felder, die einen Arm nennen (65 Records).
* Kein zweites Modell, kein zweiter Promptstand auf derselben Basis.
* Die Armzeilen-Zuordnung ist eine Heuristik über den nächsten Zeilenkopf, kein
  Tabellenparser.

## 7. Nächste Schritte (Reihenfolge nach Hebel je Token)

1. **Version 4**: Gold 295 auf 10,4; Spaltenprüfung der Pre/Post-Tabellen.
   Kein Netzzugriff.
2. **Auswertung reparieren**: `_kanonisch` um „post" erweitern, Zellen ohne Gold
   trennen, fehlende Records ausweisen. Kein Netzzugriff.
3. **Armfelder prüfen**: read-only, 65 Records, Stichprobe oder vollständig.
4. **Abdeckungslauf** über die Records ohne Antwort (kleine `--ids`-Liste).
5. **Hauptlauf auf Version 4** — erst danach, mit fixierten Abbruchkriterien.

## Quellen

* `test76_hauptlauf.md` — Hauptlauf, Kennzahlen, Fehlerklassen
* `korrektur_yun2024_479.md` — Version 2
* `comparator_pruefung.md` — Prüfung am Artikel, 11 unklare Comparator-Felder
* `korrektur_v3_comparator.md` — Version 3
* `v3_comparator_289_295.md` — V3-Teillauf, 14/14
* `armzeile_pruefung_291_295.md` — gescheiterter Prompt-Zusatz
* `teststrategie.md`, `test76_sha256.txt` — Basis und Hashes
* Läufe unter `runs/`: `test76_hauptlauf_20261116`, `v3_comparator_289_295_20261116`,
  `armzeile_291_295_20261116`
