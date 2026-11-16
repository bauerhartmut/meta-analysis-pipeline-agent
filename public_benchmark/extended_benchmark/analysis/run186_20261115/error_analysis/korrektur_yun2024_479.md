# Korrektur des Goldes von yun2024:479 (Version 2 der Testbasis, 16.11.2026)

## Anlass

Der Hauptlauf auf allen 76 Records meldete eine MAE von 30,09. Zwei Zellen
trugen davon 3.837 der 3.912 absoluten Abweichung — beide in `yun2024:479`
(Gruppengrößen 1,919 und 1,922). Eine Gruppengröße von 1,9 Personen ist
unmöglich, der Artikel wurde geprüft.

## Befund im Artikel

PMC4144850, Tabelle 4 „Effect of the intervention on health outcomes, 2011“,
Kopfzeile: `Health Outcomes | Control Group | Intervention Group | ITT
Unadjusted | ITT Adjusted`. Die Zeile lautet:

```
Anemic: Hb<110 g/l   1,922   0.508   1,919   0.562   0.050 [-0.011 to 0.110] …
```

Die Kommata sind **Tausendertrenner**: 1.922 Personen in der Kontrollgruppe und
1.919 im Interventionsarm. Die Ereigniszahlen folgen aus den berichteten
Anteilen:

* 1919 × 0,562 = 1078,5 → **1.078** Ereignisse (Intervention)
* 1922 × 0,508 = 976,4 → **976** Ereignisse (Kontrolle)

Die Armzuordnung des Goldes war also richtig, nur die Dezimalstelle falsch
(`1.078` statt `1078`, `1.919` statt `1919`, `1.922` statt `1922`). Das Modell
antwortete 1919 und 1922 und hatte recht; es wurde für einen Gold-Fehler
bestraft.

## Änderung

| Feld | alt | neu |
|---|---|---|
| `intervention_group_size` | 1,919 | 1919 |
| `intervention_events` | 1,078 | 1078 |
| `comparator_group_size` | 1,922 | 1922 |
| `comparator_events` | 976 | 976 (unverändert) |

Die Quelle `records/yun_test76_ohne_ziel.jsonl` bleibt unverändert. Die Korrektur
steht als Tabelle `GOLD_KORREKTUREN` in `annotate_test76.py` und wird beim
Erzeugen der Ziel-Datei angewandt — eine Neuerzeugung verliert sie damit nicht.

Geprüft: Nach dem Neuerzeugen unterscheidet sich genau ein Record (479) in genau
drei Zellen; Reihenfolge, Zielzeitpunkte und die übrigen 239 Zellen sind
identisch.

## Hashes

* Version 1: `06fea97c37864debe50f130f03a926f5fb5654a1cd0d2ef75ab330da04ad0ca7`
* Version 2: `74fd0c057356c22831fae45d71644d8b7640a8a109fb48a60cc7782cfb1db704`
* Version 3: `3f811bed35653bda0da92a5ab13dc16a13a23dfc79c04a0808b0d2ec8267b587`
  (Comparator von 289–295 und zwei Goldzellen, `korrektur_v3_comparator.md`)

Aktualisiert in `tests/test_test76_ziel.py`, `teststrategie.md`,
`test76_sha256.txt` und `gesamtbericht.md`.

## Tests

* `test_datei_hat_den_eingefrorenen_hash` trägt den neuen Hash.
* `test_gold_von_479_ist_korrigiert` prüft die vier Werte und die Gegenprobe
  über die im Artikel berichteten Anteile (0,508 und 0,562).
* `test_korrektur_ueberlebt_eine_neuerzeugung` prüft, dass die Korrektur im
  Annotationsskript steht.

## Wirkung auf den 76er-Hauptlauf (ohne API neu ausgewertet)

| Kennzahl | Version 1 | Version 2 |
|---|---|---|
| Zell-F1 | 0,5351 | **0,5455** |
| Precision | 0,7254 | **0,7394** |
| Recall | 0,4239 | **0,4321** |
| MAE | 30,0929 | **0,5763** |
| `zieltreu` richtig / falsch | 55 / 11 | **57 / 9** |
| `zieltreu` Precision | 0,8333 | **0,8636** |
| Zellen richtig / falsch gesamt | 91 / 25 | **93 / 23** |

Unverändert: Abdeckung 130/243, exakte Records 16/76, `rueckfall` 48 Zellen
(32 richtig, 16 falsch), Gruppengrößen-Ausnahme 4/4, Auslassungen 125,
technische Ausfälle 5, leere Antworten 29, Belegstufen.

## Grenzen

Geprüft wurde eine Zeile, nicht das ganze Korpus. Andere Records mit
Tausendertrennzeichen im Artikel sind nicht systematisch gesucht worden; ein
Mustertest „Goldwert < 10, im Artikel steht derselbe Wert mit Komma und drei
Ziffern danach“ wäre der nächste Schritt.
