# `yun2024:3 comparator_mean`: −7,0 statt −0,7 (15.11.2026)

Frage: Ist die Abweichung eine Ziffern-Verrutschung des Modells oder steht die
Zahl im Artikel? Gold bleibt unverändert.

## Textfenster der Zelle

Quelle: `PMC1216327.md` (16.578 Zeichen), zwei Stellen nennen denselben
Vergleich:

* **Kurzfassung, Position 1.151–1.303 (Abstract):** „The mean body weight gain
  was greater among patients receiving WGJ (+ 50.7 gm) as compared with the
  patients in the AJ group (+ 18.3 gm) or the patients fed WA (- 0.7 gm)
  (p = 0.08)."
* **Ergebnisabschnitt, Position 8.987–9.194:** „The mean body weight gain was
  also higher among the juice fed patients; there was a mean weight gain of
  18.3 gm in the AJ fed patients and of 50.6 gm in those given WGJ, whereas
  there was a mean loss of body weight (- 7.0 gm) among the WA group patients
  (p = 0.08)."

Beide Sätze beschreiben denselben Vergleich (WA gegen WGJ, p = 0,08), nennen
aber unterschiedliche Zahlenpaare: Abstract **50,7 / −0,7**, Ergebnisteil
**50,6 / −7,0**. Eine Tabelle mit diesem Wertepaar gibt es nicht — die
Zeichenkette „body weight gain" kommt nur an diesen zwei Stellen vor.

## Vorhersagen

| Lauf | intervention_mean | comparator_mean | passt zu |
|---|---|---|---|
| Lauf 9 (`yun_dev_v6`) | 50,6 (Gold) | **−7,0** | Ergebnisteil |
| Lauf 10 (`yun_dev_v6b`) | 50,7 | −0,7 (Gold) | Abstract |
| Lauf 11 (`yun_dev_v6c`) | 50,6 (Gold) | **−7,0** | Ergebnisteil |

Jeder Lauf zitiert **ein** Zahlenpaar vollständig und in sich stimmig. Kein
Lauf mischt die Stellen, keiner verschiebt eine Dezimalstelle.

## Befund

**Keine Ziffern-Verrutschung.** −7,0 steht wörtlich im Artikel; das Modell liest
den Ergebnisteil, während Gold −0,7 aus der Kurzfassung nimmt. Gold selbst ist
über die beiden Stellen hinweg **gemischt**: 50,6 aus dem Ergebnisteil, −0,7 aus
dem Abstract. Kein konsistentes Lesen des Artikels kann beide Goldzellen
gleichzeitig treffen — deshalb ist genau eine der beiden Zellen in jedem Lauf
falsch, und zwar abhängig davon, welche Stelle das Modell zitiert.

Das ist derselbe Datensatz wie die bereits dokumentierte 50,6/50,7-Dopplung,
nur dass die Abweichung hier 6,3 statt 0,1 beträgt und damit den MAE der v6-
Läufe (0,037–0,039) vollständig erklärt.

## Folgt daraus eine Gegenmaßnahme?

**Keine Prompt-Änderung.** Die Regel „Zahl wörtlich übernehmen" ist erfüllt; das
Modell erfindet nichts. Eine Prompt-Verschärfung würde nur die willkürliche
Wahl zwischen zwei belegten Stellen verschieben und wäre am Dev-Satz nicht
prüfbar.

Sinnvoll sind zwei datenseitige Schritte, beide ohne Gold-Änderung:

1. Die Zelle `yun2024:3 comparator_mean` neben `intervention_mean` als
   **dokumentierten Gold-Konflikt** führen (Mechanismus `GEPRUEFTE_FAELLE` in
   `analyze_errors.py`), damit sie in künftigen Auswertungen als Datenqualität
   und nicht als Modellfehler erscheint. Kostet nichts, ändert keine Metrik.
2. Wenn dieser Fall sauber getrennt werden soll, ist die einzige belegbare
   Regel „bei Doppelangaben gilt der Ergebnisteil, nicht die Kurzfassung" — sie
   macht beide Zellen richtig oder beide falsch und braucht einen eigenen Lauf
   zur Prüfung; sie ist damit eine neue Prompt-Version, keine Korrektur.
