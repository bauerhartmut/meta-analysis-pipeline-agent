# Length-Analyse der 18 Ausfälle (15.11.2026)

Grundlage: `runs/yun_test186_v7_folgelauf_20261116/predictions.jsonl`,
`runs/yun_test186_v6_20261115/predictions.jsonl`, Records und Artikeltexte.
Erzeugt von `error_analysis/analysiere_47.py`; Zahlen in `kennzahlen.json`.
Kein Modellaufruf.

## 1. Der zentrale Befund: es gibt keine Ausgabe

Für alle 18 Ausfälle gilt dasselbe Muster **[belegt, Datenfeld je Zeile]**:

| Feld | Wert bei allen 18 |
|---|---|
| `finish_reason` | `length` |
| `content_len` | **0** |
| `parse_error` | `kein_json` |
| `completion_tokens` | **19.000** (exakt das Limit) |

`content_len = 0` heißt: Das Modell hat **kein einziges Zeichen** Inhalt
geliefert. Es gibt also kein abgeschnittenes JSON, keine halbe Zellenliste und
keine redundante Ausgabe — die gesamte Budgetaufnahme fand vor dem ersten
ausgegebenen Zeichen statt (Reasoning-Kanal oder interner Abbruch).

Damit sind mehrere der in der Aufgabe genannten Hypothesen **widerlegt**:

| Hypothese | Befund |
|---|---|
| 1. Output-Limit zu klein | Kein Inhalt bei 19.000; dieselben Records scheiterten auch bei 16.000 (17 Fälle) und 24.000 (1 Fall). Ein höheres Limit half in keinem Fall. |
| 2. Unnötig ausführliche Ausgaben | Keine Ausgabe, also keine Ausführlichkeit. |
| 4. Redundante Prompt-Informationen | Ein Ausfall hat nur **4.648 Zeichen** Prompt (Median 17.186); ein anderer mit 22.099 Zeichen gelingt nicht, während Nachbarn mit ähnlicher Größe Zellen liefern. |
| 5. Ineffiziente JSON-Struktur | Ohne Ausgabe nicht messbar; das v7-Schema ist zudem kleiner als v6. |
| 3. Zu viele Variablen gleichzeitig | **[Hypothese, nicht belegt]** Alle 18 haben 2–6 Goldzellen, also nie besonders viele; ein Zusammenhang mit der Zellzahl ist in den Daten nicht sichtbar (Ausfallquote 28,2 % bei 2 Zellen, 15,4 % bei 3–4, 22,2 % bei ≥ 5 in der v6-Diagnose). |

Wahrscheinlichste Ursache: **modellseitige Generierungsschleife im
Reasoning-Kanal** bis zum harten Limit, ohne je Inhalt zu emittieren.

## 2. Kein Zusammenhang mit Inputgröße

Ausfallquote innerhalb der 47 Records nach Artikelgröße **[belegt]**:

| Textgröße | Records | davon Length | Quote |
|---|---:|---:|---:|
| < 8k Zeichen | 4 | 1 | 25,0 % |
| 8–16k | 22 | 9 | 40,9 % |
| 16–24k | 19 | 8 | 42,1 % |
| ≥ 24k | 2 | 0 | 0 % |

Die beiden größten Artikel der Gruppe sind **nicht** gescheitert. Der
Zusammenhang ist schwach und nicht monoton (v6-Gesamtdaten: 23/98 unter 15k
gegen 24/88 darüber, Fisher p = 0,87).

Promptgröße: Median 17.186 Zeichen bei den Ausfällen gegen 14.571 bei den 23
Records mit Zellen **[belegt]** — ein Unterschied von 18 %, aber mit
Überlappung in beide Richtungen. Kein Schwellwert erkennbar.

## 3. Kosten und Streuung

| Posten | Tokens |
|---|---:|
| v6-Versuche der 18 Records | 296.000 |
| v7-Versuche | 342.000 |
| **Summe ohne eine einzige Zelle** | **638.000** |
| Anteil der Ausfälle an den v7-Tokens der 47 | 56,0 % |

Die 18 verteilen sich auf **12 verschiedene Dokumente**, höchstens zwei pro
Dokument (PMC5056957, PMC5686687, PMC5541727, PMC115849, PMC3504298,
PMC2836833 je 2; sechs weitere je 1). Es gibt also kein einzelnes kaputtes
Dokument als Ursache.

## 4. Was sich aus den vorhandenen Daten **nicht** klären lässt

* **Reasoning-Inhalt:** Der Client speichert weder `reasoning_tokens` noch den
  Reasoning-Text. Ob die Schleife im Reasoning steckt, ist damit eine
  begründete Schlussfolgerung aus `content_len = 0`, kein direkter Nachweis.
* **Rohantwort:** `--save-content` war nicht gesetzt; für künftige Läufe sollte
  es an sein (Mehrkosten nur im Speicher, nicht im Tokenbudget).
* **Gateway-Parameter:** Ob das Gateway ein Reasoning-Budget kennt, ist im Repo
  nicht belegt; der Client sendet nur `max_tokens` und `temperature`.

## 5. Tabelle der 18 Records

Spalten: Text/Prompt in Zeichen, Tokens je Lauf, `content_len` der v7-Antwort.
| Record | Dokument | Text | Prompt | v6 Tok | v7 Tok | content_len | Summe |
|---|---|---:|---:|---:|---:|---:|---:|
| `yun2024:158` | PMC5056957 | 16081 | 17778 | 24000 | 19000 | 0 | 43000 |
| `yun2024:163` | PMC5056957 | 16081 | 17773 | 16000 | 19000 | 0 | 35000 |
| `yun2024:169` | PMC5079604 | 20409 | 22099 | 16000 | 19000 | 0 | 35000 |
| `yun2024:328` | PMC5559992 | 2999 | 4648 | 16000 | 19000 | 0 | 35000 |
| `yun2024:348` | PMC5686687 | 9253 | 10893 | 16000 | 19000 | 0 | 35000 |
| `yun2024:349` | PMC5686687 | 9253 | 10890 | 16000 | 19000 | 0 | 35000 |
| `yun2024:356` | PMC5884950 | 19352 | 21324 | 16000 | 19000 | 0 | 35000 |
| `yun2024:368` | PMC1475568 | 11667 | 13429 | 16000 | 19000 | 0 | 35000 |
| `yun2024:405` | PMC5781260 | 12175 | 13819 | 16000 | 19000 | 0 | 35000 |
| `yun2024:566` | PMC5541727 | 15499 | 17204 | 16000 | 19000 | 0 | 35000 |
| `yun2024:570` | PMC5541727 | 15499 | 17167 | 16000 | 19000 | 0 | 35000 |
| `yun2024:581` | PMC115849 | 17712 | 19411 | 16000 | 19000 | 0 | 35000 |
| `yun2024:582` | PMC3504298 | 12838 | 14545 | 16000 | 19000 | 0 | 35000 |
| `yun2024:584` | PMC3504298 | 12838 | 14511 | 16000 | 19000 | 0 | 35000 |
| `yun2024:605` | PMC115849 | 17712 | 19376 | 16000 | 19000 | 0 | 35000 |
| `yun2024:639` | PMC4511433 | 11362 | 13003 | 16000 | 19000 | 0 | 35000 |
| `yun2024:685` | PMC2836833 | 18929 | 20578 | 16000 | 19000 | 0 | 35000 |
| `yun2024:686` | PMC2836833 | 18929 | 20589 | 16000 | 19000 | 0 | 35000 |

Alle 18 Zeilen: `finish_reason = length`, `parse_error = kein_json`, `content_len = 0`.
