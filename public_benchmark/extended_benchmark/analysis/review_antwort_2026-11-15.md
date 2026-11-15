# Antwort auf das Review vom 15.11.2026

Alle sechs Befunde sind geprüft und, soweit sie Code oder Berichte betreffen,
behoben. Kein API-Aufruf, keine Gold-Änderung, kein Split-Eingriff. Tests: 226
grün (vorher 221).

## Befund 1: „5 von 6 liefern Zellen" war irreführend — behoben

Richtig: fünf Antworten sind valides JSON, **vier** liefern Zellen.
`yun2024:325` antwortet gültig mit leerer Zellenliste.

* `pilot_len.urteil()` trennt jetzt `erfolge_json` und `erfolge_mit_zellen`
  (plus `quote_json`, `quote_mit_zellen`, `kriterium_erfuellt_json`).
* `pilot_urteil.json` ist neu erzeugt: 5 valides JSON, 4 mit Zellen,
  Median 8.951, `bestanden = false`.
* `pilot_v7.md` nennt beide Zahlen und sagt ausdrücklich, dass das vorab
  festgelegte Kriterium auf parsebares JSON zielt.
* Commit-Titel der Vergangenheit bleiben stehen (keine History-Rewrites); die
  Korrektur steht im Bericht.

## Befund 2: README beschrieb einen überholten Stand — behoben

Kopfzeile nennt jetzt den Stand vom 15.11.2026 mit Hauptlauf (186 Records,
1,71 Mio Completion-Tokens), 221/226 Tests, Verweis auf die Run-Verzeichnisse
und `analysis/run186_20261115/`. In „Offene Punkte" steht, welche Auswerter
gebaut sind und dass Label-Genauigkeit und Spannen-F1 weiterhin fehlen.

## Befund 3: `mische_quelle.py` ohne Überschreibschutz — behoben

* `fuehre_zusammen()` vergleicht `resolve()` von Ziel und beiden Quellen
  (Datei **und** Elternverzeichnis) und bricht mit `ValueError` ab; `main()`
  gibt dann Exit-Code 2.
* Folgelauf-IDs ohne Gegenstück im Hauptlauf werden gezählt und als
  `folge_nicht_zugeordnet` / `folge_nicht_zugeordnet_ids` ausgewiesen. Beim
  echten Merge: 0.
* Zwei Tests: verbotene Zielpfade, Ersetzungsregel plus fremde ID.

## Befund 4: `ausfaelle` in `je_quelle` war unscharf — behoben

`je_quelle` trennt jetzt `technische_ausfaelle` (gesetzte `fehlerklasse`) und
`leere_antworten` (gültige Antwort ohne Zellen). Für den Folgelauf heißt das
18 technische Ausfälle und 6 leere Antworten statt pauschal 18 „Ausfälle".

## Befund 5: neue Entscheidungslogik ungetestet — behoben

Drei neue Testdateien-Abschnitte in `tests/test_analyse_skripte.py`:

1. `pilot_len.urteil()` zählt eine leere `stop`-Antwort als JSON-Erfolg, nicht
   als Zellerfolg; das Kriterium schlägt erst ab fünf parsebaren Antworten an.
2. `mische_quelle.fuehre_zusammen()` verweigert Haupt- und Folgelauf als Ziel
   und zählt fremde IDs.
3. `evaluate_fallback` zählt `technische_ausfaelle` und `leere_antworten`
   getrennt und respektiert `--nur-ids`.

## Befund 6: zwei F1-Werte — behoben

Der Bericht `folgelauf_v7_und_goldkonflikte.md` nennt `gesamt.cell_f1 = 0,6934`
ausdrücklich als Hauptwert und erklärt `zell_f1_aus_klassen = 0,6784` als
Nebenrechnung aus den Klassenzählern, die nicht austauschbar ist.

## Offen geblieben

* Keine inhaltliche Neubewertung der Gold-Konflikte über die vorhandenen
  Textbelege hinaus.
* Label-Genauigkeit und Spannen-F1 haben weiterhin keine Auswerter.
* Die kombinierte Kennzahl bleibt eine Mischung aus 157 v6- und 29 v7-Zeilen
  mit 18 verbliebenen v7-Fehlern im v6-Stand; sie ist keine
  Modellverbesserung und wird im Bericht so eingeordnet.
