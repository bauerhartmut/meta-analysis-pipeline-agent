#!/usr/bin/env python
"""Zaehlt Kopfangaben unter den Goldzellen der 33 P5-Budgetfaelle (Sprint 48).

Frage 1: Wie viele Goldzellen der 33 `length_ohne_ergebnis`-Records stehen als
feste Kopfangabe (`n = ...`) in den Tabellen und sind damit fuer den
Tabellenpfad (Zellen der Outcome-Zeile) nicht erreichbar?

Frage 2: Wo stehen die uebrigen Gruppengroessen - in einer Caption, im
Fliesstext, nur in einer Tabellenzelle oder nirgends im Markdown?

Rein lesend: keine Netzaufrufe, keine Predictions, kein Gold wird geschrieben.
Gelesen werden die P5-Predictions, die Records und die Markdown-Dokumente;
Kopfangaben kommen aus dem vorhandenen Parser und `enrich_table`
(`Table.header_facts`), nicht aus einer neuen Erkennung.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/yun_full/zaehle_kopfangaben_sprint48.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
ROOT = HIER.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))
sys.path.insert(0, str(BENCH))

from research_agent.table_decomposition.parser import parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    reachable_cells,
)

RUN_ID = "yun699_p5_24000_20261118"
RUN = BENCH / "runs" / RUN_ID / "predictions.jsonl"
RECORDS = HIER / "records" / "yun699.jsonl"
AUSGABE = BENCH / "iterativ" / "ergebnisse" / "sprint48_kopfangaben_20261119"

#: Felder, die eine Gruppengroesse tragen; nur sie koennen eine Kopfangabe sein.
GRUPPENFELDER = ("intervention_group_size", "comparator_group_size")


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def kontext(record: dict) -> dict[str, Any]:
    ctx = record.get("context") or {}
    return {
        "intervention": ctx.get("intervention"),
        "comparator": ctx.get("comparator"),
        "outcome": ctx.get("outcome"),
        "outcome_type": ctx.get("outcome_type"),
        "timepoint_target": (record.get("timepoint") or {}).get("target"),
    }


def gleicher_wert(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= 1e-6


def wertmuster(wert: Any) -> re.Pattern:
    """Ganze Zahl als eigenstaendiges Zahlwort (kein `1402`, kein `4021`)."""
    zahl = int(round(float(wert)))
    return re.compile(rf"(?<![\d.]){zahl}(?!\d)")


#: Woerter, die eine Zahl als Gruppengroesse ausweisen (Korpus ist englisch).
GRUPPENWORT = (
    r"(?:women|woman|patients?|participants?|mothers?|infants?|neonates?|children|"
    r"men|subjects?|cases?|pregnancies|clusters?|schools?|providers?|pupils?|"
    r"households?|villages?|facilities?|sites?|practices?|units?|randomi[sz]ed|"
    r"assigned|recruited|enrolled|included|allocated)"
)


def n_angabe_muster(wert: Any) -> re.Pattern:
    """`n = 402`, `*n* = 402` vor der Zahl (auch `N~c~ = 12`)."""
    zahl = int(round(float(wert)))
    return re.compile(rf"\*?[nN](?:~[a-z]+~)?\*?\s*=\s*{zahl}(?!\d)")


def gruppenkontext(zeile: str, start: int, ende: int) -> bool:
    """Steht die Zahl in einem Zusammenhang, der sie als Gruppengroesse ausweist?

    Ohne diese Pruefung treffen bare Zahlwoerter im Abstract oder in Prozent-
    und Dezimalwerten zufaellig. Akzeptiert werden: `n = <zahl>` direkt davor,
    die Zahl als Nenner eines Bruchs (`42/402`), ein Gruppenwort direkt danach
    (`402 women`) und eine Randomisierungsfloskel im naechsten Satzteil.
    """
    vor = zeile[max(0, start - 60):start]
    nach = zeile[ende:ende + 60]
    if re.search(r"\*?[nN](?:~[a-z]+~)?\*?\s*=\s*$", vor):
        return True
    if re.search(r"\d\s*/\s*$", vor):
        return True
    if re.match(rf"\s*{GRUPPENWORT}\b", nach, re.I):
        return True
    if re.search(
        r"(randomi[sz]ed|assigned|recruited|enrolled|included|allocated)[^.;]{0,50}$",
        vor,
        re.I,
    ):
        return True
    if re.match(
        rf"[^.;]{{0,40}}(randomi[sz]ed|assigned|recruited|enrolled|included|allocated)",
        nach,
        re.I,
    ):
        return True
    return False


def analysiere_dokument(text: str, doc_id: str, context: dict) -> tuple[Any, list, set, set]:
    """Ein Parse je Dokument: Tabellen, Kopfangaben, erreichbare Felder."""
    try:
        parsed = parse_document(text, doc_id)
    except Exception as fehler:  # noqa: BLE001 - Parserausfall ist ein Befund
        return None, [{"parser_fehler": f"{type(fehler).__name__}: {fehler}"}], set(), set()
    facts: list[dict] = []
    zeilen: set = set()
    alles: set = set()
    for tabelle in parsed.tables:
        enrich_table(tabelle, context)
        for fact in tabelle.header_facts:
            facts.append(
                {
                    "table_id": tabelle.table_id,
                    "text": " ".join((fact.get("text") or "").split()),
                    "value": fact.get("value"),
                    "arm": fact.get("arm"),
                    "basis": fact.get("basis"),
                    "arm_basis": fact.get("arm_basis"),
                }
            )
        zellen = reachable_cells(tabelle, context)
        alles |= {name for _zeile, name in zellen}
        zeilen |= {name for zeile, name in zellen if zeile >= 0}
    return parsed, facts, zeilen, alles


def caption_zeilen(lines: list[str]) -> list[tuple[int, int]]:
    """Zeilenbereiche der `::: caption`-Bloecke (Start, Ende exklusiv)."""
    bereiche: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith(":::") and "caption" in lines[i]:
            start = i
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(":::"):
                i += 1
            bereiche.append((start, i + 1))
        i += 1
    return bereiche


def tabellen_zeilen(parsed: Any) -> list[tuple[int, int]]:
    if parsed is None:
        return []
    return [
        (t.line_start, t.line_end)
        for t in parsed.tables
        if getattr(t, "line_start", -1) >= 0 and getattr(t, "line_end", -1) >= 0
    ]


def in_bereichen(index: int, bereiche: list[tuple[int, int]]) -> bool:
    return any(start <= index <= ende for start, ende in bereiche)


def herkunft(wert: Any, lines: list[str], caption: list[tuple[int, int]],
             tabellen: list[tuple[int, int]]) -> dict[str, Any]:
    """Wo steht dieser Wert im Markdown?"""
    muster = wertmuster(wert)
    n_muster = n_angabe_muster(wert)
    kategorien: set[str] = set()
    roh_kategorien: set[str] = set()
    belege: list[dict] = []
    verworfen = 0
    for index, zeile in enumerate(lines):
        for treffer in muster.finditer(zeile):
            if in_bereichen(index, caption):
                roh = "caption"
            elif in_bereichen(index, tabellen):
                roh = "tabelle"
            else:
                roh = "fliesstext"
            roh_kategorien.add(roh)
            if not gruppenkontext(zeile, treffer.start(), treffer.end()):
                verworfen += 1
                continue
            kategorie = roh
            kategorien.add(kategorie)
            belege.append(
                {
                    "zeile": index,
                    "kategorie": kategorie,
                    "als_n_angabe": bool(
                        n_muster.search(zeile[max(0, treffer.start() - 20):treffer.end() + 5])
                    ),
                    "text": " ".join(zeile[max(0, treffer.start() - 70):treffer.end() + 70].split())[:180],
                }
            )
    if not kategorien and roh_kategorien:
        klasse = "ohne_kontext"
    elif not kategorien:
        klasse = "nicht_gefunden"
    elif len(kategorien) > 1:
        klasse = "mehrfach"
    else:
        klasse = next(iter(kategorien))
    return {
        "klasse": klasse,
        "kategorien": sorted(kategorien) if kategorien else sorted(roh_kategorien),
        "belege": belege,
        "verworfen_ohne_kontext": verworfen,
    }


def klassifiziere(zelle: dict, facts: list[dict]) -> tuple[str, list[dict]]:
    """Wie steht diese Goldzelle im Dokument da?"""
    if zelle.get("field") not in GRUPPENFELDER:
        return "kein_gruppenfeld", []
    treffer = [
        f for f in facts
        if f.get("value") is not None and gleicher_wert(zelle["value"], f["value"])
    ]
    if not treffer:
        return "keine_kopfangabe", []
    arm = zelle.get("arm")
    with_arm = [f for f in treffer if f.get("arm") == arm]
    if with_arm:
        return "kopfangabe_mit_arm", with_arm
    without_arm = [f for f in treffer if not f.get("arm")]
    if without_arm:
        return "kopfangabe_ohne_arm", without_arm
    return "kopfangabe_anderer_arm", treffer


def zaehle_fall(row: dict, record: dict, text: str) -> dict[str, Any]:
    doc_id = str((record.get("document") or {}).get("id") or row["record_id"])
    context = kontext(record)
    parsed, facts, zeilen_felder, _ = analysiere_dokument(text, doc_id, context)
    parser_fehler = next((f["parser_fehler"] for f in facts if "parser_fehler" in f), "")
    facts = [f for f in facts if "parser_fehler" not in f]
    lines = text.splitlines()
    caption = caption_zeilen(lines)
    tabellen = tabellen_zeilen(parsed)

    zellen = []
    for zelle in (record.get("gold") or {}).get("cells") or []:
        klasse, belege = klassifiziere(zelle, facts)
        ueber_zeile = zelle.get("field") in zeilen_felder
        nur_kopf = klasse == "kopfangabe_mit_arm" and not ueber_zeile
        eintrag = {
            "field": zelle.get("field"),
            "arm": zelle.get("arm"),
            "value": zelle.get("value"),
            "source": zelle.get("source"),
            "klasse": klasse,
            "belege": belege,
            "feld_ueber_outcome_zeile": ueber_zeile,
            "nur_als_kopfangabe": nur_kopf,
        }
        if klasse == "keine_kopfangabe":
            eintrag["herkunft"] = herkunft(zelle["value"], lines, caption, tabellen)
        zellen.append(eintrag)

    ohne_kopf = [z for z in zellen if z["klasse"] == "keine_kopfangabe"]
    return {
        "record_id": row["record_id"],
        "dokument_id": doc_id,
        "parser_fehler": parser_fehler,
        "gold_zellen": len(zellen),
        "gruppenfeld_zellen": sum(1 for z in zellen if z["field"] in GRUPPENFELDER),
        "kopfangabe_mit_arm": sum(1 for z in zellen if z["klasse"] == "kopfangabe_mit_arm"),
        "kopfangabe_ohne_arm": sum(1 for z in zellen if z["klasse"] == "kopfangabe_ohne_arm"),
        "kopfangabe_anderer_arm": sum(
            1 for z in zellen if z["klasse"] == "kopfangabe_anderer_arm"
        ),
        "keine_kopfangabe": len(ohne_kopf),
        "kein_gruppenfeld": sum(1 for z in zellen if z["klasse"] == "kein_gruppenfeld"),
        "ueber_outcome_zeile": sum(1 for z in zellen if z["feld_ueber_outcome_zeile"]),
        "nur_als_kopfangabe": sum(1 for z in zellen if z["nur_als_kopfangabe"]),
        "weder_noch": sum(
            1
            for z in zellen
            if not z["feld_ueber_outcome_zeile"] and not z["nur_als_kopfangabe"]
        ),
        "herkunft_fliesstext": sum(1 for z in ohne_kopf if z["herkunft"]["klasse"] == "fliesstext"),
        "herkunft_caption": sum(1 for z in ohne_kopf if z["herkunft"]["klasse"] == "caption"),
        "herkunft_tabelle": sum(1 for z in ohne_kopf if z["herkunft"]["klasse"] == "tabelle"),
        "herkunft_mehrfach": sum(1 for z in ohne_kopf if z["herkunft"]["klasse"] == "mehrfach"),
        "herkunft_ohne_kontext": sum(
            1 for z in ohne_kopf if z["herkunft"]["klasse"] == "ohne_kontext"
        ),
        "herkunft_nicht_gefunden": sum(
            1 for z in ohne_kopf if z["herkunft"]["klasse"] == "nicht_gefunden"
        ),
        "kopfangaben_im_dokument": len(facts),
        "kopfangaben_mit_arm": sum(1 for f in facts if f.get("arm")),
        "zellen": zellen,
    }


def de(wert: float) -> str:
    """Deutsche Dezimalschreibweise fuer die Anteile im Bericht."""
    return f"{wert:.1f}".replace(".", ",")


def schreibe_md(faelle: list[dict]) -> str:
    n = len(faelle)
    gold = sum(f["gold_zellen"] for f in faelle)
    gruppen = sum(f["gruppenfeld_zellen"] for f in faelle)
    mit_arm = sum(f["kopfangabe_mit_arm"] for f in faelle)
    ohne_arm = sum(f["kopfangabe_ohne_arm"] for f in faelle)
    anderer_arm = sum(f["kopfangabe_anderer_arm"] for f in faelle)
    keine = sum(f["keine_kopfangabe"] for f in faelle)
    kein_gruppen = sum(f["kein_gruppenfeld"] for f in faelle)
    outcome = sum(f["ueber_outcome_zeile"] for f in faelle)
    nur_kopf = sum(f["nur_als_kopfangabe"] for f in faelle)
    weder = sum(f["weder_noch"] for f in faelle)
    gezaehlt = mit_arm + ohne_arm
    quote = 100 * gezaehlt / gold if gold else 0.0
    herkunft_summe = {
        key: sum(f[f"herkunft_{key}"] for f in faelle)
        for key in (
            "fliesstext", "caption", "tabelle", "mehrfach", "ohne_kontext", "nicht_gefunden"
        )
    }

    zeilen: list[str] = []
    a = zeilen.append
    a("# Sprint 48: Kopfangaben unter den Goldzellen der 33 Budgetfaelle")
    a("")
    a(
        f"Grundgesamtheit: **{n}** `length_ohne_ergebnis`-Records aus "
        f"`yun699_p5_24000_20261118`, **{gold}** Goldzellen. Rein lesend: keine "
        "Netzaufrufe, keine Predictions geschrieben, keine eingefrorene Eingabe "
        "beruehrt. Die Entscheidungsvorlage `sprint48_nachzug_entscheidung_20261119.md` "
        "wird mit dem Ergebnis nachgezogen."
    )
    a("")
    a("## 1. Befund")
    a("")
    a(
        f"- **{gruppen} von {gold} Goldzellen** sind Gruppengroessen "
        "(`intervention_group_size`, `comparator_group_size`). Nur diese koennen "
        "ueberhaupt eine Kopfangabe sein."
    )
    a(
        f"- **{gezaehlt} Goldzellen ({de(quote)} % aller Goldzellen) stehen als "
        f"`n = ...` im Tabellenkopf**: {mit_arm} mit belegtem Arm und {ohne_arm} ohne "
        f"Arm. Weitere {anderer_arm} treffen eine Kopfangabe nur mit einem anderen Arm."
    )
    a(
        f"- **{keine} Gruppengroessen haben keine passende Kopfangabe**; "
        f"{kein_gruppen} Goldzellen sind Messwerte (Mittelwert, Streuung, Ereignisse)."
    )
    a(
        "- Herkunft der {keine} ohne Kopfangabe: **{fliesstext} nur im Fliesstext**, "
        "**{caption} nur in einer Caption**, **{tabelle} nur in einer Tabellenzelle**, "
        "**{mehrfach} an mehreren Stellen**, **{ohne_kontext} nur ohne Gruppen-Kontext** "
        "und **{nicht_gefunden} nirgends im Markdown**.".format(**herkunft_summe, keine=keine)
    )
    a(
        f"- Ueber die Outcome-Zeile erreichbar sind **{outcome} von {gold}** Goldzellen; "
        f"**{nur_kopf}** nur ueber eine Kopfangabe und **{weder}** weder ueber Zeile noch "
        "Kopfangabe (Fliesstext, andere Tabelle oder im Markdown nicht enthalten)."
    )
    a("")
    a("## 2. Je Record")
    a("")
    a(
        "| Record | Dokument | Gold | Gruppenfeld | Kopf m. Arm | Kopf o. Arm | and. Arm | "
        "keine Kopfangabe | ueber Outcome-Zeile | nur Kopf (Wert) | weder/noch |"
    )
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for f in sorted(faelle, key=lambda x: (-x["gold_zellen"], x["record_id"])):
        a(
            f"| `{f['record_id']}` | {f['dokument_id']} | {f['gold_zellen']} | "
            f"{f['gruppenfeld_zellen']} | {f['kopfangabe_mit_arm']} | "
            f"{f['kopfangabe_ohne_arm']} | {f['kopfangabe_anderer_arm']} | "
            f"{f['keine_kopfangabe']} | {f['ueber_outcome_zeile']} | "
            f"{f['nur_als_kopfangabe']} | {f['weder_noch']} |"
        )
    a("")
    a(
        "Spalten: `Kopf m. Arm` = Goldwert steht als `n = ...` im Kopf und der Arm ist "
        "belegt; `Kopf o. Arm` = Kopfangabe ohne belegten Arm; `and. Arm` = Wert nur "
        "mit anderem Arm; `keine Kopfangabe` = Gruppengroesse, deren Wert nicht als "
        "`n = ...` vorkommt; `ueber Outcome-Zeile` = Goldfeld kommt in "
        "`reachable_cells` mit einer echten Datenzeile vor (feldweise, wie im "
        "Benchmark); `nur Kopf (Wert)` = Wert steht als Kopfangabe mit belegtem Arm "
        "und das Feld kommt in keiner Datenzeile vor; `weder/noch` = keiner der "
        "beiden Wege fuer diesen Wert."
    )
    a("")
    a("## 3. Was das fuer den Kopf-Fakten-Prompt bedeutet")
    a("")
    a(
        f"Ein Kopf-Fakten-Prompt kann hoechstens die {gezaehlt} Goldzellen mit "
        f"belegter oder unbelegter Kopfangabe direkt liefern - das sind {de(quote)} % "
        f"der {gold} Goldzellen dieser 33 Faelle. Die uebrigen {gold - gezaehlt} "
        f"Zellen sind {kein_gruppen} Messwerte und {keine} Gruppengroessen ohne "
        "passende `n = ...`-Angabe; fuer sie aendert ein Kopf-Fakten-Prompt nichts."
    )
    a("")
    plan_ids = ("yun2024:30", "yun2024:252", "yun2024:421", "yun2024:672", "yun2024:678")
    plan = [f for rid in plan_ids for f in faelle if f["record_id"] == rid]
    if plan:
        p_gold = sum(f["gold_zellen"] for f in plan)
        p_kopf = sum(f["kopfangabe_mit_arm"] + f["kopfangabe_ohne_arm"] for f in plan)
        a(
            "In den fuenf Planfaellen aus der Diagnose sieht der Hebel so aus "
            f"({p_kopf} von {p_gold} Goldzellen sind Kopfangaben):"
        )
        a("")
        a("| Record | Gold | Gruppenfeld | Kopfangabe | mit Arm | ohne Arm |")
        a("|---|---:|---:|---:|---:|---:|")
        for f in plan:
            a(
                f"| `{f['record_id']}` | {f['gold_zellen']} | {f['gruppenfeld_zellen']} | "
                f"{f['kopfangabe_mit_arm'] + f['kopfangabe_ohne_arm']} | "
                f"{f['kopfangabe_mit_arm']} | {f['kopfangabe_ohne_arm']} |"
            )
        a("")
        voll = [f["record_id"] for f in plan
                if f["gold_zellen"] and f["kopfangabe_mit_arm"] + f["kopfangabe_ohne_arm"] == f["gold_zellen"]]
        leer = [f["record_id"] for f in plan if f["gruppenfeld_zellen"] and not (
            f["kopfangabe_mit_arm"] + f["kopfangabe_ohne_arm"]
        )]
        abdeckung = (
            ("Vollstaendig ueber Kopfangaben abgedeckt ist nur " + ", ".join(f"`{r}`" for r in voll) + ". ")
            if voll else "Kein Planfall ist vollstaendig ueber Kopfangaben abgedeckt. "
        )
        if leer:
            abdeckung += (
                "Ohne jeden Kopfangaben-Treffer bleiben " + ", ".join(f"`{r}`" for r in leer)
                + ": dort stehen die gesuchten Gruppengroessen nicht als `n = ...` im Markdown."
            )
        a(abdeckung)
        a("")
        a(
            "Der Hebel wirkt damit nur dort, wo die Aufgabe tatsaechlich nach "
            "Gruppengroessen fragt. Ob der Prompt das Reasoning entlastet, ist "
            "**nicht** gemessen: die Zaehlung zeigt nur die Obergrenze des Ertrags, "
            "nicht die Wirkung auf das Budget."
        )
        a("")
    a("## 4. Wo die {keine} Gruppengroessen ohne Kopfangabe stehen".format(keine=keine))
    a("")
    a(
        "Gesucht wurde der jeweilige Goldwert als eigenstaendiges Zahlwort **mit "
        "Gruppen-Kontext** (`n = <wert>`, Nenner eines Bruchs wie `42/402`, "
        "Gruppenwort wie `402 women`, Randomisierungsfloskel); bare Zahlwoerter "
        "zaehlen nicht. Getrennt nach `::: caption`-Block, Tabellenbereich laut "
        "`Table.line_start`/`line_end` und allen uebrigen Zeilen (Fliesstext). "
        "Ein Wert kann an mehreren Stellen stehen."
    )
    a("")
    a("| Herkunft | Zellen | davon als `n = ...` |")
    a("|---|---:|---:|")
    beispiele: dict[str, list[dict]] = {}
    for f in faelle:
        for z in f["zellen"]:
            if z["klasse"] != "keine_kopfangabe":
                continue
            for beleg in z["herkunft"]["belege"]:
                if beleg["als_n_angabe"]:
                    beispiele.setdefault("n_angabe", []).append(
                        {"record_id": f["record_id"], "value": z["value"], **beleg}
                    )
    for key, label in (
        ("fliesstext", "nur Fliesstext"),
        ("caption", "nur Caption"),
        ("tabelle", "nur Tabellenzelle"),
        ("mehrfach", "mehrere Stellen"),
        ("ohne_kontext", "nur ohne Gruppen-Kontext"),
        ("nicht_gefunden", "nirgends im Markdown"),
    ):
        zahl_n = sum(
            1
            for f in faelle
            for z in f["zellen"]
            if z["klasse"] == "keine_kopfangabe"
            and z["herkunft"]["klasse"] == key
            and any(b["als_n_angabe"] for b in z["herkunft"]["belege"])
        )
        a(f"| {label} | {herkunft_summe[key]} | {zahl_n} |")
    a("")
    if beispiele.get("n_angabe"):
        a("Werte, die irgendwo als `n = ...` stehen (Kategorie in Klammern):")
        a("")
        for b in beispiele["n_angabe"][:8]:
            a(f"- `{b['record_id']}` Wert {int(b['value'])}: {b['kategorie']}, Zeile {b['zeile']}: \"{b['text']}\"")
        a("")
    a("### 4.1 Die fuenf Planfaelle")
    a("")
    a("| Record | ohne Kopfangabe | Herkunft |")
    a("|---|---:|---|")
    for f in plan:
        ohne = [z for z in f["zellen"] if z["klasse"] == "keine_kopfangabe"]
        if not ohne:
            a(f"| `{f['record_id']}` | 0 | - |")
            continue
        teile = []
        for z in ohne:
            h = z["herkunft"]
            teile.append(
                f"{z['field']}={int(z['value'])}: {h['klasse']}"
                + (" (als n = ...)" if any(b["als_n_angabe"] for b in h["belege"]) else "")
            )
        a(f"| `{f['record_id']}` | {len(ohne)} | " + "; ".join(teile) + " |")
    a("")
    a("## 5. Grenzen")
    a("")
    a(
        "- Gezaehlt wird gegen `Table.header_facts` des vorhandenen Parsers; eine "
        "Kopfangabe, die der Parser nicht erkennt (etwa in einer Bild-Caption), fehlt "
        "hier. Die Zahl ist damit eine Untergrenze."
    )
    a(
        "- Der Wertvergleich ist numerisch ueber `value`; dieselbe Zahl an anderer "
        "Stelle (etwa eine Stichprobe, die zufaellig `n` entspricht) kann einen "
        "Treffer erzeugen. Deshalb ist der Arm mit ausgewiesen."
    )
    a(
        "- Die Herkunft sucht das Zahlwort ohne Toleranz (`402` trifft nicht "
        "`402,5`) und nur mit Gruppen-Kontext. Steht der Wert nur gerundet, als "
        "Summe oder ohne erkennbares Gruppenwort im Text, gilt er als nicht "
        "gefunden; Zufallstreffer im Abstract sind damit ausgeschlossen."
    )
    a(
        "- `nur Kopf (Wert)` prueft den Wert, nicht nur das Feld: `reachable_cells` "
        "fuehrt eine Kopfangabe mit belegtem Arm als `(-1, feld)` und wuerde sonst "
        "auch dann einen Treffer melden, wenn die Tabelle eine andere Zahl druckt "
        "(`yun2024:252`: Tabelle `*n* = 398`, Gold 402)."
    )
    a(
        "- Kopfangaben koennen kursiv gesetzt sein (`*n* = 398`); gezaehlt wird, was "
        "`Table.header_facts` liefert, nicht ein eigener Textabgleich."
    )
    a(
        "- Gezaehlt werden **alle Tabellen des Dokuments**. Die Planwerte in "
        "`offline_struktur_20261118b/structure.json` beziehen sich auf je eine "
        "ausgewaehlte Tabelle und koennen deshalb kleiner sein (etwa `yun2024:421`: "
        "Plan 3 = 2 Zeilen + 1 Kopfangabe, dokumentweit 4 Goldzellen ueber die "
        "Outcome-Zeile)."
    )
    parser = [f for f in faelle if f["parser_fehler"]]
    if parser:
        a("")
        a("Parserausfaelle: " + ", ".join(f"`{f['record_id']}`" for f in parser) + ".")
    return "\n".join(zeilen) + "\n"


def main() -> int:
    rows = [
        r for r in lies_jsonl(RUN)
        if r.get("fehlerklasse") == "length_ohne_ergebnis"
    ]
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}
    cache: dict[str, str] = {}
    faelle = []
    for row in rows:
        record = records[row["record_id"]]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        key = str(pfad)
        if key not in cache:
            cache[key] = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        faelle.append(zaehle_fall(row, record, cache[key]))

    summe = Counter()
    for f in faelle:
        for key in (
            "gold_zellen",
            "gruppenfeld_zellen",
            "kopfangabe_mit_arm",
            "kopfangabe_ohne_arm",
            "kopfangabe_anderer_arm",
            "keine_kopfangabe",
            "kein_gruppenfeld",
            "ueber_outcome_zeile",
            "nur_als_kopfangabe",
            "weder_noch",
            "herkunft_fliesstext",
            "herkunft_caption",
            "herkunft_tabelle",
            "herkunft_mehrfach",
            "herkunft_ohne_kontext",
            "herkunft_nicht_gefunden",
        ):
            summe[key] += f[key]

    daten = {
        "sprint": 48,
        "frage": (
            "Wie viele Goldzellen der 33 Budgetfaelle sind Kopfangaben (n = ...), und "
            "wo stehen die uebrigen Gruppengroessen?"
        ),
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/zaehle_kopfangaben_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "lauf": RUN_ID,
        "records": len(faelle),
        "summe": dict(summe),
        "faelle": faelle,
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    AUSGABE.with_suffix(".md").write_text(schreibe_md(faelle), encoding="utf-8")
    print(json.dumps({"records": len(faelle), **dict(summe)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
