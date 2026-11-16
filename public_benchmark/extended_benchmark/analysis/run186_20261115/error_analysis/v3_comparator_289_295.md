# Vergleichslauf Version 3 über die sieben MCCB-Records (16.11.2026)

Freigabe: Lauf nur über `yun2024:289`–`295` auf Version 3 der Testbasis
(`3f811bed…`), mit `--repair` und `--split test`.

## Befehl und Kosten

```
run_extended_extraction.py --models glm --split test \
  --records records/yun_test76_ziel.jsonl \
  --ids yun2024:289,…,yun2024:295 \
  --cell-timepoint --target-fallback --group-size-mode aus \
  --repair --max-tokens 19000 --workers 3 \
  --run-id v3_comparator_289_295_20261116 --quelle v3_comparator
```

Run-ID `v3_comparator_289_295_20261116`. **24.768 Completion-Tokens** für 7
Records (3.538 je Record), 7 von 7 Aufträgen mit `ok`, keine 503-Wiederholungen,
keine technischen Ausfälle, keine leeren Antworten. Reparaturpfad wurde nicht
gebraucht.

## Ergebnis: 14 von 14 Komparatorzellen richtig

```
yun2024:289  comparator_mean 48.2 / SD 12.3   Gold 48.2 / 12.3
yun2024:290  comparator_mean 41.3 / SD 10.1   Gold 41.3 / 10.1
yun2024:291  comparator_mean 46.5 / SD  9.8   Gold 46.5 /  9.8
yun2024:292  comparator_mean 50.8 / SD 12.1   Gold 50.8 / 12.1
yun2024:293  comparator_mean 47.3 / SD 10.4   Gold 47.3 / 10.4
yun2024:294  comparator_mean 45.4 / SD  7.7   Gold 45.4 /  7.7
yun2024:295  comparator_mean 42.8 / SD 11.7   Gold 42.8 / 11.7
```

**14/14** — im Hauptlauf auf Version 2 waren genau diese 14 Zellen falsch
(Modell: `FAT Pre`). Der Hebel war die Vorgabe, nicht der Prompt: Mit
`comparator: "treatment as usual (TAU)"` liest das Modell die Zeile `TAU Post`,
ohne dass ein Prompt-Zusatz nötig ist. Der im November gebaute und wieder
entfernte Armzeilen-Zusatz hätte das nicht geleistet (0/10).

Über alle 42 Zellen des Teillaufs: **41 richtig, 1 falsch** → Precision 0,9762
(Rückfall-Bucket), Abdeckung 42 von 243 Zellen der Gesamtbasis (Teillauf, nicht
mit dem Hauptlauf vergleichbar).

## Einzige Abweichung: Gold von 295 trägt den Pre-SD

| Record | Feld | Gold | Modell | Artikel |
|---|---|---|---|---|
| 295 | `intervention_standard_deviation` | 11,1 | **10,4** | `FAT Post` Spalte 7: 39,3 ± **10,4**; `FAT Pre` Spalte 7: 39,3 ± **11,1** |

Der Mittelwert 39,3 steht in beiden Zeilen, nur der SD unterscheidet sie — das
Gold hat den Pre-SD erwischt, das Modell den Post-SD. Dieselbe Verwechslung wie
bei 291 (dort in Version 3 korrigiert). **Das Gold ist hier falsch, nicht das
Modell**; die Zelle ist in Version 3 unverändert und sollte in einer Version 4
auf 10,4 gesetzt werden.

## Befund zum Zielzeitpunkt-Bucket

Alle 42 Zellen landen im Bucket `rueckfall`, weil `_kanonisch` in
`evaluate_fallback.py` nur Baseline-Synonyme kennt:

```
_kanonisch("post (after 4-week training)") -> unverändert
klassifiziere("post (after 4-week training)", "Post") -> "rueckfall"
```

Die sieben Records können damit nie „zieltreu" werden, obwohl das Modell den
Zeitpunkt korrekt als `post: after 4-week intervention period` bzw. `Post`
meldet. Für die Komparatorzählung ist das folgenlos, für die
Zieltreue-Kennzahl aber irreführend. Nicht geändert.

## Grenzen

* Sieben Records, ein Modell (`glm`), ein Lauf. Keine Aussage über die übrigen
  69 Records der Basis.
* Die Precision 0,9762 gilt für diesen Teillauf; sie ist keine neue
  Gesamtkennzahl und ersetzt den Hauptlauf nicht.
* Der Lauf prüft nur, ob die korrigierte Vorgabe die richtige Tabellenzeile
  trifft — nicht, ob die Vorgabe in allen 76 Records stimmt.

## Artefakte

* `runs/v3_comparator_289_295_20261116/predictions.jsonl` (7 Zeilen)
* `runs/v3_comparator_289_295_20261116/auswertung.json`
* `runs/v3_comparator_289_295_20261116/lauf.log`
