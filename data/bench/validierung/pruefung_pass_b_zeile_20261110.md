# Pruefung der Pass-B-Zeile e8ba18ca3525

Stand: 2026-11-10 · read-only · keine Modellaufrufe · keine DB-Aenderung

## Ergebnis

Die Pass-B-Zeile stammt aus einer Uebersichtsarbeit ueber prospektive
Kohorten. Das Gate erkennt das Design als Meta-Analyse; die Zeile wird
deshalb nicht als Primaerstudie gepoolt.

- `aggregate_design(...)` erkennt die Uebersichtsarbeit.
- `standardize` weist die Zeile ab.
- `build_analysis` fuehrt sie in `excluded` mit dem Grund
  "Uebersichtsarbeit ..., keine Primaerstudie", nicht in einer Gruppe und
  nicht in `off_target`.

**Entscheidung:** Die Zeile bleibt draussen; es ist keine Aenderung noetig.

## Hinweis zur SE-Skala

Die gespeicherte SE lag auf der HR-Skala. Fuer den Pool ist das
gegenstandslos, weil `standardize` bei Ratio-Typen mit vorhandenem KI die
log-SE aus dem KI berechnet. Konkrete Effekt- und SE-Werte werden hier
bewusst nicht dokumentiert.
