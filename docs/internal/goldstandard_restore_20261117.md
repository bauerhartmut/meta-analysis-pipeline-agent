# Goldstandard-Records wiederhergestellt

**Datum:** 2026-11-17  
**Anlass:** Vier Tests in `public_benchmark/tests/test_goldstandard_adapters.py`
scheiterten, weil `eururology_v1/records.jsonl` und
`pico_corpus_v1/records.jsonl` fehlten.

## Ergebnis

Beide Record-Dateien wurden aus den dokumentierten Originalquellen neu
erzeugt. Es wurden keine Werte ergänzt oder geschätzt.

### European Urology

Quelle: OSF-Projekt `8fzps`, <https://osf.io/8fzps/>.

Die vier Arbeitsmappen wurden über ihre SHA-256-Werte den im Manifest
erwarteten Dateinamen zugeordnet:

| Datei | SHA-256 |
|---|---|
| `prompt1_chatgpt.xlsx` | `e4f0709385a72e2c24f72ccc304ca3c3f779ef32a03972e4961a5a103a8e995c` |
| `prompt1_claude.xlsx` | `0f7b700ea85d6e54c65550fcc4c75711df5a6942ff5398436ee18a86673d6adf` |
| `prompt2_chatgpt.xlsx` | `5e1564e30922857cb4f267f7b47d640e23c59b7216bdafe4aab8b80ea1bdde36` |
| `prompt2_claude.xlsx` | `f4b50462ab685df7eefbc657c7449d6628a0ff2bc4cd210457b46c0e19e5a598` |

Alle vier Hashes stimmten mit dem vorhandenen `manifest.json` überein.
`adapter_eururology.py` erzeugte daraus 104 Records (41 binär, 63
kontinuierlich) aus 20 Trials. Das Manifest blieb byte-identisch.

### PICO-Corpus

Quelle: <https://github.com/sociocom/PICO-Corpus>, Branch `main`.

Das Archiv `pico_corpus_main.zip` hat den SHA-256-Wert
`5c093b07271e43f93f3ef8b285297351817f88a6b34c1781fedf09188d551d27`.
Es enthält 1011 `.ann`-Dateien unter dem erwarteten Präfix
`PICO-Corpus-main/pico_corpus_brat_annotated_files/`.
`adapter_pico_corpus.py` erzeugte daraus 5024 Records; 217 Zahlstellen
bleiben als Wortwert ohne numerischen Wert. Das Manifest blieb
byte-identisch.

## Prüfung

```text
python -m pytest public_benchmark/tests -q
264 passed in 1.75s
```

Log: `data/test_runs/public_benchmark_restore_20261117.log`

## Ablage und Lizenz

Die Rohdaten und `records.jsonl` bleiben in den bestehenden
`.gitignore`-Pfaden und sind nicht Teil des Commits. Für beide Quellen ist
keine ausreichende Lizenz dokumentiert; die Manifeste bleiben als
Quellen- und Lizenznachweis im Repository.
