# Sprint 48: Alias-Test Control -> PBO und Definition -> IPAT

Rein offline. Kein Pipeline-Umbau, `structure.json` unveraendert.

## 1. Methode

Je Record die Plan-Tabelle kopiert, die Bandspanne des Alias gesucht
(`PBO + MTX`, `IPAT`), Arm `comparator` auf die Fakten und Spalten unter dieser
Spanne gesetzt, `reachable_cells` neu berechnet und die Goldzellen mit
Gruppengroesse gegen Wert **und** Arm geprueft. Vorher-Werte aus dem
unveraenderten Lauf.

## 2. Ergebnis

| Record | Alias | vorher wertrichtig | nachher wertrichtig |
|---|---|---|---|
| `yun2024:30` | Control -> `PBO + MTX` | 393 intervention | 393 intervention, **199 comparator** |
| `yun2024:15` | Definition -> `IPAT` | 103 intervention | 103 intervention, **97 comparator** |
| `yun2024:16` | Definition -> `IPAT` | 103 intervention | 103 intervention, **97 comparator** |

Alle drei neuen Zellen tragen Wert **und** Arm. Damit:

- Feldtreffer: **94 -> 97**
- nicht widerlegt: **68 -> 71**
- Die 68 aus dem unveraenderten Lauf bleiben gueltig; 71 ist das Ergebnis
  dieser Simulation, nicht des Artefakts.

## 3. Bedingung und Risiko

- Die Zuordnung muss fachlich bestaetigt sein: `Control` ist hier die
  Placebo-Gruppe (`PBO + MTX`, n = 199), die Definition "full course of therapy
  in the hospital setting" ist `IPAT` (n = 97). Beides passt zu den Goldwerten.
- Eine generische Regel "control -> placebo" waere riskant, weil ein dritter
  Arm gemeint sein kann. Die Alias-Liste gehoert daher bewusst gefuehrt (pro
  Record oder als kontrolliertes Vokabular) und mit einem Test abgesichert.
- Ohne Alias bleibt es bei 68; die Simulation aendert nichts am Artefakt.

## 4. Umsetzung (19.11.2026)

- Die Zuordnung steht als `_ARM_ALIASEN` in `research_agent/table_decomposition/semantics.py`
  und ist auf `(record_id, Armtext)` geschluesselt; `record_id` kommt ueber
  `context_of` in den Tabellenkontext. `bind_arm`/`_score` und `_group_size_facts`
  reichen sie durch, damit sowohl Spaltenarme als auch Kopfangaben greifen.
- Generisch bleibt es bei der Textbewertung: ohne passenden Record-Schluessel
  aendert sich nichts (`test_arm_alias_curated_only_for_record`).

Gemessen am neu erzeugten `structure.json` (`offline_struktur_20261118b`,
Lauf `offline_struktur_20261119c`):

- Goldfelder: **97** in allen fuenf Verfahren; 60/60 Tabellen komplett, 0 Fehler.
- Nicht widerlegt: **71 von 97** (45 Wert und Arm, 4 Arm vertauscht, 22 anderer Wert).
- Warnungen: A **144** (137 + 7 Armkontext-Befunde), B 115, C 244, D 330, E 260.
- Nur drei Records aendern sich: `yun2024:15` 1 -> 2, `:16` 1 -> 2, `:30` 1 -> 2.
- Plan-Audit (`pruefe_armbindung_sprint48.py`): Summe 97 = Sollwert 97, 71
  kopf-basierte Feldtreffer, Bandpruefung 113 ok / 4 ohne Arm.
