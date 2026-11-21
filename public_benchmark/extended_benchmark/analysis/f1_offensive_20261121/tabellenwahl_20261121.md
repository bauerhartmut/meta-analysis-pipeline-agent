# Tabellenwahl: Nachher-Tabelle vor Baseline-Tabelle (21.11.2026)

Offline, ohne Netzaufruf. `tabellenwahl_20261121.py`. Die Regel bewertet
Tabellenkoepfe (`+2` Follow-up/Zeitpunkt, `-2` Baseline) und zieht bei
gleichem Alias-Treffer in die Nachher-Tabelle um - aber nur, wenn diese
ihre Arme in der Unterschrift nennt (`I; n=104`).

## Die vier Records

| Record | Outcome | Felder | richtig alt | richtig neu | vollstaendig richtig neu |
|---|---|---:|---:|---:|---|
| `yun2024:196` | WMS-R (0 min) | 6 | 0 | 0 | nein |
| `yun2024:447` | effects for walking | 6 | 1 | 6 | ja |
| `yun2024:448` | effects for vigorous activity | 6 | 1 | 6 | ja |
| `yun2024:450` | weekly moderate physical activity sessions | 6 | 1 | 6 | ja |

### Zellen im Vergleich

| Record | Feld | alt | neu | Gold | neu richtig | Quelle neu |
|---|---|---:|---:|---:|---|---|
| `yun2024:196` | intervention_group_size | 80.0 | 80.0 | 24.0 | nein | position / Zeile 47 |
| `yun2024:196` | comparator_group_size | 78.0 | 78.0 | 24.0 | nein | position / Zeile 47 |
| `yun2024:196` | intervention_mean | - | - | 1.29 | nein | - / Zeile - |
| `yun2024:196` | comparator_mean | - | - | 1.08 | nein | - / Zeile - |
| `yun2024:196` | intervention_standard_deviation | - | - | 3.14 | nein | - / Zeile - |
| `yun2024:196` | comparator_standard_deviation | - | - | 1.55 | nein | - / Zeile - |
| `yun2024:447` | intervention_group_size | 114.0 | 104.0 | 104.0 | ja | unterschrift_n / Zeile 125 |
| `yun2024:447` | comparator_group_size | 114.0 | 114.0 | 114.0 | ja | unterschrift_n / Zeile 125 |
| `yun2024:447` | intervention_mean | 3.99 | -0.55 | -0.55 | ja | armzeile / Zeile 125 |
| `yun2024:447` | comparator_mean | 3.3 | 0.31 | 0.31 | ja | armzeile / Zeile 127 |
| `yun2024:447` | intervention_standard_deviation | 3.04 | 2.29 | 2.29 | ja | armzeile / Zeile 125 |
| `yun2024:447` | comparator_standard_deviation | 2.44 | 3.84 | 3.84 | ja | armzeile / Zeile 127 |
| `yun2024:448` | intervention_group_size | 114.0 | 104.0 | 104.0 | ja | unterschrift_n / Zeile 117 |
| `yun2024:448` | comparator_group_size | 114.0 | 114.0 | 114.0 | ja | unterschrift_n / Zeile 117 |
| `yun2024:448` | intervention_mean | 1.56 | 0.2 | 0.2 | ja | armzeile / Zeile 117 |
| `yun2024:448` | comparator_mean | 2.33 | -0.4 | -0.4 | ja | armzeile / Zeile 119 |
| `yun2024:448` | intervention_standard_deviation | 1.86 | 1.56 | 1.56 | ja | armzeile / Zeile 117 |
| `yun2024:448` | comparator_standard_deviation | 2.53 | 2.48 | 2.48 | ja | armzeile / Zeile 119 |
| `yun2024:450` | intervention_group_size | 114.0 | 104.0 | 104.0 | ja | unterschrift_n / Zeile 121 |
| `yun2024:450` | comparator_group_size | 114.0 | 114.0 | 114.0 | ja | unterschrift_n / Zeile 121 |
| `yun2024:450` | intervention_mean | 1.11 | 0.19 | 0.19 | ja | armzeile / Zeile 121 |
| `yun2024:450` | comparator_mean | 1.6 | -0.68 | -0.68 | ja | armzeile / Zeile 123 |
| `yun2024:450` | intervention_standard_deviation | 1.78 | 1.82 | 1.82 | ja | armzeile / Zeile 121 |
| `yun2024:450` | comparator_standard_deviation | 1.97 | 2.32 | 2.32 | ja | armzeile / Zeile 123 |

## Tabellen der Dokumente, einzeln gelesen

Jede Tabelle allein an die Regel gegeben; so wird sichtbar, welche Werte
in welcher Tabelle stehen.

### `yun2024:196`

| Zeile | Zeitpunkt | richtig | Tabellenkopf |
|---:|---:|---:|---|
| 1 | 2 | 0 | # Abstract ## Background Plasmalogens (Pls) reportedly decreased in postmortem brain and i |
| 2 | -2 | 0 | caption Baseline characteristics. |
| 6 | 0 | 0 | Table 1 Variable Pls group (n = 145) Placebo group (n = 140) P value[a](#) |
| 30 | 2 | 0 | caption Mean difference from the baseline. |
| 34 | 0 | 0 | Table 2 Variable Week Pls group Placebo group P value |
| 64 | 2 | 0 | caption Mean difference from the baseline, in patients with MMSE-J score 20 to 23. |
| 69 | 0 | 2 | Table 3 Variable Week Pls group Placebo group P value |
| 90 | 2 | 0 | caption Mean difference from the baseline, by gender and age, in patients with MMSE-J scor |
| 95 | 0 | 1 | Table 4 Gender/age Week Pls group Placebo group P value |
| 118 | 2 | 0 | caption Mean difference from the baseline, in patients with MMSE-J score 20 to 23. |
| 123 | 0 | 0 | Table 5 Variable Week Pls group Placebo group P value |
| 138 | 0 | 0 | caption List of reported adverse events. |
| 142 | 0 | 0 | Table 6 Pls group (n = 169) Placebo group (n = 167) |

### `yun2024:447`

| Zeile | Zeitpunkt | richtig | Tabellenkopf |
|---:|---:|---:|---|
| 1 | 2 | 0 | # Abstract ## Background Extending contact with participants after initial, intensive inte |
| 2 | -2 | 1 | caption Characteristics of 'Get Healthy, Stay Healthy' (GHSH) trial participants. |
| 94 | 2 | 6 | caption Mean changes within the 'Get Healthy, Stay Healthy' (GHSH) intervention group (I;  |
| 176 | 2 | 0 | caption Mean differences in changes between the 'Get Healthy, Stay Healthy' (GHSH) interve |

### `yun2024:448`

| Zeile | Zeitpunkt | richtig | Tabellenkopf |
|---:|---:|---:|---|
| 1 | 2 | 0 | # Abstract ## Background Extending contact with participants after initial, intensive inte |
| 2 | -2 | 1 | caption Characteristics of 'Get Healthy, Stay Healthy' (GHSH) trial participants. |
| 94 | 2 | 6 | caption Mean changes within the 'Get Healthy, Stay Healthy' (GHSH) intervention group (I;  |
| 176 | 2 | 0 | caption Mean differences in changes between the 'Get Healthy, Stay Healthy' (GHSH) interve |

### `yun2024:450`

| Zeile | Zeitpunkt | richtig | Tabellenkopf |
|---:|---:|---:|---|
| 1 | 2 | 0 | # Abstract ## Background Extending contact with participants after initial, intensive inte |
| 2 | -2 | 1 | caption Characteristics of 'Get Healthy, Stay Healthy' (GHSH) trial participants. |
| 94 | 2 | 6 | caption Mean changes within the 'Get Healthy, Stay Healthy' (GHSH) intervention group (I;  |
| 176 | 2 | 0 | caption Mean differences in changes between the 'Get Healthy, Stay Healthy' (GHSH) interve |

## Zellstand der 295 Faelle

| Stand | Zellen | TP | FP | Streuung Zellen | Streuung TP | Streuung FP |
|---|---:|---:|---:|---:|---:|---:|
| alt | 33 | 30 | 3 | 17 | 17 | 0 |
| neu | 33 | 30 | 3 | 17 | 17 | 0 |
| ohne_zeitpunkt | 33 | 30 | 3 | 17 | 17 | 0 |
| ohne_armbedingung | 33 | 18 | 15 | 17 | 5 | 12 |
| ohne_armzeile | 33 | 30 | 3 | 17 | 17 | 0 |
| ohne_vorzeichen | 33 | 30 | 3 | 17 | 17 | 0 |
| ohne_sd_ki | 33 | 30 | 3 | 17 | 17 | 0 |

Zellunterschiede: 0 hinzu, 0 entfallen, 0 kippen. Streuung: 0 hinzu, 0 entfaellt, 0 kippen.

## P5-Pool

| Stand | k | pooled | 95 %-KI | I2 |
|---|---:|---:|---|---:|
| p5 | 24 | 0.125 | -0.302 bis 0.551 | 91.1 |
| alt | 24 | 0.125 | -0.302 bis 0.551 | 91.1 |
| neu | 27 | 0.136 | -0.226 bis 0.499 | 90.4 |

## Grenzen

- Die Streuung der drei Records ist nicht gedruckt. Sie faellt aus dem
  95%-KI (`SE = halbe Breite / 1.96`, `SD = SE * sqrt(n)`) und ist damit
  eine Ableitung, kein abgelesener Wert.
- Das Kriterium zieht nur in eine Nachher-Tabelle um, die ihre Arme selbst
  benennt. Ohne diese Bedingung steht der Zellstand bei 33 Zellen / 18 TP / 15 FP und die Streuung bei 17 Zellen / 5 TP: der Umzug gewinnt dann eine
  Aenderungstabelle gegen die Tabelle mit den Absolutwerten
  (`PMC4987981`: Gold steht in der Baseline-Tabelle).
- `yun2024:196` bleibt falsch: die Tabelle mit den Goldwerten ist eine
  Subgruppentabelle (MMSE-J 20 bis 23), und diese Einschraenkung steht
  nicht im Record-Kontext. Auch allein gelesen liefert sie nur die beiden
  Mittel (2 von 6 Feldern); Groesse und Streuung brauchen die Zeilen-n
  und das KI dieser Tabelle.
