# Pruefvermerk Gold (21.11.2026)

Offline erstellt, ohne Netzaufruf. Gold wurde **nicht** geaendert; der Vermerk
haelt nur fest, ob das Dokument die Goldbeschriftung stuetzt.

| Record | Verdikt |
|---|---|
| `yun2024:331` | `armtausch_bestaetigt` |
| `yun2024:334` | `armtausch_bestaetigt` |
| `yun2024:335` | `armtausch_bestaetigt` |
| `yun2024:336` | `armtausch_bestaetigt` |
| `yun2024:196` | `verdacht_widerlegt` |

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

### `yun2024:196` (PMC5360580.md)

- Kontext: intervention = `1 mg/day of Pls purified from scallop`, comparator = `placebo`
- Gold: intervention_group_size (intervention) = 24.0, comparator_group_size (comparator) = 24.0
- Verdikt: `verdacht_widerlegt`
- Notiz: Gold stammt aus Tabelle 2 (Woche 28, n = 24, Mittel 1.29/1.08); die Regel las Tabelle 1.

Belegstellen:

  - Zeile 8: `Variable            Pls group (n = 145)   Placebo group (n = 140)   P value[a](#)`
  - Zeile 82: `28               24     1.29        (0.04; 2.55)     24               1.08       (0.46; 1.70)     0.76`

## Folge

Bei den vier `PMC5617873`-Records sind die Arme im Dokument eindeutig anders
herum beschriftet als in Gold. Ein Gold-Fix waere eine Datenentscheidung und
bleibt offen; bis dahin zaehlen diese vier Zellen in jeder Regelbilanz als FP.
Bei `yun2024:196` ist Gold belegt, der Fehler liegt bei der Regel, die die
Kopfzeile von Tabelle 1 statt der Zeile aus Tabelle 2 liest.
