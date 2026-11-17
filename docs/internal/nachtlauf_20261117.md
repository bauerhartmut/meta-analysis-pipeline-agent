# Nachtlauf 2026-11-17: Yun-699 mit drei Modellen

Fortsetzung des bestehenden Laufs `yun699_8000_alle_20261117`. Es wurde **kein
neuer Lauf** angelegt, sondern der abgebrochene Stand weitergefuehrt — gleiche
Bedingung, gleiche `quelle`, damit die Auswertung homogen bleibt.

## Ausgangslage vor dem Start

| Groesse | Wert |
|---|---|
| Zeilen in `predictions.jsonl` | 777 von 2094 |
| GLM 5.3 | 699/699 fertig (104 Ausfaelle, 36 leere Antworten) |
| Qwen 3.5 397B | 78/699 |
| Qwen3 30B | 0/699 (noch nicht gestartet) |
| Laufende Prozesse | keine |
| Record-Datei | `yun_full/records/yun699.jsonl`, 699 Zeilen |

Alle vorhandenen Zeilen tragen `quelle=v7_alle699`, `schema_version=v7_zellzeitpunkt`
und `max_tokens=8000`; die Fortsetzung verwendet dieselben Werte.

## Befehl

```bash
.venv/bin/python public_benchmark/extended_benchmark/run_extended_extraction.py \
  --models qwen30 qwen \
  --records public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl \
  --split "" --max-tokens 8000 --cell-timepoint --cache-buster --workers 3 \
  --run-id yun699_8000_alle_20261117 --quelle v7_alle699
```

Begruendung der Modellreihenfolge: Der Harness arbeitet modellweise ab. Mit
`qwen30` zuerst wird das dritte Modell in wenigen Minuten vollstaendig, statt
erst nach dem langsamen 397B-Modell zu beginnen. `glm` fehlt im Aufruf, weil alle
699 Zeilen vorliegen.

`--cache-buster` setzt einen zufaelligen `Session tag` in den Systemprompt
(`uuid4().hex[:12]`), damit das Gateway keine gecachte Antwort zurueckgibt. Der
Tag aendert nur den Cache-Schluessel, nicht die Aufgabe.

## Laufzeit-Erwartung (aus gemessenen Medianen)

| Modell | Median je Record | offen | Erwartung bei 3 Threads |
|---|---|---|---|
| qwen30 | 2,3 s | 699 | ~10-15 min |
| qwen | 125,1 s | 621 | ~7 h |
| glm | 7,2 s | 0 | — |

Quelle: `yun_full/laufzeit_telemetrie.py` (8000 Tokens, v7, ohne Cache-Treffer
und ohne Ausfaelle). Der qwen30-Wert stuetzt sich auf nur 9 Messungen und ist
deshalb unsicher; der beobachtete Startlauf lag bei etwa 1 Zeile/s, was die
Schaetzung stuetzt.

## Was danach noch fehlt

1. Fehlzeilen nachziehen (`--retry-failed`, bei erneutem `length` zusaetzlich
   `--repair`) — siehe `yun_full/befehle_nachzug_20261116.md`.
2. Duplikate entfernen (`dedupe_predictions.py --write`), weil `--retry-failed`
   neue Zeilen anhaengt.
3. Auswerten (`auswerte_yun699.py`), je Modell getrennt.

Bekannte Ausfallquote im ersten Teil: GLM 14,9 % technisch plus 5,2 % leer,
Qwen 10,3 % technisch plus 6,4 % leer (Stand 78 Zeilen).

## Grenze dieses Laufs

Ein Fortsetzungslauf nach einem Abbruch erzeugt fuer die neuen Zeilen einen
anderen `Session tag` als der erste Teil. Die Bedingung ist inhaltlich gleich,
aber die Zeilen sind nicht bit-identisch zu einer Anfrage aus dem ersten Teil.
