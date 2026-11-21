# Nachregel fuer Gruppengroessen ohne Groessenzeile (21.11.2026)

Offline, ohne Netzaufruf. Zwei deterministische Quellen, sonst Verweigerung:

1. Satz mit Zahl und Armbeschreibung (`40 patients were randomized ...`).
2. Nenner `k/n` in einer Tabellenzeile mit selbstbeschrifteter Armzeile.

## Ergebnis an den 48 Ziel-Faellen

| Kennzahl | Wert |
|---|---:|
| Faelle ohne Groessenzeile | 48 |
| Regel liefert einen Wert | 0 |
| davon richtig | 0 |
| davon falsch | 0 |
| verweigert | 48 |

Quellen der gelieferten Werte: 0 aus Saetzen,
0 aus Nennern, 0 aus
beiden (deckungsgleich).

## Warum die Regel verweigert

| Kennzahl | Wert |
|---|---:|
| Ziel-Faelle mit `events` | 29 |
| Ziel-Faelle mit `group_size` | 19 |
| Wert irgendwo als Nenner | 16 |
| Wert im Umfeld eines Armworts (150 Zeichen, grobe Naeherung) | 12 |

Ereigniszaehler haben weder Groessenzeile noch Nenner; sie sind mit dieser
Regel grundsaetzlich nicht zu holen. Bei den Groessenfaellen steht der Goldwert
zwar oft als Nenner oder in Armnaehe, aber in Tabellen anderer Subgruppen
(Beispiel yun2024:120: Nenner 30/52, Gold 20/44) oder als Kompletter-Zahl
(yun2024:547: `68 of 72`). Die Stichprobe der Satzkandidaten bestand
ausschliesslich aus Gesamtzahlen (`A total of 328 patients`) oder Fragmenten
(`1 women`). Auch die fuenf Satz-Lieferungen ausserhalb der 48 (etwa 440 statt
122, 1171 statt 357) waren falsch; die Satzquelle ist damit nicht belastbar.

## Wirkung auf die Bilanz

| Modus | TP | FP | TP-Verlust |
|---|---:|---:|---:|
| additiv (nur fehlende Schluessel) | 0 | 2 | 0 |
| ersetzen (ueberschreibt) | 0 | 0 | 0 |

Die Regel liefert insgesamt 2 Zellen ueber die 77
betroffenen Records; gezaehlt ist jede Zelle gegen das Gold des jeweiligen
Records.

## Grenzen

- Nur Gruppengroessen. Die 47 Ereignis-Felder (`events`) kann die Regel nicht
  fuellen, weil Ereigniszaehler keine Groessenzeile und keinen Nenner haben.
- Saetze werden an `;`, `and` und Satzgrenzen getrennt; ein Satz, der beide
  Arme nennt, wird verweigert.
- Nenner brauchen eine Kopfzeile, in der jede Spalte einen Arm nennt; sonst
  verweigert die Regel.
