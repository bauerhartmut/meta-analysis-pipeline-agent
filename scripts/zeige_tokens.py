#!/usr/bin/env python3
"""Zeigt die TUDaGPT-Tokens je Modell, Tag und Stunde.

Quellen: `data/tudagpt_tokens.jsonl` (vom Harness geschrieben) und die
`llm_usage`-Tabellen in `data/*.db` (Agent-Pfad). Es wird nichts geschaetzt.

Aufruf:
    .venv/bin/python scripts/zeige_tokens.py
    .venv/bin/python scripts/zeige_tokens.py --modell gwdg/glm-5.3 --seit 2026-11-18
    .venv/bin/python scripts/zeige_tokens.py --md docs/internal/token_zaehler.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from research_agent.llm import token_zaehler  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default=str(token_zaehler.LEDGER))
    parser.add_argument("--db-muster", default=token_zaehler.DB_MUSTER)
    parser.add_argument("--modell", default="", help="nur dieses Modell")
    parser.add_argument("--seit", default="", help="Tag ab (YYYY-MM-DD)")
    parser.add_argument("--bis", default="", help="Tag bis (YYYY-MM-DD)")
    parser.add_argument("--md", default="", help="Bericht zusaetzlich als Markdown ablegen")
    parser.add_argument("--json", default="", help="Rohzeilen zusaetzlich als JSON ablegen")
    parser.add_argument("--still", action="store_true", help="nichts auf der Konsole ausgeben")
    args = parser.parse_args()

    zeilen = token_zaehler.eintraege(args.ledger, args.db_muster)
    gruppen = token_zaehler.gruppiere(
        zeilen,
        modell=args.modell or None,
        seit=args.seit or None,
        bis=args.bis or None,
    )
    text = token_zaehler.bericht(gruppen)

    if args.md:
        ziel = Path(args.md)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
    if args.json:
        ziel = Path(args.json)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(gruppen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.still:
        print(text)
    return 0 if gruppen else 1


if __name__ == "__main__":
    raise SystemExit(main())
