# `yun2024:75`: Gold mischt Arme und Zeitpunkte (15.11.2026)

Der Record gehört zur B-Lymphozyten-Tabelle („The percentage of B cells") in
PMC4374278, Zielzeitpunkt `week 24`. Die Tabelle führt zwei Blöcke, je mit den
Zeilen `0`, `12`, `24`:

| Block | Zeile | B-Zellen (%) |
|---|---|---|
| Non-smokers (**placebo**, n = 27) | 0 | 10.19 ± 4.06 |
| | 12 | 10.89 ± 3.56 |
| | 24 | **11.00 ± 3.88** |
| Non-smokers (**palmvitee**, n = 29) | 0 | **11.97 ± 4.00** |
| | 12 | 12.45 ± 4.67 |
| | 24 | **13.72 ± 4.53** |

## Was Gold trägt

| Feld | Gold | Herkunft im Artikel |
|---|---|---|
| `intervention_group_size` | 29 | palmvitee-Block |
| `intervention_mean` | **11.97** | palmvitee, **Zeile 0** |
| `intervention_standard_deviation` | 4.00 | palmvitee, Zeile 0 |
| `comparator_group_size` | **29** | palmvitee-Block |
| `comparator_mean` | **13.72** | palmvitee, **Zeile 24** |
| `comparator_standard_deviation` | 4.53 | palmvitee, Zeile 24 |

Gold paart damit **palmvitee-Baseline** (Intervention) mit **palmvitee-Woche-24**
(Komparator) und trägt im Komparator die palmvitee-Gruppengröße (n = 29) statt
der Placebogröße (n = 27). Der Placebo-Arm kommt im Gold nicht vor, obwohl das
Ziel `week 24` ist und dort 11.00 ± 3.88 bereitsteht.

## Was das Modell liefert (`yun_test186_v6_20261115`)

| Feld | Modell | Zeitpunkt |
|---|---|---|
| `intervention_group_size` | 29 | `24` |
| `intervention_mean` | 13.72 | `24` |
| `intervention_standard_deviation` | 4.53 | `24` |
| `comparator_group_size` | 29 | `0` |
| `comparator_mean` | 11.97 | `0` |
| `comparator_standard_deviation` | 4.00 | `0` |

`timepoints.chosen = 24`, verworfen `0` und `12`.

Die Zahlen sind wörtlich belegt und für die palmvitee-Zeile richtig: 13.72 bei
Woche 24, 11.97 bei Woche 0. Gegenüber Gold sind die Arme aber vertauscht, und
der Komparator steht auf einem anderen Zeitpunkt — genau die Armdivergenz, die
`arme_gemischt()` erkennt.

## Warum das ein Gold-Konflikt ist und kein Modellfehler

Beide Zahlen und beide Zeitpunkte stehen im Artikel, aber keine konsistente
Lesart erzeugt das Goldpaar: Ein armtreuer Week-24-Schnitt wäre
Intervention 13.72 (palmvitee) und Komparator 11.00 (placebo, n = 27). Gold
enthält 11.97, das ausschließlich in Zeile 0 des palmvitee-Blocks steht. Damit
ist `intervention_mean = 11.97` bei Ziel `week 24` im Artikel nicht belegbar,
und `comparator_mean = 13.72` gehört nachweislich zum palmvitee-Arm.

## Entscheidung

* **Gold bleibt unverändert** — keine Zahl wird korrigiert, der Record bleibt im
  Benchmark.
* Beide Mittelwert- und beide Streuungszellen sind in
  `analyze_errors.GEPRUEFTE_FAELLE` als **Klasse 5** („Interventions-/
  Kontrollgruppe verwechselt") mit Quelle eingetragen; `MANUELLE_GOLD_HINWEISE`
  nennt den Fall zusätzlich.
* In der Auswertung wird `yun2024:75` als `arm_gemischt` geführt. Ein Fehltreffer
  des Modells an dieser Stelle ist nicht als Modellfehler zu lesen.

## Folge für die Auswertung

Der Fall zählt doppelt gegen das Modell, obwohl es die Tabelle richtig gelesen
hat: einmal als falscher Zahlenwert (`intervention_mean` 13.72 gegen 11.97) und
einmal als falscher Zeitpunkt (Komparator `0` gegen `week 24`). Bei der
Fehlerquote ist er deshalb getrennt auszuweisen. Für die zweite Kohorte sollte
vor dem Start geprüft werden, ob weitere Records aus derselben Tabelle dieselbe
Mischung tragen.
