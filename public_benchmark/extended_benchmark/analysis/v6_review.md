# Prüfung der v6-Prüfqueue (52 Fälle, 15.11.2026)

Quelle: `analysis/v1_20261115/human_review_queue.csv`, Status `referenz`,
Fassung `v6_target_fallback`, Fälle aus Lauf 9 (`yun_dev_v6_20261115`, 29) und
Lauf 10 (`yun_dev_v6b_20261115`, 23).

## Verteilung

| Priorität | Fälle | Inhalt |
|---|---|---|
| 2 | 10 | fehlende Zellen in zwei Records |
| 3 | 1 | große Abweichung |
| 4 | 1 | mehrdeutige Zuordnung |
| 5 | 40 | Kontrollfälle (korrekt) |

Nach Klasse: 40 korrekt, 6 „unvollständige Modellantwort", 4 „Zahl nicht
extrahiert", 2 „nicht eindeutig".

## Die zwölf Fälle mit Inhalt

**1. `yun2024:231` (6 Zellen, Lauf 9) — technisch, kein Inhaltsfehler.**
Die Antwort war kein gültiges JSON (`kein_json`, leer). Lauf 10 hat denselben
Record vollständig und richtig beantwortet (6/6 Zellen). Kein Gold-Problem,
kein Prompt-Problem; die Retry-Regel greift nur bei `finish_reason = "length"`,
nicht bei kaputtem JSON.

**2. `yun2024:83` (2 Gruppengrößen, beide Läufe) — Gold-Konflikt, nicht
Modellfehler.** Gold führt 940 und 1831. Im Artikel sind das die
**Krankenhausstandorte**, nicht die Studienarme: „940 (34 %) were hospitalised
in unit A, and 1,831 (66 %) in unit B". Die Mittelwerte des Records
(9,9 / 9,1) stammen dagegen aus dem Periodenvergleich („period 1 vs period 2").
Gold mischt also Standort-Gesamtzahlen mit Perioden-Mittelwerten; die
Annotation „Period 2" ist für die Mittelwerte belegt, für die Gruppengrößen
gibt es im Artikel keine passende Zahl. Das Modell lässt die Zellen aus — nach
der Regel korrekt. **Gold nicht geändert**, Fall bleibt als Datenqualitätsfall
dokumentiert.

**3. `yun2024:3 comparator_mean` (Lauf 9) — echter Modellfehler.** Gold −0,7,
Vorhersage **−7,0**. Der Artikel schreibt „the patients fed WA (- 0.7 gm)";
die Zehnerstelle ist verloren gegangen. Einzelfall, keine Systematik.

**4. `yun2024:3 intervention_mean` (Lauf 10) — Gold-Selbstwiderspruch.**
Vorhersage 50,7 (Artikeltext „+ 50.7 gm"), Gold 50,6 (Tabelle). Bereits in
Abschnitt 5 dokumentiert; das Modell folgt dem Text, nicht der Tabelle.

## Kontrollfälle

Die 40 Fälle der Priorität 5 sind Zellen, die das Modell richtig getroffen hat
und die als Stichprobe in die Queue kommen. Keine Auffälligkeit.

## Ergebnis

Von 52 Fällen sind **1 echter Modellfehler** (`yun2024:3 comparator_mean`), **1
technischer Ausfall** (`yun2024:231`, JSON), **2 Gold-Konflikte**
(`yun2024:83` Gruppengrößen, `yun2024:3` 50,6/50,7) und 40 Kontrollfälle ohne
Befund. Die verbleibende Lücke bei F1 0,96 ist damit überwiegend Datenqualität,
nicht Extraktionsqualität.
