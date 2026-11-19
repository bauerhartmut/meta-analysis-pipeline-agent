# Sprint 48: Validierungs-Finding "Kopf-n widerspricht Kontext"

**Entscheidung:** Der Record-Kontext bleibt die massgebliche Armquelle. Die
68 von 94 Feldtreffern sind damit die **endgueltige Obergrenze**; die
kopf-treue Variante (gedrucktes n schlaegt Kontext) wird nicht eingefuehrt.

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

13 Befunde in 8 Record-Paaren:

| Record | Code | Kontext vs Kopf |
|---|---|---|
| `yun2024:15`, `:16` | `kopf_n_widerspricht_kontext` | comparator "full course of therapy in the hospital setting"; n steht auf `CoPAT (n = 103)` |
| `yun2024:30` | `kontextarm_nicht_im_kopf` | comparator "Control" nicht im Kopf; n steht auf `CZP 200 mg + MTX` |
| `yun2024:78`, `:79` | `kontextarm_nicht_im_kopf` | comparator "baseline" nicht im Kopf; n steht auf `S1` |
| `yun2024:111`, `:112` | `kontextarm_nicht_im_kopf` | intervention "Intervention + targeting environmental-level factors"; n steht auf `Total` |
| `yun2024:184`, `:185` | `kontextarm_nicht_im_kopf` | intervention "Digestion-resistant maltodextrin" nicht im Kopf |
| `yun2024:335`, `:336` | `kontextarm_nicht_im_kopf` | comparator "Placbeo" (Tippfehler) nicht im Kopf; n steht auf `Placebo (n = 45)` |
| `yun2024:678`, `:682` | `kopf_n_widerspricht_kontext` | comparator "placebo" traegt kein n, `Probiotic group` druckt eins |

**Unauffaellig:** `yun2024:426` - Kontext (open MR / short-bore) und Kopf
(Open n = 21/34, Short-Bore n = 18/30) passen zusammen; der Fehler dort ist
die P-Wert-Spalte und die fehlende Open-Zuordnung, kein Kopf-Kontext-Konflikt.

## 3. Grenzen

- Das Finding misst Namens- und n-Praesenz, nicht die Richtigkeit der
  Zuordnung: ein Kopf, der beide Arme mit n nennt, aber vertauscht, bleibt
  unauffaellig.
- Es ist ein Pruefauftrag, keine Korrektur. Die Arme werden nicht umgehaengt.
- `structure.json` wurde **nicht** neu erzeugt. Der naechste Benchmark-Lauf
  zaehlt die Befunde als Warnungen mit (Strategie A: 137 plus rund 13).
