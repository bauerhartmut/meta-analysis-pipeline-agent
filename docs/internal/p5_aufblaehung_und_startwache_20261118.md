# Aufblähung der Feld/Arm-Zählung und die Startwache für P5

Stand: 18.11.2026, 15:47. Alles hier ist offline entstanden; es wurde kein
Netzlauf gestartet, abgebrochen oder verändert. P5 selbst läuft noch nicht.

Vorgeschichte: die Auflösbarkeitsprüfung (104 → 81 Ausfälle in `records/`, 23 nur
in `yun699.jsonl`, 423 Goldzellen auf 102 bewertbaren Records), die
P5-Vorbereitung mit den 103 ids und die Nullprobe der Auswertung stehen bereits in
`iterativ/ergebnisse/p5_vorbereitung_20261118.md` und
`iterativ/ergebnisse/p5_auswertung_nullprobe_20261118.md`. Diese Notiz setzt nach
der letzten Markdown an, `iterativ/ergebnisse/aufblaehung_20261118.md`, und
wiederholt deren Zahlen nur dort, wo sie für die Einordnung nötig sind.

## 1. Diff-Review: zwei echte Funde in `werte_p5_aus.py`

Der heutige Diff wurde mit frischem Blick gelesen. Zwei Stellen waren falsch, zwei
weitere Verdachtsfälle haben sich nicht bestätigt.

**Gefunden und behoben:**

1. `status()` hätte eine `fehlerklasse: "ok"` als Ausfall gelesen. Unter
   `--retry-strategie neu` trägt die Versuchsspur `ok` für eine angekommene
   Antwort; im Feld `fehlerklasse` der Zeile steht heute nur `""`,
   `length_ohne_ergebnis` oder `json_kaputt` (geprüft an allen 699 Zeilen der
   Lesekopie und am Live-Lauf). Wäre das je anders, hätte der P5-Bericht jede
   Rettung als „weiter ausgefallen" ausgewiesen. Jetzt ist `ok` ausdrücklich kein
   Ausfall, mit Test.
2. Der Bericht verglich nur `adressiert`, nicht `wertgleich`. Wichen
   ausschließlich die wertgleichen Treffer ab, hätte er „beide Zählungen stimmen
   überein" geschrieben. Jetzt werden beide Paare verglichen.

**Geprüft und verworfen:** doppelte `(Feld, Arm)`-Goldzellen gibt es in den 559
Erfolgszeilen nicht (0), und die vorhergesagten Zellen sind dublettenfrei (2.254
Zellen = 2.254 eindeutige Tripel aus Feld, Arm und Zeitpunkt). Die großzügige
Zählung bläht also nicht schon durch Doppelzählung auf.

## 2. Wie stark bläht die Feld/Arm-Zählung Treffer auf?

Gemessen an den 559 erfolgreichen `glm`-Zeilen mit Zellen aus der Lesekopie
(`yun_full/messe_aufblaehung.py`).

| Größe | Wert |
|---|---|
| Zeilen | 559 |
| Goldzellen | 2.306 |
| adressiert, großzügig (Feld und Arm) | 2.121 |
| adressiert, mit eindeutigem Zeitpunkt | 2.103 |
| **Aufblähung** | **18 (0,8 % der großzügig adressierten)** |
| wertgleich, großzügig → streng | 1.844 → 1.826 |
| betroffene Zeilen | 4 von 559 |

Verteilung je Zeile: 555 Zeilen ohne Abzug, drei Zeilen mit je 4, eine mit 6. Die
Extremfälle sind `yun2024:419` (6 adressiert, 0 streng) und `yun2024:121` (4 auf
0): dort adressiert die Vorhersage jeden Goldschlüssel, streut ihn aber über
mehrere Zeitpunkte, sodass die strenge Zählung alles fallen lässt.
`yun2024:418` und `yun2024:586` gehen von 6 auf 2.

**Die Zahl ist eine Untergrenze.** Geprüft wird nur Mehrdeutigkeit, nicht ob der
Zeitpunkt stimmt — das kann das Gold nicht beantworten, weil keine von 2.773
Goldzellen einen trägt. Eine Vorhersage mit falschem, aber eindeutigem Zeitpunkt
zählt hier als Treffer; 1.649 von 2.254 Zellen nennen überhaupt einen Zeitpunkt.
Auf den 103 Ausfällen kann die Aufblähung also größer ausfallen, kleiner nicht.

## 3. Die Lücke in der Startwache

**Der Fehler:** `yun_full/nachzug_ausfaelle.sh` schreibt `nachzug.lock` einmal beim
Start und wartet dann bis zu 720 Minuten auf den Hauptlauf. Die Startwache hielt
eine Sperre aber schon nach 90 Minuten für alt — das ist die
Doppelstart-Heuristik des Nachzugs selbst, nicht seine Lebensdauer. Nach 90
Minuten hätte die Wache „frei" gesehen und P5 gestartet, während der Nachzug
weiterlebte und sein Kind erst später startete.

**Der Fix:** entscheidend ist, ob der in der Sperre eingetragene **Prozess** lebt,
nicht wie alt die Datei ist. Die Lebendprüfung läuft über `ps -W` und vergleicht
msys- und Windows-PID, weil die Sperre die msys-PID enthält. `Get-CimInstance`
liefert für msys-Prozesse keine CommandLine, die PID ist deshalb der tragfähige
Anker. Eine Sperre ohne sichtbaren Prozess gilt noch 10 Minuten
(`SPERRE_MAX`) — für den Moment, in dem eine Steuerung gerade startet.

**Vier weitere Funde beim Durchsehen, alle behoben:**

1. Eine hart beendete Wache blockierte jeden Neustart für 730 Minuten, weil die
   Sperrdatei nur per `trap` bei normalem Ende verschwindet. Das ist live
   aufgetreten: der Stopp der alten Wache ließ `p5_gate_20261118.pid` mit toter
   PID liegen. Jetzt übernimmt die Wache eine verwaiste Sperre.
2. `MAXWARTE=abc` endete in „ABBRUCH nach 0 min", weil Bash Text als 0 rechnet —
   die Meldung sah nach abgelaufener Frist aus statt nach Tippfehler. Jetzt Exit 2
   mit klarer Meldung, für alle vier Zeitgrößen.
3. Es gab keinen Weg, den Zustand ohne Start zu sehen. Neu: `--pruefen`.
4. Ein erneuter Aufruf nach erfolgreichem Lauf hätte P5 ein zweites Mal gestartet
   (103 Anfragen à 24.000 Token). Jetzt beendet sich die Wache, wenn das
   Protokoll „P5 fertig" enthält.

## 4. Prüfungen

Offline, in einem temporären Verzeichnis mit überschriebenen `R`, `FREMD`, `GATE`
und `LOG`; der echte Lauf wurde dabei nicht angefasst.

| Fall | Ergebnis |
|---|---|
| Lebende PID, Sperre 3 h alt (der gemeldete Fall) | „Sperre PID 4811 lebt weiter" → belegt, Exit 1 |
| Tote PID, Sperre 3 h alt | „verwaist" → frei, Exit 0 |
| Tote PID, Sperre frisch | „juenger als 10 min" → belegt, Exit 1 |
| Keine Sperre | frei, Exit 0 |
| Verwaiste Wache-Sperre | wird übernommen, Wache läuft weiter |
| Lebende Wache-Sperre | „laeuft bereits", Exit 0 |
| Protokoll mit „P5 fertig" | kein zweiter Lauf, Exit 0 |
| `MAXWARTE=abc` | Exit 2 mit Meldung |

Dazu: `bash -n` sauber, 347 Tests in `public_benchmark/tests` grün (darunter drei
für die Aufblähungsmessung und einer für `status("ok")`).

**Nicht geprüft:** der Startpfad der Wache selbst (frei → Lauf → Auswertung). Er
lässt sich erst ausführen, wenn der Nachtlauf endet; ihn vorher zu testen hieße,
den Lauf zu stören oder 103 echte Anfragen zu verbrennen.

## 5. Stand der Läufe (15:47)

| Lauf | Stand |
|---|---|
| `yun699_8000_alle_20261117` (Nachtlauf, PID 3952) | 1.941 Zeilen, 0 Duplikate, 0 unlesbar |
| glm | 699 Zeilen, 104 Ausfälle (14,9 %), 36 leer (5,2 %) |
| qwen | 543 von 699, 62 Ausfälle, 56 leer |
| qwen30 | 699 Zeilen, 0 Ausfälle, 57 leer |
| Nachzug-Steuerung (PID 2153) | wartet auf den Hauptlauf, Sperre lebt |
| Startwache (PID 5032) | „belegt, P5 wuerde warten", Frist 720 min |

P5 ist **nicht** gestartet. Die Wache startet ihn, sobald drei Bedingungen
gleichzeitig gelten: kein Extraktionsprozess für den fremden Lauf, der Prozess aus
`nachzug.lock` lebt nicht mehr, und 180 Sekunden lang keine neue Zeile an
`predictions.jsonl`. Danach ruft sie `werte_p5_aus.py` auf, das die großzügige und
die strenge Zählung nebeneinander ausweist.

## 6. Offene Punkte

- Der qwen-Block hängt bei 543 von 699; wie lange der Nachtlauf noch braucht, ist
  offen. Die Wache läuft maximal 12 Stunden und startet nichts, wenn die Frist
  abläuft.
- Was ein Rettungserfolg in P5 bedeutet, ist weiterhin nur nach oben begrenzt: die
  Aufblähung von 0,8 % ist eine Untergrenze, und die Reparaturschätzung von 39 %
  bleibt eine Schätzung.
- Ein echter Zeitpunktvergleich gegen das Gold ist unmöglich, solange keine
  Goldzelle einen Zeitpunkt trägt. Das zu ändern wäre eine Änderung am
  Goldstandard und braucht Freigabe.

## 7. Empfehlung

Wache laufen lassen und den Nachzug nicht zusätzlich von Hand starten — die
Steuerung (2153) startet ihn selbst, sobald 3952 endet, und ein zweiter Nachzug
würde dieselben glm-ids doppelt anfragen. Der billigste Blick zwischendurch ist
`bash yun_full/starte_p5_wenn_frei.sh --pruefen`: eine Sekunde, keine Anfrage,
keine Wirkung auf laufende Prozesse.

## Anhang: Commits und Artefakte

| Commit | Inhalt |
|---|---|
| `9ad02ec` | Aufblähungsmessung, `status("ok")`, Berichtvergleich |
| `84eaf7d` | Erste Fassung der Startwache |
| `3c31d73` | Prozessbasierte Nachzug-Erkennung, vier weitere Funde |

Artefakte: `iterativ/ergebnisse/aufblaehung_20261118.json` und `.md`,
`iterativ/ergebnisse/p5_auswertung_nullprobe_20261118.json` und `.md`,
`runs/p5_start_20261118.log`, Skripte `yun_full/messe_aufblaehung.py`,
`yun_full/starte_p5_wenn_frei.sh`, Tests
`tests/test_messe_aufblaehung.py`.
