"""Adapter fuer den erweiterten Benchmark.

Jeder Adapter stellt ``build(...)`` bereit und liefert Records nach
``extended_benchmark/schema.json``.
"""

from . import ebm_nlp, evidence_inference, yun

__all__ = ["ebm_nlp", "evidence_inference", "yun"]
