# Gold-Konflikt-Kandidaten unter den armgemischten Records (15.11.2026)

Grundlage: `fallback_eval.json` (Lauf `yun_test186_v6_20261115`) nennt sieben
Records mit abweichenden Zeitpunkten je Arm. `zahlen_in_zeile()` liefert nur
einen Hinweis (bei gefalteten Tabellen versagt es); jeder Fall wurde deshalb am
Tabellentext geprüft. Ergebnis: **fünf Gold-Konflikte, zwei legitime Rückfälle**.

## 1. PMC3546023 — fünf Records, ein Tabellenmuster

Die Tabelle hat vier Spalten (Non-smokers placebo n = 27, non-smokers palmvitee
n = 29, smokers placebo n = 28, smokers palmvitee n = 30) und die Zeilen
`0`, `12`, `24`. Gold nimmt in allen fünf Records **zwei Zeitpunkte derselben
Spalte** und etikettiert sie als zwei Arme:

| Record | Gold intervention | Gold comparator | Beleg im Text | Befund |
|---|---|---|---|---|
| `yun2024:75` | 11.97 (n = 29) | 13.72 (n = 29) | palmvitee-Spalte, Zeile 0 und Zeile 24 | Baseline gegen Woche 24 **desselben Arms** |
| `yun2024:76` | 14.06 (n = 30) | 14.40 (n = 30) | smokers-palmvitee-Spalte, Zeile 0 und 24 | dito |
| `yun2024:78` | 14.11 (n = 30) | 11.39 (n = 30) | Zeile 11: `0 … 11.39`; Zeile 13: `24 … 14.11` (Spalte 4) | dito |
| `yun2024:80` | 14.56 (n = 29) | 11.75 (n = 29) | Zeile 11: `0 … 11.75`; Zeile 13: `24 … 14.56` (Spalte 2) | dito |
| `yun2024:81` | 675.16 (n = 29) | 63.60 (n = 29) | Zeile 15: `0 … 63.60`; Zeile 17: `24 … 675.16` (Spalte 2) | dito |

In allen fünf Fällen ist die Gruppengröße im Komparator dieselbe wie im
Interventionsarm — der Komparator ist also kein Placebo-Arm. Für `yun2024:75`
ist das bereits als Gold-Konflikt eingetragen (`analyze_errors.GEPRUEFTE_FAELLE`,
Klasse 5, Beleg in `analysis/yun2024_75_gold_conflict.md`); die vier anderen
sind nach dieser Prüfung **Kandidaten mit Textbeleg**, aber noch nicht
eingetragen.

Ein sauberer Week-24-Schnitt wäre jeweils palmvitee-Woche-24 gegen
placebo-Woche-24, z. B. bei `:78` 14.11 gegen 11.53.

## 2. PMC4996097 — zwei legitime Rückfälle

Die Tabelle führt `Study group (n = 33)` und `Control group (n = 30)` mit den
Zeilen `Preop`, `Postop 1st month`, `Postop 3rd month`. Für die Kontrollgruppe
steht bei den Postop-Zeilen ein Strich.

| Record | Gold intervention | Gold comparator | Befund |
|---|---|---|---|
| `yun2024:149` | 138 | 154 | 138 steht bei `Postop 3rd month` **und** bei `Preop` der Studiengruppe; 154 nur bei `Preop` der Kontrolle |
| `yun2024:150` | 0.25 | 0.27 | Komparator nur präoperativ berichtet |

Hier ist die Mischung keine Gold-Verwechslung, sondern die Folge davon, dass der
Komparator am Zielzeitpunkt **nicht berichtet** wird — genau der Fall, den die
v6-Regel je Feld erlaubt. Die Goldzelle ist damit formal richtig extrahiert,
aber inhaltlich ein Baseline-gegen-Follow-up-Vergleich. Das gehört in die
Berichtsansicht, nicht in die Konfliktliste.

## 3. Konsequenz

* `arm_gemischt` in `fallback_eval.json` zählt weiter sieben Records; die
  Fehlerklassen in `arm_klassen` trennen jetzt
  `arm_gemischt_gold_bestaetigt` (1: `:75`), `arm_gemischt_gold_kandidat`
  (1: `:149`, nur Hinweis) und `arm_gemischt_modell` (5).
* Die vier Kandidaten aus PMC3546023 sind **nicht** in `GEPRUEFTE_FAELLE`
  eingetragen: das ist eine Benchmark-Entscheidung, weil vier Records damit aus
  der Modellfehler-Zählung fielen. Der Textbeleg liegt oben.
* Für die zweite Kohorte empfiehlt sich eine Vorabprüfung aller Records aus
  PMC3546023 und PMC4996097, bevor ihre Goldzellen als Maßstab dienen.
