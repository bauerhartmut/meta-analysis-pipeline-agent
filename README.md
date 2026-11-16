# Meta-Analysis Agent

Ein Metaanalyse-Agent als Forschungsprototyp. Er recherchiert zu einer Frage
im Web, liest wissenschaftliche Volltexte (PDF), extrahiert Effektmaße
**Wort für Wort aus der Quelle** (Verbatim-Kontrakt), liest unlesbare
Tabellenbilder doppelt mit einem Vision-Modell (Abweichung → `disputed`,
nie Mittelung), bildet Hypothesen, prüft sie adversarial, poolt statistisch
(LLM-frei, reproduzierbar) und erzeugt einen zitierfähigen Bericht. Läuft
lokal, lange, mit Run-Resume nach Neustart.

> **Zitatregel des Projekts:** Jede zitierte Zahl und jede Satzpassage wird
> exakt aus der Quelle übernommen und in der Datenbank gegen den Quelltext
> geprüft. Die statistische Verarbeitung (`meta/`) ist LLM-frei — Zahlen
> werden nie von einem Sprachmodell errechnet.
>
> **Keine autonome Freigabe:** Der aktuelle Stand ist ein assistierter
> Forschungsprototyp. Numerische Extraktion darf nur mit vollständiger
> menschlicher Prüfung verwendet werden; automatisches Pooling und eine
> Aussage „validiert“ sind derzeit nicht zulässig.

## Aktueller Stand

Kurz gesagt: Die Infrastruktur steht, die unabhängige Validierung der
numerischen Extraktion ist der Engpass.

| Bereich | Stand |
|---|---|
| Agentenrahmen | vorhanden; lokaler Lauf, Run-Resume, Dashboard auf localhost |
| Statistik | deterministisch und LLM-frei; Pooling, Heterogenität und Sensitivitätsanalysen im Code |
| Goldstandard A/B | A abgeschlossen: 30 Dokumente, 69 Effektzeilen, 13 Begründungen ohne Effektzeile. B offen: 30 Dokumente. Kein Konsens, keine Kappa-Berechnung. |
| C1/Yun v6c | 992/1308 exakte Felder (75,8 %), 148/249 vollständig exakte Records (59,4 %), 0 Halluzinationen, 0 Parse-/Schemafehler. Gates G2–G5 offen. |
| Yun-Benchmark | 60 geschichtete Testrecords: Precision 0,8324, Recall 0,6102, F1 0,7042. 20-Record-Vergleich bei 8.000 Tokens: GLM 0,8369, Qwen3.5-397B 0,8169, Qwen3-30B 0,5950. |
| Unabhängiger Holdout | fehlt; der 249er-Test ist verbraucht |
| Nutzung | nur assistiert mit vollständiger menschlicher Prüfung aller Zahlen; kein automatisches Pooling |

Damit ist das Projekt kein fertiger autonomer Forscher, sondern eine
validierungsgetriebene Extraktions- und Synthese-Pipeline im Aufbau. Die
belastbaren Messpunkte und ihre Grenzen stehen im
[Projektstatus](docs/projektstatus_2026-11-13.md), im
[Yun-Benchmark-Bericht](benchmark_research_report_20261116.md) und im
[öffentlichen Benchmark-Bereich](public_benchmark/README.md).

## Was funktioniert

- **Belegte Extraktion:** Jede Effektzeile trägt ein exaktes Zitat mit
  Zeichenposition; der Prüfer vergleicht es gegen den gespeicherten Volltext.
- **Getrennte Doppellesung:** Unlesbare Tabellenbilder werden zweimal gelesen.
  Abweichungen werden als `disputed` markiert, nie gemittelt.
- **LLM-freie Statistik:** Pooling und Metaregression laufen deterministisch
  im Code, nicht über ein Sprachmodell.
- **Reproduzierbare Läufe:** Der Agent läuft lokal, lange und mit
  Run-Resume nach einem Neustart.
- **Öffentliche Prüfspur:** Benchmarks, Goldstandard-Fixtures und
  Validierungsschritte liegen im Repository und sind nachvollziehbar.

## Was noch fehlt

- **Zweitannotation B:** Ohne den unabhängigen Rücklauf gibt es keine
  Inter-Rater-Reliabilität und keinen A/B-Vergleich.
- **Unabhängiger G5-Holdout:** Der bisherige Test ist verbraucht; ein neuer,
  artikeldisjunkter und vorab eingefrorener Holdout fehlt.
- **Vollständiger Yun-Testsplit:** Gemessen sind Stichproben, nicht alle
  656 Testrecords.
- **Zeitpunktkonvention:** `T1`, `baseline` und `cross-sectional` sind ohne
  verbindliche Konvention nicht in Wochenwerte auflösbar.

## Benchmark

Der Yun-2024-Benchmark prüft die numerische Extraktion von Armwerten
(N, Mean, SD, Ereigniszahlen). Die wichtigsten Ergebnisse:

| Messung | Ergebnis |
|---|---|
| 60 geschichtete Testrecords, 4.000 Tokens | Precision 0,8324 / Recall 0,6102 / F1 0,7042 |
| 20 Records, 8.000 Tokens, GLM-5.3 | Precision 0,9365 / Recall 0,7564 / F1 0,8369 |
| 20 Records, 8.000 Tokens, Qwen3.5-397B | Precision 0,9062 / Recall 0,7436 / F1 0,8169 |
| 20 Records, 8.000 Tokens, Qwen3-30B | Precision 0,8372 / Recall 0,4615 / F1 0,5950 |

Das größte Fehlerbild sind Arm-, Populations- und Zeitpunktverwechslungen,
nicht Halluzinationen. Der vollständige Testsplit ist nicht gemessen; die
Zahlen sind Stichproben mit entsprechenden Konfidenzintervallen. Details,
Fehlerklassen und Reproduktionsbefehle stehen im
[Benchmark-Bericht](benchmark_research_report_20261116.md).

## Was öffentlich ist — und was nicht

- **Öffentlich:** der überwiegende Teil des Agentenrahmens (Dashboard, Tests,
  Benchmark- und Prüfskripte), `public_benchmark/`, die
  Goldstandard-Fixtures unter `data/golden_tables/`, die B-Arbeitsunterlagen
  unter `data/golden_effects/` und die Benchmark-Baseline unter
  `data/baseline/`. Die vollständige A-Annotation ist aus
  Blindheitsgründen nicht öffentlich.
- **Bewusst nicht im Repository:** die in `.gitignore` als Kernbausteine
  markierten Module (u. a. Orchestrierung, Konfiguration, Bericht, Pooling
  und Extraktion), API-Keys (nur `.env`) und Lauf-Datenbanken unter
  `data/*.db`. Die `*_PRIVAT.md`-Dateien beschreiben diese Bausteine, ohne
  ihren Quellcode zu veröffentlichen.

## Setup

Voraussetzung: Python 3.10+ (Windows ok, Bash für Shell-Kommandos).

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# oder: .venv/bin/pip install -r requirements.txt  # Linux/macOS
cp .env.example .env                            # LLM-Zugang und lokale Pfade eintragen
```

Erster Lauf zu einem Thema:

```bash
python run.py --topic "Does green tea consumption affect short-term memory?"
```

Dashboard (Port 8080, nur localhost):

```bash
python research_agent/dashboard/standalone_server.py
```

Tests:

```bash
export PYTHONIOENCODING=utf-8
python -m pytest research_agent/tests -q
python -m pytest public_benchmark/tests -q
```

## Struktur

```text
research_agent/        Agentenrahmen, Dashboard, Tests; Kernbausteine geschützt
public_benchmark/      Benchmarks, C1/Yun, Validierung, Goldstandard
scripts/               Prüf- und Reproduktionsskripte
docs/                  Projektstatus, Arbeitsnotizen, externe Unterlagen
data/                  Fixtures und ausgewählte Referenzdaten; Lauf-DBs lokal
```

## Grenzen

- Englischsprachige Quellen dominieren; die PDF-Lesung ist layoutabhängig.
  Die Vision-Lesung springt bei unlesbaren Text-Layouts ein und meldet
  Abweichungen als `disputed`.
- Kein Desktop-GUI; Bedienung über CLI und Web-Dashboard auf localhost.
- Kein Multi-User-Betrieb: Das Dashboard hat **keine Authentifizierung** und
  bindet standardmäßig nur auf `127.0.0.1`.
- Keine autonome Freigabe: B ist offen, der unabhängige G5-Holdout fehlt und
  der 249er-Test ist verbraucht.
- Die 30 Goldstandard-Volltexte sind ein gemischtes Methodensample, kein
  themenspezifischer dCBT-I-Benchmark.

## Lizenz

MIT — siehe `LICENSE`.
