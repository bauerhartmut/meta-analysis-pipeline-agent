# SD als eigenes Zellfeld: Wirkung an den 15 Records

Offline, ohne Netzaufruf. `sd_durchreichen_20261121.py`. `wert_aus_zelle`
liefert die Streuung jetzt fuer `*_standard_deviation`, aber nur aus Zellen
im Format `Mittel (SD)` oder `Mittel +/- SD`; alles andere bleibt leer.

- Records mit ausschliesslich fehlender SD: 15
- Zellauftraege: 22, geliefert 6, richtig 0, falsch 6
- Records vollstaendig: 3, davon gegen Gold ganz richtig: 0

| Record | fehlende Felder | geliefert | richtig | vollstaendig |
|---|---|---:|---:|---|
| `yun2024:6` | intervention, comparator | 0 | 0 | nein |
| `yun2024:113` | intervention, comparator | 0 | 0 | nein |
| `yun2024:110` | intervention, comparator | 0 | 0 | nein |
| `yun2024:114` | intervention, comparator | 0 | 0 | nein |
| `yun2024:149` | intervention, comparator | 0 | 0 | nein |
| `yun2024:151` | intervention, comparator | 0 | 0 | nein |
| `yun2024:160` | intervention, comparator | 0 | 0 | nein |
| `yun2024:163` | intervention, comparator | 0 | 0 | nein |
| `yun2024:203` | intervention, comparator | 0 | 0 | nein |
| `yun2024:357` | intervention, comparator | 0 | 0 | nein |
| `yun2024:367` | intervention, comparator | 0 | 0 | nein |
| `yun2024:447` | intervention, comparator | 2 | 0 | ja |
| `yun2024:449` | intervention, comparator | 0 | 0 | nein |
| `yun2024:450` | intervention, comparator | 2 | 0 | ja |
| `yun2024:448` | intervention, comparator | 2 | 0 | ja |

## Nicht gelieferte Auftraege

| Record | Feld | Grund |
|---|---|---|
| `yun2024:110` | comparator | keine Zielzeile |
| `yun2024:110` | intervention | keine Zielzeile |
| `yun2024:113` | comparator | keine Zielzeile |
| `yun2024:113` | intervention | keine Zielzeile |
| `yun2024:114` | comparator | keine Zielzeile |
| `yun2024:114` | intervention | keine Zielzeile |
| `yun2024:160` | comparator | Zielzeile ohne SD-Format |
| `yun2024:160` | intervention | Zielzeile ohne SD-Format |
| `yun2024:163` | comparator | Zielzeile ohne SD-Format |
| `yun2024:163` | intervention | Zielzeile ohne SD-Format |
| `yun2024:203` | comparator | Zielzeile ohne SD-Format |
| `yun2024:203` | intervention | Zielzeile ohne SD-Format |
| `yun2024:449` | comparator | Zielzeile ohne SD-Format |
| `yun2024:449` | intervention | Zielzeile ohne SD-Format |
| `yun2024:6` | comparator | keine Zielzeile |
| `yun2024:6` | intervention | keine Zielzeile |

## Poolbasis

| Stand | k | pooled |
|---|---:|---:|
| P5 unveraendert | 24 | 0.125 |
| mit allen gelieferten SD | 27 | 0.135 |
| mit den richtigen SD | 24 | 0.125 |

Die Poolbasis waechst nur um Records, deren uebrige Zellen schon
vollstaendig waren; fehlt weiter ein anderes Feld, bleibt der Record draussen.

## Grenzen

- Goldmittel dienen als Auftrag: die Regel muss die Zielzeile aus dem
  Goldoutcome finden, nicht aus dem P5-Ergebnis.
- Ein Treffer misst nur den SD-Wert der Zielzeile; die Zuordnung Arm/Spalte
  folgt derselben Label-Logik wie beim Mittel.
