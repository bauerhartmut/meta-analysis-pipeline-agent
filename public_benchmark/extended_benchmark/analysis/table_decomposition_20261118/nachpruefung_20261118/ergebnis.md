# Nachtrag Sprint 47 - Caption-Leser und Gegenprobe

Stand 18.11.2026. Offline, rein lesend: kein Modelllauf, kein Netz, Gold und
eingefrorene Auswahl unveraendert. Zahlen aus `caption_leser.json`,
`gegenprobe.json`, `gegenprobe_dev.json`.

## 1. Was liest `table.caption` - und was verschiebt die Korrektur?

Der Parser `research_agent/table_decomposition/parser.py` ist die Quelle der
geaenderten Captions. Andere Caption-Quellen (JATS-Parser
`research/jats_tables.py`, `research/table_extractor.py`,
`verification/tables.py`, `meta/arm_level.py`) bleiben unberuehrt, weil sie
ihre Captions selbst lesen und nicht aus diesem Parser.

Innerhalb dieses Parsers lesen vier Stellen die Caption; alle vier
verschieben sich:

| Leser | Wirkung | Groesse |
| --- | --- | --- |
| `strategies._table_header` (Zeile `CAPTION (verbatim): ...` in **jedem** Einheiten-Prompt) | neuer Text in 31 Tabellen; Zahl der Einheiten unveraendert 729 | +1 Caption-Zeile je Einheit, max. +105 Zeichen je Prompt |
| `strategies._verbatim_block` / `crops.make_crop` (Zeichenspanne ab `caption_char_span`) | Spanne beginnt 31-mal frueher (am Caption-Block), Ausschnitt wird laenger | +0 bis +164 Zeichen, 0-mal kuerzer, `includes_caption` 6 -> 31 |
| `validation.table.caption in prompt` (`caption_fehlt`), `crop_ohne_caption` | **0 Einheiten ohne Caption vorher und nachher** (die Kopfzeile traegt sie immer); `crop_ohne_caption` entfaellt fuer die 31 Tabellen | 729 Einheiten, 0 Fehler |
| `engine.py` Strukturzeile `caption[:120]` | neuer Text in 31 Strukturzeilen | 31 Zeilen |

Nicht verschoben, aber zu wissen:

* `select_tables.py` schreibt `caption[:200]` in eine Auswahl-JSON. Die
  eingefrorene Test-Auswahl bleibt unveraendert (sie traegt den alten Text);
  eine neu gebaute Auswahl traegt den neuen. Gelesen wird das Feld dort nicht
  zurueck.
* Drei Captions sind mehrzeilig (`PMC5360580:T3`, `:T4`, `:T5`). Sie werden mit
  Leerzeichen verbunden und sind deshalb **kein zusammenhaengender Teilstring**
  des Verbatim-Blocks (dort steht der Zeilenumbruch). Die Kopfzeile traegt sie
  zusammenhaengend, daher entsteht kein `caption_fehlt` - aber wer die Caption
  spaeter im Ausschnitt sucht, muss mit Zeilenumbruechen rechnen.

**Folge: Die Caption-Korrektur ist eine eigene Aenderung**, nicht Teil der
Tabellenwahl. Sie ist als eigener Commit abgetrennt (mit den zwei
Caption-Tests und diesem Nachweis); die Wahl folgt im zweiten Commit.

## 2. Gegenprobe der Tabellenwahl auf unbenutzten Records

Die Regel entstand auf der eingefrorenen Test-Auswahl (59 Records, 31
Dokumente). Die Gegenprobe baut mit demselben deterministischen Verfahren
(`select_tables.build_candidates` + `select`) eine Auswahl aus Records, deren
**Dokument** dort nicht vorkommt (`pruefe_tabellenwahl_gegenprobe.py`,
Deckel 4 Tabellen je Dokument; die Test-Auswahl nutzt 2). Kein Goldwert steuert
die Auswahl; `require_bound` zaehlt Feldnamen, keine Werte.

| Auswahl | Records | Tabellen | Dokumente | erreichbar | wertgleich vorher -> nachher | Wechsel | verloren | Armwechsel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Test (Bau der Regel) | 59 | 60 | 31 | 94 | 58 -> 68 | 9 | 0 | 0 |
| Gegenprobe (unbenutzte Dokumente) | 25 | 26 | 9 | 42 | 27 -> **29** | 2 | 0 | 0 |
| dev-Split (echter Held-out) | 4 | 4 | 3 | 8 | 5 -> 5 | 0 | 0 | 0 |

Die zwei Wechsel der Gegenprobe sind `yun2024:345`/`:347` (`PMC5686687:T1` ->
`:T2`, Outcomes `Pain` und `Need for Ibuprofen`, je eine Outcome-Zeile). Beide
gewinnen ein Feld, keines verliert eines, kein Arm aendert sich.

Damit ist die Gegenprobe bestanden, aber schwach belegt: auf 26 unbenutzten
Tabellen feuert die Regel zweimal und gewinnt zwei Felder, ohne zu verlieren.
Ueber die Rate falscher Wechsel sagt das nichts - dafuer sind 26 Tabellen zu
wenig. Der dev-Split ist mit vier Tabellen (20 Kandidaten in 43 Records) kein
eigenstaendiger Test; er zeigt nur, dass dort nichts kaputtgeht.

## Grenzen

* Gegenprobe-Umfang: 457 freie Records liefern 194 Kandidaten, davon nach
  Deckeln 26 Tabellen aus 9 Dokumenten. Der Korpus ausserhalb der 31
  Test-Dokumente ist klein.
* Gemessen wurde die Feldebene (erreichbar/wertgleich), nicht die
  Modellleistung: dafuer waeren Netzlaeufe noetig.
* Die Gegenprobe-Auswahl entstand mit dem neuen Code; die Kandidatenmenge
  haengt nicht an der Caption (nur der gespeicherte Text), ein Vergleich mit
  der alten Caption-Suche wurde nicht erneut gefahren.

## Empfehlung

Der groesste Hebel bleibt die Fliesstext-Zahl (`4/79`, `5.1% (3/83)`): sie
erschliesst die fuenf noch offenen Populationsfelder und braucht keinen
weiteren Parser-Umbau. Vor einem Netzlauf lohnt eine breitere Gegenprobe nur,
wenn mehr Dokumente lokal vorliegen - mit 9 freien Dokumenten ist der Nutzen
gering. Risiko der Caption-Aenderung ist jetzt benannt (31 Prompts/Crops,
keine Validierungsfehler); sie kann getrennt begutachtet werden.
