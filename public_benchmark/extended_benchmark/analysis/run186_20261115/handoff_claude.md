# Übergabe an Claude: drei offene Probleme der Extraktionspipeline

Stand: 15.11.2026, während der Lauf über 186 Records weiterläuft. Dieses
Dokument beschreibt nur, was belegt ist, und nennt die Stellen im Code. Ziel ist
eine Lösungsskizze für die drei Probleme in Abschnitt 4–6, ohne Gold-Daten oder
den eingefrorenen Split anzutasten.

## 1. Worum es im Projekt geht

`public_benchmark/extended_benchmark/` ist ein Benchmark für **numerische
Extraktion aus RCT-Publikationen**. Ein Record beschreibt eine Zielzelle
(Intervention/Komparator, Outcome, Zeitpunkt) und enthält Gold-Zellen mit den
richtigen Zahlen. Ein Sprachmodell bekommt den Artikeltext und soll Zellen im
JSON-Format zurückgeben; die Auswertung vergleicht Zahl und Zeitpunkt.

| Kennzahl | Wert |
|---|---|
| Kandidaten-Split | 262 Records, 809 Goldzellen |
| davon mit belegtem Zielzeitpunkt | 186 Records, 566 Zellen |
| ohne Zielzeitpunkt (zweite Kohorte, noch nicht gestartet) | 76 Records, 243 Zellen |
| Dev-Split (Referenzläufe v1–v11) | 43 Records, 170 Zellen |

Gold ist **unveränderlich**. Wo Gold fehlerhaft erscheint, wird das dokumentiert
und der Record als Konfliktfall geführt, nicht korrigiert.

## 2. Datenfluss

```
records/yun.jsonl (450 Records, Gold + Kontext)
   └─ annotate_timepoints.py  →  records/yun_kandidaten.jsonl (262, mit timepoint)
        └─ records/yun_test186.jsonl (eingefroren, 186, mit Ziel)
             └─ run_extended_extraction.py  →  runs/<run_id>/predictions.jsonl
                  └─ evaluate_fallback.py / evaluate_extended.py
```

`runs/<run_id>/predictions.jsonl` hat **eine Zeile je (record_id, model)** mit
u. a. `rows` (die Zellen), `target_timepoint`, `prompt_version`,
`completion_tokens`, `retry_tokens`, `finish_reason`, `parse_error`,
`fehlerklasse`, `failed`, `timepoints` (chosen/discarded), `elapsed_s`.

## 3. Aktueller Zustand des Laufs

Run-ID `yun_test186_v6_20261115`, Modell `glm`, Prompt `v6_target_fallback`,
`--workers 3`, ab dem zweiten Abschnitt `--max-tokens 16000`.

| Größe | Wert (Stand beim Schreiben) |
|---|---|
| Zeilen geschrieben | 47 von 186 |
| Completion-Tokens gesamt | 692.395 |
| davon Length-Fehlzeilen | 14 (je 16.000 Tokens seit der Umstellung) |
| Zellen | 107 |
| Records mit Armdivergenz | 7 (in der ersten Teilmenge von 28 gemessen) |

Der Lauf ist fortsetzbar: `done_keys()` überspringt vorhandene Zeilen, auch
Fehlzeilen; `--retry-failed` nimmt Fehlzeilen aus.

## 4. Problem 1: Reasoning-Schleifen (`finish_reason = length`)

**Beobachtung.** Ein Teil der Aufrufe endet ohne Inhalt, nachdem das Modell das
Tokenlimit erreicht hat (`finish_reason = length`, `content = ""`). Betroffen
waren in der ersten Teilmenge 5 von 10 neuen Records (50 %), im Gesamtstand
14 von 47 Zeilen (30 %). Die Artikel sind dabei nicht besonders lang
(`yun2024:119` und `117`: 10.032 Zeichen; `yun2024:115`: 49.917 Zeichen).

**Bereits geändert** (`run_extended_extraction.py`):
* `fehlerklasse_aus()` markiert `length` als `length_ohne_ergebnis`, `failed = true`.
* Kein Retry mehr bei `length` (vorher 24.000 + 32.000 = 56.000 Tokens für null Zellen).
* Nur `json_kaputt` bekommt einen zweiten Aufruf, gleiches Limit.
* Aufrufebene ist getestet: `test_length_loest_keinen_zweiten_api_aufruf_aus`
  prüft mit gefälschtem `call()`, dass genau **ein** Aufruf passiert;
  `test_kaputtes_json_bekommt_genau_einen_zweiten_aufruf` prüft zwei.

**Offen.** Der Ausfall selbst ist nicht behoben, nur verbilligt (16.000 statt
56.000 Tokens). 30 % der Records liefern damit keine Daten, und die Ausfälle
sind nicht zufällig verteilt.

**Optionen, die geprüft werden sollen**
1. Prompt: JSON zuerst verlangen („return the JSON object first, no reasoning"),
   oder Reasoning-Spur explizit verbieten.
2. `max_tokens` weiter senken (Median gültiger Antworten ≈ 4.700 Tokens) — Trade-off:
   lange Tabellenantworten werden abgeschnitten und zählen als Fehlzeile.
3. Ein zweiter Aufruf mit **anderem** Prompt (nicht größerem Limit), etwa
   kompaktem Zellschema — das ist kein „Retry derselben Anfrage".
4. Text vorher kürzen (Tabellenpriorisierung statt `text[:45000]`), damit weniger
   Kontext zu durchsuchen ist.
5. Modellwechsel für die Fehlzeilen (zweiter Lauf mit `qwen30`), Kosten verdoppeln sich.

**Frage an Claude:** Welche Option ist am wahrscheinlichsten wirksam, ohne das
Versionsetikett `v6_target_fallback` zu entwerten? Ein Promptwechsel mitten in
dieser Run-ID ist ausgeschlossen, weil dann zwei Prompt-Fassungen in einer
Ergebnisdatei liegen; ein Wechsel braucht eine neue Run-ID.

## 5. Problem 2: Zeitpunkt-Labels ohne Einheit

**Beobachtung.** Die Artikel drucken Tabellenspalten als nackte Zahl (`0`, `12`,
`24`). Der Prompt verlangt „copied exactly as printed", das Modell liefert
`'24'`, `'0'`, `'12'`. Die Auswertung verglich das roh mit dem Ziel
`week 24` und zählte jeden Treffer als Rückfall (Formatrauschen).

**Bereits geändert** (`evaluate_fallback.py`):
`normalisiere_label(label, target) -> (label, status)` ergänzt eine Einheit
**nur aus dem annotierten Ziel**: `'24'` + Ziel `week 24` → `week 24`;
`'0'` + Ziel `baseline` → `baseline`; `'24'` + Ziel `month 6` → `("", "unklar")`.
Rohlabel bleibt in `rows[].timepoint` erhalten; mehrdeutige Zellen landen in der
Klasse `unklar` (12 von 78 Zellen in der Teilmenge).

**Offen.** Die Normalisierung ist zielabhängig und damit zirkulär: Sie kann
einen Treffer nur bestätigen, wenn das Modell ohnehin den Zielzeitpunkt gewählt
hat. Bei einem echten Rückfall (`'12'` statt `week 24`) bleibt die Einheit
unklar, obwohl der Artikel sie kennt (Spaltenkopf „Weeks 12").

**Optionen**
1. Das Modell soll zusätzlich den **Spaltenkopf wörtlich** zurückgeben
   (`timepoint_header`), dann ist die Einheit belegt, ohne im Ziel nachzusehen.
2. Einheiten aus dem Artikel ziehen: Tabellenkopf in der Nähe der Zelle suchen
   (`annotate_timepoints._satz_um` / `candidate_split.finde` liefern Positionen).
3. Positionszuordnung: Spaltenindex der Zahl in der Tabellenzeile bestimmen und
   dem Kopf zuordnen — aufwendig, aber ohne Modell.
4. `unklar` als eigene Metrik führen und die Rückfallquote nur auf belegten
   Labels berichten (konservativ, aber ehrlich).

**Frage an Claude:** Ist Option 1 (Prompt-Feld) den Bruch wert, oder reicht
Option 2/4 für eine belastbare Rückfallquote?

## 6. Problem 3: Armmischung (Intervention vs. Komparator)

**Beobachtung.** In 7 von 28 Records tragen die beiden Arme unterschiedliche
Zeitpunkte, z. B. `yun2024:75`: Intervention `'24'`, Komparator `'0'`, Ziel
`week 24`. `arme_gemischt()` in `evaluate_fallback.py` erkennt das; die Zählung
läuft als `arm_gemischt` mit.

**Ursache 1 (Prompt).** Der v6-Prompt erlaubt den Rückfall **je Feld**: „If a
field is not reported at the target time point, use the closest reported time
point instead". Damit darf der Komparator einen anderen Zeitpunkt tragen als die
Intervention. Armkonsistenz ist nirgends gefordert.

**Ursache 2 (Gold-Konflikt, `yun2024:75`).** Die Tabelle (palmvitee-Studie,
B-Lymphozyten in %):

| Gruppe | Woche 0 | Woche 12 | Woche 24 |
|---|---|---|---|
| Non-smokers (placebo, n = 27) | 10.19 ± 4.06 | 10.89 ± 3.56 | **11.00 ± 3.88** |
| Non-smokers (palmvitee, n = 29) | **11.97 ± 4.00** | 12.45 ± 4.67 | **13.72 ± 4.53** |

Gold trägt `intervention_mean = 11.97` (palmvitee, **Woche 0**) und
`comparator_mean = 13.72` (palmvitee, **Woche 24**, n = 29) — also
palmvitee-Baseline gegen palmvitee-Follow-up, mit der palmvitee-Gruppengröße im
Komparator. Placebo wäre n = 27, 11.00 bei Woche 24. Das Modell lieferte
`13.72 @ '24'` (Intervention) und `11.97 @ '0'` (Komparator): Zahlen richtig für
die palmvitee-Zeile, Armzuordnung gegenüber Gold vertauscht. Der Record ist
damit ein **Gold-Konflikt**, kein reiner Modellfehler.

**Optionen**
1. Prompt v7 mit „beide Arme einer Zeile am selben Zeitpunkt; ist ein Arm dort
   nicht berichtet, entfällt die Zelle" — braucht neue Run-ID.
2. Rückfall **je Record** statt je Feld: ein Zeitpunkt gilt für alle Zellen des
   Records; abweichende Arme werden als Auslassung gezählt.
3. Nur auswerten: `arm_gemischt` bleibt Fehlerklasse, Records werden aus der
   MAE ausgeschlossen und separat berichtet.
4. `yun2024:75` in die dokumentierten Gold-Konflikte aufnehmen (analog
   `yun2024:3` in `GEPRUEFTE_FAELLE`), damit die Auswertung ihn nicht als
   Modellfehler führt.

**Frage an Claude:** Reicht Option 3+4 für die aktuelle Auswertung, oder lohnt
sich v7 (Option 1) vor der zweiten Kohorte?

## 7. Kostenmodell (gemessen)

| Größe | Wert |
|---|---|
| Tokens je Zeile, Gesamtstand | ≈ 14.700 (692.395 / 47) |
| Median gültiger Antworten | ≈ 4.700 |
| Length-Fehlzeile | 16.000 (nach Umstellung), vorher 24.000 bzw. 56.000 mit Retry |
| Prompt-Größe | 2.827.369 Zeichen für 186 Records ≈ 707.000 Tokens; 5 Texte werden bei 45.000 Zeichen gekürzt |
| Projektion für 158 Restrecords | ≈ 0,95 Mio ohne Length-Fehler, ≈ 2,3 Mio mit 30 % Fehlerquote |

Ein Euro-Betrag ist bewusst nicht angegeben: Das Gateway-Preismodell steht nicht
im Repo; berichtet werden Tokens.

## 8. Was bereits versucht und verworfen wurde

* **Pauschale Abstandsgrenze 400 Zeichen** für die Annotation: traf 59 Records,
  58 davon mit ausschließlich Gruppengrößen, wo `baseline` richtig war. Jetzt
  gilt sie nur für Ergebniszellen (1 Record betroffen).
* **Retry mit größerem Tokenlimit** bei `length`: kostete 56.000 Tokens ohne
  Ergebnis, entfernt.
* **Promptänderung mitten im Lauf:** verworfen, weil die Run-ID dann Zeilen unter
  zwei Prompt-Fassungen enthält und `prompt_version` lügt.
* **Zwei Modelle parallel:** verworfen bis ein Modell vollständig durchgelaufen
  ist (doppelte Kosten ohne Vergleichsbasis).

## 9. Regeln, die eine Lösung einhalten muss

* Gold, `records/yun_kandidaten.jsonl` und `records/yun_test186.jsonl` nicht ändern.
* Bereits geschriebene `predictions.jsonl`-Zeilen nicht überschreiben; neue
  Erkenntnisse kommen in neue Dateien/neue Run-IDs.
* Eine Run-ID = eine Prompt-Fassung = ein Modell.
* Prompt-Version wird über `bestimme_version()` gesetzt und muss zur Wahrheit passen.
* Tests müssen grün bleiben (aktuell 213).
* Keine erfundenen Zahlen; Schätzungen als Schätzung markieren.
* Antworten und Dokumentation auf Deutsch, keine chinesischen Zeichen.

## 10. Reproduktion

```bash
cd D:/daswu/AIResearch
export PYTHONIOENCODING=utf-8

# Tests
.venv/bin/python -m pytest public_benchmark/tests -q

# Lauf fortsetzen (überspringt vorhandene Zeilen)
IDS=$(cat public_benchmark/extended_benchmark/analysis/run186_20261115/ids.txt)
.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --records public_benchmark/extended_benchmark/records/yun_test186.jsonl \
  --split test --models glm --workers 3 --ids "$IDS" --target-fallback \
  --max-tokens 16000 --run-id yun_test186_v6_20261115

# Auswertung (nach Abschluss)
.venv/bin/python public_benchmark/extended_benchmark/evaluate_fallback.py \
  --run yun_test186_v6_20261115 \
  --records public_benchmark/extended_benchmark/records/yun_test186.jsonl
```

## 11. Wo was dokumentiert ist

| Datei | Inhalt |
|---|---|
| `analysis/run186_20261115/plan.md` | Laufplan, Flags, Kosten, Abbruchkriterien |
| `analysis/run186_20261115/pilot.md` | 3-Record-Pilot (Etikett, Zeitpunktfeld) |
| `analysis/run186_20261115/abbruch.md` | erster Abbruch nach 18 Records |
| `analysis/run186_20261115/stabilisierung_und_fortsetzung.md` | Ursachen der drei Probleme, Änderungen, Tests |
| `analysis/candidate_split_20261115/zeitpunkt_stichprobe.md` | zwei Textstichproben (17 + 8 Labels) |
| `analysis/candidate_split_20261115/zeitpunkte.md` | Zeitpunkte aller 262 Records mit Beleg |
| `analysis/bericht_20261115_zeitpunkte_und_lauf.md` | Gesamtbericht der Annotation |

Code-Anker: `run_extended_extraction.py` (`fehlerklasse_aus`, `done_keys`,
`build_prompt`, `work`), `evaluate_fallback.py` (`normalisiere_label`,
`arme_gemischt`, `klassifiziere`), `annotate_timepoints.py`
(`zeitpunkt_aus_text`, `zeitpunkt_aus_outcome`, `MAX_ABSTAND`).

## 12. Drei Entscheidungen, die ich von Claude bräuchte

1. **Length:** Prompt-Feld vs. kleineres Limit vs. Textkürzung — welche
   Maßnahme senkt die 30 % Ausfälle, ohne das Versionsetikett zu brechen?
2. **Labels:** `timepoint_header` im Schema (neue Prompt-Fassung) oder
   artikelbasierte Einheiten-Extraktion offline?
3. **Arme:** v7-Prompt mit Armkonsistenz, oder reicht die Auswertungsklasse
   `arm_gemischt` plus Gold-Konflikt-Eintrag für `yun2024:75`?
