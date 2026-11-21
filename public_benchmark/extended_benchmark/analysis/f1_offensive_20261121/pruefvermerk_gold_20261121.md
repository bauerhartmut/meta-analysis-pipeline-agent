# Pruefvermerk Gold (21.11.2026)

Offline erstellt, ohne Netzaufruf. Gold wurde **nicht** geaendert; der Vermerk
haelt nur fest, ob das Dokument die Goldbeschriftung stuetzt.

| Record | Verdikt |
|---|---|
| `yun2024:331` | `armtausch_bestaetigt` |
| `yun2024:334` | `armtausch_bestaetigt` |
| `yun2024:335` | `armtausch_bestaetigt` |
| `yun2024:336` | `armtausch_bestaetigt` |
| `yun2024:345` | `gold_nicht_belegt` |
| `yun2024:196` | `gold_aus_subgruppentabelle` |

## Faelle

### `yun2024:331` (PMC5617873.md)

- Kontext: intervention = `Aripiprazole`, comparator = `Placbeo`
- Gold: intervention_group_size (intervention) = 45.0, comparator_group_size (comparator) = 47.0
- Verdikt: `armtausch_bestaetigt`
- Notiz: Drei Tabellenkoepfe nennen Placebo vor Aripiprazole; Gold fuehrt 45 als Intervention.

Belegstellen:

  - Zeile 6: `Placebo (n = 45)   Aripiprazole (n = 47)   Total (n = 92)`
  - Zeile 40: `Placebo (n = 45)            Aripiprazole (n = 47)   Difference or ratio (95% confidence interval) P value`
  - Zeile 93: `Placebo (n = 45)   Aripiprazole (n = 47)`

### `yun2024:334` (PMC5617873.md)

- Kontext: intervention = `Aripiprazole`, comparator = `Placbeo`
- Gold: intervention_group_size (intervention) = 45.0, comparator_group_size (comparator) = 47.0
- Verdikt: `armtausch_bestaetigt`
- Notiz: Gleiches Dokument wie 331, gleiche Zellwerte.

Belegstellen:

  - Zeile 6: `Placebo (n = 45)   Aripiprazole (n = 47)   Total (n = 92)`
  - Zeile 40: `Placebo (n = 45)            Aripiprazole (n = 47)   Difference or ratio (95% confidence interval) P value`
  - Zeile 93: `Placebo (n = 45)   Aripiprazole (n = 47)`

### `yun2024:335` (PMC5617873.md)

- Kontext: intervention = `Aripiprazole`, comparator = `Placbeo`
- Gold: intervention_group_size (intervention) = 45.0, comparator_group_size (comparator) = 47.0
- Verdikt: `armtausch_bestaetigt`
- Notiz: Gleiches Dokument wie 331, gleiche Zellwerte.

Belegstellen:

  - Zeile 6: `Placebo (n = 45)   Aripiprazole (n = 47)   Total (n = 92)`
  - Zeile 40: `Placebo (n = 45)            Aripiprazole (n = 47)   Difference or ratio (95% confidence interval) P value`
  - Zeile 93: `Placebo (n = 45)   Aripiprazole (n = 47)`

### `yun2024:336` (PMC5617873.md)

- Kontext: intervention = `Aripiprazole`, comparator = `Placbeo`
- Gold: intervention_group_size (intervention) = 45.0, comparator_group_size (comparator) = 47.0
- Verdikt: `armtausch_bestaetigt`
- Notiz: Gleiches Dokument wie 331, gleiche Zellwerte.

Belegstellen:

  - Zeile 6: `Placebo (n = 45)   Aripiprazole (n = 47)   Total (n = 92)`
  - Zeile 40: `Placebo (n = 45)            Aripiprazole (n = 47)   Difference or ratio (95% confidence interval) P value`
  - Zeile 93: `Placebo (n = 45)   Aripiprazole (n = 47)`

### `yun2024:345` (PMC5686687.md)

- Kontext: intervention = `Resveratrol`, comparator = `Placebo`
- Gold: intervention_group_size (intervention) = 22.0, comparator_group_size (comparator) = 22.0
- Verdikt: `gold_nicht_belegt`
- Notiz: Gold nennt Mittel 2.3 (SD 2.63, laut Record aus CI zurueckgerechnet). Im Dokument steht 2.3 nur als obere Grenze der Median-Differenz (Zeile 51: 0.75 (--1.6 to 2.3), Zeile 56: 0.35 (--2.3 to 2.8), Abstract Zeile 28 ebenso); die Baseline-Zeile 13 nennt 5.4 +/- 2.6 bzw. 5.7 +/- 2. Eine Mittelwertzelle mit 2.3 gibt es nicht.

Belegstellen:

  - Zeile 13: `Pain score (VAS)                              5.4 +/- 2.6               5.7 +/- 2               0.6 [*^e^*](#)`
  - Zeile 28: `Student *t* test.:::: ## B. Primary Outcome: Pain Score After 7 days of treatment, pain scores were significantly reduced in the resveratrol group, compared with the placebo group. After 42 days of tr`
  - Zeile 51: `Difference between medians (95% CI)             0.75 (--1.6 to 2.3)`
  - Zeile 56: `Difference between medians (95% CI)             0.35 (--2.3 to 2.8)`

### `yun2024:196` (PMC5360580.md)

- Kontext: intervention = `1 mg/day of Pls purified from scallop`, comparator = `placebo`
- Gold: intervention_group_size (intervention) = 24.0, comparator_group_size (comparator) = 24.0
- Verdikt: `gold_aus_subgruppentabelle`
- Notiz: Gold (n = 24, Mittel 1.29/1.08) steht in Tabelle 3, Woche 28; deren Kopf nennt die Subgruppe MMSE-J 20 bis 23. Die Haupttabelle 2 nennt fuer Woche 28 die Werte 80/78 (Mittel 2.30/2.46). Der Wert ist belegt, gehoert aber zur Subgruppe.

Belegstellen:

  - Zeile 8: `Variable            Pls group (n = 145)   Placebo group (n = 140)   P value[a](#)`
  - Zeile 65: `Mean difference from the baseline, in patients with MMSE-J score 20 to`
  - Zeile 82: `28               24     1.29        (0.04; 2.55)     24               1.08       (0.46; 1.70)     0.76`

## Folge

Bei den vier `PMC5617873`-Records sind die Arme im Dokument eindeutig anders
herum beschriftet als in Gold. Ein Gold-Fix waere eine Datenentscheidung und
bleibt offen; bis dahin zaehlen diese vier Zellen in jeder Regelbilanz als FP.
Bei `yun2024:196` ist Gold belegt, der Fehler liegt bei der Regel, die die
Kopfzeile von Tabelle 1 statt der Zeile aus Tabelle 2 liest.
