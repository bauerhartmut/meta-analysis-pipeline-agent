# Kettenlauf mit regelbasierter Vorstufe, 20.11.2026

Lauf: `kettenlauf_20261120.py --records yun2024:420 yun2024:421 yun2024:582
yun2024:671 yun2024:672 --budget1 16000 --budget2 8000 --timeout 420`.
Vorstufe: `vorstufe_kopf` ruft `kopf_parser_20261120.kopf_parse` auf, bevor
Stufe 1 startet, und setzt bei Erfolg beide Gruppengroessen ohne Modell.

## Ergebnis je Record

| Record | Vorstufe | Stufe 1 | Stufe 2 | Zellen gesamt | TP | FP | FN | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `yun2024:420` | nichts | 11.307 | uebersprungen | 0 | 0 | 0 | 6 | kein Wert |
| `yun2024:421` | nichts | 6.828 | 6.442 (Satz) | 0 | 0 | 0 | 6 | kein Wert |
| `yun2024:582` | 16/16 | 5.501 | uebersprungen | 2 | 2 | 0 | 0 | **1,0** |
| `yun2024:671` | nichts | 4.657 | uebersprungen | 0 | 0 | 0 | 2 | kein Wert |
| `yun2024:672` | nichts | 4.418 | uebersprungen | 0 | 0 | 0 | 2 | kein Wert |

Summe 39.153 Completion-Tokens. Kein Record wurde abgebrochen (`finish_reason`
ueberall `stop`).

`kein Wert` heisst: keine einzige Zelle gelesen, TP 0 und FP 0, `v.quote`
liefert `None`. Recall ist 0; F1 ist bei TP 0 nicht definiert, nicht "0,0".

## Was die Vorstufe leistet

Sie liefert genau bei 582 die Kopfzelle und damit 16/16 **ohne Modellaufruf**;
der Record braucht Stufe 2 nicht mehr. Stufe 1 lief trotzdem und gab wie in den
beiden Vorlaeufen `found: false` aus, ohne Einfluss auf das Ergebnis.

Die Zuordnung beruht auf "erste zwei gedruckte Kopfzellen". Die Alternative
"erste Zelle je Arm" ergibt 16 und 14 und damit TP 1, FP 1, FN 1, F1 0,5 — das
ist offline nachgerechnet. Gold verlangt 16/16, also die zwei Zellen des
`Positive ABM`-Blocks (`Faces`, `Words`). Warum Gold diese beiden meint, obwohl
der Kopf vier Zellen fuer zwei Arme druckt, ist aus dem Datensatz nicht
ableitbar; der 1,0-Wert haengt an dieser Setzung.

## Auffaelligkeiten

- **420 kostet 11.307 Tokens bei 420 Zeichen Ausgabe.** Der Record verbrauchte
  rund das Zweieinhalbfache der anderen, ohne ein Ergebnis zu liefern
  (`found: false`). Bei einem Modell mit Denkanteil waere das erwartbar; ohne
  Einsicht in den Tokenizer bleibt es eine Beobachtung.
- **421 waehlte den falschen Satz.** Beide Locators zeigen auf
  `Regarding quantitative assessment of contour sharpness ...`, einen Satz zur
  Bildqualitaet, nicht zur Aufmerksamkeitsfunktion. Stufe 2 las daraus 0 Zellen.
- 672 lieferte nur einen Locator ohne Armzuordnung, ebenfalls `found: false`.
- 582 antwortete zweimal identisch (5.501 Tokens), der Prompt ist unveraendert
  gegenueber dem zweiten Kopf-Versuch.

## Grenzen

- Ein Lauf je Record, keine Wiederholung; Streuung zwischen Laeufen ist aus
  diesen Zahlen nicht schaetzbar.
- 671/672 bleiben unerreichbar: ihre Gruppengroessen stehen nur im Abstract
  und in einem Spaltenkopf bei Position 5.347, beide ausserhalb des
  Ergebnisteils.
- Die Vorstufe braucht eine gedruckte Armzeile mit mindestens zwei Labels.
  Fehlt sie, liefert sie nichts, statt zu raten.
- 420/421/671/672 haben nach diesem Lauf weiterhin keine belegten Zellen; ein
  F1 von 0 ist nicht gemessen, sondern nur "nichts gelesen".

## Empfehlung

Vorstufe behalten und den Kopf-Parser auf die Spaltenstruktur erweitern
(Armzeile plus Untergruppen wie `Faces`/`Words`), damit die Zuordnung nicht
mehr von "erste zwei Zellen" abhaengt. Fuer 420/421 ist der naechste Hebel
nicht der Kopf, sondern die Satzauswahl der Stufe 1: 421 zeigt, dass das Modell
einen falschen Satz bindet, obwohl der richtige im Ausschnitt liegt.
