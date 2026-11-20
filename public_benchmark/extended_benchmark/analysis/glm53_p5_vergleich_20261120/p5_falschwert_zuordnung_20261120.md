# Die 67 einzelnen Falschwert-Zellen: Zuordnung oder Lesefehler? (20.11.2026)

Rein lesend, kein Modellaufruf. Auswahl wie beim Dublettenfilter: eine Zelle, die im 1:1-Verbrauch uebrig bleibt, deren (Feld, Arm) im Gold des Records vorkommt und die im selben (Feld, Arm) die einzige Vorhersagezelle ist. Genau diese 67 Zellen machen zusammen mit 13 Mehrfach- und 17 Fremdschluesselzellen die 97 falschen Zellen der P5-Basis aus.

## Ergebnis

| Klasse | Zellen | Bedeutung |
|---|---:|---|
| `zuordnung_arm` | 0 | Wert ist Goldwert desselben Feldes im anderen Arm |
| `zuordnung_feld` | 0 | Wert ist Goldwert eines anderen Feldes im selben Arm |
| `zuordnung_beides` | 4 | Feld und Arm weichen ab |
| `wert_im_text` | 63 | Wert steht im Text, gehoert aber zu keinem Goldslot des Records |
| `nicht_im_text` | 0 | Wert steht so nicht im Text |

**Zuordnung insgesamt: 4 von 67 Zellen.** In 3 dieser Faelle ist der Zielslot im Lauf noch offen, eine reine Zuordnungsregel gewinnt dort also einen Treffer. In 1 der Faelle ist der Zielslot bereits richtig gefuellt; eine Umhaengung wuerde dort nur eine Dublette erzeugen.

## Wie belastbar ist "steht im Text"?

- 22 der 63 Zellen haben genau einen Treffer im Dokument, 27 zwei bis drei Treffer, 14 mehr als drei. Bei einem einmaligen Treffer in einem 10.000-Zeichen-Dokument ist der Beleg stark.
- 9 Zellen tragen einen kleinen Integer (Betrag unter 100), der im Text mehr als dreimal vorkommt. Dort ist "steht im Text" fast automatisch wahr und traegt keine Aussage; diese Zellen zaehlen mit, sind aber schwach belegt.
- Die grossen Werte sind dagegen eindeutig: 922 und 919 in `yun2024:362` sowie 769 und 667 in `yun2024:615` bis `:617` stehen je nur zweimal im Dokument und treffen keine Goldzelle.
- Der Zahlenvergleich liest Trennzeichen nur dann als Tausendertrenner, wenn jede Gruppe nach der ersten genau drei Ziffern hat; `7.69` ist damit 7,69 und nicht 769. Eine fruehere Fassung dieses Skripts hatte genau diesen Fehler und machte aus `7.69` die 769.
- Nach der Verschaerfung bleiben alle 63 Textfaelle bestaetigt; 12 Zellen verlieren Treffer, keine verliert den Beleg. Die vier grossen Werte stehen als ganze Zahlen im Text (`n = 922`, `n = 919`, 769 Frauen, 667 Frauen), nicht als Dezimalzahl.
- 63 der 63 Textfaelle haben mindestens einen eindeutigen Treffer; keiner haengt an einer mehrdeutigen Tausender-Lesart wie `1.234` (1,234 oder 1.234).
- Jede Bestaetigung traegt ihre Fundstelle im JSON (`beleg_stellen`); die 22 Zellen mit genau einem Treffer sind im Anhang mit Textzitat aufgefuehrt.

## Was eine korrigierte Zuordnung an den Kennzahlen aendert

Werden die 3 eindeutigen Zuordnungsfaelle umgehaengt, steigt TP von 170 auf 173, FP faellt von 97 auf 94, FN von 253 auf 250. Precision 0.6367 -> 0.6479, Recall 0.4019 -> 0.4090, F1 0.4928 -> 0.5014 (+0.87 Prozentpunkte). Das ist der gesamte Hebel einer reinen Zuordnungsregel auf diesem Lauf.

## Was das fuer eine Regel bedeutet

- 4 Zellen sind reine Zuordnungsfehler: die Zahl wurde richtig gelesen und am falschen Feld oder Arm abgelegt. Das ist die einzige Gruppe, die eine Zuordnungsregel ohne neues Lesen erreichen kann.
- 63 Zellen tragen eine Zahl, die im Text steht, aber zu keinem Goldslot des Records passt: anderer Zeitpunkt, andere Tabellenzeile, Untergruppe oder eine Zahl aus dem Fliesstext. Diese Gruppe braucht eine Zeilen- oder Zeitpunktregel, keine Zuordnungsregel.
- 0 Zellen tragen eine Zahl, die so nicht im Text steht. Das sind Umrechnungen, gerechnete Werte oder Lesefehler; sie sind ohne erneuten Modellaufruf nicht reparierbar.
- Die Klassifikation stuetzt sich auf das Gold als Referenz fuer Feld und Arm. Sie zeigt, wohin der Wert gehoert, nicht warum das Modell ihn dort abgelegt hat.
- Ein Grenzfall in der Zuordnungsgruppe ist `yun2024:558`: gedruckt 16,0 fuer `intervention_mean` (Gold -4,0), und 16 ist zugleich die comparator-Gruppengroesse. Bei einem solchen kleinen Integer kann die Uebereinstimmung Zufall sein; der Fall zaehlt formal als Zuordnung, ist aber nicht belegt. Belastbar sind die drei Faelle in `yun2024:113` (459 gegen 456, beide Arme vertauscht) und `yun2024:291` (12,8 statt 9,8, Wert der intervention-SD).

## Alle 67 Zellen

| Record | Feld | Arm | gedruckt | Gold | im Text | Wert steht im Gold bei | Klasse | Ziel offen |
|---|---|---|---:|---:|---|---|---|---|
| `yun2024:110` | intervention_group_size | intervention | 456.0 | 459.0 | ja | - | wert_im_text | nein |
| `yun2024:110` | intervention_mean | intervention | 2.42 | 2.5 | ja | - | wert_im_text | nein |
| `yun2024:110` | comparator_mean | comparator | 3.06 | 2.84 | ja | - | wert_im_text | nein |
| `yun2024:113` | intervention_group_size | intervention | 459.0 | 456.0 | ja | comparator_group_size/comparator | zuordnung_beides | ja |
| `yun2024:113` | comparator_group_size | comparator | 456.0 | 459.0 | ja | intervention_group_size/intervention | zuordnung_beides | ja |
| `yun2024:113` | intervention_mean | intervention | 170.63 | 167.61 | ja | - | wert_im_text | nein |
| `yun2024:113` | comparator_mean | comparator | 180.34 | 173.28 | ja | - | wert_im_text | nein |
| `yun2024:114` | intervention_group_size | intervention | 459.0 | 456.0 | ja | - | wert_im_text | nein |
| `yun2024:114` | intervention_mean | intervention | 2.22 | 2.17 | ja | - | wert_im_text | nein |
| `yun2024:114` | comparator_mean | comparator | 2.05 | 2.0 | ja | - | wert_im_text | nein |
| `yun2024:120` | intervention_group_size | intervention | 30.0 | 20.0 | ja | - | wert_im_text | nein |
| `yun2024:120` | comparator_group_size | comparator | 52.0 | 44.0 | ja | - | wert_im_text | nein |
| `yun2024:130` | intervention_events | intervention | 5.0 | 11.0 | ja | - | wert_im_text | nein |
| `yun2024:149` | intervention_mean | intervention | 145.0 | 138.0 | ja | - | wert_im_text | nein |
| `yun2024:158` | intervention_mean | intervention | 55.22 | 55.91 | ja | - | wert_im_text | nein |
| `yun2024:158` | intervention_standard_deviation | intervention | 12.51 | 15.64 | ja | - | wert_im_text | nein |
| `yun2024:158` | comparator_mean | comparator | 55.96 | 56.48 | ja | - | wert_im_text | nein |
| `yun2024:158` | comparator_standard_deviation | comparator | 12.6 | 14.76 | ja | - | wert_im_text | nein |
| `yun2024:161` | intervention_mean | intervention | 60.52 | 61.08 | ja | - | wert_im_text | nein |
| `yun2024:161` | intervention_standard_deviation | intervention | 12.72 | 15.15 | ja | - | wert_im_text | nein |
| `yun2024:161` | comparator_mean | comparator | 61.5 | 61.94 | ja | - | wert_im_text | nein |
| `yun2024:161` | comparator_standard_deviation | comparator | 13.23 | 14.25 | ja | - | wert_im_text | nein |
| `yun2024:162` | intervention_standard_deviation | intervention | 4.06 | 6.22 | ja | - | wert_im_text | nein |
| `yun2024:162` | comparator_standard_deviation | comparator | 4.33 | 5.68 | ja | - | wert_im_text | nein |
| `yun2024:291` | intervention_standard_deviation | intervention | 14.0 | 12.8 | ja | - | wert_im_text | nein |
| `yun2024:291` | comparator_mean | comparator | 42.8 | 46.5 | ja | - | wert_im_text | nein |
| `yun2024:291` | comparator_standard_deviation | comparator | 12.8 | 9.8 | ja | intervention_standard_deviation/intervention | zuordnung_beides | ja |
| `yun2024:313` | intervention_events | intervention | 100.0 | 22.0 | ja | - | wert_im_text | nein |
| `yun2024:313` | comparator_events | comparator | 80.0 | 16.0 | ja | - | wert_im_text | nein |
| `yun2024:347` | intervention_group_size | intervention | 5.0 | 22.0 | ja | - | wert_im_text | nein |
| `yun2024:347` | comparator_group_size | comparator | 5.0 | 22.0 | ja | - | wert_im_text | nein |
| `yun2024:357` | intervention_group_size | intervention | 21.0 | 13.0 | ja | - | wert_im_text | nein |
| `yun2024:357` | comparator_group_size | comparator | 20.0 | 13.0 | ja | - | wert_im_text | nein |
| `yun2024:362` | intervention_group_size | intervention | 919.0 | 720.0 | ja | - | wert_im_text | nein |
| `yun2024:362` | comparator_group_size | comparator | 922.0 | 682.0 | ja | - | wert_im_text | nein |
| `yun2024:380` | intervention_events | intervention | 79.0 | 47.0 | ja | - | wert_im_text | nein |
| `yun2024:380` | comparator_events | comparator | 29.0 | 19.0 | ja | - | wert_im_text | nein |
| `yun2024:427` | intervention_group_size | intervention | 48.0 | 44.0 | ja | - | wert_im_text | nein |
| `yun2024:427` | comparator_group_size | comparator | 55.0 | 49.0 | ja | - | wert_im_text | nein |
| `yun2024:533` | intervention_group_size | intervention | 34.0 | 37.0 | ja | - | wert_im_text | nein |
| `yun2024:533` | comparator_group_size | comparator | 30.0 | 35.0 | ja | - | wert_im_text | nein |
| `yun2024:556` | intervention_mean | intervention | 14.0 | -17.1 | ja | - | wert_im_text | nein |
| `yun2024:556` | intervention_standard_deviation | intervention | 29.0 | 68.08 | ja | - | wert_im_text | nein |
| `yun2024:556` | comparator_mean | comparator | 18.0 | -19.57 | ja | - | wert_im_text | nein |
| `yun2024:556` | comparator_standard_deviation | comparator | 25.0 | 93.53 | ja | - | wert_im_text | nein |
| `yun2024:558` | intervention_mean | intervention | 16.0 | -4.0 | ja | comparator_group_size/comparator | zuordnung_beides | nein |
| `yun2024:558` | intervention_standard_deviation | intervention | 26.0 | 12.35 | ja | - | wert_im_text | nein |
| `yun2024:558` | comparator_mean | comparator | 15.0 | -8.0 | ja | - | wert_im_text | nein |
| `yun2024:558` | comparator_standard_deviation | comparator | 41.0 | 65.41 | ja | - | wert_im_text | nein |
| `yun2024:615` | intervention_group_size | intervention | 769.0 | 754.0 | ja | - | wert_im_text | nein |
| `yun2024:615` | comparator_group_size | comparator | 667.0 | 656.0 | ja | - | wert_im_text | nein |
| `yun2024:616` | intervention_group_size | intervention | 769.0 | 754.0 | ja | - | wert_im_text | nein |
| `yun2024:616` | comparator_group_size | comparator | 667.0 | 656.0 | ja | - | wert_im_text | nein |
| `yun2024:617` | intervention_group_size | intervention | 769.0 | 754.0 | ja | - | wert_im_text | nein |
| `yun2024:617` | comparator_group_size | comparator | 667.0 | 656.0 | ja | - | wert_im_text | nein |
| `yun2024:626` | intervention_events | intervention | 2.5 | 2.0 | ja | - | wert_im_text | nein |
| `yun2024:626` | comparator_events | comparator | 3.7 | 3.0 | ja | - | wert_im_text | nein |
| `yun2024:668` | intervention_mean | intervention | 44.3 | 194.3 | ja | - | wert_im_text | nein |
| `yun2024:668` | intervention_standard_deviation | intervention | 45.4 | 63.1 | ja | - | wert_im_text | nein |
| `yun2024:668` | comparator_mean | comparator | 1.1 | 181.8 | ja | - | wert_im_text | nein |
| `yun2024:668` | comparator_standard_deviation | comparator | 43.3 | 61.3 | ja | - | wert_im_text | nein |
| `yun2024:686` | intervention_group_size | intervention | 34.0 | 17.0 | ja | - | wert_im_text | nein |
| `yun2024:686` | comparator_group_size | comparator | 34.0 | 17.0 | ja | - | wert_im_text | nein |
| `yun2024:84` | intervention_events | intervention | 2.3 | 178.0 | ja | - | wert_im_text | nein |
| `yun2024:84` | comparator_events | comparator | 1.8 | 124.0 | ja | - | wert_im_text | nein |
| `yun2024:86` | intervention_events | intervention | 0.1 | 773.0 | ja | - | wert_im_text | nein |
| `yun2024:86` | comparator_events | comparator | 0.1 | 689.0 | ja | - | wert_im_text | nein |

## Anhang: Fundstellen der einmaligen Belege

Je Zelle der erste Treffer im Markdown, 40 Zeichen davor bis 25 Zeichen danach.

| Record | Feld | gedruckt | Fundstelle im Text |
|---|---|---:|---|
| `yun2024:110` | intervention_mean | 2.42 | ...(3.76) 17.10 2.42 (0.13) --0.86... |
| `yun2024:110` | comparator_mean | 3.06 | ...(3.71) 5.37 3.06 (0.13) --0.15... |
| `yun2024:113` | intervention_mean | 170.63 | ...) 0.39 170.63 (3.81) 11... |
| `yun2024:113` | comparator_mean | 180.34 | ...) 0.32 180.34 (3.76) 17... |
| `yun2024:114` | intervention_mean | 2.22 | ...Plus 2.22 (0.07) 0.39... |
| `yun2024:114` | comparator_mean | 2.05 | ...Control 2.05 (0.07) 0.24... |
| `yun2024:149` | intervention_mean | 145.0 | ...720 Postop 1st month 145 (113--220) -... |
| `yun2024:158` | intervention_mean | 55.22 | ...55.96 (12.60) 55.22 (12.51) 61.... |
| `yun2024:158` | intervention_standard_deviation | 12.51 | ...55.96 (12.60) 55.22 (12.51) 61.50 (13.... |
| `yun2024:158` | comparator_mean | 55.96 | ....05) 49.43 (11.05) 55.96 (12.60) 55.2... |
| `yun2024:158` | comparator_standard_deviation | 12.6 | ...49.43 (11.05) 55.96 (12.60) 55.22 (12.5... |
| `yun2024:161` | intervention_mean | 60.52 | ....51) 61.50 (13.23) 60.52 (12.72) BMI[j](#)... |
| `yun2024:161` | intervention_standard_deviation | 12.72 | ...61.50 (13.23) 60.52 (12.72) BMI[j](#)... |
| `yun2024:161` | comparator_mean | 61.5 | ...55.22 (12.51) 61.50 (13.23) 60.52 (1... |
| `yun2024:161` | comparator_standard_deviation | 13.23 | ...55.22 (12.51) 61.50 (13.23) 60.52 (12.72)... |
| `yun2024:162` | intervention_standard_deviation | 4.06 | ...21.90 (4.33) 21.64 (4.06) BMI *z*-score[k](#)... |
| `yun2024:162` | comparator_standard_deviation | 4.33 | ...20.77 (3.96) 21.90 (4.33) 21.64 (4.06)... |
| `yun2024:558` | comparator_standard_deviation | 41.0 | ...ed 16% (±26) in the soy group and 15% (±41) in the placebo group (*... |
| `yun2024:626` | intervention_events | 2.5 | ...compliance, 9.9% 'well' compliance and 2.5% 'poor' compliance. In t... |
| `yun2024:626` | comparator_events | 3.7 | ...compliance rates were 91.4%, 4.6%, and 3.7%, respectively ([Table 2... |
| `yun2024:668` | intervention_standard_deviation | 45.4 | ...0.903 44.3 ± 45.4 <0.001^f... |
| `yun2024:668` | comparator_standard_deviation | 43.3 | ...^e^ Triglycerides (mg/dl) 1.1 ± 43.3 0.903... |
