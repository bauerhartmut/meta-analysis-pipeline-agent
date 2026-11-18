# Spaltenrollen aus dem Zeilenlabel (18.11.2026)

Offline geprüft, kein Netz, kein Modellaufruf. Ergebnis vorweg: die Ableitung ist
umgesetzt und getestet, schaltet auf dem eingefrorenen Material aber **keine**
zusaetzliche Goldzelle frei. Der Grund ist belegt und steht unten.

## Umsetzung

- `semantics.row_roles(label)`: `Mean (SD)` -> `mean` + `sd`, `Not complying,
  n (%)` -> `events`, `n` -> `n`. Neue Felder `Row.value_role` /
  `Row.secondary_role`; gesetzt in `enrich_table` aus dem letzten Element des
  Zeilenlabel-Pfads (Gruppenzeilen ausgenommen).
- `semantics.row_fields(table, row)`: Felder einer Zeile - Spaltenfeld zuerst;
  die Zeilenrolle greift **nur**, wenn die Spalte die Rolle `unknown` hat und die
  Zelle eine Zahl traegt.
- `reconstruct.Reconstruction._resolve_field`: dieselbe Regel fuer den Beleg;
  `_add_secondary` nimmt die Zweitrolle aus Spaltenkopf **oder** Zeilenlabel.
- Validierung meldet `rolle_aus_zeilenlabel` (Info), wenn Zeilenrollen vorliegen.

Tests: 2 neu (`Row.value_role` inklusive Reichweite, Werte in der Vorhersage),
45 gruen.

## Offline-Pruefung an den betroffenen Tabellen

**`PMC4319071:T1` (Records `yun2024:111/112`).** 9 Zeilen tragen jetzt eine
Rolle: 5x `Mean (SD)` (Zeilen 19, 22, 25, 28 und 1 `Age (years), mean (SD)`) und
4x `Not complying, n (%)` (20, 23, 26, 29). Fokus ist `[19, 20]`, erwartbar
bleibt aber genau **eine** Zelle: `comparator_group_size` (Kopf-Fakt 434).

Grund, mit Beleg: die Wertspalten dieser Tabelle liegen nicht unter den
Armkoepfen. In Zeile 13 (`Age ...`) beginnt die erste Zahl bei x=98, in Zeile 19
(`Mean (SD)`) bei x=120 - bei denselben Regelspalten (99-121, 122-138, ...).
Die Markdown-Zeilen sind also unterschiedlich umbrochen; es gibt kein
einheitliches Spaltenraster. Zusaetzlich ist `Plus` im Record nicht benannt
(Intervention heisst `Intervention + targeting environmental-level factors`),
also bleibt der Interventionsarm ungebunden.

**`PMC4319071:T2` ist die eigentliche Quelle der Gold-Mittelwerte.** `158.67`
steht in Zeile 107 (`Control ... 158.67 (3.76)`), `167.61` in Zeile 113
(`Plus ... 167.61 (3.92)`). Dort sind die **Arme Zeilenlabels**, und die
Spalten sind Outcomes. Genau umgekehrt zur hier gebauten Ableitung: T2 hat
0 Zeilenrollen und 0 Armspalten. Zusaetzlich verliert der Parser die
Outcome-Kopfzeile (Zeile 81, `Time point | Fruit (pieces) | Vegetables (grams)
| ...`) an die Prosa-Erkennung; als Kopf bleiben nur `Mean (SE)` /
`Mean change` uebrig.

## Messung (dev, read-only)

| Groesse | Wert |
|---|---|
| dev-Records mit Gold | 38 |
| Tabellen mit Zeilenrolle | 12 |
| Tabellen mit Armspalte ohne Rolle | 1 |
| Records mit Gewinn an erreichbaren Goldzellen | **0** |
| dev-Offline-Lauf (`offline_dev_zeilenrollen_20261118`) | 5 von 10, unveraendert |

Die beiden Bedingungen treffen fast nie zusammen: wo der Spaltenkopf die Rolle
nicht nennt (Armspalte), steht im Zeilenlabel meist ein Arm oder ein Outcome -
und wo das Zeilenlabel `Mean (SD)` sagt, nennt der Spaltenkopf die Rolle ohnehin.

Im Testsplit (60 ausgewaehlte Tabellen, nur gelesen): 8 Tabellen mit
Zeilenrolle, 9 mit Armspalte ohne Rolle, ebenfalls 0 Records mit Gewinn.

## Testsplit unberuehrt

`selection_test.json` `6539869cf90729c3`, `offline_struktur_20261118`
`03f8997885fad6ed`, `offline_fokus_20261118` `ca2e9369b4c90e81` - vorher und
nachher gleich; kein Testlauf gestartet, keine Testdatei geschrieben.

## Was daraus folgt

Die Zeilenrolle ist nicht der Hebel fuer `PMC4319071`; der Hebel ist
**Arm aus dem Zeilenlabel** (T2: `Control`/`Basic`/`Plus` als Zeilen) plus
Outcome-Spalte aus dem Kopf (`Vegetables (grams)`) und ein Prosa-Guard, der
Kopfzeilen mit vielen Woertern nicht verwirft. Die Zeilenrollen bleiben drin:
sie sind korrekt, markiert und greifen, sobald eine Tabelle ihre Wertspalten
unter den Armkoepfen hat.
