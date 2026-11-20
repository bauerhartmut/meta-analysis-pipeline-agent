# qwen3.5-397b auf yun2024:52: Treffer ausserhalb von PMC3877023 (20.11.2026)

Ein freigegebener Aufruf. Erste Probe des Modelleffekts auf einem der 33
P5-Abbruchrecords aus einer **anderen Publikation** (`PMC3195393`). Modell
`gwdg/qwen3.5-397b-a17b`, Satz-Locator (`stage1_satz`), Budget 16.000,
Temperatur 0, Lesezeit 900 s. Rohdaten: `predictions_satz_52_qwen_16000.jsonl`.

## Warum dieser Record

Aus den 33 leeren P5-Records (`leere_p5_muster_20261120.json`) bleiben nach
Ausschluss von `PMC3877023` nur 15 Records der Klasse `prosa_mehrfachpaar` bzw.
`prosa_einzelpaar`. Deren Abdeckung im 6.000-Zeichen-Ausschnitt ist duenn:

| Record | Dokument | Goldzellen | Werte im Ausschnitt |
|---|---|---:|---|
| `yun2024:204` | PMC5380326 | 2 | 1/1 |
| `yun2024:525` | PMC5325897 | 6 | 3/4 |
| `yun2024:523` | PMC5325897 | 6 | 3/4 |
| **`yun2024:52`** | **PMC3195393** | **6** | **2/6** |
| uebrige 11 | - | - | 0/… bis 1/6 |

`yun2024:52` ist der einzige nie gemessene Record aus einem voellig unberuehrten
Dokument mit mindestens zwei erreichbaren Goldwerten. Genau zwei Werte sind im
Ausschnitt gedruckt: `11.5` (comparator) und `13.6` (intervention); die
Standardabweichungen 0,07/0,13 und die Gruppengroessen 562/463 stehen nicht im
Fenster.

## Ergebnis

| Groesse | Wert |
|---|---|
| Status | **ok** (`finish_reason = stop`) |
| Completion-Tokens | **7.400** von 16.000 |
| Reasoning-Zeichen | 29.285 |
| Inhalt | 782 Zeichen, **2 Locators** |
| Dauer | 333,11 s |
| `satz_im_ausschnitt` | **True** fuer beide |
| `zielwerte_im_satz` | **[11,5, 13,6]** fuer beide |
| `found` | **True** fuer beide |
| `timepoint` | `postintervention` (intervention), `pre-intervention` (comparator) |

Beide Locators tragen denselben Satz, woertlich aus dem Ausschnitt:

> In the study site, there was no significant difference in the overall restraint
> rate between the pre- and postintervention periods although the overall
> restraint rate had a slightly upward trend from 11.5% to 13.6% (*P* = 0.405)
> postintervention.

## Warum das ein Treffer ist

Der Satz nennt die Arme **nicht** mit Namen, sondern ueber die Richtung:
„from 11.5% to 13.6% … postintervention". Der Kontext setzt Intervention =
„After restraint reduction program" (also nachher) und Comparator = „Before
restraint reduction program" (also vorher). Das Gold folgt dem:
`intervention_mean` = 13,6, `comparator_mean` = 11,5.

Das Modell ordnet genau so zu: `intervention` = 13,6 mit `timepoint =
"postintervention"`, `comparator` = 11,5 mit `timepoint = "pre-intervention"`.
Die Armrichtung - die klassische Fehlerquelle bei „from X to Y"-Saetzen - ist
getroffen, nicht geraten. Der Satz ist als Belegstelle geeignet; ein
Stufe-2-Aufruf darauf kann 2 der 6 Zellen erreichen (11,5 / 13,6), die uebrigen
vier sind im Ausschnitt nicht gedruckt.

## Was der Aufruf fuer die Modellfrage beantwortet

**Der Modelleffekt traegt ueber PMC3877023 hinaus.** qwen-Stufe-1-Stand:

| Record | Dokument | Ergebnis |
|---|---|---|
| `yun2024:420` | PMC3877023 | Treffer (4/6 Werte im Satz, erste Schnittstelle) |
| `yun2024:421` | PMC3877023 | **falsches Negativ** (`found: false`) |
| `yun2024:119` | PMC4323894 | Treffer (Zeitpunkt `6 months post-trauma`) |
| **`yun2024:52`** | **PMC3195393** | **Treffer (Armrichtung korrekt)** |

Drei Treffer bei vier Aufrufen, davon zwei in Publikationen ausserhalb von
`PMC3877023`; das eine falsche Negativ liegt **innerhalb** dieser Publikation.
Die frueher formulierte Sorge, der Effekt haenge an einer einzelnen
Publikation, ist damit fuer `n = 2` fremde Dokumente widerlegt. Das ist eine
Aussage ueber vier Records, nicht ueber die 33.

Ein zweiter, unabhängiger Punkt: `yun2024:52` ist einer der 33 Records, auf
denen der P5-Lauf mit `glm-5.3` (Budget 24.000, volles Dokument) abgebrochen
ist - 95.546 Reasoning-Zeichen ohne Inhalt. Auf demselben Record antwortet qwen
in 7.400 Tokens mit einem woertlich belegten Satz. Der Vergleich ist **nicht**
sauber: Prompt-Fassung und Ausschnitt unterscheiden sich (dort Volltext bis
45.000 Zeichen, hier 6.000). Er zeigt aber, dass die knappere Fassung auf einem
Record funktioniert, auf dem die groessere scheiterte - der Ausschnitt ist als
Ursache fuer diesen Record ausgeschlossen.

## Kosten

Gemessene Completion-Tokens: 151.044 (bisherige Reihe) + 7.400 = **158.444**.
Eingabetokens sind nicht budgetiert und hier nicht enthalten.

## Grenzen

- **n = 1** Aufruf auf 52, und **n = 2** fremde Dokumente insgesamt. Was auf
  weiteren 29 Abbruechen passiert, ist nicht gemessen.
- Der Ausschnitt deckt nur 2 von 6 Goldzellen ab. Der Treffer ist an zwei
  Werten geprueft, nicht an sechs.
- Die Armzuordnung ist inhaltlich korrekt, aber nicht metrisch bewertet: Stufe 1
  liefert keine Zellen, und ein Stufe-2-Aufruf auf diesem Satz steht aus.
- Der Satz enthaelt die Wendung „no significant difference", waehrend das Gold
  die beiden Prozentsaetze als Arm-Mittelwerte fuehrt; `*P* = 0.405` passt zur
  Aussage, die Bewertung dieses Satzes als „Mittelwert-Bericht" stuetzt sich
  aber auf die Annotation, nicht auf den Text.
