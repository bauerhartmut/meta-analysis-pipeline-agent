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
