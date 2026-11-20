# Kette auf fuenf Abbruchrecords (20.11.2026)

Records aus `stichprobe_20261120.md`: `yun2024:420`, `:421`, `:582`, `:671`,
`:672`. Stufe 1 mit Zeilenbindung (Budget 16.000), Stufe 2 mit Einzelblock- und
Satz-Modus (Budget 8.000), Modell `gwdg/qwen3.5-397b` wie in den Vorlaeufen.
Ein Lauf, fuenf Records, kein Wiederholungsversuch.

## Lage vor dem Lauf (offline)

| Record | Gold im Ausschnitt | Score-Zeilen | Lage der Goldwerte | Menge |
|---|---|---|---|---|
| `yun2024:420` | 4/6 | 1 | Mittelwert und SD im Prosasatz (19.104–19.137) | Satz |
| `yun2024:421` | 4/6 | 1 | dito, zweites Paar desselben Satzes | Satz |
| `yun2024:582` | 2/2 Zellen | 9 | `Mean (SD)`-Zeile mit vier Wertepaaren | Zeile |
| `yun2024:671` | 2/2 Zellen | 3 | nur Gruppengroessen (14, 12) im Tabellenkopf | Kopf |
| `yun2024:672` | 2/2 Zellen | 3 | dito | Kopf |

Bei 420 und 421 fehlen die Gruppengroessen im Ausschnitt, dort ist F1 hoechstens
0,8.

## Ergebnis

| Record | Stufe 1 | Locator | Stufe 2 | TP | FP | FN | F1 |
|---|---|---:|---|---:|---:|---:|---:|
| `yun2024:420` | ok, 7.157 Tokens | Satz (`0.95 [SD, 0.24]` vs `1.43 [SD, 0.48]`) | ok, 3.245 Tokens | 4 | 0 | 2 | **0.8** |
| `yun2024:421` | ok, 5.877 Tokens | derselbe Satz | ok, 3.505 Tokens | 0 | 4 | 6 | **0 (None)** |
| `yun2024:582` | ok, 4.976 Tokens | keine (`found: false`) | uebersprungen | — | — | — | — |
| `yun2024:671` | ok, 3.434 Tokens | keine (`found: false`) | uebersprungen | — | — | — | — |
| `yun2024:672` | ok, 3.968 Tokens | keine (`found: false`) | uebersprungen | — | — | — | — |

## Was die fuenf Faelle zeigen

- **420 erreicht genau den Deckel.** Stufe 2 liest `0.95 (0.24)` und
  `1.43 (0.48)` richtig; die fehlenden Gruppengroessen kosten die zwei
  restlichen Zellen. Mehr als 0,8 war mit diesem Ausschnitt nicht moeglich.
- **421 scheitert an der Satz-Ambiguitaet.** Derselbe Satz nennt zwei
  Schnittstellen mit je zwei Paaren; Stufe 2 liest erneut das erste Paar
  (`0.95/0.24/1.43/0.48`) statt `0.83/0.22/1.32/0.51`. 0 Treffer bei 4 falschen
  Zellen: der Fehler entsteht nicht beim Lesen, sondern bei der Bindung an die
  richtige Schnittstelle — die Stufe 1 nicht unterscheidet.
- **582, 671, 672 antworten `found: false`.** Das ist keine Abbruchantwort,
  sondern die ehrliche Auskunft, dass die Kette keine Zeile findet, die den
  Outcome-Wert traegt: bei 582 ist der Goldwert die Gruppengroesse (16/16), die
  Zeile `Mean (SD)` traegt Messwerte; bei 671/672 stehen die Gruppengroessen im
  Tabellenkopf, nicht in einer Zeile. Der Zeilenzwang schliesst diese drei
  strukturell aus.

## Kosten

| Posten | Tokens |
|---|---:|
| Stufe 1 (fuenf Records) | 25.412 |
| Stufe 2 (zwei Records) | 6.750 |
| Summe | **32.162** |

Erwartet waren 56.325, Obergrenze 120.000. Der Lauf blieb darunter, weil drei
Records in Stufe 1 mit `found: false` endeten und Stufe 2 nicht mehr lief.

## Schluss

Die Kette generalisiert nicht in der Breite: von fuenf Records liefert einer den
Deckelwert, einer eine falsche Zelle, drei finden keine Stelle. Die Ursachen
sind benennbar und liegen alle vor der Extraktion: fehlende Gruppengroessen im
Ausschnitt (420), zwei Wertepaare in einem Satz ohne Bindung (421), Goldwert als
Kopfzahl statt Zeilenwert (582, 671, 672).

## Kopf-Modus auf 582, erster Aufruf (20.11.2026)

Ein Aufruf: `--records yun2024:582 --budget1 16000 --budget2 8000`.

Ergebnis: Stufe 1 `ok`, **5.030** Tokens, zwei Locators mit `found: false`
(alle Felder leer), Stufe 2 nicht gestartet. Die Armzuordnung im Kopf ist damit
**nicht gemessen**, und es gibt keinen F1-Wert: keine Zellen, `recall = 0`,
`F1 = null`.

Ursache, offline gefunden: das JSON-Schema in `PROMPT_REGELN` listet
`fundstelle` nicht. Der Regelblock verlangte das Feld, das Schema gab ihm aber
keinen Platz; das Modell antwortete folgerichtig mit `found: false`.

Behoben: `prompt1_mit_kopf` ersetzt die Schema-Zeile und haengt
`"fundstelle": "zeile" | "satz" | "kopf"` an. Prompt fuer 582 jetzt 7.462
Zeichen, Feld und Block im Prompt belegt, Schema-Pruefung `True`. Kein weiterer
Aufruf in diesem Schritt.
