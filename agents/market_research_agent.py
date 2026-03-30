"""
Market Research Agent
──────────────────────
Responsibility: Generate comprehensive market intelligence focused on the
Suriname and broader CARICOM market context, including:
  • Market size and growth rate
  • Competitor landscape
  • Target customer personas
  • SWOT analysis
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import BusinessPlanState

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)

_SYSTEM_PROMPT = """You are a senior market research analyst specialising in
Caribbean and Suriname markets. You have deep knowledge of:
  • Surinamese consumer behaviour and purchasing power
  • CARICOM trade dynamics
  • Emerging sectors: agritech, fintech, tourism, creative industries, logistics
  • Regional competitors and international players entering the Caribbean

For the given business profile, produce a structured JSON object with:
{
  "market_size": "Narrative with estimated TAM/SAM/SOM for Caribbean/Suriname",
  "market_growth_rate": "e.g. 12% CAGR over 5 years",
  "competitor_overview": "Narrative: 3-5 key competitors with strengths/weaknesses",
  "target_customer_analysis": "Demographic + psychographic breakdown, buying triggers",
  "swot_analysis": {
    "strengths":     ["S1", "S2"],
    "weaknesses":    ["W1", "W2"],
    "opportunities": ["O1", "O2"],
    "threats":       ["T1", "T2"]
  },
  "market_entry_strategy": "Recommended go-to-market approach for Suriname/CARICOM",
  "key_market_risks": ["Risk 1", "Risk 2"]
}

Return ONLY valid JSON (no markdown fences).
"""


def market_research_agent_node(state: BusinessPlanState) -> dict[str, Any]:
    """LangGraph node for the Market Research Agent."""
    logger.info("Market Research Agent: generating market intelligence")

    profile = {
        "business_name":     state.get("business_name", ""),
        "startup_idea":      state.get("startup_idea", ""),
        "industry":          state.get("industry", ""),
        "location":          state.get("location", ""),
        "target_customers":  state.get("target_customers", ""),
        "matched_grants":    [g.get("name") for g in state.get("best_matching_grants", [])],
    }

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Business profile:\n{json.dumps(profile, indent=2)}\n\n"
            "Generate the market research JSON object."
        )),
    ]

    response = _llm.invoke(messages)
    raw_text = response.content.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    try:
        research: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Market Research Agent: JSON parse error – %s", exc)
        research = {
            "market_size":              "Market data unavailable – please research manually.",
            "competitor_overview":      "Competitor data unavailable.",
            "target_customer_analysis": "Customer analysis unavailable.",
            "swot_analysis": {
                "strengths":     [],
                "weaknesses":    [],
                "opportunities": [],
                "threats":       [],
            },
        }

    return {
        "market_size":              research.get("market_size", ""),
        "competitor_overview":      research.get("competitor_overview", ""),
        "target_customer_analysis": research.get("target_customer_analysis", ""),
        "swot_analysis":            research.get("swot_analysis", {}),
        "current_step":             "plan_writing",
        "messages": [{
            "role":    "market_research_agent",
            "content": "Market research complete.",
            "data":    research,
        }],
    }
