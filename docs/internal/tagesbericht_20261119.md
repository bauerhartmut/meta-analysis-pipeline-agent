# Tagesbericht 19.11.2026

Zusammenfassung aller Berichte dieses Tages. Zahlen sind aus den jeweils
genannten Artefakten, Commits oder Messungen gelesen; Schaetzungen sind als
solche markiert. Kein Wert dieses Berichts ist neu erhoben worden.

## 0. Kennzahlen des Tages

| Kennzahl | Wert |
| --- | --- |
| Commits | **28** (erster 10:33 `e968564`, letzter 22:01 `ec60b85`) |
| P5-Lauf | gestartet 10:02, abgebrochen 10:14, neu gestartet 10:27, Ende 13:14 mit 103 Zeilen |
| P5-Nachzug | 38 Auftraege, 24 gerettet, 14 endgueltig gescheitert, 576.082 Completion-Tokens |
| P5 verwertbar | 43 -> **67** von 103 |
| P5 wertgleich (Feld und Arm) | 114 -> **170** |
| Recall / F1 | 0,270 -> **0,402** / 0,381 -> **0,493** |
| Strukturplan | **97** Goldfelder in A-E, **71** nicht widerlegt, 0 Fehler, 60/60 komplett |
| Arm-Alias | 94 -> 97 Feldtreffer, 68 -> 71 nicht widerlegt |
| Tests | 94 passed (Harness/Nachzug), 52 passed (Engine/Validierung) |
| Push | Seitenzweig `sprint48` bei `ec60b85`; `origin/master` unveraendert `83fbfe1` |

## 1. Was heute geschafft wurde

1. **P5-Wiederanlauf betrieblich abgesichert:** Bestandsaufnahme, verwaiste
   Gate-Sperre uebernommen, Wache neu gestartet, Anbieterkapazitaet mit einem
   Vortest geprueft, danach den Lauf neu gestartet.
2. **Wiederaufnahme im Harness eingebaut:** 503, 429 und Timeout halten einen
   Auftrag jetzt am Leben (bis 4 Versuche, 90 Minuten Frist), statt ihn sofort
   als Ausfall zu verbuchen.
3. **P5-Nachzug gefahren:** 38 echte Anbieterausfaelle wiederholt, 24 gerettet,
   je Record genau eine Zeile hinterlassen.
4. **P5-Auswertung neu gerechnet:** 67 statt 43 verwertbare Records, F1 von
   0,381 auf 0,493, Positivkontrolle gruen.
5. **33 Budgetabbrueche diagnostiziert:** nicht Tabellenkomplexitaet, sondern
   Reasoning-Umfang; 13 der 33 ohne strukturelle Hypothese.
6. **Gold-Abdeckung des Strukturplans belastbar gemacht:** Planwerte neu
   erzeugt (94 Goldfelder), Kopfangaben und Goldquellen geprueft, Arm- und
   Wertbindung auf der Plan-Auswahl gemessen.
7. **Kuratierte Alias-Zuordnung** (Control -> PBO, Definition -> IPAT) hebt drei
   Zellen: **97 Goldfelder, 71 nicht widerlegt**.
8. **Neues Validierungs-Finding** `validate_arm_context` meldet
   Kopf-Kontext-Widersprueche, ohne Arme umzuhaengen.
9. **Push-Befund geklaert und Arbeit veroeffentlicht:** `origin/master` ist ein
   elternloser Snapshot, deshalb kein Rebase, sondern Seitenzweig `sprint48`.

## 2. Verlauf

| Zeit | Etappe | Beleg |
| --- | --- | --- |
| 09:59-10:24 | Bestandsaufnahme, verwaiste Sperre, Vortest der Anbieterkapazitaet | `docs/internal/p5_wiederanlauf_20261119.md`, `e968564` |
| 10:27-13:14 | P5-Lauf mit 103 Records bis zum Ende | `runs/yun699_p5_24000_20261118` |
| 10:33-13:04 | Wiederaufnahme im Harness, Nachzug-Werkzeug, eine Zeile je Record | `35a9211`, `e21397f` |
| 13:36-14:56 | Nachzug der 38 Anbieterausfaelle | `70d445c`, `a1e9bf5`, `runs/nachzug_p5_20261119.log` |
| 15:01-15:20 | Neubewertung (67 verwertbar), Zusammenfassung, Budgetdiagnose | `8c2433d`, `aeaabc2`, `454cb24` |
| 19:38-20:16 | Sechs Records ohne Tabelle, Entscheidung der fuenf Planfaelle | `ee0518d`, `ac1946d`, `d5ddab7` |
| 20:58-21:19 | Kopfangaben, Herkunft der 46, neun Goldwerte, Planwerte neu | `07ac6e5`, `7cbc72d`, `767cf73`, `911e593` |
| 21:19-21:49 | Arm-/Wertpruefung, Ursachen der 26 Zellen, 68/94 als Obergrenze | `b4c4515`, `e1f5f7b`, `3b2c2b7`, `aae8902`, `2c1fa56`, `ef95ddb` |
| 21:53-22:01 | Validierung vereinfacht, Alias-Zuordnung, Struktur neu, Push-Befund, Haertung | `de6c71c`, `428018d`, `ba36b5b`, `11d2621`, `7d16ec2`, `fe52b4f`, `ec60b85` |

## 3. P5: Wiederanlauf und Betriebspruefung

Ausgangslage um 09:59: kein Python-Prozess, P5 nie gestartet, Gate-Datei mit
PID 6630 verwaist, letzter Logeintrag des Vortags 18:30:54, Nonce abgelaufen.

| Punkt | Ergebnis |
| --- | --- |
| Verwaiste Sperre | von `starte_p5_wenn_frei.sh` ueber `pid_lebt` erkannt und uebernommen |
| Wache | PID 959, Frist 720 min, Takt 60 s, Ruhe 180 s |
| Erster Start | 10:02:46, 103 Records, 2 Threads |
| Abbruch | 10:14:09 nach 7 Records, 0 Completion-Tokens (4 x 503, 2 x Timeout, 1 x 429) |
| Vortest | `p5_vortest_20261119_102008`: HTTP 200, 1400 Tokens, Abschluss `length` |
| Neustart | 10:27:05, 96 offene Auftraege (7 Fehlzeilen galten als erledigt) |

Der Abbruch war richtig: bei 1 Record je 2 Minuten haette der Lauf rund 3,5
Stunden nur Ausfaelle geschrieben und danach die Wache gegen jeden spaeteren
Lauf gesperrt. Sicherungen liegen in `runs/_sicherung_20261119/`.

## 4. P5: Wiederaufnahme im Harness

Neues Modul `yun_full/wiederaufnahme.py`, im Harness ueber drei Optionen
gesteuert (`--wiederaufnahme-versuche` Standard 4, `--wiederaufnahme-basis`
30 s, `--wiederaufnahme-frist` 90 min).

- Wiederholbar sind nur `server_fehler` (503), `rate_limit` (429), `timeout`
  (Status 0) und `verbindungsfehler`; `auth`, `anfrage_ungueltig` und
  `budget_im_reasoning` bleiben endgueltig.
- Waehrend der Wartezeit bleibt der Auftrag auf `running`, es entsteht **keine**
  Zwischenzeile; erst nach der letzten Wiederholung oder abgelaufener Frist
  wird die Fehlerzeile mit `wiederaufnahmen: n` geschrieben.
- Wartezeiten bei Basis 30 s: rund 30, 60, 120, 240 s (zusammen etwa 7,5 min).
- `Retry-After` wird bewusst nicht verwendet: ein 429 mit "Retry after 1
  seconds" ist eine Drossel je Aufruf, keine Kapazitaetsaussage.

Grenze: Der laufende P5-Lauf hatte die alte Fassung geladen; seine Zeilen tragen
kein Feld `wiederaufnahmen`, einzelne 503 blieben dort Ausfaelle.

## 5. P5: Nachzug der Anbieterausfaelle

`yun_full/nachzug_p5.py` wiederholt nur Anbieterausfaelle, nicht Budgetgrenzen.

| Groesse | Wert |
| --- | --- |
| Fehlzeilen nach dem Lauf | 60 |
| ausgewaehlt | 38 (28 x 503, 8 x Timeout, 2 x 429) |
| ausgelassen | 22 (20 x `length_ohne_ergebnis`, 2 x ohne Zellen) |
| Tokens der ausgelassenen Zeilen | 486.343 |
| Kostenschaetzung Obergrenze | 912.000 (38 x 24.000) |
| Kostenschaetzung Erwartung | 297.931 (38 x 7.840 Mittel der Erfolge, Schaetzung) |

Lauf 13:41:48 bis 14:56:02 (74 Minuten), 2 Threads, 15 Wiederaufnahmen:

| Ergebnis | Wert |
| --- | --- |
| erfolgreich (Zellen geschrieben) | 24 |
| endgueltig gescheitert | 14 (13 x `length_ohne_ergebnis`, 1 x ohne Zellen) |
| Completion-Tokens | 576.082 |
| Harness-Exitcode | 0 |

Aufraeumen (`eindeutig_machen`): 141 Zeilen gelesen, 38 Duplikate entfernt,
0 unlesbar, **0 Records ohne genau eine Zeile**; danach 103 Zeilen. Sicherungen:
`predictions.vor_nachzug_20261119.jsonl` (13:14) und `predictions.jsonl.bak`.

Stand danach: 67 verwertbar, 3 Antworten ohne Zellen, 36 Ausfaelle (33 x
`length_ohne_ergebnis`, 0 x 503/429/Timeout). Exitcode 4 ist die bewusste
Meldung "es bleiben Ausfaelle".

## 6. P5: Neubewertung 13:14 gegen 15:04

`werte_p5_mit_kontrolle.sh`: Positivkontrolle gruen (alle 12 Kennzahlen, 22
Klassenzahlen, 25 Werte in Bilanz und Zellprotokoll stimmen), Auswertung Exit 0.

| Kennzahl | 13:14 | 15:04 |
| --- | ---: | ---: |
| gerettet (Antwort mit Zellen) | 43 | **67** |
| fertig, aber ohne Zellen | 2 | 3 |
| weiter ausgefallen | 58 | **33** |
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

Der Nachzug ist der groesste Einzelhebel bisher: +24 verwertbare Records, +23,5
Punkte Rettungsquote, +11,2 Punkte F1, +92 Zellen. Die Precision sinkt um 1,4
Punkte (mehr Dubletten und Fremdschluessel: `ueberzaehlig` 46 -> 80,
`fremdschluessel` 15 -> 17), netto ueberwiegt der Gewinn (TP +56 gegen FP +36).
Die Momentaufnahme `runs/p5_auswertung_stand1314/` bleibt absichtlich bei 43.

## 7. Sprint 48: Diagnose der 33 Budgetabbrueche

Rein lesend, 33 `length_ohne_ergebnis`-Zeilen gegen 67 verwertbare.

| Kennzahl | Ausfaelle | Erfolge |
| --- | ---: | ---: |
| Reasoning-Zeichen, Median | 95.071 | 31.444 |
| Completion-Tokens, Median | 24.000 | 8.388 |
| Tabellen, Median | 2 | 3 |
| Datenzellen, Median | 49 | 60 |
| Dauer, Median | 191,5 s | 76,2 s |

| Hypothese | Ausfaelle | Erfolge | Differenz |
| --- | ---: | ---: | ---: |
| H1 Tabellenkomplexitaet | 17/33 (51,5 %) | 24/67 (35,8 %) | 15,7 Pp |
| H2 zu viele Zellen | 7/33 (21,2 %) | 19/67 (28,4 %) | -7,2 Pp |
| H3 mehrstufige Koepfe | 9/33 (27,3 %) | 9/67 (13,4 %) | 13,9 Pp |
| H3G Gruppenkopf-Zellen | 11/33 (33,3 %) | 9/67 (13,4 %) | 19,9 Pp |
| H4a grosse Prompt | 12/33 (36,4 %) | 14/67 (20,9 %) | 15,5 Pp |
| H4b keine Tabelle mit Zielfeld | 24/33 (72,7 %) | 51/67 (76,1 %) | -3,4 Pp |
| H6 Ausgabeumfang | 9/33 (27,3 %) | 16/67 (23,9 %) | 3,4 Pp |

Befund: Die Ausfaelle sind strukturell **nicht** die groesseren Faelle. Gesichert
ist nur der Mechanismus (Budget im Reasoning, 0 Zeichen Inhalt); eine einzelne
Ursache ist nicht belegt, 13 der 33 haben keine strukturelle Hypothese.
Sechs Records (`119`, `164`, `273`, `304`, `624`, `625`) haben **keinen
Tabellentext im Markdown**: der Tabellenkoerper ist durch `![]()` ersetzt, es
gibt keine Pipe-Zeile.

## 8. Sprint 48: Gold-Abdeckung, Kopfangaben und Goldquellen

### 8.1 Planwerte neu erzeugt

`offline_struktur_20261119` (Auswahl-SHA256 unveraendert
`c22ed3fb42dbaaff7051a89cdb327c4b250a134db0a62a19d3877d5ba311c0b1`):

| Strategie | Gold erreichbar alt -> neu | komplett alt -> neu | Fehler alt -> neu |
| --- | --- | --- | --- |
| A-E | 46 -> **94** | 57/60 -> **60/60** | 7 -> **0** |

Ursache ist die Kopfangaben-Zaehlung aus Sprint 44 (`reachable_cells` fuehrt
`n = ...` als `(-1, feld)`), nicht die Auswahl. 23 von 59 Records aendern die
Reichweite, 29 Einheiten oder Prompt-Zeichen.

### 8.2 Kopfangaben der 33 Budgetfaelle

33 Records, 132 Goldzellen, davon 62 Gruppengroessen:

- **16 Goldzellen (12,1 %)** stehen als `n = ...` im Tabellenkopf: 8 mit
  belegtem Arm, 8 ohne.
- 46 Gruppengroessen ohne passende Kopfangabe: 16 nur Fliesstext, 1 nur Caption,
  4 nur Tabellenzelle, 9 an mehreren Stellen, 7 nur ohne Gruppen-Kontext,
  **9 nirgends im Markdown**.
- Ueber die Outcome-Zeile erreichbar: 10 von 132; 7 nur ueber eine Kopfangabe,
  115 weder ueber Zeile noch Kopfangabe.
- Ein Kopf-Fakten-Prompt erreicht hoechstens **28 von 132 (21,2 %)**; dokumentweit
  vollstaendig abgedeckt ist unter den Planfaellen nur `yun2024:678`.

### 8.3 Die neun Goldwerte ohne Fundstelle

Das `source`-Feld traegt nur den Feldnamen, keine Tabelle oder Zeile. Fuenf
Zellen gehoeren zu Records, die die Rohdaten selbst als Grafik-Tabelle,
Abbildung oder unvollstaendig markieren (`164`, `171`, `173`, `273`); vier
Zellen (`523`, `525`) sind als vollstaendig markiert, die `15` steht aber nur
als `0.15` im Markdown. Bei `523`/`525` ist sie ableitbar: 9+6 = 15, 8+7 = 15,
30/2 = 15, bestaetigt durch die Prozentwerte 60/40 und 53,3/46,7. Fuer alle neun
Zellen ist ein Textpfad ausgeschlossen; sie sind kein Prompt-Fehler.

### 8.4 Entscheidung der fuenf Planfaelle

| Record | Entscheidung | Begruendung |
| --- | --- | --- |
| `yun2024:678` | Nachzug ja (1 x 24.000) | beide Goldzellen im Vorlauf wertgleich, `stop` bei 10.888 Tokens |
| `yun2024:30` | Ausfall | Vorlauf adressiert 6 Felder, trifft 2 Werte; Fehler ist inhaltlich |
| `yun2024:252` | Ausfall | 2/2 wertgleich, aber 22.222 Tokens (93 % des Budgets) |
| `yun2024:421` | Ausfall | auch im Vorlauf `length` bei 24.000, nur 2 Zellen |
| `yun2024:672` | Ausfall | zwei 24k-Laeufe ohne Zelle, 0 Tabellen mit Zielfeld |

Kurz: 1 von 5 rechtfertigt einen Nachzug. Rechnerische Wirkung im Erfolgsfall:
Recall 170/423 -> 172/423, also +0,5 Prozentpunkte (`yun2024:678`, Rechnung,
kein Messwert).

## 9. Sprint 48: Arm- und Wertpruefung auf der Plan-Auswahl

Grundgesamtheit: die je Record von `load_tables` ausgewaehlte Tabelle, dieselbe
Pipeline wie `run_benchmark.py --offline`.

| Klasse der 71 Kopftreffer | Zellen |
| --- | ---: |
| Wert **und** Arm passend | 45 |
| Wert des anderen Arms (Arm vertauscht: 335, 336, 678, 682) | 4 |
| anderer Wert | 22 |

Damit sind **71 von 97** Feldtreffern nicht durch eine wertabweichende
Kopfangabe widerlegt (**Obergrenze**; Zeilenzellen und Messwerte sind nicht
wertgeprueft). Bandpruefung aller 117 Kopfangaben nach der Alias-Zuordnung:
113 ok, 0 gemischt, 0 falsch, 4 ohne Arm (vor der Alias-Zuordnung 114 / 110).
Summe 97 = Sollwert 97 aus `structure.json`.

Ursachen der 26 wertabweichenden Zellen:

| Ursache | Zellen | Records |
| --- | ---: | --- |
| Untergruppe oder geteilter Arm im selben Tableau | 17 | 78, 79, 172, 174, 265, 266, 426, 531, 532, 645, 647 |
| Goldwert in anderer Tabelle (andere Population) | 5 | 185, 194, 196 |
| Arm-/Spaltenfehlbindung | 4 | 335, 336, 678, 682 |

Zwei Spaltenzuordnungen wurden am Kopf belegt: bei `678`/`682` steht `(n=16)`
ueber der Probiotic- und `(n=15)` ueber der Antibiotic-Gruppe, der Kopf stuetzt
also das Gold, nicht die kontexttreue Plan-Bindung; bei `426` ist Short-Bore als
comparator richtig, falsch sind die fehlende Open-Zuordnung und die P-Wert-Spalte
als comparator. Entscheidung: **Der Kontext bleibt massgeblich**, die
kopf-treue Variante wird nicht eingefuehrt.

## 10. Sprint 48: Alias-Zuordnung und 97/71

Drei Records mit Alias-Luecke statt Widerspruch:

| Record | Alias | vorher wertrichtig | nachher wertrichtig |
| --- | --- | --- | --- |
| `yun2024:30` | Control -> `PBO + MTX` | 393 intervention | 393 intervention, **199 comparator** |
| `yun2024:15` | Definition -> `IPAT` | 103 intervention | 103 intervention, **97 comparator** |
| `yun2024:16` | Definition -> `IPAT` | 103 intervention | 103 intervention, **97 comparator** |

Ergebnis: Feldtreffer **94 -> 97**, nicht widerlegt **68 -> 71**. Nur diese drei
Records aendern sich (je 1 -> 2).

Umsetzung:

- `_ARM_ALIASEN` in `research_agent/table_decomposition/semantics.py`, auf
  `(record_id, Armtext)` geschluesselt; `record_id` kommt ueber `context_of` in
  den Tabellenkontext, `bind_arm`/`_score` und `_group_size_facts` reichen sie
  durch. Damit greifen Spaltenarme **und** Kopfangaben.
- Haertung: Schluessel und Armtext laufen beide durch `_normalise_arm`, damit
  Satzzeichen, Fussnotenmarker oder doppelte Leerzeichen den Alias nicht
  stillschweigend abschalten (Testfall `Control.` bindet weiter). Die fachliche
  Begruendung steht als Kommentar an der Tabelle.
- Generisch bleibt es bei der Textbewertung: ohne passenden Record-Schluessel
  aendert sich nichts (`test_arm_alias_curated_only_for_record`).

`structure.json` nach dem Neulauf `offline_struktur_20261119d` (gleiches `--out`
`offline_struktur_20261118b`):

| Kennzahl | Wert |
| --- | --- |
| Goldfelder in A-E | **97** |
| nicht widerlegt | **71 von 97** (45 Wert und Arm, 4 Arm vertauscht, 22 anderer Wert) |
| Tabellen komplett | 60/60 |
| Strukturfehler | 0 |
| Warnungen A / B / C / D / E | 144 / 115 / 244 / 330 / 260 |

Die Warnungen A 144 = 137 + 7 Armkontext-Befunde. Nach der Haertung erneut
erzeugt: identische Zahlen, `structure.json` unterscheidet sich nur im
Zeitstempel `created`.

## 11. Sprint 48: Validierungs-Finding Kopf-Kontext

`validate_arm_context(table, context)` in
`research_agent/table_decomposition/validation.py`, aufgerufen nach
`validate(...)`. Es haengt nichts um und schreibt kein Gold.

| Code | Bedingung | Severity |
| --- | --- | --- |
| `kopf_n_widerspricht_kontext` | Kontextarm im Kopf auffindbar, traegt dort aber kein n | warning |
| `kontextarm_nicht_im_kopf` | Kontextarm im Kopf nicht auffindbar, waehrend eine andere Gruppe ein n druckt | warning (info bei Beschreibungen ueber zwei Woerter) |

Ergebnis: **15 Befunde in 10 Record-Paaren**, davon 7 Warnungen (u. a. `30`,
`78`/`79`, `335`/`336`, `678`/`682`) und 8 Hinweise. `placebo` ist bewusst kein
Rollenwort, damit ein Tippfehler wie `Placbeo` sichtbar bleibt.

Vereinfachung nach frischem Blick: `_baender_mit_n` sammelt nur Gruppenbaender
(Raster-, Perioden-, Mittelwert- und Total-Labels sind Stopwoerter) und nennt bis
zu drei mit Wert; `_n_hinweis` ersetzt die dreifach wiederholte Bandschleife;
die Fallunterscheidung "Band ohne n" gegen "Band fehlt" ist wiederhergestellt.

## 12. Push-Befund und Seitenzweig

Der Push der beiden Commits wurde mit "non-fast-forward" abgelehnt. Befund:
`origin/master` (`83fbfe1`) ist ein **elternloser Wurzel-Commit** (9 Dateien:
Architektur, Lizenz, README, Pre-Push-Hook, Sperrbegriff-Scan, drei
Benchmark-Dateien); `git merge-base HEAD origin/master` endet mit Exit 1.

Ein Rebase haette alle 713 Commits neu abgespielt (History-Rewrite, gegen die
Projektregel) und drei lokale Pfade konflikthaft aufgeloest; ein Cherry-Pick der
zwei Commits ergaebe auf dem Snapshot keinen lauffaehigen Stand. Deshalb:

- Seitenzweig `sprint48` angelegt und nachgezogen, Stand `ec60b85`.
- `origin/master` unveraendert `83fbfe1`.
- Pre-Push-Hook: "Keine offenen Sperrbegriffe gefunden".
- Kein Force-Push, kein History-Rewrite.

## 13. Pruefungen des Tages

| Pruefung | Ergebnis |
| --- | --- |
| `pytest test_table_decomposition.py test_validation_arm_context.py` | **52 passed** |
| `pytest test_run_extended_extraction.py test_crash_recovery.py test_nachzug_p5.py test_wiederaufnahme.py test_dedupe_predictions.py test_jobs.py test_fehlerklassen.py` | **94 passed** |
| `nachzug_p5.py --pruefen` vor dem Start | 38 von 60 ausgewaehlt, Sperrlage frei, nichts geschrieben |
| `werte_p5_mit_kontrolle.sh` | Positivkontrolle gruen, Exit 0 |
| `pruefe_armbindung_sprint48.py` | Summe 97 = Sollwert 97, Abbruch bei Abweichung |
| `structure.json`-Diff nach der Haertung | nur `created` |
| `run_extended_extraction.py --dry-run` mit zwei IDs | Auswahl korrekt, kein Verzeichnis, keine Anfrage |

Die vollstaendige Suite aus der Wurzel wurde heute **nicht** erneut gefahren;
die Zahlen oben sind die der genannten Dateien.

## 14. Offene Punkte

1. **36 Budgetfaelle** (33 x `length_ohne_ergebnis`, 3 x ohne Zellen) sind
   unentschieden: hoeheres Budget oder im Bericht als Ausfall ausweisen.
2. **Offizielle Bewertung** (Recall, MAE) bleibt der geschuetzte Bewertungslauf;
   die Zellzaehlung ist Selbstpruefung.
3. **`_ARM_ALIASEN` liegt in der Engine.** Sauberer waere eine kuratierte Tabelle
   im Benchmark-Layer, ueber `context["arm_aliasse"]` an `bind_arm` gereicht;
   danach ein Offline-Lauf (Erwartung 97/71 unveraendert).
4. **`record_id` erreicht `bind_row_arm`, `consider_arm_candidate` und
   `transfer_arms_within_document` nicht** - derzeit unschaedlich, aber eine
   stille Luecke.
5. **Vier armlose Baender** (`band_ohne_arm = 4`) koennten die Obergrenze 71
   verschieben, aber nur mit Beleg.
6. **`origin/master`** bleibt der oeffentliche Snapshot; ein Master-Push ist ohne
   Merge unverwandter Historien oder History-Rewrite nicht moeglich.
7. **`public_benchmark/tests/test_p5_kontrolle_gate.py`** wurde heute vom echten
   P5-Lauf entkoppelt (`ac1946d`).

## 15. Artefakte

| Artefakt | Inhalt |
| --- | --- |
| `docs/internal/p5_wiederanlauf_20261119.md` | Betriebspruefung, Abbruch, Vortest, Neustart |
| `docs/internal/wiederaufnahme_harness_20261119.md` | Wiederaufnahme im Harness, Nachzug, Neuberechnung |
| `iterativ/ergebnisse/p5_nachzug_zusammenfassung_20261119.md` | Nachzug, Aufraeumen, Neubewertung |
| `iterativ/ergebnisse/p5_auswertung_20261118.{json,md}` | neu gerechnete Auswertung (67 verwertbar) |
| `runs/p5_auswertung_stand1314/` | Momentaufnahme vor dem Nachzug (43, absichtlich unveraendert) |
| `iterativ/ergebnisse/sprint48_budgetdiagnose.{json,md}` | Diagnose der 33 Budgetabbrueche |
| `iterativ/ergebnisse/sprint48_kopfangaben_20261119.{json,md}` | Kopfangaben je Goldzelle, Herkunft der 46 |
| `iterativ/ergebnisse/sprint48_goldquellen_20261119.{json,md}` | die neun Goldwerte ohne Fundstelle |
| `iterativ/ergebnisse/sprint48_nachzug_entscheidung_20261119.md` | Entscheidung der fuenf Planfaelle |
| `iterativ/ergebnisse/sprint48_planwerte_20261119.md` | Planwerte alt/neu, Auswahl-SHA256 |
| `iterativ/ergebnisse/sprint48_armbindung_20261119.{json,md}` | Arm-/Wertpruefung, 71 von 97 |
| `iterativ/ergebnisse/sprint48_planzellen_ursachen_20261119.md` | Ursachen der 26 Zellen, Spaltenbelege |
| `iterativ/ergebnisse/sprint48_armkonflikt_20261119.md` | Validierungs-Finding Kopf-Kontext |
| `iterativ/ergebnisse/sprint48_alias_20261119.md` | Alias-Messung 94 -> 97, Umsetzung, Haertung |
| `iterativ/ergebnisse/sprint48_push_befund_20261119.md` | Remote-Befund und drei Push-Optionen |
| `analysis/table_decomposition_20261118/offline_struktur_20261119/structure.json` | Planwerte des Laufs `offline_struktur_20261119` |
| `analysis/table_decomposition_20261118/offline_struktur_20261118b/structure.json` | aktueller Stand 97/71 |
| `yun_full/zaehle_kopfangaben_sprint48.py`, `pruefe_goldquellen_sprint48.py`, `pruefe_armbindung_sprint48.py`, `diagnose_sprint48.py` | Pruefskripte des Tages |
| `yun_full/nachzug_p5.py`, `yun_full/wiederaufnahme.py`, `yun_full/pruefe_glm_kapazitaet.py` | Nachzug, Wiederaufnahme, Kapazitaets-Vortest |

## 16. Grenzen

- `adressiert`, `wertgleich` und die Rettungsquote sind die Selbstpruefung aus
  `werte_p5_aus.py`, nicht die offizielle Bewertung.
- `gold_reachable` ist eine Obergrenze des Tabellenpfads, keine Modellleistung.
- Die Zeichen/Token-Umrechnung der Reasoning-Angaben ist eine Schaetzung
  (Median 4,0 aus 390 abgeschnittenen Zeilen); Reasoning-Tokens stehen nicht in
  den Predictions.
- Strukturmerkmale stammen aus dem vorhandenen Parser; wo er keine Tabelle
  erkennt, steht 0 - fuer sechs Records am Markdown geprueft.
- Zusammenhaenge in der Budgetdiagnose sind beobachtet, nicht kausal belegt.
- Der Erwartungswert fuer den Nachzug ist aus dem Mittel der 33 Vorlaufzeilen
  abgeleitet und als Schaetzung markiert.
