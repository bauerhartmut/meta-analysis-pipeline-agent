# Stufe 2 auf dem 119er Satz bricht am 4.000er Budget ab (20.11.2026)

Ein freigegebener Aufruf. Modell `gwdg/qwen3.5-397b-a17b` (`qwen`), Stufe 2 auf
dem Satz aus `predictions_satz_119_qwen_16000.jsonl`, Budget **4.000**,
Temperatur 0, Lesezeit 900 s. Rohdaten:
`predictions_stufe2_satz_119_qwen_4000.jsonl`.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **abgebrochen** (`finish_reason = length`) |
| Completion-Tokens | **4.000** (Budget vollstaendig verbraucht) |
| Reasoning-Zeichen | **15.994** |
| Inhalt | **0 Zeichen**, 0 Zellen (`parse_fehler = leer`) |
| Dauer | 97,44 s |
| Prompt | 7.668 Zeichen (Ausschnitt 6.000, Regelteil 1.668), SHA256 `0e0c102c...9291` |
| Bewertung | 0 TP / 0 FP / 4 FN — das ist der Abbruch, keine Messung des Satzes |

Das Abbruchkriterium (`content_chars == 0` oder `finish_reason == "length"`) ist
erfuellt, es gab keinen zweiten Versuch.

## Was der Aufruf beantwortet - und was nicht

**Nicht beantwortet:** ob der Satz die zwei erreichbaren Zellen (70 / 15,4) als
`mean` traegt. Der Lauf hat keinen Text produziert; ueber den Inhalt der
Belegstelle sagt er nichts. Die 4 FN in der Zeile sind die mechanische Folge des
Abbruchs, nicht ein Befund ueber die Extraktion.

**Beantwortet:** das 4.000er Budget ist fuer diesen Record zu knapp. Die
Denkspur ist doppelt so lang wie die des erfolgreichen 420er Stufe-2-Aufrufs:

| Aufruf | Satz | Budget | Verbraucht | Reasoning-Zeichen | Inhalt |
|---|---|---:|---:|---:|---|
| Stufe 2, `yun2024:420`, qwen | 354 Zeichen | 4.000 | 2.590 | 7.938 | 4 Zellen |
| **Stufe 2, `yun2024:119`, qwen** | **475 Zeichen** | **4.000** | **4.000 (voll)** | **15.994** | **0 Zeichen** |
| Stufe 1, `yun2024:119`, qwen | - | 16.000 | 6.236 | 23.030 | 2 Locators |

Das Budget war eine Setzung aus dem 420er Messpunkt, keine gemessene Grenze; sie
traegt auf 119 nicht. Dasselbe Modell hat auf demselben Record in Stufe 1
6.236 Tokens gebraucht, um zu einem Ergebnis zu kommen - ein 4.000er Budget
liegt darunter.

## Einordnung in die Reihe

| Record | Stufe 1 | Stufe 2 | Kette |
|---|---|---|---|
| `yun2024:523` | glm, 2.342 Tokens, ok | glm, 268 Tokens, 4 TP/0 FP/2 FN | **geschlossen** |
| `yun2024:420` | qwen, 7.728 Tokens, ok | qwen, 2.590 Tokens, 4 TP/0 FP/2 FN | **geschlossen** |
| `yun2024:119` | qwen, 6.236 Tokens, ok | qwen, 4.000 Tokens, **abgebrochen** | offen, Budget |
| `yun2024:421` | qwen, 10.686 Tokens, `found: false` | - | offen, `found`-Frage |

Der Abbruch ist die erste Stelle der Reihe, an der nicht das Modell und nicht
der Prompt, sondern die Budgetsetzung selbst der begrenzende Faktor war.

## Kosten

Gemessene Completion-Tokens: 141.145 (bisherige Reihe) + 4.000 = **145.145**.
Eingabetokens sind nicht budgetiert und hier nicht enthalten; Fehlversuche ohne
Tokenzaehlung sind nicht mitgezaehlt.

## Grenzen

- **n = 1** Aufruf. Ob 8.000 Tokens reichen, ist nicht gemessen; die Begruendung
  dafuer stuetzt sich auf zwei Messungen desselben Records (6.236 Tokens in
  Stufe 1) und auf 15.994 Reasoning-Zeichen ohne Ausgabe bei 4.000.
- Der Prompt ist gegenueber 420 nur um 126 Zeichen laenger; der Unterschied in
  der Denkspur stammt also nicht aus dem Prompt-Bau, sondern aus dem Satz bzw.
  dem Record. Woraus genau, ist mit einem Aufruf nicht aufloesbar.
- Der `arm_hinweis` nennt „mild cooling" gegen „no cooling". Diese Zuordnung ist
  aus dem Satz und dem Kontext abgeleitet, nicht aus dem Gold geprueft; bei
  einem Satz mit drei Vergleichsgruppen („no cooling vs deep cooling and mild
  cooling vs deep cooling") ist sie der naechste moegliche Fehlerpunkt.
