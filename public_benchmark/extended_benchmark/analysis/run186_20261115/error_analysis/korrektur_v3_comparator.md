# Korrektur des Comparators und zweier Goldzellen (Version 3 der Testbasis, 16.11.2026)

## Anlass

Der Hauptlauf meldete für die sieben MCCB-Records `yun2024:289`–`295` in allen
14 Komparatorzellen die Werte des Interventionsarms vor dem Training, während
das Gold die TAU-Gruppe nach dem Training führt. Die Prüfung am Artikel
(`comparator_pruefung.md`) ergab: Das Paper randomisiert auf **drei** Arme
(FAT, CE, TAU), es gibt keinen Arm „baseline", und alle sieben Goldwerte stehen
in der Zeile `TAU Post`. Falsch war also die Vorgabe im Record, nicht das Gold.

Beim Spaltenvergleich fielen zwei weitere Goldzellen auf, die nicht zu ihrer
Spalte passen.

## Befund im Artikel (PMC4215531)

Tabellen-Caption: „… for the seven MCCB domains before (pre) and after (post)
intervention period for the three schizophrenia patients group (*n* = 19 per
group)", Fußnote: „FAT: facial affect training, CE: cognitive exercise, TAU:
treatment as usual; pre: before intervention onset; post: after 4-week
intervention period".

```
FAT Post  44.6 ± 12.2  38.5 ± 11.8  48.2 ± 9.2  47.1 ± 10.0  49.4 ± 14.0  47.9 ± 8.8  39.3 ± 10.4  41.6 ± 11.5
TAU Post  48.2 ± 12.3  41.3 ± 10.1  50.8 ± 12.1  47.3 ± 10.4  46.5 ± 9.8   45.4 ± 7.7  42.8 ± 11.7  43.3 ± 10.8
```

Spalten: Processing speed, Attentional vigilance, Working memory, Verbal
learning, Visual learning, Reasoning, Social cognition, Overall composite.

## Änderung

| Record(s) | Feld | alt | neu | Beleg |
|---|---|---|---|---|
| 289–295 | `context.comparator` | `baseline` | `treatment as usual (TAU)` | Abstract: drei Arme; Tabelle `TAU Post` |
| 291 | `intervention_standard_deviation` | 12,8 | **14,0** | Zeile `FAT Post`, Spalte Visual learning: 49,4 ± 14,0 |
| 294 | `comparator_mean` | 46,5 | **45,4** | Zeile `TAU Post`, Spalte Reasoning (6) |
| 294 | `comparator_standard_deviation` | 9,8 | **7,7** | dito: 45,4 ± 7,7 |

Die 12,8 aus 291 ist der SD des **Pre**-Werts derselben Spalte (FAT Pre:
42,8 ± 12,8) — Mittelwert aus Post, SD aus Pre. Die 46,5 ± 9,8 aus 294 ist
Spalte 5 (Visual learning) von `TAU Post`, nicht Spalte 6 (Reasoning).

Umgesetzt an zwei Stellen im Annotationsskript, damit eine Neuerzeugung die
Korrekturen nicht verliert: `GOLD_KORREKTUREN` (Goldwerte) und der neue
`KONTEXT_KORREKTUREN` (Felder der Vorgabe; ändert den Prompt, nicht das Gold).
Die Quelle `yun_test76_ohne_ziel.jsonl` bleibt unverändert.

## Prüfung

Nach dem Neuerzeugen verglichen, Record für Record:

* **10 Änderungen**, alle beabsichtigt: 7 × `context.comparator`, 1 ×
  `intervention_standard_deviation` (291), 1 × `comparator_mean` und 1 ×
  `comparator_standard_deviation` (294).
* Unverändert: Reihenfolge der 76 Records, alle Zielzeitpunkte, 243 Goldzellen,
  Zellschlüssel und Armzuordnungen.
* Gegenprobe der Erzeugung: Ein Lauf ohne die neuen Korrekturen schreibt die
  Datei byte-identisch zur Version 2 zurück (Hash `74fd0c05…`), die Pipeline ist
  also reproduzierbar und die Änderung stammt allein aus den Korrekturen.

## Hashes

* Version 1: `06fea97c37864debe50f130f03a926f5fb5654a1cd0d2ef75ab330da04ad0ca7`
* Version 2: `74fd0c057356c22831fae45d71644d8b7640a8a109fb48a60cc7782cfb1db704`
* **Version 3: `3f811bed35653bda0da92a5ab13dc16a13a23dfc79c04a0808b0d2ec8267b587`**

## Tests

* `test_datei_hat_den_eingefrorenen_hash` trägt den neuen Hash.
* `test_comparator_von_289_bis_295_ist_tau` prüft Feld und Zielzeitpunkt der
  sieben Records.
* `test_gold_zellen_von_291_und_294_sind_korrigiert` prüft die drei Goldwerte
  samt den unveränderten Nachbarwerten.
* `test_korrekturen_ueberleben_eine_neuerzeugung` prüft beide
  Korrekturtabellen im Annotationsskript.

## Folgen für den Hauptlauf

Der Lauf `test76_hauptlauf_20261116` bleibt auf **Version 2** und wird nicht
wiederholt: Die 14 Komparatorzellen zählen dort weiter als falsch, weil die
Vorgabe sie verlangte. Die Kennzahlen des Berichts (F1 0,5455, Precision 0,7394,
Recall 0,4321, MAE 0,5763) sind damit Version-2-Zahlen und nicht mit Version 3
vergleichbar. Ob das Modell mit dem korrigierten Feld die TAU-Werte extrahiert,
war offen; der freigegebene Teillauf über 289–295 hat es geprüft:
**14 von 14 Komparatorzellen richtig**, 41 von 42 Zellen des Teillaufs
(24.768 Tokens, `v3_comparator_289_295.md`). Die einzige Abweichung ist ein
weiterer Gold-Fehler (295: SD 11,1 statt 10,4), der eine Version 4 braucht.
