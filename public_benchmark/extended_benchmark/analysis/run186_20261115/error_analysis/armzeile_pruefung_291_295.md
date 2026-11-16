# Prüflauf Armzeilen-Zusatz 291–295 (16.11.2026)

Run-ID `armzeile_291_295_20261116`, Modell `glm`, `--ids yun2024:291…295
--cell-timepoint --target-fallback --group-size-mode aus --repair
--arm-row-mode an --max-tokens 19000`.

Kosten: **27.822 Completion-Tokens** für fünf Records. 4 von 5 Records
antworteten (`291`, `293`, `294`, `295`, je 6 Zellen); `292` scheiterte an
erschöpften 503-Wiederholungen des Gateways (0 Tokens), kein erneuter Versuch.

## Ergebnis gegen die Komparatorzellen

| Record | Feld | Gold | Modell | richtig | `arm_row` des Modells |
|---|---|---:|---:|---|---|
| 291 | `comparator_mean` | 46,5 | 42,8 | nein | `FAT Pre` |
| 291 | `comparator_standard_deviation` | 9,8 | 12,8 | nein | `FAT Pre` |
| 292 | beide | 50,8 / 12,1 | – | Ausfall | – |
| 293 | `comparator_mean` | 47,3 | 46,2 | nein | `FAT Pre` |
| 293 | `comparator_standard_deviation` | 10,4 | 9,9 | nein | `FAT Pre` |
| 294 | `comparator_mean` | 46,5 | 44,5 | nein | `FAT Pre` |
| 294 | `comparator_standard_deviation` | 9,8 | 10,7 | nein | `FAT Pre` |
| 295 | `comparator_mean` | 42,8 | 39,3 | nein | `FAT Pre` |
| 295 | `comparator_standard_deviation` | 11,7 | 11,1 | nein | `FAT Pre` |

**0 von 10 auswertbaren Zellen richtig** (von 14 wären es mit 289/290 gewesen;
die liefen nach der Freigabe-Teilung nicht mit). Alle acht Zellen stammen
weiterhin aus `FAT Pre`, und das Modell **benennt die Zeile jetzt selbst** so:
`arm_row: FAT Pre` bei jedem Komparator, `FAT Post` bei jedem Interventionswert.

## Abbruchkriterium

Vorab festgelegt: Erfolg ab 10/14 richtig (anteilig 7/10), Teilerfolg 5–9/14
(4–6/10), Misserfolg ≤ 4/14 (≤ 3/10). Erreicht: **0/10 → Misserfolg.** Der
Zusatz wird nicht als Lösung weiterverfolgt.

## Warum er nicht greifen konnte

Der Zusatz machte den Fehler sichtbar, nicht kleiner — und die Aufdeckung zeigt,
dass die Prämisse nicht stimmt. Alle sieben Records tragen im Datensatz
`comparator: "baseline"`:

```
yun2024:289 … 295   intervention: "facial affect training (FAT) in 20 daily 1-hour sessions"
                    comparator:   "baseline"
```

Das Gold nimmt als Komparator aber die **TAU-Gruppe zum Post-Zeitpunkt**
(48,2 ± 12,3 = `TAU Post`, Spalte „Overall composite“). Der Modellwert
39,5 ± 10,6 ist `FAT Pre` — also genau das, was der Record unter „comparator:
baseline“ nennt: die Ausgangsmessung des Interventionsarms.

Das Modell folgt damit dem Record, nicht der Tabelle. Es ist kein Zeilenlese-
Fehler, sondern ein **Widerspruch zwischen Comparator-Feld und Gold**: das Feld
sagt „baseline“, das Gold meint „TAU“. Genau sieben Records der Testbasis tragen
`comparator: "baseline"` — es sind diese sieben.

## Konsequenz

* `--arm-row-mode` ist **aus dem Runner entfernt** (16.11.2026). Der Lauf
  `armzeile_291_295_20261116` bleibt als Beleg liegen; seine Zeilen tragen noch
  `arm_row_mode` und `arm_row`, weil sie vor dem Rückbau geschrieben wurden.
  Der Runner ist wieder byte-identisch zum Stand vor dem Zusatz (0 von 76
  Prompts abweichend).
* Die 14 „falschen Komparatorzellen“ sind **kein Modellfehler im engeren Sinn**,
  solange das Comparator-Feld `baseline` sagt. Sie sind ein Datenbefund wie
  `yun2024:479`.

## Nebenbefund: versehentlicher Lauf

Bei der CLI-Gegenprobe zur Sperre `--arm-row-mode` ohne `--cell-timepoint` hatte
ich `--ids` und `--records` weggelassen; der Befehl startete einen echten Lauf
mit Run-ID `x`, bevor die Shell nach 240 s gekappt wurde. Ergebnis: 7 Records des
Dev-Splits, **13.081 Tokens** verbraucht. Der Ordner liegt als
`runs/versehen_cli_probe_20261116/` (Datei `predictions.jsonl.bak`, untracked)
und ist nicht in die Auswertung eingegangen. Die Sperre ist inzwischen im Code
und per Test abgesichert, der Abbruch erfolgt **vor** jedem Konfigurations- oder
API-Zugriff.

## Grenzen

- Vier auswertbare Records, acht Zellen: ein Unterschied von 1–2 Zellen wäre
  nicht signifikant, 0 von 8 ist es wohl.
- Nur ein Modell, kein Kontrolllauf mit `--arm-row-mode aus` auf denselben
  Records in derselben Session.
- Ob das Comparator-Feld oder das Gold falsch ist, entscheidet sich am Artikel,
  nicht an diesem Lauf.
