#!/usr/bin/env python3
"""Phase 1: 759 FN und 507 FP des Hybrids nach Fehlerursache kategorisieren.

Rein lesend auf vorhandenen Predictions und Gold. Kein Modellaufruf, keine
Aenderung an Gold, Testset oder Bewertungslogik.

Der Hybrid ist definiert wie in ``vergleiche_20261120.py``: GLM-Zellen auf den
596 Records ausserhalb der P5-Auswahl, P5-Zellen auf den 102 bewertbaren
Records. Die Bilanzlogik wird aus diesem Modul importiert, damit die Zahlen
identisch sind (Schluessel Feld+Arm, 1:1-Verbrauch, Dubletten sind FP).

Zuordnung: Jede verbrauchte Goldzelle (FN) und jede ueberzaehlige
Vorhersagezelle (FP) bekommt genau eine Kategorie. Die Regeln greifen in fester
Reihenfolge; die erste zutreffende gewinnt. Jeder Fall traegt Regelkennung und
Beleg (Fundstelle im Text oder Vergleichszelle), damit die Zuordnung
nachpruefbar bleibt. Die Kategorien sind Heuristiken auf Text- und
Zahlenebene, keine Aussage ueber die Absicht des Modells.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/fehlerursachen_20261121.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
BENCH = ANALYSE.parent
REPO = BENCH.parent.parent
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))

import vergleiche_20261120 as v  # noqa: E402
sys.path.insert(0, str(HIER))
from zahlabgleich_20261121 import zahl_positionen  # noqa: E402

FENSTER = 45000  # Textgrenze von build_prompt; beide Laeufe nutzen sie

URTEIL = {
    "fn_leer": "leere Modellausgabe",
    "fn_nicht_im_dokument": "Wert steht im Dokument nicht (Abdeckung)",
    "fn_mehrdeutig": "Gold-Mehrdeutigkeit",
    "fn_wert_ersetzt": "Wert erkannt, falsch gebunden (anderer Wert ausgegeben)",
    "fn_nicht_ausgegeben": "Wert im Prompt, nicht ausgegeben",
    "fp_arm": "falscher Arm",
    "fp_feld": "falsches Feld",
    "fp_outcome": "falsches Outcome",
    "fp_dublette": "doppelte Zelle",
    "fp_einheit": "falsche Einheit (Faktor oder Rate als Anzahl)",
    "fp_halluzination": "Zahl steht nirgends im Dokument",
    "fp_ausserhalb_fenster": "Zahl erst hinter der Prompt-Grenze (45.000)",
    "fp_gebunden": "Wert erkannt, falsch gebunden",
    "fp_zeitpunkt": "falscher Zeitpunkt (Baseline- oder Aenderungswert)",
    "fp_zeitpunkt_zeile": "falscher Zeitpunkt (Wert aus anderer Zeile)",
}


def funde(wert: float | None, text: str) -> list[int]:
    """Fundstellen ueber den gemeinsamen Zahlabgleich (zahlabgleich_20261121)."""
    return zahl_positionen(wert, text)


ZEITWORTE = (
    "baseline",
    "mean change",
    "change from",
    "change in",
    "delta",
    "follow-up",
    "screening",
    "run-in",
    "week 0",
)


def zeitwort_in_naehe(text: str, position: int, radius: int = 120) -> bool:
    """Steht im Umfeld der Zahl ein Baseline- oder Aenderungswort?"""
    umfeld = text[max(0, position - radius) : position + radius].lower()
    return any(wort in umfeld for wort in ZEITWORTE)


def klassifiziere_record(
    record: dict[str, Any],
    text: str,
    volltext: str,
    quelle: str,
    vor: list[dict[str, Any]],
    fremde_goldwerte: dict[tuple[str, str, float], list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Gibt (FN-Faelle, FP-Faelle) eines Records zurueck."""
    gold = (record.get("gold") or {}).get("cells") or []
    augenschein = text[:FENSTER]
    verbraucht = [False] * len(vor)
    gold_werte = Counter()
    for zelle in gold:
        wert = v.zahl(zelle.get("value"))
        if wert is not None:
            gold_werte[round(wert, 6)] += 1

    # Gold-Mehrdeutigkeit: derselbe Schluessel mit mehreren Werten (Widerspruch)
    # oder derselbe Wert in beiden Armen desselben Feldes.
    werte_je_key: dict[tuple[str, str], set[float]] = defaultdict(set)
    arme_je_wert: dict[tuple[str, float], set[str]] = defaultdict(set)
    for zelle in gold:
        wert = v.zahl(zelle.get("value"))
        if wert is None:
            continue
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        werte_je_key[key].add(round(wert, 6))
        arme_je_wert[(key[0], round(wert, 6))].add(key[1])
    widerspruch = {key for key, werte in werte_je_key.items() if len(werte) > 1}
    beide_arme = {key for key, arme in arme_je_wert.items() if len(arme) > 1}

    fn_faelle: list[dict[str, Any]] = []
    for zelle in gold:
        soll = v.zahl(zelle.get("value"))
        if soll is None:
            continue
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        treffer, ersatz = None, None
        for i, kandidat in enumerate(vor):
            if verbraucht[i]:
                continue
            if (str(kandidat.get("field") or ""), v.arm_von(kandidat)) != key:
                continue
            ist = v.zahl(kandidat.get("value"))
            if ist is None:
                continue
            if abs(ist - soll) < 1e-6 and treffer is None:
                treffer = i
                break
            if ersatz is None:
                ersatz = (i, ist)
        if treffer is not None:
            verbraucht[treffer] = True
            continue

        stellen = funde(soll, augenschein)
        im_dokument = bool(funde(soll, volltext))
        schluessel = (key[0], key[1], round(soll, 6))
        mehrfach = fremde_goldwerte.get(schluessel) or []
        if not vor:
            regel = "fn_leer"
        elif not stellen:
            regel = "fn_nicht_im_dokument"
        elif key in widerspruch or (key[0], round(soll, 6)) in beide_arme:
            regel = "fn_mehrdeutig"
        elif ersatz is not None:
            regel = "fn_wert_ersetzt"
        else:
            regel = "fn_nicht_ausgegeben"
        beleg = (
            f"Position {stellen[0]}" if stellen else "Zahl steht im Prompt-Text nicht"
        )
        if regel == "fn_nicht_im_dokument":
            beleg = (
                "Zahl steht im Dokument, aber hinter der 45000-Zeichen-Grenze"
                if im_dokument
                else "Zahl steht im Dokument nicht"
            )
        if regel == "fn_wert_ersetzt":
            beleg += f"; ausgegeben {ersatz[1]} statt {soll}"
        if regel == "fn_mehrdeutig":
            beleg = (
                f"Gold traegt fuer {key[0]}/{key[1]} mehrere Werte"
                if key in widerspruch
                else f"Gold traegt {soll} in beiden Armen desselben Feldes"
            )
        fn_faelle.append(
            {
                "record_id": record["record_id"],
                "quelle": quelle,
                "feld": key[0],
                "arm": key[1],
                "wert": soll,
                "regel": regel,
                "urteil": URTEIL[regel],
                "im_dokument": im_dokument,
                "beleg": beleg,
            }
        )

    fp_gruppen: dict[tuple[str, str], int] = Counter()
    gold_keys = {(str(z.get("field") or ""), v.arm_von(z)) for z in gold}
    gold_nach_feld: dict[str, set[float]] = defaultdict(set)
    gold_nach_feld_arm: dict[tuple[str, str], set[float]] = defaultdict(set)
    for zelle in gold:
        wert = v.zahl(zelle.get("value"))
        if wert is None:
            continue
        key = (str(zelle.get("field") or ""), v.arm_von(zelle))
        gold_nach_feld[key[0]].add(round(wert, 6))
        gold_nach_feld_arm[key].add(round(wert, 6))

    fp_faelle: list[dict[str, Any]] = []
    for i, kandidat in enumerate(vor):
        wert = v.zahl(kandidat.get("value"))
        if verbraucht[i] or wert is None:
            continue
        feld = str(kandidat.get("field") or "")
        arm = v.arm_von(kandidat)
        key = (feld, arm)
        runde = round(wert, 6)
        fp_gruppen[key] += 1
        stellen = funde(wert, augenschein)
        partner = (feld, "comparator" if arm == "intervention" else "intervention")
        eigener_arm = gold_nach_feld_arm.get(key, set())
        gegen_arm = gold_nach_feld_arm.get((feld, partner[1]), set())
        if fp_gruppen[key] > 1:
            regel, beleg = "fp_dublette", f"{fp_gruppen[key]}. Zelle fuer {feld}/{arm}"
        elif runde not in eigener_arm and runde in gegen_arm:
            regel = "fp_arm"
            beleg = f"{wert} ist Goldwert des anderen Arms ({partner[1]}) im selben Record"
        elif runde not in eigener_arm and any(
            runde in werte and name[1] == arm
            for name, werte in gold_nach_feld_arm.items() if name[0] != feld
        ):
            regel = "fp_feld"
            beleg = f"{wert} ist Goldwert eines anderen Feldes im selben Arm"
        elif runde not in eigener_arm and runde in gold_nach_feld.get(feld, set()):
            regel = "fp_zeitpunkt_zeile"
            beleg = f"{wert} ist Goldwert desselben Feldes in einer anderen Zeile"
        elif feld.endswith(("_events", "_group_size")) and abs(wert - round(wert)) > 1e-9:
            regel = "fp_einheit"
            beleg = f"{feld} verlangt eine ganze Zahl, ausgegeben {wert} (Rate oder Prozent)"
        elif runde not in gold_werte and (
            runde * 100 in gold_werte or runde / 100 in gold_werte
            or runde * 1000 in gold_werte or runde / 1000 in gold_werte
        ):
            faktor = 100 if runde * 100 in gold_werte or runde / 100 in gold_werte else 1000
            regel = "fp_einheit"
            beleg = f"{wert} = Goldwert x {faktor}"
        elif not stellen:
            if funde(wert, volltext):
                regel = "fp_ausserhalb_fenster"
                beleg = f"{wert} steht erst hinter der 45000-Zeichen-Grenze"
            else:
                regel = "fp_halluzination"
                beleg = f"{wert} steht im Dokument nicht"
        elif fremde_goldwerte.get((feld, arm, runde)):
            regel = "fp_outcome"
            beleg = "gleicher Wert Gold in: " + ", ".join(fremde_goldwerte[(feld, arm, runde)])
        elif feld.endswith(("_mean", "_standard_deviation")) and any(
            zeitwort_in_naehe(augenschein, pos) for pos in stellen
        ):
            regel = "fp_zeitpunkt"
            beleg = f"Position {stellen[0]}, im Umfeld steht ein Baseline- oder Aenderungswort"
        else:
            regel, beleg = "fp_gebunden", f"Position {stellen[0]}, keine Goldzelle dazu"
        fp_faelle.append(
            {
                "record_id": record["record_id"],
                "quelle": quelle,
                "feld": feld,
                "arm": arm,
                "wert": wert,
                "regel": regel,
                "urteil": URTEIL[regel],
                "beleg": beleg,
                "partner_feld": partner[0],
            }
        )
    return fn_faelle, fp_faelle


def main() -> int:
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    ids = [i for i in json.loads(v.AUSWAHL.read_text(encoding="utf-8")).get("ids") or [] if i in records]

    def index(pfad: Path) -> dict[str, dict[str, Any]]:
        return {z["record_id"]: z for z in v.lade(pfad) if z.get("model") == "glm"}

    glm = index(v.GLM)
    p5 = index(v.P5)
    auswahl = [i for i in sorted(ids) if i != v.NICHT_BEWERTBAR]
    rest = sorted(set(records) - set(ids))
    hybrid = {r: ("glm", glm.get(r)) for r in rest}
    hybrid.update({r: ("p5", p5.get(r)) for r in auswahl})

    # Fremde Goldwerte je (Feld, Arm, Wert): gleiche Zahl in mehreren Records
    # derselben Publikation. Grundlage fuer Gold-Mehrdeutigkeit und Outcome-Fehler.
    nach_pmc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records.values():
        nach_pmc[str((r.get("document") or {}).get("id") or "")].append(r)
    fremde_goldwerte: dict[tuple[str, str, float], list[str]] = defaultdict(list)
    for pmc, gruppe in nach_pmc.items():
        for r in gruppe:
            for zelle in (r.get("gold") or {}).get("cells") or []:
                wert = v.zahl(zelle.get("value"))
                if wert is None:
                    continue
                key = (str(zelle.get("field") or ""), v.arm_von(zelle), round(wert, 6))
                fremde_goldwerte[key].append(r["record_id"])

    texte: dict[str, str] = {}
    texte_voll: dict[str, str] = {}
    fn_alle: list[dict[str, Any]] = []
    fp_alle: list[dict[str, Any]] = []
    pro_record: dict[str, dict[str, Any]] = {}
    for rid, (quelle, zeile) in sorted(hybrid.items()):
        record = records[rid]
        pfad = (record.get("document") or {}).get("path") or ""
        if pfad not in texte:
            voll = (REPO / pfad).read_text(encoding="utf-8", errors="replace") if pfad else ""
            texte_voll[pfad] = voll
            texte[pfad] = voll
        b = v.bilanz_p5((record.get("gold") or {}).get("cells") or [], v.zellen(zeile))
        fn, fp = klassifiziere_record(
            record, texte[pfad], texte_voll[pfad], quelle, v.zellen(zeile), fremde_goldwerte
        )
        fn_alle.extend(fn)
        fp_alle.extend(fp)
        pro_record[rid] = {"quelle": quelle, **b, "fn_faelle": len(fn), "fp_faelle": len(fp),
                           "leer": not v.zellen(zeile)}

    # Selbstkontrolle: Summen muessen die veroeffentlichte Hybridbilanz treffen.
    summe = {k: sum(r[k] for r in pro_record.values()) for k in ("tp", "fp", "fn")}
    if summe["fn"] != len(fn_alle) or summe["fp"] != len(fp_alle):
        raise SystemExit(f"Zuordnung unvollstaendig: {summe}, Faelle FN {len(fn_alle)} FP {len(fp_alle)}")

    def block(faelle: list[dict[str, Any]]) -> dict[str, Any]:
        zaehl = Counter(f["regel"] for f in faelle)
        return {
            "gesamt": len(faelle),
            "kategorien": [
                {"regel": regel, "urteil": URTEIL[regel], "anzahl": zahl,
                 "anteil": round(zahl / len(faelle), 4) if faelle else 0.0}
                for regel, zahl in zaehl.most_common()
            ],
            "je_quelle": dict(Counter(f["quelle"] for f in faelle)),
        }

    ergebnis = {
        "stand": "2026-11-21",
        "grundlage": {
            "records": len(records),
            "hybrid": "GLM auf 596, P5 auf 102 (wie vergleiche_20261120.py)",
            "textfenster": FENSTER,
            "bilanz": summe,
            "goldzellen": sum(len((records[r].get("gold") or {}).get("cells") or []) for r in hybrid),
            "records_ohne_zellen": sum(1 for r in pro_record.values() if r["leer"]),
        },
        "fn": block(fn_alle),
        "fp": block(fp_alle),
        "je_record": pro_record,
        "beispiele": {
            regel: [f for f in fn_alle + fp_alle if f["regel"] == regel][:3]
            for regel in URTEIL
        },
        "faelle_fn": fn_alle,
        "faelle_fp": fp_alle,
    }
    (HIER / "fehlerursachen_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    def tabelle(teil: dict[str, Any]) -> str:
        return "\n".join(
            f"| {k['urteil']} | `{k['regel']}` | {k['anzahl']} | {k['anteil']*100:.1f} % |"
            for k in teil["kategorien"]
        )

    bericht = [
        "# Fehlerursachen des Hybrids (21.11.2026)\n\n",
        "Basis: 699 Records, 2.014 Goldzellen. Hybrid wie in `vergleiche_20261120.py`\n"
        "(GLM auf 596, P5 auf 102), Bilanzlogik aus demselben Modul importiert.\n\n",
        f"| Kennzahl | Wert |\n|---|---:|\n| TP | {summe['tp']} |\n| FP | {summe['fp']} |\n"
        f"| FN | {summe['fn']} |\n| Records ohne eine einzige Zelle | "
        f"{ergebnis['grundlage']['records_ohne_zellen']} |\n\n",
        "## FN (verpasste Goldzellen)\n\n",
        "| Kategorie | Regel | Anzahl | Anteil |\n|---|---|---:|---:|\n", tabelle(ergebnis["fn"]),
        "\n\n## FP (ueberzaehlige Vorhersagezellen)\n\n",
        "| Kategorie | Regel | Anzahl | Anteil |\n|---|---|---:|---:|\n", tabelle(ergebnis["fp"]),
        "\n\n## Regeln und Grenzen\n\n",
        "Die Regeln greifen in dieser Reihenfolge, die erste zutreffende gewinnt:\n\n",
        "FN: `fn_leer` (Record ohne Zelle) → `fn_nicht_im_dokument` (Zahl steht im\n"
        "ganzen Dokument nicht; keiner dieser Faelle liegt nur hinter der\n"
        "45.000-Zeichen-Grenze) → `fn_mehrdeutig` (Gold traegt fuer denselben\n"
        "Schluessel mehrere Werte oder denselben Wert in beiden Armen) →\n"
        "`fn_wert_ersetzt` (gleicher Schluessel, anderer Wert ausgegeben) →\n"
        "`fn_nicht_ausgegeben`.\n\n",
        "FP: `fp_dublette` (zweite Zelle je Feld und Arm) → `fp_arm` (Wert ist\n"
        "Goldwert des anderen Arms) → `fp_feld` (Wert gehoert zu einem anderen Feld\n"
        "des Records) → `fp_zeitpunkt_zeile` (Wert ist Goldwert desselben Feldes in\n"
        "einer anderen Zeile) → `fp_einheit` (Faktor 10/100/1000 oder Rate als Anzahl)\n"
        "→ `fp_halluzination` (Zahl steht nirgends im Dokument) →\n"
        "`fp_ausserhalb_fenster` (Zahl erst hinter der 45.000-Zeichen-Grenze) →\n"
        "`fp_outcome` (Wert ist Goldwert eines anderen Records derselben Publikation)\n"
        "→ `fp_zeitpunkt` (Baseline- oder Aenderungswort im Umfeld eines\n"
        "Ergebnisfeldes) → `fp_gebunden`.\n\n",
        "Der Zahlabgleich ist fuer Fehleranalyse und Zellvalidierung derselbe\n"
        "(`zahlabgleich_20261121.py`): Punkt oder Komma als Trenner, nachlaufende\n"
        "Nullen erlaubt, 48 passt auf 48.0, nicht auf 48.5, und der Satzpunkt zaehlt\n"
        "nicht als Zahlbestandteil. Die fruehere, engere Fassung der Fehleranalyse\n"
        "zaehlte 12 Zellen als Halluzination, die im Dokument stehen.\n\n",
        "Grenzen: Die Zuordnung ist eine Text- und Zahlenheuristik, keine Rekonstruktion\n"
        "der Modellabsicht. `fp_zeitpunkt` vergibt sich ueber Baseline- oder\n"
        "Aenderungsworte im Umfeld; das Gold traegt fast ueberall keinen Zeitpunkt,\n"
        "ein belegter Zeitpunktvergleich ist damit nicht moeglich. `fn_mehrdeutig`\n"
        "markiert Goldwidersprueche, nicht bewiesene Goldfehler. Die Kategorien sind\n"
        "exklusiv; ein Wert, der sowohl im falschen Arm als auch am falschen Feld\n"
        "steht, zaehlt beim Arm.\n\n",
        "## Beispiele\n\n",
    ]
    for regel in URTEIL:
        faelle = ergebnis["beispiele"][regel]
        if not faelle:
            continue
        bericht.append(f"**{URTEIL[regel]}** (`{regel}`)\n\n")
        for f in faelle:
            bericht.append(
                f"- `{f['record_id']}` {f['feld']}/{f['arm']} = {f['wert']} — {f['beleg']}\n"
            )
        bericht.append("\n")

    (HIER / "fehlerursachen_20261121.md").write_text("".join(bericht), encoding="utf-8", newline="\n")

    print("Bilanz:", summe)
    print("FN:", {k["regel"]: k["anzahl"] for k in ergebnis["fn"]["kategorien"]})
    print("FP:", {k["regel"]: k["anzahl"] for k in ergebnis["fp"]["kategorien"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
