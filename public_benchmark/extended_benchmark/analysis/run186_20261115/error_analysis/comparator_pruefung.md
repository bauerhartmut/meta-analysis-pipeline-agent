# Comparator-Feld gegen Gold: Prüfung am Artikel (16.11.2026, read-only)

Frage: Ist bei `yun2024:289`–`295` das Comparator-Feld (`"baseline"`) falsch oder
das Gold (TAU zum Post-Zeitpunkt)? Danach: dieselbe Prüfung für alle Records mit
unklarem Comparator-Feld.

Die eingefrorene Testbasis wurde **nicht** geändert.

## 1. Verdikt für 289–295: das Comparator-Feld ist falsch, das Gold richtig

**a) Das Paper hat drei Arme, nicht einen Arm mit Baseline.** Abstract
(PMC4215531):

> In the present study, 57 schizophrenia patients were randomly assigned to (a)
> computer-based facial affect training …, (b) similarly intense, targeted
> cognitive training …, or (c) treatment as usual.

**b) Die Tabelle führt Arme und Zeitpunkte getrennt.** Caption und Fußnote:

> MATRICS consensus cognitive battery (MCCB) test scores (means ± standard
> deviation of normative *T*-scores) for the seven MCCB domains before (pre) and
> after (post) intervention period for the three schizophrenia patients group
> (*n* = 19 per group).

> FAT: facial affect training, CE: cognitive exercise, TAU: treatment as usual; …
> pre: before intervention onset; post: after 4-week intervention period

Damit gibt es keinen Arm „baseline“ — „pre“ ist eine Zeile *innerhalb* jedes
Arms. Die Zeilen lauten `FAT Pre`, `FAT Post`, `CE Pre`, `CE Post`, `TAU Pre`,
`TAU Post`; die Spalten sind in dieser Reihenfolge: Processing speed,
Attentional vigilance, Working memory, Verbal learning, Visual learning,
Reasoning, Social cognition, Overall composite.

**c) Das Gold liegt exakt in der TAU-Post-Zeile.** Auszug aus der Tabelle:

```
FAT Post  44.6 ± 12.2  38.5 ± 11.8  48.2 ± 9.2  47.1 ± 10.0  49.4 ± 14.0  47.9 ± 8.8  39.3 ± 10.4  41.6 ± 11.5
TAU Post  48.2 ± 12.3  41.3 ± 10.1  50.8 ± 12.1  47.3 ± 10.4  46.5 ± 9.8   45.4 ± 7.7  42.8 ± 11.7  43.3 ± 10.8
```

| Record | Outcome (Spalte) | Gold Intervention | Gold Komparator | Zeile |
|---|---|---|---|---|
| 289 | Processing speed | 44,6 ± 12,2 | 48,2 ± 12,3 | FAT Post / TAU Post |
| 290 | Attentional vigilance | 38,5 ± 11,8 | 41,3 ± 10,1 | FAT Post / TAU Post |
| 291 | Visual learning | 49,4 ± 12,8 | 46,5 ± 9,8 | FAT Post / TAU Post |
| 292 | Working memory | 48,2 ± 9,2 | 50,8 ± 12,1 | FAT Post / TAU Post |
| 293 | Verbal learning | 47,1 ± 10,0 | 47,3 ± 10,4 | FAT Post / TAU Post |
| 294 | Reasoning | 47,9 ± 8,8 | 46,5 ± 9,8 | FAT Post / **TAU Spalte 5** |
| 295 | Social cognition | 39,3 ± 10,4 | 42,8 ± 11,7 | FAT Post / TAU Post |

Alle sieben Komparatorwerte stehen in der Zeile `TAU Post`, alle sieben
Interventionswerte in `FAT Post`. Die Pre-Werte desselben Arms (FAT Pre:
39,5 ± 10,6 …) kommen im Gold nirgends vor. **Das Gold beschreibt also einen
Zwischenarm-Vergleich FAT gegen TAU zum Post-Zeitpunkt; das Feld „baseline“
behauptet dagegen einen Vorher-Nachher-Vergleich innerhalb eines Arms.**

Ergebnis: Das Feld ist falsch (richtig wäre „treatment as usual (TAU)“), das
Gold ist in der Armzuordnung richtig. Die Modellantworten (`FAT Pre`) sind genau
die Werte, die das Feld verlangt — der Fehler liegt in der Vorgabe.

## 2. Zusatzbefund: zwei Gold-Zellen passen nicht in ihre Spalte

Beim Spaltenvergleich fallen zwei Zellen auf, unabhängig vom Comparator-Feld:

* `yun2024:291` (Visual learning): Gold-SD 12,8 — die Zeile `FAT Post` nennt
  **49,4 ± 14,0**. Die 12,8 ist der SD des **Pre**-Werts derselben Spalte
  (FAT Pre: 42,8 ± 12,8). Mittelwert aus Post, SD aus Pre.
* `yun2024:294` (Reasoning): Gold-Komparator 46,5 ± 9,8 — das ist **Spalte 5
  (Visual learning)** der Zeile `TAU Post`. Die Reasoning-Spalte (6) lautet
  45,4 ± 7,7. Der Interventionswert 47,9 ± 8,8 ist dagegen die richtige
  Reasoning-Spalte.

Beide sind Gold-Kandidaten derselben Klasse wie `yun2024:479`, aber **nicht
geändert**. Sie erklären einen Teil der verbleibenden Abweichungen: das Modell
nannte für 291 die 14,0 und lag damit am Artikel richtig.

## 3. Alle Records mit unklarem Comparator-Feld

Populationsdefinition: Comparator-Feld nennt **keinen Vergleichsarm und keine
Vergleichsbedingung**, sondern einen Zeitpunkt oder eine Phase. Von den 76
Records sind das 11; alle übrigen Felder nennen Arme, Substanzen oder
Bedingungen (`Control`, `Placebo`, `paracetamol …`, `H2 (haloperidol 1 mg)`,
`P group` …).

| Record(s) | Comparator-Feld | Erwartung | Belegstelle | Widerspruch |
|---|---|---|---|---|
| 289–295 (7) | `baseline` | kein Arm, sondern Zeitpunkt | Tabelle: `TAU Post` 48,2 / 41,3 / 46,5 / 50,8 / 47,3 / 46,5 / 42,8 | **ja** — Gold nutzt TAU |
| 51–54 (4) | `Before restraint reduction program` | Phase vor der Intervention | Tabelle: „Preintervention phase / Postintervention phase, n = 463 / n = 562“; „from 11.5% to 13.6%“; „better knowledge after intervention (5.51 versus 6.23)“ | **nein** — Gold nutzt 463 und die Pre-Werte |

Für 51–54 passt das Gold zum Feld: `comparator_group_size` 463 = Preintervention,
`comparator_mean` 10,8 / 11,5 / 0,7 / 5,51 = die Vorher-Werte; die
Interventionsseite ist mit 562 und den Nachher-Werten belegt. Das Feld ist dort
zwar kein Arm, aber ein sauberer Vorher-Nachher-Vergleich — kein Widerspruch.

## 4. Konsequenz

* Für 289–295 ist die Vorgabe zu korrigieren, nicht das Gold: `comparator` sollte
  „treatment as usual (TAU)“ heißen. Das ist eine Änderung am Kontext der
  eingefrorenen Records und braucht deshalb Version 3 samt neuem Hash — wie bei
  `yun2024:479`.
* Die 14 Komparatorzellen sind nach dieser Prüfung **keine Modellfehler**,
  sondern Folgen einer falschen Vorgabe. In den Kennzahlen des Hauptlaufs zählen
  sie weiter als falsch, weil das Gold der Maßstab bleibt.
* Zusätzlich zwei Gold-Kandidaten (291 SD, 294 Komparator), die in dieselbe
  Korrekturrunde gehören.

## Grenzen

* Geprüft sind die 11 Records mit nicht-armigem Comparator-Feld. Felder, die
  einen Arm nennen, wurden nicht systematisch gegen die Artikelspalte geprüft —
  dort ist derselbe Fehler möglich.
* Die Spaltenzuordnung folgt der Tabellen-Kopfzeile; bei gefalteten Tabellen
  wäre eine Verschiebung um eine Spalte denkbar. Für 289–295 passt sie in sechs
  von sieben Records auf Anhieb, was die Zuordnung stützt.
* Ob das Original-Dataset mit „baseline“ bewusst einen Vorher-Nachher-Vergleich
  modellieren wollte, lässt sich aus dem Record nicht entscheiden; das Gold
  widerspricht dieser Lesart aber in allen sieben Fällen.
