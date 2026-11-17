# Repo-Neuaufbau `meta-analysis-pipeline-agent` — 17.11.2026

## Anlass

Das öffentliche Repo war über `refs/pull/1/head` ungekürzt abrufbar: der PR-Ref zeigte
auf `e2d21c3c49` mit 378 Dateien, darunter Golden-Set, alle `tests/`,
`supervisor.py`, zwei private Server-/Tunnel-Skripte und `dataset.py`;
38 Dateien mit Sperrbegriff-Treffern. `master` selbst war sauber
(37 Commits, 428 Blobs, 0 Treffer), aber PR-Refs lassen sich weder löschen noch
überschreiben. Einzige Abhilfe: Repo löschen und aus dem geprüften Export neu anlegen.

## Ablauf

1. Altes Repo auf `private` gestellt → anonymer Abruf sofort beendet
   (`https://github.com/...` HTTP 404, `git ls-remote … refs/pull/1/head` leer).
2. `gh repo delete bauerhartmut/meta-analysis-pipeline-agent --yes` → gelöscht,
   Seite danach HTTP 404.
3. `gh repo create bauerhartmut/meta-analysis-pipeline-agent --public --disable-wiki`
   → angelegt (GitHub setzte Default-Branch zunächst auf `main`).
4. Push aus `export_clean_20261117`: `master` → `b0b8c2f` ("Workflow: Refspec korrigiert"),
   242 Dateien im Baum.
5. Default-Branch auf `master` korrigiert (Repo-Seite danach HTTP 200).
6. Branch-Protection gesetzt — der Einzelaufruf
   `PUT …/protection/required_status_checks` antwortet auf einem frisch angelegten Repo
   mit HTTP 404; der Sammelaufruf `PUT …/protection` verlangt ein explizites
   `"restrictions": null` (sonst HTTP 422). Gesetzt per `--input -`.

## Ergebnis (verifiziert)

| Prüfung | Ergebnis |
| --- | --- |
| Sichtbarkeit | `public`, Default-Branch `master` |
| HEAD / Dateien | `b0b8c2f`, 242 Dateien |
| `refs/pull/*` | 0 Einträge |
| anonym `refs/pull/1/head` | leer |
| anonyme Refs | nur `refs/heads/master` |
| Repo-Seite anonym | HTTP 200 |
| CI „Sperrbegriff-Scan" | `success` (10 s, Run 44138625539) |
| CI „Export check" | `success` (11 s, Run 44138624948) |
| Required Checks | `export-check`, `sperrbegriff-scan`, `strict` |
| PR-Pflicht | aktiv (`dismiss_stale_reviews`, 0 Approvals) |
| `enforce_admins` | aktiv |
| Force-Push / Branch-Löschung | gesperrt |
| Conversation Resolution | verlangt |
| Wiki | aus; Issues/Projects | an |

## Sicherungen (außerhalb des Repos)

- `export_clean_20261117_review/export_master_20261117.bundle` — vollständige History
  des alten Stands (`git bundle verify` bestätigt).
- `export_clean_20261117_review/repo_einstellungen_20261117.json` — alter Repo-Zustand
  (keine Beschreibung, keine Topics, Wiki aus, Issues an).
- `export_clean_20261117_review/branch_protection_20261117.json` — alte Protection.

## Offen

- GitHub-Profil-/Suchcache kann die alte Seite kurzzeitig noch zeigen; die Daten sind weg.
- Der private Baum (`meta-analysis-agent`) ist unberührt; sein Remote zeigt nicht auf
  das öffentliche Repo.
