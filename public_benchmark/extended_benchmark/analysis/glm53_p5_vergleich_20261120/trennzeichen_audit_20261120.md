# Trennzeichen-Audit der Analyse- und Messskripte (20.11.2026)

Anlass: der alte Zahlvergleich in `falschwert_20261120.py` las `7.69` als 769, weil er Trennzeichen ohne Pruefung der Gruppengroessen entfernte. Geprueft ist, ob andere Skripte denselben oder den spiegelbildlichen Fehler haben.

## Dynamisch: vorhandene Parser mit denselben Teststrings

| Funktion | `7.69` | `7,69` | `769` | `1,919` | `1.919` | `1.234,5` | `1,234.5` | `11,897` | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `gemeinsam.als_zahl` | 7.69 | 7.69 | 769.0 | 1919.0 | 1919.0 | - **!** | - **!** | 11897.0 | fehlerhaft |
| `werte_p5_aus.zahl` | 7.69 | 7.69 | 769.0 | 1.919 | 1.919 | - **!** | - **!** | 11.897 | fehlerhaft |
| `vergleiche.zahl` | 7.69 | 7.69 | 769.0 | 1.919 | 1.919 | - **!** | - **!** | 11.897 | fehlerhaft |
| `baue_yun699.zahl` | 7.69 | - **!** | 769.0 | 1919.0 | 1.919 | - **!** | 1234.5 | 11897.0 | fehlerhaft |
| `arm_level.parse_number` | 7.69 | 7.69 | 769.0 | 1.919 | 1.919 | 1234.5 | 1234.5 | 11.897 | ok |
| `precheck_gold` | 7.69 | 7.69 | 769.0 | 1.919 | 1.919 | 1.234, 5.0 **!** | 1.234 **!** | 11.897 | fehlerhaft |
| `pruefe_extraktion.zahl` | 7.69 | 7.69 | 769.0 | 1.919 | 1.919 | 1234.5 | 1.2345 **!** | 11.897 | fehlerhaft |

`!` markiert ein Ergebnis ausserhalb der zulaessigen Lesarten. Mehrdeutige Eingaben (`1,919`, `1.919`, `11,897`) gelten als bestanden, wenn eine der beiden Konventionen getroffen wird.

## Statisch: Fundstellen im Repo

45 Fundstellen in `*.py` (ohne `.venv`). Die Spalte `Gruppierung` sagt, ob im Umfeld eine Pruefung auf Dreiergruppen steht.

| Datei | Zeile | Muster | Gruppierung | Code |
|---|---:|---|---|---|
| `public_benchmark/extended_benchmark/adapters/common.py` | 33 | Komma wird zu Punkt (Spiegelrichtung) | nein | `text = text.replace(",", ".")` |
| `public_benchmark/extended_benchmark/analysis/glm53_p5_vergleich_20261120/vergleiche_20261120.py` | 49 | Komma wird zu Punkt (Spiegelrichtung) | nein | `text = str(wert).strip().replace(",", ".")` |
| `public_benchmark/extended_benchmark/analyze_errors.py` | 252 | Komma wird zu Punkt (Spiegelrichtung) | nein | `variants.append(f"{value:,.0f}".replace(",", "."))` |
| `public_benchmark/extended_benchmark/check_timepoints.py` | 53 | Komma wird zu Punkt (Spiegelrichtung) | nein | `value = float(match.group(1).replace(",", "."))` |
| `public_benchmark/extended_benchmark/iterativ/gemeinsam.py` | 170 | Komma wird entfernt | ja | `s = s.replace(",", "")` |
| `public_benchmark/extended_benchmark/iterativ/gemeinsam.py` | 174 | Komma wird zu Punkt (Spiegelrichtung) | ja | `s = s.replace(",", ".")` |
| `public_benchmark/extended_benchmark/iterativ/gemeinsam.py` | 194 | Komma wird zu Punkt (Spiegelrichtung) | ja | `out.add(ohne_leer.replace(",", "."))` |
| `public_benchmark/extended_benchmark/precheck_gold.py` | 75 | Komma wird zu Punkt (Spiegelrichtung) | nein | `roh = treffer.group(0).replace(" ", "").replace(",", ".")` |
| `public_benchmark/extended_benchmark/run_extended_extraction.py` | 467 | Komma wird zu Punkt (Spiegelrichtung) | nein | `number = float(str(value).replace(",", "."))` |
| `public_benchmark/extended_benchmark/stage_extraction.py` | 155 | Komma wird zu Punkt (Spiegelrichtung) | nein | `text = str(raw).replace(",", ".").strip()` |
| `public_benchmark/extended_benchmark/table_decomposition/diagnose_spaltenzeitpunkte.py` | 89 | Komma wird zu Punkt (Spiegelrichtung) | nein | `paare.append((float(treffer.replace(",", ".")), treffer))` |
| `public_benchmark/extended_benchmark/table_decomposition/report.py` | 28 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return f"{value:,}".replace(",", ".")` |
| `public_benchmark/extended_benchmark/yun_full/baue_yun699.py` | 77 | Komma wird entfernt | nein | `return float(versuch.replace(",", "")), True` |
| `public_benchmark/extended_benchmark/yun_full/diagnose_sprint48.py` | 456 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return f"{int(wert):,}".replace(",", ".")` |
| `public_benchmark/extended_benchmark/yun_full/diagnose_sprint48.py` | 458 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return f"{wert:,}".replace(",", ".")` |
| `public_benchmark/extended_benchmark/yun_full/nachzug_p5.py` | 147 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return f"{zahl:,}".replace(",", ".")` |
| `public_benchmark/extended_benchmark/yun_full/werte_p5_aus.py` | 104 | Komma wird zu Punkt (Spiegelrichtung) | nein | `text = str(wert).strip().replace(",", ".")` |
| `public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/utils.py` | 370 | Komma wird entfernt | nein | `return int(value.replace(',', ''))` |
| `public_benchmark/raw_data/yun_llm_meta_analysis/evaluation/utils.py` | 383 | Komma wird entfernt | nein | `return float(value.replace(',', ''))` |
| `public_benchmark/scripts/build_inventory.py` | 78 | Komma wird entfernt | nein | `text = str(value).strip().replace(",", "")` |
| `public_benchmark/scripts/build_p0_review_batch2_checklist.py` | 48 | Komma wird entfernt | nein | `value = unicodedata.normalize("NFKC", value).casefold().replace(",", "")` |
| `public_benchmark/scripts/build_p0_review_batch2_checklist.py` | 151 | Komma wird entfernt | ja | `return {token.replace(",", "") for token in tokens}` |
| `public_benchmark/scripts/goldstandard/adapter_eururology.py` | 46 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return float(value.replace(",", "."))` |
| `public_benchmark/scripts/goldstandard/adapter_pico_corpus.py` | 55 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return float(match.group(0).replace(",", "."))` |
| `public_benchmark/scripts/goldstandard/analyse_medsr_bench.py` | 70 | Komma wird zu Punkt (Spiegelrichtung) | nein | `text = str(value).strip().replace(",", ".")` |
| `public_benchmark/scripts/goldstandard/score_tier1.py` | 53 | Komma wird zu Punkt (Spiegelrichtung) | nein | `cells.append((key, float(str(value).replace(",", "."))))` |
| `public_benchmark/scripts/goldstandard/score_tier1.py` | 127 | Komma wird zu Punkt (Spiegelrichtung) | nein | `values[key] = float(str(value).replace(",", "."))` |
| `public_benchmark/scripts/match_dcbti_review_studies.py` | 279 | Komma wird zu Punkt (Spiegelrichtung) | nein | `value = float(number.replace(",", "."))` |
| `public_benchmark/tests/test_bilanz_adversarial_20261118.py` | 41 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return float(str(wert).strip().replace(",", "."))` |
| `research_agent/agents/evidence_scorer.py` | 117 | Komma wird entfernt | nein | `n = int(match.group(1).replace(",", ""))` |
| `research_agent/llm/token_zaehler.py` | 224 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return f"{int(wert or 0):,}".replace(",", ".")` |
| `research_agent/meta/arm_level.py` | 116 | Punkt und Komma werden beide entfernt | ja | `token = token.replace(".", "").replace(",", ".")` |
| `research_agent/meta/arm_level.py` | 118 | Komma wird entfernt | ja | `token = token.replace(",", "")` |
| `research_agent/meta/arm_level.py` | 120 | Komma wird entfernt | ja | `token = token.replace(",", "")` |
| `research_agent/meta/arm_level.py` | 122 | Komma wird zu Punkt (Spiegelrichtung) | ja | `token = token.replace(",", ".")` |
| `research_agent/meta/benchmark.py` | 48 | Komma wird zu Punkt (Spiegelrichtung) | nein | `entry["wert_num"] = float(str(entry.get("wert") or "").replace(",", "."))` |
| `research_agent/meta/quote_gaps.py` | 52 | Komma wird zu Punkt (Spiegelrichtung) | nein | `text = text.replace(",", ".")` |
| `research_agent/research/vision_table.py` | 49 | Komma wird zu Punkt (Spiegelrichtung) | nein | `s = s.replace(",", ".")` |
| `research_agent/table_decomposition/parser.py` | 56 | Komma wird zu Punkt (Spiegelrichtung) | nein | `s = s.replace(",", ".")` |
| `research_agent/table_decomposition/provenienz.py` | 160 | Komma wird zu Punkt (Spiegelrichtung) | nein | `wert = float(einzel.group(2).replace(",", "."))` |
| `research_agent/table_decomposition/semantics.py` | 1255 | Komma wird zu Punkt (Spiegelrichtung) | nein | `werte.add(round(float(treffer.group(1).replace(",", ".")), 6))` |
| `research_agent/tests/test_pwert_korroboration.py` | 46 | Komma wird zu Punkt (Spiegelrichtung) | nein | `zelle.value = float(treffer.group(0).replace(",", "."))` |
| `research_agent/verification/compare.py` | 24 | Komma wird zu Punkt (Spiegelrichtung) | nein | `out.append(float(token.replace(",", ".")))` |
| `research_agent/verification/tables.py` | 49 | Komma wird zu Punkt (Spiegelrichtung) | nein | `return float(str(text).replace(",", "."))` |
| `scripts/pruefe_extraktion_20261109.py` | 83 | Punkt und Komma werden beide entfernt | nein | `text = text.replace(".", "").replace(",", ".") if "," in text else text` |
