# Table Decomposition: Ergebnisteil und Einordnung (18.11.2026)

Alle Zahlen stammen aus den unten genannten Artefakten; keine ist geschätzt,
außer der Tokenzahl, die als Zeichen/4 markiert ist. Der maschinell erzeugte
Tabellenteil liegt in `strukturbericht_20261118.md`, die Rohdaten in
`offline_struktur_20261118/structure.json` und
`offline_struktur_reihenfolge_20261118/structure.json`.

## Was gemessen wurde — und was nicht

**Gemessen:** Struktur (Abdeckung, Kontexterhalt, Validierungsbefunde) und
Aufwand (Einheiten, Prompt-Zeichen, geschätzte Tokens) für die Verfahren A–E auf
einem eingefrorenen Testdatensatz, ohne Modellaufruf.

**Nicht gemessen:** Precision, Recall, F1, Exact Match, Arm-/Outcome-/
Zeitpunktzuordnung, technische Ausfallquote, Laufzeit und Kosten pro 100
richtige Zellen. Diese Kennzahlen brauchen einen Modelllauf; er ist ohne
ausdrückliche Freigabe und Gateway-Guthaben nicht gestartet worden. Der Bericht
sagt das an jeder Stelle, statt Zahlen zu ersetzen.

## Datensatz

| Feld | Wert |
|---|---|
| Split | `test` |
| Tabellen | 60 |
| Records | 58 |
| Dokumente | 31 |
| Kandidaten (Record, Tabelle) | 537 |
| Goldzellen der 58 Records | 268 |
| Goldzellen über eine ausgewählte Tabelle erreichbar | 76 (28,4 %) |
| `records_sha256` | `c22ed3fb42dbaaff7051a89cdb327c4b250a134db0a62a19d3877d5ba311c0b1` |

Schichtverteilung: mehrzeitpunkt 37, mehrstufiger_kopf 35, fussnoten 34,
mittel 20, sehr_komplex 19, einfach 17, komplexe_pdf 8, mehrarm 8, komplex 7.

Der Devsplit hat nach derselben Prozedur nur 26 Kandidaten mit belegten
Zielspalten; mit `--target 40` wurden 6 ausgewählt. Für Schwellenoptimierung ist
der Devsplit damit zu klein — das ist ein Befund, kein Versehen.

## Struktur- und Aufwandsvergleich (Test, 58 Records, 60 Tabellen)

Standardkonfiguration (`arm_order_fallback` aus):

| Var | Verfahren | Einheiten/Record | Zeichen/Record | Tokens ges. (Sch.) | Faktor zu A | Gold erreichbar | strukturell komplett | Fehler | Warnungen |
|---|---|---|---|---|---|---|---|---|---|
| A | Full-Table | 1,03 | 5.598,0 | 81.171 | 1,00 | 76 | 60/60 | 0 | 21 |
| B | Vertical | 2,40 | 9.056,9 | 131.325 | 1,62 | 76 | 60/60 | 0 | 45 |
| C | Horizontal | 6,60 | 22.127,6 | 320.851 | 3,95 | 76 | 60/60 | 0 | 67 |
| D | Bidirectional | 7,84 | 27.041,7 | 392.104 | 4,83 | 76 | 60/60 | 0 | 67 |
| E | Adaptive | 4,28 | 17.462,2 | 253.202 | 3,12 | 76 | 60/60 | 0 | 59 |

Mit Reihenfolge-Annahme (`--arm-order-fallback`, dieselbe Auswahl):

| Var | Einheiten/Record | Zeichen/Record | Tokens ges. (Sch.) | Gold erreichbar | `armzuordnung_angenommen` |
|---|---|---|---|---|---|
| A | 1,03 | 5.600,3 | 81.204 | 84 | 8 |
| B | 2,57 | 9.647,2 | 139.885 | 84 | 8 |
| C | 6,60 | 22.142,9 | 321.072 | 84 | 8 |
| D | 8,02 | 27.643,9 | 400.837 | 84 | 8 |
| E | 4,38 | 17.867,9 | 259.085 | 84 | 8 |

Lesart:

- **Kontexterhalt ist belegt.** In beiden Läufen sind alle 60 Tabellen für alle
  fünf Verfahren strukturell vollständig (`60/60`), ohne einen einzigen Fehler:
  jede Datenzelle ist genau einer Einheit zugeordnet, jeder Spaltenpfad und
  jedes Zeilenlabel wird mitgeführt, Fußnoten sind im Ausschnitt. Nach dem
  Labelspalten-Fix ist der frühere Befund `zeilenlabel_fehlt` (vorher 395
  Warnungen bei A) vollständig verschwunden; übrig bleiben 21 Warnungen zu
  Spalten ohne Header (leere Eckzelle, Gruppenkopf-Zwischenzeilen).
- **Aufwand wächst mit der Zerlegung**, nicht linear zur Zellenzahl: C liest
  jede Zeile mit allen Köpfen und braucht deshalb fast das Vierfache an
  Prompt-Text, D durch die doppelte Leserichtung fast das Fünffache. B ist mit
  1,62× der günstigste Zerlegungspfad, weil jede Spalte ihren Kopf nur einmal
  mitführt.
- **E liegt zwischen B und C** (3,12×) und bleibt unter dem D-Aufwand, weil die
  Nachlese nur unbelegte oder konfliktäre Adressen anfasst.

## Zentraler Befund: der Engpass ist die Armzuordnung, nicht die Zerlegung

Von 268 Goldzellen der 58 Records sind über die ausgewählten Tabellen nur 76
erreichbar (28,4 %), mit Reihenfolge-Annahme 84 (31,3 %). Zwei Ursachen, beide
deterministisch nachweisbar:

1. **Ein Record verteilt seine Goldzellen über mehrere Tabellen.** Im Schnitt
   trägt eine ausgewählte Tabelle 1,3 der 4,6 Goldzellen eines Records;
   Gruppengrößen, Mittelwerte und Ereigniszahlen stehen häufig in
   verschiedenen Tabellen desselben Dokuments.
2. **Nur ein Teil der Tabellen benennt den Studienarm im Kopf.** Wo der Kopf
   „Placebo“/„Verum“ nicht nennt, bleibt die Spalte ohne Feld — bewusst, statt
   einen Arm zu raten. Die Reihenfolge-Annahme holt genau 8 Zellen (3 % der
   Goldmenge) zurück und markiert dafür 8 Spalten als prüfpflichtig.

Damit ist die Obergrenze des Tabellenpfads für Recall bekannt: selbst ein
fehlerfreies Modell kann auf diesem Testdatensatz höchstens 28–31 % der
Goldzellen liefern, wenn die Armzuordnung so bleibt. Die Zerlegung kann diesen
Deckel nicht heben; sie kann nur dafür sorgen, dass die erreichbaren Zellen
korrekt und vollständig kontextualisiert sind. Das ist die wichtigste Aussage
dieses Berichts für die Produktionsentscheidung.

## Fehleranalyse der Strukturbefunde

| Code | A | B | C | D | E | Bedeutung |
|---|---|---|---|---|---|---|
| `spaltenkopf_fehlt` | 21 | 0 | 67 | 67 | 59 | Spalte ohne Header-Pfad (leere Eckzelle, Zwischenkopf) |
| `zelle_ausserhalb_scope` | 0 | 45 | 0 | 0 | 5 | Zelle liegt außerhalb des gelesenen Ausschnitts |
| `zeilenlabel_fehlt` | 0 | 0 | 0 | 0 | 0 | nach dem Labelspalten-Fix behoben |

- Die 45 `zelle_ausserhalb_scope` bei B sind erwartbar: eine Spalteneinheit liest
  nur ihre Spalte, Zellen anderer Spalten bleiben außerhalb. Sie werden nicht
  als Fehler gezählt, weil jede Zelle von genau einer Spalteneinheit gelesen
  wird — die Abdeckung ist trotzdem vollständig.
- `spaltenkopf_fehlt` bei A/C/D betrifft Spalten, deren Kopfzelle im Markdown
  leer ist. Der Prompt führt sie als `col n: (ohne Kopf)` mit; das Modell sieht
  die Spalte also, kann sie aber nur über die Nachbarpfade einordnen. Das ist
  eine Quelle für Fehlzuordnungen und im Modelllauf gezielt zu prüfen.

## Token- und Kostenvergleich

Tokens sind aus Prompt-Zeichen / 4 geschätzt (markiert). Gemessene Tokens,
Laufzeit und Kosten entstehen erst im Modelllauf; `evaluate.py` rechnet dann aus
`prompt_tokens`/`completion_tokens` und den Preisen `--preis-in`/`--preis-out`
Kosten und Kosten pro 100 richtige Zellen. Eine Euro-Zahl ohne Modelllauf wäre
erfunden und steht deshalb hier nicht.

Relativ ist die Aussage belastbar: B kostet das 1,62-Fache von A an Eingabe, E
das 3,12-Fache, C das 3,95-Fache, D das 4,83-Fache. Bei einem Preis je Token
skaliert das linear; ob der Recall-Gewinn das rechtfertigt, entscheidet der
Modelllauf.

## Empfehlung für die produktive Integration

1. **A bleibt Baseline, B wird der Standard für den Tabellenpfad.** B hat den
   geringsten Aufwandsaufschlag (1,62×) bei vollständigem Kontexterhalt und
   liefert dieselbe Abdeckung wie die anderen Verfahren. C und D erst einsetzen,
   wenn der Modelllauf einen messbaren Recall-Vorteil zeigt, der 4–5×
   Eingabetokens rechtfertigt.
2. **E nur mit Nachlese-Budget** und nur auf `dev` eingestellt; die Nachlese
   greift ausschließlich bei unbelegten oder konfliktären Zellen, nicht
   flächendeckend.
3. **Vor dem Modelllauf die Armzuordnung verbessern** — dort liegt der Hebel.
   Konkrete, noch nicht gebaute Kandidaten: (a) Armnamen aus Tabellenfußnoten
   und Legende lesen, (b) Gruppengrößen aus `n`-Spalten gegen den Record
   abgleichen und darüber den Arm binden, (c) mehrere Tabellen eines Records
   gemeinsam auswerten statt je Tabelle. (c) ist ohne Modellkosten messbar und
   würde die erreichbare Goldmenge direkt erhöhen.
4. **Reihenfolge-Annahme standardmäßig aus lassen**, im Benchmark aber
   mitführen: sie ist billig, holt wenig und erzeugt prüfpflichtige Spalten.
5. **Erst danach der Modelllauf** (A/B/E auf `test`, C/D nur bei Bedarf), mit
   vorheriger Telemetrie des letzten Laufs und ausdrücklicher Freigabe.

## Artefakte

| Datei | Inhalt |
|---|---|
| `selection_test.json` | eingefrorene Auswahl (60 Tabellen, 537 Kandidaten, Hash) |
| `selection_dev.json` | Devauswahl (6 Tabellen aus 26 Kandidaten) |
| `offline_struktur_20261118/structure.json` | Struktur/Aufwand A–E, Standardkonfiguration |
| `offline_struktur_reihenfolge_20261118/structure.json` | dasselbe mit Reihenfolge-Annahme |
| `strukturbericht_20261118.md` | maschinell erzeugter Bericht aus `structure.json` |
| `einordnung_20261118.md` | dieser Text |

## Grenzen

- Der Strukturvergleich sagt nichts über Extraktionsqualität. Precision/Recall
  bleiben offen, bis ein Modelllauf freigegeben ist.
- `gold_reachable` ist eine Obergrenze des Tabellenpfads, keine Modellleistung.
- Der Devsplit ist mit 26 Kandidaten zu klein für Schwellenoptimierung; für
  belastbare Einstellungen muss die Devauswahl über mehr Dokumente streuen
  (z. B. `--max-per-document 1 --target 40`).
- Outcome- und Zeitpunktzuordnung sind im Gold nicht zellweise annotiert und
  bleiben im Benchmark nicht messbar; `evaluate.py` weist das aus.
