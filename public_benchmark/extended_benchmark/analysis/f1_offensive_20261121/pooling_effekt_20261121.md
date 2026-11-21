# Gepoolte Effektschaetzung in P5 mit und ohne Ersetzungen

Offline, ohne Netzaufruf. Effektableitung: Log-Odds-Ratio (binaer) bzw.
Hedges g (kontinuierlich), gepoolt mit `pool(method="hksj")` aus
`research_agent/meta/pooling.py`. Die Ableitung ist eine einfache,
hier dokumentierte Naeherung, nicht die Effektpipeline des Projekts.

## Alle vollstaendigen Records je Stand

| Stand | Zellen ersetzt | k | pooled | 95 %-KI | I2 | tau2 |
|---|---:|---:|---:|---|---:|---:|
| unveraendert | 0 | 24 | 0.125 | -0.302 bis 0.551 | 91.1 | 0.2709 |
| 33 Zellen | 33 | 24 | -0.018 | -0.575 bis 0.538 | 92.6 | 0.3315 |
| 43 Zellen | 43 | 24 | -0.018 | -0.575 bis 0.538 | 92.6 | 0.3315 |
| Gold (Referenz) | 0 | 58 | 0.318 | -0.412 bis 1.048 | 97.8 | 0.6929 |

## Records, deren Effekt sich aendert

| Record | Typ | P5 | mit Ersetzung | Gold |
|---|---|---:|---:|---:|
| `yun2024:347` | continuous | -6.238 | -6.782 | -6.782 |
| `yun2024:668` | continuous | 0.957 | 0.277 | 0.197 |

## Sensitivitaet ohne Extremwerte (|g| <= 3, gemeinsame Menge)

| Stand | k | pooled | 95 %-KI | I2 | negativ / positiv |
|---|---:|---:|---|---:|---:|
| unveraendert | 19 | 0.086 | -0.210 bis 0.382 | 89.0 | 12 / 8 |
| 33 Zellen | 19 | 0.052 | -0.226 bis 0.330 | 88.5 | 12 / 8 |
| 43 Zellen | 19 | 0.052 | -0.226 bis 0.330 | 88.5 | 12 / 8 |
| Gold (Referenz) | 19 | 0.092 | -0.155 bis 0.339 | 88.2 | 10 / 10 |

## Wo die Ersetzungen den Pool beruehren

| Stand | ersetzte Records | davon vollstaendig (im Pool) | Effekt geaendert |
|---|---:|---:|---:|
| 33 Zellen | 19 | 2 | 2 |
| 43 Zellen | 24 | 2 | 2 |

Die 10 Zellen, die das Gate zusaetzlich verwirft, liegen auf Records, die
im P5-Pool nicht vollstaendig sind; deshalb sind beide Staende gepoolt gleich.

## Gemeinsame Menge (k = 20)

| Stand | k | pooled | 95 %-KI | I2 | tau2 |
|---|---:|---:|---|---:|---:|
| unveraendert | 20 | 0.043 | -0.331 bis 0.417 | 89.5 | 0.1977 |
| 33 Zellen | 20 | -0.115 | -0.669 bis 0.438 | 91.9 | 0.2607 |
| 43 Zellen | 20 | -0.115 | -0.669 bis 0.438 | 91.9 | 0.2607 |
| Gold (Referenz) | 20 | -0.026 | -0.505 bis 0.454 | 91.7 | 0.1760 |
