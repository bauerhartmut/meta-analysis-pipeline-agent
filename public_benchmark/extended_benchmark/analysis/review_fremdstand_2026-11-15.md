# Review des Fremdstands seit `20a3dad`

Stand: 15.11.2026

Geprüfter Bereich: `20a3dad..acf3d6e`

Art: statischer Review und read-only Auswertung vorhandener Artefakte; kein neuer API-Lauf, keine Gold-Änderung, kein Merge.

## 1. Umfang

Seit dem letzten hier bekannten Commit wurden **75 Commits** mit **214 geänderten Dateien** und **42.982 Zeilen** hinzugefügt. Der Schwerpunkt liegt auf:

- Aufnahme und Adaption öffentlicher Goldstandards: GLASS, European Urology, PICO Corpus, Evidence Inference 2.0, EBM-NLP 2.00.
- Erweitertem Yun-Benchmark mit 450 Records, 262 Kandidaten-Records und einem eingefrorenen 186er-Testset.
- Extraktions-, Auswerte- und Diagnoseskripten inklusive 221 Tests.
- 186er-v6-Lauf, Zeitpunktannotation, Rückfallregel, Armklassifikation und Gold-Konflikt-Prüfung.
- v7-Pilot für Length-Ausfälle und einem Folgelauf über die 47 Fehlzeilen.

Die Tests laufen aktuell durch:

```text
pytest public_benchmark/tests -q
221 passed
```

## 2. Belegte Ergebnisse

### 2.1 v6-Hauptlauf

| Kennzahl | Wert |
|---|---:|
| Records | 186 |
| Completion-Tokens | 1.713.139 |
| Length-Ausfälle | 47 |
| Zell-F1 | 0,6548 |
| Recall | 0,6184 |
| Precision | 0,6958 |
| MAE | 0,3796 |
| MAE-Coverage | 0,6731 |
| exakte Records | 73 von 186 |

Quelle: `analysis/run186_20261115/auswertung186.md` und `fallback_eval.json`.

### 2.2 v7-Pilot

| Kennzahl | Wert |
|---|---:|
| Records | 6 |
| formale Erfolge (`finish_reason = stop`, kein Fehler) | 5 |
| davon mit mindestens einer Zelle | **4** |
| Zellen insgesamt | 13 |
| Goldzellen der 6 Records | 21 |
| Median-Tokens der Erfolge | 8.951 |
| Kriterium | mindestens 5 Erfolge, Median ≤ 6.000 |
| bestanden | **nein** |

Quelle: `analysis/run186_20261115/pilot_v7.md`, `pilot_urteil.json` und `runs/pilot_len_b_20261116/predictions.jsonl`.

### 2.3 v7-Folgelauf

Der Folgelauf `yun_test186_v7_folgelauf_20261116` ist inzwischen vollständig geschrieben:

| Kennzahl | Wert |
|---|---:|
| Zeilen | 47 |
| `finish_reason = stop` | 29 |
| Length-Ausfälle | 18 |
| leere `stop`-Antworten | 6 |
| Zellen | 79 |
| Completion-Tokens | 610.540 |

Die Auswertung `fallback_eval_v7.json` bezieht sich nur auf diese 47 Records. Die kombinierte Datei `fallback_eval_kombiniert.json` umfasst wieder 186 Records und weist im Feld `gesamt.cell_f1` **0,6934** bei **137** Auslassungen aus; der v6-Stand lag bei **0,6548** und **197** Auslassungen. Der abweichende Wert `zell_f1_aus_klassen = 0,6784` ist eine klassenbasierte Nebenrechnung und darf nicht mit dem Hauptwert verwechselt werden.

**Wichtig:** Das ist kein kontrollierter Modellvergleich. Der kombinierte Lauf besteht aus **157 v6-Zeilen** und **29 v7-Zeilen**; 18 v7-Fehler verbleiben im v6-Stand. Die Verbesserung ist daher ein Ergebnis der selektiven Ergänzung, nicht ohne Weiteres eine Verbesserung des Gesamtmodells.

## 3. Befunde

### Befund 1: „5 von 6 liefern Zellen“ ist nicht korrekt

- `pilot_v7.md` und der Commit-Titel sprechen davon, dass fünf von sechs Fehlrecords jetzt Zellen liefern.
- Die Tabelle zeigt für `yun2024:325` jedoch **0 Zellen**; `pilot_urteil.json` führt dort `zellen: 0` und `parse_error: keine_verwertbaren_zellen`.
- `pilot_len.urteil()` zählt eine Antwort als Erfolg, wenn `finish_reason == "stop"` ist, keine `fehlerklasse` gesetzt ist und der Parse-Fehler nicht `kein_json`, `kein_objet` oder `json_fehler...` ist. `keine_verwertbaren_zellen` wird damit als Erfolg gewertet.
- Für **valides JSON** ist die 5/6-Zahl korrekt. Für **verwertbare Zellen** sind es **4/6**.

**Wirkung:** Die eigentliche Pilotentscheidung bleibt `bestanden = false`, weil der Median 8.951 über 6.000 liegt. Die Erfolgsquote und der Commit-Titel sind aber irreführend und sollten vor der nächsten Entscheidung korrigiert werden.

**Empfehlung:** Entweder die Kennzahl ausdrücklich als „valides JSON“ bezeichnen oder `zellen > 0` als Erfolgsbedingung ergänzen. Bei der zweiten Variante muss `pilot_urteil.json` neu erzeugt werden; ein neuer API-Lauf ist dafür nicht nötig.

### Befund 2: `README.md` beschreibt einen überholten Stand

`public_benchmark/extended_benchmark/README.md` nennt weiterhin:

- „Status: Dateninfrastruktur aufgebaut; kein Modelllauf; kein Finetuning.“
- „Bewertungsskripte ... noch nicht gebaut.“

Inzwischen existieren Modellläufe, Auswerter, Fehleranalysen und 221 Tests. Der README-Stand ist damit irreführend, insbesondere für jemanden, der den Benchmark übernehmen will.

**Empfehlung:** Statuskopf und Abschnitt „Offene Punkte“ auf den tatsächlichen Stand aktualisieren; fertige Auswerter nicht mehr als offen führen.

### Befund 3: `mische_quelle.py` hat keinen Überschreibschutz

`analysis/run186_20261115/mische_quelle.py` schreibt direkt nach:

```text
runs/<out-run>/predictions.jsonl
```

Es prüft nicht, ob `--out-run` gleich `--haupt` oder `--folge` ist. Ein versehentlicher Aufruf kann damit den Haupt- oder Folgelauf überschreiben. Zusätzlich werden Folgelauf-Zeilen, deren `record_id` im Hauptlauf fehlt, stillschweigend ignoriert; die Zusammenfassung nennt keine nicht zugeordneten IDs.

**Empfehlung:**

- `Path.resolve()` für Haupt-, Folge- und Zielpfad vergleichen und bei Gleichheit abbrechen.
- Nicht zugeordnete Folgelauf-IDs zählen und in `zusammenfuehrung.json` ausweisen.
- Für den Merge einen kleinen Test mit einer unbekannten ID und einem verbotenen Zielpfad ergänzen.

### Befund 4: `ausfaelle` in `je_quelle` ist unscharf

`evaluate_fallback.py` zählt in `je_quelle["ausfaelle"]` nur Zeilen mit gesetzter `fehlerklasse`. Leere `stop`-Antworten mit `keine_verwertbaren_zellen` haben keine `fehlerklasse` und erscheinen daher nicht als Ausfall.

Im v7-Folgelauf stehen 47 Records, 18 Length-Ausfälle und 6 leere Antworten; `je_quelle` meldet 18 Ausfälle. Wenn „Ausfall“ auch „keine Zellen“ umfassen soll, ist die Zahl zu niedrig; wenn nur technische Fehler gemeint sind, sollte die Bezeichnung das sagen.

**Empfehlung:** Entweder `keine_verwertbaren_zellen` in eine eigene Zählung aufnehmen oder `ausfaelle` in `technische_ausfaelle` umbenennen und `leere_antworten` separat ausweisen.

### Befund 5: Neue Entscheidungslogik ist nicht getestet

Die 221 Tests decken die neuen Skripte nicht vollständig ab. Es gibt insbesondere keine Tests für:

- `pilot_len.urteil()` und die Erfolgsdefinition,
- `mische_quelle.py` und den Merge-Schutz,
- `evaluate_fallback.py --nur-ids` und `je_quelle`.

**Empfehlung:** Mindestens drei kleine Tests ergänzen:

1. `pilot_len.urteil()` zählt eine `stop`-Antwort mit 0 Zellen nicht als Zellerfolg.
2. `mische_quelle.py` verweigert `--out-run` gleich `--haupt` oder `--folge`.
3. `je_quelle` zählt eine leere `stop`-Antwort entweder als leer oder als Ausfall, je nach festgelegter Semantik.

### Befund 6: Zwei verschiedene F1-Werte in derselben Auswertung

`fallback_eval_kombiniert.json` enthält zwei F1-Werte:

- `gesamt.cell_f1 = 0,6934`
- `zell_f1_aus_klassen = 0,6784`

Der neue Bericht `folgelauf_v7_und_goldkonflikte.md` nennt 0,6934. Beide Werte können aus unterschiedlichen Zählwegen korrekt sein, dürfen aber nicht austauschbar zitiert werden. Wer den kleineren Wert als „den“ kombinierten F1 übernimmt, berichtet eine andere Kennzahl als der Bericht.

**Empfehlung:** Im Bericht ausdrücklich `gesamt.cell_f1` als Hauptwert nennen und `zell_f1_aus_klassen` nur mit Erklärung der Nebenrechnung zeigen. Der Folgelauf und die beiden Auswertungen sind inzwischen in `acf3d6e` versioniert; die frühere Untracked-Lücke ist damit geschlossen.

## 4. Was nicht geprüft wurde

- Kein neuer Modell- oder Netzaufruf.
- Keine erneute inhaltliche Prüfung der Goldzellen an den Originalartikeln.
- Keine Änderung an Gold, Split oder bestehenden Predictions.
- Keine Bewertung der fachlichen Richtigkeit der neuen Gold-Konflikt-Einträge über die vorhandenen Textbelege hinaus.

## 5. Empfohlene Reihenfolge

1. **Erfolgsdefinition korrigieren:** `pilot_len.urteil()` entweder auf `zellen > 0` umstellen und `pilot_urteil.json` neu erzeugen oder den Bericht ausdrücklich auf „valides JSON“ umformulieren. Kein API-Aufruf nötig.
2. **Merge-Schutz und Tests ergänzen:** Überschreibschutz in `mische_quelle.py`, Tests für Piloturteil, Merge und `je_quelle`.
3. **v7-Folgelauf konsolidieren:** Der Lauf ist in `acf3d6e` versioniert; im Bericht nur `gesamt.cell_f1` als Hauptwert zitieren und den Unterschied zu `zell_f1_aus_klassen` erklären. Kombinierte F1 nur mit Quellenanteil und verbleibenden 18 v7-Fehlern berichten.
4. **README aktualisieren:** Status, vorhandene Skripte, Läufe und offene Punkte auf den Stand vom 15.11.2026 bringen.
5. **Erst danach** über den nächsten API-Lauf entscheiden. Der teuerste Fehler wäre, die 5/6-Zahl als Beleg für eine gelöste Length-Quote zu verwenden, obwohl nur 4/6 Zellen liefern und der Folgelauf weiterhin 18 von 47 Length-Ausfälle hat.

## 6. Kurzfazit

Die Arbeiten sind technisch umfangreich und die Tests laufen grün. Der größte inhaltliche Fortschritt ist die saubere Trennung von Hauptlauf, Folgelauf, Quelle und Gold-Konflikt. Der größte Risikopunkt ist die Kommunikation der Pilotquote: **valides JSON ist nicht dasselbe wie verwertbare Extraktion**. Diese Unterscheidung muss vor der nächsten Entscheidung explizit gemacht werden.
