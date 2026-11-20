# Hat der P5-Lauf denselben Ausschnitt benutzt? Nein (20.11.2026)

Pruefung, ob die Abdeckungszahlen aus `ausschnitt_abdeckung_20261120.py` auf den
P5-Lauf uebertragbar sind. Ergebnis vorweg: **sie sind es nicht.** Der P5-Lauf
hat das ganze Dokument gesehen, mein Analyse-Runner ein 6.000-Zeichen-Fenster.

## Wie der P5-Ausschnitt entsteht

`public_benchmark/extended_benchmark/run_extended_extraction.py`, `main()` ->
`work()`: Der Text wird vollstaendig aus `record["document"]["path"]` gelesen und
ungekuerzt an `build_prompt(record, text, ...)` gegeben. Dort gilt
`limit: int = 45000`, und alle Prompt-Bauer setzen den Text als
`f"Publication excerpt:\n{text[:limit]}"` ein - also **Anfang des Dokuments, kein
Fenster, keine Stichwortsuche**. Fuer den P5-Lauf wurde kein abweichendes
`--limit` gesetzt (die Optionsliste von `main()` fuehrt keines; `--limit` in
`main()` ist die Record-Anzahl, nicht die Textlaenge).

Mein Analyse-Runner (`zweistufig_trocken_20261120.py`) arbeitet anders:
`waehle_ausschnitt(text, stichworte, BREITE=6000, SCHRITT=500)` sucht das Fenster
mit den meisten Outcome-Treffern und nimmt es als Ganzes - **6.000 Zeichen aus
der Dokumentmitte**, nicht aus dem Anfang.

## Groessenvergleich fuer alle 33 leeren Records

Laengen aus den Dokumentdateien; Abdeckung als Zahl der Goldwerte, die im
jeweiligen Ausschnitt gedruckt sind (Zahlenvergleich, offline).

| Record | Dokument (Zeichen) | P5-Ausschnitt | Gold in P5 | Gold im 6000er-Fenster |
|---|---:|---:|---:|---:|
| 119 | 10.032 | 10.032 | 4/4 | 4/4 |
| 128 | 7.954 | 7.954 | 3/3 | 3/3 |
| 152 | 7.782 | 7.782 | 3/3 | 2/3 |
| 159 | 16.081 | 16.081 | 4/6 | 0/6 |
| 164 | 3.808 | 3.808 | 0/1 | 0/1 |
| 171 | 20.409 | 20.409 | 3/4 | 3/4 |
| 173 | 20.409 | 20.409 | 3/4 | 3/4 |
| 204 | 14.600 | 14.600 | 1/1 | 1/1 |
| 251 | 40.101 | 40.101 | 4/4 | 3/4 |
| 252 | 40.101 | 40.101 | 2/2 | 2/2 |
| 273 | 3.360 | 3.360 | 1/2 | 1/2 |
| 30 | 25.866 | 25.866 | 6/6 | 3/6 |
| 304 | 5.515 | 5.515 | 2/3 | 2/3 |
| 356 | 19.352 | 19.352 | 1/1 | 1/1 |
| 420 | 26.274 | 26.274 | 6/6 | 6/6 |
| 421 | 26.274 | 26.274 | 6/6 | 6/6 |
| 446 | 25.267 | 25.267 | 3/6 | 1/6 |
| 451 | 25.267 | 25.267 | 3/6 | 1/6 |
| 52 | 24.933 | 24.933 | 6/6 | 2/6 |
| 523 | 6.811 | 6.811 | 3/4 | 3/4 |
| 525 | 6.811 | 6.811 | 3/4 | 3/4 |
| 557 | 13.122 | 13.122 | 2/6 | 2/6 |
| 559 | 13.122 | 13.122 | 2/6 | 2/6 |
| 582 | 12.838 | 12.838 | 1/1 | 1/1 |
| 624 | 5.258 | 5.258 | 0/1 | 0/1 |
| 625 | 5.258 | 5.258 | 0/2 | 0/2 |
| 671 | 42.606 | 42.606 | 2/2 | 2/2 |
| 672 | 42.606 | 42.606 | 2/2 | 2/2 |
| 673 | 42.606 | 42.606 | 6/6 | 3/6 |
| 674 | 42.606 | 42.606 | 6/6 | 3/6 |
| 678 | 12.349 | 12.349 | 2/2 | 2/2 |
| 685 | 18.929 | 18.929 | 1/1 | 0/1 |
| 687 | 18.929 | 18.929 | 1/1 | 0/1 |

**Kein Dokument ist laenger als 45.000 Zeichen** (groesstes: 42.606). Der
P5-Ausschnitt ist damit in allen 33 Faellen das **vollstaendige Dokument**, ohne
jede Kuerzung.

- P5 hatte bei **19 von 33** Records alle Goldwerte im Prompt.
- Bei **11 von 33** unterscheidet sich die Abdeckung zwischen P5 und meinem
  Fenster (z. B. 159: 4/6 gegen 0/6; 52: 6/6 gegen 2/6; 674: 6/6 gegen 3/6).

## Was daraus folgt

1. **Die Abdeckungstabelle beschreibt nur mein Analysefenster.** Fuer den P5-Lauf
   gilt sie nicht; dort war der Ausschnitt nie zu kurz.
2. **Meine These „Beschneidungsproblem“ ist fuer P5 widerlegt.** Bei 19 der 33
   Abbrueche standen alle Goldwerte im Prompt, und der Lauf brach trotzdem mit
   0 Zeichen Inhalt ab (Reasoning zwischen 82.625 und 101.270 Zeichen). Der
   Abbruch ist dort eine Denkschleife ueber vorhandenem Material.
3. Fuer 674 heisst das: Der P5-Abbruch (0 Zeichen, 93.674 Reasoning-Zeichen) traf
   ein Dokument, in dem 23,5 und 22,6 gedruckt waren. Mein eigener 674-Lauf
   scheiterte an einem Ausschnitt ohne diese Werte - gleiches Ergebnis, andere
   Bedingung. Der P5-Befund ist der belastbare.
4. Die Auswahl der fairen Proben bleibt fuer **meine** Kette richtig (420, 421,
   119), weil dort das 6.000er-Fenster alle Werte enthaelt. Fuer Aussagen ueber
   den P5-Lauf taugt die Auswahl aber nicht als Filter.

## Nachrechnen

Die Tabelle oben ist nicht abgetippt: `ausschnitt_abdeckung_20261120.py` rechnet
beide Spalten und schreibt sie nach `ausschnitt_abdeckung_20261120.json`.

```
.venv/bin/python .../ausschnitt_abdeckung_20261120.py
```

Je Record im JSON:

- `p5_prompt_zeichen` / `p5_im_prompt` / `p5_fehlend` - Abdeckung im P5-Ausschnitt,
  also in `text[:45000]` (`P5_LIMIT` im Skript),
- `im_ausschnitt` / `fehlend` / `pipe_zeilen_ausschnitt` - Abdeckung im 6.000er-Fenster
  aus `zweistufig_trocken_20261120.py`,
- `p5_gekuerzt` - ob das Dokument die 45.000er Grenze ueberschreitet (0/33),
- Summen: `p5_alle_goldwerte` (19/33), `p5_ohne_vollstaendige_abdeckung` (14/33),
  `p5_und_fenster_verschieden` (11/33), `fair` (420, 421, 119).

Der Lauf gibt dieselbe Tabelle zweiseitig aus (P5 und Fenster nebeneinander), damit
die Zahlen aus dem Bericht ohne Zwischenschritt pruefbar sind.

## Grenzen

- Der P5-Ausschnitt ist aus dem Code und den Dokumentlaengen hergeleitet, nicht
  aus gespeicherten Prompts: Die Predictions-Zeilen des P5-Laufs enthalten weder
  Prompt-Hash noch Prompt-Laenge (Felder geprueft: `prompt_version`,
  `completion_tokens`, `content_chars`, `target_timepoint` u. a., kein
  `prompt_sha256`). Die Herleitung ist eindeutig, weil kein Dokument die Grenze
  45.000 erreicht und `main()` kein Textlimit setzt.
- Abdeckung per Zahlenvergleich: Eine Zahl, die anderswo im Text steht, zaehlt
  mit. Die Aussage „steht im Ausschnitt“ ist damit eine Obergrenze.
