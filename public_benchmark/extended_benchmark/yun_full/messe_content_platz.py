#!/usr/bin/env python
"""Misst, wie viel Platz die mitgeschriebene Rohantwort je Record kostet.

Grundlage ist eine Lesekopie eines Laufs. Die Rohantwort wird nachgebaut (JSON
mit Zeitpunkt, Header und Zellen) und auf die gespeicherte Laenge
`content_chars` gebracht; damit hat sie die realistische Zitierdichte. Danach
wird die Zeile mit und ohne `content` serialisiert und die Differenz gemessen —
also inklusive Feldname, Anfuehrungszeichen und Escaping.

Aufruf:
    python messe_content_platz.py --run _lesekopie_20261118 \
        --out ../iterativ/ergebnisse/qwen30_vs_glm_20261118/content_platz.md
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "runs"


def lies(pfad: Path) -> list[str]:
    return [z for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def antwort_text(row: dict, laenge: int) -> str:
    """Antwort in der Form, die das Modell liefert, auf die gespeicherte Laenge gebracht."""
    roh = json.dumps(
        {
            "timepoint": row.get("target_timepoint") or "",
            "timepoint_header": row.get("timepoint_header") or "",
            "fallback": row.get("fallback"),
            "cells": row.get("rows") or [],
        },
        ensure_ascii=False,
    )
    if len(roh) >= laenge:
        return roh[:laenge]
    return roh + " " * (laenge - len(roh))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    zeilen = lies(RUNS / args.run / "predictions.jsonl")
    je_modell: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"zeichen": [], "delta": [], "zeile": []})
    gesamt_zeilen = gesamt_delta = 0

    for zeile in zeilen:
        row = json.loads(zeile)
        laenge = row.get("content_chars") or 0
        text = antwort_text(row, laenge)
        klein = json.dumps(row, ensure_ascii=False)
        gross = json.dumps({**row, "content": text}, ensure_ascii=False)
        delta = len(gross.encode("utf-8")) - len(klein.encode("utf-8"))
        k = je_modell[row["model"]]
        k["zeichen"].append(laenge)
        k["delta"].append(delta)
        k["zeile"].append(len(zeile.encode("utf-8")))
        gesamt_zeilen += 1
        gesamt_delta += delta

    zeilen_md = [
        "# Platzbedarf der mitgeschriebenen Rohantwort\n",
        "Gemessen auf einer Lesekopie: Die Antwort wird nachgebaut, auf die "
        "gespeicherte Laenge `content_chars` gebracht und die Zeile mit und ohne "
        "`content` serialisiert. Die Differenz enthaelt Feldname, "
        "Anfuehrungszeichen und Escaping.\n",
        "| Modell | Records | Zeichen Median | Zeichen Mittel | Zeichen p90 | Zeichen max "
        "| Zeile ohne (Median) | Aufschlag (Median) | Aufschlag gesamt |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for modell in sorted(je_modell):
        k = je_modell[modell]
        z = sorted(k["zeichen"])
        d = sorted(k["delta"])
        p90 = z[int(0.9 * (len(z) - 1))] if z else 0
        zeilen_md.append(
            f"| {modell} | {len(z)} | {statistics.median(z):.0f} | {statistics.mean(z):.0f} | {p90} "
            f"| {z[-1] if z else 0} | {statistics.median(k['zeile']):.0f} "
            f"| {statistics.median(d):.0f} | {sum(d) / 1024:.0f} KiB |"
        )
    zeilen_md.append("")
    zeilen_md.append(
        f"**Summe:** {gesamt_zeilen} Zeilen, Aufschlag {gesamt_delta / 1024:.0f} KiB "
        f"({gesamt_delta / gesamt_zeilen:.0f} Byte je Zeile). Ein voller Lauf mit 699 Records "
        f"je Modell (2.094 Zeilen) kostet danach rund {gesamt_delta / gesamt_zeilen * 2094 / 1024 / 1024:.1f} MiB "
        "zusaetzlich; die aktuelle Datei mit 1.582 Zeilen liegt bei "
        f"{sum(sum(v['zeile']) for v in je_modell.values()) / 1024 / 1024:.1f} MiB.\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(zeilen_md), encoding="utf-8")
    print("\n".join(zeilen_md))
    print(f"geschrieben: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
