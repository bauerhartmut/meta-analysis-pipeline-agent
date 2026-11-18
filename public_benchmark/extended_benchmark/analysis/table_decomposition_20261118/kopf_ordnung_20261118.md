# Kopfzellen an den Wertspalten (18.11.2026)

Offline geprüft, kein Netz, kein Modellaufruf, keine Testdatei geschrieben.

## Die Rechtsbuendigkeits-Annahme traegt nicht

Gemessen an `PMC4319071:T2` (Zeilen 81-84 Kopf, 82 Strichraster, 88/107 Daten):

- Strichraster: 10 Spalten, Starts 2, 26, 43, 64, 94, 123, 141, 155, 174, 189;
  Spalte 3 endet bei 93.
- Wert `158.93 (3.31)` steht ab x=93 und laeuft bis 105 - er beginnt also am
  Spaltenende und ragt in die Folgespalte.
- Kopfzelle `Vegetables (grams)` steht bei x=43, dem **Anfang** von Spalte 2.
- Die Datenzeilen streuen um 1-3 Zeichen (Zeile 88 ab 25/42/63/93, Zeile 107 ab
  25/42/63/92, Zeile 113 ab 26/43/64/93).

Kopf und Raster sind damit um eine Spalte versetzt, und die Zellenden fallen
nicht mit den Spaltenenden zusammen. Eine Zuordnung ueber x-Positionen ist in
dieser Quelle nicht belegbar.

## Was stattdessen umgesetzt ist

`parser._reassign_header_bands_by_order`: nur wenn die Kopfgeometrie bereits als
unaufloesbar notiert ist (`header_gruppe_nicht_teilbar` usw.), werden die
Kopfebenen **ordinal** den Wertspalten zugeordnet. Wertspalten sind die Spalten
mit mindestens einer Zahl.

- `M == Anzahl Wertspalten`: eine Kopfzelle je Wertspalte.
- `M-1` teilt die Anzahl Wertspalten: erste Zelle ans Zeilenlabel, der Rest als
  gleiche Gruppen (`Time point | Fruit | Vegetables | ...` -> 4 Gruppen zu je 2).
- Sonst bleibt die Ebene unzugeordnet (`kopf_ebene_ohne_spalte`) - keine
  erfundene Spanne.

Zellen und Spalten werden **nicht** umnummeriert; die Notfall-Codes werden
entfernt und durch `spalten_ordnung:kopf_nach_wertspalten` ersetzt. Fuer `T2`
wird die CI-Ebene (4 Zellen bei 8 Wertspalten) deshalb nicht zugeordnet; die
Change-Spalten tragen Rolle `mean` ohne Feld, was folgenlos ist.

Test: `test_header_bands_are_reassigned_to_value_columns`; 50 Tests gruen.

## Vorher/Nachher

**`PMC4319071:T2` (Testrecords `yun2024:111` und `yun2024:112`, read-only):**

| Feld | vorher | nachher |
|---|---|---|
| `comparator_mean` (`yun2024:112`) | nicht erreichbar (`outcome_spalte_ohne_kopfgeometrie`) | erreichbar, Zelle Zeile 12 / Spalte 4 = `158.67 (3.76)` = **Gold** |
| `comparator_mean` (`yun2024:111`) | nicht erreichbar | erreichbar, Zelle Zeile 12 / Spalte 6 = `2.84 (0.13)` = **Gold** |
| `comparator_group_size` (`T1`) | erreichbar | erreichbar (unveraendert) |
| `intervention_mean` / `_sd` | nicht erreichbar | nicht erreichbar |

Der Interventionsarm `Plus` ist im Record nicht benannt (`Intervention +
targeting environmental-level factors`), deshalb bleibt er ungebunden; die
Gold-Werte 167.61 / 2.5 und die Streuungen (Gold 83.71 / 2.76) bleiben aussen
vor. Das ist die ehrliche Grenze, kein Parserfehler.

**dev (38 Records mit Gold, alle Tabellen):**

| Groesse | vorher | nachher |
|---|---|---|
| Tabellen | 134 | 134 |
| erreichbare Goldfelder | 16 | **16** |
| Records mit mindestens einem Treffer | 5 | 5 |
| Tabellen mit Kopf-Ordnung | - | 1 (`PMC3751573:T3`) |

Kein Verlust, kein Gewinn auf dev; die Neuordnung greift dort nur einmal und
aendert die Reichweite nicht. Artefakt:
`dev_reichweite_kopf_ordnung_20261118.json`.

## Testartefakte unberuehrt

`selection_test.json` `6539869cf90729c3`, `offline_struktur_20261118`
`03f8997885fad6ed`, `offline_fokus_20261118` `ca2e9369b4c90e81` - vorher und
nachher gleich; kein Testlauf gestartet, keine Testdatei geschrieben.

## Naechster Schritt

Beide `PMC4319071`-Records tragen jetzt ihren Comparator-Mittelwert; es fehlt
der Interventionsarm. Hebel: Armnamen aus dem **Dokument** belegen (die
Strichkopfzeile von `T1` nennt `Basic`/`Plus`, `T2` fuehrt sie als Zeilen) statt
nur aus dem Record-Text - als `arm_basis="dokument"` markiert und in der
Validierung gezaehlt. Vorher lohnt kein Modelllauf: ohne Arm kein Feld.
