# Zuverlässigkeit der Extraktionspipeline: Analyse und Plan

Stand: 2026-11-18. Datenbasis: Lesekopie des Laufs `yun699_8000_alle_20261117`
(SHA-256 `8f6d622f…ab2a`, 1.582 Zeilen zum Kopierzeitpunkt), die Konsolenprotokolle
des Laufs und der Code von `public_benchmark/extended_benchmark/`.

Während dieser Analyse liefen der Nachtlauf (PID 3952) und die wartende
Nachzug-Steuerung (PID 2153) unverändert weiter; es wurde nichts gestartet,
abgebrochen oder in laufende Dateien geschrieben.

## 1. Die Kette im Überblick

| Schritt | Ort | Verhalten heute |
|---|---|---|
| Auswahl | `load_records`, `waehle_records`, `done_keys` | liest Records, überspringt `(record_id, model)`-Paare, die schon eine Zeile haben |
| Prompt | `_kopf`, `_prompt_v7`, `_prompt_v8`, `_prompt_repair` | Textauszug 16.000 Zeichen, JSON-zuerst |
| HTTP | `_call_once` | `urllib`, **ein** Timeout von 300 s, kein Retry-After, keine Trennung von Verbindungs- und Lese-Timeout |
| Retry im Aufruf | `call` | nur bei 429/500/502/503/504, vier Versuche, `20*versuch + Zufall(0,5)` s |
| JSON-Retry | `work` | nur bei `json_kaputt`, gleicher Prompt, gleiches Budget |
| Reparatur | `work` + `_prompt_repair` | nur bei `length_ohne_ergebnis` und `--repair`, 6.000 Tokens, Text 15.000 Zeichen |
| Klassifikation | `fehlerklasse_aus` | `length_ohne_ergebnis` vor `json_kaputt`, sonst leer |
| Persistenz | `work` → `predictions.jsonl` | eine Zeile je Paar, `open(..., "a")`, ohne `flush`/`fsync`-Garantie |
| Fortsetzen | `done_keys` | Datei-Scan; Fehlzeilen gelten als erledigt, mit `--retry-failed` nicht |
| Doppelstart-Schutz | nur `nachzug_ausfaelle.sh` | `nachzug.lock` mit 90-Minuten-Altersregel; der Harness selbst hat keine Sperre |
| Dedupe | `dedupe_predictions.py` | nachträglich, nicht beim Schreiben |

Bereits vorhanden und wiederverwendbar: `research_agent/llm/engine.py` hat
`_compute_delay` mit Exponential Backoff und Retry-After, ist aber `async`, an
`aiohttp` und die Research-Agent-Konfiguration gebunden. Der Benchmark nutzt es
nicht (`public_benchmark/scripts/run_c1_dev_pilot.py` ist die einzige Ausnahme).
Eine Übernahme würde den Benchmark an eine zweite HTTP-Schicht koppeln; sinnvoller
ist ein kleiner, synchroner Manager mit derselben Semantik.

## 2. Was die 104 Ausfallzeilen wirklich sind

Alle 104 `glm`-Zeilen im Einzelnen ausgewertet:

| Merkmal | Wert |
|---|---|
| `fehlerklasse` | 103 × `length_ohne_ergebnis`, 1 × `json_kaputt` |
| `http_status` | 103 × 200, 1 × 0 |
| `finish_reason` | 103 × `length`, 1 × leer |
| `completion_tokens` | 103 × **8.000**, 1 × `None` |
| `content_chars` | 102 × 0, 2 × klein (143 und 272) |
| `reasoning_chars` | min. 24.033, **Median 32.448**, max. 36.800; alle 103 über 20.000 |
| `elapsed_s` | min. 27,7 / Median 42,0 / max. 300,03 |
| `gateway_params.max_tokens` | 8.000 bei **allen** 699 GLM-Zeilen |

**Der Hauptbefund ist kein API-Fehler.** Bei 103 Zeilen hat der Anbieter mit
HTTP 200 geantwortet, aber das Modell hat das gesamte Budget von 8.000 Tokens im
Reasoning verbraucht (`reasoning_chars` im Median 32.448 Zeichen) und danach
**keinen Inhalt** mehr geliefert (`content_chars` 0, `finish_reason` `length`).
Das ist eine Budgeterschöpfung im Reasoning, keine Störung der Übertragung.

Zum Vergleich: erfolgreiche GLM-Zeilen haben `reasoning_chars` im Median 4.657
und `content_chars` 387 bei 1.278 Completion-Tokens. Die Ausfälle liegen also
beim Siebenfachen an Reasoning — der Lauf hieß `yun699_8000_alle`, und die
8.000 Token waren für diese Records zu knapp.

Die eine Zeile mit echtem Transportfehler ist `yun2024:87`: `http_status 0`,
`TimeoutError: The read operation timed out` nach **300,03 s** — also genau das
`timeout=300` aus `_call_once`. Sie wurde als `json_kaputt` klassifiziert, weil
der Timeout eine leere Antwort hinterlässt und `parse_cells` daraus `kein_json`
macht. Der automatische JSON-Retry lief (`retried: true`), bekam aber ebenfalls
keine Antwort (`retry_tokens: None`).

Die **36 leeren Antworten** ohne Ausfallklasse sind etwas anderes:
`finish_reason` 36 × `stop`, `content_chars` im Median **13 Zeichen**, 922
Completion-Tokens, Reasoning 3.991 Zeichen. Das Modell hat also geantwortet, nur
eben mit fast nichts — das ist Extraktionsverhalten, kein technischer Fehler, und
gehört nicht in dieselbe Kennzahl.

Konsolenprotokoll als Gegenprobe: 43 × `429, warte …` (alle für `qwen30`), 128 ×
`FEHLER length_ohne_ergebnis` (über alle Modelle und Versuche), 3 ×
`json_kaputt`. Keine Timeout-Zeile im Log — Timeouts werden nur in der
Ergebniszeile sichtbar, nicht auf der Konsole.

## 3. Die sechs Fragen

**1. Welche konkreten Fehler sind aufgetreten?**
103 × Budget im Reasoning erschöpft (HTTP 200, `finish_reason=length`, Inhalt
leer), 1 × Lese-Timeout nach 300 s, 43 × HTTP 429 (nur `qwen30`, alle im
`call`-Retry abgefangen), 3 × `json_kaputt` über alle Modelle.

**2. Was davon geht auf den API-Anbieter?**
Nur die 43 × 429. Sie wurden vom vorhandenen Retry behandelt: `qwen30` hat 699
Zeilen ohne einen einzigen Ausfall, jede Wartezeile endete also in einer gültigen
Antwort. Die 300-Sekunden-Grenze ist unsere Vorgabe, nicht die des Anbieters.

**3. Was entsteht durch unseren Code?**
- **Budget:** 8.000 Tokens für ein Modell, das im Median 32.000 Zeichen Reasoning
  produziert, ist eine Konfigurationsentscheidung des Laufs, keine Laune des
  Modells. Der Harness kennt kein „Reasoning hat das Budget gefressen" und
  versucht deshalb keine Gegenmaßnahme.
- **Fehldiagnose:** Ein Timeout wird als `json_kaputt` einsortiert. Damit greift
  der JSON-Retry, der dieselbe 300-s-Grenze erneut abwartet, statt den Fehler als
  Transportproblem zu behandeln.
- **Blinder Wiederholungsversuch:** Der JSON-Retry schickt denselben Prompt mit
  demselben Budget. Bei einer abgeschnittenen Antwort ist das strukturiert
  aussichtslos.
- **Fehlende Versuchsspur:** Die Zeile kennt nur `retried` und `retry_tokens`; der
  erste Fehlertext wird vom zweiten überschrieben. Wie viele Versuche es gab und
  warum, steht nirgends.

**4. Wurde etwas erfolgreich verarbeitet, aber nicht gespeichert?**
Nein, dafür gibt es keinen Hinweis. `content_chars = 0` heißt: Der gespeicherte
Text war leer, es ging also nichts verloren. Für die Zeit vor Commit `586dd18`
fehlt allerdings das Feld `content`, sodass sich „leer geliefert" und „leer
gespeichert" nicht mehr unabhängig prüfen lassen — für diesen Lauf stützt sich
die Aussage auf `content_chars`, `finish_reason` und `completion_tokens`.

**5. Temporär oder dauerhaft?**
- 429: temporär, erfolgreich behandelt.
- Timeout: temporär, aber unbehandelt (kein Retry).
- Budget im Reasoning: **strukturell dauerhaft** bei 8.000 Tokens; ein zweiter
  Versuch mit demselben Budget scheitert reproduzierbar.
- `json_kaputt` (3 Fälle): ohne Rohantwort nicht entscheidbar.

**6. Was hätte ein weiterer Versuch verhindert?**
- Der Timeout (1 Zeile, 4 Goldzellen): ja, mit einem Retry und angepasstem
  Timeout.
- Die 103 Budget-Fälle: nur mit **mehr Budget** oder kürzerem Prompt, nicht durch
  Wiederholung. Ein Retry mit 24.000 Tokens ist ein anderer Aufruf, kein Retry im
  engeren Sinn — genau das macht der vorhandene Reparaturpfad mit 6.000 Tokens
  übrigens in die falsche Richtung (kleiner statt größer).

## 4. Mängel im Code, die daraus folgen

| Nr. | Stelle | Mangel | Wirkung |
|---|---|---|---|
| M1 | `fehlerklasse_aus` / `_call_once` | Transportfehler werden zu `json_kaputt` | falscher Retry-Pfad, irreführende Kennzahl |
| M2 | `_call_once` | ein Timeout für Verbindung und Lesen, fest 300 s | lange Hänger, keine Anpassung |
| M3 | `call` | Retry nur für 429/5xx; Timeout, `URLError`, `ConnectionReset` nicht | genau der Fehler aus `yun2024:87` bleibt liegen |
| M4 | `call` | `Retry-After` wird ignoriert, Wartezeit fest `20*versuch + Zufall` | 429-Lawinen bei kurzen Grenzen; unnötige Wartezeit bei langen |
| M5 | `call` | kein Versuchsprotokoll | nicht nachvollziehbar, welcher Versuch was lieferte |
| M6 | `work` | JSON-Retry mit identischem Budget; kein Fall „abgeschnitten" | wirkungslose Wiederholung |
| M7 | `work` → Datei | `with open(..., "a")` schließt und flusht, aber ohne `fsync` | ein Prozessabsturz verliert nichts, ein Stromausfall kann die letzte Zeile kosten |
| M8 | Harness | keine Sperre; zwei Prozesse schreiben in dieselbe Datei | genau die Duplikate aus dem Vorfall vom 17.11. |
| M9 | `done_keys` | „Zeile vorhanden" ≠ „Job erfolgreich" | Fortsetzen verwechselt Erfolg und Ausfall |
| M10 | Run-Zeile | kein `attempt_id`, kein `job_status`, kein `next_retry_at` | Crash-Recovery nur grob über den Datei-Scan |

## 5. Telemetrie, die künftig erfasst werden muss

Vorhanden: `http_status`, `error`, `finish_reason`, `completion_tokens`,
`reasoning_chars`, `elapsed_s`, `content_chars`, `parse_error`, `retried`,
`retry_tokens`, `repair_tokens`, `gateway_params`, `content`/`content_primaer`/
`content_retry`.

Fehlt: Modellversion (nur `model_id`), `attempt_id`, Zeitstempel je Versuch,
Versuchsdauer je Versuch, Timeout-Wert des Versuchs, Header der Antwort
(`Retry-After`, `x-request-id`), JSON-Validierungsstatus getrennt vom
Parse-Ergebnis, `job_status`, `next_retry_at`, Versuchsanzahl.

## 6. Implementierungsplan

Reihenfolge nach Nutzen pro Risiko. **Alle Harness-Änderungen laufen hinter
`--retry-strategie {alt,neu}` mit Default `alt`**, weil die wartende
Nachzug-Steuerung (PID 2153) den Harness erst beim Start lädt: Ohne diesen Riegel
würde der Reparaturlauf ungeprüften Code ausführen.

**P0 — Diagnose und Telemetrie (kein Verhaltensrisiko)**
1. `yun_full/fehlerklassen.py`: zentrale `klassifiziere()` mit den Klassen
   `ok`, `leer`, `timeout`, `verbindungsfehler`, `rate_limit`, `server_fehler`,
   `auth`, `anfrage_ungueltig`, `budget_im_reasoning`, `json_kaputt`,
   `json_abgeschnitten`; je Klasse `temporaer: bool`.
2. `fehlerklasse_aus` delegiert dorthin; neue Klasse `budget_im_reasoning`
   (Bedingung: `finish_reason=length` ∧ `content` leer ∧ `reasoning_chars>0`).
3. Zeile erweitert um `attempts: [{attempt_id, dauer_s, http_status, fehlerklasse,
   retry_grund, wartete_s, tokens, content_chars}]` und `job_status`.
4. Prüfung: die 104 Zeilen der Lesekopie durch die neue Klassifikation schicken;
   erwartet 103 × `budget_im_reasoning`, 1 × `timeout`.

**P1 — Retry-Manager (`yun_full/retry_manager.py`, synchron, ohne Netz testbar)**
1. `RetryPolicy(max_versuche=3, timeout_s=300, timeout_faktor=1.5,
   basis_s=2.0, faktor=2.0, max_delay_s=60, jitter=0.25)`.
2. `wartezeit(versuch, retry_after)` — Retry-After hat Vorrang, sonst Backoff mit
   Jitter, gedeckelt.
3. `fuehre_aus(aufruf, policy)` — ruft `aufruf(timeout)`, klassifiziert, wiederholt
   nur bei temporären Klassen, protokolliert jeden Versuch, gibt
   `(ergebnis, versuche)` zurück; permanent (auth, ungültige Anfrage) bricht ab.
4. `call()` nutzt den Manager bei `--retry-strategie neu`; `alt` bleibt
   byte-gleich zum heutigen Verhalten.

**P2 — Persistenz und Crash-Recovery (ohne neue Datenbank)**
1. `runs/<run>/jobs.jsonl` (append-only): je Paar `record_id`, `model`, `status`
   (`pending`/`running`/`retry_pending`/`completed`/`failed_permanent`),
   `attempt_count`, `last_error`, `created_at`, `updated_at`, `next_retry_at`,
   `result_reference`.
2. `done_keys` liest künftig Jobs **und** Predictions: `completed` zählt,
   `failed_permanent` zählt nicht, `pending`/`retry_pending` werden aufgenommen.
3. Schreiben mit `flush` + `os.fsync` je Zeile; Statuswechsel vor und nach dem
   Aufruf, sodass ein Absturz `running` hinterlässt und beim Start als
   `retry_pending` gilt (Unterscheidung „abgebrochen" vs. „läuft" über PID-Spalte).
4. `runs/<run>/harness.lock` mit PID; zweiter Prozess bricht mit Exit 3 ab.
   `nachzug_ausfaelle.sh` bleibt unverändert und behält seine eigene Sperre.

**P3 — Tests, offline und über den echten Pfad (`public_benchmark/tests/`)**
1. `test_retry_manager.py`: die 14 Szenarien aus dem Auftrag gegen `fuehre_aus`
   mit injizierten Aufrufen (Timeouts, 429 mit Retry-After, 500, 503 dauerhaft,
   Verbindungsabbruch, ungültiges JSON, abgeschnitten, auth, ungültige Anfrage,
   Erfolg im ersten Versuch, Erfolg im zweiten, Jitter-Grenzen, Obergrenze,
   Protokolllänge).
2. `test_harness_fehlerpfade.py`: `main()` mit gepatchtem `call`/`get_config`
   (wie in den Pfadtests der letzten Runde), echter Schreibpfad, geprüft werden:
   erfolgreiche Zeile, Retry-Erfolg, dauerhaft Fehler, kein Überschreiben einer
   erfolgreichen Zeile, Doppelstart bricht ab, Fortsetzen nach Abbruch führt zu
   genau einer Zeile je Paar.
3. Crash-Test als Subprozess: Harness schreibt zwei Zeilen, beendet sich mit
   `os._exit(1)`; zweiter Lauf muss die zwei überspringen und den Rest schreiben.

**P4 — Zuverlässigkeitsmetriken (`yun_full/reliabilitaets_metriken.py`)**
Anfragen, Erfolg im ersten Versuch, Erfolg nach Retry, endgültig fehlgeschlagen,
Timeout-/HTTP-/JSON-Raten, Retry-Erfolgsquote, mittlere Versuche, Latenz
(Mittel/Median), Tokens je erfolgreichem Record. Getrennt ausgewiesen:
technische Zuverlässigkeit und Extraktionsqualität.

**P5 — Validierung an Yun-699 (erst nach Nachtlauf und Nachzug)**
1. Endgültige Zahl der technischen Ausfälle aus der dann aktuellen Datei.
2. Die 36 leeren Antworten separat auswerten (eigener Block).
3. Kontrolllauf nur auf den betroffenen Records mit `--retry-strategie neu` und
   dem Budget, das die Diagnose verlangt; keine parallelen Läufe, keine
   konkurrierenden Dateien.
4. Vergleichstabelle alt/neu auf **denselben** Records und Goldzellen; Ergebnis in
   `docs/internal/reliability_validierung.md`.

## 7. Erwartbare Wirkung, ehrlich beziffert

- Die 103 Budget-Fälle sind mit Retry **nicht** zu retten; sie brauchen mehr
  Budget. Der Reparaturlauf mit `--repair` und 6.000 Tokens geht in die falsche
  Richtung: kleinere Budgets für ein Modell, das im Reasoning 32.000 Zeichen
  erzeugt.
- Der eine Timeout ist mit dem neuen Manager sicher rettbar (4 Goldzellen).
- Die 43 × 429 wurden schon heute behandelt; der Gewinn liegt dort in der
  Wartezeit, nicht in der Quote.
- Der größte Hebel für den Recall liegt damit **nicht** im Retry-Manager, sondern
  in der Budgetfrage — das ist eine Prompt-/Konfigurationsentscheidung und
  ausdrücklich nicht Teil dieses Auftrags („keine unnötigen Änderungen an der
  Modell- oder Promptstrategie"). Der Plan hält sie als P6 zurück und legt sie
  erst nach der Messung vor.

## 8. Offene Unsicherheiten

1. Ob die 3 `json_kaputt`-Fälle Modell- oder Parserfehler waren, ist ohne
   Rohantwort nicht entscheidbar; ab `586dd18` ist das Feld vorhanden.
2. Ob der Anbieter `Retry-After` überhaupt setzt, ist unbekannt — der Harness
   liest die Header heute nicht. P0/P1 erfassen sie, dann ist es messbar.
3. Ob 24.000 Tokens die Budget-Fälle lösen, ist eine **Hypothese** aus der
   Reasoning-Länge (Median 32.448 Zeichen ≈ 8.000 Tokens). Sie ist erst nach
   einem kontrollierten Lauf belegt.
4. Die Latenz von 42 s im Median ist nicht in Modell- und Übertragungszeit
   zerlegbar, weil kein Zeitstempel je Versuch existiert.

## 9. Abnahmekriterien

- Simulierte temporäre Fehler (Timeout, 429, 500, Verbindungsabbruch) führen ohne
  Eingriff zu einer gültigen Zeile.
- Ein Abbruch nach n Zeilen und ein Neustart erzeugen genau eine Zeile je Paar,
  keine Duplikate, keinen Verlust.
- Zwei gleichzeitige Prozesse auf derselben run-id: einer arbeitet, der andere
  bricht mit Exit 3 ab.
- Eine erfolgreiche Zeile wird durch keinen späteren Fehler überschrieben.
- Alle Tests laufen offline; `pytest public_benchmark/tests/ -k "retry or
  fehlerpfade"` genügt.
- Der bestehende Nachzug läuft mit `--retry-strategie alt` unverändert.
