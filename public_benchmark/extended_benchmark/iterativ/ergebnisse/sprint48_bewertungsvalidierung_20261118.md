# Sprint 48: Validierung der Bewertungslogik und Vorbereitung der P5-Ergebnisprüfung

Stand: 18.11.2026, 18:30. Modus: offline, keine Modell- oder Netzwerkläufe, keine
Prozesseingriffe. Neue Dateien: diese Bericht und
`public_benchmark/tests/test_bilanz_adversarial_20261118.py`. Kein Commit
(Sprint-Vorgabe).

Prozesslage während des Sprints: Nachzug 2152/2153 und Wache 6630 unverändert;
der Nachtlauf wechselt die PID je Etappe (zuletzt 46068 laut `lauf_status.py`),
er ist nicht beendet — die Zeilen wuchsen im Sprint von 2013 auf 2121. Nichts
davon wurde angefasst.

Kategorien: **bestätigt** (belegt), **Verdacht** (Hinweis, nicht abschließend
geprüft), **nicht prüfbar** (fehlt die Grundlage).

## 1. Aufgabe A: TP/FP/FN unabhängig validiert

### Verfahren

`bilanz()` zählt Zelle für Zelle mit gieriger Erstzuordnung. Eine zweite
Zählung gleicher Bauart hätte denselben Denkfehler wiederholt, deshalb arbeitet
das Orakel in `test_bilanz_adversarial_20261118.py` anders: Es gruppiert Gold und
Vorhersage nach (Schlüssel, Wert) und nimmt je Gruppe das Minimum.

```
tp = sum(min(#gold(k,v), #vorhergesagt(k,v)))
fn = #gold_mit_zahl - tp
fp = #vorhersagezellen - tp
ueberzaehlig = #vorhersagezellen_mit_goldschluessel - tp
fremdschluessel = fp - ueberzaehlig
```

Beide Rechnungen treffen sich auf 200 Zufallsfixtures (Seed 48, Felder × Arme ×
Werte inklusive `None` und `"0,5"`) ohne Abweichung.

### Die zehn Prüffragen

| # | Frage | Antwort | Beleg |
|---|---|---|---|
| 1 | Jede Goldzelle höchstens einmal als TP? | **bestätigt** | `test_eine_vorhersagezelle_wird_nur_einmal_verbraucht`: Gold zweimal, eine Vorhersage → 1 TP, 1 FN |
| 2 | Jede Vorhersagezelle höchstens einmal verbraucht? | **bestätigt** | `test_eine_goldzelle_wird_nur_einmal_getroffen`: 3 identische Vorhersagen → 1 TP, 2 FP |
| 3 | Falscher Wert auf bekanntem Schlüssel = FP? | **bestätigt** | 1 FP (`ueberzaehlig`) und 1 FN, nicht 0 und nicht 2 |
| 4 | Dubletten als überzählige FP? | **bestätigt** | dritte Zelle auf demselben Schlüssel zählt in `ueberzaehlig`, nicht als zweiter TP |
| 5 | Unbekannte Schlüssel als fremde FP? | **bestätigt** | fremdes Feld, vertauschter Arm und fremder Schlüssel landen in `fremdschluessel` |
| 6 | Nicht bewertbare Records korrekt ausgeschlossen? | **bestätigt** | Record ohne Gold: `zellbilanz.records` bleibt 1, seine 4 Zellen stehen als `zellen_ohne_gold` |
| 7 | Records ohne Goldzellen separat? | **bestätigt** | eigene Berichtszeile „nicht als FP gezählt"; `yun2024:653` ist der einzige Fall |
| 8 | Fehlende Vorhersagen als FN? | **bestätigt** | 1 von 3 Zellen geliefert → 1 TP, 0 FP, 2 FN |
| 9 | 1:1-Zuordnung unabhängig von der Reihenfolge? | **bestätigt** | alle 6 Gold- und 24 Vorhersage-Permutationen eines gemischten Falls ergeben dieselbe Bilanz |
| 10 | Mehrdeutige Zeitpunkte konsistent? | **bestätigt, mit Vorbehalt** | `bilanz()` liest Zeitpunkte gar nicht: 1 TP + 2 überzählige FP; die strenge Zählung meldet für denselben Fall 0 Treffer. Konsistent, weil Precision bewusst eine Obergrenze ist |

### Neue adversariale Fälle (16 Tests, alle grün)

Identische Dubletten, falscher Wert, vertauschter Arm, unbekanntes Feld,
fehlende Zellen, leere Antwort, Gold-Dublette, mehrere Zeitpunkte, Record ohne
Gold, Reihenfolge-Permutationen, Goldwert `None`, unlesbarer Vorhersagewert,
Komma/Leerzeichen-Schreibweise, Feld-Großschreibung, Zufallsfixtures gegen das
Orakel, Quotientenrechnung.

### Befunde, die über die Sollprüfung hinausgehen

**B1 bestätigt: Feldnamen werden nicht normalisiert, Arme schon.** `schluessel()`
senkt den Arm und entfernt Leerzeichen, lässt das Feld aber unverändert. Ein
Goldfeld `Intervention_Mean` und eine Vorhersage `intervention_mean` sind zwei
verschiedene Schlüssel: 1 FP plus 1 FN. In Yun-699 stammen Gold und Vorhersage
aus derselben Feldliste, deshalb ist der Effekt dort voraussichtlich null — in
P5 aber nicht messbar ausgeschlossen, weil die Feldnamen aus freiem Text kommen.

**B2 bestätigt: Gold-Dubletten werden nicht dedupliziert.** Steht derselbe
Schlüssel mit demselben Wert zweimal im Gold und liefert das Modell eine Zelle,
zählt die zweite Goldzelle als FN. In Yun-699 gibt es keine doppelten
Feld/Arm-Schlüssel (im Audit geprüft), also heute wirkungslos. Würde der
Goldstandard je Dubletten bekommen, fiele der Recall künstlich.

**B3 bestätigt: eine Vorhersagezelle ohne lesbare Zahl wird doppelt bestraft.**
Sie kann nicht treffen (Goldzelle bleibt FN) und wird zugleich als FP gezählt.
Das ist bei Precision/Recall-Spannen bewusst so, sollte im P5-Bericht aber
dastehen, damit niemand es für einen Zählfehler hält.

**B4 Verdacht: die 1e-6-Toleranz kann zwei fast gleiche Zellen paaren, das
Orakel nicht.** Für den Testbetrieb irrelevant (dort stehen beidseits dieselben
Literale), für echte Läufe offen: gerundete Vorhersagen (0,7699999 gegen 0,77)
gelten als Treffer. Wirkung nach oben begrenzt, Größe unbekannt.

## 2. Aufgabe B: Die zwei übersprungenen Tests

Beide liegen in `research_agent/tests/test_win_job.py` und sind
**absichtliche Plattformwächter**, keine fehlenden Voraussetzungen:

| Test | Datei | Grund |
|---|---|---|
| `TestNoopAusserhalbWindows::test_create_job_ist_none` | `research_agent/tests/test_win_job.py:25` | `@unittest.skipUnless(not IS_WINDOWS, "nur auf Nicht-Windows relevant")` |
| `TestNoopAusserhalbWindows::test_attach_ist_false` | dieselbe Klasse | dito |

Auf diesem Rechner ist `IS_WINDOWS` wahr, deshalb wird die Klasse
`TestNoopAusserhalbWindows` übersprungen und `TestJobGrenzen` ausgeführt (7 Tests
bestanden). Die übersprungene Funktionalität ist damit **nicht** ungetestet: Der
No-op-Zweig von `create_job()`/`attach_job_limits()` ist genau das, was auf
Nicht-Windows gelten muss, und wird dort geprüft.

**Qualitätsrisiko: gering, aber vorhanden.** Auf jeder Plattform bleibt der
jeweils andere Zweig unausgeführt; auf Windows ist der No-op-Pfad nie gelaufen.
Ein Fehler, der nur dort steckt, fiele hier nicht auf. Das ist der Preis zweier
getrennter Plattformpfade und kein Versäumnis des Tests.

**Nebenbefund, nicht prüfbar:** Beim ersten Grep existierte zusätzlich
`research_agent/tests/test_pwert_korrobation.py` mit einem Skip-Marker; beim
gezielten Lauf war die Datei weg, `git log` kennt sie nicht. Sie war also
unversioniert und wurde von einem parallelen Vorgang gelöscht. Sie gehört nicht
zur Suite (der Wurzel-Lauf zählt unverändert 2 Skips) und wird hier nicht
bewertet.

## 3. Aufgabe C: Stichprobenprüfplan für den echten P5-Lauf

Keine P5-Ergebnisse vorhanden; nichts wird simuliert. Das Verfahren steht fest,
die Ziehung passiert nach dem Lauf.

### Grundgesamtheit

103 IDs der P5-Auswahl, 102 mit Gold (423 Goldzellen), 1 ohne Gold
(`yun2024:653`). Auswertungsquelle ist ausschließlich
`runs/yun699_p5_24000_20261118/predictions.jsonl` plus
`yun_full/records/yun699.jsonl` (Gold) — nie der Bericht.

### Geschichtete Ziehung

| Schicht | Umfang | Auswahl |
|---|---|---|
| Treffer mit richtigem Wert und Arm (TP) | 10 | zufällig, `seed = 48` über die sortierten Record-IDs |
| Richtiger Schlüssel, falscher Wert | bis 10 | gezielt: alle FP mit `ueberzaehlig`-Merkmal, dann Zufall bis zur Grenze |
| Richtiger Schlüssel mehrfach extrahiert | bis 5 | gezielt: Records mit `zellen_neu > goldzellen` |
| Richtiger Wert, falscher Arm | bis 10 | gezielt: FP mit `fremdschluessel`, deren Wert im Gold derselben Zelle vorkommt |
| Falscher Zeitpunkt | bis 10 | gezielt: adressiert, aber nicht wertgleich in der strengen Zählung |
| Fehlender Goldwert | alle | Goldzellen mit `value` ohne Zahl |
| Vorhersage ohne Goldzelle | alle | Zellen von `yun2024:653` |

Regel: Gezogen wird über deterministische Sortierschlüssel
`(record_id, field, arm)`, damit dieselbe Ziehung reproduzierbar ist; die
gezogenen IDs und der Seed werden im P5-Bericht protokolliert.

### Schema je Fall

| Record-ID | Goldfeld | Goldarm | Goldwert | Vorhersage | Bewertung | Fehlerursache |
|---|---|---|---|---|---|---|

- **Vorhersage:** Feld, Arm, Wert und Zeitpunkt der Zelle im Wortlaut, plus
  `timepoint`.
- **Bewertung:** `TP`, `FP-dublette`, `FP-wert`, `FP-arm`, `FP-fremd`,
  `FN-fehlt`, `FN-wert`, `nicht bewertbar`.
- **Fehlerursache:** kurz und konkret („Arm vertauscht", „Wert 0,77 gegen 0,70",
  „Schlüssel zweimal mit gleichem Wert", „Zeitpunkt 12 weeks statt 30 days").

### Abnahme

Die Stichprobe muss die Bilanz des jeweiligen Records nachrechnen. Weicht eine
Zeile ab, ist die Auswertung zu stoppen und die Ursache zu klären; die Stichprobe
darf nicht durch Nachjustieren der Erwartung „grün" gemacht werden. Ein Fall
bleibt ohne Goldwert (`yun2024:653`) und wird nur auf „nicht als FP gezählt"
geprüft.

## 4. Aufgabe D: Dokumentationsabweichungen

Verglichen: `README.md` (Tests-Abschnitt), `pytest.ini`,
`docs/verification/bericht_2026-11-13.md` §5, `VERBESSERUNGSBRIEFING.md` §8.
Die beiden Dateien sind mit Commit `632b43f` **umgesetzt**; was unten als
Zitat steht, ist der übernommene Wortlaut.

### `docs/verification/bericht_2026-11-13.md`, Abschnitt 5

Ist-Zustand: `python -m pytest research_agent/tests/test_verification_system.py -q`
mit „12 passed" und `python -m pytest public_benchmark/tests -q` mit „46 passed".

Zwei Probleme: Es fehlt der Wurzelaufruf, und die Zahlen sind ein Messwert vom
13.11.2026, der heute (382 Tests in `public_benchmark`) wie eine aktuelle Angabe
aussieht. Umgesetzte Fassung (Wortlaut aus `632b43f`):

```text
## 5. Tests

Standardaufruf (aus der Projektwurzel, gesamte Suite):

    export PYTHONIOENCODING=utf-8
    python -m pytest -q

Schnelle Einzelpruefung ohne die vollstaendige Suite:

    python -m pytest research_agent/tests -q
    python -m pytest public_benchmark/tests -q

Stand vom 13.11.2026 — damaliger Messwert, keine aktuelle Angabe:

    python -m pytest research_agent/tests/test_verification_system.py -q
    12 passed

    python -m pytest public_benchmark/tests -q
    46 passed

    python -m py_compile <alle neuen Module>
    OK
```

### `VERBESSERUNGSBRIEFING.md`, Abschnitt 8

Ist-Zustand: „Tests mit UTF-8-Ausgabe: `export PYTHONIOENCODING=utf-8; python -m
pytest research_agent/tests/<file>.py -q`".

Umgesetzte Zeile (Wortlaut aus `632b43f`):

```text
- Tests: `export PYTHONIOENCODING=utf-8; python -m pytest -q` (gesamte Suite aus
  der Wurzel, siehe `pytest.ini`). Fuer eine schnelle Einzelpruefung genuegt
  `python -m pytest research_agent/tests/<datei>.py -q`.
```

Damit steht in beiden Dateien der Wurzelaufruf als Standard, die schnellen
Einzelaufrufe bleiben, und keine alte Zahl wird als aktuelle Messung ausgegeben.
Genau so stehen die Dateien seit `632b43f`.

## 5. Offene Risiken

| # | Risiko | Kategorie | Wirkung |
|---|---|---|---|
| R1 | Feldnamen ohne Normalisierung (B1) | bestätigt | bei abweichender Schreibweise FP und FN zugleich |
| R2 | Gold-Dubletten nicht dedupliziert (B2) | bestätigt | heute wirkungslos, künftig Recall-Verlust |
| R3 | Vorhersage ohne Zahl doppelt bestraft (B3) | bestätigt | Precision und Recall sinken gemeinsam |
| R4 | 1e-6-Toleranz paart gerundete Werte (B4) | Verdacht | Precision leicht zu hoch |
| R5 | Zeitpunkt im Gold fehlt weiterhin | bestätigt (aus dem Audit) | Precision bleibt Obergrenze |
| R6 | No-op-Zweig der Job-Sandbox auf Windows ungetestet | bestätigt | geringes, plattformbedingtes Risiko |
| R7 | P5 selbst noch nicht gelaufen | bestätigt | alle Quoten sind Vorbereitung, keine Messung |
| R8 | Parallele Sitzungen ändern Dateien im Repo | nicht prüfbar | eine Datei verschwand zwischen zwei Befehlen; Prüfstände können driften |

## 6. Antwort auf die Abschlussfrage

**Ist die Bewertungslogik für den echten P5-Lauf ausreichend abgesichert?**

Ja, mit zwei ausdrücklichen Vorbehalten. Die 1:1-Zuordnung ist in beide
Richtungen belegt, die drei Fehlerarten sind getrennt zählbar, Records ohne Gold
bleiben draußen, und Orakel plus 200 Zufallsfixtures finden keine Abweichung.
Nicht abgesichert ist die Bedeutung der Zahl: Precision bleibt eine Obergrenze,
weil das Gold keinen Zeitpunkt trägt, und die drei Befunde B1 bis B3 zeigen, wo
die Quote systematisch zu niedrig ausfallen kann. Beides gehört in den P5-Bericht,
nicht in eine stille Fußnote.

Die Bewertung selbst ist damit prüfbar; die Stichprobe aus Abschnitt 3 ist der
Schritt, der nach dem Lauf aus einer Rechnung eine belegte Aussage macht.
