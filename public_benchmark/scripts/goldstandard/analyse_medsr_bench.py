"""Prüfung: Passt MedSR-Bench auf die ``study_effects``-Struktur des Projekts?

Hintergrund: MedSR-Bench (Hugging Face ``halfmorepiece/MedSR-Bench``) ist ein
Benchmark aus 100 Cochrane-Reviews mit Include-Listen, Analyse-Gruppen,
Armwerten und dreiklassigen Zielkonklusionen. Der Datensatz ist aus der
Cochrane Library abgeleitet; die Cochrane-Nutzungsbedingungen verlangen für
KI-Nutzung eine ausdrückliche Genehmigung. Dieses Skript trifft deshalb keine
Nutzungsentscheidung, sondern misst nur die *Struktur*: welche Felder vorhanden
sind, wie viele Analyse-Gruppen einen Effekt mit Standardfehler liefern, ob
Provenienzangaben existieren und ob die Studiennamen zu den Gruppen passen.

Das Skript rechnet nichts nach und ruft kein Modell auf. Es lädt die 100
JSON-Dateien (rund 10 MB) in einen Cache, der wegen der ungeklärten Lizenz
gitignored ist, und schreibt zwei versionierbare Aggregate:

- ``manifest.json`` — Quellen, SHA-256, Zählungen
- ``mapping_report.json`` und ``medsr_bench_mapping.md`` — Feldabdeckung

Aufruf::

    python public_benchmark/scripts/goldstandard/analyse_medsr_bench.py
    python public_benchmark/scripts/goldstandard/analyse_medsr_bench.py --offline
    python public_benchmark/scripts/goldstandard/analyse_medsr_bench.py --probe-pmids 40

``--probe-pmids`` prüft zusätzlich für eine deterministische Stichprobe von
PMIDs, ob Europe PMC einen offenen Volltext führt. Das ist die entscheidende
Frage für eine Extraktionsprüfung: ohne Volltext kein Lesegegenstand.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HF_BASE = "https://huggingface.co/datasets/halfmorepiece/MedSR-Bench/resolve/main/"
HF_API = "https://huggingface.co/api/datasets/halfmorepiece/MedSR-Bench"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

HERE = Path(__file__).resolve()
CROSSVAL = HERE.parents[2] / "evaluation" / "multi_model_cross_validation"
OUT = CROSSVAL / "goldstandard_datasets" / "medsr_bench_v1"
CACHE = OUT / "original" / "MedSR-Bench-json"
REPORT_MD = CROSSVAL / "medsr_bench_mapping.md"

N_REVIEWS = 100
META_KEYS = {"PICO", "trials", "study group", "date"}
Z95 = 2 * 1.959963984540054


def fetch_json(url: str, timeout: int = 60) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "meta-analysis-agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as handle:
        return json.loads(handle.read().decode("utf-8", "replace"))


def num(value: Any) -> float | None:
    """Zahl aus dem String-Feld lesen; leere und unlesbare Werte werden ``None``."""
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def review_path(number: int) -> Path:
    return CACHE / f"{number}.json"


def ensure_reviews(offline: bool) -> list[Path]:
    CACHE.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    missing = 0
    for number in range(1, N_REVIEWS + 1):
        path = review_path(number)
        if not path.exists() or path.stat().st_size == 0:
            if offline:
                raise SystemExit(f"fehlt im Cache: {path} (--offline gesetzt)")
            url = f"{HF_BASE}MedSR-Bench-json/{number}.json"
            for attempt in range(3):
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "meta-analysis-agent/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=90) as handle:
                        payload = handle.read()
                    path.write_bytes(payload)
                    break
                except (urllib.error.URLError, TimeoutError) as exc:
                    if attempt == 2:
                        raise SystemExit(f"Download fehlgeschlagen {url}: {exc}")
                    time.sleep(1.5 * (attempt + 1))
            missing += 1
            time.sleep(0.05)
        paths.append(path)
    if missing:
        print(f"  {missing} Dateien neu geladen")
    return paths


def study_blocks(review: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Die Studienblöcke eines Reviews: Schlüssel ist der Studienname."""
    blocks: dict[str, list[dict[str, Any]]] = {}
    for key, value in review.items():
        if key in META_KEYS:
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict):
            if "group num" in value[0]:
                blocks[key] = value
    return blocks


def is_continuous(study_group: dict[str, Any]) -> bool:
    return str(study_group.get("Data type", "")).strip().lower().startswith("cont")


def arm_values_complete(row: dict[str, Any], continuous: bool) -> bool:
    if continuous:
        keys = ("Experimental mean", "Experimental SD", "Experimental N",
                "Control mean", "Control SD", "Control N")
    else:
        keys = ("Experimental cases", "Experimental N", "Control cases", "Control N")
    return all(num(row.get(key)) is not None for key in keys)


def effect_and_ci(row: dict[str, Any]) -> tuple[float | None, float | None]:
    effect = num(row.get("Mean"))
    low = num(row.get("CI start"))
    high = num(row.get("CI end"))
    if effect is None or low is None or high is None:
        return None, None
    if high < low:
        low, high = high, low
    return effect, (high - low) / Z95


def implied_z(row: dict[str, Any]) -> float | None:
    """Prüft, ob das berichtete KI zu den Armwerten passt (nur Mean Difference).

    Bei einer Mittelwertdifferenz gilt se = sqrt(sd1^2/n1 + sd2^2/n2). Ist das
    KI ein 95-%-KI, muss (high - low) / (2 * se) nahe 1,96 liegen, also
    (high - low) / se nahe 3,92.
    """
    low = num(row.get("CI start"))
    high = num(row.get("CI end"))
    sd1 = num(row.get("Experimental SD"))
    sd2 = num(row.get("Control SD"))
    n1 = num(row.get("Experimental N"))
    n2 = num(row.get("Control N"))
    if None in (low, high, sd1, sd2, n1, n2) or min(n1, n2) <= 0:
        return None
    se = math.sqrt(sd1 * sd1 / n1 + sd2 * sd2 / n2)
    if se <= 0 or high < low:
        return None
    return (high - low) / se


def eprint_status(pmid: str) -> str:
    url = f"{EPMC}?query=EXT_ID:{pmid}&format=json&resultType=core&pageSize=1"
    for attempt in range(2):
        try:
            data = fetch_json(url, timeout=30)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 1:
                return "error"
            time.sleep(1.0)
            continue
        hits = data.get("resultList", {}).get("result", [])
        if not hits:
            return "notfound"
        first = hits[0]
        if first.get("isOpenAccess") == "Y":
            return "oa"
        if first.get("pmcid"):
            return "pmc_no_oa"
        return "paywall"
    return "error"


def probe_pmids(reviews: dict[int, dict[str, Any]], limit: int) -> dict[str, Any]:
    """Deterministisch die ersten PMIDs je Review prüfen, bis das Limit erreicht ist."""
    statuses: Counter[str] = Counter()
    checked = 0
    per_review: list[dict[str, Any]] = []
    for number in sorted(reviews):
        if checked >= limit:
            break
        include = [
            str(t.get("pmid", "")).strip()
            for t in reviews[number].get("trials", [])
            if t.get("relation_type") == "include" and str(t.get("pmid", "")).strip()
        ]
        take = include[: max(1, limit // 10)]
        review_status = Counter()
        for pmid in take:
            if checked >= limit:
                break
            status = eprint_status(pmid)
            statuses[status] += 1
            review_status[status] += 1
            checked += 1
            time.sleep(0.3)
        per_review.append(
            {"review": number, "checked": sum(review_status.values()),
             "status": dict(review_status)}
        )
    return {
        "checked": checked,
        "by_status": dict(statuses),
        "method": "erste PMIDs je Review in numerischer Reihenfolge, Europe PMC EXT_ID",
        "per_review": per_review,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="nur den Cache lesen")
    parser.add_argument(
        "--probe-pmids", type=int, default=0,
        help="so viele PMIDs auf offenen Volltext prüfen (0 = aus)",
    )
    args = parser.parse_args()

    paths = ensure_reviews(args.offline)
    reviews: dict[int, dict[str, Any]] = {}
    for path in paths:
        reviews[int(path.stem)] = json.loads(path.read_text(encoding="utf-8"))

    groups = 0
    rows = 0
    groups_by_type: Counter[str] = Counter()
    groups_by_measure: Counter[str] = Counter()
    conclusion_classes: Counter[str] = Counter()
    groups_with_conclusion = 0
    groups_with_effect_ci = 0
    groups_k_ge_2 = 0
    groups_poolable = 0
    groups_without_rows = 0
    rows_with_effect_ci = 0
    rows_arm_complete_continuous = 0
    rows_arm_complete_binary = 0
    unmatched_names = 0
    checked_names = 0
    orphan_reviews: list[int] = []
    z_values: list[float] = []
    provenance_found: set[str] = set()
    trials_total = 0
    trials_include = 0
    trials_by_relation: Counter[str] = Counter()
    duplicate_group_numbers = 0

    for number, review in reviews.items():
        blocks = study_blocks(review)
        trials = review.get("trials", []) or []
        trials_total += len(trials)
        trials_include += sum(1 for t in trials if t.get("relation_type") == "include")
        for trial in trials:
            key = str(trial.get("relation_type", "")).strip() or "(leer)"
            trials_by_relation[key] += 1

        study_groups = review.get("study group", []) or []
        measure_by_group: dict[str, str] = {}
        group_number_counts: Counter[str] = Counter()
        for study_group in study_groups:
            group_no = str(study_group.get("group num", "")).strip()
            group_number_counts[group_no] += 1
            measure_by_group.setdefault(
                group_no, str(study_group.get("Effect measure", "")).strip()
            )
        duplicate_group_numbers += sum(1 for c in group_number_counts.values() if c > 1)

        by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for block in blocks.values():
            for row in block:
                group_no = str(row.get("group num", "")).strip()
                by_group[group_no].append(row)
                rows += 1
                effect, se = effect_and_ci(row)
                if effect is not None and se is not None:
                    rows_with_effect_ci += 1
                continuous_complete = arm_values_complete(row, True)
                if continuous_complete:
                    rows_arm_complete_continuous += 1
                    if measure_by_group.get(group_no, "").strip().lower() == "mean difference":
                        z = implied_z(row)
                        if z is not None:
                            z_values.append(z)
                elif arm_values_complete(row, False):
                    rows_arm_complete_binary += 1

        review_orphans = 0
        for study_group in study_groups:
            groups += 1
            group_no = str(study_group.get("group num", "")).strip()
            data_type = str(study_group.get("Data type", "")).strip() or "(leer)"
            measure = str(study_group.get("Effect measure", "")).strip() or "(leer)"
            groups_by_type[data_type] += 1
            groups_by_measure[measure] += 1

            conclusion = str(study_group.get("gt conclusion", "")).strip()
            if conclusion:
                groups_with_conclusion += 1
                conclusion_classes[conclusion] += 1

            names = [
                part.strip()
                for part in str(study_group.get("data_studies", "")).split(",")
                if part.strip()
            ]
            for name in names:
                checked_names += 1
                if name not in blocks:
                    unmatched_names += 1

            group_rows = by_group.get(group_no, [])
            if not group_rows:
                review_orphans += 1
            if len(group_rows) >= 2:
                groups_k_ge_2 += 1

            continuous = is_continuous(study_group)
            usable = sum(1 for row in group_rows if effect_and_ci(row)[1] is not None)
            complete = sum(1 for row in group_rows if arm_values_complete(row, continuous))
            if group_rows and usable == len(group_rows) and len(group_rows) >= 2:
                groups_with_effect_ci += 1
                groups_poolable += 1
            if complete == 0:
                groups_without_rows += 1
        if review_orphans:
            orphan_reviews.append(number)

    provenance_found = set()
    for review in list(reviews.values())[:20]:
        for block in study_blocks(review).values():
            for row in block[:2]:
                for key in row:
                    lowered = key.lower()
                    if any(n in lowered for n in ("page", "table", "quote", "locator", "cell", "snippet", "section")):
                        provenance_found.add(key)
        for study_group in review.get("study group", [])[:2]:
            for key in study_group:
                lowered = key.lower()
                if any(n in lowered for n in ("page", "table", "quote", "locator", "cell", "snippet", "section")):
                    provenance_found.add(key)

    sha = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)
    }
    total_bytes = sum(path.stat().st_size for path in paths)

    review_findings = {
        "reviews": len(reviews),
        "trials_total": trials_total,
        "trials_include": trials_include,
        "trials_by_relation": dict(trials_by_relation),
        "analysis_groups": groups,
        "duplicate_group_numbers": duplicate_group_numbers,
        "study_rows": rows,
        "groups_by_data_type": dict(groups_by_type),
        "groups_by_effect_measure": dict(groups_by_measure),
        "groups_with_conclusion": groups_with_conclusion,
        "conclusion_classes": dict(conclusion_classes),
        "groups_with_at_least_2_studies": groups_k_ge_2,
        "groups_all_rows_with_effect_and_ci": groups_with_effect_ci,
        "groups_poolable": groups_poolable,
        "groups_without_any_complete_arm_row": groups_without_rows,
        "rows_with_effect_and_ci": rows_with_effect_ci,
        "rows_arm_complete_continuous": rows_arm_complete_continuous,
        "rows_arm_complete_binary": rows_arm_complete_binary,
        "study_names_in_data_studies": checked_names,
        "study_names_unmatched": unmatched_names,
        "reviews_with_orphan_groups": orphan_reviews,
        "implied_ci_z": {
            "n": len(z_values),
            "median": round(statistics.median(z_values), 4) if z_values else None,
            "share_within_3_6_to_4_2": (
                round(sum(1 for z in z_values if 3.6 <= z <= 4.2) / len(z_values), 4)
                if z_values else None
            ),
            "expected_95_percent": round(Z95, 4),
        },
        "provenance_like_fields": sorted(provenance_found),
    }

    manifest = {
        "dataset": "medsr_bench_v1",
        "source": "https://huggingface.co/datasets/halfmorepiece/MedSR-Bench",
        "publication": (
            "A PRISMA-Aligned Agentic Framework for Medical Systematic Reviews and "
            "Evidence Synthesis (medRxiv, Preprint, 2026)"
        ),
        "license_declared_by_uploader": "apache-2.0",
        "license_note": (
            "Inhalt aus der Cochrane Library abgeleitet. Die Cochrane-Nutzungsbedingungen "
            "verlangen fuer KI-Nutzung eine ausdrueckliche Genehmigung; die Lizenzangabe "
            "des Uploaders klaert das nicht. Rohdaten daher gitignored, nur Manifest und "
            "Aggregate versioniert."
        ),
        "files": len(paths),
        "bytes": total_bytes,
        "review_files_sha256": sha,
        "counts": review_findings,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "mapping_report.json").write_text(
        json.dumps(review_findings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    probe = None
    if args.probe_pmids > 0:
        probe = probe_pmids(reviews, args.probe_pmids)
        (OUT / "fulltext_availability.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    write_markdown(review_findings, probe, len(paths), total_bytes)
    print(json.dumps(review_findings, ensure_ascii=False, indent=2))
    if probe:
        print(json.dumps(probe["by_status"], ensure_ascii=False))
    return 0


def write_markdown(
    f: dict[str, Any], probe: dict[str, Any] | None, files: int, total_bytes: int
) -> None:
    rows = [
        ("Reviews", f["reviews"]),
        ("Trials gesamt", f["trials_total"]),
        ("davon `include`", f["trials_include"]),
        ("Analyse-Gruppen", f["analysis_groups"]),
        ("Gruppennummern mehrfach vergeben", f["duplicate_group_numbers"]),
        ("Studienzeilen", f["study_rows"]),
        ("Gruppen mit mindestens 2 Studien", f["groups_with_at_least_2_studies"]),
        ("Gruppen, deren Zeilen alle Effekt + KI tragen", f["groups_all_rows_with_effect_and_ci"]),
        ("Gruppen poolbar (k >= 2, alle Zeilen mit Effekt + KI)", f["groups_poolable"]),
        ("Gruppen ohne eine einzige vollstaendige Armzeile", f["groups_without_any_complete_arm_row"]),
        ("Studienzeilen mit Effekt + KI", f["rows_with_effect_and_ci"]),
        ("Armzeilen vollstaendig, kontinuierlich", f["rows_arm_complete_continuous"]),
        ("Armzeilen vollstaendig, binaer", f["rows_arm_complete_binary"]),
        ("Gruppen mit Zielkonklusion", f["groups_with_conclusion"]),
        ("Studiennamen in `data_studies`", f["study_names_in_data_studies"]),
        ("davon ohne passenden Studienblock", f["study_names_unmatched"]),
    ]
    lines: list[str] = []
    lines.append("# MedSR-Bench: Anschlussfähigkeit an `study_effects`")
    lines.append("")
    lines.append("Erzeugt von `public_benchmark/scripts/goldstandard/analyse_medsr_bench.py`.")
    lines.append("Alle Zahlen sind aus den 100 Review-JSONs gezählt, keine Schätzung.")
    lines.append("")
    lines.append("**Lizenzstand:** Der Datensatz ist aus der Cochrane Library abgeleitet.")
    lines.append("Cochrane verlangt für KI-Nutzung eine ausdrückliche Genehmigung; die")
    lines.append("Apache-2.0-Angabe des Uploaders klärt das nicht. Rohdaten sind gitignored.")
    lines.append("")
    lines.append(f"Dateien: {files}, {total_bytes} Bytes.")
    lines.append("")
    lines.append("## Zählungen")
    lines.append("")
    lines.append("| Kennzahl | Wert |")
    lines.append("|---|---:|")
    for label, value in rows:
        lines.append(f"| {label} | {value} |")
    lines.append("")
    lines.append("## Verteilungen")
    lines.append("")
    for title, key in (
        ("Trials nach `relation_type`", "trials_by_relation"),
        ("Datentyp", "groups_by_data_type"),
        ("Effektmaß", "groups_by_effect_measure"),
        ("Zielkonklusion", "conclusion_classes"),
    ):
        lines.append(f"**{title}**")
        lines.append("")
        lines.append("| Wert | Gruppen |")
        lines.append("|---|---:|")
        for name, count in sorted(f[key].items(), key=lambda x: -x[1]):
            lines.append(f"| {name} | {count} |")
        lines.append("")
    z = f["implied_ci_z"]
    lines.append("## KI-Konsistenz")
    lines.append("")
    lines.append("Für Mittelwertdifferenzen lässt sich der Standardfehler unabhängig aus")
    lines.append("beiden Quellen rechnen: aus dem berichteten KI und aus den Arm-SDs.")
    lines.append("Stimmen beide, ist das KI ein 95-%-KI.")
    lines.append("")
    lines.append(f"- geprüfte Zeilen: {z['n']}")
    lines.append(f"- Median von (KI-Breite / Arm-SE): {z['median']} (erwartet {z['expected_95_percent']})")
    lines.append(f"- Anteil im Fenster 3,6 bis 4,2: {z['share_within_3_6_to_4_2']}")
    lines.append("")
    lines.append("## Provenienz")
    lines.append("")
    prov = f["provenance_like_fields"]
    if prov:
        lines.append("Felder mit Belegstellen-Bezug: " + ", ".join(f"`{p}`" for p in prov))
    else:
        lines.append("Keine Felder mit Seiten-, Tabellen-, Zell- oder Zitatbezug gefunden.")
        lines.append("Der Verbatim-Kontrakt des Projekts lässt sich auf diesem Datensatz")
        lines.append("nicht prüfen.")
    lines.append("")
    if probe:
        lines.append("## Volltextverfügbarkeit (Stichprobe)")
        lines.append("")
        lines.append(f"Geprüft: {probe['checked']} PMIDs über Europe PMC.")
        lines.append("")
        lines.append("| Status | PMIDs |")
        lines.append("|---|---:|")
        for name, count in sorted(probe["by_status"].items(), key=lambda x: -x[1]):
            lines.append(f"| {name} | {count} |")
        lines.append("")
        lines.append("`oa` = offene Lizenz, `pmc_no_oa` = in PMC lesbar ohne OA-Lizenz,")
        lines.append("`paywall` = kein PMC-Volltext, `notfound` = kein Treffer.")
        lines.append("")
    lines.append("## Lesart")
    lines.append("")
    lines.append("Die Zahlen sagen, wie viel des Benchmarks überhaupt in die Struktur passt.")
    lines.append("Sie sagen nichts über die Qualität der Werte und nichts über die Lizenz.")
    lines.append("")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
