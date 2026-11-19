# Sprint 48: Entscheidungsvorlage fuer die fuenf Records mit Strukturplan

Frage: Welche der fuenf Ausfaelle mit vorhandenem Strukturplan rechtfertigen einen
Nachzug mit 24.000 Tokens, welche bleiben Ausfall? **Rein lesend.** Kein Lauf
gestartet, keine Anfrage gesendet, keine Predictions, kein Gold und keine
eingefrorene Eingabe veraendert.

## 1. Gegenstand

Der P5-Lauf `yun699_p5_24000_20261118` hat 103 Zeilen: **67 verwertbar**, **33**
`length_ohne_ergebnis` und **3** Antworten ohne Zellen. Nur die 33 sind
Budgetfaelle; die drei leeren (`yun2024:137`, `:268`, `:269`) endeten mit 575,
2.501 und 3.842 Tokens und `finish_reason = stop`, also innerhalb des Budgets —
sie brauchen eine andere Aufgabe, nicht mehr Budget.

Von den 33 haben **fuenf** einen Strukturplan (Strategien A-E) aus der
Offline-Messung: `yun2024:30`, `:252`, `:421`, `:672`, `:678`. Nur diese fuenf
werden hier entschieden.

## 2. Datenbasis und Methode

| Quelle | Verwendung |
|---|---|
| `runs/yun699_p5_24000_20261118/predictions.jsonl` | Ausfallzeilen, `completion_tokens`, `reasoning_chars`, `finish_reason` |
| `iterativ/ergebnisse/sprint48_budgetdiagnose.json` | Tabellenstruktur, Planzahlen, Hypothesen |
| `analysis/offline_struktur_20261118b/structure.json` | Quelle der Planzahlen (`units`, `prompt_chars`, `gold_reachable`) |
| `runs/yun699_8000_alle_20261117/predictions.jsonl` | Vorlauf mit `max_tokens = 24000` fuer dieselben 33 IDs |
| `yun_full/records/yun699.jsonl` | Goldzellen |
| `yun_full/werte_p5_aus.py` (`deckung()`) | Nachrechnung adressiert/wertgleich, Feld und Arm, Toleranz 1e-6 |

Zwei Definitionen, die die Entscheidung tragen:

- **`gold_reachable`** zaehlt nur Goldzellen der **Outcome-Zeile** (Spaltenfeld
  **und** Zeile). Gruppenangaben aus dem Kopf (`n = 456`) zaehlen nicht mit: sie
  sind noch kein gelesener Zellwert (`table_decomposition/run_benchmark.py`).
- **`_cb`** im Feld `prompt_version` ist ein **Cache-Buster**, kein eigener
  Prompt (`versions.py` entfernt das Suffix bei der Kanonisierung,
  `run_extended_extraction.py` setzt es nur beim Frischgenerieren). Der Vorlauf
  `v2_timepoint_cb` und der P5-Lauf `v2_timepoint` sind damit derselbe Prompt;
  am Prompttext hat sich seit dem 16.11. nichts geaendert (kein Commit aendert
  `build_prompt`, `_felder` oder `PROMPT_VERSION`).

Damit ist der Vorlauf ein gueltiger Vergleichsmassstab: **derselbe Prompt,
dasselbe Budget, frische Generierung.**

## 3. Die fuenf Records

| Record | PMC | Prompt (Zeichen) | Tabellen (mit Zielfeld) | Datenzellen | Gold | Plan B (Zeichen/Einheiten) | Gold erreichbar (A-E) | Vorlauf 24k: Zellen / adressiert / wertgleich | Vorlauf Tokens | Vorlauf Abschluss | P5-Ergebnis |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| `yun2024:30` | PMC3003523 | 26.854 | 3 (1) | 56 | 6 | 2.398 / 1 | **1** | 6 / 6 / **2** | 13.845 | stop | length |
| `yun2024:252` | PMC5614421 | 41.138 | 3 (1) | 100 | 2 | 5.318 / 1 | 0 | 24 / 2 / **2** | 22.222 | stop | length |
| `yun2024:421` | PMC3877023 | 27.320 | 4 (4) | 49 | 6 | 5.489 / 1 | 0 | 2 / 2 / **2** | 24.000 | length | length |
| `yun2024:672` | PMC4550271 | 43.591 | 5 (0) | 467 | 2 | 11.612 / 3 | 0 | 0 / 0 / **0** | 24.000 | length | length |
| `yun2024:678` | PMC5777419 | 13.328 | 3 (3) | 115 | 2 | 6.461 / 1 | 0 | 6 / 2 / **2** | 10.888 | stop | length |

Alle fuenf haben im P5-Lauf genau 24.000 Tokens im Reasoning verbraucht
(`content_chars = 0`, `finish_reason = length`). Der Vorlauf zeigt fuer vier von
ihnen, dass dasselbe Budget reicht — fuer `yun2024:672` nicht.

## 4. Was der Strukturplan leistet — und was nicht

Der Plan ist eine **Prompt-Verkuerzung**, keine Gold-Abdeckung:

- `yun2024:30`: Strategie B senkt den Prompt von 26.854 auf **2.398** Zeichen
  (91 % weniger), erreicht aber nur **1 von 6** Goldzellen.
- `yun2024:252`, `:421`, `:672`, `:678`: erreichen **0** Goldzellen, weil die
  Goldzellen Gruppengroessen aus dem Tabellenkopf sind — genau die Angaben, die
  `gold_reachable` ausdruecklich nicht mitzaehlt.
- `yun2024:672` hat zusaetzlich **0 Tabellen mit Zielfeld** bei 467 Datenzellen
  und 36 Zeilen je Tabelle: der Parser ordnet das abgefragte Feld keiner Tabelle
  zu (H4b). Ein Ausschnitt dieses Dokuments kann die 2 Goldzellen nicht liefern.

**Folgerung:** Ein planbasierter Nachzug (Ausschnitt statt Volltext) rechtfertigt
sich fuer **keinen** der fuenf aus der Gold-Abdeckung. Er kann hoechstens das
Reasoning verkleinern. Die Entscheidung unten stuetzt sich deshalb auf den
Vorlauf mit dem **unveraenderten Volltext-Prompt**.

## 5. Der Vorlauf als Erwartungswert

Fuer alle 33 aktuellen Budgetfaelle liegt eine Zeile mit `max_tokens = 24000`
aus `yun699_8000_alle_20261117` vor:

| Kennzahl | Wert |
|---|---:|
| Zeilen mit 24k-Vorlauf | 33 von 33 |
| davon mit Zellen | 18 |
| davon mit mindestens einer wertgleichen Goldzelle | 15 |
| Zellen gesamt | 102 |
| davon adressiert (Feld und Arm) | 70 |
| davon wertgleich | 43 |
| Completion-Tokens gesamt | 560.694 (Median 19.839, Mittel 16.991) |
| Abschluesse | 17 x stop, 14 x length, 2 x ohne Abschlussgrund |

Ein pauschaler Nachzug aller 33 waere damit eine **Wiederholung mit
Muenzwurf-Charakter**: rund 561.000 Tokens fuer hoechstens 43 richtige Zellen,
also etwa 13.000 Tokens je richtiger Zelle gegen 8.232 im P5-Lauf
(1.399.558 Tokens / 170 wertgleiche Zellen).

## 6. Entscheidung je Record

| Record | Entscheidung | Begruendung |
|---|---|---|
| `yun2024:678` | **Nachzug ja (1 x 24.000)** | Einziger Fall mit belastbarem Ertrag: beide Goldzellen (Interventions- und Vergleichsgruppengroesse) im Vorlauf **wertgleich** getroffen, 6 Zellen geliefert, Abschluss `stop` bei **10.888 Tokens** (45 % des Budgets, also Luft). Kleinster Prompt der fuenf (13.328 Zeichen), 3 von 3 Tabellen tragen das Zielfeld. |
| `yun2024:30` | **Ausfall bleiben** | Der Vorlauf adressiert alle 6 Goldfelder, trifft aber nur **2** Werte. Der Fehler ist inhaltlich (falsche Werte je Feld/Arm), nicht Budget: ein weiterer 24k-Lauf wiederholt eher die Fehlzuordnung. Plan erreicht 1 von 6 Goldzellen. |
| `yun2024:252` | **Ausfall bleiben** | 2 von 2 Goldzellen im Vorlauf wertgleich, aber der Erfolg kostete **22.222 Tokens** (93 % des Budgets) bei 41.138 Zeichen Prompt. Derselbe Ertrag wie `yun2024:678` zum doppelten Preis; ein Fehlversuch verbrennt volle 24.000. |
| `yun2024:421` | **Ausfall bleiben** | Auch der Vorlauf endete auf **24.000 Tokens mit `length`** und lieferte nur 2 Zellen; 4 der 6 Goldzellen blieben offen. Die Decke liegt bei diesem Prompt unter dem Budget, nicht bei der Reproduzierbarkeit. |
| `yun2024:672` | **Ausfall bleiben** | Zwei 24k-Laeufe (Vorlauf und P5) ohne eine einzige Zelle; 0 Tabellen mit Zielfeld, 0 erreichbare Goldzellen im Plan, 467 Datenzellen in 5 Tabellen. Ohne anderen Pfad aussichtslos. |

Kurz: **1 von 5 rechtfertigt einen Nachzug, 4 bleiben Ausfall.**

## 7. Kosten und Ertrag der Empfehlung

| Posten | Wert |
|---|---|
| Nachzug | `yun2024:678`, 1 Auftrag |
| Obergrenze | 24.000 Completion-Tokens |
| Gemessen im Vorlauf | 10.888 Tokens, `finish_reason = stop` |
| Erwartungswert aus dem Mittel der 33 Vorlaufzeilen | 16.991 Tokens (Schaetzung, kein Messwert fuer diesen Lauf) |
| Ertrag im Erfolgsfall | 6 Zellen, 2 wertgleich |
| Wirkung auf den Kopfwert (Rechnung) | Recall 170/423 = 0,402 -> 172/423 = 0,407, also **+0,5 Prozentpunkte** |

Der Eingriff in die Kennzahl ist klein. Der Nachzug ist deshalb nur dann
sinnvoll, wenn die zwei Zeilen fuer die Vollstaendigkeit des Bildes gebraucht
werden — nicht als Hebel auf Recall oder F1.

Wenn kein Budget fuer eine Varianzziehung ausgegeben werden soll, ist die
Alternative eindeutig: **auch `yun2024:678` bleibt Ausfall**, und die 36
Ausfaelle werden als Ausfall berichtet. Das ist die ehrlichere Variante, wenn
der naechste Lauf ohnehin eine geaenderte Aufgabe testet.

## 8. Die uebrigen 28 Budgetfaelle

Von den 28 ohne Strukturplan hatten im 24k-Vorlauf **11** mindestens eine
wertgleiche Goldzelle (15 insgesamt minus der vier Plan-Records mit Treffer).
Ein pauschaler Nachzug ueber alle 28 kostet bis zu 672.000 Tokens
Obergrenze; gemessen kosteten die 33 Vorlaufzeilen zusammen 560.694. Sie
bleiben Ausfall, bis ein geaenderter Prompt (Tabellenausschnitt, Prosa-Pfad)
getestet wird — nicht mit dem unveraenderten Volltext.

## 9. Was die Entscheidung kippen wuerde

- Ein Nachweis, dass ein Ausschnitt-Prompt die Goldzellen der Outcome-Zeile
  **und** die Kopfangaben (`n = ...`) gemeinsam mitfuehrt: dann waeren
  `yun2024:30`, `:421` und `:678` planbasiert interessant.
- Ein Messwert, dass `yun2024:678` bei 24k **zweimal** in Folge scheitert: dann
  ist der Vorlauf ein Ausreisser und der Fall bleibt Ausfall.
- Eine Entscheidung, die 36 Ausfaelle vollstaendig zu berichten statt sie zu
  reparieren: dann entfaellt jeder Nachzug.

## 10. Grenzen

- Der Vorlauf lief am 17.11.2026 gegen denselben Endpunkt, aber zu einer anderen
  Tageszeit; Anbieterlast und Serving koennen streuen. Das ist Teil der Varianz,
  die hier gemessen wird, und kein kontrollierter Faktor.
- `adressiert` und `wertgleich` sind die Selbstpruefung aus
  `werte_p5_aus.py`, nicht die offizielle Bewertung. Die offizielle Bewertung
  bleibt der geschuetzte Bewertungslauf.
- `gold_reachable` ist eine Obergrenze des Tabellenpfads, keine Modellleistung.
- Die Tokenzahlen des Vorlaufs sind gemessen; der Erwartungswert fuer den
  Nachzug ist aus dem Mittel abgeleitet und als Schaetzung markiert.
