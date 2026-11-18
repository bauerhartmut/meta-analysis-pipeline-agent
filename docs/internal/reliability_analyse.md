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
beim Siebenfachen an Reasoning, und die 8.000 Token des Laufs `yun699_8000_alle`
waren an der Grenze. Ob **mehr** Budget diese Records gerettet hätte, ist damit
noch nicht gesagt — das prüft Abschnitt 3a.

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

## 3a. Die Budget-Hypothese, an den vorhandenen Daten geprüft

Die Hypothese in der Fassung „8.000 Token waren zu knapp, mehr Budget hätte die
103 gerettet" wurde nicht nur an der Lesekopie, sondern an **allen** GLM-Zeilen
des Arbeitsbaums geprüft: 2.707 Zeilen aus 43 Läufen, dazu die 699 Zeilen der
Lesekopie. Skript: `yun_full/pruefe_budget_hypothese.py`, Ergebnis:
`iterativ/ergebnisse/budget_hypothese_20261118.json` (kein Netzaufruf, keine
Datei im Laufverzeichnis angefasst).

**A — Mechanik: bestätigt.** 395 abgeschnittene Zeilen mit bekannter Grenze,
davon **395** mit `completion_tokens` genau gleich der Grenze und 391 ohne
Inhalt. Reasoning-Zeichen je Token: Median 4,0 (min 2,8, max 4,6, n = 390). In
der Lesekopie: 103 von 103, 101 ohne Inhalt, Median 4,1. Der Schnitt liegt also
immer exakt an der Obergrenze, und das Reasoning hat sie gefüllt. Die
Bezeichnung `budget_im_reasoning` beschreibt den Mechanismus korrekt.

**B/C — Rettung: nur teilweise, und für die 103 gar nicht belegt.**

| Vergleich (gleicher Record, zwei Budgets) | Ergebnis |
|---|---|
| 8.000 → 19.000 | `length` → Zellen 15, `length` → `length` 16, `length` → leer 5 |
| 8.000 → 16.000 | `length` → `length` 18 |
| 8.000 → 24.000 | `length` → `length` 10 |
| 24.000 → 32.000 | `length` → `length` 1 |

Von 237 `length`-Ausfällen bei 8.000 haben nur 38 überhaupt eine Beobachtung mit
mehr Budget; davon enden 15 mit Zellen (39 %), 20 erneut in `length` (53 %),
3 leer. Alle 15 Rettungen stammen aus den 19.000er-Zeilen der v7-Fassung; bei
16.000 und 24.000 wurde keiner gerettet — dort wurden aber auch gezielt schon
gescheiterte Records wiederholt, was die Quote nach unten zieht. **Für die 103 Zeilen der Lesekopie existiert keine einzige Beobachtung
über 8.000** — sie stammen alle aus `v2_timepoint_cb`, und von diesem Prompt gibt
es keinen Lauf mit größerem Budget. Die Rettungsquote ist damit ein Analogieschluss
aus anderen Prompt-Fassungen, keine Messung an diesen Records.

**D — Skalierung: gegen die Hypothese.** Bei 184 Records mit zwei Budgets wächst
die Reasoning-Länge mit dem Budget, im Median auf das **2,3-fache**. Die
Ausfallquote je Stufe: 4.000 → 25,0 % (30/120), 8.000 → 15,8 % (237/1.503),
19.000 → 21,8 % (47/216). Die 16.000er- und 24.000er-Zeilen sind ausschließlich
Wiederholungen bereits gescheiterter Records (v6); ihre 100 % sind Auswahl, keine
Quote. Die 19.000-Zeilen stammen aus der v7-Fassung und sind damit ebenfalls
nicht bereinigt vergleichbar — die Richtung bleibt aber: mehr Budget
verschiebt die Grenze, statt das Verhalten zu ändern. Einzelbeleg: `yun2024:228`
lief mit Standardbudget in 3.728 Tokens zu Zellen, mit 24.000 in eine
Reasoning-Spur von 104.614 Zeichen ohne Inhalt.

**Urteil.** Die Hypothese ist **mechanisch bestätigt und als Rettung
unbestätigt**: das Budget ist die abgeschnittene Größe, aber mehr Budget löst den
Fall nicht zuverlässig, weil das Modell die zusätzliche Spanne wieder im
Reasoning verbraucht. Für die 103 Records fehlt jede Beobachtung; realistischer
Ausgangspunkt für eine Messung ist eine Rettungsquote um 40 %, nicht um 100 %.
Damit ist „mehr Budget" **keine Zuverlässigkeitsmaßnahme** und bleibt aus P1–P4
heraus; sie ist eine Konfigurationsfrage, die P5 messen muss.

## 3b. Sind die 103 vor P5 überhaupt auflösbar?

`records/yun.jsonl` ist eine abgeleitete, **unversionierte** Datei mit heute 450
Records (Stand 15.11., 19:52); der Lauf hatte 699. Der im Live-Vergleich
aufgefallene Abstand von 226 erfolgreichen Zeilen ist damit kein Verlust: die
versionierte Quelle des Laufs ist `yun_full/records/yun699.jsonl` (699 Records,
im Repo).

| Gruppe | Zeilen | in `records/` | nur über `yun699.jsonl` | nicht gefunden | ohne Dokument | ohne Gold | Goldzellen |
|---|---|---|---|---|---|---|---|
| Ausfall | 104 | 81 | 23 | 0 | 0 | 1 | 427 |
| Erfolg | 595 | 369 | 226 | 0 | 0 | 30 | 2.346 |

Alle 23 nur über die Ersatzquelle erreichbaren Ausfälle liegen in
`yun_full/records/yun699.jsonl` und haben dort eine vorhandene Dokumentdatei und
Gold; die beiden Handoff-Dumps braucht es dafür nicht. Der Probelauf mit
`--records …/yun699.jsonl --ids yun2024:128,yun2024:30,yun2024:674` wählt die
Records im Trockenlauf korrekt aus.

**Für P5 konkret:** ein Lauf auf `yun_full/records/yun699.jsonl` mit den 103 ids
erreicht jeden Ausfall. Zwei Einschränkungen: `yun2024:653` hat **keine
Goldzellen** — die 103 tragen 423 Zellen, bewertbar sind also 102 Records mit
419 Zellen; und die frühere Angabe „427 Goldzellen für die 104" bleibt richtig,
weil darin die 4 Zellen der Timeout-Zeile `yun2024:87` stecken.

Offen bleibt, warum `records/yun.jsonl` nur 450 Records hat: die 249 entfernten
liegen ausschließlich im `test`-Split, und weder `issues` noch der Split erklärt
die Auswahl (146 der entfernten tragen `issues`, aber 370 behaltene auch).
Quelle: `yun_full/pruefe_aufloesbarkeit.py`,
`iterativ/ergebnisse/aufloesbarkeit_20261118.json` und `.md`.

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

**P0 — Diagnose und Telemetrie (kein Verhaltensrisiko) — umgesetzt**
1. `yun_full/fehlerklassen.py`: zentrale `klassifiziere()` mit zehn Klassen —
   `ok`, `leer`, `timeout`, `verbindungsfehler`, `rate_limit`, `server_fehler`,
   `auth`, `anfrage_ungueltig`, `budget_im_reasoning`, `json_kaputt` —, je
   Klasse `temporaer: bool`. `json_abgeschnitten` ist gestrichen: null Fälle.
2. `budget_im_reasoning` = `finish_reason=length` ∧ keine verwertbaren Zellen.
   `fehlerklasse_aus` bleibt für den Altpfad unverändert daneben stehen; die
   Zeilenklasse bleibt kompatibel (`length_ohne_ergebnis`), weil `done_keys`,
   die Auswertung und `nachzug_ausfaelle.sh` das Feld direkt lesen.
3. Zeile erweitert um `attempts: [{attempt_id, rolle, http_status, dauer_s,
   wartete_s, finish_reason, completion_tokens, reasoning_chars, content_chars,
   fehlerklasse, temporaer}]` und `job_status` (`completed`/`failed`) — **nur**
   bei `--retry-strategie neu`; `alt` schreibt byte-gleich weiter.
4. Prüfung: `tests/test_fehlerklassen.py::test_befund_der_lesekopie` schickt die
   104 Ausfallzeilen durch die neue Klassifikation und erwartet
   103 × `budget_im_reasoning`, 1 × `timeout`.

**P1 — Retry-Manager (`yun_full/retry_manager.py`, synchron, ohne Netz testbar) — umgesetzt**
Gekürzt nach Abschnitt 3a: **kein** `timeout_faktor`, **keine** getrennten
Verbindungs- und Lesezeitgrenzen, **keine** Klasse `json_abgeschnitten`. Diese
Teile hätten nur den einen Timeout-Fall bedient; der Timeout ist im Manager eine
temporäre Klasse wie jede andere Transportstörung, ohne eigene Mechanik. Die
Frage „kam eine Antwort?“ beantwortet `fehlerklassen.klassifiziere_http`
(HTTP 200 = angekommen); die Inhaltsklasse bleibt bei `work`, damit der Manager
keine Zellenzahl vortäuschen muss.
1. `RetryPolicy(max_versuche=3, timeout_s=300, basis_s=2.0, faktor=2.0,
   max_delay_s=60, jitter=0.25)`.
2. `wartezeit(versuch, retry_after)` — Retry-After hat Vorrang, sonst Backoff mit
   Jitter, gedeckelt. Das ist der einzige heute messbare Gewinn: 43 × 429, alle
   bei `qwen30`. `_call_once` liest dafür den Header in Sekunden; ein HTTP-Datum
   wird ignoriert, und der Deckel gilt auch für `Retry-After`.
3. `fuehre_aus(aufruf, policy)` — klassifiziert über `fehlerklassen`, wiederholt
   nur temporäre Klassen, protokolliert jeden Versuch; nicht-temporäre (auth,
   ungültige Anfrage, Budget im Reasoning) enden sofort.
4. `call(..., strategie=...)` nutzt den Manager bei `neu`; `main()` reicht das
   Flag als Parameter durch — kein Modulzustand, der zwischen Aufrufen stehen
   bleibt. `alt` bleibt byte-gleich zum heutigen Verhalten. Die Zeile trägt unter
   `neu` zusätzlich `http_versuche` (Summe aller HTTP-Versuche des Auftrags) als
   Grundlage für P4.
5. Geprüft: 13 Szenarien in `tests/test_retry_manager.py` (Erfolg im ersten und
   zweiten Versuch, Retry-After vor Backoff, Deckel, 503 dauerhaft, Timeout,
   Verbindungsabbruch, endgültige Klassen, Backoff-Reihe, Jitter-Grenzen,
   Versuchsnummer, Meldung) und zwei Verdrahtungstests am echten `call`-Pfad.

**P2 — Persistenz und Crash-Recovery (ohne neue Datenbank) — umgesetzt**
Geschnitten auf das, was ein Absturz wirklich braucht: keine Job-Queue, kein
Planer. Neues Modul `yun_full/jobs.py`, wirksam nur unter `--retry-strategie neu`.
1. `runs/<run>/jobs.jsonl` (append-only, je Zeile `flush` + `os.fsync`): `ts`,
   `record_id`, `model`, `status` (`running`/`completed`/`failed`),
   `fehlerklasse`. Drei Zustände statt fünf: `pending` und `retry_pending` hätte
   niemand gelesen, weil die Auftragsliste ohnehin aus `done_keys` entsteht.
2. `unterbrochene()` liest das Journal beim Start und meldet Aufträge mit
   `running` ohne Abschluss. Sie laufen von selbst erneut, weil für sie keine
   Zeile in `predictions.jsonl` steht; `done_keys` bleibt unverändert.
3. Reihenfolge im Schreibpfad: erst `running`, dann die Zeile, dann
   `completed`/`failed`. Ein Absturz dazwischen hinterlässt `running`, und die
   Zeile entscheidet beim nächsten Start — also kein Verlust und keine Dublette.
4. `runs/<run>/harness.lock`; ein zweiter Prozess bricht mit Exit 3 ab und
   schreibt keine Zeile. Die Sperre prüft, ob der eingetragene Prozess noch
   lebt, und wird sonst **sofort** übernommen. Das war nötig, weil der echte
   Abbruchtest gezeigt hat: `os._exit` überspringt das `finally`, die Sperre
   bleibt stehen, und mit reiner Altersregel wäre ein Neustart 90 Minuten
   blockiert. Unter Windows prüft `OpenProcess` mit Leserecht — `os.kill(pid, 0)`
   würde den Prozess dort beenden statt ihn zu testen. Nur wenn sich das nicht
   entscheiden lässt (fremde PID, unbekannter Wert), gilt die 90-Minuten-Regel.
   `nachzug_ausfaelle.sh` bleibt unverändert und behält seine eigene Sperre.
5. Geprüft offline: `tests/test_jobs.py` (Journal-Replay, halb geschriebene
   Zeile, Sperre/Freigabe, fremde Sperre, lebende und beendete PID,
   Altersregel als Rückfall) und fünf Pfadtests am Harness (Journal und Freigabe,
   `alt` legt nichts an, zweiter Lauf schreibt keine zweite Zeile, belegte
   Sperre → Exit 3, unterbrochener Auftrag läuft erneut und wird abgeschlossen).
6. **Echter Abbruchtest** in `tests/test_crash_recovery.py`: ein Subprozess
   führt den echten Harness mit gefälschtem Aufruf aus, schreibt die erste
   Zeile, beginnt den zweiten Auftrag und beendet sich mit `os._exit(1)`. Danach
   liegen genau die Zustände eines Absturzes vor (eine Zeile, `running` ohne
   Abschluss, stehende Sperre). Ein zweiter Prozess meldet den unterbrochenen
   Auftrag, holt ihn nach, überspringt den fertigen und schreibt je Auftrag genau
   eine Zeile. Unter `alt` entsteht dabei weder Journal noch Sperre.

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

**P4 — Zuverlässigkeitsmetriken (`yun_full/reliabilitaets_metriken.py`) — umgesetzt**
Liest nur `predictions.jsonl`; kein Netz, keine Datenbank. Ausgegeben werden:
Aufträge, `completed`/`failed` (samt Zahl der rekonstruierten `job_status`),
Erfolg im ersten Versuch, Erfolg nach Wiederholung, endgültig fehlgeschlagen,
**aufgetretene** Transportfehler (jeder Versuch zählt, auch ein geheilter),
Versuche und HTTP-Versuche je Auftrag (Mittel/Median/Max), Wartezeit gesummt,
Latenz (Mittel/Median/p90), Tokens gesamt und je erfolgreichem Auftrag. Getrennt
davon steht die Extraktion: Aufträge mit Zellen und leere Antworten ohne
Fehlerklasse. Fehlt die Versuchsspur (Läufe unter `alt`), sind die
Retry-Kennzahlen `None`, nicht 0; der Bericht nennt den Grund.
Artefakt zum Stand: `iterativ/ergebnisse/reliabilitaets_metriken_20261118.json`
und `.md` (GLM, Lesekopie: 699 Aufträge, 595/104, Erfolgsquote 0,8512,
1.931.140 Tokens, 559 mit Zellen, 36 leer, keine Versuchsspur).

**Erster Live-Lauf unter `neu` (18.11.) — durchgeführt.** Zehn günstige Records
gegen das echte Gateway, eigener run-id, zwei Threads: 10/10 `completed`, je ein
HTTP-Versuch, Versuchsspur in allen Zeilen, `jobs.jsonl` mit 20 Zeilen
(`running` vor `completed`, auch bei zwei gleichzeitigen Aufträgen), Sperre
während des Laufs vorhanden und danach entfernt. Es trat **kein** Fehler auf,
also ist der `Retry-After`-/Backoff-Pfad live nicht beansprucht worden; er
bleibt offline geprüft. Zellenzahl gegenüber der `alt`-Zeile 10/10 gleich, der
Tokenverbrauch schwankt stark (443 → 1.195 bei `yun2024:698`). Bericht:
`iterativ/ergebnisse/neu_live_20261118.md`.

**P5 — Validierung an Yun-699 (erst nach Nachtlauf und Nachzug)**
1. Endgültige Zahl der technischen Ausfälle aus der dann aktuellen Datei.
2. Die 36 leeren Antworten separat auswerten (eigener Block).
3. Kontrolllauf nur auf den betroffenen Records mit `--retry-strategie neu` und
   dem Budget, das die Diagnose verlangt; keine parallelen Läufe, keine
   konkurrierenden Dateien.
4. Vergleichstabelle alt/neu auf **denselben** Records und Goldzellen; Ergebnis in
   `docs/internal/reliability_validierung.md`.
5. Vorbereitung (offline, erledigt): `yun_full/bereite_p5_vor.py` erzeugt aus der
   Lesekopie die Auswahl der 103 ids gegen `yun_full/records/yun699.jsonl` samt
   fertiger Kommandozeile. Ergebnis: 103 von 103 Records vorhanden, alle mit
   Dokumentdatei; 102 sind bewertbar und tragen 423 Goldzellen, `yun2024:653`
   hat keine und fällt aus Recall und MAE. Der Trockenlauf derselben Zeile wählt
   103 Aufträge und sendet nichts. Artefakt:
   `iterativ/ergebnisse/p5_vorbereitung_20261118.json` und `.md`.

## 7. Erwartbare Wirkung, ehrlich beziffert

- Die 103 Budget-Fälle sind mit Retry **nicht** zu retten (die Klasse ist
  bewusst nicht temporär). Ob mehr Budget hilft, ist nach Abschnitt 3a offen bis
  zu einer Quote um 40 % — nicht die 100 %, die die Reparaturschätzung vom 18.11.
  als Obergrenze benutzt hat. Der Reparaturlauf mit `--repair` und 6.000 Tokens
  geht in die falsche Richtung: kleineres Budget für ein Modell, das im Reasoning
  32.000 Zeichen erzeugt.
- Der eine Timeout ist mit einem zweiten Versuch wahrscheinlich rettbar, aber
  unbelegt (4 Goldzellen). Er ist kein Grund für eigene Timeout-Mechanik.
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
3. Ob 24.000 Tokens die 103 Budget-Fälle lösen, ist **offen**. Abschnitt 3a
   stützt die Mechanik (Schnitt exakt an der Grenze), aber nicht die Rettung:
   im beobachteten Teil retten 39 % der Fälle, und die Reasoning-Länge wächst mit
   dem Budget. Belegt ist das erst durch einen kontrollierten Lauf (P5).
4. Die Latenz von 42 s im Median ist nicht in Modell- und Übertragungszeit
   zerlegbar, weil kein Zeitstempel je Versuch existiert.

## 9. Abnahmekriterien

- Simulierte temporäre Fehler (Timeout, 429, 500, Verbindungsabbruch) führen ohne
  Eingriff zu einer gültigen Zeile.
- Ein Abbruch nach n Zeilen und ein Neustart erzeugen genau eine Zeile je Paar,
  keine Duplikate, keinen Verlust.
- Zwei gleichzeitige Prozesse auf derselben run-id (unter `neu`): einer
  arbeitet, der andere bricht mit Exit 3 ab.
- Eine erfolgreiche Zeile wird durch keinen späteren Fehler überschrieben.
- Alle Tests laufen offline; `pytest public_benchmark/tests/ -k "retry or
  fehlerpfade"` genügt.
- Der bestehende Nachzug läuft mit `--retry-strategie alt` unverändert.
