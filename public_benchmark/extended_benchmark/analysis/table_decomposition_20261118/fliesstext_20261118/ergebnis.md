# Sprint 48 - Zahlen aus dem Fliesstext als Fundstelle

Stand 18.11.2026, vierte Messung: aufgeraeumtes Skript, strikte Kennzahl,
Korroboration aus dem Ergebnissatz und Dosis-Bindung. Offline, rein lesend:
kein Modelllauf, kein Netz, Gold und eingefrorene Auswahl unveraendert. Alle
Zahlen aus `messung.json` (zwei Laeufe byte-gleich).

## Frage

Werden die fuenf noch offenen `population_mismatch`-Felder erreichbar und
wertgleich, wenn der gedruckte Fliesstext als Fundstelle zaehlt - ohne
Armumkehr und ohne Gold in der Regel? Und laesst sich die richtige der
gedruckten Zahlen aus dem Dokument belegen statt raten?

## Regel (`research_agent/table_decomposition/fliesstext.py`)

Drei gedruckte Formen, jede mit eigenem Beleg:

1. **Label, n = X** - der Arm steht unmittelbar an der Zahl:
   `(placebo, n = 28; RMD, n = 29)` (PMC5122613).
2. **Zahlenliste + Armliste + "respectively"**, nur mit genannter Population:
   `(283, 289, and 204 patients received quetiapine 300 mg/day, quetiapine
   600 mg/day, or placebo, respectively)` (PMC4230312, ITT) und dieselbe Form
   fuer die Safety-Population (298, 307, 214).
3. **Bruchliste + Armliste + "respectively"**: `5.1% (4/79), 3.6% (3/83), and
   5.0% (4/80) in the placebo, 30 µg YIC and 60 µg YIC groups respectively`
   (PMC2430617).

Bindung: Form 1 am Label; Form 2 und 3 nur ueber das gedruckte `respectively`
und nur bei gleich langen Listen. Ohne belegten Arm entsteht kein Fakt.
Form 1 und 3 verlangen zusaetzlich den Outcome im Satz (ausgeschrieben oder als
gedruckte Abkuerzung, `colonic transit time` -> `CTT`); Form 2 verlangt eine
genannte Population. Tabellenzonen bleiben aussen vor.

## Kennzahlen

* **wertgleich** - irgendeine Fundstelle trifft den Goldwert, auch wenn daneben
  eine zweite, abweichende Zahl steht.
* **streng** - genau eine gedruckte Zahl im Feld, und diese Zahl trifft den
  Goldwert.
* **streng_gewaehlt** - wie `streng`, aber je Feld nur mit den belegten Zahlen:
  Dosis im selben Satz und `n = X` im Ergebnissatz schneiden sich.

| Groesse | ohne Text | mit Text |
| --- | --- | --- |
| erreichbare Goldfelder | 94 | **101** |
| wertgleich | 68 | **83** |
| streng | 49 | **46** |
| streng_gewaehlt | - | **55** |

Neu wertgleich **15**, davon **5 eindeutig**; **8 Felder verlieren ihre
Eindeutigkeit**, kein Feld wird falsch. Gedruckte Zahlen je Feld (ohne -> mit):
0 Zahlen 11 -> 11, genau eine 59 -> 50, zwei 17 -> 31, drei und mehr 7 -> 9.

Die Regression im Einzelnen:

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

## Belege aus dem Dokument

Zwei Merkmale an der Fundstelle, beide nur aus gedrucktem Text:

* **`belegt`** - dieselbe Zahl steht als `n = X` in einem Fenster von 260
  Zeichen um sie, und dieses Fenster (ohne Tabellenzonen) nennt das Outcome
  (markup-tolerant: `*n* = 289`). Das belegt die Analyspopulation.
* **`arm_basis = fliesstext_dosis:<dosis>`** - das gedruckte Label traegt
  dieselbe Dosis wie der Arm dieses Records (`quetiapine 600 mg/day` neben
  `n = 289`). Das belegt die Dosis, nicht die Population.

Die Wahl schneidet beide: erst die Dosis, dann `n = X` innerhalb des Rests.
Bleibt der Schnitt leer, bleibt der Rest stehen - es wird nichts geraten.

Ergebnis: **9 Felder** werden aufgeloest, alle richtig (`streng_gewaehlt` 46 ->
55).

| Record | Feld | gedruckt | gewaehlt | Beleg |
| --- | --- | --- | --- | --- |
| yun2024:185 | comparator_group_size | 28, 33 | 28 | `n = 28` im CTT-Satz |
| yun2024:531 | comparator_group_size | 204, 214 | 204 | `n = 204` |
| yun2024:532 | comparator_group_size | 204, 214 | 204 | `n = 204` |
| yun2024:531 | intervention_group_size | 283, 289, 298, 307 | 289 | Dosis 600 mg/day ∩ `n = 289` |
| yun2024:532 | intervention_group_size | 283, 289, 298, 307 | 283 | Dosis 300 mg/day ∩ `n = 283` |
| yun2024:265 | intervention_group_size | 80, 83 | 83 | Dosis 30 µg |
| yun2024:266 | intervention_group_size | 80, 83 | 80 | Dosis 60 µg |
| yun2024:265 | intervention_events | 3, 4 | 3 | Dosis 30 µg |
| yun2024:266 | intervention_events | 3, 4 | 4 | Dosis 60 µg |

Die fuenf Zielfelder sind damit **alle streng und richtig**. Die Dosis allein
haette bei `:531`/`:532` nicht gereicht: dort sind 289 (ITT) **und** 307
(Safety) mit 600 mg/day gedruckt - erst der Schnitt mit `n = X` trennt die
Population. `population_mismatch` streng: 4 -> **11** von 15.

## Was das nicht loest

Die acht verlorenen Felder bleiben mehrdeutig; bei `:645`/`:647` (Baseline
29/30 gegen Ergebnistabelle 27/26) und `:174`, `:445`, `:639`/`:640` trennt
weder Dosis noch `n = X`. Insgesamt **18 Konflikte** (Textwert weicht von allen
Tabellenwerten ab) - alle in `messung.json`; 10 davon treffen Felder, die schon
vorher zwei Zahlen trugen oder am Goldwert vorbeizeigten.

`yun2024:78`/`:79` drucken in der Tabelle nur Untergruppen (3, 8, 19), im Text
die Summen 29/30; beide bleiben mehrdeutig.

## Grenzen

* Dosis bindet nur, wenn der Record-Arm die Dosis im Namen traegt. Bei einem
  Arm `quetiapine` ohne Dosisangabe unterbleibt die Bindung - gewollt.
* Die Dosisform ist eng (`600 mg/day`, `30 µg`, `0.5 mg/kg`); andere
  Schreibweisen binden nicht.
* Die strikte Kennzahl ist eine Obergrenze der Eindeutigkeit: sie zaehlt nur
  Zahlen, die der Leser findet.
* Die Korroboration erkennt nur `n = X`; `analysed` oder `evaluable` bleiben
  ungenutzt.
* Das Modul extrahiert nichts und aendert den Tabellenpfad nicht.

## Empfehlung

**Naechster Hebel: `timepoint_mismatch` (6 Felder), nicht weitere
Textformulare.** Die Populationsfrage ist geschlossen, die Dosisfrage fuer die
beiden offenen Zielfelder auch. Die sechs Zeitpunkt-Felder scheitern an einer
anderen Achse (Baseline gegen Endpunkt) und brauchen dieselbe Behandlung: ein
gedruckter Zeitpunkt im selben Satz oder in der Spaltenbeschriftung. Risiko
gering, weil die Zeitpunktspalte schon als Merkmal existiert (`zeitpunkt` an
der Fundstelle); Kosten: ein Messlauf offline. Danach `sum_of_subgroups` (3)
und die acht verlorenen Eindeutigkeiten, die ohne Populationsangabe im Text
nicht zu retten sind.
