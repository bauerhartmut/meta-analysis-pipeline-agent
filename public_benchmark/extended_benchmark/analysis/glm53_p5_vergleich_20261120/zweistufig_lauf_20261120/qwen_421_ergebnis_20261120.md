# qwen3.5-397b auf yun2024:421: kein Abbruch, aber ein begruendetes found:false (20.11.2026)

Ein freigegebener Aufruf. Modell `gwdg/qwen3.5-397b-a17b` (`qwen`), Satz-Locator
(`stage1_satz`), Budget 16.000, Temperatur 0, Lesezeit 900 s, Prompt 7.311
Zeichen - derselbe Prompt wie im glm-Lauf auf 421, nur anderes Modell.
Rohdaten: `predictions_satz_421_qwen_16000.jsonl`.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **10.686** von 16.000 |
| Reasoning-Zeichen | 41.200 |
| Inhalt | 199 Zeichen, **1 Locator** |
| Dauer | 212,25 s |
| Locator | `arm = intervention`, alle Label leer, **`found = false`** |

Die Antwort im Wortlaut:

```json
{"locators": [{"arm": "intervention", "satz": "", "zeilenlabel": "",
  "spaltenkopf": "", "caption": "", "timepoint": "", "found": false}]}
```

## Was das beantwortet

**Der Abbruch ist modellspezifisch.** Derselbe Prompt, derselbe Ausschnitt,
dasselbe Ziel: `glm-5.3` verbraucht viermal das volle Budget ohne ein Zeichen
Inhalt, `qwen3.5-397b` antwortet in 10.686 Tokens mit `stop`. Die Denkschleife
ist eine Eigenschaft des Modells auf diesem Text, nicht des Textes allein und
nicht des Schemas.

**Aber die Antwort ist keine Loesung.** `found: false` ist hier falsch: die
gesuchten Werte stehen im Ausschnitt (6/6 Goldwerte im Prompt, der Satz mit
0,95/0,24 gegen 1,43/0,48 ist gedruckt). Aus dem Abbruch ist damit ein
**False Negative** geworden - messbar besser, weil es eine Aussage gibt, aber
inhaltlich nicht richtig. Zweite Auffaelligkeit: das Modell liefert nur einen
Locator (`intervention`) statt zwei, obwohl der Prompt beide Arme verlangt.

| Modell | Tokens | Reasoning | Ergebnis auf demselben Prompt |
|---|---:|---:|---|
| `glm-5.3` | 16.632 (von 16.632) | 69.265 | abgebrochen, 0 Zeichen |
| **`qwen3.5-397b`** | **10.686 (von 16.000)** | **41.200** | **ok, `found: false`** |

Auch qwen rechnet viel (41.200 Reasoning-Zeichen fuer 199 Zeichen Ausgabe) - der
Text ist fuer beide Modelle schwer, qwen bricht die Schleife aber ab.

## Nebenarbeit: Timeout-Verdrahtung an einer Stelle

Beide Runner trugen denselben Monkeypatch fuer die Lesezeit dupliziert. Der
steht jetzt in `../aufruf_20261120.py` als Contextmanager `lesezeit(sekunden)`;
`zweistufig_satz_20261120.py` und `zweistufig_lauf_20261120.py` benutzen ihn:

```python
with lesezeit(args.timeout):
    antwort = rx.call(modell, prompt, key, base, attempts=3)
```

Unveraendert bleibt: `rx.call` behaelt seine Retry-Logik, getauscht wird nur die
Lesezeit je HTTP-Versuch (`rx._call_once`, Standard 300 s). Zusaetzlich hat der
Satz-Runner jetzt `--model` (Auswahl aus `rx.MODELS`), weil er zuvor fest auf
`glm` stand; das Feld `model` in der Zeile traegt den Namen.

Geprueft: `py_compile` fuer alle drei Dateien, Trockenlauf beider Runner
(`--dry-run`), danach der echte Lauf oben.

## Kosten

Gemessene Completion-Tokens: 113.905 (bisherige Reihe) + 10.686 = **124.591**.

## Grenzen

- **n = 1** je Zelle; ein Modellvergleich mit je einem Aufruf. Ob qwen bei
  Wiederholung wieder `found: false` sagt, ist nicht gemessen.
- Der Vergleich ist nicht budgetgleich (16.632 gegen 16.000 Tokens). Beide
  Budgets liegen ueber dem, was qwen brauchte (10.686), also war das Budget
  nicht der begrenzende Faktor; glm verbrauchte sein Budget vollstaendig.
- `found: false` ist hier inhaltlich falsch, aber als Modellausgabe korrekt
  protokolliert - der Bericht bewertet sie nicht als Treffer.
- Ob ein drittes Modell (`qwen30`, `deepseek`) anders antwortet, ist offen.
