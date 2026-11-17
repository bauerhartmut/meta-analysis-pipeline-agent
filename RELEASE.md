# Zwei Zonen — was rausgeht und was nie rausgeht

## `public/` — wird veröffentlicht

Alles, was in diesem Ordner liegt, wird veröffentlicht. Nichts außerhalb.

Veröffentlicht wird über `scripts/baue_release.py`: Der Bau liest **nur**
`public/`, kopiert es 1:1 in ein eigenes Repo (`_release/`) und prüft den
fertigen Stand samt Historie. Es gibt keine Allowlist mehr, also auch keine
Liste, in der versehentlich eine private Datei stehen kann.

Hinein gehören:

- Architekturbeschreibung (Aufbau, Verträge, Rollen) — ohne Code, ohne
  Dateipfade in die Kernmodule, ohne Prompt-Inhalte.
- Benchmark-Ergebnisse: Kennzahlen, Fehlerlandschaft, Datensatzherkunft,
  Laufprotokolle — mit Quelle und Kennzeichnung von Schätzungen.
- Der Prüfscan selbst (Hook, CI-Workflow), weil das Gate mitveröffentlicht
  werden muss, um zu wirken.

Nicht hinein gehören: Quellcode der Kernmodule, Konfiguration, Datenbankschema,
Tests, Datenbanken, Volltexte, Rohläufe, Vergleichsdateien, Pfade, Hostnamen,
Konten, personenbezogene Daten.

## `private/` — wird nie veröffentlicht

Ablage für alles, was lokal bleiben muss: Notizen, Screenshots, Zugangsdaten-
nahe Dateien, private Infrastruktur, Korrespondenz. Der Ordner ist über
`.gitignore` ausgeschlossen (nur diese README ist versioniert), und der
Release-Bau liest ihn nicht. Zwei unabhängige Gründe, warum nichts von hier
draußen landet.

## Alles andere

Der restliche Arbeitsbaum (Code, `data/`, `finetune/`, `local_patches/`,
`docs/internal/`, alte Export-Ordner) ist ebenfalls nicht Teil des Release. Er
ist nur nicht als Zone markiert, weil er ohnehin nie gelesen wird: Der Bau
greift ausschließlich auf `public/` zu.

## Ablauf einer Veröffentlichung

```bash
# 1. Inhalt in public/ ändern (Markdown, keine Daten, keine Pfade)
python scripts/baue_release.py --pruefen      # Scan auf public/

# 2. Altes Release-Verzeichnis entfernen, dann bauen
rm -rf _release
python scripts/baue_release.py --bauen \
  --remote-url https://github.com/bauerhartmut/meta-analysis-pipeline-agent.git

# 3. Push (Hook prüft Baum und Historie ein zweites Mal)
cd _release
git push -u origin master
```

## Warum das diesmal hält

| Früher | Jetzt |
|---|---|
| Allowlist über den ganzen Baum; jede getrackte Datei musste darin stehen | Nur `public/` wird gelesen; alles andere ist strukturell unerreichbar |
| Gelöschte Dateien blieben in der Historie abrufbar, geprüft wurde nur der Baum | Scan prüft jeden Commit der Release-Historie |
| Hook lokal überspringbar | Derselbe Scan läuft als CI-Required-Check auf GitHub |
| Löschen im Baum galt als „entfernt" | Löschen entfernt nichts; deshalb prüft der Scan die Historie, nicht die Absicht |
| Personenbezug nur im Blick, wenn jemand daran dachte | Commit-Identität im Release ist fest auf die noreply-Adresse gesetzt |

Die eine Regel, die alles trägt: **Der Release-Bau kennt genau einen
Quellordner.** Wer dort nichts hineinlegt, kann nichts veröffentlichen — auch
nicht aus Versehen.
