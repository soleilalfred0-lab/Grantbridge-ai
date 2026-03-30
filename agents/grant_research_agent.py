"""
Grant Research Agent
─────────────────────
Responsibility: Research and identify the most relevant grant programmes,
development funds, and financing schemes available to the entrepreneur
based on their industry, location, and financial needs.

Sources simulated:
  • Caribbean Development Bank (CDB) – Basic Needs Trust Fund, BNTF
  • Inter-American Development Bank (IDB) – SME programmes
  • Suriname government SME fund (S-FONDS / Staatsolie social funds)
  • CARICOM Regional Innovation Grant
  • UNDP Small Grants Programme
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import BusinessPlanState
from tools.grant_lookup import lookup_grants

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

_SYSTEM_PROMPT = """You are a grant research specialist with deep expertise in
Caribbean development financing, Suriname government programmes, and
international development bank funding.

Given an entrepreneur's profile you will:
1. Identify the 5 most relevant grant/funding programmes.
2. For each programme return a JSON object with:
   {
     "name": "Programme name",
     "provider": "Providing institution",
     "max_amount_usd": 50000,
     "eligibility_criteria": ["criterion 1", "criterion 2"],
     "required_documents": ["document 1"],
     "focus_areas": ["agriculture", "tech"],
     "application_url": "https://...",
     "deadline_notes": "Rolling / Annual",
     "match_score": 0.85   // 0-1 relevance to this entrepreneur
   }
3. Return ONLY a JSON array of these objects.
"""


def grant_research_agent_node(state: BusinessPlanState) -> dict[str, Any]:
    """LangGraph node for the Grant Research Agent."""
    logger.info("Grant Research Agent: finding relevant grants")

    # First try the structured grant lookup tool
    tool_grants = lookup_grants(
        industry=state.get("industry", ""),
        location=state.get("location", "Suriname"),
        funding_needed=state.get("financial_expectations", ""),
    )

    profile = {
        "business_name":         state.get("business_name", ""),
        "startup_idea":          state.get("startup_idea", ""),
        "industry":              state.get("industry", ""),
        "location":              state.get("location", ""),
        "target_customers":      state.get("target_customers", ""),
        "financial_expectations": state.get("financial_expectations", ""),
        "founder_background":    state.get("founder_background", ""),
    }

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Entrepreneur profile:\n{json.dumps(profile, indent=2)}\n\n"
            f"Pre-screened grants from database:\n{json.dumps(tool_grants, indent=2)}\n\n"
            "Using both the profile and pre-screened results, return the final "
            "ranked list as a JSON array only (no markdown fences)."
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
        grants: list = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Grant Research Agent: JSON parse error – %s", exc)
        grants = tool_grants

    # Sort by match_score descending
    grants.sort(key=lambda g: g.get("match_score", 0), reverse=True)
    top_grants = grants[:3]

    return {
        "available_grants":      grants,
        "best_matching_grants":  top_grants,
        "current_step":          "market_research",
        "messages": [{
            "role":    "grant_research_agent",
            "content": f"Found {len(grants)} relevant grants; top 3 selected.",
            "data":    top_grants,
        }],
    }
