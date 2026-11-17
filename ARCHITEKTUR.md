# Architektur

Der Agent führt eine Forschungsfrage auf eine zitierfähige quantitative
Synthese zurück. Beschrieben wird hier der Aufbau, nicht die Umsetzung: Die
Kernmodule bleiben lokal, deshalb nennt dieses Dokument keine Dateipfade,
Funktionsnamen oder Prompt-Inhalte.

## Überblick

```text
Frage
  |
  v
[1] Recherche        Föderierte Suche, DOI- und Titel-Dedupe, Ranking
  |
  v
[2] Volltext         Abstract -> PDF/XML, Abschnitts- und Seitenzerlegung
  |
  v
[3] Extraktion       Effektmaße als Zahlen, jede Zeile mit wörtlichem Zitat
  |                  und Zeichenposition; unlesbare Tabellen doppelt gelesen
  v
[4] Evidenzbewertung Hypothesen-Prüfung, Rollen, Widerspruchssuche
  |
  v
[5] Statistik        Pooling, Heterogenität, Sensitivität - LLM-frei
  |
  v
[6] Bericht          deterministisch erzeugt, Beleg je Zahl
```

Jeder Schritt schreibt in eine lokale Datenbank; ein Lauf ist nach einem
Neustart fortsetzbar (Run-Resume). Es gibt keinen Dienst, der dauerhaft läuft,
und kein Multi-User-Betrieb: Das Dashboard bindet nur auf `127.0.0.1` und hat
bewusst keine Authentifizierung.

## Verträge

Die folgenden Regeln sind der Grund, warum das System überhaupt prüfbar ist.
Sie gelten unabhängig von Modell oder Prompt-Version.

**Verbatim-Kontrakt.** Jede extrahierte Zahl trägt den Satz, aus dem sie stammt,
als exaktes Zitat mit Start- und Endposition im gespeicherten Volltext. Der
Prüfer vergleicht das Zitat gegen den Text. Ein Zitat, das nicht gefunden wird,
markiert die Zeile als unbelegt — sie wird nicht stillschweigend verwendet.

**Zwei Lesungen, keine Mittelung.** Unlesbare Tabellenbilder werden zweimal
unabhängig gelesen. Weichen die Ergebnisse ab, wird die Zeile als `disputed`
geführt. Es wird nie ein Mittelwert zweier abweichender Lesungen gebildet.

**LLM-freie Statistik.** Konversionen, Pooling, Heterogenität und
Sensitivitätsanalysen laufen deterministisch im Code. Ein Sprachmodell rechnet
in diesem System keine Kennzahl.

**Präzision vor Vollständigkeit.** Fehlt zu einem Effekt der Standardfehler und
das Konfidenzintervall, wird die Zeile nicht poolbar gespeichert, statt eine
Präzision zu schätzen. Ein berichtetes Intervall wird nur bei bekanntem Niveau
in einen Standardfehler umgerechnet.

**Keine stille Zusammenfassung.** Werden Effekte unterschiedlichen Typs ohne
definierte Konversion gemischt, wird das Pooling abgelehnt. Unterhalb einer
Mindestzahl an Studien berichtet der Bericht „zu wenige", nicht einen Mittelwert
über zwei heterogene Zahlen.

**Zeitpunkt und Richtung sind Pflicht.** Ohne verbindliche Konvention für den
Messzeitpunkt und ohne Vorzeichenkonvention („höher ist besser" vs. „höher ist
schlechter") ist ein gepoolter Effekt nicht interpretierbar; solche Zeilen
werden im Bericht als nicht auflösbar geführt.

## Rollen im Ablauf

Die Arbeit ist auf getrennte Rollen verteilt, damit ein einzelner Schritt nicht
seine eigene Prüfung schreibt: Recherche, Volltextbeschaffung, Extraktion,
Evidenzbewertung, gegnerische Prüfung, Synthese, Bericht. Die gegnerische
Prüfung darf Ergebnisse verwerfen; die Statistik wird davon nicht beeinflusst,
weil sie nur gespeicherte, belegte Zahlen liest.

## Was geschützt ist und warum

Nicht veröffentlicht werden Orchestrierung, Konfiguration, Datenbankschema,
Berichtsbau, Pooling, Extraktion sowie Such- und Vision-Pipeline. Gründe:

1. **Extraktions-IP.** Die Regelwerke und Prompts der numerischen Extraktion
   sind der eigentliche Entwicklungsaufwand des Projekts.
2. **Angriffsfläche.** Konfiguration und Datenbankschema beschreiben, wo
   Zugangsdaten und Bestände liegen.
3. **Änderbarkeit.** Ein veröffentlichter Prüfer, den ein Pull Request ändern
   kann, prüft nichts. Deshalb liegen die Prüfwerkzeuge dieses Repositories
   selbst unter Versionskontrolle und laufen als Required Check.

## Prüfbarkeit dieses Repositories

Der Scan auf Sperrbegriffe, Secret-Muster und absolute Nutzerpfade läuft über
den Arbeitsbaum und über jede erreichbare Fassung in der Historie — lokal vor
dem Push und serverseitig in der CI. Eine gelöschte Datei bleibt in der
Historie abrufbar; der Scan behandelt sie deshalb wie eine vorhandene.
