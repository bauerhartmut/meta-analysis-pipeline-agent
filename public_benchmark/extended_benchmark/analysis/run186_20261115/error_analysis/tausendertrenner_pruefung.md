# Tausendertrenner-Prüfung aller 243 Goldzellen (16.11.2026, read-only)

Anlass: `yun2024:479` hatte 1.922 und 1.919 Personen als 1,922 und 1,919 gelesen.
Diese Prüfung sucht denselben Fehler in der ganzen Testbasis, **ohne die
eingefrorene Datei zu ändern**. Skript: `pruefe_tausendertrenner.py`,
Ergebnis: `tausendertrenner_kandidaten.json`.

## Verfahren

Geprüft werden alle Goldzellen der Zählfelder `*_group_size` und `*_events`
(135 der 243 Zellen; Mittelwerte und SD sind legitim dezimal und bleiben außen
vor). Zwei Regeln:

* **A — Komma-Schreibweise im Text:** Wert < 1000, Wert × 1000 ganzzahlig, und
  der Artikel enthält diese Zahl mit Tausendertrenner (`1,922`) oder ohne
  (`1922`). Belegstelle wird mitgedruckt.
* **B — Zählwert nicht ganzzahlig:** Eine Anzahl von Personen oder Ereignissen
  ist immer ganzzahlig. Jeder Bruchteil verletzt die Invariante und ist der
  stärkste Hinweis — er greift auch dann, wenn die Zahl im Artikel nur als
  Anteil steht (bei 479 war 1.078 aus 1919 × 0,562 abgeleitet und kam im Text
  nicht als `1,078` vor).

## Kontrollprobe (beweist, dass die Regeln greifen)

Auf **Version 1** der Testbasis findet das Skript genau die drei kaputten Zellen
von 479 und sonst nichts:

| Record | Feld | Gold v1 | Verdacht | Beleg im Artikel |
|---|---|---:|---:|---|
| `yun2024:479` | `intervention_group_size` | 1,919 | 1919 | `1,922 0.508 1,919 0.562` |
| `yun2024:479` | `comparator_group_size` | 1,922 | 1922 | `Anemic: Hb<110 g/l 1,922 0.508` |
| `yun2024:479` | `intervention_events` | 1,078 | 1078 | (abgeleitet, kein Komma im Text) |

## Ergebnis auf Version 2

**0 Kandidaten.** Kein Zählwert ist nicht ganzzahlig, und keine kleine Zahl hat
im Artikel eine Tausendertrenner-Schreibweise. Die drei Treffer der Kontrollprobe
sind durch die Korrektur verschwunden; alle übrigen 240 Zellen sind unauffällig.

## Grenzen

* Geprüft sind Zählfelder. Ein Trennzeichenfehler in einem Mittelwert oder einer
  SD (etwa `1,234` als 1,234 statt 1234) würde nicht erfasst — dort ist die
  Dezimalzahl aber auch meist die richtige Lesart.
* Werte ab 1000 sind nicht prüfbar, weil die Verwechslung dann nicht mehr
  sichtbar ist (1919 gegen 1,919 setzt einen Wert unter 1000 voraus).
* Regel A verlangt, dass die Ziffernfolge im Text steht. Ist der Goldwert
  abgeleitet (Anteil × Gruppengröße), greift nur Regel B.
* Die Prüfung sagt nichts über falsche Armzuordnung oder falsche Zeile; dafür
  gibt es `analyse_mccb_armzeile.py`.
