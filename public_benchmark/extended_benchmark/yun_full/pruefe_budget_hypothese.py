"""Prueft die Budget-Hypothese an den vorhandenen Laufdaten, ohne Netzaufruf.

Hypothese (Fassung 1): "Die 103 `length`-Ausfaelle im Lauf `yun699_8000_alle`
entstehen, weil 8.000 Completion-Tokens zu knapp sind; mehr Budget haette sie
gerettet."

Geprueft werden vier voneinander unabhaengige Vorhersagen dieser Hypothese:

A  Mechanik: Wenn das Budget die Ursache ist, muss die Antwort genau an der
   Obergrenze abgeschnitten sein (`completion_tokens == max_tokens`) und die
   Reasoning-Laenge in Zeichen zur Obergrenze passen.
B  Dosis-Wirkung: Wo derselbe Record mit mehreren Budgets lief, muss ein
   groesseres Budget die Ausfallquote senken.
C  Rettung: Fuer die 103 Ausfaelle muss es Beobachtungen mit groesserem Budget
   geben, die gelingen.
D  Skalierung: Die Reasoning-Laenge darf nicht mit dem Budget mitwachsen. Waechst
   sie mit, verschiebt mehr Budget den Ausfall nur nach hinten.

Aufruf:  python yun_full/pruefe_budget_hypothese.py [--json PFAD] [--md PFAD]
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
RUNS = HIER.parent / "runs"
LESEKOPIE = RUNS / "_lesekopie_20261118" / "predictions.jsonl"
SCHWELLE_HOCH = 16000  # ab hier gilt ein Budget als "deutlich groesser als 8.000"


def lade(verzeichnis: Path) -> list[dict[str, Any]]:
    zeilen: list[dict[str, Any]] = []
    for pfad in sorted(verzeichnis.glob("*/predictions.jsonl")):
        lauf = pfad.parent.name
        if lauf.startswith("_"):
            continue
        with pfad.open(encoding="utf-8") as fh:
            for nummer, roh in enumerate(fh, 1):
                if not roh.strip():
                    continue
                try:
                    zeile = json.loads(roh)
                except json.JSONDecodeError:
                    continue
                zeile["_lauf"] = lauf
                zeile["_nummer"] = nummer
                zeilen.append(zeile)
    return zeilen


def budget(zeile: dict[str, Any]) -> int | None:
    """Obergrenze der Zeile; alte Laeufe haben kein `gateway_params`."""
    params = zeile.get("gateway_params") or {}
    wert = params.get("max_tokens")
    if isinstance(wert, int) and wert > 0:
        return wert
    if (zeile.get("finish_reason") or "") == "length":
        tokens = zeile.get("completion_tokens")
        if isinstance(tokens, int) and tokens > 0:
            return tokens  # abgeschnitten: die erreichte Zahl ist die Grenze
    return None


def zustand(zeile: dict[str, Any]) -> str:
    """ok = Zellen geliefert, leer = Antwort ohne Zellen, length = abgeschnitten."""
    if (zeile.get("finish_reason") or "") == "length":
        return "length"
    return "ok" if (zeile.get("rows") or []) else "leer"


def quantile(werte: list[float]) -> dict[str, float]:
    if not werte:
        return {}
    sortiert = sorted(werte)
    mitte = statistics.median(sortiert)
    return {
        "n": len(sortiert),
        "min": round(sortiert[0], 1),
        "median": round(mitte, 1),
        "max": round(sortiert[-1], 1),
    }


def teil_a(glm: list[dict[str, Any]]) -> dict[str, Any]:
    """Mechanik: sitzt der Abschnitt genau an der Obergrenze?"""
    abgeschnitten = [z for z in glm if zustand(z) == "length" and budget(z)]
    an_der_grenze = [
        z for z in abgeschnitten if z.get("completion_tokens") == budget(z)
    ]
    verhaeltnis = [
        z["reasoning_chars"] / budget(z)
        for z in an_der_grenze
        if isinstance(z.get("reasoning_chars"), int) and z["reasoning_chars"] > 0
    ]
    ohne_inhalt = [
        z for z in an_der_grenze if not (z.get("content_chars") or 0)
    ]
    return {
        "abgeschnittene_zeilen": len(abgeschnitten),
        "davon_completion_tokens_gleich_budget": len(an_der_grenze),
        "davon_ohne_inhalt": len(ohne_inhalt),
        "reasoning_zeichen_je_token": quantile(verhaeltnis),
    }


def teil_b(glm: list[dict[str, Any]]) -> dict[str, Any]:
    """Dosis-Wirkung: derselbe Record unter mehreren Budgets."""
    je_record: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for z in glm:
        b = budget(z)
        if b:
            je_record[z["record_id"]].append(z)

    paare: Counter[str] = Counter()
    beispiele: list[dict[str, Any]] = []
    for rid, zeilen in je_record.items():
        budgets = sorted({budget(z) for z in zeilen})
        for klein in budgets:
            for gross in budgets:
                if gross <= klein:
                    continue
                zustand_klein = {zustand(z) for z in zeilen if budget(z) == klein}
                zustand_gross = {zustand(z) for z in zeilen if budget(z) == gross}
                for a in zustand_klein:
                    for b in zustand_gross:
                        schluessel = f"{klein}->{gross}: {a}->{b}"
                        paare[schluessel] += 1
                        if a != b and len(beispiele) < 40:
                            beispiele.append(
                                {
                                    "record_id": rid,
                                    "von": klein,
                                    "nach": gross,
                                    "von_zustand": a,
                                    "nach_zustand": b,
                                }
                            )
    return {"paare": dict(sorted(paare.items())), "wechsel": beispiele}


def teil_c(glm: list[dict[str, Any]]) -> dict[str, Any]:
    """Rettung: die Ausfaelle des 8000er Laufs unter groesserem Budget."""
    acht = [z for z in glm if budget(z) == 8000]
    ausfaelle = [z for z in acht if zustand(z) == "length"]
    ids = {z["record_id"] for z in ausfaelle}
    hoeher: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for z in glm:
        b = budget(z)
        if b and b >= SCHWELLE_HOCH and z["record_id"] in ids:
            hoeher[z["record_id"]].append(z)

    gerettet, weiter_length, ohne_zellen = [], [], []
    for rid, zeilen in hoeher.items():
        zustaende = {zustand(z) for z in zeilen}
        if "ok" in zustaende:
            gerettet.append(rid)
        elif "length" in zustaende:
            weiter_length.append(rid)
        else:
            ohne_zellen.append(rid)
    return {
        "ausfaelle_bei_8000": len(ausfaelle),
        "davon_mit_beobachtung_ueber_schwelle": len(hoeher),
        "davon_mit_zellen_gerettet": len(gerettet),
        "davon_erneut_length": len(weiter_length),
        "davon_nur_leer": len(ohne_zellen),
        "beispiele_gerettet": sorted(gerettet)[:15],
        "beispiele_weiter_length": sorted(weiter_length)[:15],
    }


def teil_d(glm: list[dict[str, Any]]) -> dict[str, Any]:
    """Skalierung: waechst die Reasoning-Laenge mit dem Budget?"""
    je_record: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for z in glm:
        b, r = budget(z), z.get("reasoning_chars")
        if b and isinstance(r, int) and r > 0:
            je_record[z["record_id"]].append((b, r))

    zunahmen: list[float] = []
    for paare in je_record.values():
        paare.sort()
        if len(paare) < 2:
            continue
        (b_klein, r_klein), (b_gross, r_gross) = paare[0], paare[-1]
        if b_gross > b_klein:
            zunahmen.append(r_gross / r_klein)

    # Ausfallquote je Budgetstufe, nur Zeilen mit bekannter Grenze.
    je_budget: dict[int, Counter[str]] = defaultdict(Counter)
    for z in glm:
        b = budget(z)
        if b:
            je_budget[b][zustand(z)] += 1
    quota = {
        str(b): {
            "n": sum(c.values()),
            "ok": c["ok"],
            "leer": c["leer"],
            "length": c["length"],
            "anteil_length": round(c["length"] / sum(c.values()), 4),
        }
        for b, c in sorted(je_budget.items())
        if sum(c.values()) >= 5
    }
    return {
        "reasoning_wachstum_bei_mehr_budget": quantile(zunahmen),
        "quota_je_budget": quota,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(HIER.parent / "iterativ" / "ergebnisse" / "budget_hypothese_20261118.json"))
    parser.add_argument("--md", default=str(HIER.parent / "iterativ" / "ergebnisse" / "budget_hypothese_20261118.md"))
    args = parser.parse_args()

    alle = lade(RUNS)
    glm = [z for z in alle if z.get("model") == "glm"]
    kopie = []
    if LESEKOPIE.exists():
        with LESEKOPIE.open(encoding="utf-8") as fh:
            for roh in fh:
                if roh.strip():
                    zeile = json.loads(roh)
                    if zeile.get("model") == "glm":
                        kopie.append(zeile)

    bericht = {
        "datenbasis": {
            "glm_zeilen_alle_laeufe": len(glm),
            "laeufe": len({z["_lauf"] for z in glm}),
            "glm_zeilen_lesekopie": len(kopie),
        },
        "A_mechanik": teil_a(glm),
        "B_dosis_wirkung": teil_b(glm),
        "C_rettung": teil_c(glm),
        "D_skalierung": teil_d(glm),
    }
    # Teil A und C zusaetzlich auf der stabilen Lesekopie, damit die Aussage
    # nicht von spaeteren Nachzugzeilen abhaengt.
    bericht["A_mechanik_lesekopie"] = teil_a(kopie)
    bericht["C_rettung_lesekopie"] = teil_c(kopie)

    ziel = Path(args.json)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    a = bericht["A_mechanik"]
    c = bericht["C_rettung"]
    d = bericht["D_skalierung"]
    zeilen = [
        "# Budget-Hypothese: Pruefung an den vorhandenen Daten",
        "",
        f"GLM-Zeilen ueber alle Laeufe: {len(glm)} aus {bericht['datenbasis']['laeufe']} Laeufen; "
        f"Lesekopie: {len(kopie)} Zeilen. Kein Netzaufruf, keine Datei im Laufverzeichnis veraendert.",
        "",
        "## A Mechanik",
        "",
        f"- abgeschnittene Zeilen mit bekannter Grenze: {a['abgeschnittene_zeilen']}",
        f"- davon `completion_tokens` genau gleich der Grenze: {a['davon_completion_tokens_gleich_budget']}",
        f"- davon ohne Inhalt: {a['davon_ohne_inhalt']}",
        f"- Reasoning-Zeichen je Token: {a['reasoning_zeichen_je_token']}",
        "",
        "## B Dosis-Wirkung (derselbe Record, zwei Budgets)",
        "",
    ]
    for schluessel, anzahl in bericht["B_dosis_wirkung"]["paare"].items():
        zeilen.append(f"- {schluessel}: {anzahl}")
    zeilen += [
        "",
        "## C Rettung der 8000er Ausfaelle",
        "",
        f"- Ausfaelle bei 8.000: {c['ausfaelle_bei_8000']}",
        f"- davon mit Beobachtung ab {SCHWELLE_HOCH}: {c['davon_mit_beobachtung_ueber_schwelle']}",
        f"- davon mit Zellen: {c['davon_mit_zellen_gerettet']}",
        f"- davon erneut `length`: {c['davon_erneut_length']}",
        f"- gerettet: {', '.join(c['beispiele_gerettet']) or '-'}",
        f"- weiter `length`: {', '.join(c['beispiele_weiter_length']) or '-'}",
        "",
        "## D Skalierung",
        "",
        f"- Reasoning-Wachstum bei mehr Budget: {d['reasoning_wachstum_bei_mehr_budget']}",
        "",
        "| Budget | n | ok | leer | length | Anteil length |",
        "|---|---|---|---|---|---|",
    ]
    for b, q in d["quota_je_budget"].items():
        zeilen.append(f"| {b} | {q['n']} | {q['ok']} | {q['leer']} | {q['length']} | {q['anteil_length']:.1%} |")
    Path(args.md).write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in bericht.items() if k != "B_dosis_wirkung"}, ensure_ascii=False, indent=2))
    print("\nDosis-Wirkung:")
    for schluessel, anzahl in bericht["B_dosis_wirkung"]["paare"].items():
        print(f"  {schluessel}: {anzahl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
