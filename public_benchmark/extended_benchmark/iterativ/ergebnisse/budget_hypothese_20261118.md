# Budget-Hypothese: Pruefung an den vorhandenen Daten

GLM-Zeilen ueber alle Laeufe: 2707 aus 43 Laeufen; Lesekopie: 699 Zeilen. Kein Netzaufruf, keine Datei im Laufverzeichnis veraendert.

## A Mechanik

- abgeschnittene Zeilen mit bekannter Grenze: 395
- davon `completion_tokens` genau gleich der Grenze: 395
- davon ohne Inhalt: 391
- Reasoning-Zeichen je Token: {'n': 390, 'min': 2.8, 'median': 4.0, 'max': 4.6}

## B Dosis-Wirkung (derselbe Record, zwei Budgets)

- 16000->19000: length->leer: 7
- 16000->19000: length->length: 20
- 16000->19000: length->ok: 23
- 19000->24000: length->length: 2
- 19000->24000: ok->length: 4
- 24000->32000: length->length: 1
- 4000->16000: length->length: 2
- 4000->16000: ok->length: 2
- 4000->19000: leer->leer: 1
- 4000->19000: leer->ok: 1
- 4000->19000: length->leer: 1
- 4000->19000: length->length: 2
- 4000->19000: length->ok: 2
- 4000->19000: ok->leer: 1
- 4000->19000: ok->length: 3
- 4000->19000: ok->ok: 4
- 4000->8000: leer->leer: 4
- 4000->8000: leer->length: 1
- 4000->8000: leer->ok: 2
- 4000->8000: length->leer: 1
- 4000->8000: length->length: 10
- 4000->8000: length->ok: 11
- 4000->8000: ok->ok: 38
- 8000->16000: length->length: 18
- 8000->16000: ok->length: 26
- 8000->19000: length->leer: 5
- 8000->19000: length->length: 16
- 8000->19000: length->ok: 15
- 8000->19000: ok->leer: 36
- 8000->19000: ok->length: 25
- 8000->19000: ok->ok: 57
- 8000->24000: length->length: 10
- 8000->24000: ok->length: 9
- 8000->32000: ok->length: 1

## C Rettung der 8000er Ausfaelle

- Ausfaelle bei 8.000: 237
- davon mit Beobachtung ab 16000: 38
- davon mit Zellen: 15
- davon erneut `length`: 20
- gerettet: yun2024:117, yun2024:119, yun2024:149, yun2024:151, yun2024:154, yun2024:160, yun2024:161, yun2024:162, yun2024:204, yun2024:291, yun2024:357, yun2024:384, yun2024:533, yun2024:626, yun2024:678
- weiter `length`: yun2024:114, yun2024:120, yun2024:158, yun2024:159, yun2024:163, yun2024:169, yun2024:228, yun2024:232, yun2024:233, yun2024:252, yun2024:349, yun2024:356, yun2024:405, yun2024:54, yun2024:582

## D Skalierung

- Reasoning-Wachstum bei mehr Budget: {'n': 184, 'min': 0.1, 'median': 2.3, 'max': 46.6}

| Budget | n | ok | leer | length | Anteil length |
|---|---|---|---|---|---|
| 4000 | 120 | 79 | 11 | 30 | 25.0% |
| 8000 | 1503 | 1185 | 81 | 237 | 15.8% |
| 16000 | 59 | 0 | 0 | 59 | 100.0% |
| 19000 | 216 | 115 | 54 | 47 | 21.8% |
| 24000 | 21 | 0 | 0 | 21 | 100.0% |
