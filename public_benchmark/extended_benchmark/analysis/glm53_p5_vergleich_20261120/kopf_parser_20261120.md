# Regelbasierter Kopf-Parser (ohne Modell), 20.11.2026

Zweck: Gruppengroessen aus der Tabellenkopfzeile lesen, wenn das Modell die
Kopffundstelle verfehlt. Aufruf: `kopf_parser_20261120.py`, Ergebnisse als JSON
in `kopf_parser_20261120.json` (Tabellenstueck) und
`kopf_parser_ganz_20261120.json` (ganzes Dokument).

## Vorgehen

1. Im Tabellenstueck die Zeile mit mindestens zwei Kopfzellen `(n = K)` suchen.
2. Die Armzeile darueber nehmen (`Positive ABM   Neutral ABM`).
3. Kopfzellen gleichmaessig auf die Arme verteilen: bei vier Zellen und zwei
   Armen gehoeren die ersten zwei zum linken, die letzten zwei zum rechten Arm.
   Die Labelposition taugt nicht, weil die Armnamen ueber ihren Untergruppen
   zentriert stehen (erste Fassung ordnete `Words (n = 16)` dem rechten Arm zu).
4. Erste zwei Werte als Interventions-/Komparatorgroesse auswerten, beide
   Ordnungen pruefen und die beste melden.

## Ergebnis

| Record | Kopfzellen | Arme | Gold | F1 |
|---|---|---|---:|---:|
| `yun2024:582` | 16, 16, 14, 15 | Positive ABM 2x, Neutral ABM 2x | 16 / 16 | **1,0** |
| `yun2024:420` | keine | — | 18 / 21 | 0,0 |
| `yun2024:421` | keine | — | 30 / 34 | 0,0 |
| `yun2024:671` | keine | — | 14 / 12 | 0,0 |
| `yun2024:672` | keine | — | 14 / 12 | 0,0 |

Beleg fuer 582:

```
Positive ABM       Neutral ABM
Faces (*n* = 16)   Words (*n* = 16)   Faces (*n* = 14)   Words (*n* = 15)   *p*
```

Die ersten zwei Zellen sind `Faces` und `Words` des aktiven Arms, beide 16.

## Grenzen

- **Armnamen passen nicht zu Kontextnamen.** Der Kontext nennt `Word-based ABM`
  (Intervention) und `Face-based ABM` (Komparator), der Kopf `Positive ABM` und
  `Neutral ABM`. Die Zuordnung `Positive -> Intervention` ist eine Annahme. Sie
  ist bei 582 folgenlos, weil beide Werte 16 sind; bei ungleichen Werten
  entscheidet sie ueber TP und FP.
- **Nur 1 von 5 Records.** 420/421 haben im Tabellenstueck keine Kopfzelle. Im
  ganzen Dokument findet der Parser zwar `(n = 58)`, `(n = 44)` usw., das sind
  aber Befundhaeufigkeiten aus der Prosa, keine Gruppengroessen; die Zuordnung
  bleibt leer und F1 0. 671/672 haben im Dokument nur die Abstract-Angabe und
  einen Spaltenkopf bei Position 5.347, beide ausserhalb des Ergebnisteils.
- Der Parser braucht eine gedruckte Armzeile mit mindestens zwei Labels. Fehlt
  sie, liefert er nichts statt zu raten.

## Kosten

Keine Tokens; beide Laeufe sind rein lokal. Die zwei Modellaufrufe auf 582 im
Kopf-Modus kosteten 5.030 und 5.501 Completion-Tokens und lieferten beide
`found: false`.

## Empfehlung

Den Parser als Vorstufe vor Stufe 1 in den Kettenlauf haengen: findet er zwei
Kopfzellen mit Armzeile, werden die Gruppengroessen ohne Aufruf gesetzt und
Stufe 2 liest nur noch die Mittelwerte. Er greift bei 582 und laesst die anderen
Records unveraendert, statt sie mit einem weiteren Aufruf zu belasten.

## Nachtrag 20.11.2026: Arm und Untergruppe

Der Parser liest jetzt je Kopfzelle Arm und Untergruppe (`Faces`, `Words`) und
gibt drei Lesarten aus: `erste_zwei` (16/16, F1 1,0), `je_arm` (16/14, F1 0,5)
und `untergruppe` (16/14, F1 0,5). Einzelheiten in
`kopf_und_satzauswahl_20261120.md`; die 1,0 haengt an `erste_zwei`.
