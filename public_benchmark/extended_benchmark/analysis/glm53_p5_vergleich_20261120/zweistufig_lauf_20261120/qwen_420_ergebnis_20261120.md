# qwen3.5-397b auf yun2024:420: Antwort und Treffer, wo glm-5.3 zweimal abbricht (20.11.2026)

Ein freigegebener Aufruf, die Fortsetzung der Kontrolle auf dem schwersten
gemessenen Record. Modell `gwdg/qwen3.5-397b-a17b` (`qwen`), Satz-Locator
(`stage1_satz`), Budget 16.000, Temperatur 0, Lesezeit 900 s. Rohdaten:
`predictions_satz_420_qwen_16000.jsonl`, Start aus dem Repo-Wurzelverzeichnis
(die Konfiguration wird relativ zum Arbeitsverzeichnis geladen).

## Der entscheidende Punkt: identischer Prompt

| Groesse | glm-5.3 | qwen3.5-397b |
|---|---|---|
| Prompt-Zeichen | 7.313 | **7.313** |
| Prompt-SHA256 | `f7bc1167...b5b2` | **`f7bc1167...b5b2`** |
| Ausschnitt | 6.000 Zeichen (Start 15.500 von 26.274) | derselbe |
| Budget | 16.632 | 16.000 |
| Ergebnis | **abgebrochen**, 0 Zeichen | **ok**, 2 Locators |

Der Prompt ist byte-identisch (gleicher SHA256). Zwischen Abbruch und Antwort
steht in diesem Vergleich nur das Modell.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **7.728** von 16.000 |
| Reasoning-Zeichen | 27.932 |
| Inhalt | 1.120 Zeichen, **2 Locators** |
| Dauer | 150,45 s |
| Armzuordnung | je ein Locator fuer `intervention` und `comparator` |
| `satz_im_ausschnitt` | **True** fuer beide |
| `found` | **True** fuer beide |
| `timepoint` | leer |

Beide Locators tragen denselben Satz, woertlich aus dem Ausschnitt:

> Regarding quantitative assessment of contour sharpness, the mean values for
> the two assessed interfaces were significantly smaller in MR images obtained
> with the short-bore scanner than with the open MR scanner, thus indicating an
> improved contour sharpness (0.95 [SD, 0.24] versus 1.43 [SD, 0.48] and 0.83
> [SD, 0.22] versus 1.32 [SD, 0.51]; *P*<0.0001).

Das ist genau die Regel der Aufgabe: „If one sentence reports the values for both
arms, return that sentence for both." Der Satz enthaelt alle vier Werte, die das
Gold fuer Mittelwert und Streuung fuehrt (`0.95`, `0.24`, `1.43`, `0.48`), und
zusaetzlich das zweite, vom Gold nicht genutzte Schnittstellenpaar
(`0.83`/`0.22` gegen `1.32`/`0.51`). Die Abschnittsmarke, die das Modell als
`caption` angibt (`Quantitative Analysis`), steht woertlich im Ausschnitt
(geprueft, als Zwischenueberschrift `## Quantitative Analysis`).

`timepoint` bleibt leer. Das ist hier **kein Fehler des Modells**: der Record
traegt keinen Zeitpunkt (alle sechs Goldzellen haben `timepoint = null`, der
Kontext nennt keinen), und der Satz berichtet auch keinen. Bei 119 hat dasselbe
Modell den gedruckten Zeitpunkt korrekt mitgeliefert.

## Was der Treffer wert ist - und was nicht

Von den sechs Goldzellen kann der zitierte Satz hoechstens vier stuetzen:

| Goldzelle | Wert | im zitierten Satz? | im Ausschnitt gedruckt? |
|---|---:|---|---|
| `intervention_mean` | 0,95 | **ja** | ja |
| `intervention_standard_deviation` | 0,24 | **ja** | ja |
| `comparator_mean` | 1,43 | **ja** | ja |
| `comparator_standard_deviation` | 0,48 | **ja** | ja |
| `intervention_group_size` | 18 | **nein** | ja, aber nur als `n = 18` im Kopf der **qualitativen** Tabelle (`**T1w sagittal**`) |
| `comparator_group_size` | 21 | **nein** | ja, dort als `n = 21` |

Die beiden Gruppengroessen stehen also im Ausschnitt, aber nicht in dem Satz, den
Stufe 1 als Belegstelle waehlt. Ein Stufe-2-Aufruf auf dieser Belegstelle kann
deshalb 4 von 6 Zellen erreichen, nicht 6 von 6 - dieselbe Deckelung wie bei 119
(2 von 4), nur aus einem anderen Grund: dort fehlten die Werte im Ausschnitt,
hier fehlen sie in der gewaehlten Belegstelle.

Zwei weitere Beobachtungen am Ausschnitt:

- Der Begriff „contour sharpness" steht zweimal mit **verschiedenen Zahlen** im
  Ausschnitt: in der qualitativen Tabelle als Likert-Note (`2.2 (0.9)` gegen
  `3.8 (0.5)`), im Fliesstext als quantitative Messung (`0.95 [SD, 0.24]` gegen
  `1.43 [SD, 0.48]`). Das Gold meint die quantitative Fassung. qwen waehlt den
  Fliesstextsatz mit dem Abschnittslabel `Quantitative Analysis` - die
  Bindungsentscheidung, an der die P5-Laeufe scheiterten, ist hier also
  getroffen und nicht geraten.
- Der Satz traegt zwei gleichberechtigte Schnittstellenpaare. Das Gold nimmt das
  erste. Stufe 1 muss diese Wahl nicht treffen, weil der Satz beide enthaelt;
  Stufe 2 muss sie treffen. Genau die Lage, an der die Zeilenlabel-Fassung auf
  420 mit `glm-5.3` dreimal abbrach (16.632 Tokens, 66.006 bzw. 69.175
  Reasoning-Zeichen, 0 Zeichen Inhalt).

## Was der Aufruf beantwortet

**Der Modellwechsel traegt auf 420 inhaltlich, nicht nur verfuegbarkeitstechnisch.**
Auf dem identischen Prompt liefert `glm-5.3` nichts und `qwen3.5-397b` die
richtige Belegstelle mit allen vier erreichbaren Werten. Damit steht die
qwen-Reihe auf Stufe 1 bei zwei Treffern und einem falschen Negativ:

| Record | Modell | Goldzellen | Goldwerte im Ausschnitt | qwen-Antwort | Bewertung |
|---|---|---:|---:|---|---|
| `yun2024:421` | qwen | 6 | 6/6 | `found: false`, ein Locator | **falsches Negativ** |
| `yun2024:420` | qwen | 6 | 6/6 | zwei Locators, Satz woertlich, 4/6 Werte im Satz | **Treffer** |
| `yun2024:119` | qwen | 4 | 2/4 erreichbar | zwei Locators, Satz woertlich, 2/4 Werte | **Treffer** |

Die beiden 6/6-Records (420, 421) aus derselben Publikation (`PMC3877023`)
trennen sich damit nicht mehr am Modell - beide antworten -, sondern an der
Entscheidung `found` selbst: auf 420 richtig positiv, auf 421 falsch negativ.
Das ist eine andere Fehlerklasse als der Abbruch und mit einem Aufruf je Record
nicht weiter aufloesbar.

**Fuer die P5-Bilanz aendert der Treffer allein noch nichts.** `bilanz_p5` zaehlt
jedes Goldfeld ohne passende Vorhersagezelle als FN; Stufe 1 liefert keine
Zellen. Der Gewinn ist erst zu messen, wenn Stufe 2 auf dieser Belegstelle
laeuft - und dort sind fuer 420 hoechstens 4 der 6 Zellen erreichbar.

## Kosten

Gemessene Completion-Tokens: 130.827 (bisherige Reihe) + 7.728 = **138.555**.
Eingabetokens sind nicht budgetiert und hier nicht enthalten; Fehlversuche ohne
Tokenzaehlung sind nicht mitgezaehlt.

## Grenzen

- **n = 1** Aufruf auf 420 mit qwen. Eine Wiederholung kann anders ausgehen; die
  Streuung des Modells auf einem Record ist in dieser Reihe nicht gemessen.
- Die Budgets sind nicht gleich (glm 16.632, qwen 16.000). qwen blieb mit 7.728
  deutlich darunter, glm verbrauchte seines vollstaendig - das Budget war hier
  nicht der begrenzende Faktor.
- Der Treffer ist auf Stufe 1 gemessen: die Belegstelle ist belegt, die Zellen
  sind nicht extrahiert. Ein Stufe-2-Aufruf auf diesem Satz steht aus.
- Die Aussage „Modell ist der Faktor" gilt fuer **einen** Record mit identischem
  Prompt-SHA256. Auf 421 antwortet qwen falsch; der Modellwechsel ist kein
  Metrikgewinn per se.
