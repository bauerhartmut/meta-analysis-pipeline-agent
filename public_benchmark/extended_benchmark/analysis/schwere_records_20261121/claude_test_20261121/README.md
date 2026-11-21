# Claude-Test: genau die Anfrage des Harness (21.11.2026)

Dieser Ordner enthaelt fuer 41 schwere Records **denselben Text, den der
Harness im P5-Lauf an das Modell geschickt hat** — nicht die Aufgabenfassung
aus `../aufgaben/`. Ziel ist, ein anderes Modell (z. B. Claude) auf genau der
Anfrage zu testen, an der GLM im P5-Lauf gescheitert ist.

## Was hier drin steht

```
SYSTEM.txt                    Systemprompt (eine Nachricht, fuer alle Records gleich)
prompts/<record>_prompt.md    Nutzernachricht, 1:1 der Text aus build_prompt
INDEX.md                      Kennzahlen je Record (Zeichen, Kuerzung, Goldzellen, P5-Status)
```

Kein Gold, keine Loesung, kein Hinweis auf die erwarteten Werte. Wer den Ordner
weitergibt, gibt nur die Anfrage weiter. Die Loesungen liegen getrennt in
`../loesungen/`.

## Herkunft (nachrechenbar)

* Record: `public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl`
* Dokumenttext: `record["document"]["path"]`, relativ zur Projektwurzel,
  gelesen mit `errors="replace"`
* Anfrage: `run_extended_extraction.build_prompt(record, text)` mit den
  Standardwerten des P5-Laufs (Grenze 45000 Zeichen, kein Zeitpunktflag,
  keine Quellenzeile, `group_size_mode="aus"`)
* Systemprompt: `run_extended_extraction.SYSTEM`, `SESSION_TAG` leer
* Antwortbudget im Lauf: 24000 Tokens, `temperature=0.0`

Der P5-Lauf traegt in allen 41 Zeilen `prompt_version = v2_timepoint` und
`schema_version = v6_percell_timepoint`; das Skript bricht ab, wenn das nicht
mehr stimmt. Damit ist belegt, dass die hier gerenderte Fassung die Fassung des
Laufs ist.

## So testest du ein Modell

1. `SYSTEM.txt` als Systemprompt setzen (Claude-Projekte: Projektanweisung;
   API: `role=system`).
2. Genau eine Datei aus `prompts/` als Nutzernachricht senden. Eine Datei = ein
   Record = ein Aufruf. Nichts ergaenzen, nichts wegkuerzen.
3. `temperature=0`, Budget mindestens 24000 Ausgabetokens — im Lauf hat GLM das
   Budget im Reasoning aufgebraucht, deshalb dieser Wert.
4. Die Antwort als `antworten/<record>_antwort.json` speichern (roher Text,
   Codefences sind erlaubt) und mit `bewerte_claude_20261121.py` auswerten.

## Bewertung

`bewerte_claude_20261121.py` vergleicht gegen `../loesungen/*_loesung.json`:
Treffer ist `(field, arm)` gleich und `|Wert - Gold| < 1e-6`. Daraus TP, FP, FN,
Precision, Recall, F1 je Record und als Summe. `timepoint` und `quote` werden
nicht bewertet.

Wichtig: 16 der 33 Records ohne Antwort haben nach
`../analysis/glm53_p5_vergleich_20261120/leere_p5_muster_20261120.md` **keinen
Goldwert im Dokumenttext**. Dort ist die richtige Antwort eine leere
Zellenliste. Wer diese 16 mitzaehlt, ohne sie zu trennen, misst die
Dokumentaufbereitung, nicht die Extraktion. `INDEX.md` markiert sie in der
Spalte `Gold im Text`.

## Grenzen

* Ein Aufruf pro Record, kein Fenster-Schieben, keine zweite Stufe: das ist der
  P5-Aufbau, nicht die Kettenpipeline.
* Der Prompt schneidet bei 45000 Zeichen ab; die Aufgaben in `../aufgaben/`
  enthalten den Volltext. Beide Tests messen deshalb nicht dasselbe.
* Ohne Gold-Zeitpunkt im Record ist `timepoint` in der Antwort nicht bewertbar.
* Dieses Paket ersetzt keinen Netzlauf im Harness: es ist ein Fremdmodell-Test
  auf derselben Anfrage.
