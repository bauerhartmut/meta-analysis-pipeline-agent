# Sprint 48: Validierungs-Finding "Kopf-n widerspricht Kontext"

**Entscheidung:** Der Record-Kontext bleibt die massgebliche Armquelle. Die
kopf-treue Variante (gedrucktes n schlaegt Kontext) wird nicht eingefuehrt;
stattdessen sind die beiden Alias-Zuordnungen (Control -> PBO,
Definition -> IPAT) Teil des Kontexts und heben drei Zellen: **97 Feldtreffer,
71 nicht widerlegt**.

## 1. Was das Finding prueft

`validate_arm_context(table, context)` in
`research_agent/table_decomposition/validation.py`, aufgerufen in
`run_benchmark.py` direkt nach `validate(...)`. Es haengt nichts um und
schreibt kein Gold; es meldet nur, wenn der gedruckte n-Kopf nicht zu den
Kontextarmen passt:

| Code | Bedingung | Severity |
|---|---|---|
| `kopf_n_widerspricht_kontext` | Ein Kontextarm ist im Kopf auffindbar, traegt dort aber kein n, waehrend eine andere Gruppe eins druckt | warning |
| `kontextarm_nicht_im_kopf` | Ein Kontextarm ist im Kopf gar nicht auffindbar, waehrend eine andere Gruppe ein n druckt | warning |

Abgleich ueber Wortueberschneidung (normalisiert) plus die Rollenwoerter
`intervention`, `comparator`/`control`. `placebo` ist bewusst **kein**
Rollenwort, damit ein Tippfehler wie `Placbeo` sichtbar bleibt.

## 2. Ergebnis auf der Plan-Auswahl (59 Records, offline)

15 Befunde in 10 Record-Paaren:

| Record | Code | Kontext vs Kopf |
|---|---|---|
| `yun2024:15`, `:16` | `kontextarm_nicht_im_kopf` (info) | comparator-Beschreibung "full course of therapy in the hospital setting"; n steht auf `CoPAT (n = 103)`, `IPAT (n = 97)` |
| `yun2024:30` | `kontextarm_nicht_im_kopf` (warning) | comparator "Control" nicht im Kopf; n steht auf `CZP 200 mg + MTX` (393), `CZP 400 mg + MTX` (390), `PBO + MTX` (199) |
| `yun2024:78`, `:79` | `kontextarm_nicht_im_kopf` (warning) | comparator "baseline" nicht im Kopf; n steht auf `Placebo, n = 4`, `Palmvitee, n = 3`, ... |
| `yun2024:111`, `:112` | `kontextarm_nicht_im_kopf` (info) | intervention-Beschreibung; n steht auf `Control` (434), `Basic` |
| `yun2024:184`, `:185` | `kontextarm_nicht_im_kopf` (info) | intervention "Digestion-resistant maltodextrin" nicht im Kopf; n steht auf `Placebo (n = 33)`, `RMD` |
| `yun2024:335`, `:336` | `kontextarm_nicht_im_kopf` (warning) | comparator "Placbeo" (Tippfehler) nicht im Kopf; n steht auf `Placebo (n = 45)`, `Aripiprazole (n = 47)` |
| `yun2024:678`, `:682` | `kopf_n_widerspricht_kontext` (warning) | comparator "placebo" traegt kein n; n steht auf `Probiotic group` (16), `Antibiotic group` (15) |
| `yun2024:390`, `:391` | `kontextarm_nicht_im_kopf` (info) | intervention-Beschreibung "trabecular metal tibial monoblock component"; n steht auf `Cemented` (24), `Cementless` |

**Unauffaellig:** `yun2024:426` - Kontext (open MR / short-bore) und Kopf
(Open n = 21/34, Short-Bore n = 18/30) passen zusammen; der Fehler dort ist
die P-Wert-Spalte und die fehlende Open-Zuordnung, kein Kopf-Kontext-Konflikt.

## 3. Grenzen

- Das Finding misst Namens- und n-Praesenz, nicht die Richtigkeit der
  Zuordnung: ein Kopf, der beide Arme mit n nennt, aber vertauscht, bleibt
  unauffaellig.
- Es ist ein Pruefauftrag, keine Korrektur. Die Arme werden nicht umgehaengt.
- `structure.json` wurde **nicht** neu erzeugt. Der naechste Benchmark-Lauf
  zaehlt 7 Warnungen mit (Strategie A: 137 plus rund 7); die 8 Hinweise
  erhoehen die Warnzaehlung nicht.

## 4. Vereinfachung nach frischem Blick

- **Bandauswahl fuer die Meldung.** Vorher nahm `next(...)` das erste Band mit
  n und meldete bei 78/79 das Rasterband `S1`. Jetzt sammelt `_baender_mit_n`
  nur Gruppenbaender (Wort mit mindestens drei Buchstaben, Raster-, Perioden-,
  Mittelwert- und Total-Labels sind Stopwoerter) und die Meldung nennt bis zu
  drei davon mit Wert. Bei 678 steht dort `Probiotic group` (16) und
  `Antibiotic group` (15), bei 78 `Placebo, n = 4` statt `S1`.
- **Eine Meldung, ein Helfer.** `_n_hinweis` ersetzt die 3-fach wiederholte
  Bandschleife; `_band_traegt_n` ist entfallen.
- **Fallunterscheidung wiederhergestellt.** Ein gefundenes Band ohne n
  (`kopf_n_widerspricht_kontext`) ist etwas anderes als ein fehlendes Band
  (`kontextarm_nicht_im_kopf`); die erste Vereinfachung hatte beides
  zusammengelegt und 678 falsch als "nicht auffindbar" gemeldet.
- **Beschreibungen sind Hinweise.** Ist der Kontextarm laenger als zwei Woerter,
  wird daraus `info` statt `warning`; ein Name wie `Placbeo` bleibt Warnung.

## 5. Die drei zuerst geprueften Konflikte

### yun2024:30

Kontext comparator "Control"; im Kopf stehen `CZP 200 mg + MTX` (393,
intervention), `CZP 400 mg + MTX` (390, ohne Arm) und `PBO + MTX` (199, ohne
Arm). Gold verlangt comparator 199. Das ist **kein Widerspruch, sondern eine
Alias-Luecke**: "Control" ist die Placebo-Gruppe. Wuerde `Control` auf
`PBO + MTX` abgebildet, waere 199 als comparator wertrichtig - eine Zelle
mehr. Die 68 bleiben unberuehrt, weil nichts umgebaut wurde.

### yun2024:15 und :16

Kontext comparator ist eine Definition ("full course of therapy in the hospital
setting"), im Kopf steht `IPAT (*n* = 97)`; Gold verlangt comparator 97. Auch
hier eine **Alias-Luecke** (IPAT = stationaere Therapie), kein Zahlenkonflikt:
mit der Abbildung Definition -> IPAT waere 97 je Record wertrichtig, also zwei
Zellen mehr. Zusammen mit 30 sind das drei Zellen (68 -> 71), gemessen in
`sprint48_alias_20261119.md`, ohne neue Netzkosten.

### yun2024:78 und :79

Kontext comparator "baseline", im Kopf stehen Perioden-Spalten `S1`/`S2`/`S3`
mit Placebo- und Palmvitee-n. Kein Armkonflikt, sondern ein Periodenraster; die
Meldung nennt jetzt die Gruppen statt `S1`. Die urspruengliche Abweichung
(30 gegen 3+19+8) bleibt eine Untergruppen-Frage aus der Ursachenliste.
