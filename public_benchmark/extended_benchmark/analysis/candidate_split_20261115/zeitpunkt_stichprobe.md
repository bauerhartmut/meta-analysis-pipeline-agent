# Stichprobe der Zeitpunkt-Labels (15.11.2026)

Geprüft wurden **12 korrigierte** und **5 geleerte** Labels direkt am Artikeltext
(Textfenster der Goldzahlen, nicht die Heuristik). Auswahl: die korrigierten
Records alphabetisch jeder dritte, die geleerten jeder vierte — also
systematisch, nicht nach Auffälligkeit.

## Korrigierte Labels (12)

| Record | Dokument | Label | Befund am Text | Urteil |
|---|---|---|---|---|
| `yun2024:116` | PMC4323894 | month 6 | „6 months post-trauma … (70 % vs. 15,4 % attained good GOS)" trägt die Goldzahl | bestätigt |
| `yun2024:119` | PMC4323894 | month 6 | derselbe Satz, Goldzahlen 70 / 15,4 | bestätigt |
| `yun2024:150` | PMC4996097 | month 1 | Zeitpunkt nur 234 Zeichen entfernt, aber nicht im Satz der Goldzahl; die Studie berichtet Monate 0–11 | unklar |
| `yun2024:159` | PMC5056957 | month 24 → **month 12** | Outcome-Titel „BMI reduction at 12 months"; Spalte mit n = 459 ist die 12-Monats-Spalte | war falsch, jetzt korrigiert |
| `yun2024:162` | PMC5056957 | month 24 | „At 24 months …", Spalte n = 560 / 425 | bestätigt |
| `yun2024:168` | PMC5079604 | end of study/treatment | „end of the study" 425 Zeichen entfernt; Gruppengrößen sind Remission/Relapse, nicht Arme | unklar |
| `yun2024:183` | PMC5122613 | week 3 → **baseline** | Outcome „Baseline characteristics and diet"; Werte stehen in der Baseline-Tabelle | war falsch, jetzt korrigiert |
| `yun2024:203` | PMC5380326 | end of study/treatment | 6 Wochen Supplementierung, Werte danach (45,93 vs. 21,22 ng/mL) | bestätigt |
| `yun2024:277` | PMC3654355 | month 12 → **baseline** | Outcome „Baseline Height", Werte in der Baseline-Tabelle | war falsch, jetzt korrigiert |
| `yun2024:281` | PMC3654355 | month 12 → **baseline** | Outcome „baseline fat-free mass", Baseline-Tabelle | war falsch, jetzt korrigiert |
| `yun2024:325` | PMC5559992 | day 1 | Einmaldosis, aber kein Zeitpunkt im Satz der Goldzahl | unklar |
| `yun2024:328` | PMC5559992 | day 1 | wie oben | unklar |

**Ergebnis: 5 bestätigt, 4 waren falsch (jetzt korrigiert), 3 unklar.**

## Geleerte Labels (5)

| Record | Dokument | Befund am Text | Urteil |
|---|---|---|---|
| `yun2024:101` | PMC4188762 | nur Prozentwerte des Withdrawal, keine Zeitpunktangabe | Leerung richtig |
| `yun2024:105` | PMC4188762 | wie oben | Leerung richtig |
| `yun2024:114` | PMC4319071 | Text nennt „assessed at baseline and at 1- (T1) and 4-months (T2) postintervention" | **Leerung falsch** — Zeitpunkte stehen da, nur in T1/T2-Notation |
| `yun2024:129` | PMC4493951 | keine Zeitpunktangabe zum Sedation-Score | Leerung richtig |
| `yun2024:142` | PMC4880652 | Zeitpunkt steckt im Outcome-Namen („at 0 minutes"), nicht im Text | Leerung vertretbar |

**Ergebnis: 4 Leerungen richtig, 1 falsch (T1/T2-Lücke der Muster).**

## Was daraus geändert wurde

Die Stichprobe zeigte einen systematischen Fehler: Der Zielzeitpunkt steht oft
schon im **Outcome-Namen** („Baseline Height", „BMI reduction at 12 months",
„at 6 months post-trauma"). Seit dem 15.11.2026 liest die Annotation deshalb
zuerst den Outcome-Titel (`auto (Outcome-Titel)`); er schlägt Textregel und
Nähe. Damit sind vier der fünf Fehl-Labels behoben (159, 183, 277, 281).

Offen bleibt die T1/T2-Notation (`yun2024:114`) — die Muster kennen nur
„week/month/day N". 27 Records tragen jetzt ein Label aus dem Outcome-Titel,
177 von 262 haben ein Ziel.

## Grenzen der Stichprobe

* 17 von 262 Records geprüft (6,5 %); die Auswahl war systematisch, nicht
  zufällig, und deckt die auffälligen Fälle ab.
* „unklar" heißt: Der Text nennt einen Zeitpunkt in der Nähe, aber nicht im
  Satz der Goldzahl. Solche Labels sind nicht widerlegt, aber auch nicht belegt.

## Code-Review `annotate_timepoints.py` (frischer Blick)

**Entfernt (verhaltensneutral geprüft):**

1. Ein Nachlauf-Block in `annotate_kandidaten`, der `baseline`/`follow-up` bei
   Ergebniszellen verwarf, war nach der Verschärfung **unerreichbar**: beide
   Stufen von `zeitpunkt_aus_text` filtern unspezifische Labels bereits, und
   `baseline` aus dem Outcome-Titel sollte stehen bleiben. Der Status
   `not stated (unspezifisch bei Ergebniszellen)` kam 0-mal vor. Block gelöscht
   (12 Zeilen), Regeneration ergab **0 Abweichungen** bei 262 Records.
2. `UNSPEZIFISCH` enthielt `week 0`/`month 0`/`day 0`, die `_zeitpunkt_funde`
   vorher schon zu `baseline` normalisiert — tote Einträge, entfernt.

**Offen, bewusst nicht geändert:**

3. `status` trägt zwei Informationen (Herkunft *und* Sicherheit), und die
   Prüftabelle hängt an String-Vergleichen (`"auto (Satz der Goldzahl)"`).
   Sauberer wäre ein eigenes Feld `methode` ∈ {outcome, satz, naehe, keine}.
   Preis: Schema-Änderung im eingefrorenen Split plus Neuerzeugung der
   Markdown-Dateien — erst nach der nächsten Runde sinnvoll.
4. `annotate_kandidaten` ist ~150 Zeilen und macht vier Dinge (Split-Auswahl,
   Annotation, Prüftabelle, Markdown). Ein `schreibe_md()` würde das trennen.
5. `abstand` ist je nach Pfad `int` oder `""`; `None` wäre eindeutig.
6. Der zweite `zeitpunkt_aus_text`-Aufruf (`hat_ergebnis=False`) existiert nur
   für die einmalige Prüftabelle. Gemessen: 2,0 s für beide Läufe über
   3.744.667 Textzeichen — kein Problem, kann nach Abschluss der Prüfung weg.
