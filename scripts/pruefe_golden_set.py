#!/usr/bin/env python3
"""Prüft das Golden-Set der Qualitaets-Eval gegen die aktuelle research.db.

Jeder DB-verankerte Claim muss einen Record der aktuellen Erhebung zitieren.
Geprüft wird, dass der Record existiert, dass sein Text unter `record_text`
wortgleich wiederkehrt, dass jede im Claim genannte Zahl in diesem Text steht
und dass die Terme des Claims vom Record getragen werden. Externe Claims sind
am Praefix `re-research:` erkennbar und werden nicht gegen die DB geprüft.

Mit `--diff-alt` wird zusaetzlich der Record-Diffbericht gegen einen frueheren
Stand erzeugt (Paarung ueber das Feld `replaces`).

Aufruf:
    python scripts/pruefe_golden_set.py
    python scripts/pruefe_golden_set.py --diff-alt <alte_golden_answers.json>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent
GOLDEN = ROOT / "research_agent" / "evals" / "golden_answers.json"
DIFF = ROOT / "research_agent" / "evals" / "golden_set_diff.md"
DB = ROOT / "data" / "research.db"

BEFUNDE = {
    "unveraendert",
    "neu_verankert",
    "record_geaendert",
    "inhaltlich_ersetzt",
    "neu",
    "extern",
}
ABDECKUNG_MIN = 0.5
QUELLEN = {"fact": ("facts", "content"), "hypothesis": ("hypotheses", "claim"),
           "evidence": ("evidence", "content")}
FREMD = "re-research:"


def lade_quality_eval():
    """Term- und Zahlenlogik aus der Eval selbst, damit die Regeln gleich bleiben."""
    pfad = ROOT / "research_agent" / "evals" / "quality_eval.py"
    spec = importlib.util.spec_from_file_location("quality_eval", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def oeffne_db(pfad: Path) -> sqlite3.Connection:
    if not pfad.is_file():
        raise SystemExit(f"FEHLER: DB fehlt: {pfad}")
    conn = sqlite3.connect(f"file:{pfad.as_posix()}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def normalisiere(text: str) -> str:
    return " ".join((text or "").split())


def record_texte(conn: sqlite3.Connection, quelle: str) -> list[str] | None:
    """Liefert die moeglichen Record-Texte zu `fact <id>` usw.; None = kein Record."""
    teile = quelle.split()
    if len(teile) != 2 or teile[0] not in set(QUELLEN) | {"journal"}:
        return None
    art, kennung = teile
    if art == "journal":
        zeile = conn.execute(
            "SELECT important_findings FROM journal_entries WHERE id=?", (kennung,)
        ).fetchone()
        if zeile is None:
            return None
        try:
            return [normalisiere(t) for t in json.loads(zeile[0] or "[]")]
        except json.JSONDecodeError:
            return []
    tabelle, spalte = QUELLEN[art]
    zeile = conn.execute(
        f"SELECT {spalte} FROM {tabelle} WHERE id=?", (kennung,)
    ).fetchone()
    if zeile is None:
        return None
    return [normalisiere(zeile[0] or "")]


def pruefe(golden: dict, conn: sqlite3.Connection, qe) -> tuple[list[str], list[dict]]:
    fehler: list[str] = []
    zeilen: list[dict] = []
    ersetzt: dict[str, int] = {}
    for frage in golden.get("questions", []):
        for nummer, claim in enumerate(frage.get("claims", [])):
            ort = f"{frage.get('id')}[{nummer}]"
            quelle = (claim.get("source") or "").strip()
            befund = claim.get("befund", "")
            if befund not in BEFUNDE:
                fehler.append(f"{ort}: unbekannter Befund {befund!r}")
            if quelle.startswith(FREMD):
                if befund != "extern":
                    fehler.append(f"{ort}: Fremdquelle braucht den Befund 'extern'")
                if claim.get("record_text"):
                    fehler.append(f"{ort}: Fremdquelle darf keinen record_text tragen")
                zeilen.append({"ort": ort, "quelle": quelle, "befund": befund,
                               "abdeckung": None, "zahlen": claim.get("numbers", [])})
                continue
            texte = record_texte(conn, quelle)
            if texte is None:
                fehler.append(f"{ort}: Quelle fehlt in der DB: {quelle!r}")
                continue
            zitat = normalisiere(claim.get("record_text", ""))
            if not zitat:
                fehler.append(f"{ort}: record_text fehlt")
                continue
            if zitat not in texte:
                fehler.append(f"{ort}: record_text weicht vom DB-Text ab ({quelle})")
                continue
            klein = zitat.lower()
            for zahl in claim.get("numbers", []):
                varianten = qe._number_variants(str(zahl))
                if not any(v.lower() in klein for v in varianten):
                    fehler.append(f"{ort}: Zahl {zahl!r} steht nicht im Record-Text")
            claim_terme = set(qe._significant_terms(claim["claim"]))
            record_terme = set(qe._significant_terms(zitat))
            abdeckung = (
                len(claim_terme & record_terme) / len(claim_terme) if claim_terme else 1.0
            )
            if abdeckung < ABDECKUNG_MIN:
                fehler.append(
                    f"{ort}: Claim wird vom Record nur zu {abdeckung:.2f} getragen "
                    f"(Minimum {ABDECKUNG_MIN})"
                )
            alt = claim.get("replaces", "")
            if alt:
                ersetzt[alt] = ersetzt.get(alt, 0) + 1
                # Alte Quellen nennen teils zwei IDs ("fact A / fact B"); der
                # Praefix-Vergleich erkennt den gemeinsamen Record wieder.
                gleicher_record = alt == quelle or alt.startswith(quelle)
                if gleicher_record and befund != "unveraendert":
                    fehler.append(
                        f"{ort}: gleiche Quelle wie vorher braucht den Befund 'unveraendert'"
                    )
                if not gleicher_record and befund == "unveraendert":
                    fehler.append(f"{ort}: neue Quelle {quelle!r} ist nicht 'unveraendert'")
            elif befund not in {"extern", "neu"}:
                fehler.append(f"{ort}: Feld 'replaces' fehlt (welchen Claim ersetzt das?)")
            zeilen.append({"ort": ort, "quelle": quelle, "befund": befund,
                           "abdeckung": abdeckung, "zahlen": claim.get("numbers", [])})

    entfallen = golden.get("meta", {}).get("entfallen", [])
    for eintrag in entfallen:
        quelle = eintrag.get("quelle_alt", "")
        if quelle in ersetzt:
            fehler.append(
                f"entfallen: {quelle!r} wird zugleich als ersetzt gefuehrt "
                f"({eintrag.get('frage')})"
            )
    return fehler, zeilen


def pruefe_abgleich(alt: dict, neu: dict) -> list[str]:
    """Jeder alte DB-Claim ist entweder ersetzt oder ausdruecklich entfallen."""
    fehler: list[str] = []
    alt_claims = [
        (frage.get("id"), nummer, (claim.get("source") or "").strip())
        for frage in alt.get("questions", [])
        for nummer, claim in enumerate(frage.get("claims", []))
        if not (claim.get("source") or "").strip().startswith(FREMD)
    ]
    ersetzt = [
        ((claim.get("replaces") or "").strip(), frage.get("id"), nummer)
        for frage in neu.get("questions", [])
        for nummer, claim in enumerate(frage.get("claims", []))
        if (claim.get("replaces") or "").strip()
    ]
    entfallen = {
        (eintrag.get("frage"), eintrag.get("position")): eintrag.get("quelle_alt", "")
        for eintrag in neu.get("meta", {}).get("entfallen", [])
    }
    for schluessel, frage_id, nummer in ersetzt:
        if not any(quelle == schluessel for _, _, quelle in alt_claims):
            fehler.append(f"{frage_id}[{nummer}]: replaces zeigt auf keine alte Quelle: {schluessel!r}")
    offen = [
        (frage_id, nummer, quelle)
        for frage_id, nummer, quelle in alt_claims
        if quelle not in {s for s, _, _ in ersetzt}
        and (frage_id, nummer) not in entfallen
    ]
    for frage_id, nummer, quelle in offen:
        fehler.append(
            f"{frage_id}[{nummer}]: alter Claim {quelle!r} ist weder ersetzt noch in entfallen gelistet"
        )
    for (frage_id, nummer), quelle in entfallen.items():
        passend = [q for f, n, q in alt_claims if f == frage_id and n == nummer]
        if not passend:
            fehler.append(f"entfallen: {frage_id}[{nummer}] existiert im alten Set nicht")
        elif passend[0] != quelle:
            fehler.append(
                f"entfallen: {frage_id}[{nummer}] nennt {quelle!r}, alt war {passend[0]!r}"
            )
    # Doppelbuchung: eine alte Quelle darf nicht mehr Ersetzungen plus
    # Entfaelle haben, als sie im alten Set zitiert wurde.
    alt_je_quelle: dict[str, int] = {}
    for _, _, quelle in alt_claims:
        alt_je_quelle[quelle] = alt_je_quelle.get(quelle, 0) + 1
    neu_je_quelle = dict(alt_je_quelle)
    for quelle, _, _ in ersetzt:
        neu_je_quelle[quelle] = neu_je_quelle.get(quelle, 0) - 1
    for quelle in entfallen.values():
        neu_je_quelle[quelle] = neu_je_quelle.get(quelle, 0) - 1
    for quelle, rest in sorted(neu_je_quelle.items()):
        if rest:
            fehler.append(
                f"Abgleich: {quelle!r} wird {alt_je_quelle.get(quelle, 0)}x zitiert, "
                f"aber {alt_je_quelle.get(quelle, 0) - rest}x ersetzt und "
                f"{-rest if rest > 0 else 0}x als entfallen gefuehrt"
            )
    return fehler


def schreibe_diff(alt: dict, neu: dict, zeilen: list[dict], conn: sqlite3.Connection, pfad: Path) -> None:
    """Record-Diffbericht: je Claim der alte und der neue Record samt Befund."""
    alt_claims: dict[str, dict] = {}
    for frage in alt.get("questions", []):
        for claim in frage.get("claims", []):
            quelle = (claim.get("source") or "").strip()
            alt_claims.setdefault(quelle, {"frage": frage.get("id"), "claim": claim})
    neu_nach_alt: dict[str, list[dict]] = {}
    for frage in neu.get("questions", []):
        for nummer, claim in enumerate(frage.get("claims", [])):
            schluessel = (claim.get("replaces") or "").strip()
            if schluessel:
                neu_nach_alt.setdefault(schluessel, []).append(
                    {"frage": frage.get("id"), "pos": nummer, "claim": claim}
                )
    zahlen = {z["ort"]: z for z in zeilen}

    zeilen_md: list[str] = []
    entfallen_md: list[str] = []
    for frage in alt.get("questions", []):
        frage_id = frage.get("id")
        for nummer, claim in enumerate(frage.get("claims", [])):
            quelle = (claim.get("source") or "").strip()
            zahlen_alt = ", ".join(str(z) for z in claim.get("numbers", [])) or "-"
            if quelle.startswith(FREMD):
                zeilen_md.append(
                    f"| `{frage_id}` | {nummer} | `fremdbelegt` | - | extern | - | {zahlen_alt} | {zahlen_alt} |"
                )
                continue
            treffer = neu_nach_alt.get(quelle, []).pop(0) if neu_nach_alt.get(quelle) else None
            if treffer is None:
                entfallen_md.append(
                    f"| `{frage_id}` | {nummer} | `{quelle}` | - | entfallen | - | {zahlen_alt} | - |"
                )
                continue
            neu_claim = treffer["claim"]
            stats = zahlen.get(f"{treffer['frage']}[{treffer['pos']}]", {})
            abdeckung = stats.get("abdeckung")
            abdeckung_text = f"{abdeckung:.2f}" if abdeckung is not None else "-"
            neu_zahlen = ", ".join(str(z) for z in neu_claim.get("numbers", [])) or "-"
            zeilen_md.append(
                f"| `{frage_id}` | {nummer} | `{quelle}` | `{neu_claim.get('source')}` | "
                f"{neu_claim.get('befund')} | {abdeckung_text} | {zahlen_alt} | {neu_zahlen} |"
            )

    neu_ohne_alt = [
        f"| `{frage.get('id')}` | `{claim.get('source')}` | {claim.get('befund')} |"
        for frage in neu.get("questions", [])
        for claim in frage.get("claims", [])
        if not (claim.get("replaces") or "").strip() and not (claim.get("source") or "").startswith(FREMD)
    ]

    text = [
        "# Golden-Set: Record-Diff zwischen alter und aktueller Erhebung",
        "",
        "Erzeugt von `scripts/pruefe_golden_set.py --diff-alt` am 2026-11-17.",
        "Alt = `research_agent/evals/golden_answers.json` vom 2026-08-31 (Commit 0f09c89),",
        f"neu = derselbe Aufbau gegen `data/research.db` (Stand der aktuellen Erhebung).",
        "Gezeigt werden die Records, nicht die Claim-Texte: die stehen im Set selbst.",
        "",
        "Spalten: `Quelle alt` = im alten Set zitierter Record, `Quelle neu` = Record,",
        "der den Claim jetzt traegt, `Abdeckung` = Anteil der Claim-Terme, die im",
        "Record-Text vorkommen (1.00 = vollstaendig), `Zahlen alt/neu` = behauptete Werte.",
        "",
        "Befunde: `unveraendert` (Record und Text gleich), `neu_verankert` (Inhalt unter",
        "neuer ID, Text im Kern gleich), `record_geaendert` (Zahlen weichen ab),",
        "`inhaltlich_ersetzt` (anderer Record traegt die Aussage jetzt), `extern`",
        "(bewusst nicht aus der DB).",
        "",
        "| Frage | Pos. | Quelle alt | Quelle neu | Befund | Abdeckung | Zahlen alt | Zahlen neu |",
        "|---|---|---|---|---|---|---|---|",
        *zeilen_md,
        "",
    ]
    if neu_ohne_alt:
        # Claims, fuer die es im alten Stand keinen Vorgaenger gab.
        text += [
            "## Neue Claims ohne Vorgaenger",
            "",
            "| Frage | Quelle | Befund |",
            "|---|---|---|",
            *neu_ohne_alt,
            "",
        ]
    text += [
        "## Entfallene Records",
        "",
        "Diese Claims hatten im alten Set einen DB-Record, der in der aktuellen",
        "Erhebung nicht mehr existiert; ein inhaltlich tragender Ersatz wurde nicht",
        "gefunden. Sie stehen nicht mehr im Set (siehe `meta.entfallen`).",
        "",
        "| Frage | Pos. | Quelle alt | Quelle neu | Befund | Abdeckung | Zahlen alt | Zahlen neu |",
        "|---|---|---|---|---|---|---|---|",
        *entfallen_md,
        "",
        "## Zaehlung",
        "",
        f"- Claims alt: {sum(len(q.get('claims', [])) for q in alt.get('questions', []))}",
        f"- Claims neu: {sum(len(q.get('claims', [])) for q in neu.get('questions', []))}",
        f"- davon DB-verankert: "
        f"{sum(1 for q in neu.get('questions', []) for c in q.get('claims', []) if not (c.get('source') or '').startswith(FREMD))}",
        f"- entfallen: {len(neu.get('meta', {}).get('entfallen', []))}",
        "",
    ]
    pfad.write_text("\n".join(text), encoding="utf-8")
    print(f"Diffbericht: {pfad.relative_to(ROOT)} ({len(zeilen_md)} Zeilen, {len(entfallen_md)} entfallen)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-Set gegen die aktuelle DB prüfen.")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--diff-alt", type=Path, help="frueherer Stand fuer den Diffbericht")
    args = parser.parse_args()

    golden = json.loads(args.golden.read_text(encoding="utf-8"))
    qe = lade_quality_eval()
    conn = oeffne_db(args.db)
    fehler, zeilen = pruefe(golden, conn, qe)

    claims = sum(len(q.get("claims", [])) for q in golden.get("questions", []))
    if fehler:
        print(f"GOLDEN-SET FEHLGESCHLAGEN: {len(fehler)} Abweichungen", file=sys.stderr)
        for fehler_text in fehler:
            print(f"- {fehler_text}", file=sys.stderr)
        return 1

    print(f"GOLDEN-SET OK: {claims} Claims, {len(golden.get('questions', []))} Fragen")
    for zeile in zeilen:
        if zeile["befund"] == "extern":
            continue
        abdeckung = f"{zeile['abdeckung']:.2f}"
        zahlen = ",".join(str(z) for z in zeile["zahlen"]) or "-"
        print(f"  {zeile['ort']}: {zeile['quelle']} [{zeile['befund']}] Abdeckung {abdeckung}, Zahlen {zahlen}")

    if args.diff_alt:
        alt = json.loads(args.diff_alt.read_text(encoding="utf-8"))
        abgleich = pruefe_abgleich(alt, golden)
        if abgleich:
            print(f"GOLDEN-SET ABGLEICH FEHLGESCHLAGEN: {len(abgleich)} Abweichungen", file=sys.stderr)
            for fehler_text in abgleich:
                print(f"- {fehler_text}", file=sys.stderr)
            return 1
        schreibe_diff(alt, golden, zeilen, conn, DIFF)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
