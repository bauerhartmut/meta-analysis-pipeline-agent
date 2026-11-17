# Golden-Set: Record-Diff zwischen alter und aktueller Erhebung

Erzeugt von `scripts/pruefe_golden_set.py --diff-alt` am 2026-11-17.
Alt = `research_agent/evals/golden_answers.json` vom 2026-08-31 (Commit 0f09c89),
neu = derselbe Aufbau gegen `data/research.db` (Stand der aktuellen Erhebung).
Gezeigt werden die Records, nicht die Claim-Texte: die stehen im Set selbst.

Spalten: `Quelle alt` = im alten Set zitierter Record, `Quelle neu` = Record,
der den Claim jetzt traegt, `Abdeckung` = Anteil der Claim-Terme, die im
Record-Text vorkommen (1.00 = vollstaendig), `Zahlen alt/neu` = behauptete Werte.

Befunde: `unveraendert` (Record und Text gleich), `neu_verankert` (Inhalt unter
neuer ID, Text im Kern gleich), `record_geaendert` (Zahlen weichen ab),
`inhaltlich_ersetzt` (anderer Record traegt die Aussage jetzt), `extern`
(bewusst nicht aus der DB).

| Frage | Pos. | Quelle alt | Quelle neu | Befund | Abdeckung | Zahlen alt | Zahlen neu |
|---|---|---|---|---|---|---|---|
| `q01_wilson_effect` | 0 | `fact 3cab2651366a (Wilson Effect)` | `fact 86ff0620ec72` | record_geaendert | 1.00 | 0.40, 0.80 | 41, 80 |
| `q01_wilson_effect` | 1 | `fact 4bcb66847b35 / fbb9b96305e3` | `fact 4bcb66847b35` | unveraendert | 0.86 | 0.80, 18, 20 | 0.80, 18, 20 |
| `q01_wilson_effect` | 3 | `fremdbelegt` | - | extern | - | 2748, 49 | 2748, 49 |
| `q02_gwas_intelligence` | 0 | `fact b10b64d91f88` | `fact dad5222c0a90` | neu_verankert | 1.00 | - | - |
| `q02_gwas_intelligence` | 1 | `fact 89fbc72f6cf4` | `fact 4577de4fab95` | neu_verankert | 1.00 | 3 million, 3952 | 3 million, 3,952 |
| `q02_gwas_intelligence` | 2 | `fact 4511e1ed3cbf` | `fact 757de758880b` | neu_verankert | 1.00 | 0.6, 3 | 0.6%, 3% |
| `q02_gwas_intelligence` | 4 | `fremdbelegt` | - | extern | - | 1.1 million, 1271, 7, 10 | 1.1 million, 1271, 7, 10 |
| `q02_gwas_intelligence` | 5 | `fremdbelegt` | - | extern | - | 269867, 205, 190 | 269867, 205, 190 |
| `q03_pgt_outcomes` | 0 | `fact d1af12c3e759` | `fact b912d08693ad` | neu_verankert | 1.00 | 2017 | 2017 |
| `q03_pgt_outcomes` | 3 | `fact bd9728f9746c` | `evidence 372422ffbd6f` | inhaltlich_ersetzt | 0.92 | - | - |
| `q03_pgt_outcomes` | 4 | `fremdbelegt` | - | extern | - | 2000 | 2000 |
| `q04_selection_response` | 0 | `fact 5e9ee71a3d76` | `fact 0aeb31028581` | record_geaendert | 1.00 | 15, 80 | 50, 70 |
| `q04_selection_response` | 1 | `fact a70be51d24be` | `fact e377a385afa9` | neu_verankert | 1.00 | - | 2 |
| `q04_selection_response` | 2 | `hypothesis 62ad875ca16d` | `hypothesis 62ad875ca16d` | unveraendert | 0.75 | - | - |
| `q04_selection_response` | 3 | `fremdbelegt` | - | extern | - | 5.4 million, 12111, 40 | 5.4 million, 12111, 40 |
| `q05_polygenic_scores` | 0 | `fact 4511e1ed3cbf` | `fact 757de758880b` | neu_verankert | 1.00 | 0.6, 3 | 0.6%, 3% |
| `q06_cost_benefit` | 1 | `journal finding cycle 36` | `journal 61f2a83463b0` | neu_verankert | 1.00 | - | - |
| `q06_cost_benefit` | 2 | `hypothesis 9ed666b98170` | `hypothesis 9ed666b98170` | unveraendert | 0.57 | - | - |
| `q07_countries_selection` | 2 | `fact bd9728f9746c` | `evidence 372422ffbd6f` | inhaltlich_ersetzt | 0.92 | - | - |
| `q08_transhumanist_ethics` | 0 | `hypothesis 054d7f0017b0` | `hypothesis 054d7f0017b0` | unveraendert | 0.92 | - | - |
| `q08_transhumanist_ethics` | 2 | `fremdbelegt` | - | extern | - | - | - |
| `q09_flynn_plateau` | 1 | `hypothesis 9ed666b98170` | `hypothesis 9ed666b98170` | unveraendert | 1.00 | - | - |
| `q09_flynn_plateau` | 2 | `hypothesis 3a3b36bc5760` | `hypothesis 6530673ee897` | inhaltlich_ersetzt | 1.00 | - | - |
| `q09_flynn_plateau` | 3 | `fremdbelegt` | - | extern | - | 730000, 1975, 0.2, 7 | 730000, 1975, 0.2, 7 |
| `q10_max_iq_gain` | 2 | `hypothesis 29bd06f1f6cf` | `hypothesis d812f1a08fb2` | inhaltlich_ersetzt | 0.94 | - | - |
| `q10_max_iq_gain` | 3 | `fremdbelegt` | - | extern | - | 10, 2.5 | 10, 2.5 |
| `q10_max_iq_gain` | 4 | `fremdbelegt` | - | extern | - | 5, 2.5 | 5, 2.5 |

## Neue Claims ohne Vorgaenger

| Frage | Quelle | Befund |
|---|---|---|
| `q05_polygenic_scores` | `fact ecb0e511f62f` | neu |
| `q07_countries_selection` | `hypothesis 27ac1671a823` | neu |

## Entfallene Records

Diese Claims hatten im alten Set einen DB-Record, der in der aktuellen
Erhebung nicht mehr existiert; ein inhaltlich tragender Ersatz wurde nicht
gefunden. Sie stehen nicht mehr im Set (siehe `meta.entfallen`).

| Frage | Pos. | Quelle alt | Quelle neu | Befund | Abdeckung | Zahlen alt | Zahlen neu |
|---|---|---|---|---|---|---|---|
| `q01_wilson_effect` | 2 | `fact 7d1c1993f101` | - | entfallen | - | - | - |
| `q02_gwas_intelligence` | 3 | `fact 06303be4b52a` | - | entfallen | - | - | - |
| `q03_pgt_outcomes` | 1 | `fact 827fda9b9ec0` | - | entfallen | - | 20, 40 | - |
| `q03_pgt_outcomes` | 2 | `fact ca4928357e64` | - | entfallen | - | 1999, 2019 | - |
| `q05_polygenic_scores` | 1 | `fact aa3b0b2c55cc` | - | entfallen | - | - | - |
| `q05_polygenic_scores` | 2 | `fact bbce5fc3714a` | - | entfallen | - | - | - |
| `q06_cost_benefit` | 0 | `fact 44de162902d1` | - | entfallen | - | - | - |
| `q07_countries_selection` | 0 | `fact 48f98af3371f` | - | entfallen | - | - | - |
| `q07_countries_selection` | 1 | `hypothesis 6fd023b72d9c` | - | entfallen | - | - | - |
| `q08_transhumanist_ethics` | 1 | `hypothesis ed147da7e121` | - | entfallen | - | - | - |
| `q09_flynn_plateau` | 0 | `fact 44de162902d1` | - | entfallen | - | - | - |
| `q10_max_iq_gain` | 0 | `fact aa3b0b2c55cc` | - | entfallen | - | - | - |
| `q10_max_iq_gain` | 1 | `fact bbce5fc3714a` | - | entfallen | - | - | - |

## Zaehlung

- Claims alt: 40
- Claims neu: 29
- davon DB-verankert: 20
- entfallen: 13
