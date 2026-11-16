# Offene Probleme und naechste Experimente

Stand 16.11.2026. Nichts hier ist gemessen, ausser es steht ausdruecklich dabei.

## 1. Ungeloeste Probleme

### 1.1 Quellenauswahl (groesster Hebel)

13 der 29 falschen Zellen der 60er-Stichprobe sind Arm- oder Populationsfehler,
4 weitere falsche Tabellenzeilen. Das Modell liest die Zahl richtig und an der
falschen Stelle. Ein Prompt-Zusatz (v8, Quellenzeile im selben JSON) hat nicht
funktioniert: F1 0,8369 -> 0,8088, und das Modell liess zusaetzlich die
v7-Pflichtangabe `timepoint` weg (drei Rohantworten in
`laeufe/yun_v8_probe_20261116/`).

Offen: Bringt eine echte Zweistufigkeit (eigener Aufruf fuer Zeile und Arm)
den erwarteten Gewinn? `skripte/run_stage_extraction.py` und
`skripte/stage_extraction.py` machen das bereits fuer **Ereignisfelder**
(`EVENT_FIELDS`). Eine Erweiterung auf Mean/SD/Gruppengroesse fehlt.

### 1.2 Goldqualitaet

Zwei Records sind belegt widerspruechlich (yun2024:524 Text gegen Tabelle,
yun2024:447 zwei verschiedene N), ein dritter (yun2024:669) ist unklar. Ohne
Klaerung ist jede Precision eine Untergrenze. Ein Gold-Audit ueber die 60
Records steht aus.

### 1.3 Verhalten des Gateways

- Cache: Antworten wurden ohne Cache-Buster fuer abweichende Prompts
  zurueckgegeben. Bei Qwen3-30B waren 14 von 20 Antworten als Cache-Treffer
  markiert, obwohl das Modell vorher nie lief. Ob der Cache modelluebergreifend
  greift, ist ungeklaert; Token- und Laufzeitangaben fuer Cache-Treffer sind
  nicht belastbar.
- Laufzeit: Ein 8.000-Token-Lauf brauchte einmal 4-6 Minuten pro Record, ein
  zweiter 11 Sekunden. Die Ursache (Last, Timeout-Retry) ist nicht untersucht.

### 1.4 Vollstaendiger Testsplit

596 Records mit 8.000 Tokens wurden nicht gefahren. Bei den gemessenen
11-33 s/Record waeren das 2 bis 5,5 Stunden; bei der langsamen Variante
40-60 Stunden. Voraussetzung: stabile Laufzeit und Wiederaufnahme
(`predictions.jsonl` wird bereits inkrementell fortgesetzt).

### 1.5 Nicht getestete Prompt-Experimente

Experiment A (Vollstaendigkeit: alle sechs Felder pruefen, "nicht berichtet"
von "nicht gefunden" trennen), D (kompakteres Ausgabeschema) und E
(Evidenzverknuepfung je Zelle) sind beschrieben, aber nie gelaufen. Sie duerfen
nicht als erfolgversprechend zitiert werden.

## 2. Naechste sinnvolle Experimente

| Prioritaet | Experiment | Erwartung | Aufwand | Risiko |
|---|---|---|---|---|
| P0 | Zweistufig fuer kontinuierliche Felder: Stufe 1 = Zeile/Arm (eigener Aufruf), Stufe 2 = Werte | adressiert 13 von 29 Fehlern | 2 Tage Bau, 2 Aufrufe/Record (~80k statt 39k Tokens fuer 20 Records) | doppelter Tokenverbrauch, Harness-Komplexitaet |
| P1 | Gold-Audit der 60 Records (zwei Reviewer, nur Konflikte aufloesen) | macht Precision vergleichbar | 3-4 h manuell | keine |
| P1 | Ausgabeschema mit Originaleinheit und Originalwert, keine Umrechnung | 4 von 29 Fehlern | 1 Tag inkl. Parser | Schemaaenderung bricht alte Laeufe nicht, wenn additiv |
| P2 | Vollstaendigkeitsregel (Experiment A) | Recall, unklar ob Precision haelt | 1 Tag | wie v8: Zusatz kann bestehende Regeln verdraengen |
| P2 | Evidenzverknuepfung mit Seiten-/Tabellenangabe | pruefbar ohne Gold | 2 Tage | zusaetzlicher Output, ungemessen |
| P2 | Testsplit 596 Records bei 8.000 Tokens | Aussenvalidierung der 20er/60er-Zahlen | 3-6 h Rechenzeit | Kosten, Abbruchrisiko |

## 3. Was nicht wiederholt werden sollte

- Prompt-Zusaetze, die das JSON-Schema erweitern (v8): Das Modell ignoriert den
  Zusatz und laesst dafuer bestehende Pflichtfelder weg.
- Gruppengroessen-Regel im Prompt (Experiment B): kein Effekt (F1 -0,012).
- Modellvergleiche ohne Cache-Buster: nicht interpretierbar.
- Vergleiche mit GPT-4 ohne bereinigte Goldbasis: die Populationen und die
  Goldqualitaet unterscheiden sich.
