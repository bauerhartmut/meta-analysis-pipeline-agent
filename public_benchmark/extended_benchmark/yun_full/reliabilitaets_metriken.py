"""Zuverlaessigkeitsmetriken eines Laufs — offline aus `predictions.jsonl`.

Technische Zuverlaessigkeit und Extraktionsqualitaet werden getrennt gezaehlt:
eine Antwort ohne Zellen ist kein technischer Ausfall, sondern ein Ergebnis der
Extraktion.

Die Versuchsspur (`attempts`, `http_versuche`, `job_status`) entsteht nur unter
`--retry-strategie neu`. Fehlt sie, bleibt das Feld `None`; abgeleitet wird nur
`job_status` (aus `fehlerklasse`), und das steht als `abgeleitet` in der Ausgabe.

Aufruf:
    python yun_full/reliabilitaets_metriken.py --run runs/<id>/predictions.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
RUNS = HIER.parent / "runs"
LESEKOPIE = RUNS / "_lesekopie_20261118" / "predictions.jsonl"
TRANSPORT = ("timeout", "verbindungsfehler")


def lade(pfad: Path) -> list[dict[str, Any]]:
    zeilen = []
    for roh in pfad.read_text(encoding="utf-8").splitlines():
        if roh.strip():
            zeilen.append(json.loads(roh))
    return zeilen


def finale_klasse(zeile: dict[str, Any]) -> str:
    """Die Klasse, mit der der Auftrag endete.

    Mit Versuchsspur steht sie im letzten Eintrag; unter `alt` nur im Feld
    `fehlerklasse`, das dort auch Transportfehler als `json_kaputt` fuehrt.
    """
    versuche = zeile.get("attempts") or []
    if versuche:
        return versuche[-1].get("fehlerklasse") or ""
    return zeile.get("fehlerklasse") or ""


def job_status(zeile: dict[str, Any]) -> tuple[str, bool]:
    """(Status, abgeleitet?) — ohne Spur aus `fehlerklasse` rekonstruiert."""
    if zeile.get("job_status"):
        return zeile["job_status"], False
    return ("failed" if zeile.get("fehlerklasse") else "completed"), True


def _verteilung(werte: list[float]) -> dict[str, Any]:
    if not werte:
        return {"n": 0, "mittel": None, "median": None, "max": None}
    sortiert = sorted(werte)
    return {
        "n": len(werte),
        "mittel": round(statistics.mean(sortiert), 2),
        "median": round(statistics.median(sortiert), 2),
        "max": round(sortiert[-1], 2),
    }


def _p90(werte: list[float]) -> float | None:
    if not werte:
        return None
    sortiert = sorted(werte)
    stelle = max(0, min(len(sortiert) - 1, int(round(0.9 * (len(sortiert) - 1)))))
    return round(sortiert[stelle], 2)


def metriken(zeilen: list[dict[str, Any]]) -> dict[str, Any]:
    """Rechnet alle Kennzahlen; keine Schwellen, keine Interpretation."""
    status: Counter[str] = Counter()
    abgeleitet = 0
    klassen: Counter[str] = Counter()
    http: list[float] = []
    versuche: list[float] = []
    wartend: list[float] = []
    latenz: list[float] = []
    erster_versuch = 0
    nach_wiederholung = 0
    tokens_gesamt = 0
    tokens_erfolgreich = 0
    erfolgte = 0
    leer = 0
    mit_zellen = 0
    spur = 0
    transport = 0

    for zeile in zeilen:
        zustand, erfunden = job_status(zeile)
        status[zustand] += 1
        abgeleitet += int(erfunden)
        klassen[finale_klasse(zeile) or "ok"] += 1

        if zeile.get("attempts"):
            spur += 1
            versuche.append(len(zeile["attempts"]))
            # Jeder aufgetretene Transportfehler zaehlt, auch wenn der Auftrag
            # ihn mit einem zweiten Versuch geheilt hat.
            transport += sum(
                1 for eintrag in zeile["attempts"] if eintrag.get("fehlerklasse") in TRANSPORT
            )
            wartend.extend(
                eintrag["wartete_s"]
                for eintrag in zeile["attempts"]
                if isinstance(eintrag.get("wartete_s"), (int, float))
            )
        if isinstance(zeile.get("http_versuche"), int):
            http.append(zeile["http_versuche"])

        if isinstance(zeile.get("elapsed_s"), (int, float)):
            latenz.append(float(zeile["elapsed_s"]))
        tokens = zeile.get("completion_tokens")
        if isinstance(tokens, int):
            tokens_gesamt += tokens
            if zustand == "completed":
                tokens_erfolgreich += tokens
        if zustand == "completed":
            erfolgte += 1
            if zeile.get("http_versuche") == 1 and len(zeile.get("attempts") or []) == 1:
                erster_versuch += 1
            elif zeile.get("http_versuche") or len(zeile.get("attempts") or []) > 1:
                nach_wiederholung += 1
        if not zeile.get("attempts") and finale_klasse(zeile) in TRANSPORT:
            transport += 1
        if zeile.get("rows"):
            mit_zellen += 1
        elif not zeile.get("fehlerklasse"):
            leer += 1

    technisch_vorhanden = bool(spur or http)
    return {
        "auftraege": len(zeilen),
        "zeilen_mit_versuchsspur": spur,
        "job_status": {
            "completed": status["completed"],
            "failed": status["failed"],
            "abgeleitet": abgeleitet,
        },
        "finale_klassen": dict(sorted(klassen.items())),
        "transportfehler": transport,
        "erfolg_im_ersten_versuch": erster_versuch if technisch_vorhanden else None,
        "erfolg_nach_wiederholung": nach_wiederholung if technisch_vorhanden else None,
        "endgueltig_fehlgeschlagen": status["failed"],
        "quote_erfolg": round(erfolgte / len(zeilen), 4) if zeilen else None,
        "versuche_je_auftrag": _verteilung(versuche) if technisch_vorhanden else None,
        "http_versuche": _verteilung(http) if technisch_vorhanden else None,
        "wartezeit_s": (
            {"summe": round(sum(wartend), 1), "mittel": round(statistics.mean(wartend), 2)}
            if wartend
            else None
        ),
        "latenz_s": {**_verteilung(latenz), "p90": _p90(latenz)},
        "tokens": {
            "gesamt": tokens_gesamt,
            "je_auftrag": round(tokens_gesamt / len(zeilen), 1) if zeilen else None,
            "je_erfolgreichem_auftrag": round(tokens_erfolgreich / erfolgte, 1) if erfolgte else None,
        },
        "extraktion": {
            "mit_zellen": mit_zellen,
            "leere_antworten": leer,
            "anteil_leer": round(leer / len(zeilen), 4) if zeilen else None,
        },
    }


def bericht(werte: dict[str, Any], quelle: str) -> str:
    """Markdown-Bericht; nennt zuerst, was die Daten nicht hergeben."""
    luecken = []
    if not werte["zeilen_mit_versuchsspur"]:
        luecken.append(
            "Keine Versuchsspur: der Lauf entstand unter `alt`. Wiederholungs- und "
            "Wartezeiten sind deshalb `None`, nicht 0."
        )
    if werte["job_status"]["abgeleitet"]:
        luecken.append(
            f"{werte['job_status']['abgeleitet']} Zeilen ohne `job_status`; er wurde "
            "aus `fehlerklasse` rekonstruiert."
        )
    if any(k in werte["finale_klassen"] for k in ("json_kaputt",)) and not werte["transportfehler"]:
        luecken.append(
            "Transportfehler sind hier nicht separat sichtbar: unter `alt` wurde ein "
            "Timeout als `json_kaputt` einsortiert."
        )

    def zahl(wert: Any) -> str:
        return "n/a" if wert is None else f"{wert}"

    zeilen = [
        f"# Zuverlaessigkeitsmetriken: {quelle}",
        "",
        f"Auftraege: {werte['auftraege']}, Erfolgsquote (technisch): "
        f"{zahl(werte['quote_erfolg'])}.",
        "",
        "## Technische Zuverlaessigkeit",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Zeilen mit Versuchsspur | {werte['zeilen_mit_versuchsspur']} |",
        f"| completed / failed | {werte['job_status']['completed']} / {werte['job_status']['failed']} |",
        f"| Erfolg im ersten Versuch | {zahl(werte['erfolg_im_ersten_versuch'])} |",
        f"| Erfolg nach Wiederholung | {zahl(werte['erfolg_nach_wiederholung'])} |",
        f"| endgueltig fehlgeschlagen | {werte['endgueltig_fehlgeschlagen']} |",
        f"| Transportfehler (timeout + Verbindung) | {werte['transportfehler']} |",
        f"| Versuche je Auftrag | {zahl(werte['versuche_je_auftrag'])} |",
        f"| HTTP-Versuche je Auftrag | {zahl(werte['http_versuche'])} |",
        f"| Wartezeit gesamt in s | {zahl((werte['wartezeit_s'] or {}).get('summe'))} |",
        f"| Latenz je Auftrag in s (Mittel/Median/p90) | {zahl(werte['latenz_s']['mittel'])} / "
        f"{zahl(werte['latenz_s']['median'])} / {zahl(werte['latenz_s']['p90'])} |",
        f"| Tokens gesamt | {werte['tokens']['gesamt']} |",
        f"| Tokens je erfolgreichem Auftrag | {zahl(werte['tokens']['je_erfolgreichem_auftrag'])} |",
        "",
        "## Finale Klassen",
        "",
        "| Klasse | Anzahl |",
        "|---|---|",
    ]
    zeilen += [f"| {klasse} | {anzahl} |" for klasse, anzahl in werte["finale_klassen"].items()]
    zeilen += [
        "",
        "## Extraktionsqualitaet (getrennt gezaehlt)",
        "",
        f"- Auftraege mit Zellen: {werte['extraktion']['mit_zellen']}",
        f"- leere Antworten ohne Fehlerklasse: {werte['extraktion']['leere_antworten']} "
        f"({zahl(werte['extraktion']['anteil_leer'])})",
        "",
        "## Was diese Zahlen nicht sagen",
        "",
    ]
    zeilen += [f"- {punkt}" for punkt in luecken] or ["- keine Einschraenkungen erkannt"]
    return "\n".join(zeilen) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default=str(LESEKOPIE), help="Pfad zu predictions.jsonl oder run-id")
    parser.add_argument("--modell", default="", help="nur dieses Modell zaehlen (z. B. glm)")
    parser.add_argument("--json", default="", help="Ziel fuer die Rohwerte")
    parser.add_argument("--md", default="", help="Ziel fuer den Bericht")
    args = parser.parse_args()

    pfad = Path(args.run)
    if not pfad.exists() and (RUNS / args.run / "predictions.jsonl").exists():
        pfad = RUNS / args.run / "predictions.jsonl"
    if not pfad.exists():
        print(f"FEHLER: {args.run} nicht gefunden", flush=True)
        return 2

    zeilen = lade(pfad)
    if args.modell:
        zeilen = [z for z in zeilen if z.get("model") == args.modell]
    werte = metriken(zeilen)
    quelle = f"{pfad.parent.name}" + (f" / {args.modell}" if args.modell else "")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(werte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(bericht(werte, quelle), encoding="utf-8")

    print(bericht(werte, quelle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
