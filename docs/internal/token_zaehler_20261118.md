# Tokenzähler für TUDaGPT

Stand: 18.11.2026, 16:00. Gebaut, geprüft und mit den vorhandenen Daten einmal
durchgerechnet. Kein Netzlauf.

**Was er zählt:** Input- und Output-Tokens aller Aufrufe an TUDaGPT, aufgeschlüsselt
nach Modell, Tag und Stunde. Die Zahlen kommen aus dem `usage`-Block der Antwort,
nichts wird geschätzt.

## Wo er liegt

| Datei | Rolle |
|---|---|
| `research_agent/llm/token_zaehler.py` | Ledger schreiben, beide Quellen lesen, Bericht bauen |
| `scripts/zeige_tokens.py` | Kommandozeile mit Filtern (`--modell`, `--seit`, `--bis`) |
| `public_benchmark/extended_benchmark/run_extended_extraction.py` | ruft `token_zaehler.zaehle(...)` in `_call_once` auf |
| `research_agent/tests/test_token_zaehler.py` | neun Tests |
| `data/tudagpt_tokens.jsonl` | Ledger, nicht versioniert (`.gitignore`) |

## Zwei Quellen

1. **Ledger** `data/tudagpt_tokens.jsonl`: eine Zeile je Antwort, die der
   Extraktions-Harness selbst vom Gateway holt. Weil jeder Versuch, jeder Retry
   und jeder Reparaturaufruf durch `_call_once` laufen, ist das für diesen Pfad
   vollständig — auch abgebrochene Antworten zählen ihre Tokens.
2. **`llm_usage` in `data/*.db`**: der Agent-Pfad schreibt dort je Aufruf Input-
   und Output-Tokens, Phase, Backend und Modell. Diese Zeilen entstanden schon
   vorher; der Zähler liest sie nur.

Beide werden zusammengeführt; identische Zeilen (gleicher Zeitstempel, Modell und
Werte) zählen einmal.

## Was noch nicht drin ist

Diese Skripte sprechen TUDaGPT mit eigenem HTTP-Aufruf an und sind noch nicht
angebunden: `run_stage_extraction.py`, `iterativ/zell_retrieval.py`,
`table_decomposition/run_benchmark.py`, `scripts/diagnose_glm.py`,
`scripts/goldstandard/run_tier1_extraction.py`. Ebenso fehlt der **laufende**
Nachtlauf (PID 3952): sein Prozess hat den Harness vor dem Einbau geladen, seine
Aufrufe landen also nicht im Ledger. Ab dem nächsten Start (P5) zählt er mit.
Benchmark-Läufe vor heute haben nur `completion_tokens` in ihren Zeilen, keine
Prompt-Tokens; sie werden nicht nachgetragen und nicht geschätzt.

## Aufruf

```
.venv/bin/python scripts/zeige_tokens.py
.venv/bin/python scripts/zeige_tokens.py --modell gwdg/glm-5.3 --seit 2026-11-18
.venv/bin/python scripts/zeige_tokens.py --md bericht.md --json roh.json
```

`TUDAGPT_TOKEN_LEDGER` biegt den Ledger um, damit Tests die echte Buchführung
nicht mit Attrappen füllen.

## Bericht über die vorhandenen Daten

Der folgende Abschnitt ist die Ausgabe des Skripts über alle `llm_usage`-Zeilen in
`data/*.db` und den (noch leeren) Ledger. Er umfasst ausschließlich den
Agent-Pfad, also die Recherche-Läufe vom 27.10. bis 05.11.; die Zahlen sind
deshalb keine Aussage über die Benchmark-Läufe.


| Tag | Stunde | Modell | Aufrufe | Input | Output | Gesamt |
|---|---|---|---:|---:|---:|---:|
| 2026-10-27 | 11 | `gwdg/meta-llama-3.1-8b-instruct` | 11 | 16.367 | 2.310 | 18.677 |
| 2026-10-27 | 11 | `gwdg/qwen3.5-397b-a17b` | 564 | 570.622 | 188.142 | 758.764 |
| 2026-10-27 | 12 | `gwdg/meta-llama-3.1-8b-instruct` | 11 | 16.494 | 2.253 | 18.747 |
| 2026-10-27 | 12 | `gwdg/qwen3.5-397b-a17b` | 256 | 264.906 | 116.894 | 381.800 |
| 2026-10-27 | 13 | `gwdg/meta-llama-3.1-8b-instruct` | 15 | 22.841 | 2.497 | 25.338 |
| 2026-10-27 | 13 | `gwdg/qwen3.5-397b-a17b` | 260 | 242.493 | 99.530 | 342.023 |
| 2026-10-27 | 14 | `gwdg/meta-llama-3.1-8b-instruct` | 17 | 25.313 | 2.969 | 28.282 |
| 2026-10-27 | 14 | `gwdg/qwen3.5-397b-a17b` | 181 | 181.228 | 58.404 | 239.632 |
| 2026-10-27 | 15 | `gwdg/meta-llama-3.1-8b-instruct` | 23 | 34.431 | 4.315 | 38.746 |
| 2026-10-27 | 15 | `gwdg/qwen3.5-397b-a17b` | 216 | 226.555 | 56.637 | 283.192 |
| 2026-10-27 | 15 | `unbekannt` | 3 | 0 | 0 | 0 |
| 2026-10-27 | 16 | `gwdg/meta-llama-3.1-8b-instruct` | 37 | 54.903 | 6.191 | 61.094 |
| 2026-10-27 | 16 | `gwdg/qwen3.5-397b-a17b` | 418 | 397.462 | 102.416 | 499.878 |
| 2026-10-27 | 17 | `gwdg/meta-llama-3.1-8b-instruct` | 40 | 58.996 | 6.612 | 65.608 |
| 2026-10-27 | 17 | `gwdg/qwen3.5-397b-a17b` | 437 | 444.650 | 114.196 | 558.846 |
| 2026-10-27 | 18 | `gwdg/meta-llama-3.1-8b-instruct` | 43 | 63.544 | 7.141 | 70.685 |
| 2026-10-27 | 18 | `gwdg/qwen3.5-397b-a17b` | 505 | 497.417 | 131.131 | 628.548 |
| 2026-10-27 | 19 | `gwdg/meta-llama-3.1-8b-instruct` | 33 | 49.423 | 5.205 | 54.628 |
| 2026-10-27 | 19 | `gwdg/qwen3.5-397b-a17b` | 430 | 454.818 | 126.620 | 581.438 |
| 2026-10-27 | 19 | `unbekannt` | 11 | 0 | 0 | 0 |
| 2026-10-27 | 20 | `gwdg/meta-llama-3.1-8b-instruct` | 35 | 52.806 | 6.167 | 58.973 |
| 2026-10-27 | 20 | `gwdg/qwen3.5-397b-a17b` | 501 | 520.626 | 142.040 | 662.666 |
| 2026-10-27 | 21 | `gwdg/meta-llama-3.1-8b-instruct` | 31 | 46.834 | 5.139 | 51.973 |
| 2026-10-27 | 21 | `gwdg/qwen3.5-397b-a17b` | 466 | 467.486 | 130.862 | 598.348 |
| 2026-10-27 | 22 | `gwdg/meta-llama-3.1-8b-instruct` | 27 | 41.279 | 4.727 | 46.006 |
| 2026-10-27 | 22 | `gwdg/qwen3.5-397b-a17b` | 383 | 404.075 | 111.394 | 515.469 |
| 2026-10-27 | 23 | `gwdg/meta-llama-3.1-8b-instruct` | 8 | 12.368 | 1.188 | 13.556 |
| 2026-10-27 | 23 | `gwdg/qwen3.5-397b-a17b` | 120 | 118.326 | 35.522 | 153.848 |
| 2026-10-28 | 15 | `gwdg/qwen3.5-397b-a17b` | 1 | 13 | 14 | 27 |
| 2026-10-28 | 16 | `gwdg/meta-llama-3.1-8b-instruct` | 39 | 58.185 | 7.671 | 65.856 |
| 2026-10-28 | 16 | `gwdg/qwen3.5-397b-a17b` | 528 | 562.549 | 157.760 | 720.309 |
| 2026-10-28 | 17 | `gwdg/meta-llama-3.1-8b-instruct` | 33 | 50.904 | 6.437 | 57.341 |
| 2026-10-28 | 17 | `gwdg/qwen3.5-397b-a17b` | 525 | 554.412 | 147.871 | 702.283 |
| 2026-10-28 | 18 | `gwdg/meta-llama-3.1-8b-instruct` | 27 | 40.639 | 4.485 | 45.124 |
| 2026-10-28 | 18 | `gwdg/qwen3.5-397b-a17b` | 396 | 457.323 | 100.886 | 558.209 |
| 2026-10-28 | 19 | `gwdg/meta-llama-3.1-8b-instruct` | 33 | 50.132 | 5.247 | 55.379 |
| 2026-10-28 | 19 | `gwdg/qwen3.5-397b-a17b` | 544 | 699.067 | 138.333 | 837.400 |
| 2026-10-28 | 20 | `gwdg/meta-llama-3.1-8b-instruct` | 27 | 41.400 | 4.237 | 45.637 |
| 2026-10-28 | 20 | `gwdg/qwen3.5-397b-a17b` | 444 | 558.433 | 116.057 | 674.490 |
| 2026-10-28 | 21 | `gwdg/meta-llama-3.1-8b-instruct` | 28 | 43.175 | 4.901 | 48.076 |
| 2026-10-28 | 21 | `gwdg/qwen3.5-397b-a17b` | 583 | 700.865 | 147.117 | 847.982 |
| 2026-10-28 | 22 | `gwdg/meta-llama-3.1-8b-instruct` | 34 | 52.526 | 6.246 | 58.772 |
| 2026-10-28 | 22 | `gwdg/qwen3.5-397b-a17b` | 546 | 671.935 | 126.659 | 798.594 |
| 2026-10-28 | 23 | `gwdg/meta-llama-3.1-8b-instruct` | 34 | 52.851 | 6.275 | 59.126 |
| 2026-10-28 | 23 | `gwdg/qwen3.5-397b-a17b` | 643 | 817.570 | 170.626 | 988.196 |
| 2026-10-29 | 00 | `gwdg/meta-llama-3.1-8b-instruct` | 7 | 10.866 | 1.715 | 12.581 |
| 2026-10-29 | 00 | `gwdg/qwen3.5-397b-a17b` | 140 | 183.837 | 38.909 | 222.746 |
| 2026-10-29 | 10 | `gwdg/meta-llama-3.1-8b-instruct` | 24 | 31.254 | 4.124 | 35.378 |
| 2026-10-29 | 10 | `gwdg/qwen3.5-397b-a17b` | 344 | 371.320 | 106.096 | 477.416 |
| 2026-10-31 | 18 | `gwdg/qwen3.5-397b-a17b` | 1 | 13 | 14 | 27 |
| 2026-10-31 | 19 | `gwdg/meta-llama-3.1-8b-instruct` | 5 | 7.013 | 1.075 | 8.088 |
| 2026-10-31 | 19 | `gwdg/qwen3.5-397b-a17b` | 62 | 67.324 | 18.097 | 85.421 |
| 2026-10-31 | 20 | `gwdg/meta-llama-3.1-8b-instruct` | 8 | 11.134 | 1.524 | 12.658 |
| 2026-10-31 | 20 | `gwdg/qwen3.5-397b-a17b` | 110 | 136.241 | 25.512 | 161.753 |
| 2026-10-31 | 20 | `unbekannt` | 1 | 0 | 0 | 0 |
| 2026-10-31 | 21 | `gwdg/meta-llama-3.1-8b-instruct` | 21 | 29.463 | 4.890 | 34.353 |
| 2026-10-31 | 21 | `gwdg/qwen3.5-397b-a17b` | 288 | 294.635 | 74.157 | 368.792 |
| 2026-10-31 | 22 | `gwdg/meta-llama-3.1-8b-instruct` | 56 | 79.446 | 14.522 | 93.968 |
| 2026-10-31 | 22 | `gwdg/qwen3.5-397b-a17b` | 824 | 914.683 | 242.305 | 1.156.988 |
| 2026-10-31 | 23 | `gwdg/meta-llama-3.1-8b-instruct` | 57 | 81.461 | 13.051 | 94.512 |
| 2026-10-31 | 23 | `gwdg/qwen3.5-397b-a17b` | 634 | 673.066 | 191.615 | 864.681 |
| 2026-11-01 | 00 | `gwdg/meta-llama-3.1-8b-instruct` | 11 | 15.940 | 2.197 | 18.137 |
| 2026-11-01 | 00 | `gwdg/qwen3.5-397b-a17b` | 114 | 99.976 | 30.177 | 130.153 |
| 2026-11-01 | 10 | `gwdg/meta-llama-3.1-8b-instruct` | 29 | 41.563 | 5.368 | 46.931 |
| 2026-11-01 | 10 | `gwdg/qwen3.5-397b-a17b` | 341 | 385.265 | 120.377 | 505.642 |
| 2026-11-01 | 11 | `gwdg/meta-llama-3.1-8b-instruct` | 58 | 84.120 | 12.731 | 96.851 |
| 2026-11-01 | 11 | `gwdg/qwen3.5-397b-a17b` | 802 | 1.121.414 | 241.906 | 1.363.320 |
| 2026-11-01 | 12 | `gwdg/meta-llama-3.1-8b-instruct` | 74 | 109.580 | 15.507 | 125.087 |
| 2026-11-01 | 12 | `gwdg/qwen3.5-397b-a17b` | 737 | 836.256 | 213.937 | 1.050.193 |
| 2026-11-01 | 13 | `gwdg/meta-llama-3.1-8b-instruct` | 39 | 58.434 | 7.364 | 65.798 |
| 2026-11-01 | 13 | `gwdg/qwen3.5-397b-a17b` | 262 | 248.018 | 70.166 | 318.184 |
| 2026-11-01 | 16 | `gwdg/qwen3.5-397b-a17b` | 66 | 58.732 | 24.467 | 83.199 |
| 2026-11-01 | 17 | `gwdg/meta-llama-3.1-8b-instruct` | 39 | 59.562 | 7.123 | 66.685 |
| 2026-11-01 | 17 | `gwdg/qwen3.5-397b-a17b` | 640 | 665.229 | 202.053 | 867.282 |
| 2026-11-01 | 18 | `gwdg/meta-llama-3.1-8b-instruct` | 55 | 83.341 | 11.561 | 94.902 |
| 2026-11-01 | 18 | `gwdg/qwen3.5-397b-a17b` | 749 | 889.351 | 221.012 | 1.110.363 |
| 2026-11-01 | 19 | `gwdg/meta-llama-3.1-8b-instruct` | 56 | 85.645 | 10.253 | 95.898 |
| 2026-11-01 | 19 | `gwdg/qwen3.5-397b-a17b` | 687 | 909.465 | 207.241 | 1.116.706 |
| 2026-11-01 | 20 | `gwdg/meta-llama-3.1-8b-instruct` | 82 | 127.539 | 15.455 | 142.994 |
| 2026-11-01 | 20 | `gwdg/qwen3.5-397b-a17b` | 523 | 636.156 | 159.109 | 795.265 |
| 2026-11-01 | 21 | `gwdg/meta-llama-3.1-8b-instruct` | 5 | 7.684 | 725 | 8.409 |
| 2026-11-01 | 21 | `gwdg/qwen3.5-397b-a17b` | 76 | 107.901 | 27.336 | 135.237 |
| 2026-11-01 | 22 | `gwdg/meta-llama-3.1-8b-instruct` | 35 | 54.219 | 7.772 | 61.991 |
| 2026-11-01 | 22 | `gwdg/qwen3.5-397b-a17b` | 348 | 408.614 | 121.873 | 530.487 |
| 2026-11-01 | 23 | `gwdg/meta-llama-3.1-8b-instruct` | 30 | 46.185 | 5.260 | 51.445 |
| 2026-11-01 | 23 | `gwdg/qwen3.5-397b-a17b` | 316 | 361.813 | 107.962 | 469.775 |
| 2026-11-03 | 12 | `gwdg/meta-llama-3.1-8b-instruct` | 11 | 16.908 | 2.057 | 18.965 |
| 2026-11-03 | 12 | `gwdg/qwen3.5-397b-a17b` | 250 | 253.864 | 73.443 | 327.307 |
| 2026-11-03 | 13 | `gwdg/meta-llama-3.1-8b-instruct` | 40 | 59.018 | 7.459 | 66.477 |
| 2026-11-03 | 13 | `gwdg/qwen3.5-397b-a17b` | 541 | 589.894 | 136.912 | 726.806 |
| 2026-11-03 | 14 | `gwdg/meta-llama-3.1-8b-instruct` | 16 | 23.859 | 3.902 | 27.761 |
| 2026-11-03 | 14 | `gwdg/qwen3.5-397b-a17b` | 371 | 381.652 | 107.448 | 489.100 |
| 2026-11-03 | 15 | `gwdg/meta-llama-3.1-8b-instruct` | 25 | 36.974 | 6.733 | 43.707 |
| 2026-11-03 | 15 | `gwdg/qwen3.5-397b-a17b` | 387 | 445.420 | 112.924 | 558.344 |
| 2026-11-03 | 16 | `gwdg/meta-llama-3.1-8b-instruct` | 8 | 12.232 | 2.168 | 14.400 |
| 2026-11-03 | 16 | `gwdg/qwen3.5-397b-a17b` | 133 | 148.142 | 39.290 | 187.432 |
| 2026-11-05 | 15 | `gwdg/meta-llama-3.1-8b-instruct` | 12 | 18.010 | 2.426 | 20.436 |
| 2026-11-05 | 15 | `gwdg/qwen3.5-397b-a17b` | 802 | 659.129 | 222.103 | 881.232 |
| 2026-11-05 | 15 | `unbekannt` | 1 | 0 | 0 | 0 |
| 2026-11-05 | 16 | `gwdg/meta-llama-3.1-8b-instruct` | 64 | 95.365 | 15.191 | 110.556 |
| 2026-11-05 | 16 | `gwdg/qwen3.5-397b-a17b` | 1024 | 993.132 | 252.298 | 1.245.430 |
| 2026-11-05 | 17 | `gwdg/meta-llama-3.1-8b-instruct` | 80 | 120.657 | 17.474 | 138.131 |
| 2026-11-05 | 17 | `gwdg/qwen3.5-397b-a17b` | 743 | 780.014 | 198.473 | 978.487 |
| 2026-11-05 | 17 | `unbekannt` | 1 | 0 | 0 | 0 |
| 2026-11-05 | 18 | `gwdg/meta-llama-3.1-8b-instruct` | 88 | 134.744 | 23.533 | 158.277 |
| 2026-11-05 | 18 | `gwdg/qwen3.5-397b-a17b` | 854 | 868.847 | 232.690 | 1.101.537 |
| 2026-11-05 | 19 | `gwdg/meta-llama-3.1-8b-instruct` | 47 | 71.483 | 11.009 | 82.492 |
| 2026-11-05 | 19 | `gwdg/qwen3.5-397b-a17b` | 386 | 350.807 | 100.874 | 451.681 |
| 2026-11-05 | 20 | `gwdg/meta-llama-3.1-8b-instruct` | 23 | 35.909 | 6.528 | 42.437 |
| 2026-11-05 | 20 | `gwdg/qwen3.5-397b-a17b` | 386 | 363.479 | 106.832 | 470.311 |
| 2026-11-05 | 21 | `gwdg/meta-llama-3.1-8b-instruct` | 21 | 32.561 | 5.952 | 38.513 |
| 2026-11-05 | 21 | `gwdg/qwen3.5-397b-a17b` | 350 | 333.165 | 97.502 | 430.667 |
| 2026-11-05 | 22 | `gwdg/meta-llama-3.1-8b-instruct` | 32 | 49.299 | 6.821 | 56.120 |
| 2026-11-05 | 22 | `gwdg/qwen3.5-397b-a17b` | 331 | 304.044 | 70.580 | 374.624 |

## Summe je Modell

| Modell | Aufrufe | Input | Output | Gesamt |
|---|---:|---:|---:|---:|
| `gwdg/meta-llama-3.1-8b-instruct` | 1744 | 2.616.879 | 355.683 | 2.972.562 |
| `gwdg/qwen3.5-397b-a17b` | 23569 | 25.653.729 | 6.714.801 | 32.368.530 |
| `unbekannt` | 17 | 0 | 0 | 0 |

## Summe je Tag

| Tag | Aufrufe | Input | Output | Gesamt |
|---|---:|---:|---:|---:|
| 2026-10-27 | 5082 | 5.286.263 | 1.470.502 | 6.756.765 |
| 2026-10-28 | 4465 | 5.411.979 | 1.150.822 | 6.562.801 |
| 2026-10-29 | 515 | 597.277 | 150.844 | 748.121 |
| 2026-10-31 | 2067 | 2.294.479 | 586.762 | 2.881.241 |
| 2026-11-01 | 6174 | 7.502.002 | 1.848.932 | 9.350.934 |
| 2026-11-03 | 1782 | 1.967.963 | 492.336 | 2.460.299 |
| 2026-11-05 | 5245 | 5.210.645 | 1.370.286 | 6.580.931 |

Gesamt: 25.330 Aufrufe, 28.270.608 Input-Tokens, 7.070.484 Output-Tokens, 35.341.092 Tokens.

Input und Output stammen aus dem `usage`-Block der Antwort. Laeufe vor dem Ledger tragen nur die Zeilen, die der Agent-Pfad in `llm_usage` abgelegt hat.
