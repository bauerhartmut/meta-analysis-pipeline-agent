#!/usr/bin/env python
"""Cell-Level-Retrieval: ein Suchauftrag je fehlender Zelle.

Fuer eine Zelle (Feld, Arm, Outcome, Zeitpunkt) werden aus dem Studienauszug
lexikalisch die besten Textstellen und Tabellenzeilen ausgewaehlt und dem Modell
zusammen mit dem Extraktionsauftrag vorgelegt. Das Modell muss den Wert **und**
die Fundstelle nennen; die Fundstelle wird anschliessend gegen das Dokument
geprueft (Zitat muss woertlich enthalten sein). Damit ist jede Antwort
ueberpruefbar oder sie faellt weg.

Aufruf (Erzeugung der Antworten):
    python zell_retrieval.py --zellen stichprobe.json --modelle glm qwen30 \
        --out antworten.jsonl --workers 2

`stichprobe.json` ist eine Liste von `{record_id, feld, arm}`.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import gemeinsam as g

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
sys.path.insert(0, str(BENCH))
import run_extended_extraction as harness  # noqa: E402  (nur Aufruf-Helfer)

STOPP = set(
    """the of and for with versus vs in on at to from by a an is are was were be been
    this that these those we our their its as or not no than then compared comparison
    group groups patients patient study trial results result outcome outcomes""".split()
)

SYSTEM_RETRIEVAL = (
    "You extract one numerical value from a randomised controlled trial publication. "
    "You answer with a single JSON object and nothing else. "
    "You never invent values: if the value is not printed, you answer null."
)

MAX_SNIPPETS = 9
MAX_ZEICHEN = 7000


def _begriffe(text: str) -> list[str]:
    woerter = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", (text or "").lower())
    return [w for w in woerter if w not in STOPP]


def einheiten(doc: str) -> list[dict]:
    """Zerlegt das Dokument in bewertbare Einheiten (Absaetze, Tabellenzeilen)."""
    ergebnis: list[dict] = []
    for block in g.bloecke(doc):
        roh = doc[block["start"] : block["ende"]]
        if block["typ"] == "tabelle":
            caption = ""
            treffer = re.search(r"(?s):::\s*caption\s*(.*?)\s*:::", roh)
            if treffer:
                caption = re.sub(r"\s+", " ", treffer.group(1)).strip()
            for zeile in roh.split("\n"):
                zeile = zeile.strip()
                if len(zeile) < 8 or set(zeile) <= set("-: "):
                    continue
                ergebnis.append(
                    {
                        "typ": "tabellenzeile",
                        "text": (caption + " | " + zeile) if caption else zeile,
                        "roh": zeile,
                        "caption": caption,
                    }
                )
        else:
            for absatz in re.split(r"\n\s*\n", roh):
                absatz = re.sub(r"\s+", " ", absatz).strip()
                if len(absatz) >= 40:
                    ergebnis.append({"typ": block["typ"], "text": absatz, "roh": absatz, "caption": ""})
    return ergebnis


def bewerte(einheit: dict, begriffe: list[str]) -> float:
    text = einheit["text"].lower()
    treffer = sum(text.count(b) for b in begriffe)
    if not treffer:
        return 0.0
    # Laengennormierung verhindert, dass lange Absaetze alles gewinnen.
    return treffer / math.sqrt(len(text) + 1)


def waehle_ausschnitte(record: dict, feld: str, doc: str, max_n: int = MAX_SNIPPETS) -> list[dict]:
    """Waehlt die besten Textstellen fuer eine Zelle aus."""
    arm = "intervention" if feld.startswith("intervention") else "comparator"
    teile = [record["context"].get("outcome") or ""]
    teile += g.arm_begriffe(record, arm) + g.arm_begriffe(record, "comparator" if arm == "intervention" else "intervention")
    kern = feld.split("_", 1)[-1]
    for schluessel, synonyme in g.FELD_BEGRIFFE.items():
        if schluessel in feld:
            teile += list(synonyme)
    begriffe = _begriffe(" ".join(teile))
    einheiten_liste = einheiten(doc)
    bewertet = sorted(einheiten_liste, key=lambda e: -bewerte(e, begriffe))
    auswahl: list[dict] = []
    zeichen = 0
    for einheit in bewertet:
        if bewerte(einheit, begriffe) <= 0:
            break
        if zeichen + len(einheit["text"]) > MAX_ZEICHEN:
            break
        auswahl.append(einheit)
        zeichen += len(einheit["text"])
        if len(auswahl) >= max_n:
            break
    # Tabellenzeilen ohne Stichworttreffer koennen den Wert trotzdem tragen:
    # als Rueckfall die Kopfzeilen der Tabellen mit aufnehmen.
    if not auswahl:
        for einheit in einheiten_liste[:max_n]:
            auswahl.append(einheit)
    return auswahl


def prompt_fuer_zelle(record: dict, feld: str, ausschnitte: list[dict]) -> tuple[str, str]:
    arm = "intervention" if feld.startswith("intervention") else "comparator"
    ziel_arm = (
        record["context"].get("intervention")
        if arm == "intervention"
        else record["context"].get("comparator")
    )
    zeitpunkt = (record.get("timepoint") or {}).get("target") or "not stated"
    bloecke = []
    for nummer, ausschnitt in enumerate(ausschnitte, 1):
        bloecke.append(f"[{nummer}] ({ausschnitt['typ']}) {ausschnitt['text']}")
    auszug = "\n\n".join(bloecke)
    prompt = (
        f"Excerpts from one publication:\n{auszug}\n\n"
        f"Study arms: intervention = {record['context'].get('intervention') or 'not stated'}; "
        f"comparator = {record['context'].get('comparator') or 'not stated'}\n"
        f"Outcome: {record['context'].get('outcome') or 'not stated'} "
        f"({record['context'].get('outcome_type') or 'unknown'})\n"
        f"Target time point: {zeitpunkt}\n\n"
        f"Extract exactly one value: field \"{feld}\" for the {arm} arm "
        f"({ziel_arm or 'not stated'}).\n"
        'Return exactly one JSON object: {"value": <number or null>, '
        '"quote": "<the sentence or table row you read the value from, copied verbatim>", '
        '"snippet": <number of the excerpt the quote is in>, '
        '"row_label": "<verbatim row label>", "column_label": "<verbatim column header>", '
        '"note": "<short reason if null>"}\n'
        "Rules: the value must be printed in the quote; copy it exactly as printed, do not convert, "
        "do not compute, do not round. The arm must be the one named in the request; if the excerpt "
        "shows the value only for the other arm, answer null. If the value is not reported for this "
        "arm and time point, answer null. No commentary, no code fences."
    )
    return prompt, SYSTEM_RETRIEVAL


def normalisiere(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def pruefe_zitat(zitat: str, doc: str, wert) -> bool:
    """Zitat muss woertlich im Dokument stehen und den Wert enthalten."""
    zitat_norm = normalisiere(zitat)
    if len(zitat_norm) < 8:
        return False
    if zitat_norm not in normalisiere(doc):
        return False
    if wert is None:
        return True
    return bool(g.finde_zahl(zitat, str(wert))) or bool(g.finde_zahl(zitat, f"{wert}"))


def frage_zelle(
    record: dict,
    feld: str,
    modell: dict,
    key: str,
    base: str,
) -> dict:
    doc = g.dokument(record)
    ausschnitte = waehle_ausschnitte(record, feld, doc)
    prompt, system = prompt_fuer_zelle(record, feld, ausschnitte)
    # Systemtext des Harness ersetzen: der Retrieval-Auftrag ist enger.
    original = harness.SYSTEM
    try:
        harness.SYSTEM = system
        antwort = harness._call_once(modell, prompt, key, base)
        # Das Gateway beantwortet Lastspitzen mit 401 "Not authenticated"
        # statt mit 429. Nach einer Pause geht derselbe Aufruf wieder durch;
        # deshalb wird hier mit Wartezeit wiederholt.
        versuch = 1
        while antwort.get("http_status") in (401, 429) and versuch < 6:
            time.sleep(12 * versuch)
            antwort = harness._call_once(modell, prompt, key, base)
            versuch += 1
    finally:
        harness.SYSTEM = original
    roh = antwort.get("content") or ""
    payload, fehler = harness._load_payload(roh) if roh else (None, "leer")
    wert = None
    zitat = ""
    row_label = column_label = ""
    if isinstance(payload, dict):
        wert = g.als_zahl(str(payload.get("value"))) if payload.get("value") is not None else None
        zitat = str(payload.get("quote") or "").strip()
        row_label = str(payload.get("row_label") or "").strip()
        column_label = str(payload.get("column_label") or "").strip()
    verifiziert = bool(wert is not None and zitat and pruefe_zitat(zitat, doc, wert))
    return {
        "record_id": record["record_id"],
        "feld": feld,
        "modell": modell["name"],
        "model_id": modell["id"],
        "wert": wert,
        "wert_roh": payload.get("value") if isinstance(payload, dict) else None,
        "zitat": zitat,
        "row_label": row_label,
        "column_label": column_label,
        "snippet": payload.get("snippet") if isinstance(payload, dict) else None,
        "note": str(payload.get("note") or "")[:300] if isinstance(payload, dict) else "",
        "verifiziert": verifiziert,
        "parse_fehler": fehler,
        "http_status": antwort.get("http_status"),
        "finish_reason": antwort.get("finish_reason", ""),
        "completion_tokens": antwort.get("completion_tokens"),
        "prompt_zeichen": len(prompt),
        "elapsed_s": antwort.get("elapsed_s"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zellen", type=Path, required=True, help="JSON-Liste {record_id, feld}")
    parser.add_argument("--modelle", nargs="+", default=["glm"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--pause", type=float, default=8.0, help="Sekunden zwischen zwei Anfragen")
    args = parser.parse_args()

    from research_agent.config import get_config

    config = get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")

    modelle = []
    for name in args.modelle:
        if name not in harness.MODELS:
            raise SystemExit(f"unbekanntes Modell: {name}")
        eintrag = dict(harness.MODELS[name])
        eintrag["name"] = name
        # Das Retrieval antwortet kurz; ein hohes Budget laedt zu Reasoning ein.
        eintrag["max_tokens"] = min(int(eintrag.get("max_tokens") or 4000), 4000)
        modelle.append(eintrag)

    records = g.lade_records()
    zellen = json.loads(args.zellen.read_text(encoding="utf-8"))
    auftraege = [(records[z["record_id"]], z["feld"], modell) for z in zellen for modell in modelle]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sperre = threading.Lock()
    fertig = 0
    with args.out.open("w", encoding="utf-8", newline="\n") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(frage_zelle, record, feld, modell, key, base): (record, feld, modell)
                for record, feld, modell in auftraege
            }
            for future in as_completed(futures):
                record, feld, modell = futures[future]
                try:
                    zeile = future.result()
                except Exception as error:  # noqa: BLE001
                    zeile = {
                        "record_id": record["record_id"],
                        "feld": feld,
                        "modell": modell["name"],
                        "wert": None,
                        "verifiziert": False,
                        "parse_fehler": f"ausnahme: {error}",
                    }
                with sperre:
                    handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")
                    handle.flush()
                    fertig += 1
                    time.sleep(args.pause)
                    print(
                        f"{fertig}/{len(auftraege)} {zeile['modell']} {zeile['record_id']} {feld} "
                        f"-> {zeile.get('wert')} {'ok' if zeile.get('verifiziert') else 'unbelegt'}",
                        flush=True,
                    )
    print(f"fertig: {len(auftraege)} Anfragen, Ausgabe {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
