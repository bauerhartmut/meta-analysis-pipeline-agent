# Drei Bindungsluecken geschlossen, offline geprueft (20.11.2026)

Kein Modellaufruf. Alle Zahlen aus dem Dry-Run von `kettenlauf_20261120.py`
und aus dem Dokumenttext.

## Was geaendert wurde

1. **Kopfzahlen als eigene Fundstelle.** Der Stufe-1-Prompt bekommt vor der
   JSON-Ausgabe einen Block: ist der Outcome-Wert eine Gruppengroesse und steht
   sie in einer Kopfzelle (`(n = 16)`, `N = 14`), dann `zeilenlabel` leer,
   Kopftext in `spaltenkopf`, neues Feld `fundstelle = "kopf"`. Erlaubte Werte:
   `kopf`, `zeile`, `satz`.
2. **Mehrere Wertepaare je Satz werden gebunden.** Stufe 2 im Satz-Modus liest
   700 statt 300 Zeichen Kontext vor dem Satz und bindet das Paar an die im
   Outcome genannte Entitaet (Reihenfolge der Nennung im Text), statt das erste
   Paar zu nehmen. Ist die Entitaet nicht benannt, antwortet sie mit leerer
   Zellenliste statt zu raten.
3. **Ausschnitt enthaelt Kopf und Vorsatz.** Beide Stuecke werden um 400 Zeichen
   nach links gezogen (`erweitere`), ohne Ueberlappung; damit liegen
   Tabellenkoepfe und die entitaetsnennenden Saetze im Ausschnitt.

## Was das offline fuer die fuenf Records bedeutet

| Record | Stuecke alt -> neu | `n =` im Ausschnitt | Entitaet im Ausschnitt | Gold im Ausschnitt | Prompt alt -> neu |
|---|---|---|---|---|---|
| `yun2024:420` | 8.260 / 18.510 -> 7.860 / 18.110 | ja, aber nicht 18/21 | `Cervicothoracic` | 4/6 | 6.323 -> 7.440 |
| `yun2024:421` | 8.260 / 19.010 -> 7.860 / 18.610 | ja, aber nicht 30/34 | `thoracolumbar` | 4/6 | 6.321 -> 7.438 |
| `yun2024:582` | 10.226 -> 9.826 | `(*n* = 16)`, `(*n* = 14)`, `(*n* = 15)` | — | 2 Zellen | 6.305 -> 7.421 |
| `yun2024:671` | 23.937 -> 23.537 | keine | — | 2 Zellen | 6.241 -> 7.358 |
| `yun2024:672` | 23.937 -> 23.537 | keine | — | 2 Zellen | 6.261 -> 7.378 |

Belege:

- `yun2024:582` druckt die Gruppengroessen als `Faces (*n* = 16) Words (*n* = 16)
  ...` bei Position 10.692, also im verlaengerten Tabellenstueck. Genau dieser
  Fall scheiterte zuvor mit `found: false`, weil die Regel nur Zeilen erlaubte.
- `yun2024:420` und `:421` nennen die Schnittstellen bei 18.349
  (`cervicothoracic`) und 18.373 (`thoracolumbar`), also knapp vor dem alten
  Stueckbeginn (18.510 / 19.010). Mit 400 Zeichen Vorlauf liegen beide drin; das
  700-Zeichen-Fenster der Stufe 2 erreicht sie ebenfalls.
- `yun2024:671` und `:672` drucken ihre Gruppengroessen `12` und `14` nur im
  Abstract (`A total of 40 communities (12 in control, 14 per intervention arm)`,
  Position 1.018) und in einem Spaltenkopf bei 5.347, beide ausserhalb des
  Ergebnisteils. Kopfzahlen helfen dort nicht.

## Erwartung je Record (Schaetzung, nicht gemessen)

| Record | vorher | erwartbar nachher | Begruendung |
|---|---|---|---|
| `yun2024:420` | F1 0,8 | 0,8 | erstes Paar ist bereits das richtige; Deckel bleibt 0,8 |
| `yun2024:421` | F1 0 | bis 0,8 | Bindung an `thoracolumbar` macht das zweite Paar waehlbar |
| `yun2024:582` | kein Locator | bis 1,0 | Kopfzelle `(*n* = 16)` ist jetzt Fundstelle |
| `yun2024:671` | kein Locator | 0 | Gruppengroessen nur im Abstract |
| `yun2024:672` | kein Locator | 0 | dito |

Kosten: prompts rund 1.100 Zeichen laenger als im letzten Lauf; bei gleichem
Verhalten sind das etwa 32.000 bis 40.000 Completion-Tokens fuer fuenf Records
(Schaetzung aus dem letzten Lauf: 32.162).
