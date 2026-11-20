# Fensterlage der 33 P5-Abbrueche (20.11.2026)

Rein offline: Goldwerte gegen Dokumenttext und gegen das 6.000er-Fenster aus `zweistufig_trocken_20261120.py`. Kein Modellaufruf, kein Netz, Gold und Predictions unveraendert.

## Zahlpruefung vorab

- Records: **33** (die 33 Abbrueche mit `content_chars = 0`).
- Records mit **null** Goldwerten im 6.000er-Fenster: **6** (yun2024:159, yun2024:164, yun2024:624, yun2024:625, yun2024:685, yun2024:687).
- Records mit **mindestens zwei** Goldwerten im Fenster: **21**.
- Goldwerte gesamt (verschiedene Werte je Record): 118; davon im Volltext auffindbar: 92, nicht auffindbar: 26.
- Im 6.000er-Fenster sichtbar: **67** von 118; im Text, aber ausserhalb des Fensters: 25.

Die frueher notierte Zahl 21 ist damit **nicht** die Zahl der Records ohne Goldwert im Fenster: sie ist die Zahl der Records mit mindestens zwei Werten im Fenster. Die Zahl der Records ohne jeden Wert im Fenster ist 6.

## Die Records ohne Goldwert im Fenster

| Record | Dokument | Goldwerte | davon im Volltext | Werte ausserhalb des Fensters | bester blinder Treffer | Orakel |
|---|---|---:|---:|---|---:|---:|
| `yun2024:159` | PMC5056957 | 6 | 4 | 21.07 (8236 Zeichen, danach), 21.27 (8374 Zeichen, danach), 459.0 (510 Zeichen, danach), 592.0 (541 Zeichen, danach) | 4 | 4 |
| `yun2024:164` | PMC5062234 | 1 | 0 | - | 0 | 0 |
| `yun2024:624` | PMC3493722 | 1 | 0 | - | 0 | 0 |
| `yun2024:625` | PMC3493722 | 2 | 0 | - | 0 | 0 |
| `yun2024:685` | PMC2836833 | 1 | 1 | 17.0 (3709 Zeichen, danach) | 0 | 1 |
| `yun2024:687` | PMC2836833 | 1 | 1 | 17.0 (3209 Zeichen, danach) | 0 | 1 |

## Alle 33 im Ueberblick

| Record | Goldwerte | im Text | im Fenster (`score`) | bester blinder Treffer | Orakel 6.000 |
|---|---:|---:|---:|---:|---:|
| `yun2024:30` | 6 | 6 | 3 | 3 | 6 |
| `yun2024:52` | 6 | 6 | 2 | 5 | 5 |
| `yun2024:119` | 4 | 4 | 4 | 4 | 4 |
| `yun2024:128` | 3 | 3 | 3 | 3 | 3 |
| `yun2024:152` | 3 | 3 | 2 | 2 | 3 |
| `yun2024:159` | 6 | 4 | 0 | 4 | 4 |
| `yun2024:164` | 1 | 0 | 0 | 0 | 0 |
| `yun2024:171` | 4 | 3 | 3 | 3 | 3 |
| `yun2024:173` | 4 | 3 | 3 | 3 | 3 |
| `yun2024:204` | 1 | 1 | 1 | 1 | 1 |
| `yun2024:251` | 4 | 4 | 3 | 4 | 4 |
| `yun2024:252` | 2 | 2 | 2 | 2 | 2 |
| `yun2024:273` | 2 | 1 | 1 | 1 | 1 |
| `yun2024:304` | 3 | 2 | 2 | 2 | 2 |
| `yun2024:356` | 1 | 1 | 1 | 1 | 1 |
| `yun2024:420` | 6 | 6 | 6 | 6 | 6 |
| `yun2024:421` | 6 | 6 | 6 | 6 | 6 |
| `yun2024:446` | 6 | 3 | 1 | 2 | 3 |
| `yun2024:451` | 6 | 3 | 1 | 2 | 3 |
| `yun2024:523` | 4 | 3 | 3 | 3 | 3 |
| `yun2024:525` | 4 | 3 | 3 | 3 | 3 |
| `yun2024:557` | 6 | 2 | 2 | 2 | 2 |
| `yun2024:559` | 6 | 2 | 2 | 2 | 2 |
| `yun2024:582` | 1 | 1 | 1 | 1 | 1 |
| `yun2024:624` | 1 | 0 | 0 | 0 | 0 |
| `yun2024:625` | 2 | 0 | 0 | 0 | 0 |
| `yun2024:671` | 2 | 2 | 2 | 2 | 2 |
| `yun2024:672` | 2 | 2 | 2 | 2 | 2 |
| `yun2024:674` | 6 | 6 | 3 | 4 | 6 |
| `yun2024:673` | 6 | 6 | 3 | 4 | 6 |
| `yun2024:685` | 1 | 1 | 0 | 0 | 1 |
| `yun2024:678` | 2 | 2 | 2 | 2 | 2 |
| `yun2024:687` | 1 | 1 | 0 | 0 | 1 |

## Startregeln im Vergleich

| Regel | Records mit >= 1 Wert | Records mit >= 2 Werten | abgedeckte Werte | abgedeckte Goldzellen |
|---|---:|---:|---:|---:|
| `score` | 27 | 21 | 67 | 75 |
| `outcome_erste` | 26 | 20 | 58 | 66 |
| `outcome_letzte` | 27 | 21 | 62 | 70 |
| `tabelle_mitte` | 2 | 1 | 3 | 4 |
| `zeitpunkt` | 2 | 1 | 3 | 4 |
| `anker_max` | 27 | 21 | 67 | 75 |
| `mehrfach_3x2000` | 28 | 24 | 72 | 80 |
| `orakel_6000` | 30 | 24 | 91 | 101 |

Abdeckung ist eine Obergrenze: gezaehlt wird, ob der Wert irgendwo im Fenster steht, nicht ob er dort zur richtigen Zeile und zum richtigen Arm gehoert. Zum Vergleich: von 92 im Text auffindbaren Werten erreicht das beste einzelne 6.000er-Fenster 91; 1 Wert liegt weiter auseinander, als ein Fenster dieser Breite fassen kann.

## Was das fuer eine qwen-Serie heisst

Von 118 Goldwerten zeigt das aktuelle Fenster 67; 51 sind unsichtbar, davon 26 gar nicht im Dokumenttext und 25 im Text, aber ausserhalb des Fensters. Das beste einzelne 6.000er-Fenster kaeme auf 91; nur 1 Wert passt in kein Fenster dieser Breite. Die Breite ist damit nicht der Engpass, sondern die Startregel. Eine qwen-Serie auf allen 33 wuerde zu 51 von 118 Werten die Fensterwahl bzw. die Dokumentaufbereitung messen, nicht das Modell.
Von den 6 Records ohne Goldwert im Fenster haben 3 **keinen einzigen** Goldwert im Dokumenttext (yun2024:164, yun2024:624, yun2024:625). Dort kann keine Startregel etwas gewinnen: der Wert existiert im Markdown nicht, weil die Tabelle nur als Caption mit Bildplatzhalter steht. Eine Serie auf diesen Records misst die Dokumentaufbereitung, nicht das Modell und nicht das Fenster.
Bei `yun2024:159` (outcome_letzte, mehrfach_3x2000), `yun2024:685` (keine getestete blinde Regel, nur das Orakelfenster), `yun2024:687` (keine getestete blinde Regel, nur das Orakelfenster) steht mindestens ein Wert im Dokument, aber keiner im Fenster; dort ist die Startregel der Engpass. In Klammern stehen die getesteten blinden Regeln, die einen Wert erreichen.

## Vorbehalt

- Die Zahlenlesart ist bewusst grosszuegig (Trennzeichen als Tausendergruppen, beide Lesarten). Ein Treffer heisst nur, dass die Ziffernfolge im Text steht; ein Zitat, ein Literaturverweis oder eine andere Tabelle zaehlt mit.
- Die Abdeckung prueft keine Zeile und keinen Arm. Sie sagt, ob ein Modell den Wert ueberhaupt sehen konnte, nicht ob es ihn richtig bindet.
- Die Startregeln sind blind, benutzen aber Outcome-Ausdruck und Zielzeitpunkt aus dem Record-Kontext, also dieselbe Information, die auch der Prompt traegt.

Rohdaten: `fensterlage_20261120.json`.
