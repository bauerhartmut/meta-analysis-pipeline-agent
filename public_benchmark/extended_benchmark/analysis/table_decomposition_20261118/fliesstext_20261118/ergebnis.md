# Sprint 48 - Zahlen aus dem Fliesstext als Fundstelle

Stand 18.11.2026, dritte Messung: strikte Zahl direkt gegen Gold und
Korroboration aus dem Ergebnissatz. Offline, rein lesend: kein Modelllauf, kein
Netz, Gold und eingefrorene Auswahl unveraendert. Alle Zahlen aus
`messung.json` (zwei Laeufe byte-gleich).

## Frage

Werden die fuenf noch offenen `population_mismatch`-Felder erreichbar und
wertgleich, wenn der gedruckte Fliesstext als Fundstelle zaehlt - ohne
Armumkehr und ohne Gold in der Regel? Verdeckt die Zahl 83, dass der Text
Felder mehrdeutig macht - und laesst sich die Population aus dem Ergebnissatz
belegen statt raten?

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
genannte Population. Tabellenzonen (`char_start`..`char_end`) bleiben aussen
vor.

## Kennzahlen

* **wertgleich** - irgendeine Fundstelle trifft den Goldwert, auch wenn daneben
  eine zweite, abweichende Zahl steht.
* **streng** - genau eine gedruckte Zahl im Feld **und** das Feld ist
  wertgleich (die Fassung aus dem vorigen Bericht).
* **streng_direkt** - genau eine gedruckte Zahl, und **diese Zahl** trifft den
  Goldwert (Vergleich Zahl gegen Gold, ohne Umweg ueber `wertgleich`).

| Groesse | ohne Text | mit Text |
| --- | --- | --- |
| erreichbare Goldfelder | 94 | **101** |
| wertgleich | 68 | **83** |
| streng | 49 | **46** |
| streng_direkt | 49 | **46** |

**Die beiden strengen Fassungen sind auf dieser Auswahl identisch** - 49 vor,
46 nach, dieselben acht Verluste, kein Gewinn. Der Grund steht als Feld in
`messung.json`: `definition_abweichungen` ist leer, also gibt es kein Feld mit
genau einer gedruckten Zahl, das wertgleich waere, ohne dass diese Zahl der
Goldwert ist. Bei genau einer Zahl entscheidet der Textabgleich ueber dieselbe
Zahl wie der direkte Vergleich; die Fassungen koennen hier nicht
auseinanderlaufen.

Neu wertgleich **15**, davon **5 eindeutig**; **8 Felder verlieren ihre
Eindeutigkeit** - kein Feld wird falsch, alle acht bleiben wertgleich.

Gedruckte Zahlen je Feld (ohne -> mit): 0 Zahlen 11 -> 11, genau eine
59 -> 50, zwei 17 -> 31, drei und mehr 7 -> 9.

## Die Regression im Einzelnen

| Record | Feld | vorher | nachher | noch wertgleich |
| --- | --- | --- | --- | --- |
| yun2024:174 | comparator_group_size | 15 | 11, 15 | ja |
| yun2024:445 | comparator_group_size | 70 | 70, 140 | ja |
| yun2024:639 | comparator_group_size | 12 | 12, 13 | ja |
| yun2024:640 | comparator_group_size | 12 | 12, 13 | ja |
| yun2024:645 | comparator_group_size | 26 | 26, 30 | ja |
| yun2024:645 | intervention_group_size | 27 | 27, 29 | ja |
| yun2024:647 | comparator_group_size | 26 | 26, 30 | ja |
| yun2024:647 | intervention_group_size | 27 | 27, 29 | ja |

Von den fuenf neu strengen Feldern sind alle neu erreichbar: `:202`/`:205`
intervention 40, `:265`/`:266` comparator_events 4, `:682` comparator 15.

## Korroboration aus dem Ergebnissatz

Neue Regel in `fliesstext.im_ergebnis`: eine Fliesstext-Zahl ist **belegt**,
wenn dieselbe Zahl in einem Fenster von 260 Zeichen um sie als `n = X` steht
(markup-tolerant: `*n* = 289`, `***n*** = 298`) und dieses Fenster - ohne die
Tabellenzonen - das Outcome nennt. Ein blosses Vorkommen der Zahl belegt
nichts; eine Tabellenzelle belegte sich sonst selbst.

Damit laesst sich die Population aus dem Dokument waehlen, ohne sie zu raten:
`streng_gewaehlt` nimmt je Feld die belegten Zahlen (gibt es keine, alle) und
prueft, ob genau eine uebrig bleibt und sie den Goldwert trifft.

* **9 Felder** tragen eine belegte Zahl.
* **3 mehrdeutige Felder werden aufgeloest**, alle richtig:
  `:185` comparator 28 statt 33 (CTT-Satz gegen Baseline-Kopf),
  `:531` und `:532` comparator 204 statt 214 (ITT-`n` im Ergebnissatz gegen
  Safety-Liste).
* `streng_gewaehlt`: **49** (46 + 3). `population_mismatch` streng: 4 -> **7**
  von 15.
* **Nicht aufgeloest**: `:531`/`:532` intervention. Dort sind **beide** Zahlen
  belegt - 283 und 289 stehen als zwei Dosen im selben Ergebnissatz. Die
  Korroboration belegt die Population, nicht die Dosis; das Feld bleibt
  mehrdeutig, und die Regel behauptet nichts.

## Was das nicht loest

Dieselbe Unschaerfe trifft Felder, die vorher schon wertgleich waren und jetzt
eine zweite Zahl tragen (`:645`/`:647`, `:196` mit 169/167 gegen 145/140).
Insgesamt **18 Konflikte** (Textwert weicht von allen Tabellenwerten ab) - alle
in `messung.json`. Die 18 decken sich nicht mit den 8 Verlusten: 10 Konflikte
treffen Felder, die schon vorher zwei Zahlen trugen oder am Goldwert vorbei
zeigten (`:196`, `:531`/`:532`, `:78`/`:79`).

`yun2024:78`/`:79` drucken in der Tabelle nur Untergruppen (3, 8, 19), im Text
die Summen 29/30; beide bleiben mehrdeutig.

## Grenzen

* Die Textformen sind bewusst eng: drei Muster, keine freie Zahlensuche.
* Das Akronym-Gate braucht Grossschreibung (`CTT`).
* Die strikte Kennzahl ist eine **Obergrenze der Eindeutigkeit**: sie zaehlt nur
  Zahlen, die der Leser findet.
* Die Korroboration erkennt nur `n = X`. Andere gedruckte Belege fuer die
  Analyspopulation (etwa `analysed`, `evaluable`) bleiben ungenutzt.
* Das Modul extrahiert nichts und aendert den Tabellenpfad nicht; die 136
  Tests der Tabellenzerlegung bleiben gruen.

## Empfehlung

**Naechster Hebel: die Dosis trennen, nicht weitere Populationen sammeln.** Die
Korroboration hat die Populationsfrage fuer 3 von 5 Zielfeldern entschieden; die
beiden offenen Felder (`:531`/`:532` intervention) scheitern nicht an der
Population, sondern an zwei Dosen im selben Satz. Eine zweite, ebenso billige
Regel - Arm aus der Dosisangabe des Satzes (`300 mg/day` vor `[n = 283]`) -
wuerde sie schliessen. Risiko: Dosisangaben sind vielfaeltig; ohne gedruckte
Zuordnung im selben Satz darf nichts gebunden werden. Danach bleiben
`timepoint_mismatch` (6) und `sum_of_subgroups` (3).
