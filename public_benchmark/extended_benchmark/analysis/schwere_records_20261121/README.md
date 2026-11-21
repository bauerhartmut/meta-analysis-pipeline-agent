# Schwere Records: Aufgaben und Lösungen (21.11.2026)

41 Records aus dem P5-Vergleich, aufgeteilt in zwei Ordner:

```
aufgaben/    ANLEITUNG.md + je Record eine Aufgabe mit Kontext und Volltext
loesungen/   je Record eine JSON-Lösung + INDEX.md mit der Auswahltabelle
```

## Auswahl

| Klasse | Kriterium | Records |
|---|---|---:|
| A | `content_chars == 0` im P5-Lauf (keine Antwort) | 33 |
| B | P5 lieferte Zellen, aber keinen Treffer (`p5.tp == 0`, Goldzellen > 0) | 8 |

`yun2024:653` ist nicht enthalten: der Record hat keine Goldzellen, es gibt
also nichts zu treffen. Zusammen 158 Goldzellen.

**16 der 33 Records der Klasse A haben nach `leere_p5_muster_20261120.md`
keinen einzigen Goldwert im Dokumenttext** (Werte nur in Bildtabellen oder
Anhängen). Dort ist die richtige Antwort eine leere Zellenliste; die
Goldwerte stehen in der Lösung, damit die Bewertung vollständig bleibt. Wer
diese Records mit bewertet, ohne das zu trennen, misst die
Dokumentaufbereitung, nicht die Extraktion.

## Aufgabe

Jede Datei `aufgaben/yun2024_XXX_aufgabe.md` enthält:

- Kontext: Intervention, Comparator, Outcome, Outcome-Typ, Zielzeitpunkt-Regel
- Auftrag und Ausgabeschema
- den vollständigen Dokumenttext zwischen `DOKUMENTANFANG` und `DOKUMENTENDE`

Die gemeinsame Anleitung steht in `aufgaben/ANLEITUNG.md`. Sie ist
selbsttragend: acht Felder, Zeitpunktregel, Zeilenregel (Änderungszeilen nur
wenn kein Absolutwert berichtet ist), Kopfzahlen erlaubt, Armzuordnung,
Umgang mit fehlenden Werten, JSON-Schema.

## Lösung

`loesungen/yun2024_XXX_loesung.json` enthält:

- `gold_zellen`: Feld, Arm, Wert, gedruckter Rohwert, Zeitpunkt (im Gold meist `null`)
- `goldwerte_im_text`: `ja`/`nein`/`nicht ausgewertet` (Quelle: `leere_p5_muster_20261120.md`)
- `p5_lauf`: Zellen, TP, FP, FN, F1, Fehlerklasse des P5-Laufs
- `kontext` und `dokument` zur Nachvollziehbarkeit

`loesungen/INDEX.md` listet alle 41 Records mit Klasse, Goldzellen,
P5-Zellen, P5-TP, P5-F1 und der Angabe, ob ein Goldwert im Text steht.

## Bewertung

Eine Zelle ist ein Treffer, wenn `(field, arm)` übereinstimmt und der Wert
innerhalb von `1e-6` gleich ist. TP/FP/FN daraus, Precision = TP/(TP+FP),
Recall = TP/(TP+FN), F1 = 2PR/(P+R). Zusätzliche Zellen sind FP, fehlende FN.
`timepoint` und `quote` werden nicht bewertet.

## Reproduktion

```
.venv/bin/python public_benchmark/extended_benchmark/analysis/schwere_records_20261121/baue_schwere_records_20261121.py
```

Das Skript liest `vergleich_20261120.json`, `yun699.jsonl`, die
P5-Predictions und `leere_p5_muster_20261120.json`, prüft die erwarteten
Anzahlen (33 und 8) und schreibt beide Ordner neu. Kein Modellaufruf, keine
Änderung an Gold oder Predictions.

## Grenzen

- Volltext, kein Aufgaben-Prompt des P5-Laufs: Die Aufgabe enthält das ganze
  Dokument, nicht das 45.000-Zeichen-Fenster des Laufs. Die Records sind
  damit eher leichter als im Lauf, nicht schwerer.
- `gold_zellen` haben keinen Gold-Zeitpunkt; die Zeitpunktangabe in der
  Antwort ist deshalb nicht bewertbar.
- Die Einordnung "Gold im Text" ist eine Heuristik aus dem Musterbericht, keine
  Sichtprüfung jedes Falls.
