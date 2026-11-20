# Stufe 2 auf dem 420er Satz: vier Zellen, keine falsche (20.11.2026)

Ein freigegebener Aufruf, der Abschluss der Kette auf `yun2024:420`. Modell
`gwdg/qwen3.5-397b-a17b` (`qwen`), Stufe 2 auf dem Satz aus
`predictions_satz_420_qwen_16000.jsonl`, Budget **4.000**, Temperatur 0,
Lesezeit 900 s. Rohdaten: `predictions_stufe2_satz_420_qwen_4000.jsonl`.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **2.590** von 4.000 (64,8 %) |
| Reasoning-Zeichen | 7.938 |
| Inhalt | 802 Zeichen, **4 Zellen** |
| Dauer | 124,12 s |
| Bewertung (`bilanz_p5`) | **4 TP / 0 FP / 2 FN**, Precision 1,00, Recall 0,667, **F1 0,800** |
| Zellen im Ausschnitt belegt | 4 von 4 |

Die vier gelesenen Zellen, alle woertlich im Ausschnitt gedruckt:

| Feld | Wert | Gold | Treffer |
|---|---:|---:|---|
| `intervention_mean` | 0,95 | 0,95 | ja |
| `intervention_standard_deviation` | 0,24 | 0,24 | ja |
| `comparator_mean` | 1,43 | 1,43 | ja |
| `comparator_standard_deviation` | 0,48 | 0,48 | ja |

Die beiden FN sind die Gruppengroessen 18 und 21. Sie stehen nicht in der
Belegstelle, sondern nur als `n = 18` / `n = 21` im Kopf der qualitativen
Tabelle (`**T1w sagittal**`); der Stufe-2-Prompt liest ausschliesslich den Satz
und laesst nicht gedruckte Zellen aus. 4 von 6 Zellen ist damit die Obergrenze
dieser Belegstelle, nicht ein Fehler des Aufrufs.

## Die Bindungsentscheidung ist getroffen

Der Satz nennt zwei Schnittstellenpaare:

> … (0.95 [SD, 0.24] versus 1.43 [SD, 0.48] and 0.83 [SD, 0.22] versus 1.32
> [SD, 0.51]; *P*<0.0001).

Das Gold meint das **erste** Paar. Das Modell liest das erste Paar; das zweite
erscheint in keiner Zelle (0 FP, 0 ueberzaehlige). Damit ist die Stelle, an der
`glm-5.3` in drei Aufrufen das Budget ohne Ausgabe verbrauchte, mit demselben
Ausschnitt in einem Aufruf von 2.590 Tokens geloest - Belegstelle und
Paarwahl.

## Die Kette auf 420 im Vergleich

| Stufe | Modell | Aufrufe | Ergebnis |
|---|---|---:|---|
| 1 | `glm-5.3` | 3 (Zeilenlabel, Zeilenlabel + Zusatz, Satz-Locator) | je **abgebrochen**, volles Budget, 0 Zeichen |
| 1 | `qwen3.5-397b` | 1 | ok, 7.728 Tokens, 2 Locators, Satz woertlich |
| 2 | `qwen3.5-397b` | 1 | ok, 2.590 Tokens, 4 Zellen, **4 TP / 0 FP / 2 FN** |

Auf 523 sieht dieselbe Kette mit `glm-5.3` fast identisch aus (Stufe 1: 2.342
Tokens, Stufe 2: 268 Tokens, 4 TP / 0 FP / 2 FN, F1 0,800). Beide Records
enden also bei demselben F1 - nicht weil die Records gleich sind, sondern weil
in beiden Faellen genau die zwei nicht im Satz gedruckten Zellen fehlen.

## Kosten

Gemessene Completion-Tokens: 138.555 (bisherige Reihe) + 2.590 = **141.145**.
Eingabetokens sind nicht budgetiert und hier nicht enthalten; Fehlversuche ohne
Tokenzaehlung sind nicht mitgezaehlt.

## Grenzen

- **n = 1** Aufruf. Die Streuung des Modells auf dieser Belegstelle ist nicht
  gemessen; die Wahl des ersten Paares kann in einer Wiederholung anders
  ausfallen. Der Prompt sagt sie an („the target is the FIRST evaluation only"),
  sie ist also nicht frei geraten.
- Das Budget 4.000 ist **keine** gemessene Grenze, sondern eine Setzung; der
  Aufruf blieb mit 2.590 Tokens darunter. Der Vergleich mit 523 (Budget 16.632,
  268 Tokens) zeigt, dass das Budget hier nicht bindet.
- Der F1 0,800 ist ein Record-Wert, keine Aussage ueber die P5-Auswahl. Die
  beiden FN sind aus der Belegstelle nicht erreichbar; ein perfekter Stufe-2-
  Aufruf auf genau diesem Satz kann hier nicht ueber 4/6 hinauskommen.
- Der `arm_hinweis` des Prompts („short-bore scanner" gegen „open MR scanner")
  ist aus dem zitierten Satz abgeleitet, nicht aus dem Gold.
