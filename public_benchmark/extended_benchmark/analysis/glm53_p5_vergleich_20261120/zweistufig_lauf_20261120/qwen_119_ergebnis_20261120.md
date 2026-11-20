# qwen3.5-397b auf yun2024:119: kein Abbruch und ein Treffer (20.11.2026)

Ein freigegebener Aufruf, die Kontrolle zum Lauf auf `yun2024:421`. Modell
`gwdg/qwen3.5-397b-a17b` (`qwen`), Satz-Locator (`stage1_satz`), Budget 16.000,
Temperatur 0, Lesezeit 900 s, Prompt 7.278 Zeichen (Ausschnitt 6.000, Regelteil
1.278). Rohdaten: `predictions_satz_119_qwen_16000.jsonl`, Startbefehl aus dem
Repo-Wurzelverzeichnis (die Konfiguration wird relativ zum Arbeitsverzeichnis
geladen, aus dem Analyseordner bricht der Lauf mit „kein API-Schluessel" ab).

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **6.236** von 16.000 |
| Reasoning-Zeichen | 23.030 |
| Inhalt | 1.368 Zeichen, **2 Locators** |
| Dauer | 161,55 s |
| Armzuordnung | je ein Locator fuer `intervention` und `comparator` |
| `satz_im_ausschnitt` | **True** fuer beide |
| `found` | **True** fuer beide |
| `timepoint` | `6 months post-trauma` |

Beide Locators tragen denselben Satz, woertlich aus dem Ausschnitt:

> When comparison was only made between 2 groups (no cooling vs mild cooling;
> no cooling vs deep cooling and mild cooling vs deep cooling), it seems that the
> mild-cooling-treated patients fared better than no cooling (70% of mild cooling
> attained good GOS compared with only 15.4% attained good GOS in no cooling
> group, *P* = 0.013); and apparently, the deep-cooling-treated patients failed
> to be better than either no cooling (*P* = 0.074) or mild cooling group
> (*P* = 0.650).

Der Zeitpunkt stimmt mit der Aufgabe ueberein: das Abstract nennt die
GOS-Erhebung „at 6 months posttrauma", das Ziel war der primaere Zeitpunkt. Die
Abschnittsmarke, die das Modell als `caption` angibt
(`## Effect of regional brain cooling on Glasgow outcome score`), steht
woertlich im Ausschnitt (geprueft).

## Was der Aufruf beantwortet

**Der Abbruch ist auch auf einem zweiten Record modellspezifisch.** `glm-5.3`
verbraucht auf `yun2024:420` und `yun2024:421` in jeder geprueften
Prompt-Fassung das volle Budget ohne ein Zeichen Inhalt; `qwen3.5-397b`
antwortet auf 421 und auf 119 mit `stop`, jeweils deutlich unter dem Budget
(10.686 und 6.236 von 16.000). Zwei Records, zwei Antworten - das ist die
belastbarere Aussage als der Einzelbefund von 421.

**Aber der Modellwechsel loest die Aufgabe nicht von selbst.** Die beiden
qwen-Antworten unterscheiden sich in der Qualitaet:

| Record | Goldzellen | Goldwerte im Ausschnitt | qwen-Antwort | Bewertung |
|---|---:|---:|---|---|
| `yun2024:421` | 6 | 6/6 | `found: false`, nur ein Locator | **falsches Negativ** |
| `yun2024:119` | 4 | 2/4 erreichbar | `found: true`, zwei Locators, Satz woertlich | **Treffer** |

Auf 421 war `found: false` sachlich falsch, weil der Satz mit 0,95/0,24 gegen
1,43/0,48 im Ausschnitt gedruckt steht. Auf 119 ist die Antwort richtig: der
Satz nennt beide Arme zum Zielzeitpunkt, und das Modell zitiert ihn statt ihn
zu paraphrasieren.

## Was der Treffer auf 119 wert ist - und was nicht

Von den vier Goldzellen sind nur zwei aus dem Ausschnitt erreichbar:

| Goldzelle | Wert | im Ausschnitt gedruckt? |
|---|---:|---|
| `intervention_mean` | 70,0 | ja, als **70 %** |
| `comparator_mean` | 15,4 | ja, als **15,4 %** |
| `intervention_group_size` | 10 | **nein** |
| `comparator_group_size` | 13 | **nein** |

Der Text nennt nur „A total of 32 patients were recruited" und „63,2 % in cooling
group"; die Gruppengroessen 10 und 13 stehen nicht im Ausschnitt. Ein perfekter
Locator kann hier also hoechstens 2 von 4 Zellen stuetzen. Der Satz ist damit
als Stufe-1-Ergebnis richtig, die zugehoerige Extraktion kann aber nicht 4/4
erreichen.

Zweite Einschraenkung, die den Datensatz betrifft und nicht den Aufruf: der
Kontext deklariert `outcome_type = continuous` („Improvement in Glasgow outcome
score"), die gedruckte Groesse ist aber ein **dichotomierter Anteil** („70 %
attained good GOS"). Das Gold traegt die Anteile als `mean` ein. Diese
Bezeichnungsdifferenz ist ein Befund ueber die Annotation; das Gold bleibt
unveraendert, sie gehoert aber in jede Bewertung dieses Records.

Der Pruefmerker `zielwerte_im_satz` zeigt nur `15.4`. Das ist ein Artefakt der
Pruefung, nicht des Modells: sie vergleicht `str(70.0)` = `"70.0"` gegen den
Text `"70%"` und findet die Zahl deshalb nicht. Die Ziffernfolge `70` steht im
zitierten Satz.

## Kosten

Gemessene Completion-Tokens: 124.591 (bisherige Reihe) + 6.236 = **130.827**.
Eingabetokens sind nicht budgetiert und hier nicht enthalten; Fehlversuche ohne
Tokenzaehlung sind nicht mitgezaehlt.

## Grenzen

- **n = 1** je Zelle. Zwei qwen-Antworten (421, 119) sind zwei Records, nicht
  zwei Wiederholungen desselben Records; die Streuung des Modells auf einem
  Record ist nicht gemessen.
- Die Budgets sind nicht gleich (glm 16.632, qwen 16.000). Beide qwen-Laeufe
  blieben deutlich darunter (10.686 und 6.236), das Budget war also nicht der
  begrenzende Faktor; glm verbrauchte seines vollstaendig.
- 119 und 421 stammen aus verschiedenen Publikationen (`PMC3877023` gegen die
  Quelle von 119); ein Vergleich ueber Dokumente hinweg kontrolliert weder
  Abschnittslaenge noch Tabellenlage.
- Der Treffer ist auf Stufe 1 gemessen: der zitierte Satz ist belegt, die
  Zellen sind nicht extrahiert. Ein Stufe-2-Aufruf auf diesem Satz steht aus.
