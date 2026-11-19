"""Tests fuer ``validate_arm_context`` (gedruckter n-Kopf gegen Record-Kontext).

Die Faelle decken die vier Wege ab, die die Funktion unterscheiden muss:
Band ohne n, fehlendes Band, Beschreibung als Hinweis und Treffer mit n.
Der erste Test ist die Regression aus dem Sprint-48-Umbau: ein vorhandenes
Band ohne n darf nicht als "Arm nicht auffindbar" gemeldet werden.
"""

from research_agent.table_decomposition.model import Column, HeaderBand, Table
from research_agent.table_decomposition.validation import (
    SEVERITY_INFO,
    SEVERITY_WARNING,
    validate_arm_context,
)

KONTEXT = {"intervention": "Probiotic", "comparator": "Placebo"}


def _tabelle(baender, fakten):
    breite = max(ende for _level, _text, _start, ende in baender) + 1
    table = Table(table_id="T:T1", doc_id="T", index=1)
    table.header_bands = [
        HeaderBand(level=level, text=text, col_start=start, col_end=ende)
        for level, text, start, ende in baender
    ]
    table.columns = [
        Column(col_id=i, x_start=i * 10, x_end=i * 10 + 9) for i in range(breite)
    ]
    table.header_facts = fakten
    return table


def _n(text, wert, arm, start, ende):
    return {"text": text, "value": wert, "arm": arm,
            "col_start": start, "col_end": ende}


def test_band_ohne_n_ist_widerspruch_nicht_fehlendes_band():
    table = _tabelle(
        [(0, "Probiotic group", 1, 2),
         (0, "Antibiotic group", 3, 4),
         (0, "Placebo group", 5, 6)],
        [_n("(n=16)", 16, "intervention", 1, 2),
         _n("(n=15)", 15, "comparator", 3, 4)],
    )

    findings = validate_arm_context(table, KONTEXT)

    assert [finding.code for finding in findings] == ["kopf_n_widerspricht_kontext"]
    assert findings[0].severity == SEVERITY_WARNING
    assert "Probiotic group" in findings[0].message


def test_fehlendes_band_ist_warnung():
    table = _tabelle(
        [(0, "Probiotic group", 1, 2), (0, "Antibiotic group", 3, 4)],
        [_n("(n=16)", 16, "intervention", 1, 2)],
    )

    findings = validate_arm_context(
        table, {"intervention": "Probiotic", "comparator": "Prebiotic"}
    )

    assert [finding.code for finding in findings] == ["kontextarm_nicht_im_kopf"]
    assert findings[0].severity == SEVERITY_WARNING
    assert "Prebiotic" in findings[0].message


def test_beschreibung_ist_hinweis():
    table = _tabelle(
        [(0, "CoPAT (n = 103)", 1, 2), (0, "IPAT (n = 97)", 3, 4)],
        [_n("CoPAT (n = 103)", 103, "intervention", 1, 2)],
    )

    findings = validate_arm_context(
        table,
        {"intervention": "CoPAT",
         "comparator": "full course of therapy in the hospital setting"},
    )

    assert [finding.code for finding in findings] == ["kontextarm_nicht_im_kopf"]
    assert findings[0].severity == SEVERITY_INFO
    assert "Beschreibung" in findings[0].message


def test_treffer_mit_n_ist_still():
    table = _tabelle(
        [(0, "Probiotic group", 1, 2), (0, "Placebo group", 3, 4)],
        [_n("(n=16)", 16, "intervention", 1, 2),
         _n("(n=15)", 15, "comparator", 3, 4)],
    )

    assert validate_arm_context(table, KONTEXT) == []
