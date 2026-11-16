# Trockenlauf auf der Testbasis, 5 Records (16.11.2026)

Run-ID `trockenlauf76_20261116`, Modell `glm`, Datei
`records/yun_test76_ziel.jsonl` (SHA-256 `06fea97c…`, damals Version 1;
seit 16.11.2026 Version 2 mit `74fd0c05…`, siehe
`korrektur_yun2024_479.md`),
`--split test --cell-timepoint --target-fallback --group-size-mode aus --repair
--max-tokens 19000`.

Gewählt: `yun2024:44` (baseline), `51` (postintervention phase), `289` (post
(after 4-week training)), `71` (**at admission**, unsicher), `693`
(**24 h postoperatively**, unsicher). Damit sind drei der neuen Ziel-Label-
Familien plus baseline abgedeckt, zwei davon als unsicher markiert.

## 1. Lädt die Datei vollständig?

**Ja.** Der Lauf meldet `5 Records, 5 offene Auftraege`; die Auswertung liest
**76 Records** (5 mit Vorhersage, 71 ohne) und **243 Goldzellen**. Kein Record
fehlt, kein Ziel ist leer. Kosten: 57.199 Completion-Tokens für 5 Records
(11.440 je Record), davon zwei Reparaturaufrufe mit 2.491 und 1.695 Tokens.

## 2. Werden die neuen Ziel-Labels ausgewertet?

| Ziel-Label | Record | Zellen | Klasse | Belegstufe |
|---|---|---:|---|---|
| `postintervention phase` | 51 | 4 | zieltreu | gedruckt |
| `post (after 4-week training)` | 289 | 6 | zieltreu | gedruckt |
| `24 h postoperatively` | 693 | 2 | zieltreu | artikel (`24 h`) |
| `baseline` | 44 | 0 | – | leere Antwort |
| `at admission` | 71 | 0 | – | leere Antwort |

**Entscheidung zu `at admission`.** Das Ziel meint die Handkraft bei Aufnahme
(Subgruppe n = 21), also die Messung **vor** der Intervention — derselbe
Zeitpunkt, den die 44 Records mit reinen Gruppengrößen als `baseline` tragen.
Deshalb bildet `_kanonisch` die Synonyme `baseline`, `admission`,
`at admission`, `on admission`, `preoperative`, `pre-operative`, `preop` und
`before surgery` auf `baseline` ab, und zwar in beide Richtungen: Ziel
`at admission` mit Label `baseline` ist zieltreu und umgekehrt. Bewusst nicht
umgedeutet werden `day 0` und `week 0` (können je nach Studie nach der
Intervention liegen) sowie jede echte andere Zeit (`at admission` gegen
`month 6` bleibt `rueckfall`). Abgesichert durch
`test_aufnahme_ist_ein_baseline_zeitpunkt` und, an der echten Zeile
`yun2024:71`, durch `test_ziel_at_admission_ist_aufloesbar`.

**Befund: `24 h postoperatively` wurde zunächst nicht aufgelöst.** Das Modell
antwortete `"timepoint": "24"`; der Resolver kannte nur `week|month|day` und
ließ die Zelle als `unklar` fallen. Behoben in `evaluate_fallback.py`:

* `normalisiere_label` liest `24 h …` als Einheit Stunde (`hour 24`),
* `klassifiziere` vergleicht beschreibende Ziele über Einheit und Zahl,
  **nur** wenn das Ziel nicht schon die Form `month 6` hat,
* `einheiten_im_artikel` erkennt die Abkürzung `24 h` im Artikeltext.

Vor dem Fix: 10 zieltreu, 2 unklar, 6 richtig. Nach dem Fix: **12 zieltreu,
0 unklar, 8 richtig**, Precision 0,6667 auf den 12 Zellen.

`at admission` und `baseline` sind im Lauf **nicht in der Praxis** geprüft:
beide Records antworteten leer (44 mit 544 Tokens, 71 mit 12.112 Tokens). Die
Auflösung selbst ist jetzt per Test abgesichert, nicht per Modellantwort.

## 3. Erscheint der Block `unsichere_ziele`?

**Ja, nach einer Korrektur.** Erster Lauf: `4 Records, 2 Zellen, 0 richtig` —
zwei Fehler auf einmal: der Block zählte alle markierten Records der Datei
(auch die 63 und 694 ohne Vorhersage), und er zählte Zellen nur in den Zweigen
`zieltreu`/`rueckfall`, sodass die als `unklar` eingestuften Zellen von 693
weder als richtig noch als falsch erschienen.

Jetzt zählt der Block nur Records mit Vorhersage und prüft jede Zelle direkt
gegen das Gold; er hat ein eigenes `ohne_gold`:

```
[unsichere_ziele] 2 Records, 2 Zellen, richtig 2, falsch 0
```

Das sind `71` (leer, 0 Zellen) und `693` (2 Zellen, beide richtig). Ein Test in
`test_test76_ziel.py` hält das fest.

## 4. Nebenbefund: Reproduzierbarkeit der alten Läufe

Der erste Entwurf der Vergleichsregel stufte auch `"6 months"` gegen Ziel
`month 6` als zieltreu ein und verschob damit 7 Zellen im archivierten
v7-Folgelauf (46 → 53 zieltreu). Die Regel greift jetzt nur bei Zielen mit
Zusatzwörtern. Gegenprobe gegen `git show HEAD:` auf allen 75 Zellen des
v7-Folgelaufs: **0 geänderte Zellen**. Die Fehlklassifikation „6 months“ gegen
„month 6“ bleibt bestehen und ist als offener Punkt notiert, nicht stillschweigend
geändert.

## 5. Qualität der fünf Antworten

| Record | Pfad | Tokens | Zellen | richtig | falsch |
|---|---|---:|---:|---:|---:|
| 44 | standard | 544 | 0 | – | – |
| 71 | standard | 12.112 | 0 | – | – |
| 51 | repair | 19.000 + 2.491 | 4 | 2 | 2 |
| 289 | repair | 19.000 + 1.695 | 6 | 4 | 2 |
| 693 | standard | 2.357 | 2 | 2 | 0 |

Falsch: `51` Gruppengrößen 612/398 statt 562/463; `289` Komparator-Mittelwert
39,5 statt 48,2 und SD 10,6 statt 12,3 (jeweils die Prä-Werte der Tabelle).
Zwei von fünf Records antworten leer, zwei von fünf brauchen die Reparatur.

## 6. Review der Auswertung

Vereinfacht, ohne die archivierten Zahlen zu verschieben (Gegenprobe: der
v7-Folgelauf ist bis auf den neuen Block `unsichere_ziele` byte-identisch):

* `ZEIT_LABEL` wird aus `EINHEIT_WORT` gebaut. Die alte Doppelung
  (`week|month|day` hier, `week|month|day|year|hour` dort) war die Ursache des
  Stunden-Fehlers; jetzt gibt es eine Quelle.
* `_zahl_und_einheit` ersetzt die zwei Stellen, die dieselbe Regex-Logik
  (Einheit-Zahl, Zahl-Einheit, `24 h`) nacheinander probierten.
* `_kanonisch` bündelt die Baseline-Synonyme an einer Stelle, statt
  Sonderfälle in `belegstufe` und `normalisiere_label` zu verteilen.
* Toter Parameter entfernt: `arme_gemischt` und `arm_klasse` bekamen ein
  `target`, das nie gelesen wurde; vier Aufrufstellen angepasst.
* Die Zeitdistanz misst weiterhin das **gedruckte** Label, nicht die kanonische
  Form — sonst würde `preop` plötzlich als Monat 0 zählen und der archivierte
  Median der Rückfall-Distanz (2,76 Monate) sich verschieben.

Bewusst offen gelassen (jedes hätte archivierte Zahlen geändert):

* Zellen, deren Label `unklar` bleibt, zählen **zusätzlich** als Auslassung —
  doppelte Strafe. Im 76er-Lauf betrifft das 0 Zellen, in älteren Läufen aber
  welche.
* `"6 months"` gegen Ziel `month 6` bleibt `rueckfall`, weil reine Ziele
  unverändert durch den Stringvergleich laufen (Reproduzierbarkeit);
  semantisch sind sie gleich.
* `week 0` und `day 0` gegen Ziel `baseline` bleiben `rueckfall`.

## 7. Grenzen

- Fünf Records, 12 Zellen: die Precision 0,6667 ist keine Schätzung für die 76.
- Die Auflösung von `at admission` ist getestet, aber im Lauf nicht mit einer
  echten Modellantwort belegt (Record 71 antwortete leer); das Ziel selbst
  stammt aus einem abgeleiteten, unsicheren Eintrag.
- Der Lauf prüft nur den v7-Pfad mit `--group-size-mode aus`; `lang` und `kurz`
  sind hier nicht getestet.
- Die Reparatur hat bei `51` und `289` je 19.000 Tokens Primäraufruf verbrannt;
  das ist die erwartete Length-Neigung, nicht neu.
