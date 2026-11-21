# Zaehlfelder: Armzuordnung oder fehlende Groessenzeile? (21.11.2026)

Offline, ohne Netzaufruf. Grundgesamtheit: alle `fn_wert_ersetzt` mit
`group_size` oder `events`, 127 von 295 Faellen
(40 + 40 Gruppengroessen,
21 + 26 Ereignisse).

## Verteilung

| Klasse | Faelle |
|---|---:|
| groessenzeile_richtiger_arm | 31 |
| groessenzeile_anderer_arm | 20 |
| spalte_nur_aus_kopfzeile | 6 |
| arm_nicht_bestimmbar | 22 |
| nur_nenner | 16 |
| nur_fliessetext | 32 |
| nicht_im_dokument | 0 |

`spalte_nur_aus_kopfzeile` heisst: die Groessenzeile nennt den Arm nicht selbst,
der Name kommt aus einer Kopfzeile darueber. Solche Faelle zaehlen nicht als
belegte Armzuordnung.

Zusaetzlich: in 0 Faellen entspricht die ausgegebene Zahl genau der
Zahl des anderen Arms in derselben Groessenzeile.

## Antwort

Beides, aber ungleich verteilt. In 31 der 127 Faelle (24 Prozent) steht der
Goldwert in einer selbstbeschrifteten Groessenzeile und in der Spalte des
richtigen Arms; dort ist weder die Zeile noch der Arm das Problem, sondern die
Auswahl der Zahl (yun2024:100: Gold 40, ausgegeben 453). In 48 Faellen (38
Prozent) fehlt die Groessenzeile ganz: 32 mal steht der Wert nur im Fliesstext,
16 mal nur als Nenner einer Proportion. Fuer diese Gruppe ist die fehlende
Groessenzeile das Problem, nicht die Armzuordnung. In 20 Faellen (16 Prozent)
steht der Wert in der Spalte des anderen Arms; diese Klasse ist aber nicht
sauber belegt, weil Beschriftungen wie `No text message` dieselben Woerter
tragen wie der Interventionsarm und die Zuordnung dadurch kippt (Sichtpruefung
yun2024:100). 28 Faelle (22 Prozent) sind ohne Armnamen in der Zeile nicht
entscheidbar oder nur ueber eine Kopfzeile zuzuordnen.

Ein Arm-Tausch der Vorhersage ist nicht belegbar: in keinem der 127 Faelle
entspricht die ausgegebene Zahl der Zahl des anderen Arms in derselben
Groessenzeile. Die Fehlwerte stammen aus anderen Tabellen oder aus
Prozentwerten.

## Lesart

`groessenzeile_richtiger_arm` heisst: die Zeile existiert und der Goldwert steht
in der Spalte, die der Gold-Armbeschriftung entspricht. Dann ist nicht die
Tabelle das Problem, sondern die Auswahl. `groessenzeile_anderer_arm` heisst:
der Wert steht in der Spalte des anderen Arms; das ist entweder ein Fehler in
der Goldbeschriftung oder ein Fehler in der Spaltenzuordnung der Regel.
`nur_fliessetext` heisst: es gibt keine Groessenzeile mit diesem Wert, er steht
nur im Satz.
