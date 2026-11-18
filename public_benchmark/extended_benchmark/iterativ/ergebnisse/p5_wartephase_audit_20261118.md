# P5-Wartephase: Audit von Wachenübergang, Eingaben und Auswertung

Stand: 18.11.2026, 17:00. Teil 1 (bis 16:30) entstand ausschließlich lesend:
kein Modelllauf, keine Netzwerkanfrage, kein Prozesseingriff, keine Änderung an
Locks, Predictions, Goldstandard oder eingefrorenen Eingaben; er blieb im Sprint
47 bewusst uncommittet. Teil 2 (Abschnitt 0 und die Markierungen) ist der
danach freigegebene Wachenneustart. Abschnitte 1 bis 8 beschreiben weiterhin den
Zustand um 16:30 und sind als solcher gekennzeichnet.

## 0. Nachtrag 17:00: Wache neu gestartet (Befunde 1 bis 3 erledigt)

Freigegeben und ausgeführt: nur die Wache beenden, Nachtlauf, Nachzug und
Sperrdateien unangetastet lassen, danach neu starten und mit `--pruefen`
bestätigen.

| Schritt | Beleg |
|---|---|
| Identität vor dem Signal | `ps -ef` zeigte genau einen Prozess mit `bash …/starte_p5_wenn_frei.sh`, msys-PID 5032; die Gate-Datei enthielt `5032` |
| Beendet | SIGTERM an 5032, nach rund 5 s war der Prozess samt `sleep`-Kind verschwunden |
| Gate-Sperre | von der Wache selbst über ihr `trap` entfernt; keine Sperrdatei von Hand gelöscht oder verändert |
| Neu gestartet | 16:55:19, PID **6630**, Gate-Datei enthält `6630` |
| Geladene Fassung | Commit `f05928a`; der Wrapper-Aufruf `werte_p5_mit_kontrolle.sh` ist im laufenden Skript vorhanden |
| Schleife läuft | Logzeilen 16:55:20 und 16:56:21 („noch belegt … naechste Pruefung in 60s") |
| `--pruefen` | „Prozess: 1 (PID 3952) ok · Nachzug: Sperre PID 2153 lebt weiter · Letzte Zeile vor 77 s → **belegt, P5 wuerde warten**"; Exit 1 ist der dokumentierte Code für „würde warten" |
| Nichts gestartet | `runs/yun699_p5_24000_20261118/` existiert noch nicht |
| Unberührt | Nachtlauf 532/3952 (2.013 Zeilen), Nachzug 2152/2153, beide Sperrdateien |

Neue Frist: 720 Minuten ab 16:55, also **04:55** (vorher 03:45).

Damit ist der alte Pfad „Auswertung ohne Nonce, danach falsches *P5 fertig*"
nicht mehr aktiv: Erreicht die Wache die Auswertung, geht sie über Kontrolle und
Nonce, und ohne Erfolgsmarke entsteht kein Bericht, sondern Exit 3 oder 4 mit
klarer Logzeile.

**Nicht geprüft:** der Ernstfall. Dass die Wache tatsächlich startet und die
Kontrolle durchläuft, lässt sich erst zeigen, wenn Nachtlauf und Nachzug fertig
sind; ein Test wäre ein echter P5-Lauf und war nicht freigegeben. Belegt ist die
richtige Fassung, die laufende Schleife und die korrekte Bewertung „belegt".

Die Wache hängt an der laufenden Desktop-Sitzung. Wird die Anwendung oder der
Rechner geschlossen, endet sie und muss neu gestartet werden.

## 1. Zusammenfassung

Die 103 Eingaben sind konsistent, die Auswertung ist durch eine zweite
Implementierung auf drei Datensätzen bestätigt, und Precision, Recall und F1 sind
aus den vorhandenen Daten berechenbar — mit klaren Grenzen. Der einzige ernste
Befund betrifft den **Wachenübergang**: Die laufende Wache (PID 5032) ist um
15:45:09 gestartet, die Skriptfassung wurde um 16:21:43 geändert. Ob sie nach
ihrer Warteschleife die alte oder die neue Textstelle liest, ist von außen nicht
feststellbar. Beide Ausgänge sind fail-closed — es entsteht in keinem Fall ein
ungeprüfter Bericht —, sie unterscheiden sich aber darin, ob am Ende ein Bericht
existiert oder nur eine Abbruchzeile.

Seit dem Neustart um 16:55 (Abschnitt 0) gilt nur noch der rechte Zweig: Die
laufende Instanz ist PID 6630 mit der Fassung `f05928a`.

## 2. Wachenübergang und Versionsproblem

### Belegte Fakten der alten Instanz (bis 16:55)

| Größe | Wert |
|---|---|
| Nachtlauf | msys-PID 532, Windows-PID 3952, gestartet 10:50:21 |
| Nachzug-Steuerung | PID 2153, gestartet 12:22:57 |
| Startwache | PID 5032, gestartet 15:45:09 |
| Wachenskript zuletzt geändert | 18.11. 16:21:43 |
| Fassung zum Startzeitpunkt | Commit `3c31d73` |
| Fassung jetzt | Commit `f05928a` (Sprint 46) |
| Skriptgröße / Offset nach der Warteschleife / Offset des neuen Blocks | 7.393 B / 2.361 / 7.087 |

Alle Änderungen aus Sprint 46 liegen **hinter** der Warteschleife. Der Text
zwischen Schleifenende und dem geänderten Abschnitt ist byte-gleich geblieben.

### Was die beiden Fassungen nach erfüllten Bedingungen tun

Alte Fassung (`3c31d73`), wörtlich:

```
.venv/bin/python public_benchmark/extended_benchmark/yun_full/werte_p5_aus.py >> "$LOG" 2>&1
wcode=$?
log "Auswertung beendet mit Exitcode $wcode (Artefakte: iterativ/ergebnisse/p5_auswertung_20261118.{json,md})"
log "P5 fertig"
exit "$wcode"
```

Neue Fassung (`f05928a`):

```
bash public_benchmark/extended_benchmark/yun_full/werte_p5_mit_kontrolle.sh >> "$LOG" 2>&1
wcode=$?
if [ "$wcode" -eq 0 ]; then
  log "Auswertung beendet mit Exitcode 0 (Artefakte: ...)"
  log "P5 fertig"
else
  log "ABBRUCH: Positivkontrolle oder Auswertung Exitcode $wcode, kein Bericht"
fi
exit "$wcode"
```

### Antworten auf die acht Fragen

1. **Welche Fassung hat die laufende Wache geladen?** Belegt ist nur der
   Startzeitpunkt (15:45:09) und dass die Datei danach geändert wurde. Damit gilt
   für den Start die Fassung `3c31d73`. Welche Bytes sie nach dem Schleifenende
   liest, ist **nicht prüfbar**: Bash liest Skripte inkrementell, Puffer und
   Dateioffset sind von außen nicht einsehbar.
2. **Welchen Aufruf führt sie aus?** Nach der alten Fassung die Auswertung direkt,
   ohne Positivkontrolle und ohne Nonce. Nach der neuen Fassung den Wrapper.
3. **Was passiert bei Exit 3?** Die Auswertung schreibt keinen Bericht und endet
   mit 3 (Nonce fehlt). Die alte Fassung protokolliert dann „Auswertung beendet
   mit Exitcode 3 (Artefakte: …)" und „P5 fertig", obwohl keine Artefakte
   entstanden sind.
4. **Wird der Fehler protokolliert?** Ja. Der Aufruf leitet stdout und stderr nach
   `$LOG`, die Meldung „ABBRUCH: kein Kontroll-Nonce übergeben …" landet dort.
5. **Bleibt die Wache aktiv?** Nein, sie beendet sich mit `exit "$wcode"`; der
   `trap` entfernt dabei die Gate-Sperre.
6. **Wird ein falscher Status gesetzt?** In der alten Fassung ja: „P5 fertig"
   ohne Bericht. Die neue Fassung setzt ihn nur bei Exit 0, und die
   Wiederaufnahme-Prüfung verlangt zusätzlich eine nichtleere Berichtsdatei — ein
   falsches „fertig" blockiert einen Neustart also nicht.
7. **Ist ein regulärer Neustart möglich?** Ja. Die Gate-Sperre fällt beim Beenden;
   bleibt sie nach einem harten Abbruch liegen, übernimmt die neue Fassung sie,
   weil sie die eingetragene PID prüft statt das Dateialter.
8. **Gefahr eines zweiten P5-Starts oder blockierenden Locks?** Kein zweiter
   Start durch dieselbe Instanz — sie beendet sich. Zusätzlich schützt die
   `harness.lock` im Run-Verzeichnis: ein zweiter Prozess auf derselben
   `run-id` bekommt `SperreBelegt` und endet mit 3, ohne Zeilen zu schreiben.

### Zustandsdiagramm

```
[Wache wartet]  (Takt 60 s, Frist bis 03:45)
      |
      |  drei Bedingungen erfüllt: kein Prozess, keine lebende Nachzug-Sperre,
      |  180 s ohne neue Zeile
      v
[Bedingungen erfüllt]
      |
      |  laufende Instanz (Fassung 3c31d73)          neuere Fassung (f05928a)
      v                                                     v
[Auswertung ohne Nonce]                              [Positivkontrolle]
      |                                                     |
      v                                          Exit 0 + Marke --+-- Exit != 0
[Exit 3, kein Bericht, Meldung im Log]                              |        |
      |                                                     v        v
      v                                            [Auswertung]  [kein Bericht]
[alt: "P5 fertig" + exit 3]                              |            Exit 4
      |                                                  v
      v                                          [Bericht geschrieben]
[Wache beendet sich, Gate-Sperre fällt]
      |
      v
--pruefen zeigt "frei"; Neustart mit aktueller Fassung
      |
      v
[Kontrolle Exit 0 + Nonce] -> [Auswertung Exit 0] -> [Bericht]

Zweig ohne Start: Frist 03:45 läuft ab -> "ABBRUCH", kein Bericht.
```

Der linke Zweig („Auswertung ohne Nonce") gehörte zur Instanz 5032 und ist mit
ihrer Beendigung um 16:55 entfallen. Für PID 6630 gilt die Frist 04:55.

## 3. Audit der 103 P5-Eingaben

| Prüfgröße | Ergebnis |
|---|---|
| Anzahl IDs | 103 |
| Anzahl eindeutiger IDs | 103 |
| Fehlende Ausgangsrecords | 0 |
| Zusätzliche IDs | 0 |
| Fehlende Fehlerklassen | 0 |
| Doppelte Goldreferenzen | 0 |
| Nicht zuordenbare Records | 0 |

Ergänzende Befunde:

- Alle 103 IDs stehen in `yun699.jsonl` und in der Lesekopie; alle tragen in der
  Lesekopie die Klasse `length_ohne_ergebnis`. Die Lesekopie enthält genau diese
  103 `length`-Zeilen, keine weitere — Auswahl und Ausfallmenge sind identisch.
- Goldzellen: 423 über 102 Records; `yun2024:653` hat keine und ist als nicht
  bewertbar markiert. Keine doppelten Feld/Arm-Schlüssel im Gold.
- Dokumentpfade: 103 von 103 vorhanden, alle Dateien existieren.
- **Splits:** 99 `test`, 4 `dev` (`yun2024:120`, `:228`, `:232`, `:233`, zusammen
  22 Goldzellen). Das ist keine Versionsvermischung, sondern Folge der Auswahl
  aller Ausfälle; für Split-getrennte Kennzahlen muss es aber bekannt sein.
- Der P5-Befehl nutzt `--split ""`, also alle 103 gemeinsam.

Es wurde nichts korrigiert; es gab nichts zu korrigieren.

## 4. Unabhängige Prüfung der Auswertungslogik

Zweite Implementierung, bewusst anders aufgebaut: Sie gruppiert die
Vorhersagezellen einmal und entscheidet je Goldzelle, ob ein Kandidat existiert
und ob ein Wert auf 1e-6 passt. `werte_p5_aus.py` läuft dagegen je Goldzelle über
die Kandidatenliste und filtert die strenge Fassung über die Zeitpunktmenge.
Verglichen wurden alle Kernkennzahlen und die Statusverteilung.

| Datensatz | Grundgesamtheit | Abweichungen |
|---|---:|---|
| Positivkontroll-Fixture | 8 | keine |
| Nullprobe (Lesekopie gegen sich selbst) | 103 | keine |
| Zufallsdaten mit Dubletten, Mehrdeutigkeiten, `None`-Werten, Fehlerklassen | 40 | keine |

Damit sind die neun Prüfpunkte belegt:

1. Grundgesamtheit ist die 103er-Auswahl (Selection-JSON), nicht ein Klassenfilter.
2. Fehlend, leer, technisch ausgefallen und auswertbar werden unterschieden.
3. Nicht enthaltene IDs (`fehlt`) sind von ausgefallenen (`weiter_ausfall`) getrennt.
4. Goldzellen zählen nur für bewertbare Records.
5. Adressiert (Schlüssel) und wertgleich (Wert auf 1e-6) sind getrennt.
6. Großzügig und streng laufen über dieselbe Grundgesamtheit; nur die
   Zeitpunktbedingung unterscheidet sie.
7. Die Aufschlüsselung nutzt die Klasse aus der Lesekopie, nicht die neue.
8. Records ohne Gold zählen bei technischen und strukturellen Kennzahlen mit
   (`zellen_neu`, technisch, auswertbar), nicht in der Golddeckung.
9. Dubletten und Mehrdeutigkeit: mehrere Zellen desselben Schlüssels zählen bei
   der Deckung einmal, streuen sie über mehrere Zeitpunkte, fällt der Treffer in
   der strengen Fassung weg.

## 5. Vorbereitete Kennzahlen

Grundgesamtheit für alle Quoten: die 103 adressierten IDs; Goldquoten nur über
die 102 bewertbaren Records.

| Kennzahl | Definition |
|---|---|
| Technische Erfolgsquote | Records mit Antwort ohne Fehlerklasse / 103 |
| Anteil auswertbar | Records mit mindestens einer Zelle / 103 |
| Inhaltlich gerettet | Records mit mindestens einer wertgleichen Goldzelle / 102 |
| Adressierte Goldzellen | Goldzellen mit passendem Feld/Arm-Schlüssel in der Vorhersage |
| Wertgleiche Goldzellen | davon mit Wertdifferenz < 1e-6 |
| Großzügige Deckung | adressiert bzw. wertgleich / 423 |
| Strenge Deckung | dieselbe Rechnung, aber nur Schlüssel mit genau einem Zeitpunkt |
| Nach Fehlerklasse | alle Kennzahlen getrennt je Klasse aus der Lesekopie |

### Precision, Recall, F1: berechenbar, mit Auflagen

Definition auf Zellebene, 1:1-Zuordnung je Record:

- **TP:** Goldzelle, für die eine Vorhersagezelle mit gleichem Feld/Arm und
  Wertdifferenz < 1e-6 existiert (jede Vorhersagezelle höchstens einmal
  verbraucht).
- **FN:** Goldzelle ohne solche Entsprechung.
- **FP:** Vorhersagezelle, die für keine Goldzelle verbraucht wurde.

Pilot auf den 559 erfolgreichen Zeilen der Lesekopie (nicht P5): TP 1.844,
FP 410, FN 462 → Precision 0,818, Recall 0,800, F1 0,809. Die TP-Zahl stimmt
exakt mit der wertgleichen Deckung der Auswertung überein (1.844) — eine
unabhängige Gegenprobe auf demselben Material.

**Auflagen, die im späteren Bericht stehen müssen:**

- Die Zuordnung ist schlüsselbasiert. Ob die Vorhersage denselben Zeitpunkt meint,
  ist nicht prüfbar, weil das Gold keinen trägt; Precision ist deshalb eine
  Obergrenze.
- Records ohne Gold (`yun2024:653`) erzeugen zwangsläufig FP. Sie müssen aus der
  Precision herausgerechnet oder separat ausgewiesen werden.
- Mehrere Vorhersagezellen für denselben Schlüssel zählen als FP, auch wenn eine
  davon richtig ist. Das ist gewollt (Redundanz ist ein Fehler), muss aber
  dastehen.
- Die offizielle Bewertung bleibt der geschützte Bewertungslauf; diese Zahlen
  sind eine nachvollziehbare Selbstprüfung.

## 6. Reproduzierbarkeit

| Objekt | Kennung |
|---|---|
| `yun_full/werte_p5_aus.py` | Blob `70acd37db8a1a639d2f2d452ea7a23b35a089200` |
| `yun_full/positivkontrolle_p5.py` | Blob `5a66d83794de4d34088299779ec02047fd1815b0` |
| `yun_full/werte_p5_mit_kontrolle.sh` | Blob `3290dfe21fa1ced92718bdf97a418348e5f3a97b` |
| `yun_full/starte_p5_wenn_frei.sh` | Blob `f2edc3e7ddd9815ccc5fe3833c03f3248b4a777d` |
| `yun_full/bereite_p5_vor.py` | Blob `17923c7be463fcd4e037c8bcfe62c04419702fa2` |

SHA-256 der eingefrorenen Eingaben und Fixtures:

| Datei | SHA-256 |
|---|---|
| `yun_full/records/yun699.jsonl` (Records samt Gold) | `c22ed3fb42dbaaff7051a89cdb327c4b250a134db0a62a19d3877d5ba311c0b1` |
| `iterativ/ergebnisse/p5_vorbereitung_20261118.json` (Auswahl) | `9883300707a9188511778802be2a5b22c420d1ae982fa570c3b1ed7010088a97` |
| `iterativ/kontrolle/p5_positivkontrolle/alt.jsonl` | `ffc83b2d0e7483c040d3b4f5bdca2de2d5054c440bbc998b00baddc8d223f62b` |
| `iterativ/kontrolle/p5_positivkontrolle/neu.jsonl` | `0c284db915e8a7cef835d31e11ec1a3ce40e3cfac8f9feef3fecef5ecb7839a0` |
| `iterativ/ergebnisse/p5_positivkontrolle_20261118.json` | `2ce9b72d7400428a904cc4eabcfe8c81ee6ce3526898dd70c2232136a518c249` |
| `runs/_lesekopie_20261118/predictions.jsonl` (Referenz „alt") | `8f6d622ff6e1ac98233186a3e50026ee525f1f88b3d003973bb094dc1ec3ab2a` |

Laufkonfiguration: Modell `gwdg/glm-5.3` (`max_tokens` 24000), `run-id`
`yun699_p5_24000_20261118`, `--split ""`, `--workers 2`, `--retry-strategie neu`,
`--quelle p5_24000`, Budget 24.000 Tokens, Reparaturaufruf maximal 32.000 Tokens
(`RETRY_MAX_TOKENS`), Retry-Policy `retry_manager.STANDARD`. Die Prompt-Version
wird zur Laufzeit aus den Flags bestimmt (`PROMPT_VERSION`-Familie v2–v8,
`DEFAULT_TARGET_FALLBACK = True`); der P5-Befehl setzt keine abweichenden
Versionsflags.

## 7. Gefundene Fehler und Risiken

| Nr. | Befund | Kategorie | Schwere |
|---|---|---|---|
| 1 | Wache 5032 startete vor der Sprint-46-Fassung; sie hätte die Auswertung ohne Nonce gerufen | Bestätigt, **erledigt 16:55** (PID 6630, Fassung `f05928a`) | mittel |
| 2 | Auswertung verweigert dann mit Exit 3 und schreibt keinen Bericht | Bestätigt, **erledigt 16:55** (Weg über den Wrapper) | niedrig (gewollt) |
| 3 | Alte Fassung protokolliert „P5 fertig" auch ohne Bericht | Bestätigt, **erledigt 16:55** (neue Fassung prüft Exitcode und Bericht) | niedrig |
| 4 | Welche Bytes die alte Instanz nach der Schleife gelesen hätte | **entfällt** (Instanz beendet, nicht mehr ausführbar) | mittel |
| 5 | Auswertung wäre ohne Kontrolle nicht angelaufen; mit Kontrolle entsteht ein Bericht | Bestätigt | niedrig |
| 6 | `ids_ohne_altzeile` würde nicht in die Grundgesamtheit zählen | Verdacht (aktuell 0 Fälle) | niedrig |
| 7 | `yun2024:653` ohne Gold verfälscht Precision, wenn sie nicht ausgenommen wird | Bestätigt | mittel |
| 8 | 4 von 103 Records stammen aus dem dev-Split | Bestätigt | niedrig |
| 9 | Wachenfrist endet 04:55 | Bestätigt | niedrig |

## 8. Handlungsempfehlungen

1. **Nichts weiter an der Wache tun.** PID 6630 wartet mit der aktuellen Fassung;
   jeder Eingriff würde nur die Frist neu setzen.
2. **Beim nächsten Blick** genügen `bash yun_full/starte_p5_wenn_frei.sh --pruefen`
   und `tail` auf `runs/p5_start_20261118.log`. Steht dort „Bedingungen erfuellt",
   laufen P5, Kontrolle und Auswertung von selbst.
3. **Falls doch einmal von Hand ausgewertet werden muss:** niemals
   `werte_p5_aus.py` direkt, sondern `bash yun_full/werte_p5_mit_kontrolle.sh`.
   Ein direkter Aufruf endet ohne Nonce mit 3 (so gewollt).
4. **Im späteren P5-Bericht** Precision nur mit den genannten Auflagen ausweisen
   und `yun2024:653` separat führen.
5. **Vor dem Start** den Merker setzen, dass die Wachenfrist um 04:55 endet und
   die Wache an der Desktop-Sitzung hängt; danach startet sie nichts mehr und muss
   neu gestartet werden.
