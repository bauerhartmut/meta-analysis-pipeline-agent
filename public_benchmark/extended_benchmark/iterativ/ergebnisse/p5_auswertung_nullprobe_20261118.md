# P5-Auswertung: Rettung und Zellgewinn

Neu: `runs/_lesekopie_20261118/predictions.jsonl`. Vergleich: die 103 `length_ohne_ergebnis`-Zeilen der Lesekopie, Modell glm.

> **Nullprobe:** neu und alt sind dieselbe Datei. Erwartet sind 0 Rettungen, 0 Zellgewinn und die volle Goldzahl.

## Status je Record

| Status | Records |
|---|---|
| gerettet (Antwort mit Zellen) | 0 |
| fertig, aber ohne Zellen | 0 |
| weiter ausgefallen | 103 |
| im neuen Lauf nicht enthalten | 0 |

Rettungsquote auf den **102 bewertbaren** Records: **0 von 102** (0.0%)

## Zellen und Gold

| Groesse | Wert |
|---|---|
| Zellen vorher (Ausfallzeilen) | 0 |
| Zellen nachher | 0 |
| Zellgewinn | 0 |
| Goldzellen der bewertbaren | 423 |
| davon mit angegebenem Zeitpunkt | 0 |
| vorhergesagte Zellen mit Zeitpunkt | 0 |
| adressiert, Feld und Arm (grosszuegig) | 0 |
| **adressiert, Feld, Arm und eindeutiger Zeitpunkt** | **0** |
| wertgleich, Feld und Arm (grosszuegig) | 0 |
| **wertgleich, Feld, Arm und eindeutiger Zeitpunkt** | **0** |
| Feld/Arm-Gruppen mit mehreren Zeitpunkten | 0 |
| Completion-Tokens neu | 824000 |

Die Zellzaehlung ist eine grobe Selbstpruefung, nicht die offizielle Bewertung; Recall und MAE kommen aus dem geschuetzten Bewertungslauf.

Die grosszuegige Zaehlung erkennt eine Goldzelle schon an Feld und Arm. Die fett gesetzte Zaehlung verlangt zusaetzlich einen eindeutigen Zeitpunkt (normalisiert: Kleinschreibung, ein Leerzeichen, leer gleich `ohne`). Ein Vergleich Gold-Zeitpunkt gegen Vorhersage-Zeitpunkt ist nicht moeglich: das Gold traegt je Zelle keinen, und der Record-Zeitpunkt beschreibt in Yun-699 nur eine Regel.

Beide Zaehlungen stimmen ueberein: keine der 102 bewertbaren Zeilen streut einen Feld/Arm-Schluessel ueber mehrere Zeitpunkte.

0 vorhergesagte Zellen tragen einen Zeitpunkt; das Gold kann ihn weder bestaetigen noch widerlegen.

## Nicht bewertbar

- `yun2024:653`: 0 Goldzellen, Status weiter_ausfall, 0 Zellen. Zaehlt nicht in Rettungsquote oder Golddeckung, jede vorhergesagte Zelle waere ohne Trefferflaeche.

## Nicht gerettet

| Record | Status | Klasse neu | Tokens neu | Reasoning-Zeichen |
|---|---|---|---|---|
| `yun2024:110` | weiter_ausfall | length_ohne_ergebnis | 8000 | 24033 |
| `yun2024:113` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30932 |
| `yun2024:114` | weiter_ausfall | length_ohne_ergebnis | 8000 | 28137 |
| `yun2024:117` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34562 |
| `yun2024:119` | weiter_ausfall | length_ohne_ergebnis | 8000 | 29561 |
| `yun2024:120` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30553 |
| `yun2024:128` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30356 |
| `yun2024:130` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30878 |
| `yun2024:133` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35155 |
| `yun2024:136` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34584 |
| `yun2024:137` | weiter_ausfall | length_ohne_ergebnis | 8000 | 36800 |
| `yun2024:149` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33621 |
| `yun2024:151` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32282 |
| `yun2024:152` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34491 |
| `yun2024:154` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34349 |
| `yun2024:158` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30075 |
| `yun2024:159` | weiter_ausfall | length_ohne_ergebnis | 8000 | 28989 |
| `yun2024:160` | weiter_ausfall | length_ohne_ergebnis | 8000 | 29336 |
| `yun2024:161` | weiter_ausfall | length_ohne_ergebnis | 8000 | 29152 |
| `yun2024:162` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30437 |
| `yun2024:163` | weiter_ausfall | length_ohne_ergebnis | 8000 | 25611 |
| `yun2024:164` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33481 |
| `yun2024:169` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32909 |
| `yun2024:171` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33073 |
| `yun2024:173` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32078 |
| `yun2024:174` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31594 |
| `yun2024:178` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33835 |
| `yun2024:183` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35453 |
| `yun2024:203` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31062 |
| `yun2024:204` | weiter_ausfall | length_ohne_ergebnis | 8000 | 28055 |
| `yun2024:212` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31366 |
| `yun2024:213` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30168 |
| `yun2024:214` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31527 |
| `yun2024:215` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31442 |
| `yun2024:228` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35008 |
| `yun2024:232` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35706 |
| `yun2024:233` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35248 |
| `yun2024:251` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33389 |
| `yun2024:252` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35259 |
| `yun2024:268` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31357 |
| `yun2024:269` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31507 |
| `yun2024:270` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32187 |
| `yun2024:273` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32933 |
| `yun2024:291` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34192 |
| `yun2024:30` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30107 |
| `yun2024:304` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30478 |
| `yun2024:313` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33908 |
| `yun2024:32` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30047 |
| `yun2024:344` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33438 |
| `yun2024:347` | weiter_ausfall | length_ohne_ergebnis | 8000 | 29394 |
| `yun2024:349` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31652 |
| `yun2024:356` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32300 |
| `yun2024:357` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32909 |
| `yun2024:362` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33891 |
| `yun2024:367` | weiter_ausfall | length_ohne_ergebnis | 8000 | 36204 |
| `yun2024:376` | weiter_ausfall | length_ohne_ergebnis | 8000 | 35870 |
| `yun2024:380` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34732 |
| `yun2024:384` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34081 |
| `yun2024:405` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32931 |
| `yun2024:420` | weiter_ausfall | length_ohne_ergebnis | 8000 | 25995 |
| `yun2024:421` | weiter_ausfall | length_ohne_ergebnis | 8000 | 27175 |
| `yun2024:427` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30564 |
| `yun2024:446` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33898 |
| `yun2024:447` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33980 |
| `yun2024:448` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31912 |
| `yun2024:449` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33245 |
| `yun2024:450` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34562 |
| `yun2024:451` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34081 |
| `yun2024:52` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31505 |
| `yun2024:523` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31363 |
| `yun2024:525` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30402 |
| `yun2024:533` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33806 |
| `yun2024:54` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32623 |
| `yun2024:556` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31701 |
| `yun2024:557` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32100 |
| `yun2024:558` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32725 |
| `yun2024:559` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31571 |
| `yun2024:582` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33101 |
| `yun2024:6` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33972 |
| `yun2024:601` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33503 |
| `yun2024:602` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34604 |
| `yun2024:615` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32541 |
| `yun2024:616` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32202 |
| `yun2024:617` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33204 |
| `yun2024:624` | weiter_ausfall | length_ohne_ergebnis | 8000 | 28715 |
| `yun2024:625` | weiter_ausfall | length_ohne_ergebnis | 8000 | 27846 |
| `yun2024:626` | weiter_ausfall | length_ohne_ergebnis | 8000 | 28562 |
| `yun2024:662` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32184 |
| `yun2024:668` | weiter_ausfall | length_ohne_ergebnis | 8000 | 30918 |
| `yun2024:671` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34747 |
| `yun2024:672` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34126 |
| `yun2024:673` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33540 |
| `yun2024:674` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32431 |
| `yun2024:677` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33522 |
| `yun2024:678` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32448 |
| `yun2024:68` | weiter_ausfall | length_ohne_ergebnis | 8000 | 34995 |
| `yun2024:685` | weiter_ausfall | length_ohne_ergebnis | 8000 | 29831 |
| `yun2024:686` | weiter_ausfall | length_ohne_ergebnis | 8000 | 27770 |
| `yun2024:687` | weiter_ausfall | length_ohne_ergebnis | 8000 | 31098 |
| `yun2024:84` | weiter_ausfall | length_ohne_ergebnis | 8000 | 32973 |
| `yun2024:85` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33200 |
| `yun2024:86` | weiter_ausfall | length_ohne_ergebnis | 8000 | 33272 |
