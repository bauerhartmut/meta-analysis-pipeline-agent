# Ursachen der falschen Groessenzellen (21.11.2026)

Offline, ohne Netzaufruf. `groessen_ursachen_20261121.py`. Grundlage ist
die Lueckenfuellung ohne Mittel ueber alle 699 Records: 16 neue Groessenzellen, davon 4 richtig und 12 falsch. Die Ursache ist
je Zelle an der benutzten Zeile und am Goldwert zugeordnet; die
Begruendung steht in der Tabelle.

## Zahlen je Ursache

| Ursache | Zellen |
|---|---:|
| falsche_zeile | 5 |
| abweichende_definition | 7 |
| rechenfehler | 0 |

## Zellen

| Record | Feld | Arm | Wert | Gold | Zeile | Kopfzeile | Gold im Dokument | Ursache |
|---|---|---|---:|---:|---:|---|---|---|
| `yun2024:159` | intervention | intervention | 24.0 | 592.0 | 1 | ja | ja | falsche_zeile |
| `yun2024:251` | intervention | intervention | 406.0 | 402.0 | 60 | ja | ja | abweichende_definition |
| `yun2024:251` | comparator | comparator | 393.0 | 388.0 | 60 | ja | ja | abweichende_definition |
| `yun2024:252` | intervention | intervention | 398.0 | 402.0 | 10 | ja | ja | abweichende_definition |
| `yun2024:252` | comparator | comparator | 389.0 | 388.0 | 10 | ja | ja | abweichende_definition |
| `yun2024:356` | comparator | comparator | 15.0 | 13.0 | 6 | ja | ja | abweichende_definition |
| `yun2024:420` | intervention | intervention | 44.0 | 18.0 | 10 | ja | ja | falsche_zeile |
| `yun2024:420` | comparator | comparator | 49.0 | 21.0 | 10 | ja | ja | falsche_zeile |
| `yun2024:421` | intervention | intervention | 44.0 | 30.0 | 10 | ja | ja | falsche_zeile |
| `yun2024:421` | comparator | comparator | 49.0 | 34.0 | 10 | ja | ja | falsche_zeile |
| `yun2024:451` | intervention | intervention | 104.0 | 99.0 | 117 | ja | ja | abweichende_definition |
| `yun2024:451` | comparator | comparator | 114.0 | 108.0 | 117 | ja | ja | abweichende_definition |

## Begruendung je Zelle

- `yun2024:159` intervention_group_size (intervention, Regel 24.0 gegen Gold 592.0): Die 24 stammt aus der Bildunterschrift 'at baseline, 12 and 24 months'; Gold 592 steht in der Armzeile 'Intervention (n=592)' der 12-Monats-Spalte.
  Zeile 1: `::: caption`
- `yun2024:251` intervention_group_size (intervention, Regel 406.0 gegen Gold 402.0): Kopfzeile nennt randomisiert n=406, die Outcome-Zeile rechnet mit 42/402; Gold nimmt die 402.
  Zeile 60: `---------------------------------------------------- ------------------------ ------------------- --------------------------------------------------------------`
- `yun2024:251` comparator_group_size (comparator, Regel 393.0 gegen Gold 388.0): Kopfzeile nennt randomisiert n=393, die Outcome-Zeile rechnet mit 41/388; Gold nimmt die 388.
  Zeile 60: `---------------------------------------------------- ------------------------ ------------------- --------------------------------------------------------------`
- `yun2024:252` intervention_group_size (intervention, Regel 398.0 gegen Gold 402.0): Charakteristika-Tabelle nennt randomisiert n=398, Gold 402 ist der Nenner der Outcome-Zeilen.
  Zeile 10: `--------------------------------------------------- -------------------------- ---------------------`
- `yun2024:252` comparator_group_size (comparator, Regel 389.0 gegen Gold 388.0): Charakteristika-Tabelle nennt randomisiert n=389, Gold 388 ist der Nenner der Outcome-Zeilen.
  Zeile 10: `--------------------------------------------------- -------------------------- ---------------------`
- `yun2024:356` comparator_group_size (comparator, Regel 15.0 gegen Gold 13.0): Baseline-Kopfzeile nennt randomisiert n=15, Gold 13 ist die Haelfte der 26 Kinder, die die Studie abgeschlossen haben.
  Zeile 6: `------------------------------------------------------------------- --------------------------- -------------------------- -----------`
- `yun2024:420` intervention_group_size (intervention, Regel 44.0 gegen Gold 18.0): Kopfzeile der Baseline-Tabelle nennt n=44; Gold 18 steht als n=18 in der Outcome-Zeile 'T2w sagittal' der Bildqualitaetstabelle.
  Zeile 10: `----------------------------------------------- ------------------------ ------------------ -----------`
- `yun2024:420` comparator_group_size (comparator, Regel 49.0 gegen Gold 21.0): Kopfzeile der Baseline-Tabelle nennt n=49; Gold 21 steht als n=21 in derselben Outcome-Zeile.
  Zeile 10: `----------------------------------------------- ------------------------ ------------------ -----------`
- `yun2024:421` intervention_group_size (intervention, Regel 44.0 gegen Gold 30.0): Kopfzeile der Baseline-Tabelle nennt n=44; Gold 30 steht als n=30 in der Outcome-Zeile fuer die Brustwirbelsaeule.
  Zeile 10: `----------------------------------------------- ------------------------ ------------------ -----------`
- `yun2024:421` comparator_group_size (comparator, Regel 49.0 gegen Gold 34.0): Kopfzeile der Baseline-Tabelle nennt n=49; Gold 34 steht als n=34 in derselben Outcome-Zeile.
  Zeile 10: `----------------------------------------------- ------------------------ ------------------ -----------`
- `yun2024:451` intervention_group_size (intervention, Regel 104.0 gegen Gold 99.0): Die Tabellenunterschrift nennt I; n=104, Gold 99 ist die Auswertungsgroesse der MVPA-Zeile; sie steht nicht als n im Dokument.
  Zeile 117: ``
- `yun2024:451` comparator_group_size (comparator, Regel 114.0 gegen Gold 108.0): Die Tabellenunterschrift nennt C; n=114, Gold 108 ist die Auswertungsgroesse der MVPA-Zeile; sie steht nicht als n im Dokument.
  Zeile 117: ``

## Richtige Zellen

| Record | Feld | Arm | Wert | Gold |
|---|---|---|---:|---:|
| `yun2024:446` | intervention | intervention | 104.0 | 104.0 |
| `yun2024:446` | comparator | comparator | 114.0 | 114.0 |
| `yun2024:678` | intervention | intervention | 16.0 | 16.0 |
| `yun2024:678` | comparator | comparator | 15.0 | 15.0 |
