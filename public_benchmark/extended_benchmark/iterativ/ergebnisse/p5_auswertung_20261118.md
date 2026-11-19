# P5-Auswertung: Rettung und Zellgewinn

Neu: `D:/daswu/AIResearch/public_benchmark/extended_benchmark/runs/yun699_p5_24000_20261118/predictions.jsonl`. Vergleich: 103 IDs der P5-Auswahl gegen ihre Zeilen in der Lesekopie, Modell glm.

## Grundgesamtheit

| Groesse | Wert |
|---|---|
| adressierte IDs | 103 |
| davon bewertbar (Goldzellen vorhanden) | 102 |
| davon nicht bewertbar | 1 |

Verglichen wird ausschliesslich auf diesen IDs. Fehlt eine Zeile im neuen Lauf oder im alten, steht das als solcher Status in der Tabelle und wird nicht als Ausfall oder als Rettung gezaehlt.

## Status je Record

| Status | Records |
|---|---|
| gerettet (Antwort mit Zellen) | 67 |
| fertig, aber ohne Zellen | 3 |
| weiter ausgefallen | 33 |
| im neuen Lauf nicht enthalten | 0 |
| **Antwort technisch erhalten** | **70 von 103** |
| **auswertbar (mindestens eine Zelle)** | **67 von 103** |

Rettungsquote auf den **102 bewertbaren** Records: **66 von 102** (64.7%)

## Drei Stufen der Rettung

| Stufe | Definition | Records |
|---|---|---|
| 1 technische Rettung | Antwort ohne Fehlerklasse erhalten | 70 von 103 |
| 2 auswertbar | Antwort enthaelt mindestens eine Zelle | 67 von 103 |
| 3 inhaltliche Rettung | mindestens eine Goldzelle wertgleich (Feld und Arm) | 58 von 102 |
| 3b inhaltlich, streng | zusaetzlich eindeutiger Zeitpunkt | 58 von 102 |

Die Stufen sind keine Steigerung derselben Quote: Stufe 1 sagt nur, dass eine Antwort ankam, Stufe 2 dass sie Zellen enthaelt, Stufe 3 dass ein Wert stimmt. Die Reparaturschaetzung von 39 % aus der Materialanalyse ist eine Schaetzung und kein gemessener Erfolg.

## Nach urspruenglicher Fehlerklasse

| Klasse alt | IDs | technisch | auswertbar | leer | weiter ausgefallen | Goldzellen | adressiert F/A | adressiert +ZP | wertgleich F/A | wertgleich +ZP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `length_ohne_ergebnis` | 103 | 70 | 67 | 3 | 33 | 423 | 241 | 241 | 170 | 170 |

## Zellen und Gold

| Groesse | Wert |
|---|---|
| Zellen vorher (Ausfallzeilen) | 0 |
| Zellen nachher | 271 |
| Zellgewinn | 271 |
| Goldzellen der bewertbaren | 423 |
| davon mit angegebenem Zeitpunkt | 0 |
| vorhergesagte Zellen mit Zeitpunkt | 219 |
| adressiert, Feld und Arm (grosszuegig) | 241 |
| **adressiert, Feld, Arm und eindeutiger Zeitpunkt** | **241** |
| wertgleich, Feld und Arm (grosszuegig) | 170 |
| **wertgleich, Feld, Arm und eindeutiger Zeitpunkt** | **170** |
| Feld/Arm-Gruppen mit mehreren Zeitpunkten | 0 |
| Completion-Tokens neu | 1399558 |

Die Zellzaehlung ist eine grobe Selbstpruefung, nicht die offizielle Bewertung; Recall und MAE kommen aus dem geschuetzten Bewertungslauf.

Die grosszuegige Zaehlung erkennt eine Goldzelle schon an Feld und Arm. Die fett gesetzte Zaehlung verlangt zusaetzlich einen eindeutigen Zeitpunkt (normalisiert: Kleinschreibung, ein Leerzeichen, leer gleich `ohne`). Ein Vergleich Gold-Zeitpunkt gegen Vorhersage-Zeitpunkt ist nicht moeglich: das Gold traegt je Zelle keinen, und der Record-Zeitpunkt beschreibt in Yun-699 nur eine Regel.

Beide Zaehlungen stimmen ueberein: keine der 102 bewertbaren Zeilen streut einen Feld/Arm-Schluessel ueber mehrere Zeitpunkte.

219 vorhergesagte Zellen tragen einen Zeitpunkt; das Gold kann ihn weder bestaetigen noch widerlegen.

## Precision, Recall, F1 auf Zellebene

| Groesse | Wert |
|---|---:|
| Treffer (TP) | 170 |
| falsch positiv, Schluessel im Gold, aber Dublette oder falscher Wert | 80 |
| falsch positiv, Schluessel nicht im Gold | 17 |
| **falsch positiv gesamt (FP)** | **97** |
| nicht getroffen (FN) | 253 |
| **Precision** = TP/(TP+FP) | **0.637** |
| **Recall** = TP/(TP+FN) | **0.402** |
| **F1** | **0.493** |
| Goldzellen ohne numerischen Wert (ausserhalb der Bilanz) | 0 |
| bewertbare Records in der Bilanz | 102 |
| ausgenommen: Records ohne Goldzellen | 1 mit 4 Zellen, nicht als FP gezaehlt |

Die Zuordnung ist schluesselbasiert und 1:1: Jede Goldzelle trifft hoechstens einmal, jede Vorhersagezelle wird hoechstens einmal verbraucht. Nennt eine Antwort denselben Feld/Arm-Schluessel mehrfach, trifft nur eine Zelle; die uebrigen zaehlen als falsch positiv. Das Gold traegt keinen Zeitpunkt, ein Treffer auf den falschen Zeitpunkt ist also nicht erkennbar: die Precision ist eine **Obergrenze**. Records ohne Goldzellen bleiben aussen vor, weil ihre Zellen zwangslaeufig falsch positiv waeren. Die offizielle Bewertung bleibt der geschuetzte Bewertungslauf.

## Nicht bewertbar

- `yun2024:653`: 0 Goldzellen, Status gerettet, 4 Zellen. Zaehlt nicht in Rettungsquote oder Golddeckung, jede vorhergesagte Zelle waere ohne Trefferflaeche.

## Gerettete Records

| Record | Zellen | Goldzellen | adressiert F/A | adressiert +eindeutiger ZP | wertgleich F/A | wertgleich +eindeutiger ZP | Tokens neu |
|---|---|---|---|---|---|---|---|
| `yun2024:110` | 4 | 6 | 4 | 4 | 1 | 1 | 3058 |
| `yun2024:113` | 4 | 6 | 4 | 4 | 0 | 0 | 11074 |
| `yun2024:114` | 4 | 6 | 4 | 4 | 1 | 1 | 11673 |
| `yun2024:117` | 3 | 3 | 2 | 2 | 2 | 2 | 9296 |
| `yun2024:120` | 4 | 4 | 4 | 4 | 2 | 2 | 4337 |
| `yun2024:130` | 4 | 4 | 4 | 4 | 3 | 3 | 14350 |
| `yun2024:133` | 4 | 4 | 4 | 4 | 4 | 4 | 2893 |
| `yun2024:136` | 2 | 2 | 2 | 2 | 2 | 2 | 787 |
| `yun2024:149` | 4 | 4 | 4 | 4 | 3 | 3 | 12198 |
| `yun2024:151` | 6 | 4 | 4 | 4 | 3 | 3 | 8388 |
| `yun2024:154` | 4 | 2 | 2 | 2 | 2 | 2 | 7538 |
| `yun2024:158` | 6 | 6 | 6 | 6 | 2 | 2 | 2132 |
| `yun2024:160` | 4 | 6 | 4 | 4 | 4 | 4 | 15884 |
| `yun2024:161` | 6 | 6 | 6 | 6 | 2 | 2 | 18096 |
| `yun2024:162` | 6 | 6 | 6 | 6 | 4 | 4 | 12163 |
| `yun2024:163` | 4 | 6 | 4 | 4 | 4 | 4 | 16605 |
| `yun2024:169` | 4 | 2 | 2 | 2 | 2 | 2 | 12554 |
| `yun2024:174` | 6 | 4 | 4 | 4 | 2 | 2 | 22823 |
| `yun2024:178` | 2 | 4 | 2 | 2 | 2 | 2 | 13115 |
| `yun2024:183` | 6 | 6 | 6 | 6 | 6 | 6 | 6699 |
| `yun2024:203` | 4 | 6 | 4 | 4 | 4 | 4 | 4510 |
| `yun2024:212` | 4 | 6 | 4 | 4 | 4 | 4 | 5288 |
| `yun2024:213` | 4 | 6 | 4 | 4 | 4 | 4 | 11927 |
| `yun2024:214` | 6 | 6 | 4 | 4 | 4 | 4 | 9357 |
| `yun2024:215` | 6 | 6 | 4 | 4 | 4 | 4 | 6227 |
| `yun2024:228` | 6 | 6 | 6 | 6 | 6 | 6 | 11783 |
| `yun2024:232` | 6 | 6 | 6 | 6 | 6 | 6 | 10919 |
| `yun2024:233` | 6 | 6 | 6 | 6 | 6 | 6 | 9248 |
| `yun2024:270` | 2 | 2 | 2 | 2 | 2 | 2 | 7837 |
| `yun2024:291` | 6 | 6 | 6 | 6 | 3 | 3 | 1791 |
| `yun2024:313` | 4 | 4 | 4 | 4 | 2 | 2 | 1473 |
| `yun2024:32` | 6 | 6 | 6 | 6 | 6 | 6 | 5065 |
| `yun2024:344` | 2 | 2 | 2 | 2 | 2 | 2 | 5733 |
| `yun2024:347` | 6 | 6 | 6 | 6 | 4 | 4 | 7207 |
| `yun2024:349` | 2 | 2 | 2 | 2 | 2 | 2 | 5959 |
| `yun2024:357` | 4 | 2 | 2 | 2 | 0 | 0 | 14100 |
| `yun2024:362` | 2 | 4 | 2 | 2 | 0 | 0 | 1062 |
| `yun2024:367` | 4 | 4 | 4 | 4 | 4 | 4 | 2508 |
| `yun2024:376` | 4 | 2 | 2 | 2 | 2 | 2 | 2761 |
| `yun2024:380` | 4 | 4 | 4 | 4 | 2 | 2 | 1372 |
| `yun2024:384` | 4 | 2 | 2 | 2 | 2 | 2 | 12120 |
| `yun2024:405` | 2 | 2 | 2 | 2 | 2 | 2 | 6702 |
| `yun2024:427` | 6 | 6 | 6 | 6 | 4 | 4 | 6819 |
| `yun2024:447` | 4 | 6 | 4 | 4 | 4 | 4 | 9863 |
| `yun2024:448` | 4 | 6 | 4 | 4 | 4 | 4 | 16905 |
| `yun2024:449` | 4 | 6 | 4 | 4 | 4 | 4 | 4632 |
| `yun2024:450` | 4 | 6 | 4 | 4 | 4 | 4 | 7032 |
| `yun2024:533` | 2 | 2 | 2 | 2 | 0 | 0 | 13567 |
| `yun2024:54` | 2 | 4 | 2 | 2 | 2 | 2 | 11123 |
| `yun2024:556` | 6 | 6 | 6 | 6 | 2 | 2 | 22168 |
| `yun2024:558` | 6 | 6 | 6 | 6 | 2 | 2 | 22383 |
| `yun2024:6` | 4 | 6 | 4 | 4 | 4 | 4 | 10169 |
| `yun2024:601` | 2 | 2 | 2 | 2 | 2 | 2 | 2477 |
| `yun2024:602` | 2 | 2 | 2 | 2 | 2 | 2 | 2428 |
| `yun2024:615` | 2 | 4 | 2 | 2 | 0 | 0 | 17518 |
| `yun2024:616` | 2 | 4 | 2 | 2 | 0 | 0 | 7115 |
| `yun2024:617` | 3 | 4 | 3 | 3 | 1 | 1 | 14502 |
| `yun2024:626` | 2 | 2 | 2 | 2 | 0 | 0 | 17883 |
| `yun2024:662` | 3 | 2 | 2 | 2 | 1 | 1 | 9393 |
| `yun2024:668` | 6 | 6 | 6 | 6 | 2 | 2 | 1780 |
| `yun2024:677` | 2 | 2 | 2 | 2 | 2 | 2 | 3102 |
| `yun2024:68` | 2 | 2 | 2 | 2 | 2 | 2 | 4848 |
| `yun2024:686` | 6 | 2 | 2 | 2 | 0 | 0 | 9940 |
| `yun2024:84` | 4 | 4 | 4 | 4 | 2 | 2 | 16039 |
| `yun2024:85` | 4 | 4 | 2 | 2 | 2 | 2 | 3066 |
| `yun2024:86` | 4 | 4 | 4 | 4 | 2 | 2 | 9112 |

## Nicht gerettet

| Record | Status | Klasse neu | Tokens neu | Reasoning-Zeichen |
|---|---|---|---|---|
| `yun2024:119` | weiter_ausfall | length_ohne_ergebnis | 24000 | 98142 |
| `yun2024:128` | weiter_ausfall | length_ohne_ergebnis | 24000 | 90927 |
| `yun2024:137` | fertig_ohne_zellen | - | 575 | 2643 |
| `yun2024:152` | weiter_ausfall | length_ohne_ergebnis | 24000 | 99665 |
| `yun2024:159` | weiter_ausfall | length_ohne_ergebnis | 24000 | 88346 |
| `yun2024:164` | weiter_ausfall | length_ohne_ergebnis | 24000 | 99794 |
| `yun2024:171` | weiter_ausfall | length_ohne_ergebnis | 24000 | 97231 |
| `yun2024:173` | weiter_ausfall | length_ohne_ergebnis | 24000 | 93443 |
| `yun2024:204` | weiter_ausfall | length_ohne_ergebnis | 24000 | 89548 |
| `yun2024:251` | weiter_ausfall | length_ohne_ergebnis | 24000 | 97921 |
| `yun2024:252` | weiter_ausfall | length_ohne_ergebnis | 24000 | 99829 |
| `yun2024:268` | fertig_ohne_zellen | - | 2501 | 10097 |
| `yun2024:269` | fertig_ohne_zellen | - | 3842 | 15019 |
| `yun2024:273` | weiter_ausfall | length_ohne_ergebnis | 24000 | 101270 |
| `yun2024:30` | weiter_ausfall | length_ohne_ergebnis | 24000 | 89370 |
| `yun2024:304` | weiter_ausfall | length_ohne_ergebnis | 24000 | 95635 |
| `yun2024:356` | weiter_ausfall | length_ohne_ergebnis | 24000 | 96159 |
| `yun2024:420` | weiter_ausfall | length_ohne_ergebnis | 24000 | 86878 |
| `yun2024:421` | weiter_ausfall | length_ohne_ergebnis | 24000 | 84549 |
| `yun2024:446` | weiter_ausfall | length_ohne_ergebnis | 24000 | 95071 |
| `yun2024:451` | weiter_ausfall | length_ohne_ergebnis | 24000 | 95333 |
| `yun2024:52` | weiter_ausfall | length_ohne_ergebnis | 24000 | 95546 |
| `yun2024:523` | weiter_ausfall | length_ohne_ergebnis | 24000 | 89661 |
| `yun2024:525` | weiter_ausfall | length_ohne_ergebnis | 24000 | 89708 |
| `yun2024:557` | weiter_ausfall | length_ohne_ergebnis | 24000 | 93380 |
| `yun2024:559` | weiter_ausfall | length_ohne_ergebnis | 24000 | 89528 |
| `yun2024:582` | weiter_ausfall | length_ohne_ergebnis | 24000 | 99406 |
| `yun2024:624` | weiter_ausfall | length_ohne_ergebnis | 24000 | 87507 |
| `yun2024:625` | weiter_ausfall | length_ohne_ergebnis | 24000 | 82625 |
| `yun2024:671` | weiter_ausfall | length_ohne_ergebnis | 24000 | 100255 |
| `yun2024:672` | weiter_ausfall | length_ohne_ergebnis | 24000 | 100367 |
| `yun2024:673` | weiter_ausfall | length_ohne_ergebnis | 24000 | 93498 |
| `yun2024:674` | weiter_ausfall | length_ohne_ergebnis | 24000 | 93674 |
| `yun2024:678` | weiter_ausfall | length_ohne_ergebnis | 24000 | 97070 |
| `yun2024:685` | weiter_ausfall | length_ohne_ergebnis | 24000 | 88956 |
| `yun2024:687` | weiter_ausfall | length_ohne_ergebnis | 24000 | 95376 |
