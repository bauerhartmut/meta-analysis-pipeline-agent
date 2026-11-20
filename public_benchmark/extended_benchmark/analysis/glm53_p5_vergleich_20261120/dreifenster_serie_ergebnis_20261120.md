# Dreifenster-Serie auf 30, 673 und 674 (20.11.2026)

Drei disjunkte 2.000er-Stuecke je Record, ausgewaehlt mit derselben blinden
Score-Regel wie `mehrfach_3x2000` (Abweichungspruefung ueber 699 Records: 0).
Modell `gwdg/qwen3.5-397b`, Budget 16.000, Lesezeit 420 s, je ein Aufruf.
Abbruchkriterium: `content_chars == 0` oder `finish_reason == length`.

## Ergebnis je Record

| Record | Stuecke | Goldzeile | Goldzeile im Stueck | Goldwerte naiv | Status | Tokens | Zeit | Locators | Goldmittel im Satz |
|---|---|---:|---|---:|---|---:|---:|---:|---:|
| `yun2024:30` | [(750, 2750), (5500, 7500), (18750, 20750)] | 8385 | **nein** | 2/6 | ok | 5781 | 266.53 s | 2 | 0 |
| `yun2024:673` | [(0, 2000), (9250, 11250), (25750, 27750)] | 19505 | **nein** | 4/6 | ok | 6543 | 371.55 s | 2 | 0 |
| `yun2024:674` | [(0, 2000), (9250, 11250), (25750, 27750)] | 20177 | **nein** | 4/6 | ok | 9314 | 351.92 s | 2 | 0 |

Kosten: **21638** Completion-Tokens, 990.0 s. Records, deren
zitierter Satz das **Goldmittel** traegt: **0 von 3**.
Einzelne Goldwerte im Satz sind kein Treffer: auf 673/674 ist die 23.0 die
Standardabweichung des Goldes, im Satz steht aber `23 % control`.

## Was die Modelle zitiert haben

### yun2024:30

- **intervention**, timepoint 'week 52', Zahlen [0.001, 1.0, 2.1, 6.4, 36.0, 52.0, 200.0, 400.0]: Mean changes from baseline in the SF-36 Mental Component Summary (MCS) at week 52 for CZP 200 mg and 400 mg plus MTX, and PBO plus MTX were 6.4, 6.4 and 2.1, respectively (*P* < 0.001).
- **comparator**, timepoint 'week 52', Zahlen [0.001, 1.0, 2.1, 6.4, 36.0, 52.0, 200.0, 400.0]: Mean changes from baseline in the SF-36 Mental Component Summary (MCS) at week 52 for CZP 200 mg and 400 mg plus MTX, and PBO plus MTX were 6.4, 6.4 and 2.1, respectively (*P* < 0.001).

### yun2024:673

- **intervention**, timepoint '', Zahlen [23.0, 24.0, 36.0]: Although clusters in the provider arm tended to have higher proportions of people treated according to guidelines (36% in provider, 23% control, 24% pr
- **comparator**, timepoint '', Zahlen [23.0, 24.0, 36.0]: Although clusters in the provider arm tended to have higher proportions of people treated according to guidelines (36% in provider, 23% control, 24% pr

### yun2024:674

- **comparator**, timepoint '', Zahlen [23.0, 24.0, 36.0]: Although clusters in the provider arm tended to have higher proportions of people treated according to guidelines (36% in provider, 23% control, 24% pr
- **intervention**, timepoint '', Zahlen [23.0, 24.0, 36.0]: Although clusters in the provider arm tended to have higher proportions of people treated according to guidelines (36% in provider, 23% control, 24% pr

## Befund

- Die Goldzeile liegt in **allen drei** Faellen zwischen den Stuecken:
  yun2024:30 bei Zeichen 8385 (Stuecke [(750, 2750), (5500, 7500), (18750, 20750)])
  yun2024:673 bei Zeichen 19505 (Stuecke [(0, 2000), (9250, 11250), (25750, 27750)])
  yun2024:674 bei Zeichen 20177 (Stuecke [(0, 2000), (9250, 11250), (25750, 27750)])
- Die vorab gemessene Abdeckung (2/6, 4/6, 4/6) war teils zufaellig: die
  Treffer auf 673/674 sind `23 % drug stores`, `32 % facilities`, `26 % education`
  und nicht die Goldzeile `36.4 % (32)` bzw. `22.6 % (23)`.
- Das Modell antwortet in allen drei Faellen mit einem Satz zum richtigen
  Outcome, aber mit einer anderen Kennzahl: auf 30 mit der Aenderung 6,4/6,4/2,1
  statt der Tabelle 38,1 (9,5) / 31,5 (7,4); auf 673/674 mit `36 % provider,
  23 % control, 24 % ...` statt `36.4 % (32)` / `22.6 % (23)`.
- Damit misst die Serie erneut die Fensterwahl, nicht die Bindung des Modells:
  die richtige Zeile war in keinem Aufruf sichtbar.

## Blinde Tabellenregel als Gegenprobe

| Record | Tabellenfenster ab | Goldwerte darin |
|---|---:|---:|
| `yun2024:30` | 7641 | 6/6 |
| `yun2024:673` | 23937 | 4/6 |
| `yun2024:674` | 23937 | 3/6 |

Die Regel nimmt im Ergebnisteil das 2.000er-Fenster mit den meisten
Tabellenmerkern (`n =`, `mean`, `SD`, `CI`, `Table`, `%`). Sie erreicht auf 30
alle sechs Werte, auf 673/674 vier bzw. drei, weil dort mehrere Tabellen
konkurrieren. Sie ist blind und braucht kein Goldwissen.

## Empfehlung

Keine weitere Serie mit Prosa-Fenstern. Vor dem naechsten Aufruf ein
Tabellenfenster plus ein Prosa-Stueck kombinieren und offline pruefen, ob
die Goldzeile dann in beiden Records mit sechs Werten liegt; erst danach
einen Aufruf auf 30 mit diesem Prompt.
