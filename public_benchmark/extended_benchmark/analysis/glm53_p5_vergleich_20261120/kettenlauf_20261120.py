#!/usr/bin/env python
"""Kette (Fenster, Zeilenbindung, Stufe 2) auf den fuenf Stichprobenrecords.

Je Record:

1. Stufe 1 wie `zweistufig_tabelle_prosa_20261120.py --zeilenbindung`:
   Prosa-Stueck plus Tabellenfenster, bindender Regelblock, Budget 16.000.
2. Stufe 2 auf dem Zeilen-Locator, Budget 8.000. Fuer Tabellen ohne
   Wochenbeschriftung (Einzelblock-Modus) liest sie die Zeile im Ausschnitt aus
   Kopf und Zeile; die Zuordnung der Arme kommt aus den Spaltenkoepfen, die
   Stufe 1 genannt hat.

Offline (`--dry-run`) wird je Record zusaetzlich geprueft, welche Score-Zeile
im Tabellenstueck die Goldwerte traegt und wie viele Wertepaare dort stehen.
Kein Modellaufruf im Dry-Run.

Abbruchkriterium wie zuvor: `content_chars == 0` oder `finish_reason ==
"length"`; Transportfehler als `status = fehler`. Bewertung gegen Gold mit der
Logik aus `vergleiche_20261120.py`.

Aufruf:
    .venv/bin/python .../kettenlauf_20261120.py --dry-run
    .venv/bin/python .../kettenlauf_20261120.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent.parent
ROOT = HIER.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HIER))

import run_extended_extraction as rx  # noqa: E402
import vergleiche_20261120 as v  # noqa: E402
from aufruf_20261120 import lesezeit  # noqa: E402
from falschwert_20261120 import zahlen_im_text  # noqa: E402
from fensterlage_20261120 import werte_index  # noqa: E402
from zweistufig_tabelle_prosa_20261120 import (  # noqa: E402
    SCORE_ZEILE,
    STAGE1_SYSTEM,
    baue_prompt,
    bindung_pruefen,
    normalisiere,
    waehle_stuecke,
)

RECORDS = ("yun2024:420", "yun2024:421", "yun2024:582",
           "yun2024:671", "yun2024:672")
BUDGET1 = 16000
BUDGET2 = 8000
MODELL = "qwen"
LAUF = HIER / "zweistufig_lauf_20261120"
AUSGABE = LAUF / "predictions_kette_stichprobe_20261120.jsonl"
PAAR = re.compile(r"(-?\d+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*\)")
KOPF_N = re.compile(r"\(\s*\*?n\*?\s*=\s*\d+\s*\)|\b[Nn]\s*=\s*\d+")
KONTEXT2 = 700

#: Zusatz zum bindenden Regelblock: Kopfzahlen als eigene Fundstelle.
BINDUNG_KOPF = (
    "If the outcome value is a group size and it is printed in a table header "
    'cell such as "(n = 16)" or "N = 14", return the header cell as the '
    "location: leave zeilenlabel empty, put the header text into spaltenkopf and "
    'set "fundstelle": "kopf".\n'
    'Set "fundstelle" to "zeile" for a table row and to "satz" for a sentence.\n'
)

STAGE2_SYSTEM = (
    "You read numbers from a randomised controlled trial publication at a table "
    "row named by a previous step. You answer with a single JSON object and "
    "nothing else. You never compute, convert, round or estimate values."
)


def zahl_text(wert: float) -> str:
    return str(int(wert)) if float(wert).is_integer() else str(wert)


def worte_von(record: dict[str, Any]) -> list[str]:
    context = record.get("context") or {}
    worte = [w for w in re.split(r"[\s/,()-]+", str(context.get("outcome") or ""))
             if len(w) >= 4]
    return worte or [str(context.get("outcome") or "")]


def zeilen_fenster(text: str, pos: int, breite: int = 320) -> str:
    """Zeile ab `pos` bis zur naechsten Zeilenbeschriftung oder `breite`."""
    fenster = text[pos:pos + breite]
    naechste = SCORE_ZEILE.search(fenster, 1)
    if naechste:
        fenster = fenster[:naechste.start()]
    return fenster.strip()


def score_zeilen_im_stueck(text: str, stuecke: list[tuple[int, int, str]],
                           gold_werte: list[float]) -> list[dict[str, Any]]:
    """Alle Score-Zeilen des Tabellenstuecks mit Paarzahl und Goldtreffern."""
    befunde = []
    for a, b, art in stuecke:
        for m in SCORE_ZEILE.finditer(text[a:b]):
            pos = a + m.start()
            fenster = zeilen_fenster(text, pos)
            paare = PAAR.findall(fenster)
            treffer = [w for w in gold_werte
                       if re.search(r"(?<![\d.])" + re.escape(zahl_text(w)) + r"(?![\d])",
                                    fenster)]
            befunde.append({"pos": pos, "art": art, "label": m.group(0),
                            "fenster": fenster, "paare": len(paare),
                            "goldtreffer": sorted(set(treffer))})
    return befunde


def prompt1_mit_kopf(prompt: str) -> str:
    """Setzt den Kopfzahl-Block vor die JSON-Ausgabe der Stufe-1-Regeln."""
    marke = "Return exactly one JSON object:"
    stelle = prompt.rfind(marke)
    if stelle < 0:
        return prompt + "\n" + BINDUNG_KOPF
    return prompt[:stelle] + BINDUNG_KOPF + "\n" + prompt[stelle:]


def erweitere(text: str, stuecke: list[tuple[int, int, str]],
              links: int = 400) -> list[tuple[int, int, str]]:
    """Zieht jedes Stueck nach links, damit Kopfzeilen und Vorsaetze drin sind."""
    erweitert: list[tuple[int, int, str]] = []
    for i, (a, b, art) in enumerate(stuecke):
        grenze = erweitert[-1][1] if erweitert else 0
        start = max(grenze, a - links, 0)
        if i == 0:
            start = max(a - links, 0)
        erweitert.append((start, b, art))
    return erweitert


def baue_ausschnitt2(text: str, start: int, label: str) -> dict[str, Any]:
    row_pos = text.find(label, start)
    if row_pos < 0:
        raise SystemExit(f"Zeilenlabel {label!r} nicht ab {start} gefunden")
    von = max(0, row_pos - 900)
    fenster = zeilen_fenster(text, row_pos, breite=400)
    kopf = "\n".join(z.strip() for z in text[von:row_pos].splitlines() if z.strip())
    ausschnitt = "\n\n".join(t for t in (kopf, fenster) if t)
    return {"ausschnitt_text": ausschnitt, "zeile": fenster, "row_pos": row_pos}


def baue_prompt2(aus: dict[str, Any], fall: dict[str, Any], context: dict[str, Any],
                 int_loc: dict[str, Any], cmp_loc: dict[str, Any]) -> str:
    ziel = str(int_loc.get("timepoint") or fall.get("timepoint_target") or "")
    caption = str(int_loc.get("caption") or "")
    return (
        "Publication excerpt (flattened table rows):\n"
        f"{aus['ausschnitt_text']}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        "Outcome type: continuous\n"
        f'Target time point (binding): "{ziel}".\n\n'
        "A previous step located the outcome in row "
        f"\"{int_loc.get('zeilenlabel')}\" with column header "
        f"\"{int_loc.get('spaltenkopf')}\" (intervention arm) and "
        f"\"{cmp_loc.get('spaltenkopf')}\" (comparator arm)"
        + (f", caption \"{caption}\"" if caption else "")
        + ".\n\n"
        "Read only that row, in the column of each arm: the mean, the standard "
        "deviation and, if the row or its header prints it, the group size. "
        "If the row prints one value pair per arm, that pair is the target time "
        "point; if it prints several pairs per arm, the pairs follow the time "
        "points printed in the header, and the target time point is the one "
        "named above. Never read a change row or another row.\n\n"
        "Copy the numbers exactly as printed; do not convert, compute, round or "
        "substitute values. If a value is not printed, omit its cell.\n\n"
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "intervention_mean" | "intervention_standard_deviation" '
        '| "intervention_group_size" | "comparator_mean" | '
        '"comparator_standard_deviation" | "comparator_group_size", '
        '"arm": "intervention" | "comparator", "value": <number>}, ...], '
        '"quote": "<the printed row you read>", '
        '"block": "<time point you read, empty if not printed>"}\n'
        "No commentary, markdown or code fences."
    )


def kopf_ausschnitt(text: str, start: int, spaltenkopf: str) -> dict[str, Any]:
    """Kopfzeilen der Tabelle, in denen die Gruppengroesse gedruckt steht."""
    pos = text.find(spaltenkopf, start) if spaltenkopf else -1
    if pos < 0:
        treffer = KOPF_N.search(text, start)
        pos = treffer.start() if treffer else -1
    if pos < 0:
        raise SystemExit("keine Kopfzelle mit n = im Ausschnitt")
    zeilen_start = text.rfind("\n", max(0, pos - 400), pos) + 1
    block = text[zeilen_start:pos + 260]
    kopf = "\n".join(z.rstrip() for z in block.splitlines()[:4] if z.strip())
    return {"ausschnitt_text": kopf, "zeile": kopf, "row_pos": pos, "art": "kopf"}


def baue_prompt2_kopf(aus: dict[str, Any], fall: dict[str, Any],
                      context: dict[str, Any], int_loc: dict[str, Any],
                      cmp_loc: dict[str, Any]) -> str:
    ziel = str(int_loc.get("timepoint") or fall.get("timepoint_target") or "")
    caption = str(int_loc.get("caption") or "")
    return (
        "Publication excerpt (table header rows):\n"
        f"{aus['ausschnitt_text']}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        "Outcome type: continuous\n"
        f'Target time point (binding): "{ziel}".\n\n'
        "A previous step located the group size in the header cell "
        f"\"{int_loc.get('spaltenkopf')}\" (intervention arm) and "
        f"\"{cmp_loc.get('spaltenkopf')}\" (comparator arm)"
        + (f", caption \"{caption}\"" if caption else "")
        + ".\n\n"
        "Read from that header only the group size of each arm, as printed in the "
        "header cell of the arm (for example \"(n = 16)\"). The header lists the "
        "arms in the order of their column labels; the Intervention and Comparator "
        "lines name the arms. Do not read means, standard deviations or values of "
        "another row, and do not compute or sum anything. If a group size is not "
        "printed, omit its cell.\n\n"
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "intervention_group_size" | '
        '"comparator_group_size", "arm": "intervention" | "comparator", '
        '"value": <number>}, ...], "quote": "<the printed header you read>"}\n'
        "No commentary, markdown or code fences."
    )


def baue_prompt2_satz(text: str, satz: str, fall: dict[str, Any],
                      context: dict[str, Any], int_loc: dict[str, Any]) -> str:
    pos = text.find(satz)
    umgebung = (text[max(0, pos - KONTEXT2):pos + len(satz)].strip()
               if pos >= 0 else satz)
    ziel = str(int_loc.get("timepoint") or fall.get("timepoint_target") or "")
    return (
        "Publication excerpt:\n"
        f"{umgebung}\n\n"
        f"Intervention: {context.get('intervention') or 'not stated'}\n"
        f"Comparator: {context.get('comparator') or 'not stated'}\n"
        f"Outcome: {context.get('outcome') or 'not stated'}\n"
        "Outcome type: continuous\n"
        f'Target time point (binding): "{ziel}".\n\n'
        "A previous step located this sentence, copied verbatim:\n"
        f'"{satz}"\n\n'
        "Read for each arm the mean and the standard deviation printed in that "
        "sentence, and the group size if the sentence prints it. If the sentence "
        "prints more than one value pair per arm, bind the pair to the entity named "
        "in the Outcome above: the pairs are listed in the order in which the "
        "entities are named in the text before or in the sentence. Read the pair of "
        "the entity named in the Outcome, not the first pair, and say in \"block\" "
        "which entity you read. If the Outcome does not name the entity that "
        "distinguishes the pairs, set \"cells\": [] instead of choosing a pair. "
        "Do not read change values, differences or values of another outcome.\n\n"
        "Copy the numbers exactly as printed; do not convert, compute or round. "
        "If a value is not printed, omit its cell.\n\n"
        "Return exactly one JSON object:\n"
        '{"cells": [{"field": "intervention_mean" | "intervention_standard_deviation" '
        '| "intervention_group_size" | "comparator_mean" | '
        '"comparator_standard_deviation" | "comparator_group_size", '
        '"arm": "intervention" | "comparator", "value": <number>}, ...], '
        '"quote": "<the fragment you read>"}\n'
        "No commentary, markdown or code fences."
    )


def rufe(modell: dict[str, Any], prompt: str, key: str, base: str,
          system: str, timeout: float) -> dict[str, Any]:
    original = rx.SYSTEM
    try:
        with lesezeit(timeout):
            rx.SYSTEM = system
            return rx.call(modell, prompt, key, base, attempts=3)
    finally:
        rx.SYSTEM = original


def auswerten(antwort: dict[str, Any], gold: list[dict[str, Any]],
              ausschnitt: str, stufe: int) -> dict[str, Any]:
    inhalt = antwort.get("content") or ""
    finish = antwort.get("finish_reason") or ""
    tokens = antwort.get("completion_tokens")
    if stufe == 1:
        zellen, parse_fehler = [], ""
    else:
        zellen, parse_fehler = rx.parse_cells(inhalt) if inhalt else ([], "leer")
    payload, _ = rx._load_payload(inhalt) if inhalt else (None, "")
    leere = bool(isinstance(payload, dict) and isinstance(payload.get("cells"), list)
                 and not payload.get("cells"))
    if stufe == 2 and leere and not zellen:
        parse_fehler = ""
    abgebrochen = (len(inhalt) == 0) or finish == "length"
    transport = bool(antwort.get("error")) or tokens is None
    status = "fehler" if transport else ("abgebrochen" if abgebrochen else "ok")
    zahlen, _, _ = zahlen_im_text(ausschnitt) if ausschnitt else ({}, {}, {})
    for zelle in zellen:
        wert = v.zahl(zelle.get("value"))
        zelle["im_ausschnitt"] = bool(wert is not None
                                      and zahlen.get(round(float(wert), 6), 0))
    bilanz = v.bilanz_p5(gold, zellen) if zellen or stufe == 2 else {"tp": 0, "fp": 0, "fn": 0}
    quote = v.quote(bilanz["tp"], bilanz["fp"], bilanz["fn"])
    return {"status": status, "transport_fehler": transport, "finish_reason": finish,
            "completion_tokens": tokens, "content_chars": len(inhalt),
            "elapsed_s": antwort.get("elapsed_s"), "parse_fehler": parse_fehler,
            "content": inhalt, "cells": zellen, "bewertung": {**bilanz, **quote},
            "fehler": antwort.get("error") or ""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", nargs="+", default=list(RECORDS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pruefe-kopf", action="store_true",
                        help="Kopf-Modus der Stufe 2 offline bauen, kein Aufruf")
    parser.add_argument("--budget1", type=int, default=BUDGET1)
    parser.add_argument("--budget2", type=int, default=BUDGET2)
    parser.add_argument("--timeout", type=float, default=420.0)
    args = parser.parse_args()

    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    faelle: list[dict[str, Any]] = []
    for rid in args.records:
        record = records[rid]
        context = record.get("context") or {}
        text = (ROOT / (record.get("document") or {}).get("path", "")).read_text(
            encoding="utf-8", errors="replace")
        gold = (record.get("gold") or {}).get("cells") or []
        werte = sorted({round(float(z["value"]), 6) for z in gold if z.get("value") is not None})
        stuecke = erweitere(text, waehle_stuecke(text, worte_von(record)))
        bind = bindung_pruefen(text, stuecke)
        kopfzahlen = [m.group(0) for a, b, _ in stuecke
                      for m in KOPF_N.finditer(text[a:b])]
        index = werte_index(text, werte)
        abgedeckt = {w: [i + 1 for i, (a, b, _) in enumerate(stuecke)
                         if any(a <= p[0] < b for p in index.get(w, []))] for w in werte}
        prompt1 = prompt1_mit_kopf(baue_prompt(
            text, stuecke, context,
            str((record.get("timepoint") or {}).get("target") or ""),
            zeilenbindung=True))
        zeilen = score_zeilen_im_stueck(text, stuecke, werte)
        bester = max(zeilen, key=lambda z: (len(z["goldtreffer"]), z["paare"]), default=None)
        lage = {}
        for w in werte:
            stellen = [p[0] for p in index.get(w, [])]
            arten = [art for a, b, art in stuecke for p in stellen if a <= p < b]
            zeilen_art = []
            for p in stellen:
                start_zeile = text.rfind("\n", 0, p) + 1
                zeilen_art.append("tabelle" if text[start_zeile:p].count("  ") >= 2 else "prosa")
            lage[zahl_text(w)] = {"stuecke": arten[:2], "zeilen": zeilen_art[:2]}
        print(f"   Goldlage: {lage}")
        print(f"   n-Angaben im Ausschnitt: {sorted(set(kopfzahlen))[:6]}")
        if bind["score_zeilen"]:
            for t in bind["score_zeilen"][:1]:
                a, b, _ = stuecke[t["stueck"] - 1]
                vor = text[max(a, t["pos"] - KONTEXT2):t["pos"]]
                named = [w for w in str(context.get("outcome") or "").split()
                         if len(w) >= 6 and w.lower() in vor.lower()]
                print(f"   Entitaetsnamen vor der ersten Score-Zeile: {named}")
        fall = {"rid": rid, "record": record, "context": context, "text": text,
                "gold": gold, "werte": werte, "stuecke": stuecke,
                "prompt1": prompt1, "bind": bind,
                "goldwerte_im_ausschnitt": sum(1 for w in werte if abgedeckt[w]),
                "zeilen": zeilen, "bester": bester}
        faelle.append(fall)
        print(f"{rid}: Stuecke {stuecke}, Gold im Ausschnitt "
              f"{sum(1 for w in werte if abgedeckt[w])}/{len(werte)}, "
              f"Score-Zeilen {len(zeilen)}, Prompt1 {len(prompt1)} Zeichen")
        if bester:
            print(f"   beste Zeile {bester['label']!r} @{bester['pos']}: "
                  f"{bester['paare']} Wertepaare, Gold {bester['goldtreffer']}")
            print(f"   {bester['fenster'][:160]!r}")

    if args.pruefe_kopf:
        for fall in faelle:
            kopf_n = KOPF_N.search(fall["text"], fall["stuecke"][-1][0])
            if not kopf_n:
                print(f"{fall['rid']}: keine Kopfzelle mit n = im Tabellenstueck")
                continue
            aus = kopf_ausschnitt(fall["text"], fall["stuecke"][-1][0], "")
            loc = {"spaltenkopf": kopf_n.group(0), "fundstelle": "kopf",
                   "caption": "", "timepoint": ""}
            prompt = baue_prompt2_kopf(aus, {"timepoint_target": ""},
                                       fall["context"], loc, {"spaltenkopf": ""})
            drin = [w for w in fall["werte"] if zahl_text(w) in aus["ausschnitt_text"]]
            print(f"{fall['rid']}: Kopfzelle {kopf_n.group(0)!r} @{kopf_n.start()}, "
                  f"Ausschnitt {len(aus['ausschnitt_text'])} Zeichen, "
                  f"Prompt {len(prompt)} Zeichen, Goldwerte im Kopf {drin}")
            print("--- Kopfausschnitt ---")
            print(aus["ausschnitt_text"])
        return 0

    if args.dry_run:
        return 0

    config = rx.get_config()
    key = config.tudagpt_api_key
    base = config.tudagpt_api_base.rstrip("/")
    if not key:
        print("FEHLER: kein API-Schluessel in der Konfiguration", flush=True)
        return 2

    modell = dict(rx.MODELLS[args.model]) if hasattr(rx, "MODELLS") else dict(rx.MODELS[MODELL])
    for fall in faelle:
        rid = fall["rid"]
        modell1 = dict(modell)
        modell1["max_tokens"] = args.budget1
        antwort1 = rufe(modell1, fall["prompt1"], key, base, STAGE1_SYSTEM, args.timeout)
        s1 = auswerten(antwort1, fall["gold"], "", 1)
        locators = []
        payload, _ = rx._load_payload(s1["content"]) if s1["content"] else (None, "")
        if isinstance(payload, dict) and isinstance(payload.get("locators"), list):
            for eintrag in payload["locators"]:
                if isinstance(eintrag, dict):
                    locators.append({k: str(eintrag.get(k) or "").strip()
                                     for k in ("arm", "satz", "zeilenlabel", "spaltenkopf",
                                               "caption", "timepoint", "fundstelle")})
        normiert = [normalisiere(fall["text"][a:b]) for a, b, _ in fall["stuecke"]]
        for loc in locators:
            loc["zeilenlabel_im_stueck"] = next(
                (i + 1 for i, teil in enumerate(normiert)
                 if loc["zeilenlabel"] and normalisiere(loc["zeilenlabel"]) in teil), None)
        int_loc = next((l for l in locators if l["arm"] == "intervention"), {})
        print(f"{rid}: Stufe 1 {s1['status']}, {s1['completion_tokens']} Tokens, "
              f"{len(locators)} Locators, Zeile {int_loc.get('zeilenlabel')!r}, "
              f"tp {int_loc.get('timepoint')!r}")

        zeile = {"record_id": rid, "variante": "kette_stichprobe",
                 "model": MODELL, "model_id": modell1.get("id"),
                 "stuecke": fall["stuecke"], "goldwerte": fall["werte"],
                 "goldwerte_im_ausschnitt": fall["goldwerte_im_ausschnitt"],
                 "stufe1": {**s1, "locators": locators, "prompt_zeichen": len(fall["prompt1"]),
                            "prompt_sha256": hashlib.sha256(
                                fall["prompt1"].encode("utf-8")).hexdigest(),
                            "max_tokens": args.budget1},
                 "offline_beste_zeile": {k: fall["bester"][k] for k in
                                         ("label", "pos", "paare", "goldtreffer")}
                 if fall["bester"] else None}

        cmp_loc = next((l for l in locators if l["arm"] == "comparator"), {})
        zeitpunkt_target = str((fall["record"].get("timepoint") or {}).get("target") or "")
        kopf_fall = (int_loc.get("fundstelle") == "kopf"
                     or (not int_loc.get("satz") and not int_loc.get("zeilenlabel")
                         and bool(KOPF_N.search(int_loc.get("spaltenkopf") or ""))))
        if s1["status"] == "ok" and (int_loc.get("satz") or int_loc.get("zeilenlabel")
                                      or kopf_fall):
            if kopf_fall:
                aus2 = kopf_ausschnitt(fall["text"], fall["stuecke"][-1][0],
                                       int_loc.get("spaltenkopf") or "")
                prompt2 = baue_prompt2_kopf(aus2, {"timepoint_target": zeitpunkt_target},
                                            fall["context"], int_loc, cmp_loc)
            elif int_loc.get("satz"):
                aus2 = {"ausschnitt_text": int_loc["satz"], "zeile": int_loc["satz"],
                        "row_pos": fall["text"].find(int_loc["satz"]), "art": "satz"}
                prompt2 = baue_prompt2_satz(fall["text"], int_loc["satz"],
                                            {"timepoint_target": zeitpunkt_target},
                                            fall["context"], int_loc)
            else:
                aus2 = baue_ausschnitt2(fall["text"], fall["stuecke"][-1][0],
                                        int_loc["zeilenlabel"])
                aus2["art"] = "zeile"
                prompt2 = baue_prompt2(aus2, {"timepoint_target": zeitpunkt_target},
                                       fall["context"], int_loc, cmp_loc)
            modell2 = dict(modell)
            modell2["max_tokens"] = args.budget2
            antwort2 = rufe(modell2, prompt2, key, base, STAGE2_SYSTEM, args.timeout)
            s2 = auswerten(antwort2, fall["gold"], aus2["ausschnitt_text"], 2)
            payload2, _ = rx._load_payload(s2["content"]) if s2["content"] else (None, "")
            block = str(payload2.get("block") or "").strip() if isinstance(payload2, dict) else ""
            zeile["stufe2"] = {**s2, "art": aus2.get("art"), "prompt_zeichen": len(prompt2),
                               "prompt_sha256": hashlib.sha256(
                                   prompt2.encode("utf-8")).hexdigest(),
                               "ausschnitt_zeichen": len(aus2["ausschnitt_text"]),
                               "gelesener_block": block, "max_tokens": args.budget2}
            print(f"   Stufe 2 {s2['status']}, {s2['completion_tokens']} Tokens, "
                  f"{len(s2['cells'])} Zellen, Block {block!r}, "
                  f"TP {s2['bewertung']['tp']} FP {s2['bewertung']['fp']} "
                  f"FN {s2['bewertung']['fn']} F1 {s2['bewertung']['f1']}")
        else:
            zeile["stufe2"] = None
            print("   Stufe 2 uebersprungen (keine Zeile aus Stufe 1)")

        with AUSGABE.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    print("geschrieben:", AUSGABE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
