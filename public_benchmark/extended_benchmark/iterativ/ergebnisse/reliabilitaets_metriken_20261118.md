# Zuverlaessigkeitsmetriken: _lesekopie_20261118 / glm

Auftraege: 699, Erfolgsquote (technisch): 0.8512.

## Technische Zuverlaessigkeit

| Kennzahl | Wert |
|---|---|
| Zeilen mit Versuchsspur | 0 |
| completed / failed | 595 / 104 |
| Erfolg im ersten Versuch | n/a |
| Erfolg nach Wiederholung | n/a |
| endgueltig fehlgeschlagen | 104 |
| Transportfehler (timeout + Verbindung) | 0 |
| Versuche je Auftrag | n/a |
| HTTP-Versuche je Auftrag | n/a |
| Wartezeit gesamt in s | n/a |
| Latenz je Auftrag in s (Mittel/Median/p90) | 20.93 / 8.41 / 45.64 |
| Tokens gesamt | 1931140 |
| Tokens je erfolgreichem Auftrag | 1860.7 |

## Finale Klassen

| Klasse | Anzahl |
|---|---|
| json_kaputt | 1 |
| length_ohne_ergebnis | 103 |
| ok | 595 |

## Extraktionsqualitaet (getrennt gezaehlt)

- Auftraege mit Zellen: 559
- leere Antworten ohne Fehlerklasse: 36 (0.0515)

## Was diese Zahlen nicht sagen

- Keine Versuchsspur: der Lauf entstand unter `alt`. Wiederholungs- und Wartezeiten sind deshalb `None`, nicht 0.
- 699 Zeilen ohne `job_status`; er wurde aus `fehlerklasse` rekonstruiert.
- Transportfehler sind hier nicht separat sichtbar: unter `alt` wurde ein Timeout als `json_kaputt` einsortiert.
