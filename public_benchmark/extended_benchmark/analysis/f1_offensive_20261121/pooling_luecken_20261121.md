# Warum 76 P5-Records fuer das Pooling unvollstaendig sind

Offline, ohne Netzaufruf. `pooling_luecken_20261121.py`. Sollfelder je
Outcome-Typ: bei kontinuierlich sechs Zellen (Mittel, SD, Groesse je Arm),
bei binaer vier (Ereignisse, Groesse je Arm).

## Feldweise Luecken (103 Records, 27 vollstaendig, 76 mit Luecke)

| Feld | fehlt in Records | davon einzige Luecke |
|---|---:|---:|
| `intervention_mean` | 38 | 0 |
| `comparator_mean` | 39 | 0 |
| `intervention_standard_deviation` | 55 | 0 |
| `comparator_standard_deviation` | 55 | 0 |
| `intervention_group_size` | 42 | 0 |
| `comparator_group_size` | 43 | 0 |
| `intervention_events` | 15 | 0 |
| `comparator_events` | 16 | 0 |

## Vollstaendig, aber nicht poolbar (3)

| Record | Grund |
|---|---|
| `yun2024:313` | Ereignisse groesser als Gruppe |
| `yun2024:376` | Ereignisse groesser als Gruppe |
| `yun2024:380` | Ereignisse groesser als Gruppe |

## Kategorien der 76 Luecken

| Kategorie | Records |
|---|---:|
| Standardabweichung und weitere Felder | 40 |
| nur Standardabweichung fehlt | 15 |
| Ereignisse und weitere Felder | 11 |
| nur Ereignisse fehlen | 5 |
| nur Groesse/Mittel (Regeln vorhanden) | 4 |
| nur Groesse (Regeln vorhanden) | 1 |

## Sichtung der SD-Luecke (15 Records mit ausschliesslich fehlender SD)

Reine Textzaehlung, keine Regel: Steht neben beiden Goldmitteln ein
zweiter Wert im Format `Mittel +/- SD` oder `Mittel (SD)`?

- beide Arme im bekannten Format: 6
- beide Arme irgendwo im Dokument: 11

Die Zaehlung sagt nur, ob der Wert im Text steht - nicht, ob die
Zielzeile gefunden wird (bei den Kandidaten oben war sie es nicht).

## Records, die die vorhandenen Regeln schliessen koennten (5)

Bedingung: kein fehlendes Feld ausser Groesse und Mittel, also keine
fehlende SD und keine fehlenden Ereignisse. Regelauftraege aus Gold:
8 Zellen.

| Stand | geliefert | richtig | falsch | Records geschlossen | davon ganz richtig |
|---|---:|---:|---:|---:|---:|
| mit Gate | 0 | 0 | 0 | 0 | 0 |
| ohne Gate | 0 | 0 | 0 | 0 | 0 |

| Record | fehlende Felder | Werte richtig |
|---|---|---|

| Record | Grund, warum nichts geliefert wird |
|---|---|
| `yun2024:212` | keine n-Zeile in der Tabelle der Zielzeile |
| `yun2024:213` | keine n-Zeile in der Tabelle der Zielzeile |
| `yun2024:215` | keine n-Zeile in der Tabelle der Zielzeile |
| `yun2024:214` | keine n-Zeile in der Tabelle der Zielzeile |
| `yun2024:626` | Zielzeile nicht gefunden |

Ohne Goldwert im Dokument (also nicht pruefbar): yun2024:626

## Grenzen

- Die Kandidatenpruefung setzt voraus, dass die Regeln auf jedes Dokument
  anwendbar sind; gemessen wird nur, ob sie fuer das fehlende Feld einen
  Wert liefern. Ein Treffer sagt nichts ueber Records, denen SD oder
  Ereignisse fehlen - dort helfen die vorhandenen Regeln nicht.
- Gold dient als Auftrag und als Pruefmass; ein Record ohne Goldwert ist
  als Kandidat gezaehlt, aber nicht bewertbar.
