# Sprint 47 - Caption, Gruppenkopf-Zeile und Zielwahl

Stand 18.11.2026. Offline, rein lesend: kein Modelllauf, kein Netz, Gold und
eingefrorene Auswahl unveraendert. Zahlen aus `messung.json` (Skript
`diagnose_gruppenkoepfe.py`).

## Frage

Werden die 10 `population_mismatch`-Felder, deren Zahl in einer anderen Tabelle
desselben Dokuments gedruckt steht, wertgleich - ohne Armumkehr und ohne Gold
zur Steuerung?

## Befund vor der Aenderung

Die beiden in Sprint 46 benannten Parser-Luecken waren groesser als gedacht:

1. **Die beschreibende Caption ging verloren.** `PMC2430617:T4` steht hinter
   einer reinen Bildzeile (`![]()`), `PMC5360580:T6` unter einer blossen
   Zeile `Table 6`. Gelesen wurde in beiden Faellen keine Caption (T4: leer,
   T6: `"Table 6"`). Gedruckt steht dort:
   * `Occurrence of most common adverse events during treatment and follow-up.`
   * `List of reported adverse events.`
2. **Eine Baseline war sehr wohl beschriftet.** `PMC5360580:T1` traegt die
   Caption `Baseline characteristics.` - sie war nur nicht gelesen. Die in
   Sprint 46 empfohlene Regel "Baseline ueber Zeilenlabels" war damit
   gegenstandslos; sie wurde geprueft und verworfen (siehe unten).
3. **Der Gruppenkopf in einer Datenzeile war unsichtbar.** `PMC2430617:T4`
   druckt `Placebo group (N = 79)`, `30 µg YIC group (N = 83)`,
   `60 µg YIC group (N = 80)` in der ersten Datenzeile, nicht im Kopfband.

## Aenderung

* `parser.py`: Caption-Suche ueberspringt reine Bildzeilen (`_skip_over`) und
  liest bei einer blossen `Table N`-Zeile die beschreibende Caption darueber
  (`_is_label_only`, `_caption_above_label`). Von 120 Tabellen tragen jetzt
  **96** eine beschreibende Caption, 24 keine (vorher 65 beschreibend,
  6 nur Bezeichnung, 49 leer).
* `semantics.py`: `_row_group_facts` liest eine Datenzeile als Gruppenkopf,
  wenn **jede** gefuellte Zelle eine Gruppenangabe (`... (N = 79)`) mit
  belegtem Arm ist; sonst bleibt sie Datenzeile. Die Fakten tragen
  `basis="zeile_angabe"` und die Zeilennummer.
* `provenienz.py`: solche Fundstellen heissen `gruppengroesse_in_datenzeile`
  und fuehren die Zeile mit; Kopfangaben aus Baendern bleiben unveraendert.
* `tabellenwahl.py`: die gedruckte Caption zaehlt als Beleg fuer die
  Outcome-Tabelle - aber nur, wenn **keine** Tabelle eine Outcome-Zeile zum
  Outcome traegt (`caption_matches_outcome`).
* Verworfen: Baseline-Erkennung ueber Zeilenlabels (Alter, Geschlecht, MMSE).
  Sie wurde mit und ohne Regel gemessen: identische 9 Wechsel, identische 68
  wertgleiche Felder. Kein Beleg, also keine Regel.

## Ergebnis

| Groesse | Sprint 45 | Sprint 46 | Sprint 47 |
| --- | --- | --- | --- |
| erreichbare Goldfelder | 94 | 94 | 94 |
| wertgleich | 58 | 62 | **68** |
| nicht wertgleich | 36 | 32 | 26 |

* neu wertgleich gegen Sprint 45: **10** Felder, gegen Sprint 46: **6**.
* verloren: **0** Felder (gegen beide Staende).
* Armwechsel: **0**.
* Tabellenwechsel: **9** von 59 Records (60 Tabellen; Sprint 46: 4).
* Von den 15 `population_mismatch`-Feldern werden **10** wertgleich.

Die zehn Felder sind genau die erwarteten: vier aus `PMC4675066` (Sprint 46)
und sechs neue.

| Dokument | Felder | Beleg |
| --- | --- | --- |
| PMC5360580 | 2 | `yun2024:194` wechselt `T1` (Baseline 145/140) nach `T6` (`List of reported adverse events.`, 169/167). |
| PMC2430617 | 4 | `yun2024:265`/`:266` wechseln `T1` (Baseline 78/81/78) nach `T4` (79/83/80 aus der Datenzeile). |

## Was die Zahl belegt - und was nicht

`yun2024:265.intervention_group_size` ist **wertgleich, aber `mehrfach`**: in
`T4` stehen 83 (30 µg) und 80 (60 µg) beide unter dem Arm `intervention`. Der
Goldwert 83 ist woertlich gedruckt, die Dosis trennt das Feldmodell aber nicht -
beide Spalten binden an denselben Arm. Das Feld ist damit wertgleich, ohne
dass die Zuordnung "eine Gruppe, eine Groesse" gilt; ein strengerer Masstab
wuerde es als mehrdeutig fuehren.

Die Ereigniszahlen der beiden Records (3/4 bzw. 4/4) bleiben unerreichbar: sie
stehen nur im Fliesstext (`5.1% (4/79), 3.6% (3/83), 5.0% (4/80)`). Die
Datenzeilen unter dem Gruppenkopf von `T4` liest der Parser weiterhin nicht -
der Tabellenblock endet nach der Kopfzeile. Fuer diese Felder hilft das nicht.

Die fuenf weiterhin nicht wertgleichen `population_mismatch`-Felder
(`PMC4230312` 4, `PMC5122613` 1) brauchen Zahlen aus dem Fliesstext; in keiner
Tabelle stehen sie.

## Nebenwirkungen

Vier weitere Records wechseln ohne Feldwirkung:

* `yun2024:257`/`:258` (`PMC5711682:T1` -> `:T5`, `Clinical outcomes`): T1
  traegt jetzt die Caption `Baseline characteristics.`; die Felder bleiben 2/2
  wertgleich.
* `yun2024:672`/`:675` (`PMC4550271:T1` -> `:T4`/`:T2`): wie in Sprint 46, ihre
  Goldfelder waren vorher nicht erreichbar.

## Grenzen

* Gemessen auf demselben Record-Satz, auf dem die Regel entstanden ist. Die
  Gegenprobe auf unbenutzten Dokumenten steht in
  `../nachpruefung_20261118/ergebnis.md` (26 Tabellen, +2 Felder, 0 verloren).
* Die Caption-Aenderung betrifft 31 Tabellen und damit auch Stellen ausserhalb
  der Tabellenwahl. Sie ist hier nur ueber die 94 Goldfelder und die 130 Tests
  geprueft, nicht ueber einen Modelllauf.
* Die Caption ist ein schwaeherer Beleg als eine Outcome-Zeile und zaehlt nur,
  wenn keine Tabelle eine solche Zeile traegt.
* Kein Goldwert steuert eine Wahl; Gold wird erst in der Auswertung gelesen.

## Empfehlung

**Die Tabellenwahl traegt jetzt 10 von 15 Populationsfeldern ohne einen
einzigen Verlust - aber sie ist noch nicht Produktionsregel.** Vor dem
Anschalten: Gegenprobe auf einem nicht verwendeten Record-Satz (andere
Dokumente, gleiche Regel), und die Caption-Korrektur getrennt als
Parser-Aenderung pruefen, weil sie 31 Tabellen betrifft. Der naechste Hebel mit
dem besten Verhaeltnis sind die fuenf restlichen Felder: eine Zahl, die nur im
Fliesstext steht (`4/79`, `5.1% (3/83)`), als belegte Fundstelle lesen - das ist
ein eigenes Provenienz-Thema, keine Tabellenwahl.
