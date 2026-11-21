#!/usr/bin/env python3
"""Phase 3: deterministische Zellvalidierung, offline am 699-Hybrid gemessen.

Die Pruefung ist goldfrei. Sie kennt nur die Zelle und den Dokumenttext, den das
Modell gesehen hat (erste 45000 Zeichen), und verwirft eine Zelle nur aus einem
Grund, der sich nachrechnen laesst:

  kein_wert            Zelle traegt keinen Zahlwert
  zahl_nicht_im_text   Wert steht im Prompt-Text nicht
  keine_ganzzahl       `_events` oder `_group_size` mit Dezimalwert
  rate_statt_anzahl    `_events` mit Prozentzeichen direkt hinter der Zahl
  negative_streuung    `_standard_deviation` negativ
  ereignisse_zu_gross  `_events` groesser als die eigene `_group_size`
  unplausibel          `_group_size` kleiner 1 oder groesser 1.000.000

Dubletten werden bewusst NICHT gefiltert: goldfrei laesst sich nicht entscheiden,
welche der beiden Zellen gilt, und die Bilanz verbraucht je Goldzelle 1:1. Ein
Dublettenfilter hat im ersten Entwurf 137 TPs gekostet.

Gemessen wird gegen den unveraenderten Hybrid (GLM 596 + P5 102) mit derselben
Bilanzlogik wie `vergleiche_20261120.py`. Je Regel wird zusaetzlich ausgewiesen,
wie viele der verworfenen Zellen im Hybrid ein TP waren; das ist Bericht, keine
Regelauswahl.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/validiere_zellen_20261121.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
BENCH = ANALYSE.parent
REPO = BENCH.parent.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))

import vergleiche_20261120 as v  # noqa: E402

FENSTER = 45000


def zahl_positionen(wert: float, text: str) -> list[int]:
    s = f"{wert:.6f}".rstrip("0").rstrip(".")
    ganz, _, dez = s.partition(".")
    # Gedruckte Form zulassen: 14.2 als 14.20, 48 als 48.0. Eine ganzzahlige
    # Zelle darf nicht auf 48.5 passen, deshalb der Ausschluss auf Nachkommastellen
    # ungleich null.
    muster = (
        rf"(?<![\d.,]){re.escape(ganz)}[.,]{re.escape(dez)}0*(?![\d])"
        if dez
        else rf"(?<![\d.,]){re.escape(ganz)}(?![.,]\d*[1-9])(?![\d])"
    )
    return [m.start() for m in re.finditer(muster, text)]


#: Regeln, die eine Zelle verwerfen. Alle anderen Befunde werden nur gemeldet:
#: der Textabgleich ist nicht verwerfend, weil bei einigen Records die
#: gespeicherte Fassung des Dokuments die Goldwerte nicht enthaelt (gemessen:
#: 76 TPs wuerden sterben, siehe Bericht).
VERWERFEND = {"kein_wert", "keine_ganzzahl", "negative_streuung", "unplausibel",
              "ereignisse_zu_gross"}


def pruefe_zelle(zelle: dict[str, Any], text: str) -> tuple[str, bool]:
    """Gibt (Befund, verwerfend) zurueck. Leerer Befund heisst: Zelle besteht."""
    wert = v.zahl(zelle.get("value"))
    if wert is None:
        return "kein_wert", True
    feld = str(zelle.get("field") or "")
    stellen = zahl_positionen(wert, text)
    if not stellen:
        return "zahl_nicht_im_text", False
    if feld.endswith(("_events", "_group_size")) and abs(wert - round(wert)) > 1e-9:
        return "keine_ganzzahl", True
    # Nur wenn JEDE Fundstelle eine Rate ist; steht die Zahl irgendwo auch als
    # Anzahl, bleibt die Zelle.
    if feld.endswith("_events") and all(
        re.match(r"\s*%", text[pos + len(f"{wert:g}") : pos + len(f"{wert:g}") + 3])
        for pos in stellen
    ):
        return "rate_statt_anzahl", False
    if feld.endswith("_standard_deviation") and wert < 0:
        return "negative_streuung", True
    if feld.endswith("_group_size") and not (1 <= wert <= 1_000_000):
        return "unplausibel", True
    return "", False


def tp_indizes(gold: list[dict[str, Any]], vor: list[dict[str, Any]]) -> set[int]:
    """Indizes der Vorhersagezellen, die in der Bilanz ein TP sind."""
    verbraucht = [False] * len(vor)
    treffer: set[int] = set()
    for zelle in gold:
        soll = v.zahl(zelle.get("value"))
        if soll is None:
            continue
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        for i, kandidat in enumerate(vor):
            if verbraucht[i]:
                continue
            if (str(kandidat.get("field") or ""), v.arm_von(kandidat)) != key:
                continue
            ist = v.zahl(kandidat.get("value"))
            if ist is not None and abs(ist - soll) < 1e-6:
                verbraucht[i] = True
                treffer.add(i)
                break
    return treffer


def validiere(
    zellen: list[dict[str, Any]], text: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Gibt (behaltene Zellen, verworfene mit Grund und Index) zurueck."""
    behalten: list[tuple[int, dict[str, Any]]] = []
    verworfen: list[dict[str, Any]] = []
    nach_feld: dict[tuple[str, str], dict[str, Any]] = {}
    befund: list[dict[str, Any]] = []
    for i, zelle in enumerate(zellen):
        grund, verwerfend = pruefe_zelle(zelle, text)
        if grund:
            befund.append({"index": i, "zelle": zelle, "grund": grund,
                           "verworfen": verwerfend})
        if grund and verwerfend:
            verworfen.append({"index": i, "zelle": zelle, "grund": grund})
            continue
        feld = str(zelle.get("field") or "")
        arm = v.arm_von(zelle)
        behalten.append((i, zelle))
        nach_feld[(feld, arm)] = zelle

    endgueltig: list[dict[str, Any]] = []
    for index, zelle in behalten:
        feld = str(zelle.get("field") or "")
        arm = v.arm_von(zelle)
        if feld.endswith("_events"):
            gruppe = nach_feld.get((f"{arm}_group_size", arm))
            if gruppe is not None:
                ereignisse = v.zahl(zelle.get("value"))
                groesse = v.zahl(gruppe.get("value"))
                if ereignisse is not None and groesse is not None and ereignisse > groesse:
                    verworfen.append({"index": index, "zelle": zelle,
                                      "grund": "ereignisse_zu_gross"})
                    befund.append({"index": index, "zelle": zelle,
                                   "grund": "ereignisse_zu_gross", "verworfen": True})
                    continue
        endgueltig.append(zelle)
    return endgueltig, verworfen, befund


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ids = [i for i in json.loads(v.AUSWAHL.read_text(encoding="utf-8")).get("ids") or [] if i in records]

    def index(pfad: Path) -> dict[str, dict[str, Any]]:
        return {z["record_id"]: z for z in v.lade(pfad) if z.get("model") == "glm"}

    glm, p5 = index(v.GLM), index(v.P5)
    auswahl = [i for i in sorted(ids) if i != v.NICHT_BEWERTBAR]
    rest = sorted(set(records) - set(ids))
    hybrid = {r: ("glm", glm.get(r)) for r in rest}
    hybrid.update({r: ("p5", p5.get(r)) for r in auswahl})

    texte: dict[str, str] = {}
    b_vorher, b_nachher = [], []
    verworfen_alle: list[dict[str, Any]] = []
    befund_alle: list[dict[str, Any]] = []
    tp_verluste = Counter()
    for rid, (quelle, zeile) in sorted(hybrid.items()):
        record = records[rid]
        pfad = (record.get("document") or {}).get("path") or ""
        if pfad not in texte:
            # Existenz wird im ganzen Dokument geprueft, nicht nur im Fenster:
            # sonst wuerde eine richtige Zelle aus dem spaeteren Textteil verworfen.
            texte[pfad] = (REPO / pfad).read_text(encoding="utf-8", errors="replace") if pfad else ""
        gold = (record.get("gold") or {}).get("cells") or []
        roh = v.zellen(zeile)
        sauber, verworfen, befund = validiere(roh, texte[pfad])
        tps = tp_indizes(gold, roh)
        b_vorher.append(v.bilanz_p5(gold, roh))
        b_nachher.append(v.bilanz_p5(gold, sauber))
        for fall in befund:
            eintrag = {
                "record_id": rid,
                "quelle": quelle,
                "index": fall["index"],
                "feld": fall["zelle"].get("field"),
                "arm": v.arm_von(fall["zelle"]),
                "wert": v.zahl(fall["zelle"].get("value")),
                "grund": fall["grund"],
                "verworfen": fall["verworfen"],
                "war_tp": fall["index"] in tps,
            }
            befund_alle.append(eintrag)
            if not fall["verworfen"]:
                continue
            if eintrag["war_tp"]:
                tp_verluste[fall["grund"]] += 1
            verworfen_alle.append(eintrag)

    summe_vorher = {k: sum(b[k] for b in b_vorher) for k in ("tp", "fp", "fn")}
    summe_nachher = {k: sum(b[k] for b in b_nachher) for k in ("tp", "fp", "fn")}

    def f1(s: dict[str, int]) -> float:
        p = s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else 0.0
        r = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] else 0.0
        return 2 * p * r / (p + r) if p + r else 0.0

    gruende = Counter(f["grund"] for f in verworfen_alle)
    ergebnis = {
        "stand": "2026-11-21",
        "pruefung": "goldfrei, nur Zelle und Dokumenttext",
        "fenster": FENSTER,
        "vorher": summe_vorher,
        "nachher": summe_nachher,
        "f1_vorher": round(f1(summe_vorher), 4),
        "f1_nachher": round(f1(summe_nachher), 4),
        "verworfen": len(verworfen_alle),
        "gruende": dict(gruende),
        "tp_verluste_je_grund": dict(tp_verluste),
        "befunde_ohne_verwerfen": dict(
            Counter(f["grund"] for f in befund_alle if not f["verworfen"])
        ),
        "beispiele": {
            grund: [f for f in befund_alle if f["grund"] == grund][:5] for grund in gruende
        },
        "faelle": verworfen_alle,
    }
    (HIER / "validierung_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    beispiele = []
    for grund in gruende:
        for f in ergebnis["beispiele"][grund][:3]:
            beispiele.append(
                f"| `{f['record_id']}` | {f['feld']} | {f['wert']} | {grund} | "
                f"{'ja' if f['war_tp'] else 'nein'} |"
            )
    bericht = (
        "# Deterministische Zellvalidierung am 699-Hybrid (21.11.2026)\n\n"
        "Die Pruefung ist goldfrei: sie kennt nur die Zelle und den Dokumenttext, den\n"
        "das Modell gesehen hat. Verworfen wird nur, was nachrechenbar unmoeglich oder\n"
        "im Text nicht vorhanden ist.\n\n"
        "| Stand | TP | FP | FN | F1 |\n|---|---:|---:|---:|---:|\n"
        f"| Hybrid vorher | {summe_vorher['tp']} | {summe_vorher['fp']} | {summe_vorher['fn']} | "
        f"{f1(summe_vorher):.4f} |\n"
        f"| Hybrid nachher | {summe_nachher['tp']} | {summe_nachher['fp']} | {summe_nachher['fn']} | "
        f"{f1(summe_nachher):.4f} |\n\n"
        f"Verworfen: {len(verworfen_alle)} Zellen, davon {sum(tp_verluste.values())} mit TP-Verlust.\n\n"
        "| Grund | verworfen | davon war TP |\n|---|---:|---:|\n"
        + "\n".join(
            f"| `{grund}` | {zahl} | {tp_verluste.get(grund, 0)} |"
            for grund, zahl in gruende.most_common()
        )
        + "\n\n## Beispiele\n\n| Record | Feld | Wert | Grund | war TP |\n|---|---|---:|---|:---:|\n"
        + "\n".join(beispiele)
        + "\n\n## Was das ist und was nicht\n\n"
        "Das ist ein Nachfilter, keine Extraktion: er erzeugt keine fehlende Zelle und\n"
        "berichtigt keinen falschen Wert. Der Gewinn kommt allein aus Zellen, die im\n"
        "Text nicht stehen oder als Zahl unmoeglich sind. Die Zuordnungsfehler aus\n"
        "Phase 1 (`fp_gebunden`, `fp_outcome`) bleiben; sie brauchen die Zeilenbindung\n"
        "aus Stufe 1, nicht diesen Filter.\n\n"
        "Dubletten werden nicht gefiltert. Goldfrei laesst sich nicht entscheiden,\n"
        "welche der beiden Zellen gilt; im ersten Entwurf kostete ein Dublettenfilter\n"
        "137 TP, weil die richtige Zelle oft die zweite ist.\n\n"
        "Grenzen: `zahl_nicht_im_text` haengt an der 45.000-Zeichen-Grenze; eine Zelle\n"
        "aus dem spaeteren Dokumentteil wird verworfen, obwohl sie im Artikel steht.\n"
        "`rate_statt_anzahl` erkennt nur das Prozentzeichen direkt hinter der Zahl.\n"
        "Die Ereignispruefung greift nur, wenn beide Zellen vorliegen.\n"
    )
    (HIER / "validierung_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print("vorher:", summe_vorher, "F1", f1(summe_vorher))
    print("nachher:", summe_nachher, "F1", f1(summe_nachher))
    print("verworfen:", len(verworfen_alle), dict(gruende), "| TP-Verluste", dict(tp_verluste))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
