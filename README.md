# Metaanalyse-Agent — Architektur und Messergebnisse

Dieses Repository enthält **keinen Quellcode des Harness**. Es beschreibt, wie
der Agent aufgebaut ist, und dokumentiert, was er messbar leistet.

Die Trennung ist nicht redaktionell, sondern baulich: veröffentlicht wird
ausschließlich der Ordner `public/` des privaten Arbeitsbaums. Alles andere —
Kernmodule, Datenbanken, Volltexte, Rohläufe — liegt außerhalb und kann
technisch nicht mitwandern.

## Inhalt

| Datei | Inhalt |
|---|---|
| [`ARCHITEKTUR.md`](ARCHITEKTUR.md) | Aufbau, Datenfluss und Verträge der Pipeline |
| [`benchmark/extraktion_fehleranalyse_20261116.md`](benchmark/extraktion_fehleranalyse_20261116.md) | Yun-Benchmark: Kennzahlen, Metrik-Audit, Fehlerlandschaft |
| [`benchmark/yun_benchmark_20261116.md`](benchmark/yun_benchmark_20261116.md) | Datensatz, Herkunft, Hashes, Methodik |
| [`benchmark/laufprotokoll_20261116.md`](benchmark/laufprotokoll_20261116.md) | Was gelaufen ist: Records, Tokens, Laufzeit |
| `scripts/pruefe_sperrbegriffe.py` | Scan auf Baum und Historie (Hook + CI) |

## Ergebnisse in Kurzform

Numerische Extraktion aus RCT-Volltexten, gemessen gegen die Goldannotationen
des öffentlichen Yun-2024-Datensatzes. Alle Werte stammen aus den Berichten in
`benchmark/`; Schätzungen sind dort als solche gekennzeichnet.

| Messung | Precision | Recall | F1 |
|---|---:|---:|---:|
| 60 geschichtete Testrecords, 4.000 Tokens, GLM-5.3 | 0,8324 | 0,6102 | 0,7042 |
| 20 Records, 8.000 Tokens, GLM-5.3 | 0,9365 | 0,7564 | 0,8369 |
| 20 Records, 8.000 Tokens, Qwen3.5-397B | 0,9062 | 0,7436 | 0,8169 |
| 20 Records, 8.000 Tokens, Qwen3-30B | 0,8372 | 0,4615 | 0,5950 |

Weitere belegte Messpunkte:

- 992 von 1308 exakten Feldern (75,8 %) und 148 von 249 vollständig exakten
  Records (59,4 %) im C1/Yun-Lauf; 0 Halluzinationen, 0 Parse- oder Schemafehler.
- Von 29 falschen Zellen der 60er-Stichprobe sind 13 Arm- oder
  Populationsverwechslungen, 4 Zeitpunktfehler, 4 Einheiten- oder
  Skalierungsfehler, 4 Zeilen- oder Spaltenfehler und 4 Fälle mit
  widersprüchlichen Angaben im Paper selbst. Kein Fehler war eine Aussage ohne
  Quellenbasis.
- Das größte Qualitätsproblem ist damit die Quellenauswahl (Arm, Zeile,
  Zeitpunkt), nicht die Erfindung von Zahlen.

## Was hier bewusst nicht steht

- **Kernmodule des Harness**: Orchestrierung, Konfiguration, Datenbank,
  Bericht, Pooling, Extraktion, Such- und Vision-Pipeline. Sie sind der
  eigentliche Gegenstand des Projekts und bleiben lokal.
- **Daten**: Datenbanken, Volltexte, PDFs, Rohdaten, Run-Ordner, Fixtures.
- **Rohläufe und Vergleichsdateien**: Die Zahlen sind dadurch in diesem
  Repository **nicht nachrechenbar**. Sie sind Angaben mit dieser
  Einschränkung, keine reproduzierbaren Artefakte.

## Prüfspur

Jeder Push läuft durch einen Sperrbegriff- und Secret-Scan über den Arbeitsbaum
**und die gesamte Historie** (lokal als `.githooks/pre-push`, serverseitig als
Required Check). Es gibt keine Allowlist und keine Ausnahmen: ein Treffer
blockiert. Eine später gelöschte Datei bleibt in der Historie abrufbar — genau
deshalb prüft der Scan die Historie mit.

## Grenzen

- Englischsprachige Quellen dominieren; die PDF-Lesung ist layoutabhängig.
- Der vollständige Yun-Testsplit (656 Records) ist nicht gemessen; die Zahlen
  sind Stichproben mit entsprechenden Konfidenzintervallen.
- Der unabhängige Holdout für die Extraktionsgüte fehlt; der bisherige Test ist
  verbraucht.
- Keine autonome Freigabe: Nutzung nur assistiert mit vollständiger
  menschlicher Prüfung aller Zahlen.

## Lizenz

MIT — siehe [`LICENSE`](LICENSE).
