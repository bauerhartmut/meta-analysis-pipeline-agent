# Kopfzuordnung, Varianten und Satzauswahl, 20.11.2026

Zwei Offline-Pruefungen ohne Modellaufruf: die Arm-/Untergruppen-Zuordnung im
Kopf-Parser und die Satzauswahl der Stufe 1.

## 1. Kopf-Parser mit Arm und Untergruppe

`kopf_parser_20261120.kopf_parse` liest jede Kopfzelle einzeln (Feldtrennung
ueber zwei oder mehr Leerzeichen), zieht die Untergruppe aus dem Text vor der
Klammer (`Faces`, `Words`) und verteilt die Zellen gleichmaessig auf die Arme
der Armzeile. Fuer 582 ergibt das:

```
Positive ABM       Neutral ABM
Faces (*n* = 16)   Words (*n* = 16)   Faces (*n* = 14)   Words (*n* = 15)   *p*
```

| Arm | Untergruppe | Wert |
|---|---|---:|
| Positive ABM | Faces | 16 |
| Positive ABM | Words | 16 |
| Neutral ABM | Faces | 14 |
| Neutral ABM | Words | 15 |

Drei Lesarten, alle offline gegen Gold 16/16 gerechnet:

| Lesart | Werte | TP | FP | FN | F1 |
|---|---|---:|---:|---:|---:|
| `erste_zwei` | 16, 16 | 2 | 0 | 0 | **1,0** |
| `je_arm` | 16, 14 | 1 | 1 | 1 | 0,5 |
| `untergruppe` | 16, 14 | 1 | 1 | 1 | 0,5 |

Der Kettenlauf gibt alle drei Lesarten mit TP/FP/FN/F1 aus (in
`--nur-vorstufe` und im Lauf) und schreibt sie als `vorstufe_varianten_f1` ins
Ergebnis-JSON.

**Damit ist klar, worauf die 1,0 von 582 beruht:** auf `erste_zwei`, also auf
den zwei Zellen des `Positive ABM`-Blocks. Sobald die Arme getrennt gelesen
werden, steht 16 gegen 14 und F1 faellt auf 0,5. Gold verlangt 16/16; warum,
ist aus dem Dokument nicht ableitbar, denn der Kopf druckt vier Zellen fuer
zwei Arme.

## 2. Satzauswahl der Stufe 1

`satzauswahl_20261120.py` liest alle gespeicherten Stufe-1-Antworten im
Laufverzeichnis und im Kettenlauf, nimmt Locators mit nicht leerem `satz` und
prueft je Fall zwei Dinge:

- **Paar:** stehen Mittelwert und Standardabweichung aus Gold im Satz,
- **Unterscheider:** stehen die Woerter aus dem Outcome, die diesen Record von
  seinen Nachbar-Records trennen (z. B. `Cervicothoracic`, `thoracolumbar`).

Zehn Faelle ohne Doppelzaehlung (zwei Locators je Antwort zaehlen einmal):

| Record | Quelle | Paar | fehlender Unterscheider | Urteil |
|---|---|---|---|---|
| `yun2024:420` | Kette | ja | `Cervicothoracic` | Paar richtig, nicht eindeutig |
| `yun2024:420` | Satz-Variante | ja | `Cervicothoracic` | Paar richtig, nicht eindeutig |
| `yun2024:421` | Kette (2 Saetze) | ja | `thoracolumbar` | Paar richtig, nicht eindeutig |
| `yun2024:523` | Satz-Variante | ja | `results` | Paar richtig, nicht eindeutig |
| `yun2024:30` | Dreifenster | nein | — | richtiger Satz lag vor |
| `yun2024:673` | Dreifenster | nein | — | richtiger Satz lag vor |
| `yun2024:674` | Dreifenster | nein | — | richtiger Satz lag vor |
| `yun2024:119` | Satz-Variante | nein | — | kein richtiger Satz im Ausschnitt |
| `yun2024:52` | Satz-Variante | nein | — | kein richtiger Satz im Ausschnitt |

Summe: 5 Faelle mit richtigem Paar aber fehlendem Unterscheider, 3 mit
vorhandenem richtigen Satz, den das Modell nicht nahm, 2 ohne brauchbaren Satz
im Ausschnitt. Kein einziger Fall ist "richtig und eindeutig".

### Korrektur meiner letzten Aussage

Im Bericht `kette_vorstufe_20261120.md` steht, 421 habe einen falschen Satz zur
Bildqualitaet gebunden. **Das war falsch.** Das Outcome von 421 ist
`quantitative contour sharpness of the thoracolumbar spine`; der gebundene Satz
(`Regarding quantitative assessment of contour sharpness ...`) ist der richtige
Satz und enthaelt alle vier Wertepaare. Was fehlt, ist das Wort
`thoracolumbar`: der Satz nennt nur "the two assessed interfaces" und ist damit
zwischen 420 (`Cervicothoracic`) und 421 (`thoracolumbar`) nicht
unterscheidbar. Deshalb las Stufe 2 null Zellen, nicht wegen einer falschen
Satzwahl.

Ebenso ist die Aussage "420 hat keine Zellen" in `kette_vorstufe_20261120.md`
nicht als Satzfehler zu lesen: der Satz war richtig, der Unterscheider fehlte.

## Grenzen

- Geprueft sind nur die gespeicherten Antworten (10 Faelle, 8 Records). Neue
  Aufrufe wurden nicht gemacht; die Stichprobe ist damit nicht repraesentativ
  fuer die 33 leeren Records des P5-Laufs.
- "Unterscheider" ist eine Wortliste aus dem Outcome-Text; sie erkennt fehlende
  Regionsangaben, nicht jede denkbare Mehrdeutigkeit.
- Der Kopf-Parser greift weiterhin nur bei 582; 420/421/671/672 haben im
  Tabellenstueck keine Kopfzelle.

## Empfehlung

Den Satz-Locator um die Pflicht erweitern, den Unterscheider mitzubinden: wird
ein Satz gewaehlt, muss der Satz (oder der direkt folgende) die Regions- bzw.
Outcome-Angabe enthalten, sonst ist die Zeile zu nehmen. Das adressiert 420,
421 und 523 zugleich und kostet keine Tokens, weil es eine Prompt-Regel ist, die
sich gegen diese 10 Faelle offline pruefen laesst. Fuer 30/673/674 ist der
naechste Hebel die Tabellenzeile, nicht der Satz.
