# private/ — nie veröffentlicht

Dieser Ordner ist über `.gitignore` ausgeschlossen (nur diese README ist
versioniert), und der Release-Bau (`scripts/baue_release.py`) liest
ausschließlich `public/`. Beides zusammen heißt: Aus diesem Ordner geht nichts
nach draußen.

Hierhin gehören Dinge, die lokal bleiben müssen:

- Notizen, Entwürfe, Screenshots, Korrespondenz
- Skripte und Konfiguration für private Infrastruktur (Heimnetz, Tunnel,
  Zweitrechner)
- alles mit Konten, Adressen, Zugangsdaten oder personenbezogenen Daten

Nicht hierher gehören Dinge, die versioniert werden sollen — die gehören in den
normalen Arbeitsbaum. Dieser Ordner ist eine Ablage, kein Archiv.
