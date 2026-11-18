# Sprint 48 - Zahlen aus dem Fliesstext als Fundstelle

Stand 18.11.2026, zweite Messung mit strikter Kennzahl. Offline, rein lesend:
kein Modelllauf, kein Netz, Gold und eingefrorene Auswahl unveraendert. Alle
Zahlen aus `messung.json` (Skript `diagnose_fliesstext.py`, Laeufe identisch).

## Frage

Werden die fuenf noch offenen `population_mismatch`-Felder erreichbar und
wertgleich, wenn der gedruckte Fliesstext als Fundstelle zaehlt - ohne
Armumkehr und ohne Gold in der Regel? Und: verdeckt die Zahl 101/83, dass der
Text Felder mehrdeutig macht?

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

## Zwei Kennzahlen

* **wertgleich** (bisher): irgendeine Fundstelle trifft den Goldwert. Ein Feld
  zaehlt auch dann, wenn daneben eine zweite, abweichende Zahl gedruckt steht.
* **streng** (neu): im Feld steht **genau eine** gedruckte Zahl, und sie trifft
  den Goldwert. Diese Kennzahl verdeckt keine Mehrdeutigkeit.

| Groesse | ohne Text | mit Text |
| --- | --- | --- |
| erreichbare Goldfelder | 94 | **101** |
| wertgleich | 68 | **83** |
| **streng** | **49** | **46** |

Neu wertgleich **15**, davon neu streng **5** - aber **8 Felder verlieren ihre
Eindeutigkeit**. Unter dem Strich: **49 -> 46 streng**, also drei Felder
weniger als vor dem Textleser.

Gedruckte Zahlen je Feld (ohne -> mit): 0 Zahlen 11 -> 11, genau eine
59 -> 50, zwei 17 -> 31, drei und mehr 7 -> 9. Von den 50 Feldern mit genau
einer Zahl treffen 46 den Goldwert (4 nicht); vorher trafen 49 von 59.

## Die Regression im Einzelnen

Acht Felder, die vorher eindeutig und richtig waren, tragen jetzt eine zweite
gedruckte Zahl:

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

**Kein Feld wurde falsch** - alle acht bleiben wertgleich, sie verlieren nur die
Eindeutigkeit. Die zweite Zahl ist meist eine andere gedruckte Population
(Baseline gegen Outcome-Population: 645/647 drucken 29/30 als Baseline und
27/26 in der Ergebnistabelle, 639/640 drucken 13 und 12). Bei :174 (11 gegen
15) und :445 (140 gegen 70) ist die Zuordnung ohne den Satz nicht entscheidbar;
die Fundstelle traegt den Satz.

Von den fuenf neu strengen Feldern sind alle **neu erreichbar**, keines war
vorher schon wertgleich: `:202`/`:205` intervention 40, `:265`/`:266`
comparator_events 4, `:682` comparator 15.

## Die fuenf Zielfelder

| Record | Feld | gedruckt | Fundstelle | streng |
| --- | --- | --- | --- | --- |
| yun2024:531 | intervention_group_size | 289 | ITT-Liste (283, 289, 204) | nein |
| yun2024:531 | comparator_group_size | 204 | ITT-Liste | nein |
| yun2024:532 | intervention_group_size | 283 | ITT-Liste | nein |
| yun2024:532 | comparator_group_size | 204 | ITT-Liste | nein |
| yun2024:185 | comparator_group_size | 28 | `placebo, n = 28` | nein |

Alle fuenf werden **wertgleich, keines streng**: in allen steht die zweite
Population gedruckt (ITT 283/289/204 gegen Safety 298/307/214; Baseline 33
gegen CTT 28). Die Fundstelle nennt die Population in der Regel, das Feldmodell
kennt sie nicht. Eine Regel "ITT gilt" waere fuer dieses Outcome nicht gedruckt
belegt und steht deshalb nicht drin. `population_mismatch` insgesamt: 15 von 15
wertgleich (vorher 10), aber **streng 8 -> 4**.

## Was das nicht loest

Dieselbe Unschaerfe trifft Felder, die vorher schon wertgleich waren und jetzt
eine zweite Zahl tragen (`:645`/`:647`, `:196` mit 169/167 gegen 145/140).
Insgesamt **18 Konflikte** (Textwert weicht von allen Tabellenwerten ab) - alle
in `messung.json`. Die 18 decken sich nicht mit den 8 Verlusten: 10 Konflikte
treffen Felder, die schon vorher zwei Zahlen trugen oder am Goldwert vorbei
zeigten (`:196`, `:531`/`:532`, `:78`/`:79`).

Ein Sonderfall: `yun2024:78`/`:79` drucken in der Tabelle nur Untergruppen
(3, 8, 19), im Text die Summen 29/30. Beide Felder werden wertgleich, aber
mehrdeutig - und bleiben es unter der strikten Kennzahl.

## Grenzen

* Die Textformen sind bewusst eng: drei Muster, keine freie Zahlensuche. Was
  anders formuliert ist (etwa `n = 12 of 40`), bleibt unerreichbar.
* Das Akronym-Gate braucht Grossschreibung (`CTT`); kleingeschriebene
  Abkuerzungen und andere Synonyme fallen durch.
* **Die strikte Kennzahl ist eine Obergrenze der Eindeutigkeit**: sie zaehlt nur
  Zahlen, die der Leser findet. Eine gedruckte Zahl in einer ungelesenen Form
  macht ein Feld nicht mehrdeutig - fuer den Leser, aber sehr wohl fuer den
  Text.
* Das Modul extrahiert nichts und aendert den Tabellenpfad nicht: die 136
  Tests der Tabellenzerlegung bleiben gruen, die 94/68 sind identisch mit
  Sprint 47.
* Mehrdeutigkeit ist ausgewiesen, nicht aufgeloest.

## Empfehlung

**Naechster Hebel: die Population entscheiden, nicht weitere Formen sammeln.**
Eine Textzahl im selben Satz wie das Outcome (`−14.88 [n = 289]` im
MADRS-Satz) ist der gedruckte Beleg fuer die Analyspopulation. Wer sie als
Korroboration fuehrt, kann die 10 mehrdeutigen Felder auf die
Analyspopulation eingrenzen und die 8 verlorenen Felder zurueckgewinnen - ohne
Gold, ohne Netzlauf, offline messbar. Danach bleiben `timepoint_mismatch` (6)
und `sum_of_subgroups` (3) als naechste Klassen.
