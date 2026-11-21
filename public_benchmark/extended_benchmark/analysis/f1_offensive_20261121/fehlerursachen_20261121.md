# Fehlerursachen des Hybrids (21.11.2026)

Basis: 699 Records, 2.014 Goldzellen. Hybrid wie in `vergleiche_20261120.py`
(GLM auf 596, P5 auf 102), Bilanzlogik aus demselben Modul importiert.

| Kennzahl | Wert |
|---|---:|
| TP | 2014 |
| FP | 507 |
| FN | 759 |
| Records ohne eine einzige Zelle | 73 |

## FN (verpasste Goldzellen)

| Kategorie | Regel | Anzahl | Anteil |
|---|---|---:|---:|
| Wert erkannt, falsch gebunden (anderer Wert ausgegeben) | `fn_wert_ersetzt` | 286 | 37.7 % |
| leere Modellausgabe | `fn_leer` | 182 | 24.0 % |
| Wert nicht im Prompt (Abdeckung) | `fn_nicht_im_prompt` | 173 | 22.8 % |
| Wert im Prompt, nicht ausgegeben | `fn_nicht_ausgegeben` | 118 | 15.6 % |

## FP (ueberzaehlige Vorhersagezellen)

| Kategorie | Regel | Anzahl | Anteil |
|---|---|---:|---:|
| Wert erkannt, falsch gebunden | `fp_gebunden` | 264 | 52.1 % |
| falsches Outcome | `fp_outcome` | 157 | 31.0 % |
| falsche Einheit (Faktor 10/100/1000) | `fp_einheit` | 40 | 7.9 % |
| Zahl nicht im Prompt | `fp_halluzination` | 22 | 4.3 % |
| falscher Zeitpunkt (Baseline- oder Aenderungswert) | `fp_zeitpunkt` | 19 | 3.8 % |
| doppelte Zelle | `fp_dublette` | 4 | 0.8 % |
| falsches Feld | `fp_feld` | 1 | 0.2 % |

## Regeln und Grenzen

Die Regeln greifen in dieser Reihenfolge, die erste zutreffende gewinnt:

FN: `fn_leer` (Record ohne Zelle) → `fn_nicht_im_prompt` (Zahl fehlt im
45.000-Zeichen-Fenster) → `fn_mehrdeutig` (gleiche Zahl in mehreren
Goldzellen desselben Records oder derselben Publikation) → `fn_wert_ersetzt`
(gleicher Schluessel, anderer Wert ausgegeben) → `fn_nicht_ausgegeben`.

FP: `fp_dublette` (zweite Zelle je Feld und Arm) → `fp_arm` (Wert ist
Goldwert des anderen Arms) → `fp_feld` (Wert gehoert zu einem anderen Feld
des Records) → `fp_einheit` (Faktor 10/100/1000 zum Goldwert) →
`fp_halluzination` (Zahl fehlt im Fenster) → `fp_outcome` (Wert ist Goldwert
eines anderen Records derselben Publikation) → `fp_gebunden`.

Grenzen: Die Zuordnung ist eine Text- und Zahlenheuristik, keine Rekonstruktion
der Modellabsicht. `fp_zeitpunkt` ist definiert, aber nicht vergeben, weil das
Gold in diesen Records keinen Zeitpunkt traegt (fast ueberall `null`) und sich
Zeitpunktfehler damit nicht belegen lassen. `fn_mehrdeutig` markiert gleiche
Zahlen, nicht bewiesene Goldfehler. Die Kategorien sind exklusiv; ein Wert,
der sowohl im falschen Arm als auch am falschen Feld steht, zaehlt beim Arm.

## Beispiele

**leere Modellausgabe** (`fn_leer`)

- `yun2024:119` intervention_group_size/intervention = 10.0 — Position 2314
- `yun2024:119` intervention_mean/intervention = 70.0 — Position 1348
- `yun2024:119` comparator_group_size/comparator = 13.0 — Position 2144

**Wert nicht im Prompt (Abdeckung)** (`fn_nicht_im_prompt`)

- `yun2024:10` intervention_group_size/intervention = 20.0 — Zahl steht im Prompt-Text nicht
- `yun2024:10` comparator_group_size/comparator = 20.0 — Zahl steht im Prompt-Text nicht
- `yun2024:11` intervention_group_size/intervention = 20.0 — Zahl steht im Prompt-Text nicht

**Wert erkannt, falsch gebunden (anderer Wert ausgegeben)** (`fn_wert_ersetzt`)

- `yun2024:100` intervention_group_size/intervention = 40.0 — Position 1169; ausgegeben 453.0 statt 40.0
- `yun2024:100` comparator_group_size/comparator = 37.0 — Position 1141; ausgegeben 451.0 statt 37.0
- `yun2024:110` intervention_group_size/intervention = 459.0 — Position 1304; ausgegeben 456.0 statt 459.0

**Wert im Prompt, nicht ausgegeben** (`fn_nicht_ausgegeben`)

- `yun2024:10` comparator_events/comparator = 5.0 — Position 785
- `yun2024:114` comparator_standard_deviation/comparator = 1.67 — Position 33599
- `yun2024:116` comparator_mean/comparator = 70.0 — Position 1348

**falsches Feld** (`fp_feld`)

- `yun2024:370` intervention_events/intervention = 59.0 — 59.0 ist Goldwert eines anderen Feldes im selben Arm

**falsches Outcome** (`fp_outcome`)

- `yun2024:110` intervention_group_size/intervention = 456.0 — gleicher Wert Gold in: yun2024:111, yun2024:112, yun2024:113, yun2024:114, yun2024:115
- `yun2024:111` intervention_group_size/intervention = 459.0 — gleicher Wert Gold in: yun2024:110
- `yun2024:112` intervention_group_size/intervention = 459.0 — gleicher Wert Gold in: yun2024:110

**doppelte Zelle** (`fp_dublette`)

- `yun2024:151` intervention_mean/intervention = 17310.0 — 2. Zelle fuer intervention_mean/intervention
- `yun2024:174` intervention_group_size/intervention = 16.0 — 2. Zelle fuer intervention_group_size/intervention
- `yun2024:174` intervention_events/intervention = 4.0 — 2. Zelle fuer intervention_events/intervention

**falsche Einheit (Faktor 10/100/1000)** (`fp_einheit`)

- `yun2024:1` intervention_events/intervention = 14.2 — intervention_events verlangt eine ganze Zahl, ausgegeben 14.2 (Rate oder Prozent)
- `yun2024:1` comparator_events/comparator = 15.7 — comparator_events verlangt eine ganze Zahl, ausgegeben 15.7 (Rate oder Prozent)
- `yun2024:150` intervention_mean/intervention = 0.3 — 0.3 = Goldwert x 100

**Zahl nicht im Prompt** (`fp_halluzination`)

- `yun2024:112` comparator_mean/comparator = 164.3 — 164.3 steht im Prompt-Text nicht
- `yun2024:151` intervention_mean/intervention = 11609.0 — 11609.0 steht im Prompt-Text nicht
- `yun2024:151` comparator_mean/comparator = 18177.0 — 18177.0 steht im Prompt-Text nicht

**Wert erkannt, falsch gebunden** (`fp_gebunden`)

- `yun2024:100` intervention_group_size/intervention = 453.0 — Position 10314, keine Goldzelle dazu
- `yun2024:100` comparator_group_size/comparator = 451.0 — Position 10302, keine Goldzelle dazu
- `yun2024:110` intervention_mean/intervention = 2.42 — Position 19409, keine Goldzelle dazu

**falscher Zeitpunkt (Baseline- oder Aenderungswert)** (`fp_zeitpunkt`)

- `yun2024:187` intervention_mean/intervention = 49.0 — Position 6924, im Umfeld steht ein Baseline- oder Aenderungswort
- `yun2024:22` intervention_mean/intervention = 44.33 — Position 6787, im Umfeld steht ein Baseline- oder Aenderungswort
- `yun2024:267` comparator_mean/comparator = 13.1 — Position 1311, im Umfeld steht ein Baseline- oder Aenderungswort

