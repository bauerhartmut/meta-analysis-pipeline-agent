# Lesekopie für den qwen30/glm-Vergleich

Die Auswertung lief nicht auf der Datei des laufenden Nachtlaufs, sondern auf
einer Momentaufnahme. Der laufende Prozess (PID 3952) hat während der gesamten
Auswertung weitergeschrieben; er wurde weder angehalten noch beeinflusst.

## Herkunft

| Punkt | Wert |
|---|---|
| Quelle | `public_benchmark/extended_benchmark/runs/yun699_8000_alle_20261117/predictions.jsonl` |
| Kopie | `public_benchmark/extended_benchmark/runs/_lesekopie_20261118/predictions.jsonl` |
| Befehl | `cp runs/yun699_8000_alle_20261117/predictions.jsonl runs/_lesekopie_20261118/predictions.jsonl` |
| Zeilen | 1582 |
| SHA-256 | `8f6d622ff6e1ac98233186a3e50026ee525f1f88b3d003973bb094dc1ec3ab2a` |
| SHA-256 Quelle zur Kopierzeit | identisch, also byte-genaue Kopie |
| Eindeutige (record_id, model)-Paare | 1582 |
| Duplikate / unlesbare Zeilen | 0 / 0 |

Die Kopie liegt unter `runs/` und ist damit gitignoriert; sie ist aus der Quelle
mit dem obigen Befehl reproduzierbar. Für den Vergleich zählt allein der
SHA-256-Stand oben, nicht der spätere Zustand der Quelldatei.

## Stand der Kopie je Modell

| Modell | Zeilen | failed | leer |
|---|---:|---:|---:|
| glm | 699 | 104 | 36 |
| qwen30 | 699 | 0 | 57 |
| qwen | 182 | 22 | 16 |

`qwen` ist noch nicht fertig und geht in diesen Vergleich nicht ein.

## Auswertung

```
python public_benchmark/extended_benchmark/yun_full/auswerte_yun699.py \
    --run _lesekopie_20261118 --model qwen30 \
    --out public_benchmark/extended_benchmark/iterativ/ergebnisse/qwen30_vs_glm_20261118/qwen30_lesekopie.json

python public_benchmark/extended_benchmark/yun_full/auswerte_yun699.py \
    --run _lesekopie_20261118 --model glm \
    --out public_benchmark/extended_benchmark/iterativ/ergebnisse/qwen30_vs_glm_20261118/glm_lesekopie.json

python public_benchmark/extended_benchmark/yun_full/vergleiche_qwen30_glm.py \
    --run _lesekopie_20261118 \
    --out-dir public_benchmark/extended_benchmark/iterativ/ergebnisse/qwen30_vs_glm_20261118
```

Der Modellfilter `--model` wurde in `auswerte_yun699.py` ergänzt; ohne den
Parameter rechnet das Skript wie zuvor über alle Zeilen des Laufs.

## Freitext-Outcome entfernt

Die Abweichungsliste der Auswertung trug bisher den freien Outcome-Text des
Datensatzes (`context.outcome`) mit. Dieser Text ist für die Auswertung nicht
nötig, die `record_id` identifiziert den Datensatz, und er enthielt einen
Outcome-Namen des Yun-Datensatzes, der auf der Sperrbegriffsliste steht. Der
Pre-Push-Scan hat die neuen JSONs deshalb zu Recht blockiert. Die Abweichungen
tragen jetzt `outcome_typ` (binary/continuous); Kennzahlen und Ausfälle sind
gegenüber dem Stand mit Freitext unverändert. Die Artefaktdateien sind nach dem
Umbau ohne offene Treffer.

## Kontrolle der GLM-Zahlen

Die GLM-Auswertung der Kopie ergibt exakt die bereits dokumentierten Werte aus
`docs/internal/glm_699_ergebnis_20261117.md`: 1.840 richtig, 281 falsch, 652
fehlend, Precision 0,8675, Recall 0,6635, F1 0,7519, MAE 5,0573, 1.934.079
Tokens. Damit ist belegt, dass Kopie und Filter das Ergebnis nicht verändern.
