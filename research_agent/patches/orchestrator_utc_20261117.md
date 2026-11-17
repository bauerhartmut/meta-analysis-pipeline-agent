# Orchestrator: timezone-aware UTC im Journal

**Datum:** 2026-11-17  
**Datei:** `research_agent/orchestrator.py` (geschützt, gitignored)  
**Status:** lokal wirksam, nicht committed

## Anlass

Drei Tests der letzten Harness-Suite meldeten eine `DeprecationWarning` für
`datetime.utcnow()` in der Journal-Kopfzeile. Der Zeitstempel war UTC, aber
ohne Zeitzoneninformation.

## Ankerpunkt

Die Kopfzeile, die `_write_journal_file` für jeden Zyklus schreibt:
`## Cycle <n> - <Datum> <Uhrzeit> UTC`. Dort wurde `datetime.utcnow()`
verwendet.

## Wirkung

`datetime.now(timezone.utc)` liefert denselben UTC-Text wie bisher, jetzt
aber mit explizitem `tzinfo=UTC`. Das Format und die Ausgabe bleiben
unverändert; es ändert sich nur die Art der Zeitabfrage.

## Prüfung

- Fokussierte Tests für Journal-/Session-Lifecycle und Run-Resume.
- Keine `datetime.utcnow()`-Warnung mehr in diesen Tests.
- `python scripts/pruefe_report_patch.py` bleibt grün.

## Sicherung

`local_patches/orchestrator_20261117.py` — byte-identischer Stand vor der
Änderung. Kein Quellcode und kein Diff in diesem Eintrag.
