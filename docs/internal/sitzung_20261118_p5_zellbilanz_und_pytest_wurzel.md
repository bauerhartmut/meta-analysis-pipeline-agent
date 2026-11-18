# Sitzung 18.11.2026: P5-Zellbilanz, Wachenneustart und pytest aus der Wurzel

Arbeitsprotokoll der Sitzung ab 16:30. Alle Zahlen sind gemessen, nicht
geschätzt; Schätzungen sind als solche markiert. Kein Modelllauf, keine
Netzwerkanfrage, kein Eingriff in Goldstandard, Predictions oder Kerndateien.

## Ausgangslage

- Sprint 47 hatte einen rein lesenden Audit der P5-Wartephase verlangt. Der
  Bericht war erhoben, aber noch nicht geschrieben.
- Die laufende P5-Wache (PID 5032) war um 15:45:09 gestartet, das Skript um
  16:21:43 geändert: Sie hätte die Auswertung ohne Kontroll-Nonce gerufen.
- `pytest` aus der Projektwurzel brach mit 107 Sammelfehlern ab.

## 1. Audit-Bericht fertiggestellt und aktualisiert

`public_benchmark/extended_benchmark/iterativ/ergebnisse/p5_wartephase_audit_20261118.md`
(323 Zeilen), Commit **d47d6f7**.

Inhalt: Zustandsdiagramm des Wachenübergangs, Prüftabelle der 103 Eingaben,
unabhängige Nachrechnung, Kennzahlendefinitionen, Reproduzierbarkeit,
Befundtabelle mit den Kategorien Bestätigt/Verdacht/Nicht prüfbar.

Kernbefunde:

| Befund | Ergebnis |
|---|---|
| Welche Fassung die alte Wache nach der Schleife liest | **Nicht prüfbar** (Bash liest inkrementell); beide Ausgänge fail-closed |
| 103 Eingaben | 103 eindeutig, 0 Duplikate, 0 fehlende Records, 423 Goldzellen, nur `yun2024:653` ohne Gold |
| Unabhängige Zweitimplementierung | keine Abweichung auf Fixture (8), Nullprobe (103) und 40 Zufallsrecords |
| Precision/Recall/F1 machbar | ja, Pilot auf 559 Erfolgszeilen: TP 1.844, FP 410, FN 462 |
| Splits | 99 test, 4 dev (`yun2024:120`, `:228`, `:232`, `:233`, 22 Goldzellen) |

## 2. P5-Wache neu gestartet (Betrieb, kein Commit)

- Identität vor dem Signal geprüft: `ps -ef` zeigte genau einen Prozess
  `bash …/starte_p5_wenn_frei.sh` (msys-PID 5032), Gate-Datei enthielt `5032`.
- SIGTERM an 5032, nach rund 5 s beendet, `sleep`-Kind ebenfalls weg. Die
  Gate-Sperre hat die Wache über ihr eigenes `trap` entfernt; keine Sperrdatei
  von Hand angefasst.
- Neustart 16:55:19 als **PID 6630**, Gate `6630`, Fassung `f05928a`
  (Wrapper-Aufruf `werte_p5_mit_kontrolle.sh` im Skript vorhanden).
- `--pruefen`: „Prozess: 1 (PID 3952) ok · Sperre PID 2153 lebt weiter ·
  Letzte Zeile vor 77 s → **belegt, P5 wuerde warten**".
- Frist dadurch **04:55** statt 03:45; `runs/yun699_p5_24000_20261118/` existiert
  noch nicht.
- Nachtlauf 532/3952 und Nachzug 2152/2153 unverändert.

## 3. Precision, Recall, F1 in die Auswertung eingebaut

Commit **68bccc5**: `yun_full/werte_p5_aus.py`, `yun_full/positivkontrolle_p5.py`,
`tests/test_werte_p5_aus.py`, `tests/test_positivkontrolle_p5.py`
(246 Zeilen). Keine Kerndatei berührt.

Umgesetzt nach den Auflagen aus dem Audit:

- **`yun2024:653` ausgenommen:** Die Bilanz läuft nur über die 102 bewertbaren
  Records. Deren Zellen stehen als `zellen_ohne_gold` im Ergebnis und als eigene
  Berichtszeile „nicht als FP gezählt".
- **Mehrfachzellen als FP:** `bilanz()` ordnet 1:1 zu — jede Goldzelle trifft
  höchstens einmal, jede Vorhersagezelle wird höchstens einmal verbraucht.
  FP ist aufgeteilt in `ueberzaehlig` (Schlüssel im Gold: Dublette oder falscher
  Wert) und `fremdschluessel`.
- **Von der Kontrolle abgedeckt:** `ERWARTET` enthält die vollständige Bilanz,
  `pruefe()` vergleicht Feld für Feld. Soll: TP 5, FP 3 (3 überzählig, 0 fremd),
  FN 6, Precision 0,625, Recall 0,454545, F1 0,526316, 7 Records in der Bilanz,
  1 Zelle außerhalb (k8 = der 653-Fall).
- `quote()` gibt bei leerem Nenner `None` aus, im Bericht „nicht definiert" —
  keine erfundene Null.

Gegenproben:

| Prüfung | Ergebnis |
|---|---|
| Nullprobe über 103 IDs | TP 0, FP 0, FN 423, Precision „nicht definiert", Recall 0,000 |
| Pilot auf 559 Erfolgszeilen | TP 1.844, FP 410 (295 überzählig, 115 fremd), FN 462 → Precision 0,818, Recall 0,800, F1 0,809 — exakt die Audit-Zahlen |

## 4. Kontrollartefakt nachgezogen

Commit **e6f1eb2**: `p5_positivkontrolle_20261118.{json,md}`. Vorher geprüft, dass
das Artefakt-Ist exakt der Live-Rechnung entspricht (`soll == ERWARTET`, keine
Abweichungen); erst dann committet.

## 5. Testläufe

| Lauf | Ergebnis |
|---|---|
| `research_agent/tests` | 1543 passed, 2 skipped (7:28), Exit 0 |
| `public_benchmark/tests` | 382 passed (6,2 s), Exit 0 |
| Summe der eigenen Suiten | 1925 passed, 2 skipped |
| Wurzel ohne `pytest.ini` | 107 Sammelfehler, Exit 2 |

Ursache der Wurzel-Fehler: `export_clean_20261117/` und `handoff_20261116/`
enthalten eigene `research_agent`-Kopien und schieben sie vor das echte Paket
(`ModuleNotFoundError: No module named 'research_agent.database'` bzw.
`'research_agent.tests'`). Dieselben Verzeichnisse laufen einzeln fehlerfrei.
Zusätzlich wird `public_benchmark/raw_data/evidence_inference/scripts/split_train_val_test.py`
als `*_test.py` eingesammelt und liest beim Import `/home/ubuntu/...`.

## 6. pytest.ini angelegt und Wurzel-Lauf grün

Commit **2be9800**: `pytest.ini` mit

```ini
norecursedirs = export_clean_* handoff_* .venv* venv* raw_data build dist node_modules *.egg .git
```

`raw_data` kam über die beauftragte Liste hinaus dazu, weil sonst der
Fremdcode-Restfehler die Sammlung weiter abgebrochen hätte; das Verzeichnis
existiert genau einmal im Baum. Muster gelten bei `norecursedirs` für
Verzeichnisnamen, nicht für Pfade.

Ergebnis des Wurzel-Laufs: **1931 passed, 2 skipped, 0 failed, Exit 0** in 9:42.
Die sechs Tests über den 1925 liegen außerhalb von `tests/` (u. a. unter
`public_benchmark/extended_benchmark/`).

## 7. README nachgezogen

Commit **a9268f8**: Der Tests-Abschnitt führt jetzt `python -m pytest -q` aus der
Wurzel als Standard, nennt die gemessenen Zahlen und erklärt, wofür die
`pytest.ini` da ist. Die Einzelaufrufe bleiben als schnelle Variante darunter.

## Offene Punkte

- **P5 ist noch nicht gelaufen.** Die Wache wartet; der Ernstfall (Start,
  Kontrolle, Auswertung) ist damit ungetestet. Die Frist endet 04:55.
- **Echte Precision/Recall/F1 fehlen** — sie entstehen erst mit P5-Zeilen. Die
  Zahlen aus dem Pilot sind eine Selbstprüfung, nicht die offizielle Bewertung.
- **2 übersprungene Tests** in `research_agent` sind nicht einzeln benannt.
- **Push unmöglich:** `origin/master` ist ein fremder Orphan-Commit ohne
  gemeinsame Basis; ohne Force-Push (nicht erlaubt) geht nichts hinüber.
- Weitere Doku-Stellen mit dem alten Zweizeiler:
  `docs/verification/bericht_2026-11-13.md` (Z. 212/215) und
  `VERBESSERUNGSBRIEFING.md` (Z. 219).

## Empfehlung

Warten, bis Nachtlauf und Nachzug fertig sind; die Wache startet P5 dann mit
Kontrolle und Auswertung von selbst. Beim ersten echten Bericht zuerst die
Bilanzzeile „falsch positiv, Schlüssel im Gold, aber Dublette oder falscher
Wert" lesen: Liegt sie deutlich über `fremdschluessel`, wiederholt das Modell
Schlüssel und die Precision ist entsprechend zu lesen.
