# Tragen Zitate und Zufallstreffer die 92 Goldwerte? (20.11.2026)

Rein offline: jede Fundstelle eines Goldwerts wird nach Abschnitt, Zitatkontext und Tabellenkontext eingeordnet. Kein Modellaufruf, kein Netz, Gold und Predictions unveraendert.

## Einschraenkung vorab

- Keines der 33 Dokumente hat eine References-Ueberschrift; die Dateien enden vor der Literaturliste. Literaturnachweise im Text sind deshalb nur eckige Ziffernklammern und Autoren-Jahr-Klammern.
- Pipe-Tabellen gibt es nicht; Tabellen liegen eingeflacht als Text mit `n =`, `mean`, `SD` vor. Ein sicheres Urteil "fremde Tabelle" ist offline nicht moeglich; die 19 Tabellenfunde sind die eingeflachte Ergebnistabelle des eigenen Trials, weil jedes Dokument eine Publikation enthaelt.

## Etiketten der Goldwerte

| Etikette | Werte |
|---|---:|
| `ergebnisteil_text` | 56 |
| `ergebnisteil_tabelle` | 19 |
| `abstract` | 2 |
| `methoden` | 0 |
| `diskussion` | 2 |
| `body_sonstiges` | 0 |
| `unbekannt` | 12 |
| `zitat_oder_verweis` | 1 |
| `nirgends` | 26 |
| **Summe** | **118** |

Von 118 Goldwerten sind 92 im Text auffindbar und 26 nicht. Belastbar im Ergebnisteil stehen **75**; die uebrigen 17 verteilen sich auf Abstract (2), Diskussion (2), Zitat/Verweis (1) und nicht klassifizierbare Dokumente (12).

## Fenster und Orakel auf den belastbaren Fundstellen

| Groesse | alle Textfundstellen | nur Ergebnisteil | Ergebnisteil + unbekannt |
|---|---:|---:|---:|
| Goldwerte mit Fundstelle | 92 | 75 | 87 |
| im aktuellen 6.000er-Fenster | 67 | 48 | 56 |
| Orakel: bestes 6.000er-Fenster | 91 | 74 | 85 |
| drei Stuecke zu 2.000 Zeichen | 72 | 53 | 61 |

Auf den belastbaren Fundstellen bleibt ein Abstand von **26** Werten zwischen dem besten einzelnen Fenster (74) und dem aktuellen Fenster (48). Zaehlt man die 12 Werte aus Dokumenten ohne erkannte Body-Ueberschrift als belastbar mit, sind es 85 gegen 56, also 29 Werte Abstand.

## Records mit Auffaelligkeiten

| Record | Werte | im Text | belastbar | Fenster | Orakel | mit unbekannt | Fenster | Orakel | Etiketten |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `yun2024:52` | 6 | 6 | 0 | 0 | 0 | 6 | 2 | 5 | unbekannt: 6 |
| `yun2024:152` | 3 | 3 | 0 | 0 | 0 | 2 | 2 | 2 | unbekannt: 2, zitat_oder_verweis: 1 |
| `yun2024:273` | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | nirgends: 1, abstract: 1 |
| `yun2024:304` | 3 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | ergebnisteil_text: 1, nirgends: 1, abstract: 1 |
| `yun2024:557` | 6 | 2 | 0 | 0 | 0 | 2 | 2 | 2 | nirgends: 4, unbekannt: 2 |
| `yun2024:559` | 6 | 2 | 0 | 0 | 0 | 2 | 2 | 2 | nirgends: 4, unbekannt: 2 |
| `yun2024:678` | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | diskussion: 2 |

## Antwort auf die Frage

Von den 92 im Text gefundenen Werten steht **1** ausschliesslich als Zitat- oder Verweisnummer: 152: 7.0 ist die Abbildungsnummer in "Figure 7", kein Messwert. **75** stehen im Ergebnisteil, davon 19 ausschliesslich in eingeflachten Tabellentext. Nur 2 Werte stehen allein im Abstract, 2 allein in der Diskussion, 12 in Dokumenten ohne erkannte Body-Ueberschrift (52, 152, 557, 559). Der Abstand zwischen Fenster und Orakel bleibt auf der belastbaren Teilmenge erhalten (48 gegen 74); die Aussage "Startregel statt Breite" haengt damit nicht an Zufallstreffern. Die absoluten Zahlen sinken aber: fuer den Ergebnisteil heisst es 74 statt 91.

Auf `yun2024:52` stehen die sechs als `unbekannt` gefuehrten Werte sichtbar in der Ergebnistabelle (`n = 463`, `n = 562`, "from 11.5% to 13.6%"); die Body-Ueberschrift fehlt nur im Markdown. Deshalb ist die Spalte "Ergebnisteil + unbekannt" als Obergrenze mitgefuehrt: sie liefert 85 gegen 56 im Fenster, also denselben Befund.

## Vorbehalt

- Die Abschnittsgrenzen haengen an erkannten Ueberschriften. Wo keine Body-Ueberschrift gefunden wird, bleibt der Abschnitt `unbekannt` und die Fundstelle zaehlt nicht als belastbar; das ist streng, nicht grosszuegig.
- Der Tabellen-Naeherungswert prueft nur das Umfeld von 250 Zeichen. Eine eingeflachte Baseline-Tabelle kann als Outcome-Kontext durchgehen, wenn das Outcome-Stichwort im selben Umfeld steht.
- Ein Wert im Abstract kann der Hauptbefund sein; er ist hier nicht belastbar, weil der Ergebnisteil die Bindung an Zeile und Arm traegt.

Rohdaten: `fundstellen_20261120.json`.
