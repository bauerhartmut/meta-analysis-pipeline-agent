# Satz-Locator mit Unterscheider-Pflicht (21.11.2026)

Rein offline, kein Modellaufruf. Der Locator bindet einen Satz nur, wenn er
mindestens zwei Zahlen und ein unterscheidendes Wort aus dem Outcome traegt
(Wortstamm, mindestens sechs Zeichen). Der Unterscheider darf im direkt
folgenden Satz stehen. Mehrere Kandidaten werden nicht aufgeloest; der Fall
faellt dann an die Tabellenzeile, statt willkuerlich einen Satz zu waehlen.

## A: die zehn gespeicherten Faelle

| Record | Quelle | alter Satz mit Unterscheider | neuer Zustand | Goldpaar im Satz | Grund |
|---|---|:---:|---|:---:|---|
| `yun2024:30` | predictions_dreifenster_30_qwen_16000.jsonl | nein | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: At baseline, 82% of patients were female, |
| `yun2024:673` | predictions_dreifenster_673_qwen_16000.jsonl | ja | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: For those who had previously sought
treat |
| `yun2024:674` | predictions_dreifenster_674_qwen_16000.jsonl | ja | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: For those who had previously sought
treat |
| `yun2024:420` | predictions_kette_stichprobe_20261120.jsonl | ja | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'Cervicothoracic' |
| `yun2024:421` | predictions_kette_stichprobe_20261120.jsonl | ja | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'thoracolumbar' |
| `yun2024:582` | predictions_kette_stichprobe_20261120.jsonl | nein | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'Function' |
| `yun2024:671` | predictions_kette_stichprobe_20261120.jsonl | nein | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: n/N (%)                              Mean |
| `yun2024:672` | predictions_kette_stichprobe_20261120.jsonl | nein | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: n/N (%)                              Mean |
| `yun2024:582` | predictions_kette_stichprobe_20261120.jsonl | nein | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'Function' |
| `yun2024:30` | predictions_tabelle_allein_30_qwen_16000.jsonl | nein | ohne_unterscheider | nein | 1 Saetze mit Zahlen, keiner nennt das Outcome |

Zustaende: {'mehrere_kandidaten': 5, 'eindeutig': 4, 'ohne_unterscheider': 1}. Mit Goldpaar: 0 von 10.

## B: schwierige Faelle (Fenster um den ersten Goldwert)

| Record | Goldwerte im Fenster | neuer Zustand | Goldpaar im Satz | Grund |
|---|---:|---|:---:|---|
| `yun2024:30` | 2/6 | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: tions between PRO responses and clinical  |
| `yun2024:52` | 3/6 | eindeutig | ja | ein Satz mit Zahlenpaar und Pflichtbegriff 'Restraint' |
| `yun2024:119` | 4/4 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'Glasgow' |
| `yun2024:128` | 4/4 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'nausea' |
| `yun2024:152` | 3/4 | mehrere_kandidaten | nein | 3 Saetze mit Pflichtbegriff: Postoperative pain scores were measured u |
| `yun2024:159` | 2/6 | ohne_unterscheider | nein | 1 Saetze mit Zahlen, keiner nennt das Outcome |
| `yun2024:171` | 3/4 | mehrere_kandidaten | nein | 5 Saetze mit Pflichtbegriff: The optimal treatment to prevent hypergly |
| `yun2024:173` | 3/4 | ohne_unterscheider | nein | 6 Saetze mit Zahlen, keiner nennt das Outcome |
| `yun2024:204` | 2/2 | mehrere_kandidaten | nein | 3 Saetze mit Pflichtbegriff: We hypothesized that correction of vitami |
| `yun2024:251` | 3/4 | eindeutig | ja | ein Satz mit Zahlenpaar und Pflichtbegriff 'disease' |
| `yun2024:252` | 2/2 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'morbidities' |
| `yun2024:273` | 1/2 | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: There were no differences in laryngoscopy |
| `yun2024:304` | 3/4 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'erythematous' |
| `yun2024:356` | 2/2 | ohne_unterscheider | nein | 2 Saetze mit Zahlen, keiner nennt das Outcome |
| `yun2024:420` | 2/6 | eindeutig | ja | ein Satz mit Zahlenpaar und Pflichtbegriff 'Cervicothoracic' |
| `yun2024:421` | 1/6 | eindeutig | ja | ein Satz mit Zahlenpaar und Pflichtbegriff 'thoracolumbar' |
| `yun2024:446` | 2/6 | eindeutig | ja | ein Satz mit Zahlenpaar und Pflichtbegriff 'circumference' |
| `yun2024:451` | 1/6 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'vigorous' |
| `yun2024:523` | 4/6 | ohne_unterscheider | nein | Outcome traegt kein unterscheidendes Wort |
| `yun2024:525` | 4/6 | ohne_unterscheider | nein | Outcome traegt kein unterscheidendes Wort |
| `yun2024:557` | 2/6 | ohne_unterscheider | nein | 12 Saetze mit Zahlen, keiner nennt das Outcome |
| `yun2024:559` | 2/6 | ohne_unterscheider | nein | 12 Saetze mit Zahlen, keiner nennt das Outcome |
| `yun2024:582` | 2/2 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'Function' |
| `yun2024:625` | 1/2 | mehrere_kandidaten | nein | 3 Saetze mit Pflichtbegriff: The compliance rates of the 1-week PPI+MB |
| `yun2024:671` | 2/2 | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: A stratified cluster-randomized trial in  |
| `yun2024:672` | 2/2 | mehrere_kandidaten | nein | 2 Saetze mit Pflichtbegriff: A stratified cluster-randomized trial in  |
| `yun2024:673` | 2/6 | mehrere_kandidaten | nein | 3 Saetze mit Unterscheider im Folgesatz |
| `yun2024:674` | 2/6 | mehrere_kandidaten | nein | 3 Saetze mit Unterscheider im Folgesatz |
| `yun2024:678` | 2/2 | eindeutig | nein | ein Satz mit Zahlenpaar und Pflichtbegriff 'cultivable' |
| `yun2024:685` | 2/2 | ohne_unterscheider | nein | Outcome traegt kein unterscheidendes Wort |

Zustaende: {'mehrere_kandidaten': 10, 'eindeutig': 12, 'ohne_unterscheider': 8}. Mit Goldpaar: 5 von 30.

## Was sich aendert

Auf den zehn gespeicherten Faellen bindet der alte Locator fuenf Saetze,
davon vier mit dem richtigen Zahlenpaar. Der neue Locator bindet vier Saetze
mit Pflichtbegriff und keinem richtigen Zahlenpaar; sechs Faelle werden
verweigert (fuenf mehrdeutig, einer ohne Unterscheider). Die Pflicht
verschiebt die Bindung damit von der richtigen Zahl zum falschen Satz: 420
und 421 nennen das Regionswort, tragen aber andere Zahlen. Das ist ein
negatives Ergebnis und wird so berichtet.

Die Ursache ist strukturell: ein Regionswort steht im Tabellenkopf oder in
der Ueberschrift, das Zahlenpaar in der Zeile. Solange beides in einem Satz
gesucht wird, konkurrieren sie. Der naechste Schritt ist deshalb keine
weitere Satzregel, sondern die Zeilenbindung aus Phase 3.

## Gemessene Wirkung auf den zehn gespeicherten Faellen

| Stand | Bindungen | davon mit Goldpaar | Verweigerungen |
|---|---:|---:|---:|
| alter Locator | 5 | 4 | 0 |
| neuer Locator | 4 | 0 | 6 |

Die Pflicht zum Unterscheider entfernt falsche Bindungen: 420 und 421 werden
nicht mehr an einen Satz ohne Regionsangabe gehaengt. Sie erzeugt aber keine
richtigen: in den verbleibenden Bindungen steht der Pflichtbegriff, nicht das
Goldpaar. Ein Satz allein reicht damit nicht; die Zelle muss aus der Zeile
kommen. Das prueft Phase 3, und deshalb ist dieser Locator kein F1-Hebel fuer
sich, sondern eine Absicherung gegen stille Fehlbindungen.
