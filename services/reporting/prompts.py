#File: services/reporting/prompts.py
from typing import Dict

SYSTEM_PROMPT = "You are a senior scientific research assistant. Your goal is to write high-quality, evidence-backed report sections. Do not hallucinate. If data is missing, state it explicitly."

PROMPT_TEMPLATES: Dict[str, str] = {
    "executive_summary": """
Role: Scientific Editor
Task: Write an Executive Summary for a research report.
Context:
Query: {query}
Top Trends: {trend_summary}
Identified Gaps: {gap_summary}

Requirements:
- Length: 2-3 paragraphs.
- Focus on the high-level landscape.
- Do NOT cite specific papers unless crucial.
- Highlight the most significant opportunity (gap).
""",

    "trend_analysis": """
Role: Data Analyst
Task: Analyze research trends based on the provided table.
Context:
Query: {query}
Data:
{trends_table}

Requirements:
- For each ACTIVE trend, describe its status and growth.
- Clearly distinguish between "Emerging", "Saturated", and "Declining" topics.
- Mention stability/volatility.
- If data is sparse, acknowledge it ("Preliminary trend signal").
- Output format: Markdown subsections for each major trend.
""",

    "gap_analysis": """
Role: Strategic Researcher
Task: Describe research gaps and opportunities.
Context:
Query: {query}
Gaps Identified:
{gaps_list}

Requirements:
- Use "We identified..." or "Analysis suggests..." language.
- For high-confidence gaps (>0.7), use strong language ("Clear opportunity").
- For low-confidence gaps, use tentative language ("Possible under-explored area").
- Explain the 'Rationale' provided in the data.
- Output format: Markdown bullet points or short subsections.
""",

    "network_analysis": """
Role: Network Scientist
Task: Interpret the collaboration graph.
Context:
Query: {query}
Influential Authors: {author_stats}
Diversity Index: {diversity_index} (0.0 = Monolithic, 1.0 = Diverse)

Requirements:
- Discuss the key players (Influencers).
- Interpret the Diversity Index (High diversity means varied perspectives; Low means echo chamber or tight-knit group).
- If Diversity is low, warn about potential bias.
""",

    "limitations": """
Role: Scientific Auditor
Task: Write a Methodology & Limitations statement.
Context:
Stats: {provenance_stats}
Warnings: {data_warnings}

Requirements:
- Be honest about data scope.
- If warnings exist, display them prominently (e.g., "CAUTION: ...").
- Explain that metrics are derived from the specific set of retrieved papers, not the entire world's literature.
"""
}
