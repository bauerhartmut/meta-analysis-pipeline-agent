#!/usr/bin/env python3
"""Erzeugt eine maschinelle Effektzeilen-Annotation im Goldstandard-Format.

Was dieses Skript NICHT ist: die eingefrorene A-Annotation vom 10.11.2026
(69 Zeilen, SHA-256 ``d9bb867c303dc19d...``). Die ist geloescht und aus einer
Modelllesung nicht reproduzierbar. Dieses Skript erzeugt eine neue, klar als
maschinell gekennzeichnete Datei.

Vorgehen je Dokument:

1. Volltext aus ``data/fulltext/<id>.txt`` lesen (derselbe Text, gegen den
   ``quote_start``/``quote_end`` gelten).
2. Ein Lesepass mit ``EffectExtractor._one_pass`` (dieselbe Prompt- und
   Plausibilitaetslogik wie in der Pipeline, ``meta-extraction/4``).
   Ein Pass, nicht zwei: die Goldstandard-Einheit ist eine Zeile je
   Kombination, kein Doppelbefund.
3. Zitat gegen den Volltext pruefen (``locate_quote``). Nicht belegte Zeilen
   werden verworfen und gezaehlt, nie mit Position 0 eingetragen.
4. In das Schema ``docs/internal/goldstandard_schema.json`` abbilden.

Mechanisch abgeleitete Felder (dokumentiert, weil es keine Annotation ist):

* ``certainty``: ``high`` wenn Zitat belegt und ein KI berichtet ist;
  ``medium`` wenn nur ein SE berichtet ist. Zeilen ohne KI **und** ohne SE
  werden verworfen (Abschnitt 2 verlangt einen Effekt mit Unsicherheit).
* ``is_primary``: ``false`` nur wenn ``aggregate_design`` das Design als
  Uebersichtsarbeit erkennt (dieselbe Regel wie im Pooling).
* ``outcome_normalized``: ``outcome_key`` der Pipeline.

Aufruf::

    .venv/bin/python scripts/erzeuge_modell_annotation.py --limit 1
    .venv/bin/python scripts/erzeuge_modell_annotation.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research_agent.llm.engine import LLMEngine  # noqa: E402
from research_agent.meta.designs import aggregate_design  # noqa: E402
from research_agent.meta.extraction import EXTRACTOR_VERSION, EffectExtractor  # noqa: E402
from research_agent.research.fulltext import (  # noqa: E402
    locate_quote, section_for_offset, split_sections,
)

DOCS = ROOT / "data" / "golden_effects" / "documents.json"
FULLTEXT = ROOT / "data" / "fulltext"
STANDARD_OUT = ROOT / "data" / "golden_effects" / "goldstandard_modell_20261117.json"
STANDARD_MD = ROOT / "docs" / "internal" / "modell_annotation_20261117.md"

# Ein Thema fuer den ganzen Korpus. Der Korpus ist bewusst gemischt; ein
# themenspezifischer Prompt wuerde die Ausbeute je Dokument verzerren.
TOPIC = "gesundheitsbezogene Effekte in klinischer Forschung (gemischter Korpus)"

# Pipeline-Typen, die das Goldstandard-Enum nicht kennt.
TYP_ABBILDUNG = {"mean_diff": "md", "heritability": "other"}
ERLAUBTE_TYPEN = {"or", "rr", "hr", "md", "smd", "g", "beta", "r", "z", "other"}


def lade_dokumente() -> list[dict]:
    daten = json.loads(DOCS.read_text(encoding="utf-8"))
    return list(daten.get("documents") or [])


def jahr_wert(wert) -> int | None:
    try:
        jahr = int(str(wert).strip())
    except (TypeError, ValueError):
        return None
    return jahr if 1900 <= jahr <= 2100 else None


def zahlen_wert(wert):
    return None if wert is None else float(wert)


def effekt_zeile(row: dict, doc: dict, text: str, sections: list[dict],
                 index: int) -> tuple[dict | None, str]:
    """Eine Pipeline-Zeile ins Goldstandard-Schema, oder Grund zum Verwerfen."""
    effect = zahlen_wert(row.get("effect"))
    if effect is None:
        return None, "kein Effektwert"

    outcome = " ".join(str(row.get("outcome") or "").split())
    comparison = " ".join(str(row.get("comparison") or "").split())
    if len(outcome) < 2 or len(comparison) < 2:
        return None, "Outcome oder Vergleich leer"

    typ = str(row.get("effect_type") or "").strip().lower()
    typ = TYP_ABBILDUNG.get(typ, typ)
    if typ not in ERLAUBTE_TYPEN:
        return None, f"Effekttyp '{typ}' nicht im Schema"

    quote = str(row.get("quote") or "")
    span = locate_quote(text, quote) if quote else None
    if span is None:
        return None, "Zitat nicht im Volltext"
    if not span.exact:
        # Nur exakte Treffer: die Anleitung verlangt einen woertlichen
        # Ausschnitt ohne Auslassung (Abschnitt 6). Unscharf gefundene
        # Saetze sind ein Kandidat, kein Beleg.
        return None, "Zitat nur unscharf gefunden"
    # locate_quote sucht im normalisierten Text; fuer das Schema zaehlt der
    # literale Ausschnitt, damit text[quote_start:quote_end] == quote gilt.
    quote = text[span.start:span.end]
    if len(quote.strip()) < 8:
        return None, "Zitat zu kurz"

    design = " ".join(str(row.get("design") or "").split()) or doc["design_verbatim"]
    niedrig, hoch = zahlen_wert(row.get("ci_low")), zahlen_wert(row.get("ci_high"))
    se = zahlen_wert(row.get("se"))
    # Abschnitt 2 der Anleitung: eine Zeile braucht einen quantifizierten
    # Effekt MIT Unsicherheit. Ein nackter Punktschaetzer ohne KI und ohne SE
    # ist keine Goldstandard-Zeile (und der Pruefer weist sie ab).
    if se is None and (niedrig is None or hoch is None):
        return None, "ohne KI und ohne SE"
    # Kurzcheck der Anleitung: der Punktschaetzer muss im KI liegen. Eine
    # Zeile, die sich selbst widerspricht, ist keine belegte Lesung.
    if (niedrig is not None and hoch is not None
            and not (min(niedrig, hoch) - 1e-9 <= effect <= max(niedrig, hoch) + 1e-9)):
        return None, "Effekt ausserhalb des KI"
    adjusted = row.get("adjusted")
    adjusted_wert = True if adjusted == 1 else (False if adjusted == 0 else None)

    zeile = {
        "effect_id": f"{doc['document_id']}-{index:02d}",
        "outcome_verbatim": outcome,
        "outcome_normalized": str(row.get("outcome_key") or outcome).strip(),
        "comparison_verbatim": comparison,
        "effect_type": typ,
        "effect": effect,
        "se": se,
        "ci_low": niedrig,
        "ci_high": hoch,
        "ci_level": zahlen_wert(row.get("ci_level")),
        "n": int(row["n"]) if row.get("n") else None,
        "adjusted": adjusted_wert,
        "time_point": (str(row.get("time_point") or "").strip() or None),
        "population": (str(row.get("population") or "").strip() or None),
        "design_verbatim": design,
        "quote": quote,
        "quote_start": span.start,
        "quote_end": span.end,
        "section": section_for_offset(sections, span.start) or None,
        "certainty": ("high" if (niedrig is not None and hoch is not None)
                      else "medium"),
        "is_primary": not aggregate_design(design),
        "notes": (
            f"maschinell gelesen ({EXTRACTOR_VERSION}, ein Lesepass), "
            f"Zitat woertlich aus dem Volltext an Position {span.start}"
        ),
    }
    return zeile, ""


def dokument_block(doc: dict, zeilen: list[dict], verworfen: list[str]) -> dict:
    block = {
        "document_id": doc["document_id"],
        "path": f"fulltext/{doc['document_id']}.txt",
        "title": doc["title"],
        "year": jahr_wert(doc.get("year")),
        "design_verbatim": doc["design_verbatim"],
        "design_category": doc["design_category"],
        "stratum": doc["stratum"],
        "has_text_layer": True,
        "effects": zeilen,
        "no_effect_reason": None,
    }
    if doc.get("probelauf") is not None:
        block["probelauf"] = bool(doc["probelauf"])
    if not zeilen:
        grund = "Modelllesung ergab keine belegte Effektzeile"
        if verworfen:
            grund += f" ({len(verworfen)} verworfene Kandidaten)"
        block["no_effect_reason"] = grund
    return block


async def baue(args) -> int:
    dokumente = lade_dokumente()
    if args.docs:
        gewuenscht = {d.strip() for d in args.docs.split(",") if d.strip()}
        dokumente = [d for d in dokumente if d["document_id"] in gewuenscht]
    if args.limit:
        dokumente = dokumente[: args.limit]
    if not dokumente:
        print("Keine Dokumente ausgewaehlt.", file=sys.stderr)
        return 2

    llm = LLMEngine()
    extraktor = EffectExtractor(llm, None, double_pass=False)
    bremse = asyncio.Semaphore(max(1, args.concurrency))
    start = time.monotonic()

    async def ein_dokument(doc: dict) -> tuple[dict, dict]:
        pfad = FULLTEXT / f"{doc['document_id']}.txt"
        text = pfad.read_text(encoding="utf-8")
        sections = split_sections(text)
        t0 = time.monotonic()
        async with bremse:
            rows = await extraktor._one_pass(
                doc["document_id"], text, TOPIC, sections, pass_number=1,
            )
        zeilen, verworfen = [], []
        for row in rows:
            zeile, grund = effekt_zeile(row, doc, text, sections, len(zeilen) + 1)
            if zeile is None:
                verworfen.append(grund)
            else:
                zeilen.append(zeile)
        block = dokument_block(doc, zeilen, verworfen)
        dauer = time.monotonic() - t0
        print(
            f"[{doc['document_id'][:10]}] {len(rows)} gelesen, {len(zeilen)} belegt, "
            f"{len(verworfen)} verworfen, {dauer:.0f}s"
            + (f" | {verworfen[0]}" if verworfen else ""),
            flush=True,
        )
        return block, {"dauer": dauer, "gelesen": len(rows), "verworfen": verworfen}

    try:
        ergebnisse = await asyncio.gather(*(ein_dokument(d) for d in dokumente))
    finally:
        await llm.close()

    bloecke = [e[0] for e in ergebnisse]
    meta = [e[1] for e in ergebnisse]
    dauer = time.monotonic() - start

    datei = {
        "dataset": "goldstandard_effects",
        "version": "1.0",
        "annotator": "A",
        "annotation_date": datetime.now(timezone.utc).date().isoformat(),
        "instructions_version": "v1.2",
        "blind": False,
        "notes": (
            "MASCHINELL erzeugt mit scripts/erzeuge_modell_annotation.py "
            f"({EXTRACTOR_VERSION}, ein Lesepass je Dokument). Kein menschlicher "
            "Annotator, nicht blind im Sinne der Anleitung und NICHT die "
            "eingefrorene A-Datei vom 10.11.2026 "
            "(SHA-256 d9bb867c303dc19d...). certainty und is_primary sind "
            "mechanisch abgeleitet."
        ),
        "documents": bloecke,
    }

    ausgabe = Path(args.out)
    ausgabe.parent.mkdir(parents=True, exist_ok=True)
    ausgabe.write_text(json.dumps(datei, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    zeilen_gesamt = sum(len(b["effects"]) for b in bloecke)
    ohne_zeile = [b["document_id"] for b in bloecke if not b["effects"]]
    verworfen_gesamt = sum(len(m["verworfen"]) for m in meta)
    print(f"\nFertig: {len(bloecke)} Dokumente, {zeilen_gesamt} Zeilen, "
          f"{len(ohne_zeile)} ohne Zeile, {verworfen_gesamt} verworfen, "
          f"{dauer:.0f}s -> {ausgabe}", flush=True)

    if args.md:
        bericht = Path(args.md)
        bericht.parent.mkdir(parents=True, exist_ok=True)
        zeilen_md = [
            "# Maschinelle Effektzeilen-Annotation (2026-11-17)",
            "",
            "Kein menschlicher Annotator: `scripts/erzeuge_modell_annotation.py` "
            f"liest die 30 Goldstandard-Volltexte mit `{EXTRACTOR_VERSION}` "
            "(ein Lesepass) und bildet die Zeilen auf "
            "`docs/internal/goldstandard_schema.json` ab.",
            "",
            "**Nicht die eingefrorene A-Datei.** Das Original (69 Zeilen, 13 "
            "Begruendungen, SHA-256 `d9bb867c303dc19d...`) ist am 16.11.2026 "
            "geloescht worden und aus einer Modelllesung nicht reproduzierbar. "
            "Diese Datei ist eine neue, als maschinell gekennzeichnete Annotation "
            "(`blind: false`).",
            "",
            "## Ergebnis",
            "",
            f"- Dokumente: {len(bloecke)}",
            f"- Effektzeilen: {zeilen_gesamt}",
            f"- Dokumente ohne belegte Zeile: {len(ohne_zeile)}",
            f"- verworfene Kandidaten (Zitat nicht im Text, Effekttyp, leerer Wert): "
            f"{verworfen_gesamt}",
            f"- Laufzeit: {dauer / 60:.1f} min",
            f"- Datei: `{ausgabe.relative_to(ROOT).as_posix()}`",
            "",
            "## Je Dokument",
            "",
            "| Dokument | gelesen | belegt | verworfen | Dauer |",
            "|---|---|---|---|---|",
        ]
        for block, m in zip(bloecke, meta):
            zeilen_md.append(
                f"| `{block['document_id'][:10]}` | {m['gelesen']} | "
                f"{len(block['effects'])} | {len(m['verworfen'])} | {m['dauer']:.0f}s |"
            )
        gruende = [g for m in meta for g in m["verworfen"]]
        if gruende:
            from collections import Counter
            zeilen_md += ["", "## Verwerfungsgruende", ""]
            for grund, anzahl in Counter(gruende).most_common():
                zeilen_md.append(f"- {anzahl}x {grund}")
        bericht.write_text("\n".join(zeilen_md) + "\n", encoding="utf-8")
        print(f"Bericht: {bericht}", flush=True)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(STANDARD_OUT))
    parser.add_argument("--md", default=str(STANDARD_MD))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--docs", default="")
    parser.add_argument("--concurrency", type=int, default=3)
    return asyncio.run(baue(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
