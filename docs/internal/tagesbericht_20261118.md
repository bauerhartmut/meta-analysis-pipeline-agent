# Tagesbericht 18.11.2026

Zusammenfassung aller Berichte dieses Tages. Zahlen sind aus den jeweils
genannten Artefakten, Commits oder Messungen gelesen; Schätzungen sind als
solche markiert. Es wurde heute **kein** P5-Lauf gestartet.

## 0. Kennzahlen des Tages

| Kennzahl | Wert |
| --- | --- |
| Commits | 101 (erster 10:42 `57db9b1`, letzter 23:19 `5f36b37`) |
| Tests aus der Wurzel | **1964 passed, 2 skipped**, Exit 0, 7:22 min (23:18) |
| `public_benchmark/tests` | 405 passed (Stand nach `c59d1c5`) |
| Engine-Tests (`table_decomposition`) | 52 passed (0,27 s) |
| P5 | **nicht gestartet**, Run-Verzeichnis fehlt |
| P5-Wache | **tot** (Gate PID 6630, kein Prozess, letzter Logeintrag 18:30:54) |
| Vorhersagen yun699 | 2.097 Zeilen (699 × 3 Modelle), 1.990 ok, 107 failed |

## 1. Was heute geschafft wurde

1. **Neue Tabellenzerlegungs-Engine** für den Yun-Benchmark gebaut, mit fünf
   Strategien (A–E), eingefrorener Auswahl, Strukturvalidierung und
   Reproduktionspfad.
2. **Reichweite des Tabellenpfads von 28,4 % auf 34,2 %** gehoben (76 → 95 von
   278 Goldzellen; mit Reihenfolge-Annahme 99 = 35,6 %) — durch dokumentweiten
   Arm-Transfer, Verbundwerte und Auswahl nach Feldabdeckung.
3. **Erwartete Zellen korrigiert und messbar gemacht:** wertgleich 58 → 62 → 68
   → 83, streng 49 → 46, streng_gewählt 55; erreichbar 94 → 101. Dazu
   Kopf-Fakten, Outcome-Zeilen-Fokus, Caption-Leser, Fließtext-Fundstellen.
4. **Kopfband-Guard abgesichert:** erreichbare Goldfelder 46 → **56**,
   strukturell komplett 57/60 → **60/60**, Strukturfehler 7 → **0**.
5. **Nachzug der GLM-Ausfälle** gebaut, offline geprüft, gestartet und
   **abgeschlossen** (140 Aufträge, Ende 22:16).
6. **P5-Auswertung fertig und geprüft:** Zellbilanz mit Precision/Recall/F1,
   Positivkontrolle, Nonce-Gate, Zellprotokoll, 68 Tests in vier Dateien.
7. **Startwache gehärtet** (prozessbasierte Sperre, verwaiste Sperre, `--pruefen`)
   und **`pytest` aus der Wurzel repariert**: 107 Sammelfehler → 1931, am Abend
   1964 grüne Tests.
8. **Tokenzähler** für TUDaGPT eingebaut (Ledger + `llm_usage`, 9 Tests).

## 2. Verlauf

| Zeit | Etappe | Beleg |
| --- | --- | --- |
| 10:42–12:00 | Engine, Auswahl, Strukturvergleich, Reichweiten-Hebel | `57db9b1`, `2d52ef5`, `ac3b4c9`, `ergebnisbericht_20261118.md` |
| 12:00–13:50 | qwen30-Vergleich, Reparaturschätzung, Rohantwort im Harness, GLM-Nachzug, Auswahlregel, Bisect, Budget-Hypothese | `7bbf06`, `586dd18`, `9ba30aa`, `38fbeea`, `8d01cb3` |
| 13:50–16:30 | Startwache, Tokenzähler, P5-Auswertung auf 103 IDs, Positivkontrolle, Provenienz | `84eaf7d`, `4a0e0d4`, `6822174`, `288b5eb`, `9e6d87f` |
| 16:30–18:30 | Wachenneustart, P5-Audit, Caption/Gruppenköpfe, P/R/F1, `pytest.ini`, Zellbilanz | `d47d6f7`, `7285065`, `68bccc5`, `2be9800`, `c59d1c5` |
| 18:30–22:17 | Rechner offline; Wache stirbt, Nachzug läuft nach Neustart zu Ende | `konsole_nachzug.log`, `predictions.jsonl` 22:17 |
| 22:17–23:20 | Statusaufnahme, Tagesbericht | `5f36b37`, `docs/internal/status_20261118.md` |

## 3. Harness-Verbesserung in den Benchmarks (gemessen)

### 3.1 Reichweite des Tabellenpfads

| Stand | erreichbare Goldzellen | Anteil |
| --- | --- | --- |
| Ausgangspunkt | 76 von 268 | 28,4 % |
| nach drei Mechanismen (`ac3b4c9`) | **95 von 278** | **34,2 %** |
| mit Reihenfolge-Annahme | 99 von 278 | 35,6 % |

Mechanismen: dokumentweiter Arm-Transfer (+18 Spalten in 215 Tabellen,
markiert `arm_basis="uebertrag"`), Verbundwerte `12.4 (3.1)` als zwei Belege
(`secondary_role`), Auswahl nach Feldabdeckung statt Tabellenzahl
(Kandidaten 537 → 608).

Die 183 nicht erreichbaren Zellen sind klassifiziert: 100 `feld_fehlt_im_dokument`,
40 `arm_nicht_gebunden_ohne_namensrest`, 42 `spalte_nicht_ausgewaehlt`, 1 Ambiguität.
Damit ist der Deckel des Tabellenpfads bekannt: **rund 34 %** sind überhaupt
holbar, unabhängig vom Modell.

### 3.2 Struktur und Aufwand A–E (Test, 59 Records, 60 Tabellen)

| Var | Verfahren | Tokens ges. (Schätzung) | Faktor zu A | Gold erreichbar | komplett | Fehler |
| --- | --- | --- | --- | --- | --- | --- |
| A | Full-Table | 84.733 | 1,00 | 95 | 60/60 | 0 |
| B | Vertical | 157.828 | 1,86 | 95 | 60/60 | 0 |
| C | Horizontal | 332.307 | 3,92 | 95 | 60/60 | 0 |
| D | Bidirectional | 440.677 | 5,20 | 95 | 60/60 | 0 |
| E | Adaptive | 295.279 | 3,49 | 95 | 60/60 | 0 |

Strukturerhalt ist belegt (jede Datenzelle genau einer Einheit, Header-Pfad,
Zeilenlabel und Fußnoten mitgeführt). **Präzision, Recall, F1, Kosten je
richtiger Zelle sind für diesen Aufbau nicht gemessen** — dafür braucht es
einen Modelllauf.

### 3.3 Kopfband-Guard: Regression gefunden und behoben

Der Guard aus Sprint 38 (`_reassign_header_bands_by_order`) war ein Nettoverlust:

| Kennzahl | vorher | nachher (Sprint 43) |
| --- | --- | --- |
| erreichbare Goldfelder | 46 | **56** |
| strukturell komplett | 57/60 | **60/60** |
| Strukturfehler | 7 | **0** |
| Warnungen | 136 | 137 |

Der Gewinn `PMC4319071:T2` (158.67 / 167.61 exakt) bleibt. Entscheidung steht je
Tabelle in `Table.band_decision`; kein Feld geht verloren.

### 3.4 Erwartete Zellen: von 58 auf 83 wertgleich

Der Pilotlauf `modell_glm53_abe_20261118` lieferte in 5 Zeilen **0 richtige
Zellen** — nicht wegen des Modells, sondern weil die erwarteten Zellen falsch
adressiert waren (verschobene Kopfzeilen, `n=434` als Spaltenrolle, keine
Outcome-Zeile). Der Lauf wurde nach 5 von 177 Zeilen gestoppt; das sparte
geschätzt 1,4 Mio. Tokens und rund sechs Stunden.

Danach in dieser Reihenfolge gemessen:

| Schritt | erreichbar | wertgleich | streng | streng_gewählt |
| --- | --- | --- | --- | --- |
| Provenienz / Kursiv-n | 94 | 58 | 49 | — |
| Populationswahl (Caption, Gruppenkopf) | 94 | 62 | — | — |
| Gruppenköpfe + Zielwahl | 94 | **68** | — | — |
| Fließtext als Fundstelle | **101** | **83** | 46 | **55** |

Wichtige Einschränkung: der Sprung 68 → 83 ist **kein reiner Gewinn**. Er
gewann 15 Felder (5 eindeutig), nahm aber 8 Feldern die Eindeutigkeit
(`streng` 49 → 46). Der belastbare Wert für ein eindeutiges Ziel ist
`streng_gewählt = 55`, davon 9 Felder über Dosis-plus-`n = X` aufgelöst.

Weitere Korrekturen des Tages: Kopfzeilen mit `vs` sind Zeilenlabels, keine
Spaltenköpfe; Gruppengrößen aus dem Kopf sind Kopf-Fakten ohne Spaltenrolle;
erwartet werden nur Zellen der Outcome-Zeile (`reachable_cells`); Dosis im
selben Satz schneidet die richtige Zahl aus mehreren gedruckten.

### 3.5 Aufblähung der Trefferzählung

An den 559 Erfolgszeilen: 2.121 großzügig adressierte Zellen, 2.103 mit
eindeutigem Zeitpunkt → **18 Zellen Aufblähung (0,8 %)**, 4 betroffene Zeilen;
wertgleich 1.844 großzügig → 1.826 streng. Das ist eine **Untergrenze**, weil
keine Goldzelle einen Zeitpunkt trägt.

### 3.6 Modell- und Zuverlässigkeitsebene

| Kennzahl | glm | qwen30 |
| --- | --- | --- |
| richtig / falsch / fehlend | 1.840 / 281 / 652 | 1.026 / 348 / 1.399 |
| Precision / Recall / F1 | 0,8675 / 0,6635 / **0,7519** | 0,7467 / 0,3700 / **0,4948** |
| Tokens | 1.934.079 | 75.671 |
| Tokens je richtiger Zelle | 1.051,1 | 73,8 (**14,3× billiger**) |
| technische Ausfälle | 104 | 0 |

- 427 der 652 fehlenden Goldzellen (65,5 %) sind **technische Ausfälle**, nicht
  Extraktionsfehler.
- qwen30 schweigt bei Gruppengrößen: 1.066 seiner 1.399 Fehlstellen (76 %) sind
  `n` je Arm; Melderate 18,5 % gegen 77,3 % bei identischem Prompt.
- Zuverlässigkeit glm (`_lesekopie`): 595 completed / 104 failed = 85,12 %,
  Latenz Mittel 20,93 s, Median 8,41 s, p90 45,64 s.
- Erster Live-Lauf unter `--retry-strategie neu`: 10/10 completed, je genau ein
  HTTP-Versuch, Mittel 4,45 s, 7.218 Completion-Tokens. **Kein Fehlerfall
  live durchlaufen** (kein 429/Timeout/5xx).
- Budget-Hypothese (Stand ~12:50): bei 8.000 → 19.000 wurden 23 Ausfälle
  gerettet; alle 21 beobachteten 24.000er-Zeilen waren abgeschnitten, deshalb
  Retry bis 32.000.

### 3.7 Rohantwort im Harness

Seit `586dd18` schreibt der Harness die Modellantwort mit (`content`,
`content_primaer`, `content_retry`), gemessener Platzbedarf 391 Byte je Zeile,
rund 0,8 MiB für einen vollen Drei-Modell-Lauf. Damit sind künftige
Parserverluste messbar statt schätzbar.

## 4. P5: vorbereitet, geprüft — nicht gestartet

- Auswertung auf die 103 IDs umgebaut, Klasse je Record nachgeschlagen,
  Nullprobe: 103 adressiert, 102 bewertbar, 0 gerettet, 423 Goldzellen.
- Precision/Recall/F1 eingebaut; Pilot auf 559 Zeilen: TP 1.844, FP 410
  (295 überzählig, 115 fremd), FN 462 → 0,818 / 0,800 / 0,809.
- Positivkontrolle mit 8 Fixture-Records, Soll = Ist in allen Kennzahlen;
  sie erzwang einen echten Fix (`zellen_neu_mit_zeitpunkt` zählte über eine
  andere Grundgesamtheit).
- Wache-Gate: Auswertung nur mit frischer Marke und passendem Nonce
  (`werte_p5_mit_kontrolle.sh`), sonst Exit 3/4.
- Zellbilanz + Zellprotokoll (`bilanzzellen`, `_summen`) mit 20 adversarialen
  Tests; `quote()` liefert `None` statt 0.
- **Der Lauf selbst fehlt.** Die Wache startete 16:55 (PID 6630, Frist 04:55),
  starb im Offline-Fenster ab 18:31 und prüft seither nicht mehr.

## 5. Betrieb und Läufe

| Lauf | Ergebnis |
| --- | --- |
| Nachtlauf `yun699_8000_alle_20261117` | abgeschlossen, 2.097 Zeilen = 699 × 3, keine Dubletten |
| GLM-Nachzug | 140 Aufträge, fertig 22:16; glm failed 21, qwen failed 86, qwen30 0 |
| P5 `yun699_p5_24000_20261118` | existiert nicht |
| Release-Prüfung | `baue_release.py --pruefen`: 0 Treffer, 11 Dateien, Historie übersprungen |

## 6. Qualitätssicherung

- `pytest.ini` mit `norecursedirs` (Fremdkopien, `raw_data`, venvs) beendet 107
  Sammelfehler; Wurzel-Lauf 1931 → am Abend **1964 passed, 2 skipped**.
- Testwachstum in `public_benchmark/tests` im Tagesverlauf: 52 (Engine) → 347 →
  356 → 373 → 382 → 405.
- P5-Block: 68 Testfunktionen (28 / 12 / 8 / 20).
- Gegenproben: Tabellenwahl auf 26 unbenutzten Tabellen (2 Wechsel, 0 Verluste),
  dev-Split unverändert, Testsplit-Hashes vor/nach gleich.

## 7. Was heute nicht erreicht wurde

1. **Keine echten P5-Zahlen** — keine Rettungsquote, keine Golddeckung, kein
   alt/neu-Vergleich.
2. **Keine P/R/F1 für die neue Engine** — der Modelllauf wurde bewusst
   abgebrochen; die Reichweite (34 %) ist eine Obergrenze, kein Gütewert.
3. **Kein Push.** `origin/master` ist inzwischen vor unserem Stand; ohne
   `git pull` (nicht ohne Freigabe) geht nichts hinüber.
4. **Live-Fehlerpfad ungetestet** — der Retry-Lauf traf keinen einzigen Fehler.

## 8. Offene Punkte

- Wache neu starten, sonst startet P5 nicht (Frist war 04:55).
- Nach dem P5-Lauf: Stichprobe nach dem Prüfplan ziehen, Bilanz je Record
  nachrechnen, `population_mismatch`/`timepoint_mismatch` getrennt ausweisen.
- Prüfplan-Ergänzung („Ziehungseinheit", Leerkonvention) im Sprint-48-Bericht
  ist geschrieben, aber **nicht committet**.
- Rollen aus Zeilenlabels (`Mean (SD)`) fehlen weiter; ohne sie tragen Tabellen
  wie `PMC4319071:T1` keine Mittelwerte bei.
- Tokenzähler erfasst den abgeschlossenen Nachtlauf nicht (Prozess hatte den
  Harness vor dem Einbau geladen).

## 9. Empfehlung

**Heute Nacht: Wache neu starten und P5 laufen lassen.** Das ist der einzige
Schritt, dessen Ergebnis heute vorbereitet, geprüft und dennoch nicht
eingeholt wurde — und der einzige mit Zeitfenster. Danach in dieser
Reihenfolge: P5-Auswertung lesen (zuerst die FP-Zeile „Schlüssel im Gold, aber
Dublette oder falscher Wert"), Prüfplan-Ergänzung committen, dann den
Engine-Modelllauf A/B/E freigeben — aber erst, wenn `streng_gewählt` als
Zielgröße festgeschrieben ist, sonst wird gegen eine bewegliche Erwartung
gemessen.
