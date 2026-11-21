#!/usr/bin/env python3
"""Alias-Erweiterung ueber alle fn_wert_ersetzt messen.

Offline, ohne Netzaufruf. Grundgesamtheit sind alle 295 `fn_wert_ersetzt`.
Verglichen werden zwei Varianten der Zielzeilensuche:

* `ohne`  - keine Erweiterung (keine Aliasliste, keine Akronyme).
* `alias` - Alias `scanning -> scan, duration` plus Akronyme ab drei
  Buchstaben.

Je Fall wird zusaetzlich der Feldtyp gelesen: Groessen aus der Groessenzeile
ueber der Zielzeile, Mittel und Ereignisse als erste Zahl der Armzelle,
Streuungen als Zahl in Klammern. Das ist ein grober Leser, kein validierter
Extraktor; die Trefferzahlen sind entsprechend zu lesen.

Aufruf::

    .venv/bin/python public_benchmark/extended_benchmark/analysis/f1_offensive_20261121/zielzeile_alle_20261121.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

HIER = Path(__file__).resolve().parent
ANALYSE = HIER.parent
REPO = HIER.parents[3]
sys.path.insert(0, str(ANALYSE / "glm53_p5_vergleich_20261120"))
sys.path.insert(0, str(HIER))

import vergleiche_20261120 as v  # noqa: E402
import groessen_zielzeile_20261121 as g  # noqa: E402
import zielzeile_alias_20261121 as alias_mod  # noqa: E402
from zaehlfelder_20261121 import segmente, arm_von_label, STOPP_ARM  # noqa: E402


def arm_weit(label: str, context: dict[str, Any]) -> str:
    """Armerkennung wie `arm_von_label`, aber auch fuer drei Buchstaben (`Pls`)."""
    arm = arm_von_label(label, context)
    if arm:
        return arm
    li = label.lower()
    inter = [w for w in re.findall(r"[a-z][a-z-]{2,}", str(context.get("intervention") or "").lower())
             if w not in STOPP_ARM and w not in {"the", "and", "for", "per", "day", "mg", "with"}]
    comp = [w for w in re.findall(r"[a-z][a-z-]{2,}", str(context.get("comparator") or "").lower())
            if w not in STOPP_ARM and w not in {"the", "and", "for", "per", "day", "mg", "with"}]
    si = sum(1 for w in inter if w in li)
    sc = sum(1 for w in comp if w in li)
    if si > sc and si:
        return "intervention"
    if sc > si and sc:
        return "comparator"
    return ""

KAPITION = re.compile(r"^\s*(?:Table|TABLE)\s*\d|:::\s*caption", re.IGNORECASE)


def tabellengrenzen(zeilen: list[str], ziel: int) -> tuple[int, int]:
    """Anfang und Ende der Tabelle, in der die Zielzeile steht."""
    start = 0
    for j in range(ziel - 1, -1, -1):
        if KAPITION.search(zeilen[j]):
            start = j
            break
    ende = len(zeilen)
    for j in range(ziel + 1, len(zeilen)):
        if KAPITION.search(zeilen[j]):
            ende = j
            break
    return start, ende


FOLLOWUP_KOPF = re.compile(r"\bfollow[- ]?up\b|\bchange[sd]?\b|\bmean difference\b|"
                           r"\bfrom (?:the )?baseline\b|\bat \d+\s*(?:weeks?|months?)\b|"
                           r"\bweek\s*\d+\b", re.IGNORECASE)
BASELINE_KOPF = re.compile(r"\bbaseline\b|\bcharacteristics\b", re.IGNORECASE)


def tabellen_zeitpunkt(zeilen: list[str], start: int, ende: int) -> int:
    """Zeitpunkt-Kennzeichen einer Tabelle mit den Grenzen `start` bis `ende`.

    +2 fuer eine Nachher-/Follow-up-Tabelle (Aenderung, Follow-up, Zeitpunkt),
    -2 fuer eine Baseline-Tabelle (Ausgangswerte, Charakteristika), 0 sonst.
    Gelesen wird nur der Tabellenkopf: Unterschrift und erste Kopfzeilen.
    Die Grenzen werden uebergeben, weil die Unterschrift selbst eine
    Tabellengrenze ist und die Ruecksuche sie sonst ueberspringt.
    """
    kopf = " ".join(zeilen[start:min(ende, start + 10)])
    if FOLLOWUP_KOPF.search(kopf):
        return 2
    if BASELINE_KOPF.search(kopf):
        return -2
    return 0


def ziel_zeile_zeitpunkt(zeilen: list[str], outcome: str, alias: dict[str, list[str]],
                         akronyme: bool) -> int:
    """Zielzeile mit Tabellenwahl bei gleichem Alias-Treffer.

    `ziel_zeile_alias` nimmt die erste Zeile mit dem hoechsten Treffer und
    landet damit in der Baseline-Tabelle, wenn sie vor der Nachher-Tabelle
    steht. Hier gewinnt bei gleichem Treffer die Tabelle mit Zeitpunkt- oder
    Follow-up-Kopf; unter mehreren solchen Tabellen die fruehste (die
    Haupttabelle steht vor Sensitivitaets- und Subgruppentabellen). Innerhalb
    einer Tabelle bleibt es bei der spaetesten Zeile.
    """
    kandidaten: list[tuple[int, int]] = []
    for i, zeile in enumerate(zeilen):
        if g.ist_groessenzeile(zeile) or not re.search(r"[A-Za-z]{3}", zeile):
            continue
        segs = segmente(zeile)
        if len(segs) < 2 or len(g.zahlen(zeile)) < 2:
            continue
        p = max(alias_mod.treffer_alias(s, outcome, alias, akronyme) for s in segs)
        if p > 0:
            kandidaten.append((p, i))
    if not kandidaten:
        return -1
    top = max(p for p, _ in kandidaten)
    je_tabelle: dict[tuple[int, int], list[int]] = {}
    for p, i in kandidaten:
        if p == top:
            je_tabelle.setdefault(tabellengrenzen(zeilen, i), []).append(i)
    punkte = {grenzen: tabellen_zeitpunkt(zeilen, *grenzen) for grenzen in je_tabelle}
    # Umziehen lohnt nur in eine Tabelle, die ihre Arme selbst benennt (Kuerzel
    # mit n in der Unterschrift). Sonst bleibt es bei der bisherigen Wahl: sonst
    # gewaenne eine Aenderungstabelle gegen die Tabelle mit den Absolutwerten
    # (PMC4987981: Gold steht in der Baseline-Tabelle).
    bevorzugt = [grenzen for grenzen in je_tabelle
                 if punkte[grenzen] > 0
                 and (not TABELLE_ARMBEDINGUNG or armkuerzel(zeilen, grenzen))]
    if not bevorzugt:
        return min(i for p, i in kandidaten if p == top)
    frueheste = min(bevorzugt)
    return min(je_tabelle[frueheste])


def zeitverlauf_ziel(zeilen: list[str], outcome: str, alias: dict[str, list[str]],
                     akronyme: bool, spaeter: bool = False) -> int:
    """Zielzeile aus einer Tabelle mit Wochenspalte: letzter Zeitpunkt des Blocks.

    Gesucht werden Tabellen, deren Kopf `Week` nennt. In ihnen tragen nur die
    ersten Zeilen eines Blocks das Outcome-Label; die Wochenzeilen darunter sind
    nackt. Bei gleichem Treffer entscheidet die spaetere (oder fruehere) Tabelle.
    """
    grenzen: list[tuple[int, int]] = []
    start = 0
    for i, zeile in enumerate(zeilen):
        if KAPITION.search(zeile):
            if i > start:
                grenzen.append((start, i))
            start = i
    grenzen.append((start, len(zeilen)))

    beste: list[tuple[int, int, int]] = []  # (score, zeile, tabelle)
    for t_index, (a, b) in enumerate(grenzen):
        kopf = " ".join(zeilen[max(a, b - 80):min(b, a + 10)]).lower()
        if not re.search(r"\bweek\b", kopf):
            continue
        bloecke: dict[str, list[tuple[float, int]]] = {}
        label = ""
        for i in range(a, b):
            segs = segmente(zeilen[i])
            if not segs:
                continue
            if re.search(r"[A-Za-z]{3}", segs[0]):
                label = segs[0]
                if (len(segs) > 1 and re.fullmatch(r"\d{1,2}", segs[1])
                        and len(g.zahlen(zeilen[i])) >= 2):
                    bloecke.setdefault(label, []).append((float(segs[1]), i))
                continue
            if label and re.fullmatch(r"\d{1,2}", segs[0]) and len(g.zahlen(zeilen[i])) >= 2:
                bloecke.setdefault(label, []).append((float(segs[0]), i))
        for lab, reihen in bloecke.items():
            if len(reihen) < 2:
                continue
            p = alias_mod.treffer_alias(lab, outcome, alias, akronyme)
            if p <= 0:
                continue
            woche, i = max(reihen, key=lambda x: x[0])
            beste.append((p, i, t_index))
    if not beste:
        return -1
    top = max(p for p, _, _ in beste)
    kandidaten = [(i, t) for p, i, t in beste if p == top]
    return max(kandidaten)[0] if spaeter else min(kandidaten)[0]


POSITIONAL = True
# Uebereinstimmungs-Gate: Groessenzelle nur ausgeben, wenn Label-Zuordnung und
# Positionsregel denselben Wert liefern.
GATE = True
# Schalter fuer die Ablation der Bausteine.
WOCHENSPALTE = True
MESSWORT_BLOCK = True
TABELLENLOKAL = True
# Tabellenwahl: eine Tabelle mit Zeitpunkt- oder Follow-up-Kopf vor der
# Baseline-Tabelle bevorzugen.
ZEITPUNKT_TABELLE = True
# Umzug nur in eine Nachher-Tabelle, die ihre Arme selbst benennt.
TABELLE_ARMBEDINGUNG = True
# Armzeilen lesen: Armkuerzel (`I`/`C`) steht in der Zeile selbst, die
# Gruppengroesse in der Tabellenunterschrift.
ARMZEILE = True
# Fuehrendes Minus einer Zelle uebernehmen (U+2212 und ASCII).
VORZEICHEN = True
# Streuung aus einem 95%-KI ableiten, wenn keine SD gedruckt ist.
SD_AUS_KI = True
MINUS = chr(0x2212)

# Messwoerter, die im Tabellenblock stehen muessen, wenn das Outcome sie nennt.
MESSWOERTER = ("stiffness", "range of motion", "ranges of motion", "neutral zone",
               "neural zone")


def block_label(zeilen: list[str], i: int) -> str:
    """Ueberschrift des Blocks, in dem Zeile `i` steht (innerhalb ihrer Tabelle)."""
    start, _ = tabellengrenzen(zeilen, i)
    for j in range(i - 1, start - 1, -1):
        z = zeilen[j].strip()
        if len(re.findall(r"[A-Za-z]", z)) < 3 or "\u00b1" in z or len(z) > 70:
            continue
        if re.fullmatch(r"[\d.,;:\s%-]+", z):
            continue
        if len(re.findall(r"\d+(?:\.\d+)?", z)) > 2:
            continue
        return z
    return ""


def messwort(outcome: str) -> str:
    """Messwort aus dem Outcome, falls es eines der bekannten nennt."""
    text = outcome.lower()
    for wort in MESSWOERTER:
        if wort in text:
            return wort
    return ""


def ziel_zeile_block(zeilen: list[str], outcome: str, alias: dict[str, list[str]],
                     akronyme: bool) -> int:
    """Zielzeile, deren Block das Messwort des Outcomes traegt.

    Nennt das Outcome kein Messwort, bleibt es bei der normalen Zielzeile.
    Sonst gilt nur eine Zeile, die das Outcome trifft und in einem Block mit
    passendem Label steht; findet sich keine, bleibt die normale Zielzeile.
    """
    if ZEITPUNKT_TABELLE:
        standard = ziel_zeile_zeitpunkt(zeilen, outcome, alias, akronyme)
    else:
        standard = alias_mod.ziel_zeile_alias(zeilen, outcome, alias, akronyme)
    if not MESSWORT_BLOCK:
        return standard
    wort = messwort(outcome)
    if not wort:
        return standard
    beste: list[tuple[int, int]] = []
    for i, zeile in enumerate(zeilen):
        p = alias_mod.treffer_alias(zeile, outcome, alias, akronyme)
        if p <= 0:
            continue
        if wort not in block_label(zeilen, i).lower():
            continue
        beste.append((p, i))
    if not beste:
        return standard
    top = max(p for p, _ in beste)
    # Mehrere Bloecke mit passendem Label: der spaetere Traeger gilt als der
    # Auswertungsblock (bei 221-223 steht dort das Gold).
    return max(i for p, i in beste if p == top)


WOCHE = re.compile(r"\bweek\s*\d+", re.IGNORECASE)


PLACEBO = ("pbo", "placebo", "control", "untreated", "sham")


def arm_score(label: str, arm: str, context: dict[str, Any], alias: dict[str, list[str]],
              akronyme: bool) -> int:
    """Passung eines Spaltenlabels zum Arm: Alias, Dosis und Placebo-Synonyme."""
    text = str(context.get(arm) or "")
    score = alias_mod.treffer_alias(label, text, alias, akronyme)
    li = label.lower()
    dosen = re.findall(r"\d+\s*(?:mg|g|ml|iu)", text.lower())
    if dosen and any(d.replace(" ", "") in li.replace(" ", "") for d in dosen):
        score += 2
    if arm == "comparator":
        if any(w in li for w in PLACEBO) and any(w in text.lower() for w in PLACEBO):
            score += 2
    return score


def akronym_score(label: str, outcome: str) -> int:
    """Blocklabel als Akronym des Outcomes (`MCS` fuer Mental Component Summary)."""
    marke = re.sub(r"[^A-Za-z]", "", label).upper()
    if len(marke) < 2 or len(marke) > 5:
        return 0
    worte = [w for w in re.findall(r"[A-Za-z]+", outcome) if len(w) > 2]
    for start in range(0, max(1, len(worte) - len(marke) + 1)):
        stelle = "".join(w[0] for w in worte[start:start + len(marke)]).upper()
        if stelle == marke:
            return 3
    return 0


def zeitverlauf_gruppen(zeilen: list[str], i: int) -> tuple[int, int, list[str]]:
    """Wochenkopf ueber Zeile `i`: (Zeilen, Gruppen, Armlabels der Kopfzeile)."""
    start, _ = tabellengrenzen(zeilen, i)
    for j in range(i - 1, max(start - 1, i - 12), -1):
        treffer = WOCHE.findall(zeilen[j])
        if len(treffer) >= 2:
            for m in range(j + 1, min(i, j + 8)):
                kopf = segmente(zeilen[m])
                if len(kopf) >= len(treffer) * 2 and len(kopf) % len(treffer) == 0:
                    return len(treffer), len(kopf) // len(treffer), kopf
            return len(treffer), 0, []
    return 0, 0, []


def zeitverlauf_mittel(zeilen: list[str], ziel: int, outcome: str, feld: str, arm: str,  # noqa: PLR0913
                       context: dict[str, Any], alias: dict[str, list[str]],
                       akronyme: bool, mean_formate: tuple[str, ...]) -> dict[str, Any] | None:
    """Mittel aus der Zeile des passenden Subskalen-Blocks, letzter Zeitpunkt.

    Gilt nur fuer Tabellen mit mehreren Wochenspalten. Gewaehlt wird der Block,
    dessen Ueberschrift das Outcome trifft; trifft keiner, der erste Block der
    Tabelle. Innerhalb des Blocks zaehlt die erste Zeile mit lesbarem Mittel
    ( typisch `Mean score (SD)`). Die Spalte kommt aus der letzten Wochengruppe.
    """
    # Tabellen des Dokuments: eine mit Wochenkopf traegt die Zeitpunktspalten.
    grenzen: list[tuple[int, int]] = []
    start = 0
    for i, zeile in enumerate(zeilen):
        if KAPITION.search(zeile):
            if i > start:
                grenzen.append((start, i))
            start = i
    grenzen.append((start, len(zeilen)))
    for a, b in grenzen:
        gruppen = pro_gruppe = 0
        for j in range(a, min(b, a + 40)):
            treffer = WOCHE.findall(zeilen[j])
            if len(treffer) < 2:
                continue
            for m in range(j + 1, min(b, j + 8)):
                kopf = segmente(zeilen[m])
                if len(kopf) >= 2 * len(treffer) and len(kopf) % len(treffer) == 0:
                    gruppen, pro_gruppe = len(treffer), len(kopf) // len(treffer)
                    break
            if gruppen:
                break
        if gruppen < 2 or pro_gruppe < 2:
            continue
        bloecke: list[tuple[int, str, int]] = []
        for i in range(a, b):
            ueberschrift = block_label(zeilen, i)
            if not ueberschrift:
                continue
            score = max(alias_mod.treffer_alias(ueberschrift, outcome, alias, akronyme),
                        akronym_score(ueberschrift, outcome))
            bloecke.append((score, ueberschrift, i))
        if not bloecke:
            continue
        beste = max(s for s, _, _ in bloecke)
        # Nur eine belastbare Ueberschrift (Alias oder Akronym) waehlt den Block;
        # sonst gilt der erste Block der Tabelle.
        kandidaten = ([(u, i) for s, u, i in bloecke if s == beste] if beste >= 2
                      else [(u, i) for _, u, i in bloecke])
        for _, ab in kandidaten:
            for i in range(ab, min(ab + 6, b)):
                segs = segmente(zeilen[i])
                if len(segs) < gruppen * pro_gruppe:
                    continue
                spalte = 1 + (gruppen - 1) * pro_gruppe
                kandidaten_spalten: list[tuple[int, int]] = []
                for k in range(spalte, min(spalte + pro_gruppe, len(segs))):
                    if wert_aus_zelle(segs[k], feld, mean_formate) is None:
                        continue
                    label = spalte_label(zeilen, i, segs, k, context, alias, akronyme)
                    score = arm_score(label, arm, context, alias, akronyme)
                    if score > 0:
                        kandidaten_spalten.append((score, k))
                if not kandidaten_spalten:
                    continue
                _, k = max(kandidaten_spalten, key=lambda x: (x[0], -x[1]))
                return {"value": wert_aus_zelle(segs[k], feld, mean_formate),
                        "quelle": "wochenspalte", "zeile": i + 1,
                        "zellformat": zellformat(segs[k]), "block": block_label(zeilen, i)}
    return None


def spalten_reihenfolge(zeilen: list[str], ziel: int, context: dict[str, Any]) -> list[str]:
    """Arme in der Reihenfolge ihrer Datenspalten (Groessenzeile, sonst Kopf)."""
    start, _ = tabellengrenzen(zeilen, ziel)
    for i in range(ziel - 1, start - 1, -1):
        if g.ist_groessenzeile(zeilen[i]) and g.STRENGE.search(zeilen[i]):
            arme = [arm_weit(s, context) for s in segmente(zeilen[i])]
            arme = [a for a in arme if a]
            if len(arme) >= 2:
                return arme
    for j in range(ziel - 1, start - 1, -1):
        arme = [arm_weit(s, context) for s in segmente(zeilen[j])]
        arme = [a for a in arme if a]
        if len(arme) >= 2:
            return arme
    return []


def positional(treffer: dict[str, dict[str, Any]], reihenfolge: list[str]) -> dict[str, dict[str, Any]]:
    """Erste Datenspalte ist Intervention, zweite Comparator - Namen ignoriert."""
    if not treffer or "intervention" not in treffer or "comparator" not in treffer:
        return treffer
    if len(reihenfolge) < 2 or reihenfolge[0] == reihenfolge[1]:
        return treffer
    erste, zweite = reihenfolge[0], reihenfolge[1]
    if erste not in treffer or zweite not in treffer:
        return treffer
    return {"intervention": dict(treffer[erste], quelle="position"),
            "comparator": dict(treffer[zweite], quelle="position")}


def groesse_in_tabelle(zeilen: list[str], ziel: int, context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Groesse aus der Tabelle der Zielzeile: `n =`-Zeile oder Zeilen-`n`."""
    start, ende = tabellengrenzen(zeilen, ziel)
    if not TABELLENLOKAL:
        start = max(-1, ziel - 61)
    for i in range(ziel - 1, start - 1, -1):
        if g.ist_groessenzeile(zeilen[i]) and g.STRENGE.search(zeilen[i]):
            werte = g.aus_groessenzeile(zeilen, i, context)
            if werte:
                return werte
    # Zeilenlayout `n  Mean (95% CI)` je Arm: n steht in der Zielzeile selbst.
    kopf: list[str] | None = None
    for j in range(ziel - 1, start - 1, -1):
        segs = segmente(zeilen[j])
        arme = [arm_weit(s, context) for s in segs if arm_weit(s, context)]
        if len(arme) >= 2:
            fenster = " ".join(zeilen[j:min(j + 3, ziel + 1)]).lower()
            if "mean" in fenster and re.search(r"\bn\b", fenster):
                kopf = arme[:2]
            break
    if not kopf:
        # Rueckfall: naechste Groessenzeile ueber der Zielzeile, auch ausserhalb
        # der Tabellengrenzen (Tabellen ohne Beschriftung).
        for i in range(ziel - 1, max(-1, ziel - 61), -1):
            if g.ist_groessenzeile(zeilen[i]) and g.STRENGE.search(zeilen[i]):
                werte = g.aus_groessenzeile(zeilen, i, context)
                if werte:
                    return werte
        return {}
    segs = segmente(zeilen[ziel])
    if len(kopf) != 2:
        return {}

    def ganz(s: str) -> int | None:
        return int(s) if re.fullmatch(r"\d{1,6}", s) else None

    n1 = ganz(segs[1]) if len(segs) > 1 else None
    n2 = None
    for k, s in enumerate(segs[2:], start=2):
        if s.startswith("(") and k + 1 < len(segs):
            n2 = ganz(segs[k + 1])
            break
    if not n1 or not n2:
        return {}
    return {kopf[0]: {"value": float(n1), "quelle": "zeile_n", "zeile": ziel + 1},
            kopf[1]: {"value": float(n2), "quelle": "zeile_n", "zeile": ziel + 1}}

FELD_ARM = {"intervention": "intervention", "comparator": "comparator"}


def spalte_label(zeilen: list[str], i: int, segs: list[str], k: int,
                 context: dict[str, Any] | None = None,
                 alias: dict[str, list[str]] | None = None,
                 akronyme: bool = False) -> str:
    """Kopfzeilen-Label der Zellspalte `k`.

    Unter mehreren passenden Kopfzeilen (Armzeile, Dosiszeile, `(n = ...)`)
    gewinnt die, deren Label am besten zu einem Arm passt.
    """
    zahlenspalten = [n for n, s in enumerate(segs) if re.search(r"\d", s)]
    if k not in zahlenspalten:
        return ""
    pos = zahlenspalten.index(k)
    start, _ = tabellengrenzen(zeilen, i)
    beste: tuple[int, str] = (-1, "")
    for j in range(i - 1, max(start - 1, i - 41), -1):
        kopf = segmente(zeilen[j])
        if len(kopf) == len(zahlenspalten):
            ziel = pos
        elif len(kopf) == len(zahlenspalten) + 1:
            ziel = pos + 1
        else:
            continue
        if ziel >= len(kopf) or not re.search(r"[A-Za-z]{3}", kopf[ziel]) or "\u00b1" in kopf[ziel]:
            continue
        score = 0
        if context and alias is not None:
            score = max(arm_score(kopf[ziel], "intervention", context, alias, akronyme),
                        arm_score(kopf[ziel], "comparator", context, alias, akronyme))
        if score > beste[0]:
            beste = (score, kopf[ziel])
            if score >= 2:
                break
    return beste[1]


def arm_von_spalte(zeilen: list[str], i: int, segs: list[str], k: int,
                   context: dict[str, Any]) -> str:
    """Arm der Zellspalte `k`, gesucht in der Kopfzeile ueber der Zielzeile."""
    zahlenspalten = [n for n, s in enumerate(segs) if re.search(r"\d", s)]
    if k not in zahlenspalten:
        return ""
    pos = zahlenspalten.index(k)
    # Tabellenlokal: die Kopfzeile darf nur aus derselben Tabelle stammen.
    start, _ = tabellengrenzen(zeilen, i)
    for j in range(i - 1, max(start - 1, i - 41), -1):
        kopf = segmente(zeilen[j])
        if len(kopf) == len(zahlenspalten):
            ziel = pos
        elif len(kopf) == len(zahlenspalten) + 1:
            ziel = pos + 1
        else:
            continue
        if ziel < len(kopf):
            arm = arm_von_label(kopf[ziel], context)
            if arm:
                return arm
    return ""


MITTEL_SD = re.compile(r"^[\s*]*\d+(?:\.\d+)?\s*\(\s*\d+(?:\.\d+)?\s*\)[\s*^a-z(\[]*$", re.IGNORECASE)


def zellformat(zelle: str) -> str:
    """Zellform erkennen: `mittel_sd`, `mittel_ki`, `nackt`, `prozent`, `anzahl_prozent`."""
    z = zelle.strip()
    if MITTEL_SD.match(z):
        return "mittel_sd"
    if re.search(r"\(\s*\d+(?:\.\d+)?\s*;\s*\d+(?:\.\d+)?\s*\)", z):
        return "mittel_ki"
    if re.fullmatch(r"\d+(?:\.\d+)?", z):
        return "nackt"
    if re.fullmatch(r"\d+(?:\.\d+)?\s*\(\s*[\d.]+\s*%?\s*\)\**", z):
        return "anzahl_prozent"
    if "%" in z:
        return "prozent"
    if "\u00b1" in z:
        return "plus_minus"
    return "sonstig"


KI_PAAR = re.compile(r"\(\s*([" + MINUS + r"-]?)\s*(\d+(?:\.\d+)?)\s*[,;]\s*(["
                     + MINUS + r"-]?)\s*(\d+(?:\.\d+)?)\s*\)")


def ki_grenzen(zelle: str) -> tuple[float, float] | None:
    """Untere und obere Grenze eines 95%-KI in der Zelle, oder None."""
    m = KI_PAAR.search(zelle)
    if not m:
        return None
    unten = float(m.group(2)) * (-1 if m.group(1) else 1)
    oben = float(m.group(4)) * (-1 if m.group(3) else 1)
    return (unten, oben) if oben > unten else None


def wert_aus_zelle(zelle: str, feld: str, mean_formate: tuple[str, ...] | None,
                   n_arm: int | None = None) -> float | None:
    """Wert einer Armzelle: Streuung in Klammern, Mittel nur in erlaubten Formaten.

    `mean_formate=None` heisst: erste Zahl der Zelle, ohne Formatpruefung.
    `n_arm` ist die Gruppengroesse des Arms; sie wird nur gebraucht, wenn eine
    Streuung aus einem 95%-KI abgeleitet wird (keine SD gedruckt).
    """
    if feld.endswith("standard_deviation"):
        # Streuung aus einem 95%-KI: SE = halbe Intervallbreite / 1.96, SD = SE * sqrt(n).
        # Nur mit bekannter Gruppengroesse, sonst bleibt die Zelle leer.
        if SD_AUS_KI and n_arm:
            grenzen = ki_grenzen(zelle)
            if grenzen:
                halb = (grenzen[1] - grenzen[0]) / 2
                return round(halb / 1.96 * math.sqrt(n_arm), 2)
        # Streuung nur aus Zellen, deren Format den zweiten Wert als SD ausweist:
        # `Mittel (SD)` und `Mittel +/- SD`. Alles andere (KI, Prozent, n Mean)
        # bleibt leer, damit keine Intervallgrenze als SD durchgeht.
        fmt = zellformat(zelle)
        if fmt == "mittel_sd":
            m = re.search(r"\(\s*(\d+(?:\.\d+)?)\s*\)", zelle)
        elif fmt == "plus_minus":
            m = re.search(re.escape(chr(0x00B1)) + r"\s*(\d+(?:\.\d+)?)", zelle)
        else:
            return None
        return float(m.group(1)) if m else None
    if feld.endswith("mean"):
        if mean_formate is not None and zellformat(zelle) not in mean_formate:
            return None
        m = re.search(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)", zelle)
        if not m:
            return None
        wert = float(m.group(1).replace(",", ""))
        # Fuehrendes Minus (U+2212 oder ASCII) gehoert zum Wert; ohne diese
        # Regel wird aus `-0.55` eine `0.55`.
        if VORZEICHEN and re.match(r"\s*[" + MINUS + r"-]", zelle):
            wert = -wert
        return wert
    m = re.search(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)", zelle)
    return float(m.group(1).replace(",", "")) if m else None


ARMKUERZEL = re.compile(
    r"\b(intervention|control|placebo|treatment|comparison)\b[a-z ,'-]{0,20}?"
    r"group\s*\(\s*([A-Za-z])\s*[;,]\s*n\s*=\s*(\d+)\s*\)", re.IGNORECASE)


def armkuerzel(zeilen: list[str],
               grenzen: tuple[int, int]) -> dict[str, tuple[str, int]]:
    """Armkuerzel und Gruppengroesse aus der Tabellenunterschrift.

    Erkannt wird die Form `intervention group (I; n=104) and the control group
    (C; n=114)`. Das Kuerzel steht in der Armzeile, die Groesse nur in der
    Unterschrift.
    """
    start, ende = grenzen
    text = " ".join(zeilen[start:min(ende, start + 6)])
    aus: dict[str, tuple[str, int]] = {}
    for name, kuerzel, n in ARMKUERZEL.findall(text):
        arm = ("comparator" if name.lower() in ("control", "placebo", "comparison")
               else "intervention")
        aus[kuerzel] = (arm, int(n))
    return aus


def gruppenzeile_wert(zeilen: list[str], ziel: int, feld: str, arm: str,
                      mean_formate: tuple[str, ...] | None,
                      kuerzel: dict[str, tuple[str, int]]) -> dict[str, Any] | None:
    """Wert aus einer Armzeile: das Kuerzel steht in der Zeile, der Wert rechts.

    Gilt fuer Tabellen wie `Mean changes within ...`, in denen je Arm eine Zeile
    steht (`I  -0.55 (-0.99, -0.11)`). Die Zeile traegt kein Spaltenlabel, die
    Armzuordnung kommt allein aus dem Kuerzel der Unterschrift.
    """
    for i in (ziel, ziel + 1, ziel + 2, ziel + 3):
        if i >= len(zeilen):
            break
        segs = segmente(zeilen[i])
        for k, s in enumerate(segs):
            arm_i, n_i = kuerzel.get(s.strip(), ("", 0))
            if arm_i != arm:
                continue
            for zelle in segs[k + 1:k + 3]:
                # In der Armzeile steht das Mittel als nackte Zahl ohne Zellformat;
                # das Format ist hier schon durch die Armzuordnung belegt.
                formate = None if feld.endswith("mean") else mean_formate
                wert = wert_aus_zelle(zelle, feld, formate, n_arm=n_i or None)
                if wert is not None:
                    treffer = {"value": wert, "quelle": "armzeile", "zeile": i + 1,
                               "zellformat": zellformat(zelle)}
                    if feld.endswith("standard_deviation"):
                        # Kennzeichnen, ob die Streuung abgelesen oder aus dem KI
                        # abgeleitet wurde: gedruckt ist sie nur in `(SD)` und `+/-`.
                        abgeleitet = (zellformat(zelle) not in ("mittel_sd", "plus_minus")
                                      and ki_grenzen(zelle) is not None)
                        treffer["abgeleitet"] = abgeleitet
                        treffer["herkunft"] = "95%-KI" if abgeleitet else "zelle"
                    return treffer
    return None


def lies(record: dict[str, Any], text: str, feld: str, arm: str,
         alias: dict[str, list[str]], akronyme: bool,
         mean_formate: tuple[str, ...] | None = None) -> dict[str, Any] | None:
    if feld.endswith("events"):
        return None  # Ereignis-Leser abgeschaltet: 0 TP, 7 FP
    context = record.get("context") or {}
    zeilen = text.splitlines()
    if feld.endswith("group_size"):
        outcome = str(context.get("outcome") or "")
        ziel = zeitverlauf_ziel(zeilen, outcome, alias, akronyme)
        if ziel < 0:
            if ZEITPUNKT_TABELLE:
                ziel = ziel_zeile_zeitpunkt(zeilen, outcome, alias, akronyme)
            else:
                ziel = alias_mod.ziel_zeile_alias(zeilen, outcome, alias, akronyme)
        if ziel < 0:
            return None
        # Stehen die Arme als Kuerzel in der Unterschrift (`I; n=104`), gilt deren
        # Groesse; sonst die Groessenzeile der Tabelle.
        kuerzel = armkuerzel(zeilen, tabellengrenzen(zeilen, ziel)) if ARMZEILE else {}
        if kuerzel:
            werte = {a: {"value": float(n), "quelle": "unterschrift_n", "zeile": ziel + 1}
                     for a, n in kuerzel.values()}
        else:
            werte = groesse_in_tabelle(zeilen, ziel, context)
        reihenfolge = spalten_reihenfolge(zeilen, ziel, context)
        if GATE and len(reihenfolge) >= 2 and reihenfolge[0] != reihenfolge[1]:
            geprueft = positional(werte, reihenfolge)
            a, b = werte.get(arm), geprueft.get(arm)
            if not a or not b or abs(float(a["value"]) - float(b["value"])) > 1e-9:
                return None
        if POSITIONAL:
            werte = positional(werte, reihenfolge)
        treffer = werte.get(arm)
        if not treffer:
            return None
        # Gruppengroessen sind Zaehlungen: keine Dezimalwerte, keine Kleinstwerte.
        if float(treffer["value"]).is_integer() is False or float(treffer["value"]) < 5:
            return None
        return treffer

    outcome = str(context.get("outcome") or "")
    ziel = ziel_zeile_block(zeilen, outcome, alias, akronyme)
    if ziel < 0:
        return None
    if ARMZEILE:
        kuerzel = armkuerzel(zeilen, tabellengrenzen(zeilen, ziel))
        if kuerzel:
            treffer = gruppenzeile_wert(zeilen, ziel, feld, arm, mean_formate, kuerzel)
            if treffer:
                return treffer
    if mean_formate and WOCHENSPALTE:
        treffer = zeitverlauf_mittel(zeilen, ziel, outcome, feld, arm, context, alias,
                                     akronyme, mean_formate)
        if treffer:
            return treffer
    segs = segmente(zeilen[ziel])
    context = record.get("context") or {}
    kandidaten: list[tuple[int, int, int]] = []
    for k in range(1, len(segs)):
        if arm_von_spalte(zeilen, ziel, segs, k, context) != arm:
            continue
        if wert_aus_zelle(segs[k], feld, mean_formate) is None:
            continue
        label = spalte_label(zeilen, ziel, segs, k, context, alias, akronyme)
        score = arm_score(label, arm, context, alias, akronyme)
        kandidaten.append((score, len(label), k))
    if not kandidaten:
        return None
    # Bei mehreren Spalten desselben Arms gewinnt die beste Label-Uebereinstimmung,
    # bei Gleichstand das laengere (genauere) Label, dann die linke Spalte.
    _, _, k = max(kandidaten, key=lambda x: (x[0], x[1], -x[2]))
    return {"value": wert_aus_zelle(segs[k], feld, mean_formate), "quelle": "zielzeile",
            "zeile": ziel + 1, "zellformat": zellformat(segs[k])}


def messe(faelle: list[dict[str, Any]], records: dict[str, dict[str, Any]], texte: dict[str, str],
          alias: dict[str, list[str]], akronyme: bool,
          mean_formate: tuple[str, ...] | None = None) -> dict[str, Any]:
    detail: list[dict[str, Any]] = []
    ziel_gefunden = 0
    for f in faelle:
        rid = f["record_id"]
        record = records[rid]
        zeilen = texte[rid].splitlines()
        if alias_mod.ziel_zeile_alias(zeilen, str((record.get("context") or {}).get("outcome") or ""),
                                      alias, akronyme) >= 0:
            ziel_gefunden += 1
        info = lies(record, texte[rid], f["feld"], f["arm"], alias, akronyme, mean_formate)
        if info is None:
            continue
        gold = float(f["wert"])
        richtig = abs(info["value"] - gold) < 1e-6
        gerundet = richtig or abs(round(info["value"]) - gold) < 1e-6
        detail.append({"record_id": rid, "feld": f["feld"], "arm": f["arm"], "regel": info,
                       "gold": f["wert"], "richtig": richtig, "richtig_gerundet": gerundet})
    tp = sum(1 for e in detail if e["richtig"])
    tp_r = sum(1 for e in detail if e["richtig_gerundet"])
    return {"zielzeile_gefunden": ziel_gefunden, "geliefert": len(detail),
            "tp": tp, "fp": len(detail) - tp,
            "tp_gerundet": tp_r, "fp_gerundet": len(detail) - tp_r, "detail": detail}


def main() -> int:
    fehler = json.loads((HIER / "fehlerursachen_20261121.json").read_text(encoding="utf-8"))
    alle_faelle = [f for f in fehler["faelle_fn"] if f["regel"] == "fn_wert_ersetzt"]
    # Die Zaehlung unten meint Groesse und Mittel; die Streuung wird seit dem
    # Durchreichen als eigenes Feld gefuehrt und separat gezaehlt.
    faelle = [f for f in alle_faelle if not f["feld"].endswith("standard_deviation")]
    streuung_faelle = [f for f in alle_faelle if f["feld"].endswith("standard_deviation")]
    records = {r["record_id"]: r for r in v.lade(v.RECORDS)}
    texte: dict[str, str] = {}
    for rid in {f["record_id"] for f in alle_faelle}:
        texte[rid] = (REPO / records[rid]["document"]["path"]).read_text(encoding="utf-8", errors="replace")

    ohne = messe(faelle, records, texte, {}, False)
    mit = messe(faelle, records, texte, alias_mod.ALIAS, True)
    streng = messe(faelle, records, texte, alias_mod.ALIAS, True, mean_formate=("mittel_sd",))
    beide = messe(faelle, records, texte, alias_mod.ALIAS, True,
                  mean_formate=("mittel_sd", "plus_minus"))
    streuung = messe(streuung_faelle, records, texte, alias_mod.ALIAS, True,
                     mean_formate=("mittel_sd", "plus_minus"))
    neu = {(e["record_id"], e["feld"], e["arm"]) for e in mit["detail"]} - \
          {(e["record_id"], e["feld"], e["arm"]) for e in ohne["detail"]}
    neu_detail = [e for e in mit["detail"] if (e["record_id"], e["feld"], e["arm"]) in neu]

    def gruppe(feld: str) -> str:
        if feld.endswith("group_size"):
            return "groesse"
        if feld.endswith("standard_deviation"):
            return "streuung"
        if feld.endswith("events"):
            return "ereignis"
        return "mittel"

    from collections import Counter  # lokal, nur fuer die Aufschluesselung

    zell_aufschl = Counter((gruppe(e["feld"]), e["regel"].get("zellformat", "groessenzeile"),
                            e["richtig"]) for e in mit["detail"])
    zell_aufschl_neu = Counter((gruppe(e["feld"]), e["regel"].get("zellformat", "groessenzeile"),
                                e["richtig"]) for e in beide["detail"])
    fp = [e for e in mit["detail"] if not e["richtig"]]
    fp_feldtyp = Counter(gruppe(e["feld"]) for e in fp)
    fp_format = Counter((gruppe(e["feld"]), e["regel"].get("zellformat", "groessenzeile")) for e in fp)

    ergebnis = {
        "stand": "2026-11-21",
        "faelle": len(faelle),
        "alias_streng": {k: streng[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                                "tp_gerundet", "fp_gerundet")},
        "neu": {k: beide[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                     "tp_gerundet", "fp_gerundet")},
        "neu_zellformate": {f"{a}|{b}|{'richtig' if r else 'falsch'}": c
                            for (a, b, r), c in zell_aufschl_neu.items()},
        "fp_nach_feldtyp": dict(fp_feldtyp),
        "fp_nach_format": {f"{a}|{b}": c for (a, b), c in fp_format.items()},
        "zellformate": {f"{a}|{b}|{'richtig' if r else 'falsch'}": c
                        for (a, b, r), c in zell_aufschl.items()},
        "ohne": {k: ohne[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                       "tp_gerundet", "fp_gerundet")},
        "alias": {k: mit[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp",
                                      "tp_gerundet", "fp_gerundet")},
        "streuung": {k: streuung[k] for k in ("zielzeile_gefunden", "geliefert", "tp", "fp")},
        "streuung_detail": streuung["detail"],
        "nur_mit_alias": {"geliefert": len(neu_detail),
                          "tp": sum(1 for e in neu_detail if e["richtig"]),
                          "fp": sum(1 for e in neu_detail if not e["richtig"]),
                          "tp_gerundet": sum(1 for e in neu_detail if e["richtig_gerundet"]),
                          "fp_gerundet": sum(1 for e in neu_detail if not e["richtig_gerundet"])},
        "detail_nur_mit_alias": neu_detail,
    }
    (HIER / "zielzeile_alle_20261121.json").write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    zell_paar: dict[tuple[str, str], list[int]] = {}
    for (a, b, r), c in zell_aufschl_neu.items():
        zell_paar.setdefault((a, b), [0, 0])[0 if r else 1] += c
    format_tab = "\n".join(f"| {a} | {b} | {v[0]} | {v[1]} |"
                            for (a, b), v in sorted(zell_paar.items())) or "| - | - | - | - |"
    fp_feldtyp_tab = "\n".join(f"| {k} | {v} |" for k, v in fp_feldtyp.most_common()) or "| - | - |"
    fp_format_tab = "\n".join(f"| {a} | {b} | {c} |" for (a, b), c in fp_format.most_common()) or "| - | - | - |"
    tab = "\n".join(
        f"| `{e['record_id']}` | {e['feld']} | {e['regel']['value']} | {e['gold']} | "
        f"{'ja' if e['richtig'] else 'nein'} |" for e in neu_detail) or "| - | - | - | - | - |"
    bericht = f"""# Alias-Erweiterung ueber alle 295 fn_wert_ersetzt (21.11.2026)

Offline, ohne Netzaufruf. Die Zielzeilensuche laeuft ueber alle
{len(faelle)} `fn_wert_ersetzt`, nicht nur ueber die 31 Zaehlfelder. Zwei
Varianten: ohne Erweiterung und mit Alias `scanning -> scan, duration` plus
Akronymen.

| Kennzahl | ohne | mit Alias | nur `Mittel (SD)` | Ereignisse aus, Mittel beide Formate |
|---|---:|---:|---:|---:|
| Zielzeile gefunden | {ohne['zielzeile_gefunden']} | {mit['zielzeile_gefunden']} | {streng['zielzeile_gefunden']} | {beide['zielzeile_gefunden']} |
| Zellen geliefert | {ohne['geliefert']} | {mit['geliefert']} | {streng['geliefert']} | {beide['geliefert']} |
| TP (exakt) | {ohne['tp']} | {mit['tp']} | {streng['tp']} | {beide['tp']} |
| FP (exakt) | {ohne['fp']} | {mit['fp']} | {streng['fp']} | {beide['fp']} |
| TP (auf ganze Zahl gerundet) | {ohne['tp_gerundet']} | {mit['tp_gerundet']} | {streng['tp_gerundet']} | {beide['tp_gerundet']} |
| FP (auf ganze Zahl gerundet) | {ohne['fp_gerundet']} | {mit['fp_gerundet']} | {streng['fp_gerundet']} | {beide['fp_gerundet']} |

## FP nach Feldtyp (Alias-Lauf vor der Umstellung, {mit['fp']} FP)

| Feldtyp | FP |
|---|---:|
{fp_feldtyp_tab}

## Formate der gelieferten Zellen (Endvariante)

| Feldtyp | Zellformat | richtig | falsch |
|---|---|---:|---:|
{format_tab}

## FP nach Zellformat

| Feldtyp | Zellformat | FP |
|---|---|---:|
{fp_format_tab}


## Streuung als eigenes Feld

Auftraege aus den `fn_wert_ersetzt`-Faellen mit Feld `*_standard_deviation`:
{len(streuung_faelle)}. Geliefert {streuung['geliefert']}, davon richtig
{streuung['tp']} und falsch {streuung['fp']}. Gelesen wird die Streuung aus
Zellen im Format `Mittel (SD)` oder `Mittel +/- SD`. Druckt die Nachher-Tabelle
keine SD, sondern ein 95%-KI, leitet `wert_aus_zelle` sie ab
(`SD = halbe Intervallbreite / 1.96 * sqrt(n)`); solche Zellen tragen
`abgeleitet: True` und `herkunft: 95%-KI` und sind damit von abgelesenen
Streuungen unterscheidbar (hier {sum(1 for e in streuung['detail'] if e['regel'].get('abgeleitet'))} Zellen).

Nur durch den Alias neu geliefert: {len(neu_detail)} Zellen, davon
{sum(1 for e in neu_detail if e['richtig'])} exakt richtig und
{sum(1 for e in neu_detail if e['richtig_gerundet'])} nach Rundung richtig.
Die zwei exakten FP sind Rundungen: 31.7 gegen Gold 32 und 19.8 gegen Gold 20.

## Neue Zellen

| Record | Feld | Regelwert | Gold | richtig |
|---|---|---:|---:|---|
{tab}

## Lesart

Gelesen wird je Feldtyp: Groessen aus der Groessenzeile, Mittel nur in den
Formaten `Zahl +/- Zahl` und `Zahl (Zahl)`, Streuungen als Zahl in Klammern.
Der Ereignis-Leser ist in allen Laeufen abgeschaltet (vorher 0 TP, 7 FP).

Groessenzeilen kommen aus der Tabelle der Zielzeile; erst wenn dort keine
Groessenzeile steht, gilt der Rueckfall auf die naechste Zeile darueber. Das
Zellformat `n  Mean (95% CI)` einer Zeitverlaufstabelle wird als Zeilen-`n`
gelesen (n nach der Wochenzahl, zweites n nach dem ersten Klammerblock).

In der Endvariante stellen sich die {beide['fp']} FP so:

* Groesse 4 (196 Subgruppe, 426 Positionsverlust).
* Mittel 1 im Format `+/-` (345: Gold steht nur als Intervallgrenze).

Hat eine Tabelle mehrere Wochenspalten, gilt die Spalte des letzten Zeitpunkts
und der Block, dessen Ueberschrift das Outcome trifft (Alias oder Akronym wie
`MCS`); ohne Treffer der erste Block. Damit sind 33 und 34 richtig.

Nennt das Outcome ein Messwort (`stiffness`, `range of motion`, `neutral zone`,
`neural zone`), gilt nur eine Zielzeile in einem Block mit passendem Label; bei
mehreren solchen Bloecken gewinnt der spaetere. Das holt 221 bis 223 und waehlt
bei mehreren Spalten desselben Arms das genauere Label (ACVC-HA statt ACVC).

Enthaelt ein Dokument eine Tabelle mit Wochenspalte, in der das Outcome
mehrfach vorkommt, gilt die Zeile des letzten Zeitpunkts statt der
Baseline-Zeile; bei mehreren solchen Tabellen entscheidet die fruehste (die
Haupttabelle steht vor den Subgruppentabellen).

Neu bewertet `tabellen_zeitpunkt` den Tabellenkopf (`+2` Follow-up, Zeitpunkt,
Woche, Monat; `-2` Baseline, Charakteristika). Bei gleichem Alias-Treffer zieht
`ziel_zeile_zeitpunkt` in die Nachher-Tabelle um, aber nur wenn sie ihre Arme in
der Unterschrift nennt (`I; n=104`); `armkuerzel` und `gruppenzeile_wert` lesen
dann die Armzeilen, die Gruppengroesse kommt aus der Unterschrift. Auf den
{len(faelle)} Faellen aendert das keine Zelle (33/30/3 und 17/17/0); die drei
Records aus `PMC4879328` werden damit gold-richtig, siehe
`tabellenwahl_20261121.md`.

`yun2024:193` wird damit richtig (138/131 aus Tabelle 2, Woche 28).
`yun2024:196` bleibt falsch: die Haupttabelle 2 nennt fuer Woche 28 die Werte
80/78, Gold (24/24) stammt aus Tabelle 3, einer Subgruppe (MMSE-J 20 bis 23).

Die Armzuordnung der Groessen folgt der Spaltenposition (`POSITIONAL = True`):
Die erste Datenspalte ist die Intervention, die zweite der Comparator. Sie holt
die acht PMC5617873-Zellen und macht dafuer die beiden Arme von `yun2024:426`
falsch; dieser Verlust ist bewusst (Gold folgt dort den Spaltennamen, siehe
`armreihenfolge_20261121.md`).

Trefferquote: {beide['tp']} von {beide['geliefert']} Zellen, also
{100 * beide['tp'] // max(1, beide['geliefert'])} Prozent. Ereignisse tragen
nichts bei, Groessen und Mittel teilen sich die Treffer. Die Umstellung von der
ersten Zahl auf zwei erlaubte Formate kostet 3 weitere Zellen des Formats
`sonstig`, alle drei waren falsch.
"""
    (HIER / "zielzeile_alle_20261121.md").write_text(bericht, encoding="utf-8", newline="\n")

    print(f"Faelle {len(faelle)}")
    print(f"ohne  : Zielzeile {ohne['zielzeile_gefunden']} | Zellen {ohne['geliefert']} | "
          f"TP {ohne['tp']} | FP {ohne['fp']}")
    print(f"alias : Zielzeile {mit['zielzeile_gefunden']} | Zellen {mit['geliefert']} | "
          f"TP {mit['tp']} | FP {mit['fp']}")
    print(f"nur mit Alias: {len(neu_detail)} Zellen | TP {ergebnis['nur_mit_alias']['tp']} | "
          f"FP {ergebnis['nur_mit_alias']['fp']} | gerundet TP "
          f"{ergebnis['nur_mit_alias']['tp_gerundet']}")
    print(f"alias + Mittel nur (SD): Zellen {streng['geliefert']} | TP {streng['tp']} | "
          f"FP {streng['fp']} | gerundet TP {streng['tp_gerundet']}")
    print(f"Ereignisse aus + Mittel beide Formate: Zellen {beide['geliefert']} | TP {beide['tp']} | "
          f"FP {beide['fp']} | gerundet TP {beide['tp_gerundet']} | gerundet FP {beide['fp_gerundet']}")
    print(f"FP nach Feldtyp: {dict(fp_feldtyp)}")
    print(f"FP nach Format: {ergebnis['fp_nach_format']}")
    for e in neu_detail:
        print(f"  {e['record_id']:14s} {e['feld']:30s} {e['regel']['value']:>10} | gold {e['gold']} | "
              f"{'TP' if e['richtig'] else 'FP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
