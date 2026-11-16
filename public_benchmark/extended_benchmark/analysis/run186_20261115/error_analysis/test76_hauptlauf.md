# Hauptlauf auf der Testbasis, alle 76 Records (16.11.2026)

Run-ID `test76_hauptlauf_20261116`, Modell `glm` (`gwdg/glm-5.3`),
`records/yun_test76_ziel.jsonl` in **Version 2** (SHA-256 `74fd0c05…`, 76
Records, 243 Zellen), `--split test --cell-timepoint --target-fallback
--group-size-mode aus --repair --max-tokens 19000 --workers 3`.

Kosten: **552.552 Completion-Tokens** (531.767 primär, 20.785 Reparatur) für 76
Records, 7.268 je Record; 4.657 Sekunden Rechenzeit summiert über die Records,
Wanduhr rund 40 Minuten. 12 Records liefen über den Reparaturpfad.

Die Zahlen der Version 1 (vor der Gold-Korrektur) stehen in
`korrektur_yun2024_479.md`; die Auswertung wurde ohne neuen API-Aufruf
wiederholt.

## 1. Gesamtkennzahlen

| Kennzahl | Wert |
|---|---|
| Zell-F1 | 0,5455 |
| Recall | 0,4321 |
| Precision | 0,7394 |
| MAE | **0,5763** |
| Abdeckung | 0,535 (130/243) |
| exakte Records | 16/76 |

Die MAE von 0,5763 entsteht aus einer Abweichungssumme von 74,92 über 130
zugeordnete Zellen. Die größten Einzelabweichungen sind `yun2024:365`
(Komparator-Gruppengröße 20 statt 45 → 25) und die sechs Records der
MCCB-Studie mit 2,0 bis 8,7 zu niedrigen Komparator-Mittelwerten
(Abschnitt 6).

## 2. Zellklassen

| Klasse | Zellen | richtig | falsch | ohne Gold | Precision |
|---|---:|---:|---:|---:|---:|
| `zieltreu` | 76 | 57 | 9 | 10 | 0,8636 |
| `rueckfall` | 48 | 32 | 16 | 0 | 0,6667 |
| `gruppengroesse_ohne_zeitpunkt` | 4 | 4 | 0 | 0 | 1,0 |
| `ohne_zeitpunkt` / `ohne_ziel` | 0 | – | – | – | – |

Belegstufen der Zeitpunktlabels: `gedruckt` 120, `artikel` 8, `ziel` 2,
`unklar` 8. Treffer mit belegter Einheit 93, Treffer allein aus dem Ziel 2.
Rückfallquote-Intervall 0,3913–0,4493.

`unsichere_ziele`: **4 Records, 10 Zellen, 10 richtig, 0 falsch.**

## 3. Ausfälle und leere Antworten

34 Records liefern keine Zelle: 5 technische Ausfälle und 29 leere Antworten.
Von den 34 hat 31 ein Gold ohne Mittelwerte (leer ist dort erwartet), 3 ein Gold
mit Mittelwerten.

| Record | Art | Tokens | Reparatur |
|---|---|---:|---|
| `yun2024:53` | `length_ohne_ergebnis` | 19.000 | 6.000 Tokens, wieder `length` |
| `yun2024:148` | `length_ohne_ergebnis` | 19.000 | 6.000 Tokens, wieder `length` |
| `yun2024:671` | `length_ohne_ergebnis` | 19.000 | 507 Tokens, `stop`, aber keine Zelle |
| `yun2024:52` | Read-Timeout (300 s), 0 Tokens | – | Retry lief, wieder Timeout |
| `yun2024:51` | Read-Timeout (300 s), 0 Tokens | – | Retry lief, wieder Timeout |

Beide Timeout-Records hatten ihren zweiten Versuch schon; ein weiterer wäre
blinde Wiederholung.

## 4. Auslassungen konzentrieren sich auf Gruppengrößen

125 Auslassungen (Quote 0,5144): `intervention_group_size` 45,
`comparator_group_size` 45, `*_standard_deviation` 8+7, `*_mean` 7+6,
`*_events` 3+3. Die 31 folgenlosen Records sind genau die, deren Gold nur
Gruppengrößen enthält.

## 5. Gold-Korrektur `yun2024:479` (Version 2)

Der Artikel (PMC4144850, Tabelle 4) druckt `Anemic: Hb<110 g/l   1,922  0.508
1,919  0.562` mit Tausendertrennzeichen. Die Version 1 der Testbasis las daraus
1,922 und 1,919 Personen. Korrigiert auf 1919/1922 Personen und 1078/976
Ereignisse (Gegenprobe: 1919 × 0,562 = 1078,5; 1922 × 0,508 = 976,4).

Wirkung auf die Zellen (geprüft in `runs/test76_hauptlauf_20261116/
predictions.jsonl`): Die Antwort zu 479 enthält **vier** Zellen — die
Gruppengrößen 1919 und 1922, die nach der Korrektur richtig sind (vorher falsch:
`zieltreu` 57 statt 55), und die beiden Anteile 0,562 und 0,508, die das Modell
als `*_mean` gemeldet hat. Diese beiden Anteile stehen nicht im Gold und zählen
als überzählige Zellen. Die **Ereigniszahlen 1.078 und 976 hat das Modell nicht
berichtet**; die beiden `*_events`-Zellen bleiben Auslassungen — vor und nach der
Korrektur gleich. Die Abweichungssumme fiel von 3.912,08 auf 74,92, weil die
beiden Abweichungen von 1.920,08 und 1.917,08 entfielen. Details und Hashes in
`korrektur_yun2024_479.md`.

## 6. Der Modellfehler bei 289–295: falsche Armzeile, richtige Spalte

Sieben Records (`289`–`295`) gehören zur selben Studie (PMC4215531, MCCB-Tabelle
mit den Zeilen `FAT Pre`, `FAT Post`, `TAU Pre`, `TAU Post`, `CE Pre`,
`CE Post`; Spalten sind die MCCB-Untertests plus Gesamtwert). Ziel ist
`post (after 4-week training)`, Gold ist die Zeile **TAU Post**.

Read-only geprüft: In **allen 14 Komparator-Zellen** (Mittelwert und SD in sieben
Records) stammt der Wert aus der Zeile **`FAT Pre`** — also aus dem
Interventionsarm, *vor* dem Training:

| Record | Feld | Modell | Gold | Zeile im Artikel |
|---|---|---:|---:|---|
| 289 | `comparator_mean` / SD | 39,5 / 10,6 | 48,2 / 12,3 | FAT Pre |
| 290 | `comparator_mean` / SD | 33,6 / 11,5 | 41,3 / 10,1 | FAT Pre |
| 291 | `comparator_mean` / SD | 42,8 / 12,8 | 46,5 / 9,8 | FAT Pre |
| 292 | `comparator_mean` / SD | 44,6 / 10,2 | 50,8 / 12,1 | FAT Pre |
| 293 | `comparator_mean` / SD | 46,2 / 9,9 | 47,3 / 10,4 | FAT Pre |
| 294 | `comparator_mean` / SD | 44,5 / 10,7 | 46,5 / 9,8 | FAT Pre |
| 295 | `comparator_mean` / SD | 39,3 / 11,1 | 42,8 / 11,7 | FAT Pre |

Die Spalte (der jeweilige Untertest) ist also richtig getroffen, die **Zeile**
falsch: Das Modell nimmt den Interventionsarm und den Pre-Zeitpunkt, obwohl es
den Komparator zum Post-Zeitpunkt berichten soll. Mittelwert und SD stammen aus
derselben Zelle, sind also in sich stimmig — der Fehler ist nicht als
Zahlenverwechslung, sondern nur über die Armzuordnung sichtbar.

Zwei weitere Zellen derselben Gruppe liegen daneben: `291`
`intervention_standard_deviation` 14 statt 12,8 und `295`
`intervention_standard_deviation` 10,4 statt 11,1. Ihre Zuordnung ist unsicher,
weil die Werte mehrfach im Text vorkommen (die Suche nennt `FAT Pre` bzw.
`TAU Pre`). Reproduzierbar mit `analyse_mccb_armzeile.py`: 15 der 16
abweichenden Zellen liegen laut nächstem Zeilenkopf in `FAT Pre`, eine in
`TAU Pre`.

Das sind 14 der 25 falschen Zellen des Laufs. Ein Prompt-Zusatz, der die
Armzeile und den Zeitpunktzeilen-Kopf ausdrücklich verlangt (ähnlich der
Gruppengrößen-Zeile, aber opt-in), wäre der direkte Gegenhebel.

## 7. Überzählige Zellen

10 Zellen ohne Gold: `*_events` 5, `*_mean` 4, `*_standard_deviation` 1,
Gruppengrößen 2. Sie zählen in der Precision 0,7394 als Fehler und erscheinen in
der Klassentabelle als `ohne Gold`.

## 8. Grenzen

- Ein Modell, ein Lauf, kein Vergleichslauf auf denselben 76 Records.
- 243 Zellen Testbasis; ein Teil der Auslassungen ist Gold-Eigenschaft
  (Gruppengrößen ohne Zeitpunktbezug).
- Die zwei Timeout-Records fehlen in jeder Kennzahl.
- Die Armzeilen-Analyse ist eine Zuordnung über den nächsten Zeilenkopf im
  Text; sie belegt die Tendenz, ist aber kein vollständiger Tabellenparser.
