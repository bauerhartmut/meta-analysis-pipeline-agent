#!/usr/bin/env python3
"""Rendert genau die Anfrage, die der Harness im P5-Lauf an das Modell sendet.

Der P5-Lauf ``yun699_p5_24000_20261118`` ist mit ``run_extended_extraction.py``
gelaufen, ohne Zeitpunkt-, Reparatur- oder Gruppengroessen-Flags. Die Anfrage
besteht damit aus zwei Nachrichten:

* ``role=system``: ``run_extended_extraction.SYSTEM`` (SESSION_TAG ist leer),
* ``role=user``: ``build_prompt(record, text)`` mit der Standardgrenze 45000.

Beides wird hier aus dem Produktivcode gerendert, nicht abgetippt. Es gibt
keinen Modellaufruf und keine Aenderung an Gold oder Predictions.

Erzeugt in ``claude_test_20261121/``:

  SYSTEM.txt                     Systemprompt, einmal fuer alle Records
  prompts/<record>_prompt.md     Nutzernachricht, 1:1 wie gesendet
  INDEX.md                       Kennzahlen je Record
  README.md                      Zweck, Herkunft, Testanleitung, Grenzen

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/schwere_records_20261121/baue_claude_prompts_20261121.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
PAKET = HIER.parents[2]  # public_benchmark
BENCH = PAKET / "extended_benchmark"
REPO = PAKET.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(PAKET))

from extended_benchmark import run_extended_extraction as rx  # noqa: E402

GOLD = BENCH / "yun_full" / "records" / "yun699.jsonl"
RUN = BENCH / "runs" / "yun699_p5_24000_20261118"
AUSWAHL = HIER / "auswahl_20261121.json"
ZIEL = HIER / "claude_test_20261121"
PROMPTS = ZIEL / "prompts"

README = """# Claude-Test: genau die Anfrage des Harness (21.11.2026)

Dieser Ordner enthaelt fuer 41 schwere Records **denselben Text, den der
Harness im P5-Lauf an das Modell geschickt hat** — nicht die Aufgabenfassung
aus `../aufgaben/`. Ziel ist, ein anderes Modell (z. B. Claude) auf genau der
Anfrage zu testen, an der GLM im P5-Lauf gescheitert ist.

## Was hier drin steht

```
SYSTEM.txt                    Systemprompt (eine Nachricht, fuer alle Records gleich)
prompts/<record>_prompt.md    Nutzernachricht, 1:1 der Text aus build_prompt
INDEX.md                      Kennzahlen je Record (Zeichen, Kuerzung, Goldzellen, P5-Status)
```

Kein Gold, keine Loesung, kein Hinweis auf die erwarteten Werte. Wer den Ordner
weitergibt, gibt nur die Anfrage weiter. Die Loesungen liegen getrennt in
`../loesungen/`.

## Herkunft (nachrechenbar)

* Record: `public_benchmark/extended_benchmark/yun_full/records/yun699.jsonl`
* Dokumenttext: `record["document"]["path"]`, relativ zur Projektwurzel,
  gelesen mit `errors="replace"`
* Anfrage: `run_extended_extraction.build_prompt(record, text)` mit den
  Standardwerten des P5-Laufs (Grenze 45000 Zeichen, kein Zeitpunktflag,
  keine Quellenzeile, `group_size_mode="aus"`)
* Systemprompt: `run_extended_extraction.SYSTEM`, `SESSION_TAG` leer
* Antwortbudget im Lauf: 24000 Tokens, `temperature=0.0`

Der P5-Lauf traegt in allen 41 Zeilen `prompt_version = v2_timepoint` und
`schema_version = v6_percell_timepoint`; das Skript bricht ab, wenn das nicht
mehr stimmt. Damit ist belegt, dass die hier gerenderte Fassung die Fassung des
Laufs ist.

## So testest du ein Modell

1. `SYSTEM.txt` als Systemprompt setzen (Claude-Projekte: Projektanweisung;
   API: `role=system`).
2. Genau eine Datei aus `prompts/` als Nutzernachricht senden. Eine Datei = ein
   Record = ein Aufruf. Nichts ergaenzen, nichts wegkuerzen.
3. `temperature=0`, Budget mindestens 24000 Ausgabetokens — im Lauf hat GLM das
   Budget im Reasoning aufgebraucht, deshalb dieser Wert.
4. Die Antwort als `antworten/<record>_antwort.json` speichern (roher Text,
   Codefences sind erlaubt) und mit `bewerte_claude_20261121.py` auswerten.

## Bewertung

`bewerte_claude_20261121.py` vergleicht gegen `../loesungen/*_loesung.json`:
Treffer ist `(field, arm)` gleich und `|Wert - Gold| < 1e-6`. Daraus TP, FP, FN,
Precision, Recall, F1 je Record und als Summe. `timepoint` und `quote` werden
nicht bewertet.

Wichtig: 16 der 33 Records ohne Antwort haben nach
`../analysis/glm53_p5_vergleich_20261120/leere_p5_muster_20261120.md` **keinen
Goldwert im Dokumenttext**. Dort ist die richtige Antwort eine leere
Zellenliste. Wer diese 16 mitzaehlt, ohne sie zu trennen, misst die
Dokumentaufbereitung, nicht die Extraktion. `INDEX.md` markiert sie in der
Spalte `Gold im Text`.

## Grenzen

* Ein Aufruf pro Record, kein Fenster-Schieben, keine zweite Stufe: das ist der
  P5-Aufbau, nicht die Kettenpipeline.
* Der Prompt schneidet bei 45000 Zeichen ab; die Aufgaben in `../aufgaben/`
  enthalten den Volltext. Beide Tests messen deshalb nicht dasselbe.
* Ohne Gold-Zeitpunkt im Record ist `timepoint` in der Antwort nicht bewertbar.
* Dieses Paket ersetzt keinen Netzlauf im Harness: es ist ein Fremdmodell-Test
  auf derselben Anfrage.
"""


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def dateiname(record_id: str) -> str:
    return record_id.replace(":", "_").replace("/", "_")


def main() -> int:
    auswahl = json.loads(AUSWAHL.read_text(encoding="utf-8"))["records"]
    ids = [a["record_id"] for a in auswahl]
    records = {r["record_id"]: r for r in lies_jsonl(GOLD)}
    predictions = {z["record_id"]: z for z in lies_jsonl(RUN / "predictions.jsonl") if z["record_id"] in ids}

    fehlt = [rid for rid in ids if rid not in predictions]
    if fehlt:
        raise SystemExit(f"keine P5-Zeile fuer {fehlt}")
    abweichend = [
        rid
        for rid, z in predictions.items()
        if z.get("prompt_version") != "v2_timepoint"
        or z.get("schema_version") != "v6_percell_timepoint"
        or z.get("group_size_mode") != "aus"
    ]
    if abweichend:
        raise SystemExit(f"andere Promptfassung im Lauf: {abweichend}")
    if rx.SESSION_TAG:
        raise SystemExit("SESSION_TAG ist gesetzt; die gerenderte Anfrage waere nicht die des Laufs")

    PROMPTS.mkdir(parents=True, exist_ok=True)
    for alt in PROMPTS.glob("*"):
        if alt.is_file():
            alt.unlink()

    (ZIEL / "SYSTEM.txt").write_text(rx.SYSTEM + "\n", encoding="utf-8", newline="\n")

    zeilen = []
    pruefung = {"stand": "2026-11-21", "grenze": 45000, "system_zeichen": len(rx.SYSTEM), "records": []}
    for rid in ids:
        record = records[rid]
        text = (REPO / record["document"]["path"]).read_text(encoding="utf-8", errors="replace")
        prompt = rx.build_prompt(record, text)
        ziel = PROMPTS / f"{dateiname(rid)}_prompt.md"
        ziel.write_text(prompt, encoding="utf-8", newline="\n")

        # Gegenprobe: Datei == gerenderter Prompt, Nutzlast == text[:45000]
        wieder = ziel.read_text(encoding="utf-8")
        if wieder != prompt:
            raise SystemExit(f"{rid}: Datei weicht vom gerenderten Prompt ab")
        if prompt.count(text[:45000]) != 1:
            raise SystemExit(f"{rid}: Textausschnitt steht nicht genau einmal im Prompt")

        z = predictions[rid]
        gekuerzt = len(text) > 45000
        gold = len(record["gold"]["cells"])
        zeilen.append(
            f"| `{rid}` | {record['document'].get('id')} | {len(prompt):,} | {len(text):,} | "
            f"{'ja' if gekuerzt else 'nein'} | {gold} | {z.get('content_chars') or 0} | "
            f"{z.get('fehlerklasse') or 'ok'} |".replace(",", ".")
        )
        pruefung["records"].append(
            {
                "record_id": rid,
                "pmcid": record["document"].get("id"),
                "prompt_datei": ziel.relative_to(ZIEL).as_posix(),
                "prompt_zeichen": len(prompt),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "dokument_zeichen": len(text),
                "text_im_prompt_zeichen": len(text[:45000]),
                "gekuerzt": gekuerzt,
                "goldzellen": gold,
                "p5_content_chars": z.get("content_chars") or 0,
                "p5_fehlerklasse": z.get("fehlerklasse") or "",
            }
        )

    (ZIEL / "pruefung_20261121.json").write_text(
        json.dumps(pruefung, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    index = (
        "# Anfragen je Record (Stand 21.11.2026)\n\n"
        f"{len(ids)} Records, Systemprompt {len(rx.SYSTEM)} Zeichen (`SYSTEM.txt`). "
        "Die Nutzernachricht steht 1:1 in `prompts/`, ohne Zusatz.\n\n"
        "| Record | PMC | Prompt-Zeichen | Dokument-Zeichen | gekuerzt | Goldzellen | P5-Antwort-Zeichen | P5-Zustand |\n"
        "|---|---|---:|---:|:---:|---:|---:|---|\n"
        + "\n".join(zeilen)
        + "\n\n`gekuerzt` = Dokument laenger als die Grenze 45000 Zeichen des Harness. "
        "`P5-Antwort-Zeichen` = `content_chars` der P5-Zeile; 0 bedeutet Abbruch ohne Antwort "
        "(bei 33 dieser Records der Fall).\n"
    )
    (ZIEL / "INDEX.md").write_text(index, encoding="utf-8", newline="\n")
    (ZIEL / "README.md").write_text(README, encoding="utf-8", newline="\n")

    print(f"Records: {len(ids)}")
    print(f"Systemprompt: {len(rx.SYSTEM)} Zeichen")
    print(f"Gekuerzt (Dokument > 45000): {sum(1 for r in pruefung['records'] if r['gekuerzt'])}")
    print(f"Prompt-Zeichen min/max: {min(r['prompt_zeichen'] for r in pruefung['records'])}/"
          f"{max(r['prompt_zeichen'] for r in pruefung['records'])}")
    print(f"Ziel: {ZIEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
