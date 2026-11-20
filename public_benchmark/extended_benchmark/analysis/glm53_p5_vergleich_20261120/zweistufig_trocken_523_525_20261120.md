# Zweistufiger Test, Stufe 1 trocken: yun2024:523, yun2024:525 (20.11.2026)

Kein Modellaufruf. Gebaut ist nur, was Stufe 1 bekommen wuerde: Ausschnitt, Prompt und Budget, dazu die Vorabpruefung, ob die Goldwerte ueberhaupt im Text stehen.

## Uebersicht

| Record | Dokument | Text | Ausschnitt | Anteil | Outcome-Treffer | Tabellenzeilen | Prompt | Goldwerte im Text |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `yun2024:523` | PMC5325897 | 6811 | 6000 | 88.1 % | 12 | 0 | 7137 | 4/6 |
| `yun2024:525` | PMC5325897 | 6811 | 6000 | 88.1 % | 4 | 0 | 7137 | 4/6 |

Budget je Aufruf: 2000 Completion-Tokens (statt 24.000 im Einzelaufruf). Prompt-Laenge je Record unten.

## yun2024:523

- Dokument: PMC5325897, Volltext 6811 Zeichen
- Outcome: First test results
- Zielzeitpunkt: primary time point of the trial (if not stated: the last reported time point)
- Ausschnitt: Zeichen 500 bis 6500, 6000 Zeichen (88.1 %)
- Prompt: 7137 Zeichen, geschaetzt 1784 Tokens

### Stehen die Goldwerte im Text?

| Feld | Arm | Goldwert | Volltext | Ausschnitt |
|---|---|---:|---:|---:|
| intervention_group_size | intervention | 15.0 | 0 | 0 |
| intervention_mean | intervention | 10.24 | 2 | 2 |
| intervention_standard_deviation | intervention | 0.77 | 4 | 4 |
| comparator_group_size | comparator | 15.0 | 0 | 0 |
| comparator_mean | comparator | 9.73 | 3 | 2 |
| comparator_standard_deviation | comparator | 0.77 | 4 | 4 |

4 von 6 Goldwerten stehen im Volltext, 2 nicht. Fehlt ein Wert im Volltext, kann ihn keine Stufe finden: die Tabelle steht im Markdown nur als Caption mit Bildplatzhalter.

### Ausschnitt

```markdown
s design and before-after method. They were randomly allocated to two groups (with or without feedback) and evaluated three times regarding chest ultrasonography for trauma patients, using direct observation of procedural skills (DOPS) and valid and reliable checklist. Data were analyzed using SPSS 20. ## Results: 30 emergency medicine residents with the mean age of 36.63 ± 30.30 years were allocated to two equal groups (56.7% male). Studied groups were similar regarding the baseline characteristics. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001). Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). ## Conclusion: Based on the findings of the present study, giving feedback after evaluating the second year emergency medicine residents regarding chest ultrasonography for trauma patients, led to a significant improvement in their scores in future evaluations and consequently their skill. # Results ***Baseline characteristics*** 30 emergency medicine residents with the mean age of 36.63 ± 30.30 (29 - 47) years participated (56.7% male). They were randomly allocated to either Loghman Hakim (group 1) or Imam Hossein hospitals (group 2). [Table 1](#) shows the baseline characteristics of the participants. The two studied groups were similar regarding the baseline characteristics. 25 (83.4%) residents performed chest ultrasonography more than five times (56.7% more than 10 times) and 25 (83.3%) residents believed that chest ultrasonography for trauma patients had medium to high difficulty level. ***Outcomes*** Mean scores of the residents in the first, second, and third evaluations were 10.00 ± 0.54, 14.93 ± 0.32, and 18.72 ± 0.15, respectively. [Figure 1](#) shows the scores obtained by the residents for the 3 evaluations done based on the hospital. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001) according to Greenhouse-Geisser Correction test. Mean score obtained for preparation, scan and post-scan items among all residents were 3.34 ± 0.91, 9.48 ± 3.16, and 1.72 ± 0.97, respectively. [Tables 2](#) and [3](#) compare the scores obtained by each group in the 3 tests qualitatively and quantitatively. Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). As can be seen, residents in Loghman Hakim Hospital were significantly better in the second exam both quantitatively and qualitatively. ::::table-wrap
::: caption
Baseline characteristics of participants
:::

  **Variable**                                   **Loghman Hakim**   **Imam Hossein**   **P**
  ---------------------------------------------- ------------------- ------------------ -------
  **Mean age (year)**                            34.93 ± 5.40        38.33 ± 5.23       0.091
  **Sex**                                                                               
  Male                                           9 (60)              8 (53.3)           0.71
  Female                                         6 (40)              7 (46.7)           
  **Background experience1(time)**                                                      
  1 -4                                           3 (20)              2 (13.3)           0.879
  5- 9                                           4 (26.7)            4 (26.7)           
  ≥ 10                                           8 (53.3)            9 (60)             
  **Background attitude** ^2^ **(difficulty)**                                          
  Low                                            4 (26.7)            1 (6.7)            0.241
  Medium                                         10 (66.7)           11 (73.3)          
  High                                           1 (6.7)             3 (20)             
  **Mean promotion exam score**^3^               81.06 ± 6.29        82.42 ± 6.27       0.565

Data were presented as mean ± standard deviation or frequency
(percentage);

1: Previous experience of chest ultrasonography;

2: Attitude of the resident regarding the difficulty of the procedure;

3: Score in exam taken for promotion from year 1 to year 2 of the
residency program (out of 100).:::: <figure> <p><img src="" /></p> <figcaption>Trend of scores (minimum 0 and maximum 20) in three evaluations of studied groups (p &lt; 0.001, based on Greenhouse-Geisser Correction</figcaption> </figure> ::::table-wrap
::: caption
Comparison of mean evaluation scores between groups
:::

  **Evaluation**             **Loghman Hakim**   **Imam Hossein**   **P-value**
  -------------------------- ------------------- ------------------ -------------
  **Preparation (0 -- 4)**                                          
  First                      3.00 ± 0.75         2.1 ± 0.92         0.009
  Second                     4.00 ± 0.00         3.00 ± 0.85        < 0.0001
  Third                      3.93 ± 0.26         4.00 ± 0.00        0.326
  **Scan (0 -- 13)**                                                
  First                      6.87 ± 2.39         6.27 ± 2.43        0.501
  Second                     11.60 ± 0.99        7.33 ± 1.95        < 0.001
  Third                      12.53 ± 0.74        12.26 ± 0.59       0.287
  **Post scan (0 -- 3)**                                            
  First                      0.40 ± 0.63         1.20 ± 0.67        0.002
  Second                     2.13 ± 0.35         1.80 ± 0.86        0.176
  Third                      2.53 ± 0.64         2.27 ± 0.71        0.287
  **Total (0 - 20)**                
```

### Prompt Stufe 1

```text
Publication excerpt:
s design and before-after method. They were randomly allocated to two groups (with or without feedback) and evaluated three times regarding chest ultrasonography for trauma patients, using direct observation of procedural skills (DOPS) and valid and reliable checklist. Data were analyzed using SPSS 20. ## Results: 30 emergency medicine residents with the mean age of 36.63 ± 30.30 years were allocated to two equal groups (56.7% male). Studied groups were similar regarding the baseline characteristics. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001). Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). ## Conclusion: Based on the findings of the present study, giving feedback after evaluating the second year emergency medicine residents regarding chest ultrasonography for trauma patients, led to a significant improvement in their scores in future evaluations and consequently their skill. # Results ***Baseline characteristics*** 30 emergency medicine residents with the mean age of 36.63 ± 30.30 (29 - 47) years participated (56.7% male). They were randomly allocated to either Loghman Hakim (group 1) or Imam Hossein hospitals (group 2). [Table 1](#) shows the baseline characteristics of the participants. The two studied groups were similar regarding the baseline characteristics. 25 (83.4%) residents performed chest ultrasonography more than five times (56.7% more than 10 times) and 25 (83.3%) residents believed that chest ultrasonography for trauma patients had medium to high difficulty level. ***Outcomes*** Mean scores of the residents in the first, second, and third evaluations were 10.00 ± 0.54, 14.93 ± 0.32, and 18.72 ± 0.15, respectively. [Figure 1](#) shows the scores obtained by the residents for the 3 evaluations done based on the hospital. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001) according to Greenhouse-Geisser Correction test. Mean score obtained for preparation, scan and post-scan items among all residents were 3.34 ± 0.91, 9.48 ± 3.16, and 1.72 ± 0.97, respectively. [Tables 2](#) and [3](#) compare the scores obtained by each group in the 3 tests qualitatively and quantitatively. Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). As can be seen, residents in Loghman Hakim Hospital were significantly better in the second exam both quantitatively and qualitatively. ::::table-wrap
::: caption
Baseline characteristics of participants
:::

  **Variable**                                   **Loghman Hakim**   **Imam Hossein**   **P**
  ---------------------------------------------- ------------------- ------------------ -------
  **Mean age (year)**                            34.93 ± 5.40        38.33 ± 5.23       0.091
  **Sex**                                                                               
  Male                                           9 (60)              8 (53.3)           0.71
  Female                                         6 (40)              7 (46.7)           
  **Background experience1(time)**                                                      
  1 -4                                           3 (20)              2 (13.3)           0.879
  5- 9                                           4 (26.7)            4 (26.7)           
  ≥ 10                                           8 (53.3)            9 (60)             
  **Background attitude** ^2^ **(difficulty)**                                          
  Low                                            4 (26.7)            1 (6.7)            0.241
  Medium                                         10 (66.7)           11 (73.3)          
  High                                           1 (6.7)             3 (20)             
  **Mean promotion exam score**^3^               81.06 ± 6.29        82.42 ± 6.27       0.565

Data were presented as mean ± standard deviation or frequency
(percentage);

1: Previous experience of chest ultrasonography;

2: Attitude of the resident regarding the difficulty of the procedure;

3: Score in exam taken for promotion from year 1 to year 2 of the
residency program (out of 100).:::: <figure> <p><img src="" /></p> <figcaption>Trend of scores (minimum 0 and maximum 20) in three evaluations of studied groups (p &lt; 0.001, based on Greenhouse-Geisser Correction</figcaption> </figure> ::::table-wrap
::: caption
Comparison of mean evaluation scores between groups
:::

  **Evaluation**             **Loghman Hakim**   **Imam Hossein**   **P-value**
  -------------------------- ------------------- ------------------ -------------
  **Preparation (0 -- 4)**                                          
  First                      3.00 ± 0.75         2.1 ± 0.92         0.009
  Second                     4.00 ± 0.00         3.00 ± 0.85        < 0.0001
  Third                      3.93 ± 0.26         4.00 ± 0.00        0.326
  **Scan (0 -- 13)**                                                
  First                      6.87 ± 2.39         6.27 ± 2.43        0.501
  Second                     11.60 ± 0.99        7.33 ± 1.95        < 0.001
  Third                      12.53 ± 0.74        12.26 ± 0.59       0.287
  **Post scan (0 -- 3)**                                            
  First                      0.40 ± 0.63         1.20 ± 0.67        0.002
  Second                     2.13 ± 0.35         1.80 ± 0.86        0.176
  Third                      2.53 ± 0.64         2.27 ± 0.71        0.287
  **Total (0 - 20)**                

Intervention: Evaluation with feedback
Comparator: Evaluation without feedback
Outcome: First test results
Outcome type: continuous
Target time point (binding): "primary time point of the trial (if not stated: the last reported time point)".

Read no numbers. Only locate where the outcome is reported at the target time point.
Name, for each arm, the exact row label (the outcome line as printed), the exact column header of that arm as printed, the caption of the table or the paragraph, and the time point label as printed.
If the excerpt does not report the outcome at the target time point for an arm, set "found": false for that arm and leave the labels empty. Do not guess a row.
If the outcome is reported in several rows (subgroups, populations), choose the row that matches the arms named in the request.

Return exactly one JSON object:
{"locators": [{"arm": "intervention" | "comparator", "row_label": "<as printed>", "column_header": "<as printed>", "caption": "<caption or short paragraph label>", "timepoint": "<as printed>", "found": true}, ...]}
No numbers. No commentary, markdown or code fences.
```

## yun2024:525

- Dokument: PMC5325897, Volltext 6811 Zeichen
- Outcome: Final test results
- Zielzeitpunkt: primary time point of the trial (if not stated: the last reported time point)
- Ausschnitt: Zeichen 500 bis 6500, 6000 Zeichen (88.1 %)
- Prompt: 7137 Zeichen, geschaetzt 1784 Tokens

### Stehen die Goldwerte im Text?

| Feld | Arm | Goldwert | Volltext | Ausschnitt |
|---|---|---:|---:|---:|
| intervention_group_size | intervention | 15.0 | 0 | 0 |
| intervention_mean | intervention | 18.53 | 3 | 2 |
| intervention_standard_deviation | intervention | 0.22 | 4 | 4 |
| comparator_group_size | comparator | 15.0 | 0 | 0 |
| comparator_mean | comparator | 18.99 | 2 | 2 |
| comparator_standard_deviation | comparator | 0.22 | 4 | 4 |

4 von 6 Goldwerten stehen im Volltext, 2 nicht. Fehlt ein Wert im Volltext, kann ihn keine Stufe finden: die Tabelle steht im Markdown nur als Caption mit Bildplatzhalter.

### Ausschnitt

```markdown
s design and before-after method. They were randomly allocated to two groups (with or without feedback) and evaluated three times regarding chest ultrasonography for trauma patients, using direct observation of procedural skills (DOPS) and valid and reliable checklist. Data were analyzed using SPSS 20. ## Results: 30 emergency medicine residents with the mean age of 36.63 ± 30.30 years were allocated to two equal groups (56.7% male). Studied groups were similar regarding the baseline characteristics. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001). Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). ## Conclusion: Based on the findings of the present study, giving feedback after evaluating the second year emergency medicine residents regarding chest ultrasonography for trauma patients, led to a significant improvement in their scores in future evaluations and consequently their skill. # Results ***Baseline characteristics*** 30 emergency medicine residents with the mean age of 36.63 ± 30.30 (29 - 47) years participated (56.7% male). They were randomly allocated to either Loghman Hakim (group 1) or Imam Hossein hospitals (group 2). [Table 1](#) shows the baseline characteristics of the participants. The two studied groups were similar regarding the baseline characteristics. 25 (83.4%) residents performed chest ultrasonography more than five times (56.7% more than 10 times) and 25 (83.3%) residents believed that chest ultrasonography for trauma patients had medium to high difficulty level. ***Outcomes*** Mean scores of the residents in the first, second, and third evaluations were 10.00 ± 0.54, 14.93 ± 0.32, and 18.72 ± 0.15, respectively. [Figure 1](#) shows the scores obtained by the residents for the 3 evaluations done based on the hospital. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001) according to Greenhouse-Geisser Correction test. Mean score obtained for preparation, scan and post-scan items among all residents were 3.34 ± 0.91, 9.48 ± 3.16, and 1.72 ± 0.97, respectively. [Tables 2](#) and [3](#) compare the scores obtained by each group in the 3 tests qualitatively and quantitatively. Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). As can be seen, residents in Loghman Hakim Hospital were significantly better in the second exam both quantitatively and qualitatively. ::::table-wrap
::: caption
Baseline characteristics of participants
:::

  **Variable**                                   **Loghman Hakim**   **Imam Hossein**   **P**
  ---------------------------------------------- ------------------- ------------------ -------
  **Mean age (year)**                            34.93 ± 5.40        38.33 ± 5.23       0.091
  **Sex**                                                                               
  Male                                           9 (60)              8 (53.3)           0.71
  Female                                         6 (40)              7 (46.7)           
  **Background experience1(time)**                                                      
  1 -4                                           3 (20)              2 (13.3)           0.879
  5- 9                                           4 (26.7)            4 (26.7)           
  ≥ 10                                           8 (53.3)            9 (60)             
  **Background attitude** ^2^ **(difficulty)**                                          
  Low                                            4 (26.7)            1 (6.7)            0.241
  Medium                                         10 (66.7)           11 (73.3)          
  High                                           1 (6.7)             3 (20)             
  **Mean promotion exam score**^3^               81.06 ± 6.29        82.42 ± 6.27       0.565

Data were presented as mean ± standard deviation or frequency
(percentage);

1: Previous experience of chest ultrasonography;

2: Attitude of the resident regarding the difficulty of the procedure;

3: Score in exam taken for promotion from year 1 to year 2 of the
residency program (out of 100).:::: <figure> <p><img src="" /></p> <figcaption>Trend of scores (minimum 0 and maximum 20) in three evaluations of studied groups (p &lt; 0.001, based on Greenhouse-Geisser Correction</figcaption> </figure> ::::table-wrap
::: caption
Comparison of mean evaluation scores between groups
:::

  **Evaluation**             **Loghman Hakim**   **Imam Hossein**   **P-value**
  -------------------------- ------------------- ------------------ -------------
  **Preparation (0 -- 4)**                                          
  First                      3.00 ± 0.75         2.1 ± 0.92         0.009
  Second                     4.00 ± 0.00         3.00 ± 0.85        < 0.0001
  Third                      3.93 ± 0.26         4.00 ± 0.00        0.326
  **Scan (0 -- 13)**                                                
  First                      6.87 ± 2.39         6.27 ± 2.43        0.501
  Second                     11.60 ± 0.99        7.33 ± 1.95        < 0.001
  Third                      12.53 ± 0.74        12.26 ± 0.59       0.287
  **Post scan (0 -- 3)**                                            
  First                      0.40 ± 0.63         1.20 ± 0.67        0.002
  Second                     2.13 ± 0.35         1.80 ± 0.86        0.176
  Third                      2.53 ± 0.64         2.27 ± 0.71        0.287
  **Total (0 - 20)**                
```

### Prompt Stufe 1

```text
Publication excerpt:
s design and before-after method. They were randomly allocated to two groups (with or without feedback) and evaluated three times regarding chest ultrasonography for trauma patients, using direct observation of procedural skills (DOPS) and valid and reliable checklist. Data were analyzed using SPSS 20. ## Results: 30 emergency medicine residents with the mean age of 36.63 ± 30.30 years were allocated to two equal groups (56.7% male). Studied groups were similar regarding the baseline characteristics. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001). Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). ## Conclusion: Based on the findings of the present study, giving feedback after evaluating the second year emergency medicine residents regarding chest ultrasonography for trauma patients, led to a significant improvement in their scores in future evaluations and consequently their skill. # Results ***Baseline characteristics*** 30 emergency medicine residents with the mean age of 36.63 ± 30.30 (29 - 47) years participated (56.7% male). They were randomly allocated to either Loghman Hakim (group 1) or Imam Hossein hospitals (group 2). [Table 1](#) shows the baseline characteristics of the participants. The two studied groups were similar regarding the baseline characteristics. 25 (83.4%) residents performed chest ultrasonography more than five times (56.7% more than 10 times) and 25 (83.3%) residents believed that chest ultrasonography for trauma patients had medium to high difficulty level. ***Outcomes*** Mean scores of the residents in the first, second, and third evaluations were 10.00 ± 0.54, 14.93 ± 0.32, and 18.72 ± 0.15, respectively. [Figure 1](#) shows the scores obtained by the residents for the 3 evaluations done based on the hospital. In both groups, obtained scores showed a significant increase from the first to the third evaluation (p < 0.001) according to Greenhouse-Geisser Correction test. Mean score obtained for preparation, scan and post-scan items among all residents were 3.34 ± 0.91, 9.48 ± 3.16, and 1.72 ± 0.97, respectively. [Tables 2](#) and [3](#) compare the scores obtained by each group in the 3 tests qualitatively and quantitatively. Mean scores of first and second evaluations were 10.24 ± 0.77, 17.73 ± 0.46 in feedback receivers and 9.73 ± 0.77 and 12.13 ± 0.47 in others (p < 0.001). Mean third score after switching groups were 18.53 ± 0.22 in feedback receivers and 18.99 ± 0.22 in others (p = 0.213). As can be seen, residents in Loghman Hakim Hospital were significantly better in the second exam both quantitatively and qualitatively. ::::table-wrap
::: caption
Baseline characteristics of participants
:::

  **Variable**                                   **Loghman Hakim**   **Imam Hossein**   **P**
  ---------------------------------------------- ------------------- ------------------ -------
  **Mean age (year)**                            34.93 ± 5.40        38.33 ± 5.23       0.091
  **Sex**                                                                               
  Male                                           9 (60)              8 (53.3)           0.71
  Female                                         6 (40)              7 (46.7)           
  **Background experience1(time)**                                                      
  1 -4                                           3 (20)              2 (13.3)           0.879
  5- 9                                           4 (26.7)            4 (26.7)           
  ≥ 10                                           8 (53.3)            9 (60)             
  **Background attitude** ^2^ **(difficulty)**                                          
  Low                                            4 (26.7)            1 (6.7)            0.241
  Medium                                         10 (66.7)           11 (73.3)          
  High                                           1 (6.7)             3 (20)             
  **Mean promotion exam score**^3^               81.06 ± 6.29        82.42 ± 6.27       0.565

Data were presented as mean ± standard deviation or frequency
(percentage);

1: Previous experience of chest ultrasonography;

2: Attitude of the resident regarding the difficulty of the procedure;

3: Score in exam taken for promotion from year 1 to year 2 of the
residency program (out of 100).:::: <figure> <p><img src="" /></p> <figcaption>Trend of scores (minimum 0 and maximum 20) in three evaluations of studied groups (p &lt; 0.001, based on Greenhouse-Geisser Correction</figcaption> </figure> ::::table-wrap
::: caption
Comparison of mean evaluation scores between groups
:::

  **Evaluation**             **Loghman Hakim**   **Imam Hossein**   **P-value**
  -------------------------- ------------------- ------------------ -------------
  **Preparation (0 -- 4)**                                          
  First                      3.00 ± 0.75         2.1 ± 0.92         0.009
  Second                     4.00 ± 0.00         3.00 ± 0.85        < 0.0001
  Third                      3.93 ± 0.26         4.00 ± 0.00        0.326
  **Scan (0 -- 13)**                                                
  First                      6.87 ± 2.39         6.27 ± 2.43        0.501
  Second                     11.60 ± 0.99        7.33 ± 1.95        < 0.001
  Third                      12.53 ± 0.74        12.26 ± 0.59       0.287
  **Post scan (0 -- 3)**                                            
  First                      0.40 ± 0.63         1.20 ± 0.67        0.002
  Second                     2.13 ± 0.35         1.80 ± 0.86        0.176
  Third                      2.53 ± 0.64         2.27 ± 0.71        0.287
  **Total (0 - 20)**                

Intervention: Evaluation with feedback
Comparator: Evaluation without feedback
Outcome: Final test results
Outcome type: continuous
Target time point (binding): "primary time point of the trial (if not stated: the last reported time point)".

Read no numbers. Only locate where the outcome is reported at the target time point.
Name, for each arm, the exact row label (the outcome line as printed), the exact column header of that arm as printed, the caption of the table or the paragraph, and the time point label as printed.
If the excerpt does not report the outcome at the target time point for an arm, set "found": false for that arm and leave the labels empty. Do not guess a row.
If the outcome is reported in several rows (subgroups, populations), choose the row that matches the arms named in the request.

Return exactly one JSON object:
{"locators": [{"arm": "intervention" | "comparator", "row_label": "<as printed>", "column_header": "<as printed>", "caption": "<caption or short paragraph label>", "timepoint": "<as printed>", "found": true}, ...]}
No numbers. No commentary, markdown or code fences.
```

## Vorbehalt

Die Fensterwahl ist eine Heuristik (Outcome-Treffer, Tabellenzeilen, Ziffern), kein Modell. Ob der Ausschnitt die richtige Zeile enthaelt, entscheidet erst Stufe 1; ob Stufe 1 ihn richtig liest, erst der Aufruf.
