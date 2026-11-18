# Spaltenzeitpunkte: was die vier Tabellen heute liefern

Offline-Messung, 2026-11-18. Read-only: keine Produktionsdatei, kein Gold und
keine eingefrorene Messung veraendert, `primary_tables` **nicht** verdrahtet.

Werkzeug: `public_benchmark/extended_benchmark/table_decomposition/diagnose_spaltenzeitpunkte.py`
Rohdaten: `messung.json` (dieses Verzeichnis)

Erfasst wurden alle Auswahl-Eintraege, deren Tabelle Zeitpunkte im Spaltenkopf
traegt - vier Paare aus zwei Tabellen:

| Tabelle | Record | Outcome | Spaltenzeitpunkte |
| --- | --- | --- | --- |
| `PMC5777419:T2` | `yun2024:678` | the total cultivable microbiota | baseline, 3, 6, 9 months |
| `PMC5777419:T2` | `yun2024:682` | attachment gain | baseline, 3, 6, 9 months |
| `PMC3278655:T2` | `yun2024:390` | subsidence | 6, 12, 24, 60 month follow up |
| `PMC3278655:T2` | `yun2024:391` | at risk components at 5 years | 6, 12, 24, 60 month follow up |

Beide Tabellen haben **keine** Zeilenzeitpunkte (`_timepoint_key` leer) - die
Zeitpunkte stehen ausschliesslich in den Kopfbaendern.

## 1. Was heute geliefert wird

| Paar | Felder heute | Wert und Adresse | Goldzellen |
| --- | --- | --- | --- |
| `PMC5777419:T2` / `678` | `intervention_group_size` | 15 aus Band `(n=15)` unter `Antibiotic group` (Kopfangabe, c6) | 2 |
| `PMC5777419:T2` / `682` | `intervention_group_size` | derselbe Wert 15 | 6 |
| `PMC3278655:T2` / `390` | `comparator_group_size` | 24, 23, 21, 18 (vier Kopfangaben c2/c4/c6/c8) | 6 |
| `PMC3278655:T2` / `391` | `comparator_group_size` | dieselben vier Werte | 4 |

Alle vier Paare liefern **genau ein Feld**, und zwar nur ueber Kopfangaben
(`header_facts`). Kein einziger Wert kommt aus einer Zelle: die Spalten tragen
keine Rolle (`Spalten mit Feld: []` in `messung.json`), die Outcome-Zeile ist
bei drei von vier Paaren gar nicht erkannt (`outcome_zeilen: []`), und wo sie
erkannt wird (`PMC5777419:T2`, Zeile 4), stehen zwei Zahlen je Zelle
(`7.6, 31.8`) ohne Rollenangabe.

## 2. Was eine Auswahlregel je Zeitpunkt aendern wuerde

**Nichts.** Zwei Befunde, beide aus `messung.json`:

- **Kein Feldgewinn.** Schneidet man die Tabelle auf die Spalten eines
  Zeitpunkts zu, bleibt je Zeitpunkt **0 Felder** (Summe ueber alle 16
  Zeitpunktbloecke: 0). Die Zuordnung je Zeitpunkt kann nur verteilen, was die
  Tabelle hergibt; sie erzeugt keine Rolle und keinen Arm. Beispiel
  `PMC5777419:T2`, `baseline`: Spalten c1/c6/c11, alle `role=unknown`, Zellen
  `3.8 ± 0.7` - ohne Rollenangabe wird daraus kein Feld.
- **Keine Verdraengung.** Die heutige Regel verdraengt in diesen Records
  nichts (`auswahl_heute: {}`), eine um Spaltenzeitpunkte erweiterte Regel
  ebenfalls nicht (`auswahl_mit_spaltenzeitpunkten: {}`). Es gibt in beiden
  Dokumenten keine zweite Tabelle, die denselben Zeitpunktschluessel traegt -
  die Regel haette nichts zu entscheiden.

Dazu kommt eine Messgrenze: die Goldzellen tragen **kein Zeitpunktfeld**
(`timepoint: None` in allen 18 Zellen; Yun kennt nur eine Regel "primaerer
Zeitpunkt, sonst letzter"). Ein Nutzen je Zeitpunkt waere auf dieser Auswahl
also nicht einmal bewertbar.

## 3. Gold-Abgleich: wo die Werte wirklich stehen

18 Goldzellen, davon 4 mit erreichbarem Feld und 4 mit woertlich gedrucktem
Wert. Die zwei Muster:

| Paar | Goldzelle | Wert gedruckt in | Befund |
| --- | --- | --- | --- |
| `PMC5777419:T2` / `682` | `intervention_mean` 4.1 | `r0/c9`, `r0/c12`, `r0/c13` | Wert steht in Zeile 0 (`CAL (mm)`), nicht in der Outcome-Zeile `attachment gain`; Zelle `4.1 ±1.0` traegt Mittel und Streuung zusammen |
| `PMC5777419:T2` / `682` | `comparator_mean` 4.3 | `r0/c14` | ebenso |
| `PMC3278655:T2` / `390` | `intervention_mean` -0.38 | `r3/c7` | Wert steht in `Superior/inferior translation`, nicht in der als `subsidence` gesuchten Zeile; Zelle `--0.38 (0.37)` traegt beide Zahlen |
| `PMC3278655:T2` / `390` | `comparator_mean` -0.04 | `r3/c8` | ebenso |

Die uebrigen Goldwerte (Standardabweichungen, Interventions-Stichproben,
Ereigniszahlen) stehen nicht als eigener Zahlenwert in der Tabelle: sie sind
entweder der zweite Teil einer Verbundzelle (`4.1 ±1.0`, `--0.38 (0.37)`) oder
liegen in einem Kopfband ohne Arm (`(n=30)`, `(n=27)` ueber den TM-Spalten,
deren Arm nicht erkannt ist).

## 4. Zwei Praezisionsbefunde am Rande

- **Feld richtig, Wert falsch.** Bei `PMC5777419:T2` wird dem Arm
  `intervention` die Kopfangabe 15 zugeordnet (Band `(n=15)` unter
  `Antibiotic group`), waehrend Gold fuer `intervention` 16 und fuer
  `comparator` 15 erwartet. Die Kennzahl `gold_reachable` zaehlt nur Felder,
  nicht Werte - der Fehlgriff bleibt in der 56 unsichtbar. Der Comparator-Wert
  15 ist umgekehrt nicht erreichbar, weil die `(n=...)`-Baender der
  `Placebo group` fehlen.
- **Arm fehlt fuer halbe Tabelle.** Bei `PMC3278655:T2` bekommen nur die
  `Cemented`-Spalten den Arm `comparator`; die `TM`-Spalten (c1/c3/c5/c7)
  bleiben ohne Arm, obwohl `(n=30)`, `(n=29)`, `(n=28)`, `(n=27)` dort stehen.
  Daher fehlt `intervention_group_size` (Gold 27).

## 5. Ergebnis

Die Verdrahtung von `column_timepoints` in `primary_tables` bringt auf dieser
Auswahl **keinen Feldgewinn und keine Verdraengung**; sie wuerde nur eine
Regel ohne Wirkung einfuehren und die eingefrorene Messung umsonst anfassen.
Der Hebel liegt eine Ebene tiefer: Rollen aus `±`/`(SD)`-Zellen und
`Mean (SD)`-Kopfzeilen, Armzuordnung fuer Kopfspalten ohne Armband, und die
Erkennung der Outcome-Zeile bei mehrzeiligen Messwerttabellen
(`attachment gain`, `subsidence`).

## 6. Empfehlung fuer den naechsten Schritt

`PMC3278655:T2` als naechsten Fall nehmen: dort stehen alle vier
Interventions-Stichproben gedruckt, es fehlt nur der Arm fuer die `TM`-Spalten -
ein kleiner, allgemein formulierbarer Schritt (Behandlungslabel `TM` neben
`Cemented` als Armkandidat, Auswahl ueber die Validierung wie bei den
Kopfbaendern). Das ist offline messbar an vier Kopfangaben und kostet kein
Guthaben. Die Zeitpunkt-Auswahl bleibt liegen, bis eine Tabelle mit
Zeitpunkten im Kopf **und** Rollen in den Spalten existiert - erst dann ist
sie ueberhaupt bewertbar.
