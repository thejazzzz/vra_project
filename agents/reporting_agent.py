# agents/reporting_agent.py
import logging
import os
from typing import Dict, Any
from services.analysis_service import generate_report_content
from services.research_service import get_relevant_context

logger = logging.getLogger(__name__)

class ReportingAgent:
    """
    Synthesizes global analysis, structured summaries, gaps, trends, and graphs
    into a final research report.
    Phase 3.1 Enhanced: Gap ID Anchoring & Provenance Control.
    """

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("✍️ Reporting Agent: Generating final report (Enhanced)...")

        query = state.get("query", "")
        audience = state.get("audience", "general").lower()
        
        # Load Template
        template_name = f"{audience}.md"
        if audience not in ["phd", "industry"]:
             template_name = "general.md"
             
        try:
            template_path = os.path.join(os.path.dirname(__file__), "..", "templates", template_name)
            if not os.path.exists(template_path):
                template_content = "No template found. Write a standard research report."
            else:
                with open(template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            template_content = "Write a standard research report."

        # ---------------------------------------------------------
        # Prepare Data Context
        # ---------------------------------------------------------
        
        # RETRIEVAL REPLACEMENT: use semantics instead of dumping state
        retrieval_query = f"{query} overview implications state of the art"
        
        import asyncio
        from concurrent.futures import TimeoutError as FuturesTimeoutError
        
        try:
            # Standard entry point for new thread
            papers_context = asyncio.run(get_relevant_context(
                retrieval_query, 
                limit=7, 
                max_tokens=2500,
                agent_name="reporting_agent"
            ))
        except RuntimeError as e:
            # Fallback: Handle cases where an event loop might already exist/run
            logger.warning(f"Asyncio.run failed ({e}), attempting fallback via existing loop.")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                     fut = asyncio.run_coroutine_threadsafe(get_relevant_context(
                        retrieval_query, 
                        limit=7, 
                        max_tokens=2500,
                        agent_name="reporting_agent"
                     ), loop)
                     
                     try:
                         # FIX: Add timeout to prevent hanging indefinitely
                         papers_context = fut.result(timeout=30)
                     except FuturesTimeoutError:
                         logger.error("Async retrieval timed out (30s). Cancelling.")
                         fut.cancel()
                         papers_context = ""
                else:
                     papers_context = loop.run_until_complete(get_relevant_context(
                        retrieval_query, 
                        limit=7, 
                        max_tokens=2500,
                        agent_name="reporting_agent"
                     ))
            except Exception as e2:
                 logger.error(f"Async retrieval failed completely: {e2}")
                 papers_context = ""
        except Exception as e:
             logger.error(f"Async retrieval unexpected error: {e}")
             papers_context = ""

        if not papers_context:
            # FIX 5: Neutral fallback message
            papers_context = "No detailed papers retrieved."

        # Gaps (Anchored)
        gaps = state.get("research_gaps", [])
        gaps_context = "## Identified Gaps\n"
        for gap in gaps:
            gap_id = gap.get("gap_id", "UNKNOWN")
            rationale = gap.get("rationale", "")
            gaps_context += f"- [{gap_id}] {gap.get('type')}: {gap.get('description')}\n"
            if rationale:
                gaps_context += f"  Rationale: {rationale}\n"

        # Trends (with Status & Confidence)
        trends = state.get("concept_trends", {})
        trends_context = "## Trends\n"
        for concept, data in trends.items():
            status = data.get("status", "unknown")
            growth = data.get("growth_rate", 0)
            conf = data.get("trend_confidence", 0)
            trends_context += f"- {concept}: {status.upper()} (Growth: {growth:.2f}, Conf: {conf})\n"

        # Author Stats (Influence & Diversity)
        ag = state.get("author_graph", {})
        author_context = "## Author Insights\n"
        if ag and "nodes" in ag:
            nodes = ag.get("nodes", [])
            sorted_nodes = sorted(nodes, key=lambda x: x.get("influence_score", 0), reverse=True)
            top_authors = [f"{n.get('id', 'Unknown')} (Score: {n.get('influence_score',0):.1f})" for n in sorted_nodes[:5]]
            author_context += f"Top Influential Authors: {', '.join(top_authors)}.\n"
             
            diversity = ag.get("graph", {}).get("diversity_index", 0.0)
            author_context += f"Author Diversity Index: {diversity}\n"

        # ---------------------------------------------------------
        # Provenance Block (Construct manual string)
        # ---------------------------------------------------------
        kg_node_count = 0
        if state.get("knowledge_graph"):
            kg_node_count = len(state["knowledge_graph"].get("nodes", []))
            
        citation_edge_count = 0
        if state.get("citation_graph"):
            citation_edge_count = len(state["citation_graph"].get("links", []))
            
        provenance_block = f"""
## Evidence Summary
- **Papers Analyzed**: {len(state.get("selected_papers", []))}
- **Knowledge Graph Nodes**: {kg_node_count}
- **Citation Edges**: {citation_edge_count}
- **Authors Mapped**: {len(ag.get("nodes", []) if ag else [])}
<!-- Generated by VRA Reporting Agent -->
"""

        # ---------------------------------------------------------
        # Step 2: Generation
        # ---------------------------------------------------------
        context_prompt = (
            f"{gaps_context}\n"
            f"{trends_context}\n"
            f"{author_context}\n"
            f"## Detailed Paper Analysis\n{papers_context}\n"
        )
        
        prompt = (
            f"You are a research expert acting as a {audience.upper()} consultant.\n"
            f"Write a comprehensive report for the query: '{query}'.\n\n"
            f"=== DATA CONTEXT ===\n"
            f"{context_prompt}\n\n"
            f"=== REPORT STRUCTURE ===\n"
            f"{template_content}\n\n"
            f"IMPORTANT: Do NOT hallucinate data. Use the provided context IDs where possible.\n"
        )

        try:
            report_body = generate_report_content(prompt)
            
            # Manual Append for Safety
            final_report = report_body + "\n" + provenance_block
            
            state["draft_report"] = final_report
            state["current_step"] = "awaiting_final_review"
            logger.info("✅ Report generated successfully (Enhanced).")
        except Exception as e:
            logger.error(f"Reporting failed: {e}")
            state["error"] = f"Report generation failed: {str(e)}"
            state["current_step"] = "failed"
        
        return state

reporting_agent = ReportingAgent()
