# Interventionsarm aus der Dokumentdefinition (18.11.2026)

Offline geprüft, kein Netz, kein Modellaufruf, keine Testdatei geschrieben.

## Beleg im Dokument

`PMC4319071` definiert die Arme im Abstract:

```
a basic (tailored intervention targeting individual cognition and
self-regulation processes; n=456), plus (basic intervention additionally
targeting environmental-level factors; n=459), and control (generic nutrition
information; n=434) group
```

Der Record nennt nur `Intervention + targeting environmental-level factors`.
Die Definition von `plus` enthaelt genau diese Woerter (4 von 4 Tokens,
Rueckwaerts 4 von 6), die von `basic` nur `targeting` (1 von 4 = 0.25, unter
der Schwelle 0.5). Damit ist `Plus` der Interventionsarm - belegt, nicht geraten.

## Umsetzung

- `semantics.document_arm_definitions(text)`: findet `armname (definition)` mit
  Arm-Merkmal (`n =`, `intervention`, `control`, `group`, `instruction`,
  `usual`); andere Klammerzusaetze bleiben aussen vor.
- `transfer_arms_from_document(tables, context, text)`: bindet den Arm mit
  `arm_basis="dokument"` an **Zeilenlabels**, deren Wort die Definition trägt.
- Eingebunden in `engine.run_document` (Telemetrie `document_arms`), in
  `run_benchmark.py`, `pruefe_outcome_matching.py` und
  `diagnose_reachability.py`.

Bewusst **nur Zeilenlabels**, keine Spaltenkoepfe: der Armname einer Zeile
benennt die Zeile selbst. In `PMC4319071:T1` traegt die Spalte unter `Plus`
den Wert von `Control` (157.73), weil dort das Strichraster verschoben ist -
ein Spaltenarm daraus waere ein falscher Wert. Ein Testversuch mit
Spaltenbindung erzeugte genau diese drei falschen Felder (`intervention_mean`
157.73, `_standard_deviation` 64.54, `_events` 330) und wurde deshalb verworfen.

Test: `test_document_definition_proves_the_intervention_arm`; 51 Tests gruen.

## Die vier offenen Goldfelder von `PMC4319071`

| Feld (Gold) | vorher | nachher |
|---|---|---|
| `intervention_mean` 167.61 (`yun2024:112`) | nicht erreichbar | **erreichbar**, `T2` Zeile 16 (Plus) / Spalte 4 = `167.61 (3.92)` |
| `intervention_mean` 2.5 (`yun2024:111`) | nicht erreichbar | **erreichbar**, `T2` Zeile 16 (Plus) / Spalte 6 = `2.50 (0.13)` |
| `intervention_standard_deviation` 83.71 (`yun2024:112`) | nicht erreichbar | nicht erreichbar |
| `intervention_standard_deviation` 2.76 (`yun2024:111`) | nicht erreichbar | nicht erreichbar |

Zu den beiden Streuungen, mit Beleg: `83.71` und `78.33` kommen im Dokument
**nicht** vor (0 Treffer); `2.71` ebenfalls 0; `2.76` steht nur als Teil von
`72.76` (SD der Basic-Gruppe in `T1`). Die Tabellen drucken `Mean (SE)`, also
Standardfehler, keine Standardabweichung. Die Gold-SD sind damit aus diesem
Dokument nicht lesbar - sie zu setzen waere erfunden.

## dev

| Groesse | vorher | nachher |
|---|---|---|
| Dokumente mit Armdefinitionen | - | 11 |
| Records mit gebundenem Zeilenarm | - | 0 |
| erreichbare Goldfelder | 16 | 16 |
| Records mit mindestens einem Treffer | 5 | 5 |

Die Definitionen in dev greifen nicht, weil dort kein Zeilenlabel den
Definitionsnamen traegt. dev bleibt unveraendert; die Erweiterung ist
dokumentspezifisch. Artefakte: `dev_dokumentarm_20261118.json`,
`dev_outcome_matching_dokumentarm_20261118.json`.

## Testartefakte unberuehrt

`selection_test.json` `6539869cf90729c3`, `offline_struktur_20261118`
`03f8997885fad6ed`, `offline_fokus_20261118` `ca2e9369b4c90e81` - vorher und
nachher gleich; kein Testlauf, keine Testdatei geschrieben. Die Pruefung an
`PMC4319071` war read-only auf dem Dokumenttext.

## Naechster Schritt

`T4` liefert dieselben Felder wie `T2` mit anderen Werten (Vegetables 4 Monate
143.25 statt 158.67). Vor einem Modelllauf braucht es eine Auswahlregel "eine
Tabelle je Outcome und Zeitpunkt" - sonst liest das Modell zwei Kandidaten fuer
dasselbe Feld. Das ist billiger als jeder Netzlauf und offline pruefbar.
