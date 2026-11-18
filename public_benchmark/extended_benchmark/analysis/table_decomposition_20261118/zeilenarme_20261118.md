# Arme als Zeilen, Outcome als Spalte (18.11.2026)

Offline geprüft, kein Netz, kein Modellaufruf, keine Testdatei geschrieben.

## Umsetzung

- **Prosa-Guard** (`parser._looks_prose`): eine Zeile aus mindestens drei kurzen
  Zellen (je hoechstens vier Woertern) ist ein Tabellenkopf, keine Prosa. Vorher
  galt `Time point | Fruit (pieces) | Vegetables (grams) | ...` als Prosa und
  wurde verworfen - damit fehlte der Spalte ihr Outcome-Name.
- **Arm aus dem Zeilenlabel** (`semantics.bind_row_arm`, `Row.arm`/
  `arm_basis`): gilt nur bei belegtem Vorsprung, Schwelle 0.6 statt 0.5, weil
  Zeilenlabels kurz sind (`Apple Juice` teilt mit `White Grape Juice (WGJ)` nur
  `juice` und ist ein dritter Arm; `Water` gegen `colored and flavored water
  (WA)` trifft das ganze Label).
- **Outcome-Spalte aus dem Kopf** (`_mark_outcome_columns`, `Column.is_outcome`):
  Abgleich nur in Vorwaertsrichtung (alle Outcome-Woerter im Kopf), sonst haette
  `6 months follow-up` das Outcome `continued antidepressants until the 6-month`
  getroffen. Bei mehreren Spalten mit gleichem Outcome und gleicher Rolle gilt
  die zuerst gedruckte, der Rest wird als `outcome_spalte_mehrdeutig` notiert.
- **Geometrie-Guard** (`header_geometry_trustworthy`): ist die Kopfspanne nur
  notduerftig verteilt (`header_gruppe_nicht_teilbar`, `header_ohne_spalte`,
  `header_ueberzaehlig_ohne_spalte`, `header_doppelter_anker`), wird keine
  Spalte zum Outcome erklaert (`outcome_spalte_ohne_kopfgeometrie`).
- **SE ist keine Streuung**: `_detect_combined_columns` ueberspringt Kanaele mit
  `(SE)`/`(95% CI)` im Kopf. Vorher waere `3.31` aus `158.93 (3.31)` als
  Standardabweichung gefuehrt worden.
- Rekonstruktion und Reichweite nutzen dieselbe Regel (`cell_arm`,
  `_resolve_field`, `_add_secondary`, `row_fields`, `reachable_cells`,
  `reachable_fields`); Validierung meldet `arm_aus_zeilenlabel`.

Tests: 4 neu, 49 gruen.

## dev-Messung (38 Records mit Gold, alle Tabellen)

| Groesse | alt | nur Prosa-Fix | neu |
|---|---|---|---|
| Tabellen | 134 | 134 | 134 |
| erreichbare Goldfelder | 12 | 12 | **16** |
| Records mit mindestens einem Treffer | 5 | 5 | 5 |

Einziger Unterschied: `yun2024:5` (`PMC1216327:T5`, Arme als Zeilen) gewinnt
`intervention_mean`, `intervention_standard_deviation`, `comparator_mean` und
`comparator_standard_deviation`. Die gedruckten Werte stimmen exakt mit dem Gold
ueberein: Zeile `White Grape Juice` 3.59 / 2.35, Zeile `Water` 2.19 / 1.63.
`Apple Juice` (dritter Arm) bleibt ohne Arm, statt ein konkurrierendes Feld zu
erzeugen; `First Day Losses` wird als mehrdeutig verworfen, gelesen wird
`Total Losses`.

Artefakt: `dev_reichweite_zeilenarme_20261118.json`; Matcher:
`dev_outcome_matching_zeilenarme_20261118.json` (`trifft` 3 -> 4).

## `PMC4319071:T2`: Kopfzeile gerettet, Zuordnung verweigert

Der Prosa-Fix wirkt: die Bands sind jetzt `Time point`, `Fruit (pieces)`,
`Vegetables (grams)`, `High-energy snacks (pieces)`, `Saturated fat (fat
points)`. Die Zuordnung zur Wertspalte ist aber nicht belegt:

- Strichraster (Zeile 82): 10 Spalten, Startpunkte 2, 26, 43, 64, 94, 123, 141,
  155, 174, 189.
- Kopf `Vegetables (grams)` steht bei x=43, also am **Start** der dritten Spalte.
- Der Wert `158.93` steht rechtsbuendig bei x=93, also in der **vierten** Spalte;
  `158.67` (Gold) ebenso bei x=92, waehrend die Spalte unter dem Kopf `2.00`
  traegt.

Kopf und Raster sind in dieser Quelle um eine Spalte verschoben; der Parser
notiert `header_gruppe_nicht_teilbar:ebene0`. Deshalb bleibt es bei
`outcome_spalte_ohne_kopfgeometrie`: **keine** Zuordnung, kein geratener Wert.
`T1` liefert unveraendert nur `comparator_group_size`.

## Testsplit unberuehrt

`selection_test.json` `6539869cf90729c3`, `offline_struktur_20261118`
`03f8997885fad6ed`, `offline_fokus_20261118` `ca2e9369b4c90e81` - vorher und
nachher gleich; kein Testlauf, keine Testdatei geschrieben. Die `T2`-Pruefung
war read-only auf dem Dokumentstext.

## Naechster Schritt

Kopfzellen an den **Datenzellen** ankern statt am Strichraster (die Werte sind
rechtsbuendig; ihr Zellende faellt mit dem Spaltenende zusammen). Damit liessen
sich verschobene Kopfzeilen wie in `PMC4319071:T2` belegen, ohne zu raten - und
erst danach lohnt ein Pilotlauf und eine neue Auswahl-Einfrierung.
