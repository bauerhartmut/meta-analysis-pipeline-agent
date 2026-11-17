"""
Dataset Exporter - Creates fine-tuning datasets from accumulated research knowledge.
Exports knowledge as JSONL (for LLM fine-tuning) or Markdown (for reading).
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from collections import Counter

from .database import Database

logger = logging.getLogger(__name__)


class DatasetExporter:
    """Export research knowledge as structured datasets."""

    def __init__(self, db: Database):
        self.db = db

    def export_full_dataset(self, output_dir: str = "data/dataset") -> Dict[str, str]:
        """
        Export all research knowledge as a complete dataset.
        Returns dict of file paths created.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        files = {}

        # 1. Knowledge Base (JSONL for fine-tuning)
        kb_path = f"{output_dir}/knowledge_base_{timestamp}.jsonl"
        files["knowledge_base"] = self._export_knowledge_base(kb_path)

        # 2. Q&A Pairs (for instruction tuning)
        qa_path = f"{output_dir}/qa_pairs_{timestamp}.jsonl"
        files["qa_pairs"] = self._export_qa_pairs(qa_path)

        # 3. Hypothesis Dataset
        hyp_path = f"{output_dir}/hypotheses_{timestamp}.jsonl"
        files["hypotheses"] = self._export_hypotheses(hyp_path)

        # 4. Source Catalog
        src_path = f"{output_dir}/sources_{timestamp}.json"
        files["sources"] = self._export_sources(src_path)

        # 5. Research Report (Markdown)
        report_path = f"{output_dir}/research_report_{timestamp}.md"
        files["report"] = self._export_report(report_path)

        # 6. Complete Knowledge Graph
        graph_path = f"{output_dir}/knowledge_graph_{timestamp}.json"
        files["knowledge_graph"] = self._export_knowledge_graph(graph_path)

        logger.info(f"Dataset exported to {output_dir}: {list(files.keys())}")
        return files

    def _export_knowledge_base(self, path: str) -> str:
        """
        Export all facts, hypotheses, and claims as JSONL.
        Each line is a JSON object with:
        - type: fact/hypothesis/claim
        - content: the knowledge
        - confidence: confidence level
        - sources: supporting source IDs
        - metadata: additional context
        """
        records = []

        # Facts
        facts = self.db.get_facts(limit=1000)
        for fact in facts:
            records.append({
                "type": "fact",
                "content": fact.get("content", ""),
                "confidence": fact.get("confidence", 0.5),
                "sources": json.loads(fact.get("source_ids", "[]")),
                "topic": fact.get("topic", ""),
                "date_added": fact.get("date_added", ""),
            })

        # Hypotheses
        hypotheses = self.db.get_hypotheses(limit=1000)
        for hyp in hypotheses:
            records.append({
                "type": "hypothesis",
                "content": hyp.get("claim", ""),
                "confidence": hyp.get("confidence", 0.3),
                "status": hyp.get("status", ""),
                "supporting_evidence": json.loads(hyp.get("supporting_evidence", "[]")),
                "contradicting_evidence": json.loads(hyp.get("contradicting_evidence", "[]")),
                "alternative_explanations": json.loads(hyp.get("alternative_explanations", "[]")),
                "predictions": json.loads(hyp.get("predictions", "[]")),
                "falsification_conditions": hyp.get("falsification_conditions", ""),
                "rejection_reason": hyp.get("rejection_reason", ""),
                "topic": hyp.get("topic", ""),
                "date_added": hyp.get("date_added", ""),
                "last_updated": hyp.get("last_updated", ""),
            })

        # Claims
        claims = self.db.get_claims(limit=1000)
        for claim in claims:
            records.append({
                "type": "claim",
                "content": claim.get("content", ""),
                "confidence": claim.get("confidence", 0.5),
                "source_id": claim.get("source_id", ""),
                "claim_type": claim.get("claim_type", ""),
                "date_added": claim.get("date_added", ""),
            })

        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(f"Knowledge base: {len(records)} records -> {path}")
        return path

    def _export_qa_pairs(self, path: str) -> str:
        """
        Export question-answer pairs for instruction tuning.
        Format: {"instruction": "...", "input": "...", "output": "..."}
        """
        pairs = []

        # From answered questions
        questions = self.db._get_all(
            "research_questions",
            where="status = 'answered' AND answer_summary != ''",
            limit=500,
        )
        for q in questions:
            pairs.append({
                "instruction": "Based on the research, answer this question thoroughly.",
                "input": q.get("question", ""),
                "output": q.get("answer_summary", ""),
                "metadata": {
                    "importance": q.get("importance", 0.5),
                    "uncertainty": q.get("uncertainty", 0.5),
                }
            })

        # From hypotheses with reasoning
        hypotheses = self.db.get_hypotheses(limit=500)
        for hyp in hypotheses:
            if hyp.get("status") in ("supported", "confirmed", "contested"):
                supporting = json.loads(hyp.get("supporting_evidence", "[]"))
                contra = json.loads(hyp.get("contradicting_evidence", "[]"))
                alternatives = json.loads(hyp.get("alternative_explanations", "[]"))

                output_parts = [f"Hypothesis: {hyp.get('claim', '')}"]
                output_parts.append(f"Status: {hyp.get('status', '')} (confidence: {hyp.get('confidence', 0):.0%})")
                if alternatives:
                    output_parts.append(f"Alternative explanations: {'; '.join(alternatives)}")
                if hyp.get("falsification_conditions"):
                    output_parts.append(f"Falsification conditions: {hyp.get('falsification_conditions')}")

                pairs.append({
                    "instruction": "Analyze this research hypothesis and provide a balanced assessment.",
                    "input": hyp.get("claim", ""),
                    "output": "\n".join(output_parts),
                    "metadata": {
                        "status": hyp.get("status", ""),
                        "confidence": hyp.get("confidence", 0),
                    }
                })

        # From journal entries (research process knowledge)
        journal = self.db.get_journal_entries(limit=200)
        for entry in journal:
            findings = json.loads(entry.get("important_findings", "[]"))
            if findings:
                pairs.append({
                    "instruction": "Summarize the key findings from this research cycle.",
                    "input": entry.get("research_question", ""),
                    "output": "\n".join(f"- {f}" for f in findings),
                    "metadata": {
                        "cycle": entry.get("cycle_number", 0),
                        "confidence_change": entry.get("confidence_change", ""),
                    }
                })

        with open(path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        logger.info(f"Q&A pairs: {len(pairs)} pairs -> {path}")
        return path

    def _export_hypotheses(self, path: str) -> str:
        """Export detailed hypothesis dataset with full evidence chains."""
        hypotheses = self.db.get_hypotheses(limit=1000)
        records = []

        for hyp in hypotheses:
            evidence = self.db.get_evidence_for_hypothesis(hyp["id"])
            record = {
                "id": hyp["id"],
                "claim": hyp.get("claim", ""),
                "status": hyp.get("status", ""),
                "confidence": hyp.get("confidence", 0.3),
                "supporting_evidence": [
                    {
                        "content": e.get("content", ""),
                        "strength": e.get("strength", 0.5),
                        "source_id": e.get("source_id", ""),
                    }
                    for e in evidence if e.get("evidence_type") == "supports"
                ],
                "contradicting_evidence": [
                    {
                        "content": e.get("content", ""),
                        "strength": e.get("strength", 0.5),
                        "source_id": e.get("source_id", ""),
                    }
                    for e in evidence if e.get("evidence_type") == "contradicts"
                ],
                "alternative_explanations": json.loads(hyp.get("alternative_explanations", "[]")),
                "predictions": json.loads(hyp.get("predictions", "[]")),
                "falsification_conditions": hyp.get("falsification_conditions", ""),
                "rejection_reason": hyp.get("rejection_reason", ""),
                "topic": hyp.get("topic", ""),
                "date_added": hyp.get("date_added", ""),
                "last_updated": hyp.get("last_updated", ""),
            }
            records.append(record)

        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(f"Hypotheses: {len(records)} records -> {path}")
        return path

    def _export_sources(self, path: str) -> str:
        """Export source catalog as JSON."""
        sources = self.db.get_all_sources(limit=1000)
        catalog = []
        for s in sources:
            catalog.append({
                "id": s.get("id", ""),
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "source_type": s.get("source_type", ""),
                "credibility": s.get("credibility", 0.5),
                "summary": s.get("summary", ""),
                "key_claims": json.loads(s.get("key_claims", "[]")),
                "counter_claims": json.loads(s.get("counter_claims", "[]")),
                "date_added": s.get("date_added", ""),
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        logger.info(f"Sources: {len(catalog)} entries -> {path}")
        return path

    def _export_report(self, path: str) -> str:
        """Export a comprehensive research report as Markdown."""
        stats = self.db.get_stats()
        hypotheses = self.db.get_hypotheses(limit=100)
        questions = self.db._get_all("research_questions", limit=100)
        sources = self.db.get_all_sources(limit=100)
        journal = self.db.get_journal_entries(limit=50)
        contradictions = self.db.get_unresolved_contradictions()

        # Get topic from session
        session = self.db.get_active_session()
        if not session:
            sessions = self.db.get_all_sessions(limit=1)
            session = sessions[0] if sessions else {}

        topic = session.get("topic", "Unknown Topic")

        report = []
        report.append(f"# Research Report: {topic}")
        report.append(f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        report.append(f"\n---\n")

        # Statistics
        report.append("## Statistics\n")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Research Cycles | {stats.get('total_cycles', 0)} |")
        report.append(f"| Sources Analyzed | {stats.get('sources', 0)} |")
        report.append(f"| Facts Discovered | {stats.get('facts', 0)} |")
        report.append(f"| Hypotheses Generated | {stats.get('hypotheses', 0)} |")
        report.append(f"| Open Questions | {stats.get('open_questions', 0)} |")
        report.append(f"| Contradictions | {stats.get('contradictions', 0)} |")
        report.append(f"| Knowledge Nodes | {stats.get('knowledge_nodes', 0)} |")
        report.append("")

        # Active Hypotheses
        active = [h for h in hypotheses if h.get("status") in ("proposed", "plausible", "supported", "contested")]
        if active:
            report.append("## Active Hypotheses\n")
            for h in sorted(active, key=lambda x: x.get("confidence", 0), reverse=True):
                conf = h.get("confidence", 0)
                status = h.get("status", "")
                report.append(f"### [{status.upper()}] {h.get('claim', '')}")
                report.append(f"- **Confidence:** {conf:.0%}")
                alternatives = json.loads(h.get("alternative_explanations", "[]"))
                if alternatives:
                    report.append(f"- **Alternatives:** {'; '.join(alternatives)}")
                predictions = json.loads(h.get("predictions", "[]"))
                if predictions:
                    report.append(f"- **Predictions:**")
                    for p in predictions:
                        report.append(f"  - {p}")
                if h.get("falsification_conditions"):
                    report.append(f"- **Falsification:** {h.get('falsification_conditions')}")
                report.append("")

        # Rejected Hypotheses
        rejected = [h for h in hypotheses if h.get("status") == "rejected"]
        if rejected:
            report.append("## Rejected Hypotheses\n")
            for h in rejected:
                report.append(f"- **{h.get('claim', '')}**")
                if h.get("rejection_reason"):
                    report.append(f"  - Reason: {h.get('rejection_reason')}")
            report.append("")

        # Contradictions
        if contradictions:
            report.append("## Unresolved Contradictions\n")
            for c in contradictions:
                report.append(f"- **{c.get('claim_a', '')}** vs **{c.get('claim_b', '')}**")
                if c.get("resolution_note"):
                    report.append(f"  - Note: {c.get('resolution_note')}")
            report.append("")

        # Key Sources
        if sources:
            report.append("## Key Sources\n")
            for s in sorted(sources, key=lambda x: x.get("credibility", 0), reverse=True)[:20]:
                report.append(f"- [{s.get('title', 'Untitled')}]({s.get('url', '')}) (credibility: {s.get('credibility', 0):.1f})")
            report.append("")

        # Research Journal (last 10 entries)
        if journal:
            report.append("## Research Journal (Recent)\n")
            for j in journal[:10]:
                findings = json.loads(j.get("important_findings", "[]"))
                report.append(f"### Cycle {j.get('cycle_number', '?')} - {j.get('timestamp', '')}")
                report.append(f"**Question:** {j.get('research_question', '')}")
                if findings:
                    report.append(f"**Findings:**")
                    for f in findings:
                        report.append(f"  - {f}")
                report.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))

        logger.info(f"Report -> {path}")
        return path

    def _export_knowledge_graph(self, path: str) -> str:
        """Export knowledge graph as JSON."""
        nodes = self.db.get_knowledge_nodes(limit=500)
        all_edges = []
        for node in nodes[:100]:
            edges = self.db.get_edges_for_node(node["id"])
            all_edges.extend(edges)

        graph = {
            "nodes": nodes,
            "edges": all_edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(all_edges),
                "exported": datetime.utcnow().isoformat(),
            }
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)

        logger.info(f"Knowledge graph: {len(nodes)} nodes, {len(all_edges)} edges -> {path}")
        return path

    def export_for_finetuning(self, output_path: str = "data/dataset/finetune.jsonl") -> str:
        """
        Export dataset specifically formatted for LLM fine-tuning.
        Creates instruction-following pairs from all accumulated knowledge.
        Includes debate pairs (thesis -> counterargument -> refutation).
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        records = []

        # Enhanced system prompt for the specialized model
        system_prompt = (
            "You are a rigorous research analyst working on systematic reviews and "
            "meta-analyses of intervention studies. You argue both sides of a claim, "
            "ground every number in a quoted source, and name limitations, "
            "heterogeneity and risk of bias instead of smoothing them over."
        )

        # === CATEGORY 1: FACTS (knowledge retrieval pairs) ===
        facts = self.db.get_facts(limit=500)
        for fact in facts:
            confidence = fact.get('confidence', 0.5)
            if confidence < 0.5:
                continue  # Skip low-confidence facts
            records.append({
                "category": "facts",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"What does the scientific evidence say about: {fact.get('topic', 'this topic')}?"},
                    {"role": "assistant", "content": f"Based on peer-reviewed research: {fact.get('content', '')}\n\nConfidence: {confidence:.0%}. This finding is supported by {len(json.loads(fact.get('source_ids', '[]')))} sources."},
                ]
            })

        # === CATEGORY 2: HYPOTHESIS EVALUATIONS (analytical pairs) ===
        hypotheses = self.db.get_hypotheses(limit=500)
        for hyp in hypotheses:
            if hyp.get("status") in ("supported", "confirmed", "contested"):
                supporting = json.loads(hyp.get("supporting_evidence", "[]"))
                contra = json.loads(hyp.get("contradicting_evidence", "[]"))
                alternatives = json.loads(hyp.get("alternative_explanations", "[]"))
                predictions = json.loads(hyp.get("predictions", "[]"))

                # Build rich response
                response_parts = [
                    f"## Hypothesis Analysis\n",
                    f"**Claim:** {hyp.get('claim', '')}",
                    f"**Status:** {hyp.get('status', '')} | **Confidence:** {hyp.get('confidence', 0):.0%}\n",
                ]
                if supporting:
                    response_parts.append(f"**Supporting Evidence ({len(supporting)} items):**")
                    for s in supporting[:3]:
                        if isinstance(s, str):
                            response_parts.append(f"- {s}")
                if contra:
                    response_parts.append(f"\n**Contradicting Evidence ({len(contra)} items):**")
                    for c in contra[:3]:
                        if isinstance(c, str):
                            response_parts.append(f"- {c}")
                if alternatives:
                    response_parts.append(f"\n**Alternative Explanations:**")
                    for a in alternatives:
                        response_parts.append(f"- {a}")
                if predictions:
                    response_parts.append(f"\n**Testable Predictions:**")
                    for p in predictions:
                        response_parts.append(f"- {p}")
                if hyp.get("falsification_conditions"):
                    response_parts.append(f"\n**Falsification Conditions:** {hyp.get('falsification_conditions')}")

                records.append({
                    "category": "hypothesis_evaluations",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Provide a thorough analysis of this hypothesis: {hyp.get('claim', '')}"},
                        {"role": "assistant", "content": "\n".join(response_parts)},
                    ]
                })

        # === CATEGORY 3: DEBATE PAIRS (thesis -> counterargument -> refutation) ===
        # Generate debate pairs for ALL hypotheses with any evidence
        for hyp in hypotheses:
            contra = json.loads(hyp.get("contradicting_evidence", "[]") or '[]')
            supporting = json.loads(hyp.get("supporting_evidence", "[]") or '[]')
            alternatives = json.loads(hyp.get("alternative_explanations", "[]") or '[]')

            # Collect counter-arguments from any available source
            counter_args = []
            if contra:
                counter_args.extend([c for c in contra if isinstance(c, str)])
            if alternatives:
                counter_args.extend([a for a in alternatives if isinstance(a, str)])

            # Skip only if truly no evidence at all
            if not supporting and not counter_args:
                continue

            claim = hyp.get('claim', '')
            confidence = hyp.get('confidence', 0)
            status = hyp.get('status', 'active')

            # Build debate response
            debate_response = [
                f"## Critical Analysis: {claim[:120]}\n",
                f"### Thesis (Confidence: {confidence:.0%}, Status: {status}):\n",
                f"{claim}\n",
            ]

            # Arguments against
            if counter_args:
                debate_response.append(f"### Strongest Counter-Arguments:\n")
                for i, arg in enumerate(counter_args[:5], 1):
                    if isinstance(arg, str) and len(arg) > 10:
                        debate_response.append(f"{i}. {arg}")
            else:
                # Generate generic counter-arguments based on hypothesis content
                generic_counters = []
                claim_lower = claim.lower()
                if 'effect' in claim_lower or 'reduc' in claim_lower or 'improv' in claim_lower:
                    generic_counters.append("The pooled effect may be driven by small studies with wide confidence intervals rather than by a robust association.")
                if 'heterogen' in claim_lower or 'variance' in claim_lower:
                    generic_counters.append("Heterogeneity between studies is not explained by the reported population or design.")
                if 'random' in claim_lower or 'trial' in claim_lower:
                    generic_counters.append("Risk of bias in the included trials (allocation, blinding, attrition) is not addressed by the claim.")
                if 'signific' in claim_lower:
                    generic_counters.append("Statistical significance is not the same as a clinically relevant effect size.")
                if 'publication' in claim_lower or 'bias' in claim_lower:
                    generic_counters.append("Publication bias and selective outcome reporting may inflate the apparent effect.")
                if not generic_counters:
                    generic_counters.append("The hypothesis may overstate the strength of available evidence while underestimating alternative explanations.")
                    generic_counters.append("Correlation does not imply causation; confounding variables may explain the observed relationships.")
                debate_response.append(f"### Strongest Counter-Arguments:\n")
                for i, arg in enumerate(generic_counters[:3], 1):
                    debate_response.append(f"{i}. {arg}")

            # Responses / supporting evidence
            if supporting:
                debate_response.append(f"\n### Counter-Counterarguments (Responses):\n")
                debate_response.append(f"Despite these criticisms, the hypothesis maintains {confidence:.0%} confidence because:")
                for s in supporting[:3]:
                    if isinstance(s, str) and len(s) > 10:
                        debate_response.append(f"- {s}")
            else:
                debate_response.append(f"\n### Current Defense:\n")
                debate_response.append(f"The hypothesis maintains {confidence:.0%} confidence based on theoretical plausibility and indirect evidence.")
                debate_response.append(f"Direct empirical support is still accumulating.")

            # Balanced assessment
            debate_response.append(f"\n### Balanced Assessment:")
            debate_response.append(f"The hypothesis remains {status} with {confidence:.0%} confidence.")
            if counter_args:
                debate_response.append(f"Key uncertainty: Are the {len(counter_args)} counter-arguments sufficient to significantly revise confidence?")
            else:
                debate_response.append(f"Key uncertainty: Lack of direct contradicting evidence does not equal strong support.")

            records.append({
                "category": "debate_pairs",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Provide a rigorous scientific debate on this claim: '{claim[:200]}' — present the strongest arguments for and against, then give your balanced assessment."},
                    {"role": "assistant", "content": "\n".join(debate_response)},
                ]
            })

        # === CATEGORY 4: Q&A PAIRS (answered research questions) ===
        questions = self.db._get_all(
            "research_questions",
            where="status = 'answered' AND answer_summary != ''",
            limit=500,
        )
        for q in questions:
            answer = q.get("answer_summary", "")
            if len(answer) < 20:  # Skip trivial answers
                continue
            records.append({
                "category": "qa_pairs",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": q.get("question", "")},
                    {"role": "assistant", "content": answer},
                ]
            })

        # === CATEGORY 6: EVIDENCE SYNTHESIS PAIRS ===
        # For each hypothesis with evidence, create a synthesis pair
        for hyp in hypotheses:
            evidence_records = self.db.get_evidence_for_hypothesis(hyp["id"])
            if len(evidence_records) < 2:
                continue

            evidence_summary = []
            for ev in evidence_records[:10]:
                ev_type = ev.get("evidence_type", "unknown")
                strength = ev.get("strength", 0.5)
                content = ev.get("content", "")[:200]
                evidence_summary.append(f"[{ev_type}] (strength: {strength:.0%}): {content}")

            records.append({
                "category": "evidence_synthesis",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Synthesize all available evidence for or against: {hyp.get('claim', '')[:150]}. Consider the strength and type of each piece of evidence."},
                    {"role": "assistant", "content": (
                        f"## Evidence Synthesis\n\n"
                        f"**Hypothesis:** {hyp.get('claim', '')}\n"
                        f"**Current Confidence:** {hyp.get('confidence', 0):.0%} ({hyp.get('status', 'proposed')})\n\n"
                        f"**Evidence inventory ({len(evidence_records)} pieces):**\n"
                        + "\n".join(evidence_summary)
                        + f"\n\n**Synthesis:** Based on {len(evidence_records)} pieces of evidence, "
                        f"the hypothesis maintains {hyp.get('confidence', 0):.0%} confidence. "
                        f"The evidence base is {'strong' if len(evidence_records) > 5 else 'developing'}. "
                        f"Key uncertainty remains around: {'; '.join(json.loads(hyp.get('alternative_explanations', '[]'))[:2]) or 'methodological limitations'}"
                    )},
                ]
            })

        # === CATEGORY 7: CHAIN-OF-THOUGHT PAIRS (reasoning training) ===
        # Generate CoT pairs for existing hypotheses
        for hyp in hypotheses:
            if hyp.get("status") in ("supported", "contested"):
                supporting = json.loads(hyp.get("supporting_evidence", "[]") or '[]')
                contra = json.loads(hyp.get("contradicting_evidence", "[]") or '[]')
                claim = hyp.get('claim', '')
                confidence = hyp.get('confidence', 0)

                # Build CoT response
                cot_response = [
                    f"Let me analyze this hypothesis step by step:\n\n",
                    f"**Step 1: What is the hypothesis claiming?**\n{claim}\n\n",
                    f"**Step 2: What evidence supports this?**\n",
                ]
                if supporting:
                    for s in supporting[:3]:
                        if isinstance(s, str):
                            cot_response.append(f"- {s}\n")
                else:
                    cot_response.append("- (No direct supporting evidence found)\n")

                cot_response.append(f"\n**Step 3: What evidence contradicts this?**\n")
                if contra:
                    for c in contra[:3]:
                        if isinstance(c, str):
                            cot_response.append(f"- {c}\n")
                else:
                    cot_response.append("- (No direct contradicting evidence found)\n")

                cot_response.append(f"\n**Step 4: What are the key uncertainties?**\n")
                alternatives = json.loads(hyp.get("alternative_explanations", "[]") or '[]')
                if alternatives:
                    for a in alternatives[:2]:
                        if isinstance(a, str):
                            cot_response.append(f"- {a}\n")
                else:
                    cot_response.append("- Alternative explanations not yet explored\n")

                cot_response.append(f"\n**Step 5: What is my conclusion?**\n")
                cot_response.append(f"Based on {len(supporting)} supporting and {len(contra)} contradicting evidence items, ")
                cot_response.append(f"the hypothesis has {confidence:.0%} confidence. ")
                if confidence > 0.6:
                    cot_response.append("The evidence generally supports this hypothesis, though uncertainties remain.")
                elif confidence > 0.4:
                    cot_response.append("The evidence is mixed, with roughly equal support and contradiction.")
                else:
                    cot_response.append("The evidence currently does not strongly support this hypothesis.")

                records.append({
                    "category": "chain_of_thought",
                    "messages": [
                        {"role": "system", "content": system_prompt + "\n\nIMPORTANT: Always show your step-by-step reasoning before giving conclusions."},
                        {"role": "user", "content": f"Analyze this hypothesis step by step: {claim}"},
                        {"role": "assistant", "content": "".join(cot_response)},
                    ]
                })

        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Count by category for logging
        _cat_counts = Counter(r.get('category', 'unknown') for r in records)
        logger.info(f"Fine-tuning dataset: {len(records)} records -> {output_path}")
        for _cat, _cnt in _cat_counts.most_common():
            logger.info(f"  {_cat}: {_cnt}")
        return output_path
