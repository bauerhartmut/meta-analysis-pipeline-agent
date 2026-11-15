# Bericht: Zeitpunktannotation und erster Extraktionslauf (15.11.2026)

Zusammenfassung aller Ergebnisse seit dem letzten Stand (`8670d4a`, Kandidaten-Split
eingefroren) bis `d2e06a5`. Alle Zahlen stammen aus den Artefakten im Repo oder
aus Läufen, die hier genannt sind; Gold wurde in keinem Schritt verändert.

## Kurzfassung

| Größe | Stand |
|---|---|
| Kandidaten-Split | 262 Records, 809 Goldzellen |
| davon mit belegtem Zielzeitpunkt | **186** (566 Goldzellen) |
| ohne Ziel | **76** (243 Goldzellen) |
| Extraktionslauf | 18 von 186 Records, 347.204 Tokens, **abgebrochen** |
| Rückfallpfad | belegt (`yun2024:75`), aber Labels ohne Einheit |
| Tests | 203 grün |

## 1. Prüfung der 64 unspezifischen Labels (`156e170`)

Die 64 Labels, die vorher `baseline` (47) oder `follow-up` (17) hießen, wurden an
den Belegstellen geprüft.

| Alt | geleert | auf konkrete Angabe gesetzt | behalten |
|---|---|---|---|
| baseline (47) | 21 | 26 | 0 |
| follow-up (17) | 1 | 7 | 9 |

**64 geprüft, 55 geändert, 22 geleert.** Die 9 behaltenen `follow-up` sind
Records, deren Gold nur Gruppengrößen enthält. Jede Entscheidung steht mit
alt/neu und Belegzitat in `candidate_split_20261115/zeitpunkte.md`.

## 2. Heuristik verschärft

Drei Regeln, in dieser Reihenfolge (`annotate_timepoints.py`):

1. **Satz der Goldzahl** — Zeitpunktangabe im selben Satz wie die Goldzahl; bei
   Ergebniszellen nicht `baseline`/`follow-up`.
2. **Nächste Angabe** — nur ohne Satzangabe; bei Mittelwerten/Ereignissen sind
   `baseline`/`follow-up` gesperrt, `week/month/day 0` wird zu `baseline`.
3. **Nichts belegt → leer** (`not stated`) statt raten.

## 3. Stichprobe 1: 12 korrigierte + 5 geleerte Labels (`4d89ea0`)

Geprüft direkt am Artikeltext, systematisch gezogen (jeder dritte bzw. vierte).

**Ergebnis: 5 bestätigt, 4 falsch, 3 unklar; von 5 Leerungen 4 richtig, 1 falsch.**

Befund: Der Zielzeitpunkt steht oft schon im **Outcome-Namen**
(„Baseline Height", „BMI reduction at 12 months"). Seitdem liest
`zeitpunkt_aus_outcome()` ihn zuerst (`auto (Outcome-Titel)`, 28 Records).
Damit korrigiert: `yun2024:159` → `month 12`, `183/277/281` → `baseline`.

## 4. T1/T2-Lücke geschlossen + vier Fälle manuell (`387dda9`)

Neue Muster: `4-months`, `after 4 months`, `(T0)`→`baseline`, Ordnungszahl
(`6th week`); Studiendauer (`30-month study period`) zählt nicht.
`yun2024:114` trägt seitdem `month 4` statt leer.

Vier unklare Fälle mit Beleg in `ZEITPUNKTE` (Gold unverändert):

| Record | Ziel | Beleg |
|---|---|---|
| `yun2024:150` | Postoperative 3rd month | TNR-Tabelle: „Postoperative 3rd month 0.25"; 0.27 ist der präoperative Kontrollwert — **Gold mischt zwei Zeitpunkte** |
| `yun2024:168` | end of study/treatment | „remission during their last documented study visit" (n = 28/20) |
| `yun2024:325` | baseline | Dosisarmgrößen bei Aufnahme (5/4/5) |
| `yun2024:328` | baseline | Dosisarmgrößen 32 mg (5) vs. 64 mg (4) |

## 5. Muster-Review + Stichprobe 2 (`00d98e9`)

Sieben Muster für dieselbe Aussage wurden auf drei reduziert (Einheit-zuerst,
Zahl-zuerst, T-Kennung). Das breite Bindestrich-Muster entfiel: Es las Dauern
(„14-week intervention", „2-week therapy", „10-day treatment") als Zeitpunkte.
Der **40-Zeichen-Filter** für T-Labels war fehlerhaft (verglich gegen jeden
Monatstreffer, enthielt eine tote Bedingung) und wurde durch eine
Überlappungsprüfung ersetzt.

Stichprobe 2 (8 neu entstandene Labels, am Text geprüft):
**3 bestätigt, 3 falsch, 2 unklar.** Die drei falschen waren alle
Dauerangaben — Anlass für den Umbau. Danach: `626`, `398`, `289` leer statt
falsch; `203` auf `week 6` verbessert.

## 6. Abstandsobergrenze (`67283c2`, `045be4e`)

Gemessen vor der Änderung: 121 Labels kamen aus der Näherungsregel, davon
**60 weiter als 400 Zeichen** entfernt, der weiteste bei 3729 Zeichen.

Erste Fassung (Grenze für alle): 59 Records leer — davon **58 mit
ausschließlich Gruppengrößen**, wo `baseline` richtig war. Deshalb Endfassung:
Grenze nur bei **Ergebniszellen** (`hat_ergebnis`). Ergebnis: genau **ein**
Record geleert (`yun2024:178`, 1206 Zeichen), die 58 Gruppengrößen-Records
behalten ihr `baseline`.

## 7. Verteilung des Splits (Stand heute)

| Status | Records |
|---|---|
| `auto` (Näherung) | 119 |
| `auto (Satz der Goldzahl)` | 35 |
| `auto (Outcome-Titel)` | 28 |
| `manuell` | 4 |
| `not stated` | 57 |
| `not stated (nur unspezifische Angaben)` | 18 |
| `not stated (zu weit entfernt)` | 1 |
| **Summe** | **262** (186 mit Ziel, 76 ohne) |

Häufigste Ziele: `baseline` 104, `week 24` 17, `day 1` 10, `month 6` 8,
`follow-up` 8, `month 12` 7, `month 4` 6.

## 8. Laufvorbereitung (`de885c7`, `f6c2a11`)

Dabei fiel ein stiller Fehler auf: `records/yun.jsonl` trägt die
Auto-Annotation **nicht** — nur 4 der 186 hatten dort ein Ziel. Der naive
Befehl hätte 182 Records ohne Ziel extrahiert und sie als `v2_timepoint`
etikettiert, ohne dass es im Log auffällt. Behoben durch die neue Option
`--records` und zwei eingefrorene Teilsätze:

| Datei (gitignored) | Records | Zellen | Ziel | Version |
|---|---|---|---|---|
| `records/yun_test186.jsonl` | 186 | 566 | 186 | `v6_target_fallback` |
| `records/yun_test76_ohne_ziel.jsonl` | 76 | 243 | 0 | `v2_timepoint` |

Die Auswahl per `--ids` wurde in `waehle_records()` gezogen und ist getestet
(alternative Datei, ID-Auswahl, `v2_timepoint` ohne Ziel).

## 9. Pilotlauf über 3 Records (`fcbeff1`)

| Record | Ziel | Version | Zellen | Zeitpunkt an Zelle | Tokens | Dauer |
|---|---|---|---|---|---|---|
| `yun2024:35` | baseline | `v6_target_fallback` | 6 | ja | 4.581 | 17,7 s |
| `yun2024:68` | baseline | `v6_target_fallback` | 2 | ja | 4.438 | 20,8 s |
| `yun2024:67` | baseline | `v6_target_fallback` | 2 | ja | 6.461 | 29,7 s |

Alle Etiketten korrekt, 10/10 Zellen mit Zeitpunkt, keine Retries.
Hochrechnung damals: ≈ 0,96 Mio Tokens für 186 Records.

## 10. Vollauf: nach 18 Records abgebrochen (`d2e06a5`)

Freigabe mit Grenze 1,2 Mio Completion-Tokens. Vorab zwei Records mit
spezifischem Ziel, um den Rückfallpfad zu belegen:

| Record | Ziel | Ergebnis |
|---|---|---|
| `yun2024:75` | `week 24` | 6 Zellen; Intervention `tp='24'`, **Komparator `tp='0'`** |
| `yun2024:159` | `month 12` | 0 Zellen, beide Versuche `finish_reason=length` |

**Rückfallpfad belegt** (Abweichung vom Ziel wird genannt), aber zwei Mängel:
Labels kommen **ohne Einheit** (`'24'` statt `week 24`, wird von
`klassifiziere()` als `rueckfall` gezählt), und bei `75` wurde über die Arme
hinweg gemischt.

| Messpunkt | Records | Tokens | leer | Prognose 186 |
|---|---|---|---|---|
| Vorab-Records | 2 | 84.646 | 1 | — |
| ~2,5 min | 13 | 180.052 | 1 | 2,6 Mio |
| ~7 min | 17 | 334.988 | 3 | 3,7 Mio |
| **Abbruch** | **18** | **347.204** (29 % der Grenze) | 3 | ≈ 3,5 Mio |

**Ursache:** 48 % der Tokens (168.000) gingen in drei Records mit
`finish_reason=length` in beiden Versuchen (je 24.000 + 32.000 Tokens, null
Zellen): `yun2024:159`, `79`, `114`. Median der übrigen Zeilen 6.500–11.000.
Der Lauf wäre bei diesem Tempo nach ~60 Records an die Grenze gestoßen.

Der Teilsatz ist intakt und fortsetzbar: 18 Zeilen, alle parsebar, alle
`v6_target_fallback`, 64/64 Zellen mit Zeitpunkt, 3 leer (alle aus der
Length-Schleife). Ein Neustart mit demselben `--run-id` überspringt sie.

## 11. Offene Punkte

1. **Length-Schleifen** kosten 56.000 Tokens je Fall ohne Ergebnis; der
   automatische Retry mit 32.000 Tokens verdoppelt den Schaden.
2. **Labelform**: `'24'`, `'0'` sind ohne Einheit nicht mit `week 24`
   vergleichbar — die Rückfallquote wäre sonst Formatrauschen.
3. **Arm-Mischung** in `yun2024:75` (Intervention Woche 24, Komparator Baseline).
4. **76 Records ohne Ziel** sind noch nicht gelaufen (Kohorte B, Befehl im Plan).
5. 5 der 186 Artikel werden bei 45.000 Zeichen gekürzt.

## 12. Empfehlung

Vor dem Neustart zwei kleine Eingriffe, dann denselben `--run-id` fortsetzen:
Bei `finish_reason=length` **nicht** erneut mit 32.000 Tokens wiederholen,
sondern als Fehlzeile markieren; und Zeitpunkt-Labels auf Einheiten normalisieren
(`'24'` → `week 24`, nur wenn belegt). Kosten: zwei Änderungen plus Tests, kein
Netzzugang. Danach rechnet sich der Rest auf ≈ 0,9–1,1 Mio Tokens für die
verbleibenden 168 Records.

## 13. Artefakte und Commits

| Commit | Inhalt |
|---|---|
| `156e170` | 64 unspezifische Labels geprüft, Heuristik gehärtet |
| `4d89ea0` | Outcome-Titel als erste Quelle, Stichprobe 1 dokumentiert |
| `387dda9` | T1/T2-Notation, vier manuelle Fälle, Dauer-Ausschluss |
| `00d98e9` | Muster zusammengeführt, 40-Zeichen-Filter ersetzt |
| `67283c2` | Abstandsgrenze 400 (pauschal) |
| `045be4e` | Abstandsgrenze nur für Ergebniszellen |
| `de885c7` | Laufplan, `--records` im Runner |
| `f6c2a11` | Tests für `--records`, 76 Records eingefroren |
| `fcbeff1` | Pilotlauf über 3 Records |
| `d2e06a5` | Abbruch nach 18 Records dokumentiert |

Dokumente: `analysis/candidate_split_20261115/{report.md, zeitpunkte.md,
zeitpunkt_stichprobe.md}` und `analysis/run186_20261115/{plan.md, pilot.md,
abbruch.md, ids.txt, ids_ohne_ziel.txt}`.
