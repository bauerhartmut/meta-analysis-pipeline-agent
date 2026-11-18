# Erwartete Zellen: Kopf, Gruppengroesse, Outcome-Zeile (18.11.2026)

Offline-Pruefung, kein Netzlauf, kein Modellaufruf. Anlass: Der Pilotlauf
`modell_glm53_abe_20261118` lieferte in 5 Zeilen 0 richtige Zellen; die
erwarteten Zellen stammten aus falsch zusammengesetzten Kopfzeilen. Vor dem
naechsten bezahlten Lauf wurden die drei Ursachen ohne Netz behoben.

## Drei Reparaturen

**(1) Kopfzeilen mischen keine Zeilenlabels mehr.** Vergleichszeilen wie
`Basic vs control` standen an Kopfposition und wurden als Spaltenkopf gelesen;
damit bekam die erste Spalte einen falschen Header-Pfad und einen falschen Arm.
Solche Zeilen sind jetzt weder Kopf noch Datenzeile, sondern werden als
`kopfzeile_ist_zeilenlabel` notiert. Fette Zeilengruppen (`**Dietary intake**`)
beenden die Tabelle nicht mehr, sondern bilden den Zeilen-Label-Pfad
(`Table.rows[].label_path`).

**(2) Gruppengroessen aus dem Kopf sind Kopf-Fakten.** `n = 434` erzeugte
vorher eine Spalte mit Rolle `n` und damit das Feld `comparator_group_size`;
der Extraktor las daraus `49.05` (Zeile `Age (years)`). Jetzt steht der Wert in
`Table.header_facts` (Wert, Spanne, Arm, falls belegbar), die reine
Kopfangabe faellt aus Header-Pfad und Rollenbestimmung heraus. Eine Spalte mit
Rolle `n` entsteht daraus nicht mehr.

**(3) Erwartet werden nur Zellen der Outcome-Zeile.** Neu:
`semantics.outcome_rows(table, outcome)` (Label-Pfad, beidseitiger
Token-Abgleich, Pluralnormalisierung, keine Goldwerte) und
`semantics.reachable_cells(table, context)` = Spaltenfeld **und** Outcome-Zeile.
Der Benchmark zaehlt nur noch diese Zellen (`focus_rows` je Record), und
`PlanOptions.focus_outcome=True` begrenzt den Auftrag auf die Outcome-Zeile;
die uebrigen Zeilen laufen als Kontext mit. Standard der Engine bleibt `False`,
die produktive Pipeline ist unveraendert.

## Fall `PMC4319071:T1` (vorher/nachher)

| Groesse | vorher | nachher |
|---|---|---|
| gelesene Zeilen | 1 | 30 (davon 10 Gruppenzeilen) |
| Kopf-Baender mit `vs` | 3 | 0 |
| Spalten mit Rolle `n` | 3 | 0 |
| Kopf-Fakten | keine | `n=1349` (Total), `n=434` (comparator), `n=459` (Basic), `n=456` |
| Fokus-Zeilen `Vegetable intake` | keine | `Dietary intake > Vegetable intake (grams) > Mean (SD)` sowie `Not complying, n (%)` |

`n=456` ist als Fakt gefuehrt, aber **ohne Arm**: der Record nennt als
Intervention `Intervention + targeting environmental-level factors`, die
Tabelle nur `Plus`. Ohne Namensbeleg wird nichts gebunden.

Die Wertspalten dieser Tabelle tragen keine Rolle im Kopf (Mittelwerte stehen
im Zeilenlabel `Mean (SD)`), deshalb ist fuer diesen Record weiterhin 0 Zellen
erreichbar - ehrlich gezaehlt statt ueber die Zeile `Age (years)` erraten.
Naechster noetiger Schritt: Rollen aus dem Zeilenlabel (`Mean (SD)`,
`Not complying, n (%)`), nicht nur aus dem Spaltenkopf.

## Messung auf dem eingefrorenen Testsplit (60 Tabellen, 59 Records)

`offline_struktur_20261118` (alt: Feld in irgendeiner Zeile) gegen
`offline_fokus_20261118` (neu: Feld **und** Outcome-Zeile):

| Var | Einheiten/Record alt -> neu | Zeichen/Record alt -> neu | Tokens ges. (Schaetzung) alt -> neu | Gold erreichbar alt -> neu |
|---|---|---|---|---|
| A | 1,02 -> 1,02 | 5.745 -> 6.161 | 84.733 -> 90.872 | 95 -> 21 |
| B | 2,81 -> 2,44 | 10.700 -> 10.069 | 157.828 -> 148.523 | 95 -> 21 |
| E | 4,95 -> 4,46 | 20.019 -> 18.174 | 295.279 -> 268.059 | 95 -> 21 |

Alle 60 Tabellen strukturell vollstaendig, 0 Validierungsfehler (unveraendert).
Die alte Zahl 95/278 (34,2 %) war eine Obergrenze ueber alle Zeilen; die neue
Zahl 21/278 (7,6 %) ist die Obergrenze fuer die Zeile, die der Record meint.

## Wohin die restlichen Zellen verschwinden (59 Records)

| Befund | Records |
|---|---|
| ausgewaehlte Tabelle trifft die Outcome-Zeile | 12 |
| Feld vorhanden, Outcome-Zeile nicht erkannt (Abkuerzung/Synonym, z. B. `IP-10` vs `Interferon gamma-induced protein 10`) | 29 |
| Auswahl verfehlt: eine **andere** Tabelle des Dokuments traegt die Outcome-Zeile | 8 |
| Dokument enthaelt keine Tabelle mit der Outcome-Zeile | 10 |

Die 8 Auswahlverfehlungen sind mit je einer Besseren im Dokument belegt
(Beispiele: `yun2024:196` PMC5360580:T1 statt T6, `yun2024:257`/`258`
PMC5711682:T2/T5 statt T1, `yun2024:489` PMC3786549:T1 statt T3). Die
Auswahl wurde am 18.11. mit der alten, zeilenblinden Reichweite eingefroren
(Hash `c22ed3fb...`); sie neu zu ziehen aendert den Benchmark-Satz und braucht
eine eigene Entscheidung.

## Nicht gemacht

- Kein Modelllauf (keine Precision/Recall/Kosten); Netzlauf braucht Freigabe.
- Keine Neueinfrierung der Auswahl.
- Keine Rollen aus Zeilenlabels (der Grund, warum `PMC4319071:T1` weiter 0
  Zellen beitraegt).

## Reproduktion

```
python -m pytest research_agent/tests/test_table_decomposition.py \
    public_benchmark/tests/test_table_decomposition_benchmark.py -q

python public_benchmark/extended_benchmark/table_decomposition/run_benchmark.py \
    --strategies A B E --run-id offline_fokus_20261118
```
