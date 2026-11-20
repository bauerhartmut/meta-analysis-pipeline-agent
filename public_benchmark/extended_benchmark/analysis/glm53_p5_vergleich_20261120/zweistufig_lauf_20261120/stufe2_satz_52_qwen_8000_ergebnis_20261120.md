# Stufe 2 auf dem 52er Satz: zwei Zellen, keine Armvertauschung (20.11.2026)

Ein freigegebener Aufruf. Modell `gwdg/qwen3.5-397b-a17b` (`qwen`), Stufe 2 auf
dem Satz aus `predictions_satz_52_qwen_16000.jsonl`, Budget **8.000**,
Temperatur 0, Lesezeit 900 s. Rohdaten:
`predictions_stufe2_satz_52_qwen_8000.jsonl`.

## Vorab offline: wie die Arme gedruckt sind

Der Satz nennt **keine Armnamen** und die Woerter `before`/`after` kommen nicht
vor. Die Zuordnung steckt allein in der Reihenfolge und einem Richtungswort:

| Stelle | Text |
|---|---|
| Position 97 | „between the **pre-** and postintervention periods" |
| Position 195/200 | „slightly upward trend **from** 11.5%" |
| Position 206/209 | „**to** 13.6% (*P* = 0.405) **postintervention**." |

Damit ist gedruckt: 11,5 % gehoert zum **Vorher** (comparator), 13,6 % zum
**Nachher** (intervention). Der Kontext sagt dasselbe („After restraint reduction
program" gegen „Before restraint reduction program"), das Gold auch
(`intervention_mean` = 13,6, `comparator_mean` = 11,5). Standardabweichungen
(0,07/0,13) und Gruppengroessen (562/463) stehen nicht im Ausschnitt - hoechstens
zwei Zellen sind erreichbar.

## Anpassung am Prompt (notwendig, nicht kosmetisch)

Der bisherige Stufe-2-Prompt unterstellt „each arm is reported twice … the target
is the FIRST evaluation only". Das passt auf 523 und 420 (zwei Wertepaare je
Arm), nicht auf 52 (ein Wert je Arm). Ein Aufruf mit dem alten Text haette zwei
Werte als „erstes Paar" des einen Arms lesen koennen.

Deshalb hat der Runner jetzt `--paare {1,2}`; Vorgabe 2. Die bestehenden Prompts
sind **byte-gleich** geblieben (geprueft ueber den SHA256 des Prompts):

| Record | Prompt-SHA vorher = nachher |
|---|---|
| `yun2024:523` (Vorgabe) | `f6753fd3422122908cde66f4ed49f367f8957da0b03cacae914717d35a36c840` |
| `yun2024:420` | `977e817a6c235456e8185d62ea824185fe0c9c9047ef00498a8785278d09158f` |

Der `arm_hinweis` nennt nur die gedruckten Periodenbezeichnungen und die
Kontextnamen; **welche Zahl zur welchen Periode gehoert, sagt der Prompt nicht**
- das muss das Modell aus „from … to …" lesen.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **2.827** von 8.000 (35,3 %) |
| Reasoning-Zeichen | 10.082 |
| Inhalt | 408 Zeichen, **2 Zellen** |
| Dauer | 82,64 s |
| Prompt | 7.445 Zeichen, SHA256 `42607949...edfb`, `wertepaare_je_arm = 1` |
| Bewertung (`bilanz_p5`) | **2 TP / 0 FP / 4 FN**, Precision 1,00, Recall 0,333, F1 0,500 |

| Feld | Wert | Gold | Treffer |
|---|---:|---:|---|
| `intervention_mean` | 13,6 | 13,6 | ja |
| `comparator_mean` | 11,5 | 11,5 | ja |

**Keine Armvertauschung.** Das Modell liest „from 11.5% to 13.6%
postintervention" richtig herum: der Endwert der Entwicklung gehoert zur
Intervention. Es erfindet keine Zelle fuer die fehlenden Standardabweichungen und
keine fuer die Gruppengroessen (0 FP) - die 4 FN sind die vier nicht gedruckten
Zellen, nicht Fehlgriffe.

Damit ist der Fehlertyp, der 72 der 121 FN auf den beantworteten P5-Records
erklaert (falsche Armzuordnung), auf diesem Satz **nicht** aufgetreten.

## Die Kette auf 52

| Stufe | Modell | Ergebnis |
|---|---|---|
| 1 | `qwen3.5-397b` | ok, 7.400 Tokens, 2 Locators, Satz woertlich, `intervention = postintervention` |
| 2 | `qwen3.5-397b` | ok, 2.827 Tokens, 2 Zellen, **2 TP / 0 FP / 4 FN** |
| P5-Vergleich | `glm-5.3`, 24.000, Volltext | **abgebrochen**, 95.546 Reasoning-Zeichen, 0 Zeichen |

Die beiden qwen-Schritte zusammen kosten 10.227 Tokens. Der Vergleich mit dem
P5-Lauf ist nicht sauber (dort Volltext bis 45.000 Zeichen, hier 6.000), zeigt
aber, dass auf diesem Record die knappe Fassung zu Zellen fuehrt, wo die
groessere abbrach.

## Was das fuer die Breite bedeutet (offline nachgezaehlt)

Alle 33 Abbrueche, Goldwerte im 6.000er-Fenster:

| Goldwerte im Ausschnitt | Records |
|---:|---:|
| 0 | **21** |
| 1 | 7 |
| 2 | 1 |
| 3 | 2 |
| 4 | 2 |

**Nur 5 der 33** haben mindestens zwei Goldwerte im Fenster: 420 (4/6), 421
(4/6), 525 (3/4), 523 (3/4) und 52 (2/6). Vier davon sind jetzt gemessen. Eine
qwen-Serie ueber die restlichen Abbrueche wuerde bei 21 Records 0 erreichbare
Werte messen - sie wuerde die Fensterwahl messen, nicht das Modell.

## Kosten

Gemessene Completion-Tokens: 158.444 (bisherige Reihe) + 2.827 = **161.271**.
Eingabetokens sind nicht budgetiert und hier nicht enthalten.

## Grenzen

- **n = 1** Aufruf auf 52. Die Zuordnung ist in einem Aufruf richtig; die
  Streuung des Modells auf diesem Satz ist nicht gemessen.
- F1 0,500 ist durch die Belegstelle gedeckelt: 4 der 6 Goldzellen sind im
  Ausschnitt nicht gedruckt. Der Wert ist kein Modell-, sondern ein
  Abdeckungsmass dieses Ausschnitts.
- Prompt-Aenderung: `--paare 1` ist eine neue Fassung. Sie ist fuer 52 passend,
  aber nur hier gemessen; auf 523/420 wurde sie nicht verwendet (Vorgabe 2, dort
  byte-gleich).
- Der Satz sagt „no significant difference", das Gold fuehrt die Prozentsaetze
  als Arm-Mittelwerte. Die Zellen sind damit annotationstreu, nicht
  wirkungsgrossentreu (Befund 4).
