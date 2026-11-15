# Length-Diagnose `yun_test186_v6_20261115`

Erzeugt von `laenge_diagnose.py` ohne API-Aufrufe. Merkmale am Median geteilt,
p-Werte aus dem exakten zweiseitigen Fisher-Test (bei mehr als zwei Gruppen:
auffaelligste Gruppe gegen den Rest). Mehrere Merkmale sind Mehrfachvergleiche.

* Zeilen: **186**, davon gueltig 139, Length-Ausfaelle **47** (25.3%)
* Tokens gueltiger Zeilen: p50 4425, p90 12091, p95 14730, max 24000, Mittel 5702
* Limit-Empfehlung (1,25 x p95, mindestens 10.000): **19000**
* Ausfaelle kosteten 792000 Tokens (46.2% aller Tokens), je Ausfall 16851
* Goldzellen in Ausfaellen: 133 von 566 (23.5%)
* Erwartung je Record: 10326 Tokens
* Gueltige Antworten innerhalb von 5 % am hoechsten Limit: 3 von 139

| Merkmal | Gruppe | Zeilen | Ausfaelle | Quote | p |
|---|---|---|---|---|---|
| zieltyp | baseline | 104 | 19 | 18.3% | 0.0069 |
| zieltyp | day | 13 | 3 | 23.1% | 0.0069 |
| zieltyp | month | 27 | 13 | 48.1% | 0.0069 |
| zieltyp | sonstiges | 17 | 7 | 41.2% | 0.0069 |
| zieltyp | week | 25 | 5 | 20.0% | 0.0069 |
| zielzahl_im_text | ja | 65 | 21 | 32.3% | 0.1143 |
| zielzahl_im_text | nein | 121 | 26 | 21.5% | 0.1143 |
| goldzellen | 2 | 124 | 35 | 28.2% | 0.2139 |
| goldzellen | 3-4 | 26 | 4 | 15.4% | 0.2139 |
| goldzellen | >= 5 | 36 | 8 | 22.2% | 0.2139 |
| textlaenge | < 12893 | 86 | 21 | 24.4% | 0.8664 |
| textlaenge | >= 12893 | 100 | 26 | 26.0% | 0.8664 |
| tabellen | < 3 | 81 | 24 | 29.6% | 0.2389 |
| tabellen | >= 3 | 105 | 23 | 21.9% | 0.2389 |
