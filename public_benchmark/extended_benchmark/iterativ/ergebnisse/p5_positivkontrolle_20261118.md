# Positivkontrolle der P5-Auswertung

Erfundene Prediction-Datei mit vorher ausgerechneten Sollwerten. Die Zahlen unten sind von Hand bestimmt, nicht aus dem Skript abgeleitet; das Skript vergleicht nur.

Fixture: `extended_benchmark/iterativ/kontrolle/p5_positivkontrolle/alt.jsonl` und `extended_benchmark/iterativ/kontrolle/p5_positivkontrolle/neu.jsonl`.

## Soll und Ist

| Groesse | Soll | Ist |
|---|---:|---:|
| `grundgesamtheit` | 8 | 8 |
| `ids_ohne_altzeile` | [] | [] |
| `status` | {'gerettet': 5, 'fertig_ohne_zellen': 1, 'weiter_ausfall': 1, 'fehlt': 1} | {'gerettet': 5, 'fertig_ohne_zellen': 1, 'weiter_ausfall': 1, 'fehlt': 1} |
| `stufen` | {'ids': 8, 'technisch': 6, 'auswertbar': 5, 'inhaltlich': 3, 'inhaltlich_zeitpunkt': 2} | {'ids': 8, 'technisch': 6, 'auswertbar': 5, 'inhaltlich': 3, 'inhaltlich_zeitpunkt': 2} |
| `zellen_neu` | 9 | 9 |
| `zellen_neu_mit_zeitpunkt` | 9 | 9 |
| `goldzellen_bewertbar` | 11 | 11 |
| `goldzellen_mit_zeitpunkt` | 0 | 0 |
| `adressiert` | 7 | 7 |
| `adressiert_zeitpunkt` | 6 | 6 |
| `wertgleich` | 5 | 5 |
| `wertgleich_zeitpunkt` | 4 | 4 |
| `zeitpunkt_mehrdeutig` | 1 | 1 |

### Klasse `length_ohne_ergebnis`

| Groesse | Soll | Ist |
|---|---:|---:|
| `ids` | 7 | 7 |
| `technisch` | 5 | 5 |
| `auswertbar` | 4 | 4 |
| `leer` | 1 | 1 |
| `weiter_ausfall` | 1 | 1 |
| `fehlt` | 1 | 1 |
| `goldzellen` | 10 | 10 |
| `adressiert` | 6 | 6 |
| `adressiert_zeitpunkt` | 5 | 5 |
| `wertgleich` | 4 | 4 |
| `wertgleich_zeitpunkt` | 3 | 3 |

### Klasse `json_kaputt`

| Groesse | Soll | Ist |
|---|---:|---:|
| `ids` | 1 | 1 |
| `technisch` | 1 | 1 |
| `auswertbar` | 1 | 1 |
| `leer` | 0 | 0 |
| `weiter_ausfall` | 0 | 0 |
| `fehlt` | 0 | 0 |
| `goldzellen` | 1 | 1 |
| `adressiert` | 1 | 1 |
| `adressiert_zeitpunkt` | 1 | 1 |
| `wertgleich` | 1 | 1 |
| `wertgleich_zeitpunkt` | 1 | 1 |

## Ergebnis

**Alle 13 Kennzahlen und 22 Klassenzahlen stimmen.**

Was die Kontrolle abdeckt: richtige Zellen, Schluessel ohne richtigen Wert, eine leere Antwort, ein weiter ausgefallener Record, ein fehlender Record, ein Record ohne Goldzellen und eine Vorhersage mit zwei Zeitpunkten auf demselben Feld/Arm-Schluessel. Genau dort muss die grosszuegige Zaehlung einen Treffer melden und die strenge keinen.

