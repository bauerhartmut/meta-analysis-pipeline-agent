# Methodik der Evaluation

Diese Datei beschreibt, wie gemessen wurde. Sie ist Teil der Uebergabe und soll
unabhaengig von den Ergebnissen pruefbar sein.

## 1. Datensatz

Quelle: Yun et al. (2024), LLM-Meta-Analyse-Benchmark, Apache-2.0.
Rohform im Repository unter `public_benchmark/raw_data/yun_llm_meta_analysis/`.

- 699 Records aus 120 Artikeln (PMC-Volltexte als Markdown).
- Aufteilung des Originaldatensatzes: 43 Dev-, 656 Test-Records.
- 2.773 Goldzellen insgesamt.
- Adapter: `skripte/baue_yun699.py` erzeugt `daten/yun699.jsonl`; er prueft den
  SHA-256 des Quellbestands und normalisiert Tausendertrenner nur markiert
  (`normalisiert: true`, der Rohwert bleibt in `raw` erhalten).

Jeder Record enthaelt: `record_id`, `document.id` (PMC-ID), `document.path`,
`context` (Intervention, Comparator, Outcome, Outcome-Typ), `timepoint.target`
und `gold.cells`.

## 2. Stichproben

| Datei | Inhalt | Auswahlregel |
|---|---|---|
| `daten/stichprobe60.json` | 60 Records | geschichtet nach Outcome-Typ und Artikel, deterministisch |
| `daten/stichprobe20.json` | 20 Records | jeder dritte Record der 60er-Liste, damit ueber alle Schichten verteilt |

Alle Modellvergleiche laufen auf identischen Record-Listen. Die 20er-Liste ist
eine Teilmenge der 60er-Liste; Vergleiche zwischen Laeufen mit unterschiedlicher
Liste sind im Bericht als solche gekennzeichnet.

## 3. Metrikdefinitionen

### 3.1 Zellebene

Ein Goldfeld ist ein Tripel (Record, Feld, Goldwert). Ein Modellwert trifft,
wenn `|modell - gold| < 1e-9` (keine Toleranz, keine Rundung).

- **richtig** = Goldfeld mit passendem Modellwert.
- **falsch** = Goldfeld mit abweichendem Modellwert.
- **fehlend** = Goldfeld ohne Modellwert.
- **Zelle ohne Gold** = Modellwert fuer ein Feld, das im Gold nicht vorkommt.
  Diese Zellen sind **nicht bewertbar** und zaehlen weder als richtig noch als
  falsch; sie werden separat ausgewiesen.

Daraus:

```
Precision = richtig / (richtig + falsch)
Recall    = richtig / (richtig + falsch + fehlend)
F1        = 2 * Precision * Recall / (Precision + Recall)
```

Recall bezieht sich also auf **alle** Goldzellen; ein falscher Wert zaehlt wie
ein fehlender als nicht erinnert.

### 3.2 Recordebene (Yun-Zaehlweise)

Die Originalauswertung von Yun et al. arbeitet auf Recordebene:

- **exact**: alle Goldfelder des Records stimmen.
- **partial**: mindestens ein Feld stimmt, mindestens eines nicht.
- **unknown**: weder Treffer noch bewertbarer Fehler.

Sonderfall: Yun zaehlt auch `x == x` als Treffer, wenn Gold und Antwort beide
leer sind. Dadurch entstehen zwei Records, die nach strenger Zaehlweise nicht
exakt sind. Beide Zahlen werden getrennt ausgewiesen (`exakt_yun` und
`exakt_strict`).

### 3.3 Zahlenformate

Alle Werte werden als `float` verglichen. Einheiten werden nicht umgerechnet;
ein in mg/dl berichteter Wert gilt nicht als Treffer fuer einen in g/l
annotierten Goldwert.

## 4. Kontrollierte Vergleiche

Fuer jede Hypothese gilt:

1. Gleiche Records, gleiches Parsing, gleiche Evaluation.
2. Temperatur 0.0.
3. Ein identisches Outputlimit fuer alle verglichenen Modelle.
4. Eine Aenderung pro Experiment; der produktive Prompt v7 bleibt unveraendert,
   Varianten sind eigene Promptversionen.
5. Cache-Buster setzen und `suspected_cache` pruefen. Das Gateway liefert sonst
   die Antwort einer frueheren, aehnlichen Anfrage zurueck; ein erster A/B-Lauf
   bestand aus 18 von 19 Cache-Treffern und war damit wertlos.

## 5. Auswertung ohne bestreitbare Goldannotationen

Drei Records enthalten im Artikel zwei verschiedene Angaben; Gold und Modell
lesen unterschiedliche Stellen. Sie werden in `daten/ausschluss_konflikte.json`
zusaetzlich ohne diese Records ausgewiesen. Die Entscheidung, welcher Wert
richtig ist, wird **nicht** getroffen; beide Varianten stehen nebeneinander.

## 6. Validator

`skripte/validator.py` prueft Modellantworten ohne Goldzugriff und erzeugt nur
Warnungen, keine Aenderungen. Harte Regeln: Ereignisse groesser als
Gruppengroesse, doppelte Zelle, SD nicht positiv, extrem ungleiche Arme,
Ereigniszahl bei kontinuierlichem Outcome, leere Antwort. Weiche Hinweise
(fehlendes Feld, Mittelwert ohne Gruppengroesse) werden getrennt gezaehlt, weil
ein fehlendes Feld ohne Gold nicht bewertbar ist. Mit `--gegen-gold` werden
Warnungen gegen die Goldzellen gemessen.

## 7. Reproduktion

```
# Kennzahlen aller Laeufe neu berechnen
.venv/bin/python public_benchmark/extended_benchmark/yun_full/vergleich_20261116.py

# Ergebnis-Markdown neu erzeugen
.venv/bin/python public_benchmark/extended_benchmark/yun_full/ergebnisse_md.py

# Einzelnen Lauf auswerten
.venv/bin/python public_benchmark/extended_benchmark/yun_full/auswerte_yun699.py \
    --run yun20_8000_glm_cb_20261116 --out /tmp/auswertung.json

# Uebergabeordner neu bauen
.venv/bin/python public_benchmark/extended_benchmark/yun_full/baue_handoff.py
```

Die Rohantworten der Laeufe enthalten keinen Volltext-Prompt (nur mit
`--save-content`), aber `content_len`, `finish_reason`, `completion_tokens` und
die geparsten Zellen, sodass jede Kennzahl aus den Dateien nachvollziehbar ist.
