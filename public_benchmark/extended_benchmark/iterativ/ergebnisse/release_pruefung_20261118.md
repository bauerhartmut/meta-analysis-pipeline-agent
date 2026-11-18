# Release-Prüfung aus `public/`

Durchgeführt am 2026-11-18, offline, ohne Netzzugriff.

## Befehl und Ausgabe

```
$ python scripts/baue_release.py --pruefen
Arbeitsbaum: 0 Treffer
Historie:    uebersprungen
Sauber: keine Sperrbegriffe, keine Secret-Muster.
Dateien in public/: 11
```

Exitcode 0.

## Was geprüft wurde

Laut `pruefe_zone()` in `scripts/baue_release.py`:

1. `git ls-files -- public` — 11 getrackte Dateien in der Veröffentlichungszone.
2. Größenlimit von 2 MiB je Datei.
3. `public/scripts/pruefe_sperrbegriffe.py --nur-baum` im Ordner `public/`.

Der Lauf schreibt nichts: Er liest die Dateiliste, prüft Größen und ruft den
Scanner auf. `git status` zeigt danach dieselben Änderungen wie vorher, keine
neuen Dateien.

## Grenzen dieser Prüfung

- **Die Historie wird übersprungen** („Historie: uebersprungen"). Geprüft wird nur
  der Arbeitsbaum von `public/`. Ein Commit, der früher einen Sperrbegriff
  enthielt und inzwischen bereinigt ist, fällt hier nicht auf.
- **Der Bau selbst ist damit nicht geprüft.** `--pruefen` sagt nichts über
  `.git`-Initialisierung, Commit, Remote oder darüber, ob der Push des
  Release-Repos gelingt. Das leistet nur `--bauen`, und das war hier nicht
  beauftragt.
- Die Prüfung betrifft ausschließlich `public/`. Der private Arbeitsbaum mit
  `public_benchmark/`, `research_agent/` und `data/` wird nicht angefasst, seine
  Eignung für eine Veröffentlichung also auch nicht bestätigt.
