# P5-Vorbereitung: die 103 Budget-Ausfaelle

Offline erstellt, **kein Netzlauf**. Grundlage: Lesekopie `runs/_lesekopie_20261118`, Klasse `length_ohne_ergebnis` (der Timeout `yun2024:87` gehoert nicht dazu), Records aus `public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl`.

| Prüfpunkt | Wert |
|---|---|
| Ausfälle | 103 |
| bewertbar (Goldzellen > 0) | 102 |
| nicht bewertbar | 1 |
| Goldzellen der bewertbaren | 423 |
| nicht in der Record-Datei | 0 |
| ohne Dokumentdatei | 0 |

- **yun2024:653 ist nicht bewertbar** (keine Goldzellen): der Record liefert keine Trefferfläche, jede vorhergesagte Zelle wäre ein Fehlalarm. Er läuft mit, zählt aber nicht in Recall oder MAE.

## Befehl für den Lauf

```
.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl --split "" --ids yun2024:6,yun2024:120,yun2024:30,yun2024:228,yun2024:32,yun2024:52,yun2024:54,yun2024:68,yun2024:84,yun2024:85,yun2024:86,yun2024:110,yun2024:113,yun2024:114,yun2024:117,yun2024:119,yun2024:128,yun2024:130,yun2024:133,yun2024:136,yun2024:137,yun2024:149,yun2024:151,yun2024:152,yun2024:154,yun2024:158,yun2024:159,yun2024:160,yun2024:162,yun2024:161,yun2024:163,yun2024:164,yun2024:169,yun2024:171,yun2024:173,yun2024:174,yun2024:178,yun2024:183,yun2024:203,yun2024:212,yun2024:204,yun2024:213,yun2024:214,yun2024:215,yun2024:232,yun2024:233,yun2024:251,yun2024:252,yun2024:269,yun2024:268,yun2024:270,yun2024:273,yun2024:291,yun2024:304,yun2024:313,yun2024:344,yun2024:347,yun2024:349,yun2024:356,yun2024:357,yun2024:367,yun2024:362,yun2024:376,yun2024:380,yun2024:384,yun2024:405,yun2024:420,yun2024:421,yun2024:427,yun2024:447,yun2024:446,yun2024:448,yun2024:449,yun2024:450,yun2024:451,yun2024:523,yun2024:525,yun2024:533,yun2024:557,yun2024:556,yun2024:558,yun2024:559,yun2024:582,yun2024:601,yun2024:602,yun2024:616,yun2024:615,yun2024:617,yun2024:624,yun2024:626,yun2024:625,yun2024:653,yun2024:662,yun2024:668,yun2024:672,yun2024:673,yun2024:671,yun2024:674,yun2024:677,yun2024:678,yun2024:686,yun2024:685,yun2024:687 --models glm --workers 2 --max-tokens 24000 --run-id yun699_p5_24000_20261118 --retry-strategie neu --quelle p5_24000
```

Vorher `--dry-run` an dieselbe Zeile hängen: erwartet werden 103 Aufträge und keine Anfrage.

## Id-Liste

```
yun2024:6,yun2024:120,yun2024:30,yun2024:228,yun2024:32,yun2024:52,yun2024:54,yun2024:68,yun2024:84,yun2024:85,yun2024:86,yun2024:110,yun2024:113,yun2024:114,yun2024:117,yun2024:119,yun2024:128,yun2024:130,yun2024:133,yun2024:136,yun2024:137,yun2024:149,yun2024:151,yun2024:152,yun2024:154,yun2024:158,yun2024:159,yun2024:160,yun2024:162,yun2024:161,yun2024:163,yun2024:164,yun2024:169,yun2024:171,yun2024:173,yun2024:174,yun2024:178,yun2024:183,yun2024:203,yun2024:212,yun2024:204,yun2024:213,yun2024:214,yun2024:215,yun2024:232,yun2024:233,yun2024:251,yun2024:252,yun2024:269,yun2024:268,yun2024:270,yun2024:273,yun2024:291,yun2024:304,yun2024:313,yun2024:344,yun2024:347,yun2024:349,yun2024:356,yun2024:357,yun2024:367,yun2024:362,yun2024:376,yun2024:380,yun2024:384,yun2024:405,yun2024:420,yun2024:421,yun2024:427,yun2024:447,yun2024:446,yun2024:448,yun2024:449,yun2024:450,yun2024:451,yun2024:523,yun2024:525,yun2024:533,yun2024:557,yun2024:556,yun2024:558,yun2024:559,yun2024:582,yun2024:601,yun2024:602,yun2024:616,yun2024:615,yun2024:617,yun2024:624,yun2024:626,yun2024:625,yun2024:653,yun2024:662,yun2024:668,yun2024:672,yun2024:673,yun2024:671,yun2024:674,yun2024:677,yun2024:678,yun2024:686,yun2024:685,yun2024:687
```
