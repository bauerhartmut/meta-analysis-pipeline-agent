# 186er-Lauf: vorzeitiger Abbruch (15.11.2026)

Freigabe: Vollauf über 186 Records, harte Grenze **1,2 Mio Completion-Tokens**.
Der Lauf wurde nach **18 von 186 Records** gestoppt, bei **347.204 Tokens**
(29 % der Grenze). Die Grenze selbst wurde nicht erreicht — gestoppt wurde,
weil die Hochrechnung sie zwingend gerissen hätte und drei Records an einer
Endlosschleife verbrannten.

## Zwei Vorab-Records mit spezifischem Ziel (Rückfallpfad)

| Record | Ziel | Ergebnis |
|---|---|---|
| `yun2024:75` | `week 24` | 6 Zellen; Interventionsarm `tp='24'`, **Komparator `tp='0'`**; `chosen='24'`, `discarded=['0','12']` |
| `yun2024:159` | `month 12` | 0 Zellen; beide Versuche `finish_reason = length` (24.000 + 32.000 Tokens) |

Damit ist der Rückfallpfad **belegt** — das Modell weicht vom Ziel ab und nennt
den benutzten Zeitpunkt. Zwei Einschränkungen:

1. Die Labels kommen **nackt** zurück (`'24'`, `'0'`, `'12'`) statt wie gedruckt
   (`week 24`). `normalisiere()` in `stage_extraction.py` macht daraus `'24'`;
   `klassifiziere('week 24', '24')` ergibt **`rueckfall`**. Die spätere
   Auswertung würde also jeden Treffer als Rückfall zählen, solange Labels ohne
   Einheit zurückkommen.
2. Bei `yun2024:75` steht der Komparator auf `'0'` — der Zielzeitpunkt wurde
   über die Arme hinweg gemischt (Interventionsarm Woche 24, Komparator
   Baseline), obwohl der Prompt das verbietet.

## Verlauf des Massenlaufs

| Messpunkt | Records | Tokens | leer | Retries | Prognose auf 186 |
|---|---|---|---|---|---|
| nach 2 Vorab-Records | 2 | 84.646 | 1 | 1 | — |
| nach ~2,5 min | 13 | 180.052 | 1 | 2 | 2,6 Mio |
| nach ~7 min | 17 | 334.988 | 3 | 5 | 3,7 Mio |
| Abbruch | **18** | **347.204** | 3 | 5 | ≈ 3,5 Mio |

Die Grenze von 1,2 Mio wäre bei diesem Tempo nach **etwa 60 Records** erreicht
gewesen; 126 wären offen geblieben. Ein Viertel des Budgets in 18 Records ist
kein Lauf, den man zu Ende führen sollte.

**Ursache, gemessen:** 48 % der Tokens (168.000 von 347.204) gingen in drei
Records mit `finish_reason = length` in **beiden** Versuchen — je 24.000 +
32.000 Tokens für null Zellen. Median der übrigen Zeilen: 6.500–11.000 Tokens.
Bekannter Fehlermodus (Reasoning-Schleife), hier aber gehäuft: 3 von 18.

## Was der Lauf hinterlässt

`runs/yun_test186_v6_20261115/predictions.jsonl`, 18 Zeilen, alle parsebar:

* alle 18 als `v6_target_fallback` etikettiert,
* **64 von 64 Zellen tragen einen Zeitpunkt**,
* 3 leere Zeilen (`yun2024:159`, `79`, `114`) — alle drei aus der
  Length-Schleife, nicht aus einem JSON-Fehler.

Der Lauf ist fortsetzbar: derselbe `--run-id` überspringt die 18 erledigten
Zeilen. Nichts wurde gelöscht.

## Grenzen

* 18 Records sind keine Stichprobe für 186; die Fehlerquote der Schleife
  (3/18) ist mit n=18 grob, aber sie kostet proportional am meisten.
* Die Labelform (`'24'`) ist nicht bewertet, nur festgestellt: ob das Modell den
  richtigen Zeitpunkt getroffen hat, lässt sich ohne Einheiten-Normalisierung
  derzeit nicht sagen.
* Der Abbruch ist eine Entscheidung gegen die Freigabe „Vollauf": Ersparnis
  gegenüber dem Weiterlaufen sind bis zu 850.000 Tokens, Preis ist ein
  unvollständiger Teilsatz.
