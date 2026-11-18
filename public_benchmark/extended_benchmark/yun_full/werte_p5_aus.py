"""Wertet den P5-Lauf gegen die Ausfallzeilen der Lesekopie aus.

Stellt die Zeilen aus `runs/yun699_p5_24000_20261118/predictions.jsonl` je
`record_id` gegen die 103 `length_ohne_ergebnis`-Zeilen der Lesekopie und zaehlt
je Record: gerettet oder nicht, Zellen vorher/nachher, und wie viele der
Goldzellen adressiert werden. `yun2024:653` hat keine Goldzellen und wird als
nicht bewertbar getrennt gefuehrt.

Die Zellzaehlung ist eine grobe Selbstpruefung (Feld und Arm, Wertvergleich mit
1e-6), **nicht** die offizielle Bewertung; die kommt aus dem geschuetzten
Bewertungslauf und wird hier nicht nachgebaut.

Aufruf:
    python yun_full/werte_p5_aus.py                          # nach dem Lauf
    python yun_full/werte_p5_aus.py --neu <predictions.jsonl>
    python yun_full/werte_p5_aus.py --neu <lesekopie>         # Nullprobe
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
NEU = BENCH / "runs" / "yun699_p5_24000_20261118" / "predictions.jsonl"
ALT = BENCH / "runs" / "_lesekopie_20261118" / "predictions.jsonl"
RECORDS = HIER / "records" / "yun699.jsonl"
MODELL = "glm"
KLASSE = "length_ohne_ergebnis"
NICHT_BEWERTBAR = "yun2024:653"


def lade(pfad: Path) -> list[dict[str, Any]]:
    if not pfad.exists():
        return []
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def zellen(zeile: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not zeile:
        return []
    return list(((zeile.get("predicted") or {}).get("cells")) or [])


def zahl(wert: Any) -> float | None:
    if wert is None:
        return None
    text = str(wert).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def schluessel(zelle: dict[str, Any]) -> tuple[str, str]:
    return (str(zelle.get("field") or ""), str(zelle.get("arm") or "").strip().lower())


def deckung(gold: list[dict[str, Any]], vorhergesagt: list[dict[str, Any]]) -> tuple[int, int]:
    """(adressiert, wertgleich) ueber die Goldzellen; Schluessel ist Feld plus Arm."""
    nach_schluessel: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for zelle in vorhergesagt:
        nach_schluessel.setdefault(schluessel(zelle), []).append(zelle)
    adressiert = wertgleich = 0
    for zelle in gold:
        kandidaten = nach_schluessel.get(schluessel(zelle), [])
        if not kandidaten:
            continue
        adressiert += 1
        soll = zahl(zelle.get("value"))
        if soll is None:
            continue
        if any((ist := zahl(k.get("value"))) is not None and abs(ist - soll) < 1e-6 for k in kandidaten):
            wertgleich += 1
    return adressiert, wertgleich


def status(zeile: dict[str, Any] | None) -> str:
    if zeile is None:
        return "fehlt"
    if bool(zeile.get("failed")) or bool(zeile.get("fehlerklasse")):
        return "weiter_ausfall"
    return "gerettet" if zellen(zeile) else "fertig_ohne_zellen"


def auswerten(
    alt_zeilen: list[dict[str, Any]],
    neu_zeilen: list[dict[str, Any]],
    records: dict[str, dict[str, Any]],
    modell: str = MODELL,
) -> dict[str, Any]:
    alt = {
        z["record_id"]: z
        for z in alt_zeilen
        if z.get("model") == modell and z.get("fehlerklasse") == KLASSE
    }
    neu = {z["record_id"]: z for z in neu_zeilen if z.get("model") == modell}

    bewertbar: list[dict[str, Any]] = []
    nicht_bewertbar: list[dict[str, Any]] = []
    for rid in sorted(alt):
        gold = list(((records.get(rid) or {}).get("gold") or {}).get("cells") or [])
        neu_zeile = neu.get(rid)
        vorher = zellen(alt[rid])
        nachher = zellen(neu_zeile)
        adressiert, wertgleich = deckung(gold, nachher)
        eintrag = {
            "record_id": rid,
            "status": status(neu_zeile),
            "fehlerklasse_neu": (neu_zeile or {}).get("fehlerklasse", ""),
            "zellen_alt": len(vorher),
            "zellen_neu": len(nachher),
            "zellgewinn": len(nachher) - len(vorher),
            "goldzellen": len(gold),
            "adressiert": adressiert,
            "wertgleich": wertgleich,
            "tokens_alt": (alt[rid].get("completion_tokens") or 0),
            "tokens_neu": (neu_zeile or {}).get("completion_tokens") or 0,
            "reasoning_chars_neu": (neu_zeile or {}).get("reasoning_chars") or 0,
        }
        (bewertbar if len(gold) else nicht_bewertbar).append(eintrag)

    def summe(gruppe: list[dict[str, Any]], feld: str) -> int:
        return sum(e[feld] for e in gruppe)

    zaehlung = {"gerettet": 0, "fertig_ohne_zellen": 0, "weiter_ausfall": 0, "fehlt": 0}
    for eintrag in bewertbar + nicht_bewertbar:
        zaehlung[eintrag["status"]] += 1

    return {
        "modell": modell,
        "ausfallzeilen": len(alt),
        "bewertbar": bewertbar,
        "nicht_bewertbar": nicht_bewertbar,
        "status": zaehlung,
        "zellen_alt": summe(bewertbar + nicht_bewertbar, "zellen_alt"),
        "zellen_neu": summe(bewertbar + nicht_bewertbar, "zellen_neu"),
        "zellgewinn": summe(bewertbar + nicht_bewertbar, "zellgewinn"),
        "goldzellen_bewertbar": summe(bewertbar, "goldzellen"),
        "adressiert": summe(bewertbar, "adressiert"),
        "wertgleich": summe(bewertbar, "wertgleich"),
        "tokens_neu": summe(bewertbar + nicht_bewertbar, "tokens_neu"),
    }


def bericht(werte: dict[str, Any], neu_pfad: str, nullprobe: bool) -> str:
    s = werte["status"]
    bewertbar = werte["bewertbar"]
    nicht = werte["nicht_bewertbar"]
    zeilen = [
        "# P5-Auswertung: Rettung und Zellgewinn",
        "",
        f"Neu: `{neu_pfad}`. Vergleich: die {werte['ausfallzeilen']} "
        f"`{KLASSE}`-Zeilen der Lesekopie, Modell {werte['modell']}.",
        "",
    ]
    if nullprobe:
        zeilen += ["> **Nullprobe:** neu und alt sind dieselbe Datei. Erwartet sind "
                   "0 Rettungen, 0 Zellgewinn und die volle Goldzahl.", ""]
    zeilen += [
        "## Status je Record",
        "",
        "| Status | Records |",
        "|---|---|",
        f"| gerettet (Antwort mit Zellen) | {s['gerettet']} |",
        f"| fertig, aber ohne Zellen | {s['fertig_ohne_zellen']} |",
        f"| weiter ausgefallen | {s['weiter_ausfall']} |",
        f"| im neuen Lauf nicht enthalten | {s['fehlt']} |",
        "",
        f"Rettungsquote auf den **{len(bewertbar)} bewertbaren** Records: "
        f"**{sum(1 for e in bewertbar if e['status'] == 'gerettet')} von {len(bewertbar)}**"
        + (f" ({sum(1 for e in bewertbar if e['status'] == 'gerettet') / len(bewertbar):.1%})"
           if bewertbar else ""),
        "",
        "## Zellen und Gold",
        "",
        "| Groesse | Wert |",
        "|---|---|",
        f"| Zellen vorher (Ausfallzeilen) | {werte['zellen_alt']} |",
        f"| Zellen nachher | {werte['zellen_neu']} |",
        f"| Zellgewinn | {werte['zellgewinn']} |",
        f"| Goldzellen der bewertbaren | {werte['goldzellen_bewertbar']} |",
        f"| davon adressiert (Feld und Arm) | {werte['adressiert']} |",
        f"| davon wertgleich (1e-6) | {werte['wertgleich']} |",
        f"| Completion-Tokens neu | {werte['tokens_neu']} |",
        "",
        "Die Zellzaehlung ist eine grobe Selbstpruefung, nicht die offizielle "
        "Bewertung; Recall und MAE kommen aus dem geschuetzten Bewertungslauf.",
    ]
    if nicht:
        zeilen += ["", "## Nicht bewertbar", ""]
        for eintrag in nicht:
            zeilen.append(
                f"- `{eintrag['record_id']}`: {eintrag['goldzellen']} Goldzellen, "
                f"Status {eintrag['status']}, {eintrag['zellen_neu']} Zellen. "
                "Zaehlt nicht in Rettungsquote oder Golddeckung, jede vorhergesagte "
                "Zelle waere ohne Trefferflaeche."
            )
    gerettet = [e for e in bewertbar if e["status"] == "gerettet"]
    if gerettet:
        zeilen += [
            "",
            "## Gerettete Records",
            "",
            "| Record | Zellen | Goldzellen | adressiert | wertgleich | Tokens neu |",
            "|---|---|---|---|---|---|",
        ]
        for e in gerettet:
            zeilen.append(
                f"| `{e['record_id']}` | {e['zellen_neu']} | {e['goldzellen']} | "
                f"{e['adressiert']} | {e['wertgleich']} | {e['tokens_neu']} |"
            )
    offen = [e for e in bewertbar if e["status"] in {"weiter_ausfall", "fertig_ohne_zellen", "fehlt"}]
    if offen:
        zeilen += [
            "",
            "## Nicht gerettet",
            "",
            "| Record | Status | Klasse neu | Tokens neu | Reasoning-Zeichen |",
            "|---|---|---|---|---|",
        ]
        for e in offen:
            zeilen.append(
                f"| `{e['record_id']}` | {e['status']} | {e['fehlerklasse_neu'] or '-'} | "
                f"{e['tokens_neu']} | {e['reasoning_chars_neu']} |"
            )
    return "\n".join(zeilen) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neu", default=str(NEU))
    parser.add_argument("--alt", default=str(ALT))
    parser.add_argument("--records", default=str(RECORDS))
    parser.add_argument("--modell", default=MODELL)
    parser.add_argument("--json", default=str(BENCH / "iterativ" / "ergebnisse" / "p5_auswertung_20261118.json"))
    parser.add_argument("--md", default=str(BENCH / "iterativ" / "ergebnisse" / "p5_auswertung_20261118.md"))
    args = parser.parse_args()

    neu_pfad = Path(args.neu)
    if not neu_pfad.exists():
        print(f"Lauf liegt noch nicht vor: {neu_pfad}")
        print("Erst `yun_full/bereite_p5_vor.py` (Auswahl) und dann den Lauf selbst starten.")
        return 2

    records = {r["record_id"]: r for r in lade(Path(args.records))}
    werte = auswerten(lade(Path(args.alt)), lade(neu_pfad), records, args.modell)
    if not werte["ausfallzeilen"]:
        print(f"FEHLER: keine {KLASSE}-Zeilen in {args.alt}")
        return 2

    text = bericht(werte, str(neu_pfad), Path(args.alt).resolve() == neu_pfad.resolve())
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(werte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.md).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
