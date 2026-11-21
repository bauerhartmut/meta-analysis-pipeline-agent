# Deterministische Zellvalidierung am 699-Hybrid (21.11.2026)

Die Pruefung ist goldfrei: sie kennt nur die Zelle und den Dokumenttext, den
das Modell gesehen hat. Verworfen wird nur, was nachrechenbar unmoeglich oder
im Text nicht vorhanden ist.

| Stand | TP | FP | FN | F1 |
|---|---:|---:|---:|---:|
| Hybrid vorher | 2014 | 507 | 759 | 0.7609 |
| Hybrid nachher | 2014 | 459 | 759 | 0.7678 |

Verworfen: 48 Zellen, davon 0 mit TP-Verlust.

| Grund | verworfen | davon war TP |
|---|---:|---:|
| `keine_ganzzahl` | 31 | 0 |
| `ereignisse_zu_gross` | 17 | 0 |

## Beispiele

| Record | Feld | Wert | Grund | war TP |
|---|---|---:|---|:---:|
| `yun2024:1` | intervention_events | 14.2 | keine_ganzzahl | nein |
| `yun2024:1` | comparator_events | 15.7 | keine_ganzzahl | nein |
| `yun2024:153` | intervention_events | 42.5 | keine_ganzzahl | nein |
| `yun2024:121` | intervention_events | 45.0 | ereignisse_zu_gross | nein |
| `yun2024:121` | comparator_events | 35.0 | ereignisse_zu_gross | nein |
| `yun2024:313` | intervention_events | 100.0 | ereignisse_zu_gross | nein |

## Was das ist und was nicht

Das ist ein Nachfilter, keine Extraktion: er erzeugt keine fehlende Zelle und
berichtigt keinen falschen Wert. Der Gewinn kommt allein aus Zellen, die im
Text nicht stehen oder als Zahl unmoeglich sind. Die Zuordnungsfehler aus
Phase 1 (`fp_gebunden`, `fp_outcome`) bleiben; sie brauchen die Zeilenbindung
aus Stufe 1, nicht diesen Filter.

Dubletten werden nicht gefiltert. Goldfrei laesst sich nicht entscheiden,
welche der beiden Zellen gilt; im ersten Entwurf kostete ein Dublettenfilter
137 TP, weil die richtige Zelle oft die zweite ist.

Grenzen: `zahl_nicht_im_text` haengt an der 45.000-Zeichen-Grenze; eine Zelle
aus dem spaeteren Dokumentteil wird verworfen, obwohl sie im Artikel steht.
`rate_statt_anzahl` erkennt nur das Prozentzeichen direkt hinter der Zahl.
Die Ereignispruefung greift nur, wenn beide Zellen vorliegen.
