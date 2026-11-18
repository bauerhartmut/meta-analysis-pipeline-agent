# Sprint 48 - Zahlen aus dem Fliesstext als Fundstelle

Stand 18.11.2026. Offline, rein lesend: kein Modelllauf, kein Netz, Gold und
eingefrorene Auswahl unveraendert. Zahlen aus `messung.json` (Skript
`diagnose_fliesstext.py`, zwei Laeufe identisch).

## Frage

Werden die fuenf noch offenen `population_mismatch`-Felder erreichbar und
wertgleich, wenn der gedruckte Fliesstext als Fundstelle zaehlt - ohne
Armumkehr und ohne Gold in der Regel?

## Regel (`research_agent/table_decomposition/fliesstext.py`)

Drei gedruckte Formen, jede mit eigenem Beleg:

1. **Label, n = X** - der Arm steht unmittelbar an der Zahl:
   `(placebo, n = 28; RMD, n = 29)` (PMC5122613).
2. **Zahlenliste + Armliste + "respectively"**, nur mit genannter Population:
   `(283, 289, and 204 patients received quetiapine 300 mg/day, quetiapine
   600 mg/day, or placebo, respectively)` (PMC4230312, ITT) und dieselbe Form
   fuer die Safety-Population (298, 307, 214). Die Population steht in der
   Regel (`:itt`, `:sicherheit`).
3. **Bruchliste + Armliste + "respectively"**: `5.1% (4/79), 3.6% (3/83), and
   5.0% (4/80) in the placebo, 30 µg YIC and 60 µg YIC groups respectively`
   (PMC2430617). Zaehler = Ereignisse, Nenner = Gruppengroesse.

Bindung: Form 1 am Label; Form 2 und 3 nur ueber das gedruckte `respectively`
und nur bei gleich langen Listen. Ohne belegten Arm entsteht kein Fakt.
Form 1 und 3 verlangen zusaetzlich den Outcome im Satz (ausgeschrieben oder als
gedruckte Abkuerzung, `colonic transit time` -> `CTT`); Form 2 verlangt eine
genannte Population. Tabellenzonen (`char_start`..`char_end` der Tabelle)
bleiben aussen vor.

## Ergebnis

| Groesse | ohne Text | mit Text |
| --- | --- | --- |
| erreichbare Goldfelder | 94 | **101** |
| wertgleich | 68 | **83** |
| nicht wertgleich | 26 | 11 |

* neu wertgleich: **15**, davon **5 eindeutig** (nur eine gedruckte Zahl) und
  **10 mehrdeutig** (mehrere gedruckte Zahlen im selben Feld).
* felder, die erst durch den Text erreichbar werden: **7** (Ereigniszahlen und
  drei Gruppengroessen).
* verloren: **0**; Armwechsel: **0**.
* `population_mismatch`: **15 von 15** wertgleich (vorher 10).
* `subgroup_vs_total`: 2 von 3 (vorher 0), `unexplained`: 1 von 9 (vorher 0).
* Text-Fundstellen: **67** in **22** der 59 Records - `label_n` 37,
  `zahlenliste` 12, `bruchliste` 12.

Die fuenf Zielfelder:

| Record | Feld | gedruckt | Fundstelle |
| --- | --- | --- | --- |
| yun2024:531 | intervention_group_size | 289 | ITT-Liste (283, 289, 204) |
| yun2024:531 | comparator_group_size | 204 | ITT-Liste |
| yun2024:532 | intervention_group_size | 283 | ITT-Liste |
| yun2024:532 | comparator_group_size | 204 | ITT-Liste |
| yun2024:185 | comparator_group_size | 28 | `placebo, n = 28` |

## Was das nicht loest

**Die fuenf Felder sind wertgleich, aber nicht eindeutig.** In allen fuenf
stehen zwei Populationen gedruckt: ITT (283/289/204) gegen Safety
(298/307/214) bei PMC4230312, Baseline 33 gegen CTT 28 bei PMC5122613. Die
Fundstelle nennt die Population in der Regel, das Feldmodell kennt sie nicht -
eine Auswertung muesste waehlen. Ein Automatismus "ITT gilt" haette keinen
gedruckten Beleg fuer *dieses* Outcome; deshalb steht er nicht in der Regel.

Dieselbe Unschaerfe trifft 5 weitere Felder, die vorher schon wertgleich waren
und jetzt eine zweite Zahl tragen (`yun2024:645`/`:647`: Tabelle 27/26, Text
29/30; `yun2024:196`: 169/167 gegen 145/140). Insgesamt **18 Konflikte**
(Textwert weicht von allen Tabellenwerten ab) - alle in `messung.json`
aufgelistet.

Ein Sonderfall: `yun2024:78`/`:79` drucken in der Tabelle nur Untergruppen
(3, 8, 19), im Text die Summen 29/30. Beide Felder werden wertgleich, aber
mehrdeutig.

## Grenzen

* Die Textformen sind bewusst eng: drei Muster, keine freie Zahlensuche. Was
  anders formuliert ist (etwa `n = 12 of 40`), bleibt unerreichbar.
* Das Akronym-Gate braucht Grossschreibung (`CTT`); kleingeschriebene
  Abkuerzungen und andere Synonyme fallen durch.
* Das Modul extrahiert nichts und aendert den Tabellenpfad nicht: die 130
  Tests der Tabellenzerlegung bleiben gruen, die 94/68 sind identisch mit
  Sprint 47.
* Mehrdeutigkeit ist ausgewiesen, nicht aufgeloest.

## Empfehlung

**Naechster Hebel: die Population entscheiden, nicht weitere Formen sammeln.**
Eine Textzahl, die im selben Satz wie das Outcome steht, ist der gedruckte
Beleg fuer die Analyspopulation (`−14.88 [n = 289]` im MADRS-Satz). Wer sie als
Korroboration fuehrt, kann die 10 mehrdeutigen Felder auf die Analyspopulation
eingrenzen - ohne Gold, ohne Netzlauf, rein offline messbar. Danach bleiben
`timepoint_mismatch` (6) und `sum_of_subgroups` (3) als naechste Klassen.
