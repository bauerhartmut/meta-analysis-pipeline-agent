"""Tokenzaehler fuer alle Aufrufe an TUDaGPT.

Zwei Quellen, ein Bericht:

- ``data/tudagpt_tokens.jsonl`` (Ledger): eine Zeile je Antwort, geschrieben von
  Aufrufern, die selbst mit dem Gateway sprechen. Beide Zahlen kommen aus dem
  ``usage``-Block der Antwort, nichts wird geschaetzt. Der Ledger liegt in
  ``data/`` und ist nicht versioniert.
- ``llm_usage`` in ``data/*.db``: der Agent-Pfad schreibt dort je Aufruf Input-
  und Output-Tokens; diese Zeilen entstehen bereits, ohne dass hier etwas
  nachgetragen werden muss.

``bericht()`` fuehrt beide zusammen und listet Aufrufe, Input- und Output-Tokens
je Modell, Tag und Stunde. Fehlt eine Quelle, bleibt sie einfach leer; es wird
kein Wert ergaenzt oder hochgerechnet.

Abdeckung: gezaehlt wird, was diese Quellen belegen. Der Ledger wird derzeit vom
erweiterten Extraktions-Harness geschrieben (``public_benchmark/extended_benchmark/
run_extended_extraction.py``, inklusive Retry- und Reparaturaufrufen, weil alle
ueber ``_call_once`` laufen). Einmal-Skripte mit eigenem HTTP-Aufruf
(``run_stage_extraction.py``, ``iterativ/zell_retrieval.py``,
``table_decomposition/run_benchmark.py``, ``scripts/diagnose_glm.py``,
``scripts/goldstandard/run_tier1_extraction.py``) sind noch nicht angebunden.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "data" / "tudagpt_tokens.jsonl"
DB_MUSTER = "data/*.db"

# Zwei Threads duerfen gleichzeitig schreiben (der Harness laeuft mit --workers 2+).
_SCHREIBSPERRE = threading.Lock()


def zaehle(
    modell: str,
    prompt_tokens: Any,
    completion_tokens: Any,
    *,
    quelle: str = "",
    backend: str = "tudagpt",
    zeitpunkt: datetime | None = None,
    ledger: str | Path | None = None,
) -> bool:
    """Schreibt einen Aufruf in den Ledger.

    Gibt ``False`` zurueck, wenn nichts zu zaehlen war oder das Schreiben
    scheiterte. Die Funktion wirft nie: Buchfuehrung darf keinen Lauf stoppen.
    """
    try:
        eingang = int(prompt_tokens or 0)
        ausgang = int(completion_tokens or 0)
    except (TypeError, ValueError):
        eingang, ausgang = 0, 0
    if eingang <= 0 and ausgang <= 0:
        return False

    jetzt = zeitpunkt or datetime.now().astimezone()
    zeile = {
        "ts": jetzt.isoformat(timespec="seconds"),
        "tag": jetzt.strftime("%Y-%m-%d"),
        "stunde": jetzt.strftime("%H"),
        "modell": str(modell or "unbekannt"),
        "backend": str(backend or ""),
        "quelle": str(quelle or ""),
        "prompt_tokens": eingang,
        "completion_tokens": ausgang,
        "total_tokens": eingang + ausgang,
    }
    # TUDAGPT_TOKEN_LEDGER umbiegen ist fuer Tests und Einmal-Skripte gedacht,
    # damit sie die echte Buchfuehrung nicht mit Attrappen fuellen.
    pfad = Path(ledger or os.environ.get("TUDAGPT_TOKEN_LEDGER") or LEDGER)
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with _SCHREIBSPERRE, pfad.open("a", encoding="utf-8") as datei:
            datei.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def lade_ledger(pfad: str | Path | None = None) -> list[dict[str, Any]]:
    """Liest den Ledger; kaputte Zeilen werden uebersprungen, nicht geraten."""
    quelle = Path(pfad) if pfad else LEDGER
    if not quelle.exists():
        return []
    zeilen: list[dict[str, Any]] = []
    for roh in quelle.read_text(encoding="utf-8", errors="replace").splitlines():
        if not roh.strip():
            continue
        try:
            eintrag = json.loads(roh)
        except json.JSONDecodeError:
            continue
        if isinstance(eintrag, dict) and eintrag.get("modell"):
            zeilen.append(eintrag)
    return zeilen


def lade_usage_dbs(muster: str = DB_MUSTER, basis: str | Path | None = None) -> list[dict[str, Any]]:
    """Liest ``llm_usage`` aus allen passenden Datenbanken, ausschliesslich lesend."""
    wurzel = Path(basis) if basis else REPO
    zeilen: list[dict[str, Any]] = []
    for pfad in sorted(wurzel.glob(muster)):
        try:
            verbindung = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            reihen = verbindung.execute(
                "SELECT timestamp, day, phase, backend, model, prompt_tokens, completion_tokens "
                "FROM llm_usage"
            ).fetchall()
        except sqlite3.Error:
            reihen = []
        finally:
            verbindung.close()
        for ts, tag, phase, backend, modell, eingang, ausgang in reihen:
            ts = str(ts or "")
            zeilen.append(
                {
                    "ts": ts,
                    "tag": str(tag or ts[:10] or "unbekannt"),
                    "stunde": ts[11:13] or "??",
                    "modell": str(modell or "unbekannt"),
                    "backend": str(backend or ""),
                    "quelle": f"llm_usage:{pfad.name}:{phase or ''}",
                    "prompt_tokens": int(eingang or 0),
                    "completion_tokens": int(ausgang or 0),
                    "total_tokens": int(eingang or 0) + int(ausgang or 0),
                }
            )
    return zeilen


def eintraege(
    ledger: str | Path | None = None,
    db_muster: str = DB_MUSTER,
    basis: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Beide Quellen zusammen, ohne doppelte Zeilen."""
    alle = lade_usage_dbs(db_muster, basis) + lade_ledger(ledger)
    gesehen: set[tuple] = set()
    eindeutig: list[dict[str, Any]] = []
    for zeile in alle:
        schluessel = (
            zeile.get("ts", ""),
            zeile.get("modell", ""),
            zeile.get("prompt_tokens", 0),
            zeile.get("completion_tokens", 0),
        )
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        eindeutig.append(zeile)
    return eindeutig


def gruppiere(
    zeilen: Iterable[dict[str, Any]],
    *,
    modell: str | None = None,
    seit: str | None = None,
    bis: str | None = None,
) -> list[dict[str, Any]]:
    """Summen je (Tag, Stunde, Modell), sortiert nach Tag und Stunde."""
    summen: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {"aufrufe": 0, "prompt_tokens": 0, "completion_tokens": 0}
    )
    for zeile in zeilen:
        name = str(zeile.get("modell") or "unbekannt")
        if modell and name != modell:
            continue
        tag = str(zeile.get("tag") or "unbekannt")
        if seit and tag < seit:
            continue
        if bis and tag > bis:
            continue
        gruppe = summen[(tag, str(zeile.get("stunde") or "??"), name)]
        gruppe["aufrufe"] += 1
        gruppe["prompt_tokens"] += int(zeile.get("prompt_tokens") or 0)
        gruppe["completion_tokens"] += int(zeile.get("completion_tokens") or 0)
    return [
        {
            "tag": tag,
            "stunde": stunde,
            "modell": name,
            "aufrufe": werte["aufrufe"],
            "prompt_tokens": werte["prompt_tokens"],
            "completion_tokens": werte["completion_tokens"],
            "total_tokens": werte["prompt_tokens"] + werte["completion_tokens"],
        }
        for (tag, stunde, name), werte in sorted(summen.items())
    ]


def _summen(zeilen: Iterable[dict[str, Any]], feld: str) -> list[tuple[str, int, int, int]]:
    summen: dict[str, dict[str, int]] = defaultdict(
        lambda: {"aufrufe": 0, "prompt_tokens": 0, "completion_tokens": 0}
    )
    for zeile in zeilen:
        gruppe = summen[str(zeile.get(feld) or "unbekannt")]
        gruppe["aufrufe"] += zeile["aufrufe"]
        gruppe["prompt_tokens"] += zeile["prompt_tokens"]
        gruppe["completion_tokens"] += zeile["completion_tokens"]
    return [
        (name, werte["aufrufe"], werte["prompt_tokens"], werte["completion_tokens"])
        for name, werte in sorted(summen.items())
    ]


def _zahl(wert: Any) -> str:
    """Tausenderpunkte, ohne Satzzeichen des Berichts anzufassen."""
    return f"{int(wert or 0):,}".replace(",", ".")


def bericht(gruppen: list[dict[str, Any]], *, titel: str = "TUDaGPT-Tokens") -> str:
    """Markdown-Bericht: je Tag/Stunde/Modell, dann Summen je Modell und Tag."""
    if not gruppen:
        return (
            f"# {titel}\n\nKeine Aufrufe gezaehlt. Der Ledger ist leer und die "
            "`llm_usage`-Tabellen in `data/*.db` enthalten keine Zeilen.\n"
        )

    zeilen = [
        f"# {titel}",
        "",
        "| Tag | Stunde | Modell | Aufrufe | Input | Output | Gesamt |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for g in gruppen:
        zeilen.append(
            f"| {g['tag']} | {g['stunde']} | `{g['modell']}` | {g['aufrufe']} | "
            f"{_zahl(g['prompt_tokens'])} | {_zahl(g['completion_tokens'])} | {_zahl(g['total_tokens'])} |"
        )

    gesamt_aufrufe = sum(g["aufrufe"] for g in gruppen)
    gesamt_ein = sum(g["prompt_tokens"] for g in gruppen)
    gesamt_aus = sum(g["completion_tokens"] for g in gruppen)

    zeilen += ["", "## Summe je Modell", "", "| Modell | Aufrufe | Input | Output | Gesamt |", "|---|---:|---:|---:|---:|"]
    for name, aufrufe, ein, aus in _summen(gruppen, "modell"):
        zeilen.append(
            f"| `{name}` | {aufrufe} | {_zahl(ein)} | {_zahl(aus)} | {_zahl(ein + aus)} |"
        )

    zeilen += ["", "## Summe je Tag", "", "| Tag | Aufrufe | Input | Output | Gesamt |", "|---|---:|---:|---:|---:|"]
    for tag, aufrufe, ein, aus in _summen(gruppen, "tag"):
        zeilen.append(f"| {tag} | {aufrufe} | {_zahl(ein)} | {_zahl(aus)} | {_zahl(ein + aus)} |")

    zeilen += [
        "",
        f"Gesamt: {_zahl(gesamt_aufrufe)} Aufrufe, {_zahl(gesamt_ein)} Input-Tokens, "
        f"{_zahl(gesamt_aus)} Output-Tokens, {_zahl(gesamt_ein + gesamt_aus)} Tokens.",
        "",
        "Input und Output stammen aus dem `usage`-Block der Antwort. Laeufe vor dem "
        "Ledger tragen nur die Zeilen, die der Agent-Pfad in `llm_usage` abgelegt hat.",
    ]
    return "\n".join(zeilen) + "\n"
