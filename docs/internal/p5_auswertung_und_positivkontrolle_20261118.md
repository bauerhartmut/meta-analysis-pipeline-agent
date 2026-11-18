# P5-Auswertung: Umbau, Positivkontrolle und Stand der Läufe

Stand: 18.11.2026, 16:14. Offline entstanden, kein Netzlauf gestartet oder
angehalten.

**Wichtig zur Einordnung:** Es gibt weiterhin **keine P5-Messwerte**. Der Lauf hat
nicht begonnen. Dieser Bericht enthält deshalb keine Rettungsquote, keine
Golddeckung aus P5 und keinen Vergleich alt/neu — nur den Zustand der Vorbereitung
und die Belege dafür, dass die Auswertung richtig summiert, sobald Zeilen da sind.
Die 39-%-Reparaturschätzung aus der Materialanalyse bleibt eine Schätzung.

Diese Notiz setzt nach `docs/internal/token_zaehler_20261118.md` an.

## 1. Die Auswertung liefert jetzt alle geforderten Felder

`yun_full/werte_p5_aus.py` (Commit `6822174`) wurde auf die Anforderungen des
P5-Auftrags umgebaut:

| Gefordertes Feld | Umsetzung |
|---|---|
| adressierte IDs | Abschnitt „Grundgesamtheit" |
| technisch erfolgreich / ausgefallen / leer / auswertbar | Status-Tabelle mit „Antwort technisch erhalten" und „auswertbar (mindestens eine Zelle)" |
| adressierte und wertgleiche Goldzellen | Tabelle „Zellen und Gold" |
| großzügige und strenge Zählung | beide Zeilen nebeneinander, fett abgesetzt |
| Unterschied beider Zählungen | eigener Absatz mit Zahl der abweichenden Treffer und der mehrdeutigen Gruppen |
| getrennt nach ursprünglicher Fehlerklasse | neue Tabelle mit IDs, technisch, auswertbar, leer, Ausfällen, Goldzellen, beiden Deckungen |

Zwei strukturelle Änderungen waren dafür nötig:

1. **Grundgesamtheit aus der Auswahl, nicht aus einem Klassenfilter.** Bisher
   filterte die Auswertung die Lesekopie auf `length_ohne_ergebnis`. Damit hätte
   die Aufteilung nach Fehlerklasse immer nur eine Zeile gehabt. Jetzt kommt die
   ID-Menge aus `p5_vorbereitung_20261118.json` (103 IDs), die Klasse wird je
   Record aus der Lesekopie nachgeschlagen.
2. **`ausfallzeilen` heißt `grundgesamtheit`.** Der alte Name war nach dem Umbau
   falsch: die Menge ist die adressierte Auswahl, nicht die Menge der Ausfälle.
   Umbenannt in Auswertung, Bericht, Tests und neu erzeugter Nullprobe.

Nullprobe (Lesekopie gegen sich selbst, erwartetes Ergebnis „nichts gerettet"):
103 adressierte IDs, 102 bewertbar, 1 nicht bewertbar, 0 technisch erhalten,
0 auswertbar, 0 adressiert, 0 wertgleich, 423 Goldzellen, eine Klassenzeile.

## 2. Positivkontrolle: belegt, dass die Summen stimmen

`yun_full/positivkontrolle_p5.py` (Commit `288b5eb`) rechnet eine erfundene, aber
feste Prediction-Datei durch. Die Sollwerte sind von Hand aus dem Fixture
gerechnet, nicht vom Skript erzeugt; das Skript vergleicht nur und endet bei
Abweichung mit Exit 1.

Acht Records, jeder Fall genau einmal:

| Record | Fall |
|---|---|
| `k1` | drei richtige Zellen, je Feld/Arm ein Zeitpunkt |
| `k2` | Schlüssel getroffen, Werte falsch |
| `k3` | derselbe Schlüssel über zwei Zeitpunkte (großzügig Treffer, streng keiner) |
| `k4` | leere Antwort |
| `k5` | weiterhin ausgefallen |
| `k6` | im neuen Lauf nicht enthalten |
| `k7` | andere Ursprungsklasse (`json_kaputt`), richtige Zelle |
| `k8` | keine Goldzellen |

Soll und Ist, vollständig deckungsgleich:

| Größe | Soll | Ist |
|---|---:|---:|
| Grundgesamtheit | 8 | 8 |
| gerettet / leer / ausgefallen / fehlt | 5 / 1 / 1 / 1 | 5 / 1 / 1 / 1 |
| technisch erhalten | 6 | 6 |
| auswertbar | 5 | 5 |
| inhaltlich gerettet | 3 | 3 |
| inhaltlich gerettet, streng | 2 | 2 |
| Zellen neu | 9 | 9 |
| davon mit Zeitpunkt | 9 | 9 |
| Goldzellen der bewertbaren | 11 | 11 |
| adressiert großzügig / streng | 7 / 6 | 7 / 6 |
| wertgleich großzügig / streng | 5 / 4 | 5 / 4 |
| mehrdeutige Feld/Arm-Gruppen | 1 | 1 |
| Klasse `length_ohne_ergebnis`: IDs / Gold / adressiert / wertgleich | 7 / 10 / 6 / 4 | 7 / 10 / 6 / 4 |
| Klasse `json_kaputt`: IDs / Gold / adressiert / wertgleich | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |

Die Differenz zwischen großzügiger und strenger Zählung ist in beiden Kennzahlen
exakt 1 und stammt nachweislich aus dem einen mehrdeutigen Zeitpunkt.

**Der Fund, den die Kontrolle erzwungen hat:** `zellen_neu_mit_zeitpunkt`
summierte nur über die bewertbaren Records, während `zellen_neu` direkt daneben
alle zählte. Die Kontrolle zeigte 8 statt 9, weil der Record ohne Goldzellen eine
Zeitpunkt-tragende Zelle beisteuerte. Genau die Sorte inkonsistenter
Grundgesamtheit, bei der später keine einzelne Zahl falsch aussieht, der Bericht
aber trotzdem nicht stimmt. Behoben: beide Zeilen zählen über alle Records.

## 3. Stand der Läufe (16:14)

Zustandsprüfung ausschließlich über die Wache:

```
Lauf: yun699_8000_alle_20261117
Prozess: Prozesse: 1 (PID 3952)  ok
Nachzug: Sperre PID 2153 lebt weiter
Letzte Zeile: vor 1 s (Ruhe gilt ab 180 s)
=> belegt, P5 wuerde warten
```

- **Nachtlauf:** läuft weiter (PID 3952), schreibt Zeilen, kein Abbruch beobachtet.
- **Nachzug:** Steuerung lebt (PID 2153); die Lebendprüfung geht über `ps -W`, nicht
  über das Alter der Sperre, deshalb ist „lebt weiter" belastbar.
- **P5:** nicht gestartet, wartet auf drei Bedingungen gemeinsam — kein
  Extraktionsprozess, keine lebende Nachzug-Sperre, 180 Sekunden ohne neue Zeile.

Die Wache hat 720 Minuten Frist ab 15:45. Läuft sie ab, startet sie nichts und
schreibt „ABBRUCH" nach `runs/p5_start_20261118.log`.

## 4. Geprüft und nicht geprüft

**Geprüft:** 356 Tests in `public_benchmark/tests` grün, davon fünf neue für die
Positivkontrolle und vier für die Klassentabelle und die drei Stufen; Kontrolle
Exit 0; Nullprobe neu erzeugt; kein Netzlauf; Goldstandard unverändert; keine
bestehenden Ergebnisse überschrieben.

**Nicht geprüft:** der Bericht mit echten P5-Zeilen. Die Kontrolle belegt die
Rechenwege, nicht das Ergebnis. Ebenso ungeprüft bleibt der Startpfad der Wache
(frei → Lauf → Auswertung); ihn zu testen hieße, 103 echte Anfragen zu verbrennen.

## 5. Offene Punkte

- P5 ist nicht gestartet; ohne Lauf gibt es keine Rettungsquote.
- Der Nachtlauf hängt bei qwen; wie lange er noch braucht, ist offen.
- Die Zeitpunktprüfung erkennt weiterhin nur Mehrdeutigkeit. Ob ein genannter
  Zeitpunkt richtig ist, lässt sich am Gold nicht prüfen, weil keine Goldzelle
  einen trägt.
- Der Tokenzähler erfasst den laufenden Nachtlauf nicht (Prozess hat den Harness
  vor dem Einbau geladen).

## 6. Empfehlung

Warten, nichts am Harness ändern. Der einzige Schritt mit Nutzen ohne Risiko ist
die Positivkontrolle in die Wache einzuhängen: einmal vor `werte_p5_aus.py`
laufen lassen und bei Exit 1 den Bericht nicht schreiben. Kosten unter einer
Sekunde, kein Netz, und beim ersten echten P5-Bericht wäre belegt, dass die
Rechenwege intakt sind, bevor eine Zahl daraus zitiert wird. Das ist eine
Änderung an der Wache und braucht Freigabe.

## Anhang: Commits dieser Etappe

| Commit | Inhalt |
|---|---|
| `6822174` | Auswertung auf die 103er-Auswahl, Klassentabelle, drei Stufen, Umbenennung |
| `288b5eb` | Positivkontrolle samt Fixture, Tests und Bericht |

Artefakte: `iterativ/ergebnisse/p5_positivkontrolle_20261118.{json,md}`,
`iterativ/kontrolle/p5_positivkontrolle/{alt,neu}.jsonl`,
`iterativ/ergebnisse/p5_auswertung_nullprobe_20261118.{json,md}`.
Die Commits `92f5aad` und `f44c520` stammen aus Parallelarbeit und gehören nicht
zu dieser Etappe.
