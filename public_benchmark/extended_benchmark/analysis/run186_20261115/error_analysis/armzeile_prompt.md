# Armzeilen-Zusatz im Prompt (opt-in, 16.11.2026)

> **Zurückgezogen am 16.11.2026.** Der Prüflauf über 291–295 ergab 0 von 10
> richtigen Komparatorzellen (`armzeile_pruefung_291_295.md`). Der Zusatz ist
> wieder aus dem Runner entfernt; die Prompts sind byte-identisch zum Stand
> davor. Dieses Dokument bleibt als Beleg für Aufbau, Prüfung und Abbruch.

## Anlass

Im 76er-Hauptlauf stammen in den sieben MCCB-Records (`yun2024:289`–`295`,
PMC4215531) **alle 14 Komparator-Zellen** aus der Zeile `FAT Pre` — dem
Interventionsarm *vor* dem Training —, obwohl Gold `TAU Post` ist. Die Spalte
(der jeweilige Untertest) war richtig, die Zeile falsch. Das sind 14 der 25
falschen Zellen des Laufs (siehe `test76_hauptlauf.md`, Abschnitt 6).

## Der Zusatz

Neues Flag `--arm-row-mode {aus,an}`, Standard `aus`. Im Modus `an` kommt dieser
Absatz in den v7-Prompt:

> Tables often stack the arms as rows (for example "FAT Pre", "FAT Post",
> "TAU Pre", "TAU Post"). Take every value from the row of its own arm at the
> answer time point: an intervention value from the experimental arm's row, a
> comparator value from the control arm's row, each in the row for that time
> point. Never take a comparator value from the experimental arm's row, and
> never from the row of the other time point.

Zusätzlich verlangt das Zellschema dann ein Feld `arm_row` („row label copied
from the table, e.g. TAU Post“). `parse_cells` übernimmt es nur, wenn das Modell
es liefert — ältere Läufe behalten ihr Format. Jede Zeile der
`predictions.jsonl` trägt `arm_row_mode`.

Der Zusatz steht **auch im Reparaturprompt**, in kurzer Form. Grund: im
Hauptlauf kamen genau `289` und `290` über die Reparatur (19.000 Tokens Primär
plus Nachfass), ein Zusatz nur im Standardprompt hätte bei diesen beiden nichts
geändert.

## Prüfung ohne Netz

| Prüfung | Ergebnis |
|---|---|
| Prompt im Modus `aus` gegen den Stand vor der Änderung, alle 76 Records | **0 von 76 abweichend**, auch der Reparaturprompt |
| Zusatz nur im Modus `an` | Text und `arm_row`-Feld fehlen im `aus`-Prompt |
| Position im Prompt | nach dem Zeitpunkt-Absatz, vor der Schlussregel |
| Tests | 243 grün (zwei neue Prompttests, einer für `parse_cells`) |
| Baseline-Messung des alten Laufs | **0/14** Komparatorzellen richtig, alle 14 aus `FAT Pre` |

Die Baseline stammt aus `pruefe_armzeile_289_295.py --run
test76_hauptlauf_20261116`; das Skript nennt je Zelle Gold, Modellwert, Treffer
und die Zeile, aus der der Modellwert im Artikel steht.

## Prüflauf (wartet auf Freigabe)

```bash
python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models glm --split test \
  --records public_benchmark/extended_benchmark/records/yun_test76_ziel.jsonl \
  --ids yun2024:289,yun2024:290,yun2024:291,yun2024:292,yun2024:293,yun2024:294,yun2024:295 \
  --cell-timepoint --target-fallback --group-size-mode aus --repair \
  --arm-row-mode an --max-tokens 19000 \
  --run-id armzeile_289_295_20261116 --quelle armzeile_289_295

python public_benchmark/extended_benchmark/analysis/run186_20261115/error_analysis/pruefe_armzeile_289_295.py \
  --run armzeile_289_295_20261116
```

Kosten: 7 Records, im Hauptlauf 11.440 Tokens je Record im Mittel →
**rund 80.000 Completion-Tokens [Schätzung aus dem Hauptlauf]**, plus mögliche
Reparaturaufrufe (289 und 290 lagen dort bei 19.000 + 2.491 bzw. 19.000 +
1.695 Tokens).

## Abbruchkriterien, vor dem Lauf festgelegt

* **Erfolg:** mindestens 10 von 14 Zellen richtig und keine Zelle mehr aus
  `FAT Pre`. Dann den Zusatz als empfohlenen Standard für Tabellenstudien
  dokumentieren, aber weiter opt-in lassen.
* **Teilerfolg 5–9 von 14:** Zusatz behalten, Prompt dafür schärfen (Zeilenkopf
  wörtlich zitieren lassen statt „arm_row“ frei zu formulieren), kein zweiter
  Lauf ohne neue Begründung.
* **Misserfolg ≤ 4 von 14:** Zusatz verwerfen und im Bericht als wirkungslos
  vermerken; der Fehler liegt dann nicht am Prompt, sondern am Tabellenlesen
  des Modells.
* **Ausfall:** Liefert ein Record `length_ohne_ergebnis`, wird nicht wiederholt —
  das ist im Hauptlauf bei 3 von 76 Records passiert und wäre kein neuer Befund.

## Grenzen

- Sieben Records, 14 Zellen: der Vergleich ist ein Vorher-Nachher am selben
  Modell ohne Kontrollgruppe; ein Zufallstreffer von 2–3 Zellen wäre nicht
  unterscheidbar.
- Der Zusatz kostet Prompt-Länge (+507 Zeichen bei 289) und kann bei
  Length-anfälligen Records die Ausfallquote erhöhen — das ist der Hauptrisikopfad.
- `arm_row` ist ein Freitextfeld; ob das Modell die Zeile richtig *benennt*, ist
  eine andere Frage als ob es den richtigen Wert liefert.
