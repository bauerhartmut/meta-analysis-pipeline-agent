# Ursachen der falschen Groessenzellen (21.11.2026)

Offline, ohne Netzaufruf. `groessen_ursachen_20261121.py`. Grundlage ist
die Lueckenfuellung ohne Mittel ueber alle 699 Records, gemessen auf den
103 P5-Records. Gelesen wird dreimal: ohne Kopfband-Regel (`aus`),
mit Armkuerzel (`kuerzel`, z. B. `I; n=104`) und mit Armbezeichnung
(`arm`, z. B. `Control group (n=15)`).

| Stand | Groessenzellen | richtig | falsch |
|---|---:|---:|---:|
| aus | 16 | 4 | 12 |
| kuerzel | 4 | 2 | 2 |
| arm | 14 | 4 | 10 |

Von den 12 falschen Zellen entfallen mit `kuerzel` 10 und mit `arm` 2.

## Zahlen je Ursache

| Ursache | Zellen | entfallen `kuerzel` | entfallen `arm` |
|---|---:|---:|---:|
| falsche_zeile | 5 | 5 | 2 |
| abweichende_definition | 7 | 5 | 0 |
| rechenfehler | 0 | 0 | 0 |

## Zellen

| Record | Feld | Arm | Wert | Gold | Belegzeile | Beleg | Ursache | `kuerzel` | `arm` |
|---|---|---|---:|---:|---:|---|---|---|---|
| `yun2024:159` | intervention | intervention | 24.0 | 592.0 | 3 | unterschrift | falsche_zeile | entfaellt | 24.0 falsch |
| `yun2024:251` | intervention | intervention | 406.0 | 402.0 | 60 | n-form | abweichende_definition | entfaellt | 406.0 falsch |
| `yun2024:251` | comparator | comparator | 393.0 | 388.0 | 60 | n-form | abweichende_definition | entfaellt | 393.0 falsch |
| `yun2024:252` | intervention | intervention | 398.0 | 402.0 | 10 | n-form | abweichende_definition | entfaellt | 398.0 falsch |
| `yun2024:252` | comparator | comparator | 389.0 | 388.0 | 10 | n-form | abweichende_definition | entfaellt | 389.0 falsch |
| `yun2024:356` | comparator | comparator | 15.0 | 13.0 | 6 | n-form | abweichende_definition | entfaellt | 15.0 falsch |
| `yun2024:420` | intervention | intervention | 44.0 | 18.0 | 10 | n-form | falsche_zeile | entfaellt | entfaellt |
| `yun2024:420` | comparator | comparator | 49.0 | 21.0 | 10 | n-form | falsche_zeile | entfaellt | 20.0 falsch |
| `yun2024:421` | intervention | intervention | 44.0 | 30.0 | 10 | n-form | falsche_zeile | entfaellt | entfaellt |
| `yun2024:421` | comparator | comparator | 49.0 | 34.0 | 10 | n-form | falsche_zeile | entfaellt | 20.0 falsch |
| `yun2024:451` | intervention | intervention | 104.0 | 99.0 | 96 | n-form | abweichende_definition | 104.0 falsch | 104.0 falsch |
| `yun2024:451` | comparator | comparator | 114.0 | 108.0 | 96 | n-form | abweichende_definition | 114.0 falsch | 114.0 falsch |

## Begruendung je Zelle

- `yun2024:159` intervention_group_size (intervention, Regel 24.0 gegen Gold 592.0): Die 24 stammt aus der Bildunterschrift 'at baseline, 12 and 24 months'; Gold 592 steht in der Armzeile 'Intervention (n=592)' der 12-Monats-Spalte.
  Beleg Zeile 3 (unterschrift): `###### Sample characteristics at baseline, 12 and 24 months for students who provided adiposity outcome measures`
- `yun2024:251` intervention_group_size (intervention, Regel 406.0 gegen Gold 402.0): Kopfzeile nennt randomisiert n=406, die Outcome-Zeile rechnet mit 42/402; Gold nimmt die 402.
  Beleg Zeile 60 (n-form): `Outcome                                              Progesterone *n* = 406   Placebo *n* = 393   Unadjusted Treatment Effect for Progesterone versus Placebo (9`
- `yun2024:251` comparator_group_size (comparator, Regel 393.0 gegen Gold 388.0): Kopfzeile nennt randomisiert n=393, die Outcome-Zeile rechnet mit 41/388; Gold nimmt die 388.
  Beleg Zeile 60 (n-form): `Outcome                                              Progesterone *n* = 406   Placebo *n* = 393   Unadjusted Treatment Effect for Progesterone versus Placebo (9`
- `yun2024:252` intervention_group_size (intervention, Regel 398.0 gegen Gold 402.0): Charakteristika-Tabelle nennt randomisiert n=398, Gold 402 ist der Nenner der Outcome-Zeilen.
  Beleg Zeile 10 (n-form): `Characteristic                                      Progesterone (*n* = 398)   Placebo (*n* = 389)`
- `yun2024:252` comparator_group_size (comparator, Regel 389.0 gegen Gold 388.0): Charakteristika-Tabelle nennt randomisiert n=389, Gold 388 ist der Nenner der Outcome-Zeilen.
  Beleg Zeile 10 (n-form): `Characteristic                                      Progesterone (*n* = 398)   Placebo (*n* = 389)`
- `yun2024:356` comparator_group_size (comparator, Regel 15.0 gegen Gold 13.0): Baseline-Kopfzeile nennt randomisiert n=15, Gold 13 ist die Haelfte der 26 Kinder, die die Studie abgeschlossen haben.
  Beleg Zeile 6 (n-form): `Characteristic                                                      Control group ( *n* =?15)   Active group ( *n* =?16)   *p*Values`
- `yun2024:420` intervention_group_size (intervention, Regel 44.0 gegen Gold 18.0): Kopfzeile der Baseline-Tabelle nennt n=44; Gold 18 steht als n=18 in der Outcome-Zeile 'T2w sagittal' der Bildqualitaetstabelle.
  Beleg Zeile 10 (n-form): `Short-Bore MR (n?=?44)   Open MR (n?=?49)   *P* Value`
- `yun2024:420` comparator_group_size (comparator, Regel 49.0 gegen Gold 21.0): Kopfzeile der Baseline-Tabelle nennt n=49; Gold 21 steht als n=21 in derselben Outcome-Zeile.
  Beleg Zeile 10 (n-form): `Short-Bore MR (n?=?44)   Open MR (n?=?49)   *P* Value`
- `yun2024:421` intervention_group_size (intervention, Regel 44.0 gegen Gold 30.0): Kopfzeile der Baseline-Tabelle nennt n=44; Gold 30 steht als n=30 in der Outcome-Zeile fuer die Brustwirbelsaeule.
  Beleg Zeile 10 (n-form): `Short-Bore MR (n?=?44)   Open MR (n?=?49)   *P* Value`
- `yun2024:421` comparator_group_size (comparator, Regel 49.0 gegen Gold 34.0): Kopfzeile der Baseline-Tabelle nennt n=49; Gold 34 steht als n=34 in derselben Outcome-Zeile.
  Beleg Zeile 10 (n-form): `Short-Bore MR (n?=?44)   Open MR (n?=?49)   *P* Value`
- `yun2024:451` intervention_group_size (intervention, Regel 104.0 gegen Gold 99.0): Die Tabellenunterschrift in Zeile 96 nennt 'I; n=104' (randomisiert), Gold 99 ist die Auswertungsgroesse der MVPA-Zeile; sie steht nicht als n im Dokument.
  Beleg Zeile 96 (n-form): `group (I; n=104) and the control group (C; n=114)`
- `yun2024:451` comparator_group_size (comparator, Regel 114.0 gegen Gold 108.0): Die Tabellenunterschrift in Zeile 96 nennt 'C; n=114' (randomisiert), Gold 108 ist die Auswertungsgroesse der MVPA-Zeile; sie steht nicht als n im Dokument.
  Beleg Zeile 96 (n-form): `group (I; n=104) and the control group (C; n=114)`
