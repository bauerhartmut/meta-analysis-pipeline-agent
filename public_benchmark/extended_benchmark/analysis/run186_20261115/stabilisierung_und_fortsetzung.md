# Stabilisierung und Fortsetzung des 186er-Laufs (15.11.2026)

Basis: `b2e24e6` (nach `f1d406f`). Gold, Kandidaten-Split und die 18 alten
Ergebniszeilen wurden nicht verändert.

## 1. Ursachen der drei Probleme

**a) Length-Schleifen.** Der Runner behandelte `finish_reason = length` als
Retry-Fall und wiederholte den Aufruf mit 32.000 statt 24.000 Tokens. Die
Ursache der Schleife selbst liegt im Modell (Reasoning ohne Abschluss), der
Runner verdoppelte aber den Schaden: In drei Records kostete das je 56.000
Tokens für null Zellen. Am 45.000-Zeichen-Prompt liegt es nicht — der Fehler
tritt auch bei 10.000-Zeichen-Artikeln auf (`yun2024:119`, `117`).

**b) Zeitpunkte ohne Einheit.** Die Artikel drucken Spaltenköpfe als nackte
Zahl (`0`, `12`, `24`). Das Modell kopiert sie „exactly as printed", also
`'24'`. Die Auswertung verglich diese Rohzeichenkette mit dem Ziel `week 24`
und klassifizierte jeden Treffer als `rueckfall` — ein Formatproblem, kein
inhaltliches. Belegt an `yun2024:75`: Zellen tragen `'24'`/`'0'`, Ziel ist
`week 24`.

**c) Armmischung.** Der v6-Prompt erlaubt den Rückfall **je Feld**: „If a field
is not reported at the target time point, use the closest reported time point
instead". Damit darf der Komparator einen anderen Zeitpunkt tragen als die
Intervention. Das ist die Ursache in der Extraktionslogik — der Prompt schreibt
Armkonsistenz nirgends vor und die Nachverarbeitung prüft sie nicht.

**Zusatzbefund `yun2024:75` (Gold-Konflikt, keine Änderung):** Die Tabelle
„Non-smokers (placebo, n = 27)" führt bei Woche 24 den Wert `11.00 ± 3.88`, die
Zeile „Non-smokers (palmvitee, n = 29)" bei Woche 0 `11.97 ± 4.00` und bei
Woche 24 `13.72 ± 4.53`. Gold trägt aber `intervention_mean = 11.97` (palmvitee,
**Woche 0**) und `comparator_mean = 13.72` (palmvitee, **Woche 24**, n = 29) —
also palmvitee-Baseline gegen palmvitee-Follow-up, mit der palmvitee-Gruppengröße
im Komparator. Das Modell lieferte `13.72 @ '24'` (Intervention) und
`11.97 @ '0'` (Komparator): die Zahlen stimmen für die palmvitee-Zeile, die
Armzuordnung ist gegenüber Gold vertauscht. Der Datensatz ist an dieser Stelle
selbst inkonsistent; Gold bleibt unangetastet.

## 2. Geänderte Dateien und Funktionen

| Datei | Funktion | Änderung |
|---|---|---|
| `run_extended_extraction.py` | `fehlerklasse_aus()` (neu) | klassifiziert `length_ohne_ergebnis` und `json_kaputt` |
| | `work()` | kein Retry bei `length`; nur `json_kaputt` wird einmal mit **gleichem** Limit wiederholt |
| | Zeilenschema | neue Felder `fehlerklasse`, `failed` |
| | `done_keys()` | Fehlzeilen zählen als erledigt; `retry_failed=True` nimmt sie aus |
| | CLI | neues Flag `--retry-failed` |
| `evaluate_fallback.py` | `normalisiere_label()` (neu) | ergänzt Einheit nur aus dem annotierten Ziel |
| | `arme_gemischt()` (neu) | erkennt unterschiedliche Zeitpunkte je Arm |
| | `main()` | nutzt Normalisierung vor `klassifiziere()`, zählt `unklar` und `arm_gemischt` getrennt |

Kein Prompt wurde geändert (Begründung in Abschnitt 9).

## 3. Durchgeführte Änderungen im Detail

* **Length:** endet ein Versuch mit `finish_reason = length`, wird die Zeile mit
  `fehlerklasse = "length_ohne_ergebnis"` und `failed = true` geschrieben; Log:
  `glm: <record> FEHLER length_ohne_ergebnis (<n> Tokens, kein Retry)`.
* **JSON:** `kein_json`, `kein_objet`, `json_fehler` bleiben Retry-Fälle (ein
  Versuch, gleiches Limit). Danach `fehlerklasse = "json_kaputt"`.
* **Fortsetzen:** jede vorhandene Zeile gilt als erledigt, damit derselbe
  Record nicht erneut in die Schleife läuft. `--retry-failed` erzwingt die
  Wiederholung.
* **Normalisierung:** `normalisiere_label(label, target)` → `(label, status)`.
  `'24'` + Ziel `week 24` → `week 24`; `'6'` + `month 6` → `month 6`;
  `'0'` + Ziel `baseline` → `baseline`; ohne passendes Ziel → `("", "unklar")`.
  Die Rohantwort bleibt in `runs/.../predictions.jsonl` (`rows[].timepoint`)
  und in den `unklar`-Beispielen erhalten.
* **Armprüfung:** `arme_gemischt(cells, target)` vergleicht die Rohlabels je Arm;
  Treffer werden gezählt und mit Record-IDs gelistet.

## 4. Neue Regressionstests

| Test | Deckt ab |
|---|---|
| `test_length_bekommt_keinen_zweiten_versuch` | Length → Fehlzeile; JSON bleibt Retry; Erfolg ohne Klasse |
| `test_fehlzeile_ist_im_datensatz_erkennbar` | `fehlerklasse` + leere `rows` |
| `test_fortsetzen_ueberspringt_erfolgreiche_und_fehlzeilen` | Resume überspringt, `--retry-failed` wiederholt |
| `test_kaputtes_json_zaehlt_nicht_als_erfolg` | kaputtes JSON → `json_kaputt`, keine Zellen |
| `test_normalisierung_ergaenzt_einheit_nur_mit_beleg` | `24`/`week 24`, `6`/`month 6`, `1`/`day 1`, mehrdeutig |
| `test_null_wird_nur_bei_belegter_baseline_zu_baseline` | `0`/`baseline` ok, `0`/`week 24` unklar |
| `test_bereits_korrekte_labels_bleiben_unveraendert` | `week 24`, `baseline`, `Post-test` unverändert |
| `test_arme_behalten_ihre_zeitpunkte` | gleich/gemischt/fehlender Arm |

Ergebnis: **211 Tests grün** (vorher 203).

## 5. Commits

| Commit | Inhalt |
|---|---|
| `b2e24e6` | Length ohne Retry, Label-Normalisierung, Armprüfung, 8 neue Tests |

## 6. Fortgesetzte Records

Vor dem Start geprüft: `done_keys` erkennt **18** erledigte Zeilen, davon 15
erfolgreich; die 3 Fehlzeilen (`159`, `79`, `114`) werden ohne
`--retry-failed` nicht wiederholt. Offene Aufträge beim Start: **168**.

Tatsächlich fortgesetzt: **10 Records** (Zeilen 19–28), dann gestoppt. Stand:
**28 von 186**.

## 7. Tatsächlicher Tokenverbrauch

| Posten | Tokens |
|---|---|
| 18 Zeilen aus dem ersten Lauf | 347.204 |
| 10 Zeilen aus der Fortsetzung | 145.364 |
| **gesamt** | **492.568** (41 % der 1,2-Mio-Grenze) |
| je Zeile (gesamt) | 17.591 |

Von den 145.364 Tokens der Fortsetzung gingen **120.000 (83 %)** in die fünf
Length-Fehlzeilen à 24.000. Die erfolgreichen Zeilen lagen bei 1.346–10.816
Tokens (Median ≈ 4.700). Die Fortsetzung selbst ist also billiger geworden —
der Retry-Aufschlag (32.000) ist weg.

## 8. Fehlerquote und Length-Fehler

* **5 Length-Fehler** in 10 neuen Records (50 %) — alle `length_ohne_ergebnis`,
  je 24.000 Tokens, **ohne** zweiten Versuch.
* 0 JSON-Fehler. 1 leerer Record ohne Fehlzeile (`yun2024:137`,
  `keine_verwertbaren_zellen`, das Modell meldet „keine Ergebnisse" — zulässig).
* Zellklassen der 28 Zeilen: **33 zieltreu, 33 Rückfall, 12 unklar**.
* Anteil Zellen mit belegtem, normalisiertem Zeitpunkt: **66 von 78 (85 %)**;
  12 bleiben ohne Einheit, weil das Ziel sie nicht belegt.
* Gold unverändert; keine bestehende Zeile überschrieben.

## 9. Bewertung der Studienarmzuordnung

**7 von 28 Records** tragen unterschiedliche Zeitpunkte je Arm:
`yun2024:75`, `76`, `78`, `80`, `81`, `149`, `150`. Bei `75` ist die Ursache
zusätzlich ein Gold-Konflikt (Abschnitt 1c): Die Goldzellen mischen palmvitee-
Baseline mit palmvitee-Woche-24 und nennen die palmvitee-Gruppe als Komparator.

Der Prompt wurde **nicht** geändert: Die erlaubte Feld-für-Feld-Rückfallregel
ist Teil von v6; eine Änderung mitten im Lauf würde Zeilen unter zwei
Prompt-Fassungen mischen und das Versionsetikett entwerten. Die Prüfung ist
deshalb als Auswertungsklasse `arm_gemischt` umgesetzt und die Ursache
dokumentiert. Eine saubere Lösung wäre ein v7 mit der Zusatzregel „beide Arme
einer Zeile am selben Zeitpunkt; ist ein Arm dort nicht berichtet, entfällt die
Zelle" und eigener Run-ID.

## 10. Verbleibende Probleme und Empfehlungen

1. **Kosten pro Record bleiben zu hoch für 158 Records.** Ohne Length-Fehler
   ≈ 6.000 Tokens je Record → ≈ 0,95 Mio für den Rest; mit den beobachteten
   50 % Length-Fehlern à 24.000 wären es ≈ 2,8 Mio. Die 1,2-Mio-Grenze ist damit
   nicht erreichbar.
2. **Length-Fehler sind nicht behoben, nur entpreist.** Sie kosten jetzt 24.000
   statt 56.000 Tokens. Ein kleineres `--max-tokens` (z. B. 16.000) würde sie
   weiter verbilligen; das Risiko ist ein Abschneiden langer, aber gültiger
   Antworten (Median gültig ≈ 4.700).
3. **Armmischung ist systematisch** (7/28) und mindestens einmal goldbedingt.
   Ohne v7-Prompt bleibt sie eine dokumentierte Unsicherheit.
4. **Zwei Kohorten** (76 ohne Ziel) sind noch nicht gelaufen.

**Empfehlung:** Lauf bleibt gestoppt. Für die Fortsetzung entweder (a) die
Grenze bewusst auf 2,5 Mio anheben und in einem Zug durchlaufen, oder (b)
`--max-tokens 16000` setzen, damit Fehlversuche 16.000 statt 24.000 kosten, und
in zwei Etappen laufen. Vor beidem würde ich `yun2024:75` in die dokumentierten
Gold-Konflikte aufnehmen, damit die Auswertung den Record korrekt als
Konfliktfall führt statt als Modellfehler.
