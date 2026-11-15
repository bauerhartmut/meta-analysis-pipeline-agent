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

Die T1/T2-Lücke ist geschlossen: `annotate_timepoints.py` liest jetzt
„1- (T1) and 4-months (T2)", „after 4 months" und „(T0)"; ein Monatswert direkt
vor einem T-Label schlägt dieses, und „30-month study period" (Studiendauer)
zählt nicht als Messzeitpunkt. `yun2024:114` trägt damit `month 4` statt leer.
Stand: **182 von 262** Records mit Ziel, davon 28 aus dem Outcome-Titel und
4 manuell.

## Grenzen der Stichprobe

* 17 von 262 Records geprüft (6,5 %); die Auswahl war systematisch, nicht
  zufällig, und deckt die auffälligen Fälle ab.
* „unklar" heißt: Der Text nennt einen Zeitpunkt in der Nähe, aber nicht im
  Satz der Goldzahl. Solche Labels sind nicht widerlegt, aber auch nicht belegt.

## Manuell festgelegte Fälle (15.11.2026)

Die vier „unklar"-Fälle der Stichprobe stehen jetzt mit Beleg in der manuellen
Tabelle `ZEITPUNKTE` (Gold unverändert):

| Record | Ziel | Beleg |
|---|---|---|
| `yun2024:150` | Postoperative 3rd month | TNR-Tabelle: „Postoperative 3rd month 0.25 (0.23--0.26)"; der Vergleichswert 0.27 ist der **präoperative Kontrollwert** — Gold mischt zwei Zeitpunkte, das Label folgt der Studienzelle |
| `yun2024:168` | end of study/treatment | „remission during their last documented study visit" (n = 28 / 20), letzter Studienbesuch |
| `yun2024:325` | baseline | „Of 14 subjects; 5 (35.7%) obtained 32 mg, 4 (28.6%) obtained 64 mg, and 5 (35.7%) obtained 96 mg" — Armgrößen bei Aufnahme |
| `yun2024:328` | baseline | Dosisgruppen 32 mg (n = 5) vs. 64 mg (n = 4) bei Aufnahme |

Bei 325/328 ist `baseline` zulässig, weil Gold nur Gruppengrößen enthält; bei
150 mischt Gold zwei Zeitpunkte, was als Beleg vermerkt ist statt stillschweigend
geglättet zu werden.

## Zweite Stichprobe: 8 neu entstandene Labels (15.11.2026)

Nach der Muster-Erweiterung geprüft, jeweils am Textfenster der Goldzahl:

| Record | Label vor Prüfung | Befund am Text | Urteil |
|---|---|---|---|
| `yun2024:203` | week 6 | „at the 6th week … 45,93 vs. 21,22 ng/mL" | bestätigt (besser als vorher `end of study`) |
| `yun2024:110` | month 4 | „assessed at baseline and at 1- (T1) and 4-months (T2)" | bestätigt |
| `yun2024:114` | month 4 | derselbe Satz | bestätigt |
| `yun2024:178` | week 14 | „14-week intervention" = **Interventionsdauer**, kein Messzeitpunkt | falsch |
| `yun2024:626` | week 2 | „2-week quadruple rescue therapy" = **Therapiedauer** | falsch |
| `yun2024:398` | day 10 | „10-day HhAntag treatment" (Mausversuch), Gold ist Überleben in Monaten | falsch |
| `yun2024:289` | week 4 | „4-week" steht 314 Zeichen entfernt, Gold stammt aus Pre/Post-Tabelle | unklar |
| `yun2024:574` | day 1 | „at 1 day following treatment" 486 Zeichen entfernt | unklar |

**Ergebnis: 3 bestätigt, 3 falsch, 2 unklar.** Der Fehler war systematisch: das
Bindestrich-Muster las Dauerangaben („14-week intervention") als Zeitpunkte.
Nach dem Umbau sind 626, 398 und 289 leer (richtig), 203 zusätzlich auf
`week 6` verbessert; 178 und 574 bleiben distance-bedingt unsicher.

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

**Zweiter Durchgang (nach der 8er-Stichprobe):**

7. Sieben Muster für dieselbe Aussage („week 6", „at 6 weeks", „6-week",
   „after 6 months" …) sind auf drei geschrumpft: Einheit-zuerst, Zahl-zuerst
   (`at|after`) und die T-Kennung. Das breite Bindestrich-Muster ist **weg** —
   es las Dauerangaben („14-week intervention", „2-week therapy",
   „10-day treatment") als Messzeitpunkte und erzeugte drei Fehllabels. Ersatz
   sind zwei präzise Muster: Zahl + Einheit + `(Tn)` („4-months (T2)") und
   Ordnungszahl („6th week").
8. Der **40-Zeichen-Filter** für T-Labels war falsch: er verglich gegen *jeden*
   Monatstreffer im Text (auch 40 Zeichen davor, auch aus fremdem Kontext) und
   enthielt eine tote Bedingung (`f[1] != "baseline"` in einem Zweig, der schon
   `f[1].startswith("T")` verlangt). Jetzt gilt: ein T-Label entfällt, wenn es
   **im** Treffer eines Monatsmusters liegt oder nur Leerraum/Bindestrich
   dazwischen steht — unabhängig von Zeichenzahlen.
9. `_KEINE_DAUER` (Negativ-Lookahead auf study/trial/period/…/therapy/treatment)
   bleibt nur für die `at|after`-Form nötig; die Bindestrichform braucht ihn
   nicht mehr.
