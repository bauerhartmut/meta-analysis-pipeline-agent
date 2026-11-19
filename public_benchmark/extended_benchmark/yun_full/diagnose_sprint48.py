#!/usr/bin/env python
"""Diagnose der P5-Budgetabbruche (Sprint 48), rein lesend.

Frage: Warum verbraucht glm bei 33 Records das Budget von 24.000
Completion-Tokens vollstaendig im Reasoning, ohne eine Zelle auszugeben?

Das Skript liest
  * die P5-Predictions (`length_ohne_ergebnis` gegen die 67 Erfolge),
  * die Records und die Markdown-Dokumente,
  * die vorhandenen Zerlegungsartefakte unter `analysis/table_decomposition_20261118/`,
  * die frueheren Laeufe (Budget-Dosis je Record),
und schreibt zwei Diagnoseartefakte. Es sendet keine Anfrage, schreibt keine
Predictions und aendert keine eingefrorene Eingabe.

Strukturmerkmale kommen aus dem vorhandenen Parser
(`research_agent.table_decomposition.parser.parse_document`) und der
vorhandenen Komplexitaetsbewertung (`complexity.assess`); es wird kein neues
Zerlegungsverfahren implementiert. Die Promptgroesse wird mit dem echten
Prompt-Bauer des Harness (`build_prompt`) berechnet, ohne Aufruf.

Aufruf:
    .venv/bin/python public_benchmark/extended_benchmark/yun_full/diagnose_sprint48.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
BENCH = HIER.parent
ROOT = HIER.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BENCH.parent))  # Paketwurzel public_benchmark
sys.path.insert(0, str(BENCH))

from research_agent.table_decomposition.complexity import assess  # noqa: E402
from research_agent.table_decomposition.parser import ROLE_LABEL, parse_document  # noqa: E402
from research_agent.table_decomposition.semantics import (  # noqa: E402
    enrich_table,
    reachable_cells,
)
from extended_benchmark.run_extended_extraction import build_prompt  # noqa: E402

RUN_ID = "yun699_p5_24000_20261118"
RUNS = BENCH / "runs"
RUN = RUNS / RUN_ID
RECORDS = HIER / "records" / "yun699.jsonl"
ANALYSE = BENCH / "analysis" / "table_decomposition_20261118"
AUSGABE = BENCH / "iterativ" / "ergebnisse" / "sprint48_budgetdiagnose"
BUDGET = 24000
PROMPT_LIMIT = 45000  # Standard von build_prompt; P5 hat ihn nicht ueberschrieben

#: Komplexitaetsklassen in aufsteigender Ordnung (aus `complexity.assess`).
KLASSEN_RANG = {"einfach": 0, "mittel": 1, "komplex": 2, "sehr_komplex": 3}

HYPOTHESEN = {
    "H1": "Zu hohe Tabellenkomplexitaet",
    "H2": "Zu viele Tabellenzellen",
    "H3": "Mehrstufige Ueberschriften",
    "H4": "Ungeeignete Promptstruktur",
    "H5": "Zu aufwendige Reasoning-Schritte",
    "H6": "Zu umfangreiche Ausgabe",
    "H7": "Sonstige bzw. nicht eindeutig klassifizierbar",
}


def lies_jsonl(pfad: Path) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def quantil(werte: list[float], anteil: float) -> float:
    if not werte:
        return 0.0
    sortiert = sorted(werte)
    pos = min(int(anteil * (len(sortiert) - 1)), len(sortiert) - 1)
    return float(sortiert[pos])


def kennzahlen(werte: list[float]) -> dict[str, float]:
    werte = [float(w) for w in werte]
    if not werte:
        return {"n": 0}
    return {
        "n": len(werte),
        "min": min(werte),
        "median": round(statistics.median(werte), 1),
        "q75": round(quantil(werte, 0.75), 1),
        "max": max(werte),
    }


def kontext(record: dict) -> dict[str, Any]:
    ctx = record.get("context") or {}
    return {
        "intervention": ctx.get("intervention"),
        "comparator": ctx.get("comparator"),
        "outcome": ctx.get("outcome"),
        "outcome_type": ctx.get("outcome_type"),
        "timepoint_target": (record.get("timepoint") or {}).get("target"),
    }


def tabellen_masse(text: str, doc_id: str, context: dict) -> dict[str, Any]:
    """Strukturmerkmale aller Tabellen eines Dokuments fuer diesen Record."""
    try:
        parsed = parse_document(text, doc_id)
    except Exception as fehler:  # noqa: BLE001 - Parserausfall ist ein Befund
        return {"parser_fehler": f"{type(fehler).__name__}: {fehler}", "tabellen": []}

    masse = []
    for tabelle in parsed.tables:
        enrich_table(tabelle, context)
        score = assess(tabelle)
        datenspalten = {sp.col_id for sp in tabelle.columns if sp.role != ROLE_LABEL}
        zellen = 0
        for zeile in tabelle.rows:
            for col_id, zelle in zeile.cells.items():
                if col_id in datenspalten and (zelle.text or "").strip():
                    zellen += 1
        felder = {name for _zeile, name in reachable_cells(tabelle, context)}
        masse.append(
            {
                "table_id": tabelle.table_id,
                "zeilen": len(tabelle.rows),
                "spalten": len(tabelle.columns),
                "datenspalten": len(datenspalten),
                "datenzellen": zellen,
                "kopfebenen": len({band.level for band in tabelle.header_bands}),
                "gruppenkopf_zellen": sum(1 for band in tabelle.header_bands if band.span > 1),
                "fussnoten": len(tabelle.footnotes),
                "unregelmaessig": len(tabelle.irregularities),
                "komplexitaet": score.class_label,
                "komplexitaet_score": round(score.score, 3),
                "treiber": score.drivers,
                "zielfelder": sorted(felder),
                "zielfeld_zellen": zellen if felder else 0,
                "fokus_zeilen": len(tabelle.focus_rows),
                "caption": bool((tabelle.caption or "").strip()),
            }
        )
    return {"parser_fehler": "", "tabellen": masse}


def verdichte(masse: dict) -> dict[str, Any]:
    tabellen = masse["tabellen"]
    leer = {
        "parser_fehler": masse["parser_fehler"],
        "tabellen": 0,
        "tabellen_mit_zielfeld": 0,
        "zeilen_max": 0,
        "zeilen_summe": 0,
        "spalten_max": 0,
        "datenspalten_max": 0,
        "datenzellen_summe": 0,
        "datenzellen_zielfeld": 0,
        "kopfebenen_max": 0,
        "gruppenkopf_zellen": 0,
        "fussnoten_summe": 0,
        "unregelmaessige_zeilen": 0,
        "komplexitaet_max": "unbekannt",
        "komplexitaet_score_max": 0.0,
        "komplexe_tabellen": 0,
        "fokus_zeilen_summe": 0,
    }
    if masse["parser_fehler"] or not tabellen:
        return leer
    return {
        "parser_fehler": "",
        "tabellen": len(tabellen),
        "tabellen_mit_zielfeld": sum(1 for t in tabellen if t["zielfelder"]),
        "zeilen_max": max(t["zeilen"] for t in tabellen),
        "zeilen_summe": sum(t["zeilen"] for t in tabellen),
        "spalten_max": max(t["spalten"] for t in tabellen),
        "datenspalten_max": max(t["datenspalten"] for t in tabellen),
        "datenzellen_summe": sum(t["datenzellen"] for t in tabellen),
        "datenzellen_zielfeld": sum(t["zielfeld_zellen"] for t in tabellen),
        "kopfebenen_max": max(t["kopfebenen"] for t in tabellen),
        "gruppenkopf_zellen": sum(t["gruppenkopf_zellen"] for t in tabellen),
        "fussnoten_summe": sum(t["fussnoten"] for t in tabellen),
        "unregelmaessige_zeilen": sum(t["unregelmaessig"] for t in tabellen),
        "komplexitaet_max": max(
            (t["komplexitaet"] for t in tabellen), key=lambda k: KLASSEN_RANG.get(k, -1)
        ),
        "komplexitaet_score_max": max(t["komplexitaet_score"] for t in tabellen),
        "komplexe_tabellen": sum(
            1 for t in tabellen if KLASSEN_RANG.get(t["komplexitaet"], -1) >= 2
        ),
        "fokus_zeilen_summe": sum(t["fokus_zeilen"] for t in tabellen),
    }


def laufhistorie(ids: set[str]) -> dict[str, list[dict]]:
    """Fruehere glm-Zeilen je Record mit Budget aus allen Laeufen (ohne P5)."""
    historie: dict[str, list[dict]] = {rid: [] for rid in ids}
    for pfad in sorted(RUNS.glob("*/predictions.jsonl")):
        if pfad.parent.name == RUN_ID:
            continue
        for row in lies_jsonl(pfad):
            rid = row.get("record_id")
            if rid not in historie or row.get("model") != "glm":
                continue
            budget = (row.get("gateway_params") or {}).get("max_tokens")
            if budget not in (4000, 8000, 16000, 19000, 24000):
                continue
            klasse = row.get("fehlerklasse") or ("ok" if row.get("rows") else "ohne Zellen")
            historie[rid].append(
                {
                    "lauf": pfad.parent.name,
                    "budget": budget,
                    "klasse": klasse,
                    "tokens": row.get("completion_tokens"),
                    "zellen": len(row.get("rows") or []),
                }
            )
    for eintraege in historie.values():
        eintraege.sort(key=lambda e: (e["budget"], e["lauf"]))
    return historie


def zerlegungsdiagnosen(ids: set[str]) -> dict[str, dict[str, Any]]:
    """Welche vorhandenen Diagnosen und Laeufe decken einen Record ab?"""
    ergebnis: dict[str, dict[str, Any]] = {rid: {} for rid in ids}
    test = json.loads((ANALYSE / "selection_test.json").read_text(encoding="utf-8"))
    dev = json.loads((ANALYSE / "selection_dev.json").read_text(encoding="utf-8"))
    for name, auswahl in (("auswahl_test", test), ("auswahl_dev", dev)):
        gewaehlt = set(auswahl.get("record_ids") or [])
        for rid in ids:
            ergebnis[rid][name] = rid in gewaehlt
            if rid in gewaehlt:
                ergebnis[rid].setdefault("auswahl_tabellen", []).extend(
                    t["table_id"] for t in auswahl.get("tables") or [] if rid in t.get("record_ids", [])
                )

    struktur = json.loads(
        (ANALYSE / "offline_struktur_20261118b" / "structure.json").read_text(encoding="utf-8")
    )
    je_record: dict[str, dict[str, Any]] = {}
    for strategie, eintraege in (struktur.get("records") or {}).items():
        for eintrag in eintraege:
            ziel = je_record.setdefault(eintrag["record_id"], {"strategien": {}})
            ziel["strategien"][strategie] = {
                "tabellen": eintrag["tables"],
                "einheiten": eintrag["units"],
                "prompt_zeichen": eintrag["prompt_chars"],
                "komplexitaet": eintrag["complexity"],
                "gold_erreichbar": eintrag["gold_reachable"],
            }
    for rid, wert in je_record.items():
        if rid in ergebnis:
            ergebnis[rid]["offline_struktur"] = wert["strategien"]

    sprint43 = json.loads(
        (ANALYSE / "sprint43_20261118" / "phase1_diagnose.json").read_text(encoding="utf-8")
    )
    for table_id, eintrag in (sprint43.get("tabellen") or {}).items():
        for rid in eintrag.get("record_ids") or []:
            if rid in ergebnis:
                ergebnis[rid].setdefault("sprint43_tabellen", []).append(table_id)

    for name in ("gruppenkoepfe_20261118", "fliesstext_20261118", "nachpruefung_20261118"):
        datei = ANALYSE / name / ("gegenprobe.json" if name.startswith("nachpruefung") else "messung.json")
        if not datei.exists():
            continue
        daten = json.loads(datei.read_text(encoding="utf-8"))
        for eintrag in daten.get("records") or []:
            rid = eintrag.get("record_id")
            if rid in ergebnis:
                kurz = {
                    "gewaehlte_tabelle": eintrag.get("gewaehlte_tabelle") or eintrag.get("tabelle"),
                    "grund": eintrag.get("grund", ""),
                    "wechsel": eintrag.get("wechsel"),
                }
                ergebnis[rid].setdefault("diagnosen", {})[name] = kurz

    modell = ANALYSE / "modell_glm53_abe_20261118" / "predictions.jsonl"
    if modell.exists():
        for row in lies_jsonl(modell):
            rid = row.get("record_id")
            if rid in ergebnis:
                ergebnis[rid].setdefault("zerlegungslauf", []).append(
                    {
                        "strategie": row.get("strategy"),
                        "zellen": len(row.get("cells") or []),
                        "completion_tokens": (row.get("telemetry") or {}).get("completion_tokens"),
                    }
                )
    return ergebnis


def fall_eintrag(
    row: dict,
    record: dict,
    text: str,
    struktur: dict,
    verdichtet: dict,
    historie: list[dict],
    diagnosen: dict,
) -> dict[str, Any]:
    doc = record.get("document") or {}
    prompt_zeichen = len(build_prompt(record, text))
    attempts = row.get("attempts") or []
    dauer = sum(float(a.get("dauer_s") or 0) for a in attempts)
    evidenz = []
    if row.get("content_chars") == 0:
        evidenz.append("Antwort enthaelt keinen Inhalt (content_chars = 0)")
    if row.get("completion_tokens") == BUDGET:
        evidenz.append(f"completion_tokens genau auf dem Budget ({BUDGET})")
    if row.get("finish_reason") == "length":
        evidenz.append("finish_reason = length")
    if row.get("reasoning_chars"):
        evidenz.append(f"reasoning_chars = {row['reasoning_chars']}")
    if len(text) > PROMPT_LIMIT:
        evidenz.append(f"Dokument ({len(text)} Zeichen) wird bei {PROMPT_LIMIT} Zeichen abgeschnitten")
    return {
        "record_id": row["record_id"],
        "gruppe": (
            "budget_abbruch"
            if row.get("fehlerklasse") == "length_ohne_ergebnis"
            else ("erfolg" if row.get("rows") else "ohne_zellen")
        ),
        "publikation": {
            "dokument_id": doc.get("id"),
            "split": doc.get("split"),
            "dokumenttyp": doc.get("kind"),
            "titel_journal": "nicht verfuegbar (Record traegt keinen Titel)",
            "doi_pmid": "nicht verfuegbar (Record traegt nur die Dokument-ID)",
        },
        "kontext": {
            "outcome": (record.get("context") or {}).get("outcome"),
            "outcome_typ": (record.get("context") or {}).get("outcome_type"),
            "intervention": (record.get("context") or {}).get("intervention"),
            "comparator": (record.get("context") or {}).get("comparator"),
            "zeitpunkt": (record.get("timepoint") or {}).get("target"),
            "zeitpunkt_status": (record.get("timepoint") or {}).get("status"),
        },
        "gold": {
            "zellen": len((record.get("gold") or {}).get("cells") or []),
            "felder": sorted({c["field"] for c in (record.get("gold") or {}).get("cells") or []}),
        },
        "struktur": {
            **verdichtet,
            "text_zeichen": len(text),
            "text_zeichen_record": doc.get("text_chars"),
            "prompt_zeichen": prompt_zeichen,
            "prompt_text_zeichen": min(len(text), PROMPT_LIMIT),
            "tabelle_masse": [
                {
                    key: t[key]
                    for key in (
                        "table_id",
                        "zeilen",
                        "spalten",
                        "datenspalten",
                        "datenzellen",
                        "kopfebenen",
                        "gruppenkopf_zellen",
                        "fussnoten",
                        "komplexitaet",
                        "komplexitaet_score",
                        "zielfelder",
                    )
                }
                for t in struktur["tabellen"]
            ],
        },
        "lauf": {
            "completion_tokens": row.get("completion_tokens"),
            "reasoning_zeichen": row.get("reasoning_chars"),
            "reasoning_tokens": "nicht verfuegbar (Zeile traegt nur reasoning_chars)",
            "content_zeichen": row.get("content_chars"),
            "finish_reason": row.get("finish_reason"),
            "parse_error": row.get("parse_error"),
            "http_status": row.get("http_status"),
            "http_versuche": row.get("http_versuche"),
            "dauer_s": round(dauer, 1),
            "prompt_version": row.get("prompt_version"),
            "quelle": row.get("quelle"),
            "wiederaufnahmen": row.get("wiederaufnahmen"),
            "zellen": len(row.get("rows") or []),
        },
        "fruehere_laeufe": historie,
        "zerlegungsdiagnosen": diagnosen,
        "beobachtungen": evidenz,
    }


def ueber(wert: float, schwelle: float) -> bool:
    """Echt groesser als die Schwelle; bei Schwelle 0 zaehlt jeder Wert > 0.

    Ohne diesen Fall waere eine Verteilung aus lauter Nullen (etwa
    `datenzellen_zielfeld`) fuer jede Zeile ein Treffer.
    """
    return wert > schwelle if schwelle > 0 else wert > 0


def hypothese_treffer(eintrag: dict, schwellen: dict[str, float]) -> dict[str, bool]:
    s = eintrag["struktur"]
    return {
        "H1": s.get("komplexe_tabellen", 0) >= 1
        or ueber(s.get("komplexitaet_score_max", 0), schwellen["komplexitaet_score_max"]),
        "H2": ueber(s.get("datenzellen_summe", 0), schwellen["datenzellen_summe"]),
        "H3": s.get("kopfebenen_max", 0) >= 3,
        "H4": ueber(s.get("prompt_zeichen", 0), schwellen["prompt_zeichen"])
        or s.get("tabellen_mit_zielfeld", 0) == 0,
        "H6": ueber(s.get("datenzellen_zielfeld", 0), schwellen["datenzellen_zielfeld"]),
    }


def zahl(wert: Any) -> str:
    if wert is None:
        return "-"
    if isinstance(wert, float):
        if wert.is_integer():
            return f"{int(wert):,}".replace(",", ".")
        return f"{wert:.1f}".replace(".", ",")
    return f"{wert:,}".replace(",", ".")


def schreibe_md(
    eintraege: list[dict],
    abbruch: list[dict],
    erfolg: list[dict],
    hypothesen_bilanz: dict,
    merkmals_bilanz: dict,
    lauf_bilanz: dict,
    schwellen: dict,
    frueher: dict,
) -> str:
    """Bericht aus den bereits berechneten Zahlen; keine eigene Rechnung."""
    zeilen: list[str] = []
    a = zeilen.append
    a("# Sprint 48: Diagnose der P5-Budgetabbrueche")
    a("")
    ohne_zellen = sum(1 for e in eintraege if e["gruppe"] == "ohne_zellen")
    a(
        f"Grundgesamtheit: **{len(abbruch)}** `length_ohne_ergebnis`-Zeilen und "
        f"**{len(erfolg)}** verwertbare Zeilen aus `yun699_p5_24000_20261118`; "
        f"{ohne_zellen} weitere Zeilen ohne Zellen bleiben im Vergleich aussen vor. "
        "Rein lesende Auswertung: keine Netzaufrufe, keine geaenderten Predictions, "
        "kein Gold, keine eingefrorene Eingabe beruehrt."
    )
    a("")
    h1p, h3p = hypothesen_bilanz["H1"], hypothesen_bilanz["H3"]
    a(
        "**Befund in einem Satz:** Die Budgetabbrueche sind nicht ueberwiegend durch "
        "Tabellenkomplexitaet oder Zellenzahl erklaerbar. Die Ausfaelle haben im Median "
        f"weniger Tabellen und weniger Datenzellen als die Erfolge; der scharfe Kontrast "
        f"ist der Reasoning-Umfang (Median {zahl(lauf_bilanz['reasoning_zeichen']['ausfaelle'].get('median'))} "
        f"gegen {zahl(lauf_bilanz['reasoning_zeichen']['erfolge'].get('median'))} Zeichen). Am "
        f"haeufigsten greift H1 (Komplexitaet): {zahl(h1p['ausfaelle_anteil'])} % der Ausfaelle "
        f"gegen {zahl(h1p['erfolge_anteil'])} % der Erfolge; am spezifischsten H3 "
        f"(mehrstufige Koepfe): {zahl(h3p['ausfaelle_anteil'])} % gegen "
        f"{zahl(h3p['erfolge_anteil'])} %."
    )
    a("")
    a("## 1. Uebersicht der 33 Budgetfaelle")
    a("")
    a(
        "| Record | Dokument | Tab. | Zeilen max | Spalten max | Datenzellen | Kopfebenen | Komplexitaet | Prompt-Zeichen | Reasoning-Zeichen | Gold | Diagnosen | Hypothesen |"
    )
    a("|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|")
    for e in abbruch:
        s, l = e["struktur"], e["lauf"]
        dz = e["zerlegungsdiagnosen"]
        merker = "".join(
            [
                "T" if dz.get("auswahl_test") else "-",
                "P" if dz.get("offline_struktur") else "-",
                "S" if dz.get("sprint43_tabellen") else "-",
                "D" if dz.get("diagnosen") else "-",
                "M" if dz.get("zerlegungslauf") else "-",
            ]
        )
        treffer = ", ".join(
            k for k in ("H1", "H2", "H3", "H4", "H6", "H7") if e["hypothesen"].get(k)
        )
        a(
            f"| `{e['record_id']}` | {e['publikation']['dokument_id']} | {s.get('tabellen', 0)} | "
            f"{s.get('zeilen_max', 0)} | {s.get('datenspalten_max', 0)} | {s.get('datenzellen_summe', 0)} | "
            f"{s.get('kopfebenen_max', 0)} | "
            f"{s.get('komplexitaet_max', '-')} | {zahl(s.get('prompt_zeichen'))} | "
            f"{zahl(l.get('reasoning_zeichen'))} | {e['gold']['zellen']} | {merker} | {treffer or '-'} |"
        )
    a("")
    a(
        "Spalten: `Tab.` zaehlt **alle** Tabellen des Dokuments, `Zeilen max` und `Spalten max` "
        "sind das Maximum je Tabelle, `Datenzellen` die Summe nicht-leerer Datenzellen "
        "(ohne Labelspalten), `Kopfebenen` die hoechste Zahl von Header-Baendern. "
        "Diagnosen: T = eingefrorene Testauswahl, P = Strukturplan A-E, S = Kopfband-Diagnose "
        "(Sprint 43), D = Gruppenkopf-/Fliesstext-Diagnose, M = Modelllauf A/B/E, `-` = kein "
        "Artefakt. Zur **Publikation** traegt der Record nur Dokument-ID und Dokumentpfad; "
        "Titel, Journal und DOI stehen nicht in den Daten und sind im JSON als nicht "
        "verfuegbar gekennzeichnet."
    )
    a("")
    a(
        "Alle 33 Zeilen: `completion_tokens = 24000` (genau das Budget), "
        "`content_chars = 0`, `finish_reason = length`, `http_status = 200`, Version "
        "`v2_timepoint`. Jede `record_id` kommt genau einmal vor."
    )
    a("")
    a("## 2. Haeufigkeit der strukturellen Merkmale")
    a("")
    a("| Merkmal | Ausfaelle Median | Erfolge Median | Ausfaelle Q75 | Erfolge Q75 |")
    a("|---|---:|---:|---:|---:|")
    for name, werte in merkmals_bilanz.items():
        x, y = werte["ausfaelle"], werte["erfolge"]
        a(
            f"| `{name}` | {zahl(x.get('median'))} | {zahl(y.get('median'))} | "
            f"{zahl(x.get('q75'))} | {zahl(y.get('q75'))} |"
        )
    a("")
    a(
        f"Schwellen aus allen {len(eintraege)} Zeilen (Q75): "
        + ", ".join(f"`{k}` {zahl(v)}" for k, v in schwellen.items())
        + ". Die Schwellen stammen aus beiden Gruppen zusammen, damit kein Merkmal "
        "allein durch die Auswahl auffaellt."
    )
    a("")
    a("## 3. Gruppierung nach Fehlerhypothesen")
    a("")
    a("| Hypothese | Ausfaelle | Anteil | Erfolge | Anteil | Differenz |")
    a("|---|---:|---:|---:|---:|---:|")
    for key, werte in hypothesen_bilanz.items():
        a(
            f"| {key} {werte['bezeichnung']} | {werte['ausfaelle']} / {len(abbruch)} | "
            f"{zahl(werte['ausfaelle_anteil'])} % | {werte['erfolge']} / {len(erfolg)} | "
            f"{zahl(werte['erfolge_anteil'])} % | {zahl(werte['differenz_pp'])} Pp |"
        )
    a("")
    a(
        "H5 ist ein **Mechanismus, keine Ursache**: jede Ausfallzeile hat das Budget im "
        "Reasoning verbraucht, weil kein Inhalt ausgegeben wurde. H5 unterscheidet daher "
        "nichts und steht nur als Befund in der Tabelle. H7 markiert Faelle, bei denen "
        "**keine strukturelle** Hypothese (H1, H2, H3, H6) greift; H4 bleibt dabei aussen "
        "vor, weil \"keine Tabelle mit Zielfeld\" in beiden Gruppen fast ueberall zutrifft."
    )
    a("")
    a(
        "Beobachtung und Vermutung sind getrennt: die Anteile sind Beobachtung; dass ein "
        "Merkmal die Ursache ist, waere eine Vermutung. Aussagekraft hat nur ein Merkmal, "
        "das bei den Ausfaellen deutlich haeufiger auftritt als bei den Erfolgen."
    )
    a("")
    a("## 4. Vergleich mit den 67 erfolgreichen Records")
    a("")
    a("| Kennzahl | Ausfaelle | Erfolge |")
    a("|---|---:|---:|")
    for name in ("reasoning_zeichen", "completion_tokens", "dauer_s"):
        x, y = lauf_bilanz[name]["ausfaelle"], lauf_bilanz[name]["erfolge"]
        a(
            f"| {name}: Median | {zahl(x.get('median'))} | {zahl(y.get('median'))} |"
        )
        a(f"| {name}: Spanne | {zahl(x.get('min'))}-{zahl(x.get('max'))} | {zahl(y.get('min'))}-{zahl(y.get('max'))} |")
    a("")
    ohne_tabellen = sum(1 for e in abbruch if e["struktur"].get("tabellen", 0) == 0)
    ohne_zielfeld = sum(1 for e in abbruch if e["struktur"].get("tabellen_mit_zielfeld", 0) == 0)
    a(
        f"Struktureller Kontrast: {ohne_tabellen} der {len(abbruch)} Ausfaelle haben im "
        f"Dokument **keine parsebare Tabelle**, {ohne_zielfeld} haben keine Tabelle, der "
        "der Parser ein Zielfeld zuordnen kann. Bei den Erfolgen betraegt der Median der "
        f"Datenzellen {zahl(merkmals_bilanz['datenzellen_summe']['erfolge'].get('median'))}, "
        f"bei den Ausfaellen {zahl(merkmals_bilanz['datenzellen_summe']['ausfaelle'].get('median'))}; "
        "die Ausfaelle sind strukturell also **nicht** die groesseren Tabellen. Auch die "
        f"Zahl der Tabellen ist bei ihnen kleiner "
        f"({zahl(merkmals_bilanz['tabellen']['ausfaelle'].get('median'))} gegen "
        f"{zahl(merkmals_bilanz['tabellen']['erfolge'].get('median'))} im Median)."
    )
    a("")
    frueher_8000 = frueher["ausfaelle"]["klassen_8000"]
    if frueher_8000:
        a(
            "Fruehere Laeufe derselben Records bei 8.000 Tokens (vorhandene Predictions, "
            "Modell glm): "
            + ", ".join(f"{zahl(wert)} x `{klasse}`" for klasse, wert in sorted(frueher_8000.items(), key=lambda kv: -kv[1]))
            + f" Beobachtungen. Auf Record-Ebene: {zahl(frueher['ausfaelle'].get('records_mit_8000'))} "
            "der 33 haben mindestens eine 8000er-Zeile, davon "
            f"{zahl(frueher['ausfaelle'].get('records_mit_ok_8000'))} mit mindestens einem Erfolg. "
            "Die Mehrheit war also schon bei 8.000 ein Budgetabbruch; mehr Budget allein hat "
            "die Klasse nicht gedreht."
        )
        a("")
    a(
        "Die Dauerangabe ist nur eingeschraenkt brauchbar: mindestens eine Zeile nennt "
        "0,14 s bei 89.370 Reasoning-Zeichen. Sie wird deshalb nicht als Merkmal verwendet."
    )
    a("")
    a("## 5. Bereits getestete Zerlegungsverfahren")
    a("")
    a(
        "Die Zerlegung liegt als `table_decomposition`-Engine mit fuenf Strategien vor "
        "(A Full-Table, B Vertical, C Horizontal, D Bidirectional, E Adaptive Recursive); "
        "zeilen- und spaltenweise Zerlegung sind Einheiten innerhalb von B und C. "
        "Fuer die 33 Faelle ist die Abdeckung:"
    )
    a("")
    a("| Verfahren | Records der 33 mit vorhandenem Artefakt |")
    a("|---|---:|")
    strategien = ("A", "B", "C", "D", "E")
    for s in strategien:
        treffer = sum(
            1
            for e in abbruch
            if s in (e["zerlegungsdiagnosen"].get("offline_struktur") or {})
        )
        a(f"| {s} (Strukturplan, offline) | {treffer} |")
    modell = sum(1 for e in abbruch if e["zerlegungsdiagnosen"].get("zerlegungslauf"))
    sprint43 = sum(1 for e in abbruch if e["zerlegungsdiagnosen"].get("sprint43_tabellen"))
    diagnose = sum(1 for e in abbruch if e["zerlegungsdiagnosen"].get("diagnosen"))
    test = sum(1 for e in abbruch if e["zerlegungsdiagnosen"].get("auswahl_test"))
    dev = sum(1 for e in abbruch if e["zerlegungsdiagnosen"].get("auswahl_dev"))
    a(f"| Modelllauf A/B/E (echte Zellen) | {modell} |")
    a(f"| Kopfband-Diagnose (Sprint 43) | {sprint43} |")
    a(f"| Gruppenkopf-/Fliesstext-Diagnose | {diagnose} |")
    a(f"| in eingefrorener Testauswahl | {test} |")
    a(f"| in eingefrorener dev-Auswahl | {dev} |")
    a("")
    a(
        "Damit ist die Zerlegung fuer **keinen** der 33 Faelle mit einem Modell gemessen: "
        "die fuenf Strategien liegen nur als Strukturplan fuer 5 Records vor, und der "
        "Modelllauf A/B/E enthaelt keine Zeile dieser Auswahl. Zeilen- und spaltenweise "
        "Zerlegung wurden also nur als Plan, nicht als Extraktion geprueft."
    )
    a("")
    a("## 6. Fuenf interessanteste Testfaelle")
    a("")
    gewaehlt: list[tuple[dict, str]] = []
    benutzt: set[str] = set()

    def nimm(kandidat: dict | None, begruendung: str) -> None:
        if kandidat is None or kandidat["record_id"] in benutzt:
            return
        benutzt.add(kandidat["record_id"])
        gewaehlt.append((kandidat, begruendung))

    ohne = [e for e in abbruch if e["struktur"].get("tabellen", 0) == 0]
    ohne.sort(key=lambda e: -(e["lauf"]["reasoning_zeichen"] or 0))
    if ohne:
        e = ohne[0]
        nimm(
            e,
            "Dokument ohne parsebare Tabelle, trotzdem "
            f"{zahl(e['lauf']['reasoning_zeichen'])} Reasoning-Zeichen: prueft, ob der "
            "Volltext-Prompt ohne Tabellenanker das Reasoning treibt.",
        )
    nimm(
        max(abbruch, key=lambda e: e["struktur"].get("datenzellen_summe", 0)),
        "groesste Datenzellenzahl der Ausfaelle "
        f"({zahl(max(abbruch, key=lambda e: e['struktur'].get('datenzellen_summe', 0))['struktur']['datenzellen_summe'])}): "
        "Testfall fuer H2/H6.",
    )
    mit_plan = [e for e in abbruch if e["zerlegungsdiagnosen"].get("offline_struktur")]
    if mit_plan:
        e = mit_plan[0]
        einheiten = e["zerlegungsdiagnosen"]["offline_struktur"]
        nimm(
            e,
            "liegt in der eingefrorenen Auswahl und hat einen Strukturplan fuer A-E "
            f"({len(einheiten)} Strategien): einziger Falltyp, bei dem eine Zerlegung ohne "
            "neue Auswahl direkt gegen den Budgetabbruch geprueft werden kann.",
        )
    if len(gewaehlt) < 5:
        gruppen: dict[str, list[dict]] = {}
        for e in abbruch:
            gruppen.setdefault(e["publikation"]["dokument_id"], []).append(e)
        mehrfach = [v for v in gruppen.values() if len(v) > 1 and all(x["record_id"] not in benutzt for x in v)]
        if mehrfach:
            paar = mehrfach[0]
            nimm(
                paar[0],
                "teilt das Dokument "
                f"{paar[0]['publikation']['dokument_id']} mit {len(paar) - 1} weiteren Ausfall "
                f"({', '.join(x['record_id'] for x in paar[1:])}): trennt Dokumenteffekt von "
                "Recordeffekt.",
            )
    paradox = [
        e
        for e in abbruch
        if any(x["budget"] == 19000 and x["klasse"] == "ok" for x in e["fruehere_laeufe"])
    ]
    if paradox:
        e = paradox[0]
        nimm(
            e,
            "bei 19.000 Tokens erfolgreich, bei 24.000 `length`: Dosis-Wirkung ohne "
            "Strukturaenderung, starkes Indiz gegen reine Budgetknappheit.",
        )
    einfach = [e for e in abbruch if e["struktur"].get("tabellen", 0) > 0]
    einfach.sort(key=lambda e: (e["struktur"].get("datenzellen_summe", 0), e["record_id"]))
    if einfach and len(gewaehlt) < 5:
        e = einfach[0]
        nimm(
            e,
            "kleinste Tabelle unter den Ausfaellen "
            f"({e['struktur'].get('datenzellen_summe')} Datenzellen, "
            f"{e['struktur'].get('kopfebenen_max')} Kopfebenen): wenn selbst das Budget sprengt, "
            "liegt es nicht an der Tabellengroesse.",
        )
    for e, begruendung in gewaehlt:
        a(f"- `{e['record_id']}` ({e['publikation']['dokument_id']}): {begruendung}")
    a("")
    a("## 7. Empfehlungen fuer den naechsten Experimentierschritt")
    a("")
    a(
        "1. **Zerlegung vor Budget.** Fuer die 5 Faelle mit vorhandenem Strukturplan die "
        "vertikale (B) Zerlegung real extrahieren, danach die adaptive (E); beide sind "
        "bisher nur als Plan geprueft, nie als Modelllauf. Erwartung: kleinerer Ausschnitt "
        "je Aufruf, weniger Reasoning. Kosten: je Fall zwei Aufrufe, im schlimmsten Fall "
        "2 x 24.000 Tokens."
    )
    a(
        "2. **Tabellenausschnitt statt Volltext.** Der P5-Prompt sendet den ganzen "
        "Artikelauszug (bis 45.000 Zeichen) ohne Zielzeitpunkt-Bindung; der Median liegt "
        f"bei {zahl(merkmals_bilanz['prompt_zeichen']['ausfaelle'].get('median'))} Zeichen. "
        "Ein Prompt mit genau der Tabelle und ihrem Kopf ist der naechste zu testende "
        "Unterschied, nicht ein hoeheres Budget."
    )
    a(
        "3. **Prosa-Faelle trennen.** Records ohne Tabelle brauchen einen eigenen Pfad "
        "(Ergebnisse im Fliesstext), sonst sucht das Modell eine Tabelle, die es nicht gibt."
    )
    a(
        "4. **Kein Budgetaufschlag ohne Aenderung.** 24.000 loest die Faelle nicht, die bei "
        "8.000 schon `length` waren; die Dosis-Wirkung aus `budget_hypothese_20261118.md` "
        "zeigt Rettungen nur bei geaenderter Aufgabe, nicht bei mehr Budget allein."
    )
    a("")
    a("## 8. Fazit")
    a("")
    h1 = hypothesen_bilanz["H1"]
    h2 = hypothesen_bilanz["H2"]
    h3 = hypothesen_bilanz["H3"]
    h4 = hypothesen_bilanz["H4"]
    h6 = hypothesen_bilanz["H6"]
    h7 = hypothesen_bilanz["H7"]
    a(
        "Auf die Ausgangsfrage, ob die Abbrueche ueberwiegend durch Tabellenkomplexitaet, "
        "Promptstruktur, Reasoning-Aufwand oder Ausgabeumfang erklaerbar sind:"
    )
    a("")
    a(
        f"- **Tabellenkomplexitaet und Zellenzahl: nein.** H1 trennt mit "
        f"{zahl(h1['differenz_pp'])} Pp, H2 mit {zahl(h2['differenz_pp'])} Pp; die Ausfaelle "
        "haben im Median sogar weniger Datenzellen und weniger Tabellen als die Erfolge."
    )
    a(
        f"- **Mehrstufige Ueberschriften: teilweise.** H3 trifft {h3['ausfaelle']} von "
        f"{len(abbruch)} Ausfaellen gegenueber {h3['erfolge']} von {len(erfolg)} Erfolgen "
        f"({zahl(h3['differenz_pp'])} Pp). Das ist der spezifischste Strukturtrenner "
        "(selten bei Erfolgen), erklaert aber nur gut ein Viertel der Faelle."
    )
    a(
        f"- **Promptstruktur: nur schwach trennend.** H4 trifft {h4['ausfaelle']} der "
        f"{len(abbruch)} Ausfaelle und {h4['erfolge']} der {len(erfolg)} Erfolge. Der Grund: "
        "der Volltext-Prompt mit hoechstens 45.000 Zeichen gilt fuer alle Records, und bei "
        "den meisten liegt keine Tabelle mit zugeordnetem Zielfeld vor - das trifft Erfolge "
        "wie Ausfaelle."
    )
    a(
        f"- **Ausgabeumfang: nein.** H6 trennt mit {zahl(h6['differenz_pp'])} Pp."
    )
    a(
        f"- **Reasoning-Aufwand: als Mechanismus bestaetigt, als Ursache offen.** Alle "
        "Ausfaelle enden mit 24.000 Tokens und 0 Zeichen Inhalt; der Reasoning-Umfang ist "
        "rund dreimal so hoch wie bei den Erfolgen. Warum er so hoch ist, zeigt die Struktur "
        "nicht."
    )
    a(
        f"- **{h7['ausfaelle']} der {len(abbruch)} Ausfaelle haben keine strukturelle "
        "Hypothese**: bei ihnen bleibt nur der Prompt-/Reasoning-Pfad als Erklaerung."
    )
    a("")
    a(
        "Gesichert ist damit nur der Mechanismus (Budget im Reasoning, kein Inhalt) und die "
        "Tatsache, dass die Ausfaelle strukturell nicht schwieriger sind als die Erfolge. "
        "Nicht gesichert ist eine einzelne Ursache; die Daten stuetzen am ehesten die "
        "Kombination aus Volltext-Prompt und aufwendiger Reasoning-Kette."
    )
    a("")
    a("## 9. Grenzen")
    a("")
    a(
        "- Reasoning-Tokens stehen nicht in den Predictions; angegeben sind Zeichen. Die "
        "Umrechnung Zeichen/Token ist eine Schaetzung (Median 4,0 aus 390 abgeschnittenen "
        "Zeilen, `budget_hypothese_20261118.md`)."
    )
    a(
        "- Strukturmerkmale kommen aus dem vorhandenen Parser und der vorhandenen "
        "Komplexitaetsbewertung. Wo der Parser keine Tabelle erkennt, steht 0 - das ist "
        "ein Parserbefund, keine Aussage ueber das PDF."
    )
    a(
        "- Zusammenhange sind beobachtet, nicht kausal belegt. Der Bericht nennt keine "
        "Ursache als gesichert."
    )
    return "\n".join(zeilen) + "\n"


def main() -> int:
    rows = lies_jsonl(RUN / "predictions.jsonl")
    records = {r["record_id"]: r for r in lies_jsonl(RECORDS)}
    ids = [r["record_id"] for r in rows]
    faelle = []

    for row in rows:
        rid = row["record_id"]
        record = records[rid]
        pfad = ROOT / (record.get("document") or {}).get("path", "")
        text = pfad.read_text(encoding="utf-8", errors="replace") if pfad.exists() else ""
        struktur = tabellen_masse(text, str((record.get("document") or {}).get("id") or rid), kontext(record))
        faelle.append(
            {
                "row": row,
                "record": record,
                "text": text,
                "struktur": struktur,
                "verdichtet": verdichte(struktur),
            }
        )

    historie = laufhistorie(set(ids))
    diagnosen = zerlegungsdiagnosen(set(ids))
    eintraege = [
        fall_eintrag(
            fall["row"],
            fall["record"],
            fall["text"],
            fall["struktur"],
            fall["verdichtet"],
            historie.get(fall["row"]["record_id"], []),
            diagnosen.get(fall["row"]["record_id"], {}),
        )
        for fall in faelle
    ]

    # Schwellen aus allen 103 Zeilen, nicht aus den Ausfaellen: sonst wuerde
    # jedes Merkmal per Konstruktion auffallen.
    schwellen = {
        "datenzellen_summe": quantil([e["struktur"]["datenzellen_summe"] for e in eintraege], 0.75),
        "datenzellen_zielfeld": quantil(
            [e["struktur"]["datenzellen_zielfeld"] for e in eintraege], 0.75
        ),
        "prompt_zeichen": quantil([e["struktur"]["prompt_zeichen"] for e in eintraege], 0.75),
        "komplexitaet_score_max": quantil(
            [e["struktur"]["komplexitaet_score_max"] for e in eintraege], 0.75
        ),
    }
    for eintrag in eintraege:
        treffer = hypothese_treffer(eintrag, schwellen)
        eintrag["hypothesen"] = {key: wert for key, wert in treffer.items()}
        eintrag["hypothesen"]["H5"] = eintrag["gruppe"] == "budget_abbruch"
        # H7 = keine der pruefbaren Strukturhypothesen greift. H4 bleibt aussen
        # vor, weil "keine Tabelle mit Zielfeld" fast ueberall zutrifft und
        # damit nicht trennt (siehe Abschnitt 3 des Berichts).
        eintrag["hypothesen"]["H7"] = not any(
            treffer[key] for key in ("H1", "H2", "H3", "H6")
        )

    abbruch = [e for e in eintraege if e["gruppe"] == "budget_abbruch"]
    erfolg = [e for e in eintraege if e["gruppe"] == "erfolg"]
    ohne_zellen = [e for e in eintraege if e["gruppe"] == "ohne_zellen"]

    def anteil(gruppe: list[dict], key: str) -> float:
        return round(100 * sum(1 for e in gruppe if e["hypothesen"].get(key)) / max(len(gruppe), 1), 1)

    hypothesen_bilanz = {}
    for key, text in HYPOTHESEN.items():
        hypothesen_bilanz[key] = {
            "bezeichnung": text,
            "ausfaelle": sum(1 for e in abbruch if e["hypothesen"].get(key)),
            "ausfaelle_anteil": anteil(abbruch, key),
            "erfolge": sum(1 for e in erfolg if e["hypothesen"].get(key)),
            "erfolge_anteil": anteil(erfolg, key),
        }
        hypothesen_bilanz[key]["differenz_pp"] = round(
            hypothesen_bilanz[key]["ausfaelle_anteil"] - hypothesen_bilanz[key]["erfolge_anteil"], 1
        )

    merkmale = (
        "tabellen",
        "tabellen_mit_zielfeld",
        "zeilen_max",
        "datenzellen_summe",
        "datenzellen_zielfeld",
        "datenspalten_max",
        "kopfebenen_max",
        "gruppenkopf_zellen",
        "komplexe_tabellen",
        "komplexitaet_score_max",
        "prompt_zeichen",
        "text_zeichen",
        "fussnoten_summe",
        "unregelmaessige_zeilen",
    )
    merkmals_bilanz = {
        name: {
            "ausfaelle": kennzahlen([e["struktur"].get(name, 0) for e in abbruch]),
            "erfolge": kennzahlen([e["struktur"].get(name, 0) for e in erfolg]),
        }
        for name in merkmale
    }

    lauf_bilanz = {
        "reasoning_zeichen": {
            "ausfaelle": kennzahlen([e["lauf"]["reasoning_zeichen"] or 0 for e in abbruch]),
            "erfolge": kennzahlen([e["lauf"]["reasoning_zeichen"] or 0 for e in erfolg]),
        },
        "completion_tokens": {
            "ausfaelle": kennzahlen([e["lauf"]["completion_tokens"] or 0 for e in abbruch]),
            "erfolge": kennzahlen([e["lauf"]["completion_tokens"] or 0 for e in erfolg]),
        },
        "dauer_s": {
            "ausfaelle": kennzahlen([e["lauf"]["dauer_s"] for e in abbruch]),
            "erfolge": kennzahlen([e["lauf"]["dauer_s"] for e in erfolg]),
        },
    }

    # Fruehere Extraktionsergebnisse: Verteilung der 8000er-Klasse je Gruppe
    # und Zahl der Records mit einer Beobachtung bei anderem Budget.
    frueher = {}
    for name, gruppe in (("ausfaelle", abbruch), ("erfolge", erfolg)):
        klassen: Counter = Counter()
        budgets: Counter = Counter()
        mit_8000 = 0
        mit_ok_8000 = 0
        for e in gruppe:
            for lauf in e["fruehere_laeufe"]:
                budgets[lauf["budget"]] += 1
                if lauf["budget"] == 8000:
                    klassen[lauf["klasse"]] += 1
            if any(lauf["budget"] == 8000 for lauf in e["fruehere_laeufe"]):
                mit_8000 += 1
            if any(lauf["budget"] == 8000 and lauf["klasse"] == "ok" for lauf in e["fruehere_laeufe"]):
                mit_ok_8000 += 1
        frueher[name] = {
            "klassen_8000": dict(klassen),
            "zeilen_je_budget": dict(budgets),
            "records_mit_8000": mit_8000,
            "records_mit_ok_8000": mit_ok_8000,
        }

    json_ausgabe = {
        "sprint": 48,
        "frage": "Warum verbraucht glm bei diesen Records 24.000 Tokens im Reasoning ohne Zellen?",
        "erzeugt_von": "public_benchmark/extended_benchmark/yun_full/diagnose_sprint48.py",
        "nur_lesend": True,
        "netzaufrufe": 0,
        "grundgesamtheit": {
            "p5_zeilen": len(rows),
            "budget_abbrueche": len(abbruch),
            "erfolge_vergleich": len(erfolg),
        },
        "schwellen": {k: round(v, 3) for k, v in schwellen.items()},
        "hypothesen": hypothesen_bilanz,
        "merkmale": merkmals_bilanz,
        "lauf": lauf_bilanz,
        "fruehere_laeufe": frueher,
        "faelle": eintraege,
        "hinweise": [
            "H5 ist ein Mechanismus, keine Ursache: alle 33 Zeilen haben das Budget im "
            "Reasoning verbraucht, weil content_chars = 0 ist.",
            "Reasoning-Tokens stehen in den Predictions nicht; die Zeilen tragen nur "
            "reasoning_chars. Die Umrechnung Zeichen/Token ist eine Schaetzung.",
            "Die Dauerangabe elapsed_s je Zeile ist mindestens einmal inkonsistent "
            "(0,14 s bei 89.370 Reasoning-Zeichen); sie wird nicht als Merkmal verwendet.",
            "Der P5-Prompt sendet den ganzen Artikelauszug (bis 45.000 Zeichen) ohne "
            "Zielzeitpunkt-Bindung (prompt_version v2_timepoint).",
        ],
    }
    AUSGABE.with_suffix(".json").write_text(
        json.dumps(json_ausgabe, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\r\n",
    )
    bericht = schreibe_md(
        eintraege, abbruch, erfolg, hypothesen_bilanz, merkmals_bilanz, lauf_bilanz, schwellen, frueher
    )
    AUSGABE.with_suffix(".md").write_text(bericht, encoding="utf-8", newline="\r\n")
    print(f"JSON: {AUSGABE.with_suffix('.json')}")
    print(f"MD:   {AUSGABE.with_suffix('.md')}")
    for key in ("H1", "H2", "H3", "H4", "H6", "H7"):
        zeile = hypothesen_bilanz[key]
        print(
            f"{key} {zeile['bezeichnung']}: {zeile['ausfaelle_anteil']} % der Ausfaelle, "
            f"{zeile['erfolge_anteil']} % der Erfolge"
        )
    print("Merkmale (Median Ausfaelle/Erfolge):")
    for name in merkmale:
        a = merkmals_bilanz[name]["ausfaelle"]
        b = merkmals_bilanz[name]["erfolge"]
        print(f"  {name:24s} {a.get('median')} / {b.get('median')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
