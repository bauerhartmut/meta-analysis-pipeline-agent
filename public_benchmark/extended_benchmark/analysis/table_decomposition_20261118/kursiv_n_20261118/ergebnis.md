# Sprint 44 - Kursiv gesetzte Gruppengroessen und Armdiagnose

Offline, 2026-11-18. Kein Netzlauf, kein Modelllauf; Gold und eingefrorene
Eingaben unveraendert. Werkzeug:
`public_benchmark/extended_benchmark/table_decomposition/diagnose_kursiv_n.py`,
Rohdaten: `messung.json` (daneben).

## 1. Phase 1 - die vier betroffenen Tabellen

Vorher erkannte `_GROUP_SIZE_ANY_RE` nur `n = 103`; in den Dokumenten steht die
Angabe als `*n* = 103`. Je Band sind Beschriftung, alter und neuer Fund,
Geometrie und Goldfeld gegenuebergestellt.

| Record | Tabelle | Band (Original) | Geometrie | bisher | neu | Goldfeld / Arm |
| --- | --- | --- | --- | --- | --- | --- |
| yun2024:15, :16 | PMC2667135:T4 | `CoPAT^a^ (*n* = 103)` | L0, c1-1 | kein Fakt | 103 | intervention_group_size 103 / intervention |
| yun2024:15, :16 | PMC2667135:T4 | `IPAT (*n* = 97)` | L0, c2-2 | kein Fakt | 97 | comparator_group_size 97 / comparator |
| yun2024:662 | PMC4987981:T1 | `Placebo (*n* = 23)` | L0, c1-1 | kein Fakt | 23 | comparator_group_size 23 / comparator |
| yun2024:662 | PMC4987981:T1 | `Metformin (*n* = 21)` | L0, c2-2 | kein Fakt | 21 | intervention_group_size 37 (Summe, nicht gedruckt) |
| yun2024:662 | PMC4987981:T1 | `Pioglitazone (*n* = 16)` | L0, c3-3 | kein Fakt | 16 | intervention_group_size 37 (Summe, nicht gedruckt) |
| yun2024:275 | PMC3654355:T1 | `ILI ( *n* = 71)` | L0, c1-1 | kein Fakt | 71 | intervention_group_size 71 / intervention |
| yun2024:275 | PMC3654355:T1 | `Control ( *n* = 33)` | L0, c2-2 | kein Fakt | 33 | comparator_group_size 33 / comparator |
| yun2024:282 | PMC3654355:T2 | `( *n* = 71)` | L1, c1-1, unter `ILI` | kein Fakt, aber Spaltenrolle `n` | 71 | intervention_group_size 71 / intervention |
| yun2024:282 | PMC3654355:T2 | `( *n* = 33)` | L1, c2-2, unter `Control` | kein Fakt, aber Spaltenrolle `n` | 33 | comparator_group_size 33 / comparator |

Der Befund ist nicht auf diese vier Tabellen beschraenkt: im gesamten
Record-Satz tragen **14 Tabellen** solche Bänder, darunter `PMC5079604:T1`,
`PMC5122613:T1`, `PMC5874317:T1`, `PMC3786549:T3`, `PMC4230312:T1/T3`,
`PMC4511433:T2`, `PMC4675066:T1`, `PMC4987981:T2` und `PMC5781260:T1`.

## 2. Phase 2 - Parser-Erweiterung

```python
_EMPHASIS = r"[*_]{0,3}"
_GROUP_SIZE_DECL_RE = r"^\(?\s*{e}\s*n\s*{e}\s*=\s*{e}\s*(\d{1,6})\s*{e}\s*\)?$"
_GROUP_SIZE_ANY_RE  = r"(?:^|[^\w]){e}\s*n\s*{e}\s*=\s*{e}\s*(\d{1,6})\b"
```

Die Auszeichnung (`*n*`, `**N**`, `***n***`, `_n_`) ist Dekoration; verlangt
bleiben ein eigenstaendiges `n`, ein `=`, und eine Zahl mit hoechstens sechs
Ziffern. Damit gilt dieselbe Regel wie vorher, nur ohne die Markup-Bremsen:
`n = 103`, `(n = 103)`, `*n* = 103`, `(*n* = 103)`, `( *n* = 71)` und
`***n*** = 298` liefern dieselbe Zahl. Nicht erkannt werden weiterhin
`season = 5`, `df = 2`, `p = 0.05`, `n = 1234567` (sieben Ziffern) und der
tiefgestellte Zaehler `**N**~**c**~**= 12**`.

Im Eingangsmaterial der 31 Dokumente: 166-mal `*n*`, 9-mal `**n**`, kein
`_n_` und kein HTML (`<i>`). HTML-Varianten sind deshalb nicht implementiert;
`_n_` wird von der Regel mitgetragen, kommt aber nicht vor.

## 3. Phase 3 - strukturelle Bindung

* Die Kopfgeometrie ist unveraendert: fuer alle **60** Tabellen der Auswahl
  sind Ebene, Spannen und Texte aller Bänder vorher und nachher identisch
  (Vergleich im Messlauf).
* Die Kopfangabe bleibt an ihr Band gebunden (`level`, `col_start`, `col_end`);
  der Arm kommt weiterhin ausschliesslich aus dem uebergeordneten Kopfpfad
  oder - wenn dort keiner belegt ist - aus den Spalten unter dem Band.
* Eine reine kursive Angabe (`( *n* = 71)`) gilt jetzt wie `(n = 71)` als
  Kopfangabe und nicht mehr als Spaltenkopf; die Spalte darunter verliert damit
  die Rolle `n`. In `PMC3654355:T2` aendert das die Einheiten (B/D/E je eine
  weniger), nicht die Goldfelder.
* Keine Aenderung an `bind_arm`, an `_BELEGTE_ARM_BASIS` oder an der
  Spaltenarm-Zuordnung.

## 4. Phase 4 - Regressionstests

Neu: `research_agent/tests/test_gruppengroesse_kursiv.py` mit 24 Tests
(Schreibweisen, Negativfaelle, die vier Tabellen, Arm-Guard). Angepasst:
`test_kopfbaender.py::test_candidate_without_gain_keeps_the_printed_geometry`
erwartet fuer `PMC4987981:T2` jetzt zusaetzlich `intervention_group_size` und
`comparator_group_size` - die Spaltengeometrie und `band_decision` bleiben
unveraendert.

Gesamt **116 Tests gruen** (vorher 92). Geprueft sind darunter:
bestehende Gruppengroessen-Erkennung unveraendert, keine Gruppengroesse aus
gewöhnlichen Zahlen, keine neuen Armkonflikte, unveraenderte Spaltengeometrie.

## 5. Phase 5 - getrennte Auswertung

| Kennzahl | vorher | nachher |
| --- | --- | --- |
| neu erkannte Gruppengroessen (Fakten) | - | **35 eindeutig** (62 je Record) in 14 Tabellen |
| strukturell erreichbare Goldfelder | 62 | **94** (+32, kein Verlust) |
| davon korrekt adressiert (Feld und Arm) | 62 | **94** |
| davon wertgleich (Wert an der Adresse gedruckt) | 32 | **58** |
| Goldfelder mit Armkonflikt | 0 | **0** |
| strukturelle Fehler (A-E) | 0 | **0** |

**Ein erkannter Zahlenwert ist kein Goldtreffer.** Von den 32 neu erreichbaren
Feldern haben 21 den Goldwert an der Adresse; die uebrigen 11 sind strukturell
erreichbar, aber nicht wertgleich:

| Record | Feld | Goldwert | im Kopf gedruckt |
| --- | --- | --- | --- |
| yun2024:172, :174 | intervention_group_size | 33 | 17 (Metformin), 16 (Sitagliptin) |
| yun2024:185 | comparator_group_size | 28 | 33 (Placebo/RMD), 66 (Total) |
| yun2024:531, :532 | intervention / comparator | 289/283, 204 | 298, 307, 214 |
| yun2024:645, :647 | intervention / comparator | 27, 26 | 29, 30 |

Lauf A-E (nur diese Zahlen aendern sich):

| Kennzahl | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| Goldfelder | 62 -> 94 | 62 -> 94 | 62 -> 94 | 62 -> 94 | 62 -> 94 |
| erwartete Zellen | 1687 | 1261 -> 1266 | 1687 | 1687 | 1674 |
| Einheiten | 60 | 159 -> 151 | 329 | 442 -> 431 | 273 -> 262 |
| Warnungen | 137 | 101 -> 103 | 237 | 318 | 253 |
| Strukturfehler | 0 | 0 | 0 | 0 | 0 |

Die zwei zusaetzlichen Warnungen in B und die kleineren Einheiten in B/D/E
stammen aus `PMC3786549:T3` (`yun2024:486`, `:489`): die reinen kursiven
Angaben sind jetzt Kopfangaben statt Spaltenkoepfe, dadurch faellt die
spaltenweise Zerlegung auf weniger Auftraege zurueck. Goldfelder und Fehler
bleiben dort unveraendert (0 -> 2 Goldfelder, 0 Fehler).

In den vier Zieltabellen aendert sich kein Feld, aber fuenf Goldzellen werden
wertgleich: `103` (`yun2024:15`, `:16`), `71` (`:275`, `:282`) und `23`
(`yun2024:662`). Die Summe 37 in `PMC4987981:T1` und die 33 aus
`PMC3654355:T1/T2` bleiben ohne gedruckten Wert.

## 6. Phase 6 - Armkonflikte: Volltextbefund

Gesucht wurde im Volltext der beiden Dokumente (Markdown, offline, rein
lesend) nach einer Zuordnung der Zahlen zu den Gruppen. Beide Faelle sind damit
aufgeklaert - aber nicht in dieselbe Richtung, und keiner ueber die
Armzuordnung.

### `PMC5617873:T2` (`yun2024:335`, `:336`) - Text widerspricht dem Gold

* Abstract: "Ninety-two patients were randomized to placebo (n = 45) or
  aripiprazole (n = 47)."
* Ergebnisse: "92 patients were randomly assigned to receive placebo (n = 45)
  or aripiprazole (n = 47)."
* Baseline-Tabelle: "Placebo (n = 45) Aripiprazole (n = 47) Total (n = 92)".
* Gegenprobe: "Forty-two (93.3%) patients in the placebo group" (42/45 = 93,3 %)
  und "the last dose of placebo corresponding to aripiprazole (n = 45)".

Dreimal unabhaengig belegt: **45 gehoert zu Placebo (Vergleichsarm), 47 zu
Aripiprazol (Interventionsarm)**. Der Parser bindet genau so: `Aripiprazole
(n = 47)` haengt an `intervention`, das Placebo-Band bleibt ohne Arm, weil der
Vergleichsarm im Record `Placbeo` heisst. Der Widerspruch liegt also im
**Goldfeld**, das 45 als `intervention_group_size` und 47 als
`comparator_group_size` fuehrt - nicht in der Armzuordnung des Parsers. Eine
automatische Umkehrung findet nicht statt.

### `PMC5777419:T2` (`yun2024:678`, `:682`) - Text bestaetigt das Gold

* Methoden: "randomly assigned to a probiotic (n=16), antibiotic (n = 16) or
  placebo (n = 15) group."
* Analyse: "Forty-seven patients, 16 in the probiotic group, 16 in the
  antibiotic group and 15 in the placebo group were analyzed."
* Baseline-Tabelle: "Probiotic group (n=16) Antibiotic group (n=16) Placebo
  group (n=15)".

Damit ist **Antibiotika = 16, Placebo = 15** - genau das Gold (intervention 16,
comparator 15). Der Konflikt entsteht im **Kopfband**: Im Rohtext stehen die
drei Gruppengroessen zeilenweise unter `Probiotic group` / `Antibiotic group` /
`Placebo group`, der Parser legt `(n=15)` aber ueber die Spalten 6-10
(Antibiotic) und zerlegt das Probiotic-`(n=16)` in zwei Baender ueber c2 und c5.
Die Zahlen sind also richtig gelesen, aber dem falschen Band zugeordnet; das ist
ein Geometrieproblem der stark whitespace-aufgeblaehten Kopfzeile, keine
Armfrage. In diesem Sprint nicht geaendert.

In beiden Faellen bleibt die Armzuordnung unveraendert; es gibt keine
automatische Umkehrung und keine Uebernahme aus dem Goldwert.

### Vereinfachung des Messwerkzeugs

`diagnose_kursiv_n.py` ist nach dem Sprint-44-Diff auf einen Durchlauf
zusammengezogen: eine Adressauswertung je Record (Kopfangabe und Messzelle
zusammen), daraus Bilanz, neue/verlorene Felder und neue Fakten; die frueheren
Doppellisten (`_bilanz`, `_konflikte`, `korrekt_adressiert`, `wertgleich`,
`records_gold`, `neue_fakten`, `armdiagnosen`) sind weg. 274 statt 423 Zeilen,
die Messung liefert dieselben Zahlen (62/32/0 -> 94/58/0, 35 Fakten, 32 neue
Felder, 21 wertgleich, 0 verloren).

## 7. Grenzen

* Der Wertabgleich prueft Woertlichkeit, nicht Bedeutung: `intervention 16` in
  `PMC4987981:T2` ist wertgleich, weil die Untergruppe `Pioglitazone (n = 16)`
  unter dem Interventionsarm steht - ob Gold und Tabelle dieselbe Gruppe meinen,
  sagt der Vergleich nicht.
* Die Kursiv-Erkennung akzeptiert jede `*`/`_`-Auszeichnung um `n` und um den
  Wert; sie akzeptiert keine Subskripte (`N_c`) und keine Zahlen ohne `n =`.
* "Neu erkannt" heisst: neuer `header_fact`; es heisst nicht, dass der Wert zum
  Gold passt (siehe Phase 5).

## 8. Empfehlung fuer den naechsten Schritt

Zwei konkrete, offline pruefbare Hebel - beide ohne Netz und ohne Modell:

1. **Bandgeometrie bei whitespace-aufgeblaehten Kopfzeilen**
   (`PMC5777419:T2`): die drei Gruppengroessen stehen im Rohtext unter drei
   Gruppen, der Parser legt sie verschoben ab. Eine Messung ueber alle Tabellen
   mit mehr als drei Leerzeichen zwischen Kopfzellen zeigt, wie viele Baender
   betroffen sind; erst dann eine Regel, die die Spaltengrenzen aus der
   Trennzeile nimmt. Das ist der groesste Hebel, weil hier gedruckte Werte
   falsch adressiert werden, ohne dass ein Wert fehlt.
2. **Gold/Record-Abgleich `PMC5617873`**: 45/47 sind im Record vertauscht.
   Nicht automatisch korrigieren - aber als Datenbefund fuehren, damit die
   Auswahl solche Records markiert statt sie stillschweigend zu zaehlen.

Der groessere Hebel liegt finanziell bei null: Die 11 strukturell erreichbaren,
aber nicht wertgleichen Felder zeigen, dass dort Summen oder fremde Tabellen
die Quelle sind - die naechste Messung sollte deshalb die 58 wertgleichen
Felder gegen die Marke von 94 stellen, nicht die Feldzahl weiter aufblaehen.
