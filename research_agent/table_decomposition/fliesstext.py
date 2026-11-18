"""Belegte Zahlen aus dem Fliesstext - als Fundstelle, nicht als Tabellenzelle.

Manche Dokumente drucken die Gruppengroesse nur im laufenden Text, nicht in der
Tabelle. Dieses Modul liest drei gedruckte Formen und macht daraus eine
Fundstelle mit Quelle, Satz, Wert, Arm und Regel:

1. **Label, n = X** - der Arm steht unmittelbar vor seiner Zahl:
   ``(placebo, *n* = 28; RMD, *n* = 29)`` (``PMC5122613``).
2. **Zahlenliste + Armliste + "respectively"** - die Zuordnung steht im Wort
   "respectively": ``(283, 289, and 204 patients received quetiapine
   300 mg/day, quetiapine 600 mg/day, or placebo, respectively)``
   (``PMC4230312``). Nennt der Satz die Population (``ITT``, ``safety
   population``), steht sie in der Regel.
3. **Bruchliste + Armliste + "respectively"** - ``5.1% (4/79), 3.6% (3/83),
   and 5.0% (4/80) in the placebo, 30 µg YIC and 60 µg YIC groups
   respectively`` (``PMC2430617``). Der Zaehler ist eine Ereigniszahl, der
   Nenner eine Gruppengroesse; beide stehen gedruckt.

Tabellenzonen bleiben aussen vor: was in einer Tabelle steht, liest der
Tabellenpfad. Kein Arm wird aus einer Spaltenposition geraten: Form 1 bindet
den Arm am Label, Form 2 und 3 nur ueber das gedruckte ``respectively`` und nur,
wenn Zahlen- und Armliste gleich lang sind. Ohne belegten Arm entsteht kein
Fakt. Es wird kein Gold gelesen und nichts extrahiert.

Zusaetzlich wird jede Fundstelle geprueft, ob dieselbe Zahl in einem Satz
steht, der das Outcome nennt (``−14.88 [n = 289]``). Das unterscheidet die
Analyspopulation von einer zweiten gedruckten Population, ohne dass eine
Population geraten wird: das Merkmal steht als ``belegt`` an der Fundstelle.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import ROLE_EVENTS, ROLE_N, field_for
from .provenienz import DIREKT, MITTEL, QUELLE_TEXT, Provenienz
from .semantics import bind_arm, _satz_belegt_outcome, _satz_um

REGEL_LABEL = "fliesstext_label_n"
REGEL_LISTE = "fliesstext_zahlenliste_beziehungsweise"
REGEL_BRUCH = "fliesstext_bruchliste_beziehungsweise"

# ``placebo, n = 28`` / ``RMD (*n* = 29)``: ein Label direkt vor seiner Zahl.
_LABEL_N_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9 \-\u00b5\u03bc/]{1,40}?)\s*[,;(]\s*"
    r"[*_]{0,3}n[*_]{0,3}\s*=\s*(\d{1,6})",
    re.IGNORECASE,
)

# ``(283, 289, and 204 patients received ..., respectively)``
_LISTE_RE = re.compile(
    r"\(\s*([\d\s,and]{3,80}?)\s*(?:patients|participants|subjects)\s+"
    r"received\s+([^)]{3,220}?)\s*,\s*respectively\s*\)",
    re.IGNORECASE,
)

# ``5.1% (4/79)``: Prozentangabe optional, Zaehler und Nenner gedruckt.
_BRUCH_RE = re.compile(r"(\d{1,3}(?:\.\d+)?%\s*)?\(\s*(\d{1,6})\s*/\s*(\d{1,6})\s*\)")

_TRENNER_RE = re.compile(r",\s*|\s+and\s+", re.IGNORECASE)
_FUEHREND_RE = re.compile(r"^(?:in\s+the|the|in|or|and)\s+", re.IGNORECASE)
_SCHLUSS_RE = re.compile(r"\s+(?:groups?|arms?)$", re.IGNORECASE)

# Gedruckte Dosisangabe: ``600 mg/day``, ``30 µg YIC``, ``0.5 mg/kg``.
_DOSIS_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|μg|g|ml|iu|units?)(?:\s*/\s*[A-Za-z]+)?",
    re.IGNORECASE,
)

_POPULATION_ITT = re.compile(r"\bITT\b|intent[\s-]*to[\s-]*treat", re.IGNORECASE)
_POPULATION_SAFETY = re.compile(r"\bsafety\s+population\b", re.IGNORECASE)


_AKRONYM_STOPP = {"the", "of", "in", "and", "for", "with", "on", "at",
                 "by", "to", "a", "an"}

# Zeichenfenster um eine als ``n = X`` gedruckte Zahl; deckt einen Satz.
_FENSTER = 260


def _akronym(outcome: str) -> str:
    """Gedruckte Abkuerzung eines Outcomes aus seinen Woertern (``CTT``).

    ``Colonic transit time`` steht im Ergebnissatz nur als ``CTT``. Die
    Reihenfolge folgt dem gedruckten Text - nicht einem ``set``, sonst haengt
    das Kuerzel an der Hash-Reihenfolge des Prozesses (belegt: einmal ``CTT``,
    einmal ``TTC``). Mindestens zwei Buchstaben; ein einzelnes ``C`` belegt
    nichts.
    """
    woerter = [wort for wort in re.findall(r"[A-Za-z\u00c0-\u024f]+", outcome or "")
               if len(wort) >= 3 and wort.lower() not in _AKRONYM_STOPP]
    kuerzel = "".join(wort[0] for wort in woerter).upper()
    return kuerzel if len(kuerzel) >= 2 else ""


def _outcome_im_satz(satz: str, outcome: str) -> bool:
    """Nennt der Satz das Outcome - ausgeschrieben oder als Abkuerzung?"""
    if not outcome or not satz:
        return False
    if _satz_belegt_outcome(satz, outcome):
        return True
    kuerzel = _akronym(outcome)
    if not kuerzel:
        return False
    # Gross geschrieben und als eigenes Wort: ``CTT`` belegt, ``ctt`` nicht.
    return bool(re.search(rf"\b{re.escape(kuerzel)}\b", satz))


def _arm_labels(text: str) -> List[str]:
    """Armliste eines Satzes in gedruckter Reihenfolge."""
    cleaned = _FUEHREND_RE.sub("", (text or "").strip())
    cleaned = _SCHLUSS_RE.sub("", cleaned)
    return [teil.strip(" .;:") for teil in _TRENNER_RE.split(cleaned)
            if teil.strip(" .;:")]


def _zahlen(text: str) -> List[int]:
    return [int(treffer) for treffer in re.findall(r"\d{1,6}", text or "")]


def _population(satz: str) -> str:
    """Gedruckte Population des Satzes, wenn sie benannt ist."""
    if _POPULATION_ITT.search(satz or ""):
        return "itt"
    if _POPULATION_SAFETY.search(satz or ""):
        return "sicherheit"
    return ""


def _regel(basis: str, satz: str) -> str:
    population = _population(satz)
    return f"{basis}:{population}" if population else basis


def _dosis(text: str) -> str:
    """Gedruckte Dosisangabe, normiert (``600 mg/day`` -> ``600mg/day``)."""
    treffer = _DOSIS_RE.search(text or "")
    return re.sub(r"\s+", "", treffer.group(0)).lower() if treffer else ""


def _arm_basis(label: str, arm: str, context: Dict[str, Any]) -> str:
    """Grund der Armbindung.

    Traegt das gedruckte Label dieselbe Dosis wie der Arm dieses Records, ist
    die Zuordnung im selben Satz belegt (``quetiapine 600 mg/day`` neben
    ``n = 289``). Ohne gedruckte Dosis bleibt es bei ``fliesstext`` - eine
    Dosis wird nie aus der Reihenfolge oder aus dem Goldwert geraten.
    """
    dosis = _dosis(label)
    if dosis and dosis == _dosis(str(context.get(arm) or "")):
        return f"fliesstext_dosis:{dosis}"
    return "fliesstext"


def _stelle(feld: str, text: str, wert: int, arm: str, regel: str,
            sicherheit: str = MITTEL, arm_basis: str = "fliesstext") -> Provenienz:
    return Provenienz(
        feld=feld, quelle=QUELLE_TEXT, text=text, wert=float(wert), arm=arm,
        arm_basis=arm_basis, zeitpunkt="", art=DIREKT, regel=regel,
        sicherheit=sicherheit, tabelle="", zeile=None, spalten=[],
    )


def _gebunden(label: str, context: Dict[str, Any]) -> Optional[str]:
    """Arm eines gedruckten Labels - nur bei belegtem Vorsprung."""
    binding = bind_arm(
        (label,),
        str(context.get("intervention") or ""),
        str(context.get("comparator") or ""),
    )
    return binding.arm


def _zahl_muster(wert: float) -> str:
    """Dieselbe Zahl in gedruckter Schreibweise, als eigenes Zahlwort."""
    zahl = str(int(wert)) if float(wert).is_integer() else f"{wert:g}"
    return rf"(?<![\d.,]){re.escape(zahl)}(?![\d])"


def _als_n_muster(wert: float) -> str:
    """Dieselbe Zahl als gedruckte Stichprobengroesse: ``n = 289``.

    Markup-tolerant (``*n* = 289``, ``***n*** = 298``, ``<em>n</em> = 5``);
    ein blosses Vorkommen der Zahl belegt nichts.
    """
    zahl = str(int(wert)) if float(wert).is_integer() else f"{wert:g}"
    tag = r"(?:<[^>]{1,16}>)*"
    return (rf"[*_]{{0,3}}{tag}[nN]{tag}[*_]{{0,3}}\s*=\s*"
            rf"{re.escape(zahl)}(?![\d])")


def _ohne_tabellen(text: str, start: int, ende: int,
                   tabellen: Sequence[Any]) -> str:
    """Textstueck ohne die Zeichenspannen der Tabellen."""
    teile: List[str] = []
    pos = start
    for table in sorted(tabellen, key=lambda t: getattr(t, "char_start", -1)):
        t_start = getattr(table, "char_start", -1)
        t_ende = getattr(table, "char_end", -1)
        if t_start < 0 or t_ende <= t_start or t_ende <= pos or t_start >= ende:
            continue
        if t_start > pos:
            teile.append(text[pos:t_start])
        pos = max(pos, min(t_ende, ende))
    if pos < ende:
        teile.append(text[pos:ende])
    return " ".join(teile)


def im_ergebnis(text: str, context: Dict[str, Any], wert: float,
                tabellen: Sequence[Any] = ()) -> bool:
    """Steht diese Zahl als Stichprobengroesse im Satz zum Outcome?

    Gesucht wird ``n = <Zahl>`` in einem Fenster um die Zahl, aus dem die
    Tabellenzonen herausgeschnitten sind, und das Outcome muss in diesem
    Fenster genannt sein (ausgeschrieben oder als gedruckte Abkuerzung).
    Nur so unterscheidet sich ``−14.88 [n = 289]`` im Ergebnissatz von einer
    beilaeufigen Erwaehnung derselben Zahl.
    """
    outcome = str(context.get("outcome") or "")
    if not text or not outcome or wert is None:
        return False
    for treffer in re.finditer(_als_n_muster(wert), text):
        if _in_tabelle(treffer.start(), tabellen):
            continue
        start = max(0, treffer.start() - _FENSTER)
        ende = min(len(text), treffer.end() + _FENSTER)
        fenster = _ohne_tabellen(text, start, ende, tabellen)
        if _outcome_im_satz(fenster, outcome):
            return True
    return False


def _in_tabelle(position: int, tabellen: Sequence[Any]) -> bool:
    for table in tabellen:
        start, ende = getattr(table, "char_start", -1), getattr(table, "char_end", -1)
        if start >= 0 and ende > start and start <= position < ende:
            return True
    return False


def _fakten_label(text: str, context: Dict[str, Any],
                  tabellen: Sequence[Any]) -> List[Provenienz]:
    stellen: List[Provenienz] = []
    for treffer in _LABEL_N_RE.finditer(text or ""):
        if _in_tabelle(treffer.start(), tabellen):
            continue
        label, wert = treffer.group(1).strip(), int(treffer.group(2))
        arm = _gebunden(label, context)
        if arm is None:
            continue
        feld = field_for(ROLE_N, arm)
        if not feld:
            continue
        satz = _satz_um(text, treffer.start(), treffer.end())
        if not _outcome_im_satz(satz, str(context.get("outcome") or "")):
            continue
        stellen.append(_stelle(feld, " ".join(treffer.group(0).split()), wert, arm,
                               _regel(REGEL_LABEL, satz),
                               arm_basis=_arm_basis(label, arm, context)))
    return stellen


def _fakten_liste(text: str, context: Dict[str, Any],
                  tabellen: Sequence[Any]) -> List[Provenienz]:
    stellen: List[Provenienz] = []
    for treffer in _LISTE_RE.finditer(text or ""):
        if _in_tabelle(treffer.start(), tabellen):
            continue
        werte = _zahlen(treffer.group(1))
        labels = _arm_labels(treffer.group(2))
        if len(werte) != len(labels) or len(werte) < 2:
            continue
        satz = _satz_um(text, treffer.start(), treffer.end())
        # Nur eine **benannte** Population: die Liste belegt eine Population,
        # nicht das Outcome (``ITT population``, ``safety population``).
        if not _population(satz):
            continue
        for wert, label in zip(werte, labels):
            arm = _gebunden(label, context)
            if arm is None:
                continue
            feld = field_for(ROLE_N, arm)
            if not feld:
                continue
            stellen.append(_stelle(feld, f"{wert} patients received {label}", wert,
                                   arm, _regel(REGEL_LISTE, satz),
                                   arm_basis=_arm_basis(label, arm, context)))
    return stellen


def _fakten_bruch(text: str, context: Dict[str, Any],
                  tabellen: Sequence[Any]) -> List[Provenienz]:
    """Bruchliste mit gedrucktem ``respectively``: Zaehler und Nenner."""
    stellen: List[Provenienz] = []
    for treffer in re.finditer(r"\brespectively\b", text or ""):
        if _in_tabelle(treffer.start(), tabellen):
            continue
        satz = _satz_um(text, treffer.start(), treffer.end())
        if not _outcome_im_satz(satz, str(context.get("outcome") or "")):
            continue
        # Die Satzsuche ueber das Wort ``respectively`` statt ueber eine eigene
        # Klammer: ``5.1%`` traegt einen Punkt, ein Satzmuster mit ``[^.!?]``
        # wuerde dort enden.
        ende = satz.find("respectively")
        if ende < 0:
            continue
        brueche = [bruch for bruch in _BRUCH_RE.finditer(satz) if bruch.start() < ende]
        if len(brueche) < 2:
            continue
        zwischen = re.sub(r"^[\s),;]+", "", satz[brueche[-1].end():ende])
        labels = _arm_labels(zwischen)
        if len(labels) != len(brueche):
            continue
        for bruch, label in zip(brueche, labels):
            arm = _gebunden(label, context)
            if arm is None:
                continue
            zaehler, nenner = int(bruch.group(2)), int(bruch.group(3))
            text_teil = " ".join(bruch.group(0).split())
            basis = _arm_basis(label, arm, context)
            ereignis = field_for(ROLE_EVENTS, arm)
            if ereignis:
                stellen.append(_stelle(ereignis, text_teil, zaehler, arm,
                                       _regel(REGEL_BRUCH, satz),
                                       arm_basis=basis))
            feld = field_for(ROLE_N, arm)
            if feld:
                stellen.append(_stelle(feld, text_teil, nenner, arm,
                                       _regel(REGEL_BRUCH, satz),
                                       arm_basis=basis))
    return stellen


def stellen(text: str, context: Optional[Dict[str, Any]] = None,
            tabellen: Sequence[Any] = ()) -> Dict[str, List[Provenienz]]:
    """Je Feld die Fliesstext-Fundstellen eines Dokuments.

    ``tabellen`` sind die Tabellen des Dokuments; ihre Zeichenspanne bleibt
    aussen vor, damit eine Kopfangabe nicht als Fliesstext zaehlt. Die
    Sicherheit bleibt ``mittel`` - der Text nennt den Arm, aber keine Zeile.
    """
    context = context or {}
    if not text:
        return {}
    gefunden: List[Provenienz] = []
    gefunden.extend(_fakten_label(text, context, tabellen))
    gefunden.extend(_fakten_liste(text, context, tabellen))
    gefunden.extend(_fakten_bruch(text, context, tabellen))
    out: Dict[str, List[Provenienz]] = {}
    gesehen = set()
    for stelle in gefunden:
        schluessel = (stelle.feld, stelle.text, stelle.wert, stelle.arm)
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        if stelle.wert is not None and im_ergebnis(text, context, stelle.wert,
                                                  tabellen):
            stelle = replace(stelle, belegt=True)
        out.setdefault(stelle.feld, []).append(stelle)
    return out
