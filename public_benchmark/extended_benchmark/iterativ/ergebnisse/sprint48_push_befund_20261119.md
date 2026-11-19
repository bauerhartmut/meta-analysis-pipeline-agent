# Push-Befund Sprint 48 (19.11.2026)

## Anlass

Der Push der beiden Commits `ba36b5b` (Alias-Zuordnung) und `11d2621`
(Struktur neu erzeugt) wurde mit "non-fast-forward" abgelehnt. Der Auftrag
lautete, die zwei Commits auf den Remote-Stand zu rebasen.

## Befund: unverwandte Historien

- `origin/master` ist ein **Wurzel-Commit ohne Eltern**:
  `git rev-list --max-parents=0 origin/master` liefert nur `83fbfe1`.
- `git merge-base HEAD origin/master` endet mit Exit 1 und ohne Ausgabe -
  es gibt keinen gemeinsamen Vorfahren.
- Inhalte von `83fbfe1` ("Oeffentliche Architektur und Messergebnisse",
  9 Dateien): `.githooks/pre-push`, `.github/workflows/sperrbegriff-scan.yml`,
  `ARCHITEKTUR.md`, `LICENSE`, `README.md`, drei Dateien unter `benchmark/`,
  `scripts/pruefe_sperrbegriffe.py`.
- Lokal existieren davon `README.md`, `LICENSE` und `.githooks/pre-push` -
  ein Rebase muesste diese drei Pfade konflikthaft aufloesen.
- Lokal liegen **713 Commits** zwischen Wurzel und Spitze; `master` ist
  `ahead 713, behind 1`.

## Warum nicht rebased wurde

1. Ein Rebase auf `origin/master` spielt **alle 713 Commits** neu ab, nicht
   nur die beiden genannten; das aendert jede Commit-ID der Projektgeschichte
   und verstoesst gegen die Projektregel "keine History-Rewrites".
2. Die beiden Commits allein koennen auf dem oeffentlichen Stand nicht
   existieren: dort fehlt die gesamte Pipeline (`research_agent/`,
   `public_benchmark/`). Ein Cherry-Pick der zwei Commits ergaebe keinen
   lauffaehigen Stand und damit auch kein 97/71.
3. Der oeffentliche Stand ist erkennbar ein bewusst gesetzter
   veroeffentlichungs-Snapshot (Architektur, Lizenz, Sperrbegriff-Scan), keine
   Fortsetzung der internen Historie. Ob die interne Geschichte dort
   veroeffentlicht werden soll, ist eine Entscheidung des Eigentuemers, keine
   mechanische Push-Frage.

## Unveraenderter Stand (nach dem fehlgeschlagenen Push geprueft)

- `structure.json` (`offline_struktur_20261118b`): Goldfelder 97 in A-E,
  0 Fehler, 60/60 Tabellen komplett, Warnungen A 144 / B 115 / C 244 /
  D 330 / E 260.
- `pruefe_armbindung_sprint48.py`: Summe 97 = Sollwert 97.
- `pytest research_agent/tests/test_table_decomposition.py
  research_agent/tests/test_validation_arm_context.py` -> 52 passed.

## Optionen fuer den Push

1. **Seitenzweig** (kein Rewrite, kein Force): `git push origin master:sprint48`.
   Die beiden Commits sind auf dem Remote, `master` bleibt der Snapshot.
   Verhandlungspunkt: veroeffentlicht die komplette interne Historie.
2. **Merge unverwandter Historien**: `git merge --allow-unrelated-histories
   origin/master`, Konflikte in `README.md`, `LICENSE`, `.githooks/pre-push`
   entscheiden, dann fast-forward pushen. `master` traegt danach beide Staende.
3. **Remote unberuehrt lassen**, Arbeit lokal halten und die zwei Commits als
   Patch ausliefern (`git format-patch -2`).
