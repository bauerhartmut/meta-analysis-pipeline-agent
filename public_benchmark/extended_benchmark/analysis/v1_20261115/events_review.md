# Manuelle Prüfung: 20 falsche Ereigniszellen der Referenz

Geprüft am 15.11.2026 gegen die Artikeltexte. Grundlage sind die 20 Zeilen mit
Priorität 1 aus `human_review_queue.csv` (Version `v2_timepoint`). Die
Gold-Werte wurden nicht verändert; die Zuordnung im automatischen Lauf bleibt
unangetastet, hier steht das Ergebnis der Sichtprüfung.

Die 20 Zeilen betreffen nur **6 verschiedene Zellen** (drei Records, jeweils
mehrere Läufe). Jede Zelle ist unten einmal belegt, die Tabelle am Ende ordnet
alle 20 Zeilen zu.

## yun2024:190 — PMC5244530, sedative prescriptions

Tabelle 2, „Number and percent of patients who had prescriptions for
antidepressants and sedatives … at baseline and 3-, 6-, and 12-months follow
up". Spalten: Baseline | 3 months | 6 months | 12 months.

Zeile „Sedatives":

| Arm | Baseline | 3 Monate | 6 Monate | 12 Monate |
|---|---|---|---|---|
| Intervention (n=125) | 26 (21) | 64 (51) | 53 (42) | **52 (42)** |
| TAU (n=133) | 32 (24) | 73 (55) | 56 (42) | **51 (38)** |

Gold = 52 / 51 = **12-Monats-Spalte**. Beide Modelle greifen eine andere Spalte
derselben Zeile:

- glm liefert 64 / 73 → **3-Monats-Spalte**.
- qwen3-30b liefert 26 / 32 → **Baseline-Spalte**.

Damit ist die Ursache belegt: **falsche Tabellenspalte (falscher Messzeitpunkt)**,
nicht Prozentwert und nicht falsche Zeile.

## yun2024:191 — PMC5244530, sick leave

Tabelle 3, „Mean days of sick leave", Zeilen nach Zeitraum:

| Zeitraum | Intervention n (%) | TAU n (%) |
|---|---|---|
| 0–3 Monate | 31 (25) | 48 (36) |
| 4–12 Monate | 35 (28) | 47 (35) |
| **Total 0–12 Monate** | **49 (39)** | **64 (48)** |

Gold = 49 / 64 = **Total 0–12 Monate**. Beide Modelle liefern 31 / 48, also die
Zeile **0–3 Monate**.

Damit ist auch hier die Ursache belegt: **falsche Tabellenzeile (falscher
Zeitraum)**.

Wichtig für die Bewertung: Der automatische Lauf hatte die Zelle
`comparator_events` als „Prozentwert statt absoluter Zahl" klassifiziert, weil
64/133 = 48,1 % ist und die Vorhersage 48 lautet. Die Sichtprüfung zeigt, dass
48 **exakt die Ereigniszahl der 0–3-Monats-Zeile** ist und die Partnerzelle 31
ebenfalls exakt zu dieser Zeile passt. Die Prozentübereinstimmung ist Zufall;
die Zeilenerklärung ist die einfachere und durch beide Zellen gedeckt. Die
Klasse „Prozentwert" ist für diese Zelle **zurückzunehmen**.

## yun2024:120 — PMC4450164, ureteropelvic junction obstruction

Gold = 8/20 und 13/44 aus der Zeile „Partial obstruction" des DTPA-Scans
(Fußnote: DTPA bei 20 bzw. 44 Patienten). qwen3-30b liefert 2 und 8, das ist
die Zeile „Extravasation 2 (6.7) 8 (15.3)" aus der Tabelle „Post-operative IVP
(one month later)".

Damit: **falsche Tabellenzeile** (andere Nachuntersuchung, andere Zeile), für
beide Zellen belegt. Der automatische Lauf hatte nur die Comparator-Zelle so
klassifiziert; die Interventionszelle ist aus demselben Grund ebenfalls eine
falsche Zeile.

## Alle 20 Zeilen

| Lauf | Modell | Record | Feld | Gold | Vorhersage | Befund | Beleg |
|---|---|---|---|---|---|---|---|
| fresh | glm | 190 | intervention_events | 52 | 64 | falsche Spalte | 64 = 3-Monats-Spalte |
| fresh | glm | 190 | comparator_events | 51 | 73 | falsche Spalte | 73 = 3-Monats-Spalte |
| fresh | glm | 191 | intervention_events | 49 | 31 | falsche Zeile | 31 = 0–3-Monate |
| fresh | glm | 191 | comparator_events | 64 | 48 | falsche Zeile (nicht Prozent) | 48 = 0–3-Monate |
| retry | glm | 190 | intervention_events | 52 | 64 | falsche Spalte | wie oben |
| retry | glm | 190 | comparator_events | 51 | 73 | falsche Spalte | wie oben |
| retry | glm | 191 | intervention_events | 49 | 31 | falsche Zeile | wie oben |
| retry | glm | 191 | comparator_events | 64 | 48 | falsche Zeile (nicht Prozent) | wie oben |
| retry | qwen30 | 120 | intervention_events | 8 | 2 | falsche Zeile | 2 = Extravasation |
| retry | qwen30 | 120 | comparator_events | 13 | 8 | falsche Zeile | 8 = Extravasation |
| retry | qwen30 | 190 | intervention_events | 52 | 26 | falsche Spalte | 26 = Baseline |
| retry | qwen30 | 190 | comparator_events | 51 | 32 | falsche Spalte | 32 = Baseline |
| tp | glm | 190 | intervention_events | 52 | 64 | falsche Spalte | wie oben |
| tp | glm | 190 | comparator_events | 51 | 73 | falsche Spalte | wie oben |
| tp | glm | 191 | intervention_events | 49 | 31 | falsche Zeile | wie oben |
| tp | glm | 191 | comparator_events | 64 | 48 | falsche Zeile (nicht Prozent) | wie oben |
| tp | qwen30 | 120 | intervention_events | 8 | 2 | falsche Zeile | wie oben |
| tp | qwen30 | 120 | comparator_events | 13 | 8 | falsche Zeile | wie oben |
| tp | qwen30 | 190 | intervention_events | 52 | 26 | falsche Spalte | wie oben |
| tp | qwen30 | 190 | comparator_events | 51 | 32 | falsche Spalte | wie oben |

## Ergebnis

| Befund | Zellen (von 20) |
|---|---|
| falsche Tabellenspalte / Messzeitpunkt | 12 |
| falsche Tabellenzeile | 8 |
| Prozentwert statt absoluter Zahl | **0** |
| nicht belegbar | 0 |

Alle 20 Zellen sind belegbar; keine bleibt unklar. Es gibt in der Referenz
**keinen einzigen nachgewiesenen Prozentfall**. Die Prompt-Zeile aus
`v3_abs_count` („Ereignisse als absolute Anzahl") zielte damit auf eine Ursache,
die es in diesen Daten nicht gibt — was erklärt, warum der v3-Lauf bei den
Ereigniszahlen nichts verändert hat.

Der gemeinsame Nenner beider Fehlerarten ist die **Zeilen- und Spaltenauswahl
innerhalb einer Tabelle**, nicht das Zahlenlesen: Beide Modelle lesen die Zahl
richtig ab, greifen aber die falsche Zelle des Tabellengitters. Genau das
adressiert die mehrstufige Extraktion (Ansatz C im Bericht), nicht ein
Prompt-Zusatz zu Prozentwerten.
