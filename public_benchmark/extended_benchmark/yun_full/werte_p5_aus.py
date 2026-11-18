"""Wertet den P5-Lauf gegen die Ausfallzeilen der Lesekopie aus.

Stellt die Zeilen aus `runs/yun699_p5_24000_20261118/predictions.jsonl` je
`record_id` gegen die 103 `length_ohne_ergebnis`-Zeilen der Lesekopie und zaehlt
je Record: gerettet oder nicht, Zellen vorher/nachher, und wie viele der
Goldzellen adressiert werden. `yun2024:653` hat keine Goldzellen und wird als
nicht bewertbar getrennt gefuehrt.

Die Zellzaehlung ist eine grobe Selbstpruefung (Feld und Arm, Wertvergleich mit
1e-6), **nicht** die offizielle Bewertung; die kommt aus dem geschuetzten
Bewertungslauf und wird hier nicht nachgebaut. Sie wird zweimal gezaehlt: einmal
nur ueber Feld und Arm und einmal zusaetzlich ueber einen eindeutigen Zeitpunkt
je Feld und Arm, weil die grosszuegige Variante Rettungen zu gut aussehen laesst.

Vor dem ersten Lesen prueft das Skript die Erfolgsmarke der Positivkontrolle
(`iterativ/kontrolle/p5_positivkontrolle/ok.json`, Alter hoechstens 600 s). Fehlt
sie, ist sie alt oder meldet sie keinen Erfolg, endet das Skript mit Exit 3 und
schreibt keinen Bericht. Es gibt keinen Schalter, der das umgeht.

Aufruf:
    bash yun_full/werte_p5_mit_kontrolle.sh                    # Kontrolle + Auswertung
    python yun_full/werte_p5_aus.py                            # nur mit frischer Marke
    python yun_full/werte_p5_aus.py --neu <predictions.jsonl>
    python yun_full/werte_p5_aus.py --neu <lesekopie>          # Nullprobe
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
# Erfolgsmarke der Positivkontrolle. Ohne frische Marke schreibt dieses Skript
# keinen Bericht: ein Bericht aus einer ungepruefften Rechnung waere schlimmer
# als kein Bericht.
MARKE = BENCH / "iterativ" / "kontrolle" / "p5_positivkontrolle" / "ok.json"
MARKE_MAX_ALTER = 600


def pruefe_marke(
    pfad: str | Path | None = None,
    max_alter_s: int = MARKE_MAX_ALTER,
    jetzt: float | None = None,
    nonce: str | None = None,
) -> tuple[bool, str]:
    """Ist die Positivkontrolle frisch und erfolgreich belegt?

    Fail-closed: fehlende, unlesbare, erfolglose, zu alte oder datierte Marken
    gelten als nicht belegt. Ist `nonce` gesetzt, muss die Marke denselben Wert
    tragen — damit kann eine Marke aus einem anderen Lauf keine Auswertung
    autorisieren.
    """
    ziel = Path(pfad) if pfad else MARKE
    if not ziel.exists():
        return False, f"keine Marke ({ziel})"
    try:
        daten = json.loads(ziel.read_text(encoding="utf-8"))
        alter = (jetzt or time.time()) - ziel.stat().st_mtime
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Marke nicht lesbar: {exc}"
    if not isinstance(daten, dict) or daten.get("ok") is not True:
        return False, "Marke meldet keinen Erfolg"
    if nonce is not None and str(daten.get("nonce") or "") != nonce:
        return False, "Marke gehoert zu einem anderen Lauf (Nonce passt nicht)"
    if alter > max_alter_s:
        return False, f"Marke ist {alter:.0f} s alt (Grenze {max_alter_s} s)"
    if alter < -60:
        return False, "Marke liegt in der Zukunft"
    return True, f"Marke gueltig ({alter:.0f} s alt)"


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


def zeitpunkt(zelle: dict[str, Any]) -> str:
    """Zeitpunkt als Vergleichsschluessel: klein, ein Leerzeichen, leer heisst `ohne`.

    Bewusst nur Normalisierung, keine Umschreibung: "1 month" und "30 days"
    bleiben verschieden, weil eine Umrechnung geraten waere.
    """
    text = str(zelle.get("timepoint") or "").strip().lower()
    return " ".join(text.split()) or "ohne"


def mehrdeutig(vorhergesagt: list[dict[str, Any]]) -> int:
    """Anzahl der Feld/Arm-Gruppen, die mehr als einen Zeitpunkt nennen."""
    gruppen: dict[tuple[str, str], set[str]] = {}
    for zelle in vorhergesagt:
        gruppen.setdefault(schluessel(zelle), set()).add(zeitpunkt(zelle))
    return sum(1 for werte in gruppen.values() if len(werte) > 1)


def _deckung(
    gold: list[dict[str, Any]],
    vorhergesagt: list[dict[str, Any]],
    streng: bool = False,
) -> tuple[int, int]:
    """(adressiert, wertgleich) ueber die Goldzellen; Schluessel ist Feld plus Arm.

    Das Gold traegt je Zelle keinen Zeitpunkt (in Yun-699: 0 von 2.773), ein
    Vergleich Gold gegen Vorhersage ist also nicht moeglich. Mit `streng` wird
    deshalb geprueft, was am Material pruefbar ist: die Vorhersage muss fuer Feld
    und Arm **einen einzigen** Zeitpunkt nennen. Streut sie denselben Schluessel
    ueber mehrere Zeitpunkte, ist der Treffer nicht eindeutig zuzuordnen und
    zaehlt nicht.
    """
    nach_schluessel: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for zelle in vorhergesagt:
        nach_schluessel.setdefault(schluessel(zelle), []).append(zelle)
    adressiert = wertgleich = 0
    for zelle in gold:
        kandidaten = nach_schluessel.get(schluessel(zelle), [])
        if not kandidaten:
            continue
        if streng and len({zeitpunkt(k) for k in kandidaten}) > 1:
            continue
        adressiert += 1
        soll = zahl(zelle.get("value"))
        if soll is None:
            continue
        if any((ist := zahl(k.get("value"))) is not None and abs(ist - soll) < 1e-6 for k in kandidaten):
            wertgleich += 1
    return adressiert, wertgleich


def deckung(gold: list[dict[str, Any]], vorhergesagt: list[dict[str, Any]]) -> tuple[int, int]:
    """(adressiert, wertgleich) ueber Feld und Arm — ohne Zeitpunkt, also grosszuegig."""
    return _deckung(gold, vorhergesagt)


def deckung_mit_zeitpunkt(
    gold: list[dict[str, Any]], vorhergesagt: list[dict[str, Any]]
) -> tuple[int, int]:
    """Wie `deckung`, verlangt aber einen eindeutigen Zeitpunkt je Feld und Arm."""
    return _deckung(gold, vorhergesagt, streng=True)


def status(zeile: dict[str, Any] | None) -> str:
    if zeile is None:
        return "fehlt"
    # "ok" ist die Transportklasse einer angekommenen Antwort und kein Ausfall.
    klasse = str(zeile.get("fehlerklasse") or "").strip().lower()
    if bool(zeile.get("failed")) or (klasse and klasse != "ok"):
        return "weiter_ausfall"
    return "gerettet" if zellen(zeile) else "fertig_ohne_zellen"


def auswerten(
    alt_zeilen: list[dict[str, Any]],
    neu_zeilen: list[dict[str, Any]],
    records: dict[str, dict[str, Any]],
    modell: str = MODELL,
    ids: list[str] | None = None,
) -> dict[str, Any]:
    """Vergleicht die P5-Zeilen mit den Ausfallzeilen der Lesekopie.

    Grundgesamtheit ist die P5-Auswahl (`ids`), sonst wie bisher alle
    `KLASSE`-Zeilen. Die Zeilen selbst werden **nicht** nach Klasse gefiltert,
    damit die Auswertung nach der urspruenglichen Fehlerklasse gruppieren kann.
    """
    alle_alt = {z["record_id"]: z for z in alt_zeilen if z.get("model") == modell}
    if ids is not None:
        grund = [rid for rid in ids if rid in alle_alt]
        ohne_altzeile = [rid for rid in ids if rid not in alle_alt]
    else:
        grund = [rid for rid in sorted(alle_alt) if alle_alt[rid].get("fehlerklasse") == KLASSE]
        ohne_altzeile = []
    alt = {rid: alle_alt[rid] for rid in grund}
    neu = {z["record_id"]: z for z in neu_zeilen if z.get("model") == modell}

    bewertbar: list[dict[str, Any]] = []
    nicht_bewertbar: list[dict[str, Any]] = []
    for rid in sorted(alt):
        gold = list(((records.get(rid) or {}).get("gold") or {}).get("cells") or [])
        neu_zeile = neu.get(rid)
        vorher = zellen(alt[rid])
        nachher = zellen(neu_zeile)
        adressiert, wertgleich = deckung(gold, nachher)
        adressiert_zp, wertgleich_zp = deckung_mit_zeitpunkt(gold, nachher)
        eintrag = {
            "record_id": rid,
            "status": status(neu_zeile),
            "fehlerklasse_alt": alt[rid].get("fehlerklasse") or "ohne Klasse",
            "fehlerklasse_neu": (neu_zeile or {}).get("fehlerklasse", ""),
            "zellen_alt": len(vorher),
            "zellen_neu": len(nachher),
            "zellgewinn": len(nachher) - len(vorher),
            "goldzellen": len(gold),
            "adressiert": adressiert,
            "wertgleich": wertgleich,
            "adressiert_zeitpunkt": adressiert_zp,
            "wertgleich_zeitpunkt": wertgleich_zp,
            "goldzellen_mit_zeitpunkt": sum(1 for z in gold if zeitpunkt(z) != "ohne"),
            "zellen_neu_mit_zeitpunkt": sum(1 for z in nachher if zeitpunkt(z) != "ohne"),
            "zeitpunkt_mehrdeutig": mehrdeutig(nachher),
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

    alle = bewertbar + nicht_bewertbar

    # Drei Stufen, ausdruecklich getrennt: Antwort da, verwertbar, inhaltlich richtig.
    stufen = {
        "ids": len(alle),
        "technisch": sum(1 for e in alle if e["status"] in {"gerettet", "fertig_ohne_zellen"}),
        "auswertbar": sum(1 for e in alle if e["zellen_neu"] > 0),
        "inhaltlich": sum(1 for e in bewertbar if e["wertgleich"] > 0),
        "inhaltlich_zeitpunkt": sum(1 for e in bewertbar if e["wertgleich_zeitpunkt"] > 0),
    }

    # Aufteilung nach der Fehlerklasse aus der Lesekopie, nicht nach der neuen.
    nach_klasse: dict[str, dict[str, Any]] = {}
    for eintrag in alle:
        klasse = eintrag["fehlerklasse_alt"]
        werte = nach_klasse.setdefault(
            klasse,
            {
                "ids": 0,
                "technisch": 0,
                "auswertbar": 0,
                "leer": 0,
                "weiter_ausfall": 0,
                "fehlt": 0,
                "goldzellen": 0,
                "adressiert": 0,
                "wertgleich": 0,
                "adressiert_zeitpunkt": 0,
                "wertgleich_zeitpunkt": 0,
            },
        )
        werte["ids"] += 1
        werte["technisch"] += 1 if eintrag["status"] in {"gerettet", "fertig_ohne_zellen"} else 0
        werte["auswertbar"] += 1 if eintrag["zellen_neu"] > 0 else 0
        werte["leer"] += 1 if eintrag["status"] == "fertig_ohne_zellen" else 0
        werte["weiter_ausfall"] += 1 if eintrag["status"] == "weiter_ausfall" else 0
        werte["fehlt"] += 1 if eintrag["status"] == "fehlt" else 0
        werte["goldzellen"] += eintrag["goldzellen"]
        werte["adressiert"] += eintrag["adressiert"]
        werte["wertgleich"] += eintrag["wertgleich"]
        werte["adressiert_zeitpunkt"] += eintrag["adressiert_zeitpunkt"]
        werte["wertgleich_zeitpunkt"] += eintrag["wertgleich_zeitpunkt"]

    return {
        "modell": modell,
        "grundgesamtheit": len(alt),
        "ids_ohne_altzeile": ohne_altzeile,
        "bewertbar": bewertbar,
        "nicht_bewertbar": nicht_bewertbar,
        "status": zaehlung,
        "stufen": stufen,
        "nach_klasse": nach_klasse,
        "zellen_alt": summe(bewertbar + nicht_bewertbar, "zellen_alt"),
        "zellen_neu": summe(bewertbar + nicht_bewertbar, "zellen_neu"),
        "zellgewinn": summe(bewertbar + nicht_bewertbar, "zellgewinn"),
        "goldzellen_bewertbar": summe(bewertbar, "goldzellen"),
        "adressiert": summe(bewertbar, "adressiert"),
        "wertgleich": summe(bewertbar, "wertgleich"),
        "adressiert_zeitpunkt": summe(bewertbar, "adressiert_zeitpunkt"),
        "wertgleich_zeitpunkt": summe(bewertbar, "wertgleich_zeitpunkt"),
        "goldzellen_mit_zeitpunkt": summe(bewertbar, "goldzellen_mit_zeitpunkt"),
        # Ueber alle Records, damit die Zeile zur Gesamtzahl der Zellen passt
        # (`zellen_neu` zaehlt ebenfalls alle, auch die ohne Gold).
        "zellen_neu_mit_zeitpunkt": summe(bewertbar + nicht_bewertbar, "zellen_neu_mit_zeitpunkt"),
        "zeitpunkt_mehrdeutig": summe(bewertbar, "zeitpunkt_mehrdeutig"),
        "tokens_neu": summe(bewertbar + nicht_bewertbar, "tokens_neu"),
    }


def bericht(werte: dict[str, Any], neu_pfad: str, nullprobe: bool) -> str:
    s = werte["status"]
    bewertbar = werte["bewertbar"]
    nicht = werte["nicht_bewertbar"]
    zeilen = [
        "# P5-Auswertung: Rettung und Zellgewinn",
        "",
        f"Neu: `{neu_pfad}`. Vergleich: {werte['grundgesamtheit']} IDs der P5-Auswahl "
        f"gegen ihre Zeilen in der Lesekopie, Modell {werte['modell']}.",
        "",
    ]
    if nullprobe:
        zeilen += ["> **Nullprobe:** neu und alt sind dieselbe Datei. Erwartet sind "
                   "0 Rettungen, 0 Zellgewinn und die volle Goldzahl.", ""]
    st = werte["stufen"]
    zeilen += [
        "## Grundgesamtheit",
        "",
        "| Groesse | Wert |",
        "|---|---|",
        f"| adressierte IDs | {st['ids']} |",
        f"| davon bewertbar (Goldzellen vorhanden) | {len(bewertbar)} |",
        f"| davon nicht bewertbar | {len(nicht)} |",
    ]
    if werte.get("ids_ohne_altzeile"):
        zeilen.append(f"| IDs ohne Zeile in der Lesekopie | {len(werte['ids_ohne_altzeile'])} |")
    zeilen += [
        "",
        "Verglichen wird ausschliesslich auf diesen IDs. Fehlt eine Zeile im neuen "
        "Lauf oder im alten, steht das als solcher Status in der Tabelle und wird "
        "nicht als Ausfall oder als Rettung gezaehlt.",
        "",
        "## Status je Record",
        "",
        "| Status | Records |",
        "|---|---|",
        f"| gerettet (Antwort mit Zellen) | {s['gerettet']} |",
        f"| fertig, aber ohne Zellen | {s['fertig_ohne_zellen']} |",
        f"| weiter ausgefallen | {s['weiter_ausfall']} |",
        f"| im neuen Lauf nicht enthalten | {s['fehlt']} |",
        f"| **Antwort technisch erhalten** | **{st['technisch']} von {st['ids']}** |",
        f"| **auswertbar (mindestens eine Zelle)** | **{st['auswertbar']} von {st['ids']}** |",
        "",
        f"Rettungsquote auf den **{len(bewertbar)} bewertbaren** Records: "
        f"**{sum(1 for e in bewertbar if e['status'] == 'gerettet')} von {len(bewertbar)}**"
        + (f" ({sum(1 for e in bewertbar if e['status'] == 'gerettet') / len(bewertbar):.1%})"
           if bewertbar else ""),
        "",
        "## Drei Stufen der Rettung",
        "",
        "| Stufe | Definition | Records |",
        "|---|---|---|",
        f"| 1 technische Rettung | Antwort ohne Fehlerklasse erhalten | {st['technisch']} von {st['ids']} |",
        f"| 2 auswertbar | Antwort enthaelt mindestens eine Zelle | {st['auswertbar']} von {st['ids']} |",
        f"| 3 inhaltliche Rettung | mindestens eine Goldzelle wertgleich (Feld und Arm) | "
        f"{st['inhaltlich']} von {len(bewertbar)} |",
        f"| 3b inhaltlich, streng | zusaetzlich eindeutiger Zeitpunkt | "
        f"{st['inhaltlich_zeitpunkt']} von {len(bewertbar)} |",
        "",
        "Die Stufen sind keine Steigerung derselben Quote: Stufe 1 sagt nur, dass eine "
        "Antwort ankam, Stufe 2 dass sie Zellen enthaelt, Stufe 3 dass ein Wert stimmt. "
        "Die Reparaturschaetzung von 39 % aus der Materialanalyse ist eine Schaetzung "
        "und kein gemessener Erfolg.",
        "",
        "## Nach urspruenglicher Fehlerklasse",
        "",
        "| Klasse alt | IDs | technisch | auswertbar | leer | weiter ausgefallen | Goldzellen | adressiert F/A | adressiert +ZP | wertgleich F/A | wertgleich +ZP |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for klasse, k in sorted(werte["nach_klasse"].items()):
        zeilen.append(
            f"| `{klasse}` | {k['ids']} | {k['technisch']} | {k['auswertbar']} | {k['leer']} | "
            f"{k['weiter_ausfall']} | {k['goldzellen']} | {k['adressiert']} | "
            f"{k['adressiert_zeitpunkt']} | {k['wertgleich']} | {k['wertgleich_zeitpunkt']} |"
        )
    zeilen += [
        "",
        "## Zellen und Gold",
        "",
        "| Groesse | Wert |",
        "|---|---|",
        f"| Zellen vorher (Ausfallzeilen) | {werte['zellen_alt']} |",
        f"| Zellen nachher | {werte['zellen_neu']} |",
        f"| Zellgewinn | {werte['zellgewinn']} |",
        f"| Goldzellen der bewertbaren | {werte['goldzellen_bewertbar']} |",
        f"| davon mit angegebenem Zeitpunkt | {werte['goldzellen_mit_zeitpunkt']} |",
        f"| vorhergesagte Zellen mit Zeitpunkt | {werte['zellen_neu_mit_zeitpunkt']} |",
        f"| adressiert, Feld und Arm (grosszuegig) | {werte['adressiert']} |",
        f"| **adressiert, Feld, Arm und eindeutiger Zeitpunkt** | **{werte['adressiert_zeitpunkt']}** |",
        f"| wertgleich, Feld und Arm (grosszuegig) | {werte['wertgleich']} |",
        f"| **wertgleich, Feld, Arm und eindeutiger Zeitpunkt** | **{werte['wertgleich_zeitpunkt']}** |",
        f"| Feld/Arm-Gruppen mit mehreren Zeitpunkten | {werte['zeitpunkt_mehrdeutig']} |",
        f"| Completion-Tokens neu | {werte['tokens_neu']} |",
        "",
        "Die Zellzaehlung ist eine grobe Selbstpruefung, nicht die offizielle "
        "Bewertung; Recall und MAE kommen aus dem geschuetzten Bewertungslauf.",
        "",
        f"Die grosszuegige Zaehlung erkennt eine Goldzelle schon an Feld und Arm. "
        f"Die fett gesetzte Zaehlung verlangt zusaetzlich einen eindeutigen Zeitpunkt "
        "(normalisiert: Kleinschreibung, ein Leerzeichen, leer gleich `ohne`). Ein "
        "Vergleich Gold-Zeitpunkt gegen Vorhersage-Zeitpunkt ist nicht moeglich: das "
        "Gold traegt je Zelle keinen, und der Record-Zeitpunkt beschreibt in Yun-699 "
        "nur eine Regel.",
        "",
    ]
    if (werte["adressiert"], werte["wertgleich"]) != (
        werte["adressiert_zeitpunkt"],
        werte["wertgleich_zeitpunkt"],
    ):
        zeilen += [
            f"Abweichung: {werte['adressiert'] - werte['adressiert_zeitpunkt']} adressierte und "
            f"{werte['wertgleich'] - werte['wertgleich_zeitpunkt']} wertgleiche Treffer haengen an "
            f"{werte['zeitpunkt_mehrdeutig']} mehrdeutigen Feld/Arm-Gruppen.",
        ]
    else:
        zeilen += [
            f"Beide Zaehlungen stimmen ueberein: keine der {len(werte['bewertbar'])} "
            "bewertbaren Zeilen streut einen Feld/Arm-Schluessel ueber mehrere Zeitpunkte.",
        ]
    zeilen += [
        "",
        f"{werte['zellen_neu_mit_zeitpunkt']} vorhergesagte Zellen tragen einen Zeitpunkt; "
        "das Gold kann ihn weder bestaetigen noch widerlegen.",
    ]
    zeilen += [
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
            "| Record | Zellen | Goldzellen | adressiert F/A | adressiert +eindeutiger ZP | wertgleich F/A | wertgleich +eindeutiger ZP | Tokens neu |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for e in gerettet:
            zeilen.append(
                f"| `{e['record_id']}` | {e['zellen_neu']} | {e['goldzellen']} | "
                f"{e['adressiert']} | {e['adressiert_zeitpunkt']} | {e['wertgleich']} | "
                f"{e['wertgleich_zeitpunkt']} | {e['tokens_neu']} |"
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
    parser.add_argument(
        "--ids-auswahl",
        default=str(BENCH / "iterativ" / "ergebnisse" / "p5_vorbereitung_20261118.json"),
        help="JSON mit der P5-Auswahl; bestimmt die Grundgesamtheit",
    )
    parser.add_argument("--json", default=str(BENCH / "iterativ" / "ergebnisse" / "p5_auswertung_20261118.json"))
    parser.add_argument("--md", default=str(BENCH / "iterativ" / "ergebnisse" / "p5_auswertung_20261118.md"))
    parser.add_argument("--kontrolle-marke", default=str(MARKE))
    parser.add_argument("--kontrolle-max-alter", type=int, default=MARKE_MAX_ALTER)
    parser.add_argument(
        "--kontrolle-nonce",
        default="",
        help="Nonce aus werte_p5_mit_kontrolle.sh; ohne ihn laeuft die Auswertung nicht",
    )
    args = parser.parse_args()

    # Vor jedem Lesen und Schreiben: ohne belegte Positivkontrolle kein Bericht.
    if not args.kontrolle_nonce:
        print(
            "ABBRUCH: kein Kontroll-Nonce uebergeben. Die Auswertung laeuft nur ueber "
            "`yun_full/werte_p5_mit_kontrolle.sh`, damit die Positivkontrolle bei jedem "
            "Bericht wirklich gelaufen ist.",
            file=sys.stderr,
        )
        return 3
    marke_ok, marke_text = pruefe_marke(
        args.kontrolle_marke, args.kontrolle_max_alter, nonce=args.kontrolle_nonce
    )
    if not marke_ok:
        print(
            f"ABBRUCH: Positivkontrolle nicht belegt ({marke_text}). "
            "Kein Bericht geschrieben; erst `yun_full/werte_p5_mit_kontrolle.sh` laufen lassen.",
            file=sys.stderr,
        )
        return 3

    neu_pfad = Path(args.neu)
    if not neu_pfad.exists():
        print(f"Lauf liegt noch nicht vor: {neu_pfad}")
        print("Erst `yun_full/bereite_p5_vor.py` (Auswahl) und dann den Lauf selbst starten.")
        return 2

    records = {r["record_id"]: r for r in lade(Path(args.records))}
    ids: list[str] | None = None
    auswahl = Path(args.ids_auswahl)
    if auswahl.exists():
        ids = list(json.loads(auswahl.read_text(encoding="utf-8")).get("ids") or [])
    werte = auswerten(lade(Path(args.alt)), lade(neu_pfad), records, args.modell, ids=ids)
    if not werte["grundgesamtheit"]:
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
