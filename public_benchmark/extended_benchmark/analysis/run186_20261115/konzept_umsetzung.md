# Umsetzung des Konzepts „drei Probleme" (15.11.2026)

Bewertung des eingereichten Konzepts, Umsetzungsstand und Abweichungen. Alles
hier ist ohne API-Aufrufe entstanden; die kostenpflichtigen Phasen 2 und 3 des
Konzepts sind **nicht** gestartet.

## 1. Bewertung: was trägt, was ist überholt

**Trägt ohne Einschränkung**

* Die gemeinsame Ursache (Feld-für-Feld-Entscheidung im v6-Prompt) ist richtig
  beschrieben; sie erzeugt die Armmischung und die zielabhängigen Labels.
* Die Belegstufen lösen den Zirkel der Ziel-Normalisierung, ohne die alten
  Klassen zu verändern.
* Das Rückfallintervall statt einer Einzelzahl ist bei 24 unbelegten Labels
  (4,8 %) der richtige Umgang.
* `timepoint_header` plus `fallback` je Antwort ist strukturell besser als jede
  Prompt-Regel: eine Mischung ist danach nicht mehr darstellbar.
* Die Trennung „Modellmischung vs. Goldmischung“ war der wichtigste Punkt — sie
  hat fünf neue Gold-Fälle sichtbar gemacht (Abschnitt 4).

**Überholt, weil der Lauf inzwischen fertig ist**

* Der Snapshot-Reader ist unnötig: 186 Zeilen liegen abgeschlossen vor, jede
  Auswertung liest read-only.
* „Restrecords 139“ und die Kostentabelle für den v6-Rest entfallen. Gemessen
  sind es 9.210 Tokens je Record über alle 186 und 7.726 im 16.000er-Abschnitt.
* „7 von 28 Records“ ist jetzt 7 von 186 (3,8 %, Wilson 1,8–7,6 %).

**Korrigiert**

* Die Limitregel `max(10.000, 1,25 × p95)` ergibt aus den gemessenen gültigen
  Zeilen **19.000**, nicht 16.000. Der p95 liegt bei 14.730. Da nur 3 von 139
  gültigen Antworten innerhalb von 5 % am höchsten Limit lagen, hat 16.000
  trotzdem nichts Brauchbares abgeschnitten — die Regel ist trotzdem die
  saubere Grundlage für v7.
* `gleiche_zeile()` erkennt `yun2024:75` **nicht**: dessen Goldzahlen stehen in
  verschiedenen Tabellenzeilen (Zeile 0 und Zeile 24 derselben Spalte). Die
  Triage braucht deshalb eine zweite Quelle; umgesetzt ist die Klasse
  `arm_gemischt_gold_bestaetigt`, die `GEPRUEFTE_FAELLE` liest.
* Stufe B (Artikelbeleg) greift nur bei **12 Zellen**, weil 479 von 503 Zellen
  die Einheit bereits drucken („Week 24“, „12 months“). Die 12 Zellen stammen
  alle aus PMC3546023 und werden korrekt zu `week 24`; die Stichprobe ist für
  eine Precision-Aussage zu klein, deshalb steht sie als Belegstufe und nicht
  als Korrektur der Klassen.

## 2. Umgesetzt (Phase 0)

| Baustein | Datei | Ergebnis |
|---|---|---|
| Length-Diagnose ohne Tokens | `laenge_diagnose.py` | p95 14.730, Ausfälle nach Zieltyp (month 48,1 % gegen baseline 18,3 %, Fisher p = 0,0069), Textlänge ohne Signal (p = 0,87), Ausfälle kosten 46,2 % aller Tokens |
| Belegstufen | `evaluate_fallback.py` | `gedruckt` 479, `artikel` 12, `unklar` 12; Treffer belegt 340, nur aus Ziel 0 |
| Rückfallintervall | `evaluate_fallback.py` | 27,6 % bis 30,0 % (139 Rückfälle, 12 unklare Zellen); die Einzelzahl 27,6 % wäre nach unten verzerrt |
| Armtrennung | `evaluate_fallback.py` | `arm_konsistent` 179, `gemischt_modell` 5, `gold_bestaetigt` 1, `gold_kandidat` 1; Zellanteil 18 von 38 (47,4 %, Wilson 32–63 %) |
| Gold-Kandidaten | `gold_konflikt_kandidaten.md` | fünf Records aus PMC3546023 mit Textbeleg, zwei legitime Baseline-Rückfälle aus PMC4996097 |
| `yun2024:75` | `analyze_errors.py` | bereits als Klasse 5 eingetragen, vier Zellen mit Quelle |

Die alten Klassen (`zieltreu` 352, `rueckfall` 139, `unklar` 12) und alle
Metriken (F1 0,6548, MAE 0,3796 bei Coverage 0,6731) sind **unverändert** —
nachgerechnet nach dem Umbau.

## 3. Umgesetzt (Phase 1): v7-Schema

* `VERSION_CELL_TIMEPOINT = "v7_zellzeitpunkt"`; `bestimme_version()` liefert es
  nur mit Zielzeitpunkt, v6-Zeilen behalten `v6_target_fallback` (Test).
* `--cell-timepoint` schaltet `_prompt_v7()`: „Return the JSON object first“,
  ein Zeitpunkt für beide Arme, drei Fallback-Stufen, `timepoint_header`
  wörtlich aus dem Artikel, `fallback` als Kennzeichen.
* `parse_v7_meta()` liest die drei Felder; der Runner verteilt den Zeitpunkt auf
  die Zellen, damit die Auswertung **beide Schemata ohne Adapter** liest.
* Neue Protokollfelder je Zeile: `schema_version`, `timepoint_header`,
  `fallback`, `content_chars`, `gateway_params`.
* `pruefe_v7_zeile()` prüft formal: Header wörtlich im Artikel, `fallback`
  gesetzt und stimmig (`false` ⇒ Zielzeitpunkt, `true` ⇒ anderer Zeitpunkt),
  genau ein Zeitpunkt je Antwort.
* Tests: 221 grün (vorher 213), darunter Version, Prompt-Inhalt, Parsen einer
  v7-Antwort mit gefälschtem API-Aufruf und die drei formalen Prüfungen.

## 4. Neuer Befund aus der Armtriage

Alle fünf Records aus PMC3546023 (`75`, `76`, `78`, `80`, `81`) haben Gold, das
**zwei Zeitpunkte derselben Gruppe** als zwei Arme etikettiert — nachweisbar an
der Gruppengröße im Komparator (n = 29 bzw. 30, also derselbe Arm):

| Record | Gold intervention | Gold comparator | beide n |
|---|---|---|---|
| `:75` | 11.97 (Zeile 0) | 13.72 (Zeile 24) | 29 |
| `:76` | 14.06 (Zeile 0) | 14.40 (Zeile 24) | 30 |
| `:78` | 14.11 (Zeile 24) | 11.39 (Zeile 0) | 30 |
| `:80` | 14.56 (Zeile 24) | 11.75 (Zeile 0) | 29 |
| `:81` | 675.16 (Zeile 24) | 63.60 (Zeile 0) | 29 |

Das ist keine Modellschwäche, sondern ein Extraktionsfehler im Gold. Eingetragen
ist bisher nur `:75` (auf Anweisung); die vier anderen sind Kandidaten mit
Textbeleg in `gold_konflikt_kandidaten.md`.

## 5. Nicht umgesetzt (braucht Freigabe oder ist offen)

| Punkt | Grund |
|---|---|
| Pilot A/B (6 Fehl-Records, ≤ 192.000 Tokens) | Netzläufe brauchen ausdrückliche Freigabe |
| Vollauf v7 auf 186 Records (≈ 1,2–1,7 Mio) | dito, und erst nach dem Pilot |
| Zweite Kohorte (76 Records) | vom Nutzer ausgeschlossen |
| Reasoning-Parameter am Gateway | Der Client sendet nur `max_tokens` und `temperature`; ob das Gateway ein Reasoning-Budget kennt, ist im Repo nicht belegt |
| Positionszuordnung (Option 3 bei Labels) | wie im Konzept verworfen |
| Vier weitere Gold-Konflikte eintragen | Benchmark-Entscheidung, nicht ohne Prüfauftrag |

## 6. Empfehlung

**Pilot nach Abschnitt 4.4 des Konzepts starten, sobald freigegeben: 6 bereits
gescheiterte Records, Variante A (v6 + Reasoning-Parameter, falls das Gateway
ihn kennt) und Variante B (`--cell-timepoint`, Limit 19.000).** Begründung: Die
Diagnose zeigt, dass die Ausfälle an Zieltyp und nicht an Textlänge hängen
(month 48 % gegen baseline 18 %), und dass 46 % aller Tokens in Zeilen ohne
Ergebnis fließen. Ein Pilot über 6 Records kostet höchstens 192.000 Tokens und
entscheidet, ob Prompt oder Gateway-Parameter der Hebel ist — bevor 1,5 Mio
Tokens in einen Vollauf gehen.
