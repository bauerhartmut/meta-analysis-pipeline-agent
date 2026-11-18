# Platzbedarf der mitgeschriebenen Rohantwort

Gemessen auf einer Lesekopie: Die Antwort wird nachgebaut, auf die gespeicherte Laenge `content_chars` gebracht und die Zeile mit und ohne `content` serialisiert. Die Differenz enthaelt Feldname, Anfuehrungszeichen und Escaping.

| Modell | Records | Zeichen Median | Zeichen Mittel | Zeichen p90 | Zeichen max | Zeile ohne (Median) | Aufschlag (Median) | Aufschlag gesamt |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| glm | 699 | 339 | 316 | 609 | 1215 | 1598 | 401 | 257 KiB |
| qwen | 184 | 411 | 403 | 782 | 1032 | 1599 | 491 | 84 KiB |
| qwen30 | 699 | 371 | 324 | 471 | 5489 | 1622 | 443 | 263 KiB |

**Summe:** 1582 Zeilen, Aufschlag 604 KiB (391 Byte je Zeile). Ein voller Lauf mit 699 Records je Modell (2.094 Zeilen) kostet danach rund 0.8 MiB zusaetzlich; die aktuelle Datei mit 1.582 Zeilen liegt bei 2.3 MiB.
